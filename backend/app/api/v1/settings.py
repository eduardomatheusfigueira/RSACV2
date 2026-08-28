#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router para Configurações de Fontes e Credenciais de Coleta."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.harvesters.factory import HarvesterFactory
from app.infrastructure.persistence.models import SourceCredentialModel, UserModel
from app.schemas.settings import SourceCredentialResponse, SourceCredentialUpdate
from app.security.dependencies import require_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/sources", tags=["settings"])


def _mask_key(key: str | None) -> str:
    """Retorna máscara de segurança exibindo apenas os últimos 4 dígitos."""
    if not key or len(key.strip()) == 0:
        return ""
    clean = key.strip()
    if len(clean) <= 4:
        return "••••"
    return "••••••••" + clean[-4:]


@router.get("", response_model=List[SourceCredentialResponse])
def list_source_credentials(
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Lista todas as fontes com seus respectivos status de credenciais configuradas."""
    available_sources = HarvesterFactory.get_all_available()
    saved_creds = {
        r.source_name.upper(): r
        for r in db.query(SourceCredentialModel)
        .filter(SourceCredentialModel.user_id == usuario.id)
        .all()
    }

    result = []
    for s in available_sources:
        cred = saved_creds.get(s.upper())
        has_key = bool(cred and cred.api_key)
        has_inst = bool(cred and cred.inst_token)

        result.append(
            SourceCredentialResponse(
                source_name=s,
                has_api_key=has_key,
                key_preview=_mask_key(cred.api_key if cred else None),
                has_inst_token=has_inst,
                inst_token_preview=_mask_key(cred.inst_token if cred else None),
                custom_endpoint=cred.custom_endpoint if cred else None,
                updated_at=cred.updated_at if cred else None,
            )
        )

    return result


@router.put("/{source_name}", response_model=SourceCredentialResponse)
def update_source_credential(
    source_name: str,
    data: SourceCredentialUpdate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Salva ou atualiza a chave de API/token institucional de uma base científica."""
    s_upper = source_name.upper()
    if s_upper not in [s.upper() for s in HarvesterFactory.get_all_available()]:
        raise HTTPException(status_code=400, detail=f"Fonte '{source_name}' não é suportada.")

    cred = (
        db.query(SourceCredentialModel)
        .filter(
            SourceCredentialModel.user_id == usuario.id,
            SourceCredentialModel.source_name == s_upper,
        )
        .first()
    )
    if not cred:
        cred = SourceCredentialModel(user_id=usuario.id, source_name=s_upper)
        db.add(cred)

    if data.api_key is not None:
        cred.api_key = data.api_key.strip()

    if data.inst_token is not None:
        cred.inst_token = data.inst_token.strip()

    if data.custom_endpoint is not None:
        cred.custom_endpoint = data.custom_endpoint.strip() if data.custom_endpoint else None

    db.commit()
    db.refresh(cred)

    return SourceCredentialResponse(
        source_name=source_name,
        has_api_key=bool(cred.api_key),
        key_preview=_mask_key(cred.api_key),
        has_inst_token=bool(cred.inst_token),
        inst_token_preview=_mask_key(cred.inst_token),
        custom_endpoint=cred.custom_endpoint,
        updated_at=cred.updated_at,
    )


@router.delete("/{source_name}")
def delete_source_credential(
    source_name: str,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Remove as credenciais salvas de uma base científica."""
    s_upper = source_name.upper()
    cred = (
        db.query(SourceCredentialModel)
        .filter(
            SourceCredentialModel.user_id == usuario.id,
            SourceCredentialModel.source_name == s_upper,
        )
        .first()
    )
    if cred:
        db.delete(cred)
        db.commit()

    return {"status": "ok", "message": f"Credenciais da fonte '{source_name}' removidas."}
