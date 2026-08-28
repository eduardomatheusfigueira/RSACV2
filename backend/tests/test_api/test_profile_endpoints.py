#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Testes de Integração dos Endpoints de Perfil e Chaves."""

import pytest


@pytest.mark.anyio
async def test_api_keys_export_and_import(async_client):
    """
    Ciclo de backup das chaves no contrato da Fase 0 de segurança:
    exportação por POST, com senha, devolvendo envelope cifrado — e importação
    que aceita tanto o envelope quanto um arquivo legado em claro.
    """
    # 1. Exportar exige POST com senha (o GET em claro foi removido; 404 ou
    #    405 conforme a SPA esteja construída ou não)
    assert (await async_client.get("/api/v1/profile/keys/export")).status_code in (404, 405)

    res_export = await async_client.post(
        "/api/v1/profile/keys/export", json={"export_password": "senha-de-backup-123"}
    )
    assert res_export.status_code == 200
    assert res_export.json()["schema_version"] == "rsac_encrypted_envelope_v1"

    # 2. Importar chaves (formato legado em claro continua aceito)
    payload = {
        "gemini_api_keys": ["AIzaSy_API_TEST_1", "AIzaSy_API_TEST_2"],
        "qwen_api_keys": ["sk-QWEN_API_TEST"],
        "sources": {
            "SCOPUS": {"api_key": "scopus_key_xyz", "inst_token": "scopus_tok"},
            "PUBMED": {"api_key": "pubmed_key_xyz"},
            "OPENALEX": {"api_key": "contact@research.edu"},
        },
    }

    res_import = await async_client.post(
        "/api/v1/profile/keys/import", json={"payload": payload}
    )
    assert res_import.status_code == 200
    res_data = res_import.json()
    assert res_data["status"] == "ok"
    assert res_data["gemini_keys_count"] == 2
    assert res_data["qwen_keys_count"] == 1

    # 3. Conferir via GET /api/v1/ai/settings — máscaras, nunca as chaves
    res_ai_settings = await async_client.get("/api/v1/ai/settings")
    assert res_ai_settings.status_code == 200
    ai_data = res_ai_settings.json()
    assert ai_data["gemini_keys_count"] == 2
    assert ai_data["qwen_keys_count"] == 1
    assert ai_data["gemini_key_previews"] == ["••••••••ST_1", "••••••••ST_2"]
    assert "AIzaSy_API_TEST_1" not in res_ai_settings.text


@pytest.mark.anyio
async def test_api_full_profile_export_and_import(async_client):
    # 1. Criar um projeto via API
    proj_res = await async_client.post(
        "/api/v1/projects",
        json={
            "title": "Projeto Piloto de Desenvolvimento Regional",
            "description": "Análise de dinâmicas territoriais de inovação.",
            "methodology": "PRISMA-ScR",
        },
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # 2. Exportar perfil completo via POST /api/v1/profile/export
    export_req = {
        "session_preferences": {
            "theme": "indigo-rose",
            "active_project_id": proj_id,
            "sidebar_collapsed": False,
            "ai_enabled": True,
        }
    }
    exp_res = await async_client.post("/api/v1/profile/export", json=export_req)
    assert exp_res.status_code == 200
    profile_data = exp_res.json()
    assert profile_data["schema_version"] == "rsac_profile_v1"
    assert profile_data["session_preferences"]["theme"] == "indigo-rose"
    assert len(profile_data["projects"]) >= 1

    # 3. Importar perfil em outro momento via POST /api/v1/profile/import
    imp_res = await async_client.post("/api/v1/profile/import", json=profile_data)
    assert imp_res.status_code == 200
    imp_data = imp_res.json()
    assert imp_data["status"] == "ok"
    assert imp_data["projects_imported"] >= 1
    assert imp_data["restored_session"]["theme"] == "indigo-rose"
