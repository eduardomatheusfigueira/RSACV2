#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Páginas que os botões do aviso de novo pedido abrem.

`GET /convite/decidir?t=...` mostra o pedido e pede confirmação.
`POST /convite/decidir` executa a decisão e mostra o resultado.

São páginas HTML servidas pelo backend, e não telas da SPA, por dois motivos:
elas precisam funcionar sem sessão — quem clica está na caixa de entrada, não
logado no Revsist —, e precisam abrir rápido num celular, sem carregar os
1,5 MB da aplicação para mostrar um botão.

Nada aqui usa JavaScript. A política de conteúdo das páginas proíbe script, e
isso não é detalhe: o token de decisão está na URL, e uma página sem script é
uma página onde nenhum código injetado consegue lê-lo.

As garantias do link — assinatura, vencimento, uso único e ação só no POST —
estão descritas em `services/convite_admin.py`.
"""

from __future__ import annotations

import html
import logging
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import InviteRequestModel
from app.services import aprovacao_convite, convite_admin, convite_mensagens

logger = logging.getLogger(__name__)

router = APIRouter(include_in_schema=False)

e = html.escape

PAPEL = convite_mensagens.PAPEL
TINTA = convite_mensagens.TINTA
TINTA_SUAVE = convite_mensagens.TINTA_SUAVE
ACENTO = convite_mensagens.ACENTO
BORDA = convite_mensagens.BORDA
VERDE_WHATSAPP = "#1f7a4d"
VERMELHO = "#a83434"

CABECALHOS = {
    # Sem script, sem recurso externo, sem enquadramento. Estilo embutido é a
    # única coisa que a página carrega.
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'none'"
    ),
    # O token está na URL: nada de guardar a página em cache compartilhado.
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
}


def _pagina(titulo: str, corpo: str, status: int = 200) -> HTMLResponse:
    documento = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="referrer" content="no-referrer" />
<title>{e(titulo)} — Revsist</title>
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;background:{PAPEL};color:{TINTA};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%}}
  main{{max-width:480px;margin:0 auto;padding:20px 14px 40px}}
  .cartao{{background:#fff;border:1px solid {BORDA};border-top:5px solid {ACENTO};border-radius:6px;padding:26px 22px 24px}}
  .marca{{font-family:'JetBrains Mono',Consolas,monospace;font-size:13px;font-weight:700;letter-spacing:.16em;color:{ACENTO}}}
  .rotulo{{margin:20px 0 0;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:{TINTA_SUAVE}}}
  h1{{margin:6px 0 0;font-size:24px;line-height:1.25;font-weight:800;letter-spacing:-.01em}}
  p{{font-size:15px;line-height:1.6;color:{TINTA_SUAVE};margin:14px 0 0}}
  dl{{margin:18px 0 0;border-top:1px solid {BORDA}}}
  dt{{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:{TINTA_SUAVE};margin-top:12px}}
  dd{{margin:3px 0 0;padding-bottom:12px;border-bottom:1px solid {BORDA};font-size:15px;word-break:break-word}}
  .codigo{{margin:18px 0 0;padding:16px;border:2px dashed {convite_mensagens.APOIO};border-radius:4px;background:{PAPEL};text-align:center;font-family:'JetBrains Mono',Consolas,monospace;font-size:23px;font-weight:700;letter-spacing:.1em;color:{ACENTO}}}
  .botao{{display:block;width:100%;margin:20px 0 0;padding:16px 14px;border:0;border-radius:5px;font:inherit;font-size:16px;font-weight:700;text-align:center;text-decoration:none;cursor:pointer}}
  .primario{{background:{ACENTO};color:#fff}}
  .perigo{{background:{VERMELHO};color:#fff}}
  .whatsapp{{background:{VERDE_WHATSAPP};color:#fff}}
  .secundario{{background:transparent;color:{TINTA_SUAVE};border:2px solid {BORDA};margin-top:10px}}
  .aviso{{margin:18px 0 0;padding:12px 14px;border-radius:4px;font-size:14px;line-height:1.5}}
  .ok{{background:#e6f2ec;color:#1b5e3c;border:1px solid #b9dbc8}}
  .falha{{background:#f7e6e6;color:#7a2424;border:1px solid #e3bcbc}}
  .neutro{{background:{PAPEL};color:{TINTA_SUAVE};border:1px solid {BORDA}}}
  textarea{{width:100%;margin-top:8px;min-height:72px;padding:10px;border:1px solid {BORDA};border-radius:4px;font:inherit;font-size:15px}}
  label{{display:block;margin-top:18px;font-size:13px;font-weight:700;color:{TINTA}}}
  .link{{font-size:13px;word-break:break-all;color:{ACENTO}}}
  .rodape{{margin-top:22px;text-align:center;font-size:13px}}
  .rodape a{{color:{ACENTO}}}
</style>
</head>
<body>
<main>
  <div class="cartao">
    <div class="marca">REVSIST</div>
    {corpo}
  </div>
  <p class="rodape"><a href="{e(_painel(), quote=True)}">Abrir o painel de convites</a></p>
</main>
</body>
</html>"""
    return HTMLResponse(documento, status_code=status, headers=CABECALHOS)


