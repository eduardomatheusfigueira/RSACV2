#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço de Triagem com Inteligência Artificial (Screening Service).
Executa a triagem automatizada (individual e em lote) com guardrails estritos
de zero alucinação e persistência de auditoria.
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.domain.entities import Decision, Methodology, Paper, Protocol
from app.infrastructure.ai.base import BaseAIClient, ScreeningResult
from app.infrastructure.ai.factory import AIFactory
from app.infrastructure.ai.prompts import build_screening_prompt
from app.infrastructure.persistence.models import (
    AuditLogModel,
    CriterionModel,
    PaperCriterionModel,
    PaperModel,
    ProtocolModel,
)
from app.services.harvesting_service import ws_manager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditActor:
    """
    Quem acionou uma operação assistida por IA.

    Existe como valor imutável, e não como o objeto ORM do usuário, porque a
    triagem em lote roda em segundo plano com outra sessão de banco — carregar
    o modelo para lá o deixaria destacado (`DetachedInstanceError`) na primeira
    leitura de atributo.
    """

    user_id: str
    username: str


# Prefixos de origem automática que jamais devem aparecer nas observações do revisor
# (ex.: "[IA - gemini-3.6-flash]:", "[I.A. gemini]:", "(AI) ", "IA:", "Assistente:").
_AI_PREFIX_PATTERNS = [
    re.compile(r"^\s*[\[\(]\s*(?:I\.?\s*A\.?|A\.?\s*I\.?|IA|AI)\b[^\]\)]*[\]\)]\s*[:\-–—]?\s*", re.IGNORECASE),
    re.compile(r"^\s*(?:I\.?\s*A\.?|A\.?\s*I\.?|IA|AI|Assistente(?:\s+de\s+IA)?|Modelo|Gemini|OpenAI|GPT|Claude)\s*[:\-–—]\s+", re.IGNORECASE),
    re.compile(r"^\s*(?:Justificativa|Parecer|An[áa]lise)\s*[:\-–—]\s+", re.IGNORECASE),
]


def _strip_ai_prefix(text: str) -> str:
    """Remove rótulos de origem automática do início do texto, de forma iterativa.

    A observação deve soar como a anotação de um pesquisador que triou o estudo,
    sem qualquer marca de ferramenta, modelo ou provedor.
    """
    cleaned = (text or "").strip()
    changed = True
    while changed and cleaned:
        changed = False
        for pattern in _AI_PREFIX_PATTERNS:
            new_text = pattern.sub("", cleaned, count=1).strip()
            if new_text != cleaned:
                cleaned = new_text
                changed = True
    return cleaned


def _normalize_key(value: str) -> str:
    """Normaliza uma chave de critério para comparação (maiúsculas, sem separadores)."""
    return re.sub(r"[\s_\-\.\:]+", "", str(value or "")).upper()


def _build_criterion_map(criteria_list: List[CriterionModel], prefixes: List[str]) -> Dict[str, str]:
    """Monta um mapa tolerante de chaves possíveis do modelo -> id do critério.

    Cobre as variações usuais devolvidas pelos provedores: "INC1", "INC_1",
    "Critério 1", "C1", o índice puro ("1") e o próprio texto do critério.
    """
    mapping: Dict[str, str] = {}
    for idx, crit in enumerate(criteria_list, 1):
        for prefix in prefixes:
            mapping[_normalize_key(f"{prefix}{idx}")] = crit.id
        mapping[_normalize_key(str(idx))] = crit.id
        if crit.text:
            mapping[_normalize_key(crit.text)] = crit.id
    return mapping


