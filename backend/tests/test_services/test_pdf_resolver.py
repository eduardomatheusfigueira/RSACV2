#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes do resolvedor multi-estratégia de PDFs."""

import httpx
import pytest

from app.services.pdf_resolver import (
    PaperRef,
    PDFResolver,
    extract_pdf_links_from_html,
    is_pdf_bytes,
    looks_like_pdf_url,
    normalize_doi,
    pattern_candidates,
)

MIN_PDF = b"%PDF-1.7\n" + b"0" * 4000


# ── Heurísticas de URL ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://repositorio.br/artigo.pdf", True),
        ("https://revista.br/download/123.pdf?sequence=1", True),
        ("https://www.scielo.br/j/rap/a/xyz/?format=pdf&lang=pt", True),
        ("https://arxiv.org/pdf/2401.12345", True),
        ("https://pubmed.ncbi.nlm.nih.gov/12345678/", False),
        ("https://doi.org/10.1590/1234", False),
        ("", False),
    ],
)
def test_looks_like_pdf_url(url, expected):
    assert looks_like_pdf_url(url) is expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://doi.org/10.1590/S0034-76122011000500004", "10.1590/S0034-76122011000500004"),
        ("doi:10.1016/j.jclepro.2020.123456", "10.1016/j.jclepro.2020.123456"),
        ("10.1590/abc123", "10.1590/abc123"),
        ("sem doi aqui", None),
        (None, None),
    ],
)
def test_normalize_doi(raw, expected):
    assert normalize_doi(raw) == expected


def test_is_pdf_bytes_tolera_lixo_inicial():
    assert is_pdf_bytes(b"%PDF-1.4 conteudo")
    assert is_pdf_bytes(b"\n\r  %PDF-1.4")
    assert is_pdf_bytes(b"\xef\xbb\xbf%PDF-1.4 com BOM")
    assert is_pdf_bytes(b"\x00\x00 %PDF-1.5")
    assert is_pdf_bytes(b"Header lixo ... %PDF-1.7")
    assert not is_pdf_bytes(b"<!DOCTYPE html><html>")
    assert not is_pdf_bytes(b"")


# ── Padrões por domínio ───────────────────────────────────────────────

def test_pattern_scielo_classico():
    ref = PaperRef(
        download_url="https://www.scielo.br/scielo.php?script=sci_arttext&pid=S0034-761220"
    )
    urls = [c.url for c in pattern_candidates(ref)]
    assert any("sci_pdf" in u for u in urls)


def test_pattern_scielo_novo():
    ref = PaperRef(download_url="https://www.scielo.br/j/rap/a/7xKzQ9/")
    urls = [c.url for c in pattern_candidates(ref)]
    assert any(u.endswith("format=pdf&lang=pt") for u in urls)


def test_pattern_arxiv_por_doi():
    ref = PaperRef(doi="10.48550/arXiv.2401.12345")
    urls = [c.url for c in pattern_candidates(ref)]
    assert "https://arxiv.org/pdf/2401.12345" in urls


def test_pattern_dspace_handle():
    ref = PaperRef(download_url="https://repositorio.ufpr.br/handle/1884/45678")
    urls = [c.url for c in pattern_candidates(ref)]
    assert any("bitstream/handle/1884/45678" in u for u in urls)


def test_pattern_ojs_view_para_download():
    ref = PaperRef(download_url="https://periodicos.ufsc.br/index.php/rev/article/view/8899")
    urls = [c.url for c in pattern_candidates(ref)]
    assert any("/article/download/8899" in u for u in urls)


def test_pattern_pmc():
    ref = PaperRef(download_url="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7654321/")
    urls = [c.url for c in pattern_candidates(ref)]
    assert any(u.endswith("PMC7654321/pdf/") for u in urls)


# ── Raspagem de landing page ──────────────────────────────────────────

