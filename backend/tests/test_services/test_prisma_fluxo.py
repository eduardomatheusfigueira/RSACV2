#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Fluxo PRISMA 2020 — "triados" conta quem foi triado.

O diagrama PRISMA é o artefato regulado de uma revisão sistemática: é ele que
a banca lê para saber quanto trabalho foi feito. Enquanto `records_screened`
devolvia o tamanho do acervo, ele declarava como triados todos os registros do
projeto, inclusive os que ninguém tinha olhado.

Medido nos acervos reais em 01/09/2026: um projeto com **454** estudos triados
reportava 16.578 (37×); outro com **209** reportava 65.955 (316×). O número
saía na tela, na planilha exportada e no diagrama.
"""

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    HarvestRunModel,
    PaperModel,
    ProjectModel,
    ProtocolModel,
)
from app.services.export_service import ExportService
from tests.conftest import OWNER_ID_TESTE


def _projeto(db_session) -> ProjectModel:
    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto do fluxo", methodology="PRISMA")
    db_session.add(proj)
    db_session.flush()
    db_session.add(ProtocolModel(project_id=proj.id, objective="Mapear X"))
    db_session.flush()
    return proj


def _povoar(db_session, proj, *, incluidos=0, excluidos=0, pendentes=0, duplicatas=0):
    lotes = [
        (Decision.INCLUDED.value, incluidos, False),
        (Decision.EXCLUDED.value, excluidos, False),
        (Decision.PENDING.value, pendentes, False),
        (Decision.PENDING.value, duplicatas, True),
    ]
    n = 0
    for decisao, quantos, dup in lotes:
        for _ in range(quantos):
            db_session.add(
                PaperModel(
                    project_id=proj.id,
                    title=f"Estudo {n}",
                    decision=decisao,
                    is_duplicate=dup,
                )
            )
            n += 1
    db_session.commit()


def test_triados_conta_so_quem_tem_decisao(db_session):
    """O caso que motivou a correção, na proporção real do acervo."""
    proj = _projeto(db_session)
    _povoar(db_session, proj, incluidos=15, excluidos=439, pendentes=16124)

    fluxo = ExportService.get_prisma_flow_data(db_session, proj.id)["screening"]

    assert fluxo["records_screened"] == 454, "Contou o acervo inteiro como triado."
    assert fluxo["records_pending"] == 16124
    assert fluxo["records_excluded"] == 439


def test_denominador_da_triagem_e_reportado(db_session):
    """Sem o denominador, "454" é lido como se a triagem tivesse terminado."""
    proj = _projeto(db_session)
    _povoar(db_session, proj, incluidos=15, excluidos=439, pendentes=16124)

    fluxo = ExportService.get_prisma_flow_data(db_session, proj.id)["screening"]

    assert fluxo["records_to_screen"] == 16578
    assert fluxo["records_screened"] + fluxo["records_pending"] == fluxo["records_to_screen"]


def test_projeto_sem_triagem_nenhuma_reporta_zero_triados(db_session):
    """Acervo coletado e ainda não triado: zero, e não "tudo triado"."""
    proj = _projeto(db_session)
    _povoar(db_session, proj, pendentes=500)

    fluxo = ExportService.get_prisma_flow_data(db_session, proj.id)["screening"]

    assert fluxo["records_screened"] == 0
    assert fluxo["records_to_screen"] == 500


def test_revisao_terminada_tem_triados_igual_ao_denominador(db_session):
    """No fim da triagem os dois números coincidem — e é aí que a antiga
    contagem parecia certa, o que escondia o defeito."""
    proj = _projeto(db_session)
    _povoar(db_session, proj, incluidos=12, excluidos=88)

    fluxo = ExportService.get_prisma_flow_data(db_session, proj.id)["screening"]

    assert fluxo["records_screened"] == fluxo["records_to_screen"] == 100
    assert fluxo["records_pending"] == 0


def test_duplicata_nao_entra_em_nenhuma_contagem(db_session):
    """Mesmo critério da fila de triagem, do contador do projeto e do
    instantâneo. A consulta do fluxo não filtrava duplicatas."""
    proj = _projeto(db_session)
    _povoar(db_session, proj, incluidos=5, excluidos=5, pendentes=10, duplicatas=40)

    fluxo = ExportService.get_prisma_flow_data(db_session, proj.id)["screening"]

    assert fluxo["records_to_screen"] == 20, "Contou duplicatas na fila."
    assert fluxo["records_pending"] == 10


def test_identificados_vem_das_rodadas_de_coleta(db_session):
    """`identificados` é o que as bases devolveram, antes da deduplicação —
    é outro número, e continua vindo de `harvest_runs`."""
    proj = _projeto(db_session)
    _povoar(db_session, proj, incluidos=1, excluidos=1)
    db_session.add(
        HarvestRunModel(
            project_id=proj.id, source_name="SciELO", records_found=900, records_duplicate=880
        )
    )
    db_session.commit()

    fluxo = ExportService.get_prisma_flow_data(db_session, proj.id)

    assert fluxo["identification"]["total_records_identified"] == 900
    assert fluxo["identification"]["duplicates_removed"] == 880
    assert fluxo["screening"]["records_to_screen"] == 2
