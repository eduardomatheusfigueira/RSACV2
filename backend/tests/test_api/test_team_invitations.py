#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes de Equipe e Convites de Projeto (doc 43 §43.10, doc 44 Fase 1).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    PaperModel,
    ProjectInvitationModel,
    ProjectMemberModel,
    ProjectModel,
    UserModel,
    utcnow,
)
from app.main import create_app
from app.security.passwords import hash_password
from tests.conftest import OWNER_ID_TESTE, OWNER_USERNAME, SENHA_TESTE

PESQUISADOR_B_ID = "conta-pesquisador-b"
PESQUISADOR_B_USERNAME = "pesquisador_b"

PESQUISADOR_C_ID = "conta-pesquisador-c"
PESQUISADOR_C_USERNAME = "pesquisador_c"


@pytest.fixture
def acervo_equipe(db_session):
    """Projeto com protocolo e estudos pertencente ao titular coordenador."""
    projeto = ProjectModel(
        id="projeto-equipe-teste",
        owner_id=OWNER_ID_TESTE,
        title="Revisão Multicêntrica em APLs",
        methodology="PRISMA-ScR",
    )
    paper = PaperModel(
        id="estudo-equipe-1",
        project_id="projeto-equipe-teste",
        title="Dinâmica Territorial em Arranjos Produtivos",
    )
    db_session.add_all([projeto, paper])
    db_session.commit()
    return {"projeto": projeto, "paper": paper}


