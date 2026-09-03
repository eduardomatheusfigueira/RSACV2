#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Instantâneo do corpus — o conjunto parado sobre o qual se mede (doc 48 §3).

Um indicador bibliométrico é uma afirmação sobre um conjunto de documentos. Se
o conjunto muda, a afirmação muda — e a única defesa possível em banca é poder
reconstituir o conjunto exato. O acervo do Revsist muda legitimamente todo dia:
coleta, deduplicação, triagem, resolução de conflito.

O que este módulo garante não é que o corpus fique imutável. É que **toda
mudança seja percebida e dita**, em vez de o mesmo indicador devolver um número
diferente sem explicação (doc 47 §B-05).
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibSnapshotModel,
    PaperModel,
    PaperSourceModel,
)

#: Versão do motor de indicadores.
#:
#: Entra na proveniência de toda figura. Subir esta constante é declarar que um
#: número calculado antes pode não ser reproduzido agora — então ela sobe
#: quando a *conta* muda, e não a cada correção de interface.
VERSAO_DO_MOTOR = "1.0.0"

#: Separador de campo dentro do hash de conteúdo.
#:
#: Unit Separator (0x1F) não aparece em texto bibliográfico. Sem um separador,
#: um documento com título "ab" e autor "c" produziria o mesmo hash de um com
#: título "a" e autor "bc" — dois corpora diferentes com a mesma identidade.
SEPARADOR = "\x1f"

#: Campos que os indicadores leem. O hash cobre exatamente estes.
#:
#: Incluir campos que nenhum indicador usa faria o instantâneo acusar mudança
#: onde nada mudou para a medida; deixar de fora um campo lido faria o
#: contrário, que é pior.
CAMPOS_DO_HASH = (
    "title",
    "authors",
    "year",
    "doi",
    "abstract",
    "journal",
    "institution",
    "research_type",
    "decision",
    "is_duplicate",
)


@dataclass(frozen=True)
class Escopo:
    """Os filtros que definem o corpus, iguais aos da aba de Indicadores."""

    decision: Optional[str] = Decision.INCLUDED.value
    source: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None

    def como_json(self) -> str:
        return json.dumps(
            {
                "decision": self.decision,
                "source": self.source,
                "year_from": self.year_from,
                "year_to": self.year_to,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    @staticmethod
    def de_json(bruto: str) -> "Escopo":
        d = json.loads(bruto or "{}")
        return Escopo(
            decision=d.get("decision"),
            source=d.get("source"),
            year_from=d.get("year_from"),
            year_to=d.get("year_to"),
        )


@dataclass(frozen=True)
class Conferencia:
    """O que mudou no acervo desde que o instantâneo foi congelado."""

    #: `identico` | `conteudo_alterado` | `conjunto_alterado`
    estado: str
    documentos_alterados: tuple[str, ...] = ()
    documentos_adicionados: tuple[str, ...] = ()
    documentos_removidos: tuple[str, ...] = ()

    @property
    def confiavel(self) -> bool:
        """Se os números do instantâneo ainda descrevem o acervo de hoje."""
        return self.estado == "identico"


def _hash_do_conteudo(paper: PaperModel) -> str:
    """Identidade do documento para efeito de medida.

    `is_duplicate` entra convertido para `"0"`/`"1"`: o valor cru pode ser
    `None` em registros antigos, e `str(None)` mudaria o hash de um documento
    cuja marcação de duplicata apenas ganhou valor explícito.
    """
    partes = []
    for campo in CAMPOS_DO_HASH:
        valor = getattr(paper, campo, None)
        if campo == "is_duplicate":
            partes.append("1" if valor else "0")
        else:
            partes.append(str(valor or ""))
    return hashlib.sha256(SEPARADOR.join(partes).encode("utf-8")).hexdigest()


def _consultar_corpus(db: Session, project_id: str, escopo: Escopo) -> list[PaperModel]:
    """Os documentos do escopo, sempre em ordem de `id`.

    A ordem é fixada aqui, e não deixada ao banco: sem ela, o mesmo conjunto
    produziria manifestos diferentes conforme o plano de consulta, e o hash
    deixaria de identificar o corpus.
    """
    query = db.query(PaperModel).filter(
        PaperModel.project_id == project_id,
        or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)),  # noqa: E712
    )
    if escopo.decision:
        query = query.filter(PaperModel.decision == escopo.decision)
    if escopo.source:
        query = query.join(PaperSourceModel).filter(
            PaperSourceModel.source_name == escopo.source
        )
    if escopo.year_from is not None:
        query = query.filter(PaperModel.year >= str(escopo.year_from))
    if escopo.year_to is not None:
        query = query.filter(PaperModel.year <= str(escopo.year_to))
    return query.order_by(PaperModel.id).all()


