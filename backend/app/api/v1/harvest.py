#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Coleta, Controle de Jobs e WebSockets de Progresso."""

import json
import logging
from datetime import timedelta

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


# Execuções iniciadas dentro desta janela pertencem à mesma leva de coleta.
_JANELA_DA_LEVA = timedelta(minutes=10)


@router.get("/status")
def get_harvest_status(
    project_id: str,
    db: Session = Depends(get_db),
):
    """
    Retorna o estado atual da coleta do projeto, por fonte.

    A interface consulta este endpoint em laço para saber quando a coleta
    terminou e quanto cada base trouxe. Antes a resposta não trazia
    `is_complete` nem `progress`, então o painel zerava a cada consulta e a
    tela ficava "coletando" para sempre — inclusive quando uma fonte havia
    falhado.
    """
    info = harvest_job_manager.get_job_info(project_id)
    em_execucao = info is not None

    runs = (
        db.query(HarvestRunModel)
        .filter(HarvestRunModel.project_id == project_id)
        .order_by(HarvestRunModel.started_at.desc())
        .limit(30)
        .all()
    )

    if not runs:
        return {
            "project_id": project_id,
            "status": "running" if em_execucao else "idle",
            "is_complete": not em_execucao,
            "sources": (info or {}).get("sources", []),
            "progress": {},
            "total_found": 0,
            "total_new": 0,
            "total_duplicate": 0,
        }

    # Recortar a leva mais recente (as execuções disparadas juntas)
    anchor = runs[0].started_at
    da_leva = [
        r for r in runs
        if r.started_at is not None and anchor is not None and (anchor - r.started_at) <= _JANELA_DA_LEVA
    ] or [runs[0]]

    progress: dict = {}
    for r in da_leva:
        if r.source_name in progress:
            continue  # a execução mais recente da fonte já foi considerada
        progress[r.source_name] = {
            "status": r.status,
            "run_id": r.id,
            "total_found": r.records_found or 0,
            "total_new": r.records_new or 0,
            "total_duplicate": r.records_duplicate or 0,
            "error": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }

    total_found = sum(p["total_found"] for p in progress.values())
    total_new = sum(p["total_new"] for p in progress.values())
    total_duplicate = sum(p["total_duplicate"] for p in progress.values())

    if em_execucao:
        status = "running"
    elif any(p["status"] == "failed" for p in progress.values()):
        status = "failed"
    elif any(p["status"] == "cancelled" for p in progress.values()):
        status = "cancelled"
    else:
        status = da_leva[0].status

    falhas = [
        f"{fonte}: {dados['error'] or 'falha não detalhada'}"
        for fonte, dados in progress.items()
        if dados["status"] == "failed"
    ]
    avisos = [
        f"{fonte}: {dados['error']}"
        for fonte, dados in progress.items()
        if dados["status"] == "completed" and dados["error"]
    ]

    return {
        "project_id": project_id,
        "status": status,
        "is_complete": not em_execucao,
        "sources": (info or {}).get("sources", list(progress.keys())),
        "started_at": (info or {}).get("started_at")
        or (da_leva[0].started_at.isoformat() if da_leva[0].started_at else None),
        "last_run_id": runs[0].id,
        "completed_at": runs[0].completed_at.isoformat() if runs[0].completed_at else None,
        "progress": progress,
        "total_found": total_found,
        "total_new": total_new,
        "total_duplicate": total_duplicate,
        "failures": falhas,
        "warnings": avisos,
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
