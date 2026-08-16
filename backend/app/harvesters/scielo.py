#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — SciELO Harvester.
Coletor assíncrono para a base Scientific Electronic Library Online (SciELO).
"""

import asyncio
import logging
from typing import AsyncGenerator, Callable, List, Optional
import httpx

from app.harvesters.base import BaseHarvester, HarvestProgress, RawPaperRecord

logger = logging.getLogger(__name__)


class SciELOHarvester(BaseHarvester):
    """Coletor para SciELO."""

    SEARCH_URL = "https://search.scielo.org/"

    def __init__(self, timeout: float = 35.0):
        super().__init__(source_name="SciELO", timeout=timeout)

    async def harvest(
        self,
        descriptors: List[str],
        on_progress: Optional[Callable[[HarvestProgress], None]] = None,
        max_records_per_descriptor: int = 100,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for desc in descriptors:
                desc_clean = desc.strip()
                if not desc_clean:
                    continue

                page = 1
                total_for_desc = 0
                page_size = 15

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
                            "q": desc_clean,
                            "lang": "pt",
                            "count": page_size,
                            "from": (page - 1) * page_size + 1,
                            "format": "json",
                        }
                        headers = {
                            "User-Agent": "RSAC-v2-Academic-Harvester/2.0 (mailto:rsac@ufsc.br)",
                            "Accept": "application/json, text/plain, */*",
                        }

                        res = await client.get(self.SEARCH_URL, params=params, headers=headers)
                        if res.status_code != 200:
                            logger.warning(f"[SciELO] HTTP {res.status_code} para '{desc_clean}' na pág {page}")
                            break

                        try:
                            data = res.json()
                        except Exception:
                            logger.warning(f"[SciELO] Resposta não-JSON recebida.")
                            break

                        dia_response = data.get("diaServerResponse", [])
                        if not dia_response:
                            break

                        response_docs = dia_response[0].get("response", {})
                        docs = response_docs.get("docs", [])
                        if not docs:
                            break

                        for doc in docs:
                            title_list = doc.get("ti", [])
                            title_str = title_list[0] if isinstance(title_list, list) and title_list else str(title_list)

                            authors_list = doc.get("au", [])
                            authors_str = "; ".join(authors_list) if isinstance(authors_list, list) else str(authors_list)

                            year_val = doc.get("da", "") or doc.get("la_pub_year", "") or ""
                            year_str = str(year_val)[:4] if year_val else ""

                            abstract_list = doc.get("ab", [])
                            abstract_str = abstract_list[0] if isinstance(abstract_list, list) and abstract_list else str(abstract_list)

                            doi_val = doc.get("doi", "") or None
                            doc_id = doc.get("id", "")
                            doc_url = doc.get("ur", [""])[0] if doc.get("ur") else ""

                            paper = RawPaperRecord(
                                title=title_str.strip(),
                                authors=authors_str,
                                year=year_str,
                                abstract=abstract_str,
                                doi=doi_val,
                                source_name=self.source_name,
                                source_id=doc_id,
                                download_url=doc_url,
                                research_type="Artigo de Periódico",
                                institution=doc.get("fo", [""])[0] if doc.get("fo") else "SciELO",
                            )

                            if paper.title:
                                yield paper
                                total_for_desc += 1
                                if total_for_desc >= max_records_per_descriptor:
                                    break

                        num_found = response_docs.get("numFound", 0)
                        if page * page_size >= num_found or len(docs) < page_size:
                            break

                        page += 1
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"[SciELO] Erro na requisição para '{desc_clean}': {e}")
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
