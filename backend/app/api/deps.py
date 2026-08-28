#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Dependências compartilhadas da API (Dependency Injection)."""

from typing import Generator

from sqlalchemy.orm import Session

from app.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão de banco de dados para cada request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
