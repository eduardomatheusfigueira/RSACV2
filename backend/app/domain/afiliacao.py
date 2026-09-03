#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Afiliação institucional — o que o campo `institution` realmente contém.

Os coletores escrevem o **nome da própria base** no campo de instituição, e
não a afiliação dos autores:

    app/harvesters/scielo.py:115,199   institution="SciELO"
    app/harvesters/openalex.py:232     institution="OpenAlex"
    app/harvesters/pubmed.py:244       institution="PubMed/NCBI"
    app/harvesters/scopus.py:219       institution="Scopus/Elsevier"
    app/harvesters/bdtd.py:563         institution=inst_str or "BDTD/IBICT"

Só a BDTD preenche o campo com o que ele diz ser, e mesmo ela recorre ao
literal quando o registro não traz afiliação.

Medido no acervo real em 31/08/2026: **86.859 de 87.108 registros — 99,7% —
trazem um nome de coletor**. O ranking de instituições da aba de Indicadores,
que lia esse campo direto, informava ao pesquisador que a instituição mais
produtiva do seu campo era a biblioteca eletrônica de onde ele baixou os
registros (doc 47 §B-01).

Este módulo existe para que esse literal nunca mais seja confundido com uma
afiliação. A solução definitiva é `bib_authorships`, alimentada pelo
enriquecimento externo (doc 48 §4.3), onde a instituição vem com identificador
ROR resolvido; até lá, o que se pode fazer é não mentir.
"""

from __future__ import annotations

import re
import unicodedata

#: Literais que os coletores gravam no lugar da afiliação.
#:
#: Comparados após normalização, então basta a forma canônica de cada um.
NOMES_DE_COLETOR: frozenset[str] = frozenset(
    {
        "scielo",
        "openalex",
        "pubmed/ncbi",
        "pubmed",
        "ncbi",
        "scopus/elsevier",
        "scopus",
        "elsevier",
        "bdtd/ibict",
        "bdtd",
        "ibict",
        "crossref",
        "web of science",
    }
)

_ESPACOS = re.compile(r"\s+")


def _normalizar(valor: str) -> str:
    """Minúsculas, sem acento e com espaços colapsados.

    A remoção de acento é o que faz `"SciELO"` e `"Scielo"` caírem na mesma
    chave que `"scielo"` — e é barata o bastante para valer a pena num campo
    que ninguém padronizou.
    """
    texto = _ESPACOS.sub(" ", (valor or "").strip()).casefold()
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def e_nome_de_coletor(valor: str) -> bool:
    """`True` quando o campo traz o nome da base, e não uma afiliação."""
    return _normalizar(valor) in NOMES_DE_COLETOR


def filtrar_afiliacoes(valores: list[str]) -> list[str]:
    """Só o que pode ser afiliação de verdade.

    Descarta vazios e nomes de coletor. O que sobra é pouco — 0,3% do acervo
    medido — mas é real, e vem sempre acompanhado do seu denominador para que
    ninguém leia um ranking de 249 registros como se fosse de 87 mil
    (doc 48 §6.4).
    """
    return [v.strip() for v in valores if (v or "").strip() and not e_nome_de_coletor(v)]
