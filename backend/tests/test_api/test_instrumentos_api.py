#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de rotas da API para Instrumentos de Medida e Evidências Textuais (doc 48 §6, §12, doc 49 Fase 5)."""

import json
import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibInstrumentoModel,
    BibTextoModel,
    PaperModel,
    ProjectModel,
)
from tests.conftest import OWNER_ID_TESTE


@pytest.mark.anyio
async def test_sugerir_lexico_api(async_client, db_session):
    pid = "proj-api-sug-1"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Sug", methodology="PRISMA"))
    db_session.commit()

    resp = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/instrumentos/sugerir-lexico",
        json={
            "concept": "arranjos produtivos locais",
            "definition": "Aglomerações territoriais de empresas articuladas com atores locais.",
            "language": "pt",
        },
    )
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["concept"] == "arranjos produtivos locais"
    assert dados["proposed_by"] == "ai"
    assert "lexicon" in dados
    assert dados["lexicon"]["modo"] == "lema"


@pytest.mark.anyio
async def test_instrumentos_api_fluxo_completo(async_client, db_session):
    pid = "proj-api-inst-flow"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Inst Flow", methodology="PRISMA"))
    paper = PaperModel(id="p-flow-1", project_id=pid, title="Paper Flow", decision=Decision.INCLUDED.value)
    db_session.add(paper)
    db_session.add(
        BibTextoModel(
            paper_id=paper.id,
            pipeline_version="2.0.0",
            pdf_sha256="shaflow",
            n_pages=3,
            n_words=450,
            text_clean="A governança regional fortalece as instituições locais.",
            sections=json.dumps([{"name": "Introdução", "canonical_type": "introducao", "start_page": 1, "end_page": 1, "char_offset": 0, "char_length": 60}]),
        )
    )
    db_session.commit()

    # 1. Criar instrumento em rascunho
    resp_create = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/instrumentos",
        json={
            "concept": "governança regional",
            "definition": "Coordenação institucional em territórios.",
            "lexicon": {
                "conceito": "governança regional",
                "definicao": "Coordenação institucional em territórios.",
                "modo": "lema",
                "incluir": [{"forma": "governança regional", "tipo": "expressao"}],
                "excluir": [],
                "janela_de_coocorrencia": 10,
            },
        },
    )
    assert resp_create.status_code == 201
    inst_data = resp_create.json()
    inst_id = inst_data["id"]
    assert inst_data["status"] == "rascunho"

    # 2. Tentar medir em rascunho sem preview -> deve falhar (400)
    resp_fail = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/instrumentos/{inst_id}/medir",
        json={"preview": False},
    )
    assert resp_fail.status_code == 400
    assert "Instrumento em rascunho não produz número exportável" in resp_fail.json()["detail"]

    # 3. Medir em preview -> permitido
    resp_prev = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/instrumentos/{inst_id}/medir",
        json={"preview": True},
    )
    assert resp_prev.status_code == 200
    prev_data = resp_prev.json()
    assert prev_data["is_preview"] is True
    assert prev_data["frequencia_bruta"] == 1

    # 4. Aprovar instrumento
    resp_aprov = await async_client.patch(
        f"/api/v1/projects/{pid}/bibliometria/instrumentos/{inst_id}/aprovar"
    )
    assert resp_aprov.status_code == 200
    assert resp_aprov.json()["status"] == "aprovado"

    # 5. Medição oficial
    resp_medir = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/instrumentos/{inst_id}/medir",
        json={"preview": False},
    )
    assert resp_medir.status_code == 200
    medida_data = resp_medir.json()
    assert medida_data["is_preview"] is False
    assert medida_data["frequencia_bruta"] == 1
    assert medida_data["frequencia_documental"] == 1
    assert medida_data["measurement_id"] is not None

    medida_id = medida_data["measurement_id"]

    # 6. Consultar ocorrências (evidência clicável)
    resp_ocs = await async_client.get(
        f"/api/v1/projects/{pid}/bibliometria/medidas/{medida_id}/ocorrencias"
    )
    assert resp_ocs.status_code == 200
    ocs = resp_ocs.json()
    assert len(ocs) == 1
    assert ocs[0]["matched_form"] == "governança regional"
    assert ocs[0]["section"] == "introducao"
