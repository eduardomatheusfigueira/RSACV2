#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço de Exportação de Dados e Relatórios Acadêmicos.
Gera planilhas Excel (.xlsx) com múltiplas abas, arquivos BibTeX (.bib)
e dados estruturados para o diagrama de fluxo PRISMA 2020.
"""

import io
import re
from typing import Dict, List
import pandas as pd
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    CriterionModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    HarvestRunModel,
    PaperCriterionModel,
    PaperModel,
    ProjectModel,
    ProtocolModel,
)


class ExportService:
    """Serviço de Exportação Multi-formato."""

    @staticmethod
    def generate_excel(db: Session, project_id: str) -> io.BytesIO:
        """
        Gera um arquivo Excel (.xlsx) com 4 abas estruturadas:
          1. Artigos Incluídos
          2. Extração de Dados
          3. Artigos Excluídos
          4. Métricas PRISMA
        """
        project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()

        all_papers = db.query(PaperModel).filter(PaperModel.project_id == project_id).all()
        included_papers = [p for p in all_papers if p.decision == "Incluído"]
        excluded_papers = [p for p in all_papers if p.decision == "Excluído"]
        pending_papers = [p for p in all_papers if p.decision == "Pendente"]

        # Mapa de critérios para lookup rápido
        criteria_by_id = {c.id: c for c in protocol.criteria} if protocol and protocol.criteria else {}

        # ── Aba 1: Artigos Incluídos ───────────────────────────────────
        inc_data = []
        for p in included_papers:
            sources_str = ", ".join(s.source_name for s in p.sources) if p.sources else ""
            evals = db.query(PaperCriterionModel).filter(PaperCriterionModel.paper_id == p.id, PaperCriterionModel.value == True).all()
            inc_crits = [criteria_by_id[e.criterion_id].text for e in evals if e.criterion_id in criteria_by_id and not criteria_by_id[e.criterion_id].is_exclusion]

            inc_data.append({
                "ID": p.id,
                "Título": p.title,
                "Autores": p.authors,
                "Orientador(a)": p.advisor or "",
                "Ano": p.year,
                "DOI": p.doi or "",
                "Periódico / Revista": p.journal or "",
                "Bases de Dados": sources_str,
                "Tipo de Pesquisa": p.research_type,
                "Instituição": p.institution,
                "URL / Link": p.download_url,
                "Critérios de Inclusão Atendidos": "; ".join(inc_crits),
                "Resumo (Abstract)": p.abstract,
                "Observações": p.observations,
            })
        df_included = pd.DataFrame(inc_data)

        # ── Aba 2: Extração de Dados ───────────────────────────────────
        ext_data = []
        questions = sorted(protocol.extraction_questions, key=lambda x: x.order) if protocol else []

        for p in included_papers:
            row = {
                "Paper ID": p.id,
                "Título": p.title,
                "Ano": p.year,
            }
            # Buscar respostas
            answers = {
                ans.question_id: ans.answer
                for ans in db.query(ExtractionAnswerModel).filter(ExtractionAnswerModel.paper_id == p.id).all()
            }
            for i, q in enumerate(questions):
                col_name = f"Q{i+1}: {q.text[:40]}..."
                row[col_name] = answers.get(q.id, "Não preenchido")
            ext_data.append(row)
        df_extraction = pd.DataFrame(ext_data)

        # ── Aba 3: Artigos Excluídos ───────────────────────────────────
        exc_data = []
        for p in excluded_papers:
            sources_str = ", ".join(s.source_name for s in p.sources) if p.sources else ""
            evals = db.query(PaperCriterionModel).filter(PaperCriterionModel.paper_id == p.id, PaperCriterionModel.value == True).all()
            exc_crits = [criteria_by_id[e.criterion_id].text for e in evals if e.criterion_id in criteria_by_id and criteria_by_id[e.criterion_id].is_exclusion]

            exc_data.append({
                "ID": p.id,
                "Título": p.title,
                "Autores": p.authors,
                "Ano": p.year,
                "DOI": p.doi or "",
                "Bases de Dados": sources_str,
                "Critérios de Exclusão Identificados": "; ".join(exc_crits),
                "Motivo / Observações": p.observations,
            })
        df_excluded = pd.DataFrame(exc_data)


        # ── Aba 4: Métricas PRISMA ─────────────────────────────────────
        runs = db.query(HarvestRunModel).filter(HarvestRunModel.project_id == project_id).all()
        total_found = sum(r.records_found for r in runs)
        total_dup = sum(r.records_duplicate for r in runs)

        prisma_data = [
            {"Etapa PRISMA 2020": "Total de Registros Identificados nas Bases", "Quantidade": total_found},
            {"Etapa PRISMA 2020": "Registros Duplicados Removidos", "Quantidade": total_dup},
            {"Etapa PRISMA 2020": "Registros Únicos Triados (Título e Resumo)", "Quantidade": len(all_papers)},
            {"Etapa PRISMA 2020": "Estudos Excluídos na Triagem 1", "Quantidade": len(excluded_papers)},
            {"Etapa PRISMA 2020": "Estudos Pendentes de Avaliação", "Quantidade": len(pending_papers)},
            {"Etapa PRISMA 2020": "Estudos Elegíveis / Incluídos na Síntese", "Quantidade": len(included_papers)},
        ]
        df_prisma = pd.DataFrame(prisma_data)

        # Gerar BytesIO
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_included.to_excel(writer, sheet_name="Artigos Incluídos", index=False)
            df_extraction.to_excel(writer, sheet_name="Extração de Dados", index=False)
            df_excluded.to_excel(writer, sheet_name="Artigos Excluídos", index=False)
            df_prisma.to_excel(writer, sheet_name="Métricas PRISMA 2020", index=False)

        output.seek(0)
        return output

    @staticmethod
    def generate_bibtex(db: Session, project_id: str, only_included: bool = True) -> str:
        """Gera arquivo BibTeX padronizado para gerenciadores de referências (Zotero, Mendeley, LaTeX)."""
        query = db.query(PaperModel).filter(PaperModel.project_id == project_id)
        if only_included:
            query = query.filter(PaperModel.decision == "Incluído")

        papers = query.all()
        bib_entries = []

        for p in papers:
            # Gerar chave de citação (ex: Smith2024Machine)
            first_author = p.authors.split(";")[0].split(",")[0].strip() if p.authors else "Unknown"
            first_author_clean = re.sub(r"[^a-zA-Z]", "", first_author)
            year_clean = p.year[:4] if p.year else "nodate"
            first_word = re.sub(r"[^a-zA-Z]", "", p.title.split()[0]) if p.title else "paper"
            cite_key = f"{first_author_clean}{year_clean}{first_word}"

            entry_type = "article" if "tese" not in p.research_type.lower() else "phdthesis"

            entry = f"@{entry_type}{{{cite_key},\n"
            entry += f"  title = {{{p.title}}},\n"
            if p.authors:
                entry += f"  author = {{{p.authors}}},\n"
            if p.year:
                entry += f"  year = {{{p.year}}},\n"
            if p.doi:
                entry += f"  doi = {{{p.doi}}},\n"
            if p.abstract:
                entry += f"  abstract = {{{p.abstract}}},\n"
            if p.download_url:
                entry += f"  url = {{{p.download_url}}},\n"
            entry += "}\n"
            bib_entries.append(entry)

        return "\n".join(bib_entries)

    @staticmethod
    def get_prisma_flow_data(db: Session, project_id: str) -> Dict:
        """Retorna estrutura de dados para o diagrama de fluxo PRISMA 2020."""
        runs = db.query(HarvestRunModel).filter(HarvestRunModel.project_id == project_id).all()
        total_found = sum(r.records_found for r in runs)
        total_duplicates = sum(r.records_duplicate for r in runs)

        by_source = {}
        for r in runs:
            by_source[r.source_name] = by_source.get(r.source_name, 0) + r.records_found

        all_papers = db.query(PaperModel).filter(PaperModel.project_id == project_id).all()
        included = [p for p in all_papers if p.decision == "Incluído"]
        excluded = [p for p in all_papers if p.decision == "Excluído"]
        pending = [p for p in all_papers if p.decision == "Pendente"]

        return {
            "identification": {
                "total_records_identified": total_found,
                "sources_breakdown": by_source,
                "duplicates_removed": total_duplicates,
            },
            "screening": {
                "records_screened": len(all_papers),
                "records_excluded": len(excluded),
                "records_pending": len(pending),
            },
            "included": {
                "studies_included_in_synthesis": len(included),
            },
        }
