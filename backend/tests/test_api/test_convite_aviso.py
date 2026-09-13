#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — O aviso enviado a quem teve o convite aprovado.

Dois grupos de teste, e a divisão importa:

  * **As mensagens** — o que o link, o WhatsApp e o e-mail dizem. São funções
    puras, testadas sem rede.
  * **A aprovação** — que ela continua valendo quando o envio falha. É a
    propriedade que sustenta o desenho inteiro: aviso é consequência, nunca
    condição.
"""

import re
from email import message_from_bytes

import httpx
import pytest
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    InviteCodeModel,
    InviteRequestModel,
    ProcessingRecordModel,
)
from app.services import convite_mensagens, email_service

PEDIDO = {
    "nome": "Maria Souza",
    "email": "maria@universidade.edu.br",
    "telefone": "(51) 99999-8888",
    "onde_conheceu": "Indicação de orientador",
    "instituicao": "UFRGS",
}


# ══════════════════════════════════════════════════════════════════════
# As mensagens
# ══════════════════════════════════════════════════════════════════════

def test_link_direto_carrega_o_codigo():
    link = convite_mensagens.montar_link_direto("rsac-2368-0a49")
    assert link.endswith("/c/RSAC-2368-0A49")
    assert link.startswith("https://")


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("(51) 99999-8888", "5551999998888"),
        ("51 99999-8888", "5551999998888"),
        ("+55 51 99999 8888", "5551999998888"),
        ("5551999998888", "5551999998888"),
        ("51 3333-4444", "555133334444"),   # fixo, 10 dígitos
        ("+1 415 555 2671", "14155552671"),   # o `+` declara o país
        ("+55 51 99999-8888", "5551999998888"),
        ("0055 51 99999-8888", "5551999998888"),
        ("11 98888-7777", "5511988887777"),   # 11 dígitos sem `+`: Brasil
        ("", ""),
        ("sem número", ""),
    ],
)
def test_telefone_vira_numero_de_whatsapp(entrada, esperado):
    assert convite_mensagens.normalizar_telefone(entrada) == esperado


def test_whatsapp_traz_codigo_e_link_e_e_curto():
    link = convite_mensagens.montar_link_direto("RSAC-2368-0A49")
    texto, _ = convite_mensagens.montar_whatsapp("Maria Souza", "RSAC-2368-0A49", link)

    assert "RSAC-2368-0A49" in texto
    assert link in texto
    assert texto.startswith("Olá, Maria!")
    # Mensagem longa de remetente desconhecido é lida como disparo em massa.
    assert len(texto) < 400


def test_whatsapp_url_fica_vazia_sem_telefone():
    assert convite_mensagens.montar_whatsapp_url("", "Maria", "RSAC-1", "http://x") == ""


def test_saudacao_pula_titulo_academico():
    """`Olá, Prof.` é o cumprimento de um formulário mal preenchido."""
    link = "http://x"
    texto, _ = convite_mensagens.montar_whatsapp("Prof. Dra. Maria Silva", "RSAC-1", link)
    assert texto.startswith("Olá, Maria!")


def test_email_texto_puro_carrega_tudo_que_importa():
    """Quem lê só o texto puro não pode ficar sem o acesso."""
    link = convite_mensagens.montar_link_direto("RSAC-2368-0A49")
    texto = convite_mensagens.montar_email_texto("Maria Souza", "RSAC-2368-0A49", link)

    assert "RSAC-2368-0A49" in texto
    assert link in texto
    assert "<" not in texto  # nenhuma tag vazou para a versão sem HTML


def test_email_html_escapa_o_nome():
    """O nome vem de um formulário público: não pode virar marcação."""
    html = convite_mensagens.montar_email_html(
        '<script>alert(1)</script>', "RSAC-1234-5678", "https://revsist.com/c/RSAC-1234-5678"
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_email_html_referencia_as_tres_pecas():
    html = convite_mensagens.montar_email_html("Maria", "RSAC-1", "https://x/c/RSAC-1")
    for cid in (
        convite_mensagens.CID_PASSOS,
        convite_mensagens.CID_ANIMACAO,
        convite_mensagens.CID_ASSINATURA,
    ):
        assert f"cid:{cid}" in html


def test_as_pecas_do_email_existem_em_disco():
    """
    O render do Remotion precisa ter rodado.

    Sem este teste, uma peça faltando só apareceria na caixa de entrada de
    quem foi aprovado — com um retângulo vazio no lugar da instrução.
    """
    pecas = convite_mensagens.pecas_do_email()
    assert len(pecas) == 3
    for peca in pecas:
        assert peca.caminho.is_file(), f"peça ausente: {peca.caminho}"
        assert peca.caminho.stat().st_size > 1024


def test_email_nao_pesa_demais():
    """
    Teto de peso das imagens embutidas.

    Um GIF renderizado sem cuidado com a paleta passa de 2 MB e transforma o
    aviso num anexo que alguns servidores recusam.
    """
    total = sum(p.caminho.stat().st_size for p in convite_mensagens.pecas_do_email())
    assert total < 700 * 1024, f"peças somam {total // 1024} KB"


# ══════════════════════════════════════════════════════════════════════
# A montagem da mensagem MIME
# ══════════════════════════════════════════════════════════════════════

def test_mensagem_tem_alternativa_em_texto_e_imagens_embutidas(monkeypatch):
    """
    A estrutura MIME é o que decide se a imagem aparece no corpo ou vira anexo
    solto no rodapé: ela precisa estar em `related` com a parte HTML.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "smtp_from_email", "eduardo@exemplo.br")
    monkeypatch.setattr(settings, "smtp_from_name", "Eduardo Matheus Figueira")

    msg = email_service._montar(
        destinatario="maria@universidade.edu.br",
        assunto="Seu acesso ao Revsist foi aprovado",
        texto="versão simples",
        html="<html><body><img src='cid:revsist-passos'></body></html>",
        imagens=convite_mensagens.pecas_do_email(),
    )

    bruto = msg.as_bytes()
    relido = message_from_bytes(bruto)

    tipos = {parte.get_content_type() for parte in relido.walk()}
    assert "text/plain" in tipos
    assert "text/html" in tipos
    assert "image/gif" in tipos
    assert "image/png" in tipos

    embutidas = [
        p for p in relido.walk()
        if p.get("Content-ID") and p.get("Content-Disposition", "").startswith("inline")
    ]
    assert len(embutidas) == 3

    assert "Eduardo Matheus Figueira" in relido["From"]
    assert relido["Auto-Submitted"] == "auto-generated"


