#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Travessia de caminho no catch-all da SPA (doc 28 V-04, doc 29 §29.5.2).

A rota `/{full_path:path}` concatenava ao diretório de build um caminho vindo
do cliente e servia o que encontrasse. Como o servidor ASGI decodifica a
percent-encoding **antes** do roteamento, `/%2e%2e%2f...` chegava como `../`
e qualquer arquivo legível pelo processo saía pela API — inclusive o banco com
as chaves de API.

Os testes montam uma SPA de mentira com um arquivo "secreto" fora dela e
exigem que ele nunca seja servido.
"""

import httpx
import pytest

from app.main import _resolve_within, create_app


@pytest.fixture
def spa_app(tmp_path, monkeypatch):
    """App com uma SPA construída em disco e um segredo no diretório acima."""
    root = tmp_path / "projeto"
    dist = root / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>SPA</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")

    secret = root / "backend" / "segredo.txt"
    secret.parent.mkdir(parents=True)
    secret.write_text("AIzaSyCHAVE_SECRETA_DO_PESQUISADOR", encoding="utf-8")

    # `create_app` deriva o diretório da SPA a partir da localização do módulo,
    # então apontar `__file__` para dentro do tmp_path é o que faz a fábrica
    # montar esta SPA de teste em vez da do repositório.
    import app.main as main_module

    monkeypatch.setattr(main_module, "__file__", str(root / "backend" / "app" / "main.py"))
    return create_app(), secret


@pytest.fixture
async def spa_client(spa_app):
    application, _ = spa_app
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ── Verificação direta do confinamento ────────────────────────────────

@pytest.mark.parametrize(
    "hostile",
    [
        "../../etc/passwd",
        "../backend/segredo.txt",
        "../../../../../../etc/shadow",
        "a/../../../etc/passwd",
        "/etc/passwd",
        "..",
        ".",
        "",
        "../",
        "..%2f..%2fetc%2fpasswd",  # dupla codificação: fica literal, não escapa
    ],
)
def test_resolve_within_recusa_saida_da_raiz(tmp_path, hostile):
    root = (tmp_path / "dist").resolve()
    (root / "assets").mkdir(parents=True)
    resolved = _resolve_within(root, hostile)
    assert resolved is None or root in resolved.parents, (
        f"{hostile!r} escapou da raiz: {resolved}"
    )


def test_resolve_within_aceita_arquivo_legitimo(tmp_path):
    root = (tmp_path / "dist").resolve()
    (root / "assets").mkdir(parents=True)
    alvo = root / "assets" / "app.js"
    alvo.write_text("ok", encoding="utf-8")
    assert _resolve_within(root, "assets/app.js") == alvo


def test_resolve_within_recusa_symlink_para_fora(tmp_path):
    """Link simbólico é o caso que a comparação por prefixo de string perde."""
    root = (tmp_path / "dist").resolve()
    root.mkdir(parents=True)
    fora = tmp_path / "fora.txt"
    fora.write_text("segredo", encoding="utf-8")
    (root / "atalho.txt").symlink_to(fora)

    assert _resolve_within(root, "atalho.txt") is None


# ── Verificação ponta a ponta pela API ────────────────────────────────

# A SPA fica em `<raiz>/frontend/dist`, então são **dois** níveis de `..` até
# a raiz do projeto e o diretório `backend/`. Errar essa profundidade faz o
# teste passar sem exercitar nada: o caminho simplesmente não existiria.
TRAVESSIAS = [
    "/%2e%2e%2f%2e%2e%2fbackend%2fsegredo.txt",
    "/%2e%2e/%2e%2e/backend/segredo.txt",
    "/..%2f..%2fbackend%2fsegredo.txt",
    "/%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
]


@pytest.mark.anyio
@pytest.mark.parametrize("caminho", TRAVESSIAS)
async def test_spa_nunca_serve_arquivo_de_fora(spa_client, spa_app, caminho):
    _, secret = spa_app
    res = await spa_client.get(caminho)

    assert res.status_code == 200
    assert "AIzaSyCHAVE_SECRETA_DO_PESQUISADOR" not in res.text
    assert "root:" not in res.text
    # Travessia cai no index da SPA — devolver 403 confirmaria o alvo.
    assert "SPA" in res.text


@pytest.mark.anyio
async def test_a_travessia_realmente_alcancava_o_segredo(spa_client, spa_app):
    """
    Canário do próprio teste.

    Confirma duas coisas que, se deixarem de valer, tornam os testes acima
    verdes por acidente: (a) o caminho com `..` chega à aplicação **sem**
    normalização — o cliente HTTP não o limpa — e (b) sob a lógica anterior à
    correção, esse caminho resolvia para o arquivo secreto de verdade.
    """
    _, secret = spa_app
    spa_root = secret.parent.parent / "frontend" / "dist"

    caminho_bruto = "../../backend/segredo.txt"
    alvo_pela_logica_antiga = spa_root / caminho_bruto
    assert alvo_pela_logica_antiga.is_file(), "o cenário não aponta para o segredo"
    assert "AIzaSy" in alvo_pela_logica_antiga.read_text(encoding="utf-8")

    # E a requisição correspondente não devolve nada disso.
    res = await spa_client.get("/%2e%2e%2f%2e%2e%2fbackend%2fsegredo.txt")
    assert "AIzaSy" not in res.text


@pytest.mark.anyio
async def test_spa_continua_servindo_o_que_deve(spa_client):
    res = await spa_client.get("/index.html")
    assert res.status_code == 200
    assert "SPA" in res.text

    # Rota do React Router: arquivo não existe, o index responde.
    res_rota = await spa_client.get("/projetos/123/triagem")
    assert res_rota.status_code == 200
    assert "SPA" in res_rota.text


@pytest.mark.anyio
async def test_spa_nao_intercepta_a_api(spa_client):
    res = await spa_client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
