#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Schemas de Protocolo, Critérios e Seções do Manuscrito (PRISMA-ScR)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CriterionBase(BaseModel):
    """Base para critérios de inclusão/exclusão."""
    text: str = Field(..., min_length=1, max_length=1000)
    is_exclusion: bool = False
    order: int = 0


class CriterionCreate(CriterionBase):
    pass


class CriterionResponse(CriterionBase):
    id: str
    protocol_id: str

    model_config = {"from_attributes": True}


class ExtractionQuestionBase(BaseModel):
    """Base para perguntas de extração de dados."""
    text: str = Field(..., min_length=1, max_length=1000)
    order: int = 0


class ExtractionQuestionCreate(ExtractionQuestionBase):
    pass


class ExtractionQuestionResponse(ExtractionQuestionBase):
    id: str
    protocol_id: str

    model_config = {"from_attributes": True}


class ProtocolUpdate(BaseModel):
    """Atualização do protocolo da revisão sistemática / scoping review."""
    objective: Optional[str] = ""
    pico_framework: Optional[Dict[str, str]] = Field(default_factory=dict)
    search_descriptors: Optional[Dict[str, List[str]]] = Field(
        default_factory=dict,
        description="Pares de busca por idioma (máx 5 pares por idioma, máx 2 termos por par)",
    )
    search_filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Filtros de recorte de busca: anos (year_start, year_end), idiomas, tipos documentais, acesso aberto",
    )
    manuscript_sections: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Seções completas do manuscrito/protocolo (PRISMA-ScR 22 itens)",
    )
    criteria: Optional[List[CriterionCreate]] = None
    extraction_questions: Optional[List[ExtractionQuestionCreate]] = None


class ProtocolResponse(BaseModel):
    """Resposta com dados completos do protocolo e seções do manuscrito."""
    id: str
    project_id: str
    objective: str
    pico_framework: Dict[str, str]
    search_descriptors: Dict[str, List[str]]
    search_filters: Dict[str, Any] = Field(default_factory=dict)
    manuscript_sections: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    criteria: List[CriterionResponse] = []
    extraction_questions: List[ExtractionQuestionResponse] = []

    model_config = {"from_attributes": True}
