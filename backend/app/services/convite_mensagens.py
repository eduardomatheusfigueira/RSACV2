#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — As mensagens que avisam alguém de que o convite foi aprovado.

Três saídas, um mesmo conteúdo: o link direto, o WhatsApp e o e-mail. Elas
vivem juntas porque precisam **dizer a mesma coisa** — o dia em que o texto do
WhatsApp prometer uma coisa e o do e-mail outra, quem recebe os dois perde a
confiança nos dois.

O que faz o caminho ser direto é o link: `https://revsist.com/c/RSAC-XXXX-YYYY`
carrega o código dentro de si. Quem clica não copia, não cola e não digita —
chega na tela de cadastro com o convite já validado. O código continua escrito
por extenso na mensagem, e isso é deliberado: link quebra ao ser encaminhado
por aplicativos que o reescrevem, e nesse caso o código digitado à mão é o que
salva o acesso.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from app.config import settings
from app.services.email_service import ImagemEmbutida

DIRETORIO_PECAS = Path(__file__).resolve().parent.parent / "static" / "email"

# Identificadores das imagens embutidas. São arbitrários, mas precisam bater
# com os `cid:` escritos no HTML — por isso ficam aqui, num lugar só.
CID_PASSOS = "revsist-passos"
CID_ANIMACAO = "revsist-animacao"
CID_ASSINATURA = "revsist-assinatura"

# Paleta, copiada de `frontend/src/styles/globals.css` (tema Platinum & Dusk).
# Repetida aqui em vez de importada porque e-mail não carrega folha de estilo:
# cada cor precisa estar escrita dentro do atributo `style` de cada elemento.
PAPEL = "#e7ecef"
SUPERFICIE = "#ffffff"
TINTA = "#152940"
TINTA_SUAVE = "#3d5a78"
ACENTO = "#274c77"
APOIO = "#6096ba"
BORDA = "#c4d3de"


@dataclass(frozen=True)
class MensagensDeAprovacao:
    link_direto: str
    codigo: str
    whatsapp_texto: str
    whatsapp_url: str
    email_assunto: str
    email_texto: str
    email_html: str


def _base_publica() -> str:
    """
    Endereço público do serviço, sem barra final.

    Cai para `https://revsist.com` quando nada está configurado porque a
    alternativa seria pior: um link relativo numa mensagem de WhatsApp não
    leva a lugar nenhum, e um `http://127.0.0.1:8000` enviado a terceiro é um
    link quebrado com cara de link bom.
    """
    bruto = (settings.public_base_url or "").strip().rstrip("/")
    if bruto:
        return bruto
    dominio = (getattr(settings, "public_domain", "") or "").strip().rstrip("/")
    if dominio:
        return f"https://{dominio}"
    return "https://revsist.com"


def montar_link_direto(codigo: str) -> str:
    """O link curto que abre o cadastro com o convite já preenchido."""
    return f"{_base_publica()}/c/{quote(codigo.strip().upper(), safe='-')}"


def normalizar_telefone(telefone: str) -> str:
    """
    Reduz o telefone ao formato que o `wa.me` aceita: só dígitos, com país.

    O formulário aceita o telefone como a pessoa quiser escrever — "(51)
    99999-8888", "+55 51 99999 8888", "51 9 9999-8888" —, e é bom que aceite:
    exigir formato de quem está pedindo acesso é criar atrito na porta de
    entrada. A normalização fica aqui, onde o custo do palpite é baixo e
    reversível, e não no campo.

    O palpite é explícito: 10 ou 11 dígitos viram número brasileiro, com `55`
    na frente. É o certo para este público — o formulário sugere "(51)
    99999-8888" e quem o preenche é pesquisador no Brasil.

    Mas há uma colisão real nesse palpite: um celular brasileiro sem país tem
    11 dígitos, e um número dos Estados Unidos **com** país também tem 11.
    Contando só dígitos, os dois casos são indistinguíveis. O que os separa é
    o `+`: quem escreve `+1 415 555 2671` está declarando o código do país, e
    essa declaração vale mais que o palpite. Por isso o prefixo é lido antes
    de os dígitos serem contados.
    """
    bruto = (telefone or "").strip()
    digitos = re.sub(r"\D", "", bruto)
    if not digitos:
        return ""

    # `+` e `00` são as duas grafias de "o que vem a seguir é o código do
    # país". Ambas desligam o palpite.
    if bruto.startswith("+"):
        return digitos
    if digitos.startswith("00"):
        return digitos[2:]

    if len(digitos) in (10, 11):
        return f"55{digitos}"
    return digitos


