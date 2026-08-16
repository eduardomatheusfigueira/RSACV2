#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Base AI Client Interface.
Define o contrato para integração com múltiplos provedores de IA
(Google Gemini, Alibaba Qwen e Modelos Locais via OpenAI format).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from app.domain.entities import Paper, Protocol


@dataclass
class ScreeningResult:
    """Resultado estruturado da triagem com IA."""
    decision: str  # "Incluído", "Excluído", "Pendente"
    inclusion_criteria: Dict[str, bool] = field(default_factory=dict)
    exclusion_criteria: Dict[str, bool] = field(default_factory=dict)
    justification: str = ""
    confidence: float = 1.0  # 0.0 a 1.0
    model_used: str = ""
    provider: str = ""


@dataclass
class ProtocolSuggestions:
    """Sugestões geradas por IA para estruturação de protocolo."""
    objective: str = ""
    pico_population: str = ""
    pico_intervention: str = ""
    pico_comparison: str = ""
    pico_outcome: str = ""
    descriptors_pt: List[str] = field(default_factory=list)
    descriptors_en: List[str] = field(default_factory=list)
    descriptors_es: List[str] = field(default_factory=list)
    inclusion_criteria: List[str] = field(default_factory=list)
    exclusion_criteria: List[str] = field(default_factory=list)
    extraction_questions: List[str] = field(default_factory=list)


class BaseAIClient(ABC):
    """Interface abstrata para clientes de IA generativa."""

    def __init__(self, provider_name: str, model_name: str):
        self.provider_name = provider_name
        self.model_name = model_name

    @abstractmethod
    async def analyze_screening(
        self,
        paper: Paper,
        protocol: Protocol,
    ) -> ScreeningResult:
        """Executa a triagem (Triagem 1) de um artigo contra o protocolo."""
        pass

    @abstractmethod
    async def generate_protocol_suggestions(
        self,
        title: str,
        methodology: str,
        initial_description: str = "",
    ) -> ProtocolSuggestions:
        """Gera sugestões de PICO, descritores em pares e critérios para um novo protocolo."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Testa conectividade e validade das chaves com o provedor."""
        pass
