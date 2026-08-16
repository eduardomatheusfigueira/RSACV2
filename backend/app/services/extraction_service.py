#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço de Extração de Dados Estruturados (Triagem 2).
Responde às perguntas do protocolo com base no texto completo do PDF ou resumo,
utilizando IA com ancoragem estrita e citação de trechos comprovatórios.
"""

import logging
import os
from typing import Dict, List
from sqlalchemy.orm import Session

from app.infrastructure.ai.factory import AIFactory
from app.infrastructure.persistence.models import (
    ExtractionAnswerModel,
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
        questions_list_text = "\n".join(
            f"- Q{i + 1} (ID: {q.id}): {q.text}" for i, q in enumerate(questions)
        )
        question_texts = [q.text for q in questions]

        context_text, source_kind, warning = self._build_context(paper, question_texts)

        prompt = self._build_prompt(context_text, questions_list_text, source_kind)

        client = AIFactory.get_client(db)
        if hasattr(client, "_call_gemini_api"):
            data = await client._call_gemini_api(prompt)
        elif hasattr(client, "_call_chat_completion"):
            data = await client._call_chat_completion(prompt)
        else:
            data = {"respostas": []}

        answers_data = data.get("respostas", []) if isinstance(data, dict) else []
        saved_answers = []

        for ans in answers_data:
            if not isinstance(ans, dict):
                continue
            q_id = ans.get("question_id")
            ans_text = (ans.get("answer") or "").strip()
            if not q_id or not ans_text:
                continue

            evidence = (ans.get("evidencia") or ans.get("evidence") or "").strip()
            page_ref = str(ans.get("pagina") or ans.get("page") or "").strip()[:20]

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
                existing.evidence = evidence
                existing.page_ref = page_ref
                existing.source_kind = source_kind
            else:
                db.add(
                    ExtractionAnswerModel(
                        paper_id=paper.id,
                        question_id=q_id,
                        answer=ans_text,
                        ai_generated=True,
                        evidence=evidence,
                        page_ref=page_ref,
                        source_kind=source_kind,
                    )
                )

            saved_answers.append(
                {
                    "question_id": q_id,
                    "answer": ans_text,
                    "evidence": evidence,
                    "page_ref": page_ref,
                    "source_kind": source_kind,
                }
            )

        db.commit()
        if warning:
            logger.info("[ExtractionService] %s (paper %s)", warning, paper.id)
        return saved_answers

    # ── Montagem de contexto ──────────────────────────────────────────

    def _build_context(self, paper: PaperModel, question_texts: List[str]) -> tuple[str, str, str]:
        """
        Escolhe a melhor base textual disponível e devolve `(texto, tipo, aviso)`.

        Preferência: texto completo do PDF, recortado por relevância às perguntas.
        Se o PDF não existe, não abre ou é digitalizado sem texto, cai para o
        resumo — e o aviso explica ao usuário por que a resposta veio mais rasa.
        """
        header = (
            f"TÍTULO: {paper.title}\n"
            f"AUTORIA: {paper.authors or 'não informada'}\n"
            f"ANO: {paper.year or 'não informado'}\n"
        )
        abstract_context = f"{header}RESUMO: {paper.abstract or '(resumo não coletado)'}"

        if not paper.pdf_path or not os.path.exists(paper.pdf_path):
            return abstract_context, "resumo", "Sem PDF vinculado — extração baseada no resumo."

        try:
            context = self.pdf_service.build_ai_context(paper.pdf_path, question_texts)
        except Exception as exc:  # noqa: BLE001 — motor de PDF externo
            logger.warning("[ExtractionService] Falha ao ler PDF (%s). Usando resumo.", exc)
            return abstract_context, "resumo", f"Falha na leitura do PDF: {exc}"

        if len(context.strip()) < 400:
            return (
                abstract_context,
                "resumo",
                "PDF sem texto extraível (provavelmente digitalizado) — extração pelo resumo.",
            )

        return f"{header}\n{context}", "pdf", ""

    @staticmethod
    def _build_prompt(context_text: str, questions_list_text: str, source_kind: str) -> str:
        base_note = (
            "O texto abaixo é o conteúdo integral do estudo, com marcações de página "
            "no formato [[p. N]]. Use essas marcações para indicar onde encontrou cada dado."
            if source_kind == "pdf"
            else "O texto abaixo contém apenas os metadados e o resumo do estudo — "
            "o texto completo não está disponível. Não infira o que não está escrito."
        )

        return f"""Você é um pesquisador acadêmico conduzindo a fase de Extração de Dados \
(Triagem 2) de uma Revisão Sistemática.
{base_note}

==================== TEXTO DO ESTUDO ====================
{context_text}

==================== PERGUNTAS DE EXTRAÇÃO ====================
{questions_list_text}

==================== REGRAS DE EXTRAÇÃO ====================
1. ANCORAGEM ESTRITA: responda apenas com o que está escrito no texto. Se a \
informação não estiver presente, responda exatamente 'Não informado no texto'.
2. EVIDÊNCIA OBRIGATÓRIA: para cada resposta com conteúdo, transcreva em \
"evidencia" um trecho literal e curto (até 300 caracteres) que sustente a \
resposta, e informe em "pagina" o número da página correspondente \
(use as marcações [[p. N]]); deixe "" quando não houver.
3. SÍNTESE PRECISA: seja objetivo e preserve números, unidades, recortes \
temporais/territoriais e nomes de métodos exatamente como aparecem.
4. NÃO INVENTE: nunca complete dados por conhecimento externo ao texto.
5. FORMATO: responda OBRIGATORIAMENTE em JSON puro, sem texto fora do JSON:
{{
  "respostas": [
    {{
      "question_id": "ID_DA_PERGUNTA",
      "answer": "Resposta sintetizada e ancorada no texto...",
      "evidencia": "Trecho literal do estudo que sustenta a resposta",
      "pagina": "12"
    }}
  ]
}}
"""
