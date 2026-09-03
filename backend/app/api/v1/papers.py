#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Router de Artigos (Papers)."""

import json
import logging
import math
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, func

from app.api.deps import get_db
from app.domain.collaboration import politica_de
from app.domain.triabilidade import filtro_com_resumo, filtro_sem_resumo
from app.infrastructure.persistence.models import (
    AuditLogModel,
    PaperCriterionModel,
    PaperModel,
    PaperScreeningModel,
    PaperSourceModel,
    ProjectMemberModel,
    UserModel,
    utcnow,
)
from app.security.dependencies import (
    exige_revisor_ou_coordenador,
    projeto_do_usuario,
    require_session,
)
from app.services.blindness import visao_do_revisor
from app.services.consolidation_service import consolidar
from app.services.harvesting_service import ws_manager
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


@router.get("", response_model=PaperListResponse)
def list_papers(
    project_id: str,
    request: Request,
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(25, ge=1, le=200, description="Itens por página"),
    decision: Optional[str] = Query(None, description="Filtrar por decisão: Pendente, Incluído, Excluído"),
    screening_status: Optional[str] = Query(None, description="Filtrar por status de triagem"),
    search: Optional[str] = Query(None, description="Busca textual em título, autores ou abstract"),
    source: Optional[str] = Query(None, description="Filtrar por base fonte"),
    sort_by: str = Query("year_desc", description="Critério de ordenação: year_desc, year_asc, title_asc, title_desc, authors_asc, authors_desc, confidence_desc, confidence_asc, updated_desc, created_desc"),
    include_duplicates: bool = Query(False, description="Se deve incluir registros marcados como duplicatas"),
    com_resumo: Optional[bool] = Query(
        None,
        description=(
            "Recorta por triabilidade: `true` devolve só o que tem resumo utilizável "
            "(a fila da triagem assistida), `false` só o que não tem. Omitido, devolve "
            "os dois — um registro sem resumo continua no acervo e continua contando "
            "no fluxo PRISMA."
        ),
    ),
    db: Session = Depends(get_db),
    usuario: Optional[UserModel] = Depends(require_session),
):
    """Lista artigos de um projeto com filtros, ordenação configurável, paginação e proteção de cegueira no servidor."""
    projeto = getattr(request.state, "projeto", None)
    membro = getattr(request.state, "membro", None)
    is_coordinator = bool(membro and membro.project_role == "coordenador")
    politica = politica_de(projeto) if projeto else politica_de(None)
    user_id = usuario.id if usuario else None

    query = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
            selectinload(PaperModel.screenings).selectinload(PaperScreeningModel.reviewer),
            selectinload(PaperModel.conflict_resolver),
        )
        .filter(PaperModel.project_id == project_id)
    )

    if not include_duplicates:
        query = query.filter(or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)))

    if com_resumo is True:
        query = query.filter(filtro_com_resumo(PaperModel))
    elif com_resumo is False:
        query = query.filter(filtro_sem_resumo(PaperModel))

    if screening_status:
        query = query.filter(func.lower(PaperModel.screening_status) == screening_status.lower())

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

    # Mapeamento de ordenação (ano mais recente primeiro por padrão)
    sort_key = (sort_by or "year_desc").lower().strip()
    year_expr = func.nullif(PaperModel.year, "")

    if sort_key == "year_asc":
        query = query.order_by(year_expr.asc().nullslast(), PaperModel.created_at.asc())
    elif sort_key == "title_asc":
        query = query.order_by(PaperModel.title.asc().nullslast())
    elif sort_key == "title_desc":
        query = query.order_by(PaperModel.title.desc().nullslast())
    elif sort_key == "authors_asc":
        query = query.order_by(PaperModel.authors.asc().nullslast())
    elif sort_key == "authors_desc":
        query = query.order_by(PaperModel.authors.desc().nullslast())
    elif sort_key == "confidence_desc":
        query = query.order_by(PaperModel.ai_confidence.desc().nullslast(), year_expr.desc().nullslast())
    elif sort_key == "confidence_asc":
        query = query.order_by(PaperModel.ai_confidence.asc().nullslast(), year_expr.desc().nullslast())
    elif sort_key == "updated_desc":
        query = query.order_by(PaperModel.updated_at.desc())
    elif sort_key == "created_desc":
        query = query.order_by(PaperModel.created_at.desc())
    else:  # Padrão: year_desc (ano mais recente primeiro, mais antigos depois, nulos por último)
        query = query.order_by(year_expr.desc().nullslast(), PaperModel.created_at.desc())

    papers = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaperListResponse(
        items=[visao_do_revisor(p, user_id, is_coordinator, politica) for p in papers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=PaperResponse, status_code=201)
def create_paper(
    project_id: str,
    data: PaperCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_revisor_ou_coordenador),
):
    """Adiciona manualmente um artigo a um projeto."""
    projeto = getattr(request.state, "projeto", None)
    is_coordinator = bool(_membro and _membro.project_role == "coordenador")
    politica = politica_de(projeto) if projeto else politica_de(None)

    norm_title = _normalize_title(data.title)
    dec_val = data.decision.value if hasattr(data.decision, "value") else str(data.decision)

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
        decision="Pendente" if politica.triagem_cega else dec_val,
        observations=data.observations,
        ai_confidence=data.ai_confidence,
        screening_status="aguardando" if dec_val == "Pendente" else "consenso",
    )
    db.add(paper)
    db.flush()

    for s in data.sources:
        db.add(PaperSourceModel(paper_id=paper.id, source_name=s))

    if data.criteria_evaluations:
        for crit_id, val in data.criteria_evaluations.items():
            db.add(PaperCriterionModel(paper_id=paper.id, criterion_id=crit_id, value=val))

    # Criar julgamento inicial do autor se decisão informada
    if dec_val != "Pendente":
        screening = PaperScreeningModel(
            paper_id=paper.id,
            reviewer_id=usuario.id,
            decision=dec_val,
            observations=data.observations or "",
            criteria_evaluations=json.dumps(data.criteria_evaluations or {}),
            decided_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(screening)
        db.flush()
        consolidar(db, paper, politica)

    db.commit()
    db.expire(paper)
    paper = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
            selectinload(PaperModel.screenings).selectinload(PaperScreeningModel.reviewer),
            selectinload(PaperModel.conflict_resolver),
        )
        .filter(PaperModel.project_id == project_id, PaperModel.id == paper.id)
        .first()
    )
    return visao_do_revisor(paper, usuario.id, is_coordinator, politica)


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(
    project_id: str,
    paper_id: str,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Optional[UserModel] = Depends(require_session),
):
    """Obtém detalhes de um artigo específico respeitando o isolamento de cegueira."""
    projeto = getattr(request.state, "projeto", None)
    membro = getattr(request.state, "membro", None)
    is_coordinator = bool(membro and membro.project_role == "coordenador")
    politica = politica_de(projeto) if projeto else politica_de(None)
    user_id = usuario.id if usuario else None

    paper = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
            selectinload(PaperModel.screenings).selectinload(PaperScreeningModel.reviewer),
            selectinload(PaperModel.conflict_resolver),
        )
        .filter(PaperModel.project_id == project_id, PaperModel.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Artigo não encontrado.")
    return visao_do_revisor(paper, user_id, is_coordinator, politica)


@router.patch("/{paper_id}", response_model=PaperResponse)
async def update_paper(
    project_id: str,
    paper_id: str,
    data: PaperUpdate,
    request: Request,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_revisor_ou_coordenador),
):
    """Atualiza decisão, observações e critérios de triagem com concorrência otimista e consolidação."""
    projeto = getattr(request.state, "projeto", None)
    is_coordinator = bool(_membro and _membro.project_role == "coordenador")
    politica = politica_de(projeto) if projeto else politica_de(None)

    paper = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
            selectinload(PaperModel.screenings).selectinload(PaperScreeningModel.reviewer),
            selectinload(PaperModel.conflict_resolver),
        )
        .filter(PaperModel.project_id == project_id, PaperModel.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Artigo não encontrado.")

    # Controle de concorrência otimista (Doc 43 §43.12.2)
    if if_match and paper.updated_at:
        clean_match = if_match.strip('"').strip()
        current_iso = paper.updated_at.isoformat()
        if clean_match != current_iso and clean_match != str(paper.updated_at):
            raise HTTPException(
                status_code=409,
                detail="Conflito de concorrência: o estudo foi alterado por outro revisor desde a sua última leitura.",
            )

    # Atualização de campos bibliográficos
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

    # Processamento do julgamento individual de triagem do ator logado
    is_screening_update = (
        data.decision is not None
        or data.observations is not None
        or data.criteria_evaluations is not None
    )

    if is_screening_update:
        screening = (
            db.query(PaperScreeningModel)
            .filter(
                PaperScreeningModel.paper_id == paper.id,
                PaperScreeningModel.reviewer_id == usuario.id,
            )
            .first()
        )
        if not screening:
            screening = PaperScreeningModel(
                paper_id=paper.id,
                reviewer_id=usuario.id,
            )
            db.add(screening)
            if paper.screenings is None:
                paper.screenings = []
            paper.screenings.append(screening)

        if data.decision is not None:
            dec_val = data.decision.value if hasattr(data.decision, "value") else str(data.decision)
            if dec_val != screening.decision:
                screening.decision = dec_val
                screening.decided_at = utcnow()
                # Auditoria da decisão individual do revisor
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

        if data.observations is not None:
            screening.observations = data.observations

        if data.criteria_evaluations is not None:
            screening.criteria_evaluations = json.dumps(data.criteria_evaluations)
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
                    eval_record.value = bool(val)
                else:
                    db.add(
                        PaperCriterionModel(
                            paper_id=paper.id,
                            criterion_id=crit_id,
                            value=bool(val),
                        )
                    )

        screening.updated_at = utcnow()
        db.flush()

        # Executa a consolidação na mesma transação (Doc 43 §43.8)
        consolidar(db, paper, politica)

    paper.updated_at = utcnow()
    db.commit()
    db.expire(paper)

    paper = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
            selectinload(PaperModel.screenings).selectinload(PaperScreeningModel.reviewer),
            selectinload(PaperModel.conflict_resolver),
        )
        .filter(PaperModel.project_id == project_id, PaperModel.id == paper_id)
        .first()
    )

    # Notificação em tempo real via WebSocket
    await ws_manager.broadcast(
        project_id,
        {
            "type": "paper.decidido",
            "paper_id": paper.id,
            "decision": paper.decision if not politica.triagem_cega or paper.screening_status in ("consenso", "resolvido") else "Pendente",
            "screening_status": paper.screening_status,
            "por": usuario.username,
            "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
        },
    )

    return visao_do_revisor(paper, usuario.id, is_coordinator, politica)
