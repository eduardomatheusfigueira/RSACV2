#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Middlewares de segurança (doc 29 §29.6, §29.7, §29.8).

Três responsabilidades que não cabem em nenhuma rota específica porque valem
para todas: cabeçalhos de resposta, limite de taxa e o tratamento de erro que
impede a exceção interna de virar resposta HTTP.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Optional
from uuid import uuid4

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings
from app.security.sessions import SESSION_COOKIE

logger = logging.getLogger(__name__)


# ── Cabeçalhos de resposta (§29.6) ────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Aplica os cabeçalhos de segurança a **todas** as respostas.

    O que mais importa aqui é o `nosniff`: `GET /.../pdf` serve arquivo
    `inline`, na mesma origem da aplicação. Sem ele, um arquivo que passe pela
    validação de assinatura e seja interpretado como HTML executa script no
    contexto do app.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), camera=(), microphone=()"
        )

        caminho = request.url.path
        if caminho.startswith("/api/"):
            # Resposta de API não é documento: nada deve poder enquadrá-la nem
            # carregar recurso a partir dela.
            response.headers.setdefault(
                "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
            )
            response.headers.setdefault("Cache-Control", "no-store")

        # HSTS só faz sentido sobre HTTPS — e enviá-lo em `http://localhost`
        # travaria o desenvolvimento no navegador do desenvolvedor.
        if settings.is_server_profile and request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        return response


# ── Limite de taxa (§29.7) ────────────────────────────────────────────

# (limite, janela em segundos) por família de rota.
LIMITES: dict[str, tuple[int, int]] = {
    "ai": (20, 60),          # chamadas de IA — consomem cota paga
    "jobs": (5, 3600),       # coleta e lote de PDF — caros e demorados
    "auth": (10, 900),       # tentativas de autenticação
    "geral": (300, 60),
}


def _familia_da_rota(caminho: str, metodo: str) -> str:
    """Classifica a requisição na família de limite correspondente."""
    if "/auth/login" in caminho or "/auth/local" in caminho or "/auth/google" in caminho:
        return "auth"
    if "/ai/" in caminho or "/screening/ai" in caminho:
        return "ai"
    if metodo == "POST" and ("/harvest" in caminho or "/pdf/batch" in caminho):
        return "jobs"
    return "geral"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Limite de taxa por sessão (ou por IP, antes do login).

    Chaveia pela sessão, não pelo IP, de propósito: pesquisadores atrás do NAT
    de uma universidade compartilham endereço, e limitar por IP transformaria
    o uso normal de um laboratório em bloqueio mútuo. Antes do login não há
    sessão, e aí o IP é o que existe — é exatamente o caso das tentativas de
    autenticação, onde limitar por origem é o que se quer.

    A contagem é em memória: reiniciar o processo zera. É aceitável porque o
    limite aqui é contra abuso de recurso; o limite que precisa sobreviver ao
    reinício — tentativas de login — tem estado no banco (`sessions.py`).
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._historico: dict[tuple[str, str], Deque[float]] = defaultdict(deque)

    def _chave(self, request: Request) -> str:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            cabecalho = request.headers.get("Authorization", "")
            if cabecalho.lower().startswith("bearer "):
                token = cabecalho[7:].strip()
        if token:
            # Prefixo do token basta para distinguir sessões sem guardar a
            # credencial inteira em memória.
            return f"s:{token[:16]}"
        return f"ip:{request.client.host if request.client else 'desconhecido'}"

    async def dispatch(self, request: Request, call_next: Callable):
        if not settings.rate_limit_enabled:
            return await call_next(request)

        caminho = request.url.path
        if not caminho.startswith("/api/") or caminho.endswith("/health"):
            return await call_next(request)

        familia = _familia_da_rota(caminho, request.method)
        limite, janela = LIMITES[familia]
        chave = (self._chave(request), familia)

        agora = time.monotonic()
        registros = self._historico[chave]
        while registros and agora - registros[0] > janela:
            registros.popleft()

        if len(registros) >= limite:
            espera = int(janela - (agora - registros[0])) + 1
            logger.warning(
                "[RateLimit] Limite de '%s' atingido para %s (%d em %ds).",
                familia, chave[0], limite, janela,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": (
                        "Muitas requisições em pouco tempo. "
                        f"Tente novamente em {espera} segundo(s)."
                    )
                },
                headers={"Retry-After": str(espera)},
            )

        registros.append(agora)
        return await call_next(request)


# ── Tratamento de erro (§29.8) ────────────────────────────────────────

def instalar_tratamento_de_erro(app) -> None:
    """
    Instala o manipulador global de exceção não tratada.

    `raise HTTPException(500, detail=str(e))` propagava caminho absoluto de
    disco, nome de host de provedor e fragmento de SQL para o cliente. Aqui a
    mensagem que sai é estável e acompanha um identificador de correlação; o
    detalhe fica no log do servidor, indexado por esse identificador.
    """

    @app.exception_handler(Exception)
    async def tratar_excecao_nao_prevista(request: Request, exc: Exception):
        referencia = uuid4().hex[:8]
        logger.exception(
            "[Erro] Falha não tratada em %s %s (ref=%s)",
            request.method, request.url.path, referencia,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": (
                    "Falha ao processar a solicitação. "
                    f"Informe a referência {referencia} ao consultar o log do servidor."
                ),
                "reference": referencia,
            },
        )


def erro_interno(mensagem: str, exc: Optional[BaseException] = None, *, contexto: str = "") -> tuple[str, str]:
    """
    Prepara um par `(mensagem_publica, referencia)` para erros tratados na rota.

    Devolve a referência para que quem chama registre o detalhe no log com o
    mesmo identificador que o usuário vê.
    """
    referencia = uuid4().hex[:8]
    if exc is not None:
        logger.error("[Erro] %s (ref=%s): %s", contexto or mensagem, referencia, exc, exc_info=True)
    return f"{mensagem} Referência: {referencia}.", referencia
