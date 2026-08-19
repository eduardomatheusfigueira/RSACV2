#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço de Triagem com Inteligência Artificial (Screening Service).
Executa a triagem automatizada (individual e em lote) com guardrails estritos
de zero alucinação e persistência de auditoria.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.domain.entities import Decision, Methodology, Paper, Protocol
from app.infrastructure.ai.base import BaseAIClient, ProtocolSuggestions, ScreeningResult
from app.infrastructure.ai.factory import AIFactory
from app.infrastructure.persistence.models import (
    AuditLogModel,
    CriterionModel,
    PaperCriterionModel,
    PaperModel,
    ProjectModel,
    ProtocolModel,
)
from app.services.harvesting_service import ws_manager

logger = logging.getLogger(__name__)


def _to_paper_entity(model: PaperModel) -> Paper:
    dec = Decision.PENDING
    if model.decision == "Incluído":
        dec = Decision.INCLUDED
    elif model.decision == "Excluído":
        dec = Decision.EXCLUDED

    return Paper(
        id=model.id,
        title=model.title,
        authors=model.authors or "",
        year=model.year or "",
        abstract=model.abstract or "",
        doi=model.doi,
        download_url=model.download_url or "",
        decision=dec,
        observations=model.observations or "",
        ai_confidence=model.ai_confidence,
    )


def _to_protocol_entity(model: ProtocolModel) -> Protocol:
    inc_criteria = [c.text for c in model.criteria if not c.is_exclusion]
    exc_criteria = [c.text for c in model.criteria if c.is_exclusion]
    questions = [q.text for q in model.extraction_questions]

    try:
        methodology = Methodology(model.project.methodology) if model.project else Methodology.PRISMA_P
    except Exception:
        methodology = Methodology.PRISMA_P

    return Protocol(
        title=model.project.title if model.project else "",
        objective=model.objective or "",
        methodology=methodology,
        inclusion_criteria=inc_criteria,
        exclusion_criteria=exc_criteria,
        extraction_questions=questions,
    )


