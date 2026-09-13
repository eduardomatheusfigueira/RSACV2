#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Retenção e descarte (LGPD arts. 15 e 16).

O Aviso de Privacidade promete prazos. Este módulo é o que os cumpre — e a
razão de ele existir é que, antes dele, dois desses prazos eram só texto: as
tentativas de login se acumulavam para sempre, e o expurgo de estados OAuth
abandonados estava escrito mas nunca era chamado. Um aviso que promete
descarte que o sistema não faz é pior do que um aviso que não promete nada.

Os prazos ficam aqui como constantes nomeadas, e o teste de retenção os
confronta com o documento publicado: quem mudar um sem o outro quebra a
suíte.

Quando roda: na partida do servidor e, depois, de forma oportunista em rotas
de pouco tráfego, no máximo uma vez por hora. O servidor fica no ar por
semanas; rodar só na partida deixaria o descarte à mercê do próximo
reinício.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    InviteRequestModel,
    LoginAttemptModel,
    SessionModel,
)
from app.security import oauth_state

logger = logging.getLogger(__name__)

# ── Prazos publicados no Aviso de Privacidade, seção "Retenção e descarte" ──
DIAS_TENTATIVAS_DE_LOGIN = 90
DIAS_PEDIDOS_DE_CONVITE_RESPONDIDOS = 365

# Intervalo mínimo entre execuções oportunistas, em segundos.
INTERVALO_MINIMO = 3600

_ultima_execucao: float = 0.0


@dataclass(frozen=True)
class ResultadoDaRetencao:
    tentativas_de_login: int = 0
    pedidos_de_convite: int = 0
    sessoes: int = 0
    estados_oauth: int = 0

    @property
    def total(self) -> int:
        return (
            self.tentativas_de_login
            + self.pedidos_de_convite
            + self.sessoes
            + self.estados_oauth
        )


def aplicar_retencao(db: Session, agora: datetime | None = None) -> ResultadoDaRetencao:
    """
    Elimina o que venceu. Idempotente: rodar duas vezes não apaga nada a mais.

    `agora` é injetável para os testes poderem avançar o relógio sem esperar
    90 dias.
    """
    agora = agora or datetime.now(timezone.utc)

    tentativas = (
        db.query(LoginAttemptModel)
        .filter(
            LoginAttemptModel.attempted_at
            < agora - timedelta(days=DIAS_TENTATIVAS_DE_LOGIN)
        )
        .delete(synchronize_session=False)
    )

    # Só pedidos *respondidos* vencem. Um pendente continua na fila por mais
    # antigo que seja: apagá-lo seria responder "não" por omissão, sem que
    # ninguém tenha decidido isso.
    pedidos = (
        db.query(InviteRequestModel)
        .filter(
            InviteRequestModel.status != "pendente",
            InviteRequestModel.responded_at.isnot(None),
            InviteRequestModel.responded_at
            < agora - timedelta(days=DIAS_PEDIDOS_DE_CONVITE_RESPONDIDOS),
        )
        .delete(synchronize_session=False)
    )

    sessoes = (
        db.query(SessionModel)
        .filter(SessionModel.expires_at <= agora)
        .delete(synchronize_session=False)
    )

    db.commit()

    # `expurgar_vencidos` usa o próprio relógio e faz o próprio commit.
    estados = oauth_state.expurgar_vencidos(db)

    resultado = ResultadoDaRetencao(
        tentativas_de_login=tentativas,
        pedidos_de_convite=pedidos,
        sessoes=sessoes,
        estados_oauth=estados or 0,
    )
    if resultado.total:
        # Contagens, e só: o log de descarte não pode virar o lugar onde o dado
        # descartado sobrevive.
        logger.info(
            "[Retenção] Eliminados: %d tentativas de login, %d pedidos de convite, "
            "%d sessões, %d estados OAuth.",
            resultado.tentativas_de_login,
            resultado.pedidos_de_convite,
            resultado.sessoes,
            resultado.estados_oauth,
        )
    return resultado


def aplicar_retencao_se_devido(db: Session) -> None:
    """
    Versão oportunista, para chamar dentro de rotas.

    Nunca levanta: uma falha no descarte não pode derrubar a requisição de
    quem só estava pedindo um convite. O erro fica no log, e a próxima janela
    tenta de novo.
    """
    global _ultima_execucao
    agora = time.monotonic()
    if _ultima_execucao and agora - _ultima_execucao < INTERVALO_MINIMO:
        return
    _ultima_execucao = agora
    try:
        aplicar_retencao(db)
    except Exception:  # pragma: no cover — defesa, não fluxo
        db.rollback()
        logger.exception("[Retenção] Falha ao aplicar a retenção; nova tentativa na próxima janela.")
