#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de rotas da API para Grafos Bibliométricos e Exportação (doc 48 §8, §12, doc 49 Fase 6)."""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibKeywordModel,
    PaperModel,
    ProjectModel,
)
from tests.conftest import OWNER_ID_TESTE


@pytest.mark.anyio
async def test_gerar_grafo_api_e_exportar(async_client, db_session):
    pid = "proj-api-grafo-1"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Grafo API", methodology="PRISMA"))

    p1 = PaperModel(id="p-gapi-1", project_id=pid, title="Desenvolvimento Regional e Inovação", authors="Costa, Marcos; Lima, Fernanda", decision=Decision.INCLUDED.value)
    p2 = PaperModel(id="p-gapi-2", project_id=pid, title="Políticas Públicas em APLs", authors="Lima, Fernanda; Rocha, Carlos", decision=Decision.INCLUDED.value)
    db_session.add_all([p1, p2])

    kw1 = BibKeywordModel(paper_id=p1.id, term="desenvolvimento regional", source="author")
    kw2 = BibKeywordModel(paper_id=p2.id, term="desenvolvimento regional", source="author")
    db_session.add_all([kw1, kw2])
    db_session.commit()

    # 1. Gerar rede de coautoria
    resp_gen = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/grafos/gerar",
        json={
            "network_type": "coautoria",
            "normalizacao": "association_strength",
            "semente": 42,
        },
    )
    assert resp_gen.status_code == 200
    dados = resp_gen.json()
    assert dados["network_type"] == "coautoria"
    assert len(dados["nodes"]) == 3
    assert len(dados["edges"]) == 2
    assert dados["seed"] == 42
    assert "coordinates" in dados
    grafo_id = dados["id"]

    # 2. Obter grafo por ID
    resp_get = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/grafos/{grafo_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == grafo_id

    # 3. Exportar GraphML
    resp_exp = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/grafos/{grafo_id}/exportar")
    assert resp_exp.status_code == 200
    assert "application/xml" in resp_exp.headers.get("content-type", "")
    assert b"Costa, Marcos" in resp_exp.content
