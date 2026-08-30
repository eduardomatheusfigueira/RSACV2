import json
import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    AuditLogModel,
    CriterionModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    HarvestRunModel,
    PaperCriterionModel,
    PaperModel,
    PaperSourceModel,
    ProjectMemberModel,
    ProjectModel,
    ProtocolModel,
    UserModel,
)
from app.config import settings
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from app.security.dependencies import (
    exige_coordenador,
    exige_dono_do_projeto,
    origem_do_websocket_e_permitida,
    projeto_do_usuario,
    require_session,
    require_websocket_session,
    verificar_projeto_do_usuario,
)
from app.services.harvesting_service import ws_manager
from app.services.pdf_service import PDFService
from app.security.middleware import erro_interno
from app.domain.collaboration import MODALIDADES_VALIDAS

logger = logging.getLogger(__name__)

pdf_service = PDFService()

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    archived: Optional[bool] = Query(None, description="Filtrar por arquivamento"),
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Lista os projetos em que o usuário tem participação ativa."""
    query = (
        db.query(ProjectModel, ProjectMemberModel.project_role)
        .join(ProjectMemberModel, ProjectMemberModel.project_id == ProjectModel.id)
        .filter(
            ProjectMemberModel.user_id == usuario.id,
            ProjectMemberModel.is_active.is_(True),
        )
    )
    if archived is not None:
        query = query.filter(ProjectModel.is_archived == archived)
    query = query.order_by(ProjectModel.updated_at.desc())

    results = query.all()
    items = []
    for project, role in results:
        member_count = (
            db.query(ProjectMemberModel)
            .filter(
                ProjectMemberModel.project_id == project.id,
                ProjectMemberModel.is_active.is_(True),
            )
            .count()
        )
        resp = ProjectResponse.model_validate(project)
        resp.my_role = role
        resp.member_count = member_count
        items.append(resp)

    return ProjectListResponse(
        items=items,
        total=len(items),
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Cria um novo projeto de revisão sistemática, pertencente a quem o criou."""
    # Verificar teto de projetos por conta (§40.7.5, O-25)
    total_existente = (
        db.query(ProjectModel).filter(ProjectModel.owner_id == usuario.id).count()
    )
    if total_existente >= settings.max_projects_per_user:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Limite de {settings.max_projects_per_user} projetos atingido para esta conta. "
                "Exclua ou arquive projetos anteriores antes de criar um novo."
            ),
        )

    if data.collaboration_mode not in MODALIDADES_VALIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Modalidade inválida: '{data.collaboration_mode}'. Válidas: {sorted(MODALIDADES_VALIDAS)}",
        )

    project = ProjectModel(
        owner_id=usuario.id,
        title=data.title,
        description=data.description,
        methodology=data.methodology,
        collaboration_mode=data.collaboration_mode,
        reviewers_per_paper=data.reviewers_per_paper,
        conflict_resolution=data.conflict_resolution,
    )
    db.add(project)
    db.flush()

    # Cria protocolo vazio vinculado
    protocol = ProtocolModel(project_id=project.id)
    db.add(protocol)

    db.commit()
    db.refresh(project)

    logger.info(f"Projeto criado: '{project.title}' (ID: {project.id})")
    resp = ProjectResponse.model_validate(project)
    resp.my_role = "coordenador"
    resp.member_count = 1
    return resp


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    request: Request,
    project: ProjectModel = Depends(projeto_do_usuario),
    db: Session = Depends(get_db),
):
    """Obtém detalhes de um projeto específico."""
    membro = getattr(request.state, "membro", None)
    member_count = (
        db.query(ProjectMemberModel)
        .filter(
            ProjectMemberModel.project_id == project.id,
            ProjectMemberModel.is_active.is_(True),
        )
        .count()
    )
    resp = ProjectResponse.model_validate(project)
    if membro:
        resp.my_role = membro.project_role
    resp.member_count = member_count
    return resp


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    data: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
    project: ProjectModel = Depends(projeto_do_usuario),
    _membro: ProjectMemberModel = Depends(exige_coordenador),
):
    """Atualiza um projeto existente (requer papel de coordenador)."""

    update_data = data.model_dump(exclude_unset=True)

    # D-05: Se a modalidade de colaboração estiver sendo alterada, verificar se há decisões
    novo_modo = update_data.get("collaboration_mode")
    if novo_modo is not None and novo_modo != project.collaboration_mode:
        if novo_modo not in MODALIDADES_VALIDAS:
            raise HTTPException(
                status_code=400,
                detail=f"Modalidade inválida: '{novo_modo}'. Válidas: {sorted(MODALIDADES_VALIDAS)}",
            )
        estudos_decididos = (
            db.query(PaperModel)
            .filter(
                PaperModel.project_id == project.id,
                PaperModel.decision != "Pendente",
            )
            .count()
        )
        if estudos_decididos > 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Não é possível alterar a modalidade de colaboração: o projeto já possui "
                    f"{estudos_decididos} estudo(s) com decisão de triagem. Para alterar a "
                    f"modalidade, utilize a reabertura de triagem pela coordenação."
                ),
            )

    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    logger.info(f"Projeto atualizado: '{project.title}' (ID: {project.id})")
    resp = ProjectResponse.model_validate(project)
    resp.my_role = _membro.project_role
    return resp


class ReabrirTriagemPayload(ProjectUpdate):
    motivo: Optional[str] = "Reabertura de triagem pela coordenação"


@router.post("/{project_id}/screening/reabrir")
def reabrir_triagem(
    payload: ReabrirTriagemPayload,
    db: Session = Depends(get_db),
    project: ProjectModel = Depends(projeto_do_usuario),
    _membro: ProjectMemberModel = Depends(exige_coordenador),
    usuario: UserModel = Depends(require_session),
):
    """
    Reabre a triagem de todos os estudos decididos do projeto (Doc 43 §43.4.3).
    Registra logs de auditoria, redefine decisões para 'Pendente' e altera a modalidade se solicitada.
    """
    from app.infrastructure.persistence.models import utcnow
    from sqlalchemy import text

    estudos = (
        db.query(PaperModel)
        .filter(PaperModel.project_id == project.id)
        .all()
    )
    agora = utcnow()
    count_decididos = 0

    for paper in estudos:
        if paper.decision != "Pendente":
            count_decididos += 1
            db.add(
                AuditLogModel(
                    paper_id=paper.id,
                    action="screening_reopened",
                    old_value=paper.decision,
                    new_value="Pendente",
                    source="manual",
                    user_id=usuario.id,
                    username=usuario.username,
                    created_at=agora,
                )
            )
            paper.decision = "Pendente"
            paper.observations = ""
            paper.ai_confidence = None
            paper.ai_assisted = False

    # Limpar critérios consolidados de papers
    db.execute(
        text("DELETE FROM paper_criteria WHERE paper_id IN (SELECT id FROM papers WHERE project_id = :pid)"),
        {"pid": project.id},
    )

    if payload.collaboration_mode:
        if payload.collaboration_mode not in MODALIDADES_VALIDAS:
            raise HTTPException(
                status_code=400,
                detail=f"Modalidade inválida: '{payload.collaboration_mode}'. Válidas: {sorted(MODALIDADES_VALIDAS)}",
            )
        project.collaboration_mode = payload.collaboration_mode

    db.commit()
    db.refresh(project)

    logger.info(
        "[Projetos] Triagem do projeto '%s' (%s) reaberta por %s. %d estudos resetados.",
        project.title,
        project.id,
        usuario.username,
        count_decididos,
    )

    return {
        "status": "reopened",
        "project_id": project.id,
        "collaboration_mode": project.collaboration_mode,
        "papers_reset": count_decididos,
        "message": f"Triagem reaberta com sucesso. {count_decididos} estudo(s) tiveram sua decisão redefinida para Pendente.",
    }


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    project: ProjectModel = Depends(projeto_do_usuario),
    _dono: ProjectModel = Depends(exige_dono_do_projeto),
):
    """
    Exclui um projeto e todos os dados associados com cascata rigorosa e segura
    mesmo para acervos massivos (sem estourar limites de parâmetros SQL).
    """
    try:
        # 1. Remove os PDFs do disco de forma atômica
        try:
            removidos = pdf_service.delete_project_pdfs(project_id)
            if removidos:
                logger.info("[Projects] %d PDF(s) do projeto %s removidos do disco.", removidos, project_id)
        except Exception as exc:
            logger.warning("[Projects] Falha ao remover PDFs em disco do projeto %s: %s", project_id, exc)

        # 2. Deleta entidades filhas usando subconsultas SQL por project_id
        from sqlalchemy import text

        # a) Respostas de extração, critérios de papers, fontes e logs de auditoria
        db.execute(
            text("DELETE FROM paper_criteria WHERE paper_id IN (SELECT id FROM papers WHERE project_id = :pid)"),
            {"pid": project_id},
        )
        db.execute(
            text("DELETE FROM paper_criteria WHERE criterion_id IN (SELECT c.id FROM criteria c JOIN protocols p ON c.protocol_id = p.id WHERE p.project_id = :pid)"),
            {"pid": project_id},
        )
        db.execute(
            text("DELETE FROM extraction_answers WHERE paper_id IN (SELECT id FROM papers WHERE project_id = :pid)"),
            {"pid": project_id},
        )
        db.execute(
            text("DELETE FROM extraction_answers WHERE question_id IN (SELECT eq.id FROM extraction_questions eq JOIN protocols p ON eq.protocol_id = p.id WHERE p.project_id = :pid)"),
            {"pid": project_id},
        )
        db.execute(
            text("DELETE FROM paper_sources WHERE paper_id IN (SELECT id FROM papers WHERE project_id = :pid)"),
            {"pid": project_id},
        )
        db.execute(
            text("DELETE FROM audit_logs WHERE paper_id IN (SELECT id FROM papers WHERE project_id = :pid)"),
            {"pid": project_id},
        )

        # b) Perguntas de extração e critérios do protocolo
        db.execute(
            text(
                "DELETE FROM extraction_questions WHERE protocol_id IN (SELECT id FROM protocols WHERE project_id = :pid)"
            ),
            {"pid": project_id},
        )
        db.execute(
            text(
                "DELETE FROM criteria WHERE protocol_id IN (SELECT id FROM protocols WHERE project_id = :pid)"
            ),
            {"pid": project_id},
        )

        # c) Papers, Protocolos, Harvest Runs e Relatórios de Deduplicação
        db.execute(text("DELETE FROM papers WHERE project_id = :pid"), {"pid": project_id})
        db.execute(text("DELETE FROM protocols WHERE project_id = :pid"), {"pid": project_id})
        db.execute(text("DELETE FROM harvest_runs WHERE project_id = :pid"), {"pid": project_id})
        db.execute(text("DELETE FROM deduplication_reports WHERE project_id = :pid"), {"pid": project_id})

        # d) Projeto raiz
        db.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": project_id})

        db.commit()
        logger.info(f"Projeto excluído com sucesso: ID {project_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao excluir projeto {project_id}: {e}", exc_info=True)
        mensagem, _ = erro_interno(
            "Falha ao excluir o projeto.", e, contexto="[Projects] exclusão"
        )
        raise HTTPException(status_code=500, detail=mensagem) from e


