#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Schemas de Protocolo, Critérios, Estratégias e 4 Eixos Metodológicos (Doc 45)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Critérios de Elegibilidade ──────────────────────────────────────────

class CriterionBase(BaseModel):
    """Base para critérios de inclusão/exclusão."""
    text: str = Field(..., min_length=1, max_length=1000)
    is_exclusion: bool = False
    dimension: str = Field("outro", description="populacao | desenho | periodo | idioma | tipo_doc | contexto | outro")
    applies_at: str = Field("ambos", description="titulo_resumo | texto_completo | ambos")
    order: int = 0


class CriterionCreate(CriterionBase):
    id: Optional[str] = None


class CriterionResponse(CriterionBase):
    id: str
    protocol_id: str

    model_config = {"from_attributes": True}


# ── Perguntas de Extração ───────────────────────────────────────────────

class ExtractionQuestionBase(BaseModel):
    """Base para perguntas de extração de dados."""
    text: str = Field(..., min_length=1, max_length=1000)
    answer_type: str = Field("texto", description="texto | numero | categoria | multipla | booleano")
    options: List[str] = Field(default_factory=list, description="Opções para resposta categórica ou múltipla")
    required: bool = False
    order: int = 0


class ExtractionQuestionCreate(ExtractionQuestionBase):
    id: Optional[str] = None


class ExtractionQuestionResponse(ExtractionQuestionBase):
    id: str
    protocol_id: str

    model_config = {"from_attributes": True}


# ── Framework de Pergunta Tipado (Doc 45 §7) ───────────────────────────

class QuestionFrameworkComponent(BaseModel):
    key: str
    label: str
    value: str = ""


class QuestionFrameworkSchema(BaseModel):
    framework: str = "PCC"
    components: List[QuestionFrameworkComponent] = Field(default_factory=list)
    question: str = ""


# ── Estratégias de Busca Canônica e Adaptada (Doc 45 §10) ──────────────

class SearchStrategyBlock(BaseModel):
    key: str
    label: str
    terms: List[str] = Field(default_factory=list)


class SearchStrategyBase(BaseModel):
    kind: str = Field("canonica", description="'canonica' | 'adaptacao'")
    database: str = Field("", description="Vazio para canônica, ou 'BDTD', 'Scopus', 'PubMed', etc.")
    blocks: List[SearchStrategyBlock] = Field(default_factory=list)
    combination: str = Field("", description="Expressão lógica, ex: 'A AND B AND C'")
    target_fields: List[str] = Field(default_factory=lambda: ["title", "abstract", "keywords"])
    limits: Dict[str, Any] = Field(default_factory=dict)
    rendered_query: str = ""
    adaptation_note: str = ""


class SearchStrategyCreate(SearchStrategyBase):
    pass


class SearchStrategyResponse(SearchStrategyBase):
    id: str
    protocol_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Registro de Execução de Busca (Doc 45 §10.4, §10.5) ─────────────────

class SearchExecutionResponse(BaseModel):
    id: str
    protocol_id: str
    harvest_run_id: Optional[str] = None
    database: str
    query_sent: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime
    records_returned: int = 0
    records_after_dedup: int = 0
    error: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Versionamento e Emendas (Doc 45 §12) ────────────────────────────────

class ProtocolFreezeRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=50, description="Rótulo da versão, ex: 'v1.0'")


class ProtocolVersionResponse(BaseModel):
    id: str
    protocol_id: str
    label: str
    snapshot: Dict[str, Any]
    content_hash: str
    frozen_at: datetime
    frozen_by_user_id: Optional[str] = None
    frozen_by_username: Optional[str] = None

    model_config = {"from_attributes": True}


class ProtocolAmendmentCreate(BaseModel):
    from_version: str
    to_version: str
    reason: str = Field(..., min_length=5, description="Justificativa metodológica da emenda")
    project_phase: str = Field("coleta", description="Fase do projeto: 'planejamento' | 'coleta' | 'triagem' | 'extracao' | 'sintese'")
    diff: Optional[Dict[str, Any]] = None


class ProtocolAmendmentResponse(BaseModel):
    id: str
    protocol_id: str
    from_version: str
    to_version: str
    diff: Dict[str, Any]
    reason: str
    project_phase: str
    created_at: datetime
    created_by_user_id: Optional[str] = None
    created_by_username: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Auditoria de Checklist (Doc 45 §13.1) ───────────────────────────────

class ChecklistAuditItemUpdate(BaseModel):
    guideline: str
    item_id: str
    state: str = Field("pendente", description="'atendido' | 'nao_aplica' | 'pendente'")
    location: str = ""
    justification: str = ""


