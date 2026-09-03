#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Bilhete de canal: a credencial que abre um WebSocket.

O problema que este módulo resolve
----------------------------------
Abrir um WebSocket no navegador é a única requisição em que **não se pode
mandar cabeçalho**: não há `Authorization`, não há como enviar o token de
sessão pelo caminho normal. Restam duas saídas, e as duas falham em algum
arranjo real:

1. **O cookie de sessão.** Ele é `SameSite=strict`, de propósito — é o que
   impede outra página aberta no navegador de abrir um canal com a credencial
   do pesquisador. Mas isso também o impede de viajar quando a interface está
   numa origem e a API em outra: `localhost:5173` e `127.0.0.1:8000` são sítios
   diferentes para o navegador, ainda que sejam a mesma máquina. É exatamente o
   arranjo do desenvolvimento e o de quem serve a interface separada da API.

2. **O token de sessão na query.** Funciona, mas o cliente só o tem quando a
   sessão foi aberta naquela aba: ele mora em `sessionStorage`, que é por aba.
   Uma aba duplicada, ou restaurada pelo navegador, herda o cookie e não o
   token — e fica sem como abrir o canal, embora as requisições comuns
   continuem funcionando pelo cookie.

O resultado prático era um canal que caía em silêncio: a triagem em lote seguia
no servidor, e a tela não recebia mais nada. Foi diagnosticado só depois de
medir `ouvintes_do_canal: 0` no servidor enquanto a tela dizia estar aberta.

A solução
---------
Um bilhete curto, pedido por uma requisição HTTP comum — que carrega o cookie
OU o token, o que houver — e usado uma única vez para abrir o canal. Não
substitui a sessão: é derivado dela, vale por instantes e não serve para mais
nada.

Por que não devolver o próprio token da sessão: ele é `HttpOnly` justamente
para que o JavaScript não o alcance. Entregá-lo ao cliente para resolver este
problema trocaria uma inconveniência por uma exposição permanente.
"""

import secrets
import time
from typing import Dict, Optional, Tuple

#: Validade do bilhete. Ele só precisa sobreviver ao intervalo entre pedir e
#: abrir o canal — milissegundos, na prática. Trinta segundos cobre uma rede
#: ruim sem virar uma credencial pendurada.
VALIDADE_SEGUNDOS = 30.0

#: Teto de bilhetes vivos. Cada um é minúsculo, mas sem limite um cliente em
#: laço de reconexão encheria a memória do processo.
LIMITE_DE_BILHETES = 2000

#: bilhete -> (user_id, expira_em)
_BILHETES: Dict[str, Tuple[str, float]] = {}


def _limpar_vencidos(agora: float) -> None:
    for chave in [b for b, (_, exp) in _BILHETES.items() if exp <= agora]:
        _BILHETES.pop(chave, None)


def emitir(user_id: str) -> str:
    """Cria um bilhete de uso único para o usuário informado."""
    agora = time.monotonic()
    _limpar_vencidos(agora)

    if len(_BILHETES) >= LIMITE_DE_BILHETES:
        # Descarta o mais próximo do vencimento: é o de menor valor.
        mais_velho = min(_BILHETES, key=lambda b: _BILHETES[b][1])
        _BILHETES.pop(mais_velho, None)

    bilhete = secrets.token_urlsafe(32)
    _BILHETES[bilhete] = (user_id, agora + VALIDADE_SEGUNDOS)
    return bilhete


def resgatar(bilhete: Optional[str]) -> Optional[str]:
    """Consome o bilhete e devolve o `user_id`, ou `None` se não vale.

    O consumo é o ponto: um bilhete só abre um canal. Reapresentá-lo — porque
    ficou no histórico, num log de proxy, na barra de endereços — não abre
    nada.
    """
    if not bilhete:
        return None

    agora = time.monotonic()
    _limpar_vencidos(agora)

    registro = _BILHETES.pop(bilhete, None)
    if not registro:
        return None

    user_id, expira_em = registro
    return user_id if expira_em > agora else None
