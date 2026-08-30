#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Router de Gestão de Equipe e Convites de Projeto (doc 43 §43.10, Fase 1).
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import (
    ProjectInvitationModel,
    ProjectMemberModel,
    ProjectModel,
    UserModel,
    as_utc,
    utcnow,
)
from app.schemas.team import (
    AcceptInvitationResponse,
    ProjectInvitationCreate,
    ProjectInvitationResponse,
    ProjectMemberResponse,
    TeamResponse,
)
from app.security.dependencies import projeto_do_usuario, require_session
from app.services import ropa_service
from app.services.harvesting_service import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["team"])


def gerar_codigo_equipe() -> str:
    """Gera um código de convite de equipe no formato RSAC-EQ-XXXX-YYYY."""
    p1 = secrets.token_hex(2).upper()
    p2 = secrets.token_hex(2).upper()
    return f"RSAC-EQ-{p1}-{p2}"


def _serializar_membro(m: ProjectMemberModel, user: UserModel) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        id=m.id,
        project_id=m.project_id,
        user_id=m.user_id,
        username=user.username,
        display_name=user.display_name or user.full_name,
        email=user.email,
        project_role=m.project_role,
        is_active=m.is_active,
        joined_at=m.joined_at,
        left_at=m.left_at,
    )


def _serializar_convite(inv: ProjectInvitationModel, db: Session) -> ProjectInvitationResponse:
    criador = db.query(UserModel).filter(UserModel.id == inv.created_by_user_id).first()
    aceitador = (
        db.query(UserModel).filter(UserModel.id == inv.accepted_by_user_id).first()
        if inv.accepted_by_user_id
        else None
    )

    agora = utcnow()
    expira = as_utc(inv.expires_at)
    is_valid = (
        inv.revoked_at is None
        and inv.accepted_at is None
        and bool(expira and expira > agora)
    )

    return ProjectInvitationResponse(
        id=inv.id,
        project_id=inv.project_id,
        code=inv.code,
        email=inv.email,
        project_role=inv.project_role,
        created_by_user_id=inv.created_by_user_id,
        created_by_username=criador.username if criador else None,
        created_at=inv.created_at,
        expires_at=inv.expires_at,
        accepted_at=inv.accepted_at,
        accepted_by_user_id=inv.accepted_by_user_id,
        accepted_by_username=aceitador.username if aceitador else None,
        revoked_at=inv.revoked_at,
        is_valid=is_valid,
        note=inv.note,
    )


# ── Rotas com prefixo do projeto ─────────────────────────────────────

@router.get(
    "/projects/{project_id}/team",
    response_model=TeamResponse,
    summary="Resumo da equipe do projeto",
)
def obter_equipe_projeto(
    request: Request,
    project: ProjectModel = Depends(projeto_do_usuario),
    db: Session = Depends(get_db),
):
    """Retorna os membros ativos e inativos e convites (se for coordenador)."""
    membro_atual: ProjectMemberModel = request.state.membro
    is_coordenador = membro_atual.project_role == "coordenador"

    membros_db = (
        db.query(ProjectMemberModel, UserModel)
        .join(UserModel, ProjectMemberModel.user_id == UserModel.id)
        .filter(ProjectMemberModel.project_id == project.id)
        .order_by(ProjectMemberModel.joined_at.asc())
        .all()
    )
    members_resp = [_serializar_membro(m, u) for m, u in membros_db]

    invites_resp = []
    if is_coordenador:
        convites = (
            db.query(ProjectInvitationModel)
            .filter(ProjectInvitationModel.project_id == project.id)
            .order_by(ProjectInvitationModel.created_at.desc())
            .all()
        )
        invites_resp = [_serializar_convite(inv, db) for inv in convites]

    return TeamResponse(
        project_id=project.id,
        members=members_resp,
        invitations=invites_resp,
        my_role=membro_atual.project_role,
        my_user_id=membro_atual.user_id,
    )


