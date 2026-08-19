#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Router de Configurações de IA e Sugestão de Protocolos."""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.ai.factory import AIFactory
from app.infrastructure.persistence.models import AISettingsModel, UserModel
from app.schemas.ai import (
    AISettingsResponse,
    AISettingsUpdate,
    FieldAssistRequest,
    FieldAssistResponse,
    ProtocolSuggestRequest,
)
from app.security import mask_secret_list
from app.security.dependencies import require_owner

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


def _keys_by_provider(settings: AISettingsModel) -> dict[str, List[str]]:
    """Chaves em claro de cada provedor, com o fallback do campo legado."""
    gemini = _parse_keys_json(settings.gemini_api_keys_encrypted)
    qwen = _parse_keys_json(settings.qwen_api_keys_encrypted)
    local = _parse_keys_json(settings.local_api_keys_encrypted)
    legacy = _parse_keys_json(settings.api_keys_encrypted)

    # Migração / fallback suave se as colunas novas ainda estiverem vazias
    provider = (settings.provider or "gemini").lower()
    if not gemini and provider == "gemini" and legacy:
        gemini = legacy
    if not qwen and provider == "qwen" and legacy:
        qwen = legacy

    return {"gemini": gemini, "qwen": qwen, "local": local}


def _build_settings_response(settings: AISettingsModel) -> AISettingsResponse:
    """
    Monta a resposta pública das configurações de IA.

    Ponto único de saída dessas configurações: as chaves saem **sempre**
    mascaradas (doc 29 §29.4.2). Manter um só construtor é o que impede que a
    próxima rota a devolver `AISettingsResponse` reintroduza o vazamento.
    """
    keys = _keys_by_provider(settings)
    provider = (settings.provider or "gemini").lower()
    active = keys.get(provider, [])

    return AISettingsResponse(
        ai_enabled=settings.ai_enabled,
        provider=settings.provider,
        model=settings.model,
        has_api_keys=len(active) > 0,
        key_previews=mask_secret_list(active),
        gemini_key_previews=mask_secret_list(keys["gemini"]),
        qwen_key_previews=mask_secret_list(keys["qwen"]),
        local_key_previews=mask_secret_list(keys["local"]),
        gemini_keys_count=len(keys["gemini"]),
        qwen_keys_count=len(keys["qwen"]),
        local_keys_count=len(keys["local"]),
        endpoint=settings.endpoint,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )


@router.get("/settings", response_model=AISettingsResponse)
def get_ai_settings(
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_owner),
):
    """Configurações de IA ativas e a máscara das chaves de cada provedor."""
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
    return _build_settings_response(settings)


@router.put("/settings", response_model=AISettingsResponse)
def update_ai_settings(
    data: AISettingsUpdate,
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_owner),
):
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

    # Gravação write-only das chaves (doc 29 §29.4.2).
    #
    # `_assign_keys` ignora lista vazia de propósito: a interface agora exibe
    # máscaras, e um formulário salvo sem tocar no campo de chaves chegava aqui
    # como lista vazia. Sob a regra antiga isso apagaria a credencial em
    # silêncio. Apagar passou a exigir DELETE explícito.
    def _assign_keys(column: str, values: Optional[List[str]]) -> None:
        if values is None:
            return
        clean = [k.strip() for k in values if k and k.strip()]
        if not clean:
            return
        setattr(settings, column, json.dumps(clean))

    _assign_keys("gemini_api_keys_encrypted", data.gemini_api_keys)
    _assign_keys("qwen_api_keys_encrypted", data.qwen_api_keys)
    _assign_keys("local_api_keys_encrypted", data.local_api_keys)

    # `api_keys` genérico atualiza o provedor ativo e o campo legado
    if data.api_keys is not None:
        _assign_keys(f"{provider}_api_keys_encrypted", data.api_keys)
        _assign_keys("api_keys_encrypted", data.api_keys)

    db.commit()
    db.refresh(settings)

    return _build_settings_response(settings)


@router.delete("/settings/keys/{provider}", response_model=AISettingsResponse)
def delete_provider_keys(
    provider: str,
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_owner),
):
    """
    Remove todas as chaves de um provedor.

    Contrapartida da regra write-only: como o PUT deixou de apagar chave por
    lista vazia, a remoção precisa de um verbo próprio e intencional.
    """
    target = provider.lower()
    if target not in ("gemini", "qwen", "local"):
        raise HTTPException(
            status_code=400,
            detail=f"Provedor '{provider}' não é suportado. Use gemini, qwen ou local.",
        )

    settings = db.query(AISettingsModel).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Nenhuma configuração de IA cadastrada.")

    setattr(settings, f"{target}_api_keys_encrypted", "[]")
    # O campo legado espelha o provedor ativo — limpar junto evita que a chave
    # apagada volte pelo fallback de retrocompatibilidade.
    if (settings.provider or "").lower() == target:
        settings.api_keys_encrypted = "[]"

    db.commit()
    db.refresh(settings)
    logger.info("[AI] Chaves do provedor '%s' removidas a pedido do usuário.", target)

    return _build_settings_response(settings)


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

