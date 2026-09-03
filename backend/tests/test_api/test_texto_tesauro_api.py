#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de rotas da API para Camada de Texto e Tesauro (doc 48 §5, §12, doc 49 Fase 4)."""

import json
import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibTextoModel,
    BibThesaurusEntryModel,
    BibThesaurusModel,
    PaperModel,
    ProjectModel,
)
from tests.conftest import OWNER_ID_TESTE


@pytest.mark.anyio
async def test_obter_texto_endpoint(async_client, db_session):
    pid = "proj-api-txt-1"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto API Texto", methodology="PRISMA"))
    paper = PaperModel(id="paper-api-1", project_id=pid, title="Paper Teste API", decision=Decision.INCLUDED.value)
    db_session.add(paper)
    db_session.add(
        BibTextoModel(
            paper_id=paper.id,
            pipeline_version="2.0.0",
            pdf_sha256="sha-api-test-12345",
            n_pages=4,
            n_words=850,
            text_clean="Texto completo de teste da API",
            sections=json.dumps([{"name": "Introdução", "canonical_type": "introducao", "start_page": 1, "end_page": 1, "char_offset": 0, "char_length": 100}]),
        )
    )
    db_session.commit()

    resp = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/textos/{paper.id}")
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["paper_id"] == paper.id
    assert dados["pipeline_version"] == "2.0.0"
    assert dados["n_pages"] == 4
    assert dados["n_words"] == 850
    assert len(dados["sections"]) == 1
    assert dados["sections"][0]["canonical_type"] == "introducao"


@pytest.mark.anyio
async def test_tesauros_api_fluxo_completo(async_client, db_session):
    pid = "proj-api-tes-1"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto API Tesauro", methodology="PRISMA"))
    db_session.commit()

    # 1. Listar tesauros (cria padrão automaticamente se não houver)
    resp = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/tesauros")
    assert resp.status_code == 200
    tesauros = resp.json()
    assert len(tesauros) >= 1
    t_id = tesauros[0]["id"]

    # 2. Adicionar entrada
    resp_entry = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/tesauros/{t_id}/entradas",
        json={
            "preferred_term": "Políticas Públicas Territoriais",
            "variants": ["política pública territorial", "políticas territoriais"],
            "scope": "desenvolvimento regional",
        },
    )
    assert resp_entry.status_code == 201
    entry_data = resp_entry.json()
    assert entry_data["preferred_term"] == "Políticas Públicas Territoriais"
    assert len(entry_data["variants"]) == 2
    assert entry_data["approved_by"] == OWNER_ID_TESTE

    # 3. Listar entradas
    resp_list = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/tesauros/{t_id}/entradas")
    assert resp_list.status_code == 200
    entradas = resp_list.json()
    assert len(entradas) >= 1

    # 4. Aprovação em lote
    resp_aprov = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/tesauros/{t_id}/entradas/aprovar",
        json={"entry_ids": [entry_data["id"]]},
    )
    assert resp_aprov.status_code == 200
    aprovadas = resp_aprov.json()
    assert len(aprovadas) == 1
    assert aprovadas[0]["approved_by"] is not None
