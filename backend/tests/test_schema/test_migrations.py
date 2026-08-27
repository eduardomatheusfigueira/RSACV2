#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Testes da cadeia de migrações (doc 41, Fase 0).

O que estes testes protegem não é o Alembic — é a promessa de que **um banco de
mesa já existente atualiza sozinho, sem perder dado**. Essa promessa vale para
usuários reais que instalaram o RSAC antes do versionamento existir, e é a
única parte da Fase 0 cujo erro não aparece em nenhuma outra suíte: um banco
novo funciona de qualquer jeito.

Os testes rodam contra o banco que `RSAC_TEST_DATABASE_URL` indicar — SQLite em
arquivo por padrão, PostgreSQL na CI —, porque o caminho em lote do SQLite
(`render_as_batch`) e o DDL transacional do PostgreSQL são bem diferentes, e a
cadeia precisa valer nos dois.
"""

from __future__ import annotations

import os
import uuid

import pytest
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.infrastructure.persistence.models import Base
from app.schema import _alembic_config, aplicar_migracoes

TEST_DATABASE_URL = os.environ.get("RSAC_TEST_DATABASE_URL", "").strip()


@pytest.fixture
def url_descartavel(tmp_path, monkeypatch):
    """
    URL de um banco vazio e exclusivo deste teste.

    Em PostgreSQL, um *schema* próprio por teste dá o mesmo isolamento que um
    arquivo novo dá no SQLite, sem precisar de permissão para criar bancos.
    """
    if not TEST_DATABASE_URL:
        url = f"sqlite:///{tmp_path / 'migracao.db'}"
        monkeypatch.setenv("RSAC_DATABASE_URL", url)
        _recarregar_settings(monkeypatch, url)
        yield url
        return

    nome_schema = f"mig_{uuid.uuid4().hex[:12]}"
    administrador = create_engine(TEST_DATABASE_URL)
    with administrador.begin() as conexao:
        conexao.execute(text(f'CREATE SCHEMA "{nome_schema}"'))
    administrador.dispose()

    separador = "&" if "?" in TEST_DATABASE_URL else "?"
    url = f"{TEST_DATABASE_URL}{separador}options=-csearch_path%3D{nome_schema}"
    _recarregar_settings(monkeypatch, url)
    yield url

    administrador = create_engine(TEST_DATABASE_URL)
    with administrador.begin() as conexao:
        conexao.execute(text(f'DROP SCHEMA "{nome_schema}" CASCADE'))
    administrador.dispose()


def _recarregar_settings(monkeypatch, url: str) -> None:
    """`aplicar_migracoes` lê a URL de `settings`; aqui ela é apontada ao banco do teste."""
    from app.config import settings

    monkeypatch.setattr(settings, "database_url", url)


def _tabelas(engine) -> set[str]:
    tabelas = set(inspect(engine).get_table_names())
    tabelas.discard("alembic_version")
    return tabelas


def _revisao(engine) -> str | None:
    with engine.connect() as conexao:
        return MigrationContext.configure(conexao).get_current_revision()


def test_banco_vazio_sobe_ate_a_revisao_mais_recente(url_descartavel):
    """Via 3 de `aplicar_migracoes`: instalação nova."""
    engine = create_engine(url_descartavel)
    aplicar_migracoes(engine)

    assert len(_tabelas(engine)) == len(Base.metadata.tables)
    assert _revisao(engine) is not None
    engine.dispose()


def test_banco_de_mesa_legado_e_carimbado_sem_perder_dado(url_descartavel):
    """
    Via 2 — a que existe por causa de quem já tem o RSAC instalado.

    Um banco criado por `create_all`, sem `alembic_version`, precisa ser
    reconhecido como estando na revisão inicial. Sem o carimbo, o `upgrade`
    tentaria criar tabelas existentes e a atualização falharia na cara do
    usuário — que perderia o acesso ao próprio trabalho.
    """
    engine = create_engine(url_descartavel)
    Base.metadata.create_all(engine)

    with engine.begin() as conexao:
        conexao.execute(
            text(
                "INSERT INTO projects (id, title, description, methodology,"
                " created_at, updated_at, is_archived)"
                " VALUES ('legado-1', 'Revisão anterior', '', 'PRISMA-P',"
                " CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, FALSE)"
            )
        )

    assert _revisao(engine) is None, "o cenário exige um banco sem versão"

    aplicar_migracoes(engine)

    assert _revisao(engine) is not None
    with engine.connect() as conexao:
        titulo = conexao.execute(
            text("SELECT title FROM projects WHERE id = 'legado-1'")
        ).scalar_one()
    assert titulo == "Revisão anterior"
    engine.dispose()


def test_aplicar_migracoes_e_idempotente(url_descartavel):
    """Subir duas vezes seguidas não pode falhar — a partida roda a cada reinício."""
    engine = create_engine(url_descartavel)
    aplicar_migracoes(engine)
    revisao_primeira = _revisao(engine)
    aplicar_migracoes(engine)

    assert _revisao(engine) == revisao_primeira
    engine.dispose()


def test_downgrade_ate_a_base_remove_o_esquema(url_descartavel, monkeypatch):
    """
    Toda revisão precisa de `downgrade` que funcione.

    É o que transforma uma migração ruim em contratempo, e não em restauração
    de backup.
    """
    engine = create_engine(url_descartavel)
    aplicar_migracoes(engine)
    assert _tabelas(engine)

    command.downgrade(_alembic_config(), "base")

    assert _tabelas(engine) == set()
    engine.dispose()


def test_cadeia_tem_uma_unica_cabeca():
    """
    Duas cabeças significam ramos de migração divergentes — e `upgrade head`
    passa a ser ambíguo. É o defeito clássico de migração feita em paralelo por
    duas pessoas, e o teste o pega antes do merge.
    """
    cabecas = ScriptDirectory.from_config(_alembic_config()).get_heads()
    assert len(cabecas) == 1, f"cadeia com múltiplas cabeças: {cabecas}"


def test_modelos_e_migracoes_nao_divergem(url_descartavel):
    """
    Depois de `upgrade head`, a autogeração não pode ter nada a fazer.

    É o `alembic check` de §40.2.3 escrito como teste: um PR que altere
    `models.py` sem gerar a revisão correspondente falha aqui, e não em
    produção.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext as MC

    engine = create_engine(url_descartavel)
    aplicar_migracoes(engine)

    with engine.connect() as conexao:
        contexto = MC.configure(
            conexao,
            opts={
                "compare_type": True,
                "target_metadata": Base.metadata,
            },
        )
        diferencas = compare_metadata(contexto, Base.metadata)

    engine.dispose()
    assert diferencas == [], (
        "modelo e migrações divergiram — gere a revisão com "
        f"`alembic revision --autogenerate`. Diferenças: {diferencas}"
    )


