#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Nenhuma resposta da API devolve chave de API em texto claro
(doc 28 V-02, doc 29 §29.4.2 e §29.4.3).

`GET /ai/settings` devolvia as chaves inteiras e `GET /profile/keys/export`
entregava o pacote completo — ambos sem autenticação. O teste central aqui é
o de varredura: configura credenciais reconhecíveis, percorre as rotas de
leitura e falha se qualquer corpo contiver o segredo.
"""

import re

import pytest

# Padrões dos provedores realmente usados pelo Revsist.
PADROES_DE_SEGREDO = [
    re.compile(r"AIzaSy[0-9A-Za-z_\-]{10,}"),   # Google Gemini
    re.compile(r"sk-[0-9A-Za-z]{16,}"),          # OpenAI-compatível / Qwen
]

CHAVES = {
    "gemini": ["AIzaSyCHAVE_DE_TESTE_GEMINI_0001", "AIzaSyCHAVE_DE_TESTE_GEMINI_0002"],
    "qwen": ["sk-QWENCHAVEDETESTE0123456789"],
    "local": ["sk-LOCALCHAVEDETESTE0123456789"],
}
SCOPUS_KEY = "scopus_chave_secreta_de_teste"
SCOPUS_TOKEN = "scopus_token_secreto_de_teste"


def _contem_segredo(texto: str) -> list[str]:
    achados = []
    for padrao in PADROES_DE_SEGREDO:
        achados.extend(padrao.findall(texto))
    for literal in (SCOPUS_KEY, SCOPUS_TOKEN):
        if literal in texto:
            achados.append(literal)
    return achados


async def _configurar_credenciais(client):
    """Grava chaves reconhecíveis pelas rotas normais de escrita."""
    res = await client.put(
        "/api/v1/ai/settings",
        json={
            "ai_enabled": True,
            "provider": "gemini",
            "model": "gemini-3.6-flash",
            "gemini_api_keys": CHAVES["gemini"],
            "qwen_api_keys": CHAVES["qwen"],
            "local_api_keys": CHAVES["local"],
            "temperature": 0.2,
            "max_tokens": 4096,
        },
    )
    assert res.status_code == 200

    res_src = await client.put(
        "/api/v1/settings/sources/Scopus",
        json={"api_key": SCOPUS_KEY, "inst_token": SCOPUS_TOKEN},
    )
    assert res_src.status_code == 200


# ── A varredura ───────────────────────────────────────────────────────

ROTAS_DE_LEITURA = [
    "/api/v1/health",
    "/api/v1/ai/settings",
    "/api/v1/settings/sources",
    "/api/v1/projects",
]


@pytest.mark.anyio
async def test_nenhuma_rota_de_leitura_devolve_chave_em_claro(async_client):
    await _configurar_credenciais(async_client)

    for rota in ROTAS_DE_LEITURA:
        res = await async_client.get(rota)
        assert res.status_code == 200, rota
        vazados = _contem_segredo(res.text)
        assert not vazados, f"{rota} devolveu segredo em claro: {vazados}"


@pytest.mark.anyio
async def test_ai_settings_devolve_mascara_e_nao_chave(async_client):
    await _configurar_credenciais(async_client)

    data = (await async_client.get("/api/v1/ai/settings")).json()

    # O contrato antigo não pode voltar nem como campo extra.
    for campo_proibido in ("api_keys", "gemini_api_keys", "qwen_api_keys", "local_api_keys"):
        assert campo_proibido not in data, f"campo {campo_proibido} devolveu chaves de novo"

    assert data["has_api_keys"] is True
    assert data["gemini_keys_count"] == 2
    assert data["qwen_keys_count"] == 1

    # A máscara identifica a chave sem revelá-la.
    previews = data["gemini_key_previews"]
    assert previews == ["••••••••0001", "••••••••0002"]
    assert data["key_previews"] == previews  # provedor ativo é o gemini


@pytest.mark.anyio
async def test_export_de_chaves_exige_post_e_sai_cifrado(async_client):
    await _configurar_credenciais(async_client)

    # Sem SPA construída o roteador responde 405 (método errado); com a SPA
    # montada, o catch-all intercepta o GET e devolve 404 para caminhos de
    # API. Os dois significam a mesma coisa aqui: a rota que entregava as
    # chaves em claro não existe mais.
    assert (await async_client.get("/api/v1/profile/keys/export")).status_code in (404, 405)

    res = await async_client.post(
        "/api/v1/profile/keys/export", json={"export_password": "senha-de-backup-123"}
    )
    assert res.status_code == 200
    envelope = res.json()

    assert envelope["encrypted"] is True
    assert not _contem_segredo(res.text), "o envelope exportado contém chave em claro"


@pytest.mark.anyio
async def test_export_de_chaves_sem_senha_e_recusado(async_client):
    res = await async_client.post("/api/v1/profile/keys/export", json={})
    assert res.status_code == 422

    res_curta = await async_client.post(
        "/api/v1/profile/keys/export", json={"export_password": "curta"}
    )
    assert res_curta.status_code == 422


@pytest.mark.anyio
async def test_backup_cifrado_volta_pela_importacao(async_client):
    await _configurar_credenciais(async_client)
    senha = "senha-de-backup-123"

    envelope = (
        await async_client.post("/api/v1/profile/keys/export", json={"export_password": senha})
    ).json()

    # Zera e restaura
    assert (await async_client.delete("/api/v1/ai/settings/keys/gemini")).status_code == 200
    assert (await async_client.get("/api/v1/ai/settings")).json()["gemini_keys_count"] == 0

    res_import = await async_client.post(
        "/api/v1/profile/keys/import",
        json={"payload": envelope, "export_password": senha},
    )
    assert res_import.status_code == 200
    assert res_import.json()["gemini_keys_count"] == 2
    assert (await async_client.get("/api/v1/ai/settings")).json()["gemini_keys_count"] == 2


@pytest.mark.anyio
async def test_importacao_com_senha_errada_falha(async_client):
    await _configurar_credenciais(async_client)
    envelope = (
        await async_client.post(
            "/api/v1/profile/keys/export", json={"export_password": "senha-de-backup-123"}
        )
    ).json()

    res = await async_client.post(
        "/api/v1/profile/keys/import",
        json={"payload": envelope, "export_password": "senha-errada-9999"},
    )
    assert res.status_code == 400


@pytest.mark.anyio
async def test_perfil_completo_nao_leva_credencial_por_padrao(async_client):
    await _configurar_credenciais(async_client)

    res = await async_client.post("/api/v1/profile/export", json={})
    assert res.status_code == 200
    vazados = _contem_segredo(res.text)
    assert not vazados, f"a exportação de perfil levou credenciais: {vazados}"

    corpo = res.json()
    assert corpo["ai_settings"]["gemini_keys_count"] == 2
    assert "gemini_api_keys" not in corpo["ai_settings"]


@pytest.mark.anyio
async def test_perfil_completo_com_segredos_sai_cifrado(async_client):
    await _configurar_credenciais(async_client)

    res = await async_client.post(
        "/api/v1/profile/export",
        json={"include_secrets": True, "export_password": "senha-de-backup-123"},
    )
    assert res.status_code == 200
    assert res.json()["secrets"]["encrypted"] is True
    assert not _contem_segredo(res.text)


@pytest.mark.anyio
async def test_put_com_lista_vazia_nao_apaga_chaves(async_client):
    """Formulário salvo sem tocar no campo de chaves não pode destruí-las."""
    await _configurar_credenciais(async_client)

    res = await async_client.put(
        "/api/v1/ai/settings",
        json={
            "ai_enabled": True,
            "provider": "gemini",
            "model": "gemini-3.6-flash",
            "gemini_api_keys": [],
            "temperature": 0.2,
            "max_tokens": 4096,
        },
    )
    assert res.status_code == 200
    assert res.json()["gemini_keys_count"] == 2


@pytest.mark.anyio
async def test_delete_explicito_apaga_chaves(async_client):
    await _configurar_credenciais(async_client)

    res = await async_client.delete("/api/v1/ai/settings/keys/gemini")
    assert res.status_code == 200
    assert res.json()["gemini_keys_count"] == 0
    # Não derruba os outros provedores
    assert res.json()["qwen_keys_count"] == 1

    res_invalido = await async_client.delete("/api/v1/ai/settings/keys/inexistente")
    assert res_invalido.status_code == 400
