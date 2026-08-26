#!/usr/bin/env python

"""
RSAC V2 — Token local do perfil desktop (doc 29 §29.3.2).

O problema que este módulo resolve: autenticar o app de mesa sem transformar o
uso local numa tela de login. Se a proteção atrapalhar quem roda o RSAC na
própria máquina, ela será contornada — e aí não protege ninguém.

A solução é a mesma de Jupyter e do Docker Desktop: no primeiro start o backend
sorteia um token, grava num arquivo que só o dono lê (`0600`) e aceita esse
token como prova de que o cliente roda na mesma máquina — porque só quem já tem
acesso ao sistema de arquivos do usuário consegue lê-lo.

Isto vale **apenas** no perfil `desktop`. No perfil `server` o arquivo não é
criado nem aceito: lá a prova de identidade é a senha da conta.
"""

from __future__ import annotations

import contextlib
import logging
import os
import secrets
import stat
import sys
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

TOKEN_FILENAME = "runtime_token"
_TOKEN_BYTES = 32


def token_path() -> Path:
    """Caminho do arquivo do token na pasta de dados do usuário."""
    return Path(settings.data_dir) / TOKEN_FILENAME


def _restringir_permissoes(caminho: Path) -> None:
    """
    Deixa o arquivo legível só pelo dono.

    No Windows `chmod` não representa ACL, então a chamada é inócua ali; a pasta
    de dados do usuário (`%LOCALAPPDATA%`) já é protegida pelo perfil. Falhar
    aqui não deve derrubar o backend — mas precisa aparecer no log.
    """
    try:
        os.chmod(caminho, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:  # pragma: no cover — depende do sistema de arquivos
        logger.warning("[Auth] Não foi possível restringir permissões de %s: %s", caminho, exc)


def ensure_local_token() -> str | None:
    """
    Garante um token local para esta instalação e devolve-o.

    O arquivo é criado na primeira partida e reaproveitado depois.
    """
    caminho = token_path()
    if caminho.exists():
        try:
            existente = caminho.read_text(encoding="utf-8").strip()
            if existente:
                _restringir_permissoes(caminho)
                return existente
        except OSError as exc:
            logger.warning("[Auth] Token local ilegível (%s), gerando outro: %s", caminho, exc)

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(token, encoding="utf-8")
        _restringir_permissoes(caminho)
        # A pasta de dados restrita ao dono é reforço, não requisito: em
        # sistema de arquivos que não representa modo POSIX a chamada falha, e
        # o token continua protegido pelas próprias permissões.
        with contextlib.suppress(OSError):  # pragma: no cover
            os.chmod(caminho.parent, stat.S_IRWXU)
    except OSError as exc:
        logger.error("[Auth] Falha ao gravar o token local em %s: %s", caminho, exc)
        return None

    logger.info("[Auth] Token local do perfil desktop gerado em %s", caminho)
    return token


def read_local_token() -> str | None:
    """Lê o token local já existente, sem criar um novo."""
    caminho = token_path()
    if not caminho.exists():
        return None
    try:
        token = caminho.read_text(encoding="utf-8").strip()
        return token or None
    except OSError:
        return None


def matches_local_token(candidate: str | None) -> bool:
    """
    O token apresentado é o desta instalação?

    Comparação em tempo constante: uma comparação comum vaza, pelo tempo, o
    tamanho do prefixo acertado — o que transforma adivinhar 32 bytes em
    adivinhar um byte por vez.
    """
    if not candidate:
        return False
    atual = read_local_token()
    if not atual:
        return False
    return secrets.compare_digest(candidate, atual)


def descrever_para_log() -> str:
    """Linha amigável para o log de inicialização, sem revelar o token."""
    caminho = token_path()
    plataforma = "Windows" if sys.platform == "win32" else "POSIX"
    return f"token local em {caminho} ({plataforma})"
