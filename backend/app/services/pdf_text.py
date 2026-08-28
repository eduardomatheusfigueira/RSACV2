#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Pipeline de Texto de PDF (extração, limpeza, seções e contexto).

Extrair texto de PDF acadêmico não é `page.get_text()`. O que sai dali vem com
cabeçalhos e rodapés repetidos em toda página, palavras quebradas por hífen na
quebra de linha, ligaduras tipográficas (ﬁ, ﬂ), numeração de linha e ordem de
leitura embaralhada em layout de duas colunas.

Este módulo trata o texto como objeto de pesquisa:

  * `extract_document`  — extração por blocos, com ordem de leitura corrigida,
    preservando a paginação (essencial para citar "p. 7" na extração de dados).
  * `clean_page_text`   — de-hifenização, normalização de ligaduras e espaços.
  * `strip_running_heads` — remove cabeçalho/rodapé que se repete entre páginas.
  * `segment_sections`  — segmenta em IMRaD (Introdução, Método, Resultados...).
  * `build_question_context` — seleciona os trechos mais relevantes para um
    conjunto de perguntas de extração, respeitando um orçamento de caracteres.

O último ponto é o que substitui a política anterior de "primeiros 7.500 e
últimos 7.500 caracteres", que jogava fora exatamente o miolo metodológico onde
mora a resposta da maioria das perguntas de extração.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# Abaixo deste volume médio de caracteres por página, o documento é
# provavelmente digitalizado como imagem (precisa de OCR).
SCANNED_CHARS_PER_PAGE_THRESHOLD = 120

LIGATURES = {
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st",
    "“": '"', "”": '"', "‘": "'", "’": "'", "—": "—", "–": "–", " ": " ",
    "​": "", "﻿": "", " ": "\n", " ": "\n\n",
}

# Títulos canônicos de seção em português, inglês e espanhol.
SECTION_PATTERNS: list[tuple[str, str]] = [
    ("resumo", r"^(resumo|abstract|resumen)\b"),
    ("introducao", r"^(introdu[çc][ãa]o|introduction|introducci[óo]n)\b"),
    ("referencial", r"^(referencial\s+te[óo]rico|revis[ãa]o\s+(de\s+)?literatura|"
                    r"literature\s+review|fundamenta[çc][ãa]o\s+te[óo]rica|"
                    r"marco\s+te[óo]rico|background)\b"),
    ("metodo", r"^(metodologia|m[ée]todos?|materiais?\s+e\s+m[ée]todos|"
               r"procedimentos?\s+metodol[óo]gicos?|method(s|ology)?|"
               r"materials?\s+and\s+methods|metodolog[íi]a|m[ée]todos?)\b"),
    ("resultados", r"^(resultados?|results?|resultados\s+e\s+discuss[ãa]o|"
                   r"results?\s+and\s+discussion|achados|findings)\b"),
    ("discussao", r"^(discuss[ãa]o|discussion|discusi[óo]n|an[áa]lise\s+dos\s+resultados)\b"),
    ("conclusao", r"^(conclus[õoa]es?|conclusion(s)?|considera[çc][õo]es\s+finais|"
                  r"consideraciones\s+finales)\b"),
    ("referencias", r"^(refer[êe]ncias?|references?|bibliograf[íi]a|"
                    r"referencias\s+bibliogr[áa]ficas)\b"),
]

STOPWORDS = {
    # Palavras vazias de português, inglês e espanhol — as três línguas
    # das bases cobertas pelos coletores.
    "a", "o", "os", "as", "de", "do", "da", "dos", "das", "e", "em", "no", "na", "nos", "nas",
    "um", "uma", "uns", "umas", "para", "por", "com", "que", "se", "ao", "aos", "à", "às",
    "ou", "como", "qual", "quais", "quando", "onde", "foi", "ser", "sao", "são", "sobre",
    "entre", "mais", "seu", "sua", "este", "esta", "esse", "essa", "isso", "pelo", "pela",
    "num", "numa", "the", "of", "and", "in", "to", "for", "on", "with", "is", "are", "was",
    "were", "by", "at", "an", "be", "this", "that", "which", "what", "from", "or", "it", "its",
    "their", "there", "how", "does", "el", "la", "los", "las", "del", "y", "en", "un", "una",
    "con", "es", "son", "cual", "cuales"
}

