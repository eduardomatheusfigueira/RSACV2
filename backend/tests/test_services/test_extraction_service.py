#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários do ExtractionService e limpeza de JSON da IA."""

import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    ExtractionQuestionModel,
    PaperModel,
    ProjectModel,
    ProtocolModel,
    UserModel,
)
from app.services.extraction_service import ExtractionService
from app.infrastructure.ai.gemini_client import GeminiAIClient
from app.infrastructure.ai.openai_compatible_client import OpenAICompatibleAIClient


def test_clean_json_gemini():
    client = GeminiAIClient(api_keys=["AIzaSyFakeKey"])
    
    # 1. Objeto padrão com markdown
    raw_obj = "```json\n{\n  \"respostas\": []\n}\n```"
    assert client._clean_json(raw_obj) == '{\n  "respostas": []\n}'

    # 2. Array padrão com markdown
    raw_arr = "```json\n[\n  {\"question_id\": \"q1\", \"answer\": \"teste\"}\n]\n```"
    assert client._clean_json(raw_arr) == '[\n  {"question_id": "q1", "answer": "teste"}\n]'

    # 3. Array puro sem markdown
    raw_arr_plain = '[\n  {"question_id": "q1", "answer": "teste"}\n]'
    assert client._clean_json(raw_arr_plain) == '[\n  {"question_id": "q1", "answer": "teste"}\n]'

    # 4. Objeto puro
    raw_obj_plain = '{"respostas": [{"question_id": "q1", "answer": "teste"}]}'
    assert client._clean_json(raw_obj_plain) == '{"respostas": [{"question_id": "q1", "answer": "teste"}]}'


def test_clean_json_openai():
    client = OpenAICompatibleAIClient(provider_name="qwen", base_url="http://localhost:11434/v1", model_name="qwen")
    
    raw_arr = "```json\n[\n  {\"question_id\": \"q1\", \"answer\": \"teste\"}\n]\n```"
    assert client._clean_json(raw_arr) == '[\n  {"question_id": "q1", "answer": "teste"}\n]'

    raw_obj = "```json\n{\n  \"respostas\": []\n}\n```"
    assert client._clean_json(raw_obj) == '{\n  "respostas": []\n}'


@pytest.mark.anyio
async def test_extract_answers_with_various_json_formats(db_session: Session):
    # Criar usuário, projeto, protocolo e artigo
    user = UserModel(username="user_ext", email="ext@test.com", password_hash="hash", role="researcher", is_active=True)
    db_session.add(user)
    db_session.flush()

    project = ProjectModel(id="proj-ext-1", title="Projeto Extração", methodology="PRISMA-ScR", owner_id=user.id)
    db_session.add(project)

    protocol = ProtocolModel(id="proto-ext-1", project_id=project.id, objective="Objetivo Teste")
    db_session.add(protocol)

    q1 = ExtractionQuestionModel(id="q-uuid-1", protocol_id=protocol.id, text="Qual o método?", order=0)
    q2 = ExtractionQuestionModel(id="q-uuid-2", protocol_id=protocol.id, text="Qual a amostra?", order=1)
    db_session.add_all([q1, q2])

    paper = PaperModel(
        id="paper-ext-1",
        project_id=project.id,
        title="Estudo de Desenvolvimento Regional",
        abstract="Resumo do estudo...",
        year=2024,
    )
    db_session.add(paper)
    db_session.commit()

    service = ExtractionService()

    # Formato 1: Array direto retornado pela IA com labels Q1 e Q2
    mock_ai_data_array = [
        {"question_id": "Q1", "answer": "Método quantitativo", "evidencia": "usou regressão", "pagina": "2"},
        {"question_id": "Q2", "answer": "150 municípios", "evidencia": "amostra de 150", "pagina": "3"},
    ]

    with patch("app.infrastructure.ai.factory.AIFactory.get_client") as mock_factory:
        mock_client = AsyncMock()
        mock_client._call_gemini_api = AsyncMock(return_value=mock_ai_data_array)
        mock_factory.return_value = mock_client

        results = await service.extract_answers_with_ai(db_session, project.id, paper.id, user_id=user.id)
        assert len(results) == 2
        assert results[0]["question_id"] == "q-uuid-1"
        assert results[0]["answer"] == "Método quantitativo"
        assert results[1]["question_id"] == "q-uuid-2"
        assert results[1]["answer"] == "150 municípios"

    # Formato 2: Dicionário com "respostas"
    mock_ai_data_dict = {
        "respostas": [
            {"question_id": "q-uuid-1", "answer": "Método qualitativo atualizado", "evidencia": "entrevistas", "pagina": "4"},
            {"question_id": "q-uuid-2", "answer": "20 especialistas", "evidencia": "20 pessoas", "pagina": "5"},
        ]
    }

    with patch("app.infrastructure.ai.factory.AIFactory.get_client") as mock_factory:
        mock_client = AsyncMock()
        mock_client._call_gemini_api = AsyncMock(return_value=mock_ai_data_dict)
        mock_factory.return_value = mock_client

        results = await service.extract_answers_with_ai(db_session, project.id, paper.id, user_id=user.id)
        assert len(results) == 2
        assert results[0]["answer"] == "Método qualitativo atualizado"
        assert results[1]["answer"] == "20 especialistas"
