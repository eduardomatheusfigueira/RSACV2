#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Ambiente do Alembic (doc 40 §40.2.3).

Duas decisões que este arquivo carrega:

  * **A URL vem de `settings.effective_database_url`, não do `alembic.ini`.**
    Manter a URL no `.ini` significaria ter uma segunda fonte de verdade sobre
    qual banco é o banco — e uma delas ficaria errada. Como a mesma cadeia de
    migrações roda em SQLite (perfil `desktop`) e em PostgreSQL (perfil
    `server`), o `.ini` não teria sequer um valor correto a guardar.

  * **`render_as_batch` ligado.** SQLite não implementa `ALTER TABLE` para
    alterar ou remover coluna; o modo em lote recria a tabela, copia os dados e
    troca. Sem isso, toda migração que não fosse "adicionar coluna" quebraria no
    perfil `desktop` — que é exatamente a limitação do `_migrate_missing_columns`
    que esta cadeia veio substituir.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.types import TypeDecorator

from app.config import settings
from app.infrastructure.persistence.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# A URL **nunca** passa pelo `alembic.ini`. Além da duplicação de fonte de
# verdade, há um motivo mecânico: `set_main_option` grava no `configparser`,
# que interpreta `%` como sintaxe de interpolação. Uma senha de banco contendo
# `%` — ou qualquer URL com valor percent-encoded — faria a migração explodir
# com `ValueError: invalid interpolation syntax` na partida do servidor.


def _is_sqlite() -> bool:
    return settings.effective_database_url.startswith("sqlite")


def render_item(type_, obj, autogen_context):
    """
    Renderiza tipos personalizados pelo tipo que o banco realmente vê.

    Sem isto, a autogeração escreve `app.security.encrypted_type.EncryptedText()`
    na migração — e o arquivo gerado sequer importa `app`, então falha com
    `NameError` na primeira execução.

    Corrigir só o import seria o remendo errado. Uma migração é registro
    histórico: ela precisa continuar aplicável daqui a dois anos, quando
    `EncryptedText` pode ter sido movido, renomeado ou removido. E, para o
    banco, `EncryptedText` **é** um `TEXT` — a cifra acontece inteira na
    camada Python. Renderizar o `impl` mantém a migração correta e
    independente do código de aplicação.
    """
    if type_ == "type" and isinstance(obj, TypeDecorator):
        autogen_context.imports.add("import sqlalchemy as sa")
        # `impl` é a classe quando declarada na classe do decorador, e já uma
        # instância depois que o SQLAlchemy a resolve. Aceitar as duas formas
        # evita depender de qual delas chega aqui.
        impl = obj.impl
        nome = impl.__name__ if isinstance(impl, type) else type(impl).__name__
        return f"sa.{nome}()"
    return False


def run_migrations_offline() -> None:
    """Gera SQL sem conectar — usado para revisar uma migração antes de aplicá-la."""
    context.configure(
        url=settings.effective_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_is_sqlite(),
        compare_type=True,
        compare_server_default=True,
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Aplica as migrações.

    Aceita uma conexão pronta em `config.attributes["connection"]` — é como
    `app/schema.py` chama daqui de dentro da aplicação, reaproveitando o engine
    que já existe. Sem ela, abre a própria conexão a partir de `settings`, que
    é o caminho da linha de comando (`alembic upgrade head`).
    """
    conexao_externa = config.attributes.get("connection")
    if conexao_externa is not None:
        _executar(conexao_externa)
        return

    connectable = create_engine(settings.effective_database_url, poolclass=pool.NullPool)
    try:
        with connectable.connect() as connection:
            _executar(connection)
    finally:
        connectable.dispose()


def _executar(connection) -> None:
    """Configura o contexto e roda a cadeia sobre a conexão recebida."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Sem isto, uma mudança de tipo de coluna passa despercebida pela
        # autogeração e a migração "não vê" o que mudou.
        compare_type=True,
        compare_server_default=True,
        render_as_batch=_is_sqlite(),
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
