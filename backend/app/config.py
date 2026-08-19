#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Configuração da Aplicação.
Utiliza Pydantic BaseSettings para gerenciamento centralizado de configurações
com suporte a variáveis de ambiente e valores padrão.
"""

from enum import Enum
from pathlib import Path
from typing import Optional

import platformdirs
from pydantic_settings import BaseSettings


class DeploymentProfile(str, Enum):
    """
    Perfil de exposição em que o backend está rodando (doc 29 §29.2).

    O RSAC nasceu assumindo que o único cliente era o Electron na mesma
    máquina. Quando o `server_launcher.py` passou a publicar o backend na
    internet, essa premissa deixou de valer sem que nada no código soubesse.
    O perfil torna o perímetro explícito: todo controle de segurança deriva
    dele, em vez de suposição implícita.
    """

    DESKTOP = "desktop"   # Electron ou navegador local falando com loopback
    SERVER = "server"     # publicado (túnel, rede local, Netlify)
    CI = "ci"             # testes automatizados


class Settings(BaseSettings):
    """Configurações globais da aplicação RSAC V2."""

    # ── Identificação ─────────────────────────────────────────────────
    app_name: str = "RSAC"
    app_version: str = "2.0.0"
    debug: bool = False

    # ── Perímetro de confiança ────────────────────────────────────────
    deployment_profile: DeploymentProfile = DeploymentProfile.DESKTOP

    # ── Chave-mestra da cifra de segredos (doc 29 §29.4.1) ────────────
    # Obrigatória no perfil `server`: lá um arquivo de chave ao lado do banco
    # seria lido pela mesma falha que leria o banco. Fora do `server`, a
    # ausência faz o backend gerar `<data_dir>/master.key` com permissão 0600.
    secret_key: Optional[str] = None

    # ── Sessões (doc 29 §29.3.3) ──────────────────────────────────────
    # Validade da sessão, renovada por atividade: quem está triando não é
    # deslogado no meio do trabalho, mas uma aba esquecida aberta expira.
    session_ttl_hours: int = 12

    # ── Servidor ──────────────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8000

    # ── Banco de Dados ────────────────────────────────────────────────
    database_url: Optional[str] = None

    # ── CORS ──────────────────────────────────────────────────────────
    # Origens extras autorizadas no perfil `server`. Aceita lista JSON ou
    # valores separados por vírgula em RSAC_CORS_ORIGINS. No perfil `desktop`
    # o loopback já é liberado por `cors_allow_origin_regex`.
    cors_origins: list[str] = []

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

    # ── Perímetro derivado do perfil ──────────────────────────────────

    @property
    def is_server_profile(self) -> bool:
        """Verdadeiro quando o backend está publicado fora do loopback."""
        return self.deployment_profile is DeploymentProfile.SERVER

    @property
    def cors_allow_origin_regex(self) -> Optional[str]:
        """
        Regex de origem permitida — apenas loopback, e apenas fora do perfil
        `server`. A porta é variável (Vite escolhe a que estiver livre), por
        isso o regex; o que ele não faz é aceitar host arbitrário.
        """
        if self.is_server_profile:
            return None
        return r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|file://)$"

    @property
    def effective_cors_origins(self) -> list[str]:
        """Lista finita de origens autorizadas, derivada do perfil."""
        if self.deployment_profile is DeploymentProfile.CI:
            return ["http://testserver"]
        return [o.strip().rstrip("/") for o in self.cors_origins if o and o.strip()]

    @property
    def expose_api_docs(self) -> bool:
        """A documentação OpenAPI mapeia a API inteira — fechada quando exposta."""
        return not self.is_server_profile

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
