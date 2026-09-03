#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes da Fase 2 de Bibliometria — Enriquecimento OpenAlex / Crossref (doc 48 §4, doc 49)."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibAuthorshipModel,
    BibEnrichmentModel,
    BibKeywordModel,
    BibReferenceModel,
    BibTopicModel,
    BibWorkMetaModel,
    PaperModel,
    ProjectModel,
)
from app.services.bibliometria.enriquecimento import (
    ServicoDeEnriquecimento,
    extrair_metadados_crossref,
    extrair_metadados_openalex,
    normalizar_doi,
)
from app.services.insights_service import get_project_insights
from tests.conftest import OWNER_ID_TESTE



SAMPLE_OPENALEX_WORK = {
    "id": "https://openalex.org/W2741809807",
    "doi": "https://doi.org/10.1016/j.respol.2020.103980",
    "title": "Regional innovation systems and sustainability transitions",
    "publication_year": 2020,
    "cited_by_count": 42,
    "referenced_works_count": 3,
    "referenced_works": [
        "https://openalex.org/W1111111111",
        "https://openalex.org/W2222222222",
        "https://openalex.org/W3333333333",
    ],
    "type": "article",
    "language": "en",
    "open_access": {
        "is_oa": True,
        "oa_status": "gold",
    },
    "authorships": [
        {
            "author_position": "first",
            "author": {
                "id": "https://openalex.org/A5000000001",
                "display_name": "Maria Silva",
            },
            "institutions": [
                {
                    "id": "https://openalex.org/I12345678",
                    "display_name": "Universidade Federal de Santa Catarina",
                    "ror": "https://ror.org/012345678",
                    "country_code": "BR",
                }
            ],
            "countries": ["BR"],
        },
        {
            "author_position": "last",
            "author": {
                "id": "https://openalex.org/A5000000002",
                "display_name": "John Doe",
            },
            "institutions": [
                {
                    "id": "https://openalex.org/I87654321",
                    "display_name": "University of Cambridge",
                    "ror": "https://ror.org/087654321",
                    "country_code": "GB",
                }
            ],
            "countries": ["GB"],
        },
    ],
    "topics": [
        {
            "id": "https://openalex.org/T10123",
            "display_name": "Regional Innovation and Policy",
            "score": 0.98,
            "subfield": {"id": 1405},
        }
    ],
    "keywords": [
        {"keyword": "regional development", "display_name": "regional development", "score": 0.85},
        {"keyword": "smart specialization", "display_name": "smart specialization", "score": 0.78},
    ],
}

SAMPLE_CROSSREF_WORK = {
    "DOI": "10.1007/s11187-021-00500-1",
    "title": ["Territorial innovation models and governance"],
    "is-referenced-by-count": 15,
    "references-count": 2,
    "type": "journal-article",
    "language": "en",
    "author": [
        {
            "given": "Carlos",
            "family": "Pereira",
            "affiliation": [{"name": "Universidade de São Paulo"}],
        }
    ],
    "reference": [
        {"key": "ref1", "DOI": "10.1016/j.respol.2018.01.001"},
        {"key": "ref2", "DOI": "10.1080/00343404.2019.1599843"},
    ],
    "subject": ["Economics", "Regional Science"],
}


def test_normalizar_doi():
    assert normalizar_doi("https://doi.org/10.1016/j.respol.2020.103980") == "10.1016/j.respol.2020.103980"
    assert normalizar_doi("http://dx.doi.org/10.1016/j.respol.2020.103980") == "10.1016/j.respol.2020.103980"
    assert normalizar_doi("doi: 10.1016/j.respol.2020.103980 ") == "10.1016/j.respol.2020.103980"
    assert normalizar_doi("10.1016/j.respol.2020.103980") == "10.1016/j.respol.2020.103980"
    assert normalizar_doi("") == ""
    assert normalizar_doi(None) == ""


def test_extrair_metadados_openalex():
    meta, authors, refs, topics, kws = extrair_metadados_openalex(
        SAMPLE_OPENALEX_WORK, paper_id="p-001", enrichment_id="enr-001"
    )

    assert meta.paper_id == "p-001"
    assert meta.enrichment_id == "enr-001"
    assert meta.provider == "openalex"
    assert meta.cited_by_count == 42
    assert meta.referenced_works_count == 3
    assert meta.is_oa is True
    assert meta.oa_status == "gold"
    assert "Regional innovation systems" in meta.raw

    assert len(authors) == 2
    assert authors[0].author_name == "Maria Silva"
    assert authors[0].institution_name == "Universidade Federal de Santa Catarina"
    assert authors[0].institution_ror == "https://ror.org/012345678"
    assert authors[0].country == "BR"

    assert authors[1].author_name == "John Doe"
    assert authors[1].institution_name == "University of Cambridge"
    assert authors[1].country == "GB"

    assert len(refs) == 3
    assert refs[0].citing_paper_id == "p-001"
    assert refs[0].cited_external_id == "https://openalex.org/W1111111111"

    assert len(topics) == 1
    assert topics[0].topic_name == "Regional Innovation and Policy"
    assert topics[0].score == 0.98

    assert len(kws) == 2
    assert kws[0].term == "regional development"
    assert kws[1].term == "smart specialization"