@pytest.mark.parametrize(
    "colada,esperada",
    [
        ("fqim gkbe lxvj bzof", "fqimgkbelxvjbzof"),  # como o Google exibe
        ("fqimgkbelxvjbzof", "fqimgkbelxvjbzof"),     # já sem espaços
        ("  fqimgkbelxvjbzof  ", "fqimgkbelxvjbzof"),  # com sobra nas pontas
        ("", ""),
    ],
)
def test_senha_de_app_perde_os_espacos_do_google(colada, esperada):
    """
    A Senha de app copiada da tela do Google precisa funcionar como está.

    O Google a exibe em quatro grupos de quatro, e é assim que ela vai ser
    colada. O SMTP do Gmail recusa a versão espaçada com a mesma mensagem de
    "autenticação falhou" que daria para uma senha errada — o que manda quem
    está configurando procurar o problema no lugar errado.
    """
    from app.config import Settings

    assert Settings(smtp_password=colada).smtp_password == esperada


def test_endereco_e_mascarado_no_log():
    assert email_service._mascarar("maria@universidade.edu.br") == "ma***@universidade.edu.br"


def test_envio_sem_configuracao_nao_levanta(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "smtp_host", "")
    r = email_service.enviar(
        destinatario="x@y.br", assunto="a", texto="b", html="<p>c</p>"
    )
    assert r.enviado is False
    assert "não configurado" in r.detalhe


# ══════════════════════════════════════════════════════════════════════
# A aprovação
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_aprovacao_devolve_link_e_whatsapp(
    anon_client: httpx.AsyncClient, async_client: httpx.AsyncClient, db_session: Session
):
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    pedido_id = db_session.query(InviteRequestModel).one().id

    resp = await async_client.post(
        f"/api/v1/invites/requests/{pedido_id}/approve", json={}
    )
    assert resp.status_code == 200
    corpo = resp.json()
    codigo = corpo["invite"]["code"]

    assert corpo["link_direto"].endswith(f"/c/{codigo}")
    assert corpo["whatsapp_url"].startswith("https://wa.me/5551999998888?text=")
    assert codigo in corpo["whatsapp_url"]


