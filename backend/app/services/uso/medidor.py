#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Medidor de consumo de IA (doc 52 §5.5).

Os provedores devolvem a contagem de tokens em toda resposta, e o Revsist a
jogava fora. Este módulo a recolhe sem mudar a assinatura de nenhum cliente de
IA: quem inicia a operação abre um medidor, e os clientes anotam cada
tentativa no medidor que estiver aberto.

    with medidor.medir(db, usuario.id, "sugestao_protocolo"):
        sugestoes = await client.generate_protocol_suggestions(...)

O medidor vive num `ContextVar`, que o asyncio copia para as tarefas criadas
dentro do bloco — uma triagem em lote com `gather` anota tudo no mesmo lugar.

Duas regras:

  * **Toda tentativa conta**, inclusive a recusada por cota: ela também gasta
    requisição, e a proporção de recusas é o que diz se o rodízio de chaves
    funciona.
  * **Medir nunca derruba a operação medida.** A gravação passa pelo portão e
    roda numa sessão própria; qualquer falha vira log, e a triagem segue.
"""

from __future__ import annotations

import logging
import math
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import UserModel, UsoChamadaIAModel, utcnow

logger = logging.getLogger(__name__)

OPERACOES = frozenset({
    "triagem",
    "sugestao_protocolo",
    "assistencia_campo",
    "extracao",
    "teste_conexao",
    "bibliometria_tesauro",
})

RESULTADOS = frozenset({
    "ok",
    "limite_minuto",
    "limite_diario",
    "modelo_indisponivel",
    "falha",
    "resposta_invalida",
})


@dataclass
class _Medicao:
    db: Session
    user_id: str
    operacao: str
    project_id: Optional[str]
    chamadas: list[dict] = field(default_factory=list)


_atual: ContextVar[Optional[_Medicao]] = ContextVar("medidor_de_uso", default=None)

# Tentativas feitas fora de um medidor aberto. Não há onde gravá-las — falta
# a quem atribuir —, mas o número aparece no log e num teste, para que um
# ponto de chamada novo sem medidor não passe despercebido.
nao_atribuidas = 0


@contextmanager
def medir(
    db: Session,
    user_id: Optional[str],
    operacao: str,
    project_id: Optional[str] = None,
) -> Iterator[Optional[_Medicao]]:
    if operacao not in OPERACOES:
        raise ValueError(f"Operação de IA desconhecida: {operacao!r}")
    if not user_id:
        yield None
        return

    medicao = _Medicao(db=db, user_id=user_id, operacao=operacao, project_id=project_id)
    token = _atual.set(medicao)
    try:
        yield medicao
    finally:
        _atual.reset(token)
        if medicao.chamadas:
            _gravar(medicao)


def _inteiro(valor: Any) -> Optional[int]:
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)) and valor >= 0:
        return int(valor)
    return None


def tokens_do_gemini(resposta: Any) -> Optional[dict]:
    uso = resposta.get("usageMetadata") if isinstance(resposta, dict) else None
    if not isinstance(uso, dict):
        return None
    return {
        "tokens_entrada": _inteiro(uso.get("promptTokenCount")),
        "tokens_saida": _inteiro(uso.get("candidatesTokenCount")),
        "tokens_raciocinio": _inteiro(uso.get("thoughtsTokenCount")),
        "tokens_cache": _inteiro(uso.get("cachedContentTokenCount")),
        "tokens_total": _inteiro(uso.get("totalTokenCount")),
    }


def tokens_openai(resposta: Any) -> Optional[dict]:
    uso = resposta.get("usage") if isinstance(resposta, dict) else None
    if not isinstance(uso, dict):
        return None
    detalhes = uso.get("completion_tokens_details") or {}
    cache = uso.get("prompt_tokens_details") or {}
    return {
        "tokens_entrada": _inteiro(uso.get("prompt_tokens")),
        "tokens_saida": _inteiro(uso.get("completion_tokens")),
        "tokens_raciocinio": _inteiro(detalhes.get("reasoning_tokens")) if isinstance(detalhes, dict) else None,
        "tokens_cache": _inteiro(cache.get("cached_tokens")) if isinstance(cache, dict) else None,
        "tokens_total": _inteiro(uso.get("total_tokens")),
    }


def anotar(
    *,
    provedor: str,
    modelo_pedido: str,
    resultado: str,
    modelo_respondeu: str = "",
    tokens: Optional[dict] = None,
    caracteres_enviados: int = 0,
    caracteres_recebidos: int = 0,
    latencia_ms: int = 0,
    chave_ordinal: Optional[int] = None,
) -> None:
    """Anota uma tentativa no medidor aberto. Nunca levanta."""
    global nao_atribuidas
    try:
        medicao = _atual.get()
        if medicao is None:
            nao_atribuidas += 1
            logger.debug("[Uso] Chamada de IA fora de medidor (%s/%s).", provedor, modelo_pedido)
            return

        if resultado not in RESULTADOS:
            resultado = "falha"

        estimado = False
        contagem = dict(tokens) if tokens else {}
        if resultado in ("ok", "resposta_invalida") and not any(contagem.values()):
            # Sem contagem do provedor: estimativa grosseira de 4 caracteres por
            # token, marcada como tal. Melhor um número rotulado que um buraco.
            estimado = True
            contagem = {
                "tokens_entrada": math.ceil(caracteres_enviados / 4),
                "tokens_saida": math.ceil(caracteres_recebidos / 4),
                "tokens_raciocinio": None,
                "tokens_cache": None,
                "tokens_total": math.ceil((caracteres_enviados + caracteres_recebidos) / 4),
            }
        elif contagem and contagem.get("tokens_total") is None:
            partes = [contagem.get("tokens_entrada"), contagem.get("tokens_saida"), contagem.get("tokens_raciocinio")]
            if any(p is not None for p in partes):
                contagem["tokens_total"] = sum(p or 0 for p in partes)

        medicao.chamadas.append({
            "user_id": medicao.user_id,
            "project_id": medicao.project_id,
            "operacao": medicao.operacao,
            "provedor": str(provedor or "")[:40],
            "modelo_pedido": str(modelo_pedido or "")[:100],
            "modelo_respondeu": str(modelo_respondeu or "")[:100],
            "chave_ordinal": chave_ordinal,
            "tentativa": len(medicao.chamadas) + 1,
            "resultado": resultado,
            "tokens_entrada": contagem.get("tokens_entrada"),
            "tokens_saida": contagem.get("tokens_saida"),
            "tokens_raciocinio": contagem.get("tokens_raciocinio"),
            "tokens_cache": contagem.get("tokens_cache"),
            "tokens_total": contagem.get("tokens_total"),
            "estimado": estimado,
            "latencia_ms": max(0, int(latencia_ms)),
            "ocorrido_em": utcnow(),
        })
    except Exception:  # pragma: no cover — defesa, não fluxo
        logger.exception("[Uso] Falha ao anotar chamada de IA; a operação segue.")


def _gravar(medicao: _Medicao) -> None:
    from app.services.uso import portao

    try:
        usuario = medicao.db.get(UserModel, medicao.user_id)
        bloqueio = portao.motivo_de_bloqueio(medicao.db, usuario, "A")
        if bloqueio:
            return
        with Session(bind=medicao.db.get_bind()) as sessao:
            sessao.add_all(UsoChamadaIAModel(**c) for c in medicao.chamadas)
            sessao.commit()
    except Exception:
        logger.exception("[Uso] Falha ao gravar o consumo de IA; a operação medida não é afetada.")
