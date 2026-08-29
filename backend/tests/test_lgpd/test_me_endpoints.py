#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes das rotas de direitos do titular /api/v1/me (LGPD Art. 18 e 19).
"""

from pathlib import Path
import pytest
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    AISettingsModel,
    PaperModel,
    ProcessingRecordModel,
    ProjectModel,
    SessionModel,
    SourceCredentialModel,
    UserModel,
    generate_uuid,
)
from app.services.pdf_service import PDFService
from tests.conftest import RESEARCHER_ID_TESTE, RESEARCHER_USERNAME


@pytest.mark.anyio
async def test_get_me_resumo_simplificado(researcher_client, db_session: Session):
    usuario = db_session.query(UserModel).filter(UserModel.id == RESEARCHER_ID_TESTE).first()
    usuario.display_name = "Dra. Titular da Silva"
    usuario.email = "titular@revsist.org"
    usuario.email_verified = True
    db_session.commit()

    # Criar um projeto e paper para o pesquisador
    proj = ProjectModel(
        id=generate_uuid(),
        owner_id=RESEARCHER_ID_TESTE,
        title="Revisão sobre Governança Regional",
    )
    db_session.add(proj)
    db_session.flush()

    paper = PaperModel(
        id=generate_uuid(),
        project_id=proj.id,
        title="Arranjos Produtivos e Desenvolvimento Sustentável",
        decision="Incluído",
    )
    db_session.add(paper)
    db_session.commit()

    resp = await researcher_client.get("/api/v1/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == RESEARCHER_ID_TESTE
    assert data["username"] == RESEARCHER_USERNAME
    assert data["email"] == "titular@revsist.org"
    assert data["display_name"] == "Dra. Titular da Silva"
    assert data["total_projects"] == 1
    assert data["total_papers"] == 1


@pytest.mark.anyio
async def test_get_me_declaracao_completa_art19(researcher_client, db_session: Session):
    resp = await researcher_client.get("/api/v1/me/dados")
    assert resp.status_code == 200
    data = resp.json()

    assert data["titular"]["id"] == RESEARCHER_ID_TESTE
    assert "controlador" in data
    assert len(data["finalidades_e_bases_legais"]) >= 3
    assert "historico_de_operacoes_ropa" in data
    assert "destinatarios_e_transferencias" in data
    assert "politica_de_retencao" in data
    assert "direitos_do_titular" in data


@pytest.mark.anyio
async def test_patch_me_retificacao(researcher_client, db_session: Session):
    resp = await researcher_client.patch(
        "/api/v1/me",
        json={"display_name": "Profa. Titular Atualizada", "email": "novo_email@revsist.org"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Profa. Titular Atualizada"
    assert data["email"] == "novo_email@revsist.org"


@pytest.mark.anyio
async def test_get_me_portabilidade(researcher_client, db_session: Session):
    # Criar um projeto para o pesquisador
    proj = ProjectModel(
        id=generate_uuid(),
        owner_id=RESEARCHER_ID_TESTE,
        title="Revisão de Portabilidade",
    )
    db_session.add(proj)
    db_session.commit()

    resp = await researcher_client.get("/api/v1/me/portabilidade")
    assert resp.status_code == 200
    data = resp.json()
    assert "projects" in data
    assert len(data["projects"]) >= 1

    # Prova que gerou registro no ROPA
    registro = (
        db_session.query(ProcessingRecordModel)
        .filter(
            ProcessingRecordModel.user_id == RESEARCHER_ID_TESTE,
            ProcessingRecordModel.operation == "data_export",
        )
        .first()
    )
    assert registro is not None
    assert registro.legal_basis == "art7_VI_exercicio_de_direitos"


@pytest.mark.anyio
async def test_delete_me_com_prazo_de_arrependimento(researcher_client, db_session: Session):
    resp = await researcher_client.request(
        "DELETE",
        "/api/v1/me",
        json={"confirmation": RESEARCHER_USERNAME, "grace_period_days": 7},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "scheduled"
    assert data["immediate"] is False
    assert data["scheduled_erasure_at"] is not None

    # Usuário foi desativado
    usuario_db = db_session.query(UserModel).filter(UserModel.id == RESEARCHER_ID_TESTE).first()
    assert usuario_db is not None
    assert usuario_db.is_active is False

    # Sessões foram revogadas
    sessoes = db_session.query(SessionModel).filter(SessionModel.user_id == RESEARCHER_ID_TESTE).all()
    assert len(sessoes) == 0


@pytest.mark.anyio
async def test_delete_me_imediato_apaga_banco_e_disco(
    researcher_client, db_session: Session, tmp_path: Path, monkeypatch
):
    import app.api.v1.me as me_module
    monkeypatch.setattr(me_module.pdf_service, "storage_dir", tmp_path)

    # Criar projeto e paper
    proj = ProjectModel(
        id=generate_uuid(),
        owner_id=RESEARCHER_ID_TESTE,
        title="Revisão a Ser Eliminada",
    )
    db_session.add(proj)
    db_session.flush()

    paper = PaperModel(
        id=generate_uuid(),
        project_id=proj.id,
        title="Estudo a Ser Apagado",
        decision="Pendente",
    )
    db_session.add(paper)
    db_session.commit()

    # Criar PDF no disco
    proj_dir = tmp_path / proj.id
    proj_dir.mkdir(parents=True, exist_ok=True)
    pdf_file = proj_dir / f"{paper.id}.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 mock paper content")
    assert pdf_file.exists()

    resp = await researcher_client.request(
        "DELETE",
        "/api/v1/me",
        json={"confirmation": "EXCLUIR", "grace_period_days": 0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "erased"
    assert data["immediate"] is True

    # 1. Usuário removido da tabela users
    usuario_db = db_session.query(UserModel).filter(UserModel.id == RESEARCHER_ID_TESTE).first()
    assert usuario_db is None

    # 2. Projetos e papers removidos do banco
    proj_db = db_session.query(ProjectModel).filter(ProjectModel.id == proj.id).first()
    assert proj_db is None
    paper_db = db_session.query(PaperModel).filter(PaperModel.id == paper.id).first()
    assert paper_db is None

    # 3. Arquivo PDF e diretório físico apagados do disco
    assert not pdf_file.exists()
    assert not proj_dir.exists()

    # 4. ROPA sobrevive à exclusão com o registro data_erasure pseudonimizado
    ropa_erasure = (
        db_session.query(ProcessingRecordModel)
        .filter(
            ProcessingRecordModel.user_id == RESEARCHER_ID_TESTE,
            ProcessingRecordModel.operation == "data_erasure",
        )
        .first()
    )
    assert ropa_erasure is not None
    assert ropa_erasure.legal_basis == "art7_VI_exercicio_de_direitos"
