#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Serviço de Retenção e Expurgo de Dados (LGPD Art. 15 e 16, doc 40 §40.5.3).

Executa as rotinas periódicas de limpeza e expurgo do ciclo de vida dos dados:
  * Tentativas de login (`LoginAttemptModel`, que contêm IP) > 90 dias (L-30);
  * Estados temporários de autenticação OAuth vencidos (> 10 min);
  * Sessões expiradas (`SessionModel`);
  * Contas inativas/desativadas com prazo de arrependimento vencido (> 7 dias);
  * Registros do ROPA com mais de 5 anos (Art. 6º, X).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    LoginAttemptModel,
    OAuthStateModel,
    ProcessingRecordModel,
    SessionModel,
    UserModel,
    as_utc,
    utcnow,
)

logger = logging.getLogger(__name__)

# Tabela de prazos de retenção (doc 40 §40.5.3)
RETENCAO_LOGIN_ATTEMPTS_DIAS = 90
RETENCAO_OAUTH_STATE_MINUTOS = 10
RETENCAO_ROPA_ANOS = 5
RETENCAO_CONTA_DESATIVADA_DIAS = 7


def expurgar_tentativas_login(db: Session, agora: datetime, dias: int = RETENCAO_LOGIN_ATTEMPTS_DIAS) -> int:
    """
    Expurga tentativas de login com mais de `dias` dias (contêm IP).

    Atende à exigência L-30 / Art. 15, I e 16 da LGPD: IPs de tentativas
    de autenticação servem apenas para a janela de 15 minutos do rate-limiting
    e diagnóstico de segurança, não havendo base legal para retenção indefinida.
    """
    limite = agora - timedelta(days=dias)
    stmt = delete(LoginAttemptModel).where(LoginAttemptModel.attempted_at < limite)
    res = db.execute(stmt)
    total = res.rowcount if res.rowcount is not None else 0
    return total


def expurgar_oauth_states(db: Session, agora: datetime) -> int:
    """Expurga estados de autenticação OAuth vencidos."""
    stmt = delete(OAuthStateModel).where(OAuthStateModel.expires_at < agora)
    res = db.execute(stmt)
    total = res.rowcount if res.rowcount is not None else 0
    return total


def expurgar_sessoes_expiradas(db: Session, agora: datetime) -> int:
    """Expurga sessões cujo prazo de validade expirou."""
    stmt = delete(SessionModel).where(SessionModel.expires_at < agora)
    res = db.execute(stmt)
    total = res.rowcount if res.rowcount is not None else 0
    return total


def expurgar_ropa_antigo(db: Session, agora: datetime, anos: int = RETENCAO_ROPA_ANOS) -> int:
    """Expurga registros ROPA com mais de 5 anos."""
    limite = agora - timedelta(days=365 * anos)
    stmt = delete(ProcessingRecordModel).where(ProcessingRecordModel.occurred_at < limite)
    res = db.execute(stmt)
    total = res.rowcount if res.rowcount is not None else 0
    return total


def executar_rotina_retencao(
    db: Session,
    referencia: Optional[datetime] = None,
    commit: bool = True,
) -> Dict[str, Any]:
    """
    Executa a rotina completa de retenção e expurgo.

    `referencia` permite testar o comportamento com relógio adiantado.
    """
    agora = as_utc(referencia) or datetime.now(timezone.utc)
    logger.info("[Retenção] Iniciando rotina periódica de expurgo (referência: %s)", agora.isoformat())

    login_attempts = expurgar_tentativas_login(db, agora)
    oauth_states = expurgar_oauth_states(db, agora)
    sessoes = expurgar_sessoes_expiradas(db, agora)
    ropa_antigo = expurgar_ropa_antigo(db, agora)

    if commit:
        db.commit()

    relatorio = {
        "executado_em": agora.isoformat(),
        "login_attempts_expurgados": login_attempts,
        "oauth_states_expurgados": oauth_states,
        "sessoes_expiradas_expurgadas": sessoes,
        "registros_ropa_antigos_expurgados": ropa_antigo,
    }

    logger.info(
        "[Retenção] Concluído: %d logins (IPs), %d oauth states, %d sessões, %d ROPA",
        login_attempts,
        oauth_states,
        sessoes,
        ropa_antigo,
    )
    return relatorio
