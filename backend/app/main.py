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

from app.api.v1.router import api_router, public_router
from app.config import settings
from app.database import SessionLocal, create_tables
from app.infrastructure.persistence.models import HarvestRunModel, UserModel
from app.security.local_token import descrever_para_log, ensure_local_token
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
    logger.info(f"Perfil de implantação: {settings.deployment_profile.value}")
    if settings.is_server_profile:
        logger.warning(
            "[Segurança] Perfil 'server': o backend está exposto fora do loopback. "
            "O acesso exige conta e senha; publique o endereço apenas para quem "
            "deve operar a revisão."
        )
    logger.info(f"Banco de dados: {settings.effective_database_url}")
    logger.info(f"Arquivo de log: {log_file}")
    create_tables()

    # ── Portão de partida segura (doc 29 §29.2.4) ─────────────────────
    #
    # Um servidor público sem autenticação não deve ser um estado alcançável
    # do sistema. Se o perfil é `server` e não há conta provisionada, o
    # processo recusa-se a subir — em vez de subir aberto, como acontecia.
    ensure_local_token()
    logger.info(f"Autenticação: {descrever_para_log()}")

    db_boot = SessionLocal()
    try:
        contas_ativas = (
            db_boot.query(UserModel).filter(UserModel.is_active == True).count()  # noqa: E712
        )
    finally:
        db_boot.close()

    if settings.is_server_profile and contas_ativas == 0:
        mensagem = (
            "Nenhuma conta de acesso provisionada e o perfil é 'server'. "
            "Publicar o backend sem autenticação daria controle total a quem "
            "obtivesse a URL. Crie a primeira conta com:\n"
            "    python -m app.cli create-user <usuario> --role owner"
        )
        logger.critical("[Segurança] %s", mensagem)
        raise RuntimeError(mensagem)

    if contas_ativas == 0:
        logger.warning(
            "[Segurança] Nenhuma conta provisionada. No perfil desktop o app usa o "
            "token local, mas crie uma conta antes de publicar o servidor: "
            "python -m app.cli create-user <usuario> --role owner"
        )

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


# ── Confinamento de caminho no sistema de arquivos ────────────────────

def _resolve_within(root: Path, relative_path: str) -> Path | None:
    """
    Resolve `relative_path` sob `root` e devolve o caminho **apenas** se ele
    permanecer dentro da raiz. Caso contrário, `None`.

    O servidor ASGI decodifica a percent-encoding antes do roteamento, então
    `/%2e%2e%2f%2e%2e%2fetc/passwd` chega aqui como `../../etc/passwd`: sem
    esta verificação, o catch-all da SPA serve qualquer arquivo legível pelo
    processo — inclusive o banco com as chaves de API. A comparação é feita
    depois de `resolve()`, nunca por prefixo de string, porque `..` e links
    simbólicos só somem na normalização real.
    """
    if not relative_path:
        return None
    try:
        candidate = (root / relative_path).resolve()
    except (OSError, ValueError, RuntimeError):
        return None
    if candidate == root or root not in candidate.parents:
        return None
    return candidate


# ── App Factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""
    # A documentação interativa mapeia os 50+ endpoints e seus esquemas. Em
    # desenvolvimento é conveniência; publicada, é reconhecimento gratuito para
    # quem estiver sondando o túnel (doc 29 §29.2.2).
    expose_docs = settings.expose_api_docs

    app = FastAPI(
        title="RSAC API",
        description="Revisão Sistemática Assistida por Computador — Backend API",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs" if expose_docs else None,
        redoc_url="/api/redoc" if expose_docs else None,
        openapi_url="/api/openapi.json" if expose_docs else None,
    )

    # CORS — lista finita derivada do perfil de implantação (doc 29 §29.5.1).
    #
    # O regex anterior (`^https?://.*`) casava com qualquer origem existente e,
    # combinado com `allow_credentials`, permitia que um site arbitrário aberto
    # no navegador lesse e escrevesse na API em 127.0.0.1 — inclusive as chaves
    # de API. Fora do perfil `server` o que se libera é o loopback (com porta
    # variável, por causa do Vite); no perfil `server`, apenas o que estiver em
    # RSAC_CORS_ORIGINS.
    cors_kwargs: dict = {
        "allow_origins": settings.effective_cors_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-Requested-With"],
        "expose_headers": ["Content-Disposition", "X-PDF-Attempts"],
        "max_age": 600,
    }
    origin_regex = settings.cors_allow_origin_regex
    if origin_regex:
        cors_kwargs["allow_origin_regex"] = origin_regex
    app.add_middleware(CORSMiddleware, **cors_kwargs)

    # Health check no root
    @app.get("/health", response_model=HealthResponse, tags=["system"], include_in_schema=False)
    def root_health():
        return HealthResponse(
            status="ok",
            version=settings.app_version,
            database="connected",
        )

    # Incluir routers — o público antes, para que as rotas de exceção sejam
    # resolvidas sem passar pela dependência de sessão do agregador.
    app.include_router(public_router, prefix="/api/v1")
    app.include_router(api_router, prefix="/api/v1")

    # Servir Frontend Web Estático (SPA) se construído
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        spa_root = frontend_dist.resolve()
        spa_index = spa_root / "index.html"

        assets_dir = spa_root / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/favicon.svg", include_in_schema=False)
        async def serve_favicon():
            return FileResponse(spa_root / "favicon.svg")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            if full_path.startswith("api") or full_path in ("health", "docs", "redoc", "openapi.json"):
                raise HTTPException(status_code=404, detail="Not Found")

            candidate = _resolve_within(spa_root, full_path)
            if candidate is not None and candidate.is_file():
                return FileResponse(candidate)

            # Qualquer outra coisa — rota do React Router, arquivo inexistente
            # ou tentativa de travessia — cai no index. Devolver 403 no caso da
            # travessia confirmaria a existência do alvo ao atacante.
            return FileResponse(spa_index)

    return app


# Instância global
app = create_app()

