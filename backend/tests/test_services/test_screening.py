#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários do Serviço de Triagem com IA."""

import pytest
from app.domain.entities import Paper, Protocol
from app.infrastructure.ai.base import BaseAIClient, ProtocolSuggestions, ScreeningResult
from app.infrastructure.persistence.models import CriterionModel, PaperModel, ProjectModel, ProtocolModel
from app.services.screening_service import ScreeningService


class MockAIClient(BaseAIClient):
    """Mock do cliente de IA para testes isolados."""

    def __init__(self):
        super().__init__(provider_name="mock", model_name="mock-model")

    async def analyze_screening(self, paper: Paper, protocol: Protocol) -> ScreeningResult:
        if "rejeitar" in paper.title.lower():
            return ScreeningResult(
                decision="Excluído",
                inclusion_criteria={"Critério A": False},
                exclusion_criteria={"Critério B": True},
                justification="Estudo viola critério de exclusão explicitamente.",
                confidence=0.98,
                model_used="mock-model",
                provider="mock",
            )
        elif "inconclusivo" in paper.title.lower():
            return ScreeningResult(
                decision="Pendente",
                justification="Dados insuficientes no resumo.",
                confidence=0.5,
                model_used="mock-model",
                provider="mock",
            )
        else:
            return ScreeningResult(
                decision="Incluído",
                inclusion_criteria={"Critério A": True},
                exclusion_criteria={"Critério B": False},
                justification="Estudo atende aos critérios de inclusão.",
                confidence=0.95,
                model_used="mock-model",
                provider="mock",
            )

    async def generate_protocol_suggestions(self, title: str, methodology: str, initial_description: str = "") -> ProtocolSuggestions:
        return ProtocolSuggestions(
            objective="Objetivo sugerido mock",
            descriptors_pt=['"termo 1" AND "termo 2"'],
            inclusion_criteria=["Critério A"],
            exclusion_criteria=["Critério B"],
        )

    async def test_connection(self) -> bool:
        return True


@pytest.mark.anyio
async def test_screen_single_paper_included(db_session):
    mock_ai = MockAIClient()
    service = ScreeningService(ai_client=mock_ai)

    # 1. Setup projeto e protocolo
    proj = ProjectModel(title="Projeto IA", methodology="PRISMA-P")
    db_session.add(proj)
    db_session.flush()

    proto = ProtocolModel(project_id=proj.id, objective="Obj")
    db_session.add(proto)
    db_session.flush()

    crit_inc = CriterionModel(protocol_id=proto.id, text="Critério A", is_exclusion=False)
    crit_exc = CriterionModel(protocol_id=proto.id, text="Critério B", is_exclusion=True)
    db_session.add_all([crit_inc, crit_exc])

    paper = PaperModel(
        project_id=proj.id,
        title="Estudo de Machine Learning Aprovado",
        abstract="Texto do resumo completo...",
        decision="Pendente",
    )
    db_session.add(paper)
    db_session.commit()

    # 2. Executar triagem
    res = await service.screen_single_paper(db_session, proj.id, paper.id)
    assert res.decision == "Incluído"
    assert res.confidence == 0.95

    # 3. Verificar persistência
    db_session.refresh(paper)
    assert paper.decision == "Incluído"
    assert paper.ai_confidence == 0.95
    assert "[IA - mock-model]" in paper.observations


@pytest.mark.anyio
async def test_screen_single_paper_excluded(db_session):
    mock_ai = MockAIClient()
    service = ScreeningService(ai_client=mock_ai)

    proj = ProjectModel(title="Projeto IA 2", methodology="PRISMA-P")
    db_session.add(proj)
    db_session.flush()

    proto = ProtocolModel(project_id=proj.id)
    db_session.add(proto)

    paper = PaperModel(
        project_id=proj.id,
        title="Estudo a Rejeitar Fora do Escopo",
        abstract="Abstract...",
        decision="Pendente",
    )
    db_session.add(paper)
    db_session.commit()

    res = await service.screen_single_paper(db_session, proj.id, paper.id)
    assert res.decision == "Excluído"
    assert res.confidence == 0.98

    db_session.refresh(paper)
    assert paper.decision == "Excluído"
