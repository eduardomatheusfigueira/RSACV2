#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes do pipeline de texto de PDF: limpeza, seções e contexto para IA."""

import pytest

from app.services.pdf_text import (
    PDFDocument,
    PDFPage,
    build_question_context,
    chunk_document,
    clean_page_text,
    dehyphenate,
    detect_section,
    normalize_unicode,
    segment_sections,
    strip_running_heads,
)


# ── Limpeza ───────────────────────────────────────────────────────────

def test_dehyphenate_reune_palavra_quebrada():
    texto = "o desenvolvimento regio-\nnal depende de gover-\nnança territorial"
    assert dehyphenate(texto) == "o desenvolvimento regional depende de governança territorial"


def test_normalize_unicode_resolve_ligaduras():
    assert "eficiência" in normalize_unicode("eﬁciência")
    assert normalize_unicode("aspas “curvas”") == 'aspas "curvas"'


def test_clean_page_text_remove_numero_de_pagina_isolado():
    texto = "Conteúdo relevante do estudo\n\n42\n\nOutro parágrafo"
    limpo = clean_page_text(texto)
    assert "42" not in limpo.split("\n")
    assert "Conteúdo relevante do estudo" in limpo


def test_clean_page_text_colapsa_espacos_e_linhas():
    assert clean_page_text("a    b\n\n\n\nc") == "a b\n\nc"


def _pagina_com_corpo(numero: int, cabecalho: str, rodape: str) -> PDFPage:
    corpo = "\n".join(f"Linha {i} do conteúdo exclusivo da página {numero}." for i in range(1, 6))
    return PDFPage(number=numero, text=f"{cabecalho}\n{corpo}\n{rodape}")


def test_strip_running_heads_remove_cabecalho_e_rodape_repetidos():
    cabecalho = "Revista de Desenvolvimento Regional, v. 12, n. 3"
    rodape = "ISSN 1980-0000 — Todos os direitos reservados"
    pages = [_pagina_com_corpo(i, cabecalho, rodape) for i in range(1, 8)]

    limpas = strip_running_heads(pages)

    assert all(cabecalho not in p.text for p in limpas)
    assert all(rodape not in p.text for p in limpas)
    # O corpo permanece intacto.
    assert all(f"exclusivo da página {p.number}" in p.text for p in limpas)


def test_strip_running_heads_nao_toca_no_miolo_do_texto():
    """Linha repetida no meio da página é conteúdo, não diagramação."""
    repetida = "Fonte: elaboração própria com base nos dados do IBGE."
    pages = [
        PDFPage(
            number=i,
            text="\n".join(
                [f"Cabeçalho fixo do periódico", f"Parágrafo inicial da página {i}.", repetida]
                + [f"Parágrafo {j} da página {i}." for j in range(2, 5)]
            ),
        )
        for i in range(1, 8)
    ]
    limpas = strip_running_heads(pages)
    assert all(repetida in p.text for p in limpas)


def test_strip_running_heads_preserva_documento_curto():
    pages = [PDFPage(number=1, text="Cabeçalho\n\nTexto"), PDFPage(number=2, text="Cabeçalho\n\nTexto")]
    assert strip_running_heads(pages) == pages


# ── Seções ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "linha,esperado",
    [
        ("METODOLOGIA", "metodo"),
        ("3. Materiais e Métodos", "metodo"),
        ("Resultados e Discussão", "resultados"),
        ("CONSIDERAÇÕES FINAIS", "conclusao"),
        ("References", "referencias"),
        ("Introducción", "introducao"),
    ],
)
def test_detect_section_reconhece_titulos(linha, esperado):
    detectado = detect_section(linha)
    assert detectado is not None
    assert detectado[0] == esperado


def test_detect_section_ignora_paragrafo_que_comeca_com_a_palavra():
    linha = (
        "Metodologicamente, este estudo adota uma abordagem qualitativa com apoio "
        "de análise documental sobre arranjos produtivos locais"
    )
    assert detect_section(linha) is None


def test_segment_sections_divide_documento():
    document = PDFDocument(
        pages=[
            PDFPage(number=1, text="Título do estudo\n\nRESUMO\n\nEste artigo analisa..."),
            PDFPage(number=2, text="METODOLOGIA\n\nPesquisa qualitativa com 12 entrevistas."),
            PDFPage(number=3, text="RESULTADOS\n\nOs arranjos apresentaram crescimento de 12%."),
        ],
        page_count=3,
    )
    sections = segment_sections(document)
    keys = [s.key for s in sections]
    assert "metodo" in keys
    assert "resultados" in keys

    metodo = next(s for s in sections if s.key == "metodo")
    assert "12 entrevistas" in metodo.text
    assert metodo.start_page == 2


# ── Contexto para a IA ────────────────────────────────────────────────

def _documento_longo() -> PDFDocument:
    pages = []
    for numero in range(1, 41):
        if numero == 1:
            corpo = "Título do estudo sobre governança territorial\n\nRESUMO\n\n" + (
                "Este artigo investiga arranjos produtivos locais. " * 20
            )
        elif numero == 20:
            corpo = (
                "METODOLOGIA\n\nA amostra foi composta por 137 municípios, com "
                "entrevistas semiestruturadas e análise de conteúdo categorial. " * 6
            )
        elif numero == 30:
            corpo = (
                "RESULTADOS\n\nO índice de governança regional cresceu 18,4% no "
                "período analisado, com destaque para os consórcios intermunicipais. " * 6
            )
        else:
            corpo = f"Conteúdo genérico de preenchimento da página {numero}. " * 40
        pages.append(PDFPage(number=numero, text=corpo))
    return PDFDocument(pages=pages, page_count=40)


def test_chunk_document_preserva_pagina():
    document = _documento_longo()
    chunks = chunk_document(document)
    assert chunks
    assert all(chunk.page >= 1 for chunk in chunks)
    assert {chunk.index for chunk in chunks} == set(range(len(chunks)))


def test_build_question_context_respeita_orcamento():
    document = _documento_longo()
    contexto = build_question_context(
        document, ["Qual a metodologia utilizada?"], budget_chars=8000
    )
    assert 0 < len(contexto) <= 8000 * 1.2


def test_build_question_context_traz_o_miolo_relevante():
    """
    O recorte antigo (início + fim) perdia o método, que costuma estar no meio.
    O recorte por relevância precisa trazê-lo.
    """
    document = _documento_longo()
    contexto = build_question_context(
        document,
        [
            "Qual a metodologia e o tamanho da amostra?",
            "Quais resultados quantitativos foram encontrados?",
        ],
        budget_chars=9000,
    )
    assert "137 municípios" in contexto
    assert "18,4%" in contexto


def test_build_question_context_marca_pagina():
    document = _documento_longo()
    contexto = build_question_context(document, ["metodologia amostra"], budget_chars=9000)
    assert "[[p. " in contexto


def test_build_question_context_documento_curto_vai_inteiro():
    document = PDFDocument(
        pages=[PDFPage(number=1, text="Texto curto do estudo com achados relevantes.")],
        page_count=1,
    )
    contexto = build_question_context(document, ["qualquer pergunta"], budget_chars=28000)
    assert "achados relevantes" in contexto


def test_documento_detecta_digitalizado():
    from app.services.pdf_text import _finalize

    document = PDFDocument(
        pages=[PDFPage(number=i, text="") for i in range(1, 11)], page_count=10
    )
    assert _finalize(document).is_scanned is True
