#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Ocorrências de erro sanitizadas (doc 52 §5.4).

Um erro é o lugar mais provável de o conteúdo da pesquisa vazar para os dados
de uso sem ninguém perceber: `KeyError: 'Segurança pública em fronteiras'`
carrega o título de um estudo, e a mensagem de uma `IntegrityError` carrega os
parâmetros da consulta. Por isso a sanitização roda **no servidor**, sempre —
mesmo que o navegador já a tenha feito —, e o que sobra dela é o que pode
existir no banco.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Optional

from app.security.log_filter import mascarar

MAX_MENSAGEM = 300
MAX_QUADROS = 10

# Tipos cuja mensagem nunca é gravada: carregam parâmetros de consulta,
# valores de linha ou caminhos de arquivo do servidor.
TIPOS_SO_O_NOME = (
    "IntegrityError",
    "OperationalError",
    "ProgrammingError",
    "DataError",
    "StatementError",
    "DBAPIError",
    "FileNotFoundError",
    "PermissionError",
)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_URL = re.compile(r"\b(?:https?|ftp|file)://\S+", re.IGNORECASE)
_ENTRE_ASPAS = re.compile(r"(['\"`“”‘’«»]).*?(\1|[”’»])", re.DOTALL)
_DIGITOS = re.compile(r"\d{6,}")
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
_CAMINHO_WINDOWS = re.compile(r"[A-Za-z]:\\[^\s:]+")
_CAMINHO_POSIX = re.compile(r"(?<![\w.])/(?:[\w.-]+/)+[\w.-]+")

# Um quadro de pilha útil é `arquivo:linha` com função opcional. Aceita as
# formas do Python (`File "x.py", line 3, in f`) e do navegador
# (`at f (x.js:3:7)`, `f@x.js:3:7`), e descarta o resto.
_QUADRO_PY = re.compile(r'File "(?P<arq>[^"]+)", line (?P<lin>\d+)(?:, in (?P<fun>[\w<>.]+))?')
_QUADRO_JS = re.compile(
    r"(?P<arq>[\w./@-]+\.(?:js|jsx|ts|tsx|mjs|py)):(?P<lin>\d+)(?::\d+)?"
)
# A função vem antes do endereço: `at triar (https://…)` no Chromium,
# `triar@https://…` no Firefox e no Safari.
_FUNCAO_JS = re.compile(r"^\s*(?:at\s+(?P<v8>[\w$.<>]+)\s+\(|(?P<gecko>[\w$.<>]+)@)")

ORIGENS = ("cliente", "servidor")


@dataclass(frozen=True)
class OcorrenciaSanitizada:
    impressao: str
    tipo: str
    mensagem: str
    pilha: str


def _nome_curto(arquivo: str) -> str:
    """Só o que identifica o módulo do app: nada de diretório do servidor ou do usuário."""
    arquivo = arquivo.replace("\\", "/").split("?")[0]
    for marco in ("/app/", "/src/", "/assets/"):
        if marco in arquivo:
            return marco.strip("/") + "/" + arquivo.split(marco, 1)[1]
    return arquivo.rsplit("/", 1)[-1]


def sanitizar_mensagem(tipo: str, mensagem: Optional[str]) -> str:
    if any(tipo.endswith(t) for t in TIPOS_SO_O_NOME):
        return ""
    texto = mascarar(str(mensagem or ""))
    texto = _URL.sub("‹url›", texto)
    texto = _EMAIL.sub("‹email›", texto)
    texto = _ENTRE_ASPAS.sub("‹texto›", texto)
    texto = _UUID.sub("‹id›", texto)
    texto = _CAMINHO_WINDOWS.sub("‹caminho›", texto)
    texto = _CAMINHO_POSIX.sub("‹caminho›", texto)
    texto = _DIGITOS.sub("‹n›", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:MAX_MENSAGEM]


def sanitizar_pilha(pilha: Optional[str]) -> list[str]:
    quadros: list[str] = []
    for linha in str(pilha or "").splitlines():
        achado = _QUADRO_PY.search(linha)
        if achado:
            funcao = achado.group("fun") or "?"
        else:
            achado = _QUADRO_JS.search(linha)
            if not achado:
                continue
            nome = _FUNCAO_JS.search(linha)
            funcao = (nome.group("v8") or nome.group("gecko")) if nome else "?"
        arquivo = _nome_curto(achado.group("arq"))
        quadros.append(f"{arquivo}:{achado.group('lin')}:{funcao}")
        if len(quadros) >= MAX_QUADROS:
            break
    return quadros


def _tipo_limpo(tipo: Optional[str]) -> str:
    limpo = re.sub(r"[^\w.:]", "", str(tipo or "Erro"))[:80]
    return limpo or "Erro"


def impressao_digital(tipo: str, quadros: list[str]) -> str:
    """
    Agrupa ocorrências do mesmo defeito.

    Tipo mais o primeiro quadro **do próprio app**, sem o número da linha: uma
    linha em branco acrescentada acima não pode transformar o mesmo erro em
    outro depois de cada deploy.
    """
    do_app = next((q for q in quadros if q.startswith(("app/", "src/", "assets/"))), quadros[0] if quadros else "")
    ancora = re.sub(r":\d+:", "::", do_app)
    return hashlib.sha256(f"{tipo}|{ancora}".encode("utf-8")).hexdigest()


def sanitizar(tipo: Optional[str], mensagem: Optional[str], pilha: Optional[str]) -> OcorrenciaSanitizada:
    tipo_ok = _tipo_limpo(tipo)
    quadros = sanitizar_pilha(pilha)
    return OcorrenciaSanitizada(
        impressao=impressao_digital(tipo_ok, quadros),
        tipo=tipo_ok,
        mensagem=sanitizar_mensagem(tipo_ok, mensagem),
        pilha="\n".join(quadros),
    )


def familia_do_navegador(user_agent: Optional[str]) -> str:
    """`edge 131`, `firefox 129`… — nunca a string completa do agente."""
    ua = str(user_agent or "")
    for rotulo, padrao in (
        ("edge", r"Edg/(\d+)"),
        ("electron", r"Electron/(\d+)"),
        ("firefox", r"Firefox/(\d+)"),
        ("chrome", r"Chrome/(\d+)"),
        ("safari", r"Version/(\d+).*Safari"),
    ):
        achado = re.search(padrao, ua)
        if achado:
            return f"{rotulo} {achado.group(1)}"
    return "outro" if ua else ""
