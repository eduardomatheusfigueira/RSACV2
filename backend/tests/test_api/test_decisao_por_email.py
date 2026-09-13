#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Aprovar e recusar pedidos de convite pelo próprio e-mail.

Um botão de e-mail que concede acesso sem login é uma credencial. Os testes
se dividem pelas propriedades que fazem dele uma credencial segura:

  * não pode ser forjado nem ter a ação trocada;
  * vence;
  * vale uma vez;
  * abrir não age — só confirmar age.
"""

import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import InviteCodeModel, InviteRequestModel
from app.services import convite_admin, email_service

PEDIDO = {
    "nome": "Maria Souza",
    "email": "maria@universidade.edu.br",
    "telefone": "(51) 99999-8888",
    "onde_conheceu": "Indicação de orientador",
    "instituicao": "UFRGS",
}


class SMTPFalso:
    enviadas: list = []

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def ehlo(self):
        pass

    def starttls(self, **k):
        pass

    def login(self, *a):
        pass

    def send_message(self, msg):
        SMTPFalso.enviadas.append(msg)


@pytest.fixture
def smtp(monkeypatch):
    SMTPFalso.enviadas = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.exemplo.br")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "eduardo@exemplo.br")
    monkeypatch.setattr(settings, "smtp_password", "senha-de-app")
    monkeypatch.setattr(settings, "smtp_from_email", "eduardo@exemplo.br")
    monkeypatch.setattr(settings, "convites_email_admin", "admin@exemplo.br")
    monkeypatch.setattr(email_service.smtplib, "SMTP", SMTPFalso)
    return SMTPFalso


def _token_do_link(link: str) -> str:
    return parse_qs(urlparse(link).query)["t"][0]


async def _criar_pedido(anon_client, db_session) -> InviteRequestModel:
    resp = await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    assert resp.status_code == 201
    return db_session.query(InviteRequestModel).one()


# ══════════════════════════════════════════════════════════════════════
# O token
# ══════════════════════════════════════════════════════════════════════

def test_token_ida_e_volta():
    d = convite_admin.verificar(convite_admin.assinar("pedido-1", "aprovar"))
    assert (d.pedido_id, d.acao) == ("pedido-1", "aprovar")


def test_trocar_a_acao_invalida_o_token():
    """O link de recusar não pode virar link de aprovar."""
    corpo_b64, assinatura = convite_admin.assinar("pedido-1", "recusar").split(".")
    corpo = convite_admin._de_b64(corpo_b64).replace(b"|recusar|", b"|aprovar|")
    forjado = f"{convite_admin._b64(corpo)}.{assinatura}"
    with pytest.raises(convite_admin.LinkInvalido):
        convite_admin.verificar(forjado)


def test_trocar_o_pedido_invalida_o_token():
    corpo_b64, assinatura = convite_admin.assinar("pedido-1", "aprovar").split(".")
    corpo = convite_admin._de_b64(corpo_b64).replace(b"pedido-1", b"pedido-2")
    with pytest.raises(convite_admin.LinkInvalido):
        convite_admin.verificar(f"{convite_admin._b64(corpo)}.{assinatura}")


def test_estender_o_vencimento_invalida_o_token():
    corpo_b64, assinatura = convite_admin.assinar("pedido-1", "aprovar").split(".")
    pedido, acao, _ = convite_admin._de_b64(corpo_b64).decode().split("|")
    corpo = f"{pedido}|{acao}|9999999999".encode()
    with pytest.raises(convite_admin.LinkInvalido):
        convite_admin.verificar(f"{convite_admin._b64(corpo)}.{assinatura}")


@pytest.mark.parametrize("lixo", ["", "abc", "a.b", "....", "x" * 500])
def test_token_malformado_e_invalido(lixo):
    with pytest.raises(convite_admin.LinkInvalido):
        convite_admin.verificar(lixo)


def test_token_vence():
    agora = time.time()
    token = convite_admin.assinar("pedido-1", "aprovar", agora=agora)
    depois = agora + convite_admin.VALIDADE_DO_LINK_DIAS * 86400 + 1
    with pytest.raises(convite_admin.LinkVencido):
        convite_admin.verificar(token, agora=depois)


# ══════════════════════════════════════════════════════════════════════
# O aviso ao administrador
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_novo_pedido_avisa_o_administrador(anon_client, db_session, smtp):
    pedido = await _criar_pedido(anon_client, db_session)

    avisos = [m for m in smtp.enviadas if m["To"] == "admin@exemplo.br"]
    assert len(avisos) == 1
    aviso = avisos[0]
    assert "Maria Souza" in aviso["Subject"]
    # Responder o aviso fala com quem pediu.
    assert aviso["Reply-To"] == "maria@universidade.edu.br"

    corpo = aviso.as_string()
    assert "UFRGS" in corpo and "Indica" in corpo
    assert "/convite/decidir?t=" in corpo

    # Os dois botões carregam tokens válidos para este pedido, cada um com a sua ação.
    html = aviso.get_body(("html",)).get_content()
    links = [
        seg.split('"')[0].replace("&amp;", "&")
        for seg in html.split('href="')[1:]
        if "/convite/decidir" in seg.split('"')[0]
    ]
    acoes = {convite_admin.verificar(_token_do_link(l)).acao for l in links}
    assert acoes == {"aprovar", "recusar"}
    assert all(convite_admin.verificar(_token_do_link(l)).pedido_id == pedido.id for l in links)


@pytest.mark.anyio
async def test_pedido_repetido_nao_gera_segundo_aviso(anon_client, db_session, smtp):
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    assert len([m for m in smtp.enviadas if m["To"] == "admin@exemplo.br"]) == 1


@pytest.mark.anyio
async def test_email_fora_do_ar_nao_afeta_quem_pediu(anon_client, db_session, monkeypatch):
    """Quem pede acesso não pode ver erro por causa do servidor de e-mail."""
    def explodir(*a, **k):
        raise OSError("SMTP inalcançável")

    monkeypatch.setattr(settings, "smtp_host", "smtp.invalido.local")
    monkeypatch.setattr(settings, "smtp_from_email", "eduardo@exemplo.br")
    monkeypatch.setattr(email_service.smtplib, "SMTP", explodir)

    resp = await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    assert resp.status_code == 201
    assert db_session.query(InviteRequestModel).count() == 1


# ══════════════════════════════════════════════════════════════════════
# As páginas
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_abrir_o_link_nao_aprova(anon_client, db_session, smtp):
    """
    Antivírus e pré-visualização abrem os links de um e-mail para inspecioná-los.
    Se o GET agisse, o acesso seria concedido sem ninguém ter clicado.
    """
    pedido = await _criar_pedido(anon_client, db_session)
    token = convite_admin.assinar(pedido.id, "aprovar")

    resp = await anon_client.get(f"/convite/decidir?t={token}")

    assert resp.status_code == 200
    assert "Confirmar aprovação" in resp.text
    assert "Maria Souza" in resp.text
    db_session.refresh(pedido)
    assert pedido.status == "pendente"
    assert db_session.query(InviteCodeModel).count() == 0


@pytest.mark.anyio
async def test_pagina_nao_carrega_script(anon_client, db_session, smtp):
    pedido = await _criar_pedido(anon_client, db_session)
    resp = await anon_client.get(f"/convite/decidir?t={convite_admin.assinar(pedido.id, 'aprovar')}")
    csp = resp.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "script-src" not in csp
    assert "<script" not in resp.text
    assert resp.headers["cache-control"] == "no-store"


@pytest.mark.anyio
async def test_confirmar_aprova_e_avisa_quem_pediu(anon_client, db_session, smtp):
    pedido = await _criar_pedido(anon_client, db_session)
    token = convite_admin.assinar(pedido.id, "aprovar")

    resp = await anon_client.post("/convite/decidir", data={"t": token})

    assert resp.status_code == 200
    db_session.refresh(pedido)
    assert pedido.status == "aprovado"
    codigo = pedido.invite_code_generated
    assert codigo and codigo in resp.text
    assert "https://wa.me/5551999998888" in resp.text

    boas_vindas = [m for m in smtp.enviadas if m["To"] == "maria@universidade.edu.br"]
    assert len(boas_vindas) == 1
    assert codigo in boas_vindas[0].as_string()


@pytest.mark.anyio
async def test_link_vale_uma_vez(anon_client, db_session, smtp):
    pedido = await _criar_pedido(anon_client, db_session)
    token = convite_admin.assinar(pedido.id, "aprovar")

    await anon_client.post("/convite/decidir", data={"t": token})
    segunda = await anon_client.post("/convite/decidir", data={"t": token})

    assert "já foi aprovado" in segunda.text
    assert db_session.query(InviteCodeModel).count() == 1
    assert len([m for m in smtp.enviadas if m["To"] == "maria@universidade.edu.br"]) == 1


@pytest.mark.anyio
async def test_recusar_depois_de_aprovado_nao_desfaz(anon_client, db_session, smtp):
    """Recusar com um código já emitido deixaria um convite válido nas mãos de um 'recusado'."""
    pedido = await _criar_pedido(anon_client, db_session)
    await anon_client.post("/convite/decidir", data={"t": convite_admin.assinar(pedido.id, "aprovar")})

    resp = await anon_client.post("/convite/decidir", data={"t": convite_admin.assinar(pedido.id, "recusar")})

    db_session.refresh(pedido)
    assert pedido.status == "aprovado"
    assert "já foi aprovado" in resp.text


@pytest.mark.anyio
async def test_confirmar_recusa_guarda_o_motivo(anon_client, db_session, smtp):
    pedido = await _criar_pedido(anon_client, db_session)
    enviadas_antes = len(smtp.enviadas)

    resp = await anon_client.post(
        "/convite/decidir",
        data={"t": convite_admin.assinar(pedido.id, "recusar"), "notas": "Fora do escopo."},
    )

    assert resp.status_code == 200
    db_session.refresh(pedido)
    assert pedido.status == "recusado"
    assert pedido.admin_notes == "Fora do escopo."
    assert db_session.query(InviteCodeModel).count() == 0
    # A recusa não avisa quem pediu.
    assert len(smtp.enviadas) == enviadas_antes


@pytest.mark.anyio
async def test_token_forjado_nao_muda_nada(anon_client, db_session, smtp):
    pedido = await _criar_pedido(anon_client, db_session)

    resp = await anon_client.post("/convite/decidir", data={"t": "forjado.invalido"})

    assert resp.status_code == 400
    db_session.refresh(pedido)
    assert pedido.status == "pendente"


@pytest.mark.anyio
async def test_token_vencido_mostra_pagina_propria(anon_client, db_session, smtp, monkeypatch):
    pedido = await _criar_pedido(anon_client, db_session)
    antigo = convite_admin.assinar(pedido.id, "aprovar", agora=time.time() - 40 * 86400)

    resp = await anon_client.get(f"/convite/decidir?t={antigo}")

    assert resp.status_code == 410
    assert "venceu" in resp.text


@pytest.mark.anyio
async def test_pedido_excluido(anon_client, db_session, smtp):
    resp = await anon_client.get(f"/convite/decidir?t={convite_admin.assinar('nao-existe', 'aprovar')}")
    assert resp.status_code == 404
