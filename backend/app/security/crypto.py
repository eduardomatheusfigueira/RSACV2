#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Cifra de segredos em repouso (doc 29 §29.4.1).

O que este módulo corrige: as colunas do banco chamadas `*_encrypted`
guardavam `json.dumps(lista)` puro. O sufixo era falso, e o dano específico do
nome mentiroso é que ele **desliga a vigilância de quem revisa** — quem passa
por `gemini_api_keys_encrypted` conclui que a cifra está resolvida e não olha
de novo.

Agora o nome é verdadeiro. Todo valor gravado sai daqui como
`v1:<token Fernet>`; o prefixo de versão é o que permite (a) reconhecer um
valor legado em claro e migrá-lo sem intervenção, e (b) trocar o esquema no
futuro sem adivinhar o formato do que já está gravado.

Origem da chave-mestra, em ordem:
  1. `RSAC_SECRET_KEY` no ambiente — **obrigatório** no perfil `server`;
  2. `<data_dir>/master.key`, gerado com permissão `0600` — só fora do `server`.

A restrição do perfil `server` não é preciosismo: V-04 mostrou que um arquivo
ao lado do banco pode ser lido pela mesma falha que lê o banco. Guardar a
chave junto do cofre não é guardar a chave.
"""

from __future__ import annotations

import base64
import logging
import os
import stat
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.config import settings

logger = logging.getLogger(__name__)

# Prefixo de versão do formato. Valor sem prefixo é legado em texto claro.
CIPHER_PREFIX = "v1:"
MASTER_KEY_FILENAME = "master.key"

# Sal fixo do HKDF. Não precisa ser secreto — serve para separar domínios, de
# modo que a mesma `RSAC_SECRET_KEY` usada em outro contexto não produza a
# mesma chave de cifra.
_HKDF_INFO = b"rsac-v2-secret-column-encryption"
_HKDF_SALT = b"rsac-v2-kdf-salt"


class MasterKeyError(RuntimeError):
    """A chave-mestra não pôde ser obtida na configuração corrente."""


def _derivar_chave(material: bytes) -> bytes:
    """
    Deriva uma chave Fernet de 32 bytes a partir de material arbitrário.

    `RSAC_SECRET_KEY` é escrita por uma pessoa e pode ser qualquer coisa — uma
    frase, um hexadecimal, uma senha. O HKDF normaliza isso para o tamanho
    exato que o Fernet exige, em vez de obrigar o usuário a gerar uma chave no
    formato certo.
    """
    derivada = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=_HKDF_INFO,
    ).derive(material)
    return base64.urlsafe_b64encode(derivada)


def master_key_path() -> Path:
    return Path(settings.data_dir) / MASTER_KEY_FILENAME


def _ler_ou_criar_arquivo_de_chave() -> bytes:
    """Chave-mestra em arquivo, criada na primeira execução com `0600`."""
    caminho = master_key_path()
    if caminho.exists():
        conteudo = caminho.read_text(encoding="utf-8").strip()
        if conteudo:
            return conteudo.encode("utf-8")

    material = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(material, encoding="utf-8")
    try:
        os.chmod(caminho, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:  # pragma: no cover — depende do sistema de arquivos
        logger.warning("[Crypto] Não foi possível restringir permissões de %s: %s", caminho, exc)

    logger.info("[Crypto] Chave-mestra gerada em %s", caminho)
    return material.encode("utf-8")


def obter_chave_mestra() -> bytes:
    """
    Devolve o material da chave-mestra segundo o perfil de implantação.

    No perfil `server` a chave **precisa** vir do ambiente: gerar um arquivo
    ali daria a sensação de proteção sem a proteção.
    """
    do_ambiente = (settings.secret_key or "").strip()
    if do_ambiente:
        return do_ambiente.encode("utf-8")

    if settings.is_server_profile:
        raise MasterKeyError(
            "RSAC_SECRET_KEY não está definida e o perfil é 'server'. "
            "No modo servidor a chave-mestra precisa vir do ambiente — um "
            "arquivo ao lado do banco seria lido pela mesma falha que leria o "
            "banco. Gere uma chave e exporte-a antes de publicar:\n"
            "    python -m app.cli generate-secret-key"
        )

    return _ler_ou_criar_arquivo_de_chave()


class SecretCipher:
    """
    Cifra e decifra valores de coluna.

    A chave é resolvida na primeira utilização, não no import: o perfil de
    implantação e o diretório de dados precisam estar definidos, e amarrar
    isso ao momento do import tornaria o módulo impossível de testar com
    configurações diferentes.
    """

    def __init__(self, key_material: Optional[bytes] = None):
        self._material = key_material
        self._fernet: Optional[Fernet] = None

    @property
    def fernet(self) -> Fernet:
        if self._fernet is None:
            material = self._material if self._material is not None else obter_chave_mestra()
            self._fernet = Fernet(_derivar_chave(material))
        return self._fernet

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """Cifra um valor. `None` e string vazia passam intactos."""
        if plaintext is None:
            return None
        if plaintext == "":
            return ""
        if is_encrypted(plaintext):
            return plaintext  # idempotente — não cifra duas vezes
        token = self.fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")
        return f"{CIPHER_PREFIX}{token}"

    def decrypt(self, stored: Optional[str]) -> Optional[str]:
        """
        Decifra um valor gravado.

        Valor **sem** prefixo é legado em texto claro e volta como está: é o
        que permite um banco da versão anterior subir e continuar funcionando
        enquanto a migração o reescreve.
        """
        if stored is None or stored == "":
            return stored
        if not is_encrypted(stored):
            return stored

        try:
            return self.fernet.decrypt(stored[len(CIPHER_PREFIX):].encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            # Chave-mestra trocada ou banco de outra instalação. Devolver o
            # texto cifrado seria pior: viraria "chave de API" corrompida
            # enviada ao provedor. Melhor tratar como ausente e registrar.
            logger.error(
                "[Crypto] Falha ao decifrar um segredo — a chave-mestra mudou "
                "ou o banco veio de outra instalação (%s).",
                type(exc).__name__,
            )
            return None


def is_encrypted(value: Optional[str]) -> bool:
    """O valor já está no formato cifrado desta implementação?"""
    return bool(value) and isinstance(value, str) and value.startswith(CIPHER_PREFIX)


# Instância compartilhada usada pelo tipo de coluna.
cipher = SecretCipher()


def reset_cipher_cache() -> None:
    """Descarta a chave em cache — usado pelos testes ao trocar de perfil."""
    cipher._material = None
    cipher._fernet = None
