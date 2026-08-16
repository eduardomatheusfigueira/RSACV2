#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Configuração da Aplicação.
Utiliza Pydantic BaseSettings para gerenciamento centralizado de configurações
com suporte a variáveis de ambiente e valores padrão.
"""

from pathlib import Path
from typing import Optional

import platformdirs
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações globais da aplicação RSAC V2."""

    # ── Identificação ─────────────────────────────────────────────────
    app_name: str = "RSAC"
    app_version: str = "2.0.0"
    debug: bool = False

    # ── Servidor ──────────────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8000

    # ── Banco de Dados ────────────────────────────────────────────────
    database_url: Optional[str] = None

    # ── CORS ──────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:*", "http://127.0.0.1:*"]

    @property
    def data_dir(self) -> Path:
        """Diretório de dados da aplicação (cross-platform)."""
        path = Path(platformdirs.user_data_dir(self.app_name))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def database_path(self) -> Path:
        """Caminho do banco SQLite."""
        return self.data_dir / "rsac.db"

    @property
    def pdf_storage_dir(self) -> Path:
        """Diretório de armazenamento de PDFs locais."""
        path = self.data_dir / "pdfs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def effective_database_url(self) -> str:
        """URL efetiva do banco (permite override via env ou argumento)."""
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.database_path}"

    model_config = {
        "env_prefix": "RSAC_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Singleton de configuração
settings = Settings()
