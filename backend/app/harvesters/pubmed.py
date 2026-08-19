#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — PubMed Harvester (NCBI E-utilities).
Coletor assíncrono para a base biomédica PubMed com paginação completa (retstart),
lotes de efetch de 100 PMIDs, preservação de rótulos estruturados de resumo
e controle de taxa de requisições.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any, Dict, List, Optional, Set
# `defusedxml` em vez de `xml.etree`: o ElementTree não resolve entidades
# externas (não há XXE aqui), mas continua sujeito a expansão de entidades
# aninhadas. A origem é o NCBI sobre TLS, então o risco real é baixo — a troca
# custa uma linha e fecha a categoria (doc 29 §29.10).
import defusedxml.ElementTree as ET
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


@register_harvester("PUBMED")
class PubMedHarvester(BaseHarvester):
    """Coletor para PubMed via NCBI E-utilities com paginação e suporte a lotes."""

    capabilities = HarvesterCapabilities(
        supports_year_range=True,
        supports_language=True,
        supports_document_type=True,
        supports_institution=False,
        supports_open_access=True,
        supports_boolean_query=True,
        requires_api_key=False,
        default_page_size=100,
        max_page_size=100,
        default_delay=0.35,
    )

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 35.0):
        super().__init__(source_name="PubMed", timeout=timeout)
        self.api_key = api_key

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
            year_start = query.year_start
            year_end = query.year_end
            languages = query.languages
        else:
            descriptors = query
            limit = float("inf") if (not max_records_per_descriptor or max_records_per_descriptor <= 0) else max_records_per_descriptor
            year_start = None
            year_end = None
            languages = []

        delay = 0.12 if self.api_key else 0.38  # 10 req/s com chave vs 3 req/s sem chave
        seen_pmids: Set[str] = set()
        total_overall = 0

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for desc in descriptors:
                desc_clean = desc.strip()
                if not desc_clean:
                    continue

                total_for_desc = 0
                retstart = 0
                retmax = 10000 if limit == float("inf") else min(int(limit), 10000)

                # Construir termo com filtros nativos do PubMed
                term_parts = [f"({desc_clean})"]
                if year_start or year_end:
                    y_start = year_start or 1900
                    y_end = year_end or 2099
                    term_parts.append(f'("{y_start}"[Date - Publication] : "{y_end}"[Date - Publication])')
                for lang in languages:
                    term_parts.append(f'"{lang}"[Language]')

                full_term = " AND ".join(term_parts)

                if on_progress:
                    await on_progress(
                        HarvestProgress(
                            source_name=self.source_name,
                            current_descriptor=desc_clean,
                            page=1,
                            total_found_so_far=total_overall,
                            phase="harvesting",
                        )
                    )

                try:
                    # 1. ESearch para obter lista de PMIDs
                    search_params: Dict[str, Any] = {
                        "db": "pubmed",
                        "term": full_term,
                        "retmode": "json",
                        "retmax": retmax,
                        "retstart": retstart,
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

                    # 2. EFetch em lotes de 100 PMIDs
                    chunk_size = 100
                    for i in range(0, len(id_list), chunk_size):
                        chunk_ids = [pid for pid in id_list[i : i + chunk_size] if pid not in seen_pmids]
                        if not chunk_ids:
                            continue

                        for pid in chunk_ids:
                            seen_pmids.add(pid)

                        fetch_params = {
                            "db": "pubmed",
                            "id": ",".join(chunk_ids),
                            "retmode": "xml",
                        }
                        if self.api_key:
                            fetch_params["api_key"] = self.api_key

                        fetch_res = await client.get(self.EFETCH_URL, params=fetch_params)
                        if fetch_res.status_code != 200:
                            logger.warning(f"[PubMed] EFetch HTTP {fetch_res.status_code}")
                            continue

                        # Parse XML com preservação de rótulos estruturados
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

                            # Título
                            title_elem = art_elem.find("ArticleTitle")
                            title_str = "".join(title_elem.itertext()).strip() if title_elem is not None else ""

                            # Resumo com rótulos preservados (ex: BACKGROUND, METHODS)
                            abstract_elem = art_elem.find("Abstract")
                            abstract_parts = []
                            if abstract_elem is not None:
                                for text_el in abstract_elem.findall("AbstractText"):
                                    label = text_el.get("Label")
                                    text_content = "".join(text_el.itertext()).strip()
                                    if text_content:
                                        if label:
                                            abstract_parts.append(f"{label}: {text_content}")
                                        else:
                                            abstract_parts.append(text_content)
                            abstract_str = " ".join(abstract_parts).strip()

                            # Autores
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

                            # Periódico / Journal
                            journal_elem = art_elem.find(".//Journal/Title")
                            journal_name = journal_elem.text.strip() if (journal_elem is not None and journal_elem.text) else ""

                            # Ano
                            year_elem = art_elem.find(".//Journal/JournalIssue/PubDate/Year")
                            year_str = year_elem.text if (year_elem is not None and year_elem.text) else ""

                            # DOI
                            doi: Optional[str] = None
                            for id_elem in article.findall(".//ArticleIdList/ArticleId"):
                                if id_elem.get("IdType") == "doi" and id_elem.text:
                                    doi = id_elem.text.strip()
                                    break

                            # Tipo de Publicação
                            pub_types = []
                            for pt in art_elem.findall(".//PublicationTypeList/PublicationType"):
                                if pt.text:
                                    pub_types.append(pt.text.strip())
                            raw_type = pub_types[0] if pub_types else "Journal Article"
                            canonical_type = to_canonical_doc_type(self.source_name, raw_type)

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
                                research_type=canonical_type,
                                journal=journal_name,
                                institution="PubMed/NCBI",
                                matched_descriptor=desc_clean,
                            )

                            if paper.title:
                                yield paper
                                total_for_desc += 1
                                total_overall += 1
                                if total_for_desc >= limit:
                                    break

                        await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"[PubMed] Erro ao processar '{desc_clean}': {e}")
                    continue

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