@router.get(
    "/projects/{project_id}/team/members",
    response_model=list[ProjectMemberResponse],
    summary="Lista membros da equipe",
)
def listar_membros_equipe(
    project: ProjectModel = Depends(projeto_do_usuario),
    db: Session = Depends(get_db),
):
    membros_db = (
        db.query(ProjectMemberModel, UserModel)
        .join(UserModel, ProjectMemberModel.user_id == UserModel.id)
        .filter(ProjectMemberModel.project_id == project.id)
        .order_by(ProjectMemberModel.joined_at.asc())
        .all()
    )
    return [_serializar_membro(m, u) for m, u in membros_db]


@router.delete(
    "/projects/{project_id}/team/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove ou desliga um membro da equipe (doc 43 §43.13.1)",
)
async def remover_membro_equipe(
    user_id: str,
    request: Request,
    project: ProjectModel = Depends(projeto_do_usuario),
    usuario: UserModel = Depends(require_session),
    db: Session = Depends(get_db),
):
    """
    Desliga a participação do membro (is_active=False).
    Preserva o registro para rastro de autoria e decisões.
    """
    membro_solicitante: ProjectMemberModel = request.state.membro
    is_coordenador = membro_solicitante.project_role == "coordenador"
    is_proprio_usuario = usuario.id == user_id

    if not is_coordenador and not is_proprio_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas coordenadores podem remover outros pesquisadores da equipe.",
        )

    # 1. O titular perante a LGPD não pode ser removido
    if user_id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O titular da conta (dono do projeto) não pode ser removido da equipe.",
        )

    # 2. Localizar membro alvo
    membro_alvo = (
        db.query(ProjectMemberModel)
        .filter(
            ProjectMemberModel.project_id == project.id,
            ProjectMemberModel.user_id == user_id,
            ProjectMemberModel.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not membro_alvo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro ativo não encontrado neste projeto.",
        )

    # 3. Não pode deixar o projeto sem coordenador
    if membro_alvo.project_role == "coordenador":
        coordenadores_ativos = (
            db.query(ProjectMemberModel)
            .filter(
                ProjectMemberModel.project_id == project.id,
                ProjectMemberModel.project_role == "coordenador",
                ProjectMemberModel.is_active == True,  # noqa: E712
            )
            .count()
        )
        if coordenadores_ativos <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível remover o único coordenador ativo do projeto.",
            )

    agora = utcnow()
    membro_alvo.is_active = False
    membro_alvo.left_at = agora

    ropa_service.registrar(
        db,
        operation="team_membership_revoked",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Desligamento de membro de equipe de projeto de revisão sistemática",
        data_categories=["identificacao"],
        user_id=user_id,
        commit=False,
    )
    db.commit()

    logger.info(
        "[Equipe] Membro %s desligado do projeto %s por %s",
        user_id,
        project.id,
        usuario.username,
    )

    # Doc 43 §43.12.1: quem estiver com a tela de Equipe aberta precisa ver a
    # composição mudar sem recarregar — o canal já existe, faltava o evento.
    await ws_manager.broadcast(
        project.id,
        {
            "type": "equipe.alterada",
            "user_id": user_id,
            "acao": "membro_desligado",
            "por": usuario.username,
        },
    )

    return {"status": "ok", "message": "Participação no projeto encerrada com sucesso."}


@router.get(
    "/projects/{project_id}/team/invitations",
    response_model=list[ProjectInvitationResponse],
    summary="Lista convites de equipe do projeto (apenas coordenador)",
)
def listar_convites_equipe(
    request: Request,
    project: ProjectModel = Depends(projeto_do_usuario),
    db: Session = Depends(get_db),
):
    membro_solicitante: ProjectMemberModel = request.state.membro
    if membro_solicitante.project_role != "coordenador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas coordenadores podem visualizar a lista de convites emitidos.",
        )

    convites = (
        db.query(ProjectInvitationModel)
        .filter(ProjectInvitationModel.project_id == project.id)
        .order_by(ProjectInvitationModel.created_at.desc())
        .all()
    )
    return [_serializar_convite(inv, db) for inv in convites]


