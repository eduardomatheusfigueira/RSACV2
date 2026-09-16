#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Medidor de consumo de IA (doc 52 §5.5, T-11 e T-12).

Sem rede: as respostas dos provedores são gravadas aqui no formato real de
cada API, e o `httpx.AsyncClient` dos clientes é trocado por um com transporte
simulado.
"""

import json

import httpx
import pytest
from sqlalchemy.orm import Session

from app.infrastructure.ai.gemini_client import GeminiAIClient
from app.infrastructure.ai.openai_compatible_client import OpenAICompatibleAIClient
from app.infrastructure.persistence.models import UsoChamadaIAModel
from app.services.uso import medidor
from tests.conftest import RESEARCHER_ID_TESTE

RESPOSTA_GEMINI = {
    "candidates": [{"content": {"parts": [{"text": '{"decisao": "Incluído"}'}]}}],
    "usageMetadata": {
        "promptTokenCount": 812,
        "candidatesTokenCount": 64,
        "thoughtsTokenCount": 120,
        "cachedContentTokenCount": 0,
        "totalTokenCount": 996,
    },
    "modelVersion": "gemini-3.6-flash",
}

RESPOSTA_OPENAI = {
    "model": "qwen-plus",
    "choices": [{"message": {"content": '{"decisao": "Excluído"}'}}],
    "usage": {"prompt_tokens": 700, "completion_tokens": 40, "total_tokens": 740},
}


@pytest.fixture(autouse=True)
def pares_limpos():
    GeminiAIClient._DESCANSO_POR_CHAVE.clear()
    GeminiAIClient._POSICAO_DO_RODIZIO.clear()
    yield
    GeminiAIClient._DESCANSO_POR_CHAVE.clear()
    GeminiAIClient._POSICAO_DO_RODIZIO.clear()


def _rede(monkeypatch, responder):
    original = httpx.AsyncClient
    transporte = httpx.MockTransport(responder)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: original(transport=transporte))


def test_leitura_do_gemini():
    tokens = medidor.tokens_do_gemini(RESPOSTA_GEMINI)
    assert tokens == {
        "tokens_entrada": 812,
        "tokens_saida": 64,
        "tokens_raciocinio": 120,
        "tokens_cache": 0,
        "tokens_total": 996,
    }


def test_leitura_openai():
    tokens = medidor.tokens_openai(RESPOSTA_OPENAI)
    assert tokens["tokens_entrada"] == 700
    assert tokens["tokens_saida"] == 40
    assert tokens["tokens_total"] == 740


@pytest.mark.anyio
async def test_gemini_grava_tokens_da_chamada(monkeypatch, db_session: Session, coleta_aberta):
    """T-11."""
    _rede(monkeypatch, lambda req: httpx.Response(200, json=RESPOSTA_GEMINI))
    cliente = GeminiAIClient(api_keys=["AIzaSyTESTE000000000000000000001"], model_name="gemini-3.6-flash")

    with medidor.medir(db_session, RESEARCHER_ID_TESTE, "triagem", project_id="projeto-x"):
        await cliente._call_gemini_api("prompt de teste")

    chamada = db_session.query(UsoChamadaIAModel).one()
    assert chamada.user_id == RESEARCHER_ID_TESTE
    assert chamada.project_id == "projeto-x"
    assert chamada.operacao == "triagem"
    assert chamada.provedor == "gemini"
    assert chamada.resultado == "ok"
    assert chamada.tokens_total == 996
    assert chamada.tokens_raciocinio == 120
    assert chamada.estimado is False
    assert chamada.chave_ordinal == 1


@pytest.mark.anyio
async def test_recusa_por_cota_e_contada(monkeypatch, db_session: Session, coleta_aberta):
    """T-12: 429 vira linha, sem tokens; a resposta boa que vem depois também."""
    corpo_429 = {
        "error": {
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}],
                }
            ]
        }
    }

    def responder(req: httpx.Request) -> httpx.Response:
        if "gemini-3.6-flash" in str(req.url):
            return httpx.Response(429, json=corpo_429)
        return httpx.Response(200, json={**RESPOSTA_GEMINI, "modelVersion": "gemini-flash-latest"})

    _rede(monkeypatch, responder)
    cliente = GeminiAIClient(api_keys=["AIzaSyTESTE000000000000000000001"], model_name="gemini-3.6-flash")

    with medidor.medir(db_session, RESEARCHER_ID_TESTE, "triagem"):
        await cliente._call_gemini_api("prompt")

    chamadas = db_session.query(UsoChamadaIAModel).order_by(UsoChamadaIAModel.tentativa).all()
    assert [c.resultado for c in chamadas] == ["limite_diario", "ok"]
    assert chamadas[0].tokens_total is None
    # A reserva respondeu no lugar do modelo pedido: é esse o sinal da Q-05.
    assert chamadas[1].modelo_pedido == "gemini-3.6-flash"
    assert chamadas[1].modelo_respondeu == "gemini-flash-latest"


@pytest.mark.anyio
async def test_openai_compativel_sem_usage_e_estimado(monkeypatch, db_session: Session, coleta_aberta):
    sem_usage = {"choices": [{"message": {"content": '{"decisao": "Pendente"}'}}]}
    _rede(monkeypatch, lambda req: httpx.Response(200, json=sem_usage))
    cliente = OpenAICompatibleAIClient(provider_name="local", base_url="http://llm.teste/v1", api_key="ollama", model_name="llama")

    with medidor.medir(db_session, RESEARCHER_ID_TESTE, "extracao"):
        await cliente._call_chat_completion("x" * 400)

    chamada = db_session.query(UsoChamadaIAModel).one()
    assert chamada.estimado is True
    assert chamada.tokens_entrada == 100
    assert chamada.provedor == "local"


@pytest.mark.anyio
async def test_openai_compativel_com_usage(monkeypatch, db_session: Session, coleta_aberta):
    _rede(monkeypatch, lambda req: httpx.Response(200, json=RESPOSTA_OPENAI))
    cliente = OpenAICompatibleAIClient(provider_name="qwen", base_url="http://qwen.teste/v1", api_key=["sk-a", "sk-b"], model_name="qwen-plus")

    with medidor.medir(db_session, RESEARCHER_ID_TESTE, "assistencia_campo"):
        await cliente._call_chat_completion("prompt")

    chamada = db_session.query(UsoChamadaIAModel).one()
    assert (chamada.tokens_total, chamada.estimado, chamada.resultado) == (740, False, "ok")


@pytest.mark.anyio
async def test_nada_e_gravado_com_a_coleta_fechada(monkeypatch, db_session: Session, contas):
    _rede(monkeypatch, lambda req: httpx.Response(200, json=RESPOSTA_GEMINI))
    cliente = GeminiAIClient(api_keys=["AIzaSyTESTE000000000000000000001"], model_name="gemini-3.6-flash")

    with medidor.medir(db_session, RESEARCHER_ID_TESTE, "triagem"):
        await cliente._call_gemini_api("prompt")

    assert db_session.query(UsoChamadaIAModel).count() == 0


@pytest.mark.anyio
async def test_chamada_fora_de_medidor_e_contada_e_nao_quebra(monkeypatch, db_session: Session, coleta_aberta):
    _rede(monkeypatch, lambda req: httpx.Response(200, json=RESPOSTA_GEMINI))
    cliente = GeminiAIClient(api_keys=["AIzaSyTESTE000000000000000000001"], model_name="gemini-3.6-flash")

    resultado = await cliente._call_gemini_api("prompt")

    assert resultado == {"decisao": "Incluído"}
    assert medidor.nao_atribuidas == 1
    assert db_session.query(UsoChamadaIAModel).count() == 0


def test_prompt_e_chave_nunca_sao_gravados(db_session: Session, coleta_aberta):
    with medidor.medir(db_session, RESEARCHER_ID_TESTE, "triagem"):
        medidor.anotar(provedor="gemini", modelo_pedido="m", resultado="ok", tokens={"tokens_total": 5})

    linha = db_session.query(UsoChamadaIAModel).one()
    colunas = {c.name for c in UsoChamadaIAModel.__table__.columns}
    assert not colunas & {"prompt", "resposta", "chave", "api_key"}
    assert "AIzaSy" not in json.dumps({c: str(getattr(linha, c)) for c in colunas})


def test_operacao_desconhecida_e_erro_de_programacao(db_session: Session):
    with pytest.raises(ValueError):
        with medidor.medir(db_session, RESEARCHER_ID_TESTE, "inventada"):
            pass
