#!/usr/bin/env python

"""Revsist — Router agregador da API v1."""

from fastapi import APIRouter, Depends

from app.api.v1.ai import router as ai_router
from app.api.v1.auth import public_auth_router
from app.api.v1.auth import router as auth_router
from app.api.v1.deduplication import router as deduplication_router
from app.api.v1.export import router as export_router
from app.api.v1.extraction import (
    project_extraction_router,
)
from app.api.v1.extraction import (
    router as extraction_router,
)
from app.api.v1.harvest import router as harvest_router
from app.api.v1.insights import router as insights_router
from app.api.v1.me import router as me_router
from app.api.v1.papers import router as papers_router
from app.api.v1.profile import router as profile_router
from app.api.v1.projects import router as projects_router
from app.api.v1.protocols import router as protocols_router
from app.api.v1.screening_ai import router as screening_ai_router
from app.api.v1.settings import router as settings_router
from app.config import settings
from app.schemas.common import HealthResponse
from app.security.dependencies import require_session

# ── As duas metades da API ────────────────────────────────────────────
#
# `public_router` é a lista **completa** de exceções de §29.3.1 — health,
# status da autenticação, login e troca do token local. Nada mais entra aqui.
#
# `api_router` exige sessão por dependência do próprio router, e não por
# decorador em cada rota. É essa escolha que torna a proteção durável: uma rota
# nova nasce autenticada, e esquecer de protegê-la deixou de ser possível.
public_router = APIRouter()
api_router = APIRouter(dependencies=[Depends(require_session)])


@public_router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check():
    """Health check do backend. Não expõe dado de negócio."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        database="connected",
    )


public_router.include_router(public_auth_router)


# Incluir sub-routers
api_router.include_router(auth_router)
api_router.include_router(me_router)
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
api_router.include_router(insights_router)
api_router.include_router(profile_router)