RE_WORD = re.compile(r"[a-zà-öø-ÿ0-9][a-zà-öø-ÿ0-9\-]{2,}", re.IGNORECASE)
RE_HYPHEN_BREAK = re.compile(r"(\w)[-‐‑‒–]\s*\n\s*(\w)")
RE_MULTI_SPACE = re.compile(r"[ \t]{2,}")
RE_MULTI_NEWLINE = re.compile(r"\n{3,}")
RE_PAGE_NUMBER_LINE = re.compile(r"^\s*[-–—|]?\s*\d{1,4}\s*[-–—|]?\s*$")


# ── Estruturas ────────────────────────────────────────────────────────

@dataclass
class PDFPage:
    """Texto já limpo de uma página, com seu número (1-based)."""

    number: int
    text: str

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass
class PDFDocument:
    """Documento extraído com paginação preservada e diagnóstico de qualidade."""

    pages: list[PDFPage] = field(default_factory=list)
    engine: str = ""
    title: str = ""
    page_count: int = 0
    is_scanned: bool = False
    error: str = ""

    @property
    def text(self) -> str:
        """Texto contínuo do documento (sem marcadores de página)."""
        return "\n\n".join(p.text for p in self.pages if p.text.strip()).strip()

    @property
    def char_count(self) -> int:
        return len(self.text)

    def text_with_page_marks(self) -> str:
        """Texto com marcação de página — usado para ancorar evidências."""
        chunks = []
        for page in self.pages:
            if page.text.strip():
                chunks.append(f"[[p. {page.number}]]\n{page.text}")
        return "\n\n".join(chunks).strip()


@dataclass
class Section:
    """Trecho do documento associado a uma seção canônica."""

    key: str
    title: str
    text: str
    start_page: int = 0


@dataclass
class TextChunk:
    """Unidade de recuperação para montar contexto da IA."""

    text: str
    page: int
    section: str = ""
    index: int = 0


# ── Limpeza ───────────────────────────────────────────────────────────

def normalize_unicode(text: str) -> str:
    """Normaliza ligaduras, aspas tipográficas e espaços exóticos."""
    if not text:
        return ""
    for source, target in LIGATURES.items():
        if source in text:
            text = text.replace(source, target)
    text = unicodedata.normalize("NFKC", text)
    # Remove caracteres de controle preservando \n e \t.
    return "".join(ch for ch in text if ch == "\n" or ch == "\t" or unicodedata.category(ch)[0] != "C")


def dehyphenate(text: str) -> str:
    """Recompõe palavras quebradas por hífen no fim da linha."""
    previous = None
    while previous != text:
        previous = text
        text = RE_HYPHEN_BREAK.sub(r"\1\2", text)
    return text


def clean_page_text(text: str) -> str:
    """Limpeza completa do texto de uma página."""
    if not text:
        return ""
    text = normalize_unicode(text)
    text = dehyphenate(text)

    lines = []
    for raw_line in text.split("\n"):
        line = RE_MULTI_SPACE.sub(" ", raw_line).strip()
        if not line:
            lines.append("")
            continue
        # Descarta linhas que são apenas o número da página.
        if RE_PAGE_NUMBER_LINE.match(line):
            continue
        lines.append(line)

    text = "\n".join(lines)
    return RE_MULTI_NEWLINE.sub("\n\n", text).strip()


