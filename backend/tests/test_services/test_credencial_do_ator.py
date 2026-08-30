#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testes para o princípio 'Quem age paga' (D-03, Doc 43 §43.11):
Garante que credenciais e chaves de IA pertençam ao pesquisador logado.
"""

from __future__ import annotations

import httpx
import pytest
from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    AISettingsModel,
    PaperModel,
    ProjectMemberModel,
    ProjectModel,
    ProtocolModel,
    SourceCredentialModel,
    UserModel,
)
from app.main import create_app
from app.security.passwords import hash_password
from tests.conftest import OWNER_ID_TESTE, OWNER_USERNAME, SENHA_TESTE

PESQUISADOR_REV_ID = "revisor-cred-id"
PESQUISADOR_REV_USER = "revisor_cred"


@pytest.fixture
def actor_and_owner_setup(db_session):
    # Revisor convidado (NÃO tem chave Scopus configurada)
    u_revisor = UserModel(
        id=PESQUISADOR_REV_ID,
        username=PESQUISADOR_REV_USER,
        password_hash=hash_password(SENHA_TESTE),
        email="revisor@uni.br",
    )
    db_session.add(u_revisor)
    db_session.commit()

    # Credencial do Dono
    cred_dono = SourceCredentialModel(
        user_id=OWNER_ID_TESTE,
        source_name="SCOPUS",
        api_key="scopus_key_do_dono",
    )
    db_session.add(cred_dono)

    # Projeto
    proj = ProjectModel(
        id="projeto-cred-teste",
        owner_id=OWNER_ID_TESTE,
        title="Revisão com Chaves Distintas",
        methodology="PRISMA-ScR",
        collaboration_mode="colaborativa",
    )
    db_session.add(proj)
    db_session.flush()

    proto = ProtocolModel(id="proto-cred", project_id=proj.id)
    paper = PaperModel(
        id="paper-cred-1",
        project_id=proj.id,
        title="Estudo de Teste",
        abstract="Resumo do estudo",
        decision="Pendente",
    )
    db_session.add_all([proto, paper])

    m_revisor = ProjectMemberModel(
        project_id=proj.id,
        user_id=u_revisor.id,
        project_role="revisor",
        is_active=True,
    )
    db_session.add(m_revisor)
    db_session.commit()

    return {
        "project": proj,
        "paper": paper,
        "revisor_user": u_revisor,
    }


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
async def test_fontes_mostram_credencial_do_usuario_logado(db_session, actor_and_owner_setup):
    """GET /harvest/sources deve refletir as chaves de quem consulta, não as do dono do projeto."""
    p_id = actor_and_owner_setup["project"].id

    dono = await _cliente(db_session, OWNER_USERNAME)
    revisor = await _cliente(db_session, PESQUISADOR_REV_USER)

    # 1. Dono consulta: Scopus está com has_api_key=True e enabled=True
    resp_dono = await dono.get(f"/api/v1/projects/{p_id}/harvest/sources")
    assert resp_dono.status_code == 200
    sources_dono = {s["id"]: s for s in resp_dono.json()["sources"]}
    assert sources_dono["Scopus"]["has_api_key"] is True
    assert sources_dono["Scopus"]["enabled"] is True

    # 2. Revisor consulta: Scopus está com has_api_key=False e enabled=False (não herda a do dono)
    resp_rev = await revisor.get(f"/api/v1/projects/{p_id}/harvest/sources")
    assert resp_rev.status_code == 200
    sources_rev = {s["id"]: s for s in resp_rev.json()["sources"]}
    assert sources_rev["Scopus"]["has_api_key"] is False
    assert sources_rev["Scopus"]["enabled"] is False


@pytest.mark.anyio
async def test_extracao_ia_usa_configuracao_do_ator(db_session, actor_and_owner_setup):
    """POST /extraction/ai deve respeitar a chave/status do revisor logado."""
    p_id = actor_and_owner_setup["project"].id
    paper_id = actor_and_owner_setup["paper"].id
    u_rev = actor_and_owner_setup["revisor_user"]

    # Se o revisor tem assistência desativada nas configurações dele
    ai_rev = AISettingsModel(
        user_id=u_rev.id,
        ai_enabled=False,
        provider="gemini",
    )
    db_session.add(ai_rev)
    db_session.commit()

    revisor = await _cliente(db_session, PESQUISADOR_REV_USER)

    resp = await revisor.post(
        f"/api/v1/projects/{p_id}/papers/{paper_id}/extraction/ai",
    )
    assert resp.status_code == 400
    assert "desativados nas suas Configurações" in resp.json()["detail"]
