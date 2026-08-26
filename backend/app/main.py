#!/usr/bin/env python

"""
RSAC V2 — FastAPI Application Factory.
Ponto de entrada do backend — cria e configura a aplicação FastAPI,
logging estruturado em arquivo e reconciliação de jobs no ciclo de vida (lifespan).
"""

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1.router import api_router, public_router
from app.config import settings
from app.database import SessionLocal, create_tables
from app.infrastructure.persistence.models import (
    HarvestRunModel,
    PaperModel,
)
from app.schemas.common import HealthResponse
from app.security.crypto import MasterKeyError, obter_chave_mestra
from app.security.dependencies import LOCAL_TOKEN_HEADER
from app.security.local_token import descrever_para_log, ensure_local_token, token_path
from app.security.log_filter import instalar_filtro_de_segredos
from app.security.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    instalar_tratamento_de_erro,
)
from app.security.migration import cifrar_segredos_legados

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
            run.completed_at = datetime.now(UTC)
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

# Prefixo da linha que o processo principal do Electron procura na saída padrão
# do backend.
LINHA_DE_HANDSHAKE = "RSAC_RUNTIME"


def _anunciar_pasta_de_dados() -> None:
    """
    Diz na saída padrão onde ficam a pasta de dados e o arquivo de token.

    O Electron precisa do `runtime_token` para abrir a interface sem tela de
    login. Até aqui o caminho era adivinhado — e adivinhado errado: o backend
    grava onde o `platformdirs` manda (`%LOCALAPPDATA%\\RSAC\\RSAC` no
    Windows), e o app empacotado nem chegava a procurar. Adivinhar é o
    problema; o processo que grava o arquivo é quem sabe onde ele está, então
    é ele que informa.

    O que sai daqui é o **caminho**, nunca o token: a saída padrão do backend
    vai para o log do processo pai, e credencial não tem por que passar por lá.
    """
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
    logger.info(f"Banco de dados: {settings.effective_database_url}")
    logger.info(f"Arquivo de log: {log_file}")
    create_tables()

    # O token local é a credencial da instalação: gerado na primeira partida,
    # gravado com permissão restrita e entregue à interface pelo Electron.
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
        _reconciliar_coletas_interrompidas(db_boot)
        _limpar_prefixos_de_ia_legados(db_boot)
    finally:
        db_boot.close()

    logger.info("Backend pronto para receber requisições.")
    yield
    # Shutdown
    logger.info("Backend encerrando...")


# ── App Factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""
    # A documentação interativa fica ligada: ela era fechada quando o backend
    # podia ser publicado, porque ali mapear os 50+ endpoints era
    # reconhecimento gratuito para quem sondasse o túnel (doc 29 §29.2.2). Sem
    # publicação, quem alcança `127.0.0.1` é o dono da máquina, e para ele o
    # Swagger é ferramenta.
    app = FastAPI(
        title="RSAC API",
        description="Revisão Sistemática Assistida por Computador — Backend API",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS — só loopback e a origem opaca do app empacotado (doc 29 §29.5.1).
    #
    # O regex anterior (`^https?://.*`) casava com qualquer origem existente e,
    # combinado com `allow_credentials`, permitia que um site arbitrário aberto
    # no navegador lesse e escrevesse na API em 127.0.0.1 — inclusive as chaves
    # de API. O que se libera agora é o que `Settings.cors_allow_origin_regex`
    # descreve, e nada mais: não há mais lista configurável, porque não há mais
    # implantação em que ela faria sentido.
    #
    # `allow_headers` precisa nomear `X-RSAC-Local-Token`: é por ele que a
    # credencial viaja, e um cabeçalho não listado aqui é recusado pelo
    # navegador no *preflight*, antes de a requisição sair.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Requested-With", LOCAL_TOKEN_HEADER],
        expose_headers=["Content-Disposition", "X-PDF-Attempts"],
        max_age=600,
    )

    # Middlewares de segurança (doc 29 §29.6, §29.7). A ordem de registro é a
    # inversa da execução no Starlette: o limitador roda antes dos cabeçalhos,
    # de modo que uma resposta 429 também sai com eles.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

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

    # ── A SPA estática não é mais servida por aqui ────────────────────
    #
    # Havia um catch-all que servia `frontend/dist` para um navegador que
    # chegasse ao backend, com um `_resolve_within` confinando o caminho à
    # raiz da SPA — porque o servidor ASGI decodifica a percent-encoding antes
    # do roteamento, e sem esse confinamento `/%2e%2e%2f...` servia qualquer
    # arquivo legível pelo processo, o banco com as chaves de API inclusive
    # (doc 28, travessia de caminho).
    #
    # A interface passou a ser exclusivamente o app Electron, que carrega os
    # próprios arquivos do disco. O catch-all deixou de ter cliente — e a
    # forma mais segura de tratar uma superfície de travessia de caminho é não
    # ter a superfície.

    return app


# Instância global
app = create_app()

