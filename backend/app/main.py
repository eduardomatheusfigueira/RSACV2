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
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router, public_router
from app.config import settings
from app.database import SessionLocal, create_tables
from app.infrastructure.persistence.models import (
    HarvestRunModel,
    PaperModel,
    UserModel,
)
from app.security.crypto import MasterKeyError, obter_chave_mestra
from app.security.local_token import descrever_para_log, ensure_local_token, token_path
from app.security.log_filter import instalar_filtro_de_segredos
from app.security.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    instalar_tratamento_de_erro,
)
from app.security.migration import cifrar_segredos_legados
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
# Rede de segurança contra credencial escrita em log por engano (§29.4.4).
instalar_filtro_de_segredos()

logger = logging.getLogger("rsac")


# ── Tarefas de partida no banco ───────────────────────────────────────

def _reconciliar_coletas_interrompidas(db: Session) -> None:
    """
    Marca como falha a coleta que ficou `running` quando o processo caiu.

    Sem isto, uma coleta interrompida por reinício fica para sempre "em
    andamento" na interface, e o usuário espera por um trabalho que já não tem
    processo nenhum atrás.
    """
    try:
        interrompidas = (
            db.query(HarvestRunModel).filter(HarvestRunModel.status == "running").all()
        )
        if not interrompidas:
            return
        logger.warning(
            f"[Lifespan] Reconciliando {len(interrompidas)} coleta(s) que ficaram com status 'running'."
        )
        for run in interrompidas:
            run.status = "failed"
            run.error_message = "Interrompida por reinício do servidor."
            run.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001 — não pode impedir o app de subir
        db.rollback()
        logger.error(f"[Lifespan] Erro ao reconciliar execuções de coleta: {exc}")


def _limpar_prefixos_de_ia_legados(db: Session) -> None:
    """
    Remove o rótulo `[IA] …` que versões antigas gravavam nas observações.

    O filtro `ilike("[%")` faz com que, depois da primeira limpeza, a consulta
    não devolva linha nenhuma — é o que mantém isto barato a cada partida em
    vez de percorrer a triagem inteira.
    """
    try:
        from app.services.screening_service import _strip_ai_prefix

        legados = db.query(PaperModel).filter(PaperModel.observations.ilike("[%")).all()
        limpos = 0
        for paper in legados:
            limpo = _strip_ai_prefix(paper.observations)
            if limpo != (paper.observations or "").strip():
                paper.observations = limpo
                limpos += 1
        if limpos:
            db.commit()
            logger.info(
                f"[Lifespan] Removido prefixo de IA de {limpos} observação(ões) antigas."
            )
    except Exception as exc:  # noqa: BLE001 — não pode impedir o app de subir
        db.rollback()
        logger.error(f"[Lifespan] Erro ao limpar prefixos de IA das observações: {exc}")


# ── Descoberta da instalação por quem lança o processo ────────────────

# Prefixo da linha que o Electron e o `scripts/launcher.py` procuram na saída
# padrão do backend.
LINHA_DE_HANDSHAKE = "RSAC_RUNTIME"


def _anunciar_pasta_de_dados() -> None:
    """
    Diz na saída padrão onde ficam a pasta de dados e o arquivo de token.

    Quem lança o backend precisa do `runtime_token` para entrar sem tela de
    login — e até aqui adivinhava o caminho, cada um do seu jeito: o launcher
    procurava em `%LOCALAPPDATA%\\RSAC`, o backend gravava no caminho do
    `platformdirs` (`%LOCALAPPDATA%\\RSAC\\RSAC`), e o app empacotado nem
    procurava. Adivinhar é o problema; o processo que grava o arquivo é quem
    sabe onde ele está, então é ele que informa.

    O que sai daqui é o **caminho**, nunca o token: a saída padrão do backend
    vai para o log do processo pai, e credencial não tem por que passar por lá.
    """
    if settings.is_server_profile:
        return
    try:
        print(f"{LINHA_DE_HANDSHAKE} data_dir={settings.data_dir}", flush=True)
        print(f"{LINHA_DE_HANDSHAKE} token_file={token_path()}", flush=True)
    except Exception:  # pragma: no cover — saída padrão fechada/redirecionada
        pass


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
    _anunciar_pasta_de_dados()

    # ── Chave-mestra da cifra (doc 29 §29.4.1) ────────────────────────
    #
    # Resolvida aqui, e não na primeira gravação: a chave é preguiçosa por
    # desenho, e no perfil `server` sem `RSAC_SECRET_KEY` isso deixava o
    # backend subir para só falhar quando alguém tentasse salvar uma chave —
    # com a exceção engolida pela migração. Um servidor que não consegue
    # cifrar segredos não deve atender requisição nenhuma.
    try:
        obter_chave_mestra()
    except MasterKeyError as exc:
        logger.critical("[Segurança] %s", exc)
        raise RuntimeError(str(exc)) from exc

    # Cifra o que ainda estiver em texto claro nas colunas de segredo. Roda a
    # cada partida e é idempotente: valor já cifrado é reconhecido e ignorado.
    from app.database import engine

    cifrar_segredos_legados(engine)

    # ── Trabalho de partida no banco, numa sessão só ──────────────────
    #
    # Eram três sessões abertas e fechadas em sequência — contagem de contas,
    # reconciliação de coletas e limpeza de observações antigas —, cada uma
    # pagando conexão e PRAGMAs do SQLite antes de a primeira requisição poder
    # ser atendida. O trabalho é o mesmo; o que muda é que agora ele acontece
    # numa conexão única, e o backend responde ao health check mais cedo.
    db_boot = SessionLocal()
    try:
        contas_ativas = (
            db_boot.query(UserModel).filter(UserModel.is_active == True).count()  # noqa: E712
        )
        _reconciliar_coletas_interrompidas(db_boot)
        _limpar_prefixos_de_ia_legados(db_boot)
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

    # Middlewares de segurança (doc 29 §29.6, §29.7). A ordem de registro é a
    # inversa da execução no Starlette: o limitador roda antes dos cabeçalhos,
    # de modo que uma resposta 429 também sai com eles.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # No perfil `server` o backend fica atrás de um túnel: recusar Host
    # inesperado limita envenenamento de cabeçalho e uso do servidor como
    # ponte para outro nome.
    if settings.is_server_profile and settings.trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    instalar_tratamento_de_erro(app)

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
    else:
        @app.get("/", include_in_schema=False)
        async def fallback_root():
            from fastapi.responses import HTMLResponse
            return HTMLResponse("""
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="utf-8">
                <title>RSAC V2 — Backend Ativo</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; }
                    .card { max-width: 520px; padding: 2.5rem; background: #1e293b; border-radius: 12px; border: 1px solid #334155; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
                    h2 { color: #38bdf8; margin-top: 0; }
                    p { color: #94a3b8; line-height: 1.6; font-size: 15px; }
                    code { background: #0f172a; padding: 0.25rem 0.5rem; border-radius: 4px; color: #4ade80; font-family: monospace; }
                    .btn { display: inline-block; margin-top: 1.5rem; padding: 0.75rem 1.5rem; background: #2563eb; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>🚀 RSAC V2 — Servidor Backend Online</h2>
                    <p>O backend FastAPI está operando normalmente. A interface gráfica compilada não foi encontrada em <code>frontend/dist</code>.</p>
                    <p>Execute <code>npm run build:web</code> dentro da pasta <code>frontend</code> ou utilize os inicializadores automáticos.</p>
                    <a href="/api/docs" class="btn">Documentação da API (Swagger)</a>
                </div>
            </body>
            </html>
            """)

    return app


# Instância global
app = create_app()

