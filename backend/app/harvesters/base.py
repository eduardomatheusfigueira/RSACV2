#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Base Harvester Interface & Domain Contract.
Define os contratos, estruturas de dados e classe base para todos os coletores.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional


class HarvestSourceError(RuntimeError):
    """
    Falha que impede a fonte de entregar resultados confiáveis.

    Erro de rede, bloqueio (403/429 persistente) ou mudança de layout que zera a
    raspagem **não podem** terminar como coleta bem-sucedida com zero registros:
    o número de recuperados vai para o fluxograma PRISMA. Coletores levantam esta
    exceção para que a execução seja marcada `failed` com mensagem visível, em vez
    de `completed` com zero.
    """

    def __init__(self, source_name: str, motivo: str, detalhes: Optional[str] = None):
        self.source_name = source_name
        self.motivo = motivo
        self.detalhes = detalhes
        mensagem = f"[{source_name}] {motivo}"
        if detalhes:
            mensagem = f"{mensagem} ({detalhes})"
        super().__init__(mensagem)


@dataclass(frozen=True)
class HarvestQuery:
    """Recorte de busca completo e imutável para uma sessão de coleta."""

    descriptors: List[str]

    # Recorte temporal e linguístico
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    languages: List[str] = field(default_factory=list)  # ISO 639-1: "pt", "en", "es"
    document_types: List[str] = field(default_factory=list)  # Tipos canônicos
    institutions: List[str] = field(default_factory=list)
    open_access_only: bool = False

    # Volume e ritmo
    max_records_per_descriptor: Optional[int] = None  # None = ilimitado
    page_size: Optional[int] = None  # None = padrão do coletor
    delay: Optional[float] = None  # None = padrão do coletor

    # Enriquecimento e scraping de detalhes
    fetch_details: bool = True

    # Metadados de auditoria e reprodutibilidade
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class HarvesterCapabilities:
    """Declaração formal dos filtros e capacidades suportadas nativamente pela fonte."""

    supports_year_range: bool = False
    supports_language: bool = False
    supports_document_type: bool = False
    supports_institution: bool = False
    supports_open_access: bool = False
    supports_boolean_query: bool = True
    max_native_filters: Optional[int] = None  # BDTD = 2 (limite WAF)
    requires_api_key: bool = False
    default_page_size: int = 25
    max_page_size: int = 100
    default_delay: float = 1.0


@dataclass
class RawPaperRecord:
    """Registro bruto extraído de uma base de dados antes da deduplicação e persistência."""

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

    # Campos adicionais de metadados ricos e auditoria PRISMA
    advisor: str = ""
    journal: str = ""
    language: str = ""
    keywords: str = ""
    matched_descriptor: str = ""
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Coerção defensiva: garante que campos textuais nunca contenham listas ou None,
        evitando corrupção silenciosa de resumos ou autores no SQLite.
        """
        for attr in ("title", "authors", "abstract", "institution", "journal", "advisor", "research_type", "keywords"):
            val = getattr(self, attr, None)
            if isinstance(val, (list, tuple, set)):
                cleaned_val = " ".join(str(item).strip() for item in val if item)
                setattr(self, attr, cleaned_val.strip())
            elif val is None:
                setattr(self, attr, "")
            else:
                setattr(self, attr, str(val).strip())

        if self.doi:
            self.doi = str(self.doi).strip() or None

    @property
    def source(self) -> str:
        """Alias para source_name para compatibilidade retroativa."""
        return self.source_name


@dataclass
class HarvestProgress:
    """Informações de progresso transmitidas em tempo real via WebSockets."""

    source_name: str
    current_descriptor: str
    page: int
    total_found_so_far: int
    phase: str = "harvesting"  # "harvesting", "scraping_details", "completed"
    is_complete: bool = False
    error: Optional[str] = None


ProgressCallback = Callable[[HarvestProgress], Awaitable[None]]


class BaseHarvester(ABC):
    """Classe base abstrata para todos os harvesters científicos do Revsist."""

    capabilities: HarvesterCapabilities = HarvesterCapabilities()

    def __init__(self, source_name: str, timeout: float = 35.0):
        self.source_name = source_name
        self.timeout = timeout

    @abstractmethod
    async def harvest(
        self,
        query: HarvestQuery | List[str],
        on_progress: Optional[ProgressCallback] = None,
        max_records_per_descriptor: Optional[int] = None,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        """
        Executa a coleta assíncrona gerando instâncias de RawPaperRecord.
        Aceita tanto HarvestQuery quanto List[str] para retrocompatibilidade.
        """
        yield  # type: ignore
