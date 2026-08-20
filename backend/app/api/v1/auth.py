#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Router de Autenticação e Contas (doc 29 §29.3).

Este módulo tem duas metades com regimes opostos, e a distinção é deliberada:

  * `public_auth_router` — as três rotas que respondem sem sessão: `status`,
    `login` e `local`. É a lista de exceções de §29.3.1, e ela precisa ser
    curta o bastante para caber na cabeça de quem revisa.
  * `router` — gestão de contas, que exige sessão como todo o resto e, para
    criar ou remover usuários, papel `owner`.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import UserModel
from app.schemas.auth import (
    AuthStatusResponse,
    LocalTokenRequest,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    UserCreatedResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
)
from app.security.dependencies import (
    ROLE_OWNER,
    extrair_token,
    require_owner,
    require_session,
    usuario_atual_opcional,
)
from app.security.local_token import matches_local_token, read_local_token
from app.security.passwords import (
    PasswordPolicyError,
    generate_password,
    hash_password,
    verify_password,
)
from app.security.sessions import (
    SESSION_COOKIE,
    create_session,
    login_bloqueado,
    register_login_attempt,
    revoke_all_sessions,
    revoke_session,
)

logger = logging.getLogger(__name__)

public_auth_router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter(prefix="/auth", tags=["auth"])


def _serializar(user: UserModel) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _definir_cookie(response: Response, token: str, request: Request) -> None:
    """
    Grava o cookie de sessão.

    `HttpOnly` tira o token do alcance de qualquer script na página;
    `SameSite=strict` impede que outro site o envie junto de uma requisição
    forjada; `Secure` entra quando a conexão é HTTPS — que é o caso do túnel,
    e não o do `localhost` em desenvolvimento.
    """
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def _emitir_sessao(
    db: Session, user: UserModel, request: Request, response: Response
) -> LoginResponse:
    token, _ = create_session(db, user, user_agent=request.headers.get("User-Agent", ""))
    _definir_cookie(response, token, request)
    return LoginResponse(
        user=_serializar(user),
        access_token=token,
        expires_in_hours=settings.session_ttl_hours,
    )


# ── Rotas públicas (a lista de exceções de §29.3.1) ───────────────────

@public_auth_router.get("/status", response_model=AuthStatusResponse)
def auth_status(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Diz se há contas provisionadas e se esta requisição já está autenticada.

    Não revela nome de usuário nem nada que ajude a adivinhar credencial — só o
    necessário para o cliente decidir entre a tela de login e a aplicação, e
    para o lançador recusar-se a publicar um backend desprotegido.
    """
    total_contas = db.query(UserModel).filter(UserModel.is_active == True).count()  # noqa: E712
    usuario = usuario_atual_opcional(request, db)

    return AuthStatusResponse(
        authentication_enabled=True,
        deployment_profile=settings.deployment_profile.value,
        has_accounts=total_contas > 0,
        local_token_accepted=(not settings.is_server_profile) and bool(read_local_token()),
        authenticated=usuario is not None,
        user=_serializar(usuario) if usuario else None,
    )


@public_auth_router.post("/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Autentica por usuário e senha e abre uma sessão."""
    username = data.username.strip()
    client_host = request.client.host if request.client else ""

    if login_bloqueado(db, username):
        logger.warning("[Auth] Login bloqueado por excesso de tentativas: %s", username)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde 15 minutos e tente de novo.",
        )

    user = db.query(UserModel).filter(UserModel.username == username).first()
    senha_confere = bool(user) and verify_password(user.password_hash, data.password)

    if not user or not senha_confere or not user.is_active:
        register_login_attempt(db, username, client_host, successful=False)
        # Mensagem única de propósito: distinguir "usuário não existe" de
        # "senha errada" entregaria a lista de contas a quem sondar.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos.",
        )

    register_login_attempt(db, username, client_host, successful=True)
    logger.info("[Auth] Login bem-sucedido: %s (%s)", user.username, user.role)
    return _emitir_sessao(db, user, request, response)


