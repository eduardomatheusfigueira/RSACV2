#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Ambiente de Indicadores (docs 47, 48, 49).

A regra que governa todo este pacote, e que não admite exceção:

    Nenhum número produzido aqui pode ter vindo de um modelo de linguagem.

A IA propõe vocabulário, sugere fusões de termos, nomeia agrupamentos e traduz
perguntas em especificações. Contar, somar, ordenar e medir é sempre código
determinístico, sobre um corpus congelado (doc 48 §2).
"""

from .analises import ServicoDeAnalises, interpretar_pergunta
from .enriquecimento import ServicoDeEnriquecimento
from .grafos import ServicoDeGrafos, calcular_forca_aresta
from .indicadores import obter_indicadores_bibliometricos
from .instantaneo import conferir, criar, proveniencia
from .instrumentos import (
    ServicoDeInstrumentos,
    calcular_intervalo_wilson,
    sugerir_lexico_conceitual,
)
from .preregistro import ServicoDePreRegistro
from .tesauro import ServicoDeTesauro
from .texto import extrair_e_persistir_texto, obter_ou_extrair_texto
from .vanguarda import ServicoDeVanguarda

__all__ = [
    "ServicoDeAnalises",
    "ServicoDeEnriquecimento",
    "ServicoDeGrafos",
    "ServicoDeInstrumentos",
    "ServicoDePreRegistro",
    "ServicoDeTesauro",
    "ServicoDeVanguarda",
    "calcular_forca_aresta",
    "calcular_intervalo_wilson",
    "conferir",
    "criar",
    "extrair_e_persistir_texto",
    "interpretar_pergunta",
    "obter_indicadores_bibliometricos",
    "obter_ou_extrair_texto",
    "proveniencia",
    "sugerir_lexico_conceitual",
]






