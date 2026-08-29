#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Dependências de autenticação e autorização (doc 29 §29.3.1, §29.3.4).

A decisão de projeto que mais importa aqui não é *como* a sessão é validada, e
sim *onde* a validação é ligada: `require_session` entra como dependência do
router agregador, não como decorador rota a rota. Assim o padrão é "protegido"
e o esquecimento falha fechado — uma rota nova nasce exigindo sessão sem que o
autor precise lembrar de nada.

A exceção é uma lista curta e explícita, em `app/api/v1/public.py`.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import Depends, HTTPException, WebSocket, status
from sqlalchemy.orm import Session
from starlette.requests import HTTPConnection

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import ProjectModel, UserModel
from app.security.local_token import matches_local_token
from app.security.sessions import SESSION_COOKIE, resolve_session

logger = logging.getLogger(__name__)

# Cabeçalho pelo qual o app de mesa apresenta o token local (§29.3.2).
LOCAL_TOKEN_HEADER = "X-RSAC-Local-Token"

ROLE_OWNER = "owner"
ROLE_RESEARCHER = "researcher"
ROLES_VALIDOS = (ROLE_OWNER, ROLE_RESEARCHER)


def extrair_token(request: HTTPConnection) -> Optional[str]:
    """
    Recupera o token de sessão da requisição.

    Duas vias, por necessidade real: o cookie atende a SPA servida pelo próprio
    backend (o caso do túnel), e o cabeçalho `Authorization` atende o cliente
    hospedado em outra origem — Netlify, ou o Vite em `:5173` durante o
    desenvolvimento — onde um cookie `SameSite=Strict` não seria enviado.
    """
    cabecalho = request.headers.get("Authorization", "")
    if cabecalho.lower().startswith("bearer "):
        token = cabecalho[7:].strip()
        if token:
            return token
    return request.cookies.get(SESSION_COOKIE)


def _usuario_do_token_local(db: Session, request: HTTPConnection) -> Optional[UserModel]:
    """
    Resolve o token local do perfil desktop para a conta dona da instalação.

    Quem tem o token já tem acesso ao sistema de arquivos do usuário, então
    exigir senha por cima disso não acrescentaria barreira — só atrito.
    """
    candidato = request.headers.get(LOCAL_TOKEN_HEADER)
    if not matches_local_token(candidato):
        return None
    return (
        db.query(UserModel)
        .filter(UserModel.is_active == True)  # noqa: E712 — coluna SQL
        .order_by(UserModel.created_at.asc())
        .first()
    )


def usuario_atual_opcional(
    request: HTTPConnection,
    db: Session = Depends(get_db),
) -> Optional[UserModel]:
    """Usuário autenticado, ou `None`. Não levanta — para rotas de status."""
    usuario = resolve_session(db, extrair_token(request))
    if usuario:
        return usuario
    return _usuario_do_token_local(db, request)


def require_session(
    request: HTTPConnection,
    db: Session = Depends(get_db),
) -> Optional[UserModel]:
    """
    Exige uma identidade autenticada. É a dependência global da API v1.

    Recebe `HTTPConnection` — a base comum de `Request` e `WebSocket` — e não
    `Request`: a dependência é declarada no router agregador, que também carrega
    as rotas de WebSocket, e essas não têm requisição HTTP. Declarar `Request`
    aqui derrubava o handshake com `TypeError` antes de qualquer verificação.

    No escopo de WebSocket a função sai de lado: quem decide lá é
    `require_websocket_session`, chamada dentro da rota, que consegue fechar a
    conexão com o código 1008 em vez de levantar uma exceção HTTP que ninguém
    traduziria. `tests/test_security/test_websocket_auth.py` cobre cada canal.
    """
    if request.scope.get("type") == "websocket":
        return None

    usuario = usuario_atual_opcional(request, db)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.usuario = usuario
    return usuario


def require_owner(usuario: Optional[UserModel] = Depends(require_session)) -> UserModel:
    """
    Exige papel `owner` (§29.3.4).

    Usado nas rotas que leem ou gravam credenciais: um colaborador convidado
    para triar estudos não tem por que alcançar as chaves de API de quem
    convidou — nem mascaradas.
    """
    if usuario is None or usuario.role != ROLE_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operação exige uma conta administradora (owner).",
        )
    return usuario


def origem_do_websocket_e_permitida(websocket: WebSocket) -> bool:
    """
    O `Origin` do handshake está entre as origens autorizadas? (§29.3.6)

    Metade indispensável da defesa contra sequestro entre sítios: a política de
    mesma origem **não** vale para WebSocket, então a sessão sozinha não basta
    — o navegador do pesquisador enviaria o cookie de sessão junto com uma
    conexão aberta por qualquer página. É o `Origin` que distingue a aplicação
    de um sítio hostil usando as credenciais dela.

    Cliente que não é navegador (o `TestClient`, um script) não manda `Origin`.
    Aceitar essa ausência é correto: o vetor que se está fechando existe apenas
    dentro do navegador, e é lá que o cabeçalho é obrigatório.
    """
    origem = websocket.headers.get("origin")
    if not origem:
        return True

    origem = origem.rstrip("/")

    if origem in {o.rstrip("/") for o in settings.effective_cors_origins}:
        return True

    regex = settings.cors_allow_origin_regex
    if regex and re.match(regex, origem):
        return True

    return False


