#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Afiliação — separar a instituição dos autores do nome da base.

Todos os coletores menos a BDTD gravam o nome da própria base no campo de
instituição. Medido no acervo real em 31/08/2026: 99,7% dos registros
(doc 47 §B-01).
"""

import pytest

from app.domain.afiliacao import (
    NOMES_DE_COLETOR,
    e_nome_de_coletor,
    filtrar_afiliacoes,
)


@pytest.mark.parametrize(
    "literal",
    ["SciELO", "OpenAlex", "PubMed/NCBI", "Scopus/Elsevier", "BDTD/IBICT"],
)
def test_literais_gravados_pelos_coletores_sao_reconhecidos(literal):
    """Os cinco valores que aparecem no código dos coletores hoje."""
    assert e_nome_de_coletor(literal) is True


@pytest.mark.parametrize(
    "variacao", ["scielo", "SCIELO", "  SciELO  ", "Scielo", "SciELO"]
)
def test_grafia_e_espaco_nao_escapam_do_filtro(variacao):
    assert e_nome_de_coletor(variacao) is True


def test_afiliacao_de_verdade_passa():
    """O filtro tira o literal da base, não a instituição."""
    reais = [
        "Universidade Federal do Rio de Janeiro",
        "UFRRJ",
        "Instituto Federal de Educação, Ciência e Tecnologia de Pernambuco",
        "Carnegie Mellon University",
    ]
    assert [e_nome_de_coletor(v) for v in reais] == [False, False, False, False]


def test_filtrar_descarta_coletor_e_vazio_e_preserva_o_resto():
    entrada = ["UFRJ", "SciELO", "", "   ", "OpenAlex", " USP "]
    assert filtrar_afiliacoes(entrada) == ["UFRJ", "USP"]


def test_filtrar_preserva_a_ordem_e_as_repeticoes():
    """A contagem do ranking depende de as repetições sobreviverem."""
    assert filtrar_afiliacoes(["UFRJ", "SciELO", "UFRJ"]) == ["UFRJ", "UFRJ"]


def test_valor_nulo_nao_quebra():
    assert e_nome_de_coletor("") is False
    assert e_nome_de_coletor(None) is False  # type: ignore[arg-type]
    assert filtrar_afiliacoes([None, "UFRJ"]) == ["UFRJ"]  # type: ignore[list-item]


def test_conjunto_cobre_todos_os_coletores_do_codigo():
    """Guarda contra coletor novo cujo literal ninguém lembrou de registrar.

    Se um harvester passar a gravar outro nome de base, este teste não pega —
    mas os cinco de hoje ficam fixados, e a lista fica visível para quem
    escrever o próximo.
    """
    for esperado in ("scielo", "openalex", "pubmed/ncbi", "scopus/elsevier", "bdtd/ibict"):
        assert esperado in NOMES_DE_COLETOR
