#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço de Aquisição, Armazenamento e Leitura de PDFs.

Responsabilidades:
  * **Aquisição** — delega ao `PDFResolver` a busca multi-estratégia do arquivo
    a partir de DOI / URL de origem / identificadores, valida e persiste.
  * **Armazenamento** — um diretório por projeto, arquivo nomeado pelo id do
    trabalho, com `sha256` para detectar duplicidade e recolocação.
  * **Leitura** — extração de texto com cache em disco (`.txt` ao lado do PDF),
    diagnóstico de qualidade (páginas, documento digitalizado) e montagem de
    contexto orientada às perguntas de extração.

O serviço não fala com o banco: quem persiste metadados é a camada de API, o
que mantém este módulo testável sem sessão de banco.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings
from app.services.pdf_resolver import (
    PaperRef,
    PDFCandidate,
    PDFResolver,
    ResolutionAttempt,
    is_pdf_bytes,
)
from app.services.pdf_text import (
    PDFDocument,
    build_question_context,
    extract_document,
    segment_sections,
)

logger = logging.getLogger(__name__)


@dataclass
class PDFAcquisition:
    """Resultado de uma tentativa completa de obtenção de PDF."""

    success: bool
    file_path: Optional[str] = None
    resolved_url: str = ""
    strategy: str = ""
    label: str = ""
    size_bytes: int = 0
    sha256: str = ""
    page_count: int = 0
    is_scanned: bool = False
    text_chars: int = 0
    message: str = ""
    attempts: list[ResolutionAttempt] = field(default_factory=list)

    def attempts_json(self) -> str:
        return json.dumps([a.to_dict() for a in self.attempts], ensure_ascii=False)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "pdf_path": self.file_path,
            "resolved_url": self.resolved_url,
            "strategy": self.strategy,
            "label": self.label,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "page_count": self.page_count,
            "is_scanned": self.is_scanned,
            "text_chars": self.text_chars,
            "message": self.message,
            "attempts": [a.to_dict() for a in self.attempts],
        }


