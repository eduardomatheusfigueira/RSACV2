#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Schemas para Exportação e Importação de Chaves e Perfis."""

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


class KeysExportRequest(BaseModel):
    """
    Pedido de exportação de chaves (doc 29 §29.4.3).

    A senha protege o arquivo gerado. Não é a senha de nenhuma conta — é a
    chave que o usuário vai precisar informar para restaurar o backup.
    """

    export_password: str = Field(..., min_length=8, description="Senha que protegerá o arquivo exportado")


class KeysImportRequest(BaseModel):
    """Restauração de um backup — cifrado (com senha) ou legado em claro."""

    raw_content: Optional[str] = Field(default=None, description="Conteúdo bruto do arquivo (.json ou KEY=VALUE)")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Conteúdo já desserializado")
    export_password: Optional[str] = Field(default=None, description="Senha usada na exportação, se o arquivo for cifrado")


class EncryptedEnvelope(BaseModel):
    """Envelope cifrado devolvido pelas rotas de exportação de credenciais."""

    schema_version: str
    encrypted: bool = True
    kdf: str
    iterations: int
    salt: str
    ciphertext: str
    exported_at: str


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
    # Por padrão o perfil completo sai **sem** credenciais: o backup de
    # projetos, protocolos e extrações não precisa carregar chave de API junto
    # (doc 29 §29.4.2). Quem quiser as chaves no mesmo arquivo pede
    # explicitamente e fornece a senha que vai protegê-las.
    include_secrets: bool = Field(default=False, description="Incluir credenciais, cifradas, no pacote")
    export_password: Optional[str] = Field(default=None, description="Obrigatória quando include_secrets=True")


class ProfileImportResponse(BaseModel):
    status: str
    message: str
    projects_imported: int
    papers_imported: int
    extractions_imported: int
    restored_session: Dict[str, Any]
