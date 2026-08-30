#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes de Papéis de Projeto e Reabertura de Triagem (Doc 43 §43.5, Fase 2).
"""

from __future__ import annotations

import httpx
import pytest
from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    AuditLogModel,
    PaperModel,
    ProjectMemberModel,
    ProjectModel,
    ProtocolModel,
    UserModel,
)
from app.main import create_app
from app.security.passwords import hash_password
from tests.conftest import OWNER_ID_TESTE, OWNER_USERNAME, SENHA_TESTE

PESQUISADOR_REV_ID = "revisor-fase2-id"
PESQUISADOR_REV_USER = "revisor_fase2"

PESQUISADOR_OBS_ID = "observador-fase2-id"
PESQUISADOR_OBS_USER = "observador_fase2"


@pytest.fixture
def projeto_com_membros(db_session):
    """Cria projeto pertencente ao dono e cadastra revisor e observador ativos."""
    u_rev = UserModel(
        id=PESQUISADOR_REV_ID,
        username=PESQUISADOR_REV_USER,
        password_hash=hash_password(SENHA_TESTE),
        email="revisor@uni.br",
    )
    u_obs = UserModel(
        id=PESQUISADOR_OBS_ID,
        username=PESQUISADOR_OBS_USER,
        password_hash=hash_password(SENHA_TESTE),
        email="obs@uni.br",
    )
    db_session.add_all([u_rev, u_obs])
    db_session.commit()

    proj = ProjectModel(
        id="projeto-fase2-roles",
        owner_id=OWNER_ID_TESTE,
        title="Desenvolvimento Regional e Políticas Públicas",
        methodology="PRISMA-ScR",
        collaboration_mode="individual",
    )
    db_session.add(proj)
    db_session.flush()

    proto = ProtocolModel(id="proto-fase2", project_id=proj.id, objective="Objetivo inicial")
    paper = PaperModel(
        id="paper-fase2-1",
        project_id=proj.id,
        title="Estudo Territorial no Nordeste",
        decision="Pendente",
    )
    db_session.add_all([proto, paper])

    # Membros
    m_rev = ProjectMemberModel(
        project_id=proj.id,
        user_id=u_rev.id,
        project_role="revisor",
        is_active=True,
    )
    m_obs = ProjectMemberModel(
        project_id=proj.id,
        user_id=u_obs.id,
        project_role="observador",
        is_active=True,
    )
    db_session.add_all([m_rev, m_obs])
    db_session.commit()

    return {"project": proj, "paper": paper, "proto": proto}


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
async def test_escrita_protocolo_modo_individual(db_session, projeto_com_membros):
    """No modo individual, revisor e observador recebem 403 ao tentar editar protocolo."""
    p_id = projeto_com_membros["project"].id

    coord = await _cliente(db_session, OWNER_USERNAME)
    revisor = await _cliente(db_session, PESQUISADOR_REV_USER)
    observador = await _cliente(db_session, PESQUISADOR_OBS_USER)

    # 1. Coordenador consegue editar
    resp_coord = await coord.put(
        f"/api/v1/projects/{p_id}/protocol",
        json={"objective": "Novo objetivo por coordenador"},
    )
    assert resp_coord.status_code == 200
    assert resp_coord.json()["objective"] == "Novo objetivo por coordenador"

    # 2. Revisor tenta editar no modo individual -> 403
    resp_rev = await revisor.put(
        f"/api/v1/projects/{p_id}/protocol",
        json={"objective": "Tentativa de alteração por revisor"},
    )
    assert resp_rev.status_code == 403

    # 3. Observador tenta editar -> 403
    resp_obs = await observador.put(
        f"/api/v1/projects/{p_id}/protocol",
        json={"objective": "Tentativa de alteração por observador"},
    )
    assert resp_obs.status_code == 403


@pytest.mark.anyio
async def test_escrita_protocolo_modo_colaborativo(db_session, projeto_com_membros):
    """No modo colaborativo, o revisor pode coeditar o protocolo."""
    proj = projeto_com_membros["project"]
    proj.collaboration_mode = "colaborativa"
    db_session.commit()

    revisor = await _cliente(db_session, PESQUISADOR_REV_USER)
    observador = await _cliente(db_session, PESQUISADOR_OBS_USER)

    # Revisor consegue editar
    resp_rev = await revisor.put(
        f"/api/v1/projects/{proj.id}/protocol",
        json={"objective": "Objetivo colaborativo atualizado por revisor"},
    )
    assert resp_rev.status_code == 200
    assert resp_rev.json()["objective"] == "Objetivo colaborativo atualizado por revisor"

    # Observador continua recebendo 403
    resp_obs = await observador.put(
        f"/api/v1/projects/{proj.id}/protocol",
        json={"objective": "Tentativa observador"},
    )
    assert resp_obs.status_code == 403


@pytest.mark.anyio
async def test_permissoes_de_triagem_e_artigos(db_session, projeto_com_membros):
    """Revisor pode triar artigos; observador recebe 403."""
    p_id = projeto_com_membros["project"].id
    paper_id = projeto_com_membros["paper"].id

    revisor = await _cliente(db_session, PESQUISADOR_REV_USER)
    observador = await _cliente(db_session, PESQUISADOR_OBS_USER)

    # Revisor pode atualizar decisão do estudo
    resp_rev = await revisor.patch(
        f"/api/v1/projects/{p_id}/papers/{paper_id}",
        json={"decision": "Incluído", "observations": "Estudo atende aos critérios."},
    )
    assert resp_rev.status_code == 200
    assert resp_rev.json()["decision"] == "Incluído"

    # Observador recebe 403 ao tentar alterar decisão
    resp_obs = await observador.patch(
        f"/api/v1/projects/{p_id}/papers/{paper_id}",
        json={"decision": "Excluído"},
    )
    assert resp_obs.status_code == 403


@pytest.mark.anyio
async def test_bloqueio_409_troca_modalidade_com_estudos_decididos(db_session, projeto_com_membros):
    """Alterar modalidade com estudos decididos retorna 409 Conflict."""
    p_id = projeto_com_membros["project"].id
    paper = projeto_com_membros["paper"]
    paper.decision = "Incluído"
    db_session.commit()

    coord = await _cliente(db_session, OWNER_USERNAME)

    # Coordenador tenta trocar para cega_por_pares via PUT /projects/{id} -> 409
    resp = await coord.put(
        f"/api/v1/projects/{p_id}",
        json={"collaboration_mode": "cega_por_pares"},
    )
    assert resp.status_code == 409
    assert "estudo(s) com decisão" in resp.json()["detail"]


@pytest.mark.anyio
async def test_reabertura_de_triagem_pela_coordenacao(db_session, projeto_com_membros):
    """POST /projects/{id}/screening/reabrir reseta decisões para Pendente e grava audit logs."""
    p_id = projeto_com_membros["project"].id
    paper = projeto_com_membros["paper"]
    paper.decision = "Incluído"
    paper.observations = "Parecer antigo"
    db_session.commit()

    coord = await _cliente(db_session, OWNER_USERNAME)
    revisor = await _cliente(db_session, PESQUISADOR_REV_USER)

    # Revisor não pode reabrir triagem (somente coordenador)
    resp_rev = await revisor.post(
        f"/api/v1/projects/{p_id}/screening/reabrir",
        json={"collaboration_mode": "cega_por_pares"},
    )
    assert resp_rev.status_code == 403

    # Coordenador reabre e troca modalidade
    resp = await coord.post(
        f"/api/v1/projects/{p_id}/screening/reabrir",
        json={
            "collaboration_mode": "cega_por_pares",
            "motivo": "Ingresso de segundo revisor para revisão duplo-cega",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "reopened"
    assert data["papers_reset"] == 1
    assert data["collaboration_mode"] == "cega_por_pares"

    # Verificar banco de dados
    db_session.expire_all()
    paper_db = db_session.query(PaperModel).filter(PaperModel.id == paper.id).first()
    assert paper_db.decision == "Pendente"
    assert paper_db.observations == ""

    proj_db = db_session.query(ProjectModel).filter(ProjectModel.id == p_id).first()
    assert proj_db.collaboration_mode == "cega_por_pares"

    # Verificar registro no log de auditoria
    log = (
        db_session.query(AuditLogModel)
        .filter(AuditLogModel.paper_id == paper.id, AuditLogModel.action == "screening_reopened")
        .first()
    )
    assert log is not None
    assert log.old_value == "Incluído"
    assert log.new_value == "Pendente"
