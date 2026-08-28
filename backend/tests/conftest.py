#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Pytest Fixtures Globais."""

import os

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.infrastructure.persistence.models import Base, UserModel
from app.main import create_app
from app.security.passwords import hash_password

# Credenciais das contas de teste. A senha respeita a política mínima (12
# caracteres) porque `hash_password` a valida — o teste usa o caminho real.
SENHA_TESTE = "senha-de-teste-12345"
OWNER_USERNAME = "dono_teste"
RESEARCHER_USERNAME = "pesquisador_teste"

# Identificadores fixos das contas de teste.
#
# Desde a Fase 1 do doc 41 todo projeto tem dono, e `projects.owner_id` é uma
# chave estrangeira que o PostgreSQL faz valer. Fixar os identificadores
# permite que um teste crie o projeto direto no banco — sem passar pela API —
# e ainda assim ele pertença à conta que o cliente autenticado usa.
OWNER_ID_TESTE = "conta-dono-de-teste"
RESEARCHER_ID_TESTE = "conta-pesquisador-de-teste"


@pytest.fixture(autouse=True)
def dns_de_teste(monkeypatch, request):
    """
    Resolve qualquer host de teste para um IP público fictício.

    Os testes usam `httpx.MockTransport` com hosts que não existem
    (`repositorio.br`, `revista.org`). Como o guarda de saída valida o **IP
    resolvido**, e não o nome, sem isto todo teste de rede falharia por DNS —
    e ficaria a impressão errada de que o guarda está barrando o que deveria
    passar.

    A suíte `test_security/test_egress_guard.py` marca-se com `dns_real` e
    fica de fora, porque lá o objetivo é justamente exercitar a resolução de
    verdade.
    """
    if request.node.get_closest_marker("dns_real"):
        return

    import socket

    import app.security.egress as egress

    def _fake_getaddrinfo(host, porta, *args, **kwargs):
        # IP literal resolve para ele mesmo. Sem isto, `http://10.0.0.5` seria
        # "resolvido" para um endereço público e o teste do guarda passaria
        # sem exercitar nada — o fixture mascararia justamente o que verifica.
        import ipaddress

        try:
            ip = ipaddress.ip_address(host)
            familia = socket.AF_INET6 if ip.version == 6 else socket.AF_INET
            return [(familia, socket.SOCK_STREAM, 6, "", (host, porta))]
        except ValueError:
            pass

        if host == "localhost":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", porta))]

        # Nome fictício de teste resolve para um endereço público.
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", porta))]

    monkeypatch.setattr(egress, "_resolver_enderecos", _fake_getaddrinfo)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ── Banco dos testes ──────────────────────────────────────────────────
#
# Por padrão, SQLite em memória: rápido, descartável e sem nada a instalar.
# Definindo `RSAC_TEST_DATABASE_URL`, a **mesma** suíte roda contra
# PostgreSQL — é assim que a CI prova que o código não depende do dialeto
# (doc 41, tarefa 0.10).
#
# Os dois caminhos são deliberadamente diferentes. Em memória, cada teste
# ganha um banco novo, e é o mais simples que funciona. Em PostgreSQL, criar
# e destruir o esquema 400 vezes custaria minutos; então o esquema é criado
# uma vez e cada teste roda dentro de uma transação externa que é revertida
# ao final. `join_transaction_mode="create_savepoint"` é o que faz os
# `db.commit()` do código de produção virarem SAVEPOINT em vez de gravação
# definitiva — sem isso, o teste sujaria o banco do teste seguinte.

TEST_DATABASE_URL = os.environ.get("RSAC_TEST_DATABASE_URL", "").strip()


@pytest.fixture(scope="session")
def _engine_externo():
    """Engine e esquema do banco externo, criados uma vez por execução."""
    if not TEST_DATABASE_URL:
        yield None
        return

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(_engine_externo):
    """Sessão de banco isolada por teste."""
    if _engine_externo is None:
        # SQLite em memória com StaticPool, para manter o esquema entre conexões.
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        _semear_conta_dona(session)
        yield session
        session.close()
        return

    conexao = _engine_externo.connect()
    transacao = conexao.begin()
    Session = sessionmaker(bind=conexao, join_transaction_mode="create_savepoint")
    session = Session()
    _semear_conta_dona(session)
    try:
        yield session
    finally:
        session.close()
        if transacao.is_active:
            transacao.rollback()
        conexao.close()


