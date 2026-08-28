#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários do Serviço de Deduplicação de 3 passes e Persistência em Lote."""

from app.harvesters.base import RawPaperRecord
from app.infrastructure.persistence.models import ProjectModel, PaperModel
from app.services.dedup_service import DeduplicationService, generate_blocking_key
from tests.conftest import OWNER_ID_TESTE


def test_generate_blocking_key():
    assert generate_blocking_key("politicas publicas e desenvolvimento regional") == "politicas publicas desenvolvimento regional"
    assert generate_blocking_key("a study on regional clusters and innovation") == "study regional clusters and"
    assert generate_blocking_key("curto") == "curto"
    assert generate_blocking_key("") == ""


def test_doi_exact_deduplication(db_session):
    dedup = DeduplicationService()

    project = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto Teste Dedup", methodology="PRISMA-ScR")
    db_session.add(project)
    db_session.commit()

    # Registro 1
    r1 = RawPaperRecord(
        title="Políticas Públicas e Desenvolvimento Regional",
        authors="Silva, J.",
        year="2024",
        doi="10.1234/reg.2024",
        source_name="SciELO",
    )
    p1, is_new_1 = dedup.process_record(db_session, project.id, r1)
    assert is_new_1 is True
    assert p1.doi == "10.1234/reg.2024"

    # Registro 2 com mesmo DOI mas título ligeiramente diferente
    r2 = RawPaperRecord(
        title="Politicas Publicas e Desenvolvimento Regional Sustentavel",
        authors="Silva, Joao",
        year="2024",
        doi="10.1234/REG.2024",  # Case mismatch
        source_name="OpenAlex",
    )
    p2, is_new_2 = dedup.process_record(db_session, project.id, r2)
    assert is_new_2 is False
    assert p2.id == p1.id  # Mesma entidade unificada!


def test_title_exact_normalized_deduplication(db_session):
    dedup = DeduplicationService()

    project = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto Teste Dedup", methodology="PRISMA-ScR")
    db_session.add(project)
    db_session.commit()

    # Título com acentos e pontuação
    r1 = RawPaperRecord(
        title="Revisão de Escopo: Arranjos Produtivos Locais no Nordeste!",
        authors="Santos, M.",
        year="2023",
        source_name="BDTD",
    )
    p1, is_new_1 = dedup.process_record(db_session, project.id, r1)
    assert is_new_1 is True

    # Título sem acentos e pontuação
    r2 = RawPaperRecord(
        title="Revisao de Escopo Arranjos Produtivos Locais no Nordeste",
        authors="Santos, M.",
        year="2023",
        source_name="OpenAlex",
    )
    p2, is_new_2 = dedup.process_record(db_session, project.id, r2)
    assert is_new_2 is False
    assert p2.id == p1.id


def test_fuzzy_title_deduplication(db_session):
    dedup = DeduplicationService()

    project = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto Teste Dedup", methodology="PRISMA-ScR")
    db_session.add(project)
    db_session.commit()

    # Título com pequena variação de stopwords/ordem
    r1 = RawPaperRecord(
        title="Territorial Governance and Regional Development in Latin America",
        authors="Johnson, K.",
        year="2022",
        source_name="Scopus",
    )
    p1, is_new_1 = dedup.process_record(db_session, project.id, r1)
    assert is_new_1 is True

    r2 = RawPaperRecord(
        title="Territorial Governance and Regional Development of Latin America",
        authors="Johnson, K.",
        year="2022",
        source_name="OpenAlex",
    )
    p2, is_new_2 = dedup.process_record(db_session, project.id, r2)
    assert is_new_2 is False
    assert p2.id == p1.id


def test_process_batch_persistence(db_session):
    dedup = DeduplicationService()

    project = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto Batch", methodology="PRISMA-ScR")
    db_session.add(project)
    db_session.commit()

    batch = [
        RawPaperRecord(
            title="Estudo 1: Inovação Territorial",
            authors="Autor A",
            year="2023",
            source_name="BDTD",
            advisor="Prof. Orientador 1",
        ),
        RawPaperRecord(
            title="Estudo 2: Políticas Urbanas",
            authors="Autor B",
            year="2024",
            source_name="SciELO",
            journal="Revista Brasileira de Planejamento",
        ),
        RawPaperRecord(
            title="Estudo 1: Inovação Territorial",  # Duplicata exata no mesmo lote
            authors="Autor A",
            year="2023",
            source_name="OpenAlex",
        ),
    ]

    new_c, dup_c, summaries = dedup.process_batch(db_session, project.id, batch)
    assert new_c == 2
    assert dup_c == 1
    assert len(summaries) == 3

    # Verificar dados no banco
    papers = db_session.query(PaperModel).filter(PaperModel.project_id == project.id).all()
    assert len(papers) == 2
    p1 = next(p for p in papers if "Inovação Territorial" in p.title)
    assert p1.advisor == "Prof. Orientador 1"
    assert p1.blocking_key is not None
