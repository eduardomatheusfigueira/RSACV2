#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Ciclo de vida das tarefas longas.

Coleta, triagem em lote e aquisição de PDFs correm em segundo plano por
minutos. Enquanto a tarefa era um `BackgroundTasks` do FastAPI, não havia
como interrompê-la: o pesquisador que disparasse um lote errado — ou visse a
cota do provedor estourar — só tinha a opção de fechar o programa. Guardar a
`asyncio.Task` num registro por projeto é o que torna "parar" possível, e é
também o que impede duas execuções do mesmo tipo de se sobreporem no mesmo
acervo.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Coroutine, Dict, Optional

logger = logging.getLogger(__name__)


class AsyncJobManager:
    """Registro de tarefas ativas por projeto, com cancelamento gracioso."""

    def __init__(self, nome: str):
        self.nome = nome
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_metadata: Dict[str, dict] = {}

    def is_job_running(self, project_id: str) -> bool:
        """Existe tarefa ativa deste tipo para o projeto?"""
        task = self._active_tasks.get(project_id)
        return task is not None and not task.done()

    def start_job(self, project_id: str, coro: Coroutine, **metadata) -> asyncio.Task:
        """Registra e dispara a tarefa, recusando sobreposição no mesmo projeto."""
        if self.is_job_running(project_id):
            # Fechar a corrotina recusada evita o aviso de "coroutine was never
            # awaited", que polui o log justamente quando algo deu errado.
            coro.close()
            raise RuntimeError(
                f"Já existe {self.nome} em andamento para o projeto '{project_id}'."
            )

        task = asyncio.create_task(coro)
        self._active_tasks[project_id] = task
        self._task_metadata[project_id] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            **metadata,
        }

        def _cleanup_callback(t: asyncio.Task):
            self._active_tasks.pop(project_id, None)
            self._task_metadata.pop(project_id, None)
            if t.cancelled():
                logger.info(f"[JobManager] {self.nome} do projeto {project_id} cancelada.")
            elif t.exception():
                logger.error(
                    f"[JobManager] {self.nome} do projeto {project_id} encerrou com erro: {t.exception()}"
                )
            else:
                logger.info(f"[JobManager] {self.nome} do projeto {project_id} finalizada.")

        task.add_done_callback(_cleanup_callback)
        return task

    async def cancel_job(self, project_id: str) -> bool:
        """Cancela a tarefa ativa do projeto. Devolve `False` se não havia nenhuma."""
        task = self._active_tasks.get(project_id)
        if not task or task.done():
            return False

        logger.info(f"[JobManager] Cancelando {self.nome} do projeto {project_id}...")
        task.cancel()

        await self._ao_cancelar(project_id)

        # `shield` para que a espera não seja ela própria cancelada junto; o
        # limite existe porque uma tarefa presa numa chamada de rede não deve
        # segurar a resposta ao pesquisador que pediu para parar.
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        except Exception:
            pass

        return True

    async def _ao_cancelar(self, project_id: str) -> None:
        """Gancho para o registro específico de cada tipo de tarefa."""
        return None

    def get_job_info(self, project_id: str) -> Optional[dict]:
        """Metadados da tarefa em execução, ou `None` se não há nenhuma."""
        if not self.is_job_running(project_id):
            return None
        return {
            "project_id": project_id,
            "status": "running",
            **self._task_metadata.get(project_id, {}),
        }
