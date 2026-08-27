#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Estado da coleta por fonte (`GET /harvest/status`).

A interface consulta este endpoint em laço para saber quando parar de mostrar
"coletando" e quanto cada base trouxe. Enquanto a resposta não trazia
`is_complete` nem `progress`, o painel zerava a cada consulta e uma fonte que
falhou por completo não produzia sinal nenhum na tela — que é exatamente o
sintoma de "a coleta começa zerada e não recupera nada".
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.infrastructure.persistence.models import HarvestRunModel


@pytest.mark.anyio
async def test_status_sem_execucoes(async_client):
    res = await async_client.post(
        "/api/v1/projects", json={"title": "Projeto Vazio", "methodology": "PRISMA-P"}
    )
    project_id = res.json()["id"]

    status = await async_client.get(f"/api/v1/projects/{project_id}/harvest/status")
    assert status.status_code == 200
    corpo = status.json()
    assert corpo["status"] == "idle"
    assert corpo["is_complete"] is True
    assert corpo["progress"] == {}


@pytest.mark.anyio
async def test_status_reporta_progresso_e_falha_por_fonte(async_client, db_session):
    res = await async_client.post(
        "/api/v1/projects", json={"title": "Projeto Coleta", "methodology": "PRISMA-P"}
    )
    project_id = res.json()["id"]

    agora = datetime.now(timezone.utc)
    db_session.add_all(
        [
            HarvestRunModel(
                project_id=project_id,
                source_name="SciELO",
                started_at=agora - timedelta(seconds=30),
                completed_at=agora,
                records_found=0,
                records_new=0,
                records_duplicate=0,
                status="failed",
                error_message="[SciELO] nenhuma página de resultados pôde ser lida",
            ),
            HarvestRunModel(
                project_id=project_id,
                source_name="BDTD",
                started_at=agora - timedelta(seconds=29),
                completed_at=agora,
                records_found=94,
                records_new=87,
                records_duplicate=7,
                status="completed",
            ),
        ]
    )
    db_session.commit()

    corpo = (await async_client.get(f"/api/v1/projects/{project_id}/harvest/status")).json()

    assert corpo["is_complete"] is True
    assert corpo["status"] == "failed"
    assert corpo["total_found"] == 94
    assert corpo["total_new"] == 87
    assert corpo["total_duplicate"] == 7
    assert corpo["progress"]["BDTD"]["status"] == "completed"
    assert corpo["progress"]["SciELO"]["status"] == "failed"
    # A causa precisa chegar à tela: é o que distingue "base vazia" de "base fora do ar".
    assert "nenhuma página" in corpo["failures"][0]


@pytest.mark.anyio
async def test_status_expoe_aviso_de_coleta_parcial(async_client, db_session):
    res = await async_client.post(
        "/api/v1/projects", json={"title": "Projeto Parcial", "methodology": "PRISMA-P"}
    )
    project_id = res.json()["id"]

    agora = datetime.now(timezone.utc)
    db_session.add(
        HarvestRunModel(
            project_id=project_id,
            source_name="SciELO",
            started_at=agora,
            completed_at=agora,
            records_found=12,
            records_new=12,
            records_duplicate=0,
            status="completed",
            error_message="2 de 10 descritores ficaram incompletos",
        )
    )
    db_session.commit()

    corpo = (await async_client.get(f"/api/v1/projects/{project_id}/harvest/status")).json()

    assert corpo["status"] == "completed"
    assert corpo["warnings"] == ["SciELO: 2 de 10 descritores ficaram incompletos"]