def strip_running_heads(pages: list[PDFPage], min_pages: int = 4) -> list[PDFPage]:
    """
    Remove cabeçalhos e rodapés repetidos.

    Uma linha que aparece no topo (ou no rodapé) de mais de 60% das páginas é
    elemento de diagramação, não conteúdo — some com ela.
    """
    if len(pages) < min_pages:
        return pages

    head_counts: dict[str, int] = {}
    foot_counts: dict[str, int] = {}

    for page in pages:
        lines = _dense_lines(page)
        if not lines:
            continue
        for line in lines[:2]:
            key = _repeat_key(line)
            if key:
                head_counts[key] = head_counts.get(key, 0) + 1
        for line in lines[-2:]:
            key = _repeat_key(line)
            if key:
                foot_counts[key] = foot_counts.get(key, 0) + 1

    threshold = max(3, int(len(pages) * 0.6))
    repeated = {k for k, v in head_counts.items() if v >= threshold}
    repeated |= {k for k, v in foot_counts.items() if v >= threshold}
    if not repeated:
        return pages

    cleaned: list[PDFPage] = []
    for page in pages:
        lines = page.text.split("\n")
        dense = _dense_lines(page)
        if not dense:
            # Página esparsa (folha de rosto, tabela solta): não mexe.
            cleaned.append(page)
            continue
        # Só as bordas da página são candidatas — nunca o miolo do texto.
        border = {dense[0], dense[1] if len(dense) > 1 else "", dense[-1], dense[-2] if len(dense) > 1 else ""}
        kept = [
            line
            for line in lines
            if not line.strip() or line not in border or _repeat_key(line) not in repeated
        ]
        cleaned.append(
            PDFPage(number=page.number, text=RE_MULTI_NEWLINE.sub("\n\n", "\n".join(kept)).strip())
        )
    return cleaned


def _dense_lines(page: PDFPage, min_lines: int = 4) -> list[str]:
    """
    Linhas não vazias de uma página com corpo de texto suficiente.

    A detecção de cabeçalho/rodapé só faz sentido em página com corpo: numa
    página de duas linhas, *toda* linha é borda e o conteúdo seria confundido
    com diagramação.
    """
    lines = [line for line in page.text.split("\n") if line.strip()]
    return lines if len(lines) >= min_lines else []


def _repeat_key(line: str) -> str:
    """Chave de comparação de linha, tolerante a variação de numeração."""
    stripped = re.sub(r"\d+", "#", line.strip().lower())
    stripped = re.sub(r"\s+", " ", stripped)
    return stripped if 4 <= len(stripped) <= 120 else ""


# ── Extração ──────────────────────────────────────────────────────────

def extract_document(file_path: str) -> PDFDocument:
    """
    Extrai o documento com PyMuPDF (ordem de leitura por blocos) e cai para
    pypdf se o primeiro motor falhar.
    """
    document = _extract_with_pymupdf(file_path)
    if document.pages and document.char_count > 0:
        return _finalize(document)

    fallback = _extract_with_pypdf(file_path)
    if fallback.pages and fallback.char_count > 0:
        return _finalize(fallback)

    # Nenhum motor produziu texto: PDF digitalizado ou corrompido.
    result = document if document.page_count else fallback
    result.is_scanned = result.page_count > 0
    if not result.error:
        result.error = "Nenhum texto extraível — documento provavelmente digitalizado (imagem)."
    return result


def _extract_with_pymupdf(file_path: str) -> PDFDocument:
    document = PDFDocument(engine="pymupdf")
    try:
        # `pymupdf` é o nome atual do pacote; `fitz` é o alias legado, mantido
        # como fallback para instalações antigas.
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
    except ImportError as exc:  # pragma: no cover - dependência declarada
        document.error = f"PyMuPDF indisponível: {exc}"
        return document

    try:
        with fitz.open(file_path) as doc:
            document.page_count = doc.page_count
            document.title = (doc.metadata or {}).get("title") or ""
            for index in range(doc.page_count):
                page = doc.load_page(index)
                text = _blocks_to_text(page)
                document.pages.append(PDFPage(number=index + 1, text=clean_page_text(text)))
    except Exception as exc:  # noqa: BLE001 — motor externo, falha não pode subir
        logger.warning("[PDFText] PyMuPDF falhou em %s: %s", file_path, exc)
        document.error = f"PyMuPDF: {exc}"
    return document


def _blocks_to_text(page) -> str:  # noqa: ANN001 - tipo do fitz
    """
    Reconstrói a ordem de leitura a partir dos blocos de texto.

    `get_text("blocks")` devolve (x0, y0, x1, y1, texto, nº, tipo). Ordenar por
    (coluna, y, x) recupera o fluxo correto em layout de duas colunas, que a
    extração linear embaralha.
    """
    try:
        blocks = page.get_text("blocks")
    except Exception:  # noqa: BLE001
        return page.get_text() or ""

    text_blocks = [b for b in blocks if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()]
    if not text_blocks:
        return page.get_text() or ""

    page_width = float(getattr(page.rect, "width", 0) or 0)
    midpoint = page_width / 2 if page_width else 0

    def sort_key(block):  # noqa: ANN001
        x0, y0 = float(block[0]), float(block[1])
        # Duas colunas: bloco inteiramente à direita do meio vai depois.
        column = 1 if (midpoint and x0 > midpoint * 1.02) else 0
        return (column, round(y0, 1), round(x0, 1))

    if _is_single_column(text_blocks, midpoint):
        text_blocks.sort(key=lambda b: (round(float(b[1]), 1), round(float(b[0]), 1)))
    else:
        text_blocks.sort(key=sort_key)

    return "\n\n".join(block[4].strip() for block in text_blocks)


