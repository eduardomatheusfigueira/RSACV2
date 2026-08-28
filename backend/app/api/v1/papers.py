#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Artigos (Papers)."""

import logging
import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, func

from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    AuditLogModel,
    PaperCriterionModel,
    PaperModel,
    PaperSourceModel,
    UserModel,
)
from app.security.dependencies import projeto_do_usuario, require_session
from app.schemas.paper import (
    PaperCreate,
    PaperListResponse,
    PaperResponse,
    PaperUpdate,
)

logger = logging.getLogger(__name__)

# A titularidade entra como dependência do router, e não rota a rota (doc 40
# §40.3.2): é o mesmo padrão de `require_session`, e é o que faz uma rota
# nova nascer isolada sem depender de ninguém lembrar.
router = APIRouter(
    prefix="/projects/{project_id}/papers",
    dependencies=[Depends(projeto_do_usuario)],
    tags=["papers"],
)


def _normalize_title(title: str) -> str:
    """Normaliza título para busca e deduplicação."""
    return "".join(c.lower() for c in title if c.isalnum() or c.isspace()).strip()


def _serialize_paper(paper: PaperModel) -> PaperResponse:
    sources = [s.source_name for s in paper.sources] if paper.sources else []
    criteria_evaluations = {
        c.criterion_id: c.value
        for c in paper.criteria_evaluations
    } if paper.criteria_evaluations else {}
    return PaperResponse(
        id=paper.id,
        project_id=paper.project_id,
        title=paper.title,
        title_normalized=paper.title_normalized or _normalize_title(paper.title),
        authors=paper.authors or "",
        year=paper.year or "",
        doi=paper.doi,
        abstract=paper.abstract or "",
        research_type=paper.research_type or "",
        institution=paper.institution or "",
        download_url=paper.download_url or "",
        decision=paper.decision,
        observations=paper.observations or "",
        ai_confidence=paper.ai_confidence,
        pdf_path=paper.pdf_path,
        pdf_text_extracted=paper.pdf_text_extracted,
        pdf_status=paper.pdf_status or ("obtido" if paper.pdf_path else "ausente"),
        pdf_strategy=paper.pdf_strategy or "",
        pdf_resolved_url=paper.pdf_resolved_url or "",
        pdf_page_count=paper.pdf_page_count or 0,
        pdf_is_scanned=bool(paper.pdf_is_scanned),
        sources=sources,
        criteria_evaluations=criteria_evaluations,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
    )


@router.get("", response_model=PaperListResponse)
def list_papers(
    project_id: str,
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(25, ge=1, le=200, description="Itens por página"),
    decision: Optional[str] = Query(None, description="Filtrar por decisão: Pendente, Incluído, Excluído"),
    search: Optional[str] = Query(None, description="Busca textual em título, autores ou abstract"),
    source: Optional[str] = Query(None, description="Filtrar por base fonte"),
    include_duplicates: bool = Query(False, description="Se deve incluir registros marcados como duplicatas"),
    db: Session = Depends(get_db),
):
    """Lista artigos de um projeto com filtros e paginação."""
    query = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
        )
        .filter(PaperModel.project_id == project_id)
    )

    if not include_duplicates:
        query = query.filter(or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)))

    if decision:
        query = query.filter(func.lower(PaperModel.decision) == decision.lower())

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                PaperModel.title.ilike(search_term),
                PaperModel.authors.ilike(search_term),
                PaperModel.abstract.ilike(search_term),
            )
        )

    if source:
        query = query.join(PaperSourceModel).filter(PaperSourceModel.source_name == source)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    papers = (
        query.order_by(PaperModel.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaperListResponse(
        items=[_serialize_paper(p) for p in papers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=PaperResponse, status_code=201)
def create_paper(
    project_id: str,
    data: PaperCreate,
    db: Session = Depends(get_db),
):
    """Adiciona manualmente um artigo a um projeto."""
    norm_title = _normalize_title(data.title)
    paper = PaperModel(
        project_id=project_id,
        title=data.title,
        title_normalized=norm_title,
        authors=data.authors,
        year=data.year,
        doi=data.doi,
        abstract=data.abstract,
        research_type=data.research_type,
        institution=data.institution,
        download_url=data.download_url,
        decision=data.decision.value if hasattr(data.decision, "value") else data.decision,
        observations=data.observations,
        ai_confidence=data.ai_confidence,
    )
    db.add(paper)
    db.flush()

    for s in data.sources:
        db.add(PaperSourceModel(paper_id=paper.id, source_name=s))

    if data.criteria_evaluations:
        for crit_id, val in data.criteria_evaluations.items():
            db.add(PaperCriterionModel(paper_id=paper.id, criterion_id=crit_id, value=val))

    db.commit()
    db.expire(paper)
    paper = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
        )
        .filter(PaperModel.project_id == project_id, PaperModel.id == paper.id)
        .first()
    )
    return _serialize_paper(paper)


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Obtém detalhes de um artigo específico."""
    paper = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
        )
        .filter(PaperModel.project_id == project_id, PaperModel.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Artigo não encontrado.")
    return _serialize_paper(paper)


@router.patch("/{paper_id}", response_model=PaperResponse)
def update_paper(
    project_id: str,
    paper_id: str,
    data: PaperUpdate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Atualiza decisão, observações e critérios de triagem do artigo."""
    paper = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
        )
        .filter(PaperModel.project_id == project_id, PaperModel.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Artigo não encontrado.")

    if data.decision is not None:
        dec_val = data.decision.value if hasattr(data.decision, "value") else data.decision
        if dec_val != paper.decision:
            # Registrar no log de auditoria, com autoria (doc 29 §29.3.5).
            # `source="manual"` sozinho não distinguia o pesquisador do coautor
            # — e numa revisão sistemática saber de quem foi a decisão é parte
            # do produto, não um detalhe operacional.
            audit = AuditLogModel(
                paper_id=paper.id,
                action="decision_changed",
                old_value=paper.decision,
                new_value=dec_val,
                source="manual",
                user_id=usuario.id,
                username=usuario.username,
            )
            db.add(audit)
            paper.decision = dec_val

    if data.observations is not None:
        paper.observations = data.observations

    if data.abstract is not None:
        paper.abstract = data.abstract

    if data.title is not None:
        paper.title = data.title
        paper.title_normalized = _normalize_title(data.title)

    if data.authors is not None:
        paper.authors = data.authors

    if data.year is not None:
        paper.year = data.year

    if data.doi is not None:
        paper.doi = data.doi

    if data.download_url is not None:
        paper.download_url = data.download_url

    if data.criteria_evaluations is not None:
        for crit_id, val in data.criteria_evaluations.items():
            eval_record = (
                db.query(PaperCriterionModel)
                .filter(
                    PaperCriterionModel.paper_id == paper.id,
                    PaperCriterionModel.criterion_id == crit_id,
                )
                .first()
            )
            if eval_record:
                eval_record.value = val
            else:
                db.add(
                    PaperCriterionModel(
                        paper_id=paper.id,
                        criterion_id=crit_id,
                        value=val,
                    )
                )

    db.commit()
    db.expire(paper)
    paper = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
        )
        .filter(PaperModel.project_id == project_id, PaperModel.id == paper_id)
        .first()
    )
    return _serialize_paper(paper)

