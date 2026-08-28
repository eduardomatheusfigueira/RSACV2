#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Base AI Client Interface.
Define o contrato para integração com múltiplos provedores de IA
(Google Gemini, Alibaba Qwen e Modelos Locais via OpenAI format).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.domain.entities import Paper, Protocol

# Vocabulário fechado das decisões de triagem (doc 29 §29.9.2). Qualquer coisa
# fora disto é resposta inválida do modelo, não uma decisão nova.
DECISOES_VALIDAS = ("Incluído", "Excluído", "Pendente")


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
    # A resposta do modelo veio dentro do contrato? Quando `False`, a decisão
    # foi rebaixada para "Pendente" e isso precisa aparecer na auditoria — uma
    # coerção silenciosa esconderia justamente o sinal de que algo tentou
    # desviar a triagem (§29.9.2).
    response_valid: bool = True
    validation_note: str = ""


def validar_resposta_de_triagem(dados: dict) -> tuple[str, float, str, bool, str]:
    """
    Valida a resposta bruta do modelo contra o contrato de triagem.

    Devolve `(decisao, confianca, justificativa, valida, nota)`.

    Rebaixar para "Pendente" é falha fechada: a decisão volta para o
    pesquisador em vez de entrar na revisão sem que ninguém tenha olhado. O que
    muda em relação ao comportamento anterior é que o desvio deixa de ser
    silencioso — ele é registrado.
    """
    problemas: list[str] = []

    bruta = dados.get("decisao")
    decisao = bruta if bruta in DECISOES_VALIDAS else "Pendente"
    if bruta not in DECISOES_VALIDAS:
        problemas.append(f"decisão fora do vocabulário: {str(bruta)[:60]!r}")

    try:
        confianca = float(dados.get("confianca", 0.9))
    except (TypeError, ValueError):
        confianca = 0.0
        problemas.append("confiança não numérica")

    if not 0.0 <= confianca <= 1.0:
        problemas.append(f"confiança fora da faixa: {confianca}")
        confianca = min(max(confianca, 0.0), 1.0)

    justificativa = dados.get("justificativa") or ""
    if not isinstance(justificativa, str):
        justificativa = str(justificativa)
        problemas.append("justificativa não textual")

    # Justificativa desmesurada costuma ser eco do prompt ou do conteúdo
    # injetado, não análise.
    if len(justificativa) > 8000:
        justificativa = justificativa[:8000] + " […truncada]"
        problemas.append("justificativa truncada por tamanho")

    valida = not problemas
    if not valida:
        decisao = "Pendente"

    return decisao, confianca, justificativa, valida, "; ".join(problemas)


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
    async def assist_field(
        self,
        field_label: str,
        field_guidelines: str = "",
        current_value: str = "",
        project_title: str = "",
        methodology: str = "PRISMA-ScR",
        project_context: Optional[dict] = None,
        action: str = "generate",
        custom_instruction: str = "",
    ) -> dict:
        """Preenche, corrige ou aprimora o conteúdo de um campo específico com system prompt adequado."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Testa conectividade e validade das chaves com o provedor."""
        pass

