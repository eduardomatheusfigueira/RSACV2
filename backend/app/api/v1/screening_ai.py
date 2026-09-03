#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Router de Triagem com IA (Individual e Batch)."""

import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    AISettingsModel,
    ProjectMemberModel,
    ProjectModel,
    UserModel,
)
from app.schemas.ai import BatchScreeningRequest
from app.security.dependencies import (
    exige_revisor_ou_coordenador,
    origem_do_websocket_e_permitida,
    projeto_do_usuario,
    require_session,
    require_websocket_session,
    verificar_projeto_do_usuario,
)
from app.security.middleware import erro_interno
from app.services.harvesting_service import ws_manager
from app.services.job_manager import AsyncJobManager
from app.services.screening_service import AuditActor, ScreeningService

logger = logging.getLogger(__name__)

# A titularidade entra como dependência do router, e não rota a rota (doc 40
# §40.3.2): é o mesmo padrão de `require_session`, e é o que faz uma rota
# nova nascer isolada sem depender de ninguém lembrar.
router = APIRouter(
    prefix="/projects/{project_id}/screening/ai",
    dependencies=[Depends(projeto_do_usuario)],
    tags=["screening_ai"],
)
screening_service = ScreeningService()

# A triagem em lote deixou de ser um `BackgroundTasks` do FastAPI: aquilo não
# tem alça, e sem alça não há como parar. Guardada como `asyncio.Task` no
# gerenciador, a execução pode ser interrompida — e duas triagens do mesmo
# acervo deixam de correr sobrepostas, queimando cota do provedor em dobro.
batch_job_manager = AsyncJobManager("uma triagem em lote")


def _check_ai_enabled(db: Session, user_id: Optional[str] = None):
    if not user_id:
        return
    settings = db.query(AISettingsModel).filter(AISettingsModel.user_id == user_id).first()
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de Assistência estão desativados nas suas Configurações (Modo 100% Manual).",
        )


@router.post("/single/{paper_id}")
async def screen_single_paper(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_revisor_ou_coordenador),
):
    """Executa a triagem com IA para um único artigo e retorna a decisão estruturada."""
    _check_ai_enabled(db, user_id=usuario.id)
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
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_revisor_ou_coordenador),
):
    """Inicia a triagem em lote de artigos pendentes em segundo plano."""
    _check_ai_enabled(db, user_id=usuario.id)
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")

    if batch_job_manager.is_job_running(project_id):
        raise HTTPException(
            status_code=409,
            detail=(
                "Já existe uma triagem em lote em andamento neste projeto. "
                "Aguarde o término ou pare a execução atual."
            ),
        )

    batch_job_manager.start_job(
        project_id,
        screening_service.run_batch_screening(
            project_id,
            limit=data.limit,
            concurrency=data.concurrency,
            pausa_entre_estudos=data.pausa_entre_estudos,
            actor=AuditActor(user_id=usuario.id, username=usuario.username),
        ),
        limit=data.limit,
        concurrency=data.concurrency,
        pausa_entre_estudos=data.pausa_entre_estudos,
    )

    return {
        "status": "started",
        "message": f"Triagem em lote de até {data.limit} artigos pendentes iniciada.",
    }


@router.post("/batch/cancel")
async def cancel_batch_screening(
    project_id: str,
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_revisor_ou_coordenador),
):
    """Interrompe a triagem em lote em andamento no projeto."""
    # Os contadores são lidos antes do cancelamento: o `finally` da tarefa os
    # descarta, e é justamente o parcial que interessa relatar a quem parou.
    parcial = screening_service.get_batch_state(project_id) or {}

    cancelado = await batch_job_manager.cancel_job(project_id)
    if not cancelado:
        return {
            "status": "not_running",
            "message": "Nenhuma triagem em lote ativa para interromper.",
        }

    await ws_manager.broadcast(
        project_id,
        {
            "type": "batch_screening_cancelled",
            "message": "Triagem em lote interrompida pelo pesquisador.",
            "processed": parcial.get("processed", 0),
            "total": parcial.get("total", 0),
            "included": parcial.get("included", 0),
            "excluded": parcial.get("excluded", 0),
        },
    )

    return {"status": "cancelled", "message": "Triagem em lote interrompida."}


@router.get("/batch/status")
def get_batch_screening_status(project_id: str):
    """
    Situação da triagem em lote do projeto.

    Existe para a tela se recompor: recarregar a página no meio de um lote
    apagava a barra de progresso e o botão de parar, embora a triagem seguisse
    correndo no servidor.
    """
    if not batch_job_manager.is_job_running(project_id):
        # Sem lote correndo, devolve o DESFECHO do último — não `None`. Quem
        # acompanha pela consulta periódica descobre o fim justamente por esta
        # resposta, e um `null` aqui deixava a tela congelada no penúltimo
        # estudo, como se o último tivesse travado.
        return {
            "is_running": False,
            "progress": screening_service.get_batch_state(project_id),
            "ouvintes_do_canal": len(ws_manager.active_connections.get(project_id, ())),
        }

    return {
        "is_running": True,
        "progress": screening_service.get_batch_state(project_id),
        "job": batch_job_manager.get_job_info(project_id),
        # Quantas telas estão de fato escutando o canal deste projeto. Sem este
        # número não há como distinguir "o lote não anda" de "o lote anda e
        # ninguém está ouvindo" — que foram dois problemas diferentes com o
        # mesmo sintoma: a barra parada em 0%.
        "ouvintes_do_canal": len(ws_manager.active_connections.get(project_id, ())),
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

    # A dependência de titularidade do router não alcança o WebSocket — lá não
    # há requisição HTTP para responder com 404. Sem esta verificação, quem
    # tivesse qualquer sessão válida acompanharia a coleta e a triagem de
    # outro assinante apenas conhecendo o identificador do projeto.
    if not verificar_projeto_do_usuario(db, project_id, usuario):
        await websocket.close(code=1008, reason="Projeto não encontrado.")
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
