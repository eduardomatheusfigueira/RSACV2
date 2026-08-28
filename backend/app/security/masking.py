#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Mascaramento de Segredos (doc 29 §29.4.2).

Nenhuma resposta da API devolve chave de API em texto claro. O que sobe para a
interface é a máscara: o suficiente para o usuário reconhecer *qual* chave está
configurada, insuficiente para alguém usá-la.

A função vivia em `api/v1/settings.py` e valia só para as credenciais de bases
científicas — enquanto `/ai/settings` e `/profile/keys/export` devolviam as
chaves inteiras. Trazer para cá é o que permite aplicar a mesma regra em todos
os pontos de leitura.
"""

from typing import Iterable, Optional

# Quantos caracteres do fim permanecem visíveis. Quatro bastam para o usuário
# distinguir duas chaves suas e são pouco demais para reconstruir qualquer uma.
VISIBLE_SUFFIX = 4


def mask_secret(secret: Optional[str]) -> str:
    """
    Devolve a máscara de um segredo: `••••••••` seguido dos 4 últimos
    caracteres. Segredo vazio devolve string vazia; segredo curto demais para
    revelar qualquer parte devolve máscara sem sufixo.
    """
    if not secret:
        return ""
    clean = secret.strip()
    if not clean:
        return ""
    if len(clean) <= VISIBLE_SUFFIX:
        return "••••"
    return "••••••••" + clean[-VISIBLE_SUFFIX:]


def mask_secret_list(secrets: Optional[Iterable[str]]) -> list[str]:
    """Máscara de cada segredo de uma lista, preservando a ordem."""
    if not secrets:
        return []
    return [mask_secret(s) for s in secrets if s and str(s).strip()]
