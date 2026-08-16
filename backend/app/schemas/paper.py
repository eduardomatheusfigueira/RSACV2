#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Schemas de Artigos Científicos (Papers)."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.domain.enums import Decision


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


class PaperCreate(PaperBase):
    sources: List[str] = []


class PaperUpdate(BaseModel):
    decision: Optional[Decision] = None
    observations: Optional[str] = None
    criteria_evaluations: Optional[Dict[str, bool]] = None
    extraction_answers: Optional[Dict[str, str]] = None


class PaperResponse(PaperBase):
    id: str
    project_id: str
    title_normalized: str
    pdf_path: Optional[str] = None
    pdf_text_extracted: bool = False
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
