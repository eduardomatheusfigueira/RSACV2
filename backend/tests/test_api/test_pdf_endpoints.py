#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes dos endpoints de aquisição, leitura e lote de PDFs."""

import asyncio

import pytest

from app.api.v1 import extraction as extraction_api
from app.infrastructure.persistence.models import PaperModel, ProjectModel
from app.services.pdf_resolver import ResolutionAttempt
from app.services.pdf_service import PDFAcquisition


def _make_pdf(paginas: list[str]) -> bytes:
    try:
        import pymupdf as fitz
    except ImportError:  # pragma: no cover
        import fitz

    doc = fitz.open()
    for texto in paginas:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(56, 56, 540, 760), texto, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


CORPO = (
    "A governança regional articula consórcios intermunicipais e políticas "
    "territoriais de desenvolvimento em escala sub-regional. "
) * 8


@pytest.fixture
def projeto_com_artigo(db_session, tmp_path):
    extraction_api.pdf_service.storage_dir = tmp_path

    projeto = ProjectModel(title="Revisão PDF", methodology="PRISMA-P")
    db_session.add(projeto)
    db_session.flush()

    paper = PaperModel(
        project_id=projeto.id,
        title="Arranjos produtivos locais e governança territorial",
        authors="Silva, A.",
        year="2024",
        doi="10.1590/apl.2024",
        abstract="Estudo sobre APLs.",
        download_url="https://repositorio.org/handle/1/2",
        decision="Incluído",
    )
    db_session.add(paper)
    db_session.commit()
    return projeto, paper


@pytest.mark.anyio
async def test_status_inicial_sem_pdf(async_client, projeto_com_artigo):
    projeto, paper = projeto_com_artigo
    res = await async_client.get(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf/status"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_pdf"] is False
    assert data["pdf_status"] == "ausente"
    assert data["attempts"] == []


