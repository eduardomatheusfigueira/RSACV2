#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Exportação de Dados (Excel, BibTeX e PRISMA)."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.security.dependencies import projeto_do_usuario
from app.infrastructure.persistence.models import ProjectModel
from app.services.export_service import ExportService, cabecalho_de_download

logger = logging.getLogger(__name__)

# A titularidade entra como dependência do router, e não rota a rota (doc 40
# §40.3.2): é o mesmo padrão de `require_session`, e é o que faz uma rota
# nova nascer isolada sem depender de ninguém lembrar.
router = APIRouter(
    prefix="/projects/{project_id}/export",
    dependencies=[Depends(projeto_do_usuario)],
    tags=["export"],
)
export_service = ExportService()


@router.get("/excel")
def export_to_excel(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Gera e retorna planilha Excel (.xlsx) com múltiplas abas."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    excel_stream = export_service.generate_excel(db, project_id)

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=cabecalho_de_download(f"RSAC_Export_{project.title[:30]}", "xlsx"),
    )


@router.get("/bibtex")
def export_to_bibtex(
    project_id: str,
    only_included: bool = Query(True, description="Apenas estudos incluídos"),
    db: Session = Depends(get_db),
):
    """Gera e retorna arquivo BibTeX (.bib) com citações formatadas."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    bib_text = export_service.generate_bibtex(db, project_id, only_included=only_included)

    return Response(
        content=bib_text,
        media_type="text/plain; charset=utf-8",
        headers=cabecalho_de_download(f"RSAC_References_{project.title[:30]}", "bib"),
    )


@router.get("/prisma")
def get_prisma_flow_metrics(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Retorna dados estruturados para o diagrama de fluxo PRISMA 2020."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    return export_service.get_prisma_flow_data(db, project_id)
