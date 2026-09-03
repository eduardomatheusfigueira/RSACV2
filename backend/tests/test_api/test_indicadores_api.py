#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes da rota HTTP de Indicadores Bibliométricos de Nível 0 e 1 (doc 48 §7, doc 49 Fase 3)."""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibWorkMetaModel,
    PaperModel,
    ProjectModel,
    ProtocolModel,
)
from tests.conftest import OWNER_ID_TESTE


def _projeto_completo_para_indicadores(db_session, pid="proj-api-ind-1") -> str:
    proj = ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto API Indicadores", methodology="PRISMA")
    db_session.add(proj)
    db_session.flush()
    db_session.add(ProtocolModel(project_id=pid, objective="Análise Bibliométrica"))

    p1 = PaperModel(
        id="p-api-1",
        project_id=pid,
        title="Desenvolvimento Regional e Inovação",
        authors="Silva, M.; Santos, A.",
        journal="Revista de Estudos Regionais",
        year="2021",
        doi="10.1016/j.respol.2021.001",
        decision=Decision.INCLUDED.value,
    )
    p2 = PaperModel(
        id="p-api-2",
        project_id=pid,
        title="Políticas Públicas e Sustentabilidade",
        authors="Silva, M.",
        journal="Revista de Estudos Regionais",
        year="2022",
        doi="10.1016/j.respol.2022.002",
        decision=Decision.INCLUDED.value,
    )
    db_session.add_all([p1, p2])

    db_session.add(BibWorkMetaModel(paper_id="p-api-1", cited_by_count=20, is_oa=True, oa_status="gold", raw="{}"))
    db_session.add(BibWorkMetaModel(paper_id="p-api-2", cited_by_count=5, is_oa=False, oa_status="closed", raw="{}"))
    db_session.commit()
    return pid


@pytest.mark.anyio
async def test_obter_indicadores_endpoint(async_client, db_session):
    pid = _projeto_completo_para_indicadores(db_session, "proj-api-ind-ok")

    res = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/indicadores?decision=Incluído")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["project_id"] == pid
    assert data["total_papers"] == 2

    # Bradford
    assert data["bradford"]["total_articles"] == 2
    assert data["bradford"]["total_journals"] == 1

    # Colaboração
    assert data["collaboration"]["total_articles"] == 2
    assert data["collaboration"]["single_author_articles"] == 1
    assert data["collaboration"]["multi_author_articles"] == 1
    assert data["collaboration"]["subramanyam_index"] == 0.5

    # Citações
    assert data["citations"]["total_citations"] == 25
    assert data["citations"]["h_index"] == 2

    # Acesso Aberto
    assert data["open_access"]["open_access_count"] == 1
    assert data["open_access"]["open_access_pct"] == 50.0


@pytest.mark.anyio
async def test_obter_indicadores_404_para_instantaneo_invalido(async_client, db_session):
    pid = _projeto_completo_para_indicadores(db_session, "proj-api-ind-404")

    res = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/indicadores?instantaneo=nao-existe")
    assert res.status_code == 404
