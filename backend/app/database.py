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


# ── Criação de Tabelas e Migrações Automáticas ───────────────────────

def _migrate_missing_columns() -> None:
    """
    Migra automaticamente colunas novas adicionadas aos modelos ORM para bancos
    SQLite já existentes, evitando erros de 'table has no column named...'.
    """
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        with engine.connect() as conn:
            for table_name, table in Base.metadata.tables.items():
                if table_name in existing_tables:
                    existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                    for column in table.columns:
                        if column.name not in existing_columns:
                            col_type = column.type.compile(engine.dialect)
                            default_clause = ""
                            if column.default is not None and hasattr(column.default, "arg"):
                                arg = column.default.arg
                                if isinstance(arg, str):
                                    default_clause = f" DEFAULT '{arg}'"
                                elif isinstance(arg, (int, float)):
                                    default_clause = f" DEFAULT {arg}"
                                elif isinstance(arg, bool):
                                    default_clause = " DEFAULT 1" if arg else " DEFAULT 0"
                            elif str(col_type).upper().startswith("TEXT") or str(col_type).upper().startswith("VARCHAR"):
                                default_clause = " DEFAULT ''"

                            sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}{default_clause}"
                            logger.info(f"Migração automática de esquema: {sql}")
                            conn.execute(text(sql))
                            conn.commit()
                            logger.info(f"Coluna '{column.name}' adicionada à tabela '{table_name}' com sucesso.")
    except Exception as e:
        logger.warning(f"Aviso na verificação de migrações automáticas: {e}")


def create_tables() -> None:
    """Cria todas as tabelas e sincroniza colunas no banco de dados."""
    logger.info(f"Sincronizando tabelas no banco: {settings.effective_database_url}")
    Base.metadata.create_all(bind=engine)
    _migrate_missing_columns()
    logger.info("Tabelas e colunas sincronizadas com sucesso.")


def drop_tables() -> None:
    """Remove todas as tabelas (CUIDADO — apenas para testes)."""
    Base.metadata.drop_all(bind=engine)