def _primeiro_nome(nome: str) -> str:
    partes = (nome or "").strip().split()
    if not partes:
        return ""
    # Títulos não são nome: "Prof. Dra. Maria Silva" cumprimentada como "Olá,
    # Prof." soa como formulário mal preenchido, que é o oposto do que uma
    # mensagem de boas-vindas precisa transmitir.
    titulos = {
        "prof", "profa", "prof.", "profa.", "dr", "dra", "dr.", "dra.",
        "doutor", "doutora", "me", "me.", "mestre", "sr", "sra", "sr.", "sra.",
    }
    for parte in partes:
        if parte.lower().strip(".") not in {t.strip(".") for t in titulos}:
            return parte
    return partes[-1]


# ══════════════════════════════════════════════════════════════════════
# WhatsApp
# ══════════════════════════════════════════════════════════════════════

def montar_whatsapp(nome: str, codigo: str, link: str) -> tuple[str, str]:
    """
    Texto curto e o `wa.me` que o abre já endereçado.

    Curto de propósito: no WhatsApp, mensagem longa de remetente desconhecido
    é lida como disparo em massa. O que precisa estar ali é o essencial — foi
    aprovado, este é o código, este é o link — e a assinatura de quem fala.
    """
    saudacao = f"Olá, {_primeiro_nome(nome)}!" if _primeiro_nome(nome) else "Olá!"

    texto = (
        f"{saudacao} Seu pedido de acesso ao Revsist foi aprovado.\n\n"
        f"Seu código de convite: {codigo}\n\n"
        f"Para entrar direto, com o código já preenchido:\n{link}\n\n"
        f"Qualquer dúvida, é só responder por aqui.\n"
        f"— Eduardo, Revsist"
    )
    return texto, f"https://wa.me/{{telefone}}?text={quote(texto)}"


def montar_whatsapp_url(telefone: str, nome: str, codigo: str, link: str) -> str:
    """URL pronta do WhatsApp, ou vazia se o telefone não der um número."""
    numero = normalizar_telefone(telefone)
    if not numero:
        return ""
    texto, _ = montar_whatsapp(nome, codigo, link)
    return f"https://wa.me/{numero}?text={quote(texto)}"


# ══════════════════════════════════════════════════════════════════════
# E-mail
# ══════════════════════════════════════════════════════════════════════

def _assinante() -> str:
    return (settings.smtp_from_name or "Eduardo Matheus Figueira").strip()


def montar_email_texto(nome: str, codigo: str, link: str) -> str:
    """
    Versão em texto puro — a que sobra quando o HTML não renderiza.

    Carrega tudo o que importa: o código, o link e como pedir ajuda. Nenhuma
    informação do e-mail bonito existe só lá.
    """
    saudacao = f"Olá, {_primeiro_nome(nome)}." if _primeiro_nome(nome) else "Olá."
    return f"""{saudacao}

Seu pedido de acesso ao Revsist foi aprovado.

SEU CÓDIGO DE CONVITE
{codigo}

ENTRAR DIRETO
{link}

Esse link abre o Revsist com o código já preenchido — não precisa copiar
nem digitar nada. Se preferir, entre em {_base_publica()}/app, escolha
"Tenho um convite" e informe o código acima.

COMO COMEÇAR
1. Clique no link acima.
2. Confira seus dados e escolha um usuário e uma senha.
3. Pronto: o ambiente abre com seu primeiro projeto à espera.

O convite é de uso único e vale para uma conta só.

Qualquer dúvida, responda este e-mail.

— {_assinante()}
Coordenação do Revsist
{_base_publica()}
"""


