#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Fixtures dos testes de dados de uso (doc 52).

O estado padrão do sistema é **coleta fechada**: perfil de testes, interruptor
de implantação desligado, nenhuma versão dos termos declarando a coleta e
estado `aguardando`. Quem precisa de coleta aberta pede `coleta_aberta`, que
abre as cinco travas explicitamente — e cada teste de bloqueio fecha só uma
delas, para provar que ela sozinha basta.
"""

import pytest

from app.config import settings
from app.infrastructure.persistence.models import SistemaEstadoDaColetaModel, UserModel
from app.api.v1 import uso as rota_uso
from app.services import retencao
from app.services.uso import medidor, portao


@pytest.fixture(autouse=True)
def estado_limpo(monkeypatch):
    """Cache do estado, limite de lotes e contadores são globais de processo."""
    portao.invalidar_cache()
    rota_uso._lotes_recentes.clear()
    monkeypatch.setattr(medidor, "nao_atribuidas", 0)
    monkeypatch.setattr(retencao, "ultima_execucao_em", None)
    yield
    portao.invalidar_cache()
    rota_uso._lotes_recentes.clear()


@pytest.fixture
def coleta_aberta(db_session, contas, monkeypatch):
    monkeypatch.setattr(portao, "perfil_permite_coleta", lambda: True)
    monkeypatch.setattr(settings, "uso_coleta_ativa", True)
    monkeypatch.setattr(settings, "uso_versao_dos_termos", settings.terms_version)

    for conta in db_session.query(UserModel).all():
        conta.terms_version = settings.terms_version
    linha = db_session.get(SistemaEstadoDaColetaModel, "unico")
    if linha is None:
        linha = SistemaEstadoDaColetaModel(id="unico", motivo="")
        db_session.add(linha)
    linha.estado = "ativa"
    db_session.commit()
    portao.invalidar_cache()
    return contas
