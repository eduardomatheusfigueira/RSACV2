#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Router de Gestão de Convites (doc 41, Sistema de Convites).

Permite que o administrador/owner emita, consulte e revogue convites de uso único
para o cadastro de novos pesquisadores na plataforma.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    InviteCodeModel,
    InviteRequestModel,
    UserModel,
    as_utc,
    generate_uuid,
)
from app.schemas.invites import (
    InviteCreateRequest,
    InviteListResponse,
    InviteRequestApprove,
    InviteRequestApproveResponse,
    InviteRequestListResponse,
    InviteRequestResponse,
    InviteRequestUpdate,
    InviteResponse,
)
from app.security.dependencies import require_owner
from app.services import aprovacao_convite
from app.services.retencao import aplicar_retencao_se_devido

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invites", tags=["invites"])


gerar_codigo_convite = aprovacao_convite.gerar_codigo_convite


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


# ── Fila de solicitações vindas da tela de login ──────────────────────
#
# O convite continua sendo de emissão exclusiva do administrador; o que estas
# rotas acrescentam é a fila de quem pediu. Aprovar é o atalho que faltava:
# uma chamada gera o código, marca o pedido como atendido e guarda qual código
# foi emitido para aquela pessoa — o vínculo que, feito à mão, se perdia.


def _serializar_solicitacao(s: InviteRequestModel) -> InviteRequestResponse:
    return InviteRequestResponse(
        id=s.id,
        nome=s.nome,
        email=s.email,
        telefone=s.telefone,
        onde_conheceu=s.onde_conheceu,
        instituicao=s.instituicao or "",
        status=s.status,
        created_at=s.created_at,
        responded_at=s.responded_at,
        invite_code_generated=s.invite_code_generated,
        admin_notes=s.admin_notes or "",
    )


@router.get(
    "/requests",
    response_model=InviteRequestListResponse,
    summary="Listar solicitações de convite recebidas (apenas owner)",
)
def listar_solicitacoes(
    status_filtro: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(require_owner),
):
    """
    Lista os pedidos de acesso enviados pela tela de login.

    Pendentes primeiro, e dentro de cada grupo o mais recente na frente: a
    fila existe para ser respondida, e ordenar só por data deixaria um pedido
    novo já recusado acima de um antigo ainda sem resposta.
    """
    aplicar_retencao_se_devido(db)

    consulta = db.query(InviteRequestModel)
    if status_filtro:
        consulta = consulta.filter(InviteRequestModel.status == status_filtro.strip().lower())

    solicitacoes = consulta.order_by(InviteRequestModel.created_at.desc()).all()
    itens = [_serializar_solicitacao(s) for s in solicitacoes]
    itens.sort(key=lambda i: (i.status != "pendente", -i.created_at.timestamp()))

    pendentes = db.query(InviteRequestModel).filter(
        InviteRequestModel.status == "pendente"
    ).count()

    return InviteRequestListResponse(
        requests=itens,
        total=len(itens),
        pendentes=pendentes,
    )


@router.post(
    "/requests/{request_id}/approve",
    response_model=InviteRequestApproveResponse,
    summary="Aprovar solicitação emitindo um convite de uso único (apenas owner)",
)
def aprovar_solicitacao(
    request_id: str,
    payload: InviteRequestApprove,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_owner),
):
    """
    Emite um convite para quem solicitou e marca o pedido como aprovado.
    """
    solicitacao = (
        db.query(InviteRequestModel).filter(InviteRequestModel.id == request_id).first()
    )
    if not solicitacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação não encontrada.",
        )
    try:
        resultado = aprovacao_convite.aprovar(
            db,
            solicitacao,
            aprovado_por_id=admin.id,
            via="painel",
            expires_in_days=payload.expires_in_days,
            nota=payload.note,
        )
    except aprovacao_convite.PedidoJaRespondido:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Esta solicitação já foi aprovada com o convite "
                f"{solicitacao.invite_code_generated}."
            ),
        )

    convite = resultado.convite
    mensagens = resultado.mensagens
    envio = resultado.envio

    return InviteRequestApproveResponse(
        request=_serializar_solicitacao(solicitacao),
        invite=_serializar_convite(convite, db),
        link_direto=mensagens.link_direto,
        whatsapp_url=mensagens.whatsapp_url,
        email_enviado=envio.enviado,
        email_detalhe=envio.detalhe,
    )


@router.patch(
    "/requests/{request_id}",
    response_model=InviteRequestResponse,
    summary="Atualizar status ou anotação de uma solicitação (apenas owner)",
)
def atualizar_solicitacao(
    request_id: str,
    payload: InviteRequestUpdate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_owner),
):
    """
    Recusa, reabre ou anota um pedido sem emitir convite.
    """
    solicitacao = (
        db.query(InviteRequestModel).filter(InviteRequestModel.id == request_id).first()
    )
    if not solicitacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação não encontrada.",
        )

    if payload.status is not None and payload.status != solicitacao.status:
        solicitacao.status = payload.status
        solicitacao.responded_at = (
            datetime.now(timezone.utc) if payload.status != "pendente" else None
        )
    if payload.admin_notes is not None:
        solicitacao.admin_notes = payload.admin_notes.strip()

    db.commit()
    db.refresh(solicitacao)

    logger.info(
        "[Convites] Solicitação %s atualizada por '%s' (status: %s).",
        solicitacao.id,
        admin.username,
        solicitacao.status,
    )
    return _serializar_solicitacao(solicitacao)


@router.delete(
    "/requests/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir definitivamente uma solicitação (apenas owner)",
)
def excluir_solicitacao(
    request_id: str,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_owner),
):
    """
    Apaga o pedido e, com ele, os dados de contato de quem não virou usuário.

    É a contrapartida do formulário público: a fila guarda nome, e-mail e
    telefone de gente que não tem conta para pedir a própria eliminação, de
    modo que o administrador precisa poder fazê-lo por ela.
    """
    solicitacao = (
        db.query(InviteRequestModel).filter(InviteRequestModel.id == request_id).first()
    )
    if not solicitacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação não encontrada.",
        )

    db.delete(solicitacao)
    db.commit()
    logger.info(
        "[Convites] Solicitação %s excluída pelo administrador '%s'.",
        request_id,
        admin.username,
    )
