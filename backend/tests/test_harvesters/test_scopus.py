#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários para o coletor Scopus (Elsevier API & Abstract Retrieval)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.harvesters.scopus import ScopusHarvester
from app.harvesters.base import HarvestQuery, RawPaperRecord


@pytest.mark.anyio
async def test_scopus_missing_api_key():
    harvester = ScopusHarvester(api_key=None)
    query = HarvestQuery(descriptors=['"regional development"'])
    with pytest.raises(ValueError, match="Scopus requer chave de API"):
        async for _ in harvester.harvest(query):
            pass


@pytest.mark.anyio
async def test_scopus_harvest_success():
    harvester = ScopusHarvester(api_key="mock_scopus_key", inst_token="mock_inst_token")

    scopus_search_data = {
        "search-results": {
            "opensearch:totalResults": "1",
            "entry": [
                {
                    "dc:identifier": "SCOPUS_ID:85012345678",
                    "dc:title": "Spatial Dynamics of Regional Innovation Systems",
                    "dc:creator": "Oliveira, F.",
                    "prism:coverDate": "2024-05-01",
                    "prism:publicationName": "Regional Science Review",
                    "prism:doi": "10.1016/j.regsci.2024.01.005",
                    "prism:aggregationType": "Journal",
                    "dc:description": "Detailed empirical assessment of spatial clusters.",
                    "link": [
                        {"@ref": "scopus", "@href": "https://www.scopus.com/record/xyz"}
                    ],
                }
            ],
        }
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = scopus_search_data
    mock_client.get.return_value = mock_resp

    with patch("httpx.AsyncClient", return_value=mock_client):
        query = HarvestQuery(
            descriptors=['"regional innovation" AND "clusters"'],
            max_records_per_descriptor=5,
        )

        records = []
        async for r in harvester.harvest(query):
            records.append(r)

        assert len(records) == 1
        record = records[0]
        assert isinstance(record, RawPaperRecord)
        assert record.title == "Spatial Dynamics of Regional Innovation Systems"
        assert record.source == "Scopus"
        assert record.doi == "10.1016/j.regsci.2024.01.005"
        assert record.authors == "Oliveira, F."
        assert record.journal == "Regional Science Review"
        assert record.research_type == "Artigo de Periódico"
        assert "Detailed empirical assessment" in record.abstract
