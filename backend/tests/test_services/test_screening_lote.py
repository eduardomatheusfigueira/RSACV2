#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Triagem em lote — o caminho que a triagem individual não exercita.

A individual devolve a decisão na própria resposta HTTP. O lote responde 202 e
manda *todo* o resto pelo WebSocket, em segundo plano e com outra sessão de
banco. São dois caminhos diferentes o bastante para um funcionar com o outro
quebrado — que é exatamente o relato que motivou estes testes.
"""

import asyncio
from typing import List, Optional

import pytest

from app.domain.entities import Paper, Protocol
from app.infrastructure.ai.base import (
    BaseAIClient,
    ProtocolSuggestions,
    ProvedorIndisponivel,
    ScreeningResult,
)
from app.infrastructure.persistence.models import PaperModel
from app.services.screening_service import AuditActor
from tests.conftest import OWNER_ID_TESTE
from tests.test_services.conftest import (
    RESUMO_DE_TESTE,
    ClienteDeTeste,
    _montar_projeto,
)


@pytest.mark.anyio
async def test_lote_tria_todos_os_pendentes(db_session, servico_de_lote):
    """O lote precisa chamar a IA uma vez por artigo pendente e gravar a decisão."""
    servico, cliente, espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=3)

    await servico.run_batch_screening(projeto_id, limit=50, concurrency=2,
                                      actor=AuditActor(user_id=OWNER_ID_TESTE, username="dono"))

    assert len(cliente.chamadas) == 3, (
        f"A IA foi chamada {len(cliente.chamadas)} vez(es) para 3 pendentes. "
        f"Eventos emitidos: {espiao.tipos()}"
    )

    decisoes = [
        p.decision
        for p in db_session.query(PaperModel).filter(PaperModel.project_id == projeto_id).all()
    ]
    assert decisoes == ["Incluído"] * 3, f"Decisões gravadas: {decisoes}"


@pytest.mark.anyio
async def test_lote_anuncia_inicio_progresso_e_fim(db_session, servico_de_lote):
    """A tela só sabe do lote pelo canal: os três marcos precisam sair."""
    servico, _cliente, espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=2)

    await servico.run_batch_screening(projeto_id, limit=50, concurrency=1)

    tipos = espiao.tipos()
    assert "batch_screening_started" in tipos, f"Sem anúncio de início: {tipos}"
    assert tipos.count("batch_screening_item_start") == 2, f"Eventos: {tipos}"
    assert tipos.count("batch_screening_progress") == 2, f"Eventos: {tipos}"
    assert "batch_screening_completed" in tipos, f"Sem anúncio de fim: {tipos}"
    assert "batch_screening_failed" not in tipos, (
        f"O lote falhou: {[m for m in espiao.mensagens if m.get('type') == 'batch_screening_failed']}"
    )


@pytest.mark.anyio
async def test_lote_sem_pendentes_avisa_em_vez_de_silenciar(db_session, servico_de_lote):
    """Sem artigos pendentes, a tela precisa ouvir 'vazio' — e não ficar em 0/N."""
    servico, cliente, espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=0)

    await servico.run_batch_screening(projeto_id, limit=50, concurrency=1)

    assert espiao.tipos() == ["batch_screening_empty"]
    assert cliente.chamadas == []


@pytest.mark.anyio
async def test_limite_recorta_o_lote(db_session, servico_de_lote):
    """`limit` é o teto de artigos do lote — e o que a janela envia ao servidor."""
    servico, cliente, _espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=5)

    await servico.run_batch_screening(projeto_id, limit=2, concurrency=1)

    assert len(cliente.chamadas) == 2


@pytest.mark.anyio
async def test_lote_ignora_duplicatas(db_session, servico_de_lote):
    """O lote precisa triar o mesmo conjunto que a tela conta e mostra.

    A fila de triagem (`GET /papers`) e o contador do projeto (`GET /stats`)
    excluem duplicatas. Se o lote não excluir, ele gasta o limite em registros
    que o pesquisador já removeu do acervo — e a tela não muda, porque aqueles
    registros não estão nela.
    """
    servico, cliente, _espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=0)

    db_session.add(
        PaperModel(
            id="paper-dup",
            project_id=projeto_id,
            title="Duplicata pendente",
            abstract=RESUMO_DE_TESTE,
            decision="Pendente",
            is_duplicate=True,
        )
    )
    db_session.add(
        PaperModel(
            id="paper-unico",
            project_id=projeto_id,
            title="Estudo único pendente",
            abstract=RESUMO_DE_TESTE,
            decision="Pendente",
            is_duplicate=False,
        )
    )
    db_session.commit()

    await servico.run_batch_screening(projeto_id, limit=50, concurrency=1)

    assert cliente.chamadas == ["Estudo único pendente"], (
        f"O lote triou duplicatas: {cliente.chamadas}"
    )


class ClienteSemCota(BaseAIClient):
    """Recusa toda chamada como o provedor faz quando a cota acaba."""

    def __init__(self):
        super().__init__(provider_name="mock", model_name="mock-model")
        self.chamadas = 0

    async def analyze_screening(self, paper: Paper, protocol: Protocol) -> ScreeningResult:
        self.chamadas += 1
        raise ProvedorIndisponivel(
            "O Gemini recusou todas as tentativas por limite de uso.",
            esgotado_por_cota=True,
        )

    async def generate_protocol_suggestions(self, *args, **kwargs) -> ProtocolSuggestions:
        return ProtocolSuggestions(objective="", descriptors_pt=[])

    async def assist_field(self, *args, **kwargs) -> str:  # type: ignore[override]
        return ""

    async def test_connection(self) -> bool:
        return True


@pytest.mark.anyio
async def test_lote_para_quando_a_cota_do_provedor_acaba(db_session, servico_de_lote):
    """Cota esgotada é falha de TODOS os artigos, não de um.

    Sem isto, o lote seguia até o fim marcando cada estudo como processado com
    decisão "Pendente", anunciava `batch_screening_completed` e o pesquisador
    via um lote que rodou inteiro sem decidir nada — sem nenhuma pista de que a
    causa era a cota da chave.
    """
    servico, _cliente, espiao = servico_de_lote
    servico.ai_client = ClienteSemCota()
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=20)

    await servico.run_batch_screening(projeto_id, limit=20, concurrency=2)

    tipos = espiao.tipos()
    assert "batch_screening_failed" in tipos, f"O lote não avisou da queda: {tipos}"
    assert "batch_screening_completed" not in tipos, (
        "O lote anunciou conclusão apesar de não ter decidido nada."
    )

    falha = next(m for m in espiao.mensagens if m["type"] == "batch_screening_failed")
    assert "limite de uso" in falha["message"]

    # Desistiu cedo: não gastou uma tentativa por artigo.
    assert servico.ai_client.chamadas < 20, (
        f"Insistiu {servico.ai_client.chamadas} vezes com o provedor fora do ar."
    )

    # Nenhum estudo foi marcado: todos continuam pendentes para a próxima vez.
    pendentes = (
        db_session.query(PaperModel)
        .filter(PaperModel.project_id == projeto_id, PaperModel.decision == "Pendente")
        .count()
    )
    assert pendentes == 20, f"Estudos alterados indevidamente: restaram {pendentes} pendentes."


class ClienteQueOscila(BaseAIClient):
    """Recusa uma vez a cada tantos, como um limite de taxa passageiro."""

    def __init__(self, recusar_a_cada: int = 3):
        super().__init__(provider_name="mock", model_name="mock-model")
        self.recusar_a_cada = recusar_a_cada
        self.chamadas = 0

    async def analyze_screening(self, paper: Paper, protocol: Protocol) -> ScreeningResult:
        self.chamadas += 1
        if self.chamadas % self.recusar_a_cada == 0:
            raise ProvedorIndisponivel("Limite de taxa momentâneo.", esgotado_por_cota=True)
        return ScreeningResult(
            decision="Incluído",
            inclusion_criteria={},
            exclusion_criteria={},
            justification="Atende.",
            confidence=0.9,
            model_used="mock-model",
            provider="mock",
        )

    async def generate_protocol_suggestions(self, *args, **kwargs) -> ProtocolSuggestions:
        return ProtocolSuggestions(objective="", descriptors_pt=[])

    async def assist_field(self, *args, **kwargs) -> str:  # type: ignore[override]
        return ""

    async def test_connection(self) -> bool:
        return True


@pytest.mark.anyio
async def test_recusa_passageira_nao_derruba_o_lote(db_session, servico_de_lote):
    """Limite de taxa intercalado com sucessos é soluço, não queda.

    É o caso normal de uma triagem em lote: o provedor recusa de vez em quando,
    o cliente espera e a próxima passa. Se o lote desistisse na primeira recusa,
    interromperia um trabalho que ia terminar — e foi para evitar isso que a
    desistência passou a exigir recusas CONSECUTIVAS.
    """
    servico, _cliente, espiao = servico_de_lote
    servico.ai_client = ClienteQueOscila(recusar_a_cada=3)
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=9)

    await servico.run_batch_screening(projeto_id, limit=9, concurrency=1)

    tipos = espiao.tipos()
    assert "batch_screening_completed" in tipos, f"O lote desistiu por um soluço: {tipos}"
    assert "batch_screening_failed" not in tipos

    incluidos = (
        db_session.query(PaperModel)
        .filter(PaperModel.project_id == projeto_id, PaperModel.decision == "Incluído")
        .count()
    )
    assert incluidos >= 5, f"Triou apenas {incluidos} de 9 apesar de o provedor responder."


@pytest.mark.anyio
async def test_estado_mostra_o_lote_inteiro_desde_o_inicio(db_session, servico_de_lote):
    """A janela precisa poder responder "quais estudos entraram neste lote?".

    Antes, o estado do lote era só contadores mais o estudo do momento: a
    relação dos estudos nunca existia em lugar nenhum, e a tela tentava
    remontá-la a partir dos eventos que passavam. Quem perdesse o canal — ou
    abrisse a janela no meio — não tinha como recuperar o conjunto.
    """
    servico, _cliente, espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=4)

    vistos = []
    original = servico.screen_single_paper

    async def espiar(db, pid_projeto, paper_id, actor=None):
        # Fotografa a relação no meio do caminho, antes de o lote acabar.
        vistos.append([dict(i) for i in servico.get_batch_state(pid_projeto)["itens"]])
        return await original(db, pid_projeto, paper_id, actor=actor)

    servico.screen_single_paper = espiar
    await servico.run_batch_screening(projeto_id, limit=10, concurrency=1)

    # O anúncio de início já leva a relação completa.
    inicio = next(m for m in espiao.mensagens if m["type"] == "batch_screening_started")
    assert len(inicio["itens"]) == 4
    assert {i["status"] for i in inicio["itens"]} == {"na_fila"}

    # No meio do lote convivem os três estados.
    meio = vistos[2]
    assert [i["status"] for i in meio] == ["concluido", "concluido", "em_analise", "na_fila"]
    assert all(i["decision"] == "Incluído" for i in meio[:2])
    assert all(i["justification"] for i in meio[:2])
    assert meio[3]["decision"] is None


@pytest.mark.anyio
async def test_justificativa_da_relacao_e_recortada(db_session, servico_de_lote):
    """A relação inteira viaja a cada consulta: o texto integral não cabe."""

    class ClienteFalante(ClienteDeTeste):
        async def analyze_screening(self, paper, protocol):
            r = await super().analyze_screening(paper, protocol)
            r.justification = "x" * 5000
            return r

    servico, _c, _e = servico_de_lote
    servico.ai_client = ClienteFalante()
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=1)

    await servico.run_batch_screening(projeto_id, limit=1, concurrency=1)

    # A relação inteira viaja a cada consulta de situação: o texto integral de
    # 500 estudos viraria uma resposta de centenas de milhares de caracteres.
    desfecho = servico.get_batch_state(projeto_id)
    assert desfecho is not None
    justificativa = desfecho["itens"][0]["justification"]
    assert len(justificativa) == 400, f"Guardou {len(justificativa)} caracteres na relação."

    # No evento do canal, que é por estudo, o texto vai inteiro.
    progresso = next(m for m in _e.mensagens if m["type"] == "batch_screening_progress")
    assert len(progresso["justification"]) == 5000


@pytest.mark.anyio
async def test_ritmo_espaca_os_disparos(db_session, servico_de_lote):
    """Limitar a concorrência não limita a velocidade.

    Com concorrência 1 e chamadas rápidas, o lote dispara uma requisição logo
    atrás da outra — uma chamada de três segundos vira vinte por minuto, acima
    do limite do provedor. A pausa entre disparos é o controle que faltava.
    """
    servico, _cliente, _espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=4)

    instantes = []
    original = servico.screen_single_paper

    async def marcar(db, pid_projeto, paper_id, actor=None):
        instantes.append(asyncio.get_running_loop().time())
        return await original(db, pid_projeto, paper_id, actor=actor)

    servico.screen_single_paper = marcar
    await servico.run_batch_screening(
        projeto_id, limit=4, concurrency=1, pausa_entre_estudos=0.25
    )

    assert len(instantes) == 4
    intervalos = [b - a for a, b in zip(instantes, instantes[1:])]
    assert all(i >= 0.2 for i in intervalos), f"Disparos colados: {intervalos}"


@pytest.mark.anyio
async def test_sem_pausa_o_lote_nao_espera(db_session, servico_de_lote):
    """Quem escolhe ritmo livre não deve pagar espera nenhuma."""
    servico, _cliente, _espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=5)

    inicio = asyncio.get_running_loop().time()
    await servico.run_batch_screening(
        projeto_id, limit=5, concurrency=2, pausa_entre_estudos=0
    )
    duracao = asyncio.get_running_loop().time() - inicio

    assert duracao < 1.0, f"Esperou {duracao:.2f}s com a pausa desligada."


@pytest.mark.anyio
async def test_lote_nao_analisa_dois_estudos_ao_mesmo_tempo(db_session, servico_de_lote):
    """Uma triagem por vez, por padrão.

    O paralelismo não acelerava o que importa — o gargalo é o tempo de resposta
    do provedor — e multiplicava por N a chance de bater no limite de
    requisições. Também tornava o acompanhamento confuso: com três em análise,
    "o estudo sendo triado agora" deixa de ser uma coisa só.
    """
    servico, _cliente, _espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=6)

    em_voo = 0
    pico = 0
    original = servico.screen_single_paper

    async def contar(db, pid_projeto, paper_id, actor=None):
        nonlocal em_voo, pico
        em_voo += 1
        pico = max(pico, em_voo)
        try:
            await asyncio.sleep(0.02)
            return await original(db, pid_projeto, paper_id, actor=actor)
        finally:
            em_voo -= 1

    servico.screen_single_paper = contar
    # Sem passar `concurrency`: é o padrão que precisa ser sequencial.
    await servico.run_batch_screening(projeto_id, limit=6, pausa_entre_estudos=0)

    assert pico == 1, f"Chegou a analisar {pico} estudos ao mesmo tempo."


@pytest.mark.anyio
async def test_desfecho_do_lote_sobrevive_ao_encerramento(db_session, servico_de_lote):
    """Quem acompanha pela consulta periódica só sabe do fim por ela.

    O estado era descartado no instante em que o lote terminava. A última
    consulta antes do fim via N-1 de N; a seguinte encontrava `None`, e o último
    estudo ficava eternamente "analisando" na tela — o relato de que "o último
    do lote sempre trava", quando o lote havia terminado normalmente.
    """
    servico, _cliente, espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=3)

    await servico.run_batch_screening(projeto_id, limit=3, concurrency=1, pausa_entre_estudos=0)

    assert "batch_screening_completed" in espiao.tipos()

    desfecho = servico.get_batch_state(projeto_id)
    assert desfecho is not None, "O desfecho foi descartado ao terminar."
    assert desfecho["encerrado"] is True
    assert desfecho["processed"] == 3
    assert desfecho["total"] == 3
    assert all(i["status"] == "concluido" for i in desfecho["itens"])
    assert desfecho["current_paper_title"] == "", "Ficou um estudo 'em análise' depois do fim."


@pytest.mark.anyio
async def test_estudo_nao_decidido_volta_para_a_fila_no_desfecho(db_session, servico_de_lote):
    """Interrompido no meio, nada pode ficar preso em 'analisando'."""
    servico, _cliente, espiao = servico_de_lote
    servico.ai_client = ClienteSemCota()
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=5)

    await servico.run_batch_screening(projeto_id, limit=5, concurrency=1, pausa_entre_estudos=0)

    desfecho = servico.get_batch_state(projeto_id)
    assert desfecho is not None
    assert not any(i["status"] == "em_analise" for i in desfecho["itens"]), (
        "Sobrou estudo marcado como em análise depois do encerramento."
    )


@pytest.mark.anyio
async def test_lote_novo_substitui_o_desfecho_anterior(db_session, servico_de_lote):
    """O registro do desfecho não pode virar acúmulo."""
    servico, _cliente, _espiao = servico_de_lote
    projeto_id = _montar_projeto(db_session, quantidade_pendentes=4)

    await servico.run_batch_screening(projeto_id, limit=2, concurrency=1, pausa_entre_estudos=0)
    primeiro = servico.get_batch_state(projeto_id)
    assert primeiro["total"] == 2

    await servico.run_batch_screening(projeto_id, limit=2, concurrency=1, pausa_entre_estudos=0)
    segundo = servico.get_batch_state(projeto_id)
    assert segundo["total"] == 2
    assert segundo is not primeiro, "O segundo lote reaproveitou o registro do primeiro."
