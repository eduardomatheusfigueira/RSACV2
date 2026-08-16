#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Scopus Harvester (Elsevier API).
Coletor assíncrono para a base Scopus via Elsevier Developer API.
"""

import asyncio
import logging
from typing import AsyncGenerator, Callable, List, Optional
import httpx

from app.harvesters.base import BaseHarvester, HarvestProgress, RawPaperRecord

logger = logging.getLogger(__name__)


class ScopusHarvester(BaseHarvester):
    """Coletor para Scopus Search API."""

    SEARCH_URL = "https://api.elsevier.com/content/search/scopus"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 35.0):
        super().__init__(source_name="Scopus", timeout=timeout)
        self.api_key = api_key

    async def harvest(
        self,
        descriptors: List[str],
        on_progress: Optional[Callable[[HarvestProgress], None]] = None,
        max_records_per_descriptor: int = 100,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        if not self.api_key:
            logger.info("[Scopus] API Key não configurada. Pulando Scopus.")
            return

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for desc in descriptors:
                desc_clean = desc.strip()
                if not desc_clean:
                    continue

                page = 1
                total_for_desc = 0
                count_per_page = 25

                while total_for_desc < max_records_per_descriptor:
                    if on_progress:
                        on_progress(
                            HarvestProgress(
                                source_name=self.source_name,
                                current_descriptor=desc_clean,
                                page=page,
                                total_found_so_far=total_for_desc,
                            )
                        )

                    try:
                        params = {
                            "query": f"TITLE-ABS-KEY({desc_clean})",
                            "count": count_per_page,
                            "start": (page - 1) * count_per_page,
                            "view": "STANDARD",
                        }
                        headers = {
                            "X-ELS-APIKey": self.api_key,
                            "Accept": "application/json",
                        }

                        res = await client.get(self.SEARCH_URL, params=params, headers=headers)
                        if res.status_code != 200:
                            logger.warning(f"[Scopus] HTTP {res.status_code} para '{desc_clean}'")
                            break

                        data = res.json()
                        search_results = data.get("search-results", {})
                        entries = search_results.get("entry", [])
                        if not entries:
                            break

                        for entry in entries:
                            title_str = entry.get("dc:title", "")
                            creator = entry.get("dc:creator", "")
                            pub_date = entry.get("prism:coverDate", "")
                            year_str = pub_date[:4] if pub_date else ""
                            doi = entry.get("prism:doi") or None
                            doc_type = entry.get("subtypeDescription", "Article")
                            pub_name = entry.get("prism:publicationName", "Scopus")

                            link_obj = next(
                                (l for l in entry.get("link", []) if l.get("@ref") == "scopus"),
                                None,
                            )
                            scopus_url = link_obj.get("@href", "") if link_obj else ""

                            paper = RawPaperRecord(
                                title=title_str.strip(),
                                authors=creator,
                                year=year_str,
                                abstract=entry.get("dc:description", "") or "",
                                doi=doi,
                                source_name=self.source_name,
                                source_id=entry.get("dc:identifier", ""),
                                download_url=scopus_url,
                                research_type=doc_type,
                                institution=pub_name,
                            )

                            if paper.title:
                                yield paper
                                total_for_desc += 1
                                if total_for_desc >= max_records_per_descriptor:
                                    break

                        total_results = int(search_results.get("opensearch:totalResults", 0))
                        if page * count_per_page >= total_results or len(entries) < count_per_page:
                            break

                        page += 1
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"[Scopus] Erro na requisição: {e}")
                        break

            if on_progress:
                on_progress(
                    HarvestProgress(
                        source_name=self.source_name,
                        current_descriptor="",
                        page=1,
                        total_found_so_far=total_for_desc,
                        is_complete=True,
                    )
                )