def _painel() -> str:
    return f"{convite_mensagens._base_publica()}/app/#/settings"


def _ficha(p: InviteRequestModel) -> str:
    return f"""
    <dl>
      <dt>E-mail</dt><dd>{e(p.email)}</dd>
      <dt>Telefone</dt><dd>{e(p.telefone)}</dd>
      <dt>Instituição</dt><dd>{e(p.instituicao or 'não informada')}</dd>
      <dt>Como conheceu</dt><dd>{e(p.onde_conheceu)}</dd>
      <dt>Recebido em</dt><dd>{e(convite_admin.hora_de_brasilia(p.created_at))}</dd>
    </dl>"""


def _erro(titulo: str, texto: str, status: int) -> HTMLResponse:
    return _pagina(
        titulo,
        f"""<p class="rotulo">Não foi possível continuar</p>
        <h1>{e(titulo)}</h1>
        <p>{texto}</p>""",
        status,
    )


def _abrir(db: Session, token: str):
    """Confere o token e busca o pedido. Devolve (decisão, pedido) ou uma página de erro."""
    try:
        decisao = convite_admin.verificar(token)
    except convite_admin.LinkVencido:
        return None, _erro(
            "Este link venceu",
            f"Os botões do e-mail valem por {convite_admin.VALIDADE_DO_LINK_DIAS} dias. "
            "O pedido continua no painel, onde você pode decidir.",
            410,
        )
    except convite_admin.LinkInvalido:
        return None, _erro(
            "Link inválido",
            "O endereço está incompleto ou foi alterado. Abra o link direto do e-mail, "
            "sem editar, ou decida pelo painel.",
            400,
        )

    pedido = db.query(InviteRequestModel).filter(InviteRequestModel.id == decisao.pedido_id).first()
    if not pedido:
        return None, _erro(
            "Pedido não encontrado",
            "Este pedido foi excluído ou já não existe.",
            404,
        )
    return (decisao, pedido), None


def _pagina_ja_respondido(p: InviteRequestModel) -> HTMLResponse:
    if p.status == "aprovado" and p.invite_code_generated:
        # Reaproveitar o link de aprovar mostra de novo o que falta fazer — o
        # WhatsApp — sem reenviar e-mail nem gerar outro código. É o caso de
        # quem aprovou, fechou a página e só depois lembrou da mensagem.
        m = convite_mensagens.montar_tudo(p.nome, p.telefone, p.invite_code_generated)
        zap = (
            f'<a class="botao whatsapp" href="{e(m.whatsapp_url, quote=True)}">Enviar no WhatsApp</a>'
            if m.whatsapp_url
            else ""
        )
        return _pagina(
            "Pedido já aprovado",
            f"""<p class="rotulo">Já decidido</p>
            <h1>{e(p.nome)} já foi aprovado(a)</h1>
            <p>Aprovado em {e(convite_admin.hora_de_brasilia(p.responded_at))}. Nada foi feito de novo.</p>
            <div class="codigo">{e(p.invite_code_generated)}</div>
            {zap}
            <p class="link">{e(m.link_direto)}</p>""",
        )
    return _pagina(
        "Pedido já respondido",
        f"""<p class="rotulo">Já decidido</p>
        <h1>Este pedido já foi {e(p.status)}</h1>
        <p>Respondido em {e(convite_admin.hora_de_brasilia(p.responded_at))}. Para mudar a decisão, use o painel.</p>""",
    )