async def require_websocket_session(websocket: WebSocket, db: Session) -> Optional[UserModel]:
    """
    Valida a sessão no handshake do WebSocket.

    O navegador não permite cabeçalhos personalizados ao abrir um WebSocket, e
    o cookie não viaja entre origens diferentes; por isso o token também é
    aceito na query string. Não é vazamento equivalente ao de uma URL comum: o
    endereço do WebSocket não vai para histórico nem para `Referer`.

    A checagem de `Origin` é feita antes, pela rota, via
    `origem_do_websocket_e_permitida`.
    """
    token = websocket.query_params.get("token")
    if not token:
        cookie = websocket.cookies.get(SESSION_COOKIE)
        token = cookie
    usuario = resolve_session(db, token)
    if usuario:
        return usuario

    if matches_local_token(websocket.query_params.get("local_token")):
        return (
            db.query(UserModel)
            .filter(UserModel.is_active == True)  # noqa: E712
            .order_by(UserModel.created_at.asc())
            .first()
        )
    return None


# ── Titularidade do acervo (doc 40 §40.3.2) ───────────────────────────


def projeto_do_usuario(
    project_id: str,
    request: HTTPConnection,
    usuario: Optional[UserModel] = Depends(require_session),
    db: Session = Depends(get_db),
) -> Optional[ProjectModel]:
    """
    Exige que o projeto da URL pertença a quem está pedindo.

    Como `require_session`, esta verificação é declarada **no router**, e não
    rota a rota: todos os nove roteadores de projeto já carregam
    `/projects/{project_id}` no prefixo, então a dependência alcança tudo o que
    existe hoje — e, o que importa mais, alcança sozinha o que for escrito
    amanhã. Uma rota nova nasce isolada, e esquecer deixou de ser possível.

    **Devolve 404, nunca 403.** Um 403 confirmaria que aquele projeto existe, e
    o identificador é um UUID: negar a existência é a única resposta que não
    entrega nada a quem estiver sondando. É a mesma decisão já tomada no
    confinamento de caminho da SPA, em `main.py`.

    No escopo de WebSocket sai de lado, como `require_session`: lá não há
    requisição HTTP para responder com 404, e quem decide é a própria rota,
    que consegue fechar a conexão com o código 1008. `verificar_projeto_do_usuario`
    é a forma que as rotas de WebSocket usam.
    """
    if request.scope.get("type") == "websocket":
        return None

    projeto = (
        db.query(ProjectModel)
        .filter(
            ProjectModel.id == project_id,
            ProjectModel.owner_id == (usuario.id if usuario else None),
        )
        .first()
    )
    if projeto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado.",
        )

    request.state.projeto = projeto
    return projeto


def verificar_projeto_do_usuario(
    db: Session, project_id: str, usuario: Optional[UserModel]
) -> bool:
    """
    Versão sem HTTP da verificação acima, para o handshake de WebSocket.

    O canal de progresso é por projeto: sem isto, quem tivesse sessão válida
    acompanharia a coleta e a triagem de qualquer outro assinante apenas
    adivinhando — ou vazando — um identificador de projeto.
    """
    if usuario is None:
        return False
    return (
        db.query(ProjectModel.id)
        .filter(ProjectModel.id == project_id, ProjectModel.owner_id == usuario.id)
        .first()
        is not None
    )


def require_aceite(
    request: HTTPConnection,
    usuario: Optional[UserModel] = Depends(require_session),
) -> Optional[UserModel]:
    """
    Barra quem ainda não deu ciência do aviso vigente (doc 43 §43.10).

    Entra como dependência do **router**, e não rota a rota, pela mesma razão
    que `require_session`: uma rota nova nasce protegida, e esquecer deixou de
    ser possível.

    O que fica de fora, de propósito: `/aceite`, que é onde a pessoa lê e
    concorda, e `/auth`, que é como ela sai. Trancar essas duas prenderia
    alguém do lado de fora do único lugar onde poderia entrar.

    No escopo de WebSocket sai de lado, como as demais: lá não há resposta HTTP
    para devolver, e a checagem é feita dentro da rota.
    """
    if request.scope.get("type") == "websocket":
        return usuario

    # Import tardio: `aceite` importa `dependencies` para as suas próprias
    # rotas, e o ciclo em tempo de importação derrubaria a partida.
    from app.api.v1.aceite import aceite_pendente

    if aceite_pendente(usuario):
        raise HTTPException(
            status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
            detail=(
                "É preciso ler e dar ciência do aviso do BETA antes de usar o "
                "Revsist. Abra /aceite."
            ),
        )
    return usuario
