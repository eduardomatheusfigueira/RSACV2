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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.database import SessionLocal, create_tables
from app.infrastructure.persistence.models import HarvestRunModel

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

    # CORS — aceita apenas origens locais
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Permissivo em dev; Electron usa localhost
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Incluir routers
    app.include_router(api_router, prefix="/api/v1")

    return app


# Instância global
app = create_app()
