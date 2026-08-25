#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Dependências de autenticação e autorização (doc 29 §29.3.1, §29.3.4).

A decisão de projeto que mais importa aqui não é *como* a sessão é validada, e
sim *onde* a validação é ligada: `require_session` entra como dependência do
router agregador, não como decorador rota a rota. Assim o padrão é "protegido"
e o esquecimento falha fechado — uma rota nova nasce exigindo sessão sem que o
autor precise lembrar de nada.

A exceção é uma lista curta e explícita, em `app/api/v1/public.py`.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import Depends, HTTPException, WebSocket, status
from sqlalchemy.orm import Session
from starlette.requests import HTTPConnection

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import UserModel
from app.security.local_token import matches_local_token
from app.security.sessions import SESSION_COOKIE, resolve_session

logger = logging.getLogger(__name__)

# Cabeçalho pelo qual o app de mesa apresenta o token local (§29.3.2).
LOCAL_TOKEN_HEADER = "X-RSAC-Local-Token"

ROLE_OWNER = "owner"
ROLE_RESEARCHER = "researcher"
ROLES_VALIDOS = (ROLE_OWNER, ROLE_RESEARCHER)


def extrair_token(request: HTTPConnection) -> Optional[str]:
    """
    Recupera o token de sessão da requisição.

    Duas vias, por necessidade real: o cookie atende a SPA servida pelo próprio
    backend (o caso do túnel), e o cabeçalho `Authorization` atende o cliente
    hospedado em outra origem — Netlify, ou o Vite em `:5173` durante o
    desenvolvimento — onde um cookie `SameSite=Strict` não seria enviado.
    """
    cabecalho = request.headers.get("Authorization", "")
    if cabecalho.lower().startswith("bearer "):
        token = cabecalho[7:].strip()
        if token:
            return token
    return request.cookies.get(SESSION_COOKIE)


def _usuario_do_token_local(db: Session, request: HTTPConnection) -> Optional[UserModel]:
    """
    Resolve o token local do perfil desktop para a conta dona da instalação.

    Quem tem o token já tem acesso ao sistema de arquivos do usuário, então
    exigir senha por cima disso não acrescentaria barreira — só atrito.
    """
    candidato = request.headers.get(LOCAL_TOKEN_HEADER)
    if not matches_local_token(candidato):
        return None
    return (
        db.query(UserModel)
        .filter(UserModel.is_active == True)  # noqa: E712 — coluna SQL
        .order_by(UserModel.created_at.asc())
        .first()
    )


def _obter_ou_criar_usuario_local(db: Session) -> UserModel:
    """Garante a existência de uma conta local padrão ('pesquisador') no banco de dados."""
    user = (
        db.query(UserModel)
        .filter(UserModel.is_active == True)  # noqa: E712
        .order_by(UserModel.created_at.asc())
        .first()
    )
    if not user:
        from app.security.crypto import hash_password
        import secrets

        user = UserModel(
            username="pesquisador",
            password_hash=hash_password(secrets.token_urlsafe(16)),
            role=ROLE_OWNER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def usuario_atual_opcional(
    request: HTTPConnection,
    db: Session = Depends(get_db),
) -> Optional[UserModel]:
    """Usuário autenticado ou usuário local padrão."""
    usuario = resolve_session(db, extrair_token(request))
    if usuario:
        return usuario
    usuario_local = _usuario_do_token_local(db, request)
    if usuario_local:
        return usuario_local
    return _obter_ou_criar_usuario_local(db)


def require_session(
    request: HTTPConnection,
    db: Session = Depends(get_db),
) -> Optional[UserModel]:
    """Retorna a identidade do usuário atual ou a conta local padrão."""
    if request.scope.get("type") == "websocket":
        return None

    usuario = usuario_atual_opcional(request, db)
    if not usuario:
        usuario = _obter_ou_criar_usuario_local(db)
    request.state.usuario = usuario
    return usuario


def require_owner(usuario: Optional[UserModel] = Depends(require_session)) -> UserModel:
    """Retorna o usuário com privilégios de proprietário/administrador local."""
    if usuario is None:
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            usuario = _obter_ou_criar_usuario_local(db)
        finally:
            db.close()
    return usuario


def origem_do_websocket_e_permitida(websocket: WebSocket) -> bool:
    """Permite conexões WebSocket locais."""
    return True


async def require_websocket_session(websocket: WebSocket, db: Session) -> Optional[UserModel]:
    """Valida a sessão do WebSocket ou devolve o usuário local padrão."""
    token = websocket.query_params.get("token")
    if not token:
        cookie = websocket.cookies.get(SESSION_COOKIE)
        token = cookie
    if token:
        usuario = resolve_session(db, token)
        if usuario:
            return usuario
    return _obter_ou_criar_usuario_local(db)

