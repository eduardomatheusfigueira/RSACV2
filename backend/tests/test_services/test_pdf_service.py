#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de armazenamento, cache e leitura do PDFService com arquivos reais."""

import httpx
import pytest

from app.services.pdf_resolver import PaperRef
from app.services.pdf_service import PDFService


def _make_pdf(paginas: list[str]) -> bytes:
    """Gera um PDF real (não um esqueleto) para exercitar a extração de texto."""
    try:
        import pymupdf as fitz
    except ImportError:  # pragma: no cover
        import fitz

    doc = fitz.open()
    for texto in paginas:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(56, 56, 540, 760), texto, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def service(tmp_path, monkeypatch) -> PDFService:
    svc = PDFService(contact_email="")
    svc.storage_dir = tmp_path
    return svc


_ENCHIMENTO = (
    "O desenvolvimento regional depende da articulação entre atores públicos e "
    "privados no território, com coordenação intergovernamental efetiva. "
) * 6

PAGINAS = [
    "Governança territorial e arranjos produtivos locais\n\n"
    "RESUMO\n\nEste artigo analisa consórcios intermunicipais no Paraná.\n\n" + _ENCHIMENTO,
    "METODOLOGIA\n\nForam analisados 137 municípios por meio de entrevistas "
    "semiestruturadas e análise documental de planos regionais.\n\n" + _ENCHIMENTO,
    "RESULTADOS\n\nO índice de governança cresceu 18,4% no período estudado.\n\n" + _ENCHIMENTO,
]


def test_salva_valida_e_le_pdf(service):
    conteudo = _make_pdf(PAGINAS)
    caminho = service.save_uploaded_pdf("proj1", "paper1", conteudo)

    document = service.read_document(caminho)
    assert document.page_count == 3
    assert "137 municípios" in document.text
    assert document.is_scanned is False
    # Paginação preservada — base para citar a página na evidência.
    assert document.pages[1].number == 2


def test_rejeita_arquivo_que_nao_e_pdf(service):
    with pytest.raises(ValueError, match="não é um PDF válido"):
        service.save_uploaded_pdf("proj1", "paper1", b"<html>pagina de login</html>")


def test_cache_de_texto_evita_reextracao(service, monkeypatch):
    caminho = service.save_uploaded_pdf("proj1", "paper1", _make_pdf(PAGINAS))
    service.read_document(caminho)  # popula o cache

    chamadas = {"n": 0}
    original = __import__(
        "app.services.pdf_service", fromlist=["extract_document"]
    ).extract_document

    def espiao(path):
        chamadas["n"] += 1
        return original(path)

    monkeypatch.setattr("app.services.pdf_service.extract_document", espiao)
    document = service.read_document(caminho)

    assert chamadas["n"] == 0
    assert "137 municípios" in document.text


def test_cache_e_invalidado_ao_substituir_arquivo(service):
    caminho = service.save_uploaded_pdf("proj1", "paper1", _make_pdf(PAGINAS))
    assert "137 municípios" in service.read_document(caminho).text

    service.save_uploaded_pdf("proj1", "paper1", _make_pdf(["Outro documento totalmente distinto."]))
    document = service.read_document(caminho)

    assert "137 municípios" not in document.text
    assert "totalmente distinto" in document.text


def test_delete_remove_arquivo_e_cache(service):
    caminho = service.save_uploaded_pdf("proj1", "paper1", _make_pdf(PAGINAS))
    service.read_document(caminho)
    cache = service._text_cache_path(caminho)
    assert cache.exists()

    assert service.delete_pdf("proj1", "paper1", caminho) is True
    assert not cache.exists()


def test_secoes_detectadas_no_arquivo(service):
    caminho = service.save_uploaded_pdf("proj1", "paper1", _make_pdf(PAGINAS))
    chaves = [s["key"] for s in service.get_sections(caminho)]
    assert "metodo" in chaves
    assert "resultados" in chaves


def test_contexto_para_ia_prioriza_pergunta(service):
    caminho = service.save_uploaded_pdf("proj1", "paper1", _make_pdf(PAGINAS))
    contexto = service.build_ai_context(caminho, ["Qual a amostra do estudo?"], budget_chars=500)
    assert contexto


