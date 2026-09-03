#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de rotas da API para Estatística Sob Demanda (doc 48 §9, §12, doc 49 Fase 7)."""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibWorkMetaModel,
    PaperModel,
    ProjectModel,
)
from tests.conftest import OWNER_ID_TESTE


@pytest.mark.anyio
async def test_ciclo_completo_analises_api(async_client, db_session):
    pid = "proj-api-stat-cycle"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Stat API", methodology="PRISMA"))

    p1 = PaperModel(id="ps-1", project_id=pid, title="Políticas Territoriais 1", year="2022", decision=Decision.INCLUDED.value)
    p2 = PaperModel(id="ps-2", project_id=pid, title="Políticas Territoriais 2", year="2022", decision=Decision.INCLUDED.value)
    db_session.add_all([p1, p2])
    db_session.add(BibWorkMetaModel(paper_id=p1.id, cited_by_count=10, is_oa=True))
    db_session.add(BibWorkMetaModel(paper_id=p2.id, cited_by_count=20, is_oa=False))
    db_session.commit()

    # 1. Interpretar pergunta
    resp_interp = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/analises/interpretar",
        json={"question": "qual a média de citações por ano?"},
    )
    assert resp_interp.status_code == 200
    dados_interp = resp_interp.json()
    assert dados_interp["supported"] is True
    assert dados_interp["specification"]["medida"] == "media"
    assert dados_interp["specification"]["campo"] == "citacoes_recebidas"
    assert dados_interp["specification"]["por"] == ["ano"]

    # 2. Executar especificação
    resp_exec = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/analises/executar",
        json={"specification": dados_interp["specification"]},
    )
    assert resp_exec.status_code == 200
    dados_exec = resp_exec.json()
    assert len(dados_exec["results"]) == 1
    assert dados_exec["results"][0]["valor"] == 15.0  # (10 + 20) / 2
    assert dados_exec["results"][0]["n_docs"] == 2

    # 3. Salvar análise
    resp_save = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/analises/salvas",
        json={
            "question": "qual a média de citações por ano?",
            "specification": dados_interp["specification"],
        },
    )
    assert resp_save.status_code == 201
    dados_save = resp_save.json()
    analise_id = dados_save["id"]

    # 4. Listar análises salvas
    resp_list = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/analises/salvas")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1

    # 5. Excluir análise salva
    resp_del = await async_client.delete(f"/api/v1/projects/{pid}/bibliometria/analises/salvas/{analise_id}")
    assert resp_del.status_code == 200
