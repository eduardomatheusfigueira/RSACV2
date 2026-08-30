#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Schemas de Artigos Científicos (Papers) e Julgamentos de Triagem."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.domain.enums import Decision


class PaperScreeningResponse(BaseModel):
    id: str
    paper_id: str
    reviewer_id: str
    reviewer_username: Optional[str] = None
    decision: str = "Pendente"
    observations: str = ""
    criteria_evaluations: Dict[str, bool] = Field(default_factory=dict)
    ai_confidence: Optional[float] = None
    ai_assisted: bool = False
    decided_at: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperBase(BaseModel):
    title: str
    authors: str = ""
    year: str = ""
    doi: Optional[str] = None
    abstract: str = ""
    research_type: str = ""
    institution: str = ""
    download_url: str = ""
    decision: Decision = Decision.PENDING
    observations: str = ""
    ai_confidence: Optional[float] = None
    criteria_evaluations: Dict[str, bool] = Field(default_factory=dict)


class PaperCreate(PaperBase):
    sources: List[str] = []


class PaperUpdate(BaseModel):
    decision: Optional[Decision] = None
    observations: Optional[str] = None
    criteria_evaluations: Optional[Dict[str, bool]] = None
    extraction_answers: Optional[Dict[str, str]] = None
    abstract: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[str] = None
    doi: Optional[str] = None
    download_url: Optional[str] = None


class PaperResponse(PaperBase):
    id: str
    project_id: str
    title_normalized: str
    screening_status: str = "aguardando"
    reviewers_completed_count: int = 0
    reviewers_required_count: int = 1
    my_screening: Optional[PaperScreeningResponse] = None
    screenings: Optional[List[PaperScreeningResponse]] = None
    conflict_resolved_by_user_id: Optional[str] = None
    conflict_resolved_by_username: Optional[str] = None
    conflict_resolved_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    pdf_text_extracted: bool = False
    pdf_status: str = "ausente"
    pdf_strategy: str = ""
    pdf_resolved_url: str = ""
    pdf_page_count: int = 0
    pdf_is_scanned: bool = False
    sources: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperListResponse(BaseModel):
    items: List[PaperResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ConflictResolutionRequest(BaseModel):
    decision: Decision
    observations: Optional[str] = None
    criteria_evaluations: Optional[Dict[str, bool]] = None
