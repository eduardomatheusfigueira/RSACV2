#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Router de Gestão de Convites (doc 41, Sistema de Convites).

Permite que o administrador/owner emita, consulte e revogue convites de uso único
para o cadastro de novos pesquisadores na plataforma.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    InviteCodeModel,
    UserModel,
    as_utc,
    generate_uuid,
)
from app.schemas.invites import (
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
)
from app.security.dependencies import require_owner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invites", tags=["invites"])


def gerar_codigo_convite() -> str:
    """Gera um código de convite legível e seguro no formato RSAC-XXXX-YYYY."""
    p1 = secrets.token_hex(2).upper()
    p2 = secrets.token_hex(2).upper()
    return f"RSAC-{p1}-{p2}"


def _serializar_convite(inv: InviteCodeModel, db: Session) -> InviteResponse:
    username_usuario = None
    if inv.used_by_user_id:
        usuario = db.query(UserModel).filter(UserModel.id == inv.used_by_user_id).first()
        if usuario:
            username_usuario = usuario.username

    return InviteResponse(
        id=inv.id,
        code=inv.code,
        note=inv.note,
        created_at=inv.created_at,
        expires_at=inv.expires_at,
        is_used=inv.is_used,
        used_at=inv.used_at,
        used_by_user_id=inv.used_by_user_id,
        used_by_username=username_usuario,
        is_revoked=inv.is_revoked,
    )


@router.post(
    "",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo convite de uso único (apenas owner)",
)
@router.post(
    "/",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def criar_convite(
    payload: InviteCreateRequest,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_owner),
):
    """
    Gera um novo convite de uso único para cadastro de usuário.
    """
    codigo = payload.custom_code.strip().upper() if payload.custom_code else gerar_codigo_convite()

    # Garantir unicidade
    existente = db.query(InviteCodeModel).filter(InviteCodeModel.code == codigo).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um convite com este código. Escolha outro ou deixe em branco para gerar automaticamente.",
        )

    agora = datetime.now(timezone.utc)
    expira_em = (
        agora + timedelta(days=payload.expires_in_days)
        if payload.expires_in_days
        else None
    )

    convite = InviteCodeModel(
        id=generate_uuid(),
        code=codigo,
        created_by_user_id=admin.id,
        created_at=agora,
        expires_at=expira_em,
        is_used=False,
        is_revoked=False,
        note=payload.note.strip(),
    )
    db.add(convite)
    db.commit()
    db.refresh(convite)

    logger.info(
        "[Convites] Novo convite '%s' criado pelo administrador '%s' (Nota: %s).",
        convite.code,
        admin.username,
        convite.note,
    )
    return _serializar_convite(convite, db)


@router.get(
    "",
    response_model=InviteListResponse,
    summary="Listar todos os convites emitidos (apenas owner)",
)
@router.get(
    "/",
    response_model=InviteListResponse,
    include_in_schema=False,
)
def listar_convites(
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(require_owner),
):
    """
    Lista todos os convites criados, status de uso e destinatários.
    """
    convites = db.query(InviteCodeModel).order_by(InviteCodeModel.created_at.desc()).all()
    resultado = [_serializar_convite(c, db) for c in convites]
    return InviteListResponse(invites=resultado, total=len(resultado))


@router.delete(
    "/{invite_id}",
    response_model=InviteResponse,
    summary="Revogar convite não utilizado (apenas owner)",
)
def revogar_convite(
    invite_id: str,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_owner),
):
    """
    Revoga um convite, impedindo que seja utilizado para novos cadastros.
    """
    convite = db.query(InviteCodeModel).filter(InviteCodeModel.id == invite_id).first()
    if not convite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado.",
        )

    if convite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível revogar um convite que já foi utilizado.",
        )

    convite.is_revoked = True
    db.commit()
    db.refresh(convite)

    logger.info(
        "[Convites] Convite '%s' (%s) revogado pelo administrador '%s'.",
        convite.code,
        convite.id,
        admin.username,
    )
    return _serializar_convite(convite, db)
