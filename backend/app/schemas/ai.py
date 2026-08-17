#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Schemas de Inteligência Artificial."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AISettingsUpdate(BaseModel):
    """Configuração dos provedores de IA."""
    ai_enabled: bool = Field(default=True, description="Chave mestra para ativar ou desativar os recursos de IA (Modo Manual)")
    provider: str = Field(..., description="gemini, qwen ou local")
    model: str = Field(..., description="Nome do modelo, ex: gemini-3.6-flash, qwen3.8-max, Llama-3.2-3B")
    api_keys: Optional[List[str]] = Field(default=None, description="Chaves do provedor ativo atualmente")
    gemini_api_keys: Optional[List[str]] = Field(default=None, description="Lista de API Keys dedicadas para Google Gemini")
    qwen_api_keys: Optional[List[str]] = Field(default=None, description="Lista de API Keys dedicadas para Alibaba Qwen / DashScope")
    local_api_keys: Optional[List[str]] = Field(default=None, description="Lista de API Keys / tokens locais ou OpenRouter")
    endpoint: Optional[str] = Field(None, description="URL do endpoint local (Ollama/vLLM) ou DashScope/OpenRouter")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, ge=256, le=32768)


class AISettingsResponse(BaseModel):
    ai_enabled: bool = True
    provider: str
    model: str
    has_api_keys: bool
    api_keys: List[str] = Field(default_factory=list, description="Lista de API Keys do provedor ativo")
    gemini_api_keys: List[str] = Field(default_factory=list, description="Chaves cadastradas para Google Gemini")
    qwen_api_keys: List[str] = Field(default_factory=list, description="Chaves cadastradas para Alibaba Qwen")
    local_api_keys: List[str] = Field(default_factory=list, description="Chaves cadastradas para Local/OpenRouter")
    endpoint: Optional[str] = None
    temperature: float
    max_tokens: int


class ProtocolSuggestRequest(BaseModel):
    title: str = Field(..., min_length=3)
    methodology: str = "PRISMA-P"
    description: str = ""


class FieldAssistRequest(BaseModel):
    field_id: str
    field_label: str
    current_value: str = ""
    field_guidelines: str = ""
    project_title: str = ""
    methodology: str = "PRISMA-ScR"
    project_context: Optional[Dict[str, str]] = None
    action: str = "generate"  # "generate", "improve", "grammar", "expand", "shorten"
    custom_instruction: str = ""


class FieldAssistResponse(BaseModel):
    field_id: str
    suggested_text: str
    explanation: Optional[str] = None
    model_used: str = ""
    provider: str = ""


class BatchScreeningRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    concurrency: int = Field(default=3, ge=1, le=10)
