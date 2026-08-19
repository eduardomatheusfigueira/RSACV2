#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Resolvedor Multi-Estratégia de PDFs (Localizador de Texto Completo).

O problema que este módulo resolve: o campo `download_url` coletado pelos
harvesters quase nunca é o link direto do arquivo PDF. É uma *landing page*
(página do DOI, registro do PubMed, página do artigo na SciELO, registro do
repositório institucional na BDTD, página do Scopus). Baixar essa URL retorna
HTML, não PDF.

A estratégia aqui é a de um bibliotecário: a partir dos identificadores
disponíveis (DOI, PMID, arXiv, URL de origem, título), gerar **candidatos** de
URL de PDF por várias vias independentes, tentar cada um em ordem de
probabilidade e validar o conteúdo recebido de fato como PDF legível.

Vias implementadas (em ordem de tentativa):
  1. `direct`        — a própria URL já aponta para um arquivo PDF.
  2. `pattern`       — padrões conhecidos por domínio (SciELO, arXiv, PMC, DSpace...).
  3. `unpaywall`     — API do Unpaywall por DOI (exige e-mail de contato).
  4. `openalex`      — localizações de acesso aberto do OpenAlex por DOI/título.
  5. `semantic`      — `openAccessPdf` do Semantic Scholar por DOI.
  6. `crossref`      — links de texto completo declarados pelo editor no Crossref.
  7. `europepmc`     — Europe PMC / PMC (cobre PubMed e boa parte da biomédica).
  8. `landing`       — raspagem da landing page (meta `citation_pdf_url`, DSpace,
                       VuFind, âncoras `.pdf` pontuadas por heurística).
  9. `doi_landing`   — resolve `https://doi.org/<doi>` e raspa a página final.

Toda tentativa é registrada em uma trilha de auditoria (`ResolutionAttempt`) que
sobe até a interface — o usuário vê o que foi tentado e por que falhou, em vez
de um "não foi possível baixar o PDF" opaco.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import quote, urljoin, urlparse

import httpx

from app.security.egress import EgressBlocked, detalhe_publico
from app.security.safe_http import get_com_guarda

logger = logging.getLogger(__name__)

# ── Constantes de rede ────────────────────────────────────────────────

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

HTML_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,es;q=0.7",
}

PDF_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# Tamanho mínimo plausível para um PDF real (evita salvar páginas de erro).
MIN_PDF_BYTES = 2048
# Teto de download por candidato (evita travar em arquivos gigantes/streams).
MAX_PDF_BYTES = 120 * 1024 * 1024

RE_DOI = re.compile(r"10\.\d{4,9}/[^\s\"'<>&]+", re.IGNORECASE)
RE_ARXIV = re.compile(r"arxiv[.:/]\s*([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", re.IGNORECASE)
RE_ARXIV_OLD = re.compile(r"arxiv\.org/(?:abs|pdf)/([a-z\-]+/[0-9]{7}(?:v[0-9]+)?)", re.IGNORECASE)
RE_PMID = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", re.IGNORECASE)
RE_PMCID = re.compile(r"(PMC\d{4,})", re.IGNORECASE)
RE_HANDLE = re.compile(r"handle/([^/?#]+)/([^/?#]+)", re.IGNORECASE)

# Trechos de URL que nunca são o PDF do trabalho.
NEGATIVE_URL_HINTS = (
    "thumbnail", "license", "licenca", "licença", "policy", "politica", "política",
    "logo", "banner", ".png", ".jpg", ".jpeg", ".gif", ".css", ".js",
    "tutorial", "guia", "manual", "template", "modelo", "capa", "ficha",
    "termo", "autorizacao", "autorização", "declaracao", "declaração",
)


# ── Estruturas de dados ───────────────────────────────────────────────

@dataclass
class PaperRef:
    """Identificadores disponíveis de um trabalho para localizar seu PDF."""

    title: str = ""
    doi: Optional[str] = None
    download_url: str = ""
    source_name: str = ""
    landing_urls: list[str] = field(default_factory=list)

    def all_landing_urls(self) -> list[str]:
        urls = []
        for url in [self.download_url, *self.landing_urls]:
            clean = (url or "").strip()
            if clean and clean not in urls:
                urls.append(clean)
        return urls


