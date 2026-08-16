#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — BDTD Harvester (Biblioteca Digital Brasileira de Teses e Dissertações).
Interface assíncrona com o motor VuFind da BDTD via API de busca / Search Record.
"""

import asyncio
import logging
import urllib.parse
from typing import AsyncGenerator, Callable, List, Optional
import httpx

from app.harvesters.base import BaseHarvester, HarvestProgress, RawPaperRecord

logger = logging.getLogger(__name__)


class BDTDHarvester(BaseHarvester):
    """Coletor para a BDTD (IBICT / VuFind)."""

    BASE_URL = "https://bdtd.ibict.br/vufind/api/v1/search"

    def __init__(self, timeout: float = 40.0):
        super().__init__(source_name="BDTD", timeout=timeout)

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
                page_size = 20

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
                            "lookfor": desc_clean,
                            "type": "AllFields",
                            "page": page,
                            "limit": page_size,
                            "sort": "relevance",
                        }
                        headers = {
                            "User-Agent": "RSAC-v2-Academic-Harvester/2.0 (mailto:rsac@ufsc.br)"
                        }

                        res = await client.get(self.BASE_URL, params=params, headers=headers)
                        if res.status_code != 200:
                            logger.warning(f"[BDTD] HTTP {res.status_code} para '{desc_clean}' na pág {page}")
                            break

                        data = res.json()
                        records = data.get("records", [])
                        if not records:
                            break

                        for rec in records:
                            # Parse authors
                            authors_raw = rec.get("authors", {})
                            primary_authors = authors_raw.get("primary", {})
                            authors_list = list(primary_authors.keys()) if isinstance(primary_authors, dict) else []
                            authors_str = "; ".join(authors_list)

                            # Parse year
                            pub_dates = rec.get("publicationDates", [])
                            year_str = str(pub_dates[0]) if pub_dates else ""

                            # Parse institutions / formats
                            institutions = rec.get("institutions", [])
                            inst_str = ", ".join(institutions) if isinstance(institutions, list) else str(institutions)

                            formats = rec.get("formats", [])
                            res_type = formats[0] if formats else "Tese/Dissertação"

                            record_id = rec.get("id", "")
                            detail_url = f"https://bdtd.ibict.br/vufind/Record/{record_id}" if record_id else ""

                            # Parse URLs / DOIs
                            urls = rec.get("urls", [])
                            dl_url = urls[0].get("url", "") if urls and isinstance(urls[0], dict) else detail_url

                            doi = None
                            for u in urls:
                                url_val = u.get("url", "") if isinstance(u, dict) else ""
                                if "doi.org" in url_val:
                                    doi = url_val.split("doi.org/")[-1].strip()
                                    break

                            paper = RawPaperRecord(
                                title=rec.get("title", "").strip(),
                                authors=authors_str,
                                year=year_str,
                                abstract=rec.get("summary", "") or rec.get("description", "") or "",
                                doi=doi,
                                source_name=self.source_name,
                                source_id=record_id,
                                download_url=dl_url,
                                research_type=res_type,
                                institution=inst_str,
                            )

                            if paper.title:
                                yield paper
                                total_for_desc += 1
                                if total_for_desc >= max_records_per_descriptor:
                                    break

                        # Verificar se há mais páginas
                        result_count = data.get("resultCount", 0)
                        if page * page_size >= result_count or len(records) < page_size:
                            break

                        page += 1
                        await asyncio.sleep(0.5)  # Rate limiting gentil
                    except Exception as e:
                        logger.error(f"[BDTD] Erro na requisição para '{desc_clean}': {e}")
                        if on_progress:
                            on_progress(
                                HarvestProgress(
                                    source_name=self.source_name,
                                    current_descriptor=desc_clean,
                                    page=page,
                                    total_found_so_far=total_for_desc,
                                    error=str(e),
                                )
                            )
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
