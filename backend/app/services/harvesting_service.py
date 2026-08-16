#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço Orquestrador de Coleta (Harvesting Service).
Coordena a execução concorrente ou sequencial de múltiplos coletores,
comunicação de progresso via WebSockets e deduplicação automática.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Set
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.harvesters.base import HarvestProgress
from app.harvesters.factory import HarvesterFactory
from app.infrastructure.persistence.models import HarvestRunModel, ProjectModel, ProtocolModel
from app.services.dedup_service import DeduplicationService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerenciador de conexões WebSocket para stream de progresso."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()
        self.active_connections[project_id].add(websocket)

    def disconnect(self, project_id: str, websocket: WebSocket):
        if project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast(self, project_id: str, message: dict):
        if project_id in self.active_connections:
            dead = set()
            for ws in self.active_connections[project_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.add(ws)
            for d in dead:
                self.active_connections[project_id].discard(d)


ws_manager = ConnectionManager()


class HarvestingService:
    """Orquestrador de coleta com deduplicação em tempo real."""

    def __init__(self):
        self.dedup_service = DeduplicationService()

    async def run_harvest(
        self,
        project_id: str,
        sources: List[str],
        max_records_per_descriptor: int = 100,
        custom_descriptors: Optional[List[str]] = None,
    ):
        """Executa a coleta para as fontes selecionadas."""
        db = SessionLocal()
        try:
            protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
            if not protocol:
                logger.error(f"[Harvesting] Protocolo não encontrado para projeto {project_id}")
                return

            # Obter descritores
            descriptors: List[str] = []
            if custom_descriptors:
                descriptors = custom_descriptors
            elif protocol.search_descriptors:
                try:
                    desc_dict = json.loads(protocol.search_descriptors)
                    for lang, pairs in desc_dict.items():
                        descriptors.extend(pairs)
                except Exception:
                    pass

            if not descriptors:
                logger.warning(f"[Harvesting] Nenhum descritor configurado para o projeto {project_id}")
                return

            logger.info(
                f"[Harvesting] Iniciando coleta para projeto {project_id} nas fontes {sources} com {len(descriptors)} descritores."
            )

            for source_name in sources:
                run = HarvestRunModel(
                    project_id=project_id,
                    source_name=source_name,
                    descriptors_used=json.dumps(descriptors, ensure_ascii=False),
                    started_at=datetime.now(timezone.utc),
                    status="running",
                )
                db.add(run)
                db.commit()
                db.refresh(run)

                try:
                    harvester = HarvesterFactory.get_harvester(source_name)

                    async def on_progress_callback(prog: HarvestProgress):
                        await ws_manager.broadcast(
                            project_id,
                            {
                                "type": "harvest_progress",
                                "run_id": run.id,
                                "source": source_name,
                                "descriptor": prog.current_descriptor,
                                "page": prog.page,
                                "total_found": prog.total_found_so_far,
                                "is_complete": prog.is_complete,
                                "error": prog.error,
                            },
                        )

                    found_count = 0
                    new_count = 0
                    dup_count = 0

                    async for raw_record in harvester.harvest(
                        descriptors=descriptors,
                        max_records_per_descriptor=max_records_per_descriptor,
                    ):
                        found_count += 1
                        _, is_new = self.dedup_service.process_record(db, project_id, raw_record)
                        if is_new:
                            new_count += 1
                        else:
                            dup_count += 1

                        # Notificar live a cada 5 papers ou em tempo real
                        await ws_manager.broadcast(
                            project_id,
                            {
                                "type": "paper_harvested",
                                "run_id": run.id,
                                "source": source_name,
                                "title": raw_record.title,
                                "is_new": is_new,
                                "total_found": found_count,
                                "total_new": new_count,
                                "total_duplicate": dup_count,
                            },
                        )

                    run.status = "completed"
                    run.completed_at = datetime.now(timezone.utc)
                    run.records_found = found_count
                    run.records_new = new_count
                    run.records_duplicate = dup_count
                    db.commit()

                    await ws_manager.broadcast(
                        project_id,
                        {
                            "type": "harvest_source_completed",
                            "run_id": run.id,
                            "source": source_name,
                            "records_found": found_count,
                            "records_new": new_count,
                            "records_duplicate": dup_count,
                        },
                    )

                except Exception as e:
                    logger.error(f"[Harvesting] Falha no coletor {source_name}: {e}")
                    run.status = "failed"
                    run.error_message = str(e)
                    run.completed_at = datetime.now(timezone.utc)
                    db.commit()

                    await ws_manager.broadcast(
                        project_id,
                        {
                            "type": "harvest_source_failed",
                            "run_id": run.id,
                            "source": source_name,
                            "error": str(e),
                        },
                    )

            logger.info(f"[Harvesting] Todas as fontes concluídas para o projeto {project_id}.")
            await ws_manager.broadcast(
                project_id,
                {"type": "harvest_all_completed", "project_id": project_id},
            )

        finally:
            db.close()
