#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Schemas para Configurações de Fontes e Credenciais."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SourceCredentialUpdate(BaseModel):
    """Atualização de credencial de base científica."""
    api_key: Optional[str] = Field(default=None, description="Chave de API (Scopus, PubMed, OpenAlex)")
    inst_token: Optional[str] = Field(default=None, description="Institutional Token (Elsevier/Scopus)")
    custom_endpoint: Optional[str] = Field(default=None, description="Endpoint personalizado (se aplicável)")


class SourceCredentialResponse(BaseModel):
    """Resposta com status da credencial (nunca expõe a chave completa em texto claro)."""
    source_name: str
    has_api_key: bool
    key_preview: str = ""  # ex: "••••••••a1b2"
    has_inst_token: bool = False
    inst_token_preview: str = ""
    custom_endpoint: Optional[str] = None
    updated_at: Optional[datetime] = None
