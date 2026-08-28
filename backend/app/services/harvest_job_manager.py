#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Harvest Job Manager.
Gerencia o ciclo de vida de tarefas assíncronas de coleta, concorrência por projeto,
cancelamento gracioso e prevenção de sobreposição de execuções.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Coroutine, Dict, Optional

from app.database import SessionLocal
from app.infrastructure.persistence.models import HarvestRunModel

logger = logging.getLogger(__name__)


class HarvestJobManager:
    """Gerenciador centralizado de tarefas de coleta ativas."""

    def __init__(self):
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_metadata: Dict[str, dict] = {}

    def is_job_running(self, project_id: str) -> bool:
        """Verifica se existe uma coleta ativa em andamento para o projeto."""
        task = self._active_tasks.get(project_id)
        return task is not None and not task.done()

    def start_job(
        self,
        project_id: str,
        coro: Coroutine,
        sources: list[str],
    ) -> asyncio.Task:
        """Inicia uma nova tarefa assíncrona de coleta para o projeto."""
        if self.is_job_running(project_id):
            raise RuntimeError(f"Já existe uma coleta em andamento para o projeto '{project_id}'.")

        task = asyncio.create_task(coro)
        self._active_tasks[project_id] = task
        self._task_metadata[project_id] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "sources": sources,
        }

        def _cleanup_callback(t: asyncio.Task):
            self._active_tasks.pop(project_id, None)
            self._task_metadata.pop(project_id, None)
            if t.cancelled():
                logger.info(f"[JobManager] Coleta para projeto {project_id} cancelada com sucesso.")
            elif t.exception():
                logger.error(f"[JobManager] Coleta para projeto {project_id} encerrou com erro: {t.exception()}")
            else:
                logger.info(f"[JobManager] Coleta para projeto {project_id} finalizada com sucesso.")

        task.add_done_callback(_cleanup_callback)
        return task

    async def cancel_job(self, project_id: str) -> bool:
        """Cancela graciosamente a coleta ativa do projeto e atualiza o banco de dados."""
        task = self._active_tasks.get(project_id)
        if not task or task.done():
            return False

        logger.info(f"[JobManager] Solicitando cancelamento da coleta para projeto {project_id}...")
        task.cancel()

        # Atualizar status das runs no banco
        try:
            db = SessionLocal()
            runs = (
                db.query(HarvestRunModel)
                .filter(
                    HarvestRunModel.project_id == project_id,
                    HarvestRunModel.status == "running",
                )
                .all()
            )
            for r in runs:
                r.status = "cancelled"
                r.completed_at = datetime.now(timezone.utc)
                r.error_message = "Coleta cancelada pelo usuário."
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"[JobManager] Erro ao marcar runs como canceladas: {e}")

        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
            pass

        return True

    def get_job_info(self, project_id: str) -> Optional[dict]:
        """Retorna informações da tarefa em execução."""
        if not self.is_job_running(project_id):
            return None
        meta = self._task_metadata.get(project_id, {})
        return {
            "project_id": project_id,
            "status": "running",
            "started_at": meta.get("started_at"),
            "sources": meta.get("sources", []),
        }


# Instância global singleton do gerenciador de jobs
harvest_job_manager = HarvestJobManager()
