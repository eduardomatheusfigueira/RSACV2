#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários do Serviço de Triagem com IA."""

from typing import Optional
import pytest
from app.domain.entities import Paper, Protocol
from app.infrastructure.ai.base import BaseAIClient, ProtocolSuggestions, ScreeningResult
from app.infrastructure.persistence.models import CriterionModel, PaperModel, ProjectModel, ProtocolModel
from app.services.screening_service import ScreeningService
from tests.conftest import OWNER_ID_TESTE


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

    async def assist_field(
        self,
        field_label: str,
        field_guidelines: str = "",
        current_value: str = "",
        project_title: str = "",
        methodology: str = "PRISMA-ScR",
        project_context: Optional[dict] = None,
        action: str = "generate",
        custom_instruction: str = "",
    ) -> dict:
        return {
            "suggested_text": f"Texto sugerido para {field_label}",
            "explanation": "Justificativa mock de preenchimento.",
            "model_used": "mock-model",
            "provider": "mock",
        }

    async def test_connection(self) -> bool:
        return True


@pytest.mark.anyio
async def test_screen_single_paper_included(db_session):
    mock_ai = MockAIClient()
    service = ScreeningService(ai_client=mock_ai)

    # 1. Setup projeto e protocolo
    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto IA", methodology="PRISMA-P")
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
    # O commit ebccbc5 removeu de propósito o prefixo "[IA - modelo]" das
    # observações; a justificativa é gravada limpa.
    assert paper.observations == "Estudo atende aos critérios de inclusão."
    assert "[IA -" not in paper.observations
    assert "IA" not in paper.observations
    assert "mock-model" not in paper.observations

    # Os critérios avaliados pela triagem devem ficar marcados para o estudo
    evaluations = {ce.criterion_id: ce.value for ce in paper.criteria_evaluations}
    assert evaluations[crit_inc.id] is True
    assert evaluations[crit_exc.id] is False


@pytest.mark.anyio
async def test_screen_single_paper_excluded(db_session):
    mock_ai = MockAIClient()
    service = ScreeningService(ai_client=mock_ai)

    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto IA 2", methodology="PRISMA-P")
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


@pytest.mark.anyio
async def test_screen_single_paper_marca_criterios_por_codigo(db_session):
    """Códigos INC1/EXC1 devolvidos pelo modelo devem marcar os critérios do protocolo."""

    class CodeAIClient(MockAIClient):
        async def analyze_screening(self, paper: Paper, protocol: Protocol) -> ScreeningResult:
            return ScreeningResult(
                decision="Incluído",
                inclusion_criteria={"INC 1": True, "inc2": False},
                exclusion_criteria={"EXC_1": False},
                justification="[IA - mock-model]: Estudo alinhado ao escopo da revisão.",
                confidence=0.9,
                model_used="mock-model",
                provider="mock",
            )

    service = ScreeningService(ai_client=CodeAIClient())

    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title="Projeto Códigos", methodology="PRISMA-P")
    db_session.add(proj)
    db_session.flush()

    proto = ProtocolModel(project_id=proj.id, objective="Obj")
    db_session.add(proto)
    db_session.flush()

    inc1 = CriterionModel(protocol_id=proto.id, text="Publicado em periódico revisado", is_exclusion=False)
    inc2 = CriterionModel(protocol_id=proto.id, text="Aborda desenvolvimento regional", is_exclusion=False)
    exc1 = CriterionModel(protocol_id=proto.id, text="Editorial ou resenha", is_exclusion=True)
    db_session.add_all([inc1, inc2, exc1])

    paper = PaperModel(
        project_id=proj.id,
        title="Estudo sobre arranjos produtivos locais",
        abstract="Resumo completo do estudo.",
        decision="Pendente",
    )
    db_session.add(paper)
    db_session.commit()

    await service.screen_single_paper(db_session, proj.id, paper.id)
    db_session.refresh(paper)

    evaluations = {ce.criterion_id: ce.value for ce in paper.criteria_evaluations}
    assert evaluations[inc1.id] is True
    assert evaluations[inc2.id] is False
    assert evaluations[exc1.id] is False

    # O prefixo de origem automática é removido antes de gravar a observação
    assert paper.observations == "Estudo alinhado ao escopo da revisão."


def test_strip_ai_prefix_remove_variacoes():
    from app.services.screening_service import _strip_ai_prefix

    assert _strip_ai_prefix("[IA - gemini-3.6-flash]: Texto do parecer.") == "Texto do parecer."
    assert _strip_ai_prefix("[I.A. gemini-3.6-flash] Texto do parecer.") == "Texto do parecer."
    assert _strip_ai_prefix("(AI - gpt-4o): Texto do parecer.") == "Texto do parecer."
    assert _strip_ai_prefix("IA: Texto do parecer.") == "Texto do parecer."
    assert _strip_ai_prefix("Justificativa: Texto do parecer.") == "Texto do parecer."
    assert _strip_ai_prefix("Texto do parecer.") == "Texto do parecer."
    assert _strip_ai_prefix("") == ""
