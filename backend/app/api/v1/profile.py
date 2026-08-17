#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router para Backup e Restauração de Chaves e Perfil de Workspace."""

import json
import logging
from typing import Any, Dict
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.profile import (
    KeysBackupData,
    KeysImportResponse,
    ProfileExportRequest,
    ProfileImportResponse,
)
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])
profile_service = ProfileService()


@router.get("/keys/export", response_model=KeysBackupData)
def export_keys(db: Session = Depends(get_db)):
    """Exporta arquivo estruturado contendo todas as chaves de API e credenciais cadastradas."""
    try:
        return profile_service.export_keys(db)
    except Exception as e:
        logger.error(f"[Profile] Erro ao exportar chaves: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Falha ao exportar chaves de API: {str(e)}")


@router.post("/keys/import", response_model=KeysImportResponse)
def import_keys(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Importa e aplica um arquivo estruturado de chaves de API (.json ou texto formatado).
    Atualiza as configurações do Gemini, Qwen e credenciais de bases científicas.
    """
    try:
        raw_content = payload.get("raw_content")
        target_input = raw_content if raw_content else payload
        return profile_service.import_keys(db, target_input)
    except Exception as e:
        logger.error(f"[Profile] Erro ao importar chaves: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Falha ao importar chaves de API: {str(e)}")


@router.post("/export")
def export_full_profile(
    request: ProfileExportRequest = Body(default_factory=ProfileExportRequest),
    db: Session = Depends(get_db),
):
    """
    Exporta o perfil completo de sessão, preferências, configurações de IA,
    credenciais de fontes e todos os projetos com artigos, protocolos e extrações.
    """
    try:
        session_prefs = request.session_preferences.model_dump() if request.session_preferences else {}
        return profile_service.export_profile(db, session_prefs)
    except Exception as e:
        logger.error(f"[Profile] Erro ao exportar perfil completo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Falha ao exportar perfil completo: {str(e)}")


@router.post("/import", response_model=ProfileImportResponse)
def import_full_profile(
    profile_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Restaura um perfil completo de sessão e workspace.
    Sincroniza projetos, protocolos, artigos, extrações, chaves e preferências.
    """
    try:
        if not isinstance(profile_data, dict):
            raise ValueError("O conteúdo do perfil deve ser um objeto JSON válido.")
        
        # Aceitar tanto envelope { "profile_data": { ... } } quanto { "schema_version": ... }
        data = profile_data.get("profile_data", profile_data)
        return profile_service.import_profile(db, data)
    except Exception as e:
        logger.error(f"[Profile] Erro ao restaurar perfil completo: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Falha ao restaurar perfil: {str(e)}")
