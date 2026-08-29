#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Provisionamento da conta local (doc 29 §29.3.2).

O perfil `desktop` autentica pelo token local: quem tem o arquivo já tem o
sistema de arquivos do usuário, e exigir senha por cima disso seria atrito sem
barreira. Só que o token não autentica sozinho — ele **resolve para uma conta**,
e sem nenhuma conta no banco não resolve para nada.

O efeito era uma instalação nova que subia normalmente e respondia 401 a tudo,
abrindo na tela de login para pedir um comando de terminal. Este módulo fecha
esse buraco: a instalação de mesa ganha sua titular na primeira partida.
"""

from __future__ import annotations

import logging

from app.infrastructure.persistence.models import UserModel

logger = logging.getLogger(__name__)

USUARIO_LOCAL = "local"

# Marcador de senha inutilizável, na convenção que o Django popularizou. Não é
# um hash Argon2 válido, então `verify_password` recusa qualquer senha contra
# ele — a conta existe para o token local ter um titular, não para login por
# senha. Quem quiser senha usa `python -m app.cli reset-password local`.
SENHA_INUTILIZAVEL = "!"


def senha_inutilizavel(password_hash: str | None) -> bool:
    """A conta tem senha com a qual seja possível entrar?"""
    return not password_hash or password_hash.strip() in {"", SENHA_INUTILIZAVEL}


def provisionar_conta_local(session_factory) -> int:
    """
    Garante a conta dona da instalação. Devolve o total de contas ativas.

    Idempotente: se já houver qualquer conta ativa, não faz nada. O papel é
    `owner` porque esta é a dona do acervo daquela máquina — a mesma pessoa que
    já tinha acesso irrestrito pelo sistema de arquivos.
    """
    db = session_factory()
    try:
        ativas = db.query(UserModel).filter(UserModel.is_active == True).count()  # noqa: E712
        if ativas:
            return ativas

        nome = USUARIO_LOCAL
        n = 1
        while db.query(UserModel).filter(UserModel.username == nome).first():
            n += 1
            nome = f"{USUARIO_LOCAL}-{n}"

        db.add(
            UserModel(
                username=nome,
                password_hash=SENHA_INUTILIZAVEL,
                role="owner",
                display_name="Instalação local",
                auth_provider="password",
            )
        )
        db.commit()
        logger.info("[Provisionamento] Conta local '%s' criada.", nome)
        return 1
    finally:
        db.close()