def montar_email_html(nome: str, codigo: str, link: str) -> str:
    """
    O e-mail em HTML.

    Escrito em tabelas aninhadas e com todo o estilo embutido em atributos
    `style`, o que em qualquer outro contexto seria retrocesso de uma década.
    Aqui é o que funciona: o Outlook para Windows renderiza e-mail com o motor
    do Word, que ignora `<style>` no topo, `float`, `flex` e `grid`. Layout
    feito com qualquer técnica moderna chega empilhado e desalinhado na caixa
    de entrada de quem usa Outlook — que, em universidade, é muita gente.

    As imagens entram por `cid:`, referenciando o que `pecas_do_email()`
    anexa. `width` e `alt` são obrigatórios em cada uma: sem largura, o Outlook
    estoura a imagem no tamanho nativo; sem `alt`, quem bloqueia imagem fica
    sem a instrução.
    """
    primeiro = _primeiro_nome(nome)
    saudacao = f"Olá, {html.escape(primeiro)}." if primeiro else "Olá."
    codigo_seguro = html.escape(codigo)
    link_seguro = html.escape(link, quote=True)
    base = html.escape(_base_publica())

    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Seu acesso ao Revsist foi aprovado</title>
</head>
<body style="margin:0; padding:0; background-color:{PAPEL}; -webkit-text-size-adjust:100%;">

<!-- Prévia: é a linha que o Gmail mostra ao lado do assunto, antes de abrir.
     Sem ela, o cliente usa o primeiro texto que encontrar — que seria o
     "Olá, Fulano." e desperdiçaria o único resumo que o leitor vê na lista. -->
