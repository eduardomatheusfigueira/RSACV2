#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — OpenAlex Harvester.
Coletor assíncrono para a base OpenAlex (grafo global com mais de 250M de trabalhos)
com paginação por cursor (sem teto de 10k), busca focada em título e resumo
(`title_and_abstract.search`), reconstrução de resumo invertido e pool de cortesia.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any, Dict, List, Optional
import httpx

from app.domain.enums import to_canonical_doc_type
from app.harvesters.base import (
    BaseHarvester,
    HarvesterCapabilities,
    HarvestProgress,
    HarvestQuery,
    ProgressCallback,
    RawPaperRecord,
)
from app.harvesters.factory import register_harvester

logger = logging.getLogger(__name__)


@register_harvester("OPENALEX")
class OpenAlexHarvester(BaseHarvester):
    """Coletor para OpenAlex REST API com paginação por cursor."""

    capabilities = HarvesterCapabilities(
        supports_year_range=True,
        supports_language=True,
        supports_document_type=True,
        supports_institution=False,
        supports_open_access=True,
        supports_boolean_query=True,
        requires_api_key=False,
        default_page_size=50,
        max_page_size=100,
        default_delay=0.25,
    )

    BASE_URL = "https://api.openalex.org/works"

    def __init__(
        self,
        api_key: Optional[str] = None,
        mailto: str = "rsac@ufsc.br",
        timeout: float = 35.0,
    ):
        super().__init__(source_name="OpenAlex", timeout=timeout)
        self.api_key = api_key
        self.mailto = mailto

    def _reconstruct_abstract(self, inverted_index: Optional[dict]) -> str:
        """Reconstrói o abstract a partir do abstract_inverted_index do OpenAlex."""
        if not inverted_index or not isinstance(inverted_index, dict):
            return ""
        try:
            position_word_map = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    position_word_map.append((pos, word))
            position_word_map.sort(key=lambda x: x[0])
            return " ".join([word for _, word in position_word_map])
        except Exception:
            return ""

    async def harvest(
        self,
        query: HarvestQuery | List[str],
        on_progress: Optional[ProgressCallback] = None,
        max_records_per_descriptor: Optional[int] = None,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        # Normalizar HarvestQuery
        if isinstance(query, HarvestQuery):
            descriptors = query.descriptors
            limit = query.max_records_per_descriptor or float("inf")
            per_page = query.page_size or self.capabilities.default_page_size
            year_start = query.year_start
            year_end = query.year_end
            languages = query.languages
            open_access_only = query.open_access_only
        else:
            descriptors = query
            limit = float("inf") if (not max_records_per_descriptor or max_records_per_descriptor <= 0) else max_records_per_descriptor
            per_page = self.capabilities.default_page_size
            year_start = None
            year_end = None
            languages = []
            open_access_only = False

        headers = {
            "User-Agent": f"Revsist/2.0 (mailto:{self.mailto})",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["api_key"] = self.api_key

        total_overall = 0

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            for desc in descriptors:
                desc_clean = desc.strip().replace('"', "")
                if not desc_clean:
                    continue

                cursor = "*"
                page = 1
                total_for_desc = 0

                while total_for_desc < limit and cursor:
                    if on_progress:
                        await on_progress(
                            HarvestProgress(
                                source_name=self.source_name,
                                current_descriptor=desc_clean,
                                page=page,
                                total_found_so_far=total_overall,
                                phase="harvesting",
                            )
                        )

                    # Montar filtros nativos do OpenAlex
                    filter_parts = []

                    # 1. Busca focada em título e resumo (para evitar ruído de texto integral)
                    if "*" in desc_clean or "?" in desc_clean:
                        search_param = desc_clean
                    else:
                        filter_parts.append(f"title_and_abstract.search:{desc_clean}")
                        search_param = None

                    # 2. Recorte temporal
                    if year_start and year_end and year_start == year_end:
                        filter_parts.append(f"publication_year:{year_start}")
                    elif year_start or year_end:
                        y_start = year_start or 1900
                        y_end = year_end or 2099
                        filter_parts.append(f"from_publication_date:{y_start}-01-01,to_publication_date:{y_end}-12-31")

                    # 3. Idiomas
                    if languages:
                        clean_langs = [l.strip().lower() for l in languages if l.strip()]
                        if len(clean_langs) == 1:
                            filter_parts.append(f"language:{clean_langs[0]}")
                        elif len(clean_langs) > 1:
                            filter_parts.append(f"language:{'|'.join(clean_langs)}")

                    # 4. Open Access
                    if open_access_only:
                        filter_parts.append("is_oa:true")

                    params: Dict[str, Any] = {
                        "per-page": per_page,
                        "cursor": cursor,
                        "mailto": self.mailto,
                    }
                    if filter_parts:
                        params["filter"] = ",".join(filter_parts)
                    if search_param:
                        params["search"] = search_param

                    try:
                        res = await client.get(self.BASE_URL, params=params)
                        if res.status_code != 200:
                            logger.warning(f"[OpenAlex] HTTP {res.status_code} para '{desc_clean}' (cursor {cursor})")
                            break

                        data = res.json()
                        results = data.get("results", [])
                        if not results:
                            break

                        for work in results:
                            raw_title = work.get("title")
                            title_str = str(raw_title).strip() if raw_title else ""
                            if not title_str:
                                continue

                            # Authors
                            authorships = work.get("authorships", [])
                            authors_names = [
                                a.get("author", {}).get("display_name", "")
                                for a in authorships
                                if a.get("author", {}).get("display_name")
                            ]
                            authors_str = "; ".join(authors_names)

                            # Year
                            pub_year = str(work.get("publication_year", ""))

                            # Abstract
                            inverted = work.get("abstract_inverted_index")
                            abstract_str = self._reconstruct_abstract(inverted)

                            # DOI
                            raw_doi = work.get("doi", "") or None
                            doi_clean = raw_doi.replace("https://doi.org/", "").strip() if raw_doi else None

                            # Primary location / URL / Journal
                            prim_loc = work.get("primary_location", {}) or {}
                            dl_url = prim_loc.get("landing_page_url", "") or raw_doi or ""

                            source_info = prim_loc.get("source", {}) or {}
                            journal_name = source_info.get("display_name", "")

                            # Canonical Research Type
                            raw_type = work.get("type_crossref") or work.get("type") or "journal-article"
                            canonical_type = to_canonical_doc_type(self.source_name, raw_type)

                            # Clean source ID (sem prefixo URL)
                            raw_id = work.get("id", "")
                            clean_id = raw_id.replace("https://openalex.org/", "").strip()

                            paper = RawPaperRecord(
                                title=title_str,
                                authors=authors_str,
                                year=pub_year,
                                abstract=abstract_str,
                                doi=doi_clean,
                                source_name=self.source_name,
                                source_id=clean_id,
                                download_url=dl_url,
                                research_type=canonical_type,
                                journal=journal_name,
                                institution="OpenAlex",
                                matched_descriptor=desc_clean,
                                extra_metadata={"raw_work": work},
                            )

                            if paper.title:
                                yield paper
                                total_for_desc += 1
                                total_overall += 1
                                if total_for_desc >= limit:
                                    break

                        # Avançar cursor para próxima página
                        meta = data.get("meta", {})
                        next_cursor = meta.get("next_cursor")
                        if not next_cursor or next_cursor == cursor or len(results) == 0:
                            break

                        cursor = next_cursor
                        page += 1
                        await asyncio.sleep(self.capabilities.default_delay)

                    except Exception as e:
                        logger.error(f"[OpenAlex] Erro na requisição para '{desc_clean}': {e}")
                        break

            if on_progress:
                await on_progress(
                    HarvestProgress(
                        source_name=self.source_name,
                        current_descriptor="",
                        page=1,
                        total_found_so_far=total_overall,
                        phase="completed",
                        is_complete=True,
                    )
                )
