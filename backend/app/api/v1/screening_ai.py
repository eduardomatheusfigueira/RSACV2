#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Triagem com IA (Individual e Batch)."""

import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import AISettingsModel, ProjectModel, UserModel
from app.schemas.ai import BatchScreeningRequest
from app.security.dependencies import (
    origem_do_websocket_e_permitida,
    require_session,
    require_websocket_session,
)
from app.security.middleware import erro_interno
from app.services.harvesting_service import ws_manager
from app.services.screening_service import AuditActor, ScreeningService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/screening/ai", tags=["screening_ai"])
screening_service = ScreeningService()


def _check_ai_enabled(db: Session):
    settings = db.query(AISettingsModel).first()
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de IA estão desativados nas Configurações (Modo 100% Manual).",
        )


@router.post("/single/{paper_id}")
async def screen_single_paper(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Executa a triagem com IA para um único artigo e retorna a decisão estruturada."""
    _check_ai_enabled(db)
    ator = AuditActor(user_id=usuario.id, username=usuario.username)
    try:
        result = await screening_service.screen_single_paper(
            db, project_id, paper_id, actor=ator
        )
        return {
            "status": "success",
            "paper_id": paper_id,
            "decision": result.decision,
            "confidence": result.confidence,
            "justification": result.justification,
            "inclusion_criteria": result.inclusion_criteria,
            "exclusion_criteria": result.exclusion_criteria,
            "model_used": result.model_used,
            "provider": result.provider,
        }
    except Exception as e:
        mensagem, _ = erro_interno(
            "Falha ao executar a triagem assistida.", e,
            contexto=f"[ScreeningAI] triagem do paper {paper_id}",
        )
        raise HTTPException(status_code=500, detail=mensagem) from e


@router.post("/batch", status_code=202)
async def start_batch_screening(
    project_id: str,
    data: BatchScreeningRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Inicia a triagem em lote de artigos pendentes em segundo plano."""
    _check_ai_enabled(db)
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")

    background_tasks.add_task(
        screening_service.run_batch_screening,
        project_id,
        limit=data.limit,
        concurrency=data.concurrency,
        actor=AuditActor(user_id=usuario.id, username=usuario.username),
    )

    return {
        "status": "started",
        "message": f"Triagem em lote de até {data.limit} artigos pendentes iniciada.",
    }


@router.websocket("/ws")
async def screening_websocket(
    websocket: WebSocket,
    project_id: str,
    db: Session = Depends(get_db),
):
    """
    Canal WebSocket para streaming de progresso em tempo real da triagem.

    Mesma regra do canal de coleta: sessão conferida antes de `accept()`.
    """
    # `Origin` antes da sessão: sem essa checagem, o cookie do pesquisador
    # abriria o canal para qualquer página aberta no navegador dele (§29.3.6).
    if not origem_do_websocket_e_permitida(websocket):
        await websocket.close(code=1008, reason="Origem não autorizada.")
        return

    usuario = await require_websocket_session(websocket, db)
    if not usuario:
        await websocket.close(code=1008, reason="Autenticação necessária.")
        return

    await ws_manager.connect(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
    except Exception as e:
        logger.warning(f"[WebSocket Screening] Conexão encerrada: {e}")
        ws_manager.disconnect(project_id, websocket)
