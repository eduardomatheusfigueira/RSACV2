#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Cofre de Exportação (doc 29 §29.4.3).

Cifra o pacote de credenciais com uma senha escolhida pelo usuário no momento
da exportação. O arquivo de backup deixa de ser um JSON de chaves legível por
quem o encontrar — em disco, num anexo de e-mail ou numa pasta sincronizada
com a nuvem.

Derivação: PBKDF2-HMAC-SHA256 com sal aleatório de 16 bytes e 600 000
iterações (recomendação OWASP para PBKDF2-SHA256), produzindo a chave de um
Fernet (AES-128-CBC + HMAC-SHA256, com autenticação — senha errada falha em
vez de devolver lixo).

O envelope guarda os parâmetros da derivação: um backup feito hoje continua
abrindo depois que o custo de iteração for aumentado.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ENVELOPE_SCHEMA = "rsac_encrypted_envelope_v1"
KDF_NAME = "pbkdf2-sha256"
KDF_ITERATIONS = 600_000
SALT_BYTES = 16

# Curta demais e a derivação não compensa; este é o piso, não a recomendação.
MIN_PASSWORD_LENGTH = 8


class SecretBoxError(ValueError):
    """Falha de cifra, decifra ou de formato do envelope."""


def _derive_key(password: str, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def validate_password(password: str) -> str:
    """Valida a senha de exportação e devolve a versão utilizável."""
    if not password or not password.strip():
        raise SecretBoxError("Informe uma senha para proteger o arquivo exportado.")
    clean = password.strip()
    if len(clean) < MIN_PASSWORD_LENGTH:
        raise SecretBoxError(
            f"A senha de exportação precisa ter ao menos {MIN_PASSWORD_LENGTH} caracteres."
        )
    return clean


def encrypt_payload(payload: Dict[str, Any], password: str) -> Dict[str, Any]:
    """Cifra `payload` e devolve o envelope pronto para ser serializado."""
    clean_password = validate_password(password)
    salt = os.urandom(SALT_BYTES)
    key = _derive_key(clean_password, salt, KDF_ITERATIONS)

    plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    token = Fernet(key).encrypt(plaintext)

    return {
        "schema_version": ENVELOPE_SCHEMA,
        "encrypted": True,
        "kdf": KDF_NAME,
        "iterations": KDF_ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "ciphertext": token.decode("ascii"),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


def is_envelope(data: Any) -> bool:
    """O objeto recebido é um envelope cifrado desta implementação?"""
    return (
        isinstance(data, dict)
        and data.get("schema_version") == ENVELOPE_SCHEMA
        and bool(data.get("ciphertext"))
    )


def decrypt_envelope(envelope: Dict[str, Any], password: str) -> Dict[str, Any]:
    """Abre um envelope cifrado. Senha errada levanta `SecretBoxError`."""
    if not is_envelope(envelope):
        raise SecretBoxError("O conteúdo informado não é um arquivo cifrado do RSAC.")
    if not password or not password.strip():
        raise SecretBoxError("Este arquivo está protegido por senha. Informe a senha usada na exportação.")

    try:
        salt = base64.b64decode(envelope["salt"])
        iterations = int(envelope.get("iterations", KDF_ITERATIONS))
        key = _derive_key(password.strip(), salt, iterations)
        plaintext = Fernet(key).decrypt(envelope["ciphertext"].encode("ascii"))
    except InvalidToken as exc:
        raise SecretBoxError("Senha incorreta ou arquivo corrompido.") from exc
    except (KeyError, ValueError, TypeError) as exc:
        raise SecretBoxError(f"Arquivo de backup inválido: {exc}") from exc

    try:
        return json.loads(plaintext.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise SecretBoxError("O conteúdo decifrado não é um JSON válido.") from exc