class PDFService:
    """Serviço de download, armazenamento e extração de texto de PDFs."""

    def __init__(self, contact_email: Optional[str] = None):
        self.storage_dir = settings.pdf_storage_dir
        self.contact_email = (
            contact_email if contact_email is not None else settings.contact_email
        )

    # ── Armazenamento ─────────────────────────────────────────────────

    def get_project_pdf_dir(self, project_id: str) -> Path:
        """Diretório exclusivo de PDFs do projeto."""
        proj_dir = self.storage_dir / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        return proj_dir

    def get_pdf_path(self, project_id: str, paper_id: str) -> Path:
        return self.get_project_pdf_dir(project_id) / f"{paper_id}.pdf"

    def _text_cache_path(self, pdf_path: str) -> Path:
        return Path(pdf_path).with_suffix(".txt")

    def _invalidate_text_cache(self, pdf_path: str) -> None:
        cache = self._text_cache_path(pdf_path)
        if cache.exists():
            try:
                cache.unlink()
            except OSError as exc:
                logger.warning("[PDFService] Não foi possível limpar o cache de texto: %s", exc)

    def save_pdf_bytes(self, project_id: str, paper_id: str, content: bytes) -> str:
        """Grava os bytes do PDF e invalida o cache de texto anterior."""
        target_path = self.get_pdf_path(project_id, paper_id)
        target_path.write_bytes(content)
        self._invalidate_text_cache(str(target_path))
        return str(target_path)

    def save_uploaded_pdf(self, project_id: str, paper_id: str, file_bytes: bytes) -> str:
        """Salva um PDF enviado manualmente pelo usuário (com validação)."""
        if not is_pdf_bytes(file_bytes):
            raise ValueError(
                "O arquivo enviado não é um PDF válido (assinatura %PDF ausente)."
            )
        return self.save_pdf_bytes(project_id, paper_id, file_bytes)

    def delete_pdf(self, project_id: str, paper_id: str, pdf_path: Optional[str] = None) -> bool:
        """Remove o arquivo e seu cache de texto. Retorna se algo foi apagado."""
        path = Path(pdf_path) if pdf_path else self.get_pdf_path(project_id, paper_id)
        removed = False
        if path.exists():
            try:
                path.unlink()
                removed = True
            except OSError as exc:
                logger.warning("[PDFService] Falha ao remover %s: %s", path, exc)
        self._invalidate_text_cache(str(path))
        return removed

    @staticmethod
    def sha256_of(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    # ── Aquisição ─────────────────────────────────────────────────────

    async def acquire_pdf(
        self,
        project_id: str,
        paper_id: str,
        ref: PaperRef,
        client: Optional[httpx.AsyncClient] = None,
    ) -> PDFAcquisition:
        """
        Busca o PDF por todas as vias disponíveis, valida e persiste.

        Nunca lança em caso de falha de rede: devolve `success=False` com a
        trilha completa de tentativas, que é o que a interface precisa mostrar.
        """
        resolver = PDFResolver(contact_email=self.contact_email)
        resolved, attempts = await resolver.acquire(ref, client=client)

        if not resolved:
            return PDFAcquisition(
                success=False,
                attempts=attempts,
                message=self._failure_message(ref, attempts),
            )

        file_path = self.save_pdf_bytes(project_id, paper_id, resolved.content)
        document = extract_document(file_path)

        return PDFAcquisition(
            success=True,
            file_path=file_path,
            resolved_url=resolved.url,
            strategy=resolved.strategy,
            label=resolved.label,
            size_bytes=len(resolved.content),
            sha256=self.sha256_of(resolved.content),
            page_count=document.page_count,
            is_scanned=document.is_scanned,
            text_chars=document.char_count,
            attempts=attempts,
            message=(
                f"PDF obtido via {resolved.strategy} — {document.page_count} página(s)."
                + (
                    " Atenção: o documento parece digitalizado (imagem), sem texto"
                    " selecionável — a extração assistida usará apenas o resumo."
                    if document.is_scanned
                    else ""
                )
            ),
        )

    async def find_candidates(
        self,
        ref: PaperRef,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[PDFCandidate]:
        """Modo diagnóstico: lista os links candidatos sem baixar nada."""
        resolver = PDFResolver(contact_email=self.contact_email)
        return await resolver.find_candidates(ref, client=client)

    async def download_pdf(
        self, project_id: str, paper_id: str, download_url: str
    ) -> Optional[str]:
        """
        Compatibilidade com o fluxo antigo: baixa a partir de uma URL única.

        Mantido porque chamadores externos e testes dependem desta assinatura;
        internamente já passa pelo resolvedor, então uma landing page continua
        levando ao PDF.
        """
        if not download_url:
            return None
        result = await self.acquire_pdf(
            project_id, paper_id, PaperRef(download_url=download_url)
        )
        return result.file_path if result.success else None

    def _failure_message(self, ref: PaperRef, attempts: list[ResolutionAttempt]) -> str:
        """Mensagem acionável — o usuário precisa saber o que fazer em seguida."""
        if not attempts:
            return (
                "Nenhum candidato a PDF foi encontrado. Este registro não tem DOI nem "
                "URL de origem utilizável — informe um link direto ou anexe o arquivo."
            )

        blocked = [a for a in attempts if a.http_status in (401, 402, 403)]
        html_only = [a for a in attempts if a.status == "nao_pdf"]
        not_found = [a for a in attempts if a.http_status == 404]

        if blocked:
            return (
                f"{len(attempts)} caminho(s) tentado(s). O texto completo existe, mas está "
                "atrás de assinatura ou bloqueio antirrobô. Acesse pelo navegador "
                "(com o acesso da sua instituição) e anexe o arquivo manualmente."
            )
        if html_only:
            return (
                f"{len(attempts)} caminho(s) tentado(s). As fontes devolveram páginas HTML, "
                "não o arquivo. Abra o link de origem, copie o endereço direto do PDF e "
                "use a opção 'Link', ou anexe o arquivo baixado."
            )
        if not_found:
            return (
                f"{len(attempts)} caminho(s) tentado(s), sem arquivo disponível nos "
                "endereços conhecidos. Verifique se o trabalho é de acesso aberto."
            )
        return (
            f"{len(attempts)} caminho(s) tentado(s) sem sucesso. Consulte a trilha de "
            "tentativas para ver o que cada fonte respondeu."
        )

    # ── Leitura ───────────────────────────────────────────────────────

    def read_document(self, file_path: str, use_cache: bool = True) -> PDFDocument:
        """
        Lê o documento com cache em disco.

        O cache evita reextrair um PDF de 40 páginas a cada troca de aba na
        interface — o custo estava sendo pago em toda chamada de `/pdf/text`.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {file_path}")

        cache_path = self._text_cache_path(file_path)
        if use_cache and cache_path.exists():
            try:
                if cache_path.stat().st_mtime >= os.path.getmtime(file_path):
                    payload = json.loads(cache_path.read_text(encoding="utf-8"))
                    return _document_from_cache(payload)
            except (OSError, ValueError, KeyError) as exc:
                logger.debug("[PDFService] Cache de texto inválido (%s): %s", cache_path, exc)

        document = extract_document(file_path)
        try:
            cache_path.write_text(
                json.dumps(_document_to_cache(document), ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.debug("[PDFService] Não foi possível gravar cache de texto: %s", exc)
        return document

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Texto integral limpo do PDF (assinatura preservada da versão anterior)."""
        return self.read_document(file_path).text

    def get_sections(self, file_path: str) -> list[dict]:
        """Seções canônicas (IMRaD) detectadas no documento."""
        document = self.read_document(file_path)
        return [
            {
                "key": section.key,
                "title": section.title,
                "start_page": section.start_page,
                "char_count": len(section.text),
            }
            for section in segment_sections(document)
        ]

    def build_ai_context(
        self,
        file_path: str,
        questions: list[str],
        budget_chars: Optional[int] = None,
    ) -> str:
        """Contexto orientado às perguntas, dentro do orçamento configurado."""
        document = self.read_document(file_path)
        return build_question_context(
            document,
            questions,
            budget_chars=budget_chars or settings.ai_context_budget_chars,
        )

    def extract_key_sections(self, full_text: str, max_chars: int = 15000) -> str:
        """
        Recorte de fallback quando só há texto solto (sem documento paginado).

        Preserva a assinatura antiga por compatibilidade, mas agora corta em
        limite de parágrafo em vez de no meio de uma frase.
        """
        if len(full_text) <= max_chars:
            return full_text

        half = max_chars // 2
        beginning = _cut_on_paragraph(full_text[:half])
        ending = _cut_on_paragraph(full_text[-half:], from_start=False)
        return (
            f"{beginning}\n\n[... SEÇÕES INTERMEDIÁRIAS OMITIDAS POR LIMITE DE CONTEXTO ...]\n\n"
            f"{ending}"
        )


def _cut_on_paragraph(text: str, from_start: bool = True) -> str:
    """Ajusta o corte para a fronteira de parágrafo mais próxima."""
    if from_start:
        index = text.rfind("\n\n")
        return text[:index].strip() if index > len(text) * 0.5 else text.strip()
    index = text.find("\n\n")
    return text[index:].strip() if 0 <= index < len(text) * 0.5 else text.strip()


def _document_to_cache(document: PDFDocument) -> dict:
    return {
        "engine": document.engine,
        "title": document.title,
        "page_count": document.page_count,
        "is_scanned": document.is_scanned,
        "error": document.error,
        "pages": [{"number": p.number, "text": p.text} for p in document.pages],
    }


def _document_from_cache(payload: dict) -> PDFDocument:
    from app.services.pdf_text import PDFPage

    return PDFDocument(
        pages=[PDFPage(number=p["number"], text=p["text"]) for p in payload.get("pages", [])],
        engine=payload.get("engine", ""),
        title=payload.get("title", ""),
        page_count=payload.get("page_count", 0),
        is_scanned=payload.get("is_scanned", False),
        error=payload.get("error", ""),
    )
