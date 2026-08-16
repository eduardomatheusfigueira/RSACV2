# 10 — Banco de Dados

> Modelagem relacional, ORM SQLAlchemy, migrações Alembic e estratégia de cache.

---

## 10.1 Decisão: SQLite

| Critério | SQLite | PostgreSQL |
|----------|:------:|:----------:|
| Zero configuração | ✅ | ❌ |
| Arquivo local (portável) | ✅ | ❌ |
| Não requer serviço rodando | ✅ | ❌ |
| Transações ACID | ✅ | ✅ |
| Full-text search | ✅ (FTS5) | ✅ |
| Concorrência de escrita | ⚠️ WAL mode | ✅ |
| Cross-platform | ✅ | ✅ |

**Decisão**: 🟢 **SQLite** com WAL mode — adequado para aplicação single-user desktop.

> Se no futuro houver necessidade de versão web multi-usuário, a abstração via SQLAlchemy permite migrar para PostgreSQL sem alterar código de domínio.

---

## 10.2 SQLAlchemy Models (ORM)

```python
# infrastructure/persistence/models.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float,
    DateTime, ForeignKey, Enum as SAEnum, JSON, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from app.domain.enums import Decision, Methodology, HarvestStatus


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    methodology: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    protocol: Mapped["ProtocolModel"] = relationship(back_populates="project", uselist=False)
    papers: Mapped[list["PaperModel"]] = relationship(back_populates="project")
    harvest_runs: Mapped[list["HarvestRunModel"]] = relationship(back_populates="project")


class ProtocolModel(Base):
    __tablename__ = "protocols"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True)
    objective: Mapped[str] = mapped_column(Text, default="")
    pico_framework: Mapped[dict] = mapped_column(JSON, default=dict)
    search_descriptors: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="protocol")
    criteria: Mapped[list["CriterionModel"]] = relationship(back_populates="protocol")
    extraction_questions: Mapped[list["ExtractionQuestionModel"]] = relationship(back_populates="protocol")


class CriterionModel(Base):
    __tablename__ = "criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol_id: Mapped[str] = mapped_column(ForeignKey("protocols.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_exclusion: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    protocol: Mapped["ProtocolModel"] = relationship(back_populates="criteria")
    paper_evaluations: Mapped[list["PaperCriterionModel"]] = relationship(back_populates="criterion")


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
    title_normalized: Mapped[str] = mapped_column(Text, default="")  # Para deduplicação
    authors: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[str] = mapped_column(String(10), default="")
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    abstract: Mapped[str] = mapped_column(Text, default="")
    research_type: Mapped[str] = mapped_column(String(100), default="")
    institution: Mapped[str] = mapped_column(Text, default="")
    download_url: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(String(20), default=Decision.PENDING.value)
    observations: Mapped[str] = mapped_column(Text, default="")
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    project: Mapped["ProjectModel"] = relationship(back_populates="papers")
    sources: Mapped[list["PaperSourceModel"]] = relationship(back_populates="paper")
    criteria_evaluations: Mapped[list["PaperCriterionModel"]] = relationship(back_populates="paper")
    extraction_answers: Mapped[list["ExtractionAnswerModel"]] = relationship(back_populates="paper")
    audit_logs: Mapped[list["AuditLogModel"]] = relationship(back_populates="paper")


class PaperSourceModel(Base):
    __tablename__ = "paper_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)  # BDTD, SciELO, etc.
    source_id: Mapped[str] = mapped_column(String(200), default="")  # ID na base original
    harvested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    paper: Mapped["PaperModel"] = relationship(back_populates="sources")


class PaperCriterionModel(Base):
    __tablename__ = "paper_criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    criterion_id: Mapped[str] = mapped_column(ForeignKey("criteria.id"))
    value: Mapped[bool] = mapped_column(Boolean, nullable=False)

    paper: Mapped["PaperModel"] = relationship(back_populates="criteria_evaluations")
    criterion: Mapped["CriterionModel"] = relationship(back_populates="paper_evaluations")


class ExtractionQuestionModel(Base):
    __tablename__ = "extraction_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    protocol_id: Mapped[str] = mapped_column(ForeignKey("protocols.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    protocol: Mapped["ProtocolModel"] = relationship(back_populates="extraction_questions")
    answers: Mapped[list["ExtractionAnswerModel"]] = relationship(back_populates="question")


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


class HarvestRunModel(Base):
    __tablename__ = "harvest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    descriptors_used: Mapped[dict] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    records_found: Mapped[int] = mapped_column(Integer, default=0)
    records_new: Mapped[int] = mapped_column(Integer, default=0)
    records_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["ProjectModel"] = relationship(back_populates="harvest_runs")


class AuditLogModel(Base):
    """Log de auditoria para rastreabilidade de decisões."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # "decision_changed", "criteria_updated"
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # "manual" | "ai"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    paper: Mapped["PaperModel"] = relationship(back_populates="audit_logs")


class AISettingsModel(Base):
    """Configurações de IA persistidas."""
    __tablename__ = "ai_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    api_keys_encrypted: Mapped[str] = mapped_column(Text, default="")  # JSON array encriptado
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.3)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
```

---

## 10.3 Alembic — Schema Migrations

### Configuração Inicial

```bash
# Dentro do diretório backend/
alembic init alembic
```

### Gerar Migração

```bash
alembic revision --autogenerate -m "initial schema"
```

### Aplicar Migrações (automático no startup)

```python
# database.py

from alembic.config import Config
from alembic import command

def run_migrations():
    """Executa migrações pendentes automaticamente no startup."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

---

## 10.4 Database Session Management

```python
# database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from app.config import settings

engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},  # SQLite + async
    echo=settings.debug,
)

# Habilitar WAL mode para melhor concorrência
with engine.connect() as conn:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db() -> Session:
    """Dependency injection para FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 10.5 Full-Text Search (FTS5)

```sql
-- Migração para criar tabela FTS5 para busca em papers
CREATE VIRTUAL TABLE papers_fts USING fts5(
    title,
    authors,
    abstract,
    content='papers',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);

-- Trigger para manter FTS atualizado
CREATE TRIGGER papers_ai AFTER INSERT ON papers BEGIN
    INSERT INTO papers_fts(rowid, title, authors, abstract)
    VALUES (new.rowid, new.title, new.authors, new.abstract);
END;
```

---

## 10.6 Localização do Banco

```python
# config.py

from pydantic_settings import BaseSettings
from pathlib import Path
import platformdirs

class Settings(BaseSettings):
    app_name: str = "RSAC"
    debug: bool = False

    @property
    def data_dir(self) -> Path:
        """Diretório de dados da aplicação (cross-platform)."""
        return Path(platformdirs.user_data_dir(self.app_name))

    @property
    def database_path(self) -> Path:
        """Caminho do banco SQLite."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "rsac.db"
```
