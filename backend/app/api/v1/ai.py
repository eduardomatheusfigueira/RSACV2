#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Configurações de IA e Sugestão de Protocolos."""

import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.ai.factory import AIFactory
from app.infrastructure.persistence.models import AISettingsModel
from app.schemas.ai import AISettingsResponse, AISettingsUpdate, ProtocolSuggestRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/settings", response_model=AISettingsResponse)
def get_ai_settings(db: Session = Depends(get_db)):
    """Obtém as configurações de IA ativas."""
    settings = db.query(AISettingsModel).first()
    if not settings:
        return AISettingsResponse(
            ai_enabled=True,
            provider="gemini",
            model="gemini-3.6-flash",
            has_api_keys=False,
            endpoint=None,
            temperature=0.2,
            max_tokens=4096,
        )

    try:
        keys = json.loads(settings.api_keys_encrypted) if settings.api_keys_encrypted else []
    except Exception:
        keys = []

    return AISettingsResponse(
        ai_enabled=settings.ai_enabled,
        provider=settings.provider,
        model=settings.model,
        has_api_keys=len(keys) > 0,
        endpoint=settings.endpoint,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )


@router.put("/settings", response_model=AISettingsResponse)
def update_ai_settings(data: AISettingsUpdate, db: Session = Depends(get_db)):
    """Atualiza as configurações e chaves dos provedores de IA."""
    settings = db.query(AISettingsModel).first()
    if not settings:
        settings = AISettingsModel()
        db.add(settings)

    settings.ai_enabled = data.ai_enabled
    settings.provider = data.provider.lower()
    settings.model = data.model
    settings.api_keys_encrypted = json.dumps([k.strip() for k in data.api_keys if k.strip()])
    settings.endpoint = data.endpoint
    settings.temperature = data.temperature
    settings.max_tokens = data.max_tokens

    db.commit()
    db.refresh(settings)

    return AISettingsResponse(
        ai_enabled=settings.ai_enabled,
        provider=settings.provider,
        model=settings.model,
        has_api_keys=len(data.api_keys) > 0,
        endpoint=settings.endpoint,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )


@router.post("/test")
async def test_ai_connection(db: Session = Depends(get_db)):
    """Testa conectividade com o provedor de IA ativo."""
    settings = db.query(AISettingsModel).first()
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de IA estão desativados nas Configurações (Modo 100% Manual). Ative a IA para testar a conexão.",
        )

    client = AIFactory.get_client(db)
    success = await client.test_connection()
    if not success:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao conectar com o provedor '{client.provider_name}' ({client.model_name}). Verifique a API Key ou endpoint.",
        )
    return {
        "status": "ok",
        "provider": client.provider_name,
        "model": client.model_name,
        "message": "Conexão com IA estabelecida com sucesso!",
    }


@router.post("/suggest-protocol")
async def suggest_protocol(data: ProtocolSuggestRequest, db: Session = Depends(get_db)):
    """Gera sugestões de PICO, descritores em pares e critérios via IA."""
    settings = db.query(AISettingsModel).first()
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de IA estão desativados nas Configurações (Modo 100% Manual).",
        )

    client = AIFactory.get_client(db)
    try:
        suggestions = await client.suggest_protocol(
            title=data.title,
            methodology=data.methodology,
            description=data.description,
        )
        return suggestions
    except Exception as e:
        logger.error(f"[AI] Erro ao sugerir protocolo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
