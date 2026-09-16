#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Direitos do titular e retenção dos dados de uso (doc 52 §7.5, §7.6; T-09).
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import (
    ProcessingRecordModel,
    UserModel,
    UsoChamadaIAModel,
    UsoErroModel,
    UsoEventoModel,
)
from app.services import retencao
from tests.conftest import RESEARCHER_ID_TESTE


def _registros_da_pesquisadora(db: Session, quando: datetime | None = None) -> None:
    quando = quando or datetime.now(timezone.utc)
    db.add(UsoEventoModel(user_id=RESEARCHER_ID_TESTE, nome="acao", ocorrido_em=quando, recebido_em=quando))
    db.add(UsoErroModel(user_id=RESEARCHER_ID_TESTE, origem="cliente", impressao="c" * 64, tipo="E", mensagem="", pilha="", ocorrido_em=quando, recebido_em=quando))
    db.add(UsoChamadaIAModel(user_id=RESEARCHER_ID_TESTE, operacao="triagem", provedor="g", resultado="ok", ocorrido_em=quando))
    db.commit()


def test_eliminacao_da_conta_apaga_os_dados_de_uso(db_session: Session, contas):
    """T-09."""
    from app.api.v1.me import executar_eliminacao_completa_usuario

    _registros_da_pesquisadora(db_session)
    executar_eliminacao_completa_usuario(db_session, RESEARCHER_ID_TESTE)

    assert db_session.query(UsoEventoModel).count() == 0
    assert db_session.query(UsoErroModel).count() == 0
    assert db_session.query(UsoChamadaIAModel).count() == 0


@pytest.mark.anyio
async def test_interruptor_do_titular(researcher_client: httpx.AsyncClient, db_session: Session):
    situacao = (await researcher_client.get("/api/v1/me/uso")).json()
    assert situacao["coleta_ativa"] is True
    assert situacao["beta_fim"] == "2027-09-12"

    desligado = (await researcher_client.patch("/api/v1/me/uso", json={"coleta_ativa": False})).json()
    assert desligado["coleta_ativa"] is False
    assert desligado["alterada_em"] is not None
    assert db_session.get(UserModel, RESEARCHER_ID_TESTE).uso_coleta_ativa is False
    assert db_session.query(ProcessingRecordModel).filter_by(operation="usage_opt_out").count() == 1


@pytest.mark.anyio
async def test_desligar_e_apagar_o_que_ja_existe(researcher_client: httpx.AsyncClient, db_session: Session):
    _registros_da_pesquisadora(db_session)

    resp = await researcher_client.patch("/api/v1/me/uso", json={"coleta_ativa": False, "apagar_registros": True})
    assert resp.json()["contagens"] == {"eventos": 0, "erros": 0, "chamadas_ia": 0}
    assert db_session.query(ProcessingRecordModel).filter_by(operation="usage_data_erased").count() == 1


@pytest.mark.anyio
async def test_apagar_sem_desligar(researcher_client: httpx.AsyncClient, db_session: Session):
    _registros_da_pesquisadora(db_session)
    resp = await researcher_client.delete("/api/v1/me/uso")
    assert resp.json()["coleta_ativa"] is True
    assert resp.json()["contagens"]["eventos"] == 0


@pytest.mark.anyio
async def test_portabilidade_inclui_os_dados_de_uso(researcher_client: httpx.AsyncClient, db_session: Session):
    _registros_da_pesquisadora(db_session)
    pacote = (await researcher_client.get("/api/v1/me/portabilidade")).json()
    assert len(pacote["dados_de_uso_do_beta"]["chamadas_de_ia"]) == 1


# ── Retenção ──────────────────────────────────────────────────────────


def test_prazos_dos_dados_de_uso(db_session: Session, contas):
    agora = datetime(2027, 3, 1, 12, 0, tzinfo=timezone.utc)
    _registros_da_pesquisadora(db_session, agora - timedelta(days=181))
    _registros_da_pesquisadora(db_session, agora - timedelta(days=100))

    r = retencao.aplicar_retencao(db_session, agora=agora)

    assert r.eventos_de_uso == 1      # 180 dias
    assert r.ocorrencias_de_erro == 2  # 90 dias
    assert r.chamadas_de_ia == 0       # 12 meses
    assert retencao.ultima_execucao_em is not None


def test_nenhum_evento_bruto_sobrevive_ao_fim_do_beta_mais_30_dias(db_session: Session, contas):
    assert settings.beta_fim.isoformat() == "2027-09-12"
    recente = datetime(2027, 10, 11, 12, 0, tzinfo=timezone.utc)
    _registros_da_pesquisadora(db_session, recente)

    vespera = datetime(2027, 10, 12, 2, 0, tzinfo=timezone.utc)   # 23:00 de 11/10 em Brasília
    assert retencao.aplicar_retencao(db_session, agora=vespera).eventos_de_uso == 0

    descarte = datetime(2027, 10, 12, 3, 0, tzinfo=timezone.utc)  # 00:00 de 12/10 em Brasília
    assert retencao.aplicar_retencao(db_session, agora=descarte).eventos_de_uso == 1
