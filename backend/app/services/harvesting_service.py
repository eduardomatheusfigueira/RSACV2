#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço Orquestrador de Coleta (Harvesting Service).
Coordena a execução concorrente de múltiplos coletores científicos com:
  - Resolução de credenciais do banco
  - Resolução de filtros de busca do protocolo (anos, idiomas, tipos)
  - Concorrência limitada via semáforo (até 3 fontes simultâneas)
  - Persistência em lote fora do event loop (batch dedup)
  - Stream de progresso e lotes via WebSockets
  - Suporte completo a cancelamento
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from fastapi import WebSocket

from app.database import SessionLocal
from app.harvesters.base import (
    HarvestProgress,
    HarvestQuery,
    RawPaperRecord,
)
from app.harvesters.factory import HarvesterFactory
from app.infrastructure.persistence.models import (
    HarvestRunModel,
    ProtocolModel,
    SourceCredentialModel,
)
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
            for ws in list(self.active_connections[project_id]):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.add(ws)
            for d in dead:
                self.active_connections[project_id].discard(d)


ws_manager = ConnectionManager()


class HarvestingService:
    """Orquestrador de coleta com processamento concorrente e deduplicação em lote."""

    def __init__(self):
        self.dedup_service = DeduplicationService()
        self._source_semaphore = asyncio.Semaphore(3)  # Máximo de 3 fontes em paralelo

    def _load_credentials(self, db) -> Dict[str, dict]:
        """Carrega credenciais de API salvas para cada fonte."""
        creds = {}
        try:
            records = db.query(SourceCredentialModel).all()
            for r in records:
                creds[r.source_name.upper()] = {
                    "api_key": r.api_key,
                    "inst_token": r.inst_token,
                    "custom_endpoint": r.custom_endpoint,
                }
        except Exception as e:
            logger.warning(f"[Harvesting] Aviso ao carregar credenciais: {e}")
        return creds

    async def _harvest_single_source(
        self,
        project_id: str,
        source_name: str,
        query: HarvestQuery,
        creds: dict,
    ):
        """Executa a coleta de uma fonte individual com persistência em lote."""
        async with self._source_semaphore:
            db = SessionLocal()
            run = HarvestRunModel(
                project_id=project_id,
                source_name=source_name,
                descriptors_used=json.dumps(query.descriptors, ensure_ascii=False),
                query_parameters=json.dumps(
                    {
                        "year_start": query.year_start,
                        "year_end": query.year_end,
                        "languages": query.languages,
                        "document_types": query.document_types,
                        "max_records": query.max_records_per_descriptor,
                    },
                    ensure_ascii=False,
                ),
                started_at=datetime.now(timezone.utc),
                status="running",
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = run.id
            db.close()

            found_count = 0
            new_count = 0
            dup_count = 0

            try:
                source_creds = creds.get(source_name.upper(), {})
                harvester = HarvesterFactory.get_harvester(
                    source=source_name,
                    api_key=source_creds.get("api_key") or None,
                    inst_token=source_creds.get("inst_token") or None,
                    custom_endpoint=source_creds.get("custom_endpoint") or None,
                )

                async def on_progress_callback(prog: HarvestProgress):
                    await ws_manager.broadcast(
                        project_id,
                        {
                            "type": "harvest_progress",
                            "run_id": run_id,
                            "source": source_name,
                            "descriptor": prog.current_descriptor,
                            "page": prog.page,
                            "total_found": prog.total_found_so_far,
                            "phase": prog.phase,
                            "is_complete": prog.is_complete,
                            "error": prog.error,
                        },
                    )

                # Coletar em lotes de 25 registros para evitar fsync O(N^2)
                batch_records: List[RawPaperRecord] = []

                def _persist_batch_sync(records: List[RawPaperRecord]):
                    session = SessionLocal()
                    try:
                        n_c, d_c, summaries = self.dedup_service.process_batch(
                            session, project_id, records
                        )
                        return n_c, d_c, summaries
                    finally:
                        session.close()

                async for raw_record in harvester.harvest(query=query, on_progress=on_progress_callback):
                    found_count += 1
                    batch_records.append(raw_record)

                    if len(batch_records) >= 25:
                        batch_to_process = list(batch_records)
                        batch_records.clear()

                        b_new, b_dup, summaries = await asyncio.to_thread(
                            _persist_batch_sync, batch_to_process
                        )
                        new_count += b_new
                        dup_count += b_dup

                        # Emitir atualização em lote
                        last_items = [
                            {"paper_id": pid, "title": t, "is_new": is_n}
                            for pid, t, is_n in summaries[-5:]
                        ]
                        await ws_manager.broadcast(
                            project_id,
                            {
                                "type": "paper_harvested",
                                "run_id": run_id,
                                "source": source_name,
                                "total_found": found_count,
                                "total_new": new_count,
                                "total_duplicate": dup_count,
                                "recent_items": last_items,
                            },
                        )

                # Processar lote remanescente
                if batch_records:
                    b_new, b_dup, summaries = await asyncio.to_thread(
                        _persist_batch_sync, batch_records
                    )
                    new_count += b_new
                    dup_count += b_dup

                # Concluir run com sucesso
                db = SessionLocal()
                run_obj = db.query(HarvestRunModel).filter(HarvestRunModel.id == run_id).first()
                if run_obj:
                    run_obj.status = "completed"
                    run_obj.completed_at = datetime.now(timezone.utc)
                    run_obj.records_found = found_count
                    run_obj.records_new = new_count
                    run_obj.records_duplicate = dup_count
                    db.commit()
                db.close()

                await ws_manager.broadcast(
                    project_id,
                    {
                        "type": "harvest_source_completed",
                        "run_id": run_id,
                        "source": source_name,
                        "records_found": found_count,
                        "records_new": new_count,
                        "records_duplicate": dup_count,
                    },
                )

            except asyncio.CancelledError:
                logger.info(f"[Harvesting] Coleta da fonte {source_name} cancelada.")
                db = SessionLocal()
                run_obj = db.query(HarvestRunModel).filter(HarvestRunModel.id == run_id).first()
                if run_obj:
                    run_obj.status = "cancelled"
                    run_obj.completed_at = datetime.now(timezone.utc)
                    run_obj.error_message = "Cancelada pelo usuário."
                    run_obj.records_found = found_count
                    run_obj.records_new = new_count
                    run_obj.records_duplicate = dup_count
                    db.commit()
                db.close()
                raise

            except Exception as e:
                logger.error(f"[Harvesting] Falha no coletor {source_name}: {e}")
                db = SessionLocal()
                run_obj = db.query(HarvestRunModel).filter(HarvestRunModel.id == run_id).first()
                if run_obj:
                    run_obj.status = "failed"
                    run_obj.error_message = str(e)
                    run_obj.completed_at = datetime.now(timezone.utc)
                    run_obj.records_found = found_count
                    run_obj.records_new = new_count
                    run_obj.records_duplicate = dup_count
                    db.commit()
                db.close()

                await ws_manager.broadcast(
                    project_id,
                    {
                        "type": "harvest_source_failed",
                        "run_id": run_id,
                        "source": source_name,
                        "error": str(e),
                    },
                )

    async def run_harvest(
        self,
        project_id: str,
        sources: List[str],
        max_records_per_descriptor: Optional[int] = None,
        custom_descriptors: Optional[List[str]] = None,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        languages: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None,
        fetch_details: bool = True,
    ):
        """Orquestra a coleta de múltiplos coletores em paralelo."""
        db = SessionLocal()
        try:
            protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
            if not protocol:
                logger.error(f"[Harvesting] Protocolo não encontrado para projeto {project_id}")
                return

            descriptors: List[str] = []
            if custom_descriptors:
                descriptors = [d.strip() for d in custom_descriptors if d.strip()]
            elif protocol.search_descriptors:
                try:
                    desc_dict = json.loads(protocol.search_descriptors)
                    for lang, pairs in desc_dict.items():
                        descriptors.extend([p.strip() for p in pairs if p.strip()])
                except Exception:
                    pass

            if not descriptors:
                logger.warning(f"[Harvesting] Nenhum descritor configurado para o projeto {project_id}")
                await ws_manager.broadcast(
                    project_id,
                    {
                        "type": "harvest_error",
                        "message": "Nenhum descritor de busca configurado no protocolo.",
                    },
                )
                return

            # Resolver filtros do protocolo
            proto_filters = {}
            if protocol.search_filters:
                try:
                    proto_filters = json.loads(protocol.search_filters)
                except Exception:
                    pass

            effective_year_start = year_start if year_start is not None else proto_filters.get("year_start")
            effective_year_end = year_end if year_end is not None else proto_filters.get("year_end")
            effective_languages = languages if languages is not None else proto_filters.get("languages", [])
            effective_doc_types = document_types if document_types is not None else proto_filters.get("document_types", [])

            harvest_query = HarvestQuery(
                descriptors=descriptors,
                year_start=effective_year_start,
                year_end=effective_year_end,
                languages=effective_languages,
                document_types=effective_doc_types,
                max_records_per_descriptor=max_records_per_descriptor,
                fetch_details=fetch_details,
            )

            creds = self._load_credentials(db)

        finally:
            db.close()

        logger.info(
            f"[Harvesting] Iniciando coleta paralela para projeto {project_id} nas fontes {sources} "
            f"com {len(descriptors)} descritores."
        )

        tasks = [
            self._harvest_single_source(project_id, s, harvest_query, creds)
            for s in sources
        ]

        # Execução concorrente de todas as fontes selecionadas
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"[Harvesting] Coleta finalizada para todas as fontes do projeto {project_id}.")
        await ws_manager.broadcast(
            project_id,
            {"type": "harvest_all_completed", "project_id": project_id},
        )
