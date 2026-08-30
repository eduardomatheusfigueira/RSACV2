#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Router do Catálogo Metodológico de Protocolos (Doc 45)."""

from fastapi import APIRouter
from app.schemas.protocol import ProtocolCatalogResponse, ReviewDesignMeta
from app.services.protocol_catalog_service import (
    get_full_protocol_catalog,
    get_review_design,
)

router = APIRouter(prefix="/protocol-catalog", tags=["protocol-catalog"])


@router.get("", response_model=ProtocolCatalogResponse)
def get_catalog():
    """Retorna o catálogo completo de desenhos, diretrizes, padrões, frameworks e instrumentos."""
    return get_full_protocol_catalog()


@router.get("/designs/{design_id}", response_model=ReviewDesignMeta)
def get_design_details(design_id: str):
    """Retorna os metadados e perguntas de extração sugeridas de um desenho de revisão."""
    design = get_review_design(design_id)
    if not design:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Desenho de revisão '{design_id}' não encontrado.")
    return design
