#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Testes do ProfileService (Isolamento de Chaves, Exportação e Restauração de Perfil)."""

import json
from app.infrastructure.persistence.models import (
    AISettingsModel,
    CriterionModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    PaperModel,
    PaperSourceModel,
    ProjectModel,
    ProtocolModel,
    SourceCredentialModel,
)
from app.services.profile_service import ProfileService


def test_keys_isolation_and_export(db_session):
    service = ProfileService()

    # 1. Configurar configurações com chaves distintas para Gemini e Qwen
    settings = AISettingsModel(
        provider="gemini",
        model="gemini-3.6-flash",
        gemini_api_keys_encrypted=json.dumps(["AIzaSy_GEMINI_KEY_1", "AIzaSy_GEMINI_KEY_2"]),
        qwen_api_keys_encrypted=json.dumps(["sk-QWEN_KEY_1"]),
        local_api_keys_encrypted=json.dumps([]),
    )
    db_session.add(settings)

    # 2. Configurar credenciais de bases científicas
    scopus = SourceCredentialModel(source_name="SCOPUS", api_key="scopus_key_123", inst_token="scopus_token_abc")
    pubmed = SourceCredentialModel(source_name="PUBMED", api_key="ncbi_key_456")
    openalex = SourceCredentialModel(source_name="OPENALEX", api_key="researcher@university.edu")
    db_session.add_all([scopus, pubmed, openalex])
    db_session.commit()

    # 3. Exportar chaves
    exported = service.export_keys(db_session)

    assert exported["schema_version"] == "rsac_api_keys_v1"
    assert exported["gemini_api_keys"] == ["AIzaSy_GEMINI_KEY_1", "AIzaSy_GEMINI_KEY_2"]
    assert exported["qwen_api_keys"] == ["sk-QWEN_KEY_1"]
    assert exported["sources"]["SCOPUS"]["api_key"] == "scopus_key_123"
    assert exported["sources"]["SCOPUS"]["inst_token"] == "scopus_token_abc"
    assert exported["sources"]["PUBMED"]["api_key"] == "ncbi_key_456"
    assert exported["sources"]["OPENALEX"]["api_key"] == "researcher@university.edu"


def test_keys_import_json_and_env(db_session):
    service = ProfileService()

    # 1. Importar JSON estruturado
    json_payload = {
        "gemini_api_keys": ["AIzaSy_NEW_GEMINI_A", "AIzaSy_NEW_GEMINI_B"],
        "qwen_api_keys": ["sk-NEW_QWEN_KEY"],
        "sources": {
            "SCOPUS": {"api_key": "imported_scopus_key", "inst_token": "imported_token"},
            "PUBMED": {"api_key": "imported_pubmed_key"},
            "OPENALEX": {"api_key": "imported@domain.org"},
        },
    }

    result = service.import_keys(db_session, json_payload)
    assert result["status"] == "ok"
    assert result["gemini_keys_count"] == 2
    assert result["qwen_keys_count"] == 1

    settings = db_session.query(AISettingsModel).first()
    assert json.loads(settings.gemini_api_keys_encrypted) == ["AIzaSy_NEW_GEMINI_A", "AIzaSy_NEW_GEMINI_B"]
    assert json.loads(settings.qwen_api_keys_encrypted) == ["sk-NEW_QWEN_KEY"]

    scopus = db_session.query(SourceCredentialModel).filter_by(source_name="SCOPUS").first()
    assert scopus.api_key == "imported_scopus_key"

    # 2. Importar formato .env / texto puro
    env_text = """
    # Chaves de API do RSAC
    GEMINI_API_KEY=AIzaSy_ENV_GEMINI_1, AIzaSy_ENV_GEMINI_2
    DASHSCOPE_API_KEY=sk-ENV_QWEN_KEY
    SCOPUS_API_KEY=env_scopus_key
    SCOPUS_INST_TOKEN=env_token
    PUBMED_API_KEY=env_pubmed_key
    OPENALEX_EMAIL=env_user@edu.br
    """

    res_env = service.import_keys(db_session, env_text)
    assert res_env["status"] == "ok"
    assert res_env["gemini_keys_count"] == 2
    assert res_env["qwen_keys_count"] == 1

    db_session.refresh(settings)
    assert json.loads(settings.gemini_api_keys_encrypted) == ["AIzaSy_ENV_GEMINI_1", "AIzaSy_ENV_GEMINI_2"]
    assert json.loads(settings.qwen_api_keys_encrypted) == ["sk-ENV_QWEN_KEY"]


