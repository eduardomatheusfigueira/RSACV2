#!/usr/bin/env python

"""Revsist — Schemas da Aba de B.I. e Bibliometria (doc 32)."""


from pydantic import BaseModel

from app.schemas.bibliometria import Proveniencia


class CriterionFunnelItem(BaseModel):
    criterion_id: str
    text: str
    is_exclusion: bool
    evaluated_count: int
    met_count: int
    not_met_count: int


class SourceComposition(BaseModel):
    source_name: str
    found_count: int
    included_count: int


class YearCount(BaseModel):
    year: str
    count: int


class NameCount(BaseModel):
    """Item de ranking (periódico, autor ou instituição) — doc 32 §4."""
    name: str
    count: int


class PdfHealth(BaseModel):
    by_status: dict[str, int]
    scanned_ratio: float | None = None
    extraction_completeness: float | None = None


class InsightsFiltersApplied(BaseModel):
    decision: str
    source: str | None = None
    year_from: int | None = None
    year_to: int | None = None


class AiProvenance(BaseModel):
    """Processo e proveniência de IA — doc 32 §6.5, doc 33 Fase 3."""
    throughput_by_user: list[NameCount]
    decisions_by_origin: dict[str, int]
    ai_invalid_response_rate: float | None = None
    ai_confidence_distribution: list[NameCount]


class ProjectInsights(BaseModel):
    prisma: dict
    criteria_funnel: list[CriterionFunnelItem]
    composition_by_decision: dict[str, int]
    composition_by_source: list[SourceComposition]
    composition_by_year: list[YearCount]
    composition_by_research_type: list[NameCount]
    top_journals: list[NameCount]
    top_authors: list[NameCount]
    top_institutions: list[NameCount]
    #: Denominador do ranking acima. As bases de coleta não fornecem afiliação
    #: — o campo traz o nome do próprio coletor em 99,7% dos registros
    #: (doc 47 §B-01) —, então o ranking cobre uma fração pequena do acervo e
    #: precisa dizer qual (doc 48 §6.4).
    institutions_coverage: dict[str, int]
    #: Sobre que corpus estes números foram calculados (doc 48 §14.4).
    #:
    #: `None` quando a consulta não citou instantâneo — e nesse caso os
    #: agregados descrevem o acervo de agora, que muda todo dia. É o que a
    #: tela precisa dizer em vez de deixar subentendido.
    provenance: Proveniencia | None = None
    pdf_health: PdfHealth
    ai_provenance: AiProvenance
    filters_applied: InsightsFiltersApplied
