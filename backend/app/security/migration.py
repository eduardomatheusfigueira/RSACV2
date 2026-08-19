#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Migração dos segredos gravados em texto claro (doc 29 §29.4.1).

Bancos criados antes da Fase 2 têm chaves de API em claro nas colunas
`*_encrypted`. `EncryptedText` já as **lê** sem quebrar, mas enquanto elas não
forem reescritas o `strings rsac.db | grep AIza` continua entregando tudo — e
é exatamente esse o critério de aceite da fase.

A migração roda na partida, é idempotente (valor já cifrado é reconhecido pelo
prefixo `v1:` e ignorado) e usa SQL direto de propósito: passar pelo ORM faria
o `EncryptedText` decifrar na leitura, e aí não haveria como distinguir o que
já estava cifrado do que não estava.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.security.crypto import cipher, is_encrypted

logger = logging.getLogger(__name__)

# Tabela → colunas que guardam segredo.
COLUNAS_SECRETAS: dict[str, tuple[str, ...]] = {
    "ai_settings": (
        "api_keys_encrypted",
        "gemini_api_keys_encrypted",
        "qwen_api_keys_encrypted",
        "local_api_keys_encrypted",
    ),
    "source_credentials": ("api_key", "inst_token"),
}


def cifrar_segredos_legados(engine: Engine) -> int:
    """
    Reescreve cifrado todo valor ainda em texto claro. Devolve quantos migrou.

    Falhar aqui não pode derrubar o backend: um banco de outra instalação, ou
    uma chave-mestra trocada, tornaria o app impossível de abrir — o que é pior
    que seguir com os segredos como estão e registrar o problema.
    """
    total = 0

    try:
        with engine.begin() as conn:
            tabelas = {
                linha[0]
                for linha in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }

            for tabela, colunas in COLUNAS_SECRETAS.items():
                if tabela not in tabelas:
                    continue

                existentes = {
                    linha[1] for linha in conn.execute(text(f"PRAGMA table_info({tabela})"))
                }
                alvo = [c for c in colunas if c in existentes]
                if not alvo:
                    continue

                lista = ", ".join(alvo)
                linhas = conn.execute(text(f"SELECT id, {lista} FROM {tabela}")).fetchall()

                for linha in linhas:
                    registro_id = linha[0]
                    atualizacoes: dict[str, str] = {}

                    for indice, coluna in enumerate(alvo, start=1):
                        valor = linha[indice]
                        if valor is None or valor == "" or is_encrypted(valor):
                            continue
                        cifrado = cipher.encrypt(valor)
                        if cifrado is not None:
                            atualizacoes[coluna] = cifrado

                    if not atualizacoes:
                        continue

                    atribuicoes = ", ".join(f"{c} = :{c}" for c in atualizacoes)
                    conn.execute(
                        text(f"UPDATE {tabela} SET {atribuicoes} WHERE id = :registro_id"),
                        {**atualizacoes, "registro_id": registro_id},
                    )
                    total += len(atualizacoes)

    except Exception as exc:  # noqa: BLE001 — não pode impedir o app de subir
        logger.error(
            "[Crypto] Falha ao migrar segredos legados para o formato cifrado: %s", exc
        )
        return 0

    if total:
        logger.info("[Crypto] %d segredo(s) em texto claro migrado(s) para o formato cifrado.", total)
    return total
