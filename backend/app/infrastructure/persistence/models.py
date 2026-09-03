#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Modelos ORM (SQLAlchemy 2.x).
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
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from app.security.encrypted_type import EncryptedText


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos ORM."""
    pass


def generate_uuid() -> str:
    """Gera um UUID v4 como string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Retorna datetime UTC atual, com fuso explícito."""
    return datetime.now(timezone.utc)


def as_utc(moment: datetime | None) -> datetime | None:
    """
    Normaliza para UTC consciente uma data **lida do banco**.

    Existe porque os dois bancos legítimos do Revsist devolvem coisas diferentes da
    mesma coluna `DateTime(timezone=True)`:

      * **PostgreSQL** armazena `timestamptz` e devolve datetime consciente;
      * **SQLite** não tem tipo com fuso — ignora `timezone=True` e devolve
        datetime ingênuo, contendo a hora **UTC** que foi gravada.

    Comparar um consciente com um ingênuo levanta `TypeError`, e é exatamente o
    que aconteceria ao rodar em SQLite um código escrito e testado em
    PostgreSQL. Passar toda leitura por aqui elimina a diferença num ponto só,
    em vez de espalhar `tzinfo=None` pelas consultas.
    """
    if moment is None:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


# ─────────────────────────────────────────────────────────────────────
# Projeto
# ─────────────────────────────────────────────────────────────────────

class ProjectModel(Base):
    """
    Projeto de revisão sistemática.

    `owner_id` é o que torna o Revsist utilizável por mais de uma pessoa. Sem ele
    — como era até a Fase 1 do doc 41 — qualquer conta autenticada lia, editava
    e apagava o acervo de qualquer outra: aceitável quando o único cliente era
    o Electron na própria máquina, e vazamento entre controladores distintos
    assim que o backend passou a atender vários pesquisadores (doc 39, O-01).
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    methodology: Mapped[str] = mapped_column(String(50), nullable=False, default="PRISMA-P")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    collaboration_mode: Mapped[str] = mapped_column(
        String(30), nullable=False, default="individual", server_default="individual"
    )
    reviewers_per_paper: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    conflict_resolution: Mapped[str] = mapped_column(
        String(30), nullable=False, default="coordenador", server_default="coordenador"
    )

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
    deduplication_reports: Mapped[list["DeduplicationReportModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    members: Mapped[list["ProjectMemberModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    invitations: Mapped[list["ProjectInvitationModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.owner_id and not any(m.user_id == self.owner_id for m in getattr(self, "members", [])):
            self.members.append(
                ProjectMemberModel(
                    user_id=self.owner_id,
                    project_role="coordenador",
                    is_active=True,
                )
            )


# ─────────────────────────────────────────────────────────────────────
# Participação em Projeto (doc 43 §43.3.1 — Pesquisa em Equipe)
# ─────────────────────────────────────────────────────────────────────

class ProjectMemberModel(Base):
    """
    Participação de um usuário em um projeto de revisão.

    `project_role` separa coordenador, revisor e observador dentro do projeto.
    `is_active` desliga a participação sem apagar a linha, preservando o rastro
    de autoria e proveniência dos julgamentos realizados.
    """

    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        Index("ix_project_members_user", "user_id"),
        Index("ix_project_members_project", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="coordenador"
    )  # 'coordenador' | 'revisor' | 'observador'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    invited_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="members")
    user: Mapped["UserModel"] = relationship(
        foreign_keys=[user_id], back_populates="memberships"
    )


# ─────────────────────────────────────────────────────────────────────
# Convites de Projeto (doc 43 §43.3.2 — Pesquisa em Equipe)
# ─────────────────────────────────────────────────────────────────────

class ProjectInvitationModel(Base):
    """
    Convite para participação em projeto de revisão sistemática (§43.3.2).
    """

    __tablename__ = "project_invitations"
    __table_args__ = (
        UniqueConstraint("code", name="uq_project_invitations_code"),
        Index("ix_project_invitations_project", "project_id"),
        Index("ix_project_invitations_code", "code"),
        Index("ix_project_invitations_created_by", "created_by_user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="revisor"
    )  # 'coordenador' | 'revisor' | 'observador'
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="invitations")
    created_by: Mapped["UserModel"] = relationship(
        foreign_keys=[created_by_user_id]
    )
    accepted_by: Mapped["UserModel | None"] = relationship(
        foreign_keys=[accepted_by_user_id]
    )


# ─────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────
# Protocolo (Doc 45 — 4 Eixos Ortogonais)
# ─────────────────────────────────────────────────────────────────────

class ProtocolModel(Base):
    __tablename__ = "protocols"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True)
    mode: Mapped[str] = mapped_column(String(20), default="simplificado", nullable=False)  # 'simplificado' | 'completo'
    review_design: Mapped[str] = mapped_column(String(20), default="D4", nullable=False)  # 'D1'..'D14'
    reporting_guideline: Mapped[str] = mapped_column(String(50), default="PRISMA-ScR", nullable=False)  # 'PRISMA-2020' | 'PRISMA-ScR' | ...
    conduct_standards: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list
    question_framework: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON tipado (§7)
    objective: Mapped[str] = mapped_column(Text, default="")
    pico_framework: Mapped[str] = mapped_column(Text, default="{}")  # JSON string (legado / compatibilidade)
    search_descriptors: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    search_filters: Mapped[str] = mapped_column(Text, default="{}")  # JSON string para recorte temporal, idiomas, etc.
    manuscript_sections: Mapped[str] = mapped_column(Text, default="{}")  # JSON string para seções do manuscrito
    appraisal: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON {instrument, policy, notes}
    synthesis: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON {type, groupings, params}
    bibliometrics: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON (§11.2)
    status: Mapped[str] = mapped_column(String(20), default="rascunho", nullable=False)  # 'rascunho'|'vigente'|'concluido'
    current_version: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ex: 'v1.0'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="protocol")
    criteria: Mapped[list["CriterionModel"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    extraction_questions: Mapped[list["ExtractionQuestionModel"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    search_strategies: Mapped[list["SearchStrategyModel"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    search_executions: Mapped[list["SearchExecutionModel"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    versions: Mapped[list["ProtocolVersionModel"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    amendments: Mapped[list["ProtocolAmendmentModel"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    checklist_audits: Mapped[list["ChecklistAuditModel"]] = relationship(
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
    dimension: Mapped[str] = mapped_column(String(30), default="outro", nullable=False)  # 'populacao'|'desenho'|'periodo'|'idioma'|'tipo_doc'|'contexto'|'outro'
    applies_at: Mapped[str] = mapped_column(String(30), default="ambos", nullable=False)  # 'titulo_resumo' | 'texto_completo' | 'ambos'
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
    pdf_acquired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    merged_into_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # ── Estado de Consolidação da Triagem (Doc 43 §43.3.5) ───────────────
    # "legado" | "aguardando" | "parcial" | "consenso" | "conflito" | "resolvido"
    screening_status: Mapped[str] = mapped_column(
        String(20), default="aguardando", nullable=False
    )
    conflict_resolved_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    conflict_resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

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
    screenings: Mapped[list["PaperScreeningModel"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
    conflict_resolver: Mapped["UserModel | None"] = relationship(
        foreign_keys=[conflict_resolved_by_user_id]
    )


# ─────────────────────────────────────────────────────────────────────
# Julgamento de Triagem por Revisor (doc 43 §43.3.4 — Modo Cego & Colaborativo)
# ─────────────────────────────────────────────────────────────────────

class PaperScreeningModel(Base):
    """
    Julgamento individual de um revisor sobre um estudo.

    O coração da modalidade cega e da autoria de triagem. Em todas as modalidades,
    registra o parecer, observações e critérios avaliados pelo revisor específico.
    """

    __tablename__ = "paper_screenings"
    __table_args__ = (
        UniqueConstraint("paper_id", "reviewer_id", name="uq_paper_screenings_paper_reviewer"),
        Index("ix_paper_screenings_paper", "paper_id"),
        Index("ix_paper_screenings_reviewer", "reviewer_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    paper_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(20), default="Pendente", nullable=False)
    observations: Mapped[str] = mapped_column(Text, default="", nullable=False)
    criteria_evaluations: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON {criterion_id: bool}
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_assisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    paper: Mapped["PaperModel"] = relationship(back_populates="screenings")
    reviewer: Mapped["UserModel"] = relationship(foreign_keys=[reviewer_id])


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
    harvested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

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
    answer_type: Mapped[str] = mapped_column(String(30), default="texto", nullable=False)  # 'texto'|'numero'|'categoria'|'multipla'|'booleano'
    options: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    paper: Mapped["PaperModel"] = relationship(back_populates="extraction_answers")
    question: Mapped["ExtractionQuestionModel"] = relationship(back_populates="answers")


# ─────────────────────────────────────────────────────────────────────
# Estratégias de Busca Canônicas e Adaptadas por Base (Doc 45 §10, §14)
# ─────────────────────────────────────────────────────────────────────

class SearchStrategyModel(Base):
    __tablename__ = "search_strategies"
    __table_args__ = (
        Index("ix_search_strategies_protocol_kind", "protocol_id", "kind"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), default="canonica", nullable=False)  # 'canonica' | 'adaptacao'
    database: Mapped[str] = mapped_column(String(50), default="", nullable=False)  # '' para canônica ou 'BDTD', 'Scopus', etc.
    blocks: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list de blocos de conceito
    combination: Mapped[str] = mapped_column(String(255), default="", nullable=False)  # ex: 'A AND B AND C'
    target_fields: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list: ['title', 'abstract', 'keywords']
    limits: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON filtros: anos, idiomas, tipos, acesso aberto
    rendered_query: Mapped[str] = mapped_column(Text, default="", nullable=False)  # Query traduzida e pronta
    adaptation_note: Mapped[str] = mapped_column(Text, default="", nullable=False)  # Justificativa/nota técnica de adaptação
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    protocol: Mapped["ProtocolModel"] = relationship(back_populates="search_strategies")


# ─────────────────────────────────────────────────────────────────────
# Registro de Execuções de Busca por Base (Doc 45 §10.4, §10.5)
# ─────────────────────────────────────────────────────────────────────

class SearchExecutionModel(Base):
    __tablename__ = "search_executions"
    __table_args__ = (
        Index("ix_search_executions_protocol", "protocol_id"),
        Index("ix_search_executions_executed_at", "executed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False
    )
    harvest_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("harvest_runs.id", ondelete="SET NULL"), nullable=True
    )
    database: Mapped[str] = mapped_column(String(50), nullable=False)
    query_sent: Mapped[str] = mapped_column(Text, default="", nullable=False)
    filters: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON filtros efetivamente aplicados
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    records_returned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_after_dedup: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    protocol: Mapped["ProtocolModel"] = relationship(back_populates="search_executions")
    harvest_run: Mapped["HarvestRunModel | None"] = relationship(back_populates="search_executions")


# ─────────────────────────────────────────────────────────────────────
# Versionamento e Congelamento de Protocolo (Doc 45 §12, §14)
# ─────────────────────────────────────────────────────────────────────

class ProtocolVersionModel(Base):
    __tablename__ = "protocol_versions"
    __table_args__ = (
        Index("ix_protocol_versions_protocol", "protocol_id"),
        Index("ix_protocol_versions_label", "protocol_id", "label"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(50), nullable=False)  # ex: 'v1.0'
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)  # JSON completo canônico
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    frozen_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    protocol: Mapped["ProtocolModel"] = relationship(back_populates="versions")
    frozen_by: Mapped["UserModel | None"] = relationship(foreign_keys=[frozen_by_user_id])


# ─────────────────────────────────────────────────────────────────────
# Emendas ao Protocolo (Doc 45 §12.1, §14)
# ─────────────────────────────────────────────────────────────────────

class ProtocolAmendmentModel(Base):
    __tablename__ = "protocol_amendments"
    __table_args__ = (
        Index("ix_protocol_amendments_protocol", "protocol_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False
    )
    from_version: Mapped[str] = mapped_column(String(50), nullable=False)
    to_version: Mapped[str] = mapped_column(String(50), nullable=False)
    diff: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON com diferenças estruturadas
    reason: Mapped[str] = mapped_column(Text, nullable=False)  # Justificativa metodológica
    project_phase: Mapped[str] = mapped_column(String(50), default="coleta", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    protocol: Mapped["ProtocolModel"] = relationship(back_populates="amendments")
    created_by: Mapped["UserModel | None"] = relationship(foreign_keys=[created_by_user_id])


# ─────────────────────────────────────────────────────────────────────
# Auditoria de Conformidade com Checklist (Doc 45 §13.1, §14)
# ─────────────────────────────────────────────────────────────────────

class ChecklistAuditModel(Base):
    __tablename__ = "checklist_audits"
    __table_args__ = (
        UniqueConstraint("protocol_id", "guideline", "item_id", name="uq_checklist_audit_protocol_guideline_item"),
        Index("ix_checklist_audits_protocol_guideline", "protocol_id", "guideline"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False
    )
    guideline: Mapped[str] = mapped_column(String(50), nullable=False)  # 'PRISMA-ScR', 'PRISMA-2020', 'BIBLIO', etc.
    item_id: Mapped[str] = mapped_column(String(50), nullable=False)  # ex: '1', '2a', '7'
    state: Mapped[str] = mapped_column(String(20), default="pendente", nullable=False)  # 'atendido' | 'nao_aplica' | 'pendente'
    location: Mapped[str] = mapped_column(String(100), default="", nullable=False)  # ex: 'Pág. 3, Seção Métodos'
    justification: Mapped[str] = mapped_column(Text, default="", nullable=False)  # Obrigatória se nao_aplica
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    protocol: Mapped["ProtocolModel"] = relationship(back_populates="checklist_audits")
    updated_by: Mapped["UserModel | None"] = relationship(foreign_keys=[updated_by_user_id])


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
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_found: Mapped[int] = mapped_column(Integer, default=0)
    records_new: Mapped[int] = mapped_column(Integer, default=0)
    records_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Autoria da execução de coleta (Doc 43 §43.3.7, Fase 3)
    run_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    search_executions: Mapped[list["SearchExecutionModel"]] = relationship(
        back_populates="harvest_run"
    )

    project: Mapped["ProjectModel"] = relationship(back_populates="harvest_runs")
    runner: Mapped["UserModel | None"] = relationship(foreign_keys=[run_by_user_id])


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    paper: Mapped["PaperModel"] = relationship(back_populates="audit_logs")


# ─────────────────────────────────────────────────────────────────────
# Contas de Acesso e Sessões (doc 29 §29.3)
# ─────────────────────────────────────────────────────────────────────

class UserModel(Base):
    """
    Conta de acesso ao Revsist.

    A senha nunca é guardada — só o hash Argon2id, que `app/security/passwords`
    produz e verifica. `role` separa quem opera a revisão de quem administra as
    credenciais (§29.3.4).
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # Opcional desde o login com Google (doc 40 §40.4.2): uma conta criada por
    # OAuth não tem senha, e inventar uma seria pior — viraria uma credencial
    # que ninguém conhece e que mesmo assim autentica.
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="researcher", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Identidade (doc 40 §40.4.2) ────────────────────────────────────
    # Sem e-mail não há como responder a requisição de titular (art. 18),
    # recuperar conta, nem vincular a identidade que o Google devolve.
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # O identificador **estável** do Google. O vínculo é por ele, e não pelo
    # e-mail: dentro de um domínio corporativo um endereço pode ser reatribuído
    # a outra pessoa, e o `sub` não.
    google_sub: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), default="")
    # "password" | "google" | "both"
    auth_provider: Mapped[str] = mapped_column(
        String(20), default="password", nullable=False
    )
    # Prova do aceite dos Termos e do Aviso de Privacidade (art. 8º, §2º):
    # quando e de qual versão.
    terms_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    terms_version: Mapped[str] = mapped_column(String(20), default="")

    # ── Perfil Acadêmico e Cadastral ──────────────────────────────────
    full_name: Mapped[str] = mapped_column(String(200), default="", server_default="")
    phone: Mapped[str] = mapped_column(String(30), default="", server_default="")
    institution: Mapped[str] = mapped_column(String(200), default="", server_default="")
    academic_degree: Mapped[str] = mapped_column(String(50), default="", server_default="")
    is_studying: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    study_program: Mapped[str] = mapped_column(String(200), default="", server_default="")
    profession: Mapped[str] = mapped_column(String(100), default="", server_default="")
    research_area: Mapped[str] = mapped_column(String(200), default="", server_default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list["SessionModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["ProjectMemberModel"]] = relationship(
        foreign_keys="ProjectMemberModel.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class InviteCodeModel(Base):
    """
    Convite de uso único para cadastro de pesquisador.

    Garante que apenas convidados consigam se registrar. Ao concluir o cadastro,
    o convite é marcado como utilizado (is_used=True) e associado ao usuário.
    """

    __tablename__ = "invites"
    __table_args__ = (
        Index("ix_invites_code", "code"),
        Index("ix_invites_is_used", "is_used"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=True
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="")


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
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
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OAuthStateModel(Base):
    """
    Estado de uma autenticação com Google em curso (doc 40 §40.4.1).

    Guardar isto no servidor — e não num cookie assinado — é a mesma decisão
    que levou o Revsist a usar sessão com estado em vez de JWT: o que está no
    banco pode ser invalidado na hora. Aqui isso importa porque o `state` é de
    **uso único**: ele é apagado ao ser consumido, o que fecha a repetição do
    callback. Um cookie assinado continuaria válido até vencer.

    O `code_verifier` é a metade privada do PKCE. Nunca sai do servidor: o que
    vai ao Google é o desafio (o SHA-256 dele), e é a apresentação do
    verificador na troca que prova que quem resgata o código é quem o pediu.
    """

    __tablename__ = "oauth_states"
    __table_args__ = (Index("ix_oauth_states_expires_at", "expires_at"),)

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    # Caminho **interno** para onde voltar depois do login. Nunca uma URL
    # absoluta: aceitar uma faria do callback um redirecionador aberto, e o
    # link de login viraria isca de phishing com o domínio do Revsist na barra.
    redirect_after: Mapped[str] = mapped_column(String(200), default="/app")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ─────────────────────────────────────────────────────────────────────
# Configurações de Fontes / Credenciais de Coleta (Scopus, PubMed, etc.)
# ─────────────────────────────────────────────────────────────────────

class SourceCredentialModel(Base):
    """
    Credencial de base científica — **por usuário e por fonte**.

    `source_name` era único no banco inteiro, então o token institucional de
    uma universidade servia a todas as outras contas — o que, além do
    vazamento, viola o contrato de licença da base (doc 39, O-03).
    """

    __tablename__ = "source_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "source_name", name="uq_source_credentials_user_source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key: Mapped[str] = mapped_column(EncryptedText, default="")
    inst_token: Mapped[str] = mapped_column(EncryptedText, default="")
    custom_endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# ─────────────────────────────────────────────────────────────────────
# Configurações de IA (persistidas)
# ─────────────────────────────────────────────────────────────────────

class AISettingsModel(Base):
    """
    Configuração de IA — **uma por usuário**.

    Era uma linha só no banco inteiro, lida em dez pontos como
    `db.query(AISettingsModel).first()`. Com contas individuais e chave do
    próprio assinante (BYOK), isso significava que o segundo a salvar
    sobrescrevia a chave do primeiro, e que a triagem de um rodava na cota paga
    do outro (doc 39, O-02).
    """

    __tablename__ = "ai_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="deduplication_reports")



# ─────────────────────────────────────────────────────────────────────
# Registro das Operações de Tratamento — ROPA (doc 40 §40.5.2, L-60)
# ─────────────────────────────────────────────────────────────────────

class ProcessingRecordModel(Base):
    """
    O que o Revsist fez com dado pessoal, quando, sob qual base legal.

    É o registro que o art. 37 da LGPD exige do controlador, e o que se
    apresenta à ANPD quando ela pergunta. Não se confunde com o
    `AuditLogModel`, que guarda decisões metodológicas sobre estudos: aquele
    responde "por que este artigo foi excluído", este responde "com que
    fundamento vocês trataram o dado desta pessoa".

    Regra dura: o que houve, nunca o que era
    ========================================
    O ROPA registra **que** houve tratamento e de que **categoria** era o dado
    — nunca o dado. Um registro de auditoria que copia o dado pessoal é mais um
    lugar de onde ele vaza, e o pior deles: fica de fora do `DELETE /me`, porque
    precisa sobreviver a ele.

    A garantia não é de boa vontade. `data_categories` só aceita nomes de uma
    lista fechada (`app/services/ropa_service.py`), então não há por onde passar
    um e-mail: ele não é uma categoria válida, e a gravação levanta exceção.

    Por que `user_id` não é chave estrangeira
    =========================================
    De propósito, e não por esquecimento. O registro precisa sobreviver à
    eliminação da conta — é justamente ele que prova que a eliminação
    aconteceu, e em que data. Com `ON DELETE CASCADE` o `DELETE /me` apagaria a
    prova de si mesmo; com `SET NULL`, restaria um registro que não se sabe de
    quem foi, o que é o mesmo que não ter registro.

    Depois que a conta some, o UUID que fica aqui não identifica ninguém: as
    colunas que identificavam — e-mail, nome, `google_sub` — foram embora com a
    linha de `users`. O que resta é uma referência pseudônima, que é
    exatamente o que a prestação de contas do art. 6º X precisa.
    """

    __tablename__ = "processing_records"
    __table_args__ = (
        Index("ix_processing_records_user", "user_id"),
        Index("ix_processing_records_occurred", "occurred_at"),
        Index("ix_processing_records_operation", "operation"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Titular ou operador envolvido. Sem FK — ver o docstring. Nulo quando a
    # operação não tem titular identificado (ex.: tentativa de login que não
    # chegou a resolver uma conta).
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(300), nullable=False)

    # Lista JSON de nomes de categoria. Nunca valores.
    data_categories: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Destinatário, quando houver (ex.: `google_gemini`). Nulo em operação
    # que não sai do Revsist.
    recipient: Mapped[str | None] = mapped_column(String(64), nullable=True)
    international: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# ─────────────────────────────────────────────────────────────────────
# Bibliometria — Instantâneo do corpus (doc 48 §3)
# ─────────────────────────────────────────────────────────────────────

class BibSnapshotModel(Base):
    """O corpus congelado sobre o qual um indicador foi calculado.

    Um indicador bibliométrico é uma afirmação sobre um conjunto. O acervo
    muda todo dia — coleta, deduplicação, triagem, resolução de conflito —,
    então um número obtido na terça não é reproduzível na quinta, e nada na
    tela registrava sobre que corpus ele havia sido obtido (doc 47 §B-05).

    O instantâneo **não copia o acervo**: copiar dezenas de milhares de linhas
    por análise seria inviável e desnecessário. Ele guarda um manifesto —
    para cada documento no escopo, o par `(paper_id, hash_do_conteúdo)` — e o
    hash do manifesto inteiro. Ao reabrir a análise, recomputa-se e compara-se:
    idêntico, conteúdo alterado, ou conjunto alterado. Os três desfechos são
    informação, e nenhum deles recomputa em silêncio.
    """

    __tablename__ = "bib_snapshots"
    __table_args__ = (
        Index("ix_bib_snapshots_project", "project_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    #: Como a pessoa reconhece este instantâneo depois ("Análise principal").
    label: Mapped[str] = mapped_column(Text, default="", nullable=False)

    #: Filtros que definiram o corpus, em JSON — os mesmos da aba de
    #: Indicadores (doc 32 §3.2). É o que permite recriar o escopo.
    scope: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    n_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    #: sha256 do manifesto ordenado. A identidade do corpus.
    corpus_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    #: Manifesto comprimido: `paper_id\x1fconteudo_hash` por linha, ordenado
    #: por `paper_id`. Guardado para poder dizer QUAIS documentos mudaram, e
    #: não apenas que algo mudou.
    manifest: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    #: Versão do código que calcula indicadores. Entra na proveniência de toda
    #: figura, porque uma mudança aqui pode mudar um número.
    engine_version: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


# ─────────────────────────────────────────────────────────────────────
# Bibliometria — Enriquecimento externo (doc 48 §4, doc 49 Fase 2)
# ─────────────────────────────────────────────────────────────────────

class BibEnrichmentModel(Base):
    """Sessão de enriquecimento externo de um projeto."""

    __tablename__ = "bib_enrichments"
    __table_args__ = (
        Index("ix_bib_enrichments_project", "project_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), default="openalex", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    n_consulted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    n_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="em_andamento", nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class BibWorkMetaModel(Base):
    """Metadados estendidos da obra (OpenAlex / Crossref)."""

    __tablename__ = "bib_work_meta"
    __table_args__ = (
        Index("ix_bib_work_meta_external_id", "external_id"),
    )

    paper_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    enrichment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("bib_enrichments.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="openalex", nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cited_by_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referenced_works_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_oa: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    oa_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    raw: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    obtained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class BibReferenceModel(Base):
    """Referências citadas por cada documento (fecha B-03)."""

    __tablename__ = "bib_references"
    __table_args__ = (
        Index("ix_bib_references_citing", "citing_paper_id"),
        Index("ix_bib_references_cited_external", "cited_external_id"),
        Index("ix_bib_references_cited_doi", "cited_doi"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    citing_paper_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    cited_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cited_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)


class BibAuthorshipModel(Base):
    """Afiliação e autoria resolvida institucionalmente com ROR (fecha B-01)."""

    __tablename__ = "bib_authorships"
    __table_args__ = (
        Index("ix_bib_authorships_paper", "paper_id"),
        Index("ix_bib_authorships_ror", "institution_ror"),
        Index("ix_bib_authorships_author", "author_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    author_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_name: Mapped[str] = mapped_column(Text, default="", nullable=False)
    institution_ror: Mapped[str | None] = mapped_column(String(100), nullable=True)
    institution_name: Mapped[str] = mapped_column(Text, default="", nullable=False)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)


class BibTopicModel(Base):
    """Tópicos temáticos com scores de relevância (OpenAlex)."""

    __tablename__ = "bib_topics"
    __table_args__ = (
        Index("ix_bib_topics_paper", "paper_id"),
        Index("ix_bib_topics_topic", "topic_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    topic_name: Mapped[str] = mapped_column(Text, default="", nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class BibKeywordModel(Base):
    """Palavras-chave com procedência declarada (fecha B-02)."""

    __tablename__ = "bib_keywords"
    __table_args__ = (
        Index("ix_bib_keywords_paper", "paper_id"),
        Index("ix_bib_keywords_term", "term"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    term: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="openalex", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# ── Camada de Texto e Tesauro (Fase 4, doc 48 §5, §12) ──────────────────


class BibTextoModel(Base):
    """Texto limpo extraído do PDF com mapa de seções IMRaD e contagem (fecha B-04)."""

    __tablename__ = "bib_textos"
    __table_args__ = (
        Index("ix_bib_textos_pipeline_version", "pipeline_version"),
    )

    paper_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    pipeline_version: Mapped[str] = mapped_column(String(32), default="2.0.0", nullable=False)
    pdf_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    n_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    n_words: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    text_clean: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON com lista de seções
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BibThesaurusModel(Base):
    """Tesauros e vocabulários controlados por projeto (fecha B-06)."""

    __tablename__ = "bib_thesauri"
    __table_args__ = (
        Index("ix_bib_thesauri_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BibThesaurusEntryModel(Base):
    """Entradas do tesauro mapeando termo preferido e variantes aprovadas (doc 48 §6.1)."""

    __tablename__ = "bib_thesaurus_entries"
    __table_args__ = (
        Index("ix_bib_thesaurus_entries_thesaurus_id", "thesaurus_id"),
        Index("ix_bib_thesaurus_entries_preferred_term", "preferred_term"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    thesaurus_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bib_thesauri.id", ondelete="CASCADE"), nullable=False
    )
    preferred_term: Mapped[str] = mapped_column(String(255), nullable=False)
    variants: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON com lista de strings
    scope: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    proposed_by: Mapped[str] = mapped_column(String(128), default="manual", nullable=False)  # "ai" ou user_id
    approved_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ── Instrumentos de Medida e Evidências (Fase 5, doc 48 §6, §12) ─────────


class BibInstrumentoModel(Base):
    """Instrumento conceitual com léxico e porta de aprovação humana (fecha B-07)."""

    __tablename__ = "bib_instrumentos"
    __table_args__ = (
        Index("ix_bib_instrumentos_project_id", "project_id"),
        Index("ix_bib_instrumentos_concept", "concept"),
        Index("ix_bib_instrumentos_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    concept: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lexicon: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON com modo, incluir, excluir, janela
    version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="rascunho", nullable=False)  # rascunho / aprovado / arquivado
    proposed_by: Mapped[str] = mapped_column(String(128), default="manual", nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision_ci: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON [lower, upper]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BibMedidaModel(Base):
    """Execução de contagem determinística oficial sobre corpus/instantâneo com denominador."""

    __tablename__ = "bib_medidas"
    __table_args__ = (
        Index("ix_bib_medidas_instrument_id", "instrument_id"),
        Index("ix_bib_medidas_snapshot_id", "snapshot_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    snapshot_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("bib_snapshots.id", ondelete="SET NULL"), nullable=True
    )
    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bib_instrumentos.id", ondelete="CASCADE"), nullable=False
    )
    instrument_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    result: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON com frequências e distribuição
    n_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    n_documents_with_text: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BibOcorrenciaModel(Base):
    """Ocorrência textual ancorada em documento, seção IMRaD, página e offset (doc 48 §6.6)."""

    __tablename__ = "bib_ocorrencias"
    __table_args__ = (
        Index("ix_bib_ocorrencias_measurement_id", "measurement_id"),
        Index("ix_bib_ocorrencias_paper_id", "paper_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    measurement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bib_medidas.id", ondelete="CASCADE"), nullable=False
    )
    paper_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False
    )
    section: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_form: Mapped[str] = mapped_column(Text, nullable=False)
    context_snippet: Mapped[str] = mapped_column(Text, default="", nullable=False)


# ── Grafos e Análise Estrutural (Fase 6, doc 48 §8, §12) ─────────────────


class BibGrafoModel(Base):
    """Grafo bibliométrico determinístico com layout espacial e comunidades Louvain (fecha B-08)."""

    __tablename__ = "bib_grafos"
    __table_args__ = (
        Index("ix_bib_grafos_project_id", "project_id"),
        Index("ix_bib_grafos_snapshot_id", "snapshot_id"),
        Index("ix_bib_grafos_network_type", "network_type"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("bib_snapshots.id", ondelete="SET NULL"), nullable=True
    )
    network_type: Mapped[str] = mapped_column(String(50), nullable=False)  # coautoria / coocorrencia_termos / acoplamento_bibliografico / cocitacao
    parameters: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # normalizacao, resolucao, corte, semente, iteracoes
    nodes: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON lista de nós
    edges: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON lista de arestas
    coordinates: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON coordenadas { node_id: {x, y} }
    clusters: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON metadados de clusters
    seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ── Estatística Sob Demanda (Fase 7, doc 48 §9, §12) ─────────────────────


class BibAnaliseModel(Base):
    """Análise estatística sob demanda salva e reexecutável (doc 48 §9.3)."""

    __tablename__ = "bib_analises"
    __table_args__ = (
        Index("ix_bib_analises_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    specification: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON validado contra esquema fechado
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )





