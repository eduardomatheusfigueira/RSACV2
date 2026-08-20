#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — OpenAI-Compatible AI Client (Qwen / DashScope / Local LLM / Ollama).
Integração resiliente com qualquer endpoint compatível com a API OpenAI Chat Completions,
com suporte a fallback de modelos, rotação de chaves e tratamento de formatos de resposta.
"""

import json
import logging
import re
from typing import List, Optional

import httpx

from app.domain.entities import Paper, Protocol
from app.infrastructure.ai.base import (
    BaseAIClient,
    ProtocolSuggestions,
    ScreeningResult,
    validar_resposta_de_triagem,
)
from app.infrastructure.ai.prompts import (
    build_field_assist_prompt,
    build_protocol_suggestion_prompt,
    build_screening_prompt,
)

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
        api_key: str | List[str] = "",
        model_name: str = "qwen-plus",
        temperature: float = 0.2,
    ):
        super().__init__(provider_name=provider_name, model_name=model_name)
        self.base_url = base_url.rstrip("/")
        if isinstance(api_key, list):
            self.api_keys = [str(k).strip() for k in api_key if str(k).strip()]
        elif isinstance(api_key, str) and api_key.strip():
            self.api_keys = [api_key.strip()]
        else:
            self.api_keys = []
        self.current_key_idx = 0
        self.temperature = temperature

    @property
    def api_key(self) -> str:
        """Retorna a chave atualmente ativa na rotação."""
        if not self.api_keys:
            return ""
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def _rotate_key(self) -> None:
        """Rotaciona para a próxima chave configurada."""
        if self.api_keys:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            logger.info(f"[{self.provider_name}] Chave rotacionada para índice {self.current_key_idx}")

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
        current_k = self.api_key
        headers = {
            "Content-Type": "application/json",
        }
        if current_k:
            headers["Authorization"] = f"Bearer {current_k}"

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

        # Validação contra o contrato, com o desvio registrado em vez de
        # coagido em silêncio (doc 29 §29.9.2).
        decisao, confianca, justificativa, valida, nota = validar_resposta_de_triagem(data)
        if not valida:
            logger.warning(
                "[%s] Resposta de triagem fora do contrato (%s) — decisão rebaixada para Pendente.",
                self.provider_name, nota,
            )

        inc = data.get("criterios_inclusao_atendidos") or data.get("criterios_inclusao") or {}
        exc = data.get("criterios_exclusao_atendidos") or data.get("criterios_exclusao") or {}
        if not isinstance(inc, dict):
            inc = {}
        if not isinstance(exc, dict):
            exc = {}

        return ScreeningResult(
            decision=decisao,
            inclusion_criteria=inc,
            exclusion_criteria=exc,
            justification=justificativa,
            confidence=confianca,
            model_used=self.model_name,
            provider=self.provider_name,
            response_valid=valida,
            validation_note=nota,
        )

    async def generate_protocol_suggestions(
        self,
        title: str,
        methodology: str,
        initial_description: str = "",
    ) -> ProtocolSuggestions:
        return await self.suggest_protocol(title, methodology, initial_description)

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

    async def assist_field(
        self,
        field_label: str,
        field_guidelines: str = "",
        current_value: str = "",
        project_title: str = "",
        methodology: str = "PRISMA-ScR",
        project_context: Optional[dict] = None,
        action: str = "generate",
        custom_instruction: str = "",
    ) -> dict:
        """Preenche, corrige ou aprimora o conteúdo de um campo específico com system prompt adequado."""
        prompt = build_field_assist_prompt(
            field_label=field_label,
            field_guidelines=field_guidelines,
            current_value=current_value,
            project_title=project_title,
            methodology=methodology,
            project_context=project_context,
            action=action,
            custom_instruction=custom_instruction,
        )
        data = await self._call_chat_completion(prompt)
        return {
            "suggested_text": data.get("suggested_text", ""),
            "explanation": data.get("explanation", ""),
            "model_used": self.model_name,
            "provider": self.provider_name,
        }

    async def test_connection(self) -> bool:
        """Testa conectividade e validade das chaves com o endpoint compatível."""
        if not self.api_key:
            raise ValueError("Nenhuma API Key cadastrada para este provedor.")
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"[{self.provider_name}] Erro no teste de conexão: {e}")
            raise
