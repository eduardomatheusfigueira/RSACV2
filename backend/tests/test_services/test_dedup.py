#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários do Serviço de Deduplicação de 3 passes."""

from app.harvesters.base import RawPaperRecord
from app.infrastructure.persistence.models import ProjectModel
from app.services.dedup_service import DeduplicationService


def test_doi_exact_deduplication(db_session):
    dedup = DeduplicationService()

    # Criar projeto no banco de teste
    project = ProjectModel(title="Projeto Teste Dedup", methodology="PRISMA-P")
    db_session.add(project)
    db_session.commit()

    # Registro 1
    r1 = RawPaperRecord(
        title="Inteligência Artificial e Diagnóstico",
        authors="Silva, J.",
        year="2024",
        doi="10.1234/ai.2024",
        source_name="SciELO",
    )
    p1, is_new_1 = dedup.process_record(db_session, project.id, r1)
    assert is_new_1 is True
    assert p1.doi == "10.1234/ai.2024"

    # Registro 2 com mesmo DOI mas título ligeiramente diferente
    r2 = RawPaperRecord(
        title="Inteligencia Artificial & Diagnostico Clinico",
        authors="Silva, Joao",
        year="2024",
        doi="10.1234/AI.2024",  # Case mismatch
        source_name="OpenAlex",
    )
    p2, is_new_2 = dedup.process_record(db_session, project.id, r2)
    assert is_new_2 is False
    assert p2.id == p1.id  # Mesma entidade!


def test_title_exact_normalized_deduplication(db_session):
    dedup = DeduplicationService()

    project = ProjectModel(title="Projeto Teste Dedup", methodology="PRISMA-P")
    db_session.add(project)
    db_session.commit()

    # Título com acentos e pontuação
    r1 = RawPaperRecord(
        title="Revisão Sistemática: Uso de Machine Learning na Saúde!",
        authors="Santos, M.",
        year="2023",
        source_name="BDTD",
    )
    p1, is_new_1 = dedup.process_record(db_session, project.id, r1)
    assert is_new_1 is True

    # Título sem acentos e pontuação
    r2 = RawPaperRecord(
        title="Revisao Sistematica Uso de Machine Learning na Saude",
        authors="Santos, M.",
        year="2023",
        source_name="PubMed",
    )
    p2, is_new_2 = dedup.process_record(db_session, project.id, r2)
    assert is_new_2 is False
    assert p2.id == p1.id


def test_fuzzy_title_deduplication(db_session):
    dedup = DeduplicationService()

    project = ProjectModel(title="Projeto Teste Dedup", methodology="PRISMA-P")
    db_session.add(project)
    db_session.commit()

    # Título com pequena variação de palavras
    r1 = RawPaperRecord(
        title="Deep Learning Methods for Chest X-Ray Disease Classification",
        authors="Johnson, K.",
        year="2022",
        source_name="PubMed",
    )
    p1, is_new_1 = dedup.process_record(db_session, project.id, r1)
    assert is_new_1 is True

    r2 = RawPaperRecord(
        title="Deep Learning Methods for Chest X-Ray Classification of Diseases",
        authors="Johnson, K.",
        year="2022",
        source_name="OpenAlex",
    )
    p2, is_new_2 = dedup.process_record(db_session, project.id, r2)
    assert is_new_2 is False
    assert p2.id == p1.id
