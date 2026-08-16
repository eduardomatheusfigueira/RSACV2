#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — SciELO Harvester.
Coletor assíncrono para a base Scientific Electronic Library Online (SciELO)
utilizando raspagem resiliente de HTML (lxml), emulação de navegador, aquecimento
de sessão, retries exponenciais para tolerância a HTTP 500/503/429 e pós-filtros locais.
"""

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup, Tag
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

# Expressões regulares pré-compiladas (padrão RSAC)
RE_YEAR_ID: re.Pattern = re.compile(r"S\d{4}-\d{3,4}(\d{4})")
RE_YEAR_TEXT: re.Pattern = re.compile(r"((?:19|20)\d{2})")
RE_TOTAL_HITS: re.Pattern = re.compile(r"de\s+(\d[\d.]*)\s")
RE_DOI: re.Pattern = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)


def parse_scielo_item(item_tag: Tag, descriptor: str = "") -> RawPaperRecord:
    """Extrai e higieniza os metadados de uma tag HTML <div class='item'> do SciELO."""
    # 1. ID único
    item_id = item_tag.get("id", "")

    # 2. Título
    title_tag = item_tag.find(class_="title")
    title_str = title_tag.text.strip() if title_tag else ""
    if title_str.startswith("[SciELO Preprints] - "):
        title_str = title_str.replace("[SciELO Preprints] - ", "")

    # 3. URL do artigo
    article_url = ""
    if title_tag:
        parent_a = title_tag.parent
        if parent_a and parent_a.name == "a":
            article_url = parent_a.get("href", "")

    # 4. Autores
    authors_str = ""
    authors_div = item_tag.find(class_="authors")
    if authors_div:
        author_links = authors_div.find_all("a")
        authors_str = "; ".join(a.text.strip() for a in author_links if a.text.strip())

    # 5. Periódico / Revista (separado de Instituição)
    journal_str = ""
    source_div = item_tag.find(class_="source")
    if source_div:
        source_link = source_div.find("a")
        journal_str = source_link.text.strip() if source_link else ""

    # 6. Ano de publicação
    year_str = ""
    m = RE_YEAR_ID.search(item_id)
    if m:
        year_str = m.group(1)
    if not year_str and source_div:
        for s in source_div.stripped_strings:
            m2 = RE_YEAR_TEXT.search(s)
            if m2:
                year_str = m2.group(1)
                break

    # 7. Tipo de Pesquisa Canônico
    raw_type = "Preprint" if "preprint" in item_id.lower() else "Artigo de Periódico"
    canonical_type = to_canonical_doc_type("SciELO", raw_type)

    # 8. Resumo
    abstract_divs = item_tag.find_all(class_="abstract")
    abstract_str = ""
    for ab in abstract_divs:
        text = ab.text.strip()
        if text.lower().startswith("resumo"):
            abstract_str = text.replace("Resumo", "", 1).strip()
            break
    if not abstract_str and abstract_divs:
        abstract_str = abstract_divs[0].text.strip()

    # 9. DOI
    doi_span = item_tag.find(class_="DOIResults")
    doi_text = doi_span.text.strip() if doi_span else ""
    doi_match = RE_DOI.search(doi_text)
    doi_clean = doi_match.group(1).strip() if doi_match else (doi_text if (doi_text and "10." in doi_text) else None)

    return RawPaperRecord(
        title=title_str,
        authors=authors_str,
        year=year_str,
        abstract=abstract_str,
        doi=doi_clean,
        source_name="SciELO",
        source_id=item_id,
        download_url=article_url,
        research_type=canonical_type,
        journal=journal_str,
        institution="SciELO",
        matched_descriptor=descriptor,
    )


@register_harvester("SCIELO")
class SciELOHarvester(BaseHarvester):
    """Coletor para SciELO com scraping de HTML via BeautifulSoup/lxml e retry inteligente."""

    capabilities = HarvesterCapabilities(
        supports_year_range=False,  # Pós-filtro local
        supports_language=False,  # Pós-filtro local
        supports_document_type=False,
        supports_institution=False,
        supports_open_access=True,
        supports_boolean_query=True,
        default_page_size=15,
        max_page_size=50,
        default_delay=1.0,
    )

    SEARCH_URL = "https://search.scielo.org/"
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(self, timeout: float = 35.0):
        super().__init__(source_name="SciELO", timeout=timeout)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://search.scielo.org/",
        }

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
            page_size = query.page_size or self.capabilities.default_page_size
            year_start = query.year_start
            year_end = query.year_end
        else:
            descriptors = query
            limit = float("inf") if (not max_records_per_descriptor or max_records_per_descriptor <= 0) else max_records_per_descriptor
            page_size = self.capabilities.default_page_size
            year_start = None
            year_end = None

        total_overall = 0

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=self.headers) as client:
            # 1. Warm-up da sessão HTTP para adquirir cookies de sessão
            try:
                await client.get(self.SEARCH_URL)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"[SciELO] Aviso ao aquecer sessão: {e}")

            for desc in descriptors:
                desc_clean = desc.strip()
                if not desc_clean:
                    continue

                page = 1
                total_for_desc = 0

                while total_for_desc < limit:
                    offset = (page - 1) * page_size + 1
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

                    params: Dict[str, str] = {
                        "q": desc_clean,
                        "lang": "pt",
                        "count": str(page_size),
                        "from": str(offset),
                        "output": "site",
                    }

                    # Estratégia de retry exponencial para resiliência a oscilações do SciELO
                    res = None
                    for attempt in range(1, 6):
                        try:
                            res = await client.get(self.SEARCH_URL, params=params)
                            if res.status_code == 200:
                                break
                            elif res.status_code in self.RETRY_STATUS_CODES:
                                backoff = 1.5 ** attempt
                                logger.warning(
                                    f"[SciELO] HTTP {res.status_code} na pág {page} (tentativa {attempt}/5). "
                                    f"Aguardando {backoff:.1f}s..."
                                )
                                await asyncio.sleep(backoff)
                            else:
                                logger.warning(f"[SciELO] HTTP {res.status_code} para '{desc_clean}' na pág {page}")
                                break
                        except Exception as e:
                            backoff = 1.5 ** attempt
                            logger.warning(f"[SciELO] Erro de rede na pág {page} (tentativa {attempt}/5): {e}")
                            await asyncio.sleep(backoff)

                    if not res or res.status_code != 200:
                        logger.error(f"[SciELO] Falha definitiva para '{desc_clean}' na pág {page}")
                        break

                    soup = BeautifulSoup(res.text, "lxml")
                    items = soup.find_all(class_="item")
                    if not items:
                        logger.info(f"[SciELO] Fim dos registros para '{desc_clean}' na pág {page}")
                        break

                    # Extrair total de resultados na pág 1 (com fallback para regex)
                    if page == 1:
                        num_found = 0
                        total_hits_elem = soup.find(id="TotalHits")
                        if total_hits_elem:
                            try:
                                num_found = int(total_hits_elem.text.strip().replace(".", ""))
                            except Exception:
                                pass
                        if not num_found:
                            m = RE_TOTAL_HITS.search(soup.get_text())
                            if m:
                                try:
                                    num_found = int(m.group(1).replace(".", ""))
                                except Exception:
                                    pass
                        if num_found:
                            logger.info(f"[SciELO] Total encontrado para '{desc_clean}': {num_found}")

                    for item in items:
                        paper = parse_scielo_item(item, descriptor=desc_clean)

                        # Pós-filtro local de anos
                        if year_start or year_end:
                            try:
                                y_int = int(paper.year[:4])
                                if year_start and y_int < year_start:
                                    continue
                                if year_end and y_int > year_end:
                                    continue
                            except ValueError:
                                pass

                        if paper.title:
                            yield paper
                            total_for_desc += 1
                            total_overall += 1
                            if total_for_desc >= limit:
                                break

                    if len(items) < page_size:
                        break

                    page += 1
                    await asyncio.sleep(self.capabilities.default_delay)

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
