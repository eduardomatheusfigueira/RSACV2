#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Aprovar e recusar pedidos de convite.

Duas portas levam aqui: o painel de administração e os botões do e-mail que
avisa o administrador de um novo pedido. As duas precisam fazer exatamente a
mesma coisa — gerar o código, gravar a decisão, avisar quem pediu —, e é por
isso que a regra mora num serviço e não em nenhuma das duas rotas. Com a
lógica copiada em cada porta, a primeira correção feita numa só produziria
duas aprovações que se comportam diferente conforme o botão clicado.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    InviteCodeModel,
    InviteRequestModel,
    generate_uuid,
)
from app.services import convite_mensagens, email_service, ropa_service

logger = logging.getLogger(__name__)

VALIDADE_PADRAO_DIAS = 14


class PedidoJaRespondido(Exception):
    """O pedido não está mais pendente; a decisão já foi tomada."""

    def __init__(self, solicitacao: InviteRequestModel):
        self.solicitacao = solicitacao
        super().__init__(f"Pedido {solicitacao.id} já está '{solicitacao.status}'.")


@dataclass(frozen=True)
class ResultadoDaAprovacao:
    solicitacao: InviteRequestModel
    convite: InviteCodeModel
    mensagens: convite_mensagens.MensagensDeAprovacao
    envio: email_service.ResultadoDeEnvio


def gerar_codigo_convite() -> str:
    """Código legível e seguro no formato RSAC-XXXX-YYYY."""
    return f"RSAC-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"


def aprovar(
    db: Session,
    solicitacao: InviteRequestModel,
    *,
    aprovado_por_id: Optional[str],
    via: str,
    expires_in_days: Optional[int] = VALIDADE_PADRAO_DIAS,
    nota: Optional[str] = None,
) -> ResultadoDaAprovacao:
    """
    Emite o convite, grava a aprovação e avisa quem pediu.

    `via` entra só no log ("painel", "e-mail") — é o que permite, depois,
    saber por qual porta uma aprovação chegou.

    Levanta `PedidoJaRespondido` se o pedido já tiver sido aprovado. Um pedido
    recusado pode ser aprovado depois: mudar de ideia a favor de alguém é
    legítimo, e a recusa não emitiu nada que precise ser desfeito.
    """
    if solicitacao.status == "aprovado" and solicitacao.invite_code_generated:
        raise PedidoJaRespondido(solicitacao)

    agora = datetime.now(timezone.utc)
    expira_em = agora + timedelta(days=expires_in_days) if expires_in_days else None
    nota_final = (nota or "").strip() or f"Solicitação de {solicitacao.nome} ({solicitacao.email})"

    codigo = gerar_codigo_convite()
    while db.query(InviteCodeModel).filter(InviteCodeModel.code == codigo).first():
        codigo = gerar_codigo_convite()

    convite = InviteCodeModel(
        id=generate_uuid(),
        code=codigo,
        created_by_user_id=aprovado_por_id,
        created_at=agora,
        expires_at=expira_em,
        is_used=False,
        is_revoked=False,
        note=nota_final[:255],
    )
    db.add(convite)

    solicitacao.status = "aprovado"
    solicitacao.responded_at = agora
    solicitacao.invite_code_generated = codigo

    db.commit()
    db.refresh(convite)
    db.refresh(solicitacao)

    logger.info(
        "[Convites] Pedido %s aprovado (via %s) com o convite '%s'.",
        solicitacao.id,
        via,
        codigo,
    )

    # Daqui para baixo nada pode derrubar a aprovação: ela já foi gravada, e o
    # acesso já é válido. O envio é consequência, não condição — por isso vem
    # depois do `commit`, e o resultado é relatado em vez de levantado.
    mensagens = convite_mensagens.montar_tudo(
        nome=solicitacao.nome,
        telefone=solicitacao.telefone,
        codigo=codigo,
    )
    envio = email_service.enviar(
        destinatario=solicitacao.email,
        assunto=mensagens.email_assunto,
        texto=mensagens.email_texto,
        html=mensagens.email_html,
        imagens=convite_mensagens.pecas_do_email(),
    )
    if envio.enviado:
        ropa_service.registrar(
            db,
            operation="invite_approved_notice",
            legal_basis="art7_I_consentimento",
            purpose="Comunicar a aprovação do pedido de acesso a quem o enviou",
            data_categories=["contato"],
            user_id=aprovado_por_id,
            commit=True,
        )

    return ResultadoDaAprovacao(solicitacao, convite, mensagens, envio)


def recusar(
    db: Session,
    solicitacao: InviteRequestModel,
    *,
    via: str,
    notas: str = "",
) -> InviteRequestModel:
    """
    Marca o pedido como recusado. Não avisa quem pediu.

    Levanta `PedidoJaRespondido` se o pedido já tiver sido aprovado: recusar
    depois de emitir o convite deixaria um código válido nas mãos de alguém
    registrado como recusado. Para voltar atrás numa aprovação, o caminho é
    revogar o convite no painel.
    """
    if solicitacao.status == "aprovado":
        raise PedidoJaRespondido(solicitacao)

    solicitacao.status = "recusado"
    solicitacao.responded_at = datetime.now(timezone.utc)
    if notas:
        solicitacao.admin_notes = notas.strip()
    db.commit()
    db.refresh(solicitacao)

    logger.info("[Convites] Pedido %s recusado (via %s).", solicitacao.id, via)
    return solicitacao
