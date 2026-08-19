#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cabeçalhos, limites de recurso e sanitização de erro
(doc 28 V-10, V-11, V-13, V-14; doc 29 §29.6, §29.7, §29.8).
"""

import io

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.deps import get_db
from app.config import Settings
from app.main import create_app
from tests.conftest import OWNER_USERNAME, SENHA_TESTE

# ── Cabeçalhos de segurança (§29.6) ───────────────────────────────────

@pytest.mark.anyio
@pytest.mark.parametrize(
    "cabecalho,valor",
    [
        ("x-content-type-options", "nosniff"),
        ("x-frame-options", "DENY"),
        ("referrer-policy", "no-referrer"),
    ],
)
async def test_cabecalhos_presentes_em_toda_resposta(async_client, cabecalho, valor):
    for rota in ("/api/v1/health", "/api/v1/projects", "/api/v1/auth/me"):
        resposta = await async_client.get(rota)
        assert resposta.headers.get(cabecalho) == valor, f"{rota} sem {cabecalho}"


@pytest.mark.anyio
async def test_cabecalhos_presentes_ate_em_resposta_de_erro(anon_client):
    """Resposta 401 também precisa deles — é resposta como qualquer outra."""
    resposta = await anon_client.get("/api/v1/projects")
    assert resposta.status_code == 401
    assert resposta.headers.get("x-content-type-options") == "nosniff"


@pytest.mark.anyio
async def test_api_declara_csp_restritiva(async_client):
    """
    `GET /.../pdf` serve arquivo `inline` na mesma origem. Sem `nosniff` e sem
    CSP, um arquivo interpretado como HTML executaria script no contexto do app.
    """
    resposta = await async_client.get("/api/v1/health")
    csp = resposta.headers.get("content-security-policy", "")
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert resposta.headers.get("cache-control") == "no-store"


# ── Limite de taxa (§29.7) ────────────────────────────────────────────

@pytest.mark.anyio
async def test_excesso_de_requisicoes_recebe_429(async_client):
    """
    O limite de rotas de IA é o que importa: cada chamada consome cota paga
    pelo pesquisador.
    """
    # `GET /ai/settings` cai na família "ai" do limitador e não depende de
    # chave configurada — o que se está medindo é o limite, não o provedor.
    respostas = []
    for _ in range(25):
        respostas.append(await async_client.get("/api/v1/ai/settings"))

    codigos = [r.status_code for r in respostas]
    assert 429 in codigos, f"nenhuma requisição foi limitada: {set(codigos)}"

    limitada = next(r for r in respostas if r.status_code == 429)
    assert limitada.headers.get("retry-after")
    assert "Muitas requisições" in limitada.json()["detail"]


@pytest.mark.anyio
async def test_health_nao_e_limitado(async_client):
    """O lançador consulta o health em laço enquanto o backend sobe."""
    for _ in range(40):
        assert (await async_client.get("/api/v1/health")).status_code == 200


@pytest.mark.anyio
async def test_uso_normal_nao_e_limitado(async_client):
    """Limite apertado demais viraria bloqueio do trabalho legítimo."""
    for _ in range(30):
        assert (await async_client.get("/api/v1/projects")).status_code == 200


# ── Upload (§29.7) ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_upload_acima_do_limite_recebe_413(async_client, monkeypatch):
    """
    O `await file.read()` anterior carregava o arquivo inteiro na RAM antes de
    qualquer validação — um POST de alguns GB derrubava o processo.
    """
    import app.services.pdf_service as pdf_service_module

    monkeypatch.setattr(
        pdf_service_module, "settings", Settings(max_upload_mb=1)
    )

    projeto = (
        await async_client.post(
            "/api/v1/projects", json={"title": "Projeto de upload", "methodology": "PRISMA-ScR"}
        )
    ).json()
    paper = (
        await async_client.post(
            f"/api/v1/projects/{projeto['id']}/papers",
            json={"title": "Estudo com anexo grande", "decision": "Pendente"},
        )
    ).json()

    grande = b"%PDF-1.7" + b"A" * (2 * 1024 * 1024)
    resposta = await async_client.post(
        f"/api/v1/projects/{projeto['id']}/papers/{paper['id']}/extraction/pdf/upload",
        files={"file": ("grande.pdf", io.BytesIO(grande), "application/pdf")},
    )

    assert resposta.status_code == 413
    assert "limite" in resposta.json()["detail"].lower()


@pytest.mark.anyio
async def test_upload_que_nao_e_pdf_e_recusado(async_client):
    projeto = (
        await async_client.post(
            "/api/v1/projects", json={"title": "Projeto tipo", "methodology": "PRISMA-ScR"}
        )
    ).json()
    paper = (
        await async_client.post(
            f"/api/v1/projects/{projeto['id']}/papers",
            json={"title": "Estudo com anexo inválido", "decision": "Pendente"},
        )
    ).json()

    resposta = await async_client.post(
        f"/api/v1/projects/{projeto['id']}/papers/{paper['id']}/extraction/pdf/upload",
        files={"file": ("falso.pdf", io.BytesIO(b"<html>nao sou pdf</html>"), "application/pdf")},
    )
    assert resposta.status_code == 400
    assert "PDF" in resposta.json()["detail"]


@pytest.mark.anyio
async def test_upload_legitimo_continua_funcionando(async_client):
    projeto = (
        await async_client.post(
            "/api/v1/projects", json={"title": "Projeto ok", "methodology": "PRISMA-ScR"}
        )
    ).json()
    paper = (
        await async_client.post(
            f"/api/v1/projects/{projeto['id']}/papers",
            json={"title": "Estudo com anexo válido", "decision": "Pendente"},
        )
    ).json()

    conteudo = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
    resposta = await async_client.post(
        f"/api/v1/projects/{projeto['id']}/papers/{paper['id']}/extraction/pdf/upload",
        files={"file": ("artigo.pdf", io.BytesIO(conteudo), "application/pdf")},
    )
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "uploaded"


# ── Sanitização de erro (§29.8) ───────────────────────────────────────

VAZAMENTOS = ("Traceback", "sqlalchemy", "/home/", "site-packages", "File \"")


@pytest.mark.anyio
async def test_erro_interno_nao_vaza_detalhe(async_client, monkeypatch):
    """
    `detail=str(e)` propagava caminho absoluto, host de provedor e fragmento
    de SQL. O que sai agora é mensagem estável mais um identificador.
    """
    from app.services.dedup_service import DeduplicationService

    def _explode(*args, **kwargs):
        raise RuntimeError(
            "falha em /home/pesquisador/app/sqlalchemy/engine.py: conexão recusada"
        )

    monkeypatch.setattr(DeduplicationService, "run_project_deduplication", _explode)

    projeto = (
        await async_client.post(
            "/api/v1/projects", json={"title": "Projeto erro", "methodology": "PRISMA-ScR"}
        )
    ).json()
    resposta = await async_client.post(f"/api/v1/projects/{projeto['id']}/deduplicate")

    assert resposta.status_code == 500
    corpo = resposta.text
    for vazamento in VAZAMENTOS:
        assert vazamento not in corpo, f"resposta de erro contém {vazamento!r}"
    assert "Referência:" in resposta.json()["detail"]


@pytest.mark.anyio
async def test_erro_de_arquivo_nao_vaza_caminho(async_client):
    """A mensagem original de `FileNotFoundError` carrega o caminho no disco."""
    projeto = (
        await async_client.post(
            "/api/v1/projects", json={"title": "Projeto pdf", "methodology": "PRISMA-ScR"}
        )
    ).json()
    paper = (
        await async_client.post(
            f"/api/v1/projects/{projeto['id']}/papers",
            json={"title": "Estudo sem pdf", "decision": "Pendente"},
        )
    ).json()

    resposta = await async_client.get(
        f"/api/v1/projects/{projeto['id']}/papers/{paper['id']}/extraction/pdf/text"
    )
    assert resposta.status_code == 404
    for vazamento in VAZAMENTOS:
        assert vazamento not in resposta.text


# ── Origin no WebSocket (§29.3.6) ─────────────────────────────────────

CANAIS = [
    "/api/v1/projects/projeto-teste/harvest/ws",
    "/api/v1/projects/projeto-teste/screening/ai/ws",
]


@pytest.fixture
def ws_client(db_session, contas):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c


def _token(client) -> str:
    res = client.post(
        "/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": SENHA_TESTE}
    )
    return res.json()["access_token"]


@pytest.mark.parametrize("canal", CANAIS)
def test_websocket_de_origem_hostil_e_recusado(ws_client, canal):
    """
    O caso que a sessão sozinha não resolve: a política de mesma origem não
    vale para WebSocket, então o cookie do pesquisador abriria o canal para
    qualquer página aberta no navegador dele.
    """
    token = _token(ws_client)
    with pytest.raises(WebSocketDisconnect) as exc:
        with ws_client.websocket_connect(
            f"{canal}?token={token}", headers={"Origin": "https://evil.example"}
        ) as ws:
            ws.receive_text()
    assert exc.value.code == 1008


def test_websocket_de_origem_local_e_aceito(ws_client):
    token = _token(ws_client)
    with ws_client.websocket_connect(
        f"{CANAIS[0]}?token={token}", headers={"Origin": "http://localhost:5173"}
    ) as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_websocket_sem_origem_e_aceito(ws_client):
    """Cliente que não é navegador não manda `Origin` — e o vetor é do navegador."""
    token = _token(ws_client)
    with ws_client.websocket_connect(f"{CANAIS[0]}?token={token}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_origem_hostil_e_recusada_antes_da_sessao(ws_client):
    """A ordem importa: `Origin` primeiro, para não vazar validade de token."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with ws_client.websocket_connect(
            f"{CANAIS[0]}?token=token-invalido", headers={"Origin": "https://evil.example"}
        ) as ws:
            ws.receive_text()
    assert exc.value.code == 1008


