#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Protocolo de Revisão Sistemática e Scoping Review (PRISMA-ScR)."""

import json
import logging
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.security.dependencies import projeto_do_usuario
from app.infrastructure.persistence.models import (
    CriterionModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    PaperCriterionModel,
    ProjectModel,
    ProtocolModel,
)
from app.schemas.protocol import (
    CriterionResponse,
    ExtractionQuestionResponse,
    ProtocolResponse,
    ProtocolUpdate,
)

logger = logging.getLogger(__name__)

# A titularidade entra como dependência do router, e não rota a rota (doc 40
# §40.3.2): é o mesmo padrão de `require_session`, e é o que faz uma rota
# nova nascer isolada sem depender de ninguém lembrar.
router = APIRouter(
    prefix="/projects/{project_id}/protocol",
    dependencies=[Depends(projeto_do_usuario)],
    tags=["protocols"],
)


def _serialize_protocol(protocol: ProtocolModel) -> ProtocolResponse:
    try:
        pico = json.loads(protocol.pico_framework) if protocol.pico_framework else {}
    except Exception:
        pico = {}

    try:
        descriptors = json.loads(protocol.search_descriptors) if protocol.search_descriptors else {}
    except Exception:
        descriptors = {}

    try:
        filters = json.loads(protocol.search_filters) if protocol.search_filters else {}
    except Exception:
        filters = {}

    try:
        sections = json.loads(protocol.manuscript_sections) if protocol.manuscript_sections else {}
    except Exception:
        sections = {}

    return ProtocolResponse(
        id=protocol.id,
        project_id=protocol.project_id,
        objective=protocol.objective or "",
        pico_framework=pico,
        search_descriptors=descriptors,
        search_filters=filters,
        manuscript_sections=sections,
        created_at=protocol.created_at,
        updated_at=protocol.updated_at,
        criteria=[
            CriterionResponse.model_validate(c) for c in sorted(protocol.criteria, key=lambda x: x.order)
        ],
        extraction_questions=[
            ExtractionQuestionResponse.model_validate(q)
            for q in sorted(protocol.extraction_questions, key=lambda x: x.order)
        ],
    )


@router.get("", response_model=ProtocolResponse)
def get_protocol(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Obtém o protocolo detalhado do projeto com todas as seções do artigo/PRISMA-ScR."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail=f"Protocolo para o projeto '{project_id}' não encontrado.")

    return _serialize_protocol(protocol)


@router.put("", response_model=ProtocolResponse)
def update_protocol(
    project_id: str,
    data: ProtocolUpdate,
    db: Session = Depends(get_db),
):
    """Atualiza o protocolo, critérios, seções do manuscrito, filtros e questões de extração."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")
        protocol = ProtocolModel(project_id=project_id)
        db.add(protocol)
        db.flush()

    if data.objective is not None:
        protocol.objective = data.objective

    if data.pico_framework is not None:
        protocol.pico_framework = json.dumps(data.pico_framework, ensure_ascii=False)

    if data.manuscript_sections is not None:
        protocol.manuscript_sections = json.dumps(data.manuscript_sections, ensure_ascii=False)

    if data.search_descriptors is not None:
        for lang, pairs in data.search_descriptors.items():
            for pair in pairs:
                terms = [t.strip() for t in pair.split(" AND ") if t.strip()]
                if len(terms) > 2:
                    raise HTTPException(
                        status_code=400,
                        detail=f"A expressão '{pair}' contém mais de 2 termos combinados. Formule no máximo em pares ('termo_1' AND 'termo_2') para compatibilidade BDTD.",
                    )
        protocol.search_descriptors = json.dumps(data.search_descriptors, ensure_ascii=False)

    if data.search_filters is not None:
        protocol.search_filters = json.dumps(data.search_filters, ensure_ascii=False)

    # Atualizar critérios se fornecidos (preservando IDs e integridade referencial)
    if data.criteria is not None:
        existing_criteria = {c.id: c for c in protocol.criteria}
        kept_crit_ids = set()

        for idx, crit_data in enumerate(data.criteria):
            crit_id = getattr(crit_data, "id", None)
            if crit_id and crit_id in existing_criteria:
                crit = existing_criteria[crit_id]
                crit.text = crit_data.text
                crit.is_exclusion = crit_data.is_exclusion
                crit.order = idx
                kept_crit_ids.add(crit_id)
            else:
                crit_kwargs = {
                    "protocol_id": protocol.id,
                    "text": crit_data.text,
                    "is_exclusion": crit_data.is_exclusion,
                    "order": idx,
                }
                if crit_id:
                    crit_kwargs["id"] = crit_id
                new_crit = CriterionModel(**crit_kwargs)
                db.add(new_crit)

        for c_id, c_obj in existing_criteria.items():
            if c_id not in kept_crit_ids:
                db.query(PaperCriterionModel).filter(PaperCriterionModel.criterion_id == c_id).delete()
                db.delete(c_obj)

    # Atualizar perguntas de extração se fornecidas (preservando IDs e integridade referencial)
    if data.extraction_questions is not None:
        existing_questions = {q.id: q for q in protocol.extraction_questions}
        kept_q_ids = set()

        for idx, q_data in enumerate(data.extraction_questions):
            q_id = getattr(q_data, "id", None)
            if q_id and q_id in existing_questions:
                question = existing_questions[q_id]
                question.text = q_data.text
                question.order = idx
                kept_q_ids.add(q_id)
            else:
                q_kwargs = {
                    "protocol_id": protocol.id,
                    "text": q_data.text,
                    "order": idx,
                }
                if q_id:
                    q_kwargs["id"] = q_id
                new_q = ExtractionQuestionModel(**q_kwargs)
                db.add(new_q)

        for q_id, q_obj in existing_questions.items():
            if q_id not in kept_q_ids:
                db.query(ExtractionAnswerModel).filter(ExtractionAnswerModel.question_id == q_id).delete()
                db.delete(q_obj)

    db.commit()
    db.refresh(protocol)
    return _serialize_protocol(protocol)