def test_extrair_metadados_crossref():
    meta, authors, refs, topics, kws = extrair_metadados_crossref(
        SAMPLE_CROSSREF_WORK, paper_id="p-002", enrichment_id="enr-002"
    )

    assert meta.paper_id == "p-002"
    assert meta.provider == "crossref"
    assert meta.cited_by_count == 15
    assert meta.referenced_works_count == 2
    assert len(authors) == 1
    assert authors[0].author_name == "Carlos Pereira"
    assert authors[0].institution_name == "Universidade de São Paulo"
    assert len(refs) == 2
    assert refs[0].cited_doi == "10.1016/j.respol.2018.01.001"
    assert len(kws) == 2
    assert kws[0].term == "Economics"


@pytest.mark.anyio
async def test_enriquecimento_lote_openalex_persiste_tudo(db_session):
    """Verifica que o serviço enriquece papers com DOI e persiste todos os modelos relacionais."""
    pid = "proj-enr-1"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Teste Enriquecimento", methodology="PRISMA"))
    db_session.add(
        PaperModel(
            id="paper-101",
            project_id=pid,
            title="Paper A",
            doi="10.1016/j.respol.2020.103980",
            decision=Decision.INCLUDED.value,
        )
    )
    db_session.add(
        PaperModel(
            id="paper-102",
            project_id=pid,
            title="Paper Sem DOI",
            doi=None,
            decision=Decision.INCLUDED.value,
        )
    )
    db_session.commit()

    servico = ServicoDeEnriquecimento()

    with patch.object(
        servico, "_consultar_openalex_lote", new_callable=AsyncMock
    ) as mock_oa, patch.object(
        servico, "_consultar_crossref_individual", new_callable=AsyncMock
    ) as mock_cr:
        mock_oa.return_value = [SAMPLE_OPENALEX_WORK]

        eventos = []
        async def _progresso(e):
            eventos.append(e)

        enr = await servico.executar_enriquecimento(
            db_session, pid, on_progress=_progresso, pausa_entre_lotes=0.0
        )

        assert enr.status == "concluido"
        assert enr.n_consulted == 1  # Apenas 1 tinha DOI
        assert enr.n_found == 1

        # Verificar persistência
        meta = db_session.query(BibWorkMetaModel).filter(BibWorkMetaModel.paper_id == "paper-101").first()
        assert meta is not None
        assert meta.cited_by_count == 42
        assert meta.provider == "openalex"

        authors = (
            db_session.query(BibAuthorshipModel)
            .filter(BibAuthorshipModel.paper_id == "paper-101")
            .order_by(BibAuthorshipModel.position)
            .all()
        )
        assert len(authors) == 2
        assert authors[0].institution_name == "Universidade Federal de Santa Catarina"
        assert authors[0].institution_ror == "https://ror.org/012345678"

        refs = db_session.query(BibReferenceModel).filter(BibReferenceModel.citing_paper_id == "paper-101").all()
        assert len(refs) == 3

        topics = db_session.query(BibTopicModel).filter(BibTopicModel.paper_id == "paper-101").all()
        assert len(topics) == 1
        assert topics[0].topic_name == "Regional Innovation and Policy"

        kws = db_session.query(BibKeywordModel).filter(BibKeywordModel.paper_id == "paper-101").all()
        assert len(kws) == 2

        assert any(e["type"] == "enrichment_completed" for e in eventos)