@dataclass
class PDFCandidate:
    """URL candidata a arquivo PDF, com a via que a produziu."""

    url: str
    strategy: str
    label: str
    referer: str = ""

    def __post_init__(self) -> None:
        self.url = (self.url or "").strip()


@dataclass
class ResolutionAttempt:
    """Registro auditável de uma tentativa de obtenção."""

    strategy: str
    url: str
    status: str  # ok | nao_pdf | http_erro | timeout | erro | vazio | pequeno_demais
    detail: str = ""
    http_status: Optional[int] = None

    def to_dict(self) -> dict:
        """
        Retrato da tentativa para a interface.

        No perfil `server`, `detail` e `http_status` de host desconhecido são
        reduzidos a categoria (§29.5.4): sem isso, a correção do SSRF ainda
        deixaria o atacante aprender pela mensagem de erro o que não conseguiu
        alcançar — SSRF cego vira scanner com retorno completo.
        """
        publico = detalhe_publico(self.url, self.detail)
        detalhado = publico == self.detail

        return {
            "strategy": self.strategy,
            "url": self.url,
            "status": self.status,
            "detail": publico,
            "http_status": self.http_status if detalhado else None,
        }


@dataclass
class ResolvedPDF:
    """Resultado bem-sucedido: bytes do PDF e a procedência de onde veio."""

    content: bytes
    url: str
    strategy: str
    label: str


# ── Utilidades de URL ─────────────────────────────────────────────────

def normalize_doi(raw: Optional[str]) -> Optional[str]:
    """Extrai o DOI canônico (10.xxxx/yyyy) de qualquer forma de entrada."""
    if not raw:
        return None
    match = RE_DOI.search(str(raw).strip())
    if not match:
        return None
    return match.group(0).rstrip(".,;)]}").strip()


def looks_like_pdf_url(url: str) -> bool:
    """Heurística barata: a URL aparenta apontar diretamente para um PDF?"""
    if not url:
        return False
    low = url.lower()
    if low.endswith(".pdf") or ".pdf?" in low or ".pdf#" in low:
        return True
    return any(
        token in low
        for token in ("format=pdf", "type=pdf", "/pdf/", "pdf=render", "sci_pdf", "fulltextpdf")
    )


def is_negative_url(url: str) -> bool:
    """Descarta anexos acessórios (capa, ficha catalográfica, licença, ícones)."""
    low = url.lower()
    return any(bad in low for bad in NEGATIVE_URL_HINTS)


def _domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except ValueError:
        return ""


# ── Extração de candidatos a partir de HTML ───────────────────────────