@pytest.mark.anyio
async def test_acquire_sucesso_persiste_procedencia(
    async_client, db_session, projeto_com_artigo, monkeypatch, tmp_path
):
    projeto, paper = projeto_com_artigo
    destino = tmp_path / f"{paper.id}.pdf"
    destino.write_bytes(_make_pdf([f"METODOLOGIA\n\n137 municípios.\n\n{CORPO}"]))

    async def fake_acquire(project_id, paper_id, ref, client=None):
        assert ref.doi == "10.1590/apl.2024"
        return PDFAcquisition(
            success=True,
            file_path=str(destino),
            resolved_url="https://repositorio.org/bitstream/1/2/artigo.pdf",
            strategy="landing",
            label="Metadado citation_pdf_url da página",
            size_bytes=destino.stat().st_size,
            sha256="a" * 64,
            page_count=1,
            text_chars=900,
            attempts=[
                ResolutionAttempt("direct", "https://repositorio.org/handle/1/2", "nao_pdf", "HTML"),
                ResolutionAttempt("landing", str(destino), "ok", "PDF válido"),
            ],
            message="PDF obtido via landing — 1 página(s).",
        )

    monkeypatch.setattr(extraction_api.pdf_service, "acquire_pdf", fake_acquire)

    res = await async_client.post(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf/acquire"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "downloaded"
    assert data["strategy"] == "landing"
    assert len(data["attempts"]) == 2

    db_session.refresh(paper)
    assert paper.pdf_status == "obtido"
    assert paper.pdf_strategy == "landing"
    assert paper.pdf_resolved_url.endswith("artigo.pdf")
    assert paper.pdf_acquired_at is not None


@pytest.mark.anyio
async def test_acquire_falha_devolve_trilha_sem_erro_http(
    async_client, db_session, projeto_com_artigo, monkeypatch
):
    projeto, paper = projeto_com_artigo

    async def fake_acquire(project_id, paper_id, ref, client=None):
        return PDFAcquisition(
            success=False,
            attempts=[
                ResolutionAttempt("direct", "https://editora.com/a", "http_erro", "HTTP 403", 403)
            ],
            message="Conteúdo restrito por assinatura.",
        )

    monkeypatch.setattr(extraction_api.pdf_service, "acquire_pdf", fake_acquire)

    res = await async_client.post(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf/acquire"
    )
    # A falha de busca é resultado esperado do fluxo, não erro de API: o cliente
    # precisa da trilha para orientar o usuário.
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "failed"
    assert data["attempts"][0]["http_status"] == 403

    db_session.refresh(paper)
    assert paper.pdf_status == "falhou"
    assert "403" in paper.pdf_attempts


@pytest.mark.anyio
async def test_upload_rejeita_arquivo_invalido(async_client, projeto_com_artigo):
    projeto, paper = projeto_com_artigo
    res = await async_client.post(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf/upload",
        files={"file": ("fake.pdf", b"<html>login</html>", "application/pdf")},
    )
    assert res.status_code == 400
    assert "não é um PDF válido" in res.json()["detail"]


@pytest.mark.anyio
async def test_upload_e_texto_com_paginas_e_secoes(async_client, projeto_com_artigo):
    projeto, paper = projeto_com_artigo
    conteudo = _make_pdf(
        [
            f"Título do estudo\n\nRESUMO\n\nAnálise de APLs.\n\n{CORPO}",
            f"METODOLOGIA\n\nForam analisados 137 municípios.\n\n{CORPO}",
        ]
    )

    upload = await async_client.post(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf/upload",
        files={"file": ("artigo.pdf", conteudo, "application/pdf")},
    )
    assert upload.status_code == 200
    assert upload.json()["page_count"] == 2
    assert upload.json()["is_scanned"] is False

    texto = await async_client.get(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf/text"
    )
    assert texto.status_code == 200
    data = texto.json()
    assert data["page_count"] == 2
    assert len(data["pages"]) == 2
    assert "137 municípios" in data["text"]
    assert any(s["key"] == "metodo" for s in data["sections"])


@pytest.mark.anyio
async def test_pdf_servido_inline_para_visualizador_embutido(
    async_client, projeto_com_artigo
):
    projeto, paper = projeto_com_artigo
    await async_client.post(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf/upload",
        files={"file": ("artigo.pdf", _make_pdf([CORPO]), "application/pdf")},
    )

    res = await async_client.get(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf"
    )
    assert res.status_code == 200
    assert res.headers["content-disposition"].startswith("inline")

    baixar = await async_client.get(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf?download=true"
    )
    assert baixar.headers["content-disposition"].startswith("attachment")


@pytest.mark.anyio
async def test_delete_limpa_procedencia(async_client, db_session, projeto_com_artigo):
    projeto, paper = projeto_com_artigo
    await async_client.post(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf/upload",
        files={"file": ("artigo.pdf", _make_pdf([CORPO]), "application/pdf")},
    )

    res = await async_client.delete(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf"
    )
    assert res.status_code == 200

    db_session.refresh(paper)
    assert paper.pdf_path is None
    assert paper.pdf_status == "ausente"
    assert paper.pdf_page_count == 0


@pytest.mark.anyio
async def test_candidatos_em_modo_diagnostico(async_client, projeto_com_artigo, monkeypatch):
    projeto, paper = projeto_com_artigo

    from app.services.pdf_resolver import PDFCandidate

    async def fake_find(ref, client=None):
        return [
            PDFCandidate(url="https://repositorio.org/a.pdf", strategy="landing", label="Link"),
        ]

    monkeypatch.setattr(extraction_api.pdf_service, "find_candidates", fake_find)

    res = await async_client.get(
        f"/api/v1/projects/{projeto.id}/papers/{paper.id}/extraction/pdf/candidates"
    )
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["candidates"][0]["strategy"] == "landing"


@pytest.mark.anyio
async def test_lote_processa_incluidos_pendentes(
    async_client, db_session, projeto_com_artigo, monkeypatch, tmp_path
):
    projeto, paper = projeto_com_artigo
    destino = tmp_path / f"{paper.id}.pdf"
    destino.write_bytes(_make_pdf([CORPO]))

    async def fake_acquire(project_id, paper_id, ref, client=None):
        return PDFAcquisition(
            success=True,
            file_path=str(destino),
            strategy="unpaywall",
            page_count=1,
            text_chars=500,
            message="ok",
        )

    monkeypatch.setattr(extraction_api.pdf_service, "acquire_pdf", fake_acquire)
    # O lote abre e fecha a própria sessão; no teste ela aponta para o banco em
    # memória, então o `close()` precisa ser neutralizado.
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(extraction_api, "SessionLocal", lambda: db_session)

    start = await async_client.post(f"/api/v1/projects/{projeto.id}/extraction/pdf/batch")
    assert start.status_code == 200
    assert start.json()["status"] in ("running", "done")
    assert start.json()["total"] == 1

    # Aguarda o término do lote consultando o progresso.
    for _ in range(50):
        await asyncio.sleep(0.02)
        status = await async_client.get(f"/api/v1/projects/{projeto.id}/extraction/pdf/batch")
        if status.json().get("status") == "done":
            break

    final = status.json()
    assert final["status"] == "done"
    assert final["succeeded"] == 1
    assert final["results"][0]["strategy"] == "unpaywall"


@pytest.mark.anyio
async def test_lote_vazio_quando_todos_tem_pdf(
    async_client, db_session, projeto_com_artigo, tmp_path
):
    projeto, paper = projeto_com_artigo
    arquivo = tmp_path / "existente.pdf"
    arquivo.write_bytes(_make_pdf([CORPO]))
    paper.pdf_path = str(arquivo)
    db_session.commit()

    res = await async_client.post(f"/api/v1/projects/{projeto.id}/extraction/pdf/batch")
    assert res.status_code == 200
    assert res.json()["status"] == "empty"