def test_full_profile_export_and_restoration(db_session):
    service = ProfileService()

    # 1. Criar projeto completo no banco
    project = ProjectModel(
        id="proj-1234-uuid",
        title="Revisão Sistemática em Arranjos Produtivos Locais",
        description="Avaliação de políticas públicas para APLs regionais.",
        methodology="PRISMA-ScR",
    )
    db_session.add(project)

    protocol = ProtocolModel(
        id="prot-1234-uuid",
        project_id="proj-1234-uuid",
        objective="Mapear evidências sobre sustentabilidade em APLs",
        pico_framework=json.dumps({"population": "APLs", "context": "Brasil"}),
        search_descriptors=json.dumps({"pt": ['"arranjo produtivo local" AND "governança"']}),
    )
    db_session.add(protocol)

    criterion1 = CriterionModel(
        id="crit-1",
        protocol_id="prot-1234-uuid",
        text="Estudos focados em governança de APLs",
        is_exclusion=False,
        order=0,
    )
    criterion2 = CriterionModel(
        id="crit-2",
        protocol_id="prot-1234-uuid",
        text="Ensaios clínicos ou área médica",
        is_exclusion=True,
        order=1,
    )
    db_session.add_all([criterion1, criterion2])

    question1 = ExtractionQuestionModel(
        id="q-1",
        protocol_id="prot-1234-uuid",
        text="Quais são os principais fatores de sucesso institucional identificados?",
        order=0,
    )
    db_session.add(question1)

    paper = PaperModel(
        id="paper-100",
        project_id="proj-1234-uuid",
        title="Dinâmicas Territoriais e Governança no APL Calçadista de Franca",
        authors="Silva, M.; Santos, A.",
        year="2023",
        doi="10.1234/apl.2023.001",
        abstract="Este artigo analisa o papel da governança local no desenvolvimento regional...",
        decision="Incluído",
    )
    db_session.add(paper)

    source = PaperSourceModel(
        paper_id="paper-100",
        source_name="BDTD",
        source_id="bdtd:10293",
    )
    db_session.add(source)

    answer = ExtractionAnswerModel(
        paper_id="paper-100",
        question_id="q-1",
        answer="Cooperação interinstitucional e capacitação técnica contínua.",
        evidence="O estudo aponta cooperação como pilar central (pág. 14).",
        page_ref="14",
        source_kind="pdf",
    )
    db_session.add(answer)

    settings = AISettingsModel(
        provider="qwen",
        model="qwen3.8-max",
        gemini_api_keys_encrypted=json.dumps(["AIza_GEMINI_BACKUP"]),
        qwen_api_keys_encrypted=json.dumps(["sk-QWEN_BACKUP"]),
    )
    db_session.add(settings)
    db_session.commit()

    # 2. Exportar Perfil Completo
    session_prefs = {
        "theme": "lava-steel",
        "active_project_id": "proj-1234-uuid",
        "sidebar_collapsed": True,
        "ai_enabled": True,
    }
    profile_data = service.export_profile(db_session, session_prefs)

    assert profile_data["schema_version"] == "rsac_profile_v1"
    assert profile_data["session_preferences"]["theme"] == "lava-steel"
    assert len(profile_data["projects"]) == 1
    assert profile_data["projects"][0]["title"] == "Revisão Sistemática em Arranjos Produtivos Locais"
    assert len(profile_data["projects"][0]["papers"]) == 1
    assert len(profile_data["projects"][0]["papers"][0]["extraction_answers"]) == 1

    # 3. Limpar tabelas e restaurar a partir do arquivo de perfil exportado
    db_session.query(ExtractionAnswerModel).delete()
    db_session.query(PaperSourceModel).delete()
    db_session.query(PaperModel).delete()
    db_session.query(ExtractionQuestionModel).delete()
    db_session.query(CriterionModel).delete()
    db_session.query(ProtocolModel).delete()
    db_session.query(ProjectModel).delete()
    db_session.query(AISettingsModel).delete()
    db_session.commit()

    # Restaurar
    import_res = service.import_profile(db_session, profile_data)
    assert import_res["status"] == "ok"
    assert import_res["projects_imported"] == 1
    assert import_res["papers_imported"] == 1
    assert import_res["extractions_imported"] == 1
    assert import_res["restored_session"]["theme"] == "lava-steel"

    # Verificar que tudo foi restaurado perfeitamente
    restored_proj = db_session.query(ProjectModel).filter_by(id="proj-1234-uuid").first()
    assert restored_proj is not None
    assert restored_proj.title == "Revisão Sistemática em Arranjos Produtivos Locais"

    restored_paper = db_session.query(PaperModel).filter_by(id="paper-100").first()
    assert restored_paper is not None
    assert restored_paper.decision == "Incluído"

    restored_answer = db_session.query(ExtractionAnswerModel).filter_by(paper_id="paper-100").first()
    assert restored_answer is not None
    assert restored_answer.page_ref == "14"
    assert "Cooperação" in restored_answer.answer
