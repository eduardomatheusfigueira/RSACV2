#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço de Deduplicação de Artigos.
Estratégia de 3 passes:
  1. DOI Match (exato)
  2. Título Normalizado (exato)
  3. Fuzzy String Similarity (RapidFuzz token_sort_ratio >= 92%)
"""

import re
import unicodedata
from typing import List, Optional, Tuple
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.harvesters.base import RawPaperRecord
from app.infrastructure.persistence.models import PaperModel, PaperSourceModel


class DeduplicationService:
    """Serviço responsável por identificar e unificar duplicatas."""

    @staticmethod
    def normalize_title(title: str) -> str:
        """Remove acentos, pontuação e múltiplos espaços, convertendo para minúsculo."""
        if not title:
            return ""
        # Decompor caracteres Unicode e remover diacríticos
        text = unicodedata.normalize("NFKD", title)
        text = "".join(c for c in text if not unicodedata.combining(c))
        # Manter apenas letras e números
        text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
        return " ".join(text.lower().split())

    @staticmethod
    def normalize_doi(doi: Optional[str]) -> Optional[str]:
        """Normaliza strings de DOI."""
        if not doi:
            return None
        clean = doi.lower().strip()
        clean = clean.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
        return clean.strip() or None

    def find_duplicate(
        self,
        db: Session,
        project_id: str,
        record: RawPaperRecord,
        fuzzy_threshold: float = 92.0,
    ) -> Optional[PaperModel]:
        """
        Executa os 3 passos de verificação de duplicata para um novo registro no banco.
        Retorna o PaperModel existente se for duplicata, ou None se for novo.
        """
        doi_clean = self.normalize_doi(record.doi)
        title_norm = self.normalize_title(record.title)

        if not title_norm:
            return None

        # ── Passo 1: DOI Match (Exato) ─────────────────────────────────
        if doi_clean:
            match_doi = (
                db.query(PaperModel)
                .filter(PaperModel.project_id == project_id, PaperModel.doi == doi_clean)
                .first()
            )
            if match_doi:
                return match_doi

        # ── Passo 2: Título Normalizado (Exato) ────────────────────────
        match_title = (
            db.query(PaperModel)
            .filter(
                PaperModel.project_id == project_id,
                PaperModel.title_normalized == title_norm,
            )
            .first()
        )
        if match_title:
            return match_title

        # ── Passo 3: Fuzzy Matching ───────────────────────────────────
        # Buscar títulos similares no mesmo projeto
        candidates = (
            db.query(PaperModel.id, PaperModel.title_normalized, PaperModel.year)
            .filter(PaperModel.project_id == project_id)
            .all()
        )

        for cand_id, cand_title_norm, cand_year in candidates:
            if not cand_title_norm:
                continue
            ratio = fuzz.token_sort_ratio(title_norm, cand_title_norm)
            if ratio >= fuzzy_threshold:
                # Se ambos têm ano e o ano difere por mais de 2 anos, não é a mesma publicação
                if record.year and cand_year:
                    try:
                        y1, y2 = int(record.year[:4]), int(cand_year[:4])
                        if abs(y1 - y2) > 2:
                            continue
                    except ValueError:
                        pass

                return db.query(PaperModel).filter(PaperModel.id == cand_id).first()

        return None

    def process_record(
        self,
        db: Session,
        project_id: str,
        record: RawPaperRecord,
        fuzzy_threshold: float = 92.0,
    ) -> Tuple[PaperModel, bool]:
        """
        Processa um registro bruto:
          - Se for duplicata: anexa a nova fonte ao registro existente e retorna (paper, False).
          - Se for novo: cria o novo PaperModel e anexa a fonte, retornando (paper, True).
        """
        existing = self.find_duplicate(db, project_id, record, fuzzy_threshold=fuzzy_threshold)

        if existing:
            # Verificar se a fonte já está registrada
            source_exists = (
                db.query(PaperSourceModel)
                .filter(
                    PaperSourceModel.paper_id == existing.id,
                    PaperSourceModel.source_name == record.source_name,
                )
                .first()
            )
            if not source_exists:
                db.add(
                    PaperSourceModel(
                        paper_id=existing.id,
                        source_name=record.source_name,
                        source_id=record.source_id or "",
                    )
                )

            # Preencher campos faltantes no paper existente se o novo registro trouxer
            if not existing.doi and record.doi:
                existing.doi = self.normalize_doi(record.doi)
            if not existing.abstract and record.abstract:
                existing.abstract = record.abstract
            if not existing.download_url and record.download_url:
                existing.download_url = record.download_url

            db.commit()
            return existing, False

        # Criar novo PaperModel
        title_norm = self.normalize_title(record.title)
        doi_clean = self.normalize_doi(record.doi)

        new_paper = PaperModel(
            project_id=project_id,
            title=record.title,
            title_normalized=title_norm,
            authors=record.authors,
            year=record.year,
            doi=doi_clean,
            abstract=record.abstract,
            research_type=record.research_type,
            institution=record.institution,
            download_url=record.download_url,
            decision="Pendente",
        )
        db.add(new_paper)
        db.flush()

        db.add(
            PaperSourceModel(
                paper_id=new_paper.id,
                source_name=record.source_name,
                source_id=record.source_id or "",
            )
        )

        db.commit()
        db.refresh(new_paper)
        return new_paper, True
