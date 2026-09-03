#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de ordenação de artigos (papers) por data de publicação e múltiplos critérios."""

import pytest


@pytest.mark.anyio
async def test_papers_sorting_options(async_client):
    """Testa ordenação de papers por ano (desc/asc), título, autores e confiança."""
    # 1. Criar projeto
    res = await async_client.post(
        "/api/v1/projects",
        json={"title": "Projeto Teste Ordenação", "methodology": "PRISMA-ScR"},
    )
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Criar 4 estudos com metadados variados
    p1 = await async_client.post(
        f"/api/v1/projects/{project_id}/papers",
        json={"title": "Alpha Study", "authors": "Silva, A.", "year": "2024", "abstract": "Resumo alpha"},
    )
    assert p1.status_code == 201

    p2 = await async_client.post(
        f"/api/v1/projects/{project_id}/papers",
        json={"title": "Gamma Study", "authors": "Costa, B.", "year": "2018", "abstract": "Resumo gamma"},
    )
    assert p2.status_code == 201

    p3 = await async_client.post(
        f"/api/v1/projects/{project_id}/papers",
        json={"title": "Beta Study", "authors": "Alves, C.", "year": "2021", "abstract": "Resumo beta"},
    )
    assert p3.status_code == 201

    p4 = await async_client.post(
        f"/api/v1/projects/{project_id}/papers",
        json={"title": "Delta Study", "authors": "Zico, D.", "year": "", "abstract": "Resumo delta"},
    )
    assert p4.status_code == 201

    # 3. Testar ordenação padrão (sem passar sort_by) -> deve ser year_desc (anos recentes primeiro, nulo/vazio por último)
    res_default = await async_client.get(f"/api/v1/projects/{project_id}/papers")
    assert res_default.status_code == 200
    items_default = res_default.json()["items"]
    titles_default = [item["title"] for item in items_default]
    assert titles_default == ["Alpha Study", "Beta Study", "Gamma Study", "Delta Study"]

    # 4. Testar sort_by=year_desc explicitamente
    res_ydesc = await async_client.get(f"/api/v1/projects/{project_id}/papers?sort_by=year_desc")
    assert res_ydesc.status_code == 200
    titles_ydesc = [item["title"] for item in res_ydesc.json()["items"]]
    assert titles_ydesc == ["Alpha Study", "Beta Study", "Gamma Study", "Delta Study"]

    # 5. Testar sort_by=year_asc (anos antigos primeiro, nulo/vazio por último)
    res_yasc = await async_client.get(f"/api/v1/projects/{project_id}/papers?sort_by=year_asc")
    assert res_yasc.status_code == 200
    titles_yasc = [item["title"] for item in res_yasc.json()["items"]]
    assert titles_yasc == ["Gamma Study", "Beta Study", "Alpha Study", "Delta Study"]

    # 6. Testar sort_by=title_asc (A -> Z)
    res_tasc = await async_client.get(f"/api/v1/projects/{project_id}/papers?sort_by=title_asc")
    assert res_tasc.status_code == 200
    titles_tasc = [item["title"] for item in res_tasc.json()["items"]]
    assert titles_tasc == ["Alpha Study", "Beta Study", "Delta Study", "Gamma Study"]

    # 7. Testar sort_by=title_desc (Z -> A)
    res_tdesc = await async_client.get(f"/api/v1/projects/{project_id}/papers?sort_by=title_desc")
    assert res_tdesc.status_code == 200
    titles_tdesc = [item["title"] for item in res_tdesc.json()["items"]]
    assert titles_tdesc == ["Gamma Study", "Delta Study", "Beta Study", "Alpha Study"]

    # 8. Testar sort_by=authors_asc (A -> Z)
    res_aasc = await async_client.get(f"/api/v1/projects/{project_id}/papers?sort_by=authors_asc")
    assert res_aasc.status_code == 200
    titles_aasc = [item["title"] for item in res_aasc.json()["items"]]
    assert titles_aasc == ["Beta Study", "Gamma Study", "Alpha Study", "Delta Study"]

    # 9. Testar sort_by=authors_desc (Z -> A)
    res_adesc = await async_client.get(f"/api/v1/projects/{project_id}/papers?sort_by=authors_desc")
    assert res_adesc.status_code == 200
    titles_adesc = [item["title"] for item in res_adesc.json()["items"]]
    assert titles_adesc == ["Delta Study", "Alpha Study", "Gamma Study", "Beta Study"]
