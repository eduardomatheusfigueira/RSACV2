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
    """Exclui um projeto e todos os dados associados com cascata rigorosa."""
    try:
        # 1. Coleta IDs de Papers vinculados ao projeto
        paper_ids = [r[0] for r in db.query(PaperModel.id).filter(PaperModel.project_id == project_id).all()]

        # 1b. Apaga os PDFs do disco **antes** de perder os identificadores.
        #
        # A cascata era rigorosa no banco e ignorava o sistema de arquivos: o
        # PDF — a peça com maior densidade de dado pessoal do acervo, porque
        # traz nomes, vínculos e às vezes dados de saúde de terceiros —
        # sobrevivia à exclusão do projeto que o trouxe. É o achado F-02 do
        # doc 37 e o item L-24 do checklist: o art. 16 da LGPD exige que a
        # eliminação alcance todos os repositórios, não só o principal.
        #
        # A remoção do arquivo não pode derrubar a exclusão: um PDF que não
        # sai deixa lixo em disco, mas um erro aqui deixaria o usuário sem
        # conseguir apagar o próprio projeto.
        removidos = 0
        for paper_id in paper_ids:
            try:
                if pdf_service.delete_pdf(project_id, paper_id):
                    removidos += 1
            except OSError as exc:
                logger.warning(
                    "[Projects] PDF de %s não pôde ser removido: %s", paper_id, exc
                )
        if removidos:
            logger.info("[Projects] %d PDF(s) removidos do disco.", removidos)

        # 2. Deleta entidades filhas dos papers
        if paper_ids:
            db.query(PaperSourceModel).filter(PaperSourceModel.paper_id.in_(paper_ids)).delete(synchronize_session=False)
            db.query(PaperCriterionModel).filter(PaperCriterionModel.paper_id.in_(paper_ids)).delete(synchronize_session=False)
            db.query(ExtractionAnswerModel).filter(ExtractionAnswerModel.paper_id.in_(paper_ids)).delete(synchronize_session=False)
            db.query(AuditLogModel).filter(AuditLogModel.paper_id.in_(paper_ids)).delete(synchronize_session=False)
            db.query(PaperModel).filter(PaperModel.project_id == project_id).delete(synchronize_session=False)

        # 3. Coleta protocolos do projeto e deleta critérios e perguntas de extração
        protocol_ids = [r[0] for r in db.query(ProtocolModel.id).filter(ProtocolModel.project_id == project_id).all()]
        if protocol_ids:
            criterion_ids = [r[0] for r in db.query(CriterionModel.id).filter(CriterionModel.protocol_id.in_(protocol_ids)).all()]
            if criterion_ids:
                db.query(PaperCriterionModel).filter(PaperCriterionModel.criterion_id.in_(criterion_ids)).delete(synchronize_session=False)
                db.query(CriterionModel).filter(CriterionModel.protocol_id.in_(protocol_ids)).delete(synchronize_session=False)

            question_ids = [r[0] for r in db.query(ExtractionQuestionModel.id).filter(ExtractionQuestionModel.protocol_id.in_(protocol_ids)).all()]
            if question_ids:
                db.query(ExtractionAnswerModel).filter(ExtractionAnswerModel.question_id.in_(question_ids)).delete(synchronize_session=False)
                db.query(ExtractionQuestionModel).filter(ExtractionQuestionModel.protocol_id.in_(protocol_ids)).delete(synchronize_session=False)

            db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).delete(synchronize_session=False)

        # 4. Deleta execuções de coleta (harvest runs)
        db.query(HarvestRunModel).filter(HarvestRunModel.project_id == project_id).delete(synchronize_session=False)

        # 5. Deleta o projeto raiz
        db.query(ProjectModel).filter(ProjectModel.id == project_id).delete(synchronize_session=False)
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
