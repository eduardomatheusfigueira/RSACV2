#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes dos limites de recursos de infraestrutura (doc 40 §40.7.5, O-25, O-26).
"""

from pathlib import Path
import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import ProjectModel, UserModel, generate_uuid
from app.services.pdf_service import PDFService
from tests.conftest import RESEARCHER_ID_TESTE, RESEARCHER_USERNAME


def test_configuracao_limites_padrao():
    assert settings.max_upload_mb == 50
    assert settings.max_account_storage_mb == 5120
    assert settings.max_projects_per_user == 20
    assert settings.max_papers_per_project == 20000


@pytest.mark.anyio
async def test_bloqueio_criacao_ao_atingir_teto_de_projetos(researcher_client, db_session: Session, monkeypatch):
    # Definir teto temporário baixo para o teste (ex: 3 projetos)
    monkeypatch.setattr(settings, "max_projects_per_user", 3)

    # Criar 3 projetos existentes
    for i in range(3):
        proj = ProjectModel(
            id=generate_uuid(),
            owner_id=RESEARCHER_ID_TESTE,
            title=f"Projeto Existente {i+1}",
        )
        db_session.add(proj)
    db_session.commit()

    # Tentativa de criar o 4º projeto deve ser rejeitada com 400
    resp = await researcher_client.post(
        "/api/v1/projects",
        json={"title": "Projeto Excedente", "description": "Não deve passar"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "Limite de 3 projetos atingido" in data["detail"]


def test_calculo_armazenamento_projeto(tmp_path: Path):
    pdf_service = PDFService()
    pdf_service.storage_dir = tmp_path

    project_id = generate_uuid()
    proj_dir = tmp_path / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Sem arquivos
    assert pdf_service.calculate_project_storage_bytes(project_id) == 0

    # Criar dois PDFs
    (proj_dir / "paper1.pdf").write_bytes(b"A" * 1024)
    (proj_dir / "paper2.pdf").write_bytes(b"B" * 2048)

    assert pdf_service.calculate_project_storage_bytes(project_id) == 3072
