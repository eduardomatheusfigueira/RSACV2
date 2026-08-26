#!/usr/bin/env python

"""
Autenticação dos WebSockets (doc 28 V-06, doc 29 §29.3.6).

Os dois canais transmitem o log de coleta e o progresso da triagem em tempo
real — descritores de busca, URLs consultadas, decisões. Como a política de
mesma origem não vale para WebSocket, `accept()` sem checar credencial
entregava o canal a qualquer página aberta no navegador do pesquisador.

São duas metades: a credencial e o `Origin`. A credencial deixou de ser um
token de sessão e passou a ser o token local — pela query, porque o navegador
não deixa mandar cabeçalho personalizado num handshake de WebSocket.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.deps import get_db
from app.main import create_app

CANAIS = [
    "/api/v1/projects/projeto-teste/harvest/ws",
    "/api/v1/projects/projeto-teste/screening/ai/ws",
]


@pytest.fixture
def client(db_session, token_local):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("canal", CANAIS)
def test_websocket_sem_credencial_e_recusado(client, canal):
    """Sem token, a conexão fecha antes de qualquer dado trafegar."""
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(canal) as ws:
        ws.receive_text()
    assert exc.value.code == 1008


@pytest.mark.parametrize("canal", CANAIS)
def test_websocket_com_token_invalido_e_recusado(client, canal):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"{canal}?local_token=nao-e-o-token") as ws:
            ws.receive_text()
    assert exc.value.code == 1008


@pytest.mark.parametrize("canal", CANAIS)
def test_websocket_com_token_local_conecta(client, canal, token_local):
    """Com o token da instalação, o canal abre."""
    with client.websocket_connect(f"{canal}?local_token={token_local}") as ws:
        assert ws is not None


def test_websocket_recusa_origem_hostil(client, token_local):
    """
    Credencial válida **e** origem hostil ainda fecha.

    É o caso que a checagem de `Origin` existe para cobrir: uma página em
    evil.example não consegue ler o token, mas se conseguisse por outra via, o
    `Origin` ainda a separaria da aplicação.
    """
    canal = f"{CANAIS[0]}?local_token={token_local}"
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(canal, headers={"Origin": "https://evil.example"}) as ws:
            ws.receive_text()
    assert exc.value.code == 1008


def test_websocket_aceita_origem_opaca_do_app_de_mesa(client, token_local):
    """
    O handshake vindo do app empacotado chega com `Origin: null` — a origem
    opaca do `file://`. Sem esta aceitação o canal fecha com 1008 e a coleta
    parece travada, mesmo com o backend íntegro.
    """
    canal = f"{CANAIS[0]}?local_token={token_local}"
    with client.websocket_connect(canal, headers={"Origin": "null"}) as ws:
        assert ws is not None
