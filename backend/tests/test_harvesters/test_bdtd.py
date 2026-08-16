#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários para o coletor BDTD (VuFind / IBICT)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.harvesters.bdtd import (
    BDTDHarvester,
    clean_advisor_name,
    clean_creator_name,
    sanitize_bdtd_filters,
)
from app.harvesters.base import HarvestQuery, RawPaperRecord


def test_clean_advisor_name():
    assert clean_advisor_name("Silva, João 1970-") == "Silva, João"
    assert clean_advisor_name("Souza, Maria; Santos, Pedro") == "Souza, Maria; Santos, Pedro"
    assert clean_advisor_name("Não informado") == ""
    assert clean_advisor_name("None") == ""
    assert clean_advisor_name("") == ""


def test_clean_creator_name():
    assert clean_creator_name("Oliveira, Carlos 1980-2020") == "Oliveira, Carlos"
    assert clean_creator_name("Ferreira, Ana; Souza, B.") == "Ferreira, Ana; Souza, B."


def test_sanitize_bdtd_filters():
    filters = [
        'format:"Thesis"',
        'language:"por"',
        'publishDate:[2020 TO 2025]',
        'institution:"USP"',
    ]
    api_filters, allowed_langs = sanitize_bdtd_filters(filters)
    assert len(api_filters) == 2
    assert api_filters[0] == 'format:"Thesis"'
    assert api_filters[1] == 'publishDate:[2020 TO 2025]'
    assert "por" in allowed_langs


@pytest.mark.anyio
async def test_bdtd_harvest_success():
    harvester = BDTDHarvester()

    mock_vufind_response = {
        "status": "OK",
        "resultCount": 1,
        "records": [
            {
                "id": "USP_12345",
                "title": "Políticas Públicas e Desenvolvimento Regional no Semiárido",
                "authors": {"primary": {"Silva, João": {}}},
                "publicationDates": ["2023"],
                "formats": ["Tese"],
                "institutions": ["Universidade de São Paulo"],
                "summary": ["Resumo sobre o impacto das políticas territoriais de convivência com a seca."],
                "languages": ["por"],
                "urls": [{"url": "https://teses.usp.br/teses/12345"}],
            }
        ],
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_vufind_response
    mock_client.get.return_value = mock_resp

    with patch("httpx.AsyncClient", return_value=mock_client):
        query = HarvestQuery(
            descriptors=['"desenvolvimento regional" AND "politicas publicas"'],
            fetch_details=False,
            max_records_per_descriptor=10,
        )

        records = []
        async for r in harvester.harvest(query):
            records.append(r)

        assert len(records) == 1
        record = records[0]
        assert isinstance(record, RawPaperRecord)
        assert record.title == "Políticas Públicas e Desenvolvimento Regional no Semiárido"
        assert record.source == "BDTD"
        assert record.year == "2023"
        assert record.research_type == "Tese"
        assert "Resumo sobre o impacto" in record.abstract
        assert isinstance(record.abstract, str)


@pytest.mark.anyio
async def test_bdtd_language_post_filtering():
    harvester = BDTDHarvester()

    mock_vufind_response = {
        "status": "OK",
        "resultCount": 2,
        "records": [
            {
                "id": "REC_POR",
                "title": "Estudo em Português",
                "publicationDates": ["2022"],
                "languages": ["por"],
                "formats": ["Tese"],
                "summary": ["Resumo em português."],
            },
            {
                "id": "REC_ENG",
                "title": "Study in English",
                "publicationDates": ["2022"],
                "languages": ["eng"],
                "formats": ["Tese"],
                "summary": ["Summary in english."],
            },
        ],
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_vufind_response
    mock_client.get.return_value = mock_resp

    with patch("httpx.AsyncClient", return_value=mock_client):
        query = HarvestQuery(
            descriptors=['"desenvolvimento regional"'],
            languages=["por"],
            fetch_details=False,
        )

        records = []
        async for r in harvester.harvest(query):
            records.append(r)

        # English record should be discarded by local post-filtering
        assert len(records) == 1
        assert records[0].title == "Estudo em Português"