def _semear_conta_dona(session) -> None:
    """
    Garante a conta dona antes de qualquer teste tocar o banco.

    Sem ela, todo teste que cria um projeto direto no banco falharia na chave
    estrangeira `projects.owner_id` — que o PostgreSQL faz valer e o SQLite,
    sem o PRAGMA, não. Semear aqui mantém os dois bancos com o mesmo
    comportamento, que é o ponto da matriz da CI.
    """
    if session.query(UserModel).filter(UserModel.id == OWNER_ID_TESTE).first():
        return
    session.add(
        UserModel(
            id=OWNER_ID_TESTE,
            username=OWNER_USERNAME,
            password_hash=hash_password(SENHA_TESTE),
            role="owner",
        )
    )
    session.commit()


@pytest.fixture(scope="function")
def contas(db_session):
    """Provisiona uma conta `owner` e uma `researcher` no banco de teste."""
    dono = db_session.query(UserModel).filter(UserModel.id == OWNER_ID_TESTE).first()
    pesquisador = UserModel(
        id=RESEARCHER_ID_TESTE,
        username=RESEARCHER_USERNAME,
        password_hash=hash_password(SENHA_TESTE),
        role="researcher",
    )
    db_session.add(pesquisador)
    db_session.commit()
    db_session.refresh(dono)
    db_session.refresh(pesquisador)
    return {"owner": dono, "researcher": pesquisador}


def _montar_app(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return app


async def _autenticar(client: httpx.AsyncClient, username: str) -> None:
    """Abre sessão pela rota real de login — o teste exercita o caminho real."""
    res = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": SENHA_TESTE}
    )
    assert res.status_code == 200, f"login de teste falhou: {res.status_code} {res.text}"
    # O cookie já fica no jar do cliente; o Bearer cobre, além disso, o caso do
    # cliente hospedado em outra origem, que não recebe cookie SameSite=Strict.
    client.headers["Authorization"] = f"Bearer {res.json()['access_token']}"


@pytest.fixture(scope="function")
async def async_client(db_session, contas):
    """
    Cliente autenticado como `owner` — o padrão dos testes funcionais.

    Desde a Fase 1 do plano de segurança a API inteira exige sessão, então o
    cliente padrão precisa ter uma. Para verificar a própria barreira, use
    `anon_client`.
    """
    transport = httpx.ASGITransport(app=_montar_app(db_session))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _autenticar(client, OWNER_USERNAME)
        yield client


@pytest.fixture(scope="function")
async def researcher_client(db_session, contas):
    """Cliente autenticado como `researcher` — sem acesso às credenciais."""
    transport = httpx.ASGITransport(app=_montar_app(db_session))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _autenticar(client, RESEARCHER_USERNAME)
        yield client


@pytest.fixture(scope="function")
async def anon_client(db_session, contas):
    """Cliente sem sessão. É com ele que se verifica o que a barreira barra."""
    app = _montar_app(db_session)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="function")
def db_session_sem_contas(db_session):
    """
    Sessão de uma instalação **sem nenhuma conta** provisionada.

    `db_session` semeia a conta dona, porque desde a Fase 1 todo projeto
    precisa de dono. Os testes de partida segura exigem o oposto — provar que
    o backend se recusa a subir no perfil `server` quando não há conta —, e
    para eles a semeadura é desfeita.
    """
    db_session.query(UserModel).delete()
    db_session.commit()
    return db_session


@pytest.fixture(scope="function")
async def anon_client_sem_contas(db_session_sem_contas):
    """Cliente sem sessão numa instalação sem nenhuma conta provisionada."""
    app = _montar_app(db_session_sem_contas)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
