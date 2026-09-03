#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A rota de indicadores responde — inclusive sobre corpus degenerado.

Escrito depois de a rota devolver **500** em produção sobre um recorte real de
15 estudos. A causa foi um desencontro entre serviço e schema: o serviço passou
a devolver `is_adherent = None` para amostras que não decidem, e o schema ainda
declarava `bool`. O navegador reportou erro de CORS, porque a resposta de erro
não carrega os cabeçalhos — o que escondeu a causa real.

Os testes de unidade das leis passavam; faltava alguém exercitar a rota
inteira, que é onde o schema entra.
"""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import PaperModel, ProjectModel, ProtocolModel
from tests.conftest import OWNER_ID_TESTE


def _projeto(db_session, titulo="Projeto de indicadores") -> str:
    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title=titulo, methodology="PRISMA")
    db_session.add(proj)
    db_session.flush()
    db_session.add(ProtocolModel(project_id=proj.id, objective="Mapear X"))
    db_session.commit()
    return proj.id


@pytest.mark.anyio
async def test_corpus_degenerado_responde_200(async_client, db_session):
    """Um periódico e poucos autores: o caso que derrubava a rota."""
    pid = _projeto(db_session, "Corpus degenerado")
    db_session.add_all(
        [
            PaperModel(
                project_id=pid,
                title=f"Estudo {i}",
                authors=f"Autor {i}",
                year="2020",
                journal="Sociedade e Estado" if i == 0 else "",
                decision=Decision.INCLUDED.value,
            )
            for i in range(15)
        ]
    )
    db_session.commit()

    res = await async_client.get(
        f"/api/v1/projects/{pid}/bibliometria/indicadores", params={"decision": "Incluído"}
    )

    assert res.status_code == 200, res.text
    corpo = res.json()
    assert corpo["lotka"]["is_adherent"] is None, "Emitiu veredicto sem amostra."
    assert corpo["lotka"]["sample_ok"] is False
    assert corpo["bradford"]["confiavel"] is False
    assert corpo["bradford"]["zones"] == []


@pytest.mark.anyio
async def test_corpus_vazio_responde_200(async_client, db_session):
    """Projeto sem nenhum estudo não é erro — é um projeto novo."""
    pid = _projeto(db_session, "Corpus vazio")

    res = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/indicadores")

    assert res.status_code == 200, res.text
    assert res.json()["total_papers"] == 0


@pytest.mark.anyio
async def test_corpus_com_amostra_suficiente_recebe_veredicto(async_client, db_session):
    """Com autores bastantes, o teste de aderência volta a decidir."""
    pid = _projeto(db_session, "Corpus com massa")
    db_session.add_all(
        [
            PaperModel(
                project_id=pid,
                title=f"Estudo {i}",
                authors=f"Autor {i}",
                year=str(2015 + (i % 8)),
                journal=f"Revista {i % 12}",
                decision=Decision.INCLUDED.value,
            )
            for i in range(70)
        ]
    )
    db_session.commit()

    corpo = (
        await async_client.get(
            f"/api/v1/projects/{pid}/bibliometria/indicadores", params={"decision": "Incluído"}
        )
    ).json()

    assert corpo["lotka"]["sample_ok"] is True
    assert corpo["lotka"]["is_adherent"] in (True, False)
    assert len(corpo["bradford"]["zones"]) == 3


@pytest.mark.anyio
async def test_sem_enriquecimento_as_citacoes_declaram_o_denominador(async_client, db_session):
    """Zero citações e corpus não enriquecido precisam ser distinguíveis.

    `papers_with_citation_data` é o que permite à tela dizer "ainda não
    enriquecido" em vez de afirmar "índice h: 0".
    """
    pid = _projeto(db_session, "Sem enriquecimento")
    db_session.add(
        PaperModel(
            project_id=pid, title="Estudo", authors="A", decision=Decision.INCLUDED.value
        )
    )
    db_session.commit()

    corpo = (
        await async_client.get(
            f"/api/v1/projects/{pid}/bibliometria/indicadores", params={"decision": "Incluído"}
        )
    ).json()

    assert corpo["citations"]["papers_with_citation_data"] == 0
    assert corpo["open_access"]["by_status"] == []