@router.get("/convite/decidir")
def confirmar(t: str = "", db: Session = Depends(get_db)):
    """Mostra o pedido e pede confirmação. Não muda nada."""
    aberto, erro = _abrir(db, t)
    if erro:
        return erro
    decisao, pedido = aberto

    if pedido.status != "pendente":
        return _pagina_ja_respondido(pedido)

    primeiro = e(pedido.nome.split()[0] if pedido.nome.split() else pedido.nome)
    if decisao.acao == "aprovar":
        acao_html = f"""
        <form method="post" action="/convite/decidir">
          <input type="hidden" name="t" value="{e(t, quote=True)}" />
          <button class="botao primario" type="submit">Confirmar aprovação</button>
        </form>
        <p>Isto gera o código de uso único, envia a {primeiro} o e-mail de boas-vindas e deixa o
        WhatsApp pronto para você mandar.</p>"""
        rotulo = "Aprovar pedido de convite"
    else:
        acao_html = f"""
        <form method="post" action="/convite/decidir">
          <input type="hidden" name="t" value="{e(t, quote=True)}" />
          <label for="notas">Motivo (opcional, fica só com você)</label>
          <textarea id="notas" name="notas" maxlength="2000"></textarea>
          <button class="botao perigo" type="submit">Confirmar recusa</button>
        </form>
        <p>{primeiro} não recebe aviso da recusa.</p>"""
        rotulo = "Recusar pedido de convite"

    return _pagina(
        rotulo,
        f"""<p class="rotulo">{rotulo}</p>
        <h1>{e(pedido.nome)}</h1>
        {_ficha(pedido)}
        {acao_html}""",
    )


@router.post("/convite/decidir")
async def decidir(request: Request, db: Session = Depends(get_db)):
    """Executa a decisão confirmada."""
    # Leitura manual do formulário: o corpo é pequeno e fixo, e isso mantém a
    # rota independente do formato de envio que o navegador escolher.
    campos = parse_qs((await request.body()).decode("utf-8", errors="replace"))
    token = (campos.get("t") or [""])[0]
    notas = (campos.get("notas") or [""])[0][:2000]

    aberto, erro = _abrir(db, token)
    if erro:
        return erro
    decisao, pedido = aberto

    if pedido.status != "pendente":
        return _pagina_ja_respondido(pedido)

    if decisao.acao == "recusar":
        aprovacao_convite.recusar(db, pedido, via="e-mail", notas=notas)
        return _pagina(
            "Pedido recusado",
            f"""<p class="rotulo">Feito</p>
            <h1>Pedido de {e(pedido.nome)} recusado</h1>
            <p>A pessoa não foi avisada. Se mudar de ideia, dá para aprovar depois pelo painel.</p>""",
        )

    r = aprovacao_convite.aprovar(db, pedido, aprovado_por_id=None, via="e-mail")
    primeiro = e(pedido.nome.split()[0] if pedido.nome.split() else pedido.nome)

    if r.envio.enviado:
        aviso_email = f'<div class="aviso ok">E-mail de boas-vindas enviado para <strong>{e(pedido.email)}</strong>.</div>'
    else:
        aviso_email = (
            f'<div class="aviso falha">O convite foi criado, mas o e-mail não saiu: '
            f"{e(r.envio.detalhe)} Mande o código pelo WhatsApp ou copie o link abaixo.</div>"
        )

    if r.mensagens.whatsapp_url:
        zap = f"""<a class="botao whatsapp" href="{e(r.mensagens.whatsapp_url, quote=True)}">Enviar no WhatsApp</a>
        <p>A mensagem abre escrita e endereçada a {primeiro}. Falta só você apertar enviar.</p>"""
    else:
        zap = '<div class="aviso neutro">O telefone informado não forma um número de WhatsApp.</div>'

    return _pagina(
        "Convite aprovado",
        f"""<p class="rotulo">Aprovado</p>
        <h1>{e(pedido.nome)} foi aprovado(a)</h1>
        <div class="codigo">{e(r.convite.code)}</div>
        {aviso_email}
        {zap}
        <p style="margin-top:20px">Link direto do cadastro:</p>
        <p class="link">{e(r.mensagens.link_direto)}</p>""",
    )