<div style="display:none; max-height:0; overflow:hidden; opacity:0; color:transparent; height:0; width:0;">
  Seu código de convite é {codigo_seguro} — entre direto pelo link, sem digitar nada.
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{PAPEL};">
<tr>
<td align="center" style="padding:28px 12px 40px 12px;">

  <!--[if mso]><table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
  <!-- Fluido em todo cliente, travado em 600px só no Outlook para Windows, que
       ignora max-width. Com width="600" fixo, o e-mail transbordava a tela do
       celular — que é onde a maioria de quem recebe convite vai lê-lo. -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px; margin:0 auto;">

    <!-- Filete da marca -->
    <tr><td style="height:5px; background-color:{ACENTO}; font-size:0; line-height:0;">&nbsp;</td></tr>

    <tr>
    <td style="background-color:{SUPERFICIE}; padding:30px 26px 34px 26px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

      <!-- Marca -->
      <table role="presentation" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="vertical-align:middle;">
            <span style="font-family:'JetBrains Mono',Consolas,monospace; font-size:14px; font-weight:700; letter-spacing:0.16em; color:{ACENTO};">REVSIST</span>
          </td>
        </tr>
      </table>

      <!-- Chamada -->
      <p style="margin:26px 0 0 0; font-size:16px; line-height:1.5; color:{TINTA_SUAVE};">{saudacao}</p>

      <h1 style="margin:10px 0 0 0; font-size:27px; line-height:1.25; font-weight:800; color:{TINTA}; letter-spacing:-0.01em;">
        Seu acesso ao Revsist<br />foi aprovado.
      </h1>

      <p style="margin:16px 0 0 0; font-size:16px; line-height:1.6; color:{TINTA_SUAVE};">
        Seu pedido foi avaliado e aprovado. Abaixo está o seu código de convite
        e o link que abre o cadastro com ele já preenchido.
      </p>

      <!-- Código -->
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:26px 0 0 0;">
        <tr>
          <td align="center" style="background-color:{PAPEL}; border:2px dashed {APOIO}; border-radius:4px; padding:18px 14px;">
            <div style="font-size:11px; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; color:{TINTA_SUAVE};">Seu código de convite</div>
            <div style="margin-top:9px; font-family:'JetBrains Mono',Consolas,monospace; font-size:25px; font-weight:700; letter-spacing:0.11em; color:{ACENTO};">{codigo_seguro}</div>
          </td>
        </tr>
      </table>

      <!-- Botão. Tabela, e não <a> estilizado: no Outlook o padding de um
           link não cria área clicável, e só o texto responderia ao clique. -->
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:26px auto 0 auto;">
        <tr>
          <td align="center" bgcolor="{ACENTO}" style="border-radius:4px;">
            <a href="{link_seguro}" target="_blank"
               style="display:inline-block; padding:15px 38px; font-size:16px; font-weight:700; color:#ffffff; text-decoration:none; border-radius:4px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
              Entrar no Revsist &nbsp;&rarr;
            </a>
          </td>
        </tr>
      </table>

      <p style="margin:14px 0 0 0; font-size:13px; line-height:1.6; color:{TINTA_SUAVE}; text-align:center;">
        Se o botão não funcionar, copie este endereço:<br />
        <a href="{link_seguro}" style="color:{ACENTO}; word-break:break-all;">{link_seguro}</a>
      </p>

      <!-- Divisória -->
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:32px 0 0 0;">
        <tr><td style="height:1px; background-color:{BORDA}; font-size:0; line-height:0;">&nbsp;</td></tr>
      </table>

      <h2 style="margin:30px 0 0 0; font-size:19px; font-weight:800; color:{TINTA};">Como começar</h2>

      <!-- Os três passos, parados. É o que sustenta a instrução onde a
           animação não roda. -->
      <img src="cid:{CID_PASSOS}" width="512" alt="Passo 1: clique no botão deste e-mail. Passo 2: confira seus dados e escolha usuário e senha. Passo 3: comece a revisão."
           style="display:block; width:512px; max-width:100%; height:auto; margin:18px 0 0 0; border:1px solid {BORDA};" />

      <p style="margin:26px 0 0 0; font-size:14px; line-height:1.6; color:{TINTA_SUAVE};">
        E o mesmo caminho, acontecendo:
      </p>

      <img src="cid:{CID_ANIMACAO}" width="512" alt="Animação do percurso: o clique no botão, o código entrando sozinho no campo e o cadastro sendo concluído."
           style="display:block; width:512px; max-width:100%; height:auto; margin:12px 0 0 0; border:1px solid {BORDA};" />

      <p style="margin:26px 0 0 0; font-size:14px; line-height:1.6; color:{TINTA_SUAVE};">
        O convite é de uso único e vale para uma conta só. Qualquer dúvida,
        é só responder este e-mail — ele chega direto para mim.
      </p>

      <!-- Assinatura -->
      <img src="cid:{CID_ASSINATURA}" width="400" alt="{html.escape(_assinante())} — Coordenação do Revsist"
           style="display:block; width:400px; max-width:100%; height:auto; margin:30px 0 0 0;" />

    </td>
    </tr>

    <!-- Rodapé -->
    <tr>
    <td style="padding:18px 26px 0 26px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; font-size:12px; line-height:1.6; color:{TINTA_SUAVE};">
      <p style="margin:0;">
        Você recebeu este e-mail porque pediu acesso ao Revsist em
        <a href="{base}" style="color:{ACENTO}; text-decoration:none;">{base}</a>.
        Se não foi você, pode ignorar — sem o código acima, ninguém entra.
      </p>
    </td>
    </tr>

  </table>
  <!--[if mso]></td></tr></table><![endif]-->

</td>
</tr>
</table>

</body>
</html>"""


def pecas_do_email() -> list[ImagemEmbutida]:
    """As imagens que viajam dentro da mensagem."""
    return [
        ImagemEmbutida(CID_PASSOS, DIRETORIO_PECAS / "como-comecar.png", "como-comecar.png"),
        ImagemEmbutida(CID_ANIMACAO, DIRETORIO_PECAS / "boas-vindas.gif", "boas-vindas.gif"),
        ImagemEmbutida(CID_ASSINATURA, DIRETORIO_PECAS / "assinatura.png", "assinatura.png"),
    ]


def montar_tudo(nome: str, telefone: str, codigo: str) -> MensagensDeAprovacao:
    """Monta as três mensagens de uma vez, a partir do pedido aprovado."""
    codigo = codigo.strip().upper()
    link = montar_link_direto(codigo)
    texto_zap, _ = montar_whatsapp(nome, codigo, link)

    return MensagensDeAprovacao(
        link_direto=link,
        codigo=codigo,
        whatsapp_texto=texto_zap,
        whatsapp_url=montar_whatsapp_url(telefone, nome, codigo, link),
        email_assunto="Seu acesso ao Revsist foi aprovado",
        email_texto=montar_email_texto(nome, codigo, link),
        email_html=montar_email_html(nome, codigo, link),
    )
