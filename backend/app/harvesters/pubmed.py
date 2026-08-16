#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — PubMed Harvester (NCBI E-utilities).
Coletor assíncrono para a base biomédica PubMed.
"""

import asyncio
import logging
from typing import AsyncGenerator, Callable, List, Optional
import xml.etree.ElementTree as ET
import httpx

from app.harvesters.base import BaseHarvester, HarvestProgress, RawPaperRecord

logger = logging.getLogger(__name__)


class PubMedHarvester(BaseHarvester):
    """Coletor para PubMed via NCBI E-utilities."""

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 35.0):
        super().__init__(source_name="PubMed", timeout=timeout)
        self.api_key = api_key

    async def harvest(
        self,
        descriptors: List[str],
        on_progress: Optional[Callable[[HarvestProgress], None]] = None,
        max_records_per_descriptor: Optional[int] = None,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        limit = float("inf") if (not max_records_per_descriptor or max_records_per_descriptor <= 0) else max_records_per_descriptor
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for desc in descriptors:
                desc_clean = desc.strip()
                if not desc_clean:
                    continue

                total_for_desc = 0
                retmax = 500 if limit == float("inf") else min(int(limit), 500)

                if on_progress:
                    on_progress(
                        HarvestProgress(
                            source_name=self.source_name,
                            current_descriptor=desc_clean,
                            page=1,
                            total_found_so_far=0,
                        )
                    )

                try:
                    # 1. ESearch para obter PMIDs
                    search_params = {
                        "db": "pubmed",
                        "term": desc_clean,
                        "retmode": "json",
                        "retmax": retmax,
                        "sort": "pub_date",
                    }
                    if self.api_key:
                        search_params["api_key"] = self.api_key

                    search_res = await client.get(self.ESEARCH_URL, params=search_params)
                    if search_res.status_code != 200:
                        logger.warning(f"[PubMed] ESearch HTTP {search_res.status_code} para '{desc_clean}'")
                        continue

                    search_data = search_res.json()
                    id_list = search_data.get("esearchresult", {}).get("idlist", [])
                    if not id_list:
                        continue

                    # 2. EFetch em lotes de 25 PMIDs
                    chunk_size = 25
                    for i in range(0, len(id_list), chunk_size):
                        chunk_ids = id_list[i : i + chunk_size]
                        fetch_params = {
                            "db": "pubmed",
                            "id": ",".join(chunk_ids),
                            "retmode": "xml",
                        }
                        if self.api_key:
                            fetch_params["api_key"] = self.api_key

                        fetch_res = await client.get(self.EFETCH_URL, params=fetch_params)
                        if fetch_res.status_code != 200:
                            continue

                        # Parse XML
                        root = ET.fromstring(fetch_res.text)
                        for article in root.findall(".//PubmedArticle"):
                            medline = article.find("MedlineCitation")
                            if medline is None:
                                continue

                            pmid_elem = medline.find("PMID")
                            pmid = pmid_elem.text if pmid_elem is not None else ""

                            art_elem = medline.find("Article")
                            if art_elem is None:
                                continue

                            # Title
                            title_elem = art_elem.find("ArticleTitle")
                            title_str = "".join(title_elem.itertext()).strip() if title_elem is not None else ""

                            # Abstract
                            abstract_elem = art_elem.find("Abstract")
                            abstract_str = ""
                            if abstract_elem is not None:
                                parts = [
                                    "".join(t.itertext())
                                    for t in abstract_elem.findall("AbstractText")
                                ]
                                abstract_str = " ".join(parts).strip()

                            # Authors
                            author_list_elem = art_elem.find("AuthorList")
                            authors = []
                            if author_list_elem is not None:
                                for a in author_list_elem.findall("Author"):
                                    last_name = a.find("LastName")
                                    fore_name = a.find("ForeName")
                                    if last_name is not None and last_name.text:
                                        name = last_name.text
                                        if fore_name is not None and fore_name.text:
                                            name += f", {fore_name.text}"
                                        authors.append(name)
                            authors_str = "; ".join(authors)

                            # Year
                            year_elem = art_elem.find(".//Journal/JournalIssue/PubDate/Year")
                            year_str = year_elem.text if year_elem is not None and year_elem.text else ""

                            # DOI
                            doi = None
                            for id_elem in article.findall(".//ArticleIdList/ArticleId"):
                                if id_elem.get("IdType") == "doi" and id_elem.text:
                                    doi = id_elem.text.strip()
                                    break

                            dl_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

                            paper = RawPaperRecord(
                                title=title_str,
                                authors=authors_str,
                                year=year_str,
                                abstract=abstract_str,
                                doi=doi,
                                source_name=self.source_name,
                                source_id=pmid,
                                download_url=dl_url,
                                research_type="Artigo Biomédico (PubMed)",
                                institution="PubMed/NCBI",
                            )

                            if paper.title:
                                yield paper
                                total_for_desc += 1

                        await asyncio.sleep(0.4)

                except Exception as e:
                    logger.error(f"[PubMed] Erro na requisição para '{desc_clean}': {e}")
                    continue

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
