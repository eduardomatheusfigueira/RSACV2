#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — O aviso ao administrador a cada feedback do beta.

Mesmo destino e mesma aparência do aviso de novo pedido de convite: o dono da
instalação recebe o feedback no e-mail em que já decide os convites, e
responder a mensagem fala direto com quem enviou.

Diferente daquele aviso, este não carrega botão de ação. Um feedback não
concede nada; o que ele pede é leitura, e a triagem da fila acontece no
painel.
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from datetime import datetime

from app.services import convite_admin, convite_mensagens, email_service

logger = logging.getLogger(__name__)

ROTULO_DO_TIPO = {
    "problema": "Problema relatado",
    "sugestao": "Sugestão",
    "elogio": "Elogio",
    "outro": "Feedback",
}

# Cor da faixa do topo por tipo: o dono separa um problema de um elogio antes
# de abrir a mensagem.
COR_DO_TIPO = {
    "problema": "#a83434",
    "sugestao": convite_mensagens.ACENTO,
    "elogio": "#2f7d4f",
    "outro": convite_mensagens.TINTA_SUAVE,
}

PAPEL = convite_mensagens.PAPEL
SUPERFICIE = convite_mensagens.SUPERFICIE
TINTA = convite_mensagens.TINTA
TINTA_SUAVE = convite_mensagens.TINTA_SUAVE
ACENTO = convite_mensagens.ACENTO
BORDA = convite_mensagens.BORDA
FONTE = convite_admin.FONTE
MONO = convite_admin.MONO


@dataclass(frozen=True)
class DadosDoFeedback:
    """
    Retrato do feedback tirado na hora da requisição.

    Pelo mesmo motivo de `convite_admin.DadosDoPedido`: o aviso sai em segundo
    plano, depois que a sessão de banco da requisição já foi fechada.
    """

    id: str
    tipo: str
    mensagem: str
    pagina: str
    navegador: str
    versao: str
    autor_nome: str
    autor_usuario: str
    autor_email: str
    recebido_em: datetime


def montar_email(f: DadosDoFeedback) -> tuple[str, str, str]:
    """Devolve (assunto, texto puro, HTML) do aviso ao administrador."""
    rotulo = ROTULO_DO_TIPO.get(f.tipo, "Feedback")
    cor = COR_DO_TIPO.get(f.tipo, ACENTO)
    quando = convite_admin.hora_de_brasilia(f.recebido_em)
    painel = f"{convite_mensagens._base_publica()}/app/#/settings"
    autor = f.autor_nome or f.autor_usuario or "Usuário sem nome"
    trecho = " ".join(f.mensagem.split())[:70]

    assunto = f"[Beta] {rotulo} — {autor}: {trecho}"

    texto = f"""{rotulo} enviado pelo botão de feedback do Revsist

De:        {autor} (@{f.autor_usuario}){f' <{f.autor_email}>' if f.autor_email else ''}
Recebido:  {quando}
Tela:      {f.pagina or '—'}
Versão:    {f.versao or '—'}
Navegador: {f.navegador or '—'}

{f.mensagem}

Responder este e-mail fala direto com {autor}.
Fila completa no painel: {painel}
"""

    e = html.escape
    contato = e(f"@{f.autor_usuario}")
    if f.autor_email:
        contato = (
            f'<a href="mailto:{e(f.autor_email, quote=True)}" style="color:{ACENTO}; '
            f'text-decoration:none;">{e(f.autor_email)}</a> · {contato}'
        )

    def linha(rotulo_linha: str, valor_html: str) -> str:
        return f"""
          <tr>
            <td style="padding:6px 0; width:92px; vertical-align:top; font-size:11px; font-weight:700; letter-spacing:0.07em; text-transform:uppercase; color:{TINTA_SUAVE};">{rotulo_linha}</td>
            <td style="padding:6px 0; font-size:13px; line-height:1.45; color:{TINTA}; word-break:break-word;">{valor_html}</td>
          </tr>"""

    corpo = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e(assunto)}</title>
</head>
<body style="margin:0; padding:0; background-color:{PAPEL}; -webkit-text-size-adjust:100%;">

<div style="display:none; max-height:0; overflow:hidden; opacity:0; color:transparent;">
  {e(trecho)}
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{PAPEL};">
<tr><td align="center" style="padding:24px 12px 36px 12px;">

  <!--[if mso]><table role="presentation" width="560" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px; margin:0 auto;">
    <tr><td style="height:5px; background-color:{cor}; font-size:0; line-height:0;">&nbsp;</td></tr>
    <tr>
    <td style="background-color:{SUPERFICIE}; padding:28px 24px 28px 24px; font-family:{FONTE};">

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="font-family:{MONO}; font-size:13px; font-weight:700; letter-spacing:0.16em; color:{ACENTO};">REVSIST · BETA</td>
          <td align="right" style="font-size:12px; color:{TINTA_SUAVE};">{e(quando)}</td>
        </tr>
      </table>

      <p style="margin:22px 0 0 0; font-size:12px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:{cor};">{e(rotulo)}</p>
      <h1 style="margin:6px 0 0 0; font-size:23px; line-height:1.25; font-weight:800; color:{TINTA}; letter-spacing:-0.01em;">{e(autor)}</h1>

      <div style="margin:18px 0 0 0; padding:16px 18px; background-color:{PAPEL}; border-left:3px solid {cor}; font-size:15px; line-height:1.6; color:{TINTA}; white-space:pre-wrap; word-break:break-word;">{e(f.mensagem)}</div>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:18px 0 0 0;">
        {linha("Contato", contato)}
        {linha("Tela", f'<span style="font-family:{MONO}; font-size:12px;">{e(f.pagina or "—")}</span>')}
        {linha("Versão", e(f.versao or "—"))}
        {linha("Navegador", f'<span style="font-size:12px; color:{TINTA_SUAVE};">{e(f.navegador or "—")}</span>')}
      </table>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:22px 0 0 0;">
        <tr><td style="height:1px; background-color:{BORDA}; font-size:0; line-height:0;">&nbsp;</td></tr>
      </table>

      <p style="margin:16px 0 0 0; font-size:12px; line-height:1.6; color:{TINTA_SUAVE};">
        Responder este e-mail fala direto com {e(autor)}. A fila de feedback, com as
        situações e as suas anotações, fica no <a href="{e(painel, quote=True)}" style="color:{ACENTO};">painel de administração</a>
        e no Gerenciador de Convites.
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


def enviar_aviso_de_feedback(f: DadosDoFeedback) -> None:
    """
    Tarefa de segundo plano. Nunca levanta.

    Quem enviou o feedback já recebeu a confirmação; uma falha do servidor de
    e-mail não chega a essa pessoa, e o feedback continua gravado na fila.
    """
    destino = convite_admin.email_do_admin()
    if not destino:
        logger.info("[Feedback] Nenhum e-mail de administrador configurado; aviso não enviado.")
        return
    try:
        assunto, texto, corpo = montar_email(f)
        resultado = email_service.enviar(
            destinatario=destino,
            assunto=assunto,
            texto=texto,
            html=corpo,
            responder_para=f.autor_email or None,
        )
        if not resultado.enviado:
            logger.warning("[Feedback] Aviso ao administrador não enviado: %s", resultado.detalhe)
    except Exception:
        logger.exception("[Feedback] Falha ao montar ou enviar o aviso ao administrador.")
