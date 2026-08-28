#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Database Engine e Session Management.

O engine é derivado do **dialeto da URL**, e não fixado em SQLite (doc 40
§40.2.2). A razão é que o Revsist passou a ter dois bancos legítimos: SQLite no
perfil `desktop`, onde é a escolha certa — um arquivo, zero administração —,
e PostgreSQL no perfil `server`, onde um arquivo único em WAL com coleta e
triagem concorrentes de vários assinantes vira contenção e ponto único de
corrupção.

Nada aqui decide qual banco usar. Quem decide é `settings.effective_database_url`,
e este módulo apenas se adapta ao que recebe.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


# ── Dialeto ───────────────────────────────────────────────────────────

def _is_sqlite(url: str) -> bool:
    """
    O dialeto é lido da URL, não do perfil de implantação.

    Separar as duas coisas é deliberado: a suíte de testes roda o perfil `ci`
    contra os dois bancos, e amarrar o dialeto ao perfil tornaria essa
    verificação impossível de escrever.
    """
    return make_url(url).get_backend_name() == "sqlite"


# ── Engine ────────────────────────────────────────────────────────────

def _build_engine(url: str) -> Engine:
    """
    Constrói o engine com os argumentos que **aquele** dialeto aceita.

    `check_same_thread` e `timeout` são argumentos do driver do SQLite; passá-los
    ao psycopg levanta `TypeError` na primeira conexão. O caminho inverso é
    igualmente verdadeiro: `pool_size` não se aplica ao `SingletonThreadPool`
    que o SQLite usa em arquivo.
    """
    if _is_sqlite(url):
        return create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 30},
            echo=settings.debug,
            pool_pre_ping=True,
        )

    return create_engine(
        url,
        echo=settings.debug,
        pool_pre_ping=True,
        # Dimensionado para o desenho de um worker do doc 40 §40.6: o trabalho
        # do Revsist é espera de rede, não CPU, e um laço de eventos sozinho não
        # consome mais que isto de conexões simultâneas.
        pool_size=5,
        max_overflow=10,
        # Devolve conexões antes do tempo em que um proxy ou o próprio
        # PostgreSQL as encerraria por ociosidade.
        pool_recycle=1800,
    )


engine = _build_engine(settings.effective_database_url)


def _register_sqlite_pragmas(target: Engine) -> None:
    """
    Aplica os PRAGMAs de SQLite na conexão.

    Fica atrás de uma verificação de dialeto porque antes era um listener
    global: em PostgreSQL, ele executava `PRAGMA journal_mode=WAL` em **toda**
    conexão nova e derrubava o pool inteiro.
    """

    @event.listens_for(target, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.close()


if _is_sqlite(settings.effective_database_url):
    _register_sqlite_pragmas(engine)


# ── Session Factory ───────────────────────────────────────────────────

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency injection para FastAPI — fornece uma sessão de banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Esquema ───────────────────────────────────────────────────────────

def create_tables() -> None:
    """
    Sincroniza o esquema do banco.

    Em produção quem manda é o Alembic (`app/schema.py`, chamado no `lifespan`).
    Esta função permanece para os testes, que criam um banco descartável por
    execução e não têm por que pagar o custo de uma cadeia de migrações — e
    para o perfil `desktop`, onde a migração também roda, mas o `create_all`
    é a rede de segurança de um banco recém-criado.
    """
    from app.infrastructure.persistence.models import Base

    logger.info(f"Sincronizando tabelas no banco: {settings.effective_database_url}")
    Base.metadata.create_all(bind=engine)
    logger.info("Tabelas sincronizadas com sucesso.")


def drop_tables() -> None:
    """Remove todas as tabelas (CUIDADO — apenas para testes)."""
    from app.infrastructure.persistence.models import Base

    Base.metadata.drop_all(bind=engine)
