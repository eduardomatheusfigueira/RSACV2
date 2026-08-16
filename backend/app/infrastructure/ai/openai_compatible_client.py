#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — OpenAI-Compatible AI Client (Qwen / DashScope / Local LLM / Ollama).
Integração resiliente com qualquer endpoint compatível com a API OpenAI Chat Completions,
com suporte a fallback de modelos, rotação de chaves e tratamento de formatos de resposta.
"""

import asyncio
import json
import logging
import re
from typing import List, Optional
import httpx

from app.domain.entities import Paper, Protocol
from app.infrastructure.ai.base import BaseAIClient, ProtocolSuggestions, ScreeningResult
from app.infrastructure.ai.prompts import build_protocol_suggestion_prompt, build_screening_prompt

logger = logging.getLogger(__name__)

# Endpoints regionais do Alibaba Qwen
QWEN_REGIONS = {
    "intl": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "us": "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
    "cn": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


class OpenAICompatibleAIClient(BaseAIClient):
    """Cliente robusto para APIs compatíveis com OpenAI (Qwen, Ollama, LM Studio, vLLM)."""

    def __init__(
        self,
        provider_name: str,
        base_url: str,
        api_key: str = "",
        model_name: str = "qwen-plus",
        temperature: float = 0.2,
    ):
        super().__init__(provider_name=provider_name, model_name=model_name)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.temperature = temperature

    def _clean_json(self, raw_text: str) -> str:
        """Extrai o bloco JSON limpo de textos gerados pela IA."""
        text = raw_text.strip()
        if "```json" in text:
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif "```" in text:
            match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # Tentar extrair do primeiro '{' ao último '}'
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx : end_idx + 1].strip()

        return text

    async def _call_chat_completion(self, prompt: str) -> dict:
        """Envia requisição para /chat/completions com retentativa sem response_format se necessário."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # 1. Tentativa com response_format json_object
        payload_with_format = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um pesquisador acadêmico e assistente rigoroso de revisão sistemática. Responda ESTRITAMENTE em formato JSON válido, sem texto explicativo fora do JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                res = await client.post(url, json=payload_with_format, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    cleaned = self._clean_json(content)
                    return json.loads(cleaned)
                elif res.status_code in (400, 422):
                    # Alguns modelos locais ou endpoints não suportam response_format: json_object
                    logger.info(f"[{self.provider_name}] Endpoint retornou {res.status_code} com response_format. Tentando sem response_format...")
                else:
                    raise RuntimeError(f"[{self.provider_name}] Erro HTTP {res.status_code}: {res.text}")
            except (json.JSONDecodeError, RuntimeError) as e:
                logger.warning(f"[{self.provider_name}] Tentativa padrão falhou: {e}. Tentando fallback sem response_format...")

            # 2. Fallback sem response_format
            payload_fallback = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é um assistente acadêmico rigoroso de revisão sistemática. Responda ESTRITAMENTE em formato JSON puro.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.temperature,
            }

            res = await client.post(url, json=payload_fallback, headers=headers)
            if res.status_code != 200:
                raise RuntimeError(f"[{self.provider_name}] Erro na API: HTTP {res.status_code} - {res.text}")

            data = res.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            cleaned = self._clean_json(content)
            return json.loads(cleaned)

    async def analyze_screening(
        self,
        paper: Paper,
        protocol: Protocol,
    ) -> ScreeningResult:
        """Executa a triagem com o modelo compatível com OpenAI."""
        prompt = build_screening_prompt(paper, protocol)
        data = await self._call_chat_completion(prompt)

        decisao = data.get("decisao", "Pendente")
        if decisao not in ("Incluído", "Excluído", "Pendente"):
            decisao = "Pendente"

        return ScreeningResult(
            decision=decisao,
            inclusion_criteria=data.get("criterios_inclusao", {}),
            exclusion_criteria=data.get("criterios_exclusao", {}),
            justification=data.get("justificativa", ""),
            confidence=float(data.get("confianca", 0.9)),
            model_used=self.model_name,
            provider=self.provider_name,
        )

    async def suggest_protocol(
        self,
        title: str,
        methodology: str,
        description: Optional[str] = None,
    ) -> ProtocolSuggestions:
        """Gera sugestões estruturadas para o protocolo de revisão."""
        prompt = build_protocol_suggestion_prompt(title, methodology, description)
        data = await self._call_chat_completion(prompt)

        desc_pt = data.get("descritores_pt", [])
        desc_en = data.get("descritores_en", [])
        desc_es = data.get("descritores_es", [])

        # Garantir limite de 5 pares por idioma
        return ProtocolSuggestions(
            objective=data.get("objetivo", ""),
            pico_population=data.get("pico_populacao", ""),
            pico_intervention=data.get("pico_intervencao", ""),
            pico_comparison=data.get("pico_comparacao", ""),
            pico_outcome=data.get("pico_desfecho", ""),
            descriptors_pt=desc_pt[:5],
            descriptors_en=desc_en[:5],
            descriptors_es=desc_es[:5],
            inclusion_criteria=data.get("criterios_inclusao", []),
            exclusion_criteria=data.get("criterios_exclusao", []),
            extraction_questions=data.get("perguntas_extracao", []),
        )
