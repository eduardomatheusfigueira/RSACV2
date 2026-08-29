#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Controle da triagem em lote: parar, não sobrepor e se recompor.

Enquanto o lote era um `BackgroundTasks`, não havia alça para interrompê-lo —
quem disparasse 100 artigos por engano, ou visse a cota do provedor estourar,
só tinha a opção de fechar o programa. Estes testes fixam as três garantias
que a alça trouxe: a execução para quando se pede, uma segunda não começa por
cima da primeira, e a tela consegue perguntar ao servidor o que está correndo.
"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.infrastructure.ai.base import ScreeningResult
from app.infrastructure.persistence.models import (
    CriterionModel,
    PaperModel,
    ProjectModel,
    ProtocolModel,
)
from app.main import create_app
from tests.conftest import OWNER_ID_TESTE, OWNER_USERNAME, SENHA_TESTE

PROJETO = "projeto-do-lote"
BASE = f"/api/v1/projects/{PROJETO}/screening/ai"


class IALenta:
    """Analisa devagar o bastante para o lote ainda estar vivo quando se pede parar."""

    provider_name = "fake"
    model_name = "fake-1"

    def __init__(self, atraso: float = 2.0):
        self.atraso = atraso
        self.analisados = 0

    async def analyze_screening(self, paper, protocol):
        await asyncio.sleep(self.atraso)
        self.analisados += 1
        return ScreeningResult(
            decision="Incluído",
            inclusion_criteria={},
            exclusion_criteria={},
            justification="parecer",
            confidence=0.9,
            model_used=self.model_name,
            provider=self.provider_name,
            response_valid=True,
            validation_note="",
        )


@pytest.fixture
def client(db_session, contas, monkeypatch):
    db_session.add(
        ProjectModel(
            id=PROJETO, owner_id=OWNER_ID_TESTE, title="Acervo", methodology="PRISMA-ScR"
        )
    )
    db_session.flush()
    db_session.add(ProtocolModel(id="proto-lote", project_id=PROJETO, objective="objetivo"))
    db_session.flush()
    db_session.add(
        CriterionModel(id="c1", protocol_id="proto-lote", text="critério", is_exclusion=False)
    )
    for i in range(6):
        db_session.add(
            PaperModel(id=f"p{i}", project_id=PROJETO, title=f"Artigo {i}", decision="Pendente")
        )
    db_session.commit()

    # A tarefa de segundo plano abre a própria sessão; sem este desvio ela
    # consultaria o banco de produção em vez do banco do teste.
    import app.services.screening_service as servico

    monkeypatch.setattr(servico, "SessionLocal", lambda: db_session)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c


@pytest.fixture
def token(client):
    res = client.post(
        "/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": SENHA_TESTE}
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture(autouse=True)
def ia_lenta():
    import app.api.v1.screening_ai as rota

    anterior = rota.screening_service.ai_client
    rota.screening_service.ai_client = IALenta()
    yield rota.screening_service.ai_client
    rota.screening_service.ai_client = anterior


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_lote_pode_ser_interrompido(client, token):
    """O pedido de parar encerra a execução e avisa a tela pelo canal."""
    with client.websocket_connect(f"{BASE}/ws?token={token}") as ws:
        inicio = client.post(
            f"{BASE}/batch", json={"limit": 6, "concurrency": 1}, headers=_auth(token)
        )
        assert inicio.status_code == 202

        # O primeiro evento confirma que a tarefa está de pé.
        assert json.loads(ws.receive_text())["type"] == "batch_screening_started"

        situacao = client.get(f"{BASE}/batch/status", headers=_auth(token)).json()
        assert situacao["is_running"] is True
        assert situacao["progress"]["total"] == 6

        parada = client.post(f"{BASE}/batch/cancel", headers=_auth(token))
        assert parada.status_code == 200
        assert parada.json()["status"] == "cancelled"

        eventos = []
        for _ in range(6):
            eventos.append(json.loads(ws.receive_text())["type"])
            if eventos[-1] == "batch_screening_cancelled":
                break
        assert "batch_screening_cancelled" in eventos

    # E a tarefa realmente morreu: nada mais consta como em andamento.
    assert client.get(f"{BASE}/batch/status", headers=_auth(token)).json()["is_running"] is False


def test_parar_sem_lote_ativo_nao_e_erro(client, token):
    """Sem nada correndo, parar é uma resposta informativa — não uma falha."""
    res = client.post(f"{BASE}/batch/cancel", headers=_auth(token))
    assert res.status_code == 200
    assert res.json()["status"] == "not_running"


def test_segundo_lote_nao_sobrepoe_o_primeiro(client, token):
    """
    Disparar de novo com um lote vivo é recusado.

    Sem esta trava, cada clique repetido somava mais uma varredura concorrente
    sobre os mesmos artigos pendentes — dobrando o consumo de cota do provedor
    e embaralhando os contadores de progresso na tela.
    """
    try:
        primeiro = client.post(
            f"{BASE}/batch", json={"limit": 6, "concurrency": 1}, headers=_auth(token)
        )
        assert primeiro.status_code == 202

        segundo = client.post(
            f"{BASE}/batch", json={"limit": 6, "concurrency": 1}, headers=_auth(token)
        )
        assert segundo.status_code == 409
        assert "andamento" in segundo.json()["detail"]
    finally:
        client.post(f"{BASE}/batch/cancel", headers=_auth(token))