@router.post(
    "/projects/{project_id}/team/invitations",
    response_model=ProjectInvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Emite novo convite de equipe para o projeto (apenas coordenador)",
)
def emitir_convite_equipe(
    payload: ProjectInvitationCreate,
    request: Request,
    project: ProjectModel = Depends(projeto_do_usuario),
    usuario: UserModel = Depends(require_session),
    db: Session = Depends(get_db),
):
    membro_solicitante: ProjectMemberModel = request.state.membro
    if membro_solicitante.project_role != "coordenador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas coordenadores podem emitir convites para este projeto.",
        )

    # 1. Teto de membros ativos
    membros_ativos = (
        db.query(ProjectMemberModel)
        .filter(
            ProjectMemberModel.project_id == project.id,
            ProjectMemberModel.is_active == True,  # noqa: E712
        )
        .count()
    )
    if membros_ativos >= settings.max_members_per_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {settings.max_members_per_project} membros atingido para este projeto.",
        )

    # 2. Teto de convites ativos pendentes
    agora = utcnow()
    convites_ativos = (
        db.query(ProjectInvitationModel)
        .filter(
            ProjectInvitationModel.project_id == project.id,
            ProjectInvitationModel.revoked_at.is_(None),
            ProjectInvitationModel.accepted_at.is_(None),
            ProjectInvitationModel.expires_at > agora,
        )
        .count()
    )
    if convites_ativos >= settings.max_active_invitations_per_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {settings.max_active_invitations_per_project} convites pendentes atingido.",
        )

    # 3. Gerar código único
    codigo = gerar_codigo_equipe()
    while db.query(ProjectInvitationModel).filter(ProjectInvitationModel.code == codigo).first():
        codigo = gerar_codigo_equipe()

    expira_em = agora + timedelta(days=settings.project_invitation_expiry_days)

    convite = ProjectInvitationModel(
        project_id=project.id,
        code=codigo,
        email=payload.email.strip().lower() if payload.email else None,
        project_role=payload.project_role,
        created_by_user_id=usuario.id,
        created_at=agora,
        expires_at=expira_em,
        note=payload.note.strip(),
    )
    db.add(convite)
    db.flush()

    ropa_service.registrar(
        db,
        operation="team_invitation_issued",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Emissão de convite de equipe para projeto de revisão sistemática",
        data_categories=["identificacao", "contato"] if payload.email else ["identificacao"],
        user_id=usuario.id,
        commit=False,
    )
    db.commit()
    db.refresh(convite)

    logger.info(
        "[Equipe] Convite %s emitido por %s para o projeto %s (papel: %s)",
        convite.code,
        usuario.username,
        project.id,
        convite.project_role,
    )
    return _serializar_convite(convite, db)


@router.delete(
    "/projects/{project_id}/team/invitations/{invite_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoga um convite de equipe (apenas coordenador)",
)
def revogar_convite_equipe(
    invite_id: str,
    request: Request,
    project: ProjectModel = Depends(projeto_do_usuario),
    usuario: UserModel = Depends(require_session),
    db: Session = Depends(get_db),
):
    membro_solicitante: ProjectMemberModel = request.state.membro
    if membro_solicitante.project_role != "coordenador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas coordenadores podem revogar convites deste projeto.",
        )

    convite = (
        db.query(ProjectInvitationModel)
        .filter(
            ProjectInvitationModel.id == invite_id,
            ProjectInvitationModel.project_id == project.id,
        )
        .first()
    )
    if not convite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convite não encontrado.")

    if convite.revoked_at:
        return {"status": "ok", "message": "Convite já se encontrava revogado."}

    convite.revoked_at = utcnow()
    db.commit()
    logger.info("[Equipe] Convite %s revogado por %s", convite.code, usuario.username)
    return {"status": "ok", "message": "Convite revogado com sucesso."}


