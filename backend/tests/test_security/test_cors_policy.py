#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Política de origem cruzada (doc 28 V-03, doc 29 §29.5.1).

`allow_origin_regex=r"^https?://.*"` com `allow_credentials=True` casava com
qualquer origem existente. Na prática: um site arbitrário aberto no navegador
do pesquisador lia e escrevia na API em `127.0.0.1:8000` — inclusive as chaves
de API — sem que ele instalasse ou clicasse em nada.

Estes testes fixam o comportamento nos dois perfis.
"""

import httpx
import pytest

from app.api.deps import get_db
from app.config import DeploymentProfile, Settings
from app.main import create_app

ALLOW_ORIGIN = "access-control-allow-origin"


async def _client_for(settings_obj, db_session, monkeypatch):
    """App construído com um objeto de configuração específico."""
    import app.config as config_module
    import app.main as main_module

    monkeypatch.setattr(config_module, "settings", settings_obj)
    monkeypatch.setattr(main_module, "settings", settings_obj)

    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=application)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# ── Perfil desktop: só loopback ───────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.parametrize(
    "origem",
    [
        "https://evil.example",
        "http://evil.example",
        "https://rsac.attacker.com",
        "http://localhost.evil.com",          # sufixo que finge ser local
        "http://127.0.0.1.evil.com",
        "https://127.0.0.1.attacker.io:8000",
    ],
)
async def test_origem_hostil_nao_recebe_liberacao(db_session, monkeypatch, origem):
    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    async with await _client_for(settings_obj, db_session, monkeypatch) as client:
        res = await client.get("/api/v1/health", headers={"Origin": origem})

    assert res.status_code == 200
    assert ALLOW_ORIGIN not in {k.lower() for k in res.headers}, (
        f"origem {origem!r} foi liberada pelo CORS"
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "origem",
    ["http://localhost:5173", "http://127.0.0.1:8000", "http://localhost"],
)
async def test_loopback_continua_liberado_no_desktop(db_session, monkeypatch, origem):
    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    async with await _client_for(settings_obj, db_session, monkeypatch) as client:
        res = await client.get("/api/v1/health", headers={"Origin": origem})

    assert res.headers.get(ALLOW_ORIGIN) == origem


@pytest.mark.anyio
async def test_origem_opaca_do_app_de_mesa_e_liberada_no_desktop(db_session, monkeypatch):
    """
    O app empacotado carrega a interface de `file://`, e o Chromium apresenta
    isso como a origem opaca `null` — nunca como `file://`.

    Enquanto o regex só previa `file://`, o cabeçalho de liberação não saía e o
    navegador embutido barrava **toda** chamada da API: o app instalado abria e
    ficava em laço de reconexão, sem nunca alcançar o próprio backend. Este
    teste fixa a origem que o navegador realmente envia.
    """
    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    async with await _client_for(settings_obj, db_session, monkeypatch) as client:
        res = await client.get("/api/v1/health", headers={"Origin": "null"})

    assert res.headers.get(ALLOW_ORIGIN) == "null"


@pytest.mark.anyio
async def test_origem_opaca_nao_e_liberada_no_perfil_server(db_session, monkeypatch):
    """
    A concessão acima vale só para o app de mesa.

    Publicado, `null` é a origem de um iframe em sandbox de qualquer sítio — e
    lá não há app local nenhum a atender.
    """
    settings_obj = Settings(
        deployment_profile=DeploymentProfile.SERVER,
        cors_origins=["https://minha-revisao.exemplo"],
    )
    async with await _client_for(settings_obj, db_session, monkeypatch) as client:
        res = await client.get("/api/v1/health", headers={"Origin": "null"})

    assert ALLOW_ORIGIN not in {k.lower() for k in res.headers}


# ── Perfil server: apenas a lista declarada ───────────────────────────

@pytest.mark.anyio
async def test_server_libera_apenas_origens_declaradas(db_session, monkeypatch):
    settings_obj = Settings(
        deployment_profile=DeploymentProfile.SERVER,
        cors_origins=["https://minha-revisao.netlify.app"],
    )
    async with await _client_for(settings_obj, db_session, monkeypatch) as client:
        permitida = await client.get(
            "/api/v1/health", headers={"Origin": "https://minha-revisao.netlify.app"}
        )
        negada = await client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
        # No perfil `server` o loopback deixa de ser automático.
        loopback = await client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})

    assert permitida.headers.get(ALLOW_ORIGIN) == "https://minha-revisao.netlify.app"
    assert ALLOW_ORIGIN not in {k.lower() for k in negada.headers}
    assert ALLOW_ORIGIN not in {k.lower() for k in loopback.headers}


@pytest.mark.anyio
async def test_preflight_hostil_nao_ganha_metodos(db_session, monkeypatch):
    """O preflight é o que autoriza DELETE cross-origin — precisa recusar antes."""
    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    async with await _client_for(settings_obj, db_session, monkeypatch) as client:
        res = await client.options(
            "/api/v1/projects",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "DELETE",
            },
        )

    assert ALLOW_ORIGIN not in {k.lower() for k in res.headers}


def test_configuracao_nao_usa_mais_regex_aberto():
    """Guarda contra a volta do `^https?://.*` por copiar e colar."""
    desktop = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    server = Settings(deployment_profile=DeploymentProfile.SERVER)

    assert server.cors_allow_origin_regex is None
    regex = desktop.cors_allow_origin_regex
    assert regex is not None
    assert regex.startswith("^") and regex.endswith("$")
    assert ".*" not in regex
