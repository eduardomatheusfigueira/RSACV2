#!/usr/bin/env python

"""
RSAC V2 — Estado da autenticação local.

O que sobrou de um router que tinha nove rotas. Foram-se `login`, `logout`,
`me`, a troca de senha e as três de gestão de contas, junto com as contas
propriamente ditas: sem publicação por túnel, a prova de identidade é possuir
o arquivo `runtime_token`, e quem o possui é o dono da máquina. Ver
`app/security/dependencies.py` para o raciocínio inteiro.

Fica uma rota, e ela é pública porque precisa responder **antes** de a
interface saber se está autenticada: é o que permite a um app recém-instalado
distinguir "o backend não subiu" de "o token não bate", em vez de mostrar a
mesma tela de erro para os dois.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.config import settings
from app.schemas.auth import AuthStatusResponse
from app.security.dependencies import requisicao_autenticada
from app.security.local_token import read_local_token

logger = logging.getLogger(__name__)

public_auth_router = APIRouter(prefix="/auth", tags=["auth"])


@public_auth_router.get("/status", response_model=AuthStatusResponse)
def auth_status(request: Request):
    """
    Diz se esta instalação tem token local e se esta requisição o apresentou.

    Não devolve nada além disso — nem caminho de arquivo, nem o token, nem
    contagem de coisa nenhuma. Quem chega aqui sem credencial só aprende que
    existe um RSAC atendendo nesta porta, o que ele já sabia por ter chegado.
    """
    return AuthStatusResponse(
        app_version=settings.app_version,
        local_token_disponivel=bool(read_local_token()),
        authenticated=requisicao_autenticada(request),
    )
