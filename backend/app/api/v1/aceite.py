#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Aceite do aviso do BETA (doc 43 §43.10; doc 38 L-12).

Duas rotas: uma que mostra o texto vigente e o estado do aceite, outra que o
registra. Ambas exigem sessão, e **nenhuma das duas exige aceite** — se
exigissem, a pessoa ficaria presa fora do único lugar onde poderia entrar.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import UserModel
from app.legal import aceite as texto_legal
from app.security.dependencies import require_session
from app.services import ropa_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aceite", tags=["aceite"])


class AceiteVigente(BaseModel):
    """O que a tela precisa para se desenhar."""

    exigido: bool = Field(..., description="Falso no perfil desktop, onde não há terceiro")
    aceito: bool
    versao: str
    titulo: str
    rotulo_da_caixa: str
    texto: str
    versao_aceita: str = ""


class PedidoDeAceite(BaseModel):
    """
    A versão vem do cliente e é conferida contra a vigente.

    Sem essa conferência, uma aba aberta há uma semana registraria aceite do
    texto novo tendo exibido o antigo — que é precisamente o defeito que este
    módulo existe para não ter.
    """

    versao: str


def aceite_pendente(usuario: UserModel | None) -> bool:
    """
    Falta aceitar o texto vigente?

    No perfil `desktop` nunca falta: ali não há terceiro cujos dados proteger,
    e a única conta é a de quem instalou o programa na própria máquina.
    Interpor uma tela de aceite ali seria atrito sem função.
    """
    if not settings.is_server_profile:
        return False
    if usuario is None:
        return False
    return (
        usuario.terms_accepted_at is None
        or usuario.terms_version != texto_legal.VERSAO
    )


@router.get("", response_model=AceiteVigente)
def ver_aceite(usuario: UserModel = Depends(require_session)) -> AceiteVigente:
    return AceiteVigente(
        exigido=settings.is_server_profile,
        aceito=not aceite_pendente(usuario),
        versao=texto_legal.VERSAO,
        titulo=texto_legal.TITULO,
        rotulo_da_caixa=texto_legal.ROTULO_DA_CAIXA,
        texto=texto_legal.TEXTO,
        versao_aceita=usuario.terms_version or "",
    )


@router.post("", response_model=AceiteVigente)
def registrar_aceite(
    pedido: PedidoDeAceite,
    usuario: UserModel = Depends(require_session),
    db: Session = Depends(get_db),
) -> AceiteVigente:
    if pedido.versao != texto_legal.VERSAO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "O aviso mudou desde que esta tela foi aberta. "
                "Recarregue a página e leia a versão vigente."
            ),
        )

    usuario.terms_accepted_at = datetime.now(timezone.utc)
    usuario.terms_version = texto_legal.VERSAO
    usuario.terms_sha256 = texto_legal.sha256()

    # O aceite e o seu registro no ROPA caem juntos se algo falhar no meio:
    # um aceite sem registro é tratamento sem prestação de contas, e um
    # registro sem aceite é prova de algo que não aconteceu.
    ropa_service.registrar(
        db,
        operation="consent_given",
        legal_basis="art7_I_consentimento",
        purpose="Ciência do aviso e dos termos do BETA, versão " + texto_legal.VERSAO,
        data_categories=["consentimento", "identificacao"],
        user_id=usuario.id,
        commit=False,
    )
    db.commit()
    db.refresh(usuario)

    logger.info("[Aceite] %s registrou ciência da versão %s", usuario.username, texto_legal.VERSAO)
    return ver_aceite(usuario)
