#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários para o coletor PubMed (ESearch / EFetch & Structured XML)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.harvesters.pubmed import PubMedHarvester
from app.harvesters.base import HarvestQuery, RawPaperRecord


@pytest.mark.anyio
async def test_pubmed_harvest_success():
    harvester = PubMedHarvester(api_key="mock_ncbi_key")

    esearch_data = {
        "esearchresult": {
            "count": "1",
            "retmax": "10000",
            "retstart": "0",
            "idlist": ["12345678"],
        }
    }

    efetch_xml = """<?xml version="1.0"?>
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>12345678</PMID>
          <Article>
            <ArticleTitle>Socioeconomic Factors in Rural Health Planning.</ArticleTitle>
            <Journal>
              <Title>Journal of Community Development</Title>
              <JournalIssue>
                <PubDate>
                  <Year>2023</Year>
                </PubDate>
              </JournalIssue>
            </Journal>
            <AuthorList>
              <Author>
                <LastName>Smith</LastName>
                <ForeName>John</ForeName>
              </Author>
            </AuthorList>
            <Abstract>
              <AbstractText Label="OBJECTIVE">To assess rural regional development policies.</AbstractText>
              <AbstractText Label="RESULTS">Significantly improved local governance.</AbstractText>
            </Abstract>
          </Article>
        </MedlineCitation>
        <PubmedData>
          <ArticleIdList>
            <ArticleId IdType="doi">10.1016/j.jcd.2023.01.002</ArticleId>
          </ArticleIdList>
        </PubmedData>
      </PubmedArticle>
    </PubmedArticleSet>
    """

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mock_search_resp = MagicMock(status_code=200)
    mock_search_resp.json.return_value = esearch_data

    mock_fetch_resp = MagicMock(status_code=200)
    mock_fetch_resp.text = efetch_xml

    mock_client.get.side_effect = [mock_search_resp, mock_fetch_resp]

    with patch("httpx.AsyncClient", return_value=mock_client):
        query = HarvestQuery(
            descriptors=['"rural development" AND "health planning"'],
            max_records_per_descriptor=5,
        )

        records = []
        async for r in harvester.harvest(query):
            records.append(r)

        assert len(records) == 1
        record = records[0]
        assert isinstance(record, RawPaperRecord)
        assert record.title == "Socioeconomic Factors in Rural Health Planning."
        assert record.source == "PubMed"
        assert record.doi == "10.1016/j.jcd.2023.01.002"
        assert record.authors == "Smith, John"
        assert record.journal == "Journal of Community Development"
        assert "OBJECTIVE: To assess rural regional development policies." in record.abstract
        assert "RESULTS: Significantly improved local governance." in record.abstract