def montar_manifesto(papers: Iterable[PaperModel]) -> tuple[bytes, str]:
    """Manifesto comprimido e hash do corpus.

    O manifesto guarda os pares, e não só o hash agregado, porque a pergunta
    útil não é "mudou?" — é "o que mudou?". Sem os pares, a única resposta
    possível seria pedir à pessoa que recomeçasse.
    """
    linhas = sorted(f"{p.id}{SEPARADOR}{_hash_do_conteudo(p)}" for p in papers)
    texto = "\n".join(linhas)
    comprimido = gzip.compress(texto.encode("utf-8"), compresslevel=6, mtime=0)
    return comprimido, hashlib.sha256(texto.encode("utf-8")).hexdigest()


def ler_manifesto(comprimido: bytes) -> dict[str, str]:
    if not comprimido:
        return {}
    texto = gzip.decompress(comprimido).decode("utf-8")
    if not texto:
        return {}
    return dict(linha.split(SEPARADOR, 1) for linha in texto.split("\n"))


def criar(
    db: Session,
    project_id: str,
    *,
    escopo: Escopo | None = None,
    rotulo: str = "",
    criado_por: str | None = None,
) -> BibSnapshotModel:
    """Congela o corpus e devolve o instantâneo — já persistido."""
    escopo = escopo or Escopo()
    papers = _consultar_corpus(db, project_id, escopo)
    manifesto, corpus_hash = montar_manifesto(papers)

    instantaneo = BibSnapshotModel(
        project_id=project_id,
        label=rotulo.strip(),
        scope=escopo.como_json(),
        n_documents=len(papers),
        corpus_hash=corpus_hash,
        manifest=manifesto,
        engine_version=VERSAO_DO_MOTOR,
        created_by_user_id=criado_por,
    )
    db.add(instantaneo)
    db.commit()
    db.refresh(instantaneo)
    return instantaneo


def conferir(db: Session, instantaneo: BibSnapshotModel) -> Conferencia:
    """Compara o instantâneo com o acervo de agora.

    Distingue conteúdo alterado de conjunto alterado porque as duas coisas
    pedem respostas diferentes: metadado corrigido em três documentos costuma
    ser inofensivo para um ranking de periódicos e fatal para uma contagem de
    termos; documento que entrou ou saiu muda todo denominador.
    """
    antes = ler_manifesto(instantaneo.manifest)
    agora = {
        p.id: _hash_do_conteudo(p)
        for p in _consultar_corpus(
            db, instantaneo.project_id, Escopo.de_json(instantaneo.scope)
        )
    }

    adicionados = tuple(sorted(set(agora) - set(antes)))
    removidos = tuple(sorted(set(antes) - set(agora)))
    if adicionados or removidos:
        return Conferencia(
            estado="conjunto_alterado",
            documentos_adicionados=adicionados,
            documentos_removidos=removidos,
        )

    alterados = tuple(sorted(pid for pid, h in agora.items() if antes.get(pid) != h))
    if alterados:
        return Conferencia(estado="conteudo_alterado", documentos_alterados=alterados)

    return Conferencia(estado="identico")


def proveniencia(instantaneo: BibSnapshotModel) -> dict:
    """O carimbo que acompanha todo número derivado deste instantâneo.

    Vai no rodapé de cada figura e na exportação (doc 48 §14.4). É o que
    transforma "de onde veio esse número?" numa pergunta respondível.
    """
    congelado = instantaneo.created_at
    if congelado is not None and congelado.tzinfo is None:
        congelado = congelado.replace(tzinfo=timezone.utc)
    return {
        "snapshot_id": instantaneo.id,
        "corpus_hash": instantaneo.corpus_hash,
        "n_documents": instantaneo.n_documents,
        "scope": json.loads(instantaneo.scope or "{}"),
        "engine_version": instantaneo.engine_version,
        "frozen_at": congelado.isoformat() if congelado else None,
    }
