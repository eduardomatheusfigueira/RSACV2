#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Hash de Senhas (doc 29 §29.3.3).

Argon2id, vencedor da Password Hashing Competition e recomendação atual da
OWASP. O custo é deliberado: cada verificação leva dezenas de milissegundos,
o que é irrelevante para quem digita a senha e caro para quem tenta um
dicionário.

Nunca use SHA/MD5 aqui, com ou sem sal — são rápidos por projeto, que é
exatamente o contrário do que se quer de um hash de senha.
"""

from __future__ import annotations

import secrets
import string

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Parâmetros do perfil RFC 9106 "low memory" (64 MiB, 3 passagens): dá margem
# confortável em máquina de pesquisador sem inviabilizar o login.
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

MIN_PASSWORD_LENGTH = 12
_ALFABETO_SENHA = string.ascii_letters + string.digits + "!@#$%&*-_=+?"


class PasswordPolicyError(ValueError):
    """A senha informada não satisfaz a política mínima."""


def validate_password(password: str) -> str:
    """Valida a senha contra a política e devolve a versão utilizável."""
    if not password or not password.strip():
        raise PasswordPolicyError("A senha não pode ficar em branco.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"A senha precisa ter ao menos {MIN_PASSWORD_LENGTH} caracteres."
        )
    return password


def hash_password(password: str) -> str:
    """Gera o hash Argon2id da senha, já validada pela política."""
    return _hasher.hash(validate_password(password))


def verify_password(password_hash: str, password: str) -> bool:
    """
    Confere a senha contra o hash.

    Devolve `False` em qualquer falha — inclusive hash corrompido — em vez de
    propagar exceção, para que a rota de login trate todos os casos pelo mesmo
    caminho e não vaze pela mensagem de erro qual deles ocorreu.
    """
    if not password_hash or not password:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """O hash foi gerado com parâmetros mais fracos que os atuais?"""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return False


def generate_password(length: int = 20) -> str:
    """
    Senha aleatória para provisionamento inicial.

    O provisionamento nunca inventa uma senha fixa no código: gera esta,
    mostra uma vez e não a guarda em lugar nenhum além do hash.
    """
    size = max(length, MIN_PASSWORD_LENGTH)
    return "".join(secrets.choice(_ALFABETO_SENHA) for _ in range(size))
