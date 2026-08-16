#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Modelos ORM (SQLAlchemy 2.x).
Mapeamento objeto-relacional para todas as tabelas do banco de dados.
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
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_normalized: Mapped[str] = mapped_column(Text, default="")
    authors: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[str] = mapped_column(String(10), default="")
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    abstract: Mapped[str] = mapped_column(Text, default="")
    research_type: Mapped[str] = mapped_column(String(100), default="")
    institution: Mapped[str] = mapped_column(Text, default="")
    download_url: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(String(20), default="Pendente")
    observations: Mapped[str] = mapped_column(Text, default="")
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_text_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    paper: Mapped["PaperModel"] = relationship(back_populates="audit_logs")


# ─────────────────────────────────────────────────────────────────────
# Configurações de IA (persistidas)
# ─────────────────────────────────────────────────────────────────────

class AISettingsModel(Base):
    __tablename__ = "ai_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="gemini")
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="gemini-3.6-flash")
    api_keys_encrypted: Mapped[str] = mapped_column(Text, default="[]")
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
