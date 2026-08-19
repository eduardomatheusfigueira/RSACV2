#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Modelos ORM (SQLAlchemy 2.x).
Mapeamento objeto-relacional para todas as tabelas do banco de dados SQLite.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.security.encrypted_type import EncryptedText


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos ORM."""
    pass


def generate_uuid() -> str:
    """Gera um UUID v4 como string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Retorna datetime UTC atual."""
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────
# Projeto
# ─────────────────────────────────────────────────────────────────────

class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    methodology: Mapped[str] = mapped_column(String(50), nullable=False, default="PRISMA-P")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    protocol: Mapped["ProtocolModel"] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    papers: Mapped[list["PaperModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    harvest_runs: Mapped[list["HarvestRunModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────
# Protocolo
# ─────────────────────────────────────────────────────────────────────

class ProtocolModel(Base):
    __tablename__ = "protocols"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True)
    objective: Mapped[str] = mapped_column(Text, default="")
    pico_framework: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    search_descriptors: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    search_filters: Mapped[str] = mapped_column(Text, default="{}")  # JSON string para recorte temporal, idiomas, etc.
    manuscript_sections: Mapped[str] = mapped_column(Text, default="{}")  # JSON string para todas as seções do PRISMA-ScR
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="protocol")
    criteria: Mapped[list["CriterionModel"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    extraction_questions: Mapped[list["ExtractionQuestionModel"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────
# Critérios (Inclusão e Exclusão)
# ─────────────────────────────────────────────────────────────────────

class CriterionModel(Base):
    __tablename__ = "criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol_id: Mapped[str] = mapped_column(ForeignKey("protocols.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_exclusion: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    protocol: Mapped["ProtocolModel"] = relationship(back_populates="criteria")
    paper_evaluations: Mapped[list["PaperCriterionModel"]] = relationship(
        back_populates="criterion", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────
# Paper (Artigo Científico)
# ─────────────────────────────────────────────────────────────────────

class PaperModel(Base):
    __tablename__ = "papers"
    __table_args__ = (
        Index("ix_papers_project_decision", "project_id", "decision"),
        Index("ix_papers_doi", "doi"),
        Index("ix_papers_title_normalized", "title_normalized"),
        Index("ix_papers_project_doi", "project_id", "doi"),
        Index("ix_papers_project_title_norm", "project_id", "title_normalized"),
        Index("ix_papers_project_blocking_key", "project_id", "blocking_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_normalized: Mapped[str] = mapped_column(Text, default="")
    blocking_key: Mapped[str] = mapped_column(String(120), default="", index=True)
    authors: Mapped[str] = mapped_column(Text, default="")
    advisor: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[str] = mapped_column(String(10), default="")
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    abstract: Mapped[str] = mapped_column(Text, default="")
    research_type: Mapped[str] = mapped_column(String(100), default="")
    institution: Mapped[str] = mapped_column(Text, default="")
    journal: Mapped[str] = mapped_column(Text, default="")
    download_url: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(String(20), default="Pendente")
    observations: Mapped[str] = mapped_column(Text, default="")
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_text_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    # ── Procedência e diagnóstico do PDF ──────────────────────────────
    # "ausente" | "obtido" | "manual" | "falhou" | "indisponivel"
    pdf_status: Mapped[str] = mapped_column(String(20), default="ausente")
    pdf_resolved_url: Mapped[str] = mapped_column(Text, default="")
    pdf_strategy: Mapped[str] = mapped_column(String(40), default="")
    pdf_attempts: Mapped[str] = mapped_column(Text, default="[]")  # JSON da trilha
    pdf_page_count: Mapped[int] = mapped_column(Integer, default=0)
    pdf_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    pdf_sha256: Mapped[str] = mapped_column(String(64), default="")
    pdf_text_chars: Mapped[int] = mapped_column(Integer, default=0)
    pdf_is_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    pdf_acquired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    merged_into_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="papers")
    sources: Mapped[list["PaperSourceModel"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
    criteria_evaluations: Mapped[list["PaperCriterionModel"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
    extraction_answers: Mapped[list["ExtractionAnswerModel"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLogModel"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────
# Fontes do Paper (em quais bases foi encontrado)
# ─────────────────────────────────────────────────────────────────────

class PaperSourceModel(Base):
    __tablename__ = "paper_sources"
    __table_args__ = (
        Index("ix_paper_sources_unique", "paper_id", "source_name", "source_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(200), default="")
    harvested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    paper: Mapped["PaperModel"] = relationship(back_populates="sources")


# ─────────────────────────────────────────────────────────────────────
# Avaliação de Critério por Paper
# ─────────────────────────────────────────────────────────────────────

class PaperCriterionModel(Base):
    __tablename__ = "paper_criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    criterion_id: Mapped[str] = mapped_column(ForeignKey("criteria.id"))
    value: Mapped[bool] = mapped_column(Boolean, nullable=False)

    paper: Mapped["PaperModel"] = relationship(back_populates="criteria_evaluations")
    criterion: Mapped["CriterionModel"] = relationship(back_populates="paper_evaluations")


# ─────────────────────────────────────────────────────────────────────
# Perguntas de Extração
# ─────────────────────────────────────────────────────────────────────

class ExtractionQuestionModel(Base):
    __tablename__ = "extraction_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol_id: Mapped[str] = mapped_column(ForeignKey("protocols.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    protocol: Mapped["ProtocolModel"] = relationship(back_populates="extraction_questions")
    answers: Mapped[list["ExtractionAnswerModel"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────
# Respostas de Extração
# ─────────────────────────────────────────────────────────────────────

class ExtractionAnswerModel(Base):
    __tablename__ = "extraction_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    question_id: Mapped[str] = mapped_column(ForeignKey("extraction_questions.id"))
    answer: Mapped[str] = mapped_column(Text, default="")
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    # Trecho literal do estudo que sustenta a resposta e a página onde está —
    # sem isso a extração assistida não é auditável em revisão sistemática.
    evidence: Mapped[str] = mapped_column(Text, default="")
    page_ref: Mapped[str] = mapped_column(String(20), default="")
    source_kind: Mapped[str] = mapped_column(String(20), default="")  # pdf | resumo | manual
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    paper: Mapped["PaperModel"] = relationship(back_populates="extraction_answers")
    question: Mapped["ExtractionQuestionModel"] = relationship(back_populates="answers")


# ─────────────────────────────────────────────────────────────────────
# Execuções de Coleta (Harvest Runs)
# ─────────────────────────────────────────────────────────────────────

class HarvestRunModel(Base):
    __tablename__ = "harvest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    descriptors_used: Mapped[str] = mapped_column(Text, default="[]")  # JSON string
    query_parameters: Mapped[str] = mapped_column(Text, default="{}")  # JSON string (HarvestQuery snapshot)
    checkpoint: Mapped[str] = mapped_column(Text, default="{}")  # JSON string para retomada
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    records_found: Mapped[int] = mapped_column(Integer, default=0)
    records_new: Mapped[int] = mapped_column(Integer, default=0)
    records_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["ProjectModel"] = relationship(back_populates="harvest_runs")


# ─────────────────────────────────────────────────────────────────────
# Log de Auditoria
# ─────────────────────────────────────────────────────────────────────

class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    # Quem fez a alteração. Sem isto, `source="manual"` não distingue o
    # pesquisador do coautor nem de um terceiro — e uma revisão sistemática
    # cujo produto é a reprodutibilidade precisa saber de quem foi a decisão.
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    # Proveniência da decisão assistida (doc 29 §29.9.3): provedor, modelo e o
    # hash do contexto enviado. É o que permite refazer a conta depois —
    # inclusive descobrir que uma decisão veio de conteúdo adulterado.
    ai_provider: Mapped[str] = mapped_column(String(40), default="")
    ai_model: Mapped[str] = mapped_column(String(80), default="")
    ai_context_sha256: Mapped[str] = mapped_column(String(64), default="")
    ai_response_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    paper: Mapped["PaperModel"] = relationship(back_populates="audit_logs")


# ─────────────────────────────────────────────────────────────────────
# Contas de Acesso e Sessões (doc 29 §29.3)
# ─────────────────────────────────────────────────────────────────────

class UserModel(Base):
    """
    Conta de acesso ao RSAC.

    A senha nunca é guardada — só o hash Argon2id, que `app/security/passwords`
    produz e verifica. `role` separa quem opera a revisão de quem administra as
    credenciais (§29.3.4).
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="researcher", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sessions: Mapped[list["SessionModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SessionModel(Base):
    """
    Sessão ativa, com estado no servidor.

    A alternativa — um JWT auto-contido — não permitiria revogar acesso antes
    do vencimento; aqui `logout` apaga a linha e o token morre na hora
    (§29.3.3). O que se guarda é o *hash* do token: um vazamento do banco não
    entrega sessões utilizáveis.
    """

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_token_hash", "token_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    user_agent: Mapped[str] = mapped_column(String(200), default="")

    user: Mapped["UserModel"] = relationship(back_populates="sessions")


class LoginAttemptModel(Base):
    """
    Tentativas de login, para o limite de força bruta (§29.7).

    Guardar as tentativas no banco — e não em memória — é o que faz o limite
    sobreviver ao reinício do processo, que de outro modo seria a forma trivial
    de zerá-lo.
    """

    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_username_time", "username", "attempted_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    client_host: Mapped[str] = mapped_column(String(64), default="")
    successful: Mapped[bool] = mapped_column(Boolean, default=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ─────────────────────────────────────────────────────────────────────
# Configurações de Fontes / Credenciais de Coleta (Scopus, PubMed, etc.)
# ─────────────────────────────────────────────────────────────────────

class SourceCredentialModel(Base):
    __tablename__ = "source_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    api_key: Mapped[str] = mapped_column(EncryptedText, default="")
    inst_token: Mapped[str] = mapped_column(EncryptedText, default="")
    custom_endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# ─────────────────────────────────────────────────────────────────────
# Configurações de IA (persistidas)
# ─────────────────────────────────────────────────────────────────────

class AISettingsModel(Base):
    __tablename__ = "ai_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="gemini")
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="gemini-3.6-flash")
    # O sufixo `_encrypted` era falso até a Fase 2 do plano de segurança: o que
    # se gravava era `json.dumps(lista)` puro. `EncryptedText` torna o nome
    # verdadeiro — e o nome mentiroso era pior que a ausência da cifra, porque
    # desarmava quem revisasse o código.
    api_keys_encrypted: Mapped[str] = mapped_column(EncryptedText, default="[]")
    gemini_api_keys_encrypted: Mapped[str] = mapped_column(EncryptedText, default="[]")
    qwen_api_keys_encrypted: Mapped[str] = mapped_column(EncryptedText, default="[]")
    local_api_keys_encrypted: Mapped[str] = mapped_column(EncryptedText, default="[]")
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# ─────────────────────────────────────────────────────────────────────
# Relatórios de Deduplicação (Persistidos por Projeto)
# ─────────────────────────────────────────────────────────────────────

class DeduplicationReportModel(Base):
    __tablename__ = "deduplication_reports"
    __table_args__ = (Index("ix_dedup_reports_project", "project_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    total_raw: Mapped[int] = mapped_column(Integer, default=0)
    total_unique: Mapped[int] = mapped_column(Integer, default=0)
    total_duplicates: Mapped[int] = mapped_column(Integer, default=0)
    sources_breakdown: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    duplicates_list: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    report_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    project: Mapped["ProjectModel"] = relationship()