def test_extract_citation_pdf_url_tem_prioridade():
    html = """
    <html><head>
      <meta name="citation_title" content="Governança regional">
      <meta name="citation_pdf_url" content="/artigos/123/download.pdf">
    </head><body>
      <a href="/licenca.pdf">Licença de uso</a>
    </body></html>
    """
    candidates = extract_pdf_links_from_html(html, "https://revista.org/artigo/123")
    assert candidates[0].url == "https://revista.org/artigos/123/download.pdf"
    assert "citation_pdf_url" in candidates[0].label


def test_extract_dspace_bitstream_pontua_handle():
    html = """
    <html><body>
      <a href="/bitstream/1884/45678/1/tese_completa.pdf?sequence=1&isAllowed=y">
        Texto completo em PDF</a>
      <a href="/bitstream/1884/45678/2/ficha_catalografica.pdf">Ficha catalográfica</a>
      <a href="/themes/logo.png">logo</a>
    </body></html>
    """
    candidates = extract_pdf_links_from_html(
        html, "https://acervodigital.ufpr.br/handle/1884/45678"
    )
    urls = [c.url for c in candidates]
    assert urls[0].endswith("tese_completa.pdf?sequence=1&isAllowed=y")
    # Anexos acessórios e imagens são descartados.
    assert not any("ficha_catalografica" in u for u in urls)
    assert not any("logo.png" in u for u in urls)


def test_extract_ignora_ancoras_irrelevantes():
    html = "<html><body><a href='/sobre'>Sobre a revista</a></body></html>"
    assert extract_pdf_links_from_html(html, "https://revista.org/artigo/1") == []


def test_extract_link_alternate_pdf():
    html = """
    <html><head>
      <link rel="alternate" type="application/pdf" href="https://cdn.org/a/1.pdf">
    </head><body></body></html>
    """
    candidates = extract_pdf_links_from_html(html, "https://revista.org/a/1")
    assert candidates[0].url == "https://cdn.org/a/1.pdf"


# ── Fluxo completo com transporte simulado ────────────────────────────

def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    )


@pytest.mark.anyio
async def test_acquire_via_landing_page_quando_url_e_html():
    """A URL cadastrada é uma landing page; o PDF está num link dentro dela."""
    landing = "https://repositorio.br/handle/1/2"
    pdf_url = "https://repositorio.br/bitstream/1/2/tese.pdf"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == landing:
            html = f'<html><head><meta name="citation_pdf_url" content="{pdf_url}"></head></html>'
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
        if str(request.url) == pdf_url:
            return httpx.Response(
                200, content=MIN_PDF, headers={"content-type": "application/pdf"}
            )
        return httpx.Response(404)

    resolver = PDFResolver()
    async with _client(handler) as client:
        resolved, attempts = await resolver.acquire(PaperRef(download_url=landing), client=client)

    assert resolved is not None
    assert resolved.url == pdf_url
    assert resolved.strategy == "landing"
    assert any(a.status == "ok" for a in attempts)


@pytest.mark.anyio
async def test_acquire_segue_pagina_intermediaria_html():
    """Um candidato devolve HTML; o arquivo real está a um salto de distância."""
    direct = "https://revista.org/a/9/?format=pdf"
    real_pdf = "https://revista.org/download/9.pdf"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == direct:
            html = f'<html><body><a href="{real_pdf}">Baixar PDF</a></body></html>'
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
        if url == real_pdf:
            return httpx.Response(
                200, content=MIN_PDF, headers={"content-type": "application/pdf"}
            )
        return httpx.Response(404)

    resolver = PDFResolver()
    async with _client(handler) as client:
        resolved, attempts = await resolver.acquire(PaperRef(download_url=direct), client=client)

    assert resolved is not None
    assert resolved.url == real_pdf
    assert any(a.status == "nao_pdf" for a in attempts)
    assert any(a.strategy.endswith("+html") for a in attempts)


