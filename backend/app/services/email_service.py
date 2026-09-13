#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Envio de e-mail por SMTP.

Uma regra governa este módulo: **o e-mail é aviso, não é a operação**. Quem
aprova um convite está concedendo acesso; o e-mail apenas conta isso à pessoa.
Se o servidor de e-mail estiver fora, com credencial vencida ou simplesmente
não configurado, a concessão continua válida e o administrador continua com o
código na mão para enviar como quiser.

É por isso que nada aqui levanta exceção para quem chama: `enviar` devolve um
`ResultadoDeEnvio` que diz o que aconteceu, e a rota de aprovação trata esse
resultado como informação a exibir, nunca como motivo para desfazer a
aprovação. O erro oposto — deixar uma falha de SMTP abortar a transação —
produziria o pior estado possível: a pessoa sem acesso e o administrador
convencido de que aprovou.
"""

from __future__ import annotations

import logging
import mimetypes
import smtplib
import ssl
from dataclasses import dataclass
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Optional, Sequence

from app.config import settings

logger = logging.getLogger(__name__)

# Tempo máximo de conversa com o servidor de SMTP. O envio acontece dentro do
# ciclo da requisição de aprovação, e sem teto um servidor que aceita a conexão
# mas não responde deixaria o administrador olhando para um botão girando.
TIMEOUT_SMTP = 20.0


@dataclass(frozen=True)
class ImagemEmbutida:
    """
    Imagem que viaja dentro da mensagem, referenciada por `cid:`.

    Embutida, e não linkada: Outlook, Thunderbird e boa parte dos clientes
    corporativos bloqueiam imagem remota por padrão, e o leitor veria o
    esqueleto do e-mail com três retângulos vazios justamente onde estão as
    instruções. O custo é o peso do anexo — que é a razão de o GIF ser
    renderizado em paleta chapada.
    """

    cid: str
    caminho: Path
    """Nome que aparece se o cliente listar os anexos."""
    nome: str = ""


@dataclass(frozen=True)
class ResultadoDeEnvio:
    enviado: bool
    detalhe: str
    destinatario: str = ""


def email_configurado() -> bool:
    """Há SMTP configurado o bastante para tentar um envio?"""
    return bool(settings.smtp_host and settings.smtp_from_email)


def _remetente() -> str:
    nome = (settings.smtp_from_name or "").strip()
    endereco = settings.smtp_from_email.strip()
    if not nome:
        return endereco
    usuario, _, dominio = endereco.partition("@")
    return str(Address(nome, usuario, dominio))


def _montar(
    *,
    destinatario: str,
    assunto: str,
    texto: str,
    html: str,
    imagens: Sequence[ImagemEmbutida] = (),
    responder_para: Optional[str] = None,
) -> EmailMessage:
    """
    Monta a mensagem em `multipart/related` com alternativa em texto puro.

    A versão em texto não é cortesia: um e-mail que só existe em HTML é sinal
    clássico de disparo automatizado e pesa contra na filtragem de spam — além
    de ser o que resta para quem lê por leitor de tela ou cliente de terminal.
    Ela carrega a mesma informação, inclusive o código e o link.
    """
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = _remetente()
    msg["To"] = destinatario
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=settings.smtp_from_email.split("@")[-1] or None)
    # `responder_para` vence o padrão: no aviso de novo pedido, apertar
    # "responder" precisa falar com quem pediu, e não com o próprio remetente.
    if responder_para:
        msg["Reply-To"] = responder_para
    elif settings.smtp_reply_to:
        msg["Reply-To"] = settings.smtp_reply_to

    # `Auto-Submitted` avisa a outros servidores que isto é disparo automático
    # e não deve gerar resposta automática de volta — é o que evita o par de
    # robôs trocando "estou ausente" para sempre.
    msg["Auto-Submitted"] = "auto-generated"

    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")

    if imagens:
        # As imagens precisam ficar em `related` com a *parte HTML*, e não com
        # a mensagem inteira: penduradas na raiz, `cid:` não resolve em vários
        # clientes e elas aparecem como anexos soltos no rodapé.
        parte_html = msg.get_payload()[-1]
        for img in imagens:
            if not img.caminho.is_file():
                logger.warning("[E-mail] Imagem ausente, seguindo sem ela: %s", img.caminho)
                continue
            tipo, _ = mimetypes.guess_type(img.caminho.name)
            principal, _, secundario = (tipo or "application/octet-stream").partition("/")
            parte_html.add_related(
                img.caminho.read_bytes(),
                maintype=principal,
                subtype=secundario,
                cid=f"<{img.cid}>",
                filename=img.nome or img.caminho.name,
                disposition="inline",
            )

    return msg


def enviar(
    *,
    destinatario: str,
    assunto: str,
    texto: str,
    html: str,
    imagens: Sequence[ImagemEmbutida] = (),
    responder_para: Optional[str] = None,
) -> ResultadoDeEnvio:
    """
    Entrega a mensagem. Nunca levanta — devolve o que aconteceu.
    """
    if not email_configurado():
        return ResultadoDeEnvio(
            enviado=False,
            detalhe=(
                "Envio de e-mail não configurado no servidor "
                "(defina RSAC_SMTP_HOST e RSAC_SMTP_FROM_EMAIL)."
            ),
            destinatario=destinatario,
        )

    try:
        msg = _montar(
            destinatario=destinatario,
            assunto=assunto,
            texto=texto,
            html=html,
            imagens=imagens,
            responder_para=responder_para,
        )
    except Exception as err:  # pragma: no cover — falha de montagem é defeito
        logger.exception("[E-mail] Falha ao montar a mensagem.")
        return ResultadoDeEnvio(False, f"Falha ao montar a mensagem: {err}", destinatario)

    contexto = ssl.create_default_context()

    try:
        if settings.smtp_port == 465:
            servidor = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port,
                timeout=TIMEOUT_SMTP, context=contexto,
            )
        else:
            servidor = smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=TIMEOUT_SMTP
            )

        with servidor:
            servidor.ehlo()
            if settings.smtp_port != 465 and settings.smtp_use_tls:
                servidor.starttls(context=contexto)
                servidor.ehlo()
            if settings.smtp_user:
                servidor.login(settings.smtp_user, settings.smtp_password)
            servidor.send_message(msg)

    except smtplib.SMTPAuthenticationError:
        # O tropeço mais provável de todos, e o mais fácil de diagnosticar
        # errado: o Gmail recusa a senha da conta e aceita apenas uma Senha de
        # app. Quem lê "autenticação falhou" tende a redigitar a mesma senha.
        logger.error("[E-mail] Autenticação recusada pelo servidor SMTP.")
        return ResultadoDeEnvio(
            False,
            "O servidor de e-mail recusou as credenciais. No Gmail é preciso "
            "usar uma Senha de app, não a senha da conta.",
            destinatario,
        )
    except (smtplib.SMTPException, OSError, ssl.SSLError) as err:
        logger.error("[E-mail] Falha no envio para %s: %s", _mascarar(destinatario), err)
        return ResultadoDeEnvio(False, f"Falha no envio: {err}", destinatario)

    logger.info("[E-mail] Mensagem entregue ao servidor para %s.", _mascarar(destinatario))
    return ResultadoDeEnvio(True, "E-mail enviado.", destinatario)


def _mascarar(endereco: str) -> str:
    """
    Endereço abreviado para o log.

    O log do Revsist é lido, copiado e colado em relato de problema; o endereço
    inteiro de quem pediu acesso não precisa viajar junto (doc 40 §40.5).
    """
    usuario, _, dominio = endereco.partition("@")
    if not dominio:
        return "***"
    visivel = usuario[:2] if len(usuario) > 2 else usuario[:1]
    return f"{visivel}***@{dominio}"
