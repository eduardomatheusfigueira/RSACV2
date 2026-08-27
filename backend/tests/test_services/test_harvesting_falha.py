#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Desfecho de uma fonte que falha durante a coleta.

O orquestrador só marcava `failed` quando uma exceção subia do coletor; como os
coletores engoliam falhas de rede e simplesmente paravam, a execução terminava
`completed` com zero registros. O número zero, nesse caso, iria para o
fluxograma PRISMA como se a base não tivesse nada a oferecer.
"""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.harvesters.base import HarvestQuery, HarvestSourceError, RawPaperRecord
from app.infrastructure.persistence.models import (
    Base,
    HarvestRunModel,
    PaperModel,
    ProjectModel,
)
from app.services.harvesting_service import HarvestingService
from tests.conftest import OWNER_ID_TESTE


@pytest.fixture
def sessao_de_coleta():
    """Banco in-memory compartilhado entre as sessões abertas pelo serviço."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with patch("app.services.harvesting_service.SessionLocal", Session):
        yield Session


class _ColetorQueFalha:
    """Entrega alguns registros e então perde contato com a base."""

    TITULOS = (
        "Turismo náutico na tríplice fronteira do Iguaçu",
        "Policiamento fluvial integrado na Amazônia ocidental",
        "Cooperação transfronteiriça e mobilidade urbana no Chuí",
    )

    async def harvest(self, query, on_progress=None, **kwargs):
        for i, titulo in enumerate(self.TITULOS):
            yield RawPaperRecord(
                title=titulo,
                year="2024",
                source_name="SciELO",
                source_id=f"S{i}",
            )
        raise HarvestSourceError("SciELO", "nenhuma página de resultados pôde ser lida", "HTTP 403")


@pytest.mark.anyio
async def test_fonte_que_falha_e_marcada_como_failed(sessao_de_coleta):
    session = sessao_de_coleta()
    projeto = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto Coleta", methodology="PRISMA-P")
    session.add(projeto)
    session.commit()
    project_id = projeto.id
    session.close()

    servico = HarvestingService()
    with patch(
        "app.services.harvesting_service.HarvesterFactory.get_harvester",
        return_value=_ColetorQueFalha(),
    ):
        await servico._harvest_single_source(
            project_id, "SciELO", HarvestQuery(descriptors=["turismo"]), {}
        )

    session = sessao_de_coleta()
    run = session.query(HarvestRunModel).filter(HarvestRunModel.project_id == project_id).one()

    assert run.status == "failed"
    assert "403" in (run.error_message or "")
    # Os registros já recuperados não podem ser descartados junto com a falha.
    assert run.records_found == 3
    assert session.query(PaperModel).filter(PaperModel.project_id == project_id).count() == 3
    session.close()
