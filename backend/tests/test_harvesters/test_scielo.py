#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários para o coletor SciELO (HTML Parser / lxml)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bs4 import BeautifulSoup

from app.harvesters.scielo import SciELOHarvester, parse_scielo_item
from app.harvesters.base import HarvestQuery, RawPaperRecord


def test_parse_scielo_item():
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
    soup = BeautifulSoup(html_item, "lxml")
    item_tag = soup.find(class_="item")

    record = parse_scielo_item(item_tag, descriptor="arranjos produtivos")
    assert isinstance(record, RawPaperRecord)
    assert record.title == "Dinâmicas Territoriais e Arranjos Produtivos no Nordeste"
    assert record.source == "SciELO"
    assert record.year == "2024"
    assert record.doi == "10.1590/1980-549720240015"
    assert "Almeida, Marcos" in record.authors
    assert "Costa, Rita" in record.authors
    assert record.journal == "Revista de Economia Regional e Urbana"
    assert "Este artigo analisa a evolução" in record.abstract


@pytest.mark.anyio
async def test_scielo_harvest_integration():
    harvester = SciELOHarvester()

    html_page = """
    <html>
      <body>
        <div id="TotalHits">1</div>
        <div class="item" id="S0103-20032024000100005">
          <div class="title">
            <a href="https://scielo.br/j/rer/a/XYZ123/?lang=pt">
              Dinâmicas Territoriais no Nordeste
            </a>
          </div>
          <div class="source"><a href="#">Revista Regional</a></div>
          <div class="abstract">Resumo Estudo sobre desenvolvimento regional.</div>
        </div>
      </body>
    </html>
    """

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html_page
    mock_client.get.return_value = mock_resp

    with patch("httpx.AsyncClient", return_value=mock_client):
        query = HarvestQuery(
            descriptors=['"dinamicas territoriais"'],
            max_records_per_descriptor=5,
        )

        records = []
        async for r in harvester.harvest(query):
            records.append(r)

        assert len(records) == 1
        assert records[0].title == "Dinâmicas Territoriais no Nordeste"
        assert records[0].year == "2024"
