#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Schemas de Coleta (Harvesting)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HarvestStartRequest(BaseModel):
    """Parâmetros para iniciar uma rodada de coleta."""
    sources: List[str] = Field(
        ..., min_length=1, description="Lista de fontes: BDTD, SciELO, OpenAlex, PubMed, Scopus"
    )
    max_records_per_descriptor: Optional[int] = Field(
        default=None, ge=0, description="Limite de registros por descritor (None ou 0 = Ilimitado)"
    )
    custom_descriptors: Optional[List[str]] = None
    year_start: Optional[int] = Field(default=None, ge=1800, le=2100)
    year_end: Optional[int] = Field(default=None, ge=1800, le=2100)
    languages: Optional[List[str]] = Field(default_factory=list)
    document_types: Optional[List[str]] = Field(default_factory=list)
    institutions: Optional[List[str]] = Field(default_factory=list)
    open_access_only: Optional[bool] = False
    fetch_details: bool = Field(default=True, description="Raspar detalhes profundos como orientador e instituição de defesa")


class HarvestRunResponse(BaseModel):
    """Detalhes de uma execução de coleta."""
    id: str
    project_id: str
    source_name: str
    descriptors_used: List[str] = []
    query_parameters: Optional[Dict[str, Any]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_found: int = 0
    records_new: int = 0
    records_duplicate: int = 0
    status: str
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class HarvestRunListResponse(BaseModel):
    items: List[HarvestRunResponse]
    total: int


class SourceCapabilityResponse(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    requires_api_key: bool
    supports_year_range: bool
    supports_language: bool
    supports_document_type: bool
    supports_institution: bool
    supports_open_access: bool
    supports_boolean_query: bool
    max_native_filters: Optional[int] = None
    default_page_size: int = 25
