#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Schemas de Inteligência Artificial."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AISettingsUpdate(BaseModel):
    """Configuração dos provedores de IA."""
    ai_enabled: bool = Field(default=True, description="Chave mestra para ativar ou desativar os recursos de IA (Modo Manual)")
    provider: str = Field(..., description="gemini, qwen ou local")
    model: str = Field(..., description="Nome do modelo, ex: gemini-3.6-flash, qwen-plus, llama3")
    api_keys: List[str] = Field(default_factory=list, description="Lista de API Keys para rotação")
    endpoint: Optional[str] = Field(None, description="URL do endpoint local (Ollama/vLLM)")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, ge=256, le=32768)


class AISettingsResponse(BaseModel):
    ai_enabled: bool = True
    provider: str
    model: str
    has_api_keys: bool
    endpoint: Optional[str] = None
    temperature: float
    max_tokens: int


class ProtocolSuggestRequest(BaseModel):
    title: str = Field(..., min_length=3)
    methodology: str = "PRISMA-P"
    description: str = ""


class BatchScreeningRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    concurrency: int = Field(default=3, ge=1, le=10)