class ChecklistAuditResponse(BaseModel):
    id: str
    protocol_id: str
    guideline: str
    item_id: str
    state: str
    location: str
    justification: str
    updated_at: datetime
    updated_by_user_id: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Medidor de Prontidão e Portões (Doc 45 §13.1) ───────────────────────

class ProtocolGateStatus(BaseModel):
    gate_name: str
    stage: str
    passed: bool
    requirements: List[str]
    missing: List[str]
    is_blocking: bool = False
    warning_message: Optional[str] = None


class ProtocolReadinessResponse(BaseModel):
    overall_percentage: int
    mode: str
    review_design: str
    checklist_guideline: str
    total_checklist_items: int
    completed_checklist_items: int
    gates: List[ProtocolGateStatus]
    summary_badge: str  # 'Pronto para Coleta' | 'Planejamento Incompleto' | etc.


# ── Atualização e Resposta do Protocolo (4 Eixos) ───────────────────────

class ProtocolModeUpdate(BaseModel):
    mode: str = Field(..., description="'simplificado' | 'completo'")


class ProtocolDesignUpdate(BaseModel):
    review_design: str = Field(..., description="D1 .. D14")


class ProtocolUpdate(BaseModel):
    """Atualização do protocolo da revisão sistemática nos 4 eixos."""
    mode: Optional[str] = None
    review_design: Optional[str] = None
    reporting_guideline: Optional[str] = None
    conduct_standards: Optional[List[str]] = None
    question_framework: Optional[Dict[str, Any]] = None
    objective: Optional[str] = None
    pico_framework: Optional[Dict[str, str]] = None
    search_descriptors: Optional[Dict[str, List[str]]] = None
    search_filters: Optional[Dict[str, Any]] = None
    manuscript_sections: Optional[Dict[str, str]] = None
    appraisal: Optional[Dict[str, Any]] = None
    synthesis: Optional[Dict[str, Any]] = None
    bibliometrics: Optional[Dict[str, Any]] = None
    criteria: Optional[List[CriterionCreate]] = None
    extraction_questions: Optional[List[ExtractionQuestionCreate]] = None


class ProtocolResponse(BaseModel):
    """Resposta com dados completos do protocolo e 4 eixos metodológicos."""
    id: str
    project_id: str
    mode: str
    review_design: str
    reporting_guideline: str
    conduct_standards: List[str] = Field(default_factory=list)
    question_framework: Dict[str, Any] = Field(default_factory=dict)
    objective: str
    pico_framework: Dict[str, str] = Field(default_factory=dict)
    search_descriptors: Dict[str, List[str]] = Field(default_factory=dict)
    search_filters: Dict[str, Any] = Field(default_factory=dict)
    manuscript_sections: Dict[str, str] = Field(default_factory=dict)
    appraisal: Dict[str, Any] = Field(default_factory=dict)
    synthesis: Dict[str, Any] = Field(default_factory=dict)
    bibliometrics: Dict[str, Any] = Field(default_factory=dict)
    status: str
    current_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    criteria: List[CriterionResponse] = []
    extraction_questions: List[ExtractionQuestionResponse] = []
    search_strategies: List[SearchStrategyResponse] = []
    latest_executions: List[SearchExecutionResponse] = []
    scope_stamp: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Catálogo Metodológico da API (Doc 45 §5, §6, §7, §13.2) ────────────

class ReviewDesignMeta(BaseModel):
    id: str  # D1..D14
    name: str
    when_to_use: str
    default_framework: str
    default_reporting: str
    conduct_standards: List[str]
    critical_appraisal_requirement: str  # 'obrigatoria' | 'opcional' | 'nao_se_aplica'
    expected_synthesis: str
    registry_eligibility: str
    suggested_extraction_questions: List[str]


class ReportingGuidelineMeta(BaseModel):
    id: str
    name: str
    description: str
    item_count: int
    reference: str


class ConductStandardMeta(BaseModel):
    id: str
    name: str
    organization: str
    description: str
    reference: str


class QuestionFrameworkMeta(BaseModel):
    id: str
    name: str
    components: List[Dict[str, str]]
    recommended_for: str


class AppraisalInstrumentMeta(BaseModel):
    id: str
    name: str
    applicable_to: str
    domains: List[str]
    reference: str


class ProtocolCatalogResponse(BaseModel):
    designs: List[ReviewDesignMeta]
    guidelines: List[ReportingGuidelineMeta]
    standards: List[ConductStandardMeta]
    frameworks: List[QuestionFrameworkMeta]
    instruments: List[AppraisalInstrumentMeta]