def extract_pdf_links_from_html(html: str, base_url: str) -> list[PDFCandidate]:
    """
    Encontra links de PDF em uma landing page.

    Ordem de confiança:
      1. `<meta name="citation_pdf_url">` — padrão Highwire, respeitado por
         praticamente todo editor acadêmico e pelo Google Scholar.
      2. `<link rel="alternate" type="application/pdf">`.
      3. Âncoras `<a href>` pontuadas por heurística (bitstream/download/.pdf,
         casamento com o handle do DSpace, `sequence=1`, `isAllowed=y`).
    """
    candidates: list[PDFCandidate] = []
    seen: set[str] = set()

    def add(url: str, strategy: str, label: str) -> None:
        absolute = urljoin(base_url, (url or "").strip())
        if not absolute.lower().startswith(("http://", "https://")):
            return
        if absolute in seen or is_negative_url(absolute):
            return
        seen.add(absolute)
        candidates.append(
            PDFCandidate(url=absolute, strategy=strategy, label=label, referer=base_url)
        )

    soup = None
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
    except Exception:  # pragma: no cover - lxml sempre presente em produção
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            soup = None

    if soup is None:
        # Degradação graciosa: varredura por regex quando não há parser de HTML.
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            href = match.group(1)
            if looks_like_pdf_url(href):
                add(href, "landing", "Link .pdf encontrado na página")
        return candidates

    # 1. citation_pdf_url (e variantes de metadados acadêmicos)
    for meta in soup.find_all("meta"):
        name = (meta.get("name") or meta.get("property") or "").lower()
        content = meta.get("content") or ""
        if not content:
            continue
        if name in ("citation_pdf_url", "eprints.document_url", "bepress_citation_pdf_url"):
            add(content, "landing", "Metadado citation_pdf_url da página")

    # 2. <link rel="alternate" type="application/pdf">
    for link in soup.find_all("link"):
        link_type = (link.get("type") or "").lower()
        href = link.get("href") or ""
        if href and "application/pdf" in link_type:
            add(href, "landing", "Link alternativo declarado como application/pdf")

    # 3. Âncoras pontuadas
    handle_match = RE_HANDLE.search(base_url)
    handle_id = handle_match.group(2).lower() if handle_match else ""

    scored: list[tuple[int, str, str]] = []
    for anchor in soup.find_all("a"):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        low = href.lower()
        text = " ".join(anchor.get_text(" ", strip=True).lower().split())

        is_repo_link = any(
            token in low
            for token in ("bitstream", "/retrieve/", "/download/", "/downloads/", "/fulltext")
        )
        if not (is_repo_link or looks_like_pdf_url(low)):
            # Texto do link também conta: "Baixar PDF", "Texto completo", "Full text".
            if not any(
                token in text
                for token in ("pdf", "texto completo", "full text", "baixar", "download")
            ):
                continue

        if is_negative_url(low):
            continue

        score = 0
        if low.endswith(".pdf") or ".pdf?" in low:
            score += 6
        if handle_id and handle_id in low:
            score += 10
        if "bitstream" in low:
            score += 3
        if "sequence=1" in low:
            score += 2
        if "isallowed=y" in low:
            score += 2
        if "pdf" in text:
            score += 2
        if any(token in text for token in ("texto completo", "full text")):
            score += 2
        if "?format=pdf" in low or "format=pdf" in low:
            score += 4
        scored.append((score, href, text[:60]))

    scored.sort(key=lambda item: item[0], reverse=True)
    for score, href, text in scored[:6]:
        label = f"Link da página (score {score})"
        if text:
            label += f': "{text}"'
        add(href, "landing", label)

    return candidates


# ── Padrões por domínio ───────────────────────────────────────────────

def pattern_candidates(ref: PaperRef) -> list[PDFCandidate]:
    """
    Candidatos derivados de padrões conhecidos de URL — sem custo de rede.

    São as transformações que um pesquisador faz na mão: trocar `sci_arttext`
    por `sci_pdf` na SciELO, `abs` por `pdf` no arXiv, acrescentar `?format=pdf`
    no SciELO novo, `/pdf/` no PMC.
    """
    candidates: list[PDFCandidate] = []
    seen: set[str] = set()

    def add(url: str, label: str) -> None:
        if url and url not in seen:
            seen.add(url)
            candidates.append(PDFCandidate(url=url, strategy="pattern", label=label))

    doi = normalize_doi(ref.doi)

    # arXiv — via DOI (10.48550/arXiv.NNNN) ou via URL.
    haystack = " ".join([doi or "", *ref.all_landing_urls()])
    arxiv_match = RE_ARXIV.search(haystack) or RE_ARXIV_OLD.search(haystack)
    if arxiv_match:
        arxiv_id = arxiv_match.group(1)
        add(f"https://arxiv.org/pdf/{arxiv_id}", "Padrão arXiv (abs → pdf)")

    for url in ref.all_landing_urls():
        low = url.lower()

        # SciELO clássico: script=sci_arttext → sci_pdf
        if "sci_arttext" in low:
            add(url.replace("sci_arttext", "sci_pdf"), "Padrão SciELO (sci_arttext → sci_pdf)")
        # SciELO novo (scielo.br/j/<periodico>/a/<id>/)
        if re.search(r"scielo\.[^/]+/j/[^/]+/a/", low):
            base = url.split("?")[0].rstrip("/")
            add(f"{base}/?format=pdf&lang=pt", "Padrão SciELO novo (?format=pdf)")
            add(f"{base}/?format=pdf&lang=en", "Padrão SciELO novo (?format=pdf, en)")

        # PubMed Central
        pmc_match = RE_PMCID.search(url)
        if pmc_match:
            pmcid = pmc_match.group(1).upper()
            add(
                f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/",
                "Padrão PubMed Central (/pdf/)",
            )
            add(
                f"https://europepmc.org/api/fulltextRepo?pprId={pmcid}&type=FILE&fileName=EMS.pdf",
                "Padrão Europe PMC (repositório de texto completo)",
            )

        # DSpace / repositórios institucionais com handle
        handle_match = RE_HANDLE.search(url)
        if handle_match and "/bitstream" not in low:
            root = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            handle = f"{handle_match.group(1)}/{handle_match.group(2)}"
            add(
                f"{root}/bitstream/handle/{handle}",
                "Padrão DSpace (bitstream do handle)",
            )

        # Teses USP — a versão pt-br.html expõe o link do arquivo público
        if "teses.usp.br" in low and not low.endswith("pt-br.php"):
            add(url.rstrip("/") + "/pt-br.php", "Padrão Teses USP (página do arquivo)")

        # OJS / SEER (revistas brasileiras): /article/view/ID → /article/download/ID
        if "/article/view/" in low:
            add(
                url.replace("/article/view/", "/article/download/"),
                "Padrão OJS (view → download)",
            )

    return candidates


