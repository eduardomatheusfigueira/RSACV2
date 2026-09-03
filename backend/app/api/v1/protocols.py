#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Router de Protocolos, 4 Eixos Metodológicos, Estratégia e Versionamento (Doc 45)."""

import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    ChecklistAuditModel,
    CriterionModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    PaperCriterionModel,
    ProjectMemberModel,
    ProjectModel,
    ProtocolAmendmentModel,
    ProtocolModel,
    ProtocolVersionModel,
    SearchExecutionModel,
    SearchStrategyModel,
    UserModel,
    utcnow,
)
from app.schemas.protocol import (
    ChecklistAuditItemUpdate,
    ChecklistAuditResponse,
    CriterionResponse,
    ExtractionQuestionResponse,
    ProtocolAmendmentCreate,
    ProtocolAmendmentResponse,
    ProtocolDesignUpdate,
    ProtocolFreezeRequest,
    ProtocolModeUpdate,
    ProtocolReadinessResponse,
    ProtocolResponse,
    ProtocolUpdate,
    ProtocolVersionResponse,
    SearchExecutionResponse,
    SearchStrategyBase,
    SearchStrategyCreate,
    SearchStrategyResponse,
)
from app.security.dependencies import (
    exige_escrita_protocolo,
    projeto_do_usuario,
    require_session,
)
from app.services.harvesting_service import ws_manager
from app.services.protocol_catalog_service import get_review_design
from app.services.protocol_service import (
    calculate_protocol_readiness,
    get_scope_stamp,
)
from app.services.protocol_version_service import (
    freeze_protocol_version,
    record_protocol_amendment,
)
from app.services.search_strategy_service import (
    render_bdtd_decomposition,
    render_canonical_query,
    render_openalex_query,
    render_pubmed_query,
    render_scielo_query,
    render_scopus_query,
    run_press_review,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/protocol",
    dependencies=[Depends(projeto_do_usuario)],
    tags=["protocols"],
)