@pytest.mark.anyio
async def test_enriquecimento_e_retomavel_e_nao_reprocessa_existentes(db_session):
    """Garante que artigos já enriquecidos não são reconsultados."""
    pid = "proj-enr-2"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Retomavel", methodology="PRISMA"))
    db_session.add(
        PaperModel(
            id="paper-201",
            project_id=pid,
            title="Paper Ja Enriquecido",
            doi="10.1016/j.respol.2020.103980",
            decision=Decision.INCLUDED.value,
        )
    )
    db_session.add(
        PaperModel(
            id="paper-202",
            project_id=pid,
            title="Paper Pendente",
            doi="10.1007/s11187-021-00500-1",
            decision=Decision.INCLUDED.value,
        )
    )
    # Simula paper-201 já existente em bib_work_meta
    db_session.add(
        BibWorkMetaModel(
            paper_id="paper-201",
            provider="openalex",
            cited_by_count=10,
            raw="{}",
        )
    )
    db_session.commit()

    servico = ServicoDeEnriquecimento()

    with patch.object(
        servico, "_consultar_openalex_lote", new_callable=AsyncMock
    ) as mock_oa:
        mock_oa.return_value = [
            {
                "id": "https://openalex.org/W9999",
                "doi": "https://doi.org/10.1007/s11187-021-00500-1",
                "cited_by_count": 5,
                "authorships": [],
            }
        ]

        enr = await servico.executar_enriquecimento(db_session, pid, pausa_entre_lotes=0.0)

        assert enr.n_consulted == 1  # Apenas paper-202 foi consultado
        assert enr.n_found == 1
        assert mock_oa.call_count == 1
        # Confere que o lote enviado ao OpenAlex continha apenas o DOI pendente
        dois_consultados = mock_oa.call_args[0][1]
        assert dois_consultados == ["10.1007/s11187-021-00500-1"]


@pytest.mark.anyio
async def test_fallback_crossref_para_dois_ausentes_no_openalex(db_session):
    """Verifica que quando OpenAlex não encontra um DOI, o Crossref é consultado com sucesso."""
    pid = "proj-enr-3"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Fallback", methodology="PRISMA"))
    db_session.add(
        PaperModel(
            id="paper-301",
            project_id=pid,
            title="Paper Crossref Only",
            doi="10.1007/s11187-021-00500-1",
            decision=Decision.INCLUDED.value,
        )
    )
    db_session.commit()

    servico = ServicoDeEnriquecimento()

    with patch.object(
        servico, "_consultar_openalex_lote", new_callable=AsyncMock
    ) as mock_oa, patch.object(
        servico, "_consultar_crossref_individual", new_callable=AsyncMock
    ) as mock_cr:
        mock_oa.return_value = []  # OpenAlex não encontrou
        mock_cr.return_value = SAMPLE_CROSSREF_WORK  # Crossref encontrou

        enr = await servico.executar_enriquecimento(db_session, pid, pausa_entre_lotes=0.0)

        assert enr.n_consulted == 1
        assert enr.n_found == 1
        assert mock_cr.call_count == 1

        meta = db_session.query(BibWorkMetaModel).filter(BibWorkMetaModel.paper_id == "paper-301").first()
        assert meta is not None
        assert meta.provider == "crossref"
        assert meta.cited_by_count == 15


def test_obter_situacao_calcula_cobertura_correta(db_session):
    """Testa o cálculo de situação e porcentagem de cobertura."""
    pid = "proj-enr-sit"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Situacao", methodology="PRISMA"))
    db_session.add(PaperModel(id="p1", project_id=pid, title="P1", doi="10.1/a"))
    db_session.add(PaperModel(id="p2", project_id=pid, title="P2", doi="10.1/b"))
    db_session.add(PaperModel(id="p3", project_id=pid, title="P3", doi=None))

    db_session.add(BibWorkMetaModel(paper_id="p1", provider="openalex", cited_by_count=2, raw="{}"))
    db_session.commit()

    servico = ServicoDeEnriquecimento()
    sit = servico.obter_situacao(db_session, pid)

    assert sit["total_papers"] == 3
    assert sit["papers_with_doi"] == 2
    assert sit["papers_enriched"] == 1
    assert sit["papers_pending"] == 1
    assert sit["coverage_pct"] == 33.3


def test_top_institutions_prioriza_bib_authorships(db_session):
    """Verifica que get_project_insights lê as afiliações reais de bib_authorships (fecha B-01)."""
    pid = "proj-enr-inst"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Inst", methodology="PRISMA"))
    db_session.add(
        PaperModel(
            id="p-inst-1",
            project_id=pid,
            title="Estudo Regional",
            institution="SciELO",  # Nome do coletor que antes poluía o ranking
            decision=Decision.INCLUDED.value,
        )
    )
    # Afiliação real enriquecida pelo OpenAlex
    db_session.add(
        BibAuthorshipModel(
            paper_id="p-inst-1",
            position=0,
            author_name="Maria Silva",
            institution_name="Universidade Federal do Paraná",
            institution_ror="https://ror.org/ufpr",
            country="BR",
        )
    )
    db_session.commit()

    insights = get_project_insights(db_session, pid, decision=Decision.INCLUDED.value)
    top_inst = insights["top_institutions"]

    assert len(top_inst) == 1
    assert top_inst[0]["name"] == "Universidade Federal do Paraná"
    assert top_inst[0]["count"] == 1
    # Garante que "SciELO" não aparece
    assert not any("SciELO" in item["name"] for item in top_inst)
