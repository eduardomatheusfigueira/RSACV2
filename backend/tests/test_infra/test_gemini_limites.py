#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Cliente Gemini — limites, cotas e rodízio de chaves e modelos.

Escrito ao longo de uma investigação em que a triagem em lote parava por
motivos sucessivos e diferentes. As decisões aqui saíram de medição contra a
API real, e o essencial é este: **o Gemini limita por projeto E por modelo** —
o identificador da cota é literalmente
`GenerateRequestsPerDayPerProjectPerModel`. Cada chave do AI Studio é um
projeto; cada modelo tem cota própria dentro dele.
"""

import asyncio
import json as _json

import pytest

from app.infrastructure.ai.base import ProvedorIndisponivel
from app.infrastructure.ai.gemini_client import GeminiAIClient

RESPOSTA_OK = '{"candidates":[{"content":{"parts":[{"text":"{\\"ok\\":1}"}]}}]}'

COTA_DIARIA = "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
COTA_POR_MINUTO = "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"


class RespostaFalsa:
    def __init__(self, status: int, corpo: str = "{}", headers: dict | None = None):
        self.status_code = status
        self.text = corpo
        self.headers = headers or {}

    def json(self):
        return _json.loads(self.text)


def corpo_de_cota(quota_id: str) -> str:
    """Corpo de 429 no formato do Google, com o identificador da cota."""
    return _json.dumps(
        {
            "error": {
                "code": 429,
                "message": "You exceeded your current quota",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [{"quotaId": quota_id}],
                    }
                ],
            }
        }
    )


class HttpFalso:
    """Cliente HTTP simulado: a resposta é decidida por (modelo, chave)."""

    def __init__(self, decidir):
        self._decidir = decidir
        self.pares = []
        self.gets = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None):
        modelo = url.split("/models/")[1].split(":")[0]
        chave = url.split("key=")[-1]
        self.pares.append((modelo, chave))
        return self._decidir(modelo, chave)

    async def get(self, url):
        self.gets.append(url)
        return self._decidir("catalogo", url.split("key=")[-1])


def montar(monkeypatch, decidir, chaves, modelo="gemini-3.6-flash"):
    import app.infrastructure.ai.gemini_client as modulo

    falso = HttpFalso(decidir)
    monkeypatch.setattr(modulo.httpx, "AsyncClient", lambda **kw: falso)
    return GeminiAIClient(api_keys=chaves, model_name=modelo), falso


@pytest.fixture(autouse=True)
def memoria_dos_pares_limpa():
    """Zera o que o cliente sabe sobre os pares entre um teste e outro.

    O descanso e a posição do rodízio são de CLASSE de propósito — a fábrica
    constrói um cliente novo por artigo, e essa memória precisa sobreviver a
    isso. A contrapartida é esta limpeza.
    """
    GeminiAIClient._DESCANSO_POR_CHAVE.clear()
    GeminiAIClient._POSICAO_DO_RODIZIO.clear()
    yield
    GeminiAIClient._DESCANSO_POR_CHAVE.clear()
    GeminiAIClient._POSICAO_DO_RODIZIO.clear()


@pytest.fixture
def sem_espera(monkeypatch):
    async def _dormir(_segundos):
        return None

    monkeypatch.setattr(asyncio, "sleep", _dormir)


# ── Diagnóstico do 429 ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_cota_esgotada_vira_erro_tipado(monkeypatch, sem_espera):
    cliente, _ = montar(
        monkeypatch, lambda m, k: RespostaFalsa(429, corpo_de_cota(COTA_POR_MINUTO)), ["AIzaSyA"]
    )

    with pytest.raises(ProvedorIndisponivel) as excecao:
        await cliente._call_gemini_api("prompt")

    assert excecao.value.esgotado_por_cota is True


@pytest.mark.anyio
async def test_modelo_inexistente_nao_apaga_o_diagnostico_de_cota(monkeypatch, sem_espera):
    """Um 404 não é evidência sobre a cota, e não pode encobrir o diagnóstico.

    É o caso real desta instalação: `gemini-2.5-pro` saiu do catálogo e
    responde 404 permanente.
    """

    def decidir(modelo, chave):
        if modelo == "gemini-3.6-flash":
            return RespostaFalsa(404, '{"error":{"code":404}}')
        return RespostaFalsa(429, corpo_de_cota(COTA_POR_MINUTO))

    cliente, _ = montar(monkeypatch, decidir, ["AIzaSyA"])

    with pytest.raises(ProvedorIndisponivel) as excecao:
        await cliente._call_gemini_api("prompt")

    assert excecao.value.esgotado_por_cota is True


@pytest.mark.anyio
async def test_falha_de_servidor_nao_e_diagnosticada_como_cota(monkeypatch, sem_espera):
    cliente, _ = montar(monkeypatch, lambda m, k: RespostaFalsa(500, "erro interno"), ["AIzaSyA"])

    with pytest.raises(ProvedorIndisponivel) as excecao:
        await cliente._call_gemini_api("prompt")

    assert excecao.value.esgotado_por_cota is False


@pytest.mark.anyio
async def test_espera_respeita_o_retry_after_do_provedor(monkeypatch):
    """A janela do limite por minuto é de um minuto; 0,3s não esperava nada."""
    esperas = []

    async def _dormir(segundos):
        esperas.append(segundos)

    monkeypatch.setattr(asyncio, "sleep", _dormir)

    cliente, _ = montar(
        monkeypatch,
        lambda m, k: RespostaFalsa(429, corpo_de_cota(COTA_POR_MINUTO), {"retry-after": "35"}),
        ["AIzaSyA"],
    )

    with pytest.raises(ProvedorIndisponivel):
        await cliente._call_gemini_api("prompt")

    assert esperas and esperas[0] == 35.0, f"Ignorou o Retry-After: {esperas}"


def test_cadeia_de_reserva_nao_tem_modelo_fora_de_catalogo():
    """`gemini-2.5-pro` responde 404 permanente — era um degrau morto."""
    assert "gemini-2.5-pro" not in GeminiAIClient.FALLBACK_MODELS
    assert GeminiAIClient.FALLBACK_MODELS


# ── Cota diária: por projeto E por modelo ─────────────────────────────


@pytest.mark.anyio
async def test_cota_diaria_de_um_modelo_nao_bloqueia_os_outros(monkeypatch, sem_espera):
    """Medido contra a API real: com a cota diária de `gemini-3.6-flash`
    esgotada nas oito chaves, as mesmas oito respondiam HTTP 200 em
    `gemini-2.5-flash`. Marcar a CHAVE inteira como em descanso bloqueava todos
    os modelos de uma vez e nunca alcançava a cadeia de reserva.
    """

    def decidir(modelo, chave):
        if modelo == "gemini-3.6-flash":
            return RespostaFalsa(429, corpo_de_cota(COTA_DIARIA))
        return RespostaFalsa(200, RESPOSTA_OK)

    cliente, falso = montar(monkeypatch, decidir, ["AIzaSyA", "AIzaSyB"])

    assert await cliente._call_gemini_api("prompt") == {"ok": 1}

    falso.pares.clear()
    await cliente._call_gemini_api("prompt")
    assert not any(m == "gemini-3.6-flash" for m, _k in falso.pares), (
        f"Insistiu no modelo sem cota diária: {falso.pares}"
    )


@pytest.mark.anyio
async def test_cota_diaria_esgotada_em_tudo_nao_fica_esperando(monkeypatch):
    """Cota diária não volta hoje: esperar segundos é só perder tempo."""
    esperas = []

    async def _dormir(seg):
        esperas.append(seg)

    monkeypatch.setattr(asyncio, "sleep", _dormir)

    cliente, _ = montar(
        monkeypatch, lambda m, k: RespostaFalsa(429, corpo_de_cota(COTA_DIARIA)), ["AIzaSyA"]
    )

    with pytest.raises(ProvedorIndisponivel) as excecao:
        await cliente._call_gemini_api("prompt")

    assert excecao.value.esgotado_por_cota is True
    assert "DIÁRIA" in str(excecao.value)
    assert esperas == [], f"Esperou por uma cota que só volta amanhã: {esperas}"


# ── Rodízio sobre pares chave+modelo ──────────────────────────────────


@pytest.mark.anyio
async def test_chamadas_consecutivas_nao_repetem_o_mesmo_par(monkeypatch):
    """A carga se espalha, em vez de concentrar no par que deu certo.

    Fixar no vencedor esgota um orçamento de cada vez, e o custo por estudo
    cresce ao longo do lote. Medido num lote de dez antes desta mudança: os
    oito primeiros em segundos, o nono em 40s, o décimo em 70s.
    """
    cliente, falso = montar(
        monkeypatch,
        lambda m, k: RespostaFalsa(200, RESPOSTA_OK),
        ["AIzaSyA", "AIzaSyB", "AIzaSyC"],
    )

    for _ in range(3):
        await cliente._call_gemini_api("prompt")

    assert len(set(falso.pares)) == 3, f"Repetiu o mesmo par: {falso.pares}"
    # Espalha primeiro entre CHAVES — projetos distintos, o recurso mais
    # escasso — antes de trocar de modelo.
    assert len({chave for _m, chave in falso.pares}) == 3, (
        f"Concentrou numa chave só: {falso.pares}"
    )


@pytest.mark.anyio
async def test_par_recusado_sai_do_rodizio(monkeypatch, sem_espera):
    """Um par recusado não volta; os outros pares da mesma chave seguem em uso."""

    def decidir(modelo, chave):
        if chave == "AIzaSyRuim":
            return RespostaFalsa(429, corpo_de_cota(COTA_POR_MINUTO))
        return RespostaFalsa(200, RESPOSTA_OK)

    cliente, falso = montar(monkeypatch, decidir, ["AIzaSyRuim", "AIzaSyBoa"])

    for _ in range(12):
        await cliente._call_gemini_api("prompt")

    recusados = [par for par in falso.pares if par[1] == "AIzaSyRuim"]
    modelos = 1 + len(GeminiAIClient.FALLBACK_MODELS)
    assert len(recusados) <= modelos, (
        f"Insistiu na chave sem cota: {len(recusados)} recusas em 12 chamadas."
    )
    assert len(set(recusados)) == len(recusados), "Repetiu o mesmo par recusado."


@pytest.mark.anyio
async def test_memoria_dos_pares_sobrevive_a_troca_de_cliente(monkeypatch, sem_espera):
    """A fábrica constrói um cliente novo a cada artigo triado.

    Se o que se sabe sobre os pares morresse junto com o objeto, cada estudo
    redescobriria do zero quais estão sem cota — o que fez o primeiro estudo de
    um lote levar mais de cinco minutos.
    """

    def decidir(modelo, chave):
        if chave == "AIzaSyEsgotada":
            return RespostaFalsa(429, corpo_de_cota(COTA_POR_MINUTO))
        return RespostaFalsa(200, RESPOSTA_OK)

    import app.infrastructure.ai.gemini_client as modulo

    falso = HttpFalso(decidir)
    monkeypatch.setattr(modulo.httpx, "AsyncClient", lambda **kw: falso)

    for _ in range(12):
        cliente = GeminiAIClient(
            api_keys=["AIzaSyEsgotada", "AIzaSyBoa"], model_name="gemini-3.6-flash"
        )
        await cliente._call_gemini_api("prompt")

    recusados = [par for par in falso.pares if par[1] == "AIzaSyEsgotada"]
    modelos = 1 + len(GeminiAIClient.FALLBACK_MODELS)
    assert len(recusados) <= modelos, (
        f"A memória não sobreviveu: {len(recusados)} recusas em 12 artigos."
    )


# ── Diagnóstico da conexão ────────────────────────────────────────────


@pytest.mark.anyio
async def test_diagnostico_testa_todas_as_chaves(monkeypatch):
    """Uma chave ruim entre boas não pode reprovar o conjunto."""

    def decidir(modelo, chave):
        if chave == "AIzaSyRuim":
            return RespostaFalsa(400, '{"error":{"message":"recusada"}}')
        return RespostaFalsa(200)

    cliente, falso = montar(monkeypatch, decidir, ["AIzaSyRuim", "AIzaSyBoa1", "AIzaSyBoa2"])

    d = await cliente.diagnosticar_conexao()

    assert d.ok is True
    assert (d.chaves_testadas, d.chaves_boas, d.chaves_recusadas) == (3, 2, 1)
    assert len(falso.gets) == 3, "Não testou todas as chaves."


@pytest.mark.anyio
async def test_diagnostico_nao_gasta_cota_de_geracao(monkeypatch):
    """`generateContent` consumia uma requisição do limite só para dizer
    "está ligado" — e, repetido, provocava o 429 seguinte."""
    cliente, falso = montar(monkeypatch, lambda m, k: RespostaFalsa(200), ["AIzaSyBoa"])

    await cliente.diagnosticar_conexao()

    assert falso.gets
    assert all("generateContent" not in u for u in falso.gets)
    assert not falso.pares, "Gerou conteúdo no teste de conexão."


@pytest.mark.anyio
async def test_limite_de_taxa_nao_e_relatado_como_chave_invalida(monkeypatch):
    """429 no teste significa 'espere', não 'sua chave está errada'."""
    cliente, _ = montar(monkeypatch, lambda m, k: RespostaFalsa(429), ["AIzaSyA", "AIzaSyB"])

    d = await cliente.diagnosticar_conexao()

    assert d.ok is False
    assert d.limite_de_taxa is True
    assert "não é preciso trocar" in d.mensagem


@pytest.mark.anyio
async def test_entradas_que_nao_sao_chave_sao_apontadas(monkeypatch):
    """Colar algo que não é chave do AI Studio precisa ser dito."""
    cliente, _ = montar(
        monkeypatch, lambda m, k: RespostaFalsa(200), ["AQ.Ab8RN6Jalgo", "AIzaSyBoa"]
    )

    d = await cliente.diagnosticar_conexao()

    assert d.ok is True
    assert d.chaves_ignoradas == 1
    assert "AI Studio" in d.mensagem


@pytest.mark.anyio
async def test_so_entradas_invalidas_explica_onde_gerar_a_chave(monkeypatch):
    cliente, _ = montar(monkeypatch, lambda m, k: RespostaFalsa(200), ["AQ.Ab8RN6J", "sk-outra"])

    d = await cliente.diagnosticar_conexao()

    assert d.ok is False
    assert "aistudio.google.com" in d.mensagem


@pytest.mark.anyio
async def test_espera_ate_o_primeiro_par_voltar_e_nao_ate_o_ultimo(monkeypatch):
    """Basta um par livre para a chamada seguir.

    Cada par pede o seu próprio prazo, e esperar o MAIOR deles deixava o lote
    parado enquanto um par já disponível estava à mão — os prazos são de
    projetos e modelos independentes, e um não diz nada sobre o outro.
    """
    esperas = []

    async def _dormir(seg):
        esperas.append(seg)

    monkeypatch.setattr(asyncio, "sleep", _dormir)

    def decidir(modelo, chave):
        # Uma pede muito tempo; a outra, o mínimo.
        atraso = "300" if chave == "AIzaSyLenta" else "1"
        return RespostaFalsa(429, corpo_de_cota(COTA_POR_MINUTO), {"retry-after": atraso})

    cliente, _ = montar(monkeypatch, decidir, ["AIzaSyLenta", "AIzaSyRapida"])

    with pytest.raises(ProvedorIndisponivel):
        await cliente._call_gemini_api("prompt")

    assert esperas, "Não esperou nada."
    assert max(esperas) <= GeminiAIClient.DESCANSO_MINIMO_DA_CHAVE + 1, (
        f"Esperou o prazo do par mais lento em vez do mais rápido: {esperas}"
    )
