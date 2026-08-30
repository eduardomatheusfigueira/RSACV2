#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes da Fase 3: Colaboração em Tempo Real, Presença e Concorrência Otimista (Doc 43 §43.12).
"""

from __future__ import annotations

import json
import httpx
import pytest
from starlette.testclient import TestClient
from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    HarvestRunModel,
    PaperModel,
    ProjectMemberModel,
    ProjectModel,
    ProtocolModel,
    UserModel,
    utcnow,
)
from app.main import create_app
from app.security.passwords import hash_password
from tests.conftest import OWNER_ID_TESTE, OWNER_USERNAME, SENHA_TESTE

PESQUISADOR_B_ID = "pesquisador-b-id"
PESQUISADOR_B_USER = "pesquisador_b"


@pytest.fixture
def projeto_colaborativo(db_session):
    """Cria projeto em modalidade colaborativa com dono e segundo pesquisador ativo."""
    u_b = UserModel(
        id=PESQUISADOR_B_ID,
        username=PESQUISADOR_B_USER,
        password_hash=hash_password(SENHA_TESTE),
        email="pesquisador_b@uni.br",
    )
    db_session.add(u_b)
    db_session.commit()

    proj = ProjectModel(
        id="proj-colab-fase3",
        owner_id=OWNER_ID_TESTE,
        title="Desenvolvimento Regional e Inovação Socioeconômica",
        methodology="PRISMA-ScR",
        collaboration_mode="colaborativa",
    )
    db_session.add(proj)
    db_session.flush()

    proto = ProtocolModel(
        id="proto-colab-fase3",
        project_id=proj.id,
        objective="Mapear políticas de desenvolvimento regional no semiárido brasileiro.",
        updated_at=utcnow(),
    )
    paper = PaperModel(
        id="paper-colab-fase3-1",
        project_id=proj.id,
        title="Arranjos Produtivos Locais e Governança Territorial",
        decision="Pendente",
        updated_at=utcnow(),
    )
    db_session.add_all([proto, paper])

    m_b = ProjectMemberModel(
        project_id=proj.id,
        user_id=u_b.id,
        project_role="revisor",
        is_active=True,
    )
    db_session.add(m_b)
    db_session.commit()

    return {"project": proj, "paper": paper, "proto": proto, "user_b": u_b}


async def _cliente(db_session, username: str) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    cliente = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )
    res = await cliente.post(
        "/api/v1/auth/login", json={"username": username, "password": SENHA_TESTE}
    )
    assert res.status_code == 200, res.text
    cliente.headers["Authorization"] = f"Bearer {res.json()['access_token']}"
    return cliente


@pytest.mark.anyio
async def test_harvest_run_persists_actor(db_session, projeto_colaborativo):
    """Execução de coleta persiste e serializa o ator (run_by_user_id e run_by_username)."""
    p_id = projeto_colaborativo["project"].id

    # Criar uma execução de coleta atribuída ao usuário B
    run = HarvestRunModel(
        id="run-teste-actor-1",
        project_id=p_id,
        source_name="BDTD",
        descriptors_used='["Desenvolvimento Regional"]',
        started_at=utcnow(),
        completed_at=utcnow(),
        records_found=15,
        records_new=15,
        records_duplicate=0,
        status="completed",
        run_by_user_id=PESQUISADOR_B_ID,
    )
    db_session.add(run)
    db_session.commit()

    client = await _cliente(db_session, OWNER_USERNAME)
    res = await client.get(f"/api/v1/projects/{p_id}/harvest/runs")
    assert res.status_code == 200, res.text
    runs = res.json()["items"]
    assert len(runs) >= 1
    target_run = next(r for r in runs if r["id"] == "run-teste-actor-1")
    assert target_run["run_by_user_id"] == PESQUISADOR_B_ID
    assert target_run["run_by_username"] == PESQUISADOR_B_USER


@pytest.mark.anyio
async def test_protocol_optimistic_concurrency_409(db_session, projeto_colaborativo):
    """Controle de concorrência com If-Match rejeita edições defasadas com 409 Conflict."""
    p_id = projeto_colaborativo["project"].id

    client_a = await _cliente(db_session, OWNER_USERNAME)
    client_b = await _cliente(db_session, PESQUISADOR_B_USER)

    # 1. Pesquisador A e B leem o protocolo no mesmo instante T1
    res_a = await client_a.get(f"/api/v1/projects/{p_id}/protocol")
    assert res_a.status_code == 200
    proto_a = res_a.json()
    t1_updated_at = proto_a["updated_at"]
    assert t1_updated_at is not None

    # 2. Pesquisador B salva primeiro, avançando a versão para T2
    res_b = await client_b.put(
        f"/api/v1/projects/{p_id}/protocol",
        headers={"If-Match": t1_updated_at},
        json={"objective": "Objetivo atualizado pelo pesquisador B."},
    )
    assert res_b.status_code == 200, res_b.text
    proto_b = res_b.json()
    t2_updated_at = proto_b["updated_at"]
    assert t2_updated_at != t1_updated_at

    # 3. Pesquisador A tenta salvar com a versão defasada T1 -> 409 Conflict
    res_a_conflict = await client_a.put(
        f"/api/v1/projects/{p_id}/protocol",
        headers={"If-Match": t1_updated_at},
        json={"objective": "Objetivo em conflito do pesquisador A."},
    )
    assert res_a_conflict.status_code == 409
    assert "concorrência" in res_a_conflict.json()["detail"].lower()

    # 4. Pesquisador A recarrega e salva com T2 (ou sem If-Match para sobrescrever)
    res_a_override = await client_a.put(
        f"/api/v1/projects/{p_id}/protocol",
        headers={"If-Match": t2_updated_at},
        json={"objective": "Objetivo conciliado pelo pesquisador A."},
    )
    assert res_a_override.status_code == 200
    assert res_a_override.json()["objective"] == "Objetivo conciliado pelo pesquisador A."


@pytest.mark.anyio
async def test_paper_optimistic_concurrency_409(db_session, projeto_colaborativo):
    """Controle de concorrência com If-Match em papers/{id} rejeita decisões defasadas com 409."""
    p_id = projeto_colaborativo["project"].id
    paper_id = projeto_colaborativo["paper"].id

    client_a = await _cliente(db_session, OWNER_USERNAME)
    client_b = await _cliente(db_session, PESQUISADOR_B_USER)

    # 1. Pesquisadores A e B leem o estudo no instante T1
    res_a = await client_a.get(f"/api/v1/projects/{p_id}/papers/{paper_id}")
    assert res_a.status_code == 200
    paper_a = res_a.json()
    t1_updated_at = paper_a["updated_at"]
    assert t1_updated_at is not None

    # 2. Pesquisador B inclui o estudo
    res_b = await client_b.patch(
        f"/api/v1/projects/{p_id}/papers/{paper_id}",
        headers={"If-Match": t1_updated_at},
        json={"decision": "Incluído"},
    )
    assert res_b.status_code == 200, res_b.text
    paper_b = res_b.json()
    t2_updated_at = paper_b["updated_at"]
    assert t2_updated_at != t1_updated_at

    # 3. Pesquisador A tenta excluir com base em T1 -> 409 Conflict
    res_a_conflict = await client_a.patch(
        f"/api/v1/projects/{p_id}/papers/{paper_id}",
        headers={"If-Match": t1_updated_at},
        json={"decision": "Excluído"},
    )
    assert res_a_conflict.status_code == 409
    assert "concorrência" in res_a_conflict.json()["detail"].lower()

    # 4. Pesquisador A atualiza com T2 -> Sucesso
    res_a_ok = await client_a.patch(
        f"/api/v1/projects/{p_id}/papers/{paper_id}",
        headers={"If-Match": t2_updated_at},
        json={"decision": "Excluído"},
    )
    assert res_a_ok.status_code == 200
    assert res_a_ok.json()["decision"] == "Excluído"


def test_websocket_presence_and_heartbeat(db_session, projeto_colaborativo):
    """WebSocket de colaboração aceita conexão de membro autenticado, ping/pong e presença."""
    p_id = projeto_colaborativo["project"].id

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    client = TestClient(app)

    # Login para obter token
    login_res = client.post(
        "/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": SENHA_TESTE}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Conectar ao WebSocket com o token
    with client.websocket_connect(f"/api/v1/projects/{p_id}/ws?token={token}") as ws:
        # 1. Mensagem de boas-vindas / presença imediata disparada na conexão
        initial_msg = json.loads(ws.receive_text())
        assert initial_msg["type"] == "presenca"
        assert OWNER_USERNAME in [u["username"] for u in initial_msg["active_users"]]

        # 2. Enviar ping e receber pong
        ws.send_text("ping")
        data = ws.receive_text()
        assert data == "pong"

        # 3. Enviar presença na tela de triagem e receber broadcast atualizado
        ws.send_text(json.dumps({"type": "presenca", "tela": "triagem"}))
        presence_msg = json.loads(ws.receive_text())
        assert presence_msg["type"] == "presenca"
        assert "active_users" in presence_msg
        active_usernames = [u["username"] for u in presence_msg["active_users"]]
        assert OWNER_USERNAME in active_usernames
