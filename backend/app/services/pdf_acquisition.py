#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Orquestração da Aquisição de PDFs sobre o banco de dados.

Faz a ponte entre o `PDFService` (que não conhece ORM) e o modelo `PaperModel`:
monta os identificadores do trabalho, dispara a busca multi-estratégia, grava a
procedência do arquivo e mantém o estado de execuções em lote.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import PaperModel
from app.services.pdf_resolver import HTML_HEADERS, PaperRef
from app.services.pdf_service import PDFAcquisition, PDFService
from app.services import ropa_service

logger = logging.getLogger(__name__)


def build_paper_ref(paper: PaperModel) -> PaperRef:
    """Reúne tudo que o trabalho oferece como pista para localizar o arquivo."""
    landing: list[str] = []
    for source in paper.sources or []:
        source_url = getattr(source, "source_url", "") or ""
        if source_url:
            landing.append(source_url)
            continue
        # Reconstrói a landing page a partir do identificador da base — é o que
        # abre as vias PMC/Europe PMC para registros vindos do PubMed.
        derived = _landing_from_source(source.source_name, source.source_id)
        if derived:
            landing.append(derived)

    return PaperRef(
        title=paper.title or "",
        doi=paper.doi,
        download_url=paper.download_url or "",
        source_name=paper.sources[0].source_name if paper.sources else "",
        landing_urls=landing,
    )


def _landing_from_source(source_name: str, source_id: str) -> str:
    """Deriva a URL do registro na base a partir do identificador coletado."""
    name = (source_name or "").strip().upper()
    ident = (source_id or "").strip()
    if not ident:
        return ""
    if name == "PUBMED" and ident.isdigit():
        return f"https://pubmed.ncbi.nlm.nih.gov/{ident}/"
    if name == "OPENALEX":
        return f"https://openalex.org/{ident.replace('https://openalex.org/', '')}"
    return ""


def apply_acquisition(
    paper: PaperModel,
    result: PDFAcquisition,
    kind: str = "obtido",
) -> None:
    """Grava no trabalho o resultado da aquisição (sucesso ou falha)."""
    paper.pdf_attempts = result.attempts_json()

    if not result.success:
        paper.pdf_status = "falhou"
        return

    paper.pdf_path = result.file_path
    paper.pdf_status = kind
    paper.pdf_resolved_url = result.resolved_url
    paper.pdf_strategy = result.strategy
    paper.pdf_page_count = result.page_count
    paper.pdf_size_bytes = result.size_bytes
    paper.pdf_sha256 = result.sha256
    paper.pdf_text_chars = result.text_chars
    paper.pdf_is_scanned = result.is_scanned
    paper.pdf_text_extracted = result.text_chars > 0
    paper.pdf_acquired_at = datetime.now(timezone.utc)


def clear_pdf_state(paper: PaperModel) -> None:
    """Zera a procedência ao desvincular o arquivo."""
    paper.pdf_path = None
    paper.pdf_text_extracted = False
    paper.pdf_status = "ausente"
    paper.pdf_resolved_url = ""
    paper.pdf_strategy = ""
    paper.pdf_page_count = 0
    paper.pdf_size_bytes = 0
    paper.pdf_sha256 = ""
    paper.pdf_text_chars = 0
    paper.pdf_is_scanned = False
    paper.pdf_acquired_at = None


async def acquire_for_paper(
    db: Session,
    paper: PaperModel,
    pdf_service: Optional[PDFService] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> PDFAcquisition:
    """Busca o PDF de um trabalho e persiste o resultado."""
    service = pdf_service or PDFService()
    result = await service.acquire_pdf(
        paper.project_id, paper.id, build_paper_ref(paper), client=client
    )
    apply_acquisition(paper, result)

    if result.success:
        owner_id = paper.project.owner_id if paper.project else None
        ropa_service.registrar(
            db,
            operation="pdf_fetch",
            legal_basis="art7_V_execucao_de_contrato",
            purpose="Obtenção de texto completo de artigo científico em acesso aberto",
            data_categories=["documento", "referencia_bibliografica"],
            user_id=owner_id,
            recipient=result.strategy or "open_access_repository",
            international=True,
            commit=False,
        )

    db.commit()
    return result


# ─────────────────────────────────────────────────────────────────────
# Aquisição em lote
# ─────────────────────────────────────────────────────────────────────

class BatchState:
    """Estado observável de uma execução em lote por projeto."""

    def __init__(self, project_id: str, total: int):
        self.project_id = project_id
        self.total = total
        self.processed = 0
        self.succeeded = 0
        self.failed = 0
        self.status = "running"  # running | done | cancelled | error
        self.current_title = ""
        self.started_at = datetime.now(timezone.utc)
        self.finished_at: Optional[datetime] = None
        self.results: list[dict] = []
        self.error_message = ""

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "total": self.total,
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "current_title": self.current_title,
            "progress_percent": round(self.processed / self.total * 100, 1) if self.total else 0.0,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error_message": self.error_message,
            "results": self.results,
        }