# ── Resolvedor ────────────────────────────────────────────────────────

class PDFResolver:
    """
    Localiza e baixa o PDF de um trabalho combinando múltiplas vias.

    Uso:
        resolver = PDFResolver(contact_email="pesquisador@universidade.br")
        resolved, attempts = await resolver.acquire(ref)
    """

    def __init__(
        self,
        contact_email: str = "",
        total_timeout: float = 120.0,
        request_timeout: float = 25.0,
        max_candidates: int = 18,
    ) -> None:
        self.contact_email = (contact_email or "").strip()
        self.total_timeout = total_timeout
        self.request_timeout = request_timeout
        self.max_candidates = max_candidates

    # ── API pública ───────────────────────────────────────────────────

    async def acquire(
        self,
        ref: PaperRef,
        client: Optional[httpx.AsyncClient] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> tuple[Optional[ResolvedPDF], list[ResolutionAttempt]]:
        """
        Percorre as vias em ordem e devolve o primeiro PDF válido obtido.

        Retorna `(ResolvedPDF | None, trilha_de_tentativas)`. A trilha é sempre
        preenchida — inclusive em caso de sucesso — para exibição na interface.
        """
        attempts: list[ResolutionAttempt] = []
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.request_timeout, connect=10.0),
                # Redirecionamento é seguido manualmente por `get_com_guarda`,
                # que revalida cada salto. Com `follow_redirects=True` um host
                # público responderia `302` para 169.254.169.254 e contornaria
                # o guarda de saída inteiro (doc 29 §29.5.3).
                follow_redirects=False,
                headers=HTML_HEADERS,
            )

        tried_urls: set[str] = set()
        deadline = asyncio.get_event_loop().time() + self.total_timeout

        try:
            for producer_name, producer in self._strategy_pipeline():
                if asyncio.get_event_loop().time() >= deadline:
                    attempts.append(
                        ResolutionAttempt(
                            strategy=producer_name,
                            url="",
                            status="timeout",
                            detail="Tempo total de busca esgotado antes desta via.",
                        )
                    )
                    break

                if on_progress:
                    on_progress(producer_name)

                try:
                    candidates = await producer(ref, client)
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    attempts.append(
                        ResolutionAttempt(
                            strategy=producer_name,
                            url="",
                            status="erro",
                            detail=f"Via indisponível: {exc}",
                        )
                    )
                    continue

                for candidate in candidates:
                    if len(tried_urls) >= self.max_candidates:
                        break
                    if not candidate.url or candidate.url in tried_urls:
                        continue
                    tried_urls.add(candidate.url)

                    resolved, attempt = await self._try_candidate(candidate, client)
                    attempts.append(attempt)
                    if resolved:
                        return resolved, attempts

                    # O candidato devolveu HTML: o PDF pode estar "ali do lado".
                    if attempt.status == "nao_pdf" and attempt.detail.startswith("HTML"):
                        nested = await self._follow_html_candidate(
                            candidate, client, tried_urls
                        )
                        for nested_candidate in nested:
                            tried_urls.add(nested_candidate.url)
                            resolved, nested_attempt = await self._try_candidate(
                                nested_candidate, client
                            )
                            attempts.append(nested_attempt)
                            if resolved:
                                return resolved, attempts

            return None, attempts
        finally:
            if owns_client:
                await client.aclose()

    async def find_candidates(
        self,
        ref: PaperRef,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[PDFCandidate]:
        """Levanta candidatos de todas as vias sem baixar (modo diagnóstico)."""
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.request_timeout, connect=10.0),
                # Redirecionamento é seguido manualmente por `get_com_guarda`,
                # que revalida cada salto. Com `follow_redirects=True` um host
                # público responderia `302` para 169.254.169.254 e contornaria
                # o guarda de saída inteiro (doc 29 §29.5.3).
                follow_redirects=False,
                headers=HTML_HEADERS,
            )
        try:
            found: list[PDFCandidate] = []
            seen: set[str] = set()
            for _, producer in self._strategy_pipeline():
                try:
                    for candidate in await producer(ref, client):
                        if candidate.url and candidate.url not in seen:
                            seen.add(candidate.url)
                            found.append(candidate)
                except (httpx.HTTPError, ValueError, KeyError):
                    continue
            return found
        finally:
            if owns_client:
                await client.aclose()

    # ── Pipeline de vias ──────────────────────────────────────────────

    def _strategy_pipeline(self) -> list[tuple[str, Callable]]:
        return [
            ("direct", self._candidates_direct),
            ("pattern", self._candidates_pattern),
            ("unpaywall", self._candidates_unpaywall),
            ("openalex", self._candidates_openalex),
            ("semantic", self._candidates_semantic_scholar),
            ("crossref", self._candidates_crossref),
            ("europepmc", self._candidates_europepmc),
            ("landing", self._candidates_landing),
            ("doi_landing", self._candidates_doi_landing),
        ]

    async def _candidates_direct(
        self, ref: PaperRef, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        return [
            PDFCandidate(url=url, strategy="direct", label="URL cadastrada aponta para PDF")
            for url in ref.all_landing_urls()
            if looks_like_pdf_url(url)
        ]

    async def _candidates_pattern(
        self, ref: PaperRef, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        return pattern_candidates(ref)

    async def _candidates_unpaywall(
        self, ref: PaperRef, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        doi = normalize_doi(ref.doi)
        if not doi or not self.contact_email:
            return []

        url = f"https://api.unpaywall.org/v2/{quote(doi)}?email={quote(self.contact_email)}"
        data = await self._get_json(client, url)
        if not data:
            return []

        candidates: list[PDFCandidate] = []
        locations = []
        best = data.get("best_oa_location")
        if best:
            locations.append(best)
        locations.extend(data.get("oa_locations") or [])

        for loc in locations:
            if not isinstance(loc, dict):
                continue
            for key, label in (
                ("url_for_pdf", "Unpaywall — PDF de acesso aberto"),
                ("url", "Unpaywall — página do depósito aberto"),
            ):
                target = loc.get(key)
                if target:
                    host = loc.get("host_type") or ""
                    candidates.append(
                        PDFCandidate(
                            url=target,
                            strategy="unpaywall",
                            label=f"{label} ({host or 'repositório'})",
                        )
                    )
        return candidates

    async def _candidates_openalex(
        self, ref: PaperRef, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        doi = normalize_doi(ref.doi)
        if doi:
            url = f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='')}"
        elif ref.title and len(ref.title) > 15:
            url = (
                "https://api.openalex.org/works?filter=title.search:"
                f"{quote(ref.title[:180])}&per_page=1"
            )
        else:
            return []

        if self.contact_email:
            url += ("&" if "?" in url else "?") + f"mailto={quote(self.contact_email)}"

        data = await self._get_json(client, url)
        if not data:
            return []
        if "results" in data:
            results = data.get("results") or []
            data = results[0] if results else {}
        if not data:
            return []

        candidates: list[PDFCandidate] = []
        locations = []
        for key in ("best_oa_location", "primary_location"):
            loc = data.get(key)
            if isinstance(loc, dict):
                locations.append(loc)
        locations.extend([loc for loc in (data.get("locations") or []) if isinstance(loc, dict)])

        for loc in locations:
            source = (loc.get("source") or {}) or {}
            source_name = source.get("display_name") or "repositório"
            if loc.get("pdf_url"):
                candidates.append(
                    PDFCandidate(
                        url=loc["pdf_url"],
                        strategy="openalex",
                        label=f"OpenAlex — PDF aberto em {source_name}",
                    )
                )
            landing = loc.get("landing_page_url")
            if landing and looks_like_pdf_url(landing):
                candidates.append(
                    PDFCandidate(
                        url=landing,
                        strategy="openalex",
                        label=f"OpenAlex — landing page em formato PDF ({source_name})",
                    )
                )
        return candidates

    async def _candidates_semantic_scholar(
        self, ref: PaperRef, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        doi = normalize_doi(ref.doi)
        if not doi:
            return []
        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote(doi)}"
            "?fields=openAccessPdf,externalIds"
        )
        data = await self._get_json(client, url)
        if not data:
            return []

        candidates: list[PDFCandidate] = []
        oa_pdf = data.get("openAccessPdf") or {}
        if isinstance(oa_pdf, dict) and oa_pdf.get("url"):
            status = oa_pdf.get("status") or "aberto"
            candidates.append(
                PDFCandidate(
                    url=oa_pdf["url"],
                    strategy="semantic",
                    label=f"Semantic Scholar — PDF de acesso {status}",
                )
            )

        external = data.get("externalIds") or {}
        if isinstance(external, dict):
            if external.get("ArXiv"):
                candidates.append(
                    PDFCandidate(
                        url=f"https://arxiv.org/pdf/{external['ArXiv']}",
                        strategy="semantic",
                        label="Semantic Scholar — identificador arXiv",
                    )
                )
            if external.get("PubMedCentral"):
                pmcid = str(external["PubMedCentral"])
                if not pmcid.upper().startswith("PMC"):
                    pmcid = f"PMC{pmcid}"
                candidates.append(
                    PDFCandidate(
                        url=f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/",
                        strategy="semantic",
                        label="Semantic Scholar — identificador PubMed Central",
                    )
                )
        return candidates

    async def _candidates_crossref(
        self, ref: PaperRef, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        doi = normalize_doi(ref.doi)
        if not doi:
            return []
        url = f"https://api.crossref.org/works/{quote(doi)}"
        if self.contact_email:
            url += f"?mailto={quote(self.contact_email)}"

        data = await self._get_json(client, url)
        message = (data or {}).get("message") or {}
        links = message.get("link") or []

        candidates: list[PDFCandidate] = []
        for link in links:
            if not isinstance(link, dict):
                continue
            target = link.get("URL")
            if not target:
                continue
            content_type = (link.get("content-type") or "").lower()
            intended = (link.get("intended-application") or "").lower()
            if "pdf" in content_type or looks_like_pdf_url(target):
                candidates.append(
                    PDFCandidate(
                        url=target,
                        strategy="crossref",
                        label=f"Crossref — link do editor ({intended or 'texto completo'})",
                    )
                )
        return candidates

    async def _candidates_europepmc(
        self, ref: PaperRef, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        doi = normalize_doi(ref.doi)
        pmid = ""
        for url in ref.all_landing_urls():
            pmid_match = RE_PMID.search(url)
            if pmid_match:
                pmid = pmid_match.group(1)
                break

        if doi:
            query = f'DOI:"{doi}"'
        elif pmid:
            query = f"EXT_ID:{pmid}"
        else:
            return []

        api = (
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            f"?query={quote(query)}&format=json&resultType=core&pageSize=1"
        )
        data = await self._get_json(client, api)
        results = ((data or {}).get("resultList") or {}).get("result") or []
        if not results:
            return []
        result = results[0]

        candidates: list[PDFCandidate] = []
        full_text_urls = ((result.get("fullTextUrlList") or {}).get("fullTextUrl")) or []
        for entry in full_text_urls:
            if not isinstance(entry, dict):
                continue
            if (entry.get("documentStyle") or "").lower() == "pdf" and entry.get("url"):
                site = entry.get("site") or "Europe PMC"
                candidates.append(
                    PDFCandidate(
                        url=entry["url"],
                        strategy="europepmc",
                        label=f"Europe PMC — texto completo em {site}",
                    )
                )

        pmcid = result.get("pmcid")
        if pmcid:
            candidates.append(
                PDFCandidate(
                    url=f"https://europepmc.org/articles/{pmcid}?pdf=render",
                    strategy="europepmc",
                    label="Europe PMC — renderização em PDF",
                )
            )
            candidates.append(
                PDFCandidate(
                    url=f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/",
                    strategy="europepmc",
                    label="PubMed Central — arquivo do artigo",
                )
            )
        return candidates

    async def _candidates_landing(
        self, ref: PaperRef, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        candidates: list[PDFCandidate] = []
        for url in ref.all_landing_urls():
            if looks_like_pdf_url(url):
                continue  # já coberto pela via `direct`
            scraped = await self._scrape_landing(url, client)
            candidates.extend(scraped)
        return candidates

    async def _candidates_doi_landing(
        self, ref: PaperRef, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        doi = normalize_doi(ref.doi)
        if not doi:
            return []
        return await self._scrape_landing(f"https://doi.org/{doi}", client)

    # ── Rede ──────────────────────────────────────────────────────────

    async def _get_json(self, client: httpx.AsyncClient, url: str) -> Optional[dict]:
        """GET com tolerância a falha — APIs externas nunca derrubam a busca."""
        try:
            response = await get_com_guarda(
                client, url, headers={**HTML_HEADERS, "Accept": "application/json"}
            )
            if response.status_code != 200:
                logger.debug("[PDFResolver] %s respondeu HTTP %s", url, response.status_code)
                return None
            return response.json()
        except EgressBlocked as exc:
            logger.warning("[PDFResolver] Consulta bloqueada pelo guarda de saída: %s", exc.motivo)
            return None
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("[PDFResolver] Falha ao consultar %s: %s", url, exc)
            return None

    async def _scrape_landing(
        self, url: str, client: httpx.AsyncClient
    ) -> list[PDFCandidate]:
        """Baixa a landing page e extrai links de PDF que estejam nela."""
        try:
            response = await get_com_guarda(client, url, headers=HTML_HEADERS)
        except EgressBlocked as exc:
            logger.warning("[PDFResolver] Landing page bloqueada pelo guarda: %s", exc.motivo)
            return []
        except httpx.HTTPError as exc:
            logger.debug("[PDFResolver] Landing page inacessível (%s): %s", url, exc)
            return []

        if response.status_code != 200:
            return []

        content_type = (response.headers.get("content-type") or "").lower()
        if "application/pdf" in content_type or response.content[:5].startswith(b"%PDF"):
            return [
                PDFCandidate(
                    url=str(response.url),
                    strategy="landing",
                    label="A própria landing page devolveu um PDF",
                )
            ]
        if "html" not in content_type and content_type:
            return []

        try:
            html = response.text
        except (UnicodeDecodeError, ValueError):
            return []

        return extract_pdf_links_from_html(html, str(response.url))

    async def _follow_html_candidate(
        self,
        candidate: PDFCandidate,
        client: httpx.AsyncClient,
        tried_urls: set[str],
    ) -> list[PDFCandidate]:
        """
        Um candidato devolveu HTML em vez de PDF — comum em `?format=pdf` que
        cai numa página intermediária ou num visualizador embutido. Raspa essa
        página em busca do arquivo real, um salto apenas.
        """
        nested = await self._scrape_landing(candidate.url, client)
        result: list[PDFCandidate] = []
        for item in nested:
            if item.url in tried_urls:
                continue
            item.strategy = f"{candidate.strategy}+html"
            item.label = f"Derivado de página intermediária: {item.label}"
            result.append(item)
            if len(result) >= 3:
                break
        return result

    async def _try_candidate(
        self, candidate: PDFCandidate, client: httpx.AsyncClient
    ) -> tuple[Optional[ResolvedPDF], ResolutionAttempt]:
        """Baixa um candidato e valida se o conteúdo é mesmo um PDF legível."""
        headers = dict(PDF_HEADERS)
        if candidate.referer:
            headers["Referer"] = candidate.referer
        elif _domain(candidate.url):
            headers["Referer"] = f"https://{_domain(candidate.url)}/"

        try:
            response = await get_com_guarda(client, candidate.url, headers=headers)
        except EgressBlocked:
            # Destino interno pedido pelo usuário (ou alcançado por
            # redirecionamento). Entra na trilha como tentativa bloqueada, sem
            # revelar o que havia lá — a mensagem viraria um scanner (§29.5.4).
            return None, ResolutionAttempt(
                strategy=candidate.strategy,
                url=candidate.url,
                status="bloqueado",
                detail="Destino não elegível: endereço interno ou protocolo não permitido.",
            )
        except httpx.TimeoutException:
            return None, ResolutionAttempt(
                strategy=candidate.strategy,
                url=candidate.url,
                status="timeout",
                detail="A fonte não respondeu dentro do tempo limite.",
            )
        except httpx.HTTPError as exc:
            return None, ResolutionAttempt(
                strategy=candidate.strategy,
                url=candidate.url,
                status="erro",
                detail=f"Falha de conexão: {exc}",
            )

        if response.status_code != 200:
            hint = ""
            if response.status_code in (401, 402, 403):
                hint = " (conteúdo restrito por assinatura ou bloqueio antirrobô)"
            elif response.status_code == 404:
                hint = " (endereço inexistente)"
            return None, ResolutionAttempt(
                strategy=candidate.strategy,
                url=candidate.url,
                status="http_erro",
                detail=f"HTTP {response.status_code}{hint}",
                http_status=response.status_code,
            )

        content = response.content
        content_type = (response.headers.get("content-type") or "").lower()

        if not content:
            return None, ResolutionAttempt(
                strategy=candidate.strategy,
                url=candidate.url,
                status="vazio",
                detail="A resposta veio sem conteúdo.",
                http_status=response.status_code,
            )

        if len(content) > MAX_PDF_BYTES:
            return None, ResolutionAttempt(
                strategy=candidate.strategy,
                url=candidate.url,
                status="erro",
                detail=f"Arquivo acima do limite ({len(content) // (1024 * 1024)} MB).",
                http_status=response.status_code,
            )

        if not is_pdf_bytes(content):
            if "html" in content_type or content[:15].lstrip().lower().startswith(b"<!doctype"):
                detail = "HTML recebido no lugar do arquivo (landing page ou bloqueio)."
            else:
                detail = f"Conteúdo não é PDF (content-type: {content_type or 'desconhecido'})."
            return None, ResolutionAttempt(
                strategy=candidate.strategy,
                url=candidate.url,
                status="nao_pdf",
                detail=detail,
                http_status=response.status_code,
            )

        if len(content) < MIN_PDF_BYTES:
            return None, ResolutionAttempt(
                strategy=candidate.strategy,
                url=candidate.url,
                status="pequeno_demais",
                detail=f"PDF de apenas {len(content)} bytes — provável página de erro.",
                http_status=response.status_code,
            )

        return (
            ResolvedPDF(
                content=content,
                url=str(response.url),
                strategy=candidate.strategy,
                label=candidate.label,
            ),
            ResolutionAttempt(
                strategy=candidate.strategy,
                url=candidate.url,
                status="ok",
                detail=f"PDF válido obtido ({len(content) // 1024} KB) — {candidate.label}",
                http_status=response.status_code,
            ),
        )


def is_pdf_bytes(content: bytes) -> bool:
    """Valida a assinatura do arquivo (`%PDF`), tolerando lixo inicial."""
    if not content:
        return False
    head = content[:1024].lstrip()
    return head.startswith(b"%PDF")
