#!/usr/bin/env python

"""
Cobertura de autenticação (doc 28 V-01, doc 29 §29.3.1).

Este é o teste mais importante da suíte, e o motivo é a durabilidade: ele não
verifica que *as rotas de hoje* exigem credencial — ele **enumera** o que a
aplicação expõe e exige credencial de cada uma, com uma lista de exceções
escrita à mão. Uma rota nova que nasça desprotegida derruba o teste sem que
ninguém precise lembrar de cobri-la.

A credencial mudou de forma (era sessão por cookie, virou o token local no
cabeçalho); a garantia que este arquivo fixa é a mesma.

É o par do desenho em `api/v1/router.py`: lá a proteção é ligada no agregador
para que o padrão seja "protegido"; aqui se verifica que o padrão pegou.
"""

import pytest

from app.main import create_app

# A lista **completa** de rotas que respondem sem credencial (§29.3.1).
#
# Acrescentar algo aqui é uma decisão de segurança e deve ser justificada no
# mesmo commit. Eram quatro; são duas, porque `login` e a troca do token local
# por sessão deixaram de existir:
#   /health        — o Electron precisa saber se o processo subiu
#   /auth/status   — o app precisa distinguir "não subiu" de "token não bate"
ROTAS_PUBLICAS = {
    "/api/v1/health",
    "/api/v1/auth/status",
}

# Corpos mínimos para as rotas que validam o schema antes de olhar a sessão.
# Sem eles a resposta seria 422 e o teste não provaria nada sobre autenticação.
CORPOS = {
    ("PUT", "/api/v1/ai/settings"): {
        "ai_enabled": True,
        "provider": "gemini",
        "model": "gemini-3.6-flash",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    ("POST", "/api/v1/profile/keys/export"): {"export_password": "senha-de-teste-123"},
    ("POST", "/api/v1/profile/keys/import"): {"payload": {}},
    ("POST", "/api/v1/profile/import"): {"schema_version": "x"},
    ("PUT", "/api/v1/settings/sources/Scopus"): {"api_key": "x"},
}


def _placeholder(caminho: str) -> str:
    """Troca os parâmetros de rota por um valor qualquer — o alvo não importa."""
    partes = []
    for parte in caminho.split("/"):
        partes.append("teste" if parte.startswith("{") and parte.endswith("}") else parte)
    return "/".join(partes)


def listar_rotas_http() -> list[tuple[str, str]]:
    """
    Enumera (método, caminho) de tudo que a aplicação publica.

    Usa o esquema OpenAPI porque esta versão do FastAPI inclui os sub-routers
    de forma preguiçosa — `app.routes` não os achata, e percorrer estruturas
    internas deixaria o teste refém de detalhe de implementação.
    """
    app = create_app()
    esquema = app.openapi()

    rotas = []
    for caminho, operacoes in esquema["paths"].items():
        for metodo in operacoes:
            if metodo.lower() in ("get", "post", "put", "patch", "delete"):
                rotas.append((metodo.upper(), caminho))
    return sorted(rotas)


ROTAS_HTTP = listar_rotas_http()


def test_a_enumeracao_encontrou_a_api_inteira():
    """Guarda contra o teste virar vácuo se a enumeração parar de funcionar."""
    assert len(ROTAS_HTTP) > 40, f"só {len(ROTAS_HTTP)} rotas enumeradas — a varredura quebrou"

    caminhos = {c for _, c in ROTAS_HTTP}
    # Âncoras: se estas sumirem, é sinal de que a lista não reflete a API real.
    for esperado in ("/api/v1/projects", "/api/v1/ai/settings", "/api/v1/profile/keys/export"):
        assert esperado in caminhos, f"{esperado} sumiu da enumeração"


@pytest.mark.anyio
@pytest.mark.parametrize("metodo,caminho", ROTAS_HTTP, ids=lambda v: str(v))
async def test_toda_rota_exige_credencial(anon_client, metodo, caminho):
    """
    Sem o token local, tudo responde 401 — exceto a lista de exceções.

    Um 422 aqui também seria falha: significaria que a rota validou o corpo
    antes de olhar a credencial, isto é, que ela processa entrada de anônimo.
    """
    if caminho in ROTAS_PUBLICAS:
        pytest.skip("rota pública declarada")

    url = _placeholder(caminho)
    corpo = CORPOS.get((metodo, caminho))
    resposta = await anon_client.request(metodo, url, json=corpo)

    assert resposta.status_code == 401, (
        f"{metodo} {caminho} respondeu {resposta.status_code} sem autenticação "
        f"(esperado 401). Corpo: {resposta.text[:200]}"
    )


@pytest.mark.anyio
@pytest.mark.parametrize("caminho", sorted(ROTAS_PUBLICAS))
async def test_rotas_publicas_respondem_sem_credencial(anon_client, caminho):
    """A lista de exceções precisa mesmo funcionar sem credencial."""
    res = await anon_client.get(caminho)
    assert res.status_code == 200


@pytest.mark.anyio
async def test_status_nao_vaza_o_token(anon_client, token_local):
    """
    A rota que responde sem credencial não pode entregar a credencial.

    Parece óbvio, e é exatamente o tipo de coisa que um campo de diagnóstico
    acrescentado com boa intenção ("para ajudar a depurar") desfaz.
    """
    res = await anon_client.get("/api/v1/auth/status")
    assert res.status_code == 200
    assert token_local not in res.text

    corpo = res.json()
    assert corpo["authenticated"] is False
    assert corpo["local_token_disponivel"] is True


@pytest.mark.anyio
async def test_credencial_valida_libera_a_api(async_client):
    """O contraponto: com o token, as mesmas rotas respondem."""
    assert (await async_client.get("/api/v1/projects")).status_code == 200
    assert (await async_client.get("/api/v1/ai/settings")).status_code == 200


@pytest.mark.anyio
async def test_credencial_inventada_e_recusada(anon_client):
    """Um token inventado não vale mais que nenhum."""
    from app.security.dependencies import LOCAL_TOKEN_HEADER

    for token in ("token-inventado", "", "null", "undefined"):
        res = await anon_client.get(
            "/api/v1/projects", headers={LOCAL_TOKEN_HEADER: token}
        )
        assert res.status_code == 401


@pytest.mark.anyio
async def test_credencial_nao_e_aceita_pela_query_em_http(anon_client, token_local):
    """
    Em HTTP o token vale só no cabeçalho.

    Aceitá-lo também na query o poria no endereço — e daí no histórico, no
    `Referer` e em qualquer captura de tela. A query é exceção do WebSocket,
    onde o navegador não oferece outra via.
    """
    res = await anon_client.get(f"/api/v1/projects?local_token={token_local}")
    assert res.status_code == 401
