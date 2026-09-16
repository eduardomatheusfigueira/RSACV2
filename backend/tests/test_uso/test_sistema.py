#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Aba Sistema (doc 52 §6.6; T-15 a T-20).

O que precisa valer: só o dono entra; nada do que se visualiza identifica uma
pessoa; ativar exige o portão inteiro; encerrar não tem volta; e toda ação
deixa rastro.
"""

import json
import re
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import (
    ProcessingRecordModel,
    SistemaAcaoModel,
    SistemaEstadoDaColetaModel,
    UserModel,
    UsoChamadaIAModel,
    UsoErroModel,
    UsoEventoModel,
)
from app.services import retencao
from app.services.uso import portao
from tests.conftest import RESEARCHER_ID_TESTE

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

ROTAS_DE_VISUALIZACAO = [
    "/api/v1/sistema/beta",
    "/api/v1/sistema/resumo?periodo=30",
    "/api/v1/sistema/ia?periodo=beta",
    "/api/v1/sistema/erros?periodo=90",
    "/api/v1/sistema/dados",
    "/api/v1/sistema/acoes",
]


def _povoar(db: Session, pessoas: int) -> None:
    agora = datetime.now(timezone.utc)
    for i in range(pessoas):
        conta = UserModel(id=f"conta-extra-{i}", username=f"extra{i}", email=f"extra{i}@exemplo.br", role="researcher")
        db.add(conta)
        db.add(UsoEventoModel(user_id=conta.id, nome="sessao_uso.fim", propriedades=json.dumps({"tempo_ativo_s": 1200}), ocorrido_em=agora))
        db.add(UsoChamadaIAModel(user_id=conta.id, operacao="triagem", provedor="gemini", modelo_pedido="m", modelo_respondeu="m", resultado="ok", tokens_total=100, ocorrido_em=agora))
        db.add(UsoErroModel(user_id=conta.id, origem="cliente", impressao="a" * 64, tipo="TypeError", mensagem="x", pilha="", ocorrido_em=agora))
    db.commit()


# ── Acesso ────────────────────────────────────────────────────────────


@pytest.mark.anyio
@pytest.mark.parametrize("rota", ROTAS_DE_VISUALIZACAO)
async def test_pesquisador_nao_entra(researcher_client: httpx.AsyncClient, rota):
    """T-15."""
    assert (await researcher_client.get(rota)).status_code == 403


@pytest.mark.anyio
async def test_pesquisador_nao_age(researcher_client: httpx.AsyncClient):
    for rota in ("/api/v1/sistema/coleta/pausar", "/api/v1/sistema/dados/retencao", "/api/v1/sistema/titulares/consulta"):
        assert (await researcher_client.post(rota, json={"email": "a@b.c", "motivo": "x"})).status_code == 403


# ── Visualizar sem identificar ────────────────────────────────────────


@pytest.mark.anyio
@pytest.mark.parametrize("rota", ROTAS_DE_VISUALIZACAO)
async def test_visualizacao_nao_contem_uuid_nem_email(async_client: httpx.AsyncClient, db_session: Session, rota):
    """T-18."""
    _povoar(db_session, 6)
    resp = await async_client.get(rota)
    assert resp.status_code == 200
    assert not UUID.search(resp.text), rota
    assert not EMAIL.search(resp.text), rota


@pytest.mark.anyio
async def test_grupos_pequenos_sao_suprimidos(async_client: httpx.AsyncClient, db_session: Session):
    """T-18: três pessoas não aparecem como número."""
    _povoar(db_session, 3)

    resumo = (await async_client.get("/api/v1/sistema/resumo?periodo=30")).json()
    assert resumo["participantes_ativos"] == {"valor": None, "pessoas": None, "suprimido": True}
    assert resumo["tokens"]["suprimido"] is True
    assert resumo["tempo_ativo_mediano_min"]["valor"] is None

    ia = (await async_client.get("/api/v1/sistema/ia?periodo=30")).json()
    assert ia["suprimido"] is True
    assert all(g["tokens"] is None for g in ia["por_operacao"])

    erros = (await async_client.get("/api/v1/sistema/erros?periodo=30")).json()["itens"]
    assert erros[0]["pessoas"] is None and erros[0]["pessoas_suprimido"] is True


@pytest.mark.anyio
async def test_grupos_de_cinco_ou_mais_aparecem(async_client: httpx.AsyncClient, db_session: Session):
    _povoar(db_session, 5)
    resumo = (await async_client.get("/api/v1/sistema/resumo?periodo=30")).json()
    assert resumo["participantes_ativos"]["valor"] == 5
    assert resumo["tokens"]["valor"] == 500
    assert resumo["tempo_ativo_mediano_min"]["valor"] == 20.0


@pytest.mark.anyio
async def test_ciclo_do_beta_de_um_ano(async_client: httpx.AsyncClient):
    beta = (await async_client.get("/api/v1/sistema/beta")).json()
    assert beta["inicio"] == "2026-09-12"
    assert beta["fim"] == "2027-09-12"
    assert beta["duracao_dias"] == 365
    assert beta["aviso_de_decisao_em"] == "2027-07-14"
    assert beta["descarte_final_em"] == "2027-10-12"
    assert beta["estado"]["estado"] == "aguardando"
    assert beta["pode_ativar"] is False
    chaves = {i["chave"]: i for i in beta["portao"]}
    assert chaves["perfil"]["ok"] is False
    # Publicado o Aviso 2.1, este item passou a estar atendido — e é o teste de
    # `test_aviso_publicado.py` que garante que o texto e a versão não divirjam.
    assert chaves["termos"]["ok"] is True
    assert chaves["reaceite"]["bloqueante"] is False


# ── Gerenciar a coleta ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_ativar_com_portao_fechado_e_recusado(async_client: httpx.AsyncClient, db_session: Session):
    """T-16."""
    resp = await async_client.post("/api/v1/sistema/coleta/ativar", json={})
    assert resp.status_code == 409
    assert "Servidor publicado (perfil server)" in resp.json()["detail"]
    assert portao.obter_estado(db_session).estado == "aguardando"


def _abrir_portao(monkeypatch, db_session: Session) -> None:
    monkeypatch.setattr(portao, "perfil_permite_coleta", lambda: True)
    monkeypatch.setattr(settings, "uso_coleta_ativa", True)
    monkeypatch.setattr(settings, "uso_versao_dos_termos", settings.terms_version)
    retencao.aplicar_retencao(db_session)


@pytest.mark.anyio
async def test_ativar_pausar_e_encerrar(async_client: httpx.AsyncClient, db_session: Session, monkeypatch):
    """T-16, T-17 e T-20."""
    _abrir_portao(monkeypatch, db_session)

    assert (await async_client.post("/api/v1/sistema/coleta/ativar", json={})).json()["estado"] == "ativa"

    sem_motivo = await async_client.post("/api/v1/sistema/coleta/pausar", json={})
    assert sem_motivo.status_code == 409
    assert (await async_client.post("/api/v1/sistema/coleta/pausar", json={"motivo": "Incidente"})).json()["estado"] == "pausada"

    sem_confirmacao = await async_client.post("/api/v1/sistema/coleta/encerrar", json={"motivo": "Fim"})
    assert sem_confirmacao.status_code == 400
    encerrado = await async_client.post("/api/v1/sistema/coleta/encerrar", json={"motivo": "Fim", "confirmacao": "ENCERRAR"})
    assert encerrado.json()["estado"] == "encerrada"

    # T-17: nenhuma rota leva de volta a `ativa`.
    reabrir = await async_client.post("/api/v1/sistema/coleta/ativar", json={})
    assert reabrir.status_code == 409
    assert "não pode ser reaberto" in reabrir.json()["detail"]
    assert (await async_client.post("/api/v1/sistema/coleta/pausar", json={"motivo": "x"})).status_code == 409

    acoes = [a.acao for a in db_session.query(SistemaAcaoModel).order_by(SistemaAcaoModel.executada_em).all()]
    assert acoes == ["coleta_ativar", "coleta_pausar", "coleta_encerrar"]
    assert db_session.query(ProcessingRecordModel).filter_by(operation="usage_collection_changed").count() == 3


@pytest.mark.anyio
async def test_aplicar_retencao_agora(async_client: httpx.AsyncClient, db_session: Session):
    antigo = datetime.now(timezone.utc) - timedelta(days=200)
    db_session.add(UsoEventoModel(user_id=RESEARCHER_ID_TESTE, nome="acao", ocorrido_em=antigo, recebido_em=antigo))
    db_session.commit()

    resp = await async_client.post("/api/v1/sistema/dados/retencao")
    assert resp.status_code == 200
    assert resp.json()["eliminados"]["eventos_de_uso"] == 1
    assert db_session.query(SistemaAcaoModel).filter_by(acao="retencao_aplicar").count() == 1


# ── Pedidos de titular ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_pedido_de_titular_por_email(async_client: httpx.AsyncClient, db_session: Session):
    pesquisador = db_session.get(UserModel, RESEARCHER_ID_TESTE)
    pesquisador.email = "pesquisadora@uni.br"
    agora = datetime.now(timezone.utc)
    db_session.add(UsoEventoModel(user_id=RESEARCHER_ID_TESTE, nome="acao", ocorrido_em=agora))
    db_session.add(UsoChamadaIAModel(user_id=RESEARCHER_ID_TESTE, operacao="triagem", provedor="g", resultado="ok", ocorrido_em=agora))
    db_session.commit()

    consulta = await async_client.post("/api/v1/sistema/titulares/consulta", json={"email": "Pesquisadora@UNI.br"})
    assert consulta.json()["contagens"] == {"eventos": 1, "erros": 0, "chamadas_ia": 1}

    exportado = (await async_client.post("/api/v1/sistema/titulares/exportacao", json={"email": "pesquisadora@uni.br"})).json()
    assert len(exportado["eventos_de_uso"]) == 1
    assert RESEARCHER_ID_TESTE not in json.dumps(exportado)

    sem_confirmacao = await async_client.post("/api/v1/sistema/titulares/eliminacao", json={"email": "pesquisadora@uni.br"})
    assert sem_confirmacao.status_code == 400
    apagado = await async_client.post(
        "/api/v1/sistema/titulares/eliminacao", json={"email": "pesquisadora@uni.br", "confirmacao": "APAGAR"}
    )
    assert apagado.json()["apagados"] == {"eventos": 1, "erros": 0, "chamadas_ia": 1}
    assert db_session.query(UsoEventoModel).count() == 0

    # T-20: o e-mail do pedido não fica no diário.
    for acao in db_session.query(SistemaAcaoModel).all():
        assert "pesquisadora" not in acao.parametros.lower()
    assert db_session.query(ProcessingRecordModel).filter_by(operation="usage_data_erased").count() == 1

    inexistente = await async_client.post("/api/v1/sistema/titulares/consulta", json={"email": "ninguem@x.br"})
    assert inexistente.status_code == 404


@pytest.mark.anyio
async def test_acompanhar_defeito_e_reabertura_por_versao_nova(async_client: httpx.AsyncClient, db_session: Session):
    agora = datetime.now(timezone.utc)
    impressao = "b" * 64
    db_session.add(UsoErroModel(origem="servidor", impressao=impressao, tipo="KeyError", mensagem="", pilha="", versao_app="2.0.0", ocorrido_em=agora))
    db_session.commit()

    resp = await async_client.patch(f"/api/v1/sistema/erros/{impressao}", json={"situacao": "resolvido", "versao": "2.0.0"})
    assert resp.json()["situacao"] == "resolvido"
    assert (await async_client.get("/api/v1/sistema/erros?periodo=30")).json()["itens"][0]["situacao"] == "resolvido"

    db_session.add(UsoErroModel(origem="servidor", impressao=impressao, tipo="KeyError", mensagem="", pilha="", versao_app="2.0.1", ocorrido_em=agora + timedelta(seconds=1)))
    db_session.commit()
    assert (await async_client.get("/api/v1/sistema/erros?periodo=30")).json()["itens"][0]["situacao"] == "novo"

    assert (await async_client.patch("/api/v1/sistema/erros/naoehex", json={"situacao": "novo"})).status_code == 422
    assert (await async_client.patch(f"/api/v1/sistema/erros/{impressao}", json={"situacao": "sumido"})).status_code == 422
