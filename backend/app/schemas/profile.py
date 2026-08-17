#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Schemas para Exportação e Importação de Chaves e Perfis."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceKeyItem(BaseModel):
    api_key: Optional[str] = ""
    inst_token: Optional[str] = ""
    custom_endpoint: Optional[str] = None


class KeysBackupData(BaseModel):
    """Estrutura padronizada de exportação/importação de chaves de API."""
    schema_version: str = Field(default="rsac_api_keys_v1")
    exported_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    gemini_api_keys: List[str] = Field(default_factory=list, description="Chaves para Google Gemini")
    qwen_api_keys: List[str] = Field(default_factory=list, description="Chaves para Alibaba Qwen / DashScope")
    local_api_keys: List[str] = Field(default_factory=list, description="Chaves locais ou OpenRouter")
    sources: Dict[str, SourceKeyItem] = Field(
        default_factory=dict,
        description="Credenciais de bases científicas (SCOPUS, PUBMED, OPENALEX)",
    )


class KeysImportResponse(BaseModel):
    status: str
    message: str
    gemini_keys_count: int
    qwen_keys_count: int
    local_keys_count: int
    sources_configured: List[str]


class ProfileSessionPreferences(BaseModel):
    theme: str = "dark"
    active_project_id: Optional[str] = None
    sidebar_collapsed: bool = False
    ai_enabled: bool = True


class ProfileExportRequest(BaseModel):
    session_preferences: Optional[ProfileSessionPreferences] = None


class ProfileImportResponse(BaseModel):
    status: str
    message: str
    projects_imported: int
    papers_imported: int
    extractions_imported: int
    restored_session: Dict[str, Any]
