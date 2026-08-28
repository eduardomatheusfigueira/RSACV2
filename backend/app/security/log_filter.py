#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Filtro de log que mascara credenciais (doc 29 §29.4.4).

Rede de segurança, não a defesa principal. A defesa é não escrever segredo em
log; este filtro existe para o caso em que alguém escreve mesmo assim — numa
mensagem de erro que ecoa o corpo da requisição, num `repr` de configuração,
num `exc_info` de biblioteca de terceiros.

O arquivo `harvest.log` fica na pasta de dados do usuário, é copiado junto em
backups e costuma ser anexado em pedidos de suporte. Uma chave que vaze para
lá viaja bem mais longe do que o banco.
"""

from __future__ import annotations

import logging
import re

# Padrões dos provedores realmente usados pelo Revsist, mais o cabeçalho de
# autorização e o token de sessão do próprio app.
PADROES = [
    re.compile(r"AIzaSy[0-9A-Za-z_\-]{20,}"),                      # Google Gemini
    re.compile(r"\bsk-[0-9A-Za-z_\-]{16,}"),                       # OpenAI-compatível / Qwen
    re.compile(r"(?i)\bBearer\s+[0-9A-Za-z._\-]{16,}"),            # Authorization
    re.compile(r"(?i)(api[_-]?key\"?\s*[:=]\s*\"?)([0-9A-Za-z._\-]{16,})"),
]

MASCARA = "«segredo-mascarado»"


def mascarar(texto: str) -> str:
    """Substitui credenciais reconhecíveis pela máscara."""
    if not texto:
        return texto

    resultado = texto
    for padrao in PADROES:
        if padrao.groups >= 2:
            # Preserva o rótulo (`api_key=`) e mascara só o valor, para que a
            # linha continue legível a quem depura.
            resultado = padrao.sub(lambda m: f"{m.group(1)}{MASCARA}", resultado)
        else:
            resultado = padrao.sub(MASCARA, resultado)
    return resultado


class SecretMaskingFilter(logging.Filter):
    """
    Mascara credenciais na mensagem e nos argumentos de cada registro.

    Interpola a mensagem aqui (`record.getMessage()`) e zera `record.args`
    porque mascarar só o formato deixaria passar o segredo que viesse pelo
    argumento — que é o caso mais comum: `logger.error("falhou: %s", chave)`.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            mensagem = record.getMessage()
        except (TypeError, ValueError):  # pragma: no cover — formato inválido
            return True

        mascarada = mascarar(mensagem)
        if mascarada != mensagem:
            record.msg = mascarada
            record.args = ()

        return True


def instalar_filtro_de_segredos() -> None:
    """Aplica o filtro a todos os manipuladores do logger raiz."""
    filtro = SecretMaskingFilter()
    raiz = logging.getLogger()
    for handler in raiz.handlers:
        if not any(isinstance(f, SecretMaskingFilter) for f in handler.filters):
            handler.addFilter(filtro)
