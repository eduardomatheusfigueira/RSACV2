#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Entrada com Google (doc 40 §40.4, doc 41 Fase 2).

A suíte gera um par de chaves RSA próprio e finge ser o Google: assim cada uma
das seis validações do `id_token` pode ser derrubada **isoladamente**, que é a
única forma de saber que cada uma está lá. Um teste que só exercitasse o
caminho feliz passaria com qualquer subconjunto delas implementado.

A validação que mais importa é `email_verified`. Sem ela, quem criasse num
Google Workspace uma caixa com o endereço de um assinante existente entraria
como ele e herdaria o acervo — é o achado mais explorado em integrações de
OAuth, e o custo de fechá-lo é uma linha.
"""

from __future__ import annotations

import time

import httpx
import pytest
from joserfc import jwt
from joserfc.jwk import RSAKey

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import UserModel
from app.main import create_app
from app.security import google_oauth, oauth_state
from app.security.passwords import hash_password
from tests.conftest import SENHA_TESTE

CLIENT_ID = "rsac-de-teste.apps.googleusercontent.com"
SUB_GOOGLE = "104729384756102938475"
EMAIL = "pesquisadora@universidade.br"

_CHAVE = RSAKey.generate_key(2048, parameters={"kid": "chave-de-teste"})


@pytest.fixture(autouse=True)
def google_configurado(monkeypatch):
    """Credencial de aplicativo e chave pública sob controle do teste."""
    monkeypatch.setattr(settings, "google_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "google_client_secret", "segredo-de-teste")
    monkeypatch.setattr(settings, "public_base_url", "https://rsac.exemplo.br")
    monkeypatch.setattr(settings, "signup_allowlist", "")

    from joserfc.jwk import KeySet

    async def _jwks_falsa(client=None):
        return KeySet([_CHAVE])

    monkeypatch.setattr(google_oauth, "_obter_jwks", _jwks_falsa)
    google_oauth.limpar_cache_de_jwks()
    yield
    google_oauth.limpar_cache_de_jwks()


def _id_token(**sobrescreve) -> str:
    """Um `id_token` assinado, com as reivindicações que o Google mandaria."""
    agora = int(time.time())
    reivindicacoes = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": SUB_GOOGLE,
        "email": EMAIL,
        "email_verified": True,
        "name": "Maria Pesquisadora",
        "picture": "https://lh3.googleusercontent.com/foto-que-nao-guardamos",
        "iat": agora,
        "exp": agora + 3600,
        "nonce": "nonce-do-fluxo",
    }
    reivindicacoes.update(sobrescreve)
    return jwt.encode({"alg": "RS256", "kid": "chave-de-teste"}, reivindicacoes, _CHAVE)


# ── As seis validações, uma a uma ─────────────────────────────────────


@pytest.mark.anyio
async def test_token_valido_devolve_a_identidade():
    identidade = await google_oauth.validar_id_token(
        _id_token(), nonce_esperado="nonce-do-fluxo"
    )
    assert identidade.sub == SUB_GOOGLE
    assert identidade.email == EMAIL
    assert identidade.nome == "Maria Pesquisadora"


@pytest.mark.anyio
async def test_assinatura_de_outra_chave_e_recusada():
    """Validação 1 — sem ela, qualquer um monta um token."""
    outra = RSAKey.generate_key(2048, parameters={"kid": "chave-de-teste"})
    forjado = jwt.encode(
        {"alg": "RS256", "kid": "chave-de-teste"},
        {
            "iss": "https://accounts.google.com",
            "aud": CLIENT_ID,
            "sub": SUB_GOOGLE,
            "email": EMAIL,
            "email_verified": True,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "nonce": "nonce-do-fluxo",
        },
        outra,
    )
    with pytest.raises(google_oauth.IdentidadeRecusada):
        await google_oauth.validar_id_token(forjado, nonce_esperado="nonce-do-fluxo")


@pytest.mark.anyio
async def test_emissor_inesperado_e_recusado():
    """Validação 2."""
    with pytest.raises(google_oauth.IdentidadeRecusada, match="Emissor"):
        await google_oauth.validar_id_token(
            _id_token(iss="https://accounts.exemplo.com"), nonce_esperado="nonce-do-fluxo"
        )


@pytest.mark.anyio
async def test_token_emitido_para_outro_aplicativo_e_recusado():
    """
    Validação 3 — a que mais se esquece.

    Um `id_token` legítimo, assinado pelo Google, emitido para **outro**
    aplicativo. Quem opera aquele outro aplicativo o possui e poderia
    apresentá-lo aqui. Sem conferir `aud`, ele entra.
    """
    with pytest.raises(google_oauth.IdentidadeRecusada, match="outro aplicativo"):
        await google_oauth.validar_id_token(
            _id_token(aud="outro-app.apps.googleusercontent.com"),
            nonce_esperado="nonce-do-fluxo",
        )


@pytest.mark.anyio
async def test_token_vencido_e_recusado():
    """Validação 4."""
    agora = int(time.time())
    with pytest.raises(google_oauth.IdentidadeRecusada, match="vencido"):
        await google_oauth.validar_id_token(
            _id_token(exp=agora - 3600, iat=agora - 7200),
            nonce_esperado="nonce-do-fluxo",
        )


@pytest.mark.anyio
async def test_nonce_divergente_e_recusado():
    """Validação 5 — fecha a repetição de um token capturado."""
    with pytest.raises(google_oauth.IdentidadeRecusada, match="nonce"):
        await google_oauth.validar_id_token(
            _id_token(), nonce_esperado="outro-nonce-qualquer"
        )


@pytest.mark.anyio
async def test_email_nao_verificado_e_recusado():
    """
    Validação 6 — a trava contra tomada de conta.

    O token é válido em tudo o mais: assinatura certa, emissor certo, público
    certo, no prazo, nonce certo. Só o Google não confirma que o endereço
    pertence a quem está entrando. Isso basta para não entrar.
    """
    with pytest.raises(google_oauth.IdentidadeRecusada, match="não confirma"):
        await google_oauth.validar_id_token(
            _id_token(email_verified=False), nonce_esperado="nonce-do-fluxo"
        )


# ── PKCE e estado ─────────────────────────────────────────────────────


def test_desafio_pkce_e_o_sha256_do_verificador():
    import base64
    import hashlib

    verificador = google_oauth.gerar_verificador()
    esperado = (
        base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest())
        .decode()
        .rstrip("=")
    )
    assert google_oauth.desafio_de(verificador) == esperado
    assert "=" not in google_oauth.desafio_de(verificador)


def test_estado_e_de_uso_unico(db_session):
    """Consumir apaga: um callback repetido não encontra mais o estado."""
    registro = oauth_state.criar(
        db_session, code_verifier="v" * 64, nonce="n", redirect_after="/app"
    )
    primeiro = oauth_state.consumir(db_session, registro.state)
    segundo = oauth_state.consumir(db_session, registro.state)

    assert primeiro is not None
    assert primeiro.nonce == "n"
    assert segundo is None, "o estado foi aceito duas vezes"


def test_estado_vencido_nao_e_aceito(db_session, monkeypatch):
    from datetime import datetime, timedelta, timezone

    registro = oauth_state.criar(db_session, code_verifier="v" * 64, nonce="n")
    registro.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    assert oauth_state.consumir(db_session, registro.state) is None


@pytest.mark.parametrize(
    "candidato",
    ["//evil.com", "https://evil.com", "http://evil.com/x", "/\\evil.com", None, ""],
)
def test_destino_de_retorno_nunca_sai_do_site(candidato):
    """
    Um `redirect_after` externo faria do callback um redirecionador aberto.

    `//evil.com` é o disfarce que passa por quem só confere se a string começa
    com `/`: o navegador o trata como URL de esquema relativo.
    """
    assert oauth_state.destino_seguro(candidato) == "/app"


# ── Fluxo completo pela API ───────────────────────────────────────────


@pytest.fixture
def cliente(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


async def _entrar(cliente, db_session, monkeypatch, **token_kwargs):
    """Percorre start + callback, com a troca de código simulada."""
    inicio = await cliente.get("/api/v1/auth/google/start", follow_redirects=False)
    assert inicio.status_code == 307
    destino = inicio.headers["location"]
    state = destino.split("state=")[1].split("&")[0]

    from app.infrastructure.persistence.models import OAuthStateModel

    registro = (
        db_session.query(OAuthStateModel).filter(OAuthStateModel.state == state).first()
    )

    async def _troca(*, code, code_verifier, redirect_uri, client=None):
        assert code_verifier == registro.code_verifier, "PKCE não foi apresentado"
        return _id_token(nonce=registro.nonce, **token_kwargs)

    monkeypatch.setattr(google_oauth, "trocar_codigo_por_id_token", _troca)
    return await cliente.get(
        f"/api/v1/auth/google/callback?code=codigo-do-google&state={state}",
        follow_redirects=False,
    )


@pytest.mark.anyio
async def test_fluxo_completo_cria_conta_e_abre_sessao(cliente, db_session, monkeypatch):
    resposta = await _entrar(cliente, db_session, monkeypatch)
    await cliente.aclose()

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/app"
    assert "rsac_session" in resposta.headers.get("set-cookie", "")

    criado = db_session.query(UserModel).filter(UserModel.google_sub == SUB_GOOGLE).one()
    assert criado.email == EMAIL
    assert criado.email_verified is True
    assert criado.auth_provider == "google"
    assert criado.password_hash is None
    # A conta nasce **sem** aceite, e isto é a correção de um defeito, não
    # uma regressão: antes, `_resolver_conta` gravava `terms_accepted_at =
    # agora` no instante do cadastro, sem que nada tivesse sido mostrado a
    # ninguém. Registrar aceite que não houve fabrica prova. A trava de
    # `require_aceite` mantém a conta fora da API até a pessoa ler e concordar
    # (ver tests/test_lgpd/test_aceite_do_beta.py).
    assert criado.terms_accepted_at is None
    assert criado.terms_version == ""


@pytest.mark.anyio
async def test_autocadastro_nunca_concede_owner(cliente, db_session, monkeypatch):
    """
    Um serviço aberto em que qualquer um vira administrador não é um serviço.

    `owner` nasce só por `python -m app.cli create-user --role owner`.
    """
    await _entrar(cliente, db_session, monkeypatch)
    await cliente.aclose()

    criado = db_session.query(UserModel).filter(UserModel.google_sub == SUB_GOOGLE).one()
    assert criado.role == "researcher"


@pytest.mark.anyio
async def test_a_foto_do_perfil_nao_e_guardada(cliente, db_session, monkeypatch):
    """
    Dado desnecessário não se trata (art. 6º, III).

    A foto vem junto do escopo `profile`, que se pede pelo nome. Ela para na
    leitura do token e não chega ao banco.
    """
    await _entrar(cliente, db_session, monkeypatch)
    await cliente.aclose()

    criado = db_session.query(UserModel).filter(UserModel.google_sub == SUB_GOOGLE).one()
    colunas = " ".join(
        str(getattr(criado, c.name, "")) for c in UserModel.__table__.columns
    )
    assert "googleusercontent.com/foto" not in colunas


@pytest.mark.anyio
async def test_vinculo_com_conta_existente_por_email_verificado(
    cliente, db_session, monkeypatch
):
    """Quem já tinha conta por senha ganha o Google como segunda via."""
    existente = UserModel(
        username="maria",
        password_hash=hash_password(SENHA_TESTE),
        role="owner",
        email=EMAIL,
    )
    db_session.add(existente)
    db_session.commit()

    resposta = await _entrar(cliente, db_session, monkeypatch)
    await cliente.aclose()

    assert resposta.status_code == 303
    db_session.refresh(existente)
    assert existente.google_sub == SUB_GOOGLE
    assert existente.auth_provider == "both"
    assert existente.role == "owner", "o vínculo não pode rebaixar nem promover"
    assert db_session.query(UserModel).filter(UserModel.email == EMAIL).count() == 1


@pytest.mark.anyio
async def test_email_nao_verificado_nao_entra_pela_api(cliente, db_session, monkeypatch):
    resposta = await _entrar(cliente, db_session, monkeypatch, email_verified=False)
    await cliente.aclose()

    assert resposta.status_code == 303
    assert "erro=recusado" in resposta.headers["location"]
    assert db_session.query(UserModel).filter(UserModel.email == EMAIL).count() == 0


@pytest.mark.anyio
async def test_lista_de_admissao_barra_quem_esta_fora(cliente, db_session, monkeypatch):
    """O modo 'por convite' da v1, sem escrever código de convite."""
    monkeypatch.setattr(settings, "signup_allowlist", "@outrainstituicao.br")

    resposta = await _entrar(cliente, db_session, monkeypatch)
    await cliente.aclose()

    assert "erro=nao_admitido" in resposta.headers["location"]
    assert db_session.query(UserModel).filter(UserModel.email == EMAIL).count() == 0


@pytest.mark.anyio
async def test_callback_com_estado_reutilizado_e_recusado(cliente, db_session, monkeypatch):
    """Repetir o callback não abre uma segunda sessão."""
    inicio = await cliente.get("/api/v1/auth/google/start", follow_redirects=False)
    state = inicio.headers["location"].split("state=")[1].split("&")[0]

    from app.infrastructure.persistence.models import OAuthStateModel

    registro = (
        db_session.query(OAuthStateModel).filter(OAuthStateModel.state == state).first()
    )

    async def _troca(*, code, code_verifier, redirect_uri, client=None):
        return _id_token(nonce=registro.nonce)

    monkeypatch.setattr(google_oauth, "trocar_codigo_por_id_token", _troca)
    url = f"/api/v1/auth/google/callback?code=c&state={state}"
    primeiro = await cliente.get(url, follow_redirects=False)
    segundo = await cliente.get(url, follow_redirects=False)
    await cliente.aclose()

    assert primeiro.status_code == 303 and primeiro.headers["location"] == "/app"
    assert "erro=estado_invalido" in segundo.headers["location"]


# ── Convivência com o que já existe ───────────────────────────────────


@pytest.mark.anyio
async def test_conta_sem_senha_recebe_mensagem_util_no_login(cliente, db_session):
    """
    Quem criou conta pelo Google e tenta a senha precisa saber por quê.

    `verify_password` já devolveria `False` para um hash ausente, mas a
    resposta sairia como "usuário ou senha inválidos" — e a pessoa ficaria
    tentando lembrar de uma senha que nunca existiu.
    """
    db_session.add(
        UserModel(
            username="so_google",
            password_hash=None,
            role="researcher",
            email="so.google@exemplo.br",
            google_sub="outro-sub",
            auth_provider="google",
        )
    )
    db_session.commit()

    resposta = await cliente.post(
        "/api/v1/auth/login", json={"username": "so_google", "password": "qualquer-coisa"}
    )
    await cliente.aclose()

    assert resposta.status_code == 401
    assert "Google" in resposta.json()["detail"]


@pytest.mark.anyio
async def test_status_anuncia_a_via_do_google(cliente):
    resposta = await cliente.get("/api/v1/auth/status")
    await cliente.aclose()
    assert resposta.json()["google_login_enabled"] is True
