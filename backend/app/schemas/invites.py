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
    password: str = Field(..., min_length=8, max_length=128)
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
