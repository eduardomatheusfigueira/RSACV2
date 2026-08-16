#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — OpenAlex Harvester.
Coletor assíncrono para a base OpenAlex (dados abertos globais com mais de 250M de trabalhos).
"""

import asyncio
import logging
from typing import AsyncGenerator, Callable, List, Optional
import httpx

from app.harvesters.base import BaseHarvester, HarvestProgress, RawPaperRecord

logger = logging.getLogger(__name__)


class OpenAlexHarvester(BaseHarvester):
    """Coletor para OpenAlex REST API."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, mailto: str = "rsac@ufsc.br", timeout: float = 30.0):
        super().__init__(source_name="OpenAlex", timeout=timeout)
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
        descriptors: List[str],
        on_progress: Optional[Callable[[HarvestProgress], None]] = None,
        max_records_per_descriptor: int = 100,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for desc in descriptors:
                desc_clean = desc.strip().replace('"', '')
                if not desc_clean:
                    continue

                page = 1
                total_for_desc = 0
                per_page = 25

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
                            "search": desc_clean,
                            "per-page": per_page,
                            "page": page,
                            "mailto": self.mailto,
                        }

                        res = await client.get(self.BASE_URL, params=params)
                        if res.status_code != 200:
                            logger.warning(f"[OpenAlex] HTTP {res.status_code} para '{desc_clean}' na pág {page}")
                            break

                        data = res.json()
                        results = data.get("results", [])
                        if not results:
                            break

                        for work in results:
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

                            # Primary location / URL
                            prim_loc = work.get("primary_location", {}) or {}
                            dl_url = prim_loc.get("landing_page_url", "") or raw_doi or ""

                            # Institution / Source host
                            source_info = prim_loc.get("source", {}) or {}
                            inst_name = source_info.get("display_name", "OpenAlex")

                            paper = RawPaperRecord(
                                title=work.get("title", "").strip(),
                                authors=authors_str,
                                year=pub_year,
                                abstract=abstract_str,
                                doi=doi_clean,
                                source_name=self.source_name,
                                source_id=work.get("id", ""),
                                download_url=dl_url,
                                research_type=work.get("type_crossref", "journal-article"),
                                institution=inst_name,
                            )

                            if paper.title:
                                yield paper
                                total_for_desc += 1
                                if total_for_desc >= max_records_per_descriptor:
                                    break

                        meta = data.get("meta", {})
                        count = meta.get("count", 0)
                        if page * per_page >= count or len(results) < per_page:
                            break

                        page += 1
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        logger.error(f"[OpenAlex] Erro na requisição para '{desc_clean}': {e}")
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
