#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — BDTD Harvester (Biblioteca Digital Brasileira de Teses e Dissertações).
Interface assíncrona com o motor VuFind da BDTD via API de busca / Search Record,
com sanitização de descritores, respeito estrito à regra do WAF (máx. 2 filtros de API),
pós-filtragem local de idiomas, raspagem de detalhes (orientador, instituição de defesa),
ordenação determinística por ano e retries resilientes.
"""

import asyncio
import logging
import re
import unicodedata
from collections.abc import AsyncGenerator
from typing import Any, Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup
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

# Expressões regulares pré-compiladas
RE_PARTS_SPLIT: re.Pattern = re.compile(r"[;\n]+")
RE_YEAR_TRAILING: re.Pattern = re.compile(r"(?:,\s*|\s*)\d{4}(?:\s*-\s*\d{0,4})?$", re.IGNORECASE)
RE_ORIENTADOR_LABEL: re.Pattern = re.compile(
    r"^(?:orientador|orientadora|orientadores|orientador\(a\))\s*:\s*(.+)$", re.IGNORECASE
)
RE_DOI: re.Pattern = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)

# Limite máximo de filtros no WAF da BDTD antes de retornar 429
BDTD_MAX_API_FILTERS: int = 2


def sanitize_bdtd_keyword(keyword: str) -> str:
    """Limpa o descritor para o motor VuFind/Solr da BDTD (remove aspas e acentos)."""
    clean = keyword.replace('"', "").replace("'", "").strip()
    clean = unicodedata.normalize("NFKD", clean).encode("ASCII", "ignore").decode("utf-8")
    return clean.strip()


def sanitize_bdtd_filters(raw_filters: Optional[List[str]]) -> Tuple[List[str], Set[str]]:
    """
    Separa filtros para a API da BDTD respeitando a regra do WAF:
      - api_filters: no máximo 2 filtros enviados na query Solr
      - allowed_languages: códigos de idioma separados para pós-filtragem local
    """
    api_filters: List[str] = []
    allowed_languages: Set[str] = set()

    for f in raw_filters or []:
        if not f or not isinstance(f, str):
            continue
        f_str = f.strip()
        if not f_str:
            continue

        stripped = f_str.lstrip("~")
        if stripped.startswith("language:") or stripped.startswith("idioma:"):
            lang_code = stripped.split(":", 1)[1].strip().strip('"\'').lower()
            if lang_code:
                # Mapeamento para ISO 639-1 / VuFind
                if lang_code in ("por", "pt", "portugues", "português"):
                    allowed_languages.add("por")
                    allowed_languages.add("pt")
                elif lang_code in ("eng", "en", "ingles", "inglês"):
                    allowed_languages.add("eng")
                    allowed_languages.add("en")
                elif lang_code in ("spa", "es", "espanhol"):
                    allowed_languages.add("spa")
                    allowed_languages.add("es")
                else:
                    allowed_languages.add(lang_code)
        elif ":" in f_str:
            field_name, val = f_str.split(":", 1)
            if field_name.strip() and val.strip():
                api_filters.append(f_str)

    if len(api_filters) > BDTD_MAX_API_FILTERS:
        dropped = api_filters[BDTD_MAX_API_FILTERS:]
        api_filters = api_filters[:BDTD_MAX_API_FILTERS]
        logger.warning(
            f"[BDTD] Limite WAF atingido ({len(api_filters) + len(dropped)} filtros). "
            f"Mantendo primeiros {BDTD_MAX_API_FILTERS}: {api_filters}. Descartados da API: {dropped}"
        )

    return api_filters, allowed_languages


def clean_creator_name(creator_str: Optional[str]) -> str:
    """Remove anos de nascimento/falecimento no final do nome dos autores."""
    if not creator_str:
        return ""
    parts = RE_PARTS_SPLIT.split(creator_str)
    cleaned_parts = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        part = RE_YEAR_TRAILING.sub("", part).strip(",;-\t\n ")
        if part:
            cleaned_parts.append(part)
    return "; ".join(cleaned_parts)


def clean_advisor_name(advisor_str: Optional[str]) -> str:
    """Limpa nome do orientador removendo links Lattes/ORCID e ruídos institucionais."""
    if not advisor_str or advisor_str.lower() in ("não informado", "nao informado", "none"):
        return ""

    parts = RE_PARTS_SPLIT.split(advisor_str)
    cleaned_parts = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Descartar links
        if part.startswith("http://") or part.startswith("https://") or "lattes.cnpq.br" in part or "orcid.org" in part:
            continue

        # Descartar nomes de instituição vazados no campo de orientador
        lower_part = part.lower()
        if any(w in lower_part for w in ("universidade", "faculdade", "instituto", "departamento", "programa de", "campus")):
            continue

        part = RE_YEAR_TRAILING.sub("", part).strip(",;.- ")
        if part:
            cleaned_parts.append(part)

    return "; ".join(cleaned_parts)


def process_record_fields(description: str, advisor: str) -> Tuple[str, str]:
    """Corrige trocas de resumo com nome de orientador vindas de repositórios legados."""
    cleaned_advisor = clean_advisor_name(advisor)
    desc_clean = description.strip() if description else ""
    extracted_advisor: Optional[str] = None

    match = RE_ORIENTADOR_LABEL.match(desc_clean)
    if match:
        extracted_advisor = match.group(1).strip()
        desc_clean = ""
    elif desc_clean.lower().startswith("orientador") and len(desc_clean) < 150:
        extracted_advisor = desc_clean
        desc_clean = ""

    if extracted_advisor and (not cleaned_advisor or len(cleaned_advisor) < len(extracted_advisor)):
        cleaned_advisor = clean_advisor_name(extracted_advisor)

    return desc_clean, cleaned_advisor


def get_source_info(details: Dict[str, str]) -> str:
    """Identifica a instituição de defesa / editora / fonte a partir dos metadados detalhados."""
    institution = (
        details.get("instname_str")
        or details.get("Instituição de defesa:")
        or details.get("Instituição:")
        or details.get("institution")
    )
    publisher = (
        details.get("publisher.none.fl_str_mv")
        or details.get("dc.publisher.none.fl_str_mv")
        or details.get("Editora:")
    )
    source = (
        details.get("reponame_str")
        or details.get("dc.source.none.fl_str_mv")
        or details.get("Fonte:")
        or details.get("container_title")
    )
    return institution or source or publisher or ""


def extract_bdtd_authors(authors_dict: Any) -> str:
    """Extrai e consolida autores primários, secundários e corporativos."""
    if not authors_dict:
        return ""

    if isinstance(authors_dict, list):
        return clean_creator_name("; ".join(str(a) for a in authors_dict if a))

    if not isinstance(authors_dict, dict):
        return clean_creator_name(str(authors_dict))

    author_list: List[str] = []
    primary = authors_dict.get("primary", {})
    if isinstance(primary, dict):
        author_list.extend(primary.keys())
    elif isinstance(primary, list):
        author_list.extend(primary)

    secondary = authors_dict.get("secondary", [])
    if isinstance(secondary, dict):
        author_list.extend(secondary.keys())
    elif isinstance(secondary, list):
        for sa in secondary:
            if isinstance(sa, dict):
                author_list.extend(sa.keys())
            else:
                author_list.append(str(sa))

    corporate = authors_dict.get("corporate", [])
    if isinstance(corporate, dict):
        author_list.extend(corporate.keys())
    elif isinstance(corporate, list):
        for ca in corporate:
            if isinstance(ca, dict):
                author_list.extend(ca.keys())
            else:
                author_list.append(str(ca))

    cleaned = [RE_YEAR_TRAILING.sub("", str(a)).strip(",;.- ") for a in author_list if a]
    return "; ".join([c for c in cleaned if c])


@register_harvester("BDTD")
class BDTDHarvester(BaseHarvester):
    """Coletor para a BDTD (IBICT / VuFind) com paginação, paridade V1 e raspagem de detalhes."""

    capabilities = HarvesterCapabilities(
        supports_year_range=True,
        supports_language=True,
        supports_document_type=True,
        supports_institution=True,
        supports_open_access=False,
        supports_boolean_query=True,
        max_native_filters=2,
        requires_api_key=False,
        default_page_size=100,
        max_page_size=100,
        default_delay=0.5,
    )

    BASE_URLS = [
        "https://bdtd.ibict.br/vufind/api/v1/search",
        "https://oasisbr.ibict.br/vufind/api/v1/search",
    ]

    REQUEST_FIELDS = [
        "id",
        "title",
        "authors",
        "subjects",
        "languages",
        "formats",
        "urls",
        "summary",
        "publicationDates",
        "institutions",
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
        self._scrape_semaphore = asyncio.Semaphore(4)

    async def _scrape_record_details(self, client: httpx.AsyncClient, record_id: str) -> Dict[str, str]:
        """Raspagem assíncrona da página pública do VuFind para obter orientador e metadados Dublin Core."""
        url = f"https://bdtd.ibict.br/vufind/Record/{record_id}"
        details: Dict[str, str] = {}
        try:
            async with self._scrape_semaphore:
                res = await client.get(url, headers=self.headers, timeout=20.0)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "lxml")
                    for meta in soup.find_all("meta"):
                        name = meta.attrs.get("name")
                        content = meta.attrs.get("content")
                        if name and content:
                            details[name] = content

                    for row in soup.find_all("tr"):
                        th = row.find("th")
                        td = row.find("td")
                        if th and td:
                            key = th.text.strip()
                            val = td.text.strip()
                            lines = [l.strip() for l in val.split("\n") if l.strip()]
                            details[key] = "; ".join(lines) if len(lines) > 1 else (lines[0] if lines else "")
        except Exception as e:
            logger.debug(f"[BDTD] Scraping de detalhes do registro {record_id} falhou: {e}")
        return details

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
            fetch_details = query.fetch_details
            year_start = query.year_start
            year_end = query.year_end
            languages = query.languages
        else:
            descriptors = query
            limit = float("inf") if (not max_records_per_descriptor or max_records_per_descriptor <= 0) else max_records_per_descriptor
            page_size = self.capabilities.default_page_size
            fetch_details = True
            year_start = None
            year_end = None
            languages = []

        seen_record_ids: Set[str] = set()
        total_overall = 0

        # Montar filtros nativos Solr e pós-filtros locais
        raw_filter_list = []
        if year_start or year_end:
            y_start = year_start or 1900
            y_end = year_end or 2099
            raw_filter_list.append(f'publishDate:"[{y_start} TO {y_end}]"')
        for lang in languages:
            raw_filter_list.append(f"language:{lang}")

        api_filters, allowed_langs = sanitize_bdtd_filters(raw_filter_list)

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, headers=self.headers) as client:
            for desc in descriptors:
                desc_query = sanitize_bdtd_keyword(desc)
                if not desc_query:
                    continue

                page = 1
                total_for_desc = 0

                while total_for_desc < limit:
                    if on_progress:
                        await on_progress(
                            HarvestProgress(
                                source_name=self.source_name,
                                current_descriptor=desc.strip(),
                                page=page,
                                total_found_so_far=total_overall,
                                phase="harvesting",
                            )
                        )

                    params: Dict[str, Any] = {
                        "lookfor": desc_query,
                        "type": "AllFields",
                        "page": page,
                        "limit": page_size,
                        "sort": "year",  # Determinismo para reprodutibilidade científica
                        "field[]": self.REQUEST_FIELDS,
                    }
                    if api_filters:
                        params["filter[]"] = api_filters

                    success = False
                    data: Dict[str, Any] = {}

                    # Retries com espelhos e backoff
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
                                    logger.warning(f"[BDTD] Rate limit (429) em {base_url}. Aguardando 15s...")
                                    await asyncio.sleep(15.0)
                                else:
                                    logger.warning(f"[BDTD] HTTP {res.status_code} em {base_url} (tentativa {attempt})")
                            except Exception as e:
                                logger.warning(f"[BDTD] Tentativa {attempt} ({base_url}) falhou: {e}")

                        if success:
                            break
                        await asyncio.sleep(2.0 * attempt)

                    if not success:
                        logger.error(f"[BDTD] Falha ao consultar '{desc_query}' (pág {page}) após retries.")
                        break

                    records = data.get("records", [])
                    if not records:
                        logger.info(f"[BDTD] Fim dos registros para '{desc_query}' na pág {page}")
                        break

                    for rec in records:
                        record_id = rec.get("id", "")
                        if record_id and record_id in seen_record_ids:
                            continue
                        if record_id:
                            seen_record_ids.add(record_id)

                        # Pós-filtro local de idiomas
                        rec_langs = rec.get("languages", [])
                        if allowed_langs and rec_langs:
                            if not any(str(l).strip().lower() in allowed_langs for l in rec_langs):
                                continue

                        # Resumo: tratar listas VuFind com join seguro (P0-5)
                        summaries = rec.get("summary", [])
                        if isinstance(summaries, list):
                            abstract_str = " ".join([str(s).strip() for s in summaries if s]).strip()
                        else:
                            abstract_str = str(summaries or rec.get("description", "") or "").strip()

                        authors_str = extract_bdtd_authors(rec.get("authors", {}))

                        pub_dates = rec.get("publicationDates", [])
                        year_str = str(pub_dates[0]) if pub_dates else ""

                        # Pós-filtro local de anos se necessário
                        if year_start or year_end:
                            try:
                                y_int = int(year_str[:4])
                                if year_start and y_int < year_start:
                                    continue
                                if year_end and y_int > year_end:
                                    continue
                            except ValueError:
                                pass

                        institutions = rec.get("institutions", [])
                        inst_str = ", ".join(institutions) if isinstance(institutions, list) else str(institutions or "")

                        formats = rec.get("formats", [])
                        raw_format = formats[0] if formats else "Tese/Dissertação"
                        canonical_type = to_canonical_doc_type(self.source_name, raw_format)

                        detail_url = f"https://bdtd.ibict.br/vufind/Record/{record_id}" if record_id else ""
                        urls = rec.get("urls", [])
                        dl_url = urls[0].get("url", "") if urls and isinstance(urls[0], dict) else detail_url

                        doi: Optional[str] = None
                        for u in urls:
                            url_val = u.get("url", "") if isinstance(u, dict) else ""
                            if "doi.org" in url_val:
                                doi_match = RE_DOI.search(url_val)
                                if doi_match:
                                    doi = doi_match.group(1).strip()
                                    break

                        advisor_str = ""

                        # Enriquecimento opcional via raspagem de detalhes (Fase 5 / P1-1)
                        if fetch_details and record_id:
                            details = await self._scrape_record_details(client, record_id)
                            if details:
                                advisor_candidate = (
                                    details.get("dc.contributor.advisor")
                                    or details.get("Orientador(a):")
                                    or details.get("Orientador:")
                                    or details.get("advisor")
                                    or ""
                                )
                                detailed_inst = get_source_info(details)
                                if detailed_inst:
                                    inst_str = detailed_inst

                                # Correção de troca resumo <-> orientador
                                abstract_str, advisor_str = process_record_fields(abstract_str, advisor_candidate)

                        paper = RawPaperRecord(
                            title=rec.get("title", "").strip(),
                            authors=authors_str,
                            advisor=advisor_str,
                            year=year_str,
                            abstract=abstract_str,
                            doi=doi,
                            source_name=self.source_name,
                            source_id=record_id,
                            download_url=dl_url,
                            research_type=canonical_type,
                            institution=inst_str or "BDTD/IBICT",
                            matched_descriptor=desc.strip(),
                        )

                        if paper.title:
                            yield paper
                            total_for_desc += 1
                            total_overall += 1
                            if total_for_desc >= limit:
                                break

                    result_count = data.get("resultCount", 0)
                    if page * page_size >= result_count or len(records) < page_size:
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
