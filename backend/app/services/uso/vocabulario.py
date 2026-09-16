#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Vocabulário fechado dos eventos de uso (doc 52 §6.2, princípio P3).

Mesmo desenho do `ropa_service`: a garantia de que o conteúdo da pesquisa não
entra nos registros de uso não depende de quem instrumenta a interface lembrar
de não mandá-lo. Depende de não existir por onde passar. Um evento só é
gravado se o nome estiver em `vocabulario.json`, e cada propriedade só se o
valor couber no tipo declarado — enum, inteiro com limites, faixa ou booleano.
Texto livre não é um tipo.

Dois modos:

  * **normal**, usado na ingestão: o que não cabe é descartado e contado. Uma
    versão antiga da interface mandando um evento aposentado não pode virar
    erro 500 para quem só estava usando a plataforma;
  * **estrito**, usado nos testes e na emissão pelo próprio servidor: o que
    não cabe levanta, porque ali é erro de programação.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

ARQUIVO = Path(__file__).with_name("vocabulario.json")

TIPOS_DE_PROPRIEDADE = frozenset({"enum", "int", "faixa", "bool"})
NIVEIS = frozenset({"A", "B"})


class EventoInvalido(ValueError):
    """Evento fora do vocabulário, no modo estrito."""


@dataclass(frozen=True)
class EventoValido:
    nome: str
    nivel: str
    tela: str | None
    propriedades: dict[str, Any] = field(default_factory=dict)


@lru_cache(maxsize=1)
def carregar() -> dict:
    with ARQUIVO.open(encoding="utf-8") as f:
        return json.load(f)


def telas() -> list[str]:
    return list(carregar()["telas"])


def alvos() -> list[str]:
    return list(carregar()["alvos"])


def eventos() -> dict[str, dict]:
    return dict(carregar()["eventos"])


def faixa(n: int) -> str:
    """Contagem exata → faixa. Reduz a chance de reconhecer um projeto pelos números."""
    if n <= 0:
        return "0"
    if n <= 10:
        return "1-10"
    if n <= 100:
        return "11-100"
    if n <= 1000:
        return "101-1000"
    return ">1000"


def _valores_do_enum(spec: dict) -> list[str]:
    valores = list(spec.get("valores") or [])
    ref = spec.get("ref")
    if ref:
        valores += list(carregar()[ref])
    valores += list(spec.get("extras") or [])
    return valores


def _validar_valor(spec: dict, valor: Any) -> bool:
    tipo = spec.get("tipo")
    if tipo == "enum":
        return isinstance(valor, str) and valor in _valores_do_enum(spec)
    if tipo == "int":
        # `bool` é subclasse de `int` em Python; `True` não é uma contagem.
        if isinstance(valor, bool) or not isinstance(valor, int):
            return False
        return spec.get("min", 0) <= valor <= spec.get("max", 2**31 - 1)
    if tipo == "faixa":
        return isinstance(valor, str) and valor in carregar()["faixas"]
    if tipo == "bool":
        return isinstance(valor, bool)
    return False


def validar(
    nome: Any,
    tela: Any = None,
    propriedades: Any = None,
    *,
    estrito: bool = False,
) -> tuple[EventoValido | None, str]:
    """
    Devolve `(evento, "")` quando cabe no vocabulário, ou `(None, motivo)`.

    O motivo é uma **categoria** ("nome_desconhecido", "propriedade_invalida"),
    nunca o valor recusado: o log de descarte não pode virar o lugar onde o
    conteúdo que se tentou mandar sobrevive.
    """

    def recusar(motivo: str) -> tuple[None, str]:
        if estrito:
            raise EventoInvalido(motivo)
        return None, motivo

    catalogo = eventos()
    if not isinstance(nome, str) or nome not in catalogo:
        return recusar("nome_desconhecido")
    spec = catalogo[nome]

    if tela is not None and (not isinstance(tela, str) or tela not in telas()):
        return recusar("tela_desconhecida")

    props = propriedades if propriedades is not None else {}
    if not isinstance(props, dict):
        return recusar("propriedades_nao_objeto")

    declaradas: dict = spec.get("propriedades", {})
    for chave, valor in props.items():
        if chave not in declaradas:
            return recusar("propriedade_desconhecida")
        if not _validar_valor(declaradas[chave], valor):
            return recusar("propriedade_invalida")

    return EventoValido(nome=nome, nivel=spec["nivel"], tela=tela, propriedades=dict(props)), ""


def problemas_do_catalogo() -> list[str]:
    """
    Confere o próprio vocabulário contra as regras do doc 52. Vazio = saudável.

    Fica aqui, e não só no teste, para que o gerador de tipos do frontend
    possa recusar um vocabulário quebrado antes de gerar qualquer coisa.
    """
    problemas: list[str] = []
    for nome, spec in eventos().items():
        if spec.get("nivel") not in NIVEIS:
            problemas.append(f"{nome}: nível fora de {sorted(NIVEIS)}")
        if not spec.get("perguntas"):
            problemas.append(f"{nome}: sem pergunta que o justifique (P1)")
        if not str(spec.get("descricao_publica", "")).strip():
            problemas.append(f"{nome}: sem descrição pública")
        for chave, prop in (spec.get("propriedades") or {}).items():
            if prop.get("tipo") not in TIPOS_DE_PROPRIEDADE:
                problemas.append(f"{nome}.{chave}: tipo {prop.get('tipo')!r} não permitido (P3)")
            if prop.get("tipo") == "enum" and not _valores_do_enum(prop):
                problemas.append(f"{nome}.{chave}: enum sem valores")
    return problemas
