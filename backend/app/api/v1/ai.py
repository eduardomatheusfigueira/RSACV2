#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Router de Configurações de IA e Sugestão de Protocolos."""

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
from app.security.dependencies import require_session
from app.security.egress import EgressBlocked, validar_url
from app.security.middleware import erro_interno

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


def _settings_do_usuario(db: Session, usuario: UserModel) -> AISettingsModel | None:
    """Configuração de IA de quem está pedindo — nunca a de outro."""
    return (
        db.query(AISettingsModel).filter(AISettingsModel.user_id == usuario.id).first()
    )


def _obter_ou_criar_settings(db: Session, usuario: UserModel) -> AISettingsModel:
    """Configuração do usuário, criando-a vazia na primeira gravação."""
    settings = _settings_do_usuario(db, usuario)
    if settings is None:
        settings = AISettingsModel(user_id=usuario.id)
        db.add(settings)
    return settings


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
    usuario: UserModel = Depends(require_session),
):
    """Configurações de IA ativas e a máscara das chaves de cada provedor."""
    settings = _settings_do_usuario(db, usuario)
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
    usuario: UserModel = Depends(require_session),
):
    """Atualiza as configurações e chaves dos provedores de IA mantendo isolamento total."""
    settings = _obter_ou_criar_settings(db, usuario)

    provider = data.provider.lower()

    # O `endpoint` vira `base_url` do cliente OpenAI-compatível, e o servidor
    # passa a fazer POST **com a chave de API no cabeçalho** para esse host.
    # Sem validação, é exfiltração de credencial e SSRF na mesma requisição
    # (doc 28 V-05b). Loopback é aceito só onde é legítimo: LLM local.
    if data.endpoint and data.endpoint.strip():
        try:
            validar_url(data.endpoint.strip(), permitir_loopback=(provider == "local"))
        except EgressBlocked as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    "O endereço informado não é um destino válido para o provedor de IA. "
                    "Endereços de rede interna e protocolos fora de http/https não são aceitos."
                ),
            ) from exc

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
    usuario: UserModel = Depends(require_session),
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

    settings = _settings_do_usuario(db, usuario)
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
async def test_ai_connection(
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Testa conectividade com o provedor de IA ativo."""
    settings = _settings_do_usuario(db, usuario)
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de IA estão desativados nas Configurações (Modo 100% Manual). Ative a IA para testar a conexão.",
        )

    client = AIFactory.get_client(db, user_id=usuario.id)
    diagnostico = await client.diagnosticar_conexao()

    if not diagnostico.ok:
        # 502 continua sendo o código certo — a falha é do provedor, não do
        # pedido —, mas a mensagem agora diz QUAL é a falha. A anterior culpava
        # a chave em todos os casos, inclusive quando as chaves estavam boas e
        # o provedor só estava limitando a taxa.
        raise HTTPException(status_code=502, detail=diagnostico.mensagem)

    return {
        "status": "ok",
        "provider": diagnostico.provedor or client.provider_name,
        "model": diagnostico.modelo or client.model_name,
        "message": diagnostico.mensagem,
        "chaves_testadas": diagnostico.chaves_testadas,
        "chaves_boas": diagnostico.chaves_boas,
        "chaves_recusadas": diagnostico.chaves_recusadas,
        "chaves_ignoradas": diagnostico.chaves_ignoradas,
    }


@router.post("/suggest-protocol")
async def suggest_protocol(
    data: ProtocolSuggestRequest,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Gera sugestões de PICO, descritores em pares e critérios via IA."""
    settings = _settings_do_usuario(db, usuario)
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de IA estão desativados nas Configurações (Modo 100% Manual).",
        )

    client = AIFactory.get_client(db, user_id=usuario.id)
    try:
        suggestions = await client.generate_protocol_suggestions(
            title=data.title,
            methodology=data.methodology,
            initial_description=data.description,
        )
        return suggestions
    except Exception as e:
        mensagem, _ = erro_interno(
            "Falha ao gerar as sugestões de protocolo.", e, contexto="[AI] sugestão de protocolo"
        )
        raise HTTPException(status_code=500, detail=mensagem) from e


@router.post("/assist-field", response_model=FieldAssistResponse)
async def assist_field(
    data: FieldAssistRequest,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Preenche, corrige ou aprimora o conteúdo de um campo específico com IA baseada nas diretrizes do item."""
    settings = _settings_do_usuario(db, usuario)
    if settings and not settings.ai_enabled:
        raise HTTPException(
            status_code=400,
            detail="Os recursos de IA estão desativados nas Configurações (Modo 100% Manual). Ative a IA para usar o assistente.",
        )

    client = AIFactory.get_client(db, user_id=usuario.id)
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
            field_id=data.field_id,
        )
        return FieldAssistResponse(
            field_id=data.field_id,
            suggested_text=result.get("suggested_text", ""),
            explanation=result.get("explanation", ""),
            model_used=result.get("model_used", client.model_name),
            provider=result.get("provider", client.provider_name),
        )
    except Exception as e:
        mensagem, _ = erro_interno(
            "Falha ao processar o assistente de campo.", e,
            contexto=f"[AI] assistente do campo '{data.field_label}'",
        )
        raise HTTPException(status_code=500, detail=mensagem) from e

