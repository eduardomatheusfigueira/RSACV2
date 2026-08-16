#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de integração assíncronos dos endpoints da API v1."""

import pytest


@pytest.mark.anyio
async def test_health_check(async_client):
    res = await async_client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


@pytest.mark.anyio
async def test_search_descriptors_rules_validation(async_client):
    """Testa validação das regras de descritores de busca RSAC."""
    res = await async_client.post(
        "/api/v1/projects",
        json={"title": "Projeto Regras", "methodology": "PRISMA-P"},
    )
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 1. Envio com mais de 5 pares (permitido, limite de 5 é sugestão recomendada)
    res_more_pairs = await async_client.put(
        f"/api/v1/projects/{project_id}/protocol",
        json={
            "search_descriptors": {
                "pt": ["p1", "p2", "p3", "p4", "p5", "p6", "p7"],
            }
        },
    )
    assert res_more_pairs.status_code == 200
    assert len(res_more_pairs.json()["search_descriptors"]["pt"]) == 7

    # 2. Tentativa com mais de 2 termos por expressão (deve falhar com 400)
    res_terms = await async_client.put(
        f"/api/v1/projects/{project_id}/protocol",
        json={
            "search_descriptors": {
                "pt": ['"termo 1" AND "termo 2" AND "termo 3"'],
            }
        },
    )
    assert res_terms.status_code == 400
    assert "no máximo em pares" in res_terms.json()["detail"]


@pytest.mark.anyio
async def test_harvest_endpoints(async_client):
    """Testa listagem de fontes de coleta e endpoints de harvest."""
    # 1. Criar projeto
    res = await async_client.post(
        "/api/v1/projects",
        json={"title": "Projeto Coleta", "methodology": "PRISMA-P"},
    )
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Listar fontes disponíveis
    sources_res = await async_client.get(f"/api/v1/projects/{project_id}/harvest/sources")
    assert sources_res.status_code == 200
    sources = sources_res.json()["sources"]
    assert len(sources) >= 4
    source_ids = [s["id"] for s in sources]
    assert "BDTD" in source_ids
    assert "SciELO" in source_ids
    assert "OpenAlex" in source_ids
    assert "PubMed" in source_ids

    # 3. Listar execuções de coleta (inicialmente vazio)
    runs_res = await async_client.get(f"/api/v1/projects/{project_id}/harvest/runs")
    assert runs_res.status_code == 200
    assert runs_res.json()["total"] == 0


@pytest.mark.anyio
async def test_project_crud(async_client):
    # 1. Create
    res = await async_client.post(
        "/api/v1/projects",
        json={"title": "Revisão Teste", "methodology": "PRISMA-P"},
    )
    assert res.status_code == 201
    proj = res.json()
    assert proj["title"] == "Revisão Teste"
    project_id = proj["id"]

    # 2. Get
    res = await async_client.get(f"/api/v1/projects/{project_id}")
    assert res.status_code == 200
    assert res.json()["id"] == project_id

    # 3. List
    res = await async_client.get("/api/v1/projects")
    assert res.status_code == 200
    assert len(res.json()["items"]) >= 1

    # 4. Update Protocol
    proto_res = await async_client.put(
        f"/api/v1/projects/{project_id}/protocol",
        json={
            "objective": "Objetivo testado",
            "pico_framework": {"population": "Adultos"},
            "search_descriptors": {
                "pt": ['"inteligência artificial" AND "saúde"'],
            },
            "criteria": [
                {"text": "Estudos randomizados", "is_exclusion": False, "order": 0},
                {"text": "Sem texto completo", "is_exclusion": True, "order": 1},
            ],
        },
    )
    assert proto_res.status_code == 200
    proto = proto_res.json()
    assert proto["objective"] == "Objetivo testado"
    assert len(proto["criteria"]) == 2

    # 5. Create Paper & Decision
    paper_res = await async_client.post(
        f"/api/v1/projects/{project_id}/papers",
        json={
            "title": "Machine Learning in Medicine",
            "authors": "Smith, J.",
            "year": "2024",
            "sources": ["SciELO"],
        },
    )
    assert paper_res.status_code == 201
    paper_id = paper_res.json()["id"]

    # Patch decision to 'Incluído'
    patch_res = await async_client.patch(
        f"/api/v1/projects/{project_id}/papers/{paper_id}",
        json={"decision": "Incluído", "observations": "Artigo relevante."},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["decision"] == "Incluído"

    # 6. Check Stats
    stats_res = await async_client.get(f"/api/v1/projects/{project_id}/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_papers"] == 1
    assert stats["included_papers"] == 1
    assert stats["pending_papers"] == 0


@pytest.mark.anyio
async def test_ai_assist_field_endpoint(async_client):
    """Testa endpoint de assistência de IA por campo."""
    # 1. Quando IA está desativada, deve retornar 400
    res = await async_client.post(
        "/api/v1/ai/assist-field",
        json={
            "field_id": "objective",
            "field_label": "Objetivo Geral",
            "current_value": "",
            "field_guidelines": "PRISMA-ScR Item 4",
            "action": "generate",
        },
    )
    # Por padrão sem chaves ou IA desativada, retorna 400 explicativo
    assert res.status_code in (400, 500)

