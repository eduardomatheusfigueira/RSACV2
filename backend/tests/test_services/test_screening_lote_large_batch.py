#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Teste de triagem em lote grande (100 papers) com oscilação e limites de taxa de provedor."""

import pytest
from app.domain.entities import Paper, Protocol
from app.infrastructure.ai.base import BaseAIClient, ProtocolSuggestions, ProvedorIndisponivel, ScreeningResult
from app.infrastructure.persistence.models import PaperModel
from tests.test_services.conftest import _montar_projeto


class ClienteComLimiteRPM(BaseAIClient):
    """Simula um provedor como o Gemini que recusa por limite de RPM após ~30 chamadas rápidas."""

    def __init__(self):
        super().__init__(provider_name="mock-gemini", model_name="gemini-2.5-flash")
        self.chamadas = 0

    async def analyze_screening(self, paper: Paper, protocol: Protocol) -> ScreeningResult:
        self.chamadas += 1
        # A cada bloco de 30 chamadas, as 3 seguintes sofrem 429 temporário
        if 31 <= (self.chamadas % 40) <= 33:
            raise ProvedorIndisponivel(
                "Todas as 1 chave(s) do Gemini estão no limite de taxa por minuto. Aguarde a renovação da cota.",
                esgotado_por_cota=True,
            )

        return ScreeningResult(
            decision="Incluído" if int(paper.id.split("-")[-1]) % 2 == 0 else "Excluído",
            inclusion_criteria={},
            exclusion_criteria={},
            justification="Análise realizada com sucesso.",
            confidence=0.88,
            model_used=self.model_name,
            provider=self.provider_name,
        )

    async def generate_protocol_suggestions(self, *args, **kwargs) -> ProtocolSuggestions:
        return ProtocolSuggestions(objective="", descriptors_pt=[])

    async def assist_field(self, *args, **kwargs) -> str:
        return ""

    async def test_connection(self) -> bool:
        return True


@pytest.mark.anyio
async def test_lote_de_100_estudos_processa_ate_o_fim_com_limites_rpm(servico_de_lote, db_session):
    """Verifica se um lote de 100 estudos conclui todos os 100 estudos mesmo encontrando limites de taxa por minuto."""
    servico, _cliente, espiao = servico_de_lote
    servico.ai_client = ClienteComLimiteRPM()
    pid = _montar_projeto(db_session, quantidade_pendentes=100)

    # Executa triagem em lote com 100 papers
    await servico.run_batch_screening(pid, limit=100, concurrency=3, pausa_entre_estudos=0.0)

    tipos = espiao.tipos()
    assert "batch_screening_started" in tipos
    assert "batch_screening_completed" in tipos, f"O lote falhou prematuramente. Eventos: {tipos}"
    assert "batch_screening_failed" not in tipos

    desfecho = next(m for m in espiao.mensagens if m["type"] == "batch_screening_completed")
    assert desfecho["total_processed"] == 100, f"Processou apenas {desfecho['total_processed']} de 100."
    assert desfecho["pending"] == 0

    # Todos os 100 foram triados no banco
    pendentes_restantes = (
        db_session.query(PaperModel)
        .filter(PaperModel.project_id == pid, PaperModel.decision == "Pendente")
        .count()
    )
    assert pendentes_restantes == 0, f"Restaram {pendentes_restantes} pendentes não triados no banco."
