#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço de Extração de Dados Estruturados (Triagem 2).
Responde às perguntas do protocolo com base no texto completo do PDF ou resumo,
utilizando IA com ancoragem estrita e citação de trechos comprovatórios.
"""

import json
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.infrastructure.ai.factory import AIFactory
from app.infrastructure.persistence.models import (
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    PaperModel,
    ProtocolModel,
)
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)


class ExtractionService:
    """Serviço de Extração de Dados dos Estudos Incluídos."""

    def __init__(self):
        self.pdf_service = PDFService()

    async def extract_answers_with_ai(
        self,
        db: Session,
        project_id: str,
        paper_id: str,
    ) -> List[Dict[str, str]]:
        """Extrai respostas para todas as perguntas do protocolo usando IA e o texto do PDF/Resumo."""
        paper = db.query(PaperModel).filter(PaperModel.project_id == project_id, PaperModel.id == paper_id).first()
        if not paper:
            raise ValueError(f"Artigo '{paper_id}' não encontrado.")

        protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
        if not protocol or not protocol.extraction_questions:
            raise ValueError("Nenhuma pergunta de extração configurada no protocolo.")

        questions = sorted(protocol.extraction_questions, key=lambda x: x.order)
        questions_list_text = "\n".join(f"- Q{i+1} (ID: {q.id}): {q.text}" for i, q in enumerate(questions))

        # Obter texto para análise (PDF completo se existir, senão resumo)
        context_text = ""
        if paper.pdf_path:
            try:
                full_text = self.pdf_service.extract_text_from_pdf(paper.pdf_path)
                context_text = self.pdf_service.extract_key_sections(full_text)
            except Exception as e:
                logger.warning(f"[ExtractionService] Não foi possível ler PDF ({e}). Usando resumo.")
                context_text = f"TÍTULO: {paper.title}\nRESUMO: {paper.abstract}"
        else:
            context_text = f"TÍTULO: {paper.title}\nRESUMO: {paper.abstract}"

        prompt = f"""Você é um pesquisador acadêmico conduzindo a fase de Extração de Dados (Triagem 2) de uma Revisão Sistemática.
Com base ESTRITAMENTE no texto do artigo fornecido abaixo, responda a cada uma das perguntas de extração.

==================== TEXTO DO ESTUDO ====================
{context_text}

==================== PERGUNTAS DE EXTRAÇÃO ====================
{questions_list_text}

==================== REGRAS DE EXTRAÇÃO ====================
1. ANCORAGEM ESTRITA: Se uma informação não for mencionada no texto, responda 'Não informado no texto'.
2. SÍNTESE PRECISA: Seja objetivo, numérico e cite o trecho ou método exato quando aplicável.
3. FORMATO DE RESPOSTA: Responda OBRIGATORIAMENTE em JSON puro no formato:
{{
  "respostas": [
    {{
      "question_id": "ID_DA_PERGUNTA",
      "answer": "Resposta sintetizada e ancorada no texto..."
    }}
  ]
}}
"""

        client = AIFactory.get_client(db)
        if hasattr(client, "_call_gemini_api"):
            data = await client._call_gemini_api(prompt)
        elif hasattr(client, "_call_chat_completion"):
            data = await client._call_chat_completion(prompt)
        else:
            data = {"respostas": []}

        answers_data = data.get("respostas", [])
        saved_answers = []

        # Salvar ou atualizar no banco de dados
        for ans in answers_data:
            q_id = ans.get("question_id")
            ans_text = ans.get("answer", "")
            if not q_id or not ans_text:
                continue

            existing = (
                db.query(ExtractionAnswerModel)
                .filter(
                    ExtractionAnswerModel.paper_id == paper.id,
                    ExtractionAnswerModel.question_id == q_id,
                )
                .first()
            )

            if existing:
                existing.answer = ans_text
                existing.ai_generated = True
            else:
                db.add(
                    ExtractionAnswerModel(
                        paper_id=paper.id,
                        question_id=q_id,
                        answer=ans_text,
                        ai_generated=True,
                    )
                )

            saved_answers.append({"question_id": q_id, "answer": ans_text})

        db.commit()
        return saved_answers
