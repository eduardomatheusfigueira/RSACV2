#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes dos Indicadores Bibliométricos de Nível 0 e 1 (doc 48 §7, doc 49 Fase 3)."""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibAuthorshipModel,
    BibWorkMetaModel,
    PaperModel,
    PaperSourceModel,
    ProjectModel,
)
from app.services.bibliometria.indicadores import (
    calcular_acesso_aberto,
    calcular_bradford,
    calcular_cagr,
    calcular_citacoes_e_h,
    calcular_colaboracao,
    calcular_gini,
    calcular_hhi,
    calcular_lotka_com_ks,
    calcular_sobreposicao_fontes,
    obter_indicadores_bibliometricos,
)
from app.services.bibliometria.instantaneo import criar as criar_instantaneo
from tests.conftest import OWNER_ID_TESTE


# ── 1. CAGR & Produção Temporal ─────────────────────────────────────────


def test_cagr_calculo_exato():
    # 2020: 100 artigos, 2022: 121 artigos (10% ao ano, CAGR = 10.0%)
    dados = [(2020, 100), (2021, 110), (2022, 121)]
    res = calcular_cagr(dados)

    assert res["cagr_pct"] == 10.0
    assert res["year_start"] == 2020
    assert res["year_end"] == 2022
    assert res["total_period"] == 331
    assert len(res["series"]) == 3
    assert res["series"][1]["growth_yoy_pct"] == 10.0


def test_cagr_vazio_ou_ano_unico():
    assert calcular_cagr([])["cagr_pct"] is None
    res_um = calcular_cagr([(2022, 50)])
    assert res_um["cagr_pct"] is None
    assert res_um["total_period"] == 50


# ── 2. Lei de Bradford (1934) ──────────────────────────────────────────


def test_bradford_distribuicao_zonas_e_multiplicador():
    # 30 artigos no total -> cada zona deve conter aprox 10 artigos
    periodicos = [
        ("Revista A", 6),  # Zona 1: 6 + 4 = 10
        ("Revista B", 4),
        ("Revista C", 3),  # Zona 2: 3 + 3 + 2 + 2 = 10
        ("Revista D", 3),
        ("Revista E", 2),
        ("Revista F", 2),
        ("Revista G", 1),  # Zona 3: 10 revistas de 1 artigo = 10
        ("Revista H", 1),
        ("Revista I", 1),
        ("Revista J", 1),
        ("Revista K", 1),
        ("Revista L", 1),
        ("Revista M", 1),
        ("Revista N", 1),
        ("Revista O", 1),
        ("Revista P", 1),
    ]
    res = calcular_bradford(periodicos)

    assert res["total_articles"] == 30
    assert res["total_journals"] == 16
    assert len(res["zones"]) == 3

    z1 = res["zones"][0]
    z2 = res["zones"][1]
    z3 = res["zones"][2]

    assert z1["total_articles"] == 10
    assert z1["n_journals"] == 2

    assert z2["total_articles"] == 10
    assert z2["n_journals"] == 4

    assert z3["total_articles"] == 10
    assert z3["n_journals"] == 10

    # Multiplicador k: k1 = 4/2 = 2.0, k2 = 10/4 = 2.5 -> k_médio = 2.25
    assert res["k_multiplier"] == 2.25
    assert res["formula_ratio"] == "2 : 4 : 10"


def test_bradford_vazio():
    res = calcular_bradford([])
    assert res["total_journals"] == 0
    assert res["k_multiplier"] is None


# ── 3. Lei de Lotka e Teste de Kolmogorov-Smirnov ───────────────────────


def test_lotka_mle_recupera_expoente_power_law():
    """Corpus sintético com distribuição de potência clássica f(x) ~ x^(-2.0)."""
    # 100 autores com 1 artigo, 25 com 2 artigos, 11 com 3 artigos, 6 com 4 artigos
    autores_prod = [1] * 100 + [2] * 25 + [3] * 11 + [4] * 6
    res = calcular_lotka_com_ks(autores_prod)

    assert res["n_authors"] == 142
    # O expoente deve ficar próximo de 2.0 (tolerância de ajuste discreto)
    assert 1.8 <= res["alpha"] <= 2.3
    assert res["is_adherent"] is True
    assert "Aderência aceita" in res["p_verdict"]


def test_lotka_ks_rejeita_distribuicao_nao_power_law():
    """Corpus uniforme artificial (não segue lei de potência)."""
    # 10 autores com 1 artigo, 10 com 2, 10 com 3, ..., 10 com 15 artigos
    autores_prod = []
    for x in range(1, 16):
        autores_prod.extend([x] * 10)

    res = calcular_lotka_com_ks(autores_prod)
    # Teste KS deve rejeitar formalmente a aderência
    assert res["is_adherent"] is False
    assert "Aderência rejeitada" in res["p_verdict"]


# ── 4. Colaboração (Subramanyam) ────────────────────────────────────────


def test_subramanyam_e_colaboracao():
    # 2 artigos com 1 autor, 8 artigos com 2 ou mais autores -> C = 8 / 10 = 0.8
    autores_por_artigo = [1, 1, 2, 3, 2, 4, 2, 3, 2, 2]
    res = calcular_colaboracao(autores_por_artigo)

    assert res["total_articles"] == 10
    assert res["single_author_articles"] == 2
    assert res["multi_author_articles"] == 8
    assert res["subramanyam_index"] == 0.8
    assert res["avg_authors_per_paper"] == 2.2
    assert res["max_authors"] == 4


# ── 5. Gini e HHI ───────────────────────────────────────────────────────


