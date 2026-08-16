#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários para o coletor OpenAlex (Cursor Pagination & Inverted Index)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.harvesters.openalex import OpenAlexHarvester
from app.harvesters.base import HarvestQuery, RawPaperRecord


def test_openalex_abstract_reconstruction():
    harvester = OpenAlexHarvester()
    inverted_index = {
        "Regional": [0],
        "governance": [1],
        "and": [2],
        "local": [3],
        "development": [4],
        "policies.": [5],
    }
    abstract = harvester._reconstruct_abstract(inverted_index)
    assert abstract == "Regional governance and local development policies."


@pytest.mark.anyio
async def test_openalex_cursor_pagination():
    harvester = OpenAlexHarvester(api_key="eduardo@test.org")

    page_1_data = {
        "meta": {"count": 2, "next_cursor": "cursor_page_2"},
        "results": [
            {
                "id": "https://openalex.org/W11111",
                "title": "Territorial Development in Latin America",
                "doi": "https://doi.org/10.1000/182",
                "publication_year": 2023,
                "type": "journal-article",
                "authorships": [
                    {"author": {"display_name": "Maria Silva"}},
                    {"author": {"display_name": "Carlos Santos"}},
                ],
                "primary_location": {
                    "source": {"display_name": "Journal of Regional Studies"},
                    "landing_page_url": "https://doi.org/10.1000/182",
                },
                "abstract_inverted_index": {
                    "A": [0],
                    "comprehensive": [1],
                    "study.": [2],
                },
            }
        ],
    }

    page_2_data = {
        "meta": {"count": 2, "next_cursor": None},
        "results": [
            {
                "id": "https://openalex.org/W22222",
                "title": "Public Policy and Regional Innovation",
                "doi": "https://doi.org/10.1000/183",
                "publication_year": 2024,
                "type": "book-chapter",
                "authorships": [{"author": {"display_name": "Ana Lima"}}],
                "primary_location": {"source": {"display_name": "Springer Books"}},
                "abstract_inverted_index": {"Innovation": [0], "dynamics.": [1]},
            }
        ],
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mock_resp_1 = MagicMock(status_code=200)
    mock_resp_1.json.return_value = page_1_data

    mock_resp_2 = MagicMock(status_code=200)
    mock_resp_2.json.return_value = page_2_data

    mock_client.get.side_effect = [mock_resp_1, mock_resp_2]

    with patch("httpx.AsyncClient", return_value=mock_client):
        query = HarvestQuery(
            descriptors=['"regional development"'],
            max_records_per_descriptor=10,
        )

        records = []
        async for r in harvester.harvest(query):
            records.append(r)

        assert len(records) == 2
        assert records[0].title == "Territorial Development in Latin America"
        assert records[0].doi == "10.1000/182"
        assert records[0].authors == "Maria Silva; Carlos Santos"
        assert records[0].research_type == "Artigo de Periódico"
        assert records[0].journal == "Journal of Regional Studies"

        assert records[1].title == "Public Policy and Regional Innovation"
        assert records[1].research_type == "Capítulo de Livro"
