#!/usr/bin/env python

"""Revsist — Router da Aba de B.I. e Bibliometria (doc 32)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.security.dependencies import projeto_do_usuario
from app.domain.enums import Decision
from app.infrastructure.persistence.models import ProjectModel
from app.schemas.insights import ProjectInsights
from app.services.insights_service import get_project_insights

logger = logging.getLogger(__name__)

# A titularidade entra como dependência do router, e não rota a rota (doc 40
# §40.3.2): é o mesmo padrão de `require_session`, e é o que faz uma rota
# nova nascer isolada sem depender de ninguém lembrar.
router = APIRouter(
    prefix="/projects/{project_id}/insights",
    dependencies=[Depends(projeto_do_usuario)],
    tags=["insights"],
)


@router.get("", response_model=ProjectInsights)
def get_insights(
    project_id: str,
    decision: Decision = Query(
        Decision.INCLUDED, description="Filtra os agregados de conteúdo por decisão"
    ),
    source: str | None = Query(
        None, description="Filtra os agregados de conteúdo por base de origem"
    ),
    year_from: int | None = Query(None, description="Ano inicial (inclusive) do recorte temporal"),
    year_to: int | None = Query(None, description="Ano final (inclusive) do recorte temporal"),
    instantaneo: str | None = Query(
        None,
        description=(
            "Calcula os agregados de conteúdo sobre um corpus congelado, "
            "em vez do acervo de agora (doc 48 §3)"
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Indicadores de B.I. e bibliometria do projeto (doc 32 §6).

    Os filtros restringem só os agregados de conteúdo — rankings, distribuição
    temporal, saúde de PDF. O funil PRISMA, o funil de critérios e a
    composição por base descrevem o projeto inteiro, sempre (doc 32 §3.2).
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")

    return get_project_insights(
        db,
        project_id,
        decision=decision.value,
        source=source,
        year_from=year_from,
        year_to=year_to,
        snapshot_id=instantaneo,
    )
