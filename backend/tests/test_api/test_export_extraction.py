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

    # 8. Testar endpoints de manipulação de PDF (Upload, Texto, Download URL, Deleção)
    sample_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<>>\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n212\n%%EOF"
    
    # 8.1 Upload de PDF
    upload_res = await async_client.post(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}/extraction/pdf/upload",
        files={"file": ("test_artigo.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["status"] == "uploaded"

    # 8.2 Obter arquivo do PDF
    get_pdf_res = await async_client.get(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}/extraction/pdf"
    )
    assert get_pdf_res.status_code == 200
    assert get_pdf_res.headers["content-type"] == "application/pdf"

    # 8.3 Atualizar download URL
    patch_url_res = await async_client.patch(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}/extraction/download-url",
        json={"download_url": "https://exemplo.org/novo_link.pdf"},
    )
    assert patch_url_res.status_code == 200
    assert patch_url_res.json()["download_url"] == "https://exemplo.org/novo_link.pdf"

    # 8.4 Deletar PDF
    del_pdf_res = await async_client.delete(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}/extraction/pdf"
    )
    assert del_pdf_res.status_code == 200
    assert del_pdf_res.json()["status"] == "deleted"

