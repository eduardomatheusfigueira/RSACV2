#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Retenção e descarte.

Estes testes existem porque os prazos já foram só texto: o Aviso de
Privacidade prometia expurgo de tentativas de login em 90 dias, e o sistema
nunca apagou nenhuma. A última classe de testes lê o documento publicado e o
confronta com as constantes do código — é o que impede a promessa e a
prática de voltarem a divergir em silêncio.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    InviteRequestModel,
    LoginAttemptModel,
    SessionModel,
    UserModel,
)
from app.services import retencao

AGORA = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)


def _tentativa(db: Session, dias_atras: int) -> None:
    db.add(
        LoginAttemptModel(
            username="alguem",
            client_host="203.0.113.1",
            successful=False,
            attempted_at=AGORA - timedelta(days=dias_atras),
        )
    )


def _pedido(db: Session, status: str, respondido_dias_atras: int | None) -> None:
    db.add(
        InviteRequestModel(
            nome="Pessoa",
            email=f"p{status}{respondido_dias_atras}@exemplo.br",
            telefone="51999998888",
            onde_conheceu="Busca",
            status=status,
            created_at=AGORA - timedelta(days=400),
            responded_at=(
                AGORA - timedelta(days=respondido_dias_atras)
                if respondido_dias_atras is not None
                else None
            ),
        )
    )


def test_tentativas_de_login_vencem_em_90_dias(db_session: Session):
    _tentativa(db_session, 91)
    _tentativa(db_session, 89)
    db_session.commit()

    r = retencao.aplicar_retencao(db_session, agora=AGORA)

    assert r.tentativas_de_login == 1
    assert db_session.query(LoginAttemptModel).count() == 1


def test_pedido_respondido_vence_em_12_meses(db_session: Session):
    _pedido(db_session, "recusado", 366)
    _pedido(db_session, "aprovado", 366)
    _pedido(db_session, "recusado", 100)
    db_session.commit()

    r = retencao.aplicar_retencao(db_session, agora=AGORA)

    assert r.pedidos_de_convite == 2
    assert db_session.query(InviteRequestModel).count() == 1


def test_pedido_pendente_nunca_vence(db_session: Session):
    """Apagar um pendente seria recusá-lo por omissão, sem ninguém decidir."""
    _pedido(db_session, "pendente", None)
    db_session.commit()

    retencao.aplicar_retencao(db_session, agora=AGORA + timedelta(days=5000))

    assert db_session.query(InviteRequestModel).count() == 1


def test_sessoes_vencidas_saem(db_session: Session, contas):
    dono = db_session.query(UserModel).first()
    db_session.add(
        SessionModel(
            user_id=dono.id,
            token_hash="a" * 64,
            expires_at=AGORA - timedelta(minutes=1),
        )
    )
    db_session.add(
        SessionModel(
            user_id=dono.id,
            token_hash="b" * 64,
            expires_at=AGORA + timedelta(hours=1),
        )
    )
    db_session.commit()
    antes = db_session.query(SessionModel).count()

    r = retencao.aplicar_retencao(db_session, agora=AGORA)

    assert r.sessoes >= 1
    assert db_session.query(SessionModel).count() == antes - r.sessoes
    assert db_session.query(SessionModel).filter_by(token_hash="b" * 64).count() == 1


def test_rodar_duas_vezes_nao_apaga_mais(db_session: Session):
    _tentativa(db_session, 200)
    _tentativa(db_session, 10)
    db_session.commit()

    retencao.aplicar_retencao(db_session, agora=AGORA)
    segunda = retencao.aplicar_retencao(db_session, agora=AGORA)

    assert segunda.tentativas_de_login == 0
    assert db_session.query(LoginAttemptModel).count() == 1


def test_versao_oportunista_respeita_o_intervalo(db_session: Session, monkeypatch):
    chamadas = []
    monkeypatch.setattr(retencao, "_ultima_execucao", 0.0)
    monkeypatch.setattr(retencao, "aplicar_retencao", lambda db: chamadas.append(1))

    retencao.aplicar_retencao_se_devido(db_session)
    retencao.aplicar_retencao_se_devido(db_session)

    assert len(chamadas) == 1


# ══════════════════════════════════════════════════════════════════════
# A promessa e a prática
# ══════════════════════════════════════════════════════════════════════

AVISO = Path(__file__).resolve().parents[3] / "landing" / "privacidade" / "index.html"


def _texto_do_aviso() -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", AVISO.read_text(encoding="utf-8")))


def test_aviso_publica_o_prazo_das_tentativas_de_login():
    assert retencao.DIAS_TENTATIVAS_DE_LOGIN == 90
    assert re.search(r"Tentativas de login e IP\s+Até 90 dias", _texto_do_aviso())


def test_aviso_publica_o_prazo_dos_pedidos_de_convite():
    assert retencao.DIAS_PEDIDOS_DE_CONVITE_RESPONDIDOS == 365
    assert re.search(r"Pedidos de convite respondidos\s+Até 12 meses", _texto_do_aviso())
