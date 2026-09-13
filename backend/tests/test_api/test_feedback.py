#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes do feedback do beta.

O que precisa valer: qualquer conta envia, só o owner lê a fila, o dono recebe
o aviso por e-mail (e uma falha nesse aviso não derruba o envio), e o feedback
some junto com a conta de quem escreveu.
"""

import httpx
import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import FeedbackModel, ProcessingRecordModel
from app.services import email_service, feedback_admin
from tests.conftest import RESEARCHER_ID_TESTE

FEEDBACK = {
    "tipo": "problema",
    "mensagem": "A triagem travou quando cliquei em incluir duas vezes seguidas.",
    "pagina": "/projects/abc/screening",
}


@pytest.fixture
def envios(monkeypatch):
    """Captura o aviso ao dono em vez de falar com um servidor SMTP."""
    capturados: list[dict] = []

    def falso_enviar(**kwargs):
        capturados.append(kwargs)
        return email_service.ResultadoDeEnvio(enviado=True, detalhe="ok", destinatario=kwargs["destinatario"])

    monkeypatch.setattr(settings, "convites_email_admin", "dono@exemplo.br")
    monkeypatch.setattr(feedback_admin.email_service, "enviar", falso_enviar)
    return capturados


@pytest.mark.anyio
async def test_pesquisador_envia_e_dono_recebe_aviso(
    researcher_client: httpx.AsyncClient, db_session: Session, envios
):
    resp = await researcher_client.post(
        "/api/v1/feedback", json=FEEDBACK, headers={"User-Agent": "NavegadorDeTeste/1.0"}
    )
    assert resp.status_code == 201
    assert resp.json()["received"] is True

    gravado = db_session.query(FeedbackModel).one()
    assert gravado.user_id == RESEARCHER_ID_TESTE
    assert gravado.tipo == "problema"
    assert gravado.status == "novo"
    assert gravado.pagina == "/projects/abc/screening"
    assert gravado.navegador == "NavegadorDeTeste/1.0"
    assert gravado.versao == settings.app_version

    assert len(envios) == 1
    assert envios[0]["destinatario"] == "dono@exemplo.br"
    assert "Problema relatado" in envios[0]["assunto"]
    assert "A triagem travou" in envios[0]["texto"]


@pytest.mark.anyio
async def test_envio_registra_no_ropa_sem_o_conteudo(
    researcher_client: httpx.AsyncClient, db_session: Session, envios
):
    await researcher_client.post("/api/v1/feedback", json=FEEDBACK)

    registro = (
        db_session.query(ProcessingRecordModel)
        .filter(ProcessingRecordModel.operation == "feedback_received")
        .one()
    )
    assert registro.legal_basis == "art7_I_consentimento"
    assert registro.user_id == RESEARCHER_ID_TESTE
    assert "triagem travou" not in (registro.purpose or "")


@pytest.mark.anyio
async def test_falha_no_email_nao_derruba_o_envio(
    researcher_client: httpx.AsyncClient, db_session: Session, monkeypatch
):
    def explode(**_kwargs):
        raise RuntimeError("SMTP fora do ar")

    monkeypatch.setattr(settings, "convites_email_admin", "dono@exemplo.br")
    monkeypatch.setattr(feedback_admin.email_service, "enviar", explode)

    resp = await researcher_client.post("/api/v1/feedback", json=FEEDBACK)
    assert resp.status_code == 201
    assert db_session.query(FeedbackModel).count() == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    "corpo",
    [
        {**FEEDBACK, "tipo": "reclamacao"},
        {**FEEDBACK, "mensagem": "oi"},
        {**FEEDBACK, "mensagem": "x" * 5001},
    ],
)
async def test_envio_invalido_e_recusado(researcher_client: httpx.AsyncClient, corpo, envios):
    resp = await researcher_client.post("/api/v1/feedback", json=corpo)
    assert resp.status_code == 422
    assert envios == []


@pytest.mark.anyio
async def test_limite_por_hora(researcher_client: httpx.AsyncClient, envios, monkeypatch):
    from app.api.v1 import feedback as rota

    monkeypatch.setattr(rota, "LIMITE_POR_HORA", 2)
    for _ in range(2):
        assert (await researcher_client.post("/api/v1/feedback", json=FEEDBACK)).status_code == 201
    resp = await researcher_client.post("/api/v1/feedback", json=FEEDBACK)
    assert resp.status_code == 429


@pytest.mark.anyio
async def test_pesquisador_nao_le_a_fila(researcher_client: httpx.AsyncClient):
    assert (await researcher_client.get("/api/v1/feedback")).status_code == 403


@pytest.mark.anyio
async def test_dono_le_atualiza_e_exclui(
    async_client: httpx.AsyncClient,
    researcher_client: httpx.AsyncClient,
    db_session: Session,
    envios,
):
    await researcher_client.post("/api/v1/feedback", json=FEEDBACK)
    await researcher_client.post(
        "/api/v1/feedback", json={**FEEDBACK, "tipo": "sugestao", "mensagem": "Exportar em CSV também."}
    )

    lista = (await async_client.get("/api/v1/feedback")).json()
    assert lista["total"] == 2
    assert lista["novos"] == 2
    item = lista["items"][0]
    assert item["autor_usuario"] == "pesquisador_teste"

    alvo = next(i for i in lista["items"] if i["tipo"] == "problema")
    resp = await async_client.patch(
        f"/api/v1/feedback/{alvo['id']}",
        json={"status": "resolvido", "admin_notes": "Corrigido na 2.0.1"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolvido"
    assert resp.json()["responded_at"] is not None

    lista = (await async_client.get("/api/v1/feedback")).json()
    assert lista["novos"] == 1
    # Novos primeiro: o resolvido desce para o fim da fila.
    assert lista["items"][-1]["id"] == alvo["id"]

    assert (await async_client.patch(f"/api/v1/feedback/{alvo['id']}", json={"status": "sumido"})).status_code == 422
    assert (await async_client.delete(f"/api/v1/feedback/{alvo['id']}")).status_code == 204
    assert db_session.query(FeedbackModel).count() == 1


@pytest.mark.anyio
async def test_eliminacao_da_conta_apaga_o_feedback(
    researcher_client: httpx.AsyncClient, db_session: Session, envios
):
    from app.api.v1.me import executar_eliminacao_completa_usuario

    await researcher_client.post("/api/v1/feedback", json=FEEDBACK)
    assert db_session.query(FeedbackModel).count() == 1

    executar_eliminacao_completa_usuario(db_session, RESEARCHER_ID_TESTE)
    assert db_session.query(FeedbackModel).count() == 0


def test_email_escapa_a_mensagem():
    from datetime import datetime, timezone

    dados = feedback_admin.DadosDoFeedback(
        id="f1",
        tipo="sugestao",
        mensagem="<script>alert(1)</script>",
        pagina="/",
        navegador="",
        versao="2.0.0",
        autor_nome="Maria",
        autor_usuario="maria",
        autor_email="maria@exemplo.br",
        recebido_em=datetime.now(timezone.utc),
    )
    _assunto, _texto, corpo = feedback_admin.montar_email(dados)
    assert "<script>" not in corpo
    assert "&lt;script&gt;" in corpo
