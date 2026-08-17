#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router agregador da API v1."""

from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.deduplication import router as deduplication_router
from app.api.v1.export import router as export_router
from app.api.v1.extraction import (
    project_extraction_router,
    router as extraction_router,
)
from app.api.v1.harvest import router as harvest_router
from app.api.v1.papers import router as papers_router
from app.api.v1.profile import router as profile_router
from app.api.v1.projects import router as projects_router
from app.api.v1.protocols import router as protocols_router
from app.api.v1.screening_ai import router as screening_ai_router
from app.api.v1.settings import router as settings_router
from app.config import settings
from app.schemas.common import HealthResponse

api_router = APIRouter()


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check():
    """Health check do backend."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        database="connected",
    )


# Incluir sub-routers
api_router.include_router(projects_router)
api_router.include_router(protocols_router)
api_router.include_router(papers_router)
api_router.include_router(harvest_router)
api_router.include_router(deduplication_router)
api_router.include_router(settings_router)
api_router.include_router(ai_router)
api_router.include_router(screening_ai_router)
api_router.include_router(extraction_router)
api_router.include_router(project_extraction_router)
api_router.include_router(export_router)
api_router.include_router(profile_router)

