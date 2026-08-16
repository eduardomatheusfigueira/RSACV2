#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Serviço de Processamento de PDFs e Extração de Texto Completo.
Utiliza PyMuPDF (fitz) com fallback para pypdf para extração de texto,
limpeza e divisão em seções relevantes para a Triagem 2 (Extração).
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class PDFService:
    """Serviço responsável por download, armazenamento e extração de texto de PDFs."""

    def __init__(self):
        self.storage_dir = settings.pdf_storage_dir

    def get_project_pdf_dir(self, project_id: str) -> Path:
        """Retorna o diretório exclusivo de PDFs do projeto."""
        proj_dir = self.storage_dir / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        return proj_dir

    async def download_pdf(self, project_id: str, paper_id: str, download_url: str) -> Optional[str]:
        """Faz o download do PDF a partir de uma URL e salva localmente."""
        if not download_url:
            return None

        proj_dir = self.get_project_pdf_dir(project_id)
        target_path = proj_dir / f"{paper_id}.pdf"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                res = await client.get(download_url, headers=headers)
                if res.status_code == 200 and ("application/pdf" in res.headers.get("content-type", "") or res.content[:4] == b"%PDF"):
                    with open(target_path, "wb") as f:
                        f.write(res.content)
                    logger.info(f"[PDFService] PDF baixado com sucesso: {target_path}")
                    return str(target_path)
                else:
                    logger.warning(f"[PDFService] URL não retornou um PDF válido: HTTP {res.status_code}")
                    return None
        except Exception as e:
            logger.error(f"[PDFService] Erro ao baixar PDF de {download_url}: {e}")
            return None

    def save_uploaded_pdf(self, project_id: str, paper_id: str, file_bytes: bytes) -> str:
        """Salva um PDF enviado manualmente pelo usuário."""
        proj_dir = self.get_project_pdf_dir(project_id)
        target_path = proj_dir / f"{paper_id}.pdf"
        with open(target_path, "wb") as f:
            f.write(file_bytes)
        return str(target_path)

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extrai o texto integral do arquivo PDF.
        Tenta PyMuPDF (fitz) primeiro; se falhar, tenta pypdf.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {file_path}")

        extracted_text = ""

        # 1. Tentar PyMuPDF (fitz)
        try:
            import fitz
            doc = fitz.open(file_path)
            pages = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pages.append(page.get_text())
            doc.close()
            extracted_text = "\n\n".join(pages).strip()
            if extracted_text:
                return extracted_text
        except Exception as e:
            logger.warning(f"[PDFService] PyMuPDF falhou ({e}), tentando pypdf...")

        # 2. Fallback para pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            extracted_text = "\n\n".join(pages).strip()
            return extracted_text
        except Exception as e:
            logger.error(f"[PDFService] Falha na extração com pypdf: {e}")

        return extracted_text

    def extract_key_sections(self, full_text: str, max_chars: int = 15000) -> str:
        """
        Resume ou seleciona as partes mais relevantes do texto (Metodologia, Resultados, Conclusão)
        para não estourar o limite de tokens da IA durante a extração de dados.
        """
        if len(full_text) <= max_chars:
            return full_text

        # Pegar primeiros 6000 caracteres (Introdução/Metodologia) e últimos 6000 (Resultados/Discussão)
        half = max_chars // 2
        beginning = full_text[:half]
        ending = full_text[-half:]
        return f"{beginning}\n\n[... SEÇÕES INTERMEDIÁRIAS OMITIDAS PARA CONTEXTO ...]\n\n{ending}"
