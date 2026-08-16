#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Entidades de Domínio.
Dataclasses puras representando os conceitos centrais do negócio.
Portadas da V1 e expandidas para a V2.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.domain.enums import Decision, Methodology


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Paper:
    """
    Entidade imutável representando um artigo ou documento científico.
    Qualquer modificação retorna uma nova instância (imutabilidade).
    """
    id: str
    title: str
    authors: str = ""
    year: str = ""
    source: str = ""
    research_type: str = ""
    institution: str = ""
    abstract: str = ""
    download_url: str = ""
    doi: Optional[str] = None
    decision: Decision = Decision.PENDING
    inclusion_criteria: Dict[str, bool] = field(default_factory=dict)
    exclusion_criteria: Dict[str, bool] = field(default_factory=dict)
    questions: Dict[str, str] = field(default_factory=dict)
    observations: str = ""
    ai_confidence: Optional[float] = None

    def with_decision(self, decision: Decision) -> "Paper":
        """Retorna nova instância com a decisão atualizada."""
        return replace(self, decision=decision)

    def with_criterion(self, criterion: str, value: bool, is_exclusion: bool = False) -> "Paper":
        """Retorna nova instância com o critério especificado atualizado."""
        if is_exclusion:
            new_exclusion = dict(self.exclusion_criteria)
            new_exclusion[criterion] = value
            return replace(self, exclusion_criteria=new_exclusion)
        else:
            new_inclusion = dict(self.inclusion_criteria)
            new_inclusion[criterion] = value
            return replace(self, inclusion_criteria=new_inclusion)

    def with_question_answer(self, question: str, answer: str) -> "Paper":
        """Retorna nova instância com a resposta da pergunta de extração atualizada."""
        new_questions = dict(self.questions)
        new_questions[question] = answer
        return replace(self, questions=new_questions)

    def with_observations(self, observations: str) -> "Paper":
        """Retorna nova instância com as observações atualizadas."""
        return replace(self, observations=observations)

    def to_dict(self) -> Dict[str, Any]:
        """Converte a entidade Paper para dicionário serializável."""
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "source": self.source,
            "research_type": self.research_type,
            "institution": self.institution,
            "abstract": self.abstract,
            "download_url": self.download_url,
            "doi": self.doi,
            "decision": self.decision.value,
            "inclusion_criteria": dict(self.inclusion_criteria),
            "exclusion_criteria": dict(self.exclusion_criteria),
            "questions": dict(self.questions),
            "observations": self.observations,
            "ai_confidence": self.ai_confidence,
        }


@dataclass
class Protocol:
    """Protocolo da Revisão Sistemática (objetivos, critérios e perguntas)."""
    title: str = ""
    objective: str = ""
    methodology: Methodology = Methodology.PRISMA_P
    pico_framework: Dict[str, str] = field(default_factory=dict)
    inclusion_criteria: List[str] = field(default_factory=list)
    exclusion_criteria: List[str] = field(default_factory=list)
    extraction_questions: List[str] = field(default_factory=list)
    search_descriptors: Dict[str, List[str]] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Converte a entidade Protocol para dicionário."""
        return {
            "title": self.title,
            "objective": self.objective,
            "methodology": self.methodology.value,
            "pico_framework": dict(self.pico_framework),
            "inclusion_criteria": list(self.inclusion_criteria),
            "exclusion_criteria": list(self.exclusion_criteria),
            "extraction_questions": list(self.extraction_questions),
            "search_descriptors": dict(self.search_descriptors),
            "keywords": list(self.keywords),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ScreeningSession:
    """Agregado representando uma sessão de triagem."""
    papers: List[Paper] = field(default_factory=list)
    inclusion_criteria: List[str] = field(default_factory=list)
    exclusion_criteria: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)

    def paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """Recupera um artigo pelo ID único."""
        return next((p for p in self.papers if p.id == paper_id), None)

    def replace_paper(self, updated: Paper) -> None:
        """Substitui o artigo atualizado na sessão mantendo a ordem."""
        for i, p in enumerate(self.papers):
            if p.id == updated.id:
                self.papers[i] = updated
                return
        raise ValueError(f"Paper com ID '{updated.id}' não encontrado na sessão.")

    @property
    def total_count(self) -> int:
        return len(self.papers)

    @property
    def included_count(self) -> int:
        return sum(1 for p in self.papers if p.decision == Decision.INCLUDED)

    @property
    def excluded_count(self) -> int:
        return sum(1 for p in self.papers if p.decision == Decision.EXCLUDED)

    @property
    def pending_count(self) -> int:
        return sum(1 for p in self.papers if p.decision == Decision.PENDING)