@pytest.mark.anyio
async def test_acquire_rejeita_html_e_registra_trilha():
    """Nunca salvar HTML como se fosse PDF — a falha antiga mais comum."""
    landing = "https://editora.com/artigo/1"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><body>Faça login para acessar</body></html>",
            headers={"content-type": "text/html"},
        )

    resolver = PDFResolver()
    async with _client(handler) as client:
        resolved, attempts = await resolver.acquire(
            PaperRef(download_url=f"{landing}.pdf"), client=client
        )

    assert resolved is None
    assert attempts
    assert all(a.status != "ok" for a in attempts)
    assert any("HTML" in a.detail for a in attempts)


@pytest.mark.anyio
async def test_acquire_registra_bloqueio_por_assinatura():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    resolver = PDFResolver()
    async with _client(handler) as client:
        resolved, attempts = await resolver.acquire(
            PaperRef(download_url="https://editora.com/artigo.pdf"), client=client
        )

    assert resolved is None
    blocked = [a for a in attempts if a.http_status == 403]
    assert blocked
    assert "assinatura" in blocked[0].detail


@pytest.mark.anyio
async def test_acquire_descarta_pdf_minusculo():
    """Página de erro servida com content-type de PDF não vira arquivo salvo."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"%PDF-1.4 erro", headers={"content-type": "application/pdf"}
        )

    resolver = PDFResolver()
    async with _client(handler) as client:
        resolved, attempts = await resolver.acquire(
            PaperRef(download_url="https://editora.com/artigo.pdf"), client=client
        )

    assert resolved is None
    assert any(a.status == "pequeno_demais" for a in attempts)


@pytest.mark.anyio
async def test_acquire_via_unpaywall_por_doi():
    pdf_url = "https://repositorio.org/oa/artigo.pdf"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "api.unpaywall.org" in url:
            return httpx.Response(
                200,
                json={
                    "best_oa_location": {"url_for_pdf": pdf_url, "host_type": "repository"},
                    "oa_locations": [],
                },
            )
        if url == pdf_url:
            return httpx.Response(
                200, content=MIN_PDF, headers={"content-type": "application/pdf"}
            )
        return httpx.Response(404)

    resolver = PDFResolver(contact_email="pesquisa@universidade.br")
    async with _client(handler) as client:
        resolved, _ = await resolver.acquire(PaperRef(doi="10.1590/abc"), client=client)

    assert resolved is not None
    assert resolved.strategy == "unpaywall"


@pytest.mark.anyio
async def test_unpaywall_e_pulado_sem_email_de_contato():
    chamadas: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas.append(str(request.url))
        return httpx.Response(404)

    resolver = PDFResolver(contact_email="")
    async with _client(handler) as client:
        await resolver.acquire(PaperRef(doi="10.1590/abc"), client=client)

    assert not any("unpaywall" in url for url in chamadas)


@pytest.mark.anyio
async def test_acquire_via_openalex_quando_unpaywall_indisponivel():
    pdf_url = "https://oa.org/works/1.pdf"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "api.openalex.org" in url:
            return httpx.Response(
                200,
                json={
                    "best_oa_location": {
                        "pdf_url": pdf_url,
                        "source": {"display_name": "Revista Aberta"},
                    },
                    "locations": [],
                },
            )
        if url == pdf_url:
            return httpx.Response(
                200, content=MIN_PDF, headers={"content-type": "application/pdf"}
            )
        return httpx.Response(404)

    resolver = PDFResolver()
    async with _client(handler) as client:
        resolved, _ = await resolver.acquire(PaperRef(doi="10.1590/xyz"), client=client)

    assert resolved is not None
    assert resolved.strategy == "openalex"


@pytest.mark.anyio
async def test_find_candidates_nao_baixa_arquivos():
    baixados: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith(".pdf"):
            baixados.append(url)
            return httpx.Response(200, content=MIN_PDF)
        return httpx.Response(404)

    resolver = PDFResolver()
    async with _client(handler) as client:
        candidates = await resolver.find_candidates(
            PaperRef(download_url="https://www.scielo.br/j/rap/a/abc/"), client=client
        )

    assert candidates
    assert baixados == []
