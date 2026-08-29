#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Utilitário de Rotação de Chave Mestra (doc 40 §40.7.3, doc 41 Tarefa 4.14).

Recifra atomicamente todas as colunas de credenciais e chaves de API com uma nova
chave mestra (RSAC_SECRET_KEY), sem perda de dados e com rollback em caso de falha.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Garantir que o backend está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import settings
from app.security.crypto import obter_chave_mestra
from app.security.key_rotation import rotacionar_chaves


def main():
    parser = argparse.ArgumentParser(
        description="Revsist — Utilitário de Rotação de Chave Mestra (RSAC_SECRET_KEY)"
    )
    parser.add_argument(
        "--old-key",
        type=str,
        default="",
        help="Chave mestra antiga (se omitida, tenta ler da configuração atual)",
    )
    parser.add_argument(
        "--new-key",
        type=str,
        required=True,
        help="Nova chave mestra que substituirá a anterior",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default="",
        help="URL do banco de dados (se omitida, usa RSAC_DATABASE_URL)",
    )

    args = parser.parse_args()

    db_url = args.db_url or settings.effective_database_url
    old_key = args.old_key
    if not old_key:
        try:
            old_key = obter_chave_mestra().decode("utf-8")
        except Exception as exc:
            logger.error("Não foi possível obter a chave antiga automaticamente: %s", exc)
            sys.exit(1)

    new_key = args.new_key.strip()
    if len(new_key) < 16:
        logger.error("A nova chave mestra deve ter pelo menos 16 caracteres de entropia.")
        sys.exit(1)

    engine = create_engine(db_url)
    try:
        rotacionar_chaves(engine, old_key, new_key)
        print("\nSUCESSO: Chaves rotacionadas com segurança.")
        print(f"Atualize a variável RSAC_SECRET_KEY no arquivo .env com a nova chave e reinicie o contêiner.\n")
    except Exception as exc:
        print(f"\nERRO: Rotação cancelada e revertida: {exc}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
