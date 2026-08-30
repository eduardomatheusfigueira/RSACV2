#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Router de Triagem (Conflitos, Resoluções e Métricas de Concordância)."""

import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.domain.collaboration import politica_de
from app.infrastructure.persistence.models import (
    AuditLogModel,
    PaperCriterionModel,
    PaperModel,
    PaperScreeningModel,
    ProjectMemberModel,
    UserModel,
    utcnow,
)
from app.security.dependencies import (
    exige_coordenador,
    projeto_do_usuario,
    require_session,
)
from app.services.agreement_service import calcular_concordancia_projeto
from app.services.blindness import visao_do_revisor
from app.services.harvesting_service import ws_manager
from app.schemas.paper import (
    ConflictResolutionRequest,
    PaperResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/screening",
    dependencies=[Depends(projeto_do_usuario)],
    tags=["screening"],
)


@router.get("/conflitos", response_model=List[PaperResponse])
def list_conflicts(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_coordenador),
):
    """
    Lista todos os artigos com divergência de triagem (conflito entre revisores).

    Acesso restrito à coordenação (Doc 43 §43.8.3). Aqui a cegueira é suspensa
    para permitir ao coordenador analisar ambos os pareceres e critérios lado a lado.
    """
    projeto = getattr(request.state, "projeto", None)
    politica = politica_de(projeto) if projeto else politica_de(None)

    papers = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.sources),
            selectinload(PaperModel.criteria_evaluations),
            selectinload(PaperModel.screenings).selectinload(PaperScreeningModel.reviewer),
            selectinload(PaperModel.conflict_resolver),
        )
        .filter(
            PaperModel.project_id == project_id,
            PaperModel.screening_status == "conflito",
        )
        .order_by(PaperModel.updated_at.desc())
        .all()
    )

    # Coordenador recebendo a fila de conflitos: is_coordinator=True desbloqueia os julgamentos
    return [visao_do_revisor(p, usuario.id, is_coordinator=True, politica=politica) for p in papers]


@router.post("/conflitos/{paper_id}/resolver", response_model=PaperResponse)
async def resolve_conflict(
    project_id: str,
    paper_id: str,
    data: ConflictResolutionRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
    _membro: ProjectMemberModel = Depends(exige_coordenador),
):
    """
    Registra a decisão arbitral do coordenador desempatando um estudo em conflito (Doc 43 §43.8).
    """
    projeto = getattr(request.state, "projeto", None)
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

    dec_val = data.decision.value if hasattr(data.decision, "value") else str(data.decision)

    old_decision = paper.decision
    paper.decision = dec_val
    paper.screening_status = "resolvido"
    paper.conflict_resolved_by_user_id = usuario.id
    paper.conflict_resolved_at = utcnow()
    if data.observations is not None:
        paper.observations = data.observations
    paper.updated_at = utcnow()

    # Sincronizar critérios avaliados pelo resolvedor
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
                eval_record.value = bool(val)
            else:
                db.add(
                    PaperCriterionModel(
                        paper_id=paper.id,
                        criterion_id=crit_id,
                        value=bool(val),
                    )
                )

    # Log de auditoria da resolução de conflito
    audit = AuditLogModel(
        paper_id=paper.id,
        action="conflict_resolved",
        old_value=f"conflito:{old_decision}",
        new_value=dec_val,
        source="coordenador",
        user_id=usuario.id,
        username=usuario.username,
    )
    db.add(audit)
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

    # Notificação via WebSocket
    await ws_manager.broadcast(
        project_id,
        {
            "type": "paper.decidido",
            "paper_id": paper.id,
            "decision": paper.decision,
            "screening_status": "resolvido",
            "por": usuario.username,
            "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
        },
    )

    return visao_do_revisor(paper, usuario.id, is_coordinator=True, politica=politica)


@router.get("/concordancia")
def get_agreement_metrics(
    project_id: str,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """
    Retorna os coeficientes de concordância interobservador (Kappa de Cohen, concordância bruta e matriz cruzada).
    """
    return calcular_concordancia_projeto(db, project_id)
