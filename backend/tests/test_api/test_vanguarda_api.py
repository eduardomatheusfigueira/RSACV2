#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de rotas da API para Indicadores de Vanguarda (doc 48 §7.4, §10, doc 49 Fase 8)."""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibKeywordModel,
    PaperModel,
    ProjectModel,
)
from tests.conftest import OWNER_ID_TESTE


@pytest.mark.anyio
async def test_rotas_vanguarda_api(async_client, db_session):
    pid = "proj-api-vang-all"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Vanguarda API", methodology="PRISMA"))

    for i in range(1, 6):
        p = PaperModel(
            id=f"pv-{i}",
            project_id=pid,
            title=f"Estudo Vanguarda {i}",
            journal="Revista de Desenvolvimento Regional",
            year="2023",
            decision=Decision.INCLUDED.value,
        )
        db_session.add(p)
        db_session.add(BibKeywordModel(paper_id=p.id, term="políticas públicas"))
        db_session.add(BibKeywordModel(paper_id=p.id, term="território"))

    db_session.commit()

    # 1. Diagrama Estratégico
    r_diag = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/vanguarda/diagrama-estrategico")
    assert r_diag.status_code == 200
    assert "items" in r_diag.json()

    # 2. Rajadas
    r_raj = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/vanguarda/rajadas")
    assert r_raj.status_code == 200
    assert "rajadas" in r_raj.json()

    # 3. Bootstrap Rankings
    r_boot = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/vanguarda/bootstrap-rankings?tipo_ranking=periodicos")
    assert r_boot.status_code == 200
    assert "items" in r_boot.json()
    assert len(r_boot.json()["items"]) >= 1

    # 4. Sensibilidade
    r_sens = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/vanguarda/sensibilidade")
    assert r_sens.status_code == 200
    assert "varredura" in r_sens.json()

    # 5. Cobertura do Campo
    r_cob = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/vanguarda/cobertura-campo")
    assert r_cob.status_code == 200
    assert "topicos_robustos" in r_cob.json()