def test_url_com_porcentagem_nao_quebra_a_migracao(tmp_path, monkeypatch):
    """
    Regressão: `%` na URL do banco derrubava a partida.

    A primeira versão deste módulo passava a URL por
    `Config.set_main_option("sqlalchemy.url", ...)`. Aquilo grava no
    `configparser`, que lê `%` como sintaxe de interpolação — e uma senha de
    banco contendo `%`, ou qualquer valor percent-encoded na URL, fazia o
    servidor morrer na partida com `ValueError: invalid interpolation syntax`.

    O defeito só aparece com um caractere que ninguém pensa em testar, e o
    sintoma — falha de interpolação de arquivo `.ini` — não sugere em nada a
    causa. Daí o teste.
    """
    diretorio = tmp_path / "pasta%com%porcento"
    diretorio.mkdir()
    url = f"sqlite:///{diretorio / 'migracao.db'}"
    assert "%" in url

    _recarregar_settings(monkeypatch, url)
    engine = create_engine(url)

    aplicar_migracoes(engine)

    assert _revisao(engine) is not None
    engine.dispose()


@pytest.mark.skipif(
    not TEST_DATABASE_URL.startswith("postgresql"),
    reason="a conversão para timestamptz só existe em PostgreSQL",
)
def test_conversao_para_timestamptz_preserva_o_instante(url_descartavel):
    """
    A migração de fuso não pode deslocar as datas já gravadas.

    `ALTER COLUMN ... TYPE timestamptz` sem cláusula explícita interpreta cada
    valor como hora local **do servidor**. Num servidor em `America/Sao_Paulo`,
    as 12:00 UTC que o RSAC gravou virariam 15:00 UTC — três horas somadas a
    todo o banco, sem erro nenhum, e o sintoma apareceria semanas depois como
    sessão expirando cedo e rotina de retenção apagando o que não devia.

    Este teste roda a migração com o servidor deliberadamente fora de UTC e
    exige que o instante saia idêntico ao que entrou.
    """
    engine = create_engine(url_descartavel)
    config = _alembic_config()

    with engine.begin() as conexao:
        command.upgrade(_alembic_config(conexao), "48963bb8d65a")

    with engine.begin() as conexao:
        conexao.execute(
            text(
                "INSERT INTO users (id, username, password_hash, role, is_active,"
                " created_at) VALUES ('tz-1', 'fuso', 'x', 'owner', TRUE,"
                " TIMESTAMP '2026-08-27 12:00:00')"
            )
        )

    with engine.begin() as conexao:
        # O servidor passa a responder em horário de Brasília durante a migração.
        conexao.execute(text("SET LOCAL TimeZone = 'America/Sao_Paulo'"))
        command.upgrade(_alembic_config(conexao), "head")

    with engine.connect() as conexao:
        # `information_schema` cruza todos os schemas do banco. Sem filtrar
        # pelo schema corrente, a consulta também enxerga a tabela `users` que
        # a fixture de sessão cria em `public` — e devolve duas linhas.
        tipo = conexao.execute(
            text(
                "SELECT data_type FROM information_schema.columns"
                " WHERE table_name = 'users' AND column_name = 'created_at'"
                " AND table_schema = current_schema()"
            )
        ).scalar_one()
        instante = conexao.execute(
            text("SELECT created_at FROM users WHERE id = 'tz-1'")
        ).scalar_one()

    engine.dispose()

    assert tipo == "timestamp with time zone"
    assert instante.utcoffset().total_seconds() == 0
    assert instante.replace(tzinfo=None).isoformat() == "2026-08-27T12:00:00", (
        "a migração deslocou o instante — falta o `AT TIME ZONE 'UTC'` "
        f"no postgresql_using (obtido: {instante})"
    )
    assert config  # a configuração de módulo continua utilizável
