#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Autenticação dos WebSockets (doc 28 V-06, doc 29 §29.3.6).

Os dois canais transmitem o log de coleta e o progresso da triagem em tempo
real — descritores de busca, URLs consultadas, decisões. Como a política de
mesma origem não vale para WebSocket, `accept()` sem checar credencial
entregava o canal a qualquer página aberta no navegador do pesquisador.

A checagem de `Origin` — a outra metade da defesa contra sequestro entre
sítios — entra na Fase 3; aqui se fixa a parte da sessão.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.deps import get_db
from app.main import create_app
from tests.conftest import OWNER_USERNAME, SENHA_TESTE

CANAIS = [
    "/api/v1/projects/projeto-teste/harvest/ws",
    "/api/v1/projects/projeto-teste/screening/ai/ws",
]


@pytest.fixture
def client(db_session, contas):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c


def _token_de_sessao(client) -> str:
    res = client.post(
        "/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": SENHA_TESTE}
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.mark.parametrize("canal", CANAIS)
def test_websocket_sem_sessao_e_recusado(client, canal):
    """Sem token, a conexão fecha antes de qualquer dado trafegar."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(canal) as ws:
            ws.receive_text()
    assert exc.value.code == 1008


@pytest.mark.parametrize("canal", CANAIS)
def test_websocket_com_token_invalido_e_recusado(client, canal):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"{canal}?token=inventado-123") as ws:
            ws.receive_text()
    assert exc.value.code == 1008


def test_websocket_com_sessao_valida_conecta(client):
    """O contraponto: com sessão, o canal funciona como antes."""
    token = _token_de_sessao(client)
    with client.websocket_connect(f"{CANAIS[0]}?token={token}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_websocket_aceita_cookie_de_sessao(client):
    """A SPA servida pelo próprio backend não precisa passar token na URL."""
    _token_de_sessao(client)  # o cookie fica no jar do TestClient
    with client.websocket_connect(CANAIS[0]) as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_websocket_recusa_sessao_encerrada(client):
    """Depois do logout o token não abre mais o canal."""
    token = _token_de_sessao(client)
    assert client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
    ).status_code == 200

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"{CANAIS[0]}?token={token}") as ws:
            ws.receive_text()
    assert exc.value.code == 1008


# ── Origem do handshake (§29.3.6) ─────────────────────────────────────

def test_origem_opaca_do_app_de_mesa_e_aceita_no_handshake(monkeypatch):
    """
    O painel de log e o acompanhamento de coleta dependem do WebSocket, e o
    handshake vindo do app empacotado chega com `Origin: null` — a origem
    opaca do `file://`. Sem esta aceitação o canal fecha com 1008 e a coleta
    parece travada, mesmo com o backend íntegro.
    """
    import app.security.dependencies as deps_module
    from app.config import DeploymentProfile, Settings
    from app.security.dependencies import origem_do_websocket_e_permitida

    # O módulo importa `settings` para o próprio espaço de nomes, então é ele
    # que precisa ser trocado — trocar `app.config.settings` não teria efeito
    # nenhum aqui, e o teste passaria por acaso.
    monkeypatch.setattr(
        deps_module, "settings", Settings(deployment_profile=DeploymentProfile.DESKTOP)
    )

    class _FakeWS:
        def __init__(self, origem):
            self.headers = {"origin": origem} if origem else {}

    assert origem_do_websocket_e_permitida(_FakeWS("null"))
    assert origem_do_websocket_e_permitida(_FakeWS("http://localhost:5173"))
    assert not origem_do_websocket_e_permitida(_FakeWS("https://evil.example"))
