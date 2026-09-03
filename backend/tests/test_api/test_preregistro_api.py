#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de rotas da API para Pré-Registro e Exportação (doc 48 §11, doc 49 Fase 9)."""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    PaperModel,
    ProjectModel,
)
from tests.conftest import OWNER_ID_TESTE


@pytest.mark.anyio
async def test_ciclo_preregistro_e_exportacao_api(async_client, db_session):
    pid = "proj-api-prereg-all"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto API Pré-Registro", methodology="PRISMA"))
    db_session.add(PaperModel(id="pp-1", project_id=pid, title="Estudo 1", decision=Decision.INCLUDED.value))
    db_session.commit()

    # 1. Obter plano inicial
    r_get = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/preregistro/plano")
    assert r_get.status_code == 200
    dados_plano = r_get.json()
    assert "indicadores_previstos" in dados_plano

    # 2. Atualizar plano
    r_put = await async_client.put(
        f"/api/v1/projects/{pid}/bibliometria/preregistro/plano",
        json={
            "indicadores_previstos": ["producao_anual", "top_autores", "rajadas"],
            "unidade_analise": "autor",
            "janela_temporal": "2015-2023",
            "justificativa_janela": "Período com dados consolidados.",
            "cortes_declarados": {"freq_minima_termo": 2},
            "tesauro_obrigatorio": True,
        },
    )
    assert r_put.status_code == 200
    dados_atualizados = r_put.json()
    assert dados_atualizados["unidade_analise"] == "autor"
    assert dados_atualizados["janela_temporal"] == "2015-2023"

    # 3. Obter Relatório BIBLIO
    r_bib = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/preregistro/relatorio-biblio")
    assert r_bib.status_code == 200
    dados_bib = r_bib.json()
    assert dados_bib["total_itens"] == 20
    assert len(dados_bib["itens"]) == 20

    # 4. Exportar pacote de replicação em ZIP
    r_zip = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/exportar-pacote")
    assert r_zip.status_code == 200
    assert r_zip.headers["content-type"] == "application/zip"
    assert len(r_zip.content) > 0
