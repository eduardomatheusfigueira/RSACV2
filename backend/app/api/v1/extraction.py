#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Extração de Dados e Gestão de PDFs."""

import logging
from typing import Dict, List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    PaperModel,
    ProtocolModel,
)
from app.services.extraction_service import ExtractionService
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/papers/{paper_id}/extraction", tags=["extraction"])
pdf_service = PDFService()
extraction_service = ExtractionService()


@router.get("")
def get_paper_extraction_answers(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Obtém as respostas de extração de dados cadastradas para o artigo."""
    paper = db.query(PaperModel).filter(PaperModel.project_id == project_id, PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Artigo não encontrado.")

    answers = (
        db.query(ExtractionAnswerModel)
        .filter(ExtractionAnswerModel.paper_id == paper_id)
        .all()
    )

    return {
        "paper_id": paper_id,
        "has_pdf": paper.pdf_path is not None,
        "pdf_path": paper.pdf_path,
        "answers": [
            {
                "id": a.id,
                "question_id": a.question_id,
                "answer": a.answer,
                "ai_generated": a.ai_generated,
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
        else:
            db.add(
                ExtractionAnswerModel(
                    paper_id=paper_id,
                    question_id=q_id,
                    answer=ans_text,
                    ai_generated=False,
                )
            )

    db.commit()
    return {"status": "saved", "total_answers": len(data)}


@router.post("/ai")
async def extract_answers_with_ai(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Executa a extração automática das respostas do artigo usando IA e o texto do PDF/Resumo."""
    settings = db.query(AISettingsModel).first()
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de IA estão desativados nas Configurações (Modo 100% Manual).",
        )
    try:
        answers = await extraction_service.extract_answers_with_ai(db, project_id, paper_id)
        return {"status": "success", "answers": answers}
    except Exception as e:
        logger.error(f"[ExtractionAPI] Erro ao extrair com IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pdf/upload")
async def upload_paper_pdf(
    project_id: str,
    paper_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Faz o upload manual do PDF do artigo."""
    paper = db.query(PaperModel).filter(PaperModel.project_id == project_id, PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Artigo não encontrado.")

    content = await file.read()
    saved_path = pdf_service.save_uploaded_pdf(project_id, paper_id, content)

    paper.pdf_path = saved_path
    paper.pdf_text_extracted = True
    db.commit()

    return {"status": "uploaded", "pdf_path": saved_path}


@router.post("/pdf/download")
async def download_paper_pdf(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Tenta baixar automaticamente o PDF a partir do download_url do artigo."""
    paper = db.query(PaperModel).filter(PaperModel.project_id == project_id, PaperModel.id == paper_id).first()
    if not paper or not paper.download_url:
        raise HTTPException(status_code=400, detail="Artigo não possui download_url cadastrada.")

    saved_path = await pdf_service.download_pdf(project_id, paper_id, paper.download_url)
    if not saved_path:
        raise HTTPException(status_code=404, detail="Não foi possível obter o PDF na URL cadastrada.")

    paper.pdf_path = saved_path
    paper.pdf_text_extracted = True
    db.commit()

    return {"status": "downloaded", "pdf_path": saved_path}
