#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Enumeradores de Domínio.
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


class TaskStatus(str, Enum):
    """Status genérico de tarefas em background."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