def _serialize_protocol(protocol: ProtocolModel, db: Session) -> ProtocolResponse:
    try:
        pico = json.loads(protocol.pico_framework) if protocol.pico_framework else {}
    except Exception:
        pico = {}

    try:
        descriptors = json.loads(protocol.search_descriptors) if protocol.search_descriptors else {}
    except Exception:
        descriptors = {}

    has_any_descriptor = any(p.strip() for pairs in descriptors.values() for p in pairs if p.strip()) if isinstance(descriptors, dict) else False
    if not has_any_descriptor and protocol.search_strategies:
        canonical_strat = next((s for s in protocol.search_strategies if s.kind == "canonica"), None)
        if canonical_strat and canonical_strat.blocks:
            try:
                blocks = json.loads(canonical_strat.blocks)
                pairs, _ = render_bdtd_decomposition(blocks, max_pairs=5)
                if pairs:
                    descriptors = {"pt": pairs}
            except Exception:
                pass

    try:
        filters = json.loads(protocol.search_filters) if protocol.search_filters else {}
    except Exception:
        filters = {}

    try:
        sections = json.loads(protocol.manuscript_sections) if protocol.manuscript_sections else {}
    except Exception:
        sections = {}

    try:
        standards = json.loads(protocol.conduct_standards) if protocol.conduct_standards else []
    except Exception:
        standards = []

    try:
        framework = json.loads(protocol.question_framework) if protocol.question_framework else {}
    except Exception:
        framework = {}

    try:
        appraisal = json.loads(protocol.appraisal) if protocol.appraisal else {}
    except Exception:
        appraisal = {}

    try:
        synthesis = json.loads(protocol.synthesis) if protocol.synthesis else {}
    except Exception:
        synthesis = {}

    try:
        bibliometrics = json.loads(protocol.bibliometrics) if protocol.bibliometrics else {}
    except Exception:
        bibliometrics = {}

    # Estratégias de busca
    strategies = [
        SearchStrategyResponse(
            id=s.id,
            protocol_id=s.protocol_id,
            kind=s.kind,
            database=s.database,
            blocks=json.loads(s.blocks) if s.blocks else [],
            combination=s.combination,
            target_fields=json.loads(s.target_fields) if s.target_fields else [],
            limits=json.loads(s.limits) if s.limits else {},
            rendered_query=s.rendered_query,
            adaptation_note=s.adaptation_note,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in protocol.search_strategies
    ]

    # Últimas execuções de busca
    latest_execs = [
        SearchExecutionResponse(
            id=e.id,
            protocol_id=e.protocol_id,
            harvest_run_id=e.harvest_run_id,
            database=e.database,
            query_sent=e.query_sent,
            filters=json.loads(e.filters) if e.filters else {},
            executed_at=e.executed_at,
            records_returned=e.records_returned,
            records_after_dedup=e.records_after_dedup,
            error=e.error,
        )
        for e in sorted(protocol.search_executions, key=lambda x: x.executed_at, reverse=True)[:10]
    ]

    return ProtocolResponse(
        id=protocol.id,
        project_id=protocol.project_id,
        mode=protocol.mode or "simplificado",
        review_design=protocol.review_design or "D4",
        reporting_guideline=protocol.reporting_guideline or "PRISMA-ScR",
        conduct_standards=standards,
        question_framework=framework,
        objective=protocol.objective or "",
        pico_framework=pico,
        search_descriptors=descriptors,
        search_filters=filters,
        manuscript_sections=sections,
        appraisal=appraisal,
        synthesis=synthesis,
        bibliometrics=bibliometrics,
        status=protocol.status or "rascunho",
        current_version=protocol.current_version,
        created_at=protocol.created_at,
        updated_at=protocol.updated_at,
        criteria=[
            CriterionResponse.model_validate(c) for c in sorted(protocol.criteria, key=lambda x: x.order)
        ],
        extraction_questions=[
            ExtractionQuestionResponse(
                id=q.id,
                protocol_id=q.protocol_id,
                text=q.text,
                answer_type=q.answer_type,
                options=json.loads(q.options) if q.options else [],
                required=q.required,
                order=q.order,
            )
            for q in sorted(protocol.extraction_questions, key=lambda x: x.order)
        ],
        search_strategies=strategies,
        latest_executions=latest_execs,
        scope_stamp=get_scope_stamp(protocol.mode or "simplificado"),
    )


@router.get("", response_model=ProtocolResponse)
def get_protocol(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Obtém o protocolo completo com 4 eixos, critérios, perguntas e estratégias."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail=f"Protocolo para o projeto '{project_id}' não encontrado.")

    return _serialize_protocol(protocol, db)


@router.put("", response_model=ProtocolResponse)
async def update_protocol(
    project_id: str,
    data: ProtocolUpdate,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_escrita_protocolo),
):
    """Atualiza o protocolo com controle de concorrência otimista (If-Match / 409) e broadcast."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")
        protocol = ProtocolModel(project_id=project_id)
        db.add(protocol)
        db.flush()

    # Controle de concorrência otimista (Doc 43 §43.12.2)
    if if_match and protocol.updated_at:
        clean_match = if_match.strip('"').strip()
        current_iso = protocol.updated_at.isoformat()
        if clean_match != current_iso and clean_match != str(protocol.updated_at):
            raise HTTPException(
                status_code=409,
                detail="Conflito de concorrência: o protocolo foi alterado por outro pesquisador desde a sua última leitura.",
            )

    if data.mode is not None:
        protocol.mode = data.mode

    if data.review_design is not None:
        protocol.review_design = data.review_design

    if data.reporting_guideline is not None:
        protocol.reporting_guideline = data.reporting_guideline

    if data.conduct_standards is not None:
        protocol.conduct_standards = json.dumps(data.conduct_standards, ensure_ascii=False)

    if data.question_framework is not None:
        protocol.question_framework = json.dumps(data.question_framework, ensure_ascii=False)

    if data.objective is not None:
        protocol.objective = data.objective

    if data.pico_framework is not None:
        protocol.pico_framework = json.dumps(data.pico_framework, ensure_ascii=False)

    if data.manuscript_sections is not None:
        protocol.manuscript_sections = json.dumps(data.manuscript_sections, ensure_ascii=False)

    if data.appraisal is not None:
        protocol.appraisal = json.dumps(data.appraisal, ensure_ascii=False)

    if data.synthesis is not None:
        protocol.synthesis = json.dumps(data.synthesis, ensure_ascii=False)

    if data.bibliometrics is not None:
        protocol.bibliometrics = json.dumps(data.bibliometrics, ensure_ascii=False)

    if data.search_descriptors is not None:
        has_valid_pair = any(p.strip() for pairs in data.search_descriptors.values() for p in pairs if p.strip())
        if has_valid_pair:
            for lang, pairs in data.search_descriptors.items():
                for pair in pairs:
                    terms = [t.strip() for t in pair.split(" AND ") if t.strip()]
                    if len(terms) > 2:
                        raise HTTPException(
                            status_code=400,
                            detail=f"A expressão '{pair}' contém mais de 2 termos combinados. Formule no máximo em pares ('termo_1' AND 'termo_2') para compatibilidade BDTD.",
                        )
            protocol.search_descriptors = json.dumps(data.search_descriptors, ensure_ascii=False)
        else:
            # Se a payload enviada estiver vazia (comum ao salvar na aba simplificada), checar se há estratégia canônica
            strat = db.query(SearchStrategyModel).filter(
                SearchStrategyModel.protocol_id == protocol.id,
                SearchStrategyModel.kind == "canonica",
            ).first()
            if strat and strat.blocks:
                try:
                    blocks = json.loads(strat.blocks)
                    pairs, _ = render_bdtd_decomposition(blocks, max_pairs=5)
                    if pairs:
                        protocol.search_descriptors = json.dumps({"pt": pairs}, ensure_ascii=False)
                    else:
                        protocol.search_descriptors = json.dumps(data.search_descriptors, ensure_ascii=False)
                except Exception:
                    protocol.search_descriptors = json.dumps(data.search_descriptors, ensure_ascii=False)
            else:
                protocol.search_descriptors = json.dumps(data.search_descriptors, ensure_ascii=False)

    if data.search_filters is not None:
        protocol.search_filters = json.dumps(data.search_filters, ensure_ascii=False)

    # Atualizar critérios se fornecidos
    if data.criteria is not None:
        existing_criteria = {c.id: c for c in protocol.criteria}
        kept_crit_ids = set()

        for idx, crit_data in enumerate(data.criteria):
            crit_id = getattr(crit_data, "id", None)
            if crit_id and crit_id in existing_criteria:
                crit = existing_criteria[crit_id]
                crit.text = crit_data.text
                crit.is_exclusion = crit_data.is_exclusion
                crit.dimension = crit_data.dimension
                crit.applies_at = crit_data.applies_at
                crit.order = idx
                kept_crit_ids.add(crit_id)
            else:
                crit_kwargs = {
                    "protocol_id": protocol.id,
                    "text": crit_data.text,
                    "is_exclusion": crit_data.is_exclusion,
                    "dimension": crit_data.dimension,
                    "applies_at": crit_data.applies_at,
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

    # Atualizar perguntas de extração se fornecidas
    if data.extraction_questions is not None:
        existing_questions = {q.id: q for q in protocol.extraction_questions}
        kept_q_ids = set()

        for idx, q_data in enumerate(data.extraction_questions):
            q_id = getattr(q_data, "id", None)
            if q_id and q_id in existing_questions:
                question = existing_questions[q_id]
                question.text = q_data.text
                question.answer_type = q_data.answer_type
                question.options = json.dumps(q_data.options, ensure_ascii=False)
                question.required = q_data.required
                question.order = idx
                kept_q_ids.add(q_id)
            else:
                q_kwargs = {
                    "protocol_id": protocol.id,
                    "text": q_data.text,
                    "answer_type": q_data.answer_type,
                    "options": json.dumps(q_data.options, ensure_ascii=False),
                    "required": q_data.required,
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

    protocol.updated_at = utcnow()
    db.commit()
    db.refresh(protocol)

    await ws_manager.broadcast(
        project_id,
        {
            "type": "protocolo.alterado",
            "secao": "protocolo",
            "por": usuario.username,
            "updated_at": protocol.updated_at.isoformat() if protocol.updated_at else None,
        },
    )

    return _serialize_protocol(protocol, db)


@router.post("/mode", response_model=ProtocolResponse)
async def switch_protocol_mode(
    project_id: str,
    payload: ProtocolModeUpdate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_escrita_protocolo),
):
    """Alterna entre modo Simplificado e Completo de forma não-destrutiva (Doc 45 §8.5)."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    protocol.mode = payload.mode
    protocol.updated_at = utcnow()
    db.commit()
    db.refresh(protocol)
    return _serialize_protocol(protocol, db)


@router.post("/design", response_model=Dict[str, Any])
async def switch_review_design(
    project_id: str,
    payload: ProtocolDesignUpdate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_escrita_protocolo),
):
    """Atualiza o desenho da revisão e devolve as derivações sugeridas (Doc 45 §5)."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    design_meta = get_review_design(payload.review_design)
    if not design_meta:
        raise HTTPException(status_code=400, detail=f"Desenho '{payload.review_design}' desconhecido.")

    protocol.review_design = design_meta.id
    protocol.reporting_guideline = design_meta.default_reporting
    protocol.conduct_standards = json.dumps(design_meta.conduct_standards, ensure_ascii=False)
    protocol.updated_at = utcnow()
    db.commit()
    db.refresh(protocol)

    return {
        "protocol": _serialize_protocol(protocol, db),
        "suggested_framework": design_meta.default_framework,
        "suggested_reporting": design_meta.default_reporting,
        "suggested_conduct_standards": design_meta.conduct_standards,
        "suggested_extraction_questions": design_meta.suggested_extraction_questions,
    }


@router.get("/readiness", response_model=ProtocolReadinessResponse)
def get_readiness(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Obtém o medidor de prontidão do protocolo e avaliação dos portões metodológicos."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    return calculate_protocol_readiness(protocol, db)


# ── Estratégia de Busca Canônica & Adaptadores (Doc 45 §10) ─────────────

@router.get("/search-strategy", response_model=List[SearchStrategyResponse])
def get_search_strategies(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Retorna as estratégias de busca (canônica e adaptações por base)."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    return [
        SearchStrategyResponse(
            id=s.id,
            protocol_id=s.protocol_id,
            kind=s.kind,
            database=s.database,
            blocks=json.loads(s.blocks) if s.blocks else [],
            combination=s.combination,
            target_fields=json.loads(s.target_fields) if s.target_fields else [],
            limits=json.loads(s.limits) if s.limits else {},
            rendered_query=s.rendered_query,
            adaptation_note=s.adaptation_note,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in protocol.search_strategies
    ]


@router.put("/search-strategy", response_model=SearchStrategyResponse)
def save_canonical_strategy(
    project_id: str,
    strategy_data: SearchStrategyCreate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_escrita_protocolo),
):
    """Salva a estratégia de busca canônica e renderiza a query combinada."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    strat = db.query(SearchStrategyModel).filter(
        SearchStrategyModel.protocol_id == protocol.id,
        SearchStrategyModel.kind == strategy_data.kind,
        SearchStrategyModel.database == strategy_data.database,
    ).first()

    rendered = render_canonical_query(
        [b.model_dump() for b in strategy_data.blocks],
        strategy_data.combination,
    )

    if not strat:
        strat = SearchStrategyModel(
            protocol_id=protocol.id,
            kind=strategy_data.kind,
            database=strategy_data.database,
            blocks=json.dumps([b.model_dump() for b in strategy_data.blocks], ensure_ascii=False),
            combination=strategy_data.combination,
            target_fields=json.dumps(strategy_data.target_fields, ensure_ascii=False),
            limits=json.dumps(strategy_data.limits, ensure_ascii=False),
            rendered_query=rendered,
            adaptation_note=strategy_data.adaptation_note,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(strat)
    else:
        strat.blocks = json.dumps([b.model_dump() for b in strategy_data.blocks], ensure_ascii=False)
        strat.combination = strategy_data.combination
        strat.target_fields = json.dumps(strategy_data.target_fields, ensure_ascii=False)
        strat.limits = json.dumps(strategy_data.limits, ensure_ascii=False)
        strat.rendered_query = rendered
        strat.adaptation_note = strategy_data.adaptation_note
        strat.updated_at = utcnow()

    # Sincronizar pares de busca com protocol.search_descriptors para coleta multibase
    if strategy_data.kind == "canonica" and strategy_data.blocks:
        try:
            blocks_raw = [b.model_dump() for b in strategy_data.blocks]
            pairs, _ = render_bdtd_decomposition(blocks_raw, max_pairs=5)
            if pairs:
                current_desc = {}
                if protocol.search_descriptors:
                    try:
                        current_desc = json.loads(protocol.search_descriptors)
                    except Exception:
                        current_desc = {}
                current_desc["pt"] = pairs
                protocol.search_descriptors = json.dumps(current_desc, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Falha ao sincronizar search_descriptors na estratégia canônica: {e}")

    db.commit()
    db.refresh(strat)

    return SearchStrategyResponse(
        id=strat.id,
        protocol_id=strat.protocol_id,
        kind=strat.kind,
        database=strat.database,
        blocks=json.loads(strat.blocks) if strat.blocks else [],
        combination=strat.combination,
        target_fields=json.loads(strat.target_fields) if strat.target_fields else [],
        limits=json.loads(strat.limits) if strat.limits else {},
        rendered_query=strat.rendered_query,
        adaptation_note=strat.adaptation_note,
        created_at=strat.created_at,
        updated_at=strat.updated_at,
    )


@router.post("/search-strategy/render")
def render_database_strategy(
    project_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Renderiza a query adaptada para uma base específica (Scopus, PubMed, SciELO, BDTD, OpenAlex)."""
    database = payload.get("database", "BDTD")
    blocks = payload.get("blocks", [])
    combination = payload.get("combination", "")
    limits = payload.get("limits", {})

    db_upper = database.upper()
    if db_upper == "SCOPUS":
        query, note = render_scopus_query(blocks, combination, limits)
        return {"database": "Scopus", "rendered_query": query, "adaptation_note": note, "is_decomposed": False}
    elif db_upper == "PUBMED":
        query, note = render_pubmed_query(blocks, combination, limits)
        return {"database": "PubMed", "rendered_query": query, "adaptation_note": note, "is_decomposed": False}
    elif db_upper == "OPENALEX":
        query, note = render_openalex_query(blocks, combination, limits)
        return {"database": "OpenAlex", "rendered_query": query, "adaptation_note": note, "is_decomposed": False}
    elif db_upper == "SCIELO":
        query, note = render_scielo_query(blocks, combination, limits)
        return {"database": "SciELO", "rendered_query": query, "adaptation_note": note, "is_decomposed": False}
    elif db_upper == "BDTD":
        pairs, note = render_bdtd_decomposition(blocks)
        return {"database": "BDTD", "rendered_pairs": pairs, "rendered_query": " ; ".join(pairs), "adaptation_note": note, "is_decomposed": True}
    else:
        query = render_canonical_query(blocks, combination)
        return {"database": database, "rendered_query": query, "adaptation_note": "Sintaxe padrão aplicada.", "is_decomposed": False}


@router.post("/search-strategy/press")
def analyze_press_review(
    project_id: str,
    payload: Dict[str, Any],
):
    """Executa a análise PRESS 2016 sobre os blocos conceituais."""
    blocks = payload.get("blocks", [])
    combination = payload.get("combination", "")
    return run_press_review(blocks, combination)


# ── Versionamento, Congelamento e Emendas (Doc 45 §12) ──────────────────

@router.post("/freeze", response_model=ProtocolVersionResponse)
def freeze_version(
    project_id: str,
    payload: ProtocolFreezeRequest,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_escrita_protocolo),
):
    """Congela a versão do protocolo com snapshot JSON e hash SHA-256 (Doc 45 §12.1)."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    version = freeze_protocol_version(protocol, payload.label, usuario.id, db)
    return ProtocolVersionResponse(
        id=version.id,
        protocol_id=version.protocol_id,
        label=version.label,
        snapshot=json.loads(version.snapshot),
        content_hash=version.content_hash,
        frozen_at=version.frozen_at,
        frozen_by_user_id=version.frozen_by_user_id,
        frozen_by_username=usuario.username,
    )


@router.get("/versions", response_model=List[ProtocolVersionResponse])
def list_versions(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Lista todas as versões congeladas do protocolo."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    return [
        ProtocolVersionResponse(
            id=v.id,
            protocol_id=v.protocol_id,
            label=v.label,
            snapshot=json.loads(v.snapshot),
            content_hash=v.content_hash,
            frozen_at=v.frozen_at,
            frozen_by_user_id=v.frozen_by_user_id,
            frozen_by_username=v.frozen_by.username if v.frozen_by else None,
        )
        for v in sorted(protocol.versions, key=lambda x: x.frozen_at, reverse=True)
    ]


@router.post("/amendments", response_model=ProtocolAmendmentResponse)
def create_amendment(
    project_id: str,
    payload: ProtocolAmendmentCreate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_escrita_protocolo),
):
    """Registra uma emenda formal com justificativa e gera nova versão congelada (Doc 45 §12.1)."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    amendment = record_protocol_amendment(
        protocol=protocol,
        from_version=payload.from_version,
        to_version=payload.to_version,
        reason=payload.reason,
        project_phase=payload.project_phase,
        user_id=usuario.id,
        db=db,
        diff=payload.diff,
    )

    return ProtocolAmendmentResponse(
        id=amendment.id,
        protocol_id=amendment.protocol_id,
        from_version=amendment.from_version,
        to_version=amendment.to_version,
        diff=json.loads(amendment.diff) if amendment.diff else {},
        reason=amendment.reason,
        project_phase=amendment.project_phase,
        created_at=amendment.created_at,
        created_by_user_id=amendment.created_by_user_id,
        created_by_username=usuario.username,
    )


@router.get("/amendments", response_model=List[ProtocolAmendmentResponse])
def list_amendments(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Lista o histórico de emendas do protocolo."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    return [
        ProtocolAmendmentResponse(
            id=a.id,
            protocol_id=a.protocol_id,
            from_version=a.from_version,
            to_version=a.to_version,
            diff=json.loads(a.diff) if a.diff else {},
            reason=a.reason,
            project_phase=a.project_phase,
            created_at=a.created_at,
            created_by_user_id=a.created_by_user_id,
            created_by_username=a.created_by.username if a.created_by else None,
        )
        for a in sorted(protocol.amendments, key=lambda x: x.created_at, reverse=True)
    ]


# ── Auditoria de Checklist (Doc 45 §13.1) ───────────────────────────────

@router.get("/checklist-audit", response_model=List[ChecklistAuditResponse])
def get_checklist_audits(
    project_id: str,
    guideline: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Recupera as avaliações de auditoria da checklist."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    query = db.query(ChecklistAuditModel).filter(ChecklistAuditModel.protocol_id == protocol.id)
    if guideline:
        query = query.filter(ChecklistAuditModel.guideline == guideline)

    return [ChecklistAuditResponse.model_validate(a) for a in query.all()]


@router.put("/checklist-audit", response_model=ChecklistAuditResponse)
def update_checklist_audit_item(
    project_id: str,
    payload: ChecklistAuditItemUpdate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_escrita_protocolo),
):
    """Atualiza a auditoria de um item da checklist (atendido / nao_aplica / pendente)."""
    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")

    audit = db.query(ChecklistAuditModel).filter(
        ChecklistAuditModel.protocol_id == protocol.id,
        ChecklistAuditModel.guideline == payload.guideline,
        ChecklistAuditModel.item_id == payload.item_id,
    ).first()

    if not audit:
        audit = ChecklistAuditModel(
            protocol_id=protocol.id,
            guideline=payload.guideline,
            item_id=payload.item_id,
            state=payload.state,
            location=payload.location,
            justification=payload.justification,
            updated_at=utcnow(),
            updated_by_user_id=usuario.id,
        )
        db.add(audit)
    else:
        audit.state = payload.state
        audit.location = payload.location
        audit.justification = payload.justification
        audit.updated_at = utcnow()
        audit.updated_by_user_id = usuario.id

    db.commit()
    db.refresh(audit)
    return ChecklistAuditResponse.model_validate(audit)
