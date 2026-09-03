#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""O estudo que o provedor recusa não pode sumir do lote.

Medido contra a API real: um lote de dez fechou como "concluído" tendo triado
nove. O décimo tinha recebido uma recusa isolada do Gemini — limite de taxa de
um minuto, o caso mais comum e mais passageiro que existe — e o laço apenas
`return`ava. Sem evento, sem contagem, e com o item parado em "na fila".

Da poltrona de quem olha a janela, isso é indistinguível de travar no último:
a barra fica a um estudo do fim e nada explica por quê.
"""

import pytest

from app.infrastructure.ai.base import ProvedorIndisponivel, ScreeningResult
from app.infrastructure.persistence.models import PaperModel

from tests.test_services.conftest import _montar_projeto


def _relacao(espiao):
    """A última fotografia da relação que o canal transmitiu."""
    for m in reversed(espiao.mensagens):
        if m.get("type") == "batch_screening_started":
            return m["itens"]
    return []


class RecusaOsPrimeiros:
    """Recusa as N primeiras chamadas e aceita todas as seguintes."""

    def __init__(self, analisar_original, quantas: int):
        # O método ORIGINAL, guardado antes da substituição: guardar o cliente
        # e chamá-lo faria este objeto chamar a si mesmo.
        self._original = analisar_original
        self._restam = quantas
        self.tentativas = 0

    async def __call__(self, paper, protocol) -> ScreeningResult:
        self.tentativas += 1
        if self._restam > 0:
            self._restam -= 1
            raise ProvedorIndisponivel("Limite de requisições por minuto.")
        return await self._original(paper, protocol)


@pytest.mark.anyio
async def test_recusa_passageira_devolve_o_estudo_a_fila(servico_de_lote, db_session):
    """Uma recusa isolada não descarta o estudo: ele volta numa passada seguinte.

    Com várias chaves e vários modelos, a chamada seguinte quase sempre cai num
    par que ainda tem cota — desistir na primeira negativa jogava fora um
    estudo que ia passar.
    """
    servico, cliente, espiao = servico_de_lote
    pid = _montar_projeto(db_session, quantidade_pendentes=3)
    cliente.analyze_screening = RecusaOsPrimeiros(cliente.analyze_screening, quantas=1)

    await servico.run_batch_screening(pid, limit=10, concurrency=1, pausa_entre_estudos=0.0)

    desfecho = [m for m in espiao.mensagens if m["type"] == "batch_screening_completed"][0]
    assert desfecho["total_processed"] == 3, "Perdeu o estudo que tinha sido recusado."
    assert desfecho["nao_triados"] == 0

    triados = (
        db_session.query(PaperModel)
        .filter(PaperModel.project_id == pid, PaperModel.decision == "Incluído")
        .count()
    )
    assert triados == 3


@pytest.mark.anyio
async def test_estudo_que_nao_passou_em_nenhuma_passada_e_dito_em_voz_alta(
    servico_de_lote, db_session
):
    """Se nem a repetição resolve, o estudo aparece como não triado — não some.

    Ele segue pendente no acervo e entra no próximo lote; o que não pode é
    desaparecer da relação deixando o contador parado sem explicação.
    """
    servico, cliente, espiao = servico_de_lote
    pid = _montar_projeto(db_session, quantidade_pendentes=2)

    recusados = {"paper-lote-1"}
    original = cliente.analyze_screening

    async def recusa_sempre_o_mesmo(paper, protocol):
        if paper.id in recusados:
            raise ProvedorIndisponivel("Limite de requisições por minuto.")
        return await original(paper, protocol)

    cliente.analyze_screening = recusa_sempre_o_mesmo

    await servico.run_batch_screening(pid, limit=10, concurrency=1, pausa_entre_estudos=0.0)

    avisos = [m for m in espiao.mensagens if m["type"] == "batch_screening_item_skipped"]
    assert [m["paper_id"] for m in avisos] == ["paper-lote-1"]

    desfecho = [m for m in espiao.mensagens if m["type"] == "batch_screening_completed"][0]
    assert desfecho["nao_triados"] == 1
    assert "seguem pendentes" in desfecho["message"]

    estado = servico._batch_state[pid]
    item = [i for i in estado["itens"] if i["id"] == "paper-lote-1"][0]
    assert item["status"] == "nao_triado", "Ficou 'na fila' para sempre."
    assert item["justification"], "Não disse por quê."

    # E o estudo continua pendente no acervo, pronto para o próximo lote.
    paper = db_session.query(PaperModel).filter(PaperModel.id == "paper-lote-1").one()
    assert paper.decision == "Pendente"


@pytest.mark.anyio
async def test_provedor_realmente_fora_do_ar_ainda_interrompe_o_lote(
    servico_de_lote, db_session
):
    """A repetição não pode virar teimosia.

    Chave sem cota, credencial errada ou provedor fora do ar valem para todos
    os estudos: insistir transformaria 100 estudos em 300 falhas.
    """
    servico, cliente, espiao = servico_de_lote
    pid = _montar_projeto(db_session, quantidade_pendentes=6)

    async def recusa_tudo(paper, protocol):
        raise ProvedorIndisponivel("Cota DIÁRIA esgotada em todas as chaves.")

    cliente.analyze_screening = recusa_tudo

    await servico.run_batch_screening(pid, limit=10, concurrency=1, pausa_entre_estudos=0.0)

    assert "batch_screening_failed" in espiao.tipos()
    assert "batch_screening_completed" not in espiao.tipos()
