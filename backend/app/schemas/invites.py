#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Schemas de Validação de Convites e Cadastro (Pydantic v2).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidateInviteRequest(BaseModel):
    invite_code: str = Field(..., min_length=4, max_length=64, description="Código de convite")

    @field_validator("invite_code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        return v.strip().upper()


class ValidateInviteResponse(BaseModel):
    valid: bool
    note: str = ""
    expires_at: Optional[datetime] = None


class RegisterWithInviteRequest(BaseModel):
    invite_code: str = Field(..., min_length=4, max_length=64)
    username: str = Field(..., min_length=3, max_length=64)
    # 12, e não 8: é o mínimo de `security.passwords`, que roda depois. Com 8
    # aqui, uma senha de 9 caracteres passava na validação do formulário,
    # a pessoa preenchia o cadastro inteiro e só então era recusada.
    password: str = Field(..., min_length=12, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=200)
    email: str = Field(..., min_length=5, max_length=320)
    phone: Optional[str] = Field("", max_length=50)
    institution: Optional[str] = Field("", max_length=200)
    academic_degree: Optional[str] = Field("", max_length=100)
    is_studying: bool = False
    study_program: Optional[str] = Field("", max_length=200)
    profession: Optional[str] = Field("", max_length=100)
    research_area: Optional[str] = Field("", max_length=200)
    terms_accepted: bool = Field(...)

    @field_validator(
        "phone",
        "institution",
        "academic_degree",
        "study_program",
        "profession",
        "research_area",
        mode="before",
    )
    @classmethod
    def clean_optional_strings(cls, v: any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("invite_code")
    @classmethod
    def clean_invite_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        import unicodedata

        v = v.strip().lower()
        # Normalizar acentos
        v = "".join(
            c for c in unicodedata.normalize("NFD", v) if unicodedata.category(c) != "Mn"
        )
        # Substituir espaços por pontos
        v = re.sub(r"\s+", ".", v)
        if not re.match(r"^[a-z0-9_.-]+$", v):
            raise ValueError(
                "Nome de usuário pode conter apenas letras, números, ponto, hífen e sublinhado."
            )
        if len(v) < 3:
            raise ValueError("Nome de usuário deve ter no mínimo 3 caracteres.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Endereço de e-mail inválido.")
        return v

    @field_validator("terms_accepted")
    @classmethod
    def require_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "É obrigatório concordar com os Termos de Uso e a Política de Privacidade."
            )
        return v


class InviteCreateRequest(BaseModel):
    note: str = Field("", max_length=255)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)
    custom_code: Optional[str] = Field(None, min_length=4, max_length=32)


class InviteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    note: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_used: bool
    used_at: Optional[datetime]
    used_by_user_id: Optional[str] = None
    used_by_username: Optional[str] = None
    is_revoked: bool


class InviteListResponse(BaseModel):
    invites: list[InviteResponse]
    total: int


# ── Solicitações públicas de convite (página de login) ────────────────
#
# Quem chega ao Revsist sem convite precisa de um caminho que não seja
# "procure o administrador por fora". Estes schemas descrevem esse caminho:
# o formulário público de pedido e a visão administrativa da fila.

STATUS_SOLICITACAO = ("pendente", "aprovado", "recusado")


class InviteRequestCreate(BaseModel):
    """Pedido de convite enviado da página de login, sem sessão."""

    nome: str = Field(..., min_length=3, max_length=120)
    email: str = Field(..., min_length=5, max_length=255)
    telefone: str = Field(..., min_length=8, max_length=50)
    onde_conheceu: str = Field(..., min_length=2, max_length=255)
    instituicao: Optional[str] = Field("", max_length=255)

    @field_validator("nome", "telefone", "onde_conheceu", mode="before")
    @classmethod
    def limpar_obrigatorios(cls, v: any) -> str:
        return str(v or "").strip()

    @field_validator("instituicao", mode="before")
    @classmethod
    def limpar_instituicao(cls, v: any) -> str:
        return str(v or "").strip()

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Endereço de e-mail inválido.")
        return v


class InviteRequestPublicResponse(BaseModel):
    """
    Confirmação devolvida a quem enviou o pedido.

    Deliberadamente magra: não devolve o registro, porque a rota é pública e
    ecoar o que foi gravado transformaria o formulário em consulta de quem já
    pediu acesso.
    """

    received: bool = True
    message: str


class InviteRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    email: str
    telefone: str
    onde_conheceu: str
    instituicao: Optional[str] = ""
    status: str
    created_at: datetime
    responded_at: Optional[datetime] = None
    invite_code_generated: Optional[str] = None
    admin_notes: Optional[str] = ""


class InviteRequestListResponse(BaseModel):
    requests: list[InviteRequestResponse]
    total: int
    pendentes: int


class InviteRequestUpdate(BaseModel):
    """Mudança de status ou anotação interna sobre um pedido."""

    status: Optional[str] = Field(None, max_length=20)
    admin_notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validar_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        if v not in STATUS_SOLICITACAO:
            raise ValueError(
                f"Status inválido. Use um de: {', '.join(STATUS_SOLICITACAO)}."
            )
        return v


class InviteRequestApprove(BaseModel):
    """Aprovação: emite um convite de uso único ligado ao pedido."""

    expires_in_days: Optional[int] = Field(14, ge=1, le=365)
    note: Optional[str] = Field(None, max_length=255)


class InviteRequestApproveResponse(BaseModel):
    request: InviteRequestResponse
    invite: InviteResponse
    # ── O aviso a quem foi aprovado ──────────────────────────────────
    #
    # Estes campos descrevem o que aconteceu com o aviso, e são separados do
    # resultado da aprovação de propósito: a concessão de acesso vale mesmo
    # que o e-mail não tenha saído. O painel lê `email_enviado` para dizer o
    # que falta fazer à mão, em vez de deixar o administrador supondo.
    link_direto: str = ""
    whatsapp_url: str = ""
    email_enviado: bool = False
    email_detalhe: str = ""
