#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — AI Client Factory."""

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
    def get_client(db: Optional[Session] = None) -> BaseAIClient:
        # 1. Tentar recuperar configurações salvas no banco
        settings = db.query(AISettingsModel).first() if db else None

        if settings:
            provider = settings.provider.lower()
            model = settings.model

            # Descriptografar / deserializar chaves
            try:
                keys = json.loads(settings.api_keys_encrypted) if settings.api_keys_encrypted else []
            except Exception:
                keys = [settings.api_keys_encrypted] if settings.api_keys_encrypted else []

            if provider == AIProvider.GEMINI.value:
                return GeminiAIClient(
                    api_keys=keys or [os.environ.get("GEMINI_API_KEY", "")],
                    model_name=model or "gemini-2.5-flash",
                    temperature=settings.temperature,
                )
            elif provider == AIProvider.QWEN.value:
                return OpenAICompatibleAIClient(
                    provider_name="qwen",
                    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                    api_key=keys[0] if keys else os.environ.get("DASHSCOPE_API_KEY", ""),
                    model_name=model or "qwen-plus",
                    temperature=settings.temperature,
                )
            elif provider == AIProvider.LOCAL.value:
                return OpenAICompatibleAIClient(
                    provider_name="local",
                    base_url=settings.endpoint or "http://localhost:11434/v1",
                    api_key=keys[0] if keys else "ollama",
                    model_name=model or "qwen2.5:7b",
                    temperature=settings.temperature,
                )

        # 2. Fallback para variáveis de ambiente ou default Gemini
        env_gemini_key = os.environ.get("GEMINI_API_KEY", "")
        return GeminiAIClient(
            api_keys=[env_gemini_key] if env_gemini_key else [],
            model_name="gemini-2.5-flash",
        )
