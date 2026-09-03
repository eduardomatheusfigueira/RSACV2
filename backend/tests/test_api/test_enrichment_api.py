#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Rotas de enriquecimento externo OpenAlex (doc 48 §13, doc 49 Fase 2)."""

import pytest
from unittest.mock import AsyncMock, patch

from app.domain.enums import Decision
from app.infrastructure.persistence.models import PaperModel, ProjectModel, ProtocolModel
from tests.conftest import OWNER_ID_TESTE


def _projeto_com_estudos_doi(db_session, titulo="Projeto Enriquecimento API") -> str:
    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title=titulo, methodology="PRISMA")
    db_session.add(proj)
    db_session.flush()
    db_session.add(ProtocolModel(project_id=proj.id, objective="Mapear Desenvolvimento Regional"))
    db_session.add(
        PaperModel(
            project_id=proj.id,
            title="Estudo 1 com DOI",
            doi="10.1016/j.respol.2020.103980",
            decision=Decision.INCLUDED.value,
        )
    )
    db_session.add(
        PaperModel(
            project_id=proj.id,
            title="Estudo 2 sem DOI",
            doi=None,
            decision=Decision.INCLUDED.value,
        )
    )
    db_session.commit()
    return proj.id


@pytest.mark.anyio
async def test_obter_situacao_enriquecimento_endpoint(async_client, db_session):
    pid = _projeto_com_estudos_doi(db_session, "Projeto Situacao API")

    res = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/enriquecimento/situacao")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_papers"] == 2
    assert data["papers_with_doi"] == 1
    assert data["papers_enriched"] == 0
    assert data["papers_pending"] == 1
    assert data["coverage_pct"] == 0.0


@pytest.mark.anyio
async def test_iniciar_enriquecimento_endpoint_e_parar(async_client, db_session):
    pid = _projeto_com_estudos_doi(db_session, "Projeto Iniciar API")

    with patch(
        "app.services.bibliometria.enriquecimento.ServicoDeEnriquecimento.executar_enriquecimento",
        new_callable=AsyncMock,
    ) as mock_exec:
        res = await async_client.post(f"/api/v1/projects/{pid}/bibliometria/enriquecimento")
        assert res.status_code == 202, res.text
        data = res.json()
        assert data["status"] == "iniciado"

        # Parar enriquecimento
        res_parar = await async_client.post(f"/api/v1/projects/{pid}/bibliometria/enriquecimento/parar")
        assert res_parar.status_code == 200
