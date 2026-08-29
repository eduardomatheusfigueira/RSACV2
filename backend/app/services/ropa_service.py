#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Registro das operações de tratamento (ROPA), doc 40 §40.5.2, L-60.

O art. 37 da LGPD manda o controlador manter registro das operações de
tratamento que realiza. Este módulo é a única porta de entrada desse registro.

Ser a única porta é o ponto. A regra que interessa — **o ROPA registra que
houve tratamento, nunca o conteúdo tratado** — não se sustenta em disciplina de
quem escreve o código; sustenta-se em não existir caminho por onde o conteúdo
passe. Daí `data_categories` aceitar apenas nomes de uma lista fechada: um
e-mail não é uma categoria válida, e a tentativa levanta exceção em vez de
gravar.

Por que isso importa mais aqui do que em outra tabela: o ROPA sobrevive ao
`DELETE /me`. É ele que prova que a eliminação aconteceu. Um dado pessoal que
caísse aqui viraria o único que o titular não consegue apagar — o oposto exato
da função da tabela.
"""

from __future__ import annotations

import json
import logging
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import ProcessingRecordModel

logger = logging.getLogger(__name__)


# ── Vocabulário fechado ───────────────────────────────────────────────
#
# Três listas, e nenhuma delas aceita texto livre. Uma operação nova, uma
# categoria nova ou uma base legal nova exigem passar por aqui — o que é o
# momento certo para perguntar se o tratamento se justifica.

OPERACOES = frozenset({
    "signup",
    "login",
    "data_export",
    "data_erasure",
    "ai_dispatch",
    "pdf_fetch",
    "consent_given",
    "consent_revoked",
})

# Categorias, não valores. "contato" é categoria; "fulano@exemplo.br" não é.
CATEGORIAS = frozenset({
    "identificacao",             # nome de exibição, nome de usuário
    "contato",                   # e-mail
    "credencial",                # hash de senha, token de sessão
    "identificador_externo",     # `sub` do Google
    "conexao",                   # IP, agente de usuário, horário
    "conteudo_de_pesquisa",      # projetos, protocolos, decisões de triagem
    "referencia_bibliografica",  # metadados de publicações
    "documento",                 # PDF obtido
    "consentimento",             # data e versão do aceite
})

# Incisos do art. 7º da LGPD.
BASES_LEGAIS = frozenset({
    "art7_I_consentimento",
    "art7_II_obrigacao_legal",
    "art7_V_execucao_de_contrato",
    "art7_VI_exercicio_de_direitos",
    "art7_IX_legitimo_interesse",
})


class RegistroInvalido(ValueError):
    """
    Tentativa de gravar algo que o ROPA não aceita.

    É erro de programação, não de entrada do usuário: nenhuma requisição
    consegue provocá-lo, porque as categorias são escolhidas no código. Por
    isso levanta em vez de anotar um aviso e seguir — um ROPA que aceita o que
    não entende não serve para prestar contas.
    """


def _validar_categorias(categorias: Iterable[str]) -> list[str]:
    lista = sorted(set(categorias))
    if not lista:
        raise RegistroInvalido(
            "Toda operação trata alguma categoria de dado; lista vazia quase "
            "sempre significa que quem chamou não parou para pensar em qual."
        )
    desconhecidas = [c for c in lista if c not in CATEGORIAS]
    if desconhecidas:
        raise RegistroInvalido(
            f"Categorias fora do vocabulário: {desconhecidas}. "
            f"Se o que se quer gravar é um valor — um e-mail, um nome, um IP —, "
            f"a resposta é não: o ROPA guarda a categoria, nunca o dado. "
            f"Se é mesmo uma categoria nova, acrescente-a a CATEGORIAS."
        )
    return lista


def registrar(
    db: Session,
    *,
    operation: str,
    legal_basis: str,
    purpose: str,
    data_categories: Iterable[str],
    user_id: Optional[str] = None,
    recipient: Optional[str] = None,
    international: bool = False,
    commit: bool = True,
) -> ProcessingRecordModel:
    """
    Grava uma linha no ROPA.

    Os argumentos são só de palavra-chave de propósito: `registrar(db, x, y, z)`
    com quatro strings posicionais é convite a trocar `purpose` por
    `legal_basis` sem que nada reclame.

    `commit=False` para quem já está dentro de uma transação — o caso do
    `DELETE /me`, onde o registro da eliminação precisa cair junto com ela se
    algo falhar no meio.
    """
    if operation not in OPERACOES:
        raise RegistroInvalido(
            f"Operação desconhecida: {operation!r}. Conhecidas: {sorted(OPERACOES)}"
        )
    if legal_basis not in BASES_LEGAIS:
        raise RegistroInvalido(
            f"Base legal desconhecida: {legal_basis!r}. Conhecidas: {sorted(BASES_LEGAIS)}"
        )
    if not purpose or not purpose.strip():
        raise RegistroInvalido(
            "Finalidade em branco. O art. 6º I exige propósito determinado e informado."
        )

    categorias = _validar_categorias(data_categories)

    registro = ProcessingRecordModel(
        user_id=user_id,
        operation=operation,
        legal_basis=legal_basis,
        purpose=purpose.strip(),
        data_categories=json.dumps(categorias, ensure_ascii=False),
        recipient=recipient,
        international=international,
    )
    db.add(registro)
    if commit:
        db.commit()
        db.refresh(registro)
    else:
        db.flush()
    return registro


def categorias_de(registro: ProcessingRecordModel) -> list[str]:
    """Lê de volta a lista de categorias, tolerando linha corrompida."""
    try:
        valor = json.loads(registro.data_categories or "[]")
    except json.JSONDecodeError:
        logger.warning("[ROPA] data_categories ilegível no registro %s", registro.id)
        return []
    return valor if isinstance(valor, list) else []
