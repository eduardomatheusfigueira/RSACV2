#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Cliente HTTP com guarda de saída (doc 29 §29.5.3).

`follow_redirects=True` do httpx é conveniente e, aqui, inseguro: um host
público que responde `302 Location: http://169.254.169.254/` contorna qualquer
validação feita apenas na URL inicial. Este módulo troca a conveniência por
seguimento manual, revalidando **cada salto**.

O custo é uma função a mais no caminho de rede; o benefício é que o guarda
deixa de ser contornável por um cabeçalho de resposta.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urljoin

import httpx

from app.security.egress import MAX_REDIRECIONAMENTOS, EgressBlocked, validar_url

logger = logging.getLogger(__name__)

# Códigos que pedem para o cliente ir a outro lugar.
CODIGOS_DE_REDIRECIONAMENTO = frozenset({301, 302, 303, 307, 308})


async def request_com_guarda(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    permitir_loopback: Optional[bool] = None,
    max_saltos: int = MAX_REDIRECIONAMENTOS,
    **kwargs,
) -> httpx.Response:
    """
    Faz a requisição validando a URL e cada redirecionamento.

    Levanta `EgressBlocked` se qualquer salto apontar para destino proibido —
    inclusive quando o primeiro era legítimo. O chamador deve tratar isso como
    uma tentativa falha, não como erro de rede.
    """
    alvo = url
    vistos: set[str] = set()

    for salto in range(max_saltos + 1):
        validar_url(alvo, permitir_loopback=permitir_loopback)

        if alvo in vistos:
            raise EgressBlocked(alvo, "laço de redirecionamento")
        vistos.add(alvo)

        resposta = await client.request(method, alvo, follow_redirects=False, **kwargs)

        if resposta.status_code not in CODIGOS_DE_REDIRECIONAMENTO:
            return resposta

        destino = resposta.headers.get("location")
        if not destino:
            return resposta

        # `Location` pode ser relativo; resolver contra a URL corrente é o que
        # o navegador faria, e é sobre o resultado disso que o guarda decide.
        anterior = alvo
        alvo = urljoin(alvo, destino)
        await resposta.aclose()

        logger.debug("[Egress] Redirecionamento %d: %s -> %s", salto + 1, anterior, alvo)

    raise EgressBlocked(alvo, f"mais de {max_saltos} redirecionamentos")


async def get_com_guarda(
    client: httpx.AsyncClient,
    url: str,
    *,
    permitir_loopback: Optional[bool] = None,
    **kwargs,
) -> httpx.Response:
    """Atalho para `GET`, que é o que o resolvedor de PDF usa."""
    return await request_com_guarda(
        client, "GET", url, permitir_loopback=permitir_loopback, **kwargs
    )
