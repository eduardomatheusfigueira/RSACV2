#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes da Fila Pública de Solicitações de Convite.

O formulário da tela de login é a única rota em que alguém sem conta grava
dados pessoais no banco. Os testes aqui cobrem as duas metades disso: que o
pedido chega ao administrador, e que a rota pública não vira fonte de
informação sobre quem já pediu.
"""

import httpx
import pytest
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    InviteCodeModel,
    InviteRequestModel,
    ProcessingRecordModel,
)

PEDIDO = {
    "nome": "Maria Souza",
    "email": "maria@universidade.edu.br",
    "telefone": "(51) 99999-8888",
    "onde_conheceu": "Indicação de orientador",
    "instituicao": "UFRGS",
}


@pytest.mark.anyio
async def test_pedido_publico_grava_solicitacao(
    anon_client: httpx.AsyncClient, db_session: Session
):
    resp = await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    assert resp.status_code == 201
    assert resp.json()["received"] is True

    gravado = db_session.query(InviteRequestModel).one()
    assert gravado.email == "maria@universidade.edu.br"
    assert gravado.status == "pendente"
    assert gravado.instituicao == "UFRGS"


@pytest.mark.anyio
async def test_pedido_publico_registra_no_ropa(
    anon_client: httpx.AsyncClient, db_session: Session
):
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)

    registro = (
        db_session.query(ProcessingRecordModel)
        .filter(ProcessingRecordModel.operation == "invite_requested")
        .one()
    )
    assert registro.legal_basis == "art7_I_consentimento"


@pytest.mark.anyio
async def test_pedido_repetido_nao_duplica_nem_denuncia(
    anon_client: httpx.AsyncClient, db_session: Session
):
    """
    O segundo pedido do mesmo e-mail responde igual ao primeiro.

    É o ponto delicado da rota: distinguir as respostas transformaria o
    formulário aberto em consulta sobre quem procurou o Revsist.
    """
    primeira = await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    segunda = await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)

    assert primeira.status_code == segunda.status_code == 201
    assert primeira.json() == segunda.json()
    assert db_session.query(InviteRequestModel).count() == 1


@pytest.mark.anyio
async def test_pedido_com_email_invalido_e_recusado(anon_client: httpx.AsyncClient):
    resp = await anon_client.post(
        "/api/v1/auth/invite/request", json={**PEDIDO, "email": "sem-arroba"}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_fila_exige_owner(
    researcher_client: httpx.AsyncClient, anon_client: httpx.AsyncClient
):
    assert (await anon_client.get("/api/v1/invites/requests")).status_code == 401
    assert (await researcher_client.get("/api/v1/invites/requests")).status_code == 403


@pytest.mark.anyio
async def test_owner_ve_a_fila_com_pendentes_na_frente(
    anon_client: httpx.AsyncClient, async_client: httpx.AsyncClient, db_session: Session
):
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    await anon_client.post(
        "/api/v1/auth/invite/request", json={**PEDIDO, "email": "joao@ufsm.br"}
    )
    antigo = db_session.query(InviteRequestModel).filter_by(email="joao@ufsm.br").one()
    antigo.status = "recusado"
    db_session.commit()

    resp = await async_client.get("/api/v1/invites/requests")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 2
    assert corpo["pendentes"] == 1
    assert corpo["requests"][0]["status"] == "pendente"


@pytest.mark.anyio
async def test_aprovar_emite_convite_e_vincula_ao_pedido(
    anon_client: httpx.AsyncClient, async_client: httpx.AsyncClient, db_session: Session
):
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    pedido_id = db_session.query(InviteRequestModel).one().id

    resp = await async_client.post(
        f"/api/v1/invites/requests/{pedido_id}/approve", json={"expires_in_days": 7}
    )
    assert resp.status_code == 200
    corpo = resp.json()
    codigo = corpo["invite"]["code"]

    assert corpo["request"]["status"] == "aprovado"
    assert corpo["request"]["invite_code_generated"] == codigo
    assert corpo["request"]["responded_at"] is not None

    convite = db_session.query(InviteCodeModel).filter_by(code=codigo).one()
    assert convite.is_used is False
    assert "Maria Souza" in convite.note

    # O convite emitido pela aprovação serve para o cadastro como qualquer outro.
    validacao = await anon_client.post(
        "/api/v1/auth/invite/validate", json={"invite_code": codigo}
    )
    assert validacao.status_code == 200
    assert validacao.json()["valid"] is True


@pytest.mark.anyio
async def test_aprovar_duas_vezes_nao_emite_segundo_convite(
    anon_client: httpx.AsyncClient, async_client: httpx.AsyncClient, db_session: Session
):
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    pedido_id = db_session.query(InviteRequestModel).one().id

    assert (
        await async_client.post(f"/api/v1/invites/requests/{pedido_id}/approve", json={})
    ).status_code == 200
    repetida = await async_client.post(
        f"/api/v1/invites/requests/{pedido_id}/approve", json={}
    )

    assert repetida.status_code == 409
    assert db_session.query(InviteCodeModel).count() == 1


@pytest.mark.anyio
async def test_recusar_e_anotar_pedido(
    anon_client: httpx.AsyncClient, async_client: httpx.AsyncClient, db_session: Session
):
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    pedido_id = db_session.query(InviteRequestModel).one().id

    resp = await async_client.patch(
        f"/api/v1/invites/requests/{pedido_id}",
        json={"status": "recusado", "admin_notes": "Fora do escopo do programa."},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "recusado"
    assert resp.json()["admin_notes"] == "Fora do escopo do programa."
    assert db_session.query(InviteCodeModel).count() == 0


@pytest.mark.anyio
async def test_status_invalido_e_recusado(
    anon_client: httpx.AsyncClient, async_client: httpx.AsyncClient, db_session: Session
):
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    pedido_id = db_session.query(InviteRequestModel).one().id

    resp = await async_client.patch(
        f"/api/v1/invites/requests/{pedido_id}", json={"status": "talvez"}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_excluir_apaga_os_dados_de_contato(
    anon_client: httpx.AsyncClient, async_client: httpx.AsyncClient, db_session: Session
):
    await anon_client.post("/api/v1/auth/invite/request", json=PEDIDO)
    pedido_id = db_session.query(InviteRequestModel).one().id

    resp = await async_client.delete(f"/api/v1/invites/requests/{pedido_id}")
    assert resp.status_code == 204
    assert db_session.query(InviteRequestModel).count() == 0
