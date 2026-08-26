#!/usr/bin/env python

"""RSAC V2 — Pytest Fixtures Globais."""

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import Base
from app.main import create_app
from app.security.dependencies import LOCAL_TOKEN_HEADER
from app.security.local_token import ensure_local_token


@pytest.fixture(autouse=True)
def pasta_de_dados_isolada(tmp_path, monkeypatch):
    """
    Aponta a pasta de dados para um diretório temporário.

    Vale para toda a suíte, e não só para os testes de segurança: é o que
    impede um teste de criar `runtime_token` ou `master.key` na instalação real
    de quem está rodando `pytest` — e, pior, de passar por acidente porque
    encontrou o token de verdade da máquina.
    """
    monkeypatch.setattr(settings, "data_dir_override", tmp_path / "dados")
    yield


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


@pytest.fixture(scope="function")
def db_session():
    """Cria um banco SQLite in-memory com StaticPool para manter schema entre conexões."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def token_local() -> str:
    """
    Token desta instalação de teste, criado na pasta temporária.

    Devolve o conteúdo real do arquivo, gerado pela mesma função que o backend
    usa na partida — o teste exercita o caminho de verdade, e não uma string
    combinada entre o teste e o código.
    """
    token = ensure_local_token()
    assert token, "o token local deveria ter sido criado na pasta de teste"
    return token


def _montar_app(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return app


@pytest.fixture(scope="function")
async def async_client(db_session, token_local):
    """
    Cliente autenticado — o padrão dos testes funcionais.

    A API inteira exige o token local, então o cliente padrão precisa
    apresentá-lo. Para verificar a própria barreira, use `anon_client`.

    Era um cliente com sessão aberta por login; virou um cabeçalho, porque foi
    isso que a autenticação virou.
    """
    transport = httpx.ASGITransport(app=_montar_app(db_session))
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={LOCAL_TOKEN_HEADER: token_local},
    ) as client:
        yield client


@pytest.fixture(scope="function")
async def anon_client(db_session, token_local):
    """
    Cliente sem credencial. É com ele que se verifica o que a barreira barra.

    Depende de `token_local` de propósito: a instalação **tem** um token
    válido, e este cliente simplesmente não o apresenta. Sem essa dependência,
    o teste passaria mesmo que a barreira estivesse aberta, porque não haveria
    token nenhum contra o qual comparar.
    """
    transport = httpx.ASGITransport(app=_montar_app(db_session))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
