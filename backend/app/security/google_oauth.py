#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Entrada com Google (doc 40 §40.4).

Fluxo de código de autorização com PKCE, executado **no servidor**. O navegador
nunca vê o `client_secret` nem o `id_token`; o que ele recebe ao final é o mesmo
cookie de sessão que o login por senha já emite, o que mantém uma única
maquinaria de sessão para as duas vias de entrada.

Este módulo tem uma responsabilidade e ela é estreita: montar o pedido, validar
o que volta e dizer quem é a pessoa. Quem cria conta, vincula e emite sessão é
`api/v1/auth.py` — a separação existe para que a lista de validações abaixo
caiba inteira na cabeça de quem revisa, que é a única forma de garantir que não
falte nenhuma.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from joserfc import jwt
from joserfc.jwk import KeySet

from app.config import settings

logger = logging.getLogger(__name__)

# Descoberta do Google. Fixos de propósito: buscar o documento de descoberta a
# cada login acrescentaria uma dependência de rede no caminho crítico da
# autenticação, e estes endereços não mudam há mais de uma década.
AUTORIZACAO_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

# `iss` aceitos. O Google emite as duas formas, e recusar uma delas produziria
# uma falha intermitente e inexplicável.
EMISSORES = frozenset({"accounts.google.com", "https://accounts.google.com"})

# Só o necessário para identificar a pessoa. `profile` traz o nome — e também a
# foto, que é descartada na leitura por não servir a nada no produto (art. 6º,
# III: dado desnecessário não se trata).
ESCOPOS = "openid email profile"

# Folga de relógio na verificação de `exp` e `iat`.
FOLGA_DE_RELOGIO_S = 60

# A JWKS do Google rotaciona; o cache evita uma requisição por login sem
# atrasar a rotação além do razoável.
_TTL_JWKS_S = 3600
_jwks_cache: dict[str, Any] = {"chaves": None, "buscada_em": 0.0}


class GoogleOAuthIndisponivel(RuntimeError):
    """O login com Google não está configurado nesta instalação."""


class IdentidadeRecusada(ValueError):
    """O que o Google devolveu não autoriza entrar."""


@dataclass(frozen=True)
class IdentidadeGoogle:
    """O que se extrai do `id_token`, e nada além."""

    sub: str
    email: str
    email_verificado: bool
    nome: str


def esta_configurado() -> bool:
    """Há credencial de aplicativo para falar com o Google?"""
    return bool(settings.google_client_id and settings.google_client_secret)


def _exigir_configuracao() -> None:
    if not esta_configurado():
        raise GoogleOAuthIndisponivel(
            "Login com Google não configurado: defina RSAC_GOOGLE_CLIENT_ID e "
            "RSAC_GOOGLE_CLIENT_SECRET."
        )


# ── Início do fluxo ───────────────────────────────────────────────────


def gerar_verificador() -> str:
    """Verificador PKCE — 43 a 128 caracteres do alfabeto permitido."""
    return secrets.token_urlsafe(64)[:128]


def desafio_de(verificador: str) -> str:
    """
    Desafio S256: o SHA-256 do verificador, em base64url sem preenchimento.

    É o que viaja pela rede. Quem interceptar o código de autorização não
    consegue trocá-lo sem o verificador, que ficou no servidor.
    """
    digest = hashlib.sha256(verificador.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def montar_url_de_autorizacao(
    *, state: str, nonce: str, code_challenge: str, redirect_uri: str
) -> str:
    """Endereço para onde o navegador é enviado."""
    _exigir_configuracao()
    parametros = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": ESCOPOS,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        # Não se pede `offline`: o RSAC não age em nome da pessoa depois do
        # login, então um token de atualização seria uma credencial de longa
        # duração guardada sem finalidade.
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTORIZACAO_URL}?{urlencode(parametros)}"


# ── Troca do código ───────────────────────────────────────────────────


async def trocar_codigo_por_id_token(
    *, code: str, code_verifier: str, redirect_uri: str, client: Optional[httpx.AsyncClient] = None
) -> str:
    """Troca o código de autorização pelo `id_token`, ainda não validado."""
    _exigir_configuracao()
    dados = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }

    proprio = client is None
    client = client or httpx.AsyncClient(timeout=15.0)
    try:
        resposta = await client.post(TOKEN_URL, data=dados)
    finally:
        if proprio:
            await client.aclose()

    if resposta.status_code != 200:
        # O corpo pode conter o código de autorização; não vai para o log.
        logger.warning("[OAuth] Troca de código recusada pelo Google (%s).", resposta.status_code)
        raise IdentidadeRecusada("O Google recusou a autenticação.")

    id_token = resposta.json().get("id_token")
    if not id_token:
        raise IdentidadeRecusada("A resposta do Google não trouxe id_token.")
    return id_token


