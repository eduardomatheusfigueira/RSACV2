#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Base Harvester Interface.
Define a classe base abstrata para todos os coletores de dados científicos.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable, Dict, List, Optional


@dataclass
class RawPaperRecord:
    """Registro bruto extraído de uma base de dados antes da deduplicação."""
    title: str
    authors: str = ""
    year: str = ""
    abstract: str = ""
    doi: Optional[str] = None
    source_name: str = ""
    source_id: str = ""
    download_url: str = ""
    research_type: str = ""
    institution: str = ""
    extra_metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class HarvestProgress:
    """Informações de progresso transmitidas em tempo real."""
    source_name: str
    current_descriptor: str
    page: int
    total_found_so_far: int
    is_complete: bool = False
    error: Optional[str] = None


class BaseHarvester(ABC):
    """Classe base para harvesters de literatura científica."""

    def __init__(self, source_name: str, timeout: float = 30.0):
        self.source_name = source_name
        self.timeout = timeout

    @abstractmethod
    async def harvest(
        self,
        descriptors: List[str],
        on_progress: Optional[Callable[[HarvestProgress], None]] = None,
        max_records_per_descriptor: Optional[int] = None,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        """
        Executa a coleta de artigos para a lista de descritores fornecida.
        Retorna um gerador assíncrono de RawPaperRecord.
        """
        yield  # type: ignore