@router.get("/{project_id}/stats")
def get_project_stats(
    project_id: str,
    db: Session = Depends(get_db),
    project: ProjectModel = Depends(projeto_do_usuario),
):
    """Retorna estatísticas do projeto (contadores PRISMA)."""

    from sqlalchemy import func, or_

    from app.infrastructure.persistence.models import PaperModel

    papers = db.query(PaperModel).filter(
        PaperModel.project_id == project_id,
        or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)),
    )
    total = papers.count()
    included = papers.filter(PaperModel.decision == "Incluído").count()
    excluded = papers.filter(PaperModel.decision == "Excluído").count()
    pending = papers.filter(PaperModel.decision == "Pendente").count()

    # Contagem por fonte
    from app.infrastructure.persistence.models import PaperSourceModel
    source_counts = (
        db.query(PaperSourceModel.source_name, func.count(PaperSourceModel.id))
        .join(PaperModel, PaperModel.id == PaperSourceModel.paper_id)
        .filter(PaperModel.project_id == project_id)
        .group_by(PaperSourceModel.source_name)
        .all()
    )

    return {
        "total_papers": total,
        "included_papers": included,
        "excluded_papers": excluded,
        "pending_papers": pending,
        "total_harvest_runs": len(project.harvest_runs),
        "sources": {name: count for name, count in source_counts},
    }


@router.websocket("/{project_id}/ws")
async def project_collaboration_websocket(
    project_id: str,
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """
    Canal WebSocket unificado do projeto para colaboração ao vivo e presença (Doc 43 §43.12).
    """
    if not origem_do_websocket_e_permitida(websocket):
        await websocket.close(code=1008, reason="Origem não autorizada.")
        return

    usuario = await require_websocket_session(websocket, db)
    if not usuario:
        await websocket.close(code=1008, reason="Autenticação necessária.")
        return

    if not verificar_projeto_do_usuario(db, project_id, usuario):
        await websocket.close(code=1008, reason="Projeto não encontrado ou acesso revogado.")
        return

    await ws_manager.connect(
        project_id,
        websocket,
        user_id=usuario.id,
        username=usuario.username,
        screen="geral",
    )
    try:
        while True:
            raw_data = await websocket.receive_text()
            if raw_data == "ping":
                await websocket.send_text("pong")
                continue
            try:
                msg = json.loads(raw_data)
                if msg.get("type") == "presenca":
                    tela = msg.get("tela", "geral")
                    await ws_manager.update_presence(
                        project_id=project_id,
                        user_id=usuario.id,
                        username=usuario.username,
                        screen=tela,
                    )
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
    except Exception:
        ws_manager.disconnect(project_id, websocket)
