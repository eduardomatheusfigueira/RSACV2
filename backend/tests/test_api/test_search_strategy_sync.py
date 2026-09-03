#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de sincronização e persistência de descritores entre o protocolo simplificado e a coleta."""

import pytest
from app.database import SessionLocal
from app.infrastructure.persistence.models import ProtocolModel, SearchStrategyModel
from app.services.harvesting_service import HarvestingService


@pytest.mark.anyio
async def test_search_strategy_to_descriptors_sync(async_client, db_session):
    """Testa se salvar a estratégia canônica preenche e disponibiliza search_descriptors para o protocolo e a coleta."""
    # 1. Criar projeto
    res = await async_client.post(
        "/api/v1/projects",
        json={"title": "Projeto Sync Estratégia", "methodology": "PRISMA-ScR"},
    )
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Salvar estratégia canônica com blocos A e B
    res_strat = await async_client.put(
        f"/api/v1/projects/{project_id}/protocol/search-strategy",
        json={
            "kind": "canonica",
            "database": "",
            "blocks": [
                {"key": "A", "label": "População", "terms": ["desenvolvimento regional", "arranjos produtivos locais"]},
                {"key": "B", "label": "Conceito", "terms": ["governança territorial", "inovação socioeconômica"]},
            ],
            "combination": "A AND B",
            "target_fields": ["title", "abstract", "keywords"],
            "limits": {},
            "adaptation_note": "Estratégia canônica de teste",
        },
    )
    assert res_strat.status_code == 200

    # 3. Consultar protocolo via GET e verificar se search_descriptors foi preenchido com pares para BDTD/coleta
    res_proto = await async_client.get(f"/api/v1/projects/{project_id}/protocol")
    assert res_proto.status_code == 200
    proto_data = res_proto.json()
    assert "search_descriptors" in proto_data
    pt_desc = proto_data["search_descriptors"].get("pt", [])
    assert len(pt_desc) > 0
    # O primeiro par deve ser a combinação entre termo A e termo B
    assert '"desenvolvimento regional" AND "governança territorial"' in pt_desc[0]

    # 4. Salvar o protocolo com payload simplificada (onde search_descriptors pode vir vazio)
    res_update = await async_client.put(
        f"/api/v1/projects/{project_id}/protocol",
        json={
            "objective": "Objetivo atualizado",
            "search_descriptors": {"pt": [], "en": [], "es": []},
        },
    )
    assert res_update.status_code == 200
    proto_after_update = res_update.json()
    # Não deve ter zerado os descritores, pois preserva a estratégia canônica
    assert len(proto_after_update["search_descriptors"].get("pt", [])) > 0

    # 5. Limpar explicitamente search_descriptors no banco para testar o fallback em SearchStrategyModel
    protocol_db = db_session.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
    assert protocol_db is not None
    protocol_db.search_descriptors = "{}"
    db_session.commit()

    # O protocolo serializado deve continuar derivando de search_strategies
    proto_res_fallback = await async_client.get(f"/api/v1/projects/{project_id}/protocol")
    assert len(proto_res_fallback.json()["search_descriptors"].get("pt", [])) > 0
