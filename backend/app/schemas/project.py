#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Schemas de Projeto."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema para criação de projeto."""
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    methodology: str = "PRISMA-P"
    collaboration_mode: str = "individual"
    reviewers_per_paper: int = 1
    conflict_resolution: str = "coordenador"


class ProjectUpdate(BaseModel):
    """Schema para atualização parcial de projeto."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    methodology: Optional[str] = None
    is_archived: Optional[bool] = None
    collaboration_mode: Optional[str] = None
    reviewers_per_paper: Optional[int] = None
    conflict_resolution: Optional[str] = None


class ProjectResponse(BaseModel):
    """Schema de resposta de projeto."""
    id: str
    title: str
    description: str
    methodology: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    collaboration_mode: str = "individual"
    reviewers_per_paper: int = 1
    conflict_resolution: str = "coordenador"
    my_role: Optional[str] = None
    member_count: int = 1

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Schema de lista de projetos."""
    items: list[ProjectResponse]
    total: int
