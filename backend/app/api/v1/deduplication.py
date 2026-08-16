#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Deduplicação e Relatório Consolidado."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import DeduplicationReportModel, ProjectModel
from app.services.dedup_service import DeduplicationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/deduplicate", tags=["deduplication"])
dedup_service = DeduplicationService()


@router.post("", summary="Executa a deduplicação e gera o relatório")
def run_deduplication(
    project_id: str,
    db: Session = Depends(get_db),
):
    """
    Executa a deduplicação completa dos artigos coletados no projeto,
    unifica fontes, marca duplicatas e gera o Relatório de Deduplicação.
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    try:
        report_data = dedup_service.run_project_deduplication(db, project_id)
        return {
            "status": "success",
            "data": report_data,
        }
    except Exception as e:
        logger.error(f"[Dedup] Erro ao executar deduplicação no projeto {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Falha ao executar deduplicação: {e}")


@router.get("/report", summary="Obtém o último relatório de deduplicação gerado")
def get_latest_report(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Retorna o relatório de deduplicação mais recente gerado para o projeto."""
    import json

    report = (
        db.query(DeduplicationReportModel)
        .filter(DeduplicationReportModel.project_id == project_id)
        .order_by(DeduplicationReportModel.created_at.desc())
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Nenhum relatório de deduplicação foi gerado para este projeto ainda.",
        )

    return {
        "id": report.id,
        "project_id": report.project_id,
        "total_raw": report.total_raw,
        "total_unique": report.total_unique,
        "total_duplicates": report.total_duplicates,
        "dup_rate": round((report.total_duplicates / report.total_raw * 100), 1) if report.total_raw > 0 else 0.0,
        "sources_breakdown": json.loads(report.sources_breakdown or "{}"),
        "duplicates_list": json.loads(report.duplicates_list or "[]"),
        "report_text": report.report_text,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/download", summary="Download do relatório de deduplicação em .txt")
def download_report_txt(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Retorna o arquivo 3_relatorio_deduplicacao.txt para download direto."""
    report = (
        db.query(DeduplicationReportModel)
        .filter(DeduplicationReportModel.project_id == project_id)
        .order_by(DeduplicationReportModel.created_at.desc())
        .first()
    )

    if not report or not report.report_text:
        raise HTTPException(
            status_code=404,
            detail="Nenhum relatório de deduplicação disponível para download.",
        )

    filename = "3_relatorio_deduplicacao.txt"
    return Response(
        content=report.report_text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
