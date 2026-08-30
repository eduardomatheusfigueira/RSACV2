#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Router de Projetos."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    AuditLogModel,
    CriterionModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    HarvestRunModel,
    PaperCriterionModel,
    PaperModel,
    PaperSourceModel,
    ProjectModel,
    ProtocolModel,
    UserModel,
)
from app.config import settings
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from app.security.dependencies import projeto_do_usuario, require_session
from app.services.pdf_service import PDFService
from app.security.middleware import erro_interno

logger = logging.getLogger(__name__)

pdf_service = PDFService()

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    archived: Optional[bool] = Query(None, description="Filtrar por arquivamento"),
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Lista os projetos **de quem está pedindo**."""
    query = db.query(ProjectModel).filter(ProjectModel.owner_id == usuario.id)
    if archived is not None:
        query = query.filter(ProjectModel.is_archived == archived)
    query = query.order_by(ProjectModel.updated_at.desc())

    projects = query.all()
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=len(projects),
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Cria um novo projeto de revisão sistemática, pertencente a quem o criou."""
    # Verificar teto de projetos por conta (§40.7.5, O-25)
    total_existente = (
        db.query(ProjectModel).filter(ProjectModel.owner_id == usuario.id).count()
    )
    if total_existente >= settings.max_projects_per_user:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Limite de {settings.max_projects_per_user} projetos atingido para esta conta. "
                "Exclua ou arquive projetos anteriores antes de criar um novo."
            ),
        )

    project = ProjectModel(
        owner_id=usuario.id,
        title=data.title,
        description=data.description,
        methodology=data.methodology,
    )
    db.add(project)
    db.flush()

    # Cria protocolo vazio vinculado
    protocol = ProtocolModel(project_id=project.id)
    db.add(protocol)

    db.commit()
    db.refresh(project)

    logger.info(f"Projeto criado: '{project.title}' (ID: {project.id})")
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project: ProjectModel = Depends(projeto_do_usuario),
):
    """Obtém detalhes de um projeto específico."""
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    project: ProjectModel = Depends(projeto_do_usuario),
):
    """Atualiza um projeto existente."""

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    logger.info(f"Projeto atualizado: '{project.title}' (ID: {project.id})")
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    project: ProjectModel = Depends(projeto_do_usuario),
):
    """
    Exclui um projeto e todos os dados associados com cascata rigorosa e segura
    mesmo para acervos massivos (sem estourar limites de parâmetros SQL).
    """
    try:
        # 1. Remove os PDFs do disco de forma atômica
        try:
            removidos = pdf_service.delete_project_pdfs(project_id)
            if removidos:
                logger.info("[Projects] %d PDF(s) do projeto %s removidos do disco.", removidos, project_id)
        except Exception as exc:
            logger.warning("[Projects] Falha ao remover PDFs em disco do projeto %s: %s", project_id, exc)

        # 2. Deleta entidades filhas usando subconsultas SQL por project_id
        from sqlalchemy import text

        # a) Respostas de extração, critérios de papers, fontes e logs de auditoria
        db.execute(
            text(
                "DELETE FROM extraction_answers WHERE paper_id IN (SELECT id FROM papers WHERE project_id = :pid) "
                "OR question_id IN (SELECT eq.id FROM extraction_questions eq JOIN protocols p ON eq.protocol_id = p.id WHERE p.project_id = :pid)"
            ),
            {"pid": project_id},
        )
        db.execute(
            text(
                "DELETE FROM paper_criteria WHERE paper_id IN (SELECT id FROM papers WHERE project_id = :pid) "
                "OR criterion_id IN (SELECT c.id FROM criteria c JOIN protocols p ON c.protocol_id = p.id WHERE p.project_id = :pid)"
            ),
            {"pid": project_id},
        )
        db.execute(
            text("DELETE FROM paper_sources WHERE paper_id IN (SELECT id FROM papers WHERE project_id = :pid)"),
            {"pid": project_id},
        )
        db.execute(
            text("DELETE FROM audit_logs WHERE paper_id IN (SELECT id FROM papers WHERE project_id = :pid)"),
            {"pid": project_id},
        )

        # b) Perguntas de extração e critérios do protocolo
        db.execute(
            text(
                "DELETE FROM extraction_questions WHERE protocol_id IN (SELECT id FROM protocols WHERE project_id = :pid)"
            ),
            {"pid": project_id},
        )
        db.execute(
            text(
                "DELETE FROM criteria WHERE protocol_id IN (SELECT id FROM protocols WHERE project_id = :pid)"
            ),
            {"pid": project_id},
        )

        # c) Papers, Protocolos e Harvest Runs
        db.execute(text("DELETE FROM papers WHERE project_id = :pid"), {"pid": project_id})
        db.execute(text("DELETE FROM protocols WHERE project_id = :pid"), {"pid": project_id})
        db.execute(text("DELETE FROM harvest_runs WHERE project_id = :pid"), {"pid": project_id})

        # d) Projeto raiz
        db.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": project_id})

        db.commit()
        logger.info(f"Projeto excluído com sucesso: ID {project_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao excluir projeto {project_id}: {e}", exc_info=True)
        mensagem, _ = erro_interno(
            "Falha ao excluir o projeto.", e, contexto="[Projects] exclusão"
        )
        raise HTTPException(status_code=500, detail=mensagem) from e


@router.get("/{project_id}/stats")
def get_project_stats(
    project_id: str,
    db: Session = Depends(get_db),
    project: ProjectModel = Depends(projeto_do_usuario),
):
    """Retorna estatísticas do projeto (contadores PRISMA)."""

    from sqlalchemy import func, or_

    from app.infrastructure.persistence.models import PaperModel

    papers = db.query(PaperModel).filter(
        PaperModel.project_id == project_id,
        or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)),
    )
    total = papers.count()
    included = papers.filter(PaperModel.decision == "Incluído").count()
    excluded = papers.filter(PaperModel.decision == "Excluído").count()
    pending = papers.filter(PaperModel.decision == "Pendente").count()

    # Contagem por fonte
    from app.infrastructure.persistence.models import PaperSourceModel
    source_counts = (
        db.query(PaperSourceModel.source_name, func.count(PaperSourceModel.id))
        .join(PaperModel, PaperModel.id == PaperSourceModel.paper_id)
        .filter(PaperModel.project_id == project_id)
        .group_by(PaperSourceModel.source_name)
        .all()
    )

    return {
        "total_papers": total,
        "included_papers": included,
        "excluded_papers": excluded,
        "pending_papers": pending,
        "total_harvest_runs": len(project.harvest_runs),
        "sources": {name: count for name, count in source_counts},
    }
