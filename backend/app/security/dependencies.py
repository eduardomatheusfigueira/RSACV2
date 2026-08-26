#!/usr/bin/env python

"""
RSAC V2 — Autenticação por token local (doc 29 §29.3, revisto no doc 37).

A decisão de projeto que mais importa aqui não é *como* a credencial é
validada, e sim *onde* a validação é ligada: `require_local_token` entra como
dependência do router agregador, não como decorador rota a rota. Assim o padrão
é "protegido" e o esquecimento falha fechado — uma rota nova nasce exigindo a
credencial sem que o autor precise lembrar de nada. A exceção é uma lista curta
e explícita, em `app/api/v1/router.py`.

**O que mudou.** Havia aqui contas, senhas Argon2 e sessões com cookie, porque
o backend também podia ser publicado por túnel, e ali a prova de identidade
tinha de ser algo que viajasse pela internet. Sem publicação, o perímetro é o
sistema de arquivos da máquina: quem consegue ler `runtime_token` — um arquivo
`0600` na pasta do usuário — já tem acesso à conta do sistema operacional, e
portanto ao banco, aos PDFs e à chave-mestra. Uma senha por cima disso não
acrescentava barreira, só a tela de login que o app de mesa passava a vida
tentando contornar.

O token é apresentado de dois jeitos, pela mesma razão de sempre: o navegador
não deixa mandar cabeçalho personalizado ao abrir um WebSocket.

  * HTTP      — cabeçalho `X-RSAC-Local-Token`;
  * WebSocket — parâmetro `local_token` na query do handshake.
"""

from __future__ import annotations

import getpass
import logging
import re

from fastapi import HTTPException, WebSocket, status
from starlette.requests import HTTPConnection

from app.config import settings
from app.security.local_token import matches_local_token

logger = logging.getLogger(__name__)

# Cabeçalho pelo qual a interface apresenta o token local.
LOCAL_TOKEN_HEADER = "X-RSAC-Local-Token"

# Parâmetro equivalente na query, para o handshake do WebSocket.
LOCAL_TOKEN_QUERY = "local_token"


def extrair_token(request: HTTPConnection) -> str | None:
    """
    Recupera o token local da requisição.

    O cabeçalho tem precedência; a query só é consultada no escopo de
    WebSocket, onde o navegador não oferece outra via. Aceitar o parâmetro
    também em HTTP poria a credencial no endereço — e daí no histórico, no
    `Referer` e em qualquer captura de tela.
    """
    do_cabecalho = request.headers.get(LOCAL_TOKEN_HEADER)
    if do_cabecalho:
        return do_cabecalho.strip()

    if request.scope.get("type") == "websocket":
        return request.query_params.get(LOCAL_TOKEN_QUERY)

    return None


def require_local_token(request: HTTPConnection) -> None:
    """
    Exige o token local desta instalação. É a dependência global da API v1.

    Recebe `HTTPConnection` — a base comum de `Request` e `WebSocket` — e não
    `Request`: a dependência é declarada no router agregador, que também
    carrega as rotas de WebSocket, e essas não têm requisição HTTP. Declarar
    `Request` aqui derrubava o handshake com `TypeError` antes de qualquer
    verificação.

    No escopo de WebSocket a função sai de lado: quem decide lá é
    `require_websocket_local_token`, chamada dentro da rota, que consegue
    fechar a conexão com o código 1008 em vez de levantar uma exceção HTTP que
    ninguém traduziria.
    """
    if request.scope.get("type") == "websocket":
        return

    if not matches_local_token(extrair_token(request)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token local ausente ou inválido.",
        )


def requisicao_autenticada(request: HTTPConnection) -> bool:
    """Versão que não levanta, para a rota pública de status."""
    return matches_local_token(extrair_token(request))


def operador_local() -> str:
    """
    Nome a registrar na auditoria como autor de uma decisão.

    A trilha de auditoria de uma revisão sistemática precisa dizer de quem foi
    cada decisão — é parte do produto, não detalhe operacional. Com contas, o
    nome vinha da conta; sem elas, quem opera é o dono da sessão do sistema
    operacional, e é esse o nome mais próximo da verdade que existe. Serve
    inclusive quando o banco é aberto noutra máquina depois: o histórico
    continua dizendo em que conta cada decisão foi tomada.
    """
    try:
        return getpass.getuser() or "local"
    except Exception:  # pragma: no cover — ambiente sem usuário resolvível
        return "local"


def origem_do_websocket_e_permitida(websocket: WebSocket) -> bool:
    """
    O `Origin` do handshake está entre as origens autorizadas? (§29.3.6)

    Metade indispensável da defesa contra sequestro entre sítios: a política de
    mesma origem **não** vale para WebSocket, então a credencial sozinha não
    basta — bastaria a página hostil adivinhar o endereço para abrir o canal.
    É o `Origin` que distingue a aplicação de um sítio qualquer.

    Cliente que não é navegador (o `TestClient`, um script) não manda `Origin`.
    Aceitar essa ausência é correto: o vetor que se está fechando existe apenas
    dentro do navegador, e é lá que o cabeçalho é obrigatório.
    """
    origem = websocket.headers.get("origin")
    if not origem:
        return True

    return re.match(settings.cors_allow_origin_regex, origem.rstrip("/")) is not None


async def require_websocket_local_token(websocket: WebSocket) -> bool:
    """
    Valida o token local no handshake do WebSocket.

    Devolve `True` quando o canal pode seguir. A checagem de `Origin` é feita
    antes, pela rota, via `origem_do_websocket_e_permitida`.
    """
    return matches_local_token(websocket.query_params.get(LOCAL_TOKEN_QUERY))
