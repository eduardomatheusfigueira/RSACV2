#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Fábrica de parser de HTML tolerante a ambiente.

Os coletores SciELO e BDTD raspam HTML com `BeautifulSoup(html, "lxml")`. O
`lxml` é referenciado **apenas por string**, então nenhuma análise estática
(PyInstaller incluído) enxerga a dependência: no executável empacotado o
parser some e `BeautifulSoup` levanta `FeatureNotFound`, zerando a coleta das
duas fontes que dependem de raspagem.

Este módulo:
  1. importa `lxml` explicitamente, tornando a dependência visível ao
     empacotador;
  2. degrada para `html.parser` (biblioteca padrão) quando o `lxml` não está
     disponível, em vez de derrubar a coleta.
"""

import logging
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

try:  # Importação explícita: torna a dependência visível a empacotadores.
    import lxml  # noqa: F401
    import lxml.etree  # noqa: F401

    LXML_DISPONIVEL = True
except Exception:  # pragma: no cover - depende do ambiente de execução
    LXML_DISPONIVEL = False

_aviso_emitido = False


def parser_preferido() -> str:
    """Nome do parser de HTML efetivamente utilizável neste ambiente."""
    return "lxml" if LXML_DISPONIVEL else "html.parser"


def make_soup(html: str, parser: Optional[str] = None) -> BeautifulSoup:
    """
    Constrói um `BeautifulSoup` com o melhor parser disponível.

    Prefere `lxml` (mais rápido e tolerante a HTML malformado) e cai para
    `html.parser` quando ele não está instalado ou não pôde ser carregado.
    """
    global _aviso_emitido

    escolhido = parser or parser_preferido()
    try:
        return BeautifulSoup(html or "", escolhido)
    except Exception as exc:
        if escolhido != "html.parser":
            if not _aviso_emitido:
                logger.warning(
                    "[HTML] Parser '%s' indisponível (%s). Usando 'html.parser' da "
                    "biblioteca padrão — a raspagem continua, com desempenho menor.",
                    escolhido,
                    exc,
                )
                _aviso_emitido = True
            return BeautifulSoup(html or "", "html.parser")
        raise
