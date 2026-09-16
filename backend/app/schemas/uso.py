#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Schemas dos dados de uso e da aba Sistema (doc 52).

Os limites de tamanho daqui são a primeira barreira, e não a principal: um
evento que passe por eles ainda precisa caber no vocabulário fechado
(`services/uso/vocabulario.py`) para virar linha no banco.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

# ── Ingestão ──────────────────────────────────────────────────────────


class EventoDeUsoIn(BaseModel):
    nome: str = Field(..., max_length=64)
    tela: Optional[str] = Field(None, max_length=40)
    propriedades: dict[str, Any] = Field(default_factory=dict)
    ocorrido_em: datetime


class LoteDeEventosIn(BaseModel):
    sessao_uso_id: str = Field("", max_length=36)
    eventos: list[EventoDeUsoIn] = Field(..., max_length=50)


class OcorrenciaDeErroIn(BaseModel):
    tipo: str = Field(..., max_length=120)
    mensagem: str = Field("", max_length=2000)
    pilha: str = Field("", max_length=8000)
    tela: Optional[str] = Field(None, max_length=40)
    status_http: Optional[int] = Field(None, ge=0, le=999)
    correlacao: Optional[str] = Field(None, max_length=36)
    ocorrido_em: datetime


class LoteDeErrosIn(BaseModel):
    ocorrencias: list[OcorrenciaDeErroIn] = Field(..., max_length=10)


# ── Titular ───────────────────────────────────────────────────────────


class MeUsoResponse(BaseModel):
    coleta_ativa: bool
    alterada_em: Optional[datetime] = None
    coleta_em_vigor: bool
    beta_fim: date
    contagens: dict[str, int]


class RegistroDeUsoItem(BaseModel):
    """Um registro traduzido para linguagem comum, como a tela mostra."""

    ocorrido_em: datetime
    descricao: str
    detalhe: str = ""


class ConsumoDeIADoTitular(BaseModel):
    dia: str
    provedor: str
    modelo: str
    operacao: str
    chamadas: int
    tokens: int


class MeUsoRegistrosResponse(BaseModel):
    eventos: list[RegistroDeUsoItem]
    erros: list[RegistroDeUsoItem]
    consumo_de_ia: list[ConsumoDeIADoTitular]
    tokens_total: int
    contagens: dict[str, int]


class MeUsoUpdate(BaseModel):
    coleta_ativa: bool
    apagar_registros: bool = False


# ── Aba Sistema ───────────────────────────────────────────────────────


class MudancaDeEstadoIn(BaseModel):
    motivo: str = Field("", max_length=300)
    confirmacao: str = Field("", max_length=20)


class PedidoDeTitularIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    confirmacao: str = Field("", max_length=20)


class AcompanhamentoDeErroIn(BaseModel):
    situacao: str = Field(..., max_length=20)
    nota: Optional[str] = Field(None, max_length=2000)
    versao: Optional[str] = Field(None, max_length=20)
