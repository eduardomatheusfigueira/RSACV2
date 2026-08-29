#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Schemas de Autenticação e Contas (doc 29 §29.3)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class LocalTokenRequest(BaseModel):
    """Troca do token local do perfil desktop por uma sessão."""

    token: str = Field(..., min_length=8, description="Conteúdo de <data_dir>/runtime_token")


class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class LoginResponse(BaseModel):
    """
    Resultado do login.

    O `access_token` acompanha o cookie porque o cliente hospedado em outra
    origem (Netlify, Vite em desenvolvimento) não recebe cookie `SameSite=Strict`.
    Quem é servido pelo próprio backend pode ignorá-lo e deixar o cookie
    trabalhar.
    """

    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int


class AuthStatusResponse(BaseModel):
    """
    Estado da autenticação — a única rota que responde antes do login.

    Serve ao cliente (mostrar tela de login ou entrar direto) e ao lançador de
    servidor, que se recusa a abrir o túnel se `authentication_enabled` for
    falso (§29.11.6).
    """

    authentication_enabled: bool
    deployment_profile: str
    has_accounts: bool
    local_token_accepted: bool
    # Sem isto a tela teria de adivinhar se mostra o botão do Google — e
    # mostrá-lo numa instalação sem credencial levaria a um 503 no clique.
    google_login_enabled: bool = False
    # Falta dar ciência do aviso do BETA? A interface precisa saber
    # **antes** de tentar qualquer rota, ou a primeira tela útil vira
    # um 451 sem explicação.
    aceite_pendente: bool = False
    authenticated: bool = False
    user: Optional[UserResponse] = None


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    password: Optional[str] = Field(
        default=None, description="Se omitida, o servidor sorteia uma e a devolve uma única vez"
    )
    role: str = Field(default="researcher", pattern=r"^(owner|researcher)$")


class UserCreatedResponse(BaseModel):
    user: UserResponse
    generated_password: Optional[str] = Field(
        default=None, description="Devolvida apenas na criação, e nunca mais"
    )


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
