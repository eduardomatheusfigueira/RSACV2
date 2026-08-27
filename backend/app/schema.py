#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Aplicação do esquema na partida (doc 40 §40.2.3).

Substitui `_migrate_missing_columns`, que evoluía o banco emitindo
`ALTER TABLE ... ADD COLUMN` para toda coluna que existisse no modelo e não no
banco. Aquilo resolvia um caso — coluna nova — e silenciava todos os outros:
não renomeava, não mudava tipo, não preenchia dado, não revertia, e engolia a
exceção num `logger.warning`. Num aplicativo de mesa, onde o dado é do próprio
usuário e um erro se conserta apagando o arquivo, era um risco aceitável. Num
servidor com dados de terceiros, não é.

O caso que exige cuidado aqui não é o banco novo — é o banco **antigo**: uma
instalação de mesa tem as tabelas todas e nenhuma noção de Alembic. Rodar
`upgrade head` nela tentaria criar tabelas que já existem e falharia. Por isso
a decisão de três vias abaixo.
"""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.config import settings

logger = logging.getLogger(__name__)

# `alembic.ini` e a pasta de versões vivem na raiz do backend, ao lado de
# `app/`. Resolver por `__file__` mantém o caminho correto tanto no
# desenvolvimento quanto dentro do contêiner.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"


def _alembic_config(connection=None) -> Config:
    """
    Configuração do Alembic para uso programático.

    A URL **não** é gravada no `Config`: `set_main_option` escreve no
    `configparser`, que trata `%` como sintaxe de interpolação e rejeitaria uma
    senha de banco que o contenha. A conexão viaja por `attributes`, que é
    dicionário puro, e `env.py` a usa quando presente.
    """
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def _revisao_atual(engine: Engine) -> str | None:
    """Revisão registrada no banco, ou `None` se ele não conhece o Alembic."""
    with engine.connect() as conexao:
        return MigrationContext.configure(conexao).get_current_revision()


def _tem_tabelas_da_aplicacao(engine: Engine) -> bool:
    """O banco já tem esquema do RSAC gravado por uma versão anterior?"""
    tabelas = set(inspect(engine).get_table_names())
    tabelas.discard("alembic_version")
    return bool(tabelas)


def aplicar_migracoes(engine: Engine) -> None:
    """
    Deixa o banco na revisão mais recente, qualquer que seja o estado inicial.

    Três vias, e a do meio é a que existe por causa dos usuários que já têm o
    aplicativo instalado:

    1. **Banco que já conhece o Alembic** → `upgrade head`, o caminho normal.
    2. **Banco com tabelas e sem `alembic_version`** → instalação anterior a
       este trabalho. Carimba-se a revisão inicial (`stamp`), declarando que
       aquele esquema *é* o inicial, e só então se aplicam as revisões
       seguintes. Sem o carimbo, o `upgrade` tentaria criar tabelas existentes;
       com ele, a instalação de mesa atualiza sozinha, sem passo manual e sem
       perder dado.
    3. **Banco vazio** → `upgrade head` cria tudo do zero.
    """
    revisao = _revisao_atual(engine)

    if revisao is None and _tem_tabelas_da_aplicacao(engine):
        logger.info(
            "[Esquema] Banco anterior ao versionamento detectado. "
            "Carimbando a revisão inicial antes de migrar."
        )
        _carimbar_revisao_inicial(engine)
    with engine.begin() as conexao:
        command.upgrade(_alembic_config(conexao), "head")
    logger.info("[Esquema] Banco na revisão mais recente.")


def _carimbar_revisao_inicial(engine: Engine) -> None:
    """
    Declara que o esquema existente **é** a revisão inicial.

    A revisão inicial foi gerada a partir deste mesmo esquema, então executá-la
    tentaria criar tabelas que já existem. Carimbar registra o estado sem tocar
    em nada — e é o que permite que as revisões seguintes se apliquem em ordem.
    """
    from alembic.script import ScriptDirectory

    with engine.begin() as conexao:
        config = _alembic_config(conexao)
        inicial = next(
            script.revision
            for script in ScriptDirectory.from_config(config).walk_revisions()
            if script.down_revision is None
        )
        command.stamp(config, inicial)
