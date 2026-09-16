#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Ingestão de eventos e erros, e o portão que a guarda (doc 52 §6.4).

Cada teste de bloqueio parte da coleta aberta e fecha **uma** trava. Se uma
trava sozinha não bastasse para impedir a gravação, ela não seria trava.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import (
    SistemaEstadoDaColetaModel,
    UserModel,
    UsoErroModel,
    UsoEventoModel,
)
from app.services.uso import portao
from tests.conftest import OWNER_ID_TESTE, RESEARCHER_ID_TESTE


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lote(*eventos) -> dict:
    return {
        "sessao_uso_id": "sessao-teste",
        "eventos": list(eventos)
        or [{"nome": "acao", "tela": "projeto.triagem", "propriedades": {"alvo": "triagem.lote.iniciar"}, "ocorrido_em": _agora_iso()}],
    }


@pytest.mark.anyio
async def test_coleta_aberta_grava(researcher_client: httpx.AsyncClient, db_session: Session, coleta_aberta):
    resp = await researcher_client.post("/api/v1/uso/eventos", json=_lote())
    assert resp.status_code == 204
    assert resp.headers["X-Uso-Coleta"] == "ativa"

    gravado = db_session.query(UsoEventoModel).one()
    assert gravado.user_id == RESEARCHER_ID_TESTE
    assert gravado.nome == "acao"
    assert gravado.tela == "projeto.triagem"


@pytest.mark.anyio
async def test_padrao_e_coleta_fechada(researcher_client: httpx.AsyncClient, db_session: Session):
    """Sem nenhuma configuração, nada é gravado — e a resposta não é erro."""
    resp = await researcher_client.post("/api/v1/uso/eventos", json=_lote())
    assert resp.status_code == 204
    assert resp.headers["X-Uso-Coleta"] == "desligada"
    assert db_session.query(UsoEventoModel).count() == 0


@pytest.mark.anyio
@pytest.mark.parametrize("trava", ["perfil", "implantacao", "termos_publicados", "termos_aceitos", "oposicao", "gpc"])
async def test_cada_trava_sozinha_bloqueia(
    trava, researcher_client: httpx.AsyncClient, db_session: Session, coleta_aberta, monkeypatch
):
    """T-04, T-05, T-07: perfil de mesa, implantação, termos, aceite, oposição e GPC."""
    headers = {}
    if trava == "perfil":
        monkeypatch.setattr(portao, "perfil_permite_coleta", lambda: False)
    elif trava == "implantacao":
        monkeypatch.setattr(settings, "uso_coleta_ativa", False)
    elif trava == "termos_publicados":
        monkeypatch.setattr(settings, "uso_versao_dos_termos", "")
    elif trava == "termos_aceitos":
        db_session.get(UserModel, RESEARCHER_ID_TESTE).terms_version = "2026-01"
        db_session.commit()
    elif trava == "oposicao":
        db_session.get(UserModel, RESEARCHER_ID_TESTE).uso_coleta_ativa = False
        db_session.commit()
    elif trava == "gpc":
        headers["Sec-GPC"] = "1"

    resp = await researcher_client.post("/api/v1/uso/eventos", json=_lote(), headers=headers)
    assert resp.status_code == 204
    assert db_session.query(UsoEventoModel).count() == 0


@pytest.mark.anyio
@pytest.mark.parametrize("estado", ["aguardando", "pausada", "encerrada"])
async def test_estado_diferente_de_ativa_bloqueia(
    estado, researcher_client: httpx.AsyncClient, db_session: Session, coleta_aberta
):
    """T-16."""
    db_session.get(SistemaEstadoDaColetaModel, "unico").estado = estado
    db_session.commit()
    portao.invalidar_cache()

    await researcher_client.post("/api/v1/uso/eventos", json=_lote())
    assert db_session.query(UsoEventoModel).count() == 0