def _is_single_column(blocks: Iterable, midpoint: float) -> bool:
    """Detecta layout de coluna única (a maioria dos blocos cruza o meio)."""
    if not midpoint:
        return True
    total = 0
    crossing = 0
    for block in blocks:
        total += 1
        x0, x1 = float(block[0]), float(block[2])
        if x0 < midpoint < x1:
            crossing += 1
    return total == 0 or (crossing / total) > 0.35


def _extract_with_pypdf(file_path: str) -> PDFDocument:
    document = PDFDocument(engine="pypdf")
    try:
        import pypdf
    except ImportError as exc:
        document.error = f"pypdf indisponível: {exc}"
        return document

    try:
        reader = pypdf.PdfReader(file_path)
        document.page_count = len(reader.pages)
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            document.pages.append(PDFPage(number=index + 1, text=clean_page_text(text)))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PDFText] pypdf falhou em %s: %s", file_path, exc)
        document.error = f"pypdf: {exc}"
    return document


def _finalize(document: PDFDocument) -> PDFDocument:
    document.pages = strip_running_heads(document.pages)
    if not document.page_count:
        document.page_count = len(document.pages)
    if document.page_count:
        document.is_scanned = (
            document.char_count / document.page_count
        ) < SCANNED_CHARS_PER_PAGE_THRESHOLD
    return document


# ── Segmentação em seções ─────────────────────────────────────────────

def detect_section(line: str) -> Optional[tuple[str, str]]:
    """Reconhece um título de seção canônica numa linha isolada."""
    candidate = line.strip()
    if not candidate or len(candidate) > 90:
        return None

    # Remove numeração ("3.", "3.1", "III -") antes de comparar.
    normalized = re.sub(r"^\s*([0-9]+[.)]?\s*)+", "", candidate)
    normalized = re.sub(r"^\s*[IVXLC]+\s*[-–.)]\s*", "", normalized, flags=re.IGNORECASE)
    normalized = normalized.strip(" .:-–—\t")
    if not normalized:
        return None

    folded = _strip_accents(normalized.lower())
    for key, pattern in SECTION_PATTERNS:
        if re.match(_strip_accents(pattern), folded, re.IGNORECASE):
            # Título de seção é linha curta; parágrafo que começa com a palavra não conta.
            if len(normalized.split()) <= 6:
                return key, normalized
    return None


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )


def segment_sections(document: PDFDocument) -> list[Section]:
    """Divide o documento em seções canônicas do padrão IMRaD."""
    sections: list[Section] = []
    current_key = "preambulo"
    current_title = "Preâmbulo (título, autoria, resumo)"
    current_lines: list[str] = []
    current_page = document.pages[0].number if document.pages else 1

    for page in document.pages:
        for line in page.text.split("\n"):
            detected = detect_section(line)
            if detected:
                key, title = detected
                if current_lines:
                    sections.append(
                        Section(
                            key=current_key,
                            title=current_title,
                            text="\n".join(current_lines).strip(),
                            start_page=current_page,
                        )
                    )
                current_key, current_title = key, title
                current_lines = []
                current_page = page.number
                continue
            current_lines.append(line)

    if current_lines:
        sections.append(
            Section(
                key=current_key,
                title=current_title,
                text="\n".join(current_lines).strip(),
                start_page=current_page,
            )
        )
    return [s for s in sections if s.text.strip()]


# ── Recuperação de contexto para a IA ─────────────────────────────────

