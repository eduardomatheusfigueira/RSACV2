#!/usr/bin/env python

"""
Política de origem cruzada (doc 28 V-03, doc 29 §29.5.1).

`allow_origin_regex=r"^https?://.*"` com `allow_credentials=True` casava com
qualquer origem existente. Na prática: um site arbitrário aberto no navegador
do pesquisador lia e escrevia na API em `127.0.0.1:8000` — inclusive as chaves
de API — sem que ele instalasse ou clicasse em nada.

Havia aqui uma segunda metade, sobre o perfil `server` e a lista configurável
de origens. Saiu com a publicação por túnel: hoje existe uma política só, e é
esta.
"""

import httpx
import pytest

from app.api.deps import get_db
from app.main import create_app
from app.security.dependencies import LOCAL_TOKEN_HEADER

ALLOW_ORIGIN = "access-control-allow-origin"


async def _client(db_session):
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=application)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# ── Só loopback e a origem opaca do app empacotado ────────────────────

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
        "https://revisao.trycloudflare.com",  # o túnel que deixou de existir
    ],
)
async def test_origem_hostil_nao_recebe_liberacao(db_session, origem):
    async with await _client(db_session) as client:
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
async def test_loopback_continua_liberado(db_session, origem):
    async with await _client(db_session) as client:
        res = await client.get("/api/v1/health", headers={"Origin": origem})

    assert res.headers.get(ALLOW_ORIGIN) == origem


@pytest.mark.anyio
async def test_origem_opaca_do_app_de_mesa_e_liberada(db_session):
    """
    O app empacotado carrega a interface de `file://`, e o Chromium apresenta
    isso como a origem opaca `null` — nunca como `file://`.

    Enquanto o regex só previa `file://`, o cabeçalho de liberação não saía e o
    navegador embutido barrava **toda** chamada da API: o app instalado abria e
    ficava em laço de reconexão, sem nunca alcançar o próprio backend. Este
    teste fixa a origem que o navegador realmente envia.
    """
    async with await _client(db_session) as client:
        res = await client.get("/api/v1/health", headers={"Origin": "null"})

    assert res.headers.get(ALLOW_ORIGIN) == "null"


@pytest.mark.anyio
async def test_preflight_libera_o_cabecalho_da_credencial(db_session):
    """
    O token local viaja em `X-RSAC-Local-Token`, que não é cabeçalho simples.

    Se ele não estiver em `allow_headers`, o navegador recusa a requisição no
    *preflight* — antes de ela sair — e o app volta a não alcançar o backend,
    desta vez sem nem chegar ao servidor para deixar rastro no log.
    """
    async with await _client(db_session) as client:
        res = await client.options(
            "/api/v1/projects",
            headers={
                "Origin": "null",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": LOCAL_TOKEN_HEADER.lower(),
            },
        )

    permitidos = res.headers.get("access-control-allow-headers", "").lower()
    assert LOCAL_TOKEN_HEADER.lower() in permitidos


@pytest.mark.anyio
async def test_preflight_hostil_nao_ganha_metodos(db_session):
    """O preflight é o que autoriza DELETE cross-origin — precisa recusar antes."""
    async with await _client(db_session) as client:
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
    from app.config import Settings

    regex = Settings().cors_allow_origin_regex
    assert regex.startswith("^") and regex.endswith("$")
    assert ".*" not in regex
