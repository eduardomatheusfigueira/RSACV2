#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Schemas comuns (paginação, erros, etc.)."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Resposta de erro padronizada."""
    detail: str
    error_code: str | None = None


class HealthResponse(BaseModel):
    """Resposta do health check."""
    status: str = "ok"
    version: str
    database: str = "connected"


class PaginatedResponse(BaseModel, Generic[T]):
    """Resposta paginada genérica."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatsResponse(BaseModel):
    """Estatísticas de um projeto."""
    total_papers: int = 0
    included_papers: int = 0
    excluded_papers: int = 0
    pending_papers: int = 0
    total_harvest_runs: int = 0
    sources: dict[str, int] = {}
