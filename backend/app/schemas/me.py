#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Schemas Pydantic para Direitos do Titular (LGPD Art. 18 e 19).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MeSummaryResponse(BaseModel):
    """Formato simplificado e imediato de confirmação e acesso (Art. 19, I)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: Optional[str] = None
    email_verified: bool = False
    display_name: str = ""
    role: str
    auth_provider: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    terms_accepted_at: Optional[datetime] = None
    terms_version: str = ""
    total_projects: int = 0
    total_papers: int = 0


class MeUpdateRequest(BaseModel):
    """Atualização/Retificação de dados cadastrais (Art. 18, III)."""

    display_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=320)


class ProcessingRecordItem(BaseModel):
    """Registro individual de operação do ROPA associada ao titular."""

    id: str
    occurred_at: datetime
    operation: str
    legal_basis: str
    purpose: str
    data_categories: List[str]
    recipient: Optional[str] = None
    international: bool = False


class MeDeclarationResponse(BaseModel):
    """Declaração completa de tratamento de dados pessoais (Art. 19, II)."""

    titular: MeSummaryResponse
    controlador: Dict[str, Any]
    finalidades_e_bases_legais: List[Dict[str, Any]]
    historico_de_operacoes_ropa: List[ProcessingRecordItem]
    destinatarios_e_transferencias: List[Dict[str, Any]]
    politica_de_retencao: List[Dict[str, Any]]
    direitos_do_titular: List[Dict[str, Any]]


class MeDeleteRequest(BaseModel):
    """Confirmação de eliminação de conta e dados (Art. 18, VI)."""

    confirmation: str = Field(
        ...,
        description="Confirmação textual exigida: 'EXCLUIR' ou o próprio nome de usuário.",
    )
    grace_period_days: int = Field(
        7,
        ge=0,
        le=30,
        description="Prazo de arrependimento (0 para eliminação imediata, 7 para desativação com carência).",
    )


class MeDeleteResponse(BaseModel):
    """Resposta à solicitação de eliminação."""

    status: str
    immediate: bool
    scheduled_erasure_at: Optional[datetime] = None
    message: str
