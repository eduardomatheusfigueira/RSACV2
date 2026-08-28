#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Estado da autenticação com Google (doc 40 §40.4.1).

Três decisões concentradas num arquivo pequeno:

* **Uso único.** Consumir o estado o apaga. É o que fecha a repetição do
  callback: um código de autorização capturado não pode ser reapresentado,
  porque o estado que o acompanharia já não existe.
* **Validade curta.** Dez minutos cobrem com folga a tela de consentimento do
  Google e não deixam estado pendurado.
* **Destino interno.** O caminho de retorno é validado na gravação, não na
  leitura: aceitar uma URL absoluta faria do callback um redirecionador aberto,
  e o link de login viraria isca de phishing com o domínio do Revsist na barra de
  endereços.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import OAuthStateModel, as_utc

VALIDADE_MINUTOS = 10
DESTINO_PADRAO = "/app"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def destino_seguro(candidato: Optional[str]) -> str:
    """
    Normaliza o caminho de retorno, recusando qualquer coisa que saia do site.

    Aceita apenas caminho absoluto de uma barra só. `//evil.com` é recusado
    porque o navegador o trata como URL de esquema relativo — é o disfarce
    clássico do redirecionamento aberto, e passa despercebido por quem só
    verifica se a string começa com `/`.
    """
    if not candidato:
        return DESTINO_PADRAO
    caminho = candidato.strip()
    if not caminho.startswith("/") or caminho.startswith("//"):
        return DESTINO_PADRAO
    if "\\" in caminho or "\n" in caminho or "\r" in caminho:
        return DESTINO_PADRAO
    return caminho[:200]


def criar(
    db: Session, *, code_verifier: str, nonce: str, redirect_after: Optional[str] = None
) -> OAuthStateModel:
    """Grava um fluxo em curso e devolve o registro."""
    registro = OAuthStateModel(
        state=secrets.token_urlsafe(32)[:64],
        code_verifier=code_verifier,
        nonce=nonce,
        redirect_after=destino_seguro(redirect_after),
        expires_at=_utcnow() + timedelta(minutes=VALIDADE_MINUTOS),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def consumir(db: Session, state: Optional[str]) -> Optional[OAuthStateModel]:
    """
    Recupera e **apaga** o estado. Devolve `None` se não existir ou tiver
    vencido.

    O registro é destacado da sessão antes de ser apagado para que quem chamou
    continue podendo ler `nonce` e `code_verifier` — que é justamente para o que
    ele serve.
    """
    if not state:
        return None

    registro = db.query(OAuthStateModel).filter(OAuthStateModel.state == state).first()
    if registro is None:
        return None

    vencido = as_utc(registro.expires_at) <= _utcnow()
    dados = OAuthStateModel(
        state=registro.state,
        code_verifier=registro.code_verifier,
        nonce=registro.nonce,
        redirect_after=registro.redirect_after,
        expires_at=registro.expires_at,
    )
    db.delete(registro)
    db.commit()

    return None if vencido else dados


def expurgar_vencidos(db: Session) -> int:
    """Remove estados vencidos. Chamado pela rotina de retenção."""
    total = (
        db.query(OAuthStateModel)
        .filter(OAuthStateModel.expires_at <= _utcnow())
        .delete(synchronize_session=False)
    )
    db.commit()
    return total