# ── Endpoint de IA passa pelo guarda de saída ─────────────────────────

@pytest.mark.anyio
@pytest.mark.parametrize(
    "endpoint",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/v1",
        "file:///etc/passwd",
        "http://192.168.0.1:8080/v1",
    ],
)
async def test_endpoint_de_ia_interno_e_recusado(async_client, endpoint):
    """
    O `endpoint` vira `base_url` do cliente, e o servidor passa a fazer POST
    **com a chave de API no cabeçalho** para esse host: exfiltração de
    credencial e SSRF na mesma requisição.
    """
    resposta = await async_client.put(
        "/api/v1/ai/settings",
        json={
            "ai_enabled": True,
            "provider": "qwen",
            "model": "qwen3.8-max",
            "endpoint": endpoint,
            "temperature": 0.2,
            "max_tokens": 4096,
        },
    )
    assert resposta.status_code == 400
    assert "não é um destino válido" in resposta.json()["detail"]


@pytest.mark.anyio
async def test_endpoint_de_ia_legitimo_e_aceito(async_client):
    resposta = await async_client.put(
        "/api/v1/ai/settings",
        json={
            "ai_enabled": True,
            "provider": "qwen",
            "model": "qwen3.8-max",
            "endpoint": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "temperature": 0.2,
            "max_tokens": 4096,
        },
    )
    assert resposta.status_code == 200


@pytest.mark.anyio
async def test_llm_local_continua_configuravel(async_client):
    """A correção não pode inviabilizar o Ollama, que é uso legítimo."""
    resposta = await async_client.put(
        "/api/v1/ai/settings",
        json={
            "ai_enabled": True,
            "provider": "local",
            "model": "Llama-3.2-3B",
            "endpoint": "http://localhost:11434/v1",
            "temperature": 0.2,
            "max_tokens": 4096,
        },
    )
    assert resposta.status_code == 200
