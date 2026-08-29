#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes da rotina de retenção e expurgo (LGPD Art. 15 e 16, L-30).
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    LoginAttemptModel,
    OAuthStateModel,
    ProcessingRecordModel,
    SessionModel,
    UserModel,
    generate_uuid,
)
from app.services.retention_service import (
    executar_rotina_retencao,
    expurgar_tentativas_login,
    expurgar_oauth_states,
    expurgar_sessoes_expiradas,
)


def test_expurgo_login_attempts_com_mais_de_90_dias(db_session: Session):
    agora = datetime.now(timezone.utc)
    recente_id = generate_uuid()
    antiga_id = generate_uuid()

    # 1. Tentativa recente (10 dias atrás) — deve ser mantida
    recente = LoginAttemptModel(
        id=recente_id,
        username="pesquisador_recente",
        client_host="192.168.1.10",
        successful=False,
        attempted_at=agora - timedelta(days=10),
    )
    # 2. Tentativa antiga (95 dias atrás) — deve ser expurgada (L-30)
    antiga = LoginAttemptModel(
        id=antiga_id,
        username="atacante_antigo",
        client_host="203.0.113.50",
        successful=False,
        attempted_at=agora - timedelta(days=95),
    )
    db_session.add_all([recente, antiga])
    db_session.commit()

    relatorio = executar_rotina_retencao(db_session, referencia=agora)
    assert relatorio["login_attempts_expurgados"] >= 1

    # Verificar banco
    assert db_session.query(LoginAttemptModel).filter(LoginAttemptModel.id == recente_id).first() is not None
    assert db_session.query(LoginAttemptModel).filter(LoginAttemptModel.id == antiga_id).first() is None


def test_expurgo_oauth_states_vencidos(db_session: Session):
    agora = datetime.now(timezone.utc)

    # 1. Estado válido (expira em 5 min no futuro)
    valido = OAuthStateModel(
        state="state_valido_123",
        code_verifier="verifier_valido",
        nonce="nonce_valido",
        redirect_after="/app",
        expires_at=agora + timedelta(minutes=5),
    )
    # 2. Estado vencido (expirou há 20 minutos)
    vencido = OAuthStateModel(
        state="state_vencido_456",
        code_verifier="verifier_vencido",
        nonce="nonce_vencido",
        redirect_after="/app",
        expires_at=agora - timedelta(minutes=20),
    )
    db_session.add_all([valido, vencido])
    db_session.commit()

    relatorio = executar_rotina_retencao(db_session, referencia=agora)
    assert relatorio["oauth_states_expurgados"] >= 1

    assert db_session.query(OAuthStateModel).filter(OAuthStateModel.state == "state_valido_123").first() is not None
    assert db_session.query(OAuthStateModel).filter(OAuthStateModel.state == "state_vencido_456").first() is None


def test_expurgo_sessoes_expiradas(db_session: Session):
    agora = datetime.now(timezone.utc)
    user_id = generate_uuid()
    sessao_ativa_id = generate_uuid()
    sessao_vencida_id = generate_uuid()

    user = UserModel(
        id=user_id,
        username="user_teste_sessao",
        role="researcher",
    )
    db_session.add(user)
    db_session.commit()

    # Sessão ativa
    sessao_ativa = SessionModel(
        id=sessao_ativa_id,
        user_id=user_id,
        token_hash="hash_ativa_123",
        expires_at=agora + timedelta(hours=24),
    )
    # Sessão vencida
    sessao_vencida = SessionModel(
        id=sessao_vencida_id,
        user_id=user_id,
        token_hash="hash_vencida_456",
        expires_at=agora - timedelta(hours=2),
    )
    db_session.add_all([sessao_ativa, sessao_vencida])
    db_session.commit()

    relatorio = executar_rotina_retencao(db_session, referencia=agora)
    assert relatorio["sessoes_expiradas_expurgadas"] >= 1

    assert db_session.query(SessionModel).filter(SessionModel.id == sessao_ativa_id).first() is not None
    assert db_session.query(SessionModel).filter(SessionModel.id == sessao_vencida_id).first() is None
