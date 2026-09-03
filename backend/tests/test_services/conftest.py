#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Peças compartilhadas pelos testes de serviço da triagem em lote.

Moradas aqui, e não dentro de um dos arquivos de teste, porque mais de um
precisa delas: uma fixture que só existe no módulo onde foi escrita obriga o
segundo interessado a importá-la por caminho, o que funciona por acidente do
pytest e quebra ao primeiro rearranjo.
"""

import asyncio
from typing import List

import pytest

from app.domain.entities import Paper, Protocol
from app.infrastructure.ai.base import (
    BaseAIClient,
    ProtocolSuggestions,
    ProvedorIndisponivel,
    ScreeningResult,
)
from app.infrastructure.persistence.models import (
    CriterionModel,
    PaperModel,
    ProjectModel,
    ProtocolModel,
)
from app.services import screening_service as modulo_triagem
from app.services.screening_service import AuditActor, ScreeningService
from tests.conftest import OWNER_ID_TESTE

#: Resumo de tamanho realista.
#:
#: Precisa passar de `TAMANHO_MINIMO_DE_RESUMO`: desde que registros sem resumo
#: utilizável saíram da fila da triagem assistida, um resumo de brincadeira com
#: trinta caracteres faz o lote — corretamente — ignorar o artigo, e o teste
#: falha por um motivo que não é o que ele investiga.
RESUMO_DE_TESTE = (
    "Resumo com extensão realista: este estudo analisa arranjos de governança "
    "territorial e apresenta resultados empíricos obtidos em trabalho de campo."
)


class ClienteDeTeste(BaseAIClient):
    """Decide sempre incluir, e conta quantas vezes foi chamado."""

    def __init__(self):
        super().__init__(provider_name="mock", model_name="mock-model")
        self.chamadas: List[str] = []

    async def analyze_screening(self, paper: Paper, protocol: Protocol) -> ScreeningResult:
        self.chamadas.append(paper.title)
        return ScreeningResult(
            decision="Incluído",
            inclusion_criteria={"Critério A": True},
            exclusion_criteria={},
            justification="Atende aos critérios.",
            confidence=0.9,
            model_used="mock-model",
            provider="mock",
        )

    async def generate_protocol_suggestions(
        self, title: str, methodology: str, initial_description: str = ""
    ) -> ProtocolSuggestions:
        return ProtocolSuggestions(objective="", descriptors_pt=[])

    async def assist_field(self, *args, **kwargs) -> str:  # type: ignore[override]
        return ""

    async def test_connection(self) -> bool:
        return True


class EspiaoDeCanal:
    """Recolhe o que teria ido para o WebSocket."""

    def __init__(self):
        self.mensagens: List[dict] = []

    async def broadcast(self, project_id: str, message: dict):
        self.mensagens.append(message)

    def tipos(self) -> List[str]:
        return [m.get("type") for m in self.mensagens]


def _montar_projeto(db_session, quantidade_pendentes: int = 3) -> str:
    projeto = ProjectModel(
        id="proj-lote",
        owner_id=OWNER_ID_TESTE,
        title="Projeto de teste do lote",
        methodology="PRISMA-ScR",
    )
    db_session.add(projeto)

    protocolo = ProtocolModel(id="proto-lote", project_id="proj-lote", objective="Mapear X")
    db_session.add(protocolo)
    db_session.flush()

    db_session.add(
        CriterionModel(
            id="crit-lote-1",
            protocol_id="proto-lote",
            text="Critério A",
            is_exclusion=False,
            order=0,
        )
    )

    for i in range(quantidade_pendentes):
        db_session.add(
            PaperModel(
                id=f"paper-lote-{i}",
                project_id="proj-lote",
                title=f"Estudo pendente {i}",
                abstract=RESUMO_DE_TESTE,
                decision="Pendente",
            )
        )

    db_session.commit()
    return "proj-lote"


@pytest.fixture
def servico_de_lote(db_session, monkeypatch):
    """Serviço com IA simulada, canal espionado e a sessão do teste.

    `run_batch_screening` abre a sua própria sessão via `SessionLocal`. Num
    teste isso apontaria para outro banco que não o da fixture, e o lote não
    encontraria nenhum artigo — então a sessão é redirecionada para a do teste.
    """
    espiao = EspiaoDeCanal()
    monkeypatch.setattr(modulo_triagem, "ws_manager", espiao)

    class SessaoDoTeste:
        def __call__(self):
            return db_session

    monkeypatch.setattr(modulo_triagem, "SessionLocal", SessaoDoTeste())
    monkeypatch.setattr(db_session, "close", lambda: None)

    servico = ScreeningService()
    cliente = ClienteDeTeste()
    servico.ai_client = cliente
    return servico, cliente, espiao
