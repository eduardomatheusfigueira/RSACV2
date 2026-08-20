#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Coleta, Controle de Jobs e WebSockets de Progresso."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.harvesters.factory import HarvesterFactory
from app.infrastructure.persistence.models import (
    HarvestRunModel,
    ProjectModel,
    SourceCredentialModel,
)
from app.schemas.harvest import (
    HarvestRunListResponse,
    HarvestRunResponse,
    HarvestStartRequest,
)
from app.security.dependencies import (
    origem_do_websocket_e_permitida,
    require_websocket_session,
)
from app.services.harvest_job_manager import harvest_job_manager
from app.services.harvesting_service import HarvestingService, ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/harvest", tags=["harvest"])
harvesting_service = HarvestingService()


def _serialize_run(run: HarvestRunModel) -> HarvestRunResponse:
    try:
        descs = json.loads(run.descriptors_used) if run.descriptors_used else []
    except Exception:
        descs = []

    try:
        query_params = json.loads(run.query_parameters) if run.query_parameters else {}
    except Exception:
        query_params = {}

    return HarvestRunResponse(
        id=run.id,
        project_id=run.project_id,
        source_name=run.source_name,
        descriptors_used=descs,
        query_parameters=query_params,
        started_at=run.started_at,
        completed_at=run.completed_at,
        records_found=run.records_found,
        records_new=run.records_new,
        records_duplicate=run.records_duplicate,
        status=run.status,
        error_message=run.error_message,
    )


@router.post("", status_code=202)
async def start_harvest(
    project_id: str,
    data: HarvestStartRequest,
    db: Session = Depends(get_db),
):
    """Inicia a coleta assíncrona gerenciada nas fontes solicitadas."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")

    if harvest_job_manager.is_job_running(project_id):
        raise HTTPException(
            status_code=409,
            detail=f"Já existe uma coleta em andamento para o projeto '{project_id}'. Aguarde ou cancele a execução anterior.",
        )

    # Iniciar job assíncrono gerenciado
    harvest_job_manager.start_job(
        project_id=project_id,
        coro=harvesting_service.run_harvest(
            project_id=project_id,
            sources=data.sources,
            max_records_per_descriptor=data.max_records_per_descriptor,
            custom_descriptors=data.custom_descriptors,
            year_start=data.year_start,
            year_end=data.year_end,
            languages=data.languages,
            document_types=data.document_types,
            institutions=data.institutions,
            open_access_only=data.open_access_only,
            fetch_details=data.fetch_details,
        ),
        sources=data.sources,
    )

    return {
        "status": "started",
        "message": f"Coleta iniciada para {len(data.sources)} fonte(s) em segundo plano.",
        "project_id": project_id,
        "sources": data.sources,
    }


@router.post("/cancel")
async def cancel_harvest(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Cancela graciosamente a execução de coleta ativa para o projeto."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")

    cancelled = await harvest_job_manager.cancel_job(project_id)
    if not cancelled:
        return {"status": "not_running", "message": "Nenhuma coleta ativa encontrada para cancelar."}

    await ws_manager.broadcast(
        project_id,
        {"type": "harvest_cancelled", "project_id": project_id},
    )

    return {"status": "cancelled", "message": "Coleta cancelada com sucesso."}


@router.get("/status")
def get_harvest_status(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Retorna o estado atual da tarefa de coleta do projeto."""
    info = harvest_job_manager.get_job_info(project_id)
    if info:
        return info

    last_run = (
        db.query(HarvestRunModel)
        .filter(HarvestRunModel.project_id == project_id)
        .order_by(HarvestRunModel.started_at.desc())
        .first()
    )
    if last_run:
        return {
            "project_id": project_id,
            "status": last_run.status,
            "last_run_id": last_run.id,
            "completed_at": last_run.completed_at.isoformat() if last_run.completed_at else None,
        }

    return {"project_id": project_id, "status": "idle"}


@router.get("/runs", response_model=HarvestRunListResponse)
def list_harvest_runs(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Lista histórico de execuções de coleta do projeto."""
    runs = (
        db.query(HarvestRunModel)
        .filter(HarvestRunModel.project_id == project_id)
        .order_by(HarvestRunModel.started_at.desc())
        .all()
    )
    return HarvestRunListResponse(
        items=[_serialize_run(r) for r in runs],
        total=len(runs),
    )


@router.get("/sources")
def list_available_sources(db: Session = Depends(get_db)):
    """Retorna fontes suportadas para coleta com capacidades e status de credenciais."""
    sources_info = [
        {
            "id": "BDTD",
            "name": "Biblioteca Digital Brasileira de Teses e Dissertações (BDTD)",
            "description": "Teses e dissertações brasileiras (IBICT / VuFind)",
        },
        {
            "id": "SciELO",
            "name": "Scientific Electronic Library Online (SciELO)",
            "description": "Periódicos científicos da América Latina, Portugal e Espanha",
        },
        {
            "id": "OpenAlex",
            "name": "OpenAlex Global Scholarly Graph",
            "description": "Mais de 250M de publicações globais de todas as áreas do conhecimento",
        },
        {
            "id": "PubMed",
            "name": "PubMed (NCBI / MEDLINE)",
            "description": "Literatura biomédica, ciências da vida e ensaios clínicos",
        },
        {
            "id": "Scopus",
            "name": "Scopus (Elsevier)",
            "description": "Base multidisciplinar revisada por pares (requer API Key)",
        },
    ]

    saved_creds = {r.source_name.upper(): bool(r.api_key) for r in db.query(SourceCredentialModel).all()}

    result = []
    for s in sources_info:
        caps = HarvesterFactory.get_capabilities(s["id"])
        has_key = saved_creds.get(s["id"].upper(), False)
        enabled = (not caps.requires_api_key) or has_key

        result.append(
            {
                "id": s["id"],
                "name": s["name"],
                "description": s["description"],
                "enabled": enabled,
                "requires_api_key": caps.requires_api_key,
                "has_api_key": has_key,
                "supports_year_range": caps.supports_year_range,
                "supports_language": caps.supports_language,
                "supports_document_type": caps.supports_document_type,
                "supports_institution": caps.supports_institution,
                "supports_open_access": caps.supports_open_access,
                "supports_boolean_query": caps.supports_boolean_query,
                "max_native_filters": caps.max_native_filters,
                "default_page_size": caps.default_page_size,
            }
        )

    return {"sources": result}


@router.websocket("/ws")
async def harvest_websocket(
    project_id: str,
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """
    Canal WebSocket para streaming de progresso em tempo real da coleta.

    A sessão é conferida **antes** de `accept()`: a política de mesma origem
    não vale para WebSocket, então aceitar primeiro e checar depois já teria
    entregado o canal a quem abriu a conexão de outro sítio.
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
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
    except Exception:
        ws_manager.disconnect(project_id, websocket)