def chunk_document(document: PDFDocument, target_chars: int = 1400) -> list[TextChunk]:
    """Divide o documento em blocos de tamanho aproximado, preservando página."""
    chunks: list[TextChunk] = []
    index = 0
    for page in document.pages:
        paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]
        buffer = ""
        for paragraph in paragraphs:
            if buffer and len(buffer) + len(paragraph) > target_chars:
                chunks.append(TextChunk(text=buffer.strip(), page=page.number, index=index))
                index += 1
                buffer = paragraph
            else:
                buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if buffer.strip():
            chunks.append(TextChunk(text=buffer.strip(), page=page.number, index=index))
            index += 1
    return chunks


def tokenize(text: str) -> set[str]:
    """Tokens significativos (minúsculos, sem palavras vazias)."""
    return {
        token.lower()
        for token in RE_WORD.findall(_strip_accents(text or ""))
        if token.lower() not in STOPWORDS
    }


def score_chunk(chunk: TextChunk, query_tokens: set[str]) -> float:
    """Pontua um bloco pela sobreposição de termos com as perguntas."""
    if not query_tokens:
        return 0.0
    chunk_tokens = tokenize(chunk.text)
    if not chunk_tokens:
        return 0.0
    overlap = len(chunk_tokens & query_tokens)
    if not overlap:
        return 0.0
    # Normaliza pelo tamanho para não privilegiar blocos longos e genéricos.
    return overlap / (1 + len(chunk_tokens) ** 0.5)


def build_question_context(
    document: PDFDocument,
    questions: list[str],
    budget_chars: int = 28000,
    head_chars: int = 6000,
) -> str:
    """
    Monta o contexto enviado à IA priorizando relevância, não posição.

    Estratégia:
      1. O início do documento entra sempre (título, autoria, resumo, palavras-chave).
      2. Os demais blocos são pontuados contra os termos das perguntas de extração,
         com bônus para as seções que costumam responder revisão sistemática
         (método, resultados, discussão, conclusão).
      3. Os selecionados voltam à ordem original do documento, com marcação de
         página, para que a IA possa citar "p. 12" na evidência.
    """
    full_text = document.text
    if not full_text:
        return ""
    if len(full_text) <= budget_chars:
        return document.text_with_page_marks()

    chunks = chunk_document(document)
    if not chunks:
        return full_text[:budget_chars]

    # 1. Cabeça do documento (sempre incluída).
    head_selected: list[TextChunk] = []
    head_size = 0
    for chunk in chunks:
        if head_size + len(chunk.text) > head_chars:
            break
        head_selected.append(chunk)
        head_size += len(chunk.text)

    head_indexes = {chunk.index for chunk in head_selected}

    # 2. Rotula seção de cada bloco para bônus de pontuação.
    section_by_page = _section_map(document)
    query_tokens = tokenize(" ".join(questions))

    scored: list[tuple[float, TextChunk]] = []
    for chunk in chunks:
        if chunk.index in head_indexes:
            continue
        section = section_by_page.get(chunk.page, "")
        chunk.section = section
        score = score_chunk(chunk, query_tokens)
        if section in ("metodo", "resultados", "discussao", "conclusao"):
            score *= 1.35
        elif section == "referencias":
            score *= 0.15  # Lista bibliográfica raramente responde pergunta de extração.
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)

    selected = list(head_selected)
    used = head_size
    for score, chunk in scored:
        if used + len(chunk.text) > budget_chars:
            continue
        if score <= 0 and used > budget_chars * 0.75:
            break
        selected.append(chunk)
        used += len(chunk.text)

    # 3. Reordena e monta com marcação de página e de corte.
    selected.sort(key=lambda chunk: chunk.index)
    parts: list[str] = []
    previous_index = -2
    for chunk in selected:
        if chunk.index != previous_index + 1 and parts:
            parts.append("[... trecho omitido por limite de contexto ...]")
        parts.append(f"[[p. {chunk.page}]] {chunk.text}")
        previous_index = chunk.index

    return "\n\n".join(parts).strip()


def _section_map(document: PDFDocument) -> dict[int, str]:
    """Mapeia página → seção canônica vigente naquela página."""
    mapping: dict[int, str] = {}
    current = "preambulo"
    for page in document.pages:
        for line in page.text.split("\n"):
            detected = detect_section(line)
            if detected:
                current = detected[0]
        mapping[page.number] = current
    return mapping
