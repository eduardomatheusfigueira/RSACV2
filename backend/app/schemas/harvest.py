#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Schemas de Coleta (Harvesting)."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class HarvestStartRequest(BaseModel):
    """Parâmetros para iniciar uma rodada de coleta."""
    sources: List[str] = Field(
        ..., min_length=1, description="Lista de fontes: BDTD, SciELO, OpenAlex, PubMed, Scopus"
    )
    max_records_per_descriptor: Optional[int] = Field(
        default=0, ge=0, description="Limite de registros por descritor (0 ou None = Ilimitado)"
    )
    custom_descriptors: Optional[List[str]] = None


class HarvestRunResponse(BaseModel):
    """Detalhes de uma execução de coleta."""
    id: str
    project_id: str
    source_name: str
    descriptors_used: List[str] = []
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