def _iter_criteria_flags(raw) -> List[tuple]:
    """Converte a resposta de critérios em pares (chave, booleano).

    Aceita tanto o dicionário previsto no prompt ({"INC1": true}) quanto listas
    de códigos atendidos (["INC1", "INC3"]) devolvidas por alguns modelos.
    """
    if isinstance(raw, dict):
        return [(k, bool(v)) for k, v in raw.items()]
    if isinstance(raw, (list, tuple, set)):
        pairs = []
        for item in raw:
            if isinstance(item, dict):
                code = item.get("code") or item.get("codigo") or item.get("id")
                if code is None:
                    continue
                value = item.get("atendido", item.get("value", item.get("met", True)))
                pairs.append((code, bool(value)))
            elif isinstance(item, str) and item.strip():
                pairs.append((item, True))
        return pairs
    return []


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
        actor: Optional["AuditActor"] = None,
    ) -> ScreeningResult:
        """
        Executa a triagem com IA para um único artigo.

        `actor` é quem pediu a triagem. A decisão é da IA, mas a
        responsabilidade por tê-la acionado é de uma pessoa — e é isso que a
        auditoria precisa registrar (doc 29 §29.3.5).
        """
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

        # Hash do contexto que produziu a decisão (doc 29 §29.9.3). Guardar o
        # texto inteiro inflaria o banco a cada triagem; o hash é o suficiente
        # para provar depois que a decisão veio *daquele* conteúdo — e para
        # detectar que o conteúdo mudou desde então.
        contexto_hash = hashlib.sha256(
            build_screening_prompt(paper_entity, protocol_entity).encode("utf-8")
        ).hexdigest()

        # Atualizar banco de dados
        old_decision = paper_model.decision
        paper_model.decision = result.decision
        paper_model.ai_confidence = result.confidence

        # Observações do revisor: apenas o parecer, sem rótulo de modelo ou provedor
        clean_just = _strip_ai_prefix(result.justification)
        if clean_just:
            paper_model.observations = clean_just

        # Log de Auditoria
        audit = AuditLogModel(
            paper_id=paper_model.id,
            action="ai_screening",
            old_value=old_decision,
            new_value=result.decision,
            source=f"ai:{result.provider}",
            user_id=actor.user_id if actor else None,
            username=actor.username if actor else "",
            ai_provider=result.provider or "",
            ai_model=result.model_used or "",
            ai_context_sha256=contexto_hash,
            ai_response_valid=result.response_valid,
        )
        db.add(audit)

        # Persistir avaliações de critérios, tolerando as variações de chave dos provedores
        inc_map = _build_criterion_map(
            [c for c in protocol_model.criteria if not c.is_exclusion],
            ["INC", "I", "CI", "CRIT", "CRITERIO", "CRITÉRIO", "C"],
        )
        exc_map = _build_criterion_map(
            [c for c in protocol_model.criteria if c.is_exclusion],
            ["EXC", "E", "CE", "CRIT", "CRITERIO", "CRITÉRIO", "C"],
        )

        for raw_criteria, crit_map in (
            (result.inclusion_criteria, inc_map),
            (result.exclusion_criteria, exc_map),
        ):
            for key, bool_val in _iter_criteria_flags(raw_criteria):
                crit_id = crit_map.get(_normalize_key(key))
                if not crit_id:
                    logger.debug(f"[ScreeningAI] Critério '{key}' não corresponde a nenhum critério do protocolo.")
                    continue

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
        actor: Optional["AuditActor"] = None,
    ):
        """Executa a triagem em lote em segundo plano com controle de concorrência."""
        db = SessionLocal()
        try:
            pending_papers = (
                db.query(PaperModel.id, PaperModel.title, PaperModel.authors, PaperModel.year)
                .filter(PaperModel.project_id == project_id, PaperModel.decision == "Pendente")
                .limit(limit)
                .all()
            )
            total_papers = len(pending_papers)

            if total_papers == 0:
                await ws_manager.broadcast(
                    project_id,
                    {"type": "batch_screening_empty", "message": "Nenhum artigo pendente encontrado."},
                )
                return

            logger.info(f"[BatchScreening] Iniciando triagem de {total_papers} artigos para o projeto {project_id}...")

            await ws_manager.broadcast(
                project_id,
                {
                    "type": "batch_screening_started",
                    "total": total_papers,
                    "message": f"Iniciando triagem com IA para {total_papers} artigos pendentes...",
                },
            )

            semaphore = asyncio.Semaphore(concurrency)
            processed_count = 0
            included_count = 0
            excluded_count = 0
            pending_count = 0

            async def process_one(paper_info):
                nonlocal processed_count, included_count, excluded_count, pending_count
                pid, ptitle, pauthors, pyear = paper_info
                async with semaphore:
                    # Notificar início da análise deste estudo específico
                    await ws_manager.broadcast(
                        project_id,
                        {
                            "type": "batch_screening_item_start",
                            "paper_id": pid,
                            "paper_title": ptitle or "Sem título",
                            "paper_authors": pauthors or "",
                            "paper_year": pyear or "",
                            "total": total_papers,
                        },
                    )

                    task_db = SessionLocal()
                    try:
                        res = await self.screen_single_paper(task_db, project_id, pid, actor=actor)
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
                                "current_paper_title": ptitle or "Sem título",
                                "decision": res.decision,
                                "confidence": res.confidence,
                                "justification": res.justification,
                                "included_count": included_count,
                                "excluded_count": excluded_count,
                                "pending_count": total_papers - processed_count,
                            },
                        )
                    except Exception as e:
                        logger.error(f"[BatchScreening] Erro no paper {pid}: {e}")
                    finally:
                        task_db.close()

            tasks = [process_one(p_info) for p_info in pending_papers]
            await asyncio.gather(*tasks)

            logger.info(f"[BatchScreening] Finalizada triagem em lote do projeto {project_id}.")
            await ws_manager.broadcast(
                project_id,
                {
                    "type": "batch_screening_completed",
                    "total_processed": processed_count,
                    "included": included_count,
                    "excluded": excluded_count,
                    "pending": total_papers - processed_count,
                },
            )

        finally:
            db.close()