@public_auth_router.post("/local", response_model=LoginResponse)
def login_com_token_local(
    data: LocalTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Troca o token local do perfil desktop por uma sessão.

    É o que mantém o app de mesa sem tela de login: o Electron lê o arquivo
    `runtime_token` e chama esta rota. No perfil `server` ela não existe como
    caminho válido — lá a prova é a senha.
    """
    if settings.is_server_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O token local não é aceito no perfil de servidor. Faça login com usuário e senha.",
        )
    if not matches_local_token(data.token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token local inválido.")

    user = (
        db.query(UserModel)
        .filter(UserModel.is_active == True)  # noqa: E712
        .order_by(UserModel.created_at.asc())
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nenhuma conta provisionada nesta instalação.",
        )

    return _emitir_sessao(db, user, request, response)


# ── Rotas autenticadas ────────────────────────────────────────────────

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_session),
):
    """Encerra a sessão no servidor e apaga o cookie."""
    revoke_session(db, extrair_token(request))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "ok", "message": "Sessão encerrada."}


@router.get("/me", response_model=UserResponse)
def me(usuario: UserModel = Depends(require_session)):
    """Identidade da sessão corrente."""
    return _serializar(usuario)


@router.post("/password", status_code=200)
def alterar_senha(
    data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Troca a própria senha e encerra as demais sessões da conta."""
    if not verify_password(usuario.password_hash, data.current_password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Senha atual incorreta.")
    try:
        usuario.password_hash = hash_password(data.new_password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.commit()
    # Trocar a senha precisa derrubar sessões antigas: se a troca foi motivada
    # por suspeita de vazamento, manter as outras vivas anularia o gesto.
    revoke_all_sessions(db, usuario.id)
    return {"status": "ok", "message": "Senha alterada. Faça login novamente."}


@router.get("/users", response_model=UserListResponse)
def listar_usuarios(
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_owner),
):
    """Lista as contas da instalação. Exclusivo de `owner`."""
    usuarios = db.query(UserModel).order_by(UserModel.created_at.asc()).all()
    return UserListResponse(items=[_serializar(u) for u in usuarios], total=len(usuarios))


@router.post("/users", response_model=UserCreatedResponse, status_code=201)
def criar_usuario(
    data: UserCreateRequest,
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_owner),
):
    """Cria uma conta. Sem senha informada, sorteia uma e a devolve uma só vez."""
    username = data.username.strip()
    if db.query(UserModel).filter(UserModel.username == username).first():
        raise HTTPException(status_code=409, detail=f"O usuário '{username}' já existe.")

    senha_gerada = None
    senha = data.password
    if not senha:
        senha = generate_password()
        senha_gerada = senha

    try:
        user = UserModel(username=username, password_hash=hash_password(senha), role=data.role)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("[Auth] Conta criada: %s (%s)", user.username, user.role)

    return UserCreatedResponse(user=_serializar(user), generated_password=senha_gerada)


@router.delete("/users/{user_id}")
def desativar_usuario(
    user_id: str,
    db: Session = Depends(get_db),
    solicitante: UserModel = Depends(require_owner),
):
    """Desativa uma conta e encerra suas sessões."""
    if user_id == solicitante.id:
        raise HTTPException(status_code=400, detail="Não é possível desativar a própria conta.")

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    donos_ativos = (
        db.query(UserModel)
        .filter(UserModel.role == ROLE_OWNER, UserModel.is_active == True)  # noqa: E712
        .count()
    )
    if user.role == ROLE_OWNER and donos_ativos <= 1:
        raise HTTPException(
            status_code=400,
            detail="Esta é a última conta administradora ativa — a instalação ficaria sem dono.",
        )

    user.is_active = False
    db.commit()
    revoke_all_sessions(db, user.id)
    return {"status": "ok", "message": f"Conta '{user.username}' desativada."}