def test_fim_do_beta_encerra_sozinho(db_session: Session, coleta_aberta):
    """T-06: 11/09/2027 23:59 em Brasília ainda grava; 12/09/2027 00:00 já não."""
    assert settings.beta_fim.isoformat() == "2027-09-12"
    brasilia = timezone(timedelta(hours=-3))
    pesquisador = db_session.get(UserModel, RESEARCHER_ID_TESTE)

    vespera = datetime(2027, 9, 11, 23, 59, tzinfo=brasilia)
    assert portao.motivo_de_bloqueio(db_session, pesquisador, "B", agora=vespera) is None

    fim = datetime(2027, 9, 12, 0, 0, tzinfo=brasilia)
    assert portao.motivo_de_bloqueio(db_session, pesquisador, "B", agora=fim) == "estado_encerrada"
    assert db_session.get(SistemaEstadoDaColetaModel, "unico").estado == "encerrada"


@pytest.mark.anyio
async def test_user_id_so_vem_da_sessao(researcher_client: httpx.AsyncClient, db_session: Session, coleta_aberta):
    """T-08: um campo `user_id` no corpo não muda de quem é o evento."""
    corpo = _lote()
    corpo["user_id"] = OWNER_ID_TESTE
    corpo["eventos"][0]["user_id"] = OWNER_ID_TESTE

    await researcher_client.post("/api/v1/uso/eventos", json=corpo)
    assert db_session.query(UsoEventoModel).one().user_id == RESEARCHER_ID_TESTE


@pytest.mark.anyio
async def test_lote_misto_grava_so_o_que_cabe(researcher_client: httpx.AsyncClient, db_session: Session, coleta_aberta):
    agora = _agora_iso()
    await researcher_client.post(
        "/api/v1/uso/eventos",
        json=_lote(
            {"nome": "tela.vista", "tela": "projeto.coleta", "propriedades": {"anterior": "inicio"}, "ocorrido_em": agora},
            {"nome": "acao", "propriedades": {"alvo": "Impactos da segurança pública no turismo náutico"}, "ocorrido_em": agora},
            {"nome": "evento_inventado", "ocorrido_em": agora},
        ),
    )
    gravados = db_session.query(UsoEventoModel).all()
    assert [g.nome for g in gravados] == ["tela.vista"]
    assert "turismo" not in gravados[0].propriedades


@pytest.mark.anyio
async def test_relogio_do_navegador_implausivel_e_ignorado(
    researcher_client: httpx.AsyncClient, db_session: Session, coleta_aberta
):
    antigo = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    await researcher_client.post(
        "/api/v1/uso/eventos",
        json=_lote({"nome": "acao", "propriedades": {"alvo": "projeto.criar"}, "ocorrido_em": antigo}),
    )
    gravado = db_session.query(UsoEventoModel).one()
    assert gravado.ocorrido_em.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc) - timedelta(minutes=1)


@pytest.mark.anyio
async def test_lote_grande_demais_e_recusado(researcher_client: httpx.AsyncClient, coleta_aberta):
    eventos = [
        {"nome": "acao", "propriedades": {"alvo": "projeto.criar"}, "ocorrido_em": _agora_iso()} for _ in range(51)
    ]
    resp = await researcher_client.post("/api/v1/uso/eventos", json={"eventos": eventos})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_sem_sessao_nao_entra(anon_client: httpx.AsyncClient):
    resp = await anon_client.post("/api/v1/uso/eventos", json=_lote())
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_erro_do_navegador_e_gravado_sanitizado(
    researcher_client: httpx.AsyncClient, db_session: Session, coleta_aberta
):
    resp = await researcher_client.post(
        "/api/v1/uso/erros",
        json={
            "ocorrencias": [
                {
                    "tipo": "TypeError",
                    "mensagem": "Cannot read 'Turismo náutico em fronteiras' of maria@uni.br com AIzaSyA1234567890abcdefghijklmnop",
                    "pilha": "TypeError: x\n    at triar (https://revsist.com/assets/index-abc.js:120:15)",
                    "tela": "projeto.triagem",
                    "status_http": None,
                    "ocorrido_em": _agora_iso(),
                }
            ]
        },
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/131.0 Safari/537.36"},
    )
    assert resp.status_code == 204

    erro = db_session.query(UsoErroModel).one()
    assert erro.origem == "cliente"
    assert erro.user_id == RESEARCHER_ID_TESTE
    assert "Turismo" not in erro.mensagem
    assert "maria@uni.br" not in erro.mensagem
    assert "AIzaSy" not in erro.mensagem
    assert erro.pilha == "assets/index-abc.js:120:triar"
    assert erro.navegador == "chrome 131"
    assert erro.tela == "projeto.triagem"
