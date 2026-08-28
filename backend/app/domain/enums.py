#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Enumeradores de Domínio.
Tipos enumerados utilizados em todas as camadas da aplicação.
"""

from enum import Enum


class Decision(str, Enum):
    """Decisões possíveis na triagem de um paper."""
    PENDING = "Pendente"
    INCLUDED = "Incluído"
    EXCLUDED = "Excluído"


class Methodology(str, Enum):
    """Metodologias de revisão sistemática suportadas."""
    PRISMA_SCR = "PRISMA-ScR"
    PRISMA_2020 = "PRISMA-2020"
    PRISMA_P = "PRISMA-P"
    CAMPBELL = "Campbell"
    JBI = "JBI (Scoping/Systematic)"
    METHODI_ORDINATIO = "Methodi Ordinatio"
    CEE_ROSES = "CEE/ROSES"
    COCHRANE = "Cochrane"
    EBSE = "EBSE"
    UMBRELLA = "Umbrella Review"
    OTHER = "Other"


class HarvesterSource(str, Enum):
    """Bases de dados suportadas para coleta."""
    BDTD = "BDTD"
    SCIELO = "SciELO"
    OPENALEX = "OpenAlex"
    PUBMED = "PubMed"
    SCOPUS = "Scopus"


class HarvestStatus(str, Enum):
    """Status de uma execução de coleta."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIProvider(str, Enum):
    """Provedores de IA suportados."""
    GEMINI = "gemini"
    QWEN = "qwen"
    LOCAL = "local"


class DocumentType(str, Enum):
    """Tipos canônicos de documentos científicos."""
    TESE = "Tese"
    DISSERTACAO = "Dissertação"
    ARTIGO = "Artigo de Periódico"
    LIVRO = "Livro"
    CAPITULO = "Capítulo de Livro"
    PREPRINT = "Preprint"
    CONFERENCIA = "Trabalho em Anais/Conferência"
    RELATORIO = "Relatório Técnico"
    OUTRO = "Outro"


def to_canonical_doc_type(source: str, raw_format: str | None) -> str:
    """Normaliza o tipo de documento bruto da base para o vocabulário canônico do Revsist."""
    if not raw_format:
        return DocumentType.OUTRO.value

    fmt = str(raw_format).strip().lower()
    source_upper = source.upper()

    if source_upper == "BDTD":
        if any(k in fmt for k in ("doctoralthesis", "doctoral thesis", "doutorado", "tese")):
            return DocumentType.TESE.value
        if any(k in fmt for k in ("masterthesis", "master thesis", "mestrado", "dissertacao", "dissertação")):
            return DocumentType.DISSERTACAO.value
        if any(k in fmt for k in ("chapter", "capitulo", "capítulo")):
            return DocumentType.CAPITULO.value
        if any(k in fmt for k in ("book", "livro")):
            return DocumentType.LIVRO.value
        if "preprint" in fmt:
            return DocumentType.PREPRINT.value
        if any(k in fmt for k in ("conference", "anais", "conferencia", "congresso")):
            return DocumentType.CONFERENCIA.value
        if any(k in fmt for k in ("report", "relatorio", "relatório")):
            return DocumentType.RELATORIO.value

    elif source_upper == "SCIELO":
        if "preprint" in fmt:
            return DocumentType.PREPRINT.value
        return DocumentType.ARTIGO.value

    elif source_upper == "OPENALEX":
        if any(k in fmt for k in ("journal-article", "article", "article-journal")):
            return DocumentType.ARTIGO.value
        if any(k in fmt for k in ("dissertation", "thesis", "phd-thesis")):
            return DocumentType.TESE.value
        if "masters-thesis" in fmt:
            return DocumentType.DISSERTACAO.value
        if any(k in fmt for k in ("book-chapter", "chapter")):
            return DocumentType.CAPITULO.value
        if any(k in fmt for k in ("book", "monograph")):
            return DocumentType.LIVRO.value
        if any(k in fmt for k in ("proceedings-article", "conference")):
            return DocumentType.CONFERENCIA.value
        if "report" in fmt:
            return DocumentType.RELATORIO.value
        if "preprint" in fmt:
            return DocumentType.PREPRINT.value

    elif source_upper == "PUBMED":
        if any(k in fmt for k in ("journal article", "clinical trial", "review")):
            return DocumentType.ARTIGO.value
        if "preprint" in fmt:
            return DocumentType.PREPRINT.value
        if "book" in fmt:
            return DocumentType.LIVRO.value

    elif source_upper == "SCOPUS":
        if any(k in fmt for k in ("ar", "re", "article", "review")):
            return DocumentType.ARTIGO.value
        if any(k in fmt for k in ("bk", "book")):
            return DocumentType.LIVRO.value
        if any(k in fmt for k in ("ch", "chapter")):
            return DocumentType.CAPITULO.value
        if any(k in fmt for k in ("cp", "conference")):
            return DocumentType.CONFERENCIA.value
        if "dissertation" in fmt:
            return DocumentType.TESE.value

    return DocumentType.OUTRO.value
