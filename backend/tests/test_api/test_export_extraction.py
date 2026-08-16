#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes dos endpoints de Extração de Dados e Exportação (Excel, BibTeX, PRISMA)."""

import pytest
from app.infrastructure.persistence.models import CriterionModel, ExtractionQuestionModel, PaperModel, ProjectModel, ProtocolModel


@pytest.mark.anyio
async def test_extraction_and_export_flow(async_client, db_session):
    # 1. Setup projeto com protocolo e critérios
    proj = ProjectModel(title="Revisão Export Teste", methodology="PRISMA-P")
    db_session.add(proj)
    db_session.flush()

    proto = ProtocolModel(project_id=proj.id, objective="Objetivo de teste")
    db_session.add(proto)
    db_session.flush()

    q1 = ExtractionQuestionModel(protocol_id=proto.id, text="Qual o modelo de ML?", order=0)
    db_session.add(q1)
    db_session.flush()

    paper = PaperModel(
        project_id=proj.id,
        title="Deep Learning in Healthcare",
        authors="Taylor, B.",
        year="2024",
        doi="10.5678/dl.2024",
        abstract="We propose a CNN model.",
        decision="Incluído",
    )
    db_session.add(paper)
    db_session.commit()

    # 2. Testar salvar resposta de extração manualmente
    save_ans_res = await async_client.put(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}/extraction",
        json={q1.id: "Modelo CNN ResNet-50 com 94% de acurácia"},
    )
    assert save_ans_res.status_code == 200

    # 3. Testar consultar respostas
    get_ans_res = await async_client.get(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}/extraction"
    )
    assert get_ans_res.status_code == 200
    data = get_ans_res.json()
    assert len(data["answers"]) == 1
    assert data["answers"][0]["answer"] == "Modelo CNN ResNet-50 com 94% de acurácia"

    # 4. Testar exportação PRISMA metrics
    prisma_res = await async_client.get(f"/api/v1/projects/{proj.id}/export/prisma")
    assert prisma_res.status_code == 200
    p_data = prisma_res.json()
    assert p_data["included"]["studies_included_in_synthesis"] == 1
    assert p_data["screening"]["records_screened"] == 1

    # 5. Testar exportação BibTeX
    bib_res = await async_client.get(f"/api/v1/projects/{proj.id}/export/bibtex")
    assert bib_res.status_code == 200
    assert "@article{" in bib_res.text
    assert "Deep Learning in Healthcare" in bib_res.text

    # 6. Testar exportação Excel (.xlsx)
    excel_res = await async_client.get(f"/api/v1/projects/{proj.id}/export/excel")
    assert excel_res.status_code == 200
    assert len(excel_res.content) > 1000  # Conteúdo binário da planilha
