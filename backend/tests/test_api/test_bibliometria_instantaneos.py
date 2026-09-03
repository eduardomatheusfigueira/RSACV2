#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Rotas do instantâneo do corpus (doc 48 §13, doc 49 Fase 1)."""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import PaperModel, ProjectModel, ProtocolModel
from tests.conftest import OWNER_ID_TESTE


def _projeto_com_estudos(db_session, titulo, quantos=3) -> str:
    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title=titulo, methodology="PRISMA")
    db_session.add(proj)
    db_session.flush()
    db_session.add(ProtocolModel(project_id=proj.id, objective="Mapear X"))
    for i in range(quantos):
        db_session.add(
            PaperModel(
                project_id=proj.id,
                title=f"{titulo} — estudo {i}",
                authors=f"Autor {i}",
                year=str(2020 + i),
                decision=Decision.INCLUDED.value,
            )
        )
    db_session.commit()
    return proj.id


@pytest.mark.anyio
async def test_cria_e_lista_instantaneo(async_client, db_session):
    pid = _projeto_com_estudos(db_session, "Território")

    res = await async_client.post(
        f"/api/v1/projects/{pid}/bibliometria/instantaneos",
        json={"rotulo": "Análise principal", "escopo": {"decision": "Incluído"}},
    )
    assert res.status_code == 201, res.text
    criado = res.json()
    assert criado["n_documents"] == 3
    assert len(criado["corpus_hash"]) == 64
    assert criado["label"] == "Análise principal"
    assert criado["engine_version"]

    listagem = await async_client.get(f"/api/v1/projects/{pid}/bibliometria/instantaneos")
    assert listagem.status_code == 200
    assert [i["id"] for i in listagem.json()] == [criado["id"]]


@pytest.mark.anyio
async def test_conferencia_acusa_corpus_intocado(async_client, db_session):
    pid = _projeto_com_estudos(db_session, "Intocado")
    criado = (
        await async_client.post(
            f"/api/v1/projects/{pid}/bibliometria/instantaneos", json={}
        )
    ).json()

    res = await async_client.get(
        f"/api/v1/projects/{pid}/bibliometria/instantaneos/{criado['id']}/conferir"
    )

    assert res.status_code == 200
    assert res.json()["estado"] == "identico"
    assert res.json()["confiavel"] is True


@pytest.mark.anyio
async def test_conferencia_nomeia_o_documento_editado(async_client, db_session):
    """A tela precisa dizer o que mudou, não só que mudou."""
    pid = _projeto_com_estudos(db_session, "Editado")
    criado = (
        await async_client.post(
            f"/api/v1/projects/{pid}/bibliometria/instantaneos", json={}
        )
    ).json()

    alvo = db_session.query(PaperModel).filter(PaperModel.project_id == pid).first()
    alvo.title = "Título corrigido depois do congelamento"
    db_session.commit()

    corpo = (
        await async_client.get(
            f"/api/v1/projects/{pid}/bibliometria/instantaneos/{criado['id']}/conferir"
        )
    ).json()

    assert corpo["estado"] == "conteudo_alterado"
    assert corpo["documentos_alterados"] == [alvo.id]
    assert corpo["confiavel"] is False


@pytest.mark.anyio
async def test_instantaneo_de_outro_projeto_nao_e_alcancavel(async_client, db_session):
    """O id na URL não pode atravessar a fronteira do projeto.

    A dependência de titularidade garante que a pessoa tem acesso ao projeto
    da rota; sem o filtro por `project_id` na consulta, ela leria o
    instantâneo de qualquer outro projeto seu passando o id — e, num serviço
    multiusuário, o de terceiros.
    """
    pid_a = _projeto_com_estudos(db_session, "Projeto A")
    pid_b = _projeto_com_estudos(db_session, "Projeto B")
    do_a = (
        await async_client.post(
            f"/api/v1/projects/{pid_a}/bibliometria/instantaneos", json={}
        )
    ).json()

    res = await async_client.get(
        f"/api/v1/projects/{pid_b}/bibliometria/instantaneos/{do_a['id']}/conferir"
    )

    assert res.status_code == 404


@pytest.mark.anyio
async def test_rota_exige_sessao(anon_client, db_session):
    pid = _projeto_com_estudos(db_session, "Sem sessão")

    res = await anon_client.post(
        f"/api/v1/projects/{pid}/bibliometria/instantaneos", json={}
    )

    assert res.status_code in (401, 403)


@pytest.mark.anyio
async def test_projeto_inexistente_devolve_404(async_client):
    res = await async_client.post(
        "/api/v1/projects/nao-existe/bibliometria/instantaneos", json={}
    )
    assert res.status_code == 404


# ── Indicadores calculados sobre o corpus congelado ─────────────────────


@pytest.mark.anyio
async def test_indicadores_sem_instantaneo_descrevem_o_acervo_de_agora(
    async_client, db_session
):
    """Sem instantâneo, a proveniência é nula — e a tela precisa dizer isso."""
    pid = _projeto_com_estudos(db_session, "Sem congelamento")

    corpo = (await async_client.get(f"/api/v1/projects/{pid}/insights")).json()

    assert corpo["provenance"] is None


@pytest.mark.anyio
async def test_indicadores_sobre_instantaneo_ignoram_o_que_chegou_depois(
    async_client, db_session
):
    """É a propriedade que torna o número reproduzível.

    Um estudo coletado depois do congelamento não pode mudar um número já
    publicado — e, antes disso, mudava em silêncio (doc 47 §B-05).
    """
    pid = _projeto_com_estudos(db_session, "Congelado", quantos=3)
    inst = (
        await async_client.post(
            f"/api/v1/projects/{pid}/bibliometria/instantaneos", json={}
        )
    ).json()

    db_session.add(
        PaperModel(
            project_id=pid,
            title="Estudo que chegou depois",
            year="2031",
            journal="Revista Nova",
            decision=Decision.INCLUDED.value,
        )
    )
    db_session.commit()

    agora = (await async_client.get(f"/api/v1/projects/{pid}/insights")).json()
    congelado = (
        await async_client.get(
            f"/api/v1/projects/{pid}/insights", params={"instantaneo": inst["id"]}
        )
    ).json()

    assert sum(i["count"] for i in agora["composition_by_year"]) == 4
    assert sum(i["count"] for i in congelado["composition_by_year"]) == 3
    assert congelado["provenance"]["snapshot_id"] == inst["id"]
    assert congelado["provenance"]["corpus_hash"] == inst["corpus_hash"]
    assert congelado["provenance"]["n_documents"] == 3
