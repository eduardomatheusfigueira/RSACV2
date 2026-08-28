#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes para o fluxo de deduplicação e geração do Relatório de Deduplicação (Revsist V1 parity)."""

import pytest
from app.infrastructure.persistence.models import PaperModel, PaperSourceModel, ProjectModel
from app.services.dedup_service import DeduplicationService
from tests.conftest import OWNER_ID_TESTE


def test_run_project_deduplication_and_report_generation(db_session):
    dedup = DeduplicationService()

    # 1. Criar projeto
    project = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto Deduplicação Relatório", methodology="PRISMA-ScR")
    db_session.add(project)
    db_session.commit()

    # 2. Inserir papers brutos (com duplicatas por DOI e por título)
    p1 = PaperModel(
        project_id=project.id,
        title="Desenvolvimento Regional e Arranjos Produtivos no Nordeste",
        title_normalized=dedup.normalize_title("Desenvolvimento Regional e Arranjos Produtivos no Nordeste"),
        blocking_key=dedup.generate_blocking_key(dedup.normalize_title("Desenvolvimento Regional e Arranjos Produtivos no Nordeste")),
        authors="Silva, João",
        year="2023",
        doi="10.1590/reg.2023.001",
        abstract="Resumo curto da BDTD.",
    )
    db_session.add(p1)
    db_session.flush()
    db_session.add(PaperSourceModel(paper_id=p1.id, source_name="BDTD", source_id="rec_1"))

    # Duplicata com mesmo DOI e resumo mais longo (do SciELO)
    p2 = PaperModel(
        project_id=project.id,
        title="Desenvolvimento regional e arranjos produtivos no nordeste.",
        title_normalized=dedup.normalize_title("Desenvolvimento regional e arranjos produtivos no nordeste."),
        blocking_key=dedup.generate_blocking_key(dedup.normalize_title("Desenvolvimento regional e arranjos produtivos no nordeste.")),
        authors="Silva, J.; Santos, M.",
        year="2023",
        doi="10.1590/reg.2023.001",
        abstract="Resumo expandido e completo da base SciELO com metodologia detalhada.",
        journal="Revista de Economia Regional",
    )
    db_session.add(p2)
    db_session.flush()
    db_session.add(PaperSourceModel(paper_id=p2.id, source_name="SciELO", source_id="rec_2"))

    # Artigo único (OpenAlex)
    p3 = PaperModel(
        project_id=project.id,
        title="Políticas Públicas e Governança Metropolitana",
        title_normalized=dedup.normalize_title("Políticas Públicas e Governança Metropolitana"),
        blocking_key=dedup.generate_blocking_key(dedup.normalize_title("Políticas Públicas e Governança Metropolitana")),
        authors="Oliveira, Carlos",
        year="2024",
        doi="10.1000/182",
        abstract="Estudo sobre governança metropolitana.",
    )
    db_session.add(p3)
    db_session.flush()
    db_session.add(PaperSourceModel(paper_id=p3.id, source_name="OpenAlex", source_id="rec_3"))

    db_session.commit()

    # 3. Executar a deduplicação
    report_res = dedup.run_project_deduplication(db_session, project.id)

    assert report_res["total_raw"] == 3
    assert report_res["total_unique"] == 2
    assert report_res["total_duplicates"] == 1
    assert "RELATÓRIO DE DEDUPLICAÇÃO" in report_res["report_text"]
    assert "Trabalhos únicos após deduplicação: 2" in report_res["report_text"]
    assert "Desenvolvimento regional e arranjos produtivos" in report_res["report_text"]

    # 4. Verificar enriquecimento no paper representativo
    primary = db_session.query(PaperModel).filter(PaperModel.id == p1.id).first()
    assert primary.is_duplicate is False
    assert "Resumo expandido" in primary.abstract
    assert primary.journal == "Revista de Economia Regional"

    # Verificar que p2 foi marcado como duplicata
    dup = db_session.query(PaperModel).filter(PaperModel.id == p2.id).first()
    assert dup.is_duplicate is True
    assert dup.merged_into_id == p1.id