@pytest.mark.anyio
async def test_aprovacao_vale_mesmo_com_email_fora_do_ar(
    anon_client: httpx.AsyncClient,
    async_client: httpx.AsyncClient,
    db_session: Session,
    monkeypatch,
):
    """
    A propriedade central: SMTP quebrado não desfaz a concessão de acesso.

    O estado que este teste existe para impedir é o pior possível — a pessoa
    sem acesso e o administrador convencido de que aprovou.
    """
    def explodir(*_a, **_k):
        raise OSError("servidor de e-mail inalcançável")

    monkeypatch.setattr(email_service.smtplib, "SMTP", explodir)
    from app.config import settings
    monkeypatch.setattr(settings, "smtp_host", "smtp.invalido.local")
    monkeypatch.setattr(settings, "smtp_from_email", "eduardo@exemplo.br")

    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    pedido_id = db_session.query(InviteRequestModel).one().id

    resp = await async_client.post(
        f"/api/v1/invites/requests/{pedido_id}/approve", json={}
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["email_enviado"] is False
    assert corpo["email_detalhe"]

    # O que importa: o acesso existe de verdade.
    assert corpo["request"]["status"] == "aprovado"
    assert db_session.query(InviteCodeModel).filter_by(code=corpo["invite"]["code"]).one()
    validacao = await anon_client.post(
        "/api/v1/auth/invite/validate", json={"invite_code": corpo["invite"]["code"]}
    )
    assert validacao.json()["valid"] is True


@pytest.mark.anyio
async def test_aprovacao_envia_o_email_e_registra_no_ropa(
    anon_client: httpx.AsyncClient,
    async_client: httpx.AsyncClient,
    db_session: Session,
    monkeypatch,
):
    """Caminho feliz, com um SMTP de mentira no lugar do de verdade."""
    enviadas = []

    class SMTPFalso:
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
            enviadas.append(msg)

    from app.config import settings
    monkeypatch.setattr(settings, "smtp_host", "smtp.exemplo.br")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "eduardo@exemplo.br")
    monkeypatch.setattr(settings, "smtp_password", "senha-de-app")
    monkeypatch.setattr(settings, "smtp_from_email", "eduardo@exemplo.br")
    monkeypatch.setattr(email_service.smtplib, "SMTP", SMTPFalso)

    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    pedido_id = db_session.query(InviteRequestModel).one().id

    resp = await async_client.post(
        f"/api/v1/invites/requests/{pedido_id}/approve", json={}
    )
    assert resp.status_code == 200
    assert resp.json()["email_enviado"] is True

    # O pedido também dispara o aviso ao administrador; aqui interessa só o
    # e-mail que vai para quem pediu.
    para_quem_pediu = [m for m in enviadas if m["To"] == "maria@universidade.edu.br"]
    assert len(para_quem_pediu) == 1
    msg = para_quem_pediu[0]
    assert msg["Subject"] == "Seu acesso ao Revsist foi aprovado"

    corpo = msg.as_string()
    codigo = resp.json()["invite"]["code"]
    assert codigo in corpo

    registro = (
        db_session.query(ProcessingRecordModel)
        .filter(ProcessingRecordModel.operation == "invite_approved_notice")
        .one()
    )
    assert registro.legal_basis == "art7_I_consentimento"


# ══════════════════════════════════════════════════════════════════════
# O link curto
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_link_curto_redireciona_para_a_rota_da_spa(anon_client: httpx.AsyncClient):
    resp = await anon_client.get("/c/RSAC-2368-0A49", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/#/convite/RSAC-2368-0A49"


@pytest.mark.anyio
async def test_link_curto_normaliza_caixa(anon_client: httpx.AsyncClient):
    resp = await anon_client.get("/c/rsac-2368-0a49", follow_redirects=False)
    assert resp.headers["location"] == "/app/#/convite/RSAC-2368-0A49"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "hostil",
    [
        "https:%2F%2Fatacante.example",
        "..%2F..%2Fetc",
        "RSAC-1%0D%0ALocation:%20https://atacante.example",
    ],
)
async def test_link_curto_nao_e_redirecionador_aberto(
    anon_client: httpx.AsyncClient, hostil
):
    """
    O código entra no destino do redirecionamento, então precisa ser filtrado.

    Sem o filtro, `revsist.com/c/...` levaria ao site de outra pessoa — com o
    domínio do Revsist na barra até o último instante, que é exatamente a
    isca de um phishing convincente.
    """
    resp = await anon_client.get(f"/c/{hostil}", follow_redirects=False)

    # Duas saídas são aceitáveis, e as duas são seguras: ou o caminho nem casa
    # a rota (o `%2F` vira barra e deixa de ser um segmento só, dando 404), ou
    # casa e o filtro reduz o código ao alfabeto permitido. O que não pode, em
    # nenhuma delas, é sair um `Location` apontando para fora.
    destino = resp.headers.get("location", "")
    if resp.status_code in (301, 302, 303, 307, 308):
        assert destino.startswith("/app")
    assert "atacante" not in destino
    assert not re.search(r"https?:", destino)
