#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Partida do aplicativo de mesa (doc 29 §29.3.2, doc 41 Fase 1).

Estes testes existem por causa de uma falha real, relatada por quem instalou a
versão nova: **o programa não abria**. A suíte inteira estava verde, a build
passava e a tela fora conferida no navegador — nada disso tocava o caminho que
quebrou, porque todos os testes rodavam com contas já provisionadas pela
`conftest`.

Eram dois buracos com a mesma raiz — no perfil `desktop` não havia conta à qual
o token local se ligasse:

  * **quem já usava o produto** tinha projetos e nunca rodara `create-user`; a
    migração de titularidade recusava-se a adotar dados sem dono e o backend
    não subia;
  * **quem instalava do zero** subia normalmente e recebia 401 em tudo, caindo
    numa tela de login que pedia um comando de terminal.

A regra que os dois casos revelaram: no desktop, o dono é quem está sentado na
máquina. Não há o que perguntar.
"""

from __future__ import annotations

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.api.deps import get_db
from app.config import DeploymentProfile, settings
from app.infrastructure.persistence.models import UserModel
from app.main import create_app
from app.schema import _alembic_config, aplicar_migracoes
from app.security import local_token as local_token_module
from app.security.provisioning import (
    SENHA_INUTILIZAVEL,
    provisionar_conta_local,
    senha_inutilizavel,
)

# Revisão imediatamente anterior à que introduziu a titularidade.
ANTES_DA_TITULARIDADE = "eb25063c7237"


@pytest.fixture
def banco_de_mesa(tmp_path, monkeypatch):
    """URL de um banco isolado, com `settings` apontando para ele."""
    url = f"sqlite:///{tmp_path / 'mesa.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(local_token_module, "TOKEN_FILENAME", "token_de_teste")
    return url


def _esquema_anterior_com_projeto(url: str) -> None:
    """Instalação de mesa como era antes da Fase 1: projeto, nenhuma conta."""
    engine = create_engine(url)
    with engine.begin() as conexao:
        command.upgrade(_alembic_config(conexao), ANTES_DA_TITULARIDADE)
    with engine.begin() as conexao:
        conexao.execute(
            text(
                "INSERT INTO projects (id, title, description, methodology,"
                " created_at, updated_at, is_archived) VALUES ('p1',"
                " 'Revisão de quem já usava', '', 'PRISMA-ScR',"
                " CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)"
            )
        )
        assert conexao.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 0
    engine.dispose()


def test_migracao_adota_dados_sem_conta_no_desktop(banco_de_mesa, monkeypatch):
    """
    O caso que quebrou: projetos sem dono e nenhuma conta.

    Recusar aqui não protegia ninguém — só impedia a pessoa de abrir o próprio
    programa depois de atualizar. No desktop o dono é quem está na máquina.
    """
    monkeypatch.setattr(settings, "deployment_profile", DeploymentProfile.DESKTOP)
    _esquema_anterior_com_projeto(banco_de_mesa)

    engine = create_engine(banco_de_mesa)
    aplicar_migracoes(engine)

    with engine.connect() as conexao:
        dono = conexao.execute(
            text("SELECT owner_id FROM projects WHERE id = 'p1'")
        ).scalar_one()
        nome, papel, senha = conexao.execute(
            text("SELECT username, role, password_hash FROM users WHERE id = :i"),
            {"i": dono},
        ).one()
    engine.dispose()

    assert dono, "o projeto ficou sem dono"
    assert nome == "local"
    assert papel == "owner"
    assert senha == SENHA_INUTILIZAVEL, "a conta local não pode ter senha utilizável"


def test_migracao_ainda_recusa_adivinhar_no_servidor(banco_de_mesa, monkeypatch):
    """
    No servidor a recusa continua certa.

    Lá não há como saber de quem é o acervo, e chutar entregaria o trabalho de
    uma pessoa a outra. A correção do desktop não pode ter afrouxado isso.
    """
    monkeypatch.setattr(settings, "deployment_profile", DeploymentProfile.SERVER)
    _esquema_anterior_com_projeto(banco_de_mesa)

    engine = create_engine(banco_de_mesa)
    with pytest.raises(Exception, match="nenhuma conta ativa"):
        aplicar_migracoes(engine)
    engine.dispose()


def test_instalacao_nova_de_mesa_abre_e_funciona(banco_de_mesa, monkeypatch, db_session):
    """
    O segundo buraco: banco vazio, nenhuma conta.

    O backend subia e respondia 401 a **tudo**, porque o token local resolve
    para uma conta e não havia nenhuma. O programa abria na tela de login
    pedindo um comando de terminal.
    """
    monkeypatch.setattr(settings, "deployment_profile", DeploymentProfile.DESKTOP)
    db_session.query(UserModel).delete()
    db_session.commit()

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    import app.main as main_module

    monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    with TestClient(app) as cliente:
        cabecalho = {"X-RSAC-Local-Token": local_token_module.read_local_token()}
        listagem = cliente.get("/api/v1/projects", headers=cabecalho)
        criacao = cliente.post(
            "/api/v1/projects",
            headers=cabecalho,
            json={"title": "Primeira revisão", "methodology": "PRISMA-ScR"},
        )
        status = cliente.get("/api/v1/auth/status").json()

    assert listagem.status_code == 200, "o app de mesa não autenticou pelo token local"
    assert criacao.status_code == 201
    assert status["has_accounts"] is True


def test_provisionamento_e_idempotente(db_session):
    """Roda a cada partida: não pode multiplicar contas."""
    db_session.query(UserModel).delete()
    db_session.commit()

    primeiro = provisionar_conta_local(lambda: db_session)
    segundo = provisionar_conta_local(lambda: db_session)

    assert primeiro == 1
    assert segundo == 1
    assert db_session.query(UserModel).count() == 1


def test_provisionamento_respeita_conta_existente(db_session, contas):
    """Com conta provisionada, não inventa outra."""
    antes = db_session.query(UserModel).count()
    provisionar_conta_local(lambda: db_session)
    assert db_session.query(UserModel).count() == antes


@pytest.mark.parametrize(
    "valor,esperado",
    [(None, True), ("", True), ("!", True), (" ! ", True), ("$argon2id$v=19$...", False)],
)
def test_reconhece_senha_inutilizavel(valor, esperado):
    assert senha_inutilizavel(valor) is esperado


@pytest.mark.anyio
async def test_login_por_senha_na_conta_local_explica_o_que_fazer(anon_client, db_session):
    """
    Tentar senha numa conta sem senha precisa dizer o motivo.

    Sem isto a resposta seria "usuário ou senha inválidos", e a pessoa ficaria
    procurando uma senha que nunca existiu.
    """
    db_session.query(UserModel).delete()
    db_session.add(
        UserModel(username="local", password_hash=SENHA_INUTILIZAVEL, role="owner")
    )
    db_session.commit()

    resposta = await anon_client.post(
        "/api/v1/auth/login", json={"username": "local", "password": "qualquer-coisa"}
    )

    assert resposta.status_code == 401
    assert "reset-password" in resposta.json()["detail"]
