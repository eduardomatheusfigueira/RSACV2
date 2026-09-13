#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Schemas do feedback do beta (Pydantic v2).

Duas visões do mesmo registro: o envio, feito por qualquer pessoa com conta
pelo botão do aplicativo, e a fila, lida pelo administrador no painel.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

TIPOS_FEEDBACK = ("problema", "sugestao", "elogio", "outro")
STATUS_FEEDBACK = ("novo", "em_andamento", "resolvido", "arquivado")


class FeedbackCreate(BaseModel):
    """O que o botão de feedback envia. O contexto técnico vem do servidor."""

    tipo: str = Field(..., max_length=20)
    mensagem: str = Field(..., min_length=5, max_length=5000)
    # A tela em que a pessoa estava. Vem do cliente porque só ele sabe a rota
    # da SPA; o servidor não confia nela para nada além de exibir.
    pagina: Optional[str] = Field("", max_length=255)

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in TIPOS_FEEDBACK:
            raise ValueError(f"Tipo inválido. Use um de: {', '.join(TIPOS_FEEDBACK)}.")
        return v

    @field_validator("mensagem", mode="before")
    @classmethod
    def limpar_mensagem(cls, v: object) -> str:
        return str(v or "").strip()

    @field_validator("pagina", mode="before")
    @classmethod
    def limpar_pagina(cls, v: object) -> str:
        return str(v or "").strip()[:255]


class FeedbackAck(BaseModel):
    received: bool = True
    message: str


class FeedbackItem(BaseModel):
    id: str
    tipo: str
    mensagem: str
    pagina: str = ""
    navegador: str = ""
    versao: str = ""
    status: str
    created_at: datetime
    responded_at: Optional[datetime] = None
    admin_notes: str = ""
    autor_nome: str = ""
    autor_usuario: str = ""
    autor_email: str = ""


class FeedbackListResponse(BaseModel):
    items: list[FeedbackItem]
    total: int
    novos: int


class FeedbackUpdate(BaseModel):
    """Mudança de situação ou anotação interna sobre um feedback."""

    status: Optional[str] = Field(None, max_length=20)
    admin_notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validar_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        if v not in STATUS_FEEDBACK:
            raise ValueError(f"Situação inválida. Use uma de: {', '.join(STATUS_FEEDBACK)}.")
        return v
