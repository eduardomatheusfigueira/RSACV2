#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cobertura de autenticação (doc 28 V-01, doc 29 §29.3.1).

Este é o teste mais importante da suíte, e o motivo é a durabilidade: ele não
verifica que *as rotas de hoje* exigem sessão — ele **enumera** o que a
aplicação expõe e exige sessão de cada uma, com uma lista de exceções escrita à
mão. Uma rota nova que nasça desprotegida derruba o teste sem que ninguém
precise lembrar de cobri-la.

É o par do desenho em `api/v1/router.py`: lá a proteção é ligada no agregador
para que o padrão seja "protegido"; aqui se verifica que o padrão pegou.
"""

import pytest

from app.main import create_app

# A lista **completa** de rotas que respondem sem sessão (§29.3.1).
#
# Acrescentar algo aqui é uma decisão de segurança e deve ser justificada no
# mesmo commit. Hoje são seis caminhos, todos sem dado de negócio:
#   /health          — o lançador precisa saber se o processo subiu
#   /auth/status     — o cliente precisa saber se mostra login ou a aplicação
#   /auth/login      — porta de entrada
#   /auth/local      — troca do token local por sessão, só no perfil desktop
#   /auth/google/*   — as duas pernas do fluxo OAuth (doc 40 §40.4). Precisam
#                      responder sem sessão pela própria natureza: são o que
#                      **cria** a sessão. O que as protege não é autenticação,
#                      e sim o `state` de uso único com PKCE, e o limite da
#                      família `auth` no limitador de taxa.
ROTAS_PUBLICAS = {
    "/api/v1/health",
    "/api/v1/auth/status",
    "/api/v1/auth/login",
    "/api/v1/auth/local",
    "/api/v1/auth/invite/validate",
    "/api/v1/auth/register-with-invite",
    "/api/v1/auth/google/start",
    "/api/v1/auth/google/callback",
}

# Corpos mínimos para as rotas que validam o schema antes de olhar a sessão.
# Sem eles a resposta seria 422 e o teste não provaria nada sobre autenticação.
CORPOS = {
    ("PUT", "/api/v1/ai/settings"): {
        "ai_enabled": True,
        "provider": "gemini",
        "model": "gemini-3.6-flash",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    ("POST", "/api/v1/auth/password"): {
        "current_password": "x" * 12,
        "new_password": "y" * 12,
    },
    ("POST", "/api/v1/auth/users"): {"username": "invasor", "role": "owner"},
    ("POST", "/api/v1/profile/keys/export"): {"export_password": "senha-de-teste-123"},
    ("POST", "/api/v1/profile/keys/import"): {"payload": {}},
    ("POST", "/api/v1/profile/import"): {"schema_version": "x"},
    ("PUT", "/api/v1/settings/sources/Scopus"): {"api_key": "x"},
}


def _placeholder(caminho: str) -> str:
    """Troca os parâmetros de rota por um valor qualquer — o alvo não importa."""
    partes = []
    for parte in caminho.split("/"):
        partes.append("teste" if parte.startswith("{") and parte.endswith("}") else parte)
    return "/".join(partes)


def listar_rotas_http() -> list[tuple[str, str]]:
    """
    Enumera (método, caminho) de tudo que a aplicação publica.

    Usa o esquema OpenAPI porque esta versão do FastAPI inclui os sub-routers
    de forma preguiçosa — `app.routes` não os achata, e percorrer estruturas
    internas deixaria o teste refém de detalhe de implementação.
    """
    app = create_app()
    esquema = app.openapi()

    rotas = []
    for caminho, operacoes in esquema["paths"].items():
        for metodo in operacoes:
            if metodo.lower() in ("get", "post", "put", "patch", "delete"):
                rotas.append((metodo.upper(), caminho))
    return sorted(rotas)


ROTAS_HTTP = listar_rotas_http()


def test_a_enumeracao_encontrou_a_api_inteira():
    """Guarda contra o teste virar vácuo se a enumeração parar de funcionar."""
    assert len(ROTAS_HTTP) > 40, f"só {len(ROTAS_HTTP)} rotas enumeradas — a varredura quebrou"

    caminhos = {c for _, c in ROTAS_HTTP}
    # Âncoras: se estas sumirem, é sinal de que a lista não reflete a API real.
    for esperado in ("/api/v1/projects", "/api/v1/ai/settings", "/api/v1/profile/keys/export"):
        assert esperado in caminhos, f"{esperado} sumiu da enumeração"


@pytest.mark.anyio
@pytest.mark.parametrize("metodo,caminho", ROTAS_HTTP, ids=lambda v: str(v))
async def test_toda_rota_exige_sessao(anon_client, metodo, caminho):
    """
    Sem sessão, tudo responde 401 — exceto a lista explícita de exceções.

    Um 422 aqui também seria falha: significaria que a rota validou o corpo
    antes de olhar a credencial, isto é, que ela processa entrada de anônimo.
    """
    if caminho in ROTAS_PUBLICAS:
        pytest.skip("rota pública declarada")

    url = _placeholder(caminho)
    corpo = CORPOS.get((metodo, caminho))
    resposta = await anon_client.request(metodo, url, json=corpo)

    assert resposta.status_code == 401, (
        f"{metodo} {caminho} respondeu {resposta.status_code} sem autenticação "
        f"(esperado 401). Corpo: {resposta.text[:200]}"
    )


@pytest.mark.anyio
@pytest.mark.parametrize("caminho", sorted(ROTAS_PUBLICAS))
async def test_rotas_publicas_respondem_sem_sessao(anon_client, caminho):
    """A lista de exceções precisa mesmo funcionar sem credencial."""
    if caminho == "/api/v1/auth/login":
        res = await anon_client.post(caminho, json={"username": "x", "password": "y"})
        assert res.status_code in (401, 429)  # responde, e nega a credencial errada
    elif caminho == "/api/v1/auth/local":
        res = await anon_client.post(caminho, json={"token": "x" * 12})
        assert res.status_code in (401, 403, 409)
    elif caminho == "/api/v1/auth/google/start":
        # Sem credencial de aplicativo configurada — o caso da suíte — a rota
        # responde 503. O que importa aqui é que ela **responde**: não pede
        # sessão, porque é ela que cria a sessão.
        res = await anon_client.get(caminho)
        assert res.status_code in (307, 503)
    elif caminho == "/api/v1/auth/google/callback":
        # Sem `state` válido, devolve o navegador à tela de login em vez de um
        # erro de API: quem chega aqui é um navegador voltando do Google.
        res = await anon_client.get(caminho, follow_redirects=False)
        assert res.status_code == 303
        assert "/app/login?erro=" in res.headers["location"]
    elif caminho == "/api/v1/auth/invite/validate":
        res = await anon_client.post(caminho, json={"invite_code": "RSAC-TEST-0000"})
        assert res.status_code in (400, 404)
    elif caminho == "/api/v1/auth/register-with-invite":
        res = await anon_client.post(
            caminho,
            json={
                "invite_code": "RSAC-TEST-0000",
                "username": "teste",
                "password": "SenhaForte123!",
                "full_name": "Teste",
                "email": "teste@email.com",
                "terms_accepted": True,
            },
        )
        assert res.status_code in (400, 404)
    else:
        res = await anon_client.get(caminho)
        assert res.status_code == 200


@pytest.mark.anyio
async def test_status_nao_vaza_nomes_de_conta(anon_client):
    """O status diz *se* há contas, nunca *quais*."""
    res = await anon_client.get("/api/v1/auth/status")
    assert res.status_code == 200

    corpo = res.json()
    assert corpo["has_accounts"] is True
    assert corpo["authenticated"] is False
    assert corpo["user"] is None
    assert "dono_teste" not in res.text
    assert "pesquisador_teste" not in res.text


@pytest.mark.anyio
async def test_sessao_valida_libera_a_api(async_client):
    """O contraponto: com sessão, as mesmas rotas respondem."""
    assert (await async_client.get("/api/v1/projects")).status_code == 200
    assert (await async_client.get("/api/v1/ai/settings")).status_code == 200
    assert (await async_client.get("/api/v1/auth/me")).status_code == 200


@pytest.mark.anyio
async def test_token_invalido_e_recusado(anon_client):
    """Um Bearer inventado não vale mais que nenhum."""
    for token in ("token-inventado", "", "Bearer", "null"):
        res = await anon_client.get(
            "/api/v1/projects", headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 401
