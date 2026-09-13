#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — O aviso ao administrador a cada novo pedido de convite.

Quando alguém pede acesso, o administrador recebe um e-mail com os dados do
pedido e dois botões — aprovar e recusar — que funcionam **sem login**. É o
que permite decidir do celular, na caixa de entrada, sem abrir o painel.

Um link que concede acesso sem pedir senha é uma credencial, e é tratado como
uma:

  * **É assinado.** O link carrega o id do pedido, a ação e o vencimento, com
    um HMAC-SHA256 derivado da chave-mestra do servidor. Trocar qualquer um dos
    três invalida a assinatura; o link de recusar não vira link de aprovar.
  * **Vence.** Trinta dias. Depois disso, o caminho é o painel.
  * **Vale uma vez.** Não por registro de uso, mas pelo estado do pedido: só um
    pedido pendente pode ser decidido, e um pedido decidido não volta a ser
    pendente por clique em link velho.
  * **Não age no GET.** Abrir o link mostra uma página de confirmação; a ação
    só acontece no botão dela, que é um POST. Antivírus corporativo e
    pré-visualização de links *abrem* os endereços de um e-mail para
    inspecioná-los — um GET que aprovasse concederia acesso sem ninguém ter
    clicado em nada.

O link é tão sensível quanto a caixa de entrada que o recebe. Encaminhar o
e-mail de aviso é entregar a decisão a quem o receber.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import quote

from app.config import settings
from app.security.crypto import obter_chave_mestra
from app.services import convite_mensagens, email_service

logger = logging.getLogger(__name__)

Acao = Literal["aprovar", "recusar"]
ACOES: tuple[str, ...] = ("aprovar", "recusar")

VALIDADE_DO_LINK_DIAS = 30

# O Brasil não tem horário de verão desde 2019: um deslocamento fixo diz a hora
# certa sem depender do banco de fusos do sistema operacional.
FUSO_BRASILIA = timezone(timedelta(hours=-3), "BRT")

# Separa esta chave de todas as outras que derivam da mesma chave-mestra. Um
# HMAC feito com a chave-mestra crua poderia, em tese, coincidir com outro uso
# dela; o rótulo garante que uma assinatura de link só vale como link.
_ROTULO_DA_CHAVE = b"revsist:decisao-de-convite-por-email:v1"


class LinkInvalido(Exception):
    """Assinatura errada, formato quebrado ou ação desconhecida."""


class LinkVencido(Exception):
    """Assinatura correta, prazo esgotado."""


@dataclass(frozen=True)
class Decisao:
    pedido_id: str
    acao: str


def _chave() -> bytes:
    return hmac.new(obter_chave_mestra(), _ROTULO_DA_CHAVE, hashlib.sha256).digest()


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def assinar(pedido_id: str, acao: str, *, agora: float | None = None) -> str:
    """Devolve o token do link. `agora` é injetável para testar o vencimento."""
    if acao not in ACOES:
        raise ValueError(f"Ação desconhecida: {acao!r}")
    vence = int((agora if agora is not None else time.time()) + VALIDADE_DO_LINK_DIAS * 86400)
    corpo = f"{pedido_id}|{acao}|{vence}".encode("utf-8")
    assinatura = hmac.new(_chave(), corpo, hashlib.sha256).digest()
    return f"{_b64(corpo)}.{_b64(assinatura)}"


def verificar(token: str, *, agora: float | None = None) -> Decisao:
    """Confere e abre o token. Levanta `LinkInvalido` ou `LinkVencido`."""
    try:
        parte_corpo, parte_assinatura = (token or "").strip().split(".", 1)
        corpo = _de_b64(parte_corpo)
        assinatura = _de_b64(parte_assinatura)
    except Exception as exc:
        raise LinkInvalido("Formato de link irreconhecível.") from exc

    esperada = hmac.new(_chave(), corpo, hashlib.sha256).digest()
    # Comparação em tempo constante: a igualdade comum desiste no primeiro
    # byte diferente, e o tempo de resposta vazaria quantos bytes acertaram.
    if not hmac.compare_digest(esperada, assinatura):
        raise LinkInvalido("Assinatura não confere.")

    try:
        pedido_id, acao, vence = corpo.decode("utf-8").split("|")
        vence_em = int(vence)
    except Exception as exc:
        raise LinkInvalido("Conteúdo do link malformado.") from exc

    if acao not in ACOES:
        raise LinkInvalido("Ação desconhecida.")
    if (agora if agora is not None else time.time()) > vence_em:
        raise LinkVencido("O link venceu.")
    return Decisao(pedido_id=pedido_id, acao=acao)


