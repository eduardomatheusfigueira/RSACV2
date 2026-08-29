#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Harvest Job Manager.
Ciclo de vida das tarefas de coleta: concorrência por projeto, cancelamento
gracioso e prevenção de sobreposição de execuções.
"""

import logging
from datetime import datetime, timezone

from app.database import SessionLocal
from app.infrastructure.persistence.models import HarvestRunModel
from app.services.job_manager import AsyncJobManager

logger = logging.getLogger(__name__)


class HarvestJobManager(AsyncJobManager):
    """Gerenciador das coletas ativas."""

    def __init__(self):
        super().__init__("uma coleta")

    async def _ao_cancelar(self, project_id: str) -> None:
        """
        Fecha no banco as execuções que ficariam `running` para sempre.

        A tarefa é interrompida no meio; sem esta marcação, a próxima abertura
        da tela de coleta mostraria uma execução eternamente em andamento.
        """
        try:
            db = SessionLocal()
            try:
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
            finally:
                db.close()
        except Exception as e:
            logger.error(f"[JobManager] Erro ao marcar runs como canceladas: {e}")


# Instância global singleton do gerenciador de jobs
harvest_job_manager = HarvestJobManager()
