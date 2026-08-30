#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes do Sistema de Convites de Uso Único e Registro Acadêmico.
"""

from datetime import datetime, timedelta, timezone
import httpx
import pytest
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    InviteCodeModel,
    ProcessingRecordModel,
    UserModel,
    as_utc,
    generate_uuid,
)
from app.security.sessions import SESSION_COOKIE


@pytest.mark.anyio
async def test_validar_convite_inexistente(anon_client: httpx.AsyncClient):
    resp = await anon_client.post("/api/v1/auth/invite/validate", json={"invite_code": "NAO-EXISTE-999"})
    assert resp.status_code == 404
    assert "não encontrado" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_validar_convite_valido(anon_client: httpx.AsyncClient, db_session: Session):
    codigo = "RSAC-TEST-1234"
    convite = InviteCodeModel(
        id=generate_uuid(),
        code=codigo,
        note="Convite para Teste",
        is_used=False,
        is_revoked=False,
    )
    db_session.add(convite)
    db_session.commit()

    resp = await anon_client.post("/api/v1/auth/invite/validate", json={"invite_code": "rsac-test-1234"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["note"] == "Convite para Teste"


@pytest.mark.anyio
async def test_validar_convite_ja_utilizado(anon_client: httpx.AsyncClient, db_session: Session):
    codigo = "RSAC-USAD-0001"
    convite = InviteCodeModel(
        id=generate_uuid(),
        code=codigo,
        is_used=True,
        used_at=datetime.now(timezone.utc),
    )
    db_session.add(convite)
    db_session.commit()

    resp = await anon_client.post("/api/v1/auth/invite/validate", json={"invite_code": codigo})
    assert resp.status_code == 400
    assert "já foi utilizado" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_validar_convite_revogado(anon_client: httpx.AsyncClient, db_session: Session):
    codigo = "RSAC-REVO-0002"
    convite = InviteCodeModel(
        id=generate_uuid(),
        code=codigo,
        is_used=False,
        is_revoked=True,
    )
    db_session.add(convite)
    db_session.commit()

    resp = await anon_client.post("/api/v1/auth/invite/validate", json={"invite_code": codigo})
    assert resp.status_code == 400
    assert "revogado" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_validar_convite_expirado(anon_client: httpx.AsyncClient, db_session: Session):
    codigo = "RSAC-EXPI-0003"
    convite = InviteCodeModel(
        id=generate_uuid(),
        code=codigo,
        is_used=False,
        expires_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(convite)
    db_session.commit()

    resp = await anon_client.post("/api/v1/auth/invite/validate", json={"invite_code": codigo})
    assert resp.status_code == 400
    assert "expirou" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_registro_com_convite_sucesso_e_consumo_de_uso_unico(
    anon_client: httpx.AsyncClient, db_session: Session
):
    codigo = "RSAC-CAD-9999"
    convite = InviteCodeModel(
        id=generate_uuid(),
        code=codigo,
        note="Pesquisadora Convidada",
        is_used=False,
    )
    db_session.add(convite)
    db_session.commit()

    payload = {
        "invite_code": "rsac-cad-9999",
        "username": "maria_pesquisadora",
        "password": "SenhaForte12345!",
        "full_name": "Maria Silva e Silva",
        "email": "maria.silva@universidade.edu.br",
        "phone": "+55 51 99999-8888",
        "institution": "Universidade Federal do Rio Grande do Sul (UFRGS)",
        "academic_degree": "Doutoranda",
        "is_studying": True,
        "study_program": "Programa de Pós-Graduação em Desenvolvimento Regional (PPGDR)",
        "profession": "Professora e Pesquisadora",
        "research_area": "Ciências Sociais Aplicadas e Políticas Públicas Territoriais",
        "terms_accepted": True,
    }

    resp = await anon_client.post("/api/v1/auth/register-with-invite", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["username"] == "maria_pesquisadora"
    assert data["user"]["role"] == "researcher"

    # Verificar que o cookie de sessão foi emitido
    assert SESSION_COOKIE in resp.cookies

    # 1. Verificar usuário no banco de dados com todos os dados acadêmicos
    usuario = db_session.query(UserModel).filter(UserModel.username == "maria_pesquisadora").first()
    assert usuario is not None
    assert usuario.full_name == "Maria Silva e Silva"
    assert usuario.email == "maria.silva@universidade.edu.br"
    assert usuario.institution == "Universidade Federal do Rio Grande do Sul (UFRGS)"
    assert usuario.academic_degree == "Doutoranda"
    assert usuario.is_studying is True
    assert usuario.study_program == "Programa de Pós-Graduação em Desenvolvimento Regional (PPGDR)"
    assert usuario.research_area == "Ciências Sociais Aplicadas e Políticas Públicas Territoriais"

    # 2. Verificar que o convite foi marcado como utilizado
    db_session.refresh(convite)
    assert convite.is_used is True
    assert convite.used_at is not None
    assert convite.used_by_user_id == usuario.id

    # 3. Tentar reutilizar o mesmo convite DEVE FALHAR
    resp_segundo_uso = await anon_client.post(
        "/api/v1/auth/register-with-invite",
        json={**payload, "username": "outro_usuario", "email": "outro@email.com"},
    )
    assert resp_segundo_uso.status_code == 400
    assert "já foi utilizado" in resp_segundo_uso.json()["detail"].lower()

    # 4. Verificar registro ROPA do signup
    registro_ropa = (
        db_session.query(ProcessingRecordModel)
        .filter(
            ProcessingRecordModel.user_id == usuario.id,
            ProcessingRecordModel.operation == "signup",
        )
        .first()
    )
    assert registro_ropa is not None
    assert "convite de uso único" in registro_ropa.purpose.lower()


@pytest.mark.anyio
async def test_registro_recusa_username_ou_email_duplicados(
    anon_client: httpx.AsyncClient, db_session: Session
):
    # Criar convite 1 e registrar usuario
    c1 = InviteCodeModel(id=generate_uuid(), code="RSAC-DUP-0001", is_used=False)
    c2 = InviteCodeModel(id=generate_uuid(), code="RSAC-DUP-0002", is_used=False)
    db_session.add_all([c1, c2])
    db_session.commit()

    base_payload = {
        "invite_code": "RSAC-DUP-0001",
        "username": "usuario_original",
        "password": "SenhaForte12345!",
        "full_name": "Usuario Original",
        "email": "original@universidade.edu.br",
        "terms_accepted": True,
    }
    resp1 = await anon_client.post("/api/v1/auth/register-with-invite", json=base_payload)
    assert resp1.status_code == 201

    # Tentar com mesmo username
    resp_dup_user = await anon_client.post(
        "/api/v1/auth/register-with-invite",
        json={
            **base_payload,
            "invite_code": "RSAC-DUP-0002",
            "email": "diferente@universidade.edu.br",
        },
    )
    assert resp_dup_user.status_code == 409
    assert "nome de usuário já está em uso" in resp_dup_user.json()["detail"].lower()

    # Tentar com mesmo email
    resp_dup_email = await anon_client.post(
        "/api/v1/auth/register-with-invite",
        json={
            **base_payload,
            "invite_code": "RSAC-DUP-0002",
            "username": "usuario_diferente",
        },
    )
    assert resp_dup_email.status_code == 409
    assert "e-mail já está cadastrado" in resp_dup_email.json()["detail"].lower()


@pytest.mark.anyio
async def test_crud_convites_admin(async_client: httpx.AsyncClient):
    # 1. Criar convite autenticado como owner
    resp_create = await async_client.post(
        "/api/v1/invites",
        json={"note": "Convite para PPGDR", "expires_in_days": 15},
    )
    assert resp_create.status_code == 201
    convite_data = resp_create.json()
    assert convite_data["code"].startswith("RSAC-")
    assert convite_data["note"] == "Convite para PPGDR"
    assert convite_data["is_used"] is False
    invite_id = convite_data["id"]

    # 2. Listar convites
    resp_list = await async_client.get("/api/v1/invites")
    assert resp_list.status_code == 200
    lista = resp_list.json()
    assert lista["total"] >= 1
    assert any(c["id"] == invite_id for c in lista["invites"])

    # 3. Revogar convite
    resp_revoke = await async_client.delete(f"/api/v1/invites/{invite_id}")
    assert resp_revoke.status_code == 200
    assert resp_revoke.json()["is_revoked"] is True


@pytest.mark.anyio
async def test_gerenciamento_usuario_admin(
    async_client: httpx.AsyncClient, db_session: Session
):
    # 1. Criar um usuário pesquisador via banco
    from app.security.passwords import hash_password

    u_name = f"pesq_{generate_uuid()[:8]}"
    u = UserModel(
        id=generate_uuid(),
        username=u_name,
        password_hash=hash_password("SenhaForte123!"),
        role="researcher",
        is_active=True,
        full_name="Prof. Teste",
        email=f"{u_name}@universidade.edu.br",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    # 2. Listar usuários como owner
    resp_list = await async_client.get("/api/v1/auth/users")
    assert resp_list.status_code == 200
    users = resp_list.json()["items"]
    assert any(user["username"] == u_name for user in users)

    # 3. Atualizar papel e dados acadêmicos do usuário
    resp_patch = await async_client.patch(
        f"/api/v1/auth/users/{u.id}",
        json={
            "role": "owner",
            "institution": "UFRGS",
            "academic_degree": "Doutor(a)",
            "study_program": "PPG em Desenvolvimento Regional",
            "profession": "Docente / Pesquisador",
            "research_area": "Políticas Públicas e APLs",
        },
    )
    assert resp_patch.status_code == 200
    updated_user = resp_patch.json()
    assert updated_user["role"] == "owner"
    assert updated_user["institution"] == "UFRGS"
    assert updated_user["academic_degree"] == "Doutor(a)"
    assert updated_user["research_area"] == "Políticas Públicas e APLs"

    # 4. Redefinir senha do usuário como admin
    resp_reset = await async_client.post(
        f"/api/v1/auth/users/{u.id}/reset-password",
        json={"new_password": "NovaSenhaSegura123!"},
    )
    assert resp_reset.status_code == 200
    assert "NovaSenhaSegura123!" in resp_reset.json()["temporary_password"]

