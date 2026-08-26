#!/usr/bin/env python

"""RSAC V2 — Schema do estado da autenticação local."""

from pydantic import BaseModel


class AuthStatusResponse(BaseModel):
    """
    Estado da autenticação — a única rota que responde sem credencial.

    Existia aqui um módulo com nove schemas: login, troca de senha, criação e
    listagem de contas. Foram embora com as contas. O que a interface precisa
    saber na partida cabe em três campos, e nenhum deles ajuda quem não tiver
    o token: a versão (para a barra de estado), se esta instalação chegou a
    gerar um `runtime_token`, e se **esta** requisição o apresentou.

    A distinção entre os dois últimos é o que separa "o backend acabou de
    subir e ainda não gerou o token" de "o token existe e o que você mandou
    não é ele" — dois problemas com soluções diferentes.
    """

    app_version: str
    local_token_disponivel: bool
    authenticated: bool