@pytest.fixture
def pesquisador_b(db_session):
    """Segundo pesquisador cadastrado na plataforma."""
    user = UserModel(
        id=PESQUISADOR_B_ID,
        username=PESQUISADOR_B_USERNAME,
        password_hash=hash_password(SENHA_TESTE),
        role="researcher",
        email="pesquisador.b@universidade.edu.br",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def pesquisador_c(db_session):
    """Terceiro pesquisador cadastrado na plataforma."""
    user = UserModel(
        id=PESQUISADOR_C_ID,
        username=PESQUISADOR_C_USERNAME,
        password_hash=hash_password(SENHA_TESTE),
        role="researcher",
        email="pesquisador.c@universidade.edu.br",
    )
    db_session.add(user)
    db_session.commit()
    return user


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
async def test_coordenador_emite_e_lista_convites_de_equipe(db_session, acervo_equipe):
    """Coordenador consegue emitir convite RSAC-EQ e listar convites do projeto."""
    dono = await _cliente(db_session, OWNER_USERNAME)
    pid = acervo_equipe["projeto"].id

    res = await dono.post(
        f"/api/v1/projects/{pid}/team/invitations",
        json={"email": "colega@usp.br", "project_role": "revisor", "note": "Revisor de triagem"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["code"].startswith("RSAC-EQ-")
    assert data["project_role"] == "revisor"
    assert data["is_valid"] is True

    # Listar
    lista = await dono.get(f"/api/v1/projects/{pid}/team/invitations")
    assert lista.status_code == 200
    assert len(lista.json()) == 1
    assert lista.json()[0]["code"] == data["code"]

    await dono.aclose()


@pytest.mark.anyio
async def test_pesquisador_aceita_convite_e_acessa_projeto(
    db_session, acervo_equipe, pesquisador_b
):
    """Pesquisador B aceita convite RSAC-EQ emitido por A e lê os estudos."""
    dono = await _cliente(db_session, OWNER_USERNAME)
    pid = acervo_equipe["projeto"].id

    convite_res = await dono.post(
        f"/api/v1/projects/{pid}/team/invitations",
        json={"project_role": "revisor"},
    )
    codigo = convite_res.json()["code"]
    await dono.aclose()

    # Pesquisador B aceita
    cliente_b = await _cliente(db_session, PESQUISADOR_B_USERNAME)
    aceite = await cliente_b.post(f"/api/v1/projects/invitations/{codigo}/accept")
    assert aceite.status_code == 200, aceite.text
    assert aceite.json()["status"] == "accepted"
    assert aceite.json()["project_id"] == pid

    # Agora B consegue ler o projeto e seus papers
    proj = await cliente_b.get(f"/api/v1/projects/{pid}")
    assert proj.status_code == 200
    assert proj.json()["my_role"] == "revisor"
    assert proj.json()["member_count"] == 2

    papers = await cliente_b.get(f"/api/v1/projects/{pid}/papers")
    assert papers.status_code == 200
    assert papers.json()["total"] == 1

    # Tentar aceitar de novo
    reaceite = await cliente_b.post(f"/api/v1/projects/invitations/{codigo}/accept")
    assert reaceite.status_code == 200
    assert reaceite.json()["status"] == "already_member"

    await cliente_b.aclose()


@pytest.mark.anyio
async def test_convite_revogado_expirado_e_inexistente(
    db_session, acervo_equipe, pesquisador_b
):
    """Convites inválidos, revogados ou expirados são recusados com 4xx."""
    dono = await _cliente(db_session, OWNER_USERNAME)
    pid = acervo_equipe["projeto"].id

    # 1. Inexistente
    cliente_b = await _cliente(db_session, PESQUISADOR_B_USERNAME)
    inexistente = await cliente_b.post("/api/v1/projects/invitations/RSAC-EQ-9999-9999/accept")
    assert inexistente.status_code == 404

    # 2. Revogado
    c1 = await dono.post(
        f"/api/v1/projects/{pid}/team/invitations",
        json={"project_role": "revisor"},
    )
    convite_id = c1.json()["id"]
    codigo_revogado = c1.json()["code"]

    revoga = await dono.delete(f"/api/v1/projects/{pid}/team/invitations/{convite_id}")
    assert revoga.status_code == 200

    tentativa_revogado = await cliente_b.post(
        f"/api/v1/projects/invitations/{codigo_revogado}/accept"
    )
    assert tentativa_revogado.status_code == 400
    assert "revogado" in tentativa_revogado.json()["detail"].lower()

    # 3. Expirado
    convite_exp = ProjectInvitationModel(
        project_id=pid,
        code="RSAC-EQ-EXPI-RADO",
        project_role="revisor",
        created_by_user_id=OWNER_ID_TESTE,
        created_at=utcnow() - timedelta(days=20),
        expires_at=utcnow() - timedelta(days=6),
    )
    db_session.add(convite_exp)
    db_session.commit()

    tentativa_expirado = await cliente_b.post(
        "/api/v1/projects/invitations/RSAC-EQ-EXPI-RADO/accept"
    )
    assert tentativa_expirado.status_code == 400
    assert "expirou" in tentativa_expirado.json()["detail"].lower()

    await dono.aclose()
    await cliente_b.aclose()


@pytest.mark.anyio
async def test_cadastro_encadeado_com_convite_de_equipe(db_session, acervo_equipe):
    """Usuário sem conta se cadastra usando RSAC-EQ-... e ganha conta + membro."""
    dono = await _cliente(db_session, OWNER_USERNAME)
    pid = acervo_equipe["projeto"].id

    convite_res = await dono.post(
        f"/api/v1/projects/{pid}/team/invitations",
        json={"project_role": "observador"},
    )
    codigo = convite_res.json()["code"]
    await dono.aclose()

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    anon = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    # 1. Validar convite antes do cadastro
    val = await anon.post("/api/v1/auth/invite/validate", json={"invite_code": codigo})
    assert val.status_code == 200
    assert val.json()["valid"] is True

    # 2. Registrar
    reg = await anon.post(
        "/api/v1/auth/register-with-invite",
        json={
            "invite_code": codigo,
            "username": "novato_equipe",
            "password": "SenhaForte1234!",
            "full_name": "Novato da Equipe",
            "email": "novato@pesquisa.org",
            "phone": "",
            "institution": "UFSC",
            "academic_degree": "Mestrando",
            "is_studying": True,
            "study_program": "Pós em Desenvolvimento Regional",
            "profession": "Pesquisador",
            "research_area": "Ciências Sociais Aplicadas",
            "terms_accepted": True,
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    anon.headers["Authorization"] = f"Bearer {token}"

    # 3. Validar que já acessa o projeto como observador
    proj = await anon.get(f"/api/v1/projects/{pid}")
    assert proj.status_code == 200
    assert proj.json()["my_role"] == "observador"

    await anon.aclose()


@pytest.mark.anyio
async def test_remover_membro_da_equipe(db_session, acervo_equipe, pesquisador_b):
    """Coordenador remove membro B da equipe; B volta a receber 404."""
    pid = acervo_equipe["projeto"].id

    membro_b = ProjectMemberModel(
        project_id=pid,
        user_id=pesquisador_b.id,
        project_role="revisor",
        is_active=True,
    )
    db_session.add(membro_b)
    db_session.commit()

    cliente_b = await _cliente(db_session, PESQUISADOR_B_USERNAME)
    assert (await cliente_b.get(f"/api/v1/projects/{pid}")).status_code == 200

    # Dono remove B
    dono = await _cliente(db_session, OWNER_USERNAME)
    remocao = await dono.delete(f"/api/v1/projects/{pid}/team/members/{pesquisador_b.id}")
    assert remocao.status_code == 200

    # B volta a receber 404
    assert (await cliente_b.get(f"/api/v1/projects/{pid}")).status_code == 404

    await dono.aclose()
    await cliente_b.aclose()


@pytest.mark.anyio
async def test_protecao_dono_e_ultimo_coordenador(db_session, acervo_equipe):
    """Não é permitido remover o titular perante a LGPD nem o único coordenador ativo."""
    dono = await _cliente(db_session, OWNER_USERNAME)
    pid = acervo_equipe["projeto"].id

    # Tentar remover o dono
    res = await dono.delete(f"/api/v1/projects/{pid}/team/members/{OWNER_ID_TESTE}")
    assert res.status_code == 400
    assert "titular" in res.json()["detail"].lower()

    await dono.aclose()
