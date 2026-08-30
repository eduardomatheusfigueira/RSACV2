#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Serviço de Versionamento, Congelamento e Emendas de Protocolo (Doc 45 §12)."""

import hashlib
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    CriterionModel,
    ExtractionQuestionModel,
    ProtocolAmendmentModel,
    ProtocolModel,
    ProtocolVersionModel,
    SearchStrategyModel,
    utcnow,
)
from app.schemas.protocol import (
    ProtocolAmendmentResponse,
    ProtocolVersionResponse,
)


def _canonical_json_hash(data: Dict[str, Any]) -> str:
    """Gera o hash SHA-256 do JSON serializado de forma determinística."""
    json_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def create_protocol_snapshot(protocol: ProtocolModel, db: Session) -> Dict[str, Any]:
    """Gera o dicionário completo e canônico do estado atual do protocolo."""
    criteria = [
        {
            "id": c.id,
            "text": c.text,
            "is_exclusion": c.is_exclusion,
            "dimension": c.dimension,
            "applies_at": c.applies_at,
            "order": c.order,
        }
        for c in sorted(protocol.criteria, key=lambda x: x.order)
    ]

    questions = [
        {
            "id": q.id,
            "text": q.text,
            "answer_type": q.answer_type,
            "options": json.loads(q.options) if q.options else [],
            "required": q.required,
            "order": q.order,
        }
        for q in sorted(protocol.extraction_questions, key=lambda x: x.order)
    ]

    strategies = [
        {
            "kind": s.kind,
            "database": s.database,
            "blocks": json.loads(s.blocks) if s.blocks else [],
            "combination": s.combination,
            "limits": json.loads(s.limits) if s.limits else {},
            "rendered_query": s.rendered_query,
            "adaptation_note": s.adaptation_note,
        }
        for s in protocol.search_strategies
    ]

    return {
        "protocol_id": protocol.id,
        "project_id": protocol.project_id,
        "mode": protocol.mode,
        "review_design": protocol.review_design,
        "reporting_guideline": protocol.reporting_guideline,
        "conduct_standards": json.loads(protocol.conduct_standards) if protocol.conduct_standards else [],
        "question_framework": json.loads(protocol.question_framework) if protocol.question_framework else {},
        "objective": protocol.objective or "",
        "search_descriptors": json.loads(protocol.search_descriptors) if protocol.search_descriptors else {},
        "search_filters": json.loads(protocol.search_filters) if protocol.search_filters else {},
        "manuscript_sections": json.loads(protocol.manuscript_sections) if protocol.manuscript_sections else {},
        "appraisal": json.loads(protocol.appraisal) if protocol.appraisal else {},
        "synthesis": json.loads(protocol.synthesis) if protocol.synthesis else {},
        "bibliometrics": json.loads(protocol.bibliometrics) if protocol.bibliometrics else {},
        "criteria": criteria,
        "extraction_questions": questions,
        "search_strategies": strategies,
        "snapshot_at": utcnow().isoformat(),
    }


def freeze_protocol_version(
    protocol: ProtocolModel,
    label: str,
    user_id: Optional[str],
    db: Session,
) -> ProtocolVersionModel:
    """
    Congela a versão atual do protocolo com snapshot JSON e hash SHA-256 canônico (Doc 45 §12.1).
    """
    snapshot_dict = create_protocol_snapshot(protocol, db)
    content_hash = _canonical_json_hash(snapshot_dict)

    version = ProtocolVersionModel(
        protocol_id=protocol.id,
        label=label,
        snapshot=json.dumps(snapshot_dict, ensure_ascii=False),
        content_hash=content_hash,
        frozen_at=utcnow(),
        frozen_by_user_id=user_id,
    )
    db.add(version)

    protocol.status = "vigente"
    protocol.current_version = label
    protocol.updated_at = utcnow()

    db.commit()
    db.refresh(version)
    return version


def record_protocol_amendment(
    protocol: ProtocolModel,
    from_version: str,
    to_version: str,
    reason: str,
    project_phase: str,
    user_id: Optional[str],
    db: Session,
    diff: Optional[Dict[str, Any]] = None,
) -> ProtocolAmendmentModel:
    """
    Registra uma emenda formal com justificativa e cria nova versão congelada (Doc 45 §12.1).
    """
    # 1. Congela o estado atual sob o novo rótulo
    new_version = freeze_protocol_version(protocol, to_version, user_id, db)

    # 2. Computa diff se não fornecido
    if not diff:
        prev_v = db.query(ProtocolVersionModel).filter(
            ProtocolVersionModel.protocol_id == protocol.id,
            ProtocolVersionModel.label == from_version,
        ).first()

        diff_dict = {}
        if prev_v and prev_v.snapshot:
            try:
                prev_snap = json.loads(prev_v.snapshot)
                curr_snap = json.loads(new_version.snapshot)
                # Chaves alteradas
                for k, v in curr_snap.items():
                    if k != "snapshot_at" and prev_snap.get(k) != v:
                        diff_dict[k] = {"before": prev_snap.get(k), "after": v}
            except Exception:
                diff_dict = {"status": "diff_calculation_failed"}
        diff = diff_dict

    amendment = ProtocolAmendmentModel(
        protocol_id=protocol.id,
        from_version=from_version,
        to_version=to_version,
        diff=json.dumps(diff, ensure_ascii=False),
        reason=reason,
        project_phase=project_phase,
        created_at=utcnow(),
        created_by_user_id=user_id,
    )
    db.add(amendment)
    db.commit()
    db.refresh(amendment)
    return amendment
