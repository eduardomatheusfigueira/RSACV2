#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testes unitários para o módulo de domínio puro de colaboração (Doc 43 §43.4).
"""

import pytest
from app.domain.collaboration import (
    MODALIDADE_CEGA_POR_PARES,
    MODALIDADE_COLABORATIVA,
    MODALIDADE_INDIVIDUAL,
    PoliticaDeColaboracao,
    politica_de,
)


def test_politica_individual():
    proj = {"collaboration_mode": MODALIDADE_INDIVIDUAL}
    pol = politica_de(proj)

    assert isinstance(pol, PoliticaDeColaboracao)
    assert pol.corpus_compartilhado is False
    assert pol.protocolo_coeditavel is False
    assert pol.revisores_por_estudo == 1
    assert pol.triagem_cega is False
    assert pol.extracao_cega is False
    assert pol.resolucao_de_conflito == "coordenador"


def test_politica_colaborativa():
    proj = {"collaboration_mode": MODALIDADE_COLABORATIVA}
    pol = politica_de(proj)

    assert pol.corpus_compartilhado is True
    assert pol.protocolo_coeditavel is True
    assert pol.revisores_por_estudo == 1
    assert pol.triagem_cega is False
    assert pol.extracao_cega is False


def test_politica_cega_por_pares():
    proj = {
        "collaboration_mode": MODALIDADE_CEGA_POR_PARES,
        "reviewers_per_paper": 2,
        "conflict_resolution": "coordenador",
    }
    pol = politica_de(proj)

    assert pol.corpus_compartilhado is True
    assert pol.protocolo_coeditavel is True
    assert pol.revisores_por_estudo == 2
    assert pol.triagem_cega is True
    assert pol.extracao_cega is True
    assert pol.resolucao_de_conflito == "coordenador"


def test_politica_cega_por_pares_minimo_dois_revisores():
    # Se configurado 1 revisor por engano na modalidade cega, deve forçar no mínimo 2
    proj = {
        "collaboration_mode": MODALIDADE_CEGA_POR_PARES,
        "reviewers_per_paper": 1,
    }
    pol = politica_de(proj)
    assert pol.revisores_por_estudo == 2


def test_politica_default_quando_vazio_ou_desconhecido():
    assert politica_de({}).corpus_compartilhado is False
    assert politica_de({"collaboration_mode": "invalido"}).corpus_compartilhado is False
