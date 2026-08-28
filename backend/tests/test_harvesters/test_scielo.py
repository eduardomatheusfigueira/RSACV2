#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários para o coletor SciELO (Crossref REST API)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bs4 import BeautifulSoup

from app.harvesters.scielo import (
    SciELOHarvester,
    parse_scielo_item,
    parse_crossref_scielo_item,
    clean_crossref_abstract,
)
from app.harvesters.base import HarvestQuery, RawPaperRecord


def test_clean_crossref_abstract():
    raw_abstract = "<jats:p>Este artigo analisa os <jats:italic>arranjos produtivos locais</jats:italic> sob uma ótica territorial.</jats:p>"
    cleaned = clean_crossref_abstract(raw_abstract)
    assert cleaned == "Este artigo analisa os arranjos produtivos locais sob uma ótica territorial."


def test_parse_crossref_scielo_item():
    item_json = {
        "title": ["Dinâmicas Territoriais e Governança em Arranjos Produtivos Locais"],
        "author": [
            {"family": "Almeida", "given": "Marcos"},
            {"family": "Costa", "given": "Rita"},
        ],
        "issued": {"date-parts": [[2024, 5, 10]]},
        "abstract": "<jats:p>Análise empírica das redes de cooperação regional no semiárido.</jats:p>",
        "DOI": "10.1590/1980-549720240015",
        "URL": "https://doi.org/10.1590/1980-549720240015",
        "container-title": ["Revista de Economia Regional e Urbana"],
        "type": "journal-article",
        "member": "530",
        "publisher": "FapUNIFESP (SciELO)",
    }

    record = parse_crossref_scielo_item(item_json, descriptor="arranjos produtivos")
    assert isinstance(record, RawPaperRecord)
    assert record.title == "Dinâmicas Territoriais e Governança em Arranjos Produtivos Locais"
    assert record.source == "SciELO"
    assert record.year == "2024"
    assert record.doi == "10.1590/1980-549720240015"
    assert "Almeida, Marcos" in record.authors
    assert "Costa, Rita" in record.authors
    assert record.journal == "Revista de Economia Regional e Urbana"
    assert "Análise empírica das redes de cooperação" in record.abstract
    assert record.research_type == "Artigo de Periódico"


def test_parse_scielo_item_legacy_html():
    html_item = """
    <div class="item" id="S0103-20032024000100005">
      <div class="title">
        <a href="https://scielo.br/j/rer/a/XYZ123/?lang=pt">
          Dinâmicas Territoriais e Arranjos Produtivos no Nordeste
        </a>
      </div>
      <div class="authors">
        <a href="#">Almeida, Marcos</a>
        <a href="#">Costa, Rita</a>
      </div>
      <div class="source">
        <a href="#">Revista de Economia Regional e Urbana</a>
      </div>
      <div class="abstract">
        Resumo Este artigo analisa a evolução socioeconômica dos arranjos produtivos locais.
      </div>
      <span class="DOIResults">10.1590/1980-549720240015</span>
    </div>
    """
    soup = BeautifulSoup(html_item, "html.parser")
    item_tag = soup.find(class_="item")

    record = parse_scielo_item(item_tag, descriptor="arranjos produtivos")
    assert isinstance(record, RawPaperRecord)
    assert record.title == "Dinâmicas Territoriais e Arranjos Produtivos no Nordeste"
    assert record.source == "SciELO"
    assert record.year == "2024"
    assert record.doi == "10.1590/1980-549720240015"


@pytest.mark.anyio
async def test_scielo_harvest_integration():
    harvester = SciELOHarvester()

    payload = {
        "status": "ok",
        "message": {
            "total-results": 1,
            "next-cursor": "cursor_token_123",
            "items": [
                {
                    "title": ["Políticas Públicas e Desenvolvimento Regional"],
                    "author": [{"family": "Silva", "given": "João"}],
                    "issued": {"date-parts": [[2023]]},
                    "DOI": "10.1590/s0103-123420230001",
                    "URL": "https://doi.org/10.1590/s0103-123420230001",
                    "container-title": ["Revista Brasileira de Estudos Regionais"],
                    "type": "journal-article",
                }
            ],
        },
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload
    mock_client.get.return_value = mock_resp

    with patch("httpx.AsyncClient", return_value=mock_client):
        query = HarvestQuery(
            descriptors=['"politicas publicas"'],
            max_records_per_descriptor=5,
            year_start=2020,
            year_end=2024,
        )

        records = []
        async for r in harvester.harvest(query):
            records.append(r)

        assert len(records) == 1
        assert records[0].title == "Políticas Públicas e Desenvolvimento Regional"
        assert records[0].year == "2023"
        assert records[0].source == "SciELO"

