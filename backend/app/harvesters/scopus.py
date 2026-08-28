#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Scopus Harvester (Elsevier API).
Coletor assíncrono para a base multidisciplinar Scopus via Elsevier Developer API,
com suporte a view=COMPLETE, fallback inteligente via Abstract Retrieval API
para extração de resumos, autenticação por API Key e Institutional Token (insttoken).
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


@register_harvester("SCOPUS")
class ScopusHarvester(BaseHarvester):
    """Coletor para Scopus Search & Abstract Retrieval API."""

    capabilities = HarvesterCapabilities(
        supports_year_range=True,
        supports_language=False,
        supports_document_type=True,
        supports_institution=False,
        supports_open_access=False,
        supports_boolean_query=True,
        requires_api_key=True,
        default_page_size=25,
        max_page_size=100,
        default_delay=0.5,
    )

    SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
    ABSTRACT_URL = "https://api.elsevier.com/content/abstract/scopus_id/"

    def __init__(
        self,
        api_key: Optional[str] = None,
        inst_token: Optional[str] = None,
        timeout: float = 35.0,
    ):
        super().__init__(source_name="Scopus", timeout=timeout)
        self.api_key = api_key
        self.inst_token = inst_token
        self._abstract_semaphore = asyncio.Semaphore(3)

    async def _fetch_abstract_retrieval(
        self,
        client: httpx.AsyncClient,
        scopus_id: str,
        headers: Dict[str, str],
    ) -> str:
        """Consulta a Abstract Retrieval API como fallback para obter o resumo quando view=STANDARD."""
        if not scopus_id:
            return ""
        clean_id = scopus_id.replace("SCOPUS_ID:", "").strip()
        url = f"{self.ABSTRACT_URL}{clean_id}"
        params = {"view": "META_ABS"}

        try:
            async with self._abstract_semaphore:
                res = await client.get(url, params=params, headers=headers, timeout=20.0)
                if res.status_code == 200:
                    data = res.json()
                    ret_response = data.get("abstracts-retrieval-response", {})
                    coredata = ret_response.get("coredata", {})
                    desc = coredata.get("dc:description")
                    if desc:
                        if isinstance(desc, dict):
                            desc = desc.get("$", "")
                        return str(desc).strip()
        except Exception as e:
            logger.debug(f"[Scopus] Fallback de Abstract Retrieval para {clean_id} falhou: {e}")
        return ""

    async def harvest(
        self,
        query: HarvestQuery | List[str],
        on_progress: Optional[ProgressCallback] = None,
        max_records_per_descriptor: Optional[int] = None,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        if not self.api_key:
            msg = "Scopus requer chave de API da Elsevier (API Key). Configure em Configurações > Bases de Dados."
            logger.error(f"[Scopus] {msg}")
            raise ValueError(msg)

        # Normalizar HarvestQuery
        if isinstance(query, HarvestQuery):
            descriptors = query.descriptors
            limit = query.max_records_per_descriptor or float("inf")
            count_per_page = query.page_size or self.capabilities.default_page_size
            fetch_details = query.fetch_details
            year_start = query.year_start
            year_end = query.year_end
        else:
            descriptors = query
            limit = float("inf") if (not max_records_per_descriptor or max_records_per_descriptor <= 0) else max_records_per_descriptor
            count_per_page = self.capabilities.default_page_size
            fetch_details = True
            year_start = None
            year_end = None

        headers = {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json",
        }
        if self.inst_token:
            headers["X-ELS-Insttoken"] = self.inst_token

        total_overall = 0

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for desc in descriptors:
                desc_clean = desc.strip()
                if not desc_clean:
                    continue

                page = 1
                total_for_desc = 0

                while total_for_desc < limit:
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

                    # Montar query do Scopus
                    scopus_query = f"TITLE-ABS-KEY({desc_clean})"
                    if year_start and year_end and year_start == year_end:
                        scopus_query += f" AND PUBYEAR = {year_start}"
                    elif year_start or year_end:
                        y_start = year_start or 1900
                        y_end = year_end or 2099
                        scopus_query += f" AND PUBYEAR AFT {y_start - 1} AND PUBYEAR BEF {y_end + 1}"

                    params: Dict[str, Any] = {
                        "query": scopus_query,
                        "count": count_per_page,
                        "start": (page - 1) * count_per_page,
                        "view": "COMPLETE",
                    }

                    try:
                        res = await client.get(self.SEARCH_URL, params=params, headers=headers)
                        # Se view=COMPLETE não for autorizada pelo plano da chave, tenta STANDARD
                        if res.status_code == 403 and params.get("view") == "COMPLETE":
                            params["view"] = "STANDARD"
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
                            title = entry.get("dc:title", "").strip()
                            authors = entry.get("dc:creator", "")
                            year_val = entry.get("prism:coverDate", "")
                            year = year_val[:4] if year_val else ""
                            doi = entry.get("prism:doi")
                            scopus_id = entry.get("dc:identifier", "")
                            raw_doc_type = entry.get("subtypeDescription") or entry.get("subtype", "Article")
                            canonical_type = to_canonical_doc_type(self.source_name, raw_doc_type)
                            pub_name = entry.get("prism:publicationName", "")

                            # Tentar extrair resumo do retorno direto
                            abstract = entry.get("dc:description", "")
                            if isinstance(abstract, dict):
                                abstract = abstract.get("$", "")
                            abstract = str(abstract).strip()

                            # Se resumo não veio e fetch_details ativo, chamar Abstract Retrieval API
                            if not abstract and fetch_details and scopus_id:
                                abstract = await self._fetch_abstract_retrieval(client, scopus_id, headers)

                            scopus_url = ""
                            for link in entry.get("link", []):
                                if link.get("@ref") == "scopus":
                                    scopus_url = link.get("@href", "")
                                    break

                            paper = RawPaperRecord(
                                title=title,
                                authors=authors,
                                year=year,
                                abstract=abstract,
                                doi=doi,
                                source_name=self.source_name,
                                source_id=scopus_id,
                                download_url=scopus_url,
                                research_type=canonical_type,
                                journal=pub_name,
                                institution="Scopus/Elsevier",
                                matched_descriptor=desc_clean,
                            )

                            if paper.title:
                                yield paper
                                total_for_desc += 1
                                total_overall += 1
                                if total_for_desc >= limit:
                                    break

                        total_results = int(search_results.get("opensearch:totalResults", 0))
                        if page * count_per_page >= total_results or len(entries) < count_per_page:
                            break

                        page += 1
                        await asyncio.sleep(self.capabilities.default_delay)

                    except Exception as e:
                        logger.error(f"[Scopus] Erro ao processar '{desc_clean}': {e}")
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
