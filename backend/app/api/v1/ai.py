#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Configurações de IA e Sugestão de Protocolos."""

import json
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.ai.factory import AIFactory
from app.infrastructure.persistence.models import AISettingsModel
from app.schemas.ai import (
    AISettingsResponse,
    AISettingsUpdate,
    FieldAssistRequest,
    FieldAssistResponse,
    ProtocolSuggestRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


def _parse_keys_json(raw_text: Optional[str]) -> List[str]:
    """Deserializa JSON array de chaves com fallback resiliente."""
    if not raw_text:
        return []
    try:
        data = json.loads(raw_text)
        if isinstance(data, list):
            return [str(k).strip() for k in data if str(k).strip()]
        elif isinstance(data, str) and data.strip():
            return [data.strip()]
        return []
    except Exception:
        return [raw_text.strip()] if raw_text.strip() else []


@router.get("/settings", response_model=AISettingsResponse)
def get_ai_settings(db: Session = Depends(get_db)):
    """Obtém as configurações de IA ativas e as chaves de cada provedor de forma isolada."""
    settings = db.query(AISettingsModel).first()
    if not settings:
        return AISettingsResponse(
            ai_enabled=True,
            provider="gemini",
            model="gemini-3.6-flash",
            has_api_keys=False,
            api_keys=[],
            gemini_api_keys=[],
            qwen_api_keys=[],
            local_api_keys=[],
            endpoint=None,
            temperature=0.2,
            max_tokens=4096,
        )

    gemini_keys = _parse_keys_json(settings.gemini_api_keys_encrypted)
    qwen_keys = _parse_keys_json(settings.qwen_api_keys_encrypted)
    local_keys = _parse_keys_json(settings.local_api_keys_encrypted)
    legacy_keys = _parse_keys_json(settings.api_keys_encrypted)

    # Migração / fallback suave se as colunas novas ainda estiverem vazias
    provider = (settings.provider or "gemini").lower()
    if not gemini_keys and provider == "gemini" and legacy_keys:
        gemini_keys = legacy_keys
    if not qwen_keys and provider == "qwen" and legacy_keys:
        qwen_keys = legacy_keys

    active_keys = (
        gemini_keys if provider == "gemini"
        else qwen_keys if provider == "qwen"
        else local_keys
    )

    return AISettingsResponse(
        ai_enabled=settings.ai_enabled,
        provider=settings.provider,
        model=settings.model,
        has_api_keys=len(active_keys) > 0,
        api_keys=active_keys,
        gemini_api_keys=gemini_keys,
        qwen_api_keys=qwen_keys,
        local_api_keys=local_keys,
        endpoint=settings.endpoint,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )


@router.put("/settings", response_model=AISettingsResponse)
def update_ai_settings(data: AISettingsUpdate, db: Session = Depends(get_db)):
    """Atualiza as configurações e chaves dos provedores de IA mantendo isolamento total."""
    settings = db.query(AISettingsModel).first()
    if not settings:
        settings = AISettingsModel()
        db.add(settings)

    provider = data.provider.lower()
    settings.ai_enabled = data.ai_enabled
    settings.provider = provider
    settings.model = data.model
    settings.endpoint = data.endpoint
    settings.temperature = data.temperature
    settings.max_tokens = data.max_tokens

    # Atualizar chaves do Gemini se enviadas
    if data.gemini_api_keys is not None:
        clean_gemini = [k.strip() for k in data.gemini_api_keys if k and k.strip()]
        settings.gemini_api_keys_encrypted = json.dumps(clean_gemini)
    elif provider == "gemini" and data.api_keys is not None:
        clean_gemini = [k.strip() for k in data.api_keys if k and k.strip()]
        settings.gemini_api_keys_encrypted = json.dumps(clean_gemini)

    # Atualizar chaves do Qwen se enviadas
    if data.qwen_api_keys is not None:
        clean_qwen = [k.strip() for k in data.qwen_api_keys if k and k.strip()]
        settings.qwen_api_keys_encrypted = json.dumps(clean_qwen)
    elif provider == "qwen" and data.api_keys is not None:
        clean_qwen = [k.strip() for k in data.api_keys if k and k.strip()]
        settings.qwen_api_keys_encrypted = json.dumps(clean_qwen)

    # Atualizar chaves locais se enviadas
    if data.local_api_keys is not None:
        clean_local = [k.strip() for k in data.local_api_keys if k and k.strip()]
        settings.local_api_keys_encrypted = json.dumps(clean_local)
    elif provider == "local" and data.api_keys is not None:
        clean_local = [k.strip() for k in data.api_keys if k and k.strip()]
        settings.local_api_keys_encrypted = json.dumps(clean_local)

    # Se api_keys genérico foi passado, atualizar legado para retrocompatibilidade
    if data.api_keys is not None:
        clean_legacy = [k.strip() for k in data.api_keys if k and k.strip()]
        settings.api_keys_encrypted = json.dumps(clean_legacy)

    db.commit()
    db.refresh(settings)

    gemini_keys = _parse_keys_json(settings.gemini_api_keys_encrypted)
    qwen_keys = _parse_keys_json(settings.qwen_api_keys_encrypted)
    local_keys = _parse_keys_json(settings.local_api_keys_encrypted)

    active_keys = (
        gemini_keys if provider == "gemini"
        else qwen_keys if provider == "qwen"
        else local_keys
    )

    return AISettingsResponse(
        ai_enabled=settings.ai_enabled,
        provider=settings.provider,
        model=settings.model,
        has_api_keys=len(active_keys) > 0,
        api_keys=active_keys,
        gemini_api_keys=gemini_keys,
        qwen_api_keys=qwen_keys,
        local_api_keys=local_keys,
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
        suggestions = await client.generate_protocol_suggestions(
            title=data.title,
            methodology=data.methodology,
            initial_description=data.description,
        )
        return suggestions
    except Exception as e:
        logger.error(f"[AI] Erro ao sugerir protocolo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assist-field", response_model=FieldAssistResponse)
async def assist_field(data: FieldAssistRequest, db: Session = Depends(get_db)):
    """Preenche, corrige ou aprimora o conteúdo de um campo específico com IA baseada nas diretrizes do item."""
    settings = db.query(AISettingsModel).first()
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de IA estão desativados nas Configurações (Modo 100% Manual). Ative a IA para usar o assistente.",
        )

    client = AIFactory.get_client(db)
    try:
        result = await client.assist_field(
            field_label=data.field_label,
            field_guidelines=data.field_guidelines,
            current_value=data.current_value,
            project_title=data.project_title,
            methodology=data.methodology,
            project_context=data.project_context,
            action=data.action,
            custom_instruction=data.custom_instruction,
        )
        return FieldAssistResponse(
            field_id=data.field_id,
            suggested_text=result.get("suggested_text", ""),
            explanation=result.get("explanation", ""),
            model_used=result.get("model_used", client.model_name),
            provider=result.get("provider", client.provider_name),
        )
    except Exception as e:
        logger.error(f"[AI] Erro ao processar assistente de campo para '{data.field_label}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

