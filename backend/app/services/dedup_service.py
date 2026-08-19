#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço de Deduplicação de Artigos Otimizado.
Estratégia de 3 passes escalável com chaves de bloqueio (blocking keys):
  1. DOI Match (exato com índice composto project_id + doi)
  2. Título Normalizado (exato com índice composto project_id + title_normalized)
  3. Fuzzy String Similarity restrito a candidatos indexados por Blocking Key
  4. Persistência em lote (batch commits) para evitar fsync por registro.
"""

import re
import unicodedata
from typing import List, Optional, Tuple

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.harvesters.base import RawPaperRecord
from app.infrastructure.persistence.models import PaperModel, PaperSourceModel


class DeduplicationService:
    """Serviço responsável por identificar e unificar duplicatas de forma performática."""

    @staticmethod
    def normalize_title(title: str) -> str:
        """Remove acentos, pontuação e múltiplos espaços, convertendo para minúsculo."""
        if not title:
            return ""
        text = unicodedata.normalize("NFKD", title)
        text = "".join(c for c in text if not unicodedata.combining(c))
        text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
        return " ".join(text.lower().split())

    @staticmethod
    def generate_blocking_key(title_normalized: str) -> str:
        """Gera uma chave de bloqueio com as primeiras 4 palavras significativas do título."""
        if not title_normalized:
            return ""
        words = [w for w in title_normalized.split() if len(w) > 2]
        return " ".join(words[:4]) if words else title_normalized[:20]

    @staticmethod
    def normalize_doi(doi: Optional[str]) -> Optional[str]:
        """Normaliza strings de DOI."""
        if not doi:
            return None
        clean = str(doi).lower().strip()
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
        Verifica se um registro é duplicata através de 3 passes otimizados por índice.
        """
        doi_clean = self.normalize_doi(record.doi)
        title_norm = self.normalize_title(record.title)

        if not title_norm:
            return None

        # ── Passo 1: DOI Match (Exato com índice) ──────────────────────
        if doi_clean:
            match_doi = (
                db.query(PaperModel)
                .filter(PaperModel.project_id == project_id, PaperModel.doi == doi_clean)
                .first()
            )
            if match_doi:
                return match_doi

        # ── Passo 2: Título Normalizado (Exato com índice) ─────────────
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

        # ── Passo 3: Fuzzy Matching com Blocking Key (Reduz N para < 20) ─
        blocking_key = self.generate_blocking_key(title_norm)
        first_token = title_norm.split()[0] if title_norm.split() else ""

        query_filters = [PaperModel.project_id == project_id]
        if blocking_key:
            query_filters.append(PaperModel.blocking_key == blocking_key)
        elif first_token and record.year:
            query_filters.append(PaperModel.year == record.year)

        candidates = (
            db.query(PaperModel.id, PaperModel.title_normalized, PaperModel.year)
            .filter(*query_filters)
            .limit(50)
            .all()
        )

        for cand_id, cand_title_norm, cand_year in candidates:
            if not cand_title_norm:
                continue
            ratio = fuzz.token_sort_ratio(title_norm, cand_title_norm)
            if ratio >= fuzzy_threshold:
                if record.year and cand_year:
                    try:
                        y1, y2 = int(record.year[:4]), int(cand_year[:4])
                        if abs(y1 - y2) > 2:
                            continue
                    except ValueError:
                        pass
                return db.query(PaperModel).filter(PaperModel.id == cand_id).first()

        return None

    def process_record_in_session(
        self,
        db: Session,
        project_id: str,
        record: RawPaperRecord,
        fuzzy_threshold: float = 92.0,
    ) -> Tuple[PaperModel, bool]:
        """
        Processa e anexa o registro à sessão SQLAlchemy SEM commit (flush apenas).
        Retorna (paper, is_new).
        """
        existing = self.find_duplicate(db, project_id, record, fuzzy_threshold=fuzzy_threshold)

        if existing:
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

            # Enriquecer campos se o registro duplicado trouxer dados adicionais
            if not existing.doi and record.doi:
                existing.doi = self.normalize_doi(record.doi)
            if (not existing.abstract or len(existing.abstract) < len(record.abstract)) and record.abstract:
                existing.abstract = record.abstract
            if not existing.download_url and record.download_url:
                existing.download_url = record.download_url
            if not existing.advisor and record.advisor:
                existing.advisor = record.advisor
            if not existing.journal and record.journal:
                existing.journal = record.journal

            db.flush()
            return existing, False

        title_norm = self.normalize_title(record.title)
        blocking_key = self.generate_blocking_key(title_norm)
        doi_clean = self.normalize_doi(record.doi)

        new_paper = PaperModel(
            project_id=project_id,
            title=record.title,
            title_normalized=title_norm,
            blocking_key=blocking_key,
            authors=record.authors,
            advisor=record.advisor,
            year=record.year,
            doi=doi_clean,
            abstract=record.abstract,
            research_type=record.research_type,
            institution=record.institution,
            journal=record.journal,
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
        db.flush()
        return new_paper, True

    def process_record(
        self,
        db: Session,
        project_id: str,
        record: RawPaperRecord,
        fuzzy_threshold: float = 92.0,
    ) -> Tuple[PaperModel, bool]:
        """Processa um registro individual com commit imediato (para retrocompatibilidade)."""
        paper, is_new = self.process_record_in_session(db, project_id, record, fuzzy_threshold)
        db.commit()
        db.refresh(paper)
        return paper, is_new

    def process_batch(
        self,
        db: Session,
        project_id: str,
        records: List[RawPaperRecord],
        fuzzy_threshold: float = 92.0,
    ) -> Tuple[int, int, List[Tuple[str, str, bool]]]:
        """
        Processa um lote de registros em uma única transação atômica.
        Retorna (total_novos, total_duplicados, [(paper_id, title, is_new), ...]).
        """
        new_count = 0
        dup_count = 0
        summary_list = []

        try:
            for rec in records:
                paper, is_new = self.process_record_in_session(db, project_id, rec, fuzzy_threshold)
                if is_new:
                    new_count += 1
                else:
                    dup_count += 1
                summary_list.append((paper.id, paper.title, is_new))

            db.commit()
        except Exception:
            db.rollback()
            raise

        return new_count, dup_count, summary_list

    def run_project_deduplication(
        self,
        db: Session,
        project_id: str,
        fuzzy_threshold: float = 92.0,
    ) -> dict:
        """
        Executa a etapa completa de deduplicação e consolidação de fontes para o projeto,
        marcando duplicatas, unificando metadados e gerando o Relatório de Deduplicação (.txt).
        """
        import json
        from datetime import datetime

        from app.infrastructure.persistence.models import DeduplicationReportModel, HarvestRunModel

        # 1. Carregar todos os artigos do projeto
        all_papers = (
            db.query(PaperModel)
            .filter(PaperModel.project_id == project_id)
            .order_by(PaperModel.created_at.asc())
            .all()
        )

        if not all_papers:
            now_str = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
            empty_report_text = (
                "==================================================\n"
                "             RELATÓRIO DE DEDUPLICAÇÃO            \n"
                "==================================================\n"
                f"Gerado em: {now_str}\n\n"
                "--- ARQUIVOS / BASES FONTES PROCESSADAS ---\n"
                "Nenhum registro encontrado no projeto.\n\n"
                "--- ESTATÍSTICAS ---\n"
                "Total de registros lidos inicialmente: 0\n"
                "Trabalhos únicos após deduplicação: 0\n"
                "Registros duplicados excluídos: 0\n\n"
                "--- TRABALHOS DUPLICADOS ENCONTRADOS ---\n"
                "Nenhum trabalho duplicado foi identificado."
            )
            return {
                "total_raw": 0,
                "total_unique": 0,
                "total_duplicates": 0,
                "sources_breakdown": {},
                "duplicates_list": [],
                "report_text": empty_report_text,
                "created_at": datetime.now().isoformat(),
            }

        # 2. Mapeamento de fontes
        source_counts: dict[str, int] = {}
        paper_sources_map: dict[str, list[str]] = {}

        # Obter todas as fontes vinculadas
        all_sources = (
            db.query(PaperSourceModel)
            .join(PaperModel, PaperModel.id == PaperSourceModel.paper_id)
            .filter(PaperModel.project_id == project_id)
            .all()
        )
        for ps in all_sources:
            src = ps.source_name or "Desconhecida"
            source_counts[src] = source_counts.get(src, 0) + 1
            paper_sources_map.setdefault(ps.paper_id, []).append(src)

        # Se não houver registros em PaperSourceModel, buscar em HarvestRuns
        if not source_counts:
            runs = db.query(HarvestRunModel).filter(HarvestRunModel.project_id == project_id).all()
            for r in runs:
                source_counts[r.source_name] = source_counts.get(r.source_name, 0) + r.records_found

        # 3. Agrupamento e Deduplicação dos Artigos
        # Reseta flags de duplicata
        for p in all_papers:
            p.is_duplicate = False
            p.merged_into_id = None
            if not p.title_normalized:
                p.title_normalized = self.normalize_title(p.title)
            if not p.blocking_key:
                p.blocking_key = self.generate_blocking_key(p.title_normalized)
            if p.doi:
                p.doi = self.normalize_doi(p.doi)

        primary_papers: list[PaperModel] = []
        duplicatas_encontradas: list[dict] = []
        total_raw_count = len(all_papers)

        # Índice auxiliar para buscas rápidas em memória
        doi_lookup: dict[str, PaperModel] = {}
        title_lookup: dict[str, PaperModel] = {}
        blocking_lookup: dict[str, list[PaperModel]] = {}

        for paper in all_papers:
            matched_primary: Optional[PaperModel] = None

            # Passo 1: DOI Match
            if paper.doi and paper.doi in doi_lookup:
                matched_primary = doi_lookup[paper.doi]

            # Passo 2: Título Normalizado Match
            if not matched_primary and paper.title_normalized and paper.title_normalized in title_lookup:
                matched_primary = title_lookup[paper.title_normalized]

            # Passo 3: Fuzzy Match com Blocking Key
            if not matched_primary and paper.blocking_key and paper.blocking_key in blocking_lookup:
                for cand in blocking_lookup[paper.blocking_key]:
                    ratio = fuzz.token_sort_ratio(paper.title_normalized, cand.title_normalized)
                    if ratio >= fuzzy_threshold:
                        if paper.year and cand.year:
                            try:
                                if abs(int(paper.year[:4]) - int(cand.year[:4])) > 2:
                                    continue
                            except ValueError:
                                pass
                        matched_primary = cand
                        break

            if matched_primary and matched_primary.id != paper.id:
                # É duplicata!
                paper.is_duplicate = True
                paper.merged_into_id = matched_primary.id

                # Enriquecer o representante primário
                if (not matched_primary.abstract or len(matched_primary.abstract) < len(paper.abstract)) and paper.abstract:
                    matched_primary.abstract = paper.abstract
                if not matched_primary.doi and paper.doi:
                    matched_primary.doi = paper.doi
                    doi_lookup[paper.doi] = matched_primary
                if not matched_primary.advisor and paper.advisor:
                    matched_primary.advisor = paper.advisor
                if not matched_primary.journal and paper.journal:
                    matched_primary.journal = paper.journal
                if not matched_primary.download_url and paper.download_url:
                    matched_primary.download_url = paper.download_url

                # Vincular fontes
                primary_sources = paper_sources_map.setdefault(matched_primary.id, [])
                paper_srcs = paper_sources_map.get(paper.id, [])
                for s in paper_srcs:
                    if s not in primary_sources:
                        primary_sources.append(s)
                        db.add(PaperSourceModel(paper_id=matched_primary.id, source_name=s, source_id=""))

                duplicatas_encontradas.append({
                    "titulo": paper.title,
                    "autores": paper.authors,
                    "ano": paper.year,
                    "fontes": primary_sources if primary_sources else ["Multibase"],
                    "primary_id": matched_primary.id,
                    "duplicate_id": paper.id,
                })
            else:
                # É primário
                primary_papers.append(paper)
                if paper.doi:
                    doi_lookup[paper.doi] = paper
                if paper.title_normalized:
                    title_lookup[paper.title_normalized] = paper
                if paper.blocking_key:
                    blocking_lookup.setdefault(paper.blocking_key, []).append(paper)

        db.commit()

        total_unique = len(primary_papers)
        total_duplicates = len(duplicatas_encontradas)
        dup_rate = round((total_duplicates / total_raw_count * 100), 1) if total_raw_count > 0 else 0.0

        # 4. Montar o texto estruturado do Relatório de Deduplicação (padrão RSAC V1)
        now_str = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
        report_lines = [
            "==================================================",
            "             RELATÓRIO DE DEDUPLICAÇÃO            ",
            "==================================================",
            f"Gerado em: {now_str}\n",
            "--- ARQUIVOS / BASES FONTES PROCESSADAS ---",
        ]

        for src, count in sorted(source_counts.items()):
            report_lines.append(f" - {src}: {count} registros coletados")
        if not source_counts:
            report_lines.append(" - Todas as bases configuradas no protocolo")

        report_lines.append("\n--- ESTATÍSTICAS ---")
        report_lines.append(f"Total de registros lidos inicialmente: {total_raw_count}")
        for src, count in sorted(source_counts.items()):
            report_lines.append(f"  * Fonte '{src}': {count} registros")
        report_lines.append(f"Trabalhos únicos após deduplicação: {total_unique}")
        report_lines.append(f"Registros duplicados excluídos: {total_duplicates}")
        report_lines.append(f"Taxa de duplicação: {dup_rate}%")
        report_lines.append("\n--- TRABALHOS DUPLICADOS ENCONTRADOS ---")

        if duplicatas_encontradas:
            for j, dup in enumerate(duplicatas_encontradas, start=1):
                report_lines.append(f"{j}. Título: {dup['titulo']}")
                authors_part = f"{dup['autores']}" if dup['autores'] else "Autores não informados"
                year_part = f"({dup['ano']})" if dup['ano'] else ""
                report_lines.append(f"   Autores: {authors_part} {year_part}".strip())
                report_lines.append(f"   Ocorrências em fontes: {', '.join(dup['fontes'])}")
                report_lines.append("")
        else:
            report_lines.append("Nenhum trabalho duplicado foi identificado (títulos 100% distintos).")

        report_text = "\n".join(report_lines)

        # 5. Salvar relatório no banco de dados
        report_model = DeduplicationReportModel(
            project_id=project_id,
            total_raw=total_raw_count,
            total_unique=total_unique,
            total_duplicates=total_duplicates,
            sources_breakdown=json.dumps(source_counts, ensure_ascii=False),
            duplicates_list=json.dumps(duplicatas_encontradas, ensure_ascii=False),
            report_text=report_text,
            created_at=datetime.utcnow(),
        )
        db.add(report_model)
        db.commit()

        return {
            "id": report_model.id,
            "project_id": project_id,
            "total_raw": total_raw_count,
            "total_unique": total_unique,
            "total_duplicates": total_duplicates,
            "dup_rate": dup_rate,
            "sources_breakdown": source_counts,
            "duplicates_list": duplicatas_encontradas,
            "report_text": report_text,
            "created_at": report_model.created_at.isoformat(),
        }


# Aliases para retrocompatibilidade e facilidade de importação
normalize_title = DeduplicationService.normalize_title
generate_blocking_key = DeduplicationService.generate_blocking_key
normalize_doi = DeduplicationService.normalize_doi
