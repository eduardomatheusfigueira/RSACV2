#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Extração de Dados e Gestão de PDFs."""

import json
import logging
import os
from typing import Dict, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.database import SessionLocal
from app.infrastructure.persistence.models import (
    AISettingsModel,
    ExtractionAnswerModel,
    PaperModel,
    ProjectModel,
    ProtocolModel,
)
from app.services.extraction_service import ExtractionService
from app.services.pdf_acquisition import (
    acquire_for_paper,
    build_paper_ref,
    clear_pdf_state,
    pdf_batch_manager,
)
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/papers/{paper_id}/extraction", tags=["extraction"])
project_extraction_router = APIRouter(prefix="/projects/{project_id}/extraction", tags=["extraction"])
pdf_service = PDFService()
extraction_service = ExtractionService()


def _get_paper(db: Session, project_id: str, paper_id: str) -> PaperModel:
    """Carrega o trabalho do projeto (com fontes) ou devolve 404."""
    paper = (
        db.query(PaperModel)
        .options(selectinload(PaperModel.sources))
        .filter(PaperModel.project_id == project_id, PaperModel.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Artigo não encontrado.")
    return paper


def _pdf_state(paper: PaperModel) -> dict:
    """Retrato do estado do PDF do trabalho, com a trilha da última busca."""
    try:
        attempts = json.loads(paper.pdf_attempts or "[]")
    except ValueError:
        attempts = []

    has_file = bool(paper.pdf_path and os.path.exists(paper.pdf_path))
    return {
        "has_pdf": has_file,
        "pdf_path": paper.pdf_path if has_file else None,
        "pdf_status": paper.pdf_status or ("obtido" if has_file else "ausente"),
        "pdf_strategy": paper.pdf_strategy or "",
        "pdf_resolved_url": paper.pdf_resolved_url or "",
        "pdf_page_count": paper.pdf_page_count or 0,
        "pdf_size_bytes": paper.pdf_size_bytes or 0,
        "pdf_text_chars": paper.pdf_text_chars or 0,
        "pdf_is_scanned": bool(paper.pdf_is_scanned),
        "pdf_acquired_at": paper.pdf_acquired_at.isoformat() if paper.pdf_acquired_at else None,
        "download_url": paper.download_url or "",
        "attempts": attempts,
        # Arquivo sumiu do disco (projeto movido, pasta limpa) mas o banco ainda aponta.
        "file_missing": bool(paper.pdf_path) and not has_file,
    }


@project_extraction_router.get("/summary")
def get_project_extraction_summary(
    project_id: str,
    db: Session = Depends(get_db),
):
    """
    Retorna o resumo consolidado do fluxo de extração e a matriz de evidências por pergunta,
    servindo de base empírica para a síntese dos achados (Fase A Posteriori).
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    questions = sorted(protocol.extraction_questions, key=lambda q: q.order) if protocol and protocol.extraction_questions else []

    all_papers = db.query(PaperModel).filter(PaperModel.project_id == project_id).all()
    included_papers = [p for p in all_papers if p.decision == "Incluído"]
    excluded_papers = [p for p in all_papers if p.decision == "Excluído"]
    pending_papers = [p for p in all_papers if p.decision == "Pendente"]

    # Buscar todas as respostas de artigos incluídos
    included_paper_ids = {p.id for p in included_papers}
    answers = (
        db.query(ExtractionAnswerModel)
        .filter(ExtractionAnswerModel.paper_id.in_(included_paper_ids))
        .all()
    ) if included_paper_ids else []

    answers_by_paper_and_question: Dict[str, Dict[str, ExtractionAnswerModel]] = {}
    for a in answers:
        if a.paper_id not in answers_by_paper_and_question:
            answers_by_paper_and_question[a.paper_id] = {}
        answers_by_paper_and_question[a.paper_id][a.question_id] = a

    # Contar quantos artigos incluídos têm pelo menos uma resposta preenchida
    papers_with_answers = {
        pid for pid, qmap in answers_by_paper_and_question.items()
        if any(ans.answer and ans.answer.strip() for ans in qmap.values())
    }
    total_extracted = len(papers_with_answers)
    total_included = len(included_papers)
    extraction_progress_pct = round((total_extracted / total_included * 100), 1) if total_included > 0 else 0.0

    # Construir matriz estruturada por pergunta de extração
    questions_matrix = []
    for q in questions:
        q_answers = []
        for p in included_papers:
            ans_obj = answers_by_paper_and_question.get(p.id, {}).get(q.id)
            ans_text = ans_obj.answer if ans_obj else ""
            if ans_text and ans_text.strip():
                q_answers.append({
                    "paper_id": p.id,
                    "paper_title": p.title,
                    "authors": p.authors,
                    "year": p.year,
                    "answer": ans_text,
                    "ai_generated": ans_obj.ai_generated if ans_obj else False,
                })
        questions_matrix.append({
            "question_id": q.id,
            "question_text": q.text,
            "order": q.order,
            "total_answered": len(q_answers),
            "answers": q_answers,
        })

    return {
        "project_id": project_id,
        "total_screened": len(all_papers),
        "total_included": total_included,
        "total_excluded": len(excluded_papers),
        "total_pending": len(pending_papers),
        "total_extracted": total_extracted,
        "extraction_progress_percent": extraction_progress_pct,
        "questions_matrix": questions_matrix,
    }


@router.get("")
def get_paper_extraction_answers(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Obtém as respostas de extração de dados e o estado do PDF do artigo."""
    paper = _get_paper(db, project_id, paper_id)

    answers = (
        db.query(ExtractionAnswerModel)
        .filter(ExtractionAnswerModel.paper_id == paper_id)
        .all()
    )

    return {
        "paper_id": paper_id,
        **_pdf_state(paper),
        "answers": [
            {
                "id": a.id,
                "question_id": a.question_id,
                "answer": a.answer,
                "ai_generated": a.ai_generated,
                "evidence": a.evidence or "",
                "page_ref": a.page_ref or "",
                "source_kind": a.source_kind or "",
            }
            for a in answers
        ],
    }


@router.put("")
def update_paper_extraction_answers(
    project_id: str,
    paper_id: str,
    data: Dict[str, str],  # { "question_id": "answer" }
    db: Session = Depends(get_db),
):
    """Salva ou atualiza manualmente as respostas de extração."""
    paper = db.query(PaperModel).filter(PaperModel.project_id == project_id, PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Artigo não encontrado.")

    for q_id, ans_text in data.items():
        existing = (
            db.query(ExtractionAnswerModel)
            .filter(
                ExtractionAnswerModel.paper_id == paper_id,
                ExtractionAnswerModel.question_id == q_id,
            )
            .first()
        )
        if existing:
            existing.answer = ans_text
            existing.ai_generated = False
            existing.source_kind = "manual"
        else:
            db.add(
                ExtractionAnswerModel(
                    paper_id=paper_id,
                    question_id=q_id,
                    answer=ans_text,
                    ai_generated=False,
                    source_kind="manual",
                )
            )

    db.commit()
    return {"status": "saved", "total_answers": len(data)}


@router.post("/ai")
async def extract_answers_with_ai(
    project_id: str,
    paper_id: str,
    question_id: Optional[str] = Query(None, description="ID opcional para extrair apenas uma pergunta específica"),
    db: Session = Depends(get_db),
):
    """Executa a extração automática das respostas do artigo (todas ou uma específica) usando IA."""
    settings = db.query(AISettingsModel).first()
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de Assistência estão desativados nas Configurações (Modo Manual).",
        )
    try:
        answers = await extraction_service.extract_answers_with_ai(
            db, project_id, paper_id, question_id=question_id
        )
        return {"status": "success", "answers": answers}
    except Exception as e:
        logger.error(f"[ExtractionAPI] Erro ao extrair com assistência: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/pdf/status")
def get_paper_pdf_status(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Estado do PDF do trabalho, incluindo a trilha da última busca automática."""
    paper = _get_paper(db, project_id, paper_id)
    return {"paper_id": paper_id, **_pdf_state(paper)}


@router.post("/pdf/upload")
async def upload_paper_pdf(
    project_id: str,
    paper_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Faz o upload manual do PDF do artigo."""
    paper = _get_paper(db, project_id, paper_id)

    content = await file.read()
    try:
        saved_path = pdf_service.save_uploaded_pdf(project_id, paper_id, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document = pdf_service.read_document(saved_path)

    paper.pdf_path = saved_path
    paper.pdf_status = "manual"
    paper.pdf_strategy = "upload"
    paper.pdf_resolved_url = ""
    paper.pdf_size_bytes = len(content)
    paper.pdf_sha256 = pdf_service.sha256_of(content)
    paper.pdf_page_count = document.page_count
    paper.pdf_text_chars = document.char_count
    paper.pdf_is_scanned = document.is_scanned
    paper.pdf_text_extracted = document.char_count > 0
    db.commit()

    return {
        "status": "uploaded",
        "pdf_path": saved_path,
        "page_count": document.page_count,
        "is_scanned": document.is_scanned,
        "text_chars": document.char_count,
        "message": (
            "PDF anexado, porém sem texto selecionável (documento digitalizado). "
            "A extração assistida usará o resumo."
            if document.is_scanned
            else f"PDF anexado com {document.page_count} página(s) e texto legível."
        ),
    }


@router.post("/pdf/acquire")
async def acquire_paper_pdf(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """
    Busca o PDF do trabalho por todas as vias disponíveis (DOI, Unpaywall,
    OpenAlex, Crossref, Europe PMC, padrões de repositório e raspagem da
    landing page) e devolve a trilha completa do que foi tentado.
    """
    paper = _get_paper(db, project_id, paper_id)
    result = await acquire_for_paper(db, paper, pdf_service=pdf_service)

    return {
        "status": "downloaded" if result.success else "failed",
        **result.to_dict(),
        **_pdf_state(paper),
    }


@router.post("/pdf/download")
async def download_paper_pdf(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Alias histórico de `/pdf/acquire` — mantido para compatibilidade."""
    paper = _get_paper(db, project_id, paper_id)
    result = await acquire_for_paper(db, paper, pdf_service=pdf_service)

    if not result.success:
        raise HTTPException(
            status_code=404,
            detail=result.message,
            headers={"X-PDF-Attempts": str(len(result.attempts))},
        )

    return {"status": "downloaded", **result.to_dict()}


@router.get("/pdf/candidates")
async def list_paper_pdf_candidates(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """
    Modo diagnóstico: lista os links candidatos a texto completo encontrados
    para o trabalho, sem baixar nada. Serve para o usuário conferir na mão
    quando a busca automática falha.
    """
    paper = _get_paper(db, project_id, paper_id)
    candidates = await pdf_service.find_candidates(build_paper_ref(paper))
    return {
        "paper_id": paper_id,
        "total": len(candidates),
        "candidates": [
            {"url": c.url, "strategy": c.strategy, "label": c.label} for c in candidates
        ],
    }


@router.get("/pdf")
def get_paper_pdf_file(
    project_id: str,
    paper_id: str,
    download: bool = Query(False, description="Força anexo em vez de exibição embutida"),
    db: Session = Depends(get_db),
):
    """Serve o arquivo PDF para o visualizador embutido ou para download."""
    paper = _get_paper(db, project_id, paper_id)
    if not paper.pdf_path or not os.path.exists(paper.pdf_path):
        raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado localmente.")

    disposition = "attachment" if download else "inline"
    safe_name = f"{paper_id}.pdf"
    return FileResponse(
        path=paper.pdf_path,
        media_type="application/pdf",
        headers={
            # `inline` é o que permite renderizar o PDF dentro da aplicação;
            # com `attachment` o visualizador embutido só oferece salvar.
            "Content-Disposition": f'{disposition}; filename="{safe_name}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get("/pdf/text")
def get_paper_pdf_extracted_text(
    project_id: str,
    paper_id: str,
    refresh: bool = Query(False, description="Ignora o cache e reextrai o texto"),
    db: Session = Depends(get_db),
):
    """Texto completo do PDF, paginado e com diagnóstico de qualidade."""
    paper = _get_paper(db, project_id, paper_id)
    if not paper.pdf_path or not os.path.exists(paper.pdf_path):
        raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado localmente.")

    try:
        document = pdf_service.read_document(paper.pdf_path, use_cache=not refresh)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — motor externo de PDF
        logger.error(f"[PDFText] Erro ao extrair texto do PDF: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao extrair texto do PDF: {exc}"
        ) from exc

    # Mantém o banco em dia com o que foi de fato lido do arquivo.
    paper.pdf_page_count = document.page_count
    paper.pdf_text_chars = document.char_count
    paper.pdf_is_scanned = document.is_scanned
    paper.pdf_text_extracted = document.char_count > 0
    db.commit()

    return {
        "paper_id": paper_id,
        "text": document.text,
        "pages": [{"number": p.number, "text": p.text} for p in document.pages],
        "page_count": document.page_count,
        "char_count": document.char_count,
        "is_scanned": document.is_scanned,
        "engine": document.engine,
        "error": document.error,
        "sections": pdf_service.get_sections(paper.pdf_path),
    }


@router.delete("/pdf")
def delete_paper_pdf_file(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Remove o PDF anexado do artigo (arquivo, cache de texto e procedência)."""
    paper = _get_paper(db, project_id, paper_id)
    pdf_service.delete_pdf(project_id, paper_id, paper.pdf_path)
    clear_pdf_state(paper)
    db.commit()
    return {"status": "deleted"}


@router.patch("/download-url")
def update_paper_download_url(
    project_id: str,
    paper_id: str,
    data: Dict[str, str],
    db: Session = Depends(get_db),
):
    """Atualiza a URL de origem/download do artigo."""
    paper = _get_paper(db, project_id, paper_id)
    paper.download_url = data.get("download_url", paper.download_url)
    db.commit()
    return {"status": "updated", "download_url": paper.download_url}


# ── Aquisição em lote (todos os incluídos de uma vez) ─────────────────

@project_extraction_router.post("/pdf/batch")
async def start_pdf_batch(
    project_id: str,
    only_missing: bool = Query(True, description="Ignora trabalhos que já têm PDF"),
    decision: Optional[str] = Query("Incluído", description="Filtra por decisão da triagem"),
    db: Session = Depends(get_db),
):
    """
    Dispara a busca de PDFs de todos os trabalhos elegíveis do projeto.

    Roda em segundo plano com concorrência limitada; o progresso é consultado
    em `GET /pdf/batch`.
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    if pdf_batch_manager.is_running(project_id):
        raise HTTPException(
            status_code=409,
            detail="Já existe uma busca de PDFs em andamento para este projeto.",
        )

    query = db.query(PaperModel).filter(PaperModel.project_id == project_id)
    if decision:
        query = query.filter(PaperModel.decision == decision)
    papers = query.all()

    eligible = [
        p
        for p in papers
        if not (only_missing and p.pdf_path and os.path.exists(p.pdf_path))
    ]
    if not eligible:
        return {
            "status": "empty",
            "total": 0,
            "message": "Nenhum trabalho elegível — todos já possuem PDF vinculado.",
        }

    state = pdf_batch_manager.start(
        project_id, [p.id for p in eligible], SessionLocal, pdf_service=pdf_service
    )
    return state.to_dict()


@project_extraction_router.get("/pdf/batch")
def get_pdf_batch_status(project_id: str):
    """Progresso da busca de PDFs em lote do projeto."""
    state = pdf_batch_manager.get_state(project_id)
    if not state:
        return {"status": "idle", "project_id": project_id}
    return state.to_dict()


@project_extraction_router.delete("/pdf/batch")
async def cancel_pdf_batch(project_id: str):
    """Cancela a busca de PDFs em lote em andamento."""
    cancelled = pdf_batch_manager.cancel(project_id)
    return {"status": "cancelled" if cancelled else "idle", "project_id": project_id}
