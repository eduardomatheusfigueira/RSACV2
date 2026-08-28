#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — SciELO Harvester (Crossref REST API).
Coletor assíncrono para o acervo da Scientific Electronic Library Online (SciELO)
através da API oficial da Crossref filtrando pelos identificadores institucionais
da SciELO (SciELO Brasil / FAPESP - member:530, SciELO Chile - member:2516,
SciELO Espanha - member:2868), com paginação por cursor, filtros nativos de data
e higienização de resumos JATS/XML.
"""

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any, Dict, List, Optional, Union
from bs4 import Tag
import httpx

from app.domain.enums import to_canonical_doc_type
from app.harvesters.base import (
    BaseHarvester,
    HarvesterCapabilities,
    HarvestProgress,
    HarvestQuery,
    HarvestSourceError,
    ProgressCallback,
    RawPaperRecord,
)
from app.harvesters.factory import register_harvester

logger = logging.getLogger(__name__)

# Expressões regulares pré-compiladas
RE_YEAR_ID: re.Pattern = re.compile(r"S\d{4}-\d{3,4}(\d{4})")
RE_YEAR_TEXT: re.Pattern = re.compile(r"((?:19|20)\d{2})")
RE_DOI: re.Pattern = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)
RE_XML_TAGS: re.Pattern = re.compile(r"<[^>]+>")


def clean_crossref_abstract(raw_abstract: str) -> str:
    """Remove tags JATS/XML (como <jats:p>, <jats:sec>) e higieniza o resumo."""
    if not raw_abstract:
        return ""
    text = re.sub(r"</jats:[^>]+>", " ", raw_abstract)
    text = re.sub(r"<jats:[^>]+>", "", text)
    text = RE_XML_TAGS.sub(" ", text)
    return " ".join(text.split()).strip()


def parse_crossref_scielo_item(item: Dict[str, Any], descriptor: str = "") -> RawPaperRecord:
    """Extrai e normaliza os metadados de uma obra retornada pela Crossref API para a SciELO."""
    # 1. Título
    titles = item.get("title") or []
    title_str = str(titles[0]).strip() if titles else ""

    # 2. Autores (formatados como Sobrenome, Nome)
    authors_list: List[str] = []
    for a in item.get("author", []):
        family = str(a.get("family", "")).strip()
        given = str(a.get("given", "")).strip()
        if family and given:
            authors_list.append(f"{family}, {given}")
        elif family or given:
            authors_list.append(family or given)
    authors_str = "; ".join(authors_list)

    # 3. Ano de Publicação
    issued = (
        (item.get("issued") or {})
        .get("date-parts", [[""]])[0]
    )
    year_str = ""
    if issued and issued[0]:
        year_str = str(issued[0]).strip()
    elif item.get("published-print"):
        parts = item["published-print"].get("date-parts", [[""]])[0]
        year_str = str(parts[0]).strip() if parts and parts[0] else ""
    elif item.get("published-online"):
        parts = item["published-online"].get("date-parts", [[""]])[0]
        year_str = str(parts[0]).strip() if parts and parts[0] else ""

    # 4. Resumo higienizado
    raw_abstract = item.get("abstract", "")
    abstract_str = clean_crossref_abstract(raw_abstract)

    # 5. DOI e URLs
    raw_doi = item.get("DOI", "")
    doi_clean = str(raw_doi).strip() if raw_doi else None

    resource_url = str(item.get("URL", "")).strip()
    if not resource_url and doi_clean:
        resource_url = f"https://doi.org/{doi_clean}"

    # 6. Periódico / Revista
    containers = item.get("container-title") or []
    journal_str = str(containers[0]).strip() if containers else ""

    # 7. Tipo de Pesquisa Canônico
    raw_type = item.get("type", "journal-article")
    canonical_type = to_canonical_doc_type("SciELO", raw_type)

    return RawPaperRecord(
        title=title_str,
        authors=authors_str,
        year=year_str,
        abstract=abstract_str,
        doi=doi_clean,
        source_name="SciELO",
        source_id=doi_clean or resource_url,
        download_url=resource_url,
        research_type=canonical_type,
        journal=journal_str,
        institution="SciELO",
        matched_descriptor=descriptor,
        extra_metadata={
            "crossref_member": item.get("member"),
            "publisher": item.get("publisher"),
        },
    )


def parse_scielo_item(item_or_tag: Union[Dict[str, Any], Tag], descriptor: str = "") -> RawPaperRecord:
    """
    Parser com retrocompatibilidade: aceita tanto payload JSON da Crossref
    quanto tags BeautifulSoup <div class='item'> de HTML legado.
    """
    if isinstance(item_or_tag, dict):
        return parse_crossref_scielo_item(item_or_tag, descriptor=descriptor)

    # Parsing legado de Tag HTML
    item_tag = item_or_tag
    item_id = item_tag.get("id", "")

    title_tag = item_tag.find(class_="title")
    title_str = title_tag.text.strip() if title_tag else ""
    if title_str.startswith("[SciELO Preprints] - "):
        title_str = title_str.replace("[SciELO Preprints] - ", "")

    article_url = ""
    if title_tag:
        parent_a = title_tag.parent
        if parent_a and parent_a.name == "a":
            article_url = parent_a.get("href", "")

    authors_str = ""
    authors_div = item_tag.find(class_="authors")
    if authors_div:
        author_links = authors_div.find_all("a")
        authors_str = "; ".join(a.text.strip() for a in author_links if a.text.strip())

    journal_str = ""
    source_div = item_tag.find(class_="source")
    if source_div:
        source_link = source_div.find("a")
        journal_str = source_link.text.strip() if source_link else ""

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

    raw_type = "Preprint" if "preprint" in item_id.lower() else "Artigo de Periódico"
    canonical_type = to_canonical_doc_type("SciELO", raw_type)

    abstract_divs = item_tag.find_all(class_="abstract")
    abstract_str = ""
    for ab in abstract_divs:
        text = ab.text.strip()
        if text.lower().startswith("resumo"):
            abstract_str = text.replace("Resumo", "", 1).strip()
            break
    if not abstract_str and abstract_divs:
        abstract_str = abstract_divs[0].text.strip()

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
    """
    Coletor para SciELO integrado à Crossref REST API oficial com filtro
    de membros institucionais da SciELO e paginação por cursor.
    """

    capabilities = HarvesterCapabilities(
        supports_year_range=True,
        supports_language=False,
        supports_document_type=True,
        supports_institution=False,
        supports_open_access=True,
        supports_boolean_query=True,
        default_page_size=50,
        max_page_size=100,
        default_delay=0.25,
    )

    BASE_URL = "https://api.crossref.org/works"
    # Membros oficiais da SciELO na Crossref:
    # 530: FapUNIFESP / SciELO Brasil (acervo principal >524k obras)
    # 2516: SciELO Chile / ANID
    # 2868: SciELO Espanha / Repisalud
    MEMBER_IDS = ["530", "2516", "2868"]

    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
    MAX_TENTATIVAS = 5

    def __init__(self, mailto: str = "rsac@ufsc.br", timeout: float = 35.0):
        super().__init__(source_name="SciELO", timeout=timeout)
        self.mailto = mailto
        self.headers = {
            "User-Agent": f"Revsist/2.0 (mailto:{self.mailto})",
            "Accept": "application/json",
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
            limit = (
                float("inf")
                if (not max_records_per_descriptor or max_records_per_descriptor <= 0)
                else max_records_per_descriptor
            )
            page_size = self.capabilities.default_page_size
            year_start = None
            year_end = None

        total_overall = 0
        descritores_consultados = 0
        descritores_com_falha: List[str] = []
        falhas: List[str] = []
        pagina_lida_com_sucesso = False

        # Montar filtro de membros SciELO
        member_filter = ",".join(f"member:{m}" for m in self.MEMBER_IDS)

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=self.headers) as client:
            for desc in descriptors:
                desc_clean = desc.strip()
                if not desc_clean:
                    continue

                descritores_consultados += 1
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

                    # Construir filtros nativos da Crossref
                    filter_parts = [member_filter]
                    if year_start:
                        filter_parts.append(f"from-pub-date:{year_start}-01-01")
                    if year_end:
                        filter_parts.append(f"until-pub-date:{year_end}-12-31")

                    params: Dict[str, Any] = {
                        "query": desc_clean,
                        "filter": ",".join(filter_parts),
                        "rows": str(min(page_size, 100)),
                        "cursor": cursor,
                    }

                    res = None
                    ultimo_erro = ""
                    for attempt in range(1, self.MAX_TENTATIVAS + 1):
                        try:
                            res = await client.get(self.BASE_URL, params=params)
                            if res.status_code == 200:
                                break
                            elif res.status_code in self.RETRY_STATUS_CODES:
                                ultimo_erro = f"HTTP {res.status_code}"
                                backoff = 1.5 ** attempt
                                logger.warning(
                                    f"[SciELO/Crossref] HTTP {res.status_code} na pág {page} "
                                    f"(tentativa {attempt}/{self.MAX_TENTATIVAS}). Aguardando {backoff:.1f}s..."
                                )
                                await asyncio.sleep(backoff)
                            else:
                                ultimo_erro = f"HTTP {res.status_code}"
                                logger.warning(f"[SciELO/Crossref] HTTP {res.status_code} para '{desc_clean}' na pág {page}")
                                break
                        except Exception as e:
                            ultimo_erro = f"{type(e).__name__}: {e}"
                            backoff = 1.5 ** attempt
                            logger.warning(
                                f"[SciELO/Crossref] Erro de rede na pág {page} "
                                f"(tentativa {attempt}/{self.MAX_TENTATIVAS}): {e}"
                            )
                            await asyncio.sleep(backoff)

                    if not res or res.status_code != 200:
                        motivo = ultimo_erro or "resposta inválida"
                        logger.error(f"[SciELO/Crossref] Falha definitiva para '{desc_clean}' na pág {page}: {motivo}")
                        descritores_com_falha.append(desc_clean)
                        falhas.append(f"'{desc_clean}' pág {page}: {motivo}")
                        break

                    try:
                        data = res.json()
                    except Exception as e:
                        logger.error(f"[SciELO/Crossref] Resposta inválida em JSON para '{desc_clean}': {e}")
                        descritores_com_falha.append(desc_clean)
                        falhas.append(f"'{desc_clean}': JSON inválido ({e})")
                        break

                    message = data.get("message", {})
                    items = message.get("items", [])
                    total_results = message.get("total-results", 0)

                    pagina_lida_com_sucesso = True

                    if page == 1:
                        logger.info(f"[SciELO/Crossref] Total encontrado para '{desc_clean}': {total_results}")

                    if not items:
                        logger.info(f"[SciELO/Crossref] Fim dos registros para '{desc_clean}' na pág {page}")
                        break

                    for item in items:
                        paper = parse_crossref_scielo_item(item, descriptor=desc_clean)

                        if paper.title:
                            yield paper
                            total_for_desc += 1
                            total_overall += 1
                            if total_for_desc >= limit:
                                break

                    # Atualizar cursor para próxima página
                    next_cursor = message.get("next-cursor")
                    if not next_cursor or next_cursor == cursor or len(items) < page_size:
                        break

                    cursor = next_cursor
                    page += 1
                    await asyncio.sleep(self.capabilities.default_delay)

            # Falha total: nenhuma página foi lida com sucesso
            if descritores_consultados and not pagina_lida_com_sucesso:
                raise HarvestSourceError(
                    self.source_name,
                    "nenhuma página de resultados pôde ser lida",
                    "; ".join(falhas[:5]) or "causa não identificada",
                )

            aviso: Optional[str] = None
            if descritores_com_falha:
                aviso = (
                    f"{len(descritores_com_falha)} de {descritores_consultados} descritores "
                    f"ficaram incompletos: {'; '.join(falhas[:3])}"
                )
                logger.warning(f"[SciELO] {aviso}")

            if on_progress:
                await on_progress(
                    HarvestProgress(
                        source_name=self.source_name,
                        current_descriptor="",
                        page=1,
                        total_found_so_far=total_overall,
                        phase="completed",
                        is_complete=True,
                        error=aviso,
                    )
                )

