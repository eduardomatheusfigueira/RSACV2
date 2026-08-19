#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Perfil de implantação e exposição da documentação OpenAPI
(doc 28 V-12, doc 29 §0 e §29.2).

O perfil é o mecanismo que torna o perímetro explícito: sem ele, o backend
publicado na internet e o backend em loopback eram literalmente o mesmo
processo com a mesma política.
"""

import httpx
import pytest

from app.api.deps import get_db
from app.config import DeploymentProfile, Settings
from app.main import create_app


async def _client_for(settings_obj, db_session, monkeypatch):
    import app.config as config_module
    import app.main as main_module

    monkeypatch.setattr(config_module, "settings", settings_obj)
    monkeypatch.setattr(main_module, "settings", settings_obj)

    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=application)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def test_perfil_padrao_e_desktop():
    """Quem não configura nada fica no perfil mais restrito de rede."""
    assert Settings().deployment_profile is DeploymentProfile.DESKTOP


def test_perfil_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("RSAC_DEPLOYMENT_PROFILE", "server")
    assert Settings().deployment_profile is DeploymentProfile.SERVER


def test_perfil_invalido_e_recusado():
    """Enumeração fechada: erro de digitação não vira perfil permissivo."""
    with pytest.raises(ValueError):
        Settings(deployment_profile="produção")


@pytest.mark.anyio
@pytest.mark.parametrize("rota", ["/api/docs", "/api/redoc", "/api/openapi.json"])
async def test_docs_fechadas_no_perfil_server(db_session, monkeypatch, rota):
    settings_obj = Settings(deployment_profile=DeploymentProfile.SERVER)
    async with await _client_for(settings_obj, db_session, monkeypatch) as client:
        res = await client.get(rota)
    assert res.status_code == 404


@pytest.mark.anyio
@pytest.mark.parametrize("rota", ["/api/docs", "/api/openapi.json"])
async def test_docs_abertas_no_perfil_desktop(db_session, monkeypatch, rota):
    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    async with await _client_for(settings_obj, db_session, monkeypatch) as client:
        res = await client.get(rota)
    assert res.status_code == 200


@pytest.mark.anyio
async def test_health_responde_nos_dois_perfis(db_session, monkeypatch):
    """O lançador usa o health check para saber se o backend subiu."""
    for perfil in (DeploymentProfile.DESKTOP, DeploymentProfile.SERVER):
        settings_obj = Settings(deployment_profile=perfil)
        async with await _client_for(settings_obj, db_session, monkeypatch) as client:
            res = await client.get("/api/v1/health")
        assert res.status_code == 200, perfil
