#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Schemas de Equipe e Convites de Projeto (doc 43 §43.3, Fase 1).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ProjectRoleType = Literal["coordenador", "revisor", "observador"]


class ProjectMemberResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    project_role: ProjectRoleType
    is_active: bool
    joined_at: datetime
    left_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectInvitationCreate(BaseModel):
    email: Optional[str] = Field(None, description="Destinatário pretendido (opcional)")
    project_role: ProjectRoleType = Field("revisor", description="Papel concedido pelo convite")
    note: str = Field("", max_length=500, description="Observação ou motivo do convite")


class ProjectInvitationResponse(BaseModel):
    id: str
    project_id: str
    code: str
    email: Optional[str] = None
    project_role: ProjectRoleType
    created_by_user_id: str
    created_by_username: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    accepted_by_user_id: Optional[str] = None
    accepted_by_username: Optional[str] = None
    revoked_at: Optional[datetime] = None
    is_valid: bool = True
    note: str = ""

    model_config = {"from_attributes": True}


class TeamResponse(BaseModel):
    project_id: str
    members: list[ProjectMemberResponse]
    invitations: list[ProjectInvitationResponse] = []
    my_role: ProjectRoleType
    # Sem isto a tela não distingue a própria linha da dos colegas — e o botão
    # de sair da equipe acaba oferecido sobre o membro errado.
    my_user_id: str


class AcceptInvitationResponse(BaseModel):
    status: str
    project_id: str
    project_title: str
    project_role: ProjectRoleType
    message: str
