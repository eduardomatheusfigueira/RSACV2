#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Router do feedback do beta.

Duas portas:
  * POST /feedback — qualquer pessoa com sessão envia um problema, uma
    sugestão, um elogio. O dono recebe um aviso por e-mail.
  * GET/PATCH/DELETE /feedback — a fila, só para o owner. É a mesma fila que o
    Gerenciador de Convites mostra, lida direto do banco.

O envio exige sessão como o resto da API (o router mora em `api_router`): o
botão existe dentro do aplicativo, e a conta é o que permite responder a quem
escreveu.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import FeedbackModel, UserModel, utcnow
from app.schemas.feedback import (
    FeedbackAck,
    FeedbackCreate,
    FeedbackItem,
    FeedbackListResponse,
    FeedbackUpdate,
)
from app.security.dependencies import require_owner, require_session
from app.services import feedback_admin, ropa_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])

# Teto por conta. O limite geral de taxa conta requisições por minuto; este
# conta mensagens por hora, que é o que enche a caixa de entrada do dono.
LIMITE_POR_HORA = 10


def _nome_do_autor(usuario: Optional[UserModel]) -> str:
    if not usuario:
        return ""
    return (usuario.full_name or usuario.display_name or usuario.username or "").strip()


def _serializar(f: FeedbackModel, autor: Optional[UserModel]) -> FeedbackItem:
    return FeedbackItem(
        id=f.id,
        tipo=f.tipo,
        mensagem=f.mensagem,
        pagina=f.pagina or "",
        navegador=f.navegador or "",
        versao=f.versao or "",
        status=f.status,
        created_at=f.created_at,
        responded_at=f.responded_at,
        admin_notes=f.admin_notes or "",
        autor_nome=_nome_do_autor(autor),
        autor_usuario=autor.username if autor else "",
        autor_email=(autor.email or "") if autor else "",
    )


@router.post(
    "",
    response_model=FeedbackAck,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar feedback do beta (qualquer usuário com sessão)",
)
def enviar_feedback(
    payload: FeedbackCreate,
    request: Request,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    agora = utcnow()

    recentes = (
        db.query(FeedbackModel)
        .filter(
            FeedbackModel.user_id == usuario.id,
            FeedbackModel.created_at >= agora - timedelta(hours=1),
        )
        .count()
    )
    if recentes >= LIMITE_POR_HORA:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Você já enviou vários feedbacks na última hora. Obrigado! "
                "Tente de novo daqui a pouco."
            ),
        )

    feedback = FeedbackModel(
        user_id=usuario.id,
        tipo=payload.tipo,
        mensagem=payload.mensagem,
        pagina=payload.pagina or "",
        navegador=(request.headers.get("user-agent") or "")[:300],
        versao=(settings.app_version or "")[:20],
        status="novo",
        created_at=agora,
    )
    db.add(feedback)
    db.commit()

    ropa_service.registrar(
        db,
        operation="feedback_received",
        legal_basis="art7_I_consentimento",
        purpose="Receber e responder feedback do beta enviado voluntariamente pelo titular",
        data_categories=["identificacao", "contato", "conexao"],
        user_id=usuario.id,
        commit=True,
    )

    logger.info("[Feedback] Novo feedback (%s) registrado (id=%s).", feedback.tipo, feedback.id)

    tarefas.add_task(
        feedback_admin.enviar_aviso_de_feedback,
        feedback_admin.DadosDoFeedback(
            id=feedback.id,
            tipo=feedback.tipo,
            mensagem=feedback.mensagem,
            pagina=feedback.pagina,
            navegador=feedback.navegador,
            versao=feedback.versao,
            autor_nome=_nome_do_autor(usuario),
            autor_usuario=usuario.username,
            autor_email=usuario.email or "",
            recebido_em=agora,
        ),
    )
    return FeedbackAck(
        received=True,
        message="Recebemos seu feedback. Obrigado por ajudar a melhorar o Revsist!",
    )


@router.get(
    "",
    response_model=FeedbackListResponse,
    summary="Listar feedbacks recebidos (apenas owner)",
)
def listar_feedbacks(
    status_filtro: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(require_owner),
):
    """Novos primeiro e, dentro de cada grupo, o mais recente na frente."""
    consulta = db.query(FeedbackModel, UserModel).outerjoin(
        UserModel, UserModel.id == FeedbackModel.user_id
    )
    if status_filtro:
        consulta = consulta.filter(FeedbackModel.status == status_filtro.strip().lower())

    linhas = consulta.order_by(FeedbackModel.created_at.desc()).all()
    itens = [_serializar(f, autor) for f, autor in linhas]
    itens.sort(key=lambda i: (i.status != "novo", -i.created_at.timestamp()))

    novos = db.query(FeedbackModel).filter(FeedbackModel.status == "novo").count()
    return FeedbackListResponse(items=itens, total=len(itens), novos=novos)


@router.patch(
    "/{feedback_id}",
    response_model=FeedbackItem,
    summary="Atualizar situação ou anotação de um feedback (apenas owner)",
)
def atualizar_feedback(
    feedback_id: str,
    payload: FeedbackUpdate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_owner),
):
    feedback = db.query(FeedbackModel).filter(FeedbackModel.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback não encontrado.")

    if payload.status is not None and payload.status != feedback.status:
        feedback.status = payload.status
        feedback.responded_at = utcnow() if payload.status != "novo" else None
    if payload.admin_notes is not None:
        feedback.admin_notes = payload.admin_notes.strip()

    db.commit()
    db.refresh(feedback)
    logger.info(
        "[Feedback] Feedback %s atualizado por '%s' (situação: %s).",
        feedback.id,
        admin.username,
        feedback.status,
    )
    autor = db.query(UserModel).filter(UserModel.id == feedback.user_id).first()
    return _serializar(feedback, autor)


@router.delete(
    "/{feedback_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir definitivamente um feedback (apenas owner)",
)
def excluir_feedback(
    feedback_id: str,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_owner),
):
    feedback = db.query(FeedbackModel).filter(FeedbackModel.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback não encontrado.")

    db.delete(feedback)
    db.commit()
    logger.info("[Feedback] Feedback %s excluído por '%s'.", feedback_id, admin.username)
