#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Coleta e WebSockets de Progresso."""

import asyncio
import json
import logging
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import HarvestRunModel, ProjectModel
from app.schemas.harvest import HarvestRunListResponse, HarvestRunResponse, HarvestStartRequest
from app.services.harvesting_service import HarvestingService, ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/harvest", tags=["harvest"])
harvesting_service = HarvestingService()


def _serialize_run(run: HarvestRunModel) -> HarvestRunResponse:
    try:
        descs = json.loads(run.descriptors_used) if run.descriptors_used else []
    except Exception:
        descs = []

    return HarvestRunResponse(
        id=run.id,
        project_id=run.project_id,
        source_name=run.source_name,
        descriptors_used=descs,
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Inicia a coleta em background nas fontes solicitadas."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")

    # Disparar coleta assíncrona em background task
    background_tasks.add_task(
        harvesting_service.run_harvest,
        project_id=project_id,
        sources=data.sources,
        max_records_per_descriptor=data.max_records_per_descriptor,
        custom_descriptors=data.custom_descriptors,
    )

    return {
        "status": "started",
        "message": f"Coleta iniciada para {len(data.sources)} fontes em segundo plano.",
        "project_id": project_id,
        "sources": data.sources,
    }


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
def list_available_sources():
    """Retorna fontes suportadas para coleta."""
    return {
        "sources": [
            {
                "id": "BDTD",
                "name": "Biblioteca Digital Brasileira de Teses e Dissertações (BDTD)",
                "description": "Teses e dissertações brasileiras (IBICT / VuFind)",
                "enabled": True,
            },
            {
                "id": "SciELO",
                "name": "Scientific Electronic Library Online (SciELO)",
                "description": "Periódicos científicos da América Latina, Portugal e Espanha",
                "enabled": True,
            },
            {
                "id": "OpenAlex",
                "name": "OpenAlex Global Scholarly Graph",
                "description": "Mais de 250M de publicações globais de todas as áreas do conhecimento",
                "enabled": True,
            },
            {
                "id": "PubMed",
                "name": "PubMed (NCBI / MEDLINE)",
                "description": "Literatura biomédica, ciências da vida e ensaios clínicos",
                "enabled": True,
            },
            {
                "id": "Scopus",
                "name": "Scopus (Elsevier)",
                "description": "Base multidisciplinar revisada por pares (requer API Key)",
                "enabled": False,
            },
        ]
    }


@router.websocket("/ws")
async def harvest_websocket(project_id: str, websocket: WebSocket):
    """Canal WebSocket para streaming de progresso em tempo real da coleta."""
    await ws_manager.connect(project_id, websocket)
    try:
        while True:
            # Manter conexão viva recebendo pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
    except Exception:
        ws_manager.disconnect(project_id, websocket)
