#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Ingestão dos dados de uso do beta (doc 52 §6.4).

Duas portas, ambas com sessão exigida pelo router agregador:

  * POST /uso/eventos — telas, ações, tempo ativo (Nível B, em geral);
  * POST /uso/erros   — ocorrências de erro do navegador (Nível A).

As duas respondem **204 mesmo quando nada é gravado**. Coleta desligada não é
erro de quem está usando a plataforma; o cabeçalho `X-Uso-Coleta: desligada`
avisa o cliente para parar de enviar até a próxima carga da página.

O `user_id` vem da sessão e só dela. Não existe campo no corpo por onde uma
conta pudesse registrar eventos em nome de outra.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import UserModel, UsoErroModel, UsoEventoModel
from app.schemas.uso import LoteDeErrosIn, LoteDeEventosIn
from app.security.dependencies import require_session
from app.services.uso import erros as sanitizacao
from app.services.uso import portao, vocabulario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uso", tags=["dados_de_uso"])

TAMANHO_MAXIMO_BYTES = 32 * 1024
LOTES_POR_HORA = 120
CABECALHO = "X-Uso-Coleta"

_lotes_recentes: dict[str, deque] = defaultdict(deque)


def _dentro_do_limite(chave: str) -> bool:
    agora = time.monotonic()
    fila = _lotes_recentes[chave]
    while fila and agora - fila[0] > 3600:
        fila.popleft()
    if len(fila) >= LOTES_POR_HORA:
        return False
    fila.append(agora)
    return True


def _exigir_tamanho(request: Request) -> None:
    try:
        tamanho = int(request.headers.get("content-length") or 0)
    except ValueError:
        tamanho = 0
    if tamanho > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Lote grande demais.")


def _instante_confiavel(informado: datetime, recebido: datetime) -> datetime:
    """O relógio do navegador vale só dentro de uma janela plausível."""
    if informado.tzinfo is None:
        informado = informado.replace(tzinfo=timezone.utc)
    if recebido - timedelta(hours=24) <= informado <= recebido + timedelta(minutes=5):
        return informado
    return recebido


def _resposta(gravou: bool) -> Response:
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={CABECALHO: "ativa" if gravou else "desligada"},
    )


@router.post("/eventos", status_code=status.HTTP_204_NO_CONTENT, summary="Registrar eventos de uso do beta")
def registrar_eventos(
    lote: LoteDeEventosIn,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    _exigir_tamanho(request)
    if not _dentro_do_limite(f"eventos:{usuario.id}"):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Muitos lotes de uso.")

    gpc = request.headers.get("sec-gpc") == "1"
    bloqueios = {
        nivel: portao.motivo_de_bloqueio(db, usuario, nivel, sinal_gpc=gpc) for nivel in ("A", "B")
    }
    if bloqueios["A"] and bloqueios["B"]:
        return _resposta(False)

    recebido = datetime.now(timezone.utc)
    descartes: dict[str, int] = defaultdict(int)
    gravados = 0
    for evento in lote.eventos:
        valido, motivo = vocabulario.validar(evento.nome, evento.tela, evento.propriedades)
        if not valido:
            descartes[motivo] += 1
            continue
        if bloqueios[valido.nivel]:
            descartes["nivel_bloqueado"] += 1
            continue
        db.add(
            UsoEventoModel(
                user_id=usuario.id,
                sessao_uso_id=lote.sessao_uso_id,
                nome=valido.nome,
                tela=valido.tela,
                propriedades=json.dumps(valido.propriedades, ensure_ascii=False, sort_keys=True),
                ocorrido_em=_instante_confiavel(evento.ocorrido_em, recebido),
                recebido_em=recebido,
                versao_app=(settings.app_version or "")[:20],
            )
        )
        gravados += 1

    if gravados:
        db.commit()
    if descartes:
        # Categorias e contagens. Nunca o conteúdo que se tentou mandar.
        logger.info("[Uso] %d evento(s) descartado(s): %s", sum(descartes.values()), dict(descartes))
    return _resposta(not bloqueios["B"])


@router.post("/erros", status_code=status.HTTP_204_NO_CONTENT, summary="Registrar ocorrências de erro do navegador")
def registrar_erros(
    lote: LoteDeErrosIn,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    _exigir_tamanho(request)
    if not _dentro_do_limite(f"erros:{usuario.id}"):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Muitos lotes de erro.")

    if portao.motivo_de_bloqueio(db, usuario, "A"):
        return _resposta(False)

    recebido = datetime.now(timezone.utc)
    navegador = sanitizacao.familia_do_navegador(request.headers.get("user-agent"))
    telas = set(vocabulario.telas())
    for ocorrencia in lote.ocorrencias:
        limpa = sanitizacao.sanitizar(ocorrencia.tipo, ocorrencia.mensagem, ocorrencia.pilha)
        db.add(
            UsoErroModel(
                user_id=usuario.id,
                origem="cliente",
                impressao=limpa.impressao,
                tipo=limpa.tipo,
                mensagem=limpa.mensagem,
                pilha=limpa.pilha,
                tela=ocorrencia.tela if ocorrencia.tela in telas else None,
                status_http=ocorrencia.status_http,
                correlacao=(ocorrencia.correlacao or "")[:36] or None,
                versao_app=(settings.app_version or "")[:20],
                navegador=navegador[:40],
                ocorrido_em=_instante_confiavel(ocorrencia.ocorrido_em, recebido),
                recebido_em=recebido,
            )
        )
    db.commit()
    return _resposta(True)
