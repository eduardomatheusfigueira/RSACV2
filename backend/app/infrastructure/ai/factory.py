#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — AI Client Factory."""

import json
import os
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.enums import AIProvider
from app.infrastructure.ai.base import BaseAIClient
from app.infrastructure.ai.gemini_client import GeminiAIClient
from app.infrastructure.ai.openai_compatible_client import OpenAICompatibleAIClient
from app.infrastructure.persistence.models import AISettingsModel


class AIFactory:
    """Factory para instanciar e configurar o provedor de IA ativo."""

    @staticmethod
    def get_client(db: Optional[Session] = None, user_id: Optional[str] = None) -> BaseAIClient:
        """
        Cliente de IA configurado com as chaves **do usuário informado**.

        `user_id` é obrigatório na prática: sem ele não há configuração, e o
        cliente cai no padrão sem chave. Isso é deliberado — a alternativa,
        pegar a primeira linha da tabela como antes, faria a triagem de um
        assinante rodar na cota paga de outro (doc 39, O-02).
        """
        # 1. Tentar recuperar a configuração daquele usuário
        settings = (
            db.query(AISettingsModel).filter(AISettingsModel.user_id == user_id).first()
            if (db is not None and user_id)
            else None
        )

        if settings:
            provider = settings.provider.lower()
            model = settings.model

            def _parse_keys(raw: Optional[str]) -> List[str]:
                if not raw:
                    return []
                try:
                    res = json.loads(raw)
                    if isinstance(res, list):
                        return [str(k).strip() for k in res if str(k).strip()]
                    elif isinstance(res, str) and res.strip():
                        return [res.strip()]
                    return []
                except Exception:
                    return [raw.strip()] if raw.strip() else []

            gemini_keys = _parse_keys(settings.gemini_api_keys_encrypted)
            qwen_keys = _parse_keys(settings.qwen_api_keys_encrypted)
            local_keys = _parse_keys(settings.local_api_keys_encrypted)
            legacy_keys = _parse_keys(settings.api_keys_encrypted)

            if provider == AIProvider.GEMINI.value:
                keys = gemini_keys or legacy_keys or [os.environ.get("GEMINI_API_KEY", "")]
                return GeminiAIClient(
                    api_keys=keys,
                    model_name=model or "gemini-3.6-flash",
                    temperature=settings.temperature,
                )
            elif provider == AIProvider.QWEN.value:
                keys = qwen_keys or legacy_keys or [os.environ.get("DASHSCOPE_API_KEY", "")]
                base_url = settings.endpoint or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
                return OpenAICompatibleAIClient(
                    provider_name="qwen",
                    base_url=base_url,
                    api_key=keys,
                    model_name=model or "qwen3.8-max",
                    temperature=settings.temperature,
                )
            elif provider == AIProvider.LOCAL.value:
                keys = local_keys or ["ollama"]
                return OpenAICompatibleAIClient(
                    provider_name="local",
                    base_url=settings.endpoint or "http://localhost:11434/v1",
                    api_key=keys,
                    model_name=model or "Llama-3.2-3B",
                    temperature=settings.temperature,
                )

        # 2. Fallback para variáveis de ambiente ou default Gemini
        env_gemini_key = os.environ.get("GEMINI_API_KEY", "")
        return GeminiAIClient(
            api_keys=[env_gemini_key] if env_gemini_key else [],
            model_name="gemini-3.6-flash",
        )
