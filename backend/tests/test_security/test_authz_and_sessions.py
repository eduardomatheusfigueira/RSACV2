#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Papéis, ciclo de vida da sessão e limite de força bruta
(doc 29 §29.3.3, §29.3.4, §29.7).
"""

import pytest

from tests.conftest import RESEARCHER_USERNAME, SENHA_TESTE

# Rotas que tocam credenciais.
#
# Até a Fase 1 do doc 41 elas eram exclusivas de `owner` (§29.3.4), porque
# havia **uma** configuração de IA no banco inteiro e negá-la ao colaborador
# era a única forma de proteger a chave de quem o convidou. Com contas
# individuais e chave do próprio assinante (doc 40 §40.3.3), a pergunta deixou
# de ser "quem tem papel para ver a chave" e passou a ser "de quem é a chave":
# cada conta gere a sua, e nenhuma alcança a de outra. A garantia ficou mais
# forte, e é o que `test_credencial_de_um_nao_vaza_para_outro` verifica.
ROTAS_DE_SEGREDO = [
    ("GET", "/api/v1/ai/settings", None),
    ("GET", "/api/v1/settings/sources", None),
    ("POST", "/api/v1/profile/keys/export", {"export_password": "senha-de-teste-123"}),
    ("POST", "/api/v1/profile/export", {}),
    ("DELETE", "/api/v1/ai/settings/keys/gemini", None),
]


# ── Separação de papéis ───────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.parametrize("metodo,caminho,corpo", ROTAS_DE_SEGREDO)
async def test_rotas_de_credencial_respondem_pelo_proprio_usuario(
    researcher_client, metodo, caminho, corpo
):
    """
    As rotas de credencial atendem qualquer conta — sempre sobre a dela.

    O que se verifica aqui é que elas **respondem**, e não que negam: negar
    deixou de ser a proteção quando cada assinante passou a ter as próprias
    chaves. A proteção agora é o escopo, provado no teste seguinte.
    """
    res = await researcher_client.request(metodo, caminho, json=corpo)
    assert res.status_code != 403, f"{metodo} {caminho} negou o acesso à própria credencial"
    assert res.status_code < 500, f"{metodo} {caminho} falhou: {res.status_code}"


@pytest.mark.anyio
async def test_credencial_de_um_nao_vaza_para_outro(async_client, researcher_client):
    """
    A chave de API de uma conta é invisível para a outra.

    É o achado O-02 do doc 39: `AISettingsModel` era uma linha única no banco,
    lida em dez pontos como `.first()`. Com dois assinantes e chave própria
    (BYOK), isso significava que o segundo a salvar sobrescrevia a chave do
    primeiro — e que a triagem de um rodava na cota paga do outro.
    """
    salvou = await async_client.put(
        "/api/v1/ai/settings",
        json={"provider": "gemini", "model": "gemini-3.6-flash",
              "api_keys": ["AIzaSyCHAVE-SECRETA-DO-DONO-000"]},
    )
    assert salvou.status_code == 200
    assert salvou.json()["has_api_keys"] is True

    do_pesquisador = await researcher_client.get("/api/v1/ai/settings")
    assert do_pesquisador.status_code == 200
    assert do_pesquisador.json()["has_api_keys"] is False, (
        "a chave do dono apareceu na configuração do colaborador"
    )

    corpo = do_pesquisador.text
    assert "CHAVE-SECRETA-DO-DONO" not in corpo
    assert "AIzaSy" not in corpo


@pytest.mark.anyio
async def test_researcher_opera_a_revisao_normalmente(researcher_client):
    """A restrição é sobre credenciais, não sobre o trabalho de pesquisa."""
    res = await researcher_client.post(
        "/api/v1/projects",
        json={"title": "Revisão do colaborador", "methodology": "PRISMA-ScR"},
    )
    assert res.status_code == 201
    assert (await researcher_client.get("/api/v1/projects")).status_code == 200


@pytest.mark.anyio
async def test_owner_alcanca_as_proprias_credenciais(async_client):
    assert (await async_client.get("/api/v1/ai/settings")).status_code == 200
    assert (await async_client.get("/api/v1/settings/sources")).status_code == 200


@pytest.mark.anyio
async def test_researcher_nao_gerencia_contas(researcher_client):
    assert (await researcher_client.get("/api/v1/auth/users")).status_code == 403
    res = await researcher_client.post(
        "/api/v1/auth/users", json={"username": "novo_usuario", "role": "owner"}
    )
    assert res.status_code == 403


# ── Ciclo de vida da sessão ───────────────────────────────────────────

@pytest.mark.anyio
async def test_logout_revoga_o_token_no_servidor(async_client):
    """
    A sessão tem estado no servidor justamente para isto: depois do logout o
    token não vale mais, mesmo que quem o tenha continue apresentando-o.
    """
    assert (await async_client.get("/api/v1/auth/me")).status_code == 200

    assert (await async_client.post("/api/v1/auth/logout")).status_code == 200

    # O cabeçalho Authorization continua no cliente — e deixou de valer.
    assert (await async_client.get("/api/v1/auth/me")).status_code == 401
    assert (await async_client.get("/api/v1/projects")).status_code == 401


@pytest.mark.anyio
async def test_login_devolve_identidade_e_token(anon_client):
    res = await anon_client.post(
        "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": SENHA_TESTE}
    )
    assert res.status_code == 200

    corpo = res.json()
    assert corpo["user"]["username"] == RESEARCHER_USERNAME
    assert corpo["user"]["role"] == "researcher"
    assert len(corpo["access_token"]) > 30
    # O hash da senha nunca sai pela API.
    assert "password_hash" not in res.text
    assert SENHA_TESTE not in res.text


@pytest.mark.anyio
async def test_cookie_de_sessao_e_httponly(anon_client):
    res = await anon_client.post(
        "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": SENHA_TESTE}
    )
    set_cookie = res.headers.get("set-cookie", "")
    assert "rsac_session=" in set_cookie
    assert "HttpOnly" in set_cookie, "cookie sem HttpOnly fica ao alcance de script na página"
    assert "SameSite=strict" in set_cookie.lower().replace("samesite=strict", "SameSite=strict")


@pytest.mark.anyio
async def test_cookie_sozinho_autentica(anon_client):
    """
    Sem cabeçalho Bearer: só o cookie do jar. É o caso da SPA servida pelo
    próprio backend no modo túnel.
    """
    login = await anon_client.post(
        "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": SENHA_TESTE}
    )
    assert login.status_code == 200
    assert "Authorization" not in anon_client.headers

    assert (await anon_client.get("/api/v1/projects")).status_code == 200


@pytest.mark.anyio
async def test_troca_de_senha_derruba_as_sessoes(async_client):
    """
    Se a troca foi motivada por suspeita de vazamento, manter as sessões
    antigas vivas anularia o gesto.
    """
    res = await async_client.post(
        "/api/v1/auth/password",
        json={"current_password": SENHA_TESTE, "new_password": "nova-senha-forte-9876"},
    )
    assert res.status_code == 200
    assert (await async_client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.anyio
async def test_troca_de_senha_exige_a_senha_atual(async_client):
    res = await async_client.post(
        "/api/v1/auth/password",
        json={"current_password": "chute-errado-123", "new_password": "nova-senha-forte-9876"},
    )
    assert res.status_code == 403
    # A sessão continua válida — a tentativa falha sem efeito colateral.
    assert (await async_client.get("/api/v1/auth/me")).status_code == 200


# ── Força bruta ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_login_bloqueia_apos_cinco_tentativas(anon_client):
    for tentativa in range(5):
        res = await anon_client.post(
            "/api/v1/auth/login",
            json={"username": RESEARCHER_USERNAME, "password": f"errada-{tentativa}"},
        )
        assert res.status_code == 401, f"tentativa {tentativa} deveria falhar com 401"

    bloqueado = await anon_client.post(
        "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": "errada-6"}
    )
    assert bloqueado.status_code == 429

    # E o bloqueio vale mesmo com a senha certa — senão bastaria continuar
    # tentando para encontrar a correta.
    com_senha_certa = await anon_client.post(
        "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": SENHA_TESTE}
    )
    assert com_senha_certa.status_code == 429


@pytest.mark.anyio
async def test_login_bem_sucedido_limpa_o_historico(anon_client):
    """Erro de digitação não deve acumular contra o usuário legítimo."""
    for _ in range(3):
        await anon_client.post(
            "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": "errada"}
        )

    ok = await anon_client.post(
        "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": SENHA_TESTE}
    )
    assert ok.status_code == 200

    # Depois do acerto, o contador recomeça: mais 3 erros não bloqueiam.
    for _ in range(3):
        res = await anon_client.post(
            "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": "errada"}
        )
        assert res.status_code == 401


@pytest.mark.anyio
async def test_mensagem_de_erro_nao_revela_se_a_conta_existe(anon_client):
    """Distinguir 'não existe' de 'senha errada' entregaria a lista de contas."""
    inexistente = await anon_client.post(
        "/api/v1/auth/login", json={"username": "nao_existe_mesmo", "password": "qualquer"}
    )
    existente = await anon_client.post(
        "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": "senha-errada"}
    )

    assert inexistente.status_code == existente.status_code == 401
    assert inexistente.json()["detail"] == existente.json()["detail"]


# ── Gestão de contas ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_owner_cria_conta_com_senha_sorteada(async_client):
    res = await async_client.post(
        "/api/v1/auth/users", json={"username": "colaborador", "role": "researcher"}
    )
    assert res.status_code == 201

    corpo = res.json()
    senha = corpo["generated_password"]
    assert senha and len(senha) >= 12
    assert corpo["user"]["role"] == "researcher"

    # A senha sorteada funciona de verdade.
    login = await async_client.post(
        "/api/v1/auth/login", json={"username": "colaborador", "password": senha}
    )
    assert login.status_code == 200


@pytest.mark.anyio
async def test_nao_e_possivel_ficar_sem_dono(async_client, contas):
    """Desativar o último `owner` deixaria a instalação sem quem a administre."""
    dono_id = contas["owner"].id
    res = await async_client.delete(f"/api/v1/auth/users/{dono_id}")
    assert res.status_code == 400


@pytest.mark.anyio
async def test_usuario_desativado_perde_o_acesso(async_client, anon_client, contas):
    pesquisador_id = contas["researcher"].id
    assert (await async_client.delete(f"/api/v1/auth/users/{pesquisador_id}")).status_code == 200

    res = await anon_client.post(
        "/api/v1/auth/login", json={"username": RESEARCHER_USERNAME, "password": SENHA_TESTE}
    )
    assert res.status_code == 401
