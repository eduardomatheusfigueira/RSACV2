#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Camada de Texto Persistente e Segmentação IMRaD (doc 48 §5, doc 49 Fase 4).

Fecha B-04:
    - Extração limpa preservando paginação e IMRaD.
    - Persistência com SHA256 do arquivo e versão do pipeline ('2.0.0').
    - Reuso do texto sem reprocessamento oculto.
    - Contagem de palavras e páginas como denominador de frequência relativa.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import BibTextoModel, PaperModel
from app.services.pdf_text import (
    PDFDocument,
    clean_page_text,
    extract_document,
    segment_sections,
    strip_running_heads,
)

logger = logging.getLogger(__name__)

PIPELINE_VERSION_VIGENTE = "2.0.0"
_PALAVRAS = re.compile(r"\b[\wÀ-ÿ\-]+\b")


def contar_palavras(texto: str) -> int:
    """Conta palavras em texto limpo para servir de denominador de densidade lexical."""
    if not texto:
        return 0
    return len(_PALAVRAS.findall(texto))


def extrair_e_persistir_texto(
    db: Session,
    paper_id: str,
    pdf_bytes: bytes,
    pipeline_version: str = PIPELINE_VERSION_VIGENTE,
) -> BibTextoModel:
    """Executa o pipeline completo de extração, limpeza e segmentação, persistindo em bib_textos."""
    pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    # 1. Extração estruturada por blocos
    doc: PDFDocument = extract_document(pdf_bytes)

    # 2. Limpeza e remoção de cabeçalhos/rodapés repetidos
    doc = strip_running_heads(doc)

    # 3. Segmentação em seções IMRaD
    secoes_raw = segment_sections(doc)
    secoes_json = [
        {
            "name": getattr(s, "title", getattr(s, "name", "")),
            "canonical_type": getattr(s, "key", getattr(s, "canonical_type", "")),
            "start_page": getattr(s, "start_page", 1),
            "end_page": getattr(s, "end_page", getattr(s, "start_page", 1)),
            "char_offset": getattr(s, "char_offset", 0),
            "char_length": len(getattr(s, "text", "")),
        }
        for s in secoes_raw
    ]

    # 4. Texto limpo consolidado
    texto_completo = "\n\n".join(p.text for p in doc.pages if p.text)
    n_palavras = contar_palavras(texto_completo)

    # 5. Upsert em bib_textos
    texto_model = db.query(BibTextoModel).filter(BibTextoModel.paper_id == paper_id).first()
    if texto_model:
        texto_model.pipeline_version = pipeline_version
        texto_model.pdf_sha256 = pdf_sha256
        texto_model.n_pages = len(doc.pages)
        texto_model.n_words = n_palavras
        texto_model.text_clean = texto_completo
        texto_model.sections = json.dumps(secoes_json, ensure_ascii=False)
        texto_model.extracted_at = datetime.now(timezone.utc)
    else:
        texto_model = BibTextoModel(
            paper_id=paper_id,
            pipeline_version=pipeline_version,
            pdf_sha256=pdf_sha256,
            n_pages=len(doc.pages),
            n_words=n_palavras,
            text_clean=texto_completo,
            sections=json.dumps(secoes_json, ensure_ascii=False),
            extracted_at=datetime.now(timezone.utc),
        )
        db.add(texto_model)

    db.commit()
    db.refresh(texto_model)
    return texto_model


def obter_ou_extrair_texto(
    db: Session,
    paper_id: str,
    project_id: str,
    pdf_service: Any = None,
) -> Optional[BibTextoModel]:
    """Retorna o texto persistido existente. Se não existir, tenta carregar o PDF em disco e extrair."""
    texto_existente = db.query(BibTextoModel).filter(BibTextoModel.paper_id == paper_id).first()
    if texto_existente:
        return texto_existente

    if not pdf_service:
        return None

    try:
        caminho_pdf = pdf_service.get_pdf_path(project_id, paper_id)
        if caminho_pdf and caminho_pdf.exists():
            with open(caminho_pdf, "rb") as f:
                pdf_bytes = f.read()
            return extrair_e_persistir_texto(db, paper_id, pdf_bytes)
    except Exception as e:
        logger.warning(f"[CamadaTexto] Falha ao extrair texto do estudo {paper_id}: {e}")

    return None


def obter_resumo_secoes(db: Session, paper_id: str) -> list[dict[str, Any]]:
    """Retorna as seções IMRaD registradas para o documento."""
    texto = db.query(BibTextoModel).filter(BibTextoModel.paper_id == paper_id).first()
    if not texto or not texto.sections:
        return []
    try:
        return json.loads(texto.sections)
    except Exception:
        return []