async def _obter_jwks(client: Optional[httpx.AsyncClient] = None) -> KeySet:
    """Chaves públicas do Google, com cache."""
    agora = time.time()
    if _jwks_cache["chaves"] is not None and agora - _jwks_cache["buscada_em"] < _TTL_JWKS_S:
        return _jwks_cache["chaves"]

    proprio = client is None
    client = client or httpx.AsyncClient(timeout=15.0)
    try:
        resposta = await client.get(JWKS_URL)
        resposta.raise_for_status()
        chaves = KeySet.import_key_set(resposta.json())
    finally:
        if proprio:
            await client.aclose()

    _jwks_cache["chaves"] = chaves
    _jwks_cache["buscada_em"] = agora
    return chaves


def limpar_cache_de_jwks() -> None:
    """Descarta o cache — usado pelos testes e por rotação forçada."""
    _jwks_cache["chaves"] = None
    _jwks_cache["buscada_em"] = 0.0


# ── Validação ─────────────────────────────────────────────────────────


async def validar_id_token(
    id_token: str, *, nonce_esperado: str, client: Optional[httpx.AsyncClient] = None
) -> IdentidadeGoogle:
    """
    Valida o `id_token` e devolve a identidade.

    São seis verificações, e nenhuma é dispensável:

    1. **Assinatura** confere com a JWKS do Google. Sem isso, qualquer um monta
       um token.
    2. **`iss`** é o Google.
    3. **`aud`** é este aplicativo. É a que se esquece com mais frequência: sem
       ela, um token legítimo emitido para **outro** aplicativo — que aquele
       outro operador possui — entra aqui como se fosse nosso.
    4. **`exp`/`iat`** dentro da janela, com folga de relógio.
    5. **`nonce`** é o que foi gravado ao iniciar o fluxo. Fecha a repetição de
       um token capturado.
    6. **`email_verified`** é verdadeiro. Esta é a trava contra tomada de
       conta: sem ela, quem criasse num Google Workspace uma caixa com o
       endereço de um assinante existente entraria como ele e herdaria o
       acervo — que é o achado mais explorado em integrações de OAuth.
    """
    _exigir_configuracao()
    chaves = await _obter_jwks(client)

    try:
        token = jwt.decode(id_token, chaves)
    except Exception as exc:  # assinatura inválida, formato quebrado
        raise IdentidadeRecusada("Assinatura do id_token inválida.") from exc

    reivindicacoes = token.claims
    agora = int(time.time())

    if reivindicacoes.get("iss") not in EMISSORES:
        raise IdentidadeRecusada("Emissor do id_token inesperado.")

    if reivindicacoes.get("aud") != settings.google_client_id:
        raise IdentidadeRecusada("O id_token foi emitido para outro aplicativo.")

    exp = reivindicacoes.get("exp")
    if not isinstance(exp, int) or exp + FOLGA_DE_RELOGIO_S < agora:
        raise IdentidadeRecusada("O id_token está vencido.")

    iat = reivindicacoes.get("iat")
    if not isinstance(iat, int) or iat - FOLGA_DE_RELOGIO_S > agora:
        raise IdentidadeRecusada("O id_token foi emitido no futuro.")

    if reivindicacoes.get("nonce") != nonce_esperado:
        raise IdentidadeRecusada("O nonce do id_token não corresponde ao pedido.")

    if reivindicacoes.get("email_verified") is not True:
        raise IdentidadeRecusada(
            "O Google não confirma que este e-mail pertence a quem está entrando. "
            "Verifique o endereço na sua conta Google e tente de novo."
        )

    email = (reivindicacoes.get("email") or "").strip().lower()
    sub = (reivindicacoes.get("sub") or "").strip()
    if not email or not sub:
        raise IdentidadeRecusada("O id_token não trouxe identificação utilizável.")

    # `picture` chega junto do escopo `profile` e para aqui: não é gravada.
    return IdentidadeGoogle(
        sub=sub,
        email=email,
        email_verificado=True,
        nome=(reivindicacoes.get("name") or "").strip()[:200],
    )
