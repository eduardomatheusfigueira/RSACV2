#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Testes da Qualificação dos Protocolos (Doc 45 — 4 Eixos, Estratégia, Versões e Catálogo)."""

import json
import pytest
from app.infrastructure.persistence.models import (
    CriterionModel,
    ExtractionQuestionModel,
    ProjectModel,
    ProtocolModel,
    UserModel,
)
from app.services.protocol_catalog_service import (
    get_full_protocol_catalog,
    get_review_design,
)
from app.services.protocol_service import calculate_protocol_readiness, get_scope_stamp
from app.services.protocol_version_service import (
    freeze_protocol_version,
    record_protocol_amendment,
)
from app.services.search_strategy_service import (
    render_bdtd_decomposition,
    render_canonical_query,
    render_pubmed_query,
    render_scopus_query,
    run_press_review,
)


def test_protocol_catalog_content():
    """Valida se o catálogo metodológico contém todos os 14 desenhos e metadados completos."""
    catalog = get_full_protocol_catalog()
    assert len(catalog.designs) == 14
    design_ids = [d.id for d in catalog.designs]
    assert "D1" in design_ids
    assert "D4" in design_ids
    assert "D11" in design_ids
    assert "D14" in design_ids

    # D4 - Scoping Review
    d4 = get_review_design("D4")
    assert d4 is not None
    assert d4.default_framework == "PCC"
    assert d4.default_reporting == "PRISMA-ScR"
    assert d4.critical_appraisal_requirement == "opcional"
    assert len(d4.suggested_extraction_questions) >= 3

    # D11 - Bibliometria
    d11 = get_review_design("D11")
    assert d11 is not None
    assert d11.default_reporting == "BIBLIO"
    assert d11.critical_appraisal_requirement == "nao_se_aplica"


def test_canonical_query_rendering():
    """Valida renderização de query canônica com blocos conceituais e aspas."""
    blocks = [
        {"key": "A", "label": "População", "terms": ["desenvolvimento regional", "planejamento territorial"]},
        {"key": "B", "label": "Conceito", "terms": ["inovação", "arranjos produtivos locais"]},
    ]
    canonical = render_canonical_query(blocks, "A AND B")
    assert '("desenvolvimento regional" OR "planejamento territorial")' in canonical
    assert '(inovação OR "arranjos produtivos locais")' in canonical
    assert " AND " in canonical


def test_scopus_and_pubmed_adapters():
    """Valida os adaptadores de sintaxe para Scopus e PubMed."""
    blocks = [
        {"key": "A", "label": "População", "terms": ["cidades inteligentes", "governança"]},
        {"key": "B", "label": "Conceito", "terms": ["sustentabilidade"]},
    ]
    # Scopus
    scopus_q, scopus_note = render_scopus_query(blocks, limits={"year_start": 2020, "year_end": 2024})
    assert scopus_q.startswith("TITLE-ABS-KEY(")
    assert "PUBYEAR > 2019" in scopus_q
    assert "PUBYEAR < 2025" in scopus_q
    assert "Scopus" in scopus_note

    # PubMed
    pubmed_q, pubmed_note = render_pubmed_query(blocks)
    assert '[tiab]' in pubmed_q
    assert "PubMed" in pubmed_note


def test_bdtd_decomposition():
    """Valida decomposição declarada em N pares para o motor VuFind da BDTD."""
    blocks = [
        {"key": "A", "label": "População", "terms": ["política pública", "território"]},
        {"key": "B", "label": "Conceito", "terms": ["desenvolvimento", "inovação"]},
    ]
    pairs, note = render_bdtd_decomposition(blocks, max_pairs=5)
    assert len(pairs) == 4
    assert '"política pública" AND desenvolvimento' in pairs
    assert '"política pública" AND inovação' in pairs
    assert "VuFind" in note


def test_press_heuristic_review():
    """Valida a análise heurística PRESS dos 6 domínios."""
    blocks = [
        {"key": "A", "label": "População", "terms": ["economia circular", "resíduos"]},
        {"key": "B", "label": "Conceito", "terms": ["gestão urbana", "políticas ambientais"]},
    ]
    result = run_press_review(blocks, "A AND B")
    assert result["score_percentage"] >= 80
    assert len(result["domains"]) == 6
    assert all("domain" in d and "passed" in d for d in result["domains"])


def test_protocol_freeze_and_sha256(db_session):
    """Valida congelamento de versão e cálculo determinístico de SHA-256."""
    user = UserModel(username="pesquisador_v", email="v@example.com")
    db_session.add(user)
    db_session.flush()

    project = ProjectModel(owner_id=user.id, title="Projeto Teste Versão", description="Desc")
    db_session.add(project)
    db_session.flush()

    protocol = ProtocolModel(
        project_id=project.id,
        objective="Investigar o desenvolvimento regional sustentável",
        review_design="D4",
        reporting_guideline="PRISMA-ScR",
    )
    db_session.add(protocol)
    db_session.flush()

    crit = CriterionModel(protocol_id=protocol.id, text="Estudos sobre APLs", is_exclusion=False)
    q = ExtractionQuestionModel(protocol_id=protocol.id, text="Qual o foco setorial?")
    db_session.add_all([crit, q])
    db_session.commit()

    # Congelamento v1.0
    v1 = freeze_protocol_version(protocol, "v1.0", user.id, db_session)
    assert v1.label == "v1.0"
    assert len(v1.content_hash) == 64  # SHA-256 hex
    assert protocol.status == "vigente"
    assert protocol.current_version == "v1.0"

    # Emenda v1.1
    amendment = record_protocol_amendment(
        protocol=protocol,
        from_version="v1.0",
        to_version="v1.1",
        reason="Inclusão de critério temporal estendido",
        project_phase="coleta",
        user_id=user.id,
        db=db_session,
    )
    assert amendment.from_version == "v1.0"
    assert amendment.to_version == "v1.1"
    assert protocol.current_version == "v1.1"