class PDFBatchManager:
    """
    Executa a busca de PDFs de vários trabalhos com concorrência limitada.

    Concorrência limitada é requisito, não detalhe: as APIs de acesso aberto
    (Unpaywall, Crossref, OpenAlex) aplicam limite por origem, e um repositório
    institucional pequeno derruba a conexão se receber 30 requisições de uma vez.
    """

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._states: dict[str, BatchState] = {}

    def is_running(self, project_id: str) -> bool:
        task = self._tasks.get(project_id)
        return task is not None and not task.done()

    def get_state(self, project_id: str) -> Optional[BatchState]:
        return self._states.get(project_id)

    def cancel(self, project_id: str) -> bool:
        task = self._tasks.get(project_id)
        if task and not task.done():
            task.cancel()
            state = self._states.get(project_id)
            if state:
                state.status = "cancelled"
                state.finished_at = datetime.now(timezone.utc)
            return True
        return False

    def start(
        self,
        project_id: str,
        paper_ids: list[str],
        session_factory,
        pdf_service: Optional[PDFService] = None,
    ) -> BatchState:
        if self.is_running(project_id):
            raise RuntimeError("Já existe uma busca de PDFs em andamento para este projeto.")

        state = BatchState(project_id, len(paper_ids))
        self._states[project_id] = state
        task = asyncio.create_task(
            self._run(state, paper_ids, session_factory, pdf_service or PDFService())
        )
        self._tasks[project_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(project_id, None))
        return state

    async def _run(
        self,
        state: BatchState,
        paper_ids: list[str],
        session_factory,
        pdf_service: PDFService,
    ) -> None:
        semaphore = asyncio.Semaphore(max(1, settings.pdf_batch_concurrency))
        lock = asyncio.Lock()

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.pdf_request_timeout, connect=10.0),
            follow_redirects=True,
            headers=HTML_HEADERS,
        ) as client:

            async def process(paper_id: str) -> None:
                async with semaphore:
                    db = session_factory()
                    try:
                        paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
                        if not paper:
                            return
                        async with lock:
                            state.current_title = (paper.title or "")[:120]

                        result = await pdf_service.acquire_pdf(
                            paper.project_id, paper.id, build_paper_ref(paper), client=client
                        )
                        apply_acquisition(paper, result)
                        db.commit()

                        async with lock:
                            state.processed += 1
                            if result.success:
                                state.succeeded += 1
                            else:
                                state.failed += 1
                            state.results.append(
                                {
                                    "paper_id": paper.id,
                                    "title": (paper.title or "")[:160],
                                    "success": result.success,
                                    "strategy": result.strategy,
                                    "message": result.message,
                                    "attempts": len(result.attempts),
                                }
                            )
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:  # noqa: BLE001 — um item não derruba o lote
                        logger.error("[PDFBatch] Falha ao processar %s: %s", paper_id, exc)
                        async with lock:
                            state.processed += 1
                            state.failed += 1
                            state.results.append(
                                {
                                    "paper_id": paper_id,
                                    "title": "",
                                    "success": False,
                                    "strategy": "",
                                    "message": f"Erro interno: {exc}",
                                    "attempts": 0,
                                }
                            )
                    finally:
                        db.close()

            try:
                await asyncio.gather(*(process(pid) for pid in paper_ids))
                state.status = "done"
            except asyncio.CancelledError:
                state.status = "cancelled"
                raise
            except Exception as exc:  # noqa: BLE001
                state.status = "error"
                state.error_message = str(exc)
                logger.error("[PDFBatch] Lote interrompido: %s", exc)
            finally:
                state.finished_at = datetime.now(timezone.utc)
                state.current_title = ""


pdf_batch_manager = PDFBatchManager()
