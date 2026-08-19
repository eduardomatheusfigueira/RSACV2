#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — FastAPI Application Factory.
Ponto de entrada do backend — cria e configura a aplicação FastAPI,
logging estruturado em arquivo e reconciliação de jobs no ciclo de vida (lifespan).
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.config import settings
from app.database import SessionLocal, create_tables
from app.infrastructure.persistence.models import HarvestRunModel
from app.schemas.common import HealthResponse

# ── Logging Estruturado (Console + Arquivo) ───────────────────────────

log_dir = Path(settings.data_dir) / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "harvest.log"

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("rsac")


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia startup e shutdown da aplicação."""
    # Startup
    logger.info(f"RSAC Backend v{settings.app_version} iniciando...")
    logger.info(f"Banco de dados: {settings.effective_database_url}")
    logger.info(f"Arquivo de log: {log_file}")
    create_tables()

    # Reconciliar execuções pendentes interrompidas por queda/reinício do processo
    try:
        db = SessionLocal()
        interrupted_runs = (
            db.query(HarvestRunModel)
            .filter(HarvestRunModel.status == "running")
            .all()
        )
        if interrupted_runs:
            logger.warning(
                f"[Lifespan] Reconciliando {len(interrupted_runs)} coleta(s) que ficaram com status 'running'."
            )
            for run in interrupted_runs:
                run.status = "failed"
                run.error_message = "Interrompida por reinício do servidor."
                run.completed_at = datetime.now(timezone.utc)
            db.commit()
        db.close()
    except Exception as e:
        logger.error(f"[Lifespan] Erro ao reconciliar execuções de coleta: {e}")

    logger.info("Backend pronto para receber requisições.")
    yield
    # Shutdown
    logger.info("Backend encerrando...")


# ── App Factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""
    app = FastAPI(
        title="RSAC API",
        description="Revisão Sistemática Assistida por Computador — Backend API",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS — suporte completo para navegadores, Netlify e ambientes locais
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Health check no root
    @app.get("/health", response_model=HealthResponse, tags=["system"], include_in_schema=False)
    def root_health():
        return HealthResponse(
            status="ok",
            version=settings.app_version,
            database="connected",
        )

    # Incluir routers
    app.include_router(api_router, prefix="/api/v1")

    # Servir Frontend Web Estático (SPA) se construído
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/favicon.svg", include_in_schema=False)
        async def serve_favicon():
            return FileResponse(frontend_dist / "favicon.svg")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            if full_path.startswith("api") or full_path in ("health", "docs", "redoc", "openapi.json"):
                raise HTTPException(status_code=404, detail="Not Found")
            file_path = frontend_dist / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(frontend_dist / "index.html")

    return app


# Instância global
app = create_app()

