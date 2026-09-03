#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes do Motor de Grafos Bibliométricos e Layout Determinístico (doc 48 §8, §12, doc 49 Fase 6)."""

import json
import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibAuthorshipModel,
    BibGrafoModel,
    BibKeywordModel,
    BibReferenceModel,
    PaperModel,
    ProjectModel,
)
from app.services.bibliometria.grafos import (
    ServicoDeGrafos,
    calcular_forca_aresta,
)
from tests.conftest import OWNER_ID_TESTE


def test_normalizacoes_forca_associacao_jaccard_cosseno():
    # c_ij = 4, c_i = 10, c_j = 8, total = 50
    # Jaccard: 4 / (10 + 8 - 4) = 4 / 14 = 0.2857
    jaccard = calcular_forca_aresta(c_ij=4, c_i=10, c_j=8, total_coocorrencias=50, normalizacao="jaccard")
    assert jaccard == round(4 / 14, 4)

    # Cosine: 4 / sqrt(80) = 4 / 8.94427 = 0.4472
    cosine = calcular_forca_aresta(c_ij=4, c_i=10, c_j=8, total_coocorrencias=50, normalizacao="cosine")
    assert cosine == round(4 / (80 ** 0.5), 4)

    # Association strength: (4 * 2 * 50) / (10 * 8) = 400 / 80 = 5.0
    assoc = calcular_forca_aresta(c_ij=4, c_i=10, c_j=8, total_coocorrencias=50, normalizacao="association_strength")
    assert assoc == 5.0


def test_layout_e_identico_com_a_mesma_semente(db_session):
    """Garante determinismo do layout espacial (doc 48 §8.4): duas execuções com a mesma semente dão as mesmas coordenadas."""
    pid = "proj-grafo-det"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Grafo Det", methodology="PRISMA"))

    p1 = PaperModel(id="pg-1", project_id=pid, title="Estudo APL 1", authors="Silva, A.; Souza, B.", decision=Decision.INCLUDED.value)
    p2 = PaperModel(id="pg-2", project_id=pid, title="Estudo APL 2", authors="Souza, B.; Santos, C.", decision=Decision.INCLUDED.value)
    p3 = PaperModel(id="pg-3", project_id=pid, title="Estudo APL 3", authors="Silva, A.; Santos, C.", decision=Decision.INCLUDED.value)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    servico = ServicoDeGrafos()

    # Execução 1 com semente 42
    g1 = servico.construir_grafo(db_session, project_id=pid, network_type="coautoria", semente=42)
    # Execução 2 com semente 42
    g2 = servico.construir_grafo(db_session, project_id=pid, network_type="coautoria", semente=42)

    coords1 = json.loads(g1.coordinates)
    coords2 = json.loads(g2.coordinates)

    assert coords1 == coords2
    assert len(coords1) == 3
    for autor, xy in coords1.items():
        assert "x" in xy and "y" in xy


def test_quatro_redes_coautoria_termos_acoplamento_cocitacao(db_session):
    """Testa geração válida das 4 redes bibliométricas."""
    pid = "proj-4-redes"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto 4 Redes", methodology="PRISMA"))

    p1 = PaperModel(id="p4-1", project_id=pid, title="Políticas Públicas Regionais", authors="Silva, João; Oliveira, Maria", year="2020", decision=Decision.INCLUDED.value)
    p2 = PaperModel(id="p4-2", project_id=pid, title="Inovação e APLs", authors="Oliveira, Maria; Pereira, Lucas", year="2021", decision=Decision.INCLUDED.value)
    db_session.add_all([p1, p2])

    # Palavras-chave
    kw1 = BibKeywordModel(paper_id=p1.id, term="desenvolvimento regional", source="author")
    kw2 = BibKeywordModel(paper_id=p1.id, term="politicas publicas", source="author")
    kw3 = BibKeywordModel(paper_id=p2.id, term="desenvolvimento regional", source="author")
    kw4 = BibKeywordModel(paper_id=p2.id, term="inovacao", source="author")
    db_session.add_all([kw1, kw2, kw3, kw4])

    # Referências (para acoplamento e cocitação)
    ref1 = BibReferenceModel(citing_paper_id=p1.id, cited_doi="10.1000/ref-x")
    ref2 = BibReferenceModel(citing_paper_id=p1.id, cited_doi="10.1000/ref-y")
    ref3 = BibReferenceModel(citing_paper_id=p2.id, cited_doi="10.1000/ref-x")
    db_session.add_all([ref1, ref2, ref3])
    db_session.commit()

    servico = ServicoDeGrafos()

    # 1. Coautoria
    g_aut = servico.construir_grafo(db_session, project_id=pid, network_type="coautoria")
    assert len(json.loads(g_aut.nodes)) == 3
    assert len(json.loads(g_aut.edges)) == 2

    # 2. Termos
    g_ter = servico.construir_grafo(db_session, project_id=pid, network_type="coocorrencia_termos")
    assert len(json.loads(g_ter.nodes)) >= 2

    # 3. Acoplamento Bibliográfico
    g_acop = servico.construir_grafo(db_session, project_id=pid, network_type="acoplamento_bibliografico")
    assert len(json.loads(g_acop.nodes)) == 2
    # p1 e p2 compartilham a ref-x
    assert len(json.loads(g_acop.edges)) == 1

    # 4. Cocitação
    g_cocit = servico.construir_grafo(db_session, project_id=pid, network_type="cocitacao")
    assert len(json.loads(g_cocit.nodes)) == 2
    assert len(json.loads(g_cocit.edges)) == 1


def test_acoplamento_acima_do_teto_e_recusado_com_explicacao(db_session):
    pid = "proj-teto-acop"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Teto", methodology="PRISMA"))

    # Criar 5 papers simulando limite estrito de 4
    papers = [
        PaperModel(id=f"p-teto-{i}", project_id=pid, title=f"Estudo {i}", decision=Decision.INCLUDED.value)
        for i in range(5)
    ]
    db_session.add_all(papers)
    db_session.commit()

    servico = ServicoDeGrafos()
    with pytest.raises(ValueError, match="excede o teto computacional seguro"):
        servico.extrair_rede_acoplamento(db_session, papers=papers, max_docs=4)


def test_exportacao_graphml_contem_coordenadas_e_clusters(db_session):
    pid = "proj-graphml"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto GraphML", methodology="PRISMA"))
    p1 = PaperModel(id="pgml-1", project_id=pid, title="Estudo A", authors="Autor A; Autor B", decision=Decision.INCLUDED.value)
    db_session.add(p1)
    db_session.commit()

    servico = ServicoDeGrafos()
    grafo = servico.construir_grafo(db_session, project_id=pid, network_type="coautoria", semente=42)

    xml_str = servico.exportar_graphml(grafo)
    assert '<?xml' in xml_str or '<graphml' in xml_str
    assert 'Autor A' in xml_str
    assert 'cluster' in xml_str
    assert 'weight' in xml_str
