#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Database Engine e Session Management.
Configura SQLAlchemy engine com SQLite WAL mode e gerenciamento de sessões.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.infrastructure.persistence.models import Base

logger = logging.getLogger(__name__)

# ── Engine ────────────────────────────────────────────────────────────

engine = create_engine(
    settings.effective_database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Configura PRAGMAs do SQLite para performance e integridade."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
    cursor.close()


# ── Session Factory ───────────────────────────────────────────────────

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency injection para FastAPI — fornece uma sessão de banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Criação de Tabelas ────────────────────────────────────────────────

def create_tables() -> None:
    """Cria todas as tabelas no banco de dados (desenvolvimento)."""
    logger.info(f"Criando tabelas no banco: {settings.effective_database_url}")
    Base.metadata.create_all(bind=engine)
    logger.info("Tabelas criadas com sucesso.")


def drop_tables() -> None:
    """Remove todas as tabelas (CUIDADO — apenas para testes)."""
    Base.metadata.drop_all(bind=engine)