# ── Rota pública/autenticada de Aceite de Convite ───────────────────────

@router.post(
    "/projects/invitations/{code}/accept",
    response_model=AcceptInvitationResponse,
    summary="Aceita um convite de equipe de projeto (usuário autenticado)",
)
@router.post(
    "/projects/invitations/{code}/aceitar",
    response_model=AcceptInvitationResponse,
    include_in_schema=False,
)
async def aceitar_convite_equipe(
    code: str,
    usuario: UserModel = Depends(require_session),
    db: Session = Depends(get_db),
):
    """
    Aceita um convite RSAC-EQ-... para vincular o pesquisador autenticado
    à equipe do projeto de revisão.
    """
    codigo_limpo = code.strip().upper()
    convite = (
        db.query(ProjectInvitationModel)
        .filter(ProjectInvitationModel.code == codigo_limpo)
        .with_for_update()
        .first()
    )

    if not convite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite de equipe não encontrado. Verifique o código informado.",
        )

    if convite.revoked_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este convite de equipe foi revogado pela coordenação do projeto.",
        )

    agora = utcnow()
    expira = as_utc(convite.expires_at)
    if expira and expira < agora:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este convite de equipe expirou.",
        )

    project = db.query(ProjectModel).filter(ProjectModel.id == convite.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O projeto associado a este convite não existe ou foi excluído.",
        )

    # 1. Verificar se o usuário já é membro do projeto
    membro_existente = (
        db.query(ProjectMemberModel)
        .filter(
            ProjectMemberModel.project_id == project.id,
            ProjectMemberModel.user_id == usuario.id,
        )
        .first()
    )

    if membro_existente and membro_existente.is_active:
        return AcceptInvitationResponse(
            status="already_member",
            project_id=project.id,
            project_title=project.title,
            project_role=membro_existente.project_role,
            message="Você já é membro ativo deste projeto.",
        )

    if convite.accepted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este convite de equipe já foi utilizado.",
        )

    # 2. Verificar limite de membros
    membros_ativos = (
        db.query(ProjectMemberModel)
        .filter(
            ProjectMemberModel.project_id == project.id,
            ProjectMemberModel.is_active == True,  # noqa: E712
        )
        .count()
    )
    if membros_ativos >= settings.max_members_per_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O projeto atingiu o limite de {settings.max_members_per_project} membros.",
        )

    if membro_existente:
        # Reativação de membro que havia saído
        membro_existente.is_active = True
        membro_existente.left_at = None
        membro_existente.project_role = convite.project_role
        membro_existente.joined_at = agora
        membro_existente.invited_by_user_id = convite.created_by_user_id
    else:
        novo_membro = ProjectMemberModel(
            project_id=project.id,
            user_id=usuario.id,
            project_role=convite.project_role,
            is_active=True,
            invited_by_user_id=convite.created_by_user_id,
            joined_at=agora,
        )
        db.add(novo_membro)

    # 3. Marcar convite como aceito
    convite.accepted_at = agora
    convite.accepted_by_user_id = usuario.id

    ropa_service.registrar(
        db,
        operation="team_membership_created",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Inclusão de novo membro na equipe do projeto de revisão sistemática",
        data_categories=["identificacao"],
        user_id=usuario.id,
        commit=False,
    )
    db.commit()

    logger.info(
        "[Equipe] Usuário %s aceitou o convite %s e ingressou no projeto %s como %s",
        usuario.username,
        convite.code,
        project.id,
        convite.project_role,
    )

    await ws_manager.broadcast(
        project.id,
        {
            "type": "equipe.alterada",
            "user_id": usuario.id,
            "acao": "membro_ingressou",
            "por": usuario.username,
        },
    )

    return AcceptInvitationResponse(
        status="accepted",
        project_id=project.id,
        project_title=project.title,
        project_role=convite.project_role,
        message=f"Você ingressou com sucesso na revisão '{project.title}' como {convite.project_role}.",
    )