def link_de_decisao(pedido_id: str, acao: str) -> str:
    base = convite_mensagens._base_publica()
    return f"{base}/convite/decidir?t={quote(assinar(pedido_id, acao))}"


def email_do_admin() -> str:
    return (
        settings.convites_email_admin
        or settings.smtp_reply_to
        or settings.smtp_from_email
        or ""
    ).strip()


def hora_de_brasilia(dt: datetime | None) -> str:
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(FUSO_BRASILIA).strftime("%d/%m/%Y às %H:%M")


# ══════════════════════════════════════════════════════════════════════
# O e-mail
# ══════════════════════════════════════════════════════════════════════

# Paleta da marca, a mesma do e-mail de aprovação.
PAPEL = convite_mensagens.PAPEL
SUPERFICIE = convite_mensagens.SUPERFICIE
TINTA = convite_mensagens.TINTA
TINTA_SUAVE = convite_mensagens.TINTA_SUAVE
ACENTO = convite_mensagens.ACENTO
BORDA = convite_mensagens.BORDA

FONTE = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "'JetBrains Mono',Consolas,monospace"


@dataclass(frozen=True)
class DadosDoPedido:
    """
    Retrato do pedido tirado na hora da requisição.

    O aviso é enviado em tarefa de segundo plano, depois que a resposta já
    saiu — a essa altura a sessão de banco da requisição foi fechada. Levar os
    valores prontos, em vez do objeto do banco, é o que deixa a tarefa
    independente dela.
    """

    id: str
    nome: str
    email: str
    telefone: str
    instituicao: str
    onde_conheceu: str
    recebido_em: datetime


def _linha(rotulo: str, valor_html: str) -> str:
    # Rótulo em cima do valor, e não em coluna ao lado. Duas colunas numa tela
    # de 375px deixam ~150px para um e-mail institucional ou para "Indicação
    # de orientador — Profa. Elena", que quebram em cinco linhas; empilhado,
    # o valor ganha a largura inteira, e isso não precisa de media query —
    # que metade dos clientes de e-mail ignora.
    return f"""
          <tr>
            <td style="padding:12px 0; border-bottom:1px solid {BORDA};">
              <div style="font-size:11px; font-weight:700; letter-spacing:0.07em; text-transform:uppercase; color:{TINTA_SUAVE};">{rotulo}</div>
              <div style="margin-top:4px; font-size:15px; line-height:1.45; color:{TINTA}; word-break:break-word;">{valor_html}</div>
            </td>
          </tr>"""


def montar_email(p: DadosDoPedido) -> tuple[str, str, str]:
    """Devolve (assunto, texto puro, HTML) do aviso ao administrador."""
    aprovar = link_de_decisao(p.id, "aprovar")
    recusar = link_de_decisao(p.id, "recusar")
    painel = f"{convite_mensagens._base_publica()}/app/#/settings"
    quando = hora_de_brasilia(p.recebido_em)
    numero_zap = convite_mensagens.normalizar_telefone(p.telefone)

    assunto = f"Novo pedido de convite — {p.nome}"

    texto = f"""Novo pedido de acesso ao Revsist

Nome:          {p.nome}
E-mail:        {p.email}
Telefone:      {p.telefone}
Instituição:   {p.instituicao or '—'}
Como conheceu: {p.onde_conheceu}
Recebido em:   {quando}

APROVAR — gera o código, envia o e-mail de boas-vindas e oferece o WhatsApp:
{aprovar}

RECUSAR:
{recusar}

Os links abrem uma página de confirmação e só valem enquanto o pedido estiver
pendente, por até {VALIDADE_DO_LINK_DIAS} dias. Responder este e-mail fala direto com {p.nome}.

Painel: {painel}
"""

    e = html.escape
    email_html = f'<a href="mailto:{e(p.email, quote=True)}" style="color:{ACENTO}; text-decoration:none;">{e(p.email)}</a>'
    telefone_html = e(p.telefone)
    if numero_zap:
        telefone_html = (
            f'{e(p.telefone)} &nbsp;<a href="https://wa.me/{numero_zap}" '
            f'style="font-size:12px; color:{ACENTO}; text-decoration:none; font-weight:700;">WhatsApp →</a>'
        )

    corpo = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e(assunto)}</title>
</head>
<body style="margin:0; padding:0; background-color:{PAPEL}; -webkit-text-size-adjust:100%;">