class ScreeningService:
    """Serviço de Triagem com IA."""

    def __init__(self, ai_client: Optional[BaseAIClient] = None):
        self.ai_client = ai_client

    def _get_client(self, db: Session) -> BaseAIClient:
        if self.ai_client:
            return self.ai_client
        return AIFactory.get_client(db)

    async def screen_single_paper(
        self,
        db: Session,
        project_id: str,
        paper_id: str,
    ) -> ScreeningResult:
        """Executa a triagem com IA para um único artigo."""
        paper_model = (
            db.query(PaperModel)
            .filter(PaperModel.project_id == project_id, PaperModel.id == paper_id)
            .first()
        )
        if not paper_model:
            raise ValueError(f"Artigo '{paper_id}' não encontrado.")

        protocol_model = (
            db.query(ProtocolModel)
            .filter(ProtocolModel.project_id == project_id)
            .first()
        )
        if not protocol_model:
            raise ValueError(f"Protocolo do projeto '{project_id}' não encontrado.")

        paper_entity = _to_paper_entity(paper_model)
        protocol_entity = _to_protocol_entity(protocol_model)

        client = self._get_client(db)
        result = await client.analyze_screening(paper_entity, protocol_entity)

        # Atualizar banco de dados
        old_decision = paper_model.decision
        paper_model.decision = result.decision
        paper_model.ai_confidence = result.confidence

        # Salvar justificativa limpa diretamente nas observações (sem prefixo)
        just_entry = result.justification.strip() if result.justification else ""
        if just_entry:
            paper_model.observations = just_entry

        # Log de Auditoria
        audit = AuditLogModel(
            paper_id=paper_model.id,
            action="ai_screening",
            old_value=old_decision,
            new_value=result.decision,
            source=f"ai:{result.provider}",
        )
        db.add(audit)

        # Salvar avaliações de critérios mapeando por código (INC1, EXC1...) e por texto
        inc_criteria_list = [c for c in protocol_model.criteria if not c.is_exclusion]
        exc_criteria_list = [c for c in protocol_model.criteria if c.is_exclusion]

        inc_map = {f"INC{i}": c.id for i, c in enumerate(inc_criteria_list, 1)}
        exc_map = {f"EXC{i}": c.id for i, c in enumerate(exc_criteria_list, 1)}
        text_map = {c.text.lower().strip(): c.id for c in protocol_model.criteria}

        # 1. Critérios de Inclusão
        for key, val in (result.inclusion_criteria or {}).items():
            clean_k = str(key).strip().upper()
            crit_id = inc_map.get(clean_k) or text_map.get(str(key).lower().strip())
            if crit_id:
                bool_val = bool(val)
                eval_record = (
                    db.query(PaperCriterionModel)
                    .filter(
                        PaperCriterionModel.paper_id == paper_model.id,
                        PaperCriterionModel.criterion_id == crit_id,
                    )
                    .first()
                )
                if eval_record:
                    eval_record.value = bool_val
                else:
                    db.add(
                        PaperCriterionModel(
                            paper_id=paper_model.id,
                            criterion_id=crit_id,
                            value=bool_val,
                        )
                    )

        # 2. Critérios de Exclusão
        for key, val in (result.exclusion_criteria or {}).items():
            clean_k = str(key).strip().upper()
            crit_id = exc_map.get(clean_k) or text_map.get(str(key).lower().strip())
            if crit_id:
                bool_val = bool(val)
                eval_record = (
                    db.query(PaperCriterionModel)
                    .filter(
                        PaperCriterionModel.paper_id == paper_model.id,
                        PaperCriterionModel.criterion_id == crit_id,
                    )
                    .first()
                )
                if eval_record:
                    eval_record.value = bool_val
                else:
                    db.add(
                        PaperCriterionModel(
                            paper_id=paper_model.id,
                            criterion_id=crit_id,
                            value=bool_val,
                        )
                    )

        db.commit()
        db.refresh(paper_model)
        return result

    async def run_batch_screening(
        self,
        project_id: str,
        limit: int = 50,
        concurrency: int = 3,
    ):
        """Executa a triagem em lote em segundo plano com controle de concorrência."""
        db = SessionLocal()
        try:
            pending_papers = (
                db.query(PaperModel.id)
                .filter(PaperModel.project_id == project_id, PaperModel.decision == "Pendente")
                .limit(limit)
                .all()
            )
            paper_ids = [p[0] for p in pending_papers]
            total_papers = len(paper_ids)

            if total_papers == 0:
                await ws_manager.broadcast(
                    project_id,
                    {"type": "batch_screening_empty", "message": "Nenhum artigo pendente encontrado."},
                )
                return

            logger.info(f"[BatchScreening] Iniciando triagem de {total_papers} artigos para o projeto {project_id}...")

            semaphore = asyncio.Semaphore(concurrency)
            processed_count = 0
            included_count = 0
            excluded_count = 0
            pending_count = 0

            async def process_one(pid: str):
                nonlocal processed_count, included_count, excluded_count, pending_count
                async with semaphore:
                    task_db = SessionLocal()
                    try:
                        res = await self.screen_single_paper(task_db, project_id, pid)
                        processed_count += 1
                        if res.decision == "Incluído":
                            included_count += 1
                        elif res.decision == "Excluído":
                            excluded_count += 1
                        else:
                            pending_count += 1

                        await ws_manager.broadcast(
                            project_id,
                            {
                                "type": "batch_screening_progress",
                                "processed": processed_count,
                                "total": total_papers,
                                "percentage": round((processed_count / total_papers) * 100, 1),
                                "current_paper_id": pid,
                                "decision": res.decision,
                                "included_count": included_count,
                                "excluded_count": excluded_count,
                                "pending_count": pending_count,
                            },
                        )
                    except Exception as e:
                        logger.error(f"[BatchScreening] Erro no paper {pid}: {e}")
                    finally:
                        task_db.close()

            tasks = [process_one(pid) for pid in paper_ids]
            await asyncio.gather(*tasks)

            logger.info(f"[BatchScreening] Finalizada triagem em lote do projeto {project_id}.")
            await ws_manager.broadcast(
                project_id,
                {
                    "type": "batch_screening_completed",
                    "total_processed": processed_count,
                    "included": included_count,
                    "excluded": excluded_count,
                    "pending": pending_count,
                },
            )

        finally:
            db.close()