@pytest.mark.anyio
async def test_acquire_persiste_metadados_de_procedencia(service):
    conteudo = _make_pdf(PAGINAS)
    pdf_url = "https://repositorio.org/artigo.pdf"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == pdf_url:
            return httpx.Response(
                200, content=conteudo, headers={"content-type": "application/pdf"}
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        result = await service.acquire_pdf(
            "proj1", "paper1", PaperRef(download_url=pdf_url), client=client
        )

    assert result.success is True
    assert result.strategy == "direct"
    assert result.page_count == 3
    assert result.text_chars > 100
    assert len(result.sha256) == 64
    assert result.attempts and result.attempts[-1].status == "ok"


@pytest.mark.anyio
async def test_acquire_falha_devolve_mensagem_acionavel(service):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        result = await service.acquire_pdf(
            "proj1", "paper1", PaperRef(download_url="https://editora.com/a.pdf"), client=client
        )

    assert result.success is False
    assert result.file_path is None
    assert "anexe o arquivo manualmente" in result.message
    assert result.attempts_json().startswith("[")


@pytest.mark.anyio
async def test_download_pdf_compat_resolve_landing_page(service):
    """A assinatura antiga continua funcionando — e agora atravessa a landing page."""
    landing = "https://repositorio.org/handle/1/2"
    pdf_url = "https://repositorio.org/bitstream/1/2/artigo.pdf"
    conteudo = _make_pdf(PAGINAS)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == landing:
            return httpx.Response(
                200,
                text=f'<html><head><meta name="citation_pdf_url" content="{pdf_url}"></head></html>',
                headers={"content-type": "text/html"},
            )
        if url == pdf_url:
            return httpx.Response(
                200, content=conteudo, headers={"content-type": "application/pdf"}
            )
        return httpx.Response(404)

    # `download_pdf` cria o próprio cliente; injeta o transporte simulado.
    import app.services.pdf_resolver as resolver_module

    original_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs.pop("transport", None)
        return original_client(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
            headers=kwargs.get("headers"),
        )

    resolver_module.httpx.AsyncClient = fake_client
    try:
        caminho = await service.download_pdf("proj1", "paper1", landing)
    finally:
        resolver_module.httpx.AsyncClient = original_client

    assert caminho is not None
    assert caminho.endswith("paper1.pdf")


# ── O laço de eventos não pode travar (doc 40 §40.6) ──────────────────


@pytest.mark.anyio
async def test_extracao_de_pdf_nao_roda_no_laco_de_eventos(service):
    """
    A parte pesada da aquisição precisa sair para uma thread.

    Gravar em disco, abrir o PDF no PyMuPDF e calcular o SHA-256 são as únicas
    operações do Revsist que ocupam CPU de verdade. No desenho de produção há um
    **único** worker (doc 40 §40.6), escolhido porque todo o resto do trabalho é
    espera de rede e um laço de eventos sozinho dá conta. Essa escolha só se
    sustenta enquanto a CPU sair do laço: rodando ali, a aquisição em lote de
    três teses congelaria todas as outras requisições por segundos — inclusive
    a barra de progresso de quem estivesse triando.

    O teste afirma o mecanismo, não o tempo: a extração tem de acontecer em uma
    thread diferente da que roda o laço.
    """
    import threading

    from app.services import pdf_service as modulo

    thread_do_laco = threading.current_thread()
    threads_da_extracao: list[threading.Thread] = []

    extrair_original = modulo.extract_document

    def extrair_registrando(file_path: str):
        threads_da_extracao.append(threading.current_thread())
        return extrair_original(file_path)

    modulo.extract_document = extrair_registrando
    try:
        conteudo = _make_pdf(PAGINAS)
        pdf_url = "https://repositorio.org/artigo.pdf"

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == pdf_url:
                return httpx.Response(
                    200, content=conteudo, headers={"content-type": "application/pdf"}
                )
            return httpx.Response(404)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as client:
            resultado = await service.acquire_pdf(
                "proj1", "paper1", PaperRef(download_url=pdf_url), client=client
            )
    finally:
        modulo.extract_document = extrair_original

    assert resultado.success is True
    assert threads_da_extracao, "a extração não chegou a ser chamada"
    assert threads_da_extracao[0] is not thread_do_laco, (
        "extract_document rodou na thread do laço de eventos — "
        "a aquisição voltou a bloquear o servidor inteiro"
    )


@pytest.mark.anyio
async def test_read_document_async_sai_do_laco(service, tmp_path):
    """A leitura usada pela rota de upload segue a mesma regra."""
    import threading

    caminho = tmp_path / "doc.pdf"
    caminho.write_bytes(_make_pdf(PAGINAS))

    thread_do_laco = threading.current_thread()
    threads: list[threading.Thread] = []

    leitura_original = service.read_document

    def ler_registrando(file_path: str, use_cache: bool = True):
        threads.append(threading.current_thread())
        return leitura_original(file_path, use_cache)

    service.read_document = ler_registrando
    documento = await service.read_document_async(str(caminho))

    assert documento.page_count == 3
    assert threads and threads[0] is not thread_do_laco, (
        "read_document_async executou no laço — a rota de upload voltou a bloquear"
    )