<div style="display:none; max-height:0; overflow:hidden; opacity:0; color:transparent;">
  {e(p.nome)} · {e(p.instituicao or p.email)} · {e(p.onde_conheceu)}
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{PAPEL};">
<tr><td align="center" style="padding:24px 12px 36px 12px;">

  <!--[if mso]><table role="presentation" width="560" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px; margin:0 auto;">
    <tr><td style="height:5px; background-color:{ACENTO}; font-size:0; line-height:0;">&nbsp;</td></tr>
    <tr>
    <td style="background-color:{SUPERFICIE}; padding:28px 24px 28px 24px; font-family:{FONTE};">

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="font-family:{MONO}; font-size:13px; font-weight:700; letter-spacing:0.16em; color:{ACENTO};">REVSIST</td>
          <td align="right" style="font-size:12px; color:{TINTA_SUAVE};">{e(quando)}</td>
        </tr>
      </table>

      <p style="margin:22px 0 0 0; font-size:12px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:{TINTA_SUAVE};">Novo pedido de convite</p>
      <h1 style="margin:6px 0 0 0; font-size:25px; line-height:1.25; font-weight:800; color:{TINTA}; letter-spacing:-0.01em;">{e(p.nome)}</h1>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:20px 0 0 0; border-top:1px solid {BORDA};">
        {_linha("E-mail", email_html)}
        {_linha("Telefone", telefone_html)}
        {_linha("Instituição", e(p.instituicao) if p.instituicao else f'<span style="color:{TINTA_SUAVE};">não informada</span>')}
        {_linha("Como conheceu", e(p.onde_conheceu))}
      </table>

      <!-- Botões lado a lado. Tabela, e não <a> estilizado: no Outlook o
           padding de um link não vira área clicável. -->
      <!-- Empilhados e com a largura inteira: lado a lado, numa tela de celular,
           "Aprovar e enviar convite" quebra em duas linhas e o alvo de toque
           de "Recusar" fica estreito demais para o polegar. -->
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:26px 0 0 0;">
        <tr><td align="center" bgcolor="{ACENTO}" style="border-radius:4px;">
          <a href="{e(aprovar, quote=True)}" target="_blank" style="display:block; padding:16px 12px; font-size:16px; font-weight:700; color:#ffffff; text-decoration:none; font-family:{FONTE};">Aprovar e enviar convite</a>
        </td></tr>
        <tr><td style="height:10px; font-size:0; line-height:0;">&nbsp;</td></tr>
        <tr><td align="center" style="border-radius:4px; border:2px solid {BORDA};">
          <a href="{e(recusar, quote=True)}" target="_blank" style="display:block; padding:13px 12px; font-size:15px; font-weight:700; color:{TINTA_SUAVE}; text-decoration:none; font-family:{FONTE};">Recusar</a>
        </td></tr>
      </table>

      <p style="margin:18px 0 0 0; font-size:13px; line-height:1.6; color:{TINTA_SUAVE};">
        <strong style="color:{TINTA};">Aprovar</strong> gera o código de uso único, envia a
        {e(p.nome.split()[0] if p.nome.split() else 'quem pediu')} o e-mail de boas-vindas e deixa o WhatsApp
        pronto para você mandar. Os dois botões pedem confirmação antes de agir.
      </p>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0 0 0;">
        <tr><td style="height:1px; background-color:{BORDA}; font-size:0; line-height:0;">&nbsp;</td></tr>
      </table>

      <p style="margin:16px 0 0 0; font-size:12px; line-height:1.6; color:{TINTA_SUAVE};">
        Responder este e-mail fala direto com {e(p.nome)}. Os botões valem uma vez, enquanto o
        pedido estiver pendente, por até {VALIDADE_DO_LINK_DIAS} dias — não encaminhe esta mensagem:
        quem a receber poderá decidir por você.
        Se preferir, <a href="{e(painel, quote=True)}" style="color:{ACENTO};">abra o painel</a>.
      </p>

    </td>
    </tr>
  </table>
  <!--[if mso]></td></tr></table><![endif]-->

</td></tr>
</table>
</body>
</html>"""

    return assunto, texto, corpo


def enviar_aviso_ao_admin(p: DadosDoPedido) -> None:
    """
    Tarefa de segundo plano. Nunca levanta.

    Roda depois que a resposta ao formulário público já saiu: a pessoa que
    pediu acesso não espera o servidor de e-mail, e uma falha dele não chega a
    ela como erro no pedido — que já está gravado e continua no painel.
    """
    destino = email_do_admin()
    if not destino:
        logger.info("[Convites] Nenhum e-mail de administrador configurado; aviso não enviado.")
        return
    try:
        assunto, texto, corpo = montar_email(p)
        resultado = email_service.enviar(
            destinatario=destino,
            assunto=assunto,
            texto=texto,
            html=corpo,
            responder_para=p.email,
        )
        if not resultado.enviado:
            logger.warning("[Convites] Aviso ao administrador não enviado: %s", resultado.detalhe)
    except Exception:
        logger.exception("[Convites] Falha ao montar ou enviar o aviso ao administrador.")
