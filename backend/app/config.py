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

    # ── Aquisição de PDFs ─────────────────────────────────────────────
    # E-mail de contato usado nas APIs acadêmicas de acesso aberto.
    # Unpaywall o exige; OpenAlex e Crossref dão prioridade de fila
    # ("polite pool") a quem se identifica. Sem ele, a via Unpaywall é pulada.
    contact_email: str = ""
    # Tempo total (s) de busca por trabalho, somando todas as vias tentadas.
    pdf_search_timeout: float = 120.0
    # Tempo (s) de cada requisição isolada durante a busca.
    pdf_request_timeout: float = 25.0
    # Trabalhos buscados simultaneamente na aquisição em lote.
    pdf_batch_concurrency: int = 3

    # ── Contexto de IA ────────────────────────────────────────────────
    # Orçamento de caracteres do texto do estudo enviado à IA na extração.
    # ~28k caracteres ≈ 7–9k tokens, folgado para janelas de 32k em diante.
    ai_context_budget_chars: int = 28000

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
