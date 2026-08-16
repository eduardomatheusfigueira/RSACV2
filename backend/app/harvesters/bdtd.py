#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — BDTD Harvester (Biblioteca Digital Brasileira de Teses e Dissertações).
Interface assíncrona com o motor VuFind da BDTD via API de busca / Search Record,
com sanitização de descritores (remoção de acentos e aspas), cabeçalhos de navegador,
cookies de verificação WAF e retries com tolerância à latência do servidor IBICT.
"""

import asyncio
import logging
import re
import unicodedata
import urllib.parse
from typing import AsyncGenerator, Callable, List, Optional
import httpx

from app.harvesters.base import BaseHarvester, HarvestProgress, RawPaperRecord

logger = logging.getLogger(__name__)

RE_YEAR_TRAILING: re.Pattern = re.compile(r'(?:,\s*|\s*)\d{4}-?\d*$', re.IGNORECASE)


def sanitize_bdtd_keyword(keyword: str) -> str:
    """
    Limpa o descritor para o motor VuFind/Solr da BDTD:
    Remove aspas conflitantes e normaliza acentos para ASCII para compatibilidade com o Lucene da BDTD.
    """
    clean = keyword.replace('"', '').replace("'", "").strip()
    clean = unicodedata.normalize('NFKD', clean).encode('ASCII', 'ignore').decode('utf-8')
    return clean.strip()


def extract_bdtd_authors(authors_dict: dict) -> str:
    """Extrai e consolida autores primários, secundários e corporativos."""
    if not authors_dict or not isinstance(authors_dict, dict):
        return ""

    author_list: List[str] = []
    # 1. Primários
    primary = authors_dict.get('primary', {})
    if isinstance(primary, dict):
        author_list.extend(primary.keys())
    elif isinstance(primary, list):
        author_list.extend(primary)

    # 2. Secundários
    secondary = authors_dict.get('secondary', [])
    if isinstance(secondary, dict):
        author_list.extend(secondary.keys())
    elif isinstance(secondary, list):
        for sa in secondary:
            if isinstance(sa, dict):
                author_list.extend(sa.keys())
            else:
                author_list.append(str(sa))

    # 3. Corporativos
    corporate = authors_dict.get('corporate', [])
    if isinstance(corporate, dict):
        author_list.extend(corporate.keys())
    elif isinstance(corporate, list):
        for ca in corporate:
            if isinstance(ca, dict):
                author_list.extend(ca.keys())
            else:
                author_list.append(str(ca))

    cleaned = [RE_YEAR_TRAILING.sub('', str(a)).strip(',;.- ') for a in author_list if a]
    return "; ".join([c for c in cleaned if c])


class BDTDHarvester(BaseHarvester):
    """Coletor para a BDTD (IBICT / VuFind) com sanitização e retries com backoff."""

    BASE_URLS = [
        "https://bdtd.ibict.br/vufind/api/v1/search",
        "https://oasisbr.ibict.br/vufind/api/v1/search",
    ]

    REQUEST_FIELDS = [
        "id", "title", "authors", "subjects",
        "languages", "formats", "urls", "summary", "publicationDates", "institutions"
    ]

    def __init__(self, timeout: float = 50.0):
        super().__init__(source_name="BDTD", timeout=timeout)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Cookie": "OasisbrVerify=verified_human",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    async def harvest(
        self,
        descriptors: List[str],
        on_progress: Optional[Callable[[HarvestProgress], None]] = None,
        max_records_per_descriptor: Optional[int] = None,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        limit = float("inf") if (not max_records_per_descriptor or max_records_per_descriptor <= 0) else max_records_per_descriptor
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=self.headers, verify=False) as client:
            for desc in descriptors:
                desc_query = sanitize_bdtd_keyword(desc)
                if not desc_query:
                    continue

                page = 1
                total_for_desc = 0
                page_size = 20

                while total_for_desc < limit:
                    if on_progress:
                        on_progress(
                            HarvestProgress(
                                source_name=self.source_name,
                                current_descriptor=desc.strip(),
                                page=page,
                                total_found_so_far=total_for_desc,
                            )
                        )

                    params = {
                        "lookfor": desc_query,
                        "type": "AllFields",
                        "page": page,
                        "limit": page_size,
                        "sort": "relevance",
                        "field[]": self.REQUEST_FIELDS,
                    }

                    # Retry com backoff
                    success = False
                    data = {}
                    for attempt in range(1, 4):
                        for base_url in self.BASE_URLS:
                            try:
                                res = await client.get(base_url, params=params)
                                if res.status_code == 200:
                                    data = res.json()
                                    if "records" in data or data.get("status") == "OK":
                                        success = True
                                        break
                                elif res.status_code == 429:
                                    logger.warning(f"[BDTD] Rate limit (429) no {base_url}. Aguardando pausa...")
                                    await asyncio.sleep(5.0 * attempt)
                            except Exception as e:
                                logger.warning(f"[BDTD] Tentativa {attempt} ({base_url}) falhou: {e}")
                        if success:
                            break
                        await asyncio.sleep(2.0 * attempt)

                    if not success:
                        logger.error(f"[BDTD] Não foi possível obter resposta para '{desc_query}' (pág {page}) após 3 tentativas.")
                        break

                    records = data.get("records", [])
                    if not records:
                        logger.info(f"[BDTD] Fim dos registros para '{desc_query}' na pág {page}")
                        break

                    for rec in records:
                        authors_str = extract_bdtd_authors(rec.get("authors", {}))

                        pub_dates = rec.get("publicationDates", [])
                        year_str = str(pub_dates[0]) if pub_dates else ""

                        institutions = rec.get("institutions", [])
                        inst_str = ", ".join(institutions) if isinstance(institutions, list) else str(institutions)

                        formats = rec.get("formats", [])
                        res_type = formats[0] if formats else "Tese/Dissertação"

                        record_id = rec.get("id", "")
                        detail_url = f"https://bdtd.ibict.br/vufind/Record/{record_id}" if record_id else ""

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
                            institution=inst_str or "BDTD/IBICT",
                        )

                        if paper.title:
                            yield paper
                            total_for_desc += 1
                            if total_for_desc >= limit:
                                break

                    result_count = data.get("resultCount", 0)
                    if page * page_size >= result_count or len(records) < page_size:
                        break

                    page += 1
                    await asyncio.sleep(0.5)

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
