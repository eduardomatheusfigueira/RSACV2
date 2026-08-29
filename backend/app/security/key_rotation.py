#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Módulo de Rotação de Chave Mestra (doc 40 §40.7.3, doc 41 Tarefa 4.14).

Recifra atomicamente todas as colunas de credenciais e chaves de API com uma nova
chave mestra (RSAC_SECRET_KEY), sem perda de dados e com rollback em caso de falha.
"""

from __future__ import annotations

import logging
from typing import Any, Union

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

from app.security.crypto import CIPHER_PREFIX, _derivar_chave

logger = logging.getLogger(__name__)

# Tabela -> colunas que guardam valores cifrados
COLUNAS_SECRETAS: dict[str, tuple[str, ...]] = {
    "ai_settings": (
        "gemini_api_keys_encrypted",
        "qwen_api_keys_encrypted",
        "local_api_keys_encrypted",
    ),
    "source_credentials": ("api_key", "inst_token"),
}


def rotacionar_chaves(
    engine_ou_conexao: Union[Engine, Connection],
    old_key_material: str,
    new_key_material: str,
) -> dict[str, int]:
    """
    Decifra as colunas secretas com old_key e recifra com new_key via SQL direto.
    Executa tudo dentro de uma única transação atômica.
    """
    if not old_key_material or not new_key_material:
        raise ValueError("Tanto a chave antiga quanto a nova devem ser informadas.")

    if old_key_material == new_key_material:
        raise ValueError("A nova chave deve ser diferente da chave anterior.")

    old_fernet = Fernet(_derivar_chave(old_key_material.encode("utf-8")))
    new_fernet = Fernet(_derivar_chave(new_key_material.encode("utf-8")))

    inspector = inspect(engine_ou_conexao)
    tabelas_existentes = set(inspector.get_table_names())

    def _executar_em_conexao(conn: Connection) -> tuple[int, int]:
        total_ai = 0
        total_sources = 0

        for tabela, colunas in COLUNAS_SECRETAS.items():
            if tabela not in tabelas_existentes:
                continue

            colunas_existentes = {c["name"] for c in inspector.get_columns(tabela)}
            alvo = [c for c in colunas if c in colunas_existentes]
            if not alvo:
                continue

            lista_cols = ", ".join(alvo)
            linhas = conn.execute(text(f"SELECT id, {lista_cols} FROM {tabela}")).fetchall()

            for linha in linhas:
                registro_id = linha[0]
                atualizacoes: dict[str, str] = {}

                for indice, coluna in enumerate(alvo, start=1):
                    val = linha[indice]
                    if val and isinstance(val, str) and val.startswith(CIPHER_PREFIX):
                        token = val[len(CIPHER_PREFIX) :].encode("ascii")
                        try:
                            decifrado = old_fernet.decrypt(token).decode("utf-8")
                        except InvalidToken as exc:
                            raise RuntimeError(
                                f"Falha ao decifrar coluna '{coluna}' no registro {registro_id} da tabela '{tabela}' com a chave antiga."
                            ) from exc

                        novo_token = new_fernet.encrypt(decifrado.encode("utf-8")).decode("ascii")
                        atualizacoes[coluna] = f"{CIPHER_PREFIX}{novo_token}"

                if atualizacoes:
                    atribuicoes = ", ".join(f"{c} = :{c}" for c in atualizacoes)
                    conn.execute(
                        text(f"UPDATE {tabela} SET {atribuicoes} WHERE id = :id"),
                        {**atualizacoes, "id": registro_id},
                    )
                    if tabela == "ai_settings":
                        total_ai += 1
                    elif tabela == "source_credentials":
                        total_sources += 1

        return total_ai, total_sources

    if isinstance(engine_ou_conexao, Engine):
        with engine_ou_conexao.begin() as conn:
            total_ai, total_sources = _executar_em_conexao(conn)
    else:
        total_ai, total_sources = _executar_em_conexao(engine_ou_conexao)

    logger.info(
        "[Rotação] Concluída com sucesso! Atualizados: %d configurações de IA, %d credenciais de fontes.",
        total_ai,
        total_sources,
    )
    return {"ai_settings_atualizados": total_ai, "source_credentials_atualizadas": total_sources}
