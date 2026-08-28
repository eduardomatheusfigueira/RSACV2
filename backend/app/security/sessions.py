#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Sessões com estado no servidor (doc 29 §29.3.3).

O token vai para o cliente uma única vez; o banco guarda apenas o SHA-256 dele.
Duas consequências que motivam o desenho:

  * revogar é apagar uma linha — `logout` mata o token na hora, o que um JWT
    auto-contido não permitiria antes do vencimento;
  * um vazamento do banco não entrega sessões utilizáveis, do mesmo modo que
    não entrega senhas.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import (
    LoginAttemptModel,
    SessionModel,
    UserModel,
    as_utc,
)

# Nome do cookie de sessão. Prefixo `rsac_` para não colidir com nada servido
# no mesmo host em implantações compartilhadas.
SESSION_COOKIE = "rsac_session"

# Janela e teto do limite de força bruta (§29.7).
LOGIN_WINDOW_MINUTES = 15
LOGIN_MAX_ATTEMPTS = 5

_TOKEN_BYTES = 32


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Gravação e leitura seguem regras opostas, e é deliberado:
#
#   * **grava-se sempre consciente.** Em PostgreSQL a coluna é `timestamptz` e
#     guarda o instante correto seja qual for o fuso do servidor; em SQLite o
#     fuso é descartado na gravação, e o que fica é a hora UTC — que é o que se
#     quer.
#   * **lê-se sempre por `as_utc`**, porque só o PostgreSQL devolve o fuso de
#     volta. Sem isso, o mesmo código que funciona no servidor levanta
#     `TypeError` no aplicativo de mesa ao comparar consciente com ingênuo.
#
# A versão anterior fazia o inverso — normalizava tudo para ingênuo na
# gravação — e funcionava enquanto SQLite era o único banco. Em PostgreSQL,
# gravar ingênuo faz o banco assumir o fuso do servidor: com o servidor fora de
# UTC, a sessão expiraria horas antes ou depois do devido, silenciosamente.


def hash_token(token: str) -> str:
    """SHA-256 do token. Rápido de propósito: a entropia está no token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    """Token de sessão com 256 bits de entropia."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


# ── Ciclo de vida da sessão ───────────────────────────────────────────

def create_session(db: Session, user: UserModel, user_agent: str = "") -> tuple[str, SessionModel]:
    """Abre uma sessão e devolve `(token_em_claro, registro)`."""
    token = generate_token()
    expires = _utcnow() + timedelta(hours=settings.session_ttl_hours)

    record = SessionModel(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=expires,
        last_seen_at=_utcnow(),
        user_agent=(user_agent or "")[:200],
    )
    db.add(record)

    user.last_login_at = _utcnow()
    db.commit()
    db.refresh(record)

    return token, record


def resolve_session(db: Session, token: Optional[str]) -> Optional[UserModel]:
    """
    Devolve o usuário dono do token, ou `None`.

    Sessão vencida é apagada aqui mesmo: sem isso a tabela viraria um acervo de
    tokens mortos, e o custo de limpar é menor que o de um trabalho agendado.
    """
    if not token:
        return None

    record = (
        db.query(SessionModel)
        .filter(SessionModel.token_hash == hash_token(token))
        .first()
    )
    if not record:
        return None

    agora = _utcnow()
    if as_utc(record.expires_at) <= agora:
        db.delete(record)
        db.commit()
        return None

    user = db.query(UserModel).filter(UserModel.id == record.user_id).first()
    if not user or not user.is_active:
        return None

    # Renovação por atividade: quem está usando não é deslogado no meio de uma
    # triagem só porque o relógio bateu no TTL.
    record.last_seen_at = agora
    record.expires_at = _utcnow() + timedelta(hours=settings.session_ttl_hours)
    db.commit()

    return user


def revoke_session(db: Session, token: Optional[str]) -> bool:
    """Encerra a sessão do token. Devolve se havia algo para encerrar."""
    if not token:
        return False
    record = (
        db.query(SessionModel)
        .filter(SessionModel.token_hash == hash_token(token))
        .first()
    )
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def revoke_all_sessions(db: Session, user_id: str) -> int:
    """Encerra todas as sessões de um usuário (troca de senha, desativação)."""
    total = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return total


# ── Limite de tentativas de login ─────────────────────────────────────

def register_login_attempt(
    db: Session, username: str, client_host: str, successful: bool
) -> None:
    """Registra a tentativa; o sucesso limpa o histórico de falhas da conta."""
    db.add(
        LoginAttemptModel(
            username=(username or "")[:64],
            client_host=(client_host or "")[:64],
            successful=successful,
            attempted_at=_utcnow(),
        )
    )
    if successful:
        db.query(LoginAttemptModel).filter(
            LoginAttemptModel.username == username,
            LoginAttemptModel.successful == False,  # noqa: E712 — coluna SQL, não bool Python
        ).delete(synchronize_session=False)
    db.commit()


def failed_attempts_recentes(db: Session, username: str) -> int:
    """Falhas da conta dentro da janela corrente."""
    limite = _utcnow() - timedelta(minutes=LOGIN_WINDOW_MINUTES)
    return (
        db.query(LoginAttemptModel)
        .filter(
            LoginAttemptModel.username == username,
            LoginAttemptModel.successful == False,  # noqa: E712
            LoginAttemptModel.attempted_at >= limite,
        )
        .count()
    )


def login_bloqueado(db: Session, username: str) -> bool:
    """A conta atingiu o teto de tentativas na janela?"""
    return failed_attempts_recentes(db, username) >= LOGIN_MAX_ATTEMPTS
