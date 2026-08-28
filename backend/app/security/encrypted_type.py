#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Tipo de coluna cifrada (doc 29 §29.4.1).

`EncryptedText` cifra ao gravar e decifra ao ler, de modo que o resto da
aplicação continua tratando a coluna como texto comum. Isso importa porque a
alternativa — cifrar e decifrar em cada ponto de uso — depende de ninguém
esquecer, e o histórico deste código mostra exatamente o que acontece quando
a proteção depende de lembrança.

O tipo tolera valor legado em texto claro na leitura: um banco da versão
anterior sobe e funciona, e a migração de `app/security/migration.py` o
reescreve cifrado. Sem essa tolerância, atualizar o app apagaria as chaves de
quem já usava o produto.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.security.crypto import cipher


class EncryptedText(TypeDecorator):
    """Coluna `Text` cujo conteúdo é cifrado em repouso."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Grava cifrado."""
        if value is None:
            return None
        return cipher.encrypt(str(value))

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """
        Lê decifrado.

        Um valor que falhou ao decifrar volta como `None` (ver `crypto.decrypt`):
        devolver o texto cifrado seria pior, porque viraria "chave de API"
        corrompida enviada ao provedor.
        """
        if value is None:
            return None
        return cipher.decrypt(value)