def test_gini_e_hhi():
    # Igualdade perfeita -> Gini = 0.0
    assert calcular_gini([5, 5, 5, 5]) == 0.0

    # Desigualdade alta -> Gini alto (> 0.6)
    assert calcular_gini([1, 1, 1, 100]) > 0.6

    # HHI para 4 periódicos com 25% cada -> 4 * 625 = 2500.0
    assert calcular_hhi([10, 10, 10, 10]) == 2500.0

    # Monopólio (1 periódico com 100%) -> HHI = 10000.0
    assert calcular_hhi([50]) == 10000.0


# ── 6. Sobreposição de Fontes ───────────────────────────────────────────


def test_sobreposicao_fontes():
    artigos_fontes = [
        ["BDTD"],
        ["BDTD", "SciELO"],
        ["SciELO"],
        ["SciELO", "OpenAlex", "Scopus"],
        ["OpenAlex"],
    ]
    res = calcular_sobreposicao_fontes(artigos_fontes)

    assert res["total_papers"] == 5
    assert res["exclusive_counts"]["BDTD"] == 1
    assert res["exclusive_counts"]["SciELO"] == 1
    assert res["exclusive_counts"]["OpenAlex"] == 1
    # Matriz de sobreposição BDTD x SciELO = 1
    assert res["overlap_matrix"]["BDTD"]["SciELO"] == 1


# ── 7. Citações e Índice h ──────────────────────────────────────────────


def test_citacoes_e_indice_h():
    # Citações: [12, 10, 8, 5, 4, 3, 1]
    # Artigos com c >= 1: 7
    # Artigos com c >= 2: 6
    # Artigos com c >= 3: 6
    # Artigos com c >= 4: 5
    # Artigos com c >= 5: 4 (4 artigos têm >= 4 citações) -> h = 4
    citacoes = [12, 10, 8, 5, 4, 3, 1]
    res = calcular_citacoes_e_h(citacoes)

    assert res["h_index"] == 4
    assert res["total_citations"] == 43
    assert res["max_citations"] == 12
    assert res["median_citations"] == 5
    assert len(res["citation_bands"]) == 5


# ── 8. Acesso Aberto ────────────────────────────────────────────────────


def test_acesso_aberto_metrics():
    oa_data = [
        {"is_oa": True, "oa_status": "gold"},
        {"is_oa": True, "oa_status": "gold"},
        {"is_oa": True, "oa_status": "green"},
        {"is_oa": False, "oa_status": "closed"},
    ]
    res = calcular_acesso_aberto(oa_data)

    assert res["total_evaluated"] == 4
    assert res["open_access_count"] == 3
    assert res["open_access_pct"] == 75.0
    assert any(item["status"] == "gold" and item["count"] == 2 for item in res["by_status"])


# ── 9. Integração com Banco de Dados e Instantâneos ─────────────────────


def test_obter_indicadores_bibliometricos_integracao_db(db_session):
    pid = "proj-indicadores-1"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Indicadores", methodology="PRISMA"))

    # Criar 4 artigos
    p1 = PaperModel(
        id="p-ind-1",
        project_id=pid,
        title="Estudo A",
        authors="Silva, M.; Pereira, C.",
        journal="Revista Brasileira de Desenvolvimento Regional",
        year="2021",
        decision=Decision.INCLUDED.value,
    )
    p2 = PaperModel(
        id="p-ind-2",
        project_id=pid,
        title="Estudo B",
        authors="Silva, M.",
        journal="Revista Brasileira de Desenvolvimento Regional",
        year="2022",
        decision=Decision.INCLUDED.value,
    )
    p3 = PaperModel(
        id="p-ind-3",
        project_id=pid,
        title="Estudo C",
        authors="Souza, R.",
        journal="Revista de Economia Regional",
        year="2022",
        decision=Decision.INCLUDED.value,
    )
    p4 = PaperModel(
        id="p-ind-4",
        project_id=pid,
        title="Estudo Excluído",
        authors="Santos, J.",
        year="2023",
        decision=Decision.EXCLUDED.value,
    )
    db_session.add_all([p1, p2, p3, p4])

    # Metadados de citação
    db_session.add(BibWorkMetaModel(paper_id="p-ind-1", cited_by_count=15, is_oa=True, oa_status="gold", raw="{}"))
    db_session.add(BibWorkMetaModel(paper_id="p-ind-2", cited_by_count=8, is_oa=False, oa_status="closed", raw="{}"))
    db_session.add(BibWorkMetaModel(paper_id="p-ind-3", cited_by_count=2, is_oa=True, oa_status="hybrid", raw="{}"))

    # Afiliação de p1
    db_session.add(
        BibAuthorshipModel(
            paper_id="p-ind-1",
            position=0,
            author_name="Silva, M.",
            institution_name="Universidade Federal de Santa Catarina",
            institution_ror="https://ror.org/ufsc",
            country="BR",
        )
    )
    # Fontes
    db_session.add(PaperSourceModel(paper_id="p-ind-1", source_name="SciELO", source_id="1"))
    db_session.add(PaperSourceModel(paper_id="p-ind-1", source_name="BDTD", source_id="2"))
    db_session.add(PaperSourceModel(paper_id="p-ind-2", source_name="SciELO", source_id="3"))
    db_session.commit()

    # Cálculo filtrado por Incluído
    ind = obter_indicadores_bibliometricos(db_session, pid, decision=Decision.INCLUDED.value)

    assert ind["total_papers"] == 3
    assert ind["production_temporal"]["total_period"] == 3
    assert ind["bradford"]["total_journals"] == 2
    assert ind["citations"]["h_index"] == 2  # 15, 8, 2 -> 2 artigos têm >= 2 citações
    assert ind["open_access"]["open_access_count"] == 2
    assert len(ind["countries"]) == 1
    assert ind["countries"][0]["country"] == "BR"
