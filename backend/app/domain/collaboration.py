#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Domínio de Colaboração e Políticas de Equipe (Doc 43 §43.4, Doc 44 Fase 2).

Função pura sem dependência de FastAPI ou banco de dados.
Regra de ouro: Nenhuma comparação `collaboration_mode == ...` deve existir fora deste módulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PoliticaDeColaboracao:
    """
    Efeitos práticos da modalidade de colaboração em cada etapa da revisão.

    Garante que o comportamento do sistema seja derivado de forma determinística
    e testável sem duplicação de regras em rotas.
    """
    corpus_compartilhado: bool
    protocolo_coeditavel: bool
    revisores_por_estudo: int
    triagem_cega: bool
    extracao_cega: bool
    resolucao_de_conflito: str


# Presets canônicos (§43.4.2)
MODALIDADE_INDIVIDUAL = "individual"
MODALIDADE_COLABORATIVA = "colaborativa"
MODALIDADE_CEGA_POR_PARES = "cega_por_pares"

MODALIDADES_VALIDAS = frozenset({
    MODALIDADE_INDIVIDUAL,
    MODALIDADE_COLABORATIVA,
    MODALIDADE_CEGA_POR_PARES,
})

RESOLUCOES_VALIDAS = frozenset({
    "coordenador",
    "terceiro_revisor",
})


def politica_de(projeto: Any) -> PoliticaDeColaboracao:
    """
    Calcula a política ativa para um projeto de revisão.

    Aceita instâncias de ProjectModel, Schemas Pydantic ou dicionários.
    """
    if isinstance(projeto, dict):
        mode = projeto.get("collaboration_mode", MODALIDADE_INDIVIDUAL)
        reviewers = int(projeto.get("reviewers_per_paper") or 1)
        conflict = str(projeto.get("conflict_resolution") or "coordenador")
    else:
        mode = getattr(projeto, "collaboration_mode", MODALIDADE_INDIVIDUAL)
        reviewers = int(getattr(projeto, "reviewers_per_paper", 1) or 1)
        conflict = str(getattr(projeto, "conflict_resolution", "coordenador") or "coordenador")

    if mode == MODALIDADE_COLABORATIVA:
        return PoliticaDeColaboracao(
            corpus_compartilhado=True,
            protocolo_coeditavel=True,
            revisores_por_estudo=1,
            triagem_cega=False,
            extracao_cega=False,
            resolucao_de_conflito="coordenador",
        )
    elif mode == MODALIDADE_CEGA_POR_PARES:
        return PoliticaDeColaboracao(
            corpus_compartilhado=True,
            protocolo_coeditavel=True,
            revisores_por_estudo=max(2, reviewers),
            triagem_cega=True,
            extracao_cega=True,
            resolucao_de_conflito=conflict if conflict in RESOLUCOES_VALIDAS else "coordenador",
        )
    else:
        # Padrão: Individual
        return PoliticaDeColaboracao(
            corpus_compartilhado=False,
            protocolo_coeditavel=False,
            revisores_por_estudo=1,
            triagem_cega=False,
            extracao_cega=False,
            resolucao_de_conflito="coordenador",
        )