def test_protocol_readiness_and_scope_stamp(db_session):
    """Valida cálculo de prontidão e geração do carimbo de escopo."""
    user = UserModel(username="pesquisador_p", email="p@example.com")
    db_session.add(user)
    db_session.flush()

    project = ProjectModel(owner_id=user.id, title="Projeto Teste Prontidão", description="Desc")
    db_session.add(project)
    db_session.flush()

    protocol = ProtocolModel(
        project_id=project.id,
        mode="simplificado",
        objective="Objetivo claro de pesquisa e revisão sistemática",
        review_design="D4",
        reporting_guideline="PRISMA-ScR",
    )
    db_session.add(protocol)
    db_session.commit()

    stamp = get_scope_stamp("simplificado")
    assert stamp is not None
    assert "PRISMA-S" in stamp

    readiness = calculate_protocol_readiness(protocol, db_session)
    assert readiness.mode == "simplificado"
    assert len(readiness.gates) == 4
    assert any(g.stage == "coleta" for g in readiness.gates)


@pytest.mark.anyio
async def test_api_protocol_catalog(async_client):
    """Testa a rota GET /api/v1/protocol-catalog."""
    res = await async_client.get("/api/v1/protocol-catalog")
    assert res.status_code == 200
    data = res.json()
    assert "designs" in data
    assert len(data["designs"]) == 14
    assert "guidelines" in data
    assert "frameworks" in data
    assert "instruments" in data


@pytest.mark.anyio
async def test_api_protocol_mode_and_design(async_client, db_session, contas):
    """Testa a troca de modo (simplificado/completo) e de desenho metodológico."""
    # 1. Cria projeto com owner_id
    owner = contas["owner"]
    project = ProjectModel(
        owner_id=owner.id,
        title="Projeto API Teste",
        description="Desc",
        methodology="PRISMA-ScR",
    )
    db_session.add(project)
    db_session.flush()

    protocol = ProtocolModel(
        project_id=project.id,
        objective="Objetivo API",
        review_design="D4",
        reporting_guideline="PRISMA-ScR",
    )
    db_session.add(protocol)
    db_session.commit()

    # 2. Troca de modo
    res_mode = await async_client.post(
        f"/api/v1/projects/{project.id}/protocol/mode",
        json={"mode": "simplificado"},
    )
    assert res_mode.status_code == 200
    assert res_mode.json()["mode"] == "simplificado"
    assert res_mode.json()["scope_stamp"] is not None

    # 3. Troca de desenho
    res_design = await async_client.post(
        f"/api/v1/projects/{project.id}/protocol/design",
        json={"review_design": "D1"},
    )
    assert res_design.status_code == 200
    data_d = res_design.json()
    assert data_d["protocol"]["review_design"] == "D1"
    assert data_d["suggested_framework"] == "PICO"
    assert data_d["suggested_reporting"] == "PRISMA-2020"

    # 4. Prontidão
    res_readiness = await async_client.get(
        f"/api/v1/projects/{project.id}/protocol/readiness",
    )
    assert res_readiness.status_code == 200
    assert "overall_percentage" in res_readiness.json()
    assert "gates" in res_readiness.json()

    # 5. Congelamento de versão
    res_freeze = await async_client.post(
        f"/api/v1/projects/{project.id}/protocol/freeze",
        json={"label": "v1.0-alpha"},
    )
    assert res_freeze.status_code == 200
    assert res_freeze.json()["label"] == "v1.0-alpha"
    assert len(res_freeze.json()["content_hash"]) == 64

    # 6. Listagem de versões
    res_versions = await async_client.get(
        f"/api/v1/projects/{project.id}/protocol/versions",
    )
    assert res_versions.status_code == 200
    assert len(res_versions.json()) >= 1

    # 7. Exportação do Registro de Busca (Doc 45 D-B: JSON, CSV, DOCX, PDF)
    res_log_json = await async_client.get(
        f"/api/v1/projects/{project.id}/export/search-log?format=json",
    )
    assert res_log_json.status_code == 200
    assert "project_id" in res_log_json.json()

    res_log_csv = await async_client.get(
        f"/api/v1/projects/{project.id}/export/search-log?format=csv",
    )
    assert res_log_csv.status_code == 200
    assert "Base de Dados" in res_log_csv.text

    res_log_docx = await async_client.get(
        f"/api/v1/projects/{project.id}/export/search-log?format=docx",
    )
    assert res_log_docx.status_code == 200
    assert len(res_log_docx.content) > 100

    res_log_pdf = await async_client.get(
        f"/api/v1/projects/{project.id}/export/search-log?format=pdf",
    )
    assert res_log_pdf.status_code == 200
    assert res_log_pdf.content.startswith(b"%PDF")



