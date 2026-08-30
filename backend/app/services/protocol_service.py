#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Serviço de Prontidão, Validação e Portões do Protocolo (Doc 45 §8, §13.1)."""

import json
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    ChecklistAuditModel,
    CriterionModel,
    ExtractionQuestionModel,
    ProtocolModel,
    SearchStrategyModel,
)
from app.schemas.protocol import (
    ProtocolGateStatus,
    ProtocolReadinessResponse,
)

SCOPE_STAMP_SIMPLIFICADO = (
    "Protocolo em modo Simplificado. Cobre integralmente os 16 itens do PRISMA-S "
    "(relato de buscas), os itens 5–7 do PRISMA 2020 e os itens de dados a extrair "
    "(PRISMA-P 12 / PRISMA 2020 10a). Não cobre: registro prospectivo, apreciação crítica, "
    "métodos de síntese, avaliação da certeza da evidência, vieses de relato e conflitos de interesse. "
    "Para submissão como revisão sistemática completa, migre para o modo Completo."
)


def get_scope_stamp(mode: str) -> str | None:
    """Retorna o carimbo normativo de escopo (Doc 45 §8.4) para modo Simplificado."""
    if mode == "simplificado":
        return SCOPE_STAMP_SIMPLIFICADO
    return None


def calculate_protocol_readiness(protocol: ProtocolModel, db: Session) -> ProtocolReadinessResponse:
    """
    Calcula a prontidão do protocolo e o status de passagem pelos portões do pipeline (Doc 45 §13.1).
    """
    # 1. Avaliação do Portão de Coleta (≥1 bloco de conceito com ≥1 termo OU descritores legados; ≥1 base)
    harvest_reqs = ["Ao menos 1 bloco de conceito com termo de busca", "Ao menos 1 base de dados selecionada"]
    harvest_missing = []

    has_search_terms = False
    # Verificar search_strategies
    strat = db.query(SearchStrategyModel).filter(
        SearchStrategyModel.protocol_id == protocol.id,
        SearchStrategyModel.kind == "canonica",
    ).first()

    if strat and strat.blocks:
        try:
            blocks = json.loads(strat.blocks)
            if any(b.get("terms") for b in blocks):
                has_search_terms = True
        except Exception:
            pass

    # Fallback para search_descriptors legados
    if not has_search_terms and protocol.search_descriptors:
        try:
            desc = json.loads(protocol.search_descriptors)
            if any(pairs for pairs in desc.values() if pairs):
                has_search_terms = True
        except Exception:
            pass

    if not has_search_terms:
        harvest_missing.append("Nenhum termo ou descritor de busca configurado")

    has_database = False
    if protocol.search_filters:
        try:
            filt = json.loads(protocol.search_filters)
            if filt.get("databases") and len(filt.get("databases")) > 0:
                has_database = True
        except Exception:
            pass
    if not has_database:
        # Se não há filtro explícito, todas as bases ativas são padrão
        has_database = True

    gate_coleta = ProtocolGateStatus(
        gate_name="Portão de Coleta",
        stage="coleta",
        passed=len(harvest_missing) == 0,
        requirements=harvest_reqs,
        missing=harvest_missing,
        is_blocking=True,
        warning_message="Configure ao menos um termo de busca para poder iniciar a coleta nas bases." if harvest_missing else None,
    )

    # 2. Avaliação do Portão de Triagem (≥1 critério de inclusão)
    screening_reqs = ["Ao menos 1 critério de inclusão cadastrado"]
    screening_missing = []
    inc_count = sum(1 for c in protocol.criteria if not c.is_exclusion)
    if inc_count == 0:
        screening_missing.append("Nenhum critério de inclusão cadastrado")

    gate_triagem = ProtocolGateStatus(
        gate_name="Portão de Triagem",
        stage="triagem",
        passed=len(screening_missing) == 0,
        requirements=screening_reqs,
        missing=screening_missing,
        is_blocking=False,
        warning_message="Recomenda-se cadastrar critérios de inclusão antes da triagem." if screening_missing else None,
    )

    # 3. Avaliação do Portão de Extração (≥1 pergunta de extração - Doc 45 D-C)
    extraction_reqs = ["Ao menos 1 pergunta de extração cadastrada"]
    extraction_missing = []
    if len(protocol.extraction_questions) == 0:
        extraction_missing.append("Nenhuma pergunta de extração cadastrada no protocolo")

    gate_extracao = ProtocolGateStatus(
        gate_name="Portão de Extração",
        stage="extracao",
        passed=len(extraction_missing) == 0,
        requirements=extraction_reqs,
        missing=extraction_missing,
        is_blocking=False,
        warning_message="Perguntas de extração planejadas a priori garantem a conformidade com o PRISMA-P item 12." if extraction_missing else None,
    )

    # 4. Avaliação do Portão de Indicadores / Síntese
    insights_reqs = ["Desenho da revisão e diretriz de relato definidos"]
    insights_missing = []
    if not protocol.review_design:
        insights_missing.append("Desenho da revisão não selecionado")

    gate_indicadores = ProtocolGateStatus(
        gate_name="Portão de Indicadores",
        stage="indicadores",
        passed=len(insights_missing) == 0,
        requirements=insights_reqs,
        missing=insights_missing,
        is_blocking=False,
        warning_message=None,
    )

    gates = [gate_coleta, gate_triagem, gate_extracao, gate_indicadores]

    # Contagem de auditoria de checklist
    guideline = protocol.reporting_guideline or "PRISMA-ScR"
    audits = db.query(ChecklistAuditModel).filter(
        ChecklistAuditModel.protocol_id == protocol.id,
        ChecklistAuditModel.guideline == guideline,
    ).all()
    completed_audits = sum(1 for a in audits if a.state in ("atendido", "nao_aplica"))

    # Estimativa de total de itens da guideline
    total_items = 22 if "ScR" in guideline else 27 if "2020" in guideline else 17 if "PRISMA-P" in guideline else 20

    # Cálculo do percentual geral ponderado
    points = 0
    max_points = 100

    if protocol.objective and len(protocol.objective.strip()) > 10:
        points += 15
    if has_search_terms:
        points += 25
    if inc_count > 0:
        points += 20
    if len(protocol.extraction_questions) > 0:
        points += 20
    if protocol.review_design:
        points += 10
    if protocol.status in ("vigente", "concluido") or protocol.current_version:
        points += 10

    overall_pct = min(100, max(0, points))

    if gate_coleta.passed and inc_count > 0 and len(protocol.extraction_questions) > 0:
        summary_badge = "Pronto para Execução"
    elif gate_coleta.passed:
        summary_badge = "Pronto para Coleta"
    else:
        summary_badge = "Planejamento Incompleto"

    return ProtocolReadinessResponse(
        overall_percentage=overall_pct,
        mode=protocol.mode or "simplificado",
        review_design=protocol.review_design or "D4",
        checklist_guideline=guideline,
        total_checklist_items=total_items,
        completed_checklist_items=completed_audits,
        gates=gates,
        summary_badge=summary_badge,
    )
