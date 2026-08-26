#!/usr/bin/env python

"""
O perímetro do RSAC é fixo: loopback, na máquina de quem instalou.

Este arquivo substitui `test_deployment_profile.py`, que fixava o
comportamento de um `DeploymentProfile` de três valores — desktop, server e
ci. Com a publicação por túnel removida, o perímetro deixou de ser
configuração e virou premissa; o que faz sentido testar não é mais qual perfil
está ativo, e sim que **não existe configuração capaz de abrir o backend para
fora**.
"""

import httpx
import pytest

from app.api.deps import get_db
from app.config import Settings
from app.main import create_app


async def _client(db_session):
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=application)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def test_nao_existe_configuracao_de_exposicao():
    """
    Guarda contra a volta do perfil publicável por cópia e colagem.

    Se algum destes campos reaparecer, é sinal de que o backend voltou a poder
    ser publicado — e aí todo o raciocínio de `app/security/dependencies.py`,
    que troca senha por um arquivo `0600`, deixa de valer sem que nada avise.
    """
    settings = Settings()
    for atributo in (
        "deployment_profile",
        "is_server_profile",
        "cors_origins",
        "trusted_hosts",
        "expose_api_docs",
    ):
        assert not hasattr(settings, atributo), (
            f"`{atributo}` voltou a existir: o backend pode estar publicável de novo"
        )


def test_host_padrao_e_loopback():
    """O padrão não pode ser `0.0.0.0` — nem por descuido de digitação."""
    assert Settings().host == "127.0.0.1"


def test_origens_autorizadas_sao_apenas_locais():
    """
    O regex de CORS é a lista de quem pode falar com a API pelo navegador.

    Nenhum host da internet entra: o que passa é loopback (com porta variável,
    porque o Electron sorteia uma a cada execução) e a origem opaca do
    `file://` do app empacotado.
    """
    import re

    regex = Settings().cors_allow_origin_regex

    for permitida in ("http://localhost:5173", "http://127.0.0.1:8000", "null", "file://"):
        assert re.match(regex, permitida), f"{permitida} deveria ser permitida"

    for negada in (
        "https://evil.example",
        "http://localhost.evil.com",
        "http://127.0.0.1.evil.com",
        "https://revisao.trycloudflare.com",
    ):
        assert not re.match(regex, negada), f"{negada} não deveria ser permitida"


@pytest.mark.anyio
@pytest.mark.parametrize("rota", ["/api/docs", "/api/redoc", "/api/openapi.json"])
async def test_documentacao_fica_aberta(db_session, rota):
    """
    O Swagger era fechado quando o backend podia ser publicado — ali, mapear a
    API inteira era reconhecimento gratuito para quem sondasse o túnel. Sem
    publicação, quem alcança `127.0.0.1` é o dono da máquina, e para ele a
    documentação é ferramenta.
    """
    async with await _client(db_session) as client:
        assert (await client.get(rota)).status_code == 200


@pytest.mark.anyio
async def test_health_responde_sem_credencial(db_session):
    """O Electron usa o health check para saber se o backend subiu."""
    async with await _client(db_session) as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
