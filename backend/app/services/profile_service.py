#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Profile & API Keys Backup and Restore Service.
Serviço para exportação e restauração padronizada de chaves de API e perfis completos de workspace.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    AISettingsModel,
    AuditLogModel,
    CriterionModel,
    DeduplicationReportModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    HarvestRunModel,
    PaperCriterionModel,
    PaperModel,
    PaperSourceModel,
    ProjectModel,
    ProtocolModel,
    SourceCredentialModel,
)

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_keys_list(raw_value: Any) -> List[str]:
    if not raw_value:
        return []
    if isinstance(raw_value, list):
        return [str(k).strip() for k in raw_value if str(k).strip()]
    if isinstance(raw_value, str):
        raw_value = raw_value.strip()
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return [str(k).strip() for k in parsed if str(k).strip()]
            elif isinstance(parsed, str) and parsed.strip():
                return [parsed.strip()]
        except Exception:
            return [raw_value]
    return []


class ProfileService:
    """Gerencia exportação e importação de chaves e perfis completos do sistema."""

    # ─────────────────────────────────────────────────────────────────
    # 1. GESTÃO DE CHAVES DE API
    # ─────────────────────────────────────────────────────────────────

    def export_keys(self, db: Session) -> Dict[str, Any]:
        """Exporta todas as chaves de API cadastradas em formato estruturado padronizado."""
        settings = db.query(AISettingsModel).first()
        gemini_keys = _parse_keys_list(settings.gemini_api_keys_encrypted if settings else None)
        qwen_keys = _parse_keys_list(settings.qwen_api_keys_encrypted if settings else None)
        local_keys = _parse_keys_list(settings.local_api_keys_encrypted if settings else None)
        legacy_keys = _parse_keys_list(settings.api_keys_encrypted if settings else None)

        if not gemini_keys and settings and settings.provider == "gemini" and legacy_keys:
            gemini_keys = legacy_keys
        if not qwen_keys and settings and settings.provider == "qwen" and legacy_keys:
            qwen_keys = legacy_keys

        creds = db.query(SourceCredentialModel).all()
        sources_dict = {}
        for c in creds:
            sources_dict[c.source_name.upper()] = {
                "api_key": c.api_key or "",
                "inst_token": c.inst_token or "",
                "custom_endpoint": c.custom_endpoint,
            }

        return {
            "schema_version": "rsac_api_keys_v1",
            "exported_at": _utc_now_iso(),
            "gemini_api_keys": gemini_keys,
            "qwen_api_keys": qwen_keys,
            "local_api_keys": local_keys,
            "sources": sources_dict,
        }

    def import_keys(self, db: Session, raw_input: Any) -> Dict[str, Any]:
        """
        Importa chaves a partir de JSON estruturado ou arquivo texto tipo .env.
        Salva isoladamente chaves do Gemini, Qwen e credenciais de bases científicas.
        """
        gemini_keys: List[str] = []
        qwen_keys: List[str] = []
        local_keys: List[str] = []
        sources_dict: Dict[str, Dict[str, Any]] = {}

        if isinstance(raw_input, str):
            text_content = raw_input.strip()
            # Tentar ler como JSON
            try:
                data = json.loads(text_content)
                if isinstance(data, dict):
                    raw_input = data
            except Exception:
                # Tratar como formato .env / KEY=VALUE
                for line in text_content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip().upper()
                        v = v.strip().strip('"').strip("'")
                        if not v:
                            continue

                        if "GEMINI" in k:
                            gemini_keys.extend([x.strip() for x in v.split(",") if x.strip()])
                        elif "QWEN" in k or "DASHSCOPE" in k:
                            qwen_keys.extend([x.strip() for x in v.split(",") if x.strip()])
                        elif "LOCAL" in k or "OLLAMA" in k:
                            local_keys.extend([x.strip() for x in v.split(",") if x.strip()])
                        elif "SCOPUS_INST" in k or "SCOPUS_TOKEN" in k:
                            sources_dict.setdefault("SCOPUS", {})["inst_token"] = v
                        elif "SCOPUS" in k:
                            sources_dict.setdefault("SCOPUS", {})["api_key"] = v
                        elif "PUBMED" in k or "NCBI" in k:
                            sources_dict.setdefault("PUBMED", {})["api_key"] = v
                        elif "OPENALEX" in k:
                            sources_dict.setdefault("OPENALEX", {})["api_key"] = v

        if isinstance(raw_input, dict):
            if "gemini_api_keys" in raw_input:
                gemini_keys = _parse_keys_list(raw_input.get("gemini_api_keys"))
            elif "gemini_keys" in raw_input:
                gemini_keys = _parse_keys_list(raw_input.get("gemini_keys"))

            if "qwen_api_keys" in raw_input:
                qwen_keys = _parse_keys_list(raw_input.get("qwen_api_keys"))
            elif "qwen_keys" in raw_input:
                qwen_keys = _parse_keys_list(raw_input.get("qwen_keys"))

            if "local_api_keys" in raw_input:
                local_keys = _parse_keys_list(raw_input.get("local_api_keys"))

            # Chaves aninhadas sob 'ai'
            if "ai" in raw_input and isinstance(raw_input["ai"], dict):
                ai_block = raw_input["ai"]
                if "gemini_api_keys" in ai_block:
                    gemini_keys = _parse_keys_list(ai_block.get("gemini_api_keys"))
                if "qwen_api_keys" in ai_block:
                    qwen_keys = _parse_keys_list(ai_block.get("qwen_api_keys"))
                if "local_api_keys" in ai_block:
                    local_keys = _parse_keys_list(ai_block.get("local_api_keys"))

            # Credenciais das bases científicas
            src_block = raw_input.get("sources") or raw_input.get("source_credentials") or {}
            if isinstance(src_block, dict):
                for src_name, src_val in src_block.items():
                    if isinstance(src_val, dict):
                        sources_dict[src_name.upper()] = {
                            "api_key": src_val.get("api_key", ""),
                            "inst_token": src_val.get("inst_token", ""),
                            "custom_endpoint": src_val.get("custom_endpoint"),
                        }
            elif isinstance(src_block, list):
                for item in src_block:
                    if isinstance(item, dict) and "source_name" in item:
                        sources_dict[item["source_name"].upper()] = {
                            "api_key": item.get("api_key", ""),
                            "inst_token": item.get("inst_token", ""),
                            "custom_endpoint": item.get("custom_endpoint"),
                        }

        # 1. Salvar no AISettingsModel
        settings = db.query(AISettingsModel).first()
        if not settings:
            settings = AISettingsModel()
            db.add(settings)

        if gemini_keys:
            settings.gemini_api_keys_encrypted = json.dumps(gemini_keys)
        if qwen_keys:
            settings.qwen_api_keys_encrypted = json.dumps(qwen_keys)
        if local_keys:
            settings.local_api_keys_encrypted = json.dumps(local_keys)

        # 2. Salvar credenciais de bases científicas
        configured_sources = []
        for src_name, cred_data in sources_dict.items():
            s_model = (
                db.query(SourceCredentialModel)
                .filter(SourceCredentialModel.source_name == src_name)
                .first()
            )
            if not s_model:
                s_model = SourceCredentialModel(source_name=src_name)
                db.add(s_model)

            if "api_key" in cred_data and cred_data["api_key"] is not None:
                s_model.api_key = cred_data["api_key"].strip()
            if "inst_token" in cred_data and cred_data["inst_token"] is not None:
                s_model.inst_token = cred_data["inst_token"].strip()
            if "custom_endpoint" in cred_data:
                s_model.custom_endpoint = cred_data["custom_endpoint"]

            configured_sources.append(src_name)

        db.commit()

        return {
            "status": "ok",
            "message": "Chaves de API importadas e configuradas com sucesso!",
            "gemini_keys_count": len(gemini_keys),
            "qwen_keys_count": len(qwen_keys),
            "local_keys_count": len(local_keys),
            "sources_configured": configured_sources,
        }

    # ─────────────────────────────────────────────────────────────────
    # 2. GESTÃO DE PERFIL COMPLETO (WORKSPACE & SESSÃO)
    # ─────────────────────────────────────────────────────────────────

    def export_profile(self, db: Session, session_prefs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Exporta o perfil completo de sessão, preferências, configurações de IA,
        credenciais e todos os projetos com seus dados (estudos, extrações, protocolos).
        """
        # 1. Configurações de IA
        ai_settings_model = db.query(AISettingsModel).first()
        ai_settings_data = {
            "ai_enabled": ai_settings_model.ai_enabled if ai_settings_model else True,
            "provider": ai_settings_model.provider if ai_settings_model else "gemini",
            "model": ai_settings_model.model if ai_settings_model else "gemini-3.6-flash",
            "gemini_api_keys": _parse_keys_list(ai_settings_model.gemini_api_keys_encrypted if ai_settings_model else None),
            "qwen_api_keys": _parse_keys_list(ai_settings_model.qwen_api_keys_encrypted if ai_settings_model else None),
            "local_api_keys": _parse_keys_list(ai_settings_model.local_api_keys_encrypted if ai_settings_model else None),
            "endpoint": ai_settings_model.endpoint if ai_settings_model else None,
            "temperature": ai_settings_model.temperature if ai_settings_model else 0.2,
            "max_tokens": ai_settings_model.max_tokens if ai_settings_model else 4096,
        }

        # 2. Credenciais de Fontes
        source_creds_list = []
        for cred in db.query(SourceCredentialModel).all():
            source_creds_list.append({
                "source_name": cred.source_name,
                "api_key": cred.api_key or "",
                "inst_token": cred.inst_token or "",
                "custom_endpoint": cred.custom_endpoint,
            })

        # 3. Projetos completos
        projects_list = []
        projects = db.query(ProjectModel).all()

        for p in projects:
            p_data = {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "methodology": p.methodology,
                "is_archived": p.is_archived,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "protocol": None,
                "papers": [],
                "harvest_runs": [],
                "deduplication_report": None,
            }

            # Protocolo
            if p.protocol:
                prot = p.protocol
                p_data["protocol"] = {
                    "id": prot.id,
                    "objective": prot.objective,
                    "pico_framework": prot.pico_framework,
                    "search_descriptors": prot.search_descriptors,
                    "search_filters": prot.search_filters,
                    "manuscript_sections": prot.manuscript_sections,
                    "criteria": [
                        {
                            "id": c.id,
                            "text": c.text,
                            "is_exclusion": c.is_exclusion,
                            "order": c.order,
                        }
                        for c in prot.criteria
                    ],
                    "extraction_questions": [
                        {
                            "id": q.id,
                            "text": q.text,
                            "order": q.order,
                        }
                        for q in prot.extraction_questions
                    ],
                }

            # Papers
            for paper in p.papers:
                paper_data = {
                    "id": paper.id,
                    "title": paper.title,
                    "title_normalized": paper.title_normalized,
                    "blocking_key": paper.blocking_key,
                    "authors": paper.authors,
                    "advisor": paper.advisor,
                    "year": paper.year,
                    "doi": paper.doi,
                    "abstract": paper.abstract,
                    "research_type": paper.research_type,
                    "institution": paper.institution,
                    "journal": paper.journal,
                    "download_url": paper.download_url,
                    "decision": paper.decision,
                    "observations": paper.observations,
                    "ai_confidence": paper.ai_confidence,
                    "pdf_path": paper.pdf_path,
                    "pdf_text_extracted": paper.pdf_text_extracted,
                    "pdf_status": paper.pdf_status,
                    "pdf_resolved_url": paper.pdf_resolved_url,
                    "pdf_strategy": paper.pdf_strategy,
                    "pdf_attempts": paper.pdf_attempts,
                    "pdf_page_count": paper.pdf_page_count,
                    "pdf_size_bytes": paper.pdf_size_bytes,
                    "pdf_sha256": paper.pdf_sha256,
                    "pdf_text_chars": paper.pdf_text_chars,
                    "pdf_is_scanned": paper.pdf_is_scanned,
                    "is_duplicate": paper.is_duplicate,
                    "merged_into_id": paper.merged_into_id,
                    "created_at": paper.created_at.isoformat() if paper.created_at else None,
                    "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
                    "sources": [
                        {
                            "source_name": s.source_name,
                            "source_id": s.source_id,
                            "harvested_at": s.harvested_at.isoformat() if s.harvested_at else None,
                        }
                        for s in paper.sources
                    ],
                    "criteria_evaluations": [
                        {
                            "criterion_id": ce.criterion_id,
                            "value": ce.value,
                        }
                        for ce in paper.criteria_evaluations
                    ],
                    "extraction_answers": [
                        {
                            "question_id": ea.question_id,
                            "answer": ea.answer,
                            "ai_generated": ea.ai_generated,
                            "evidence": ea.evidence,
                            "page_ref": ea.page_ref,
                            "source_kind": ea.source_kind,
                            "created_at": ea.created_at.isoformat() if ea.created_at else None,
                        }
                        for ea in paper.extraction_answers
                    ],
                    "audit_logs": [
                        {
                            "action": al.action,
                            "old_value": al.old_value,
                            "new_value": al.new_value,
                            "source": al.source,
                            "created_at": al.created_at.isoformat() if al.created_at else None,
                        }
                        for al in paper.audit_logs
                    ],
                }
                p_data["papers"].append(paper_data)

            # Relatório de Deduplicação
            dedup_report = (
                db.query(DeduplicationReportModel)
                .filter(DeduplicationReportModel.project_id == p.id)
                .first()
            )
            if dedup_report:
                p_data["deduplication_report"] = {
                    "total_raw": dedup_report.total_raw,
                    "total_unique": dedup_report.total_unique,
                    "total_duplicates": dedup_report.total_duplicates,
                    "sources_breakdown": dedup_report.sources_breakdown,
                    "duplicates_list": dedup_report.duplicates_list,
                    "report_text": dedup_report.report_text,
                    "created_at": dedup_report.created_at.isoformat() if dedup_report.created_at else None,
                }

            # Harvest Runs
            for hr in p.harvest_runs:
                p_data["harvest_runs"].append({
                    "id": hr.id,
                    "source_name": hr.source_name,
                    "descriptors_used": hr.descriptors_used,
                    "query_parameters": hr.query_parameters,
                    "checkpoint": hr.checkpoint,
                    "started_at": hr.started_at.isoformat() if hr.started_at else None,
                    "completed_at": hr.completed_at.isoformat() if hr.completed_at else None,
                    "records_found": hr.records_found,
                    "records_new": hr.records_new,
                    "records_duplicate": hr.records_duplicate,
                    "status": hr.status,
                    "error_message": hr.error_message,
                })

            projects_list.append(p_data)

        prefs = session_prefs or {}

        return {
            "schema_version": "rsac_profile_v1",
            "app_version": "2.0.0",
            "exported_at": _utc_now_iso(),
            "session_preferences": {
                "theme": prefs.get("theme", "dark"),
                "active_project_id": prefs.get("active_project_id"),
                "sidebar_collapsed": prefs.get("sidebar_collapsed", False),
                "ai_enabled": prefs.get("ai_enabled", True),
            },
            "ai_settings": ai_settings_data,
            "source_credentials": source_creds_list,
            "projects": projects_list,
        }

    def import_profile(
        self, db: Session, profile_data: Dict[str, Any], merge_mode: str = "merge"
    ) -> Dict[str, Any]:
        """
        Restaura o perfil completo (sessão, chaves, configurações e projetos).
        Suporta modo merge ou substituição segura.
        """
        projects_count = 0
        papers_count = 0
        extractions_count = 0

        # 1. Restaurar Configurações de IA
        ai_data = profile_data.get("ai_settings", {})
        if ai_data:
            settings = db.query(AISettingsModel).first()
            if not settings:
                settings = AISettingsModel()
                db.add(settings)

            settings.ai_enabled = ai_data.get("ai_enabled", True)
            settings.provider = ai_data.get("provider", "gemini").lower()
            settings.model = ai_data.get("model", "gemini-3.6-flash")
            settings.endpoint = ai_data.get("endpoint")
            settings.temperature = float(ai_data.get("temperature", 0.2))
            settings.max_tokens = int(ai_data.get("max_tokens", 4096))

            gemini_keys = _parse_keys_list(ai_data.get("gemini_api_keys"))
            qwen_keys = _parse_keys_list(ai_data.get("qwen_api_keys"))
            local_keys = _parse_keys_list(ai_data.get("local_api_keys"))

            if gemini_keys:
                settings.gemini_api_keys_encrypted = json.dumps(gemini_keys)
            if qwen_keys:
                settings.qwen_api_keys_encrypted = json.dumps(qwen_keys)
            if local_keys:
                settings.local_api_keys_encrypted = json.dumps(local_keys)

        # 2. Restaurar Credenciais de Fontes
        src_creds = profile_data.get("source_credentials", [])
        for sc in src_creds:
            s_name = sc.get("source_name", "").upper()
            if not s_name:
                continue
            model = (
                db.query(SourceCredentialModel)
                .filter(SourceCredentialModel.source_name == s_name)
                .first()
            )
            if not model:
                model = SourceCredentialModel(source_name=s_name)
                db.add(model)
            model.api_key = sc.get("api_key", "").strip()
            model.inst_token = sc.get("inst_token", "").strip()
            model.custom_endpoint = sc.get("custom_endpoint")

        # 3. Restaurar Projetos
        projects_data = profile_data.get("projects", [])
        for p_in in projects_data:
            p_id = p_in.get("id")
            if not p_id:
                continue

            project = db.query(ProjectModel).filter(ProjectModel.id == p_id).first()
            if not project:
                project = ProjectModel(id=p_id)
                db.add(project)

            project.title = p_in.get("title", "Projeto Importado")
            project.description = p_in.get("description", "")
            project.methodology = p_in.get("methodology", "PRISMA-ScR")
            project.is_archived = p_in.get("is_archived", False)
            projects_count += 1

            # Protocolo
            prot_in = p_in.get("protocol")
            if prot_in:
                prot = db.query(ProtocolModel).filter(ProtocolModel.project_id == p_id).first()
                if not prot:
                    prot = ProtocolModel(id=prot_in.get("id"), project_id=p_id)
                    db.add(prot)
                prot.objective = prot_in.get("objective", "")
                prot.pico_framework = prot_in.get("pico_framework", "{}")
                prot.search_descriptors = prot_in.get("search_descriptors", "{}")
                prot.search_filters = prot_in.get("search_filters", "{}")
                prot.manuscript_sections = prot_in.get("manuscript_sections", "{}")

                # Critérios
                for c_in in prot_in.get("criteria", []):
                    c_id = c_in.get("id")
                    crit = db.query(CriterionModel).filter(CriterionModel.id == c_id).first()
                    if not crit:
                        crit = CriterionModel(id=c_id, protocol_id=prot.id)
                        db.add(crit)
                    crit.text = c_in.get("text", "")
                    crit.is_exclusion = c_in.get("is_exclusion", False)
                    crit.order = c_in.get("order", 0)

                # Perguntas de Extração
                for q_in in prot_in.get("extraction_questions", []):
                    q_id = q_in.get("id")
                    eq = db.query(ExtractionQuestionModel).filter(ExtractionQuestionModel.id == q_id).first()
                    if not eq:
                        eq = ExtractionQuestionModel(id=q_id, protocol_id=prot.id)
                        db.add(eq)
                    eq.text = q_in.get("text", "")
                    eq.order = q_in.get("order", 0)

            # Papers
            for paper_in in p_in.get("papers", []):
                paper_id = paper_in.get("id")
                paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
                if not paper:
                    paper = PaperModel(id=paper_id, project_id=p_id, title=paper_in.get("title", ""))
                    db.add(paper)

                paper.title = paper_in.get("title", "")
                paper.title_normalized = paper_in.get("title_normalized", "")
                paper.blocking_key = paper_in.get("blocking_key", "")
                paper.authors = paper_in.get("authors", "")
                paper.advisor = paper_in.get("advisor", "")
                paper.year = str(paper_in.get("year", ""))
                paper.doi = paper_in.get("doi")
                paper.abstract = paper_in.get("abstract", "")
                paper.research_type = paper_in.get("research_type", "")
                paper.institution = paper_in.get("institution", "")
                paper.journal = paper_in.get("journal", "")
                paper.download_url = paper_in.get("download_url", "")
                paper.decision = paper_in.get("decision", "Pendente")
                paper.observations = paper_in.get("observations", "")
                paper.ai_confidence = paper_in.get("ai_confidence")
                paper.pdf_path = paper_in.get("pdf_path")
                paper.pdf_text_extracted = paper_in.get("pdf_text_extracted", False)
                paper.pdf_status = paper_in.get("pdf_status", "ausente")
                paper.pdf_resolved_url = paper_in.get("pdf_resolved_url", "")
                paper.pdf_strategy = paper_in.get("pdf_strategy", "")
                paper.pdf_attempts = paper_in.get("pdf_attempts", "[]")
                paper.pdf_page_count = int(paper_in.get("pdf_page_count", 0))
                paper.pdf_size_bytes = int(paper_in.get("pdf_size_bytes", 0))
                paper.pdf_sha256 = paper_in.get("pdf_sha256", "")
                paper.pdf_text_chars = int(paper_in.get("pdf_text_chars", 0))
                paper.pdf_is_scanned = paper_in.get("pdf_is_scanned", False)
                paper.is_duplicate = paper_in.get("is_duplicate", False)
                paper.merged_into_id = paper_in.get("merged_into_id")
                papers_count += 1

                # Fontes do Paper
                for src_in in paper_in.get("sources", []):
                    s_name = src_in.get("source_name")
                    if s_name:
                        existing_src = (
                            db.query(PaperSourceModel)
                            .filter(
                                PaperSourceModel.paper_id == paper_id,
                                PaperSourceModel.source_name == s_name,
                            )
                            .first()
                        )
                        if not existing_src:
                            existing_src = PaperSourceModel(
                                paper_id=paper_id,
                                source_name=s_name,
                                source_id=src_in.get("source_id", ""),
                            )
                            db.add(existing_src)

                # Avaliações de Critérios
                for ce_in in paper_in.get("criteria_evaluations", []):
                    c_id = ce_in.get("criterion_id")
                    if c_id:
                        existing_ce = (
                            db.query(PaperCriterionModel)
                            .filter(
                                PaperCriterionModel.paper_id == paper_id,
                                PaperCriterionModel.criterion_id == c_id,
                            )
                            .first()
                        )
                        if not existing_ce:
                            existing_ce = PaperCriterionModel(
                                paper_id=paper_id,
                                criterion_id=c_id,
                                value=ce_in.get("value", True),
                            )
                            db.add(existing_ce)
                        else:
                            existing_ce.value = ce_in.get("value", True)

                # Respostas de Extração
                for ea_in in paper_in.get("extraction_answers", []):
                    q_id = ea_in.get("question_id")
                    if q_id:
                        existing_ea = (
                            db.query(ExtractionAnswerModel)
                            .filter(
                                ExtractionAnswerModel.paper_id == paper_id,
                                ExtractionAnswerModel.question_id == q_id,
                            )
                            .first()
                        )
                        if not existing_ea:
                            existing_ea = ExtractionAnswerModel(
                                paper_id=paper_id,
                                question_id=q_id,
                            )
                            db.add(existing_ea)
                        existing_ea.answer = ea_in.get("answer", "")
                        existing_ea.ai_generated = ea_in.get("ai_generated", False)
                        existing_ea.evidence = ea_in.get("evidence", "")
                        existing_ea.page_ref = ea_in.get("page_ref", "")
                        existing_ea.source_kind = ea_in.get("source_kind", "")
                        extractions_count += 1

                # Logs de Auditoria
                for al_in in paper_in.get("audit_logs", []):
                    al = AuditLogModel(
                        paper_id=paper_id,
                        action=al_in.get("action", "import"),
                        old_value=al_in.get("old_value"),
                        new_value=al_in.get("new_value", ""),
                        source=al_in.get("source", "profile_import"),
                    )
                    db.add(al)

            # Relatório de Deduplicação
            dedup_in = p_in.get("deduplication_report")
            if dedup_in:
                dr = (
                    db.query(DeduplicationReportModel)
                    .filter(DeduplicationReportModel.project_id == p_id)
                    .first()
                )
                if not dr:
                    dr = DeduplicationReportModel(project_id=p_id)
                    db.add(dr)
                dr.total_raw = dedup_in.get("total_raw", 0)
                dr.total_unique = dedup_in.get("total_unique", 0)
                dr.total_duplicates = dedup_in.get("total_duplicates", 0)
                dr.sources_breakdown = dedup_in.get("sources_breakdown", "{}")
                dr.duplicates_list = dedup_in.get("duplicates_list", "[]")
                dr.report_text = dedup_in.get("report_text", "")

        db.commit()

        restored_session = profile_data.get("session_preferences", {})
        return {
            "status": "ok",
            "message": f"Perfil restaurado com sucesso! ({projects_count} projetos, {papers_count} estudos e {extractions_count} extrações importados).",
            "projects_imported": projects_count,
            "papers_imported": papers_count,
            "extractions_imported": extractions_count,
            "restored_session": restored_session,
        }
