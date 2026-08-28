#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Google Gemini AI Client.
Integração com a API Google Gemini (via v1beta REST)
com suporte a rotação de API keys, modelos configurados no RSAC e output JSON estruturado.
"""

import asyncio
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


class GeminiAIClient(BaseAIClient):
    """Cliente para Google Gemini com rotação de chaves e JSON mode."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    FALLBACK_MODELS = (
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-pro",
    )

    def __init__(
        self,
        api_keys: List[str],
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.2,
    ):
        super().__init__(provider_name="gemini", model_name=model_name or "gemini-2.5-flash")
        self.api_keys = [k.strip() for k in api_keys if k.strip()]
        self.current_key_idx = 0
        self.temperature = temperature

    def _get_current_key(self) -> str:
        if not self.api_keys:
            raise ValueError("Nenhuma API Key do Gemini configurada.")
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def _rotate_key(self) -> None:
        if self.api_keys:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            logger.info(f"[Gemini] Chave rotacionada para índice {self.current_key_idx}")

    def _clean_json(self, raw_text: str) -> str:
        """Extrai JSON limpo mesmo se a IA incluir markdown backticks."""
        text = raw_text.strip()
        if "```json" in text:
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif "```" in text:
            match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return match.group(1).strip()

        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx : end_idx + 1].strip()

        return text

    async def _call_gemini_api(self, prompt: str) -> dict:
        """Chama a API do Gemini com rotação de chaves e retry em rate limit."""
        if not self.api_keys:
            raise ValueError("Nenhuma API Key do Google Gemini cadastrada nas Configurações.")

        # Priorizar chaves válidas de formato Google AI Studio (iniciadas em AIzaSy)
        valid_keys = [k for k in self.api_keys if k.startswith("AIzaSy")]
        keys_to_try = valid_keys if valid_keys else self.api_keys

        models_to_try = [self.model_name] + [m for m in self.FALLBACK_MODELS if m != self.model_name]

        for model in models_to_try:
            for key in keys_to_try:
                url = f"{self.BASE_URL}/{model}:generateContent?key={key}"

                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": self.temperature,
                        "responseMimeType": "application/json",
                    },
                }

                try:
                    async with httpx.AsyncClient(timeout=45.0) as client:
                        res = await client.post(url, json=payload)

                        if res.status_code == 200:
                            data = res.json()
                            candidate_text = (
                                data.get("candidates", [{}])[0]
                                .get("content", {})
                                .get("parts", [{}])[0]
                                .get("text", "")
                            )
                            cleaned = self._clean_json(candidate_text)
                            return json.loads(cleaned)

                        elif res.status_code == 429:
                            logger.warning(f"[Gemini] Rate limit no modelo '{model}'. Tentando próxima chave...")
                            await asyncio.sleep(0.3)
                            continue

                        elif res.status_code in (400, 404):
                            logger.warning(f"[Gemini] Modelo '{model}' retornou {res.status_code}. Tentando próximo...")
                            continue

                        else:
                            logger.warning(f"[Gemini] Erro na API (HTTP {res.status_code}): {res.text[:100]}")
                            continue

                except json.JSONDecodeError as e:
                    logger.error(f"[Gemini] Falha ao decodificar JSON gerado: {e}")
                    raise RuntimeError("O modelo Gemini não retornou um JSON válido.")
                except Exception as e:
                    logger.warning(f"[Gemini] Falha na requisição: {e}")
                    continue

        raise RuntimeError("Não foi possível obter resposta válida dos modelos Gemini configurados.")

    async def analyze_screening(
        self,
        paper: Paper,
        protocol: Protocol,
    ) -> ScreeningResult:
        prompt = build_screening_prompt(paper, protocol)
        data = await self._call_gemini_api(prompt)

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
            provider="gemini",
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
        prompt = build_protocol_suggestion_prompt(title, methodology, description)
        data = await self._call_gemini_api(prompt)

        desc_pt = data.get("descritores_pt", [])
        desc_en = data.get("descritores_en", [])
        desc_es = data.get("descritores_es", [])

        # Respeitar estritamente a regra de no máximo 5 pares por idioma
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
        data = await self._call_gemini_api(prompt)
        return {
            "suggested_text": data.get("suggested_text", ""),
            "explanation": data.get("explanation", ""),
            "model_used": self.model_name,
            "provider": self.provider_name,
        }

    async def test_connection(self) -> bool:
        """Testa conectividade e validade das chaves com o Google Gemini."""
        if not self.api_keys or not any(self.api_keys):
            raise ValueError("Nenhuma API Key do Google Gemini cadastrada nas Configurações.")
        try:
            current_key = self._get_current_key()
            url = f"{self.BASE_URL}/{self.model_name}:generateContent?key={current_key}"
            payload = {
                "contents": [{"parts": [{"text": "ping"}]}],
                "generationConfig": {"temperature": 0.0},
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"[Gemini] Erro no teste de conexão: {e}")
            raise
