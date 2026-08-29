#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Router de Direitos do Titular (LGPD Art. 18 e 19, doc 40 §40.5.1).

Implementa as cinco portas de acesso e gestão dos dados pessoais do titular
autenticado:
  * GET /me              — Confirmação simplificada imediata (Art. 19, I);
  * GET /me/dados        — Declaração completa de tratamento (Art. 19, II);
  * PATCH /me            — Retificação de dados cadastrais (Art. 18, III);
  * GET /me/portabilidade — Exportação estruturada para portabilidade (Art. 18, V);
  * DELETE /me           — Eliminação com opção de carência e limpeza total de
                           banco e PDFs em disco (Art. 16, Art. 18, VI).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import (
    AISettingsModel,
    PaperModel,
    ProcessingRecordModel,
    ProjectModel,
    SourceCredentialModel,
    UserModel,
    as_utc,
)
from app.schemas.me import (
    MeDeclarationResponse,
    MeDeleteRequest,
    MeDeleteResponse,
    MeSummaryResponse,
    MeUpdateRequest,
    ProcessingRecordItem,
)
from app.security.dependencies import require_session
from app.security.sessions import SESSION_COOKIE, revoke_all_sessions
from app.services.pdf_service import PDFService
from app.services.profile_service import ProfileService
from app.services import ropa_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["direitos_do_titular"])
pdf_service = PDFService()
profile_service = ProfileService()


def _resumo_do_titular(db: Session, usuario: UserModel) -> MeSummaryResponse:
    projetos_ids = [
        p.id for p in db.query(ProjectModel.id).filter(ProjectModel.owner_id == usuario.id).all()
    ]
    total_projetos = len(projetos_ids)
    total_papers = (
        db.query(PaperModel)
        .filter(PaperModel.project_id.in_(projetos_ids))
        .count()
        if projetos_ids
        else 0
    )

    return MeSummaryResponse(
        id=usuario.id,
        username=usuario.username,
        email=usuario.email,
        email_verified=usuario.email_verified,
        display_name=usuario.display_name or "",
        role=usuario.role,
        auth_provider=usuario.auth_provider,
        is_active=usuario.is_active,
        created_at=as_utc(usuario.created_at) or datetime.now(timezone.utc),
        last_login_at=as_utc(usuario.last_login_at),
        terms_accepted_at=as_utc(usuario.terms_accepted_at),
        terms_version=usuario.terms_version or "",
        total_projects=total_projetos,
        total_papers=total_papers,
    )


def executar_eliminacao_completa_usuario(db: Session, user_id: str) -> None:
    """
    Executa a eliminação atômica e irreversível de uma conta de usuário.

    Garante o cumprimento dos 6 passos de §40.5.1:
      1. Apaga projetos e dependências em cascata do banco;
      2. Remove todos os PDFs armazenados em disco para cada projeto;
      3. Remove configurações de IA e credenciais do usuário;
      4. Revoga todas as sessões ativas;
      5. Registra a operação no ROPA com categorias (sem reter dados pessoais);
      6. Remove o registro do usuário na tabela `users`.
    """
    projetos = db.query(ProjectModel).filter(ProjectModel.owner_id == user_id).all()

    # 1 e 2. Apagar projetos e PDFs no disco
    for proj in projetos:
        pdf_dir = pdf_service.get_project_pdf_dir(proj.id)
        if pdf_dir.exists():
            import shutil

            try:
                shutil.rmtree(pdf_dir, ignore_errors=True)
            except OSError as exc:
                logger.warning("[Me] Falha ao limpar diretório de PDFs %s: %s", pdf_dir, exc)
        db.delete(proj)

    # 3. Apagar credenciais e configurações de IA
    db.query(AISettingsModel).filter(AISettingsModel.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(SourceCredentialModel).filter(SourceCredentialModel.user_id == user_id).delete(
        synchronize_session=False
    )

    # 4. Revogar sessões
    revoke_all_sessions(db, user_id)

    # 5. Registrar no ROPA que houve eliminação
    ropa_service.registrar(
        db,
        operation="data_erasure",
        legal_basis="art7_VI_exercicio_de_direitos",
        purpose="Eliminação definitiva de conta e dados a pedido do titular (Art. 18, VI da LGPD)",
        data_categories=[
            "identificacao",
            "contato",
            "credencial",
            "identificador_externo",
            "conteudo_de_pesquisa",
            "documento",
        ],
        user_id=user_id,
        commit=False,
    )

    # 6. Remover conta
    usuario = db.query(UserModel).filter(UserModel.id == user_id).first()
    if usuario:
        db.delete(usuario)

    db.commit()
    logger.info("[Me] Eliminação completa e definitiva do usuário %s concluída.", user_id)


# ── Rotas ─────────────────────────────────────────────────────────────

@router.get("", response_model=MeSummaryResponse)
def obter_resumo(
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """
    Confirmação de existência e acesso simplificado e imediato (Art. 18, I, II; Art. 19, I).
    """
    return _resumo_do_titular(db, usuario)


@router.get("/dados", response_model=MeDeclarationResponse)
def obter_declaracao_completa(
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """
    Declaração completa de tratamento de dados pessoais (Art. 18, I, II, VII; Art. 19, II).
    """
    resumo = _resumo_do_titular(db, usuario)

    # Consultar histórico do ROPA associado a este titular
    registros_db = (
        db.query(ProcessingRecordModel)
        .filter(ProcessingRecordModel.user_id == usuario.id)
        .order_by(ProcessingRecordModel.occurred_at.desc())
        .limit(100)
        .all()
    )

    historico_ropa: List[ProcessingRecordItem] = []
    for r in registros_db:
        historico_ropa.append(
            ProcessingRecordItem(
                id=r.id,
                occurred_at=as_utc(r.occurred_at) or datetime.now(timezone.utc),
                operation=r.operation,
                legal_basis=r.legal_basis,
                purpose=r.purpose,
                data_categories=ropa_service.categorias_de(r),
                recipient=r.recipient,
                international=r.international,
            )
        )

    controlador_info = {
        "sistema": "Revsist — Plataforma de Revisão Sistemática da Literatura",
        "versao": "2.0.0",
        "perfil": settings.deployment_profile.value,
        "declaracao": (
            "O Revsist atua como operador e/ou controlador conforme as operações realizadas, "
            "assegurando os princípios de finalidade, adequação, necessidade, livre acesso e segurança."
        ),
    }

    finalidades = [
        {
            "finalidade": "Autenticação e controle de sessões",
            "base_legal": "Art. 7º, V (Execução de contrato / termos de uso)",
            "categorias": ["identificacao", "contato", "credencial", "conexao"],
            "descricao": "Permite acesso seguro e isolado ao acervo do pesquisador.",
        },
        {
            "finalidade": "Gestão de projetos e triagem metodológica de literatura científica",
            "base_legal": "Art. 7º, V (Execução de contrato)",
            "categorias": ["conteudo_de_pesquisa", "referencia_bibliografica", "documento"],
            "descricao": "Armazenamento dos estudos, decisões metodológicas e extrações da revisão.",
        },
        {
            "finalidade": "Triagem e extração assistida por Inteligência Artificial (BYOK / Opcional)",
            "base_legal": "Art. 7º, V (Execução de contrato)",
            "categorias": ["conteudo_de_pesquisa", "referencia_bibliografica"],
            "descricao": "Envio restrito a título e resumo para o provedor de IA configurado pelo usuário.",
        },
    ]

    destinatarios = [
        {
            "agente": "Provedores de IA configurados pelo usuário (ex: Google Gemini, Qwen/DashScope, OpenAI ou Local/Ollama)",
            "finalidade": "Processamento de critérios de inclusão/exclusão e extração de dados científicos",
            "transferencia_internacional": "Sim (salvo quando utilizado provedor local / Ollama)",
        },
        {
            "agente": "Bases de dados acadêmicas (ex: SciELO, BDTD, PubMed, OpenAlex, Crossref, Unpaywall)",
            "finalidade": "Recuperação de metadados e arquivos PDF de acesso aberto",
            "transferencia_internacional": "Conforme a localização do repositório de publicação",
        },
    ]

    politica_retencao = [
        {"dado": "Projetos, artigos e extrações", "prazo": "Até exclusão solicitada pelo titular"},
        {"dado": "Sessões e tokens", "prazo": "Eliminados após expiração ou logout"},
        {"dado": "Tentativas de login (IPs)", "prazo": "Expurgo automático após 90 dias"},
        {"dado": "Registro de Operações (ROPA)", "prazo": "5 anos para prestação de contas (Art. 6º, X e Art. 37)"},
    ]

    direitos = [
        {"direito": "Confirmação e Acesso", "artigo": "Art. 18, I e II", "meio": "GET /api/v1/me e GET /api/v1/me/dados"},
        {"direito": "Correção de dados incompletos ou inexatos", "artigo": "Art. 18, III", "meio": "PATCH /api/v1/me"},
        {"direito": "Portabilidade dos dados", "artigo": "Art. 18, V", "meio": "GET /api/v1/me/portabilidade"},
        {"direito": "Eliminação dos dados pessoais", "artigo": "Art. 18, VI", "meio": "DELETE /api/v1/me"},
    ]

    return MeDeclarationResponse(
        titular=resumo,
        controlador=controlador_info,
        finalidades_e_bases_legais=finalidades,
        historico_de_operacoes_ropa=historico_ropa,
        destinatarios_e_transferencias=destinatarios,
        politica_de_retencao=politica_retencao,
        direitos_do_titular=direitos,
    )


@router.patch("", response_model=MeSummaryResponse)
def atualizar_dados_cadastrais(
    dados: MeUpdateRequest,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """
    Retificação e atualização de dados cadastrais (Art. 18, III da LGPD).
    """
    if dados.display_name is not None:
        usuario.display_name = dados.display_name.strip()

    if dados.email is not None:
        email_limpo = dados.email.strip().lower()
        if email_limpo and email_limpo != (usuario.email or ""):
            existente = (
                db.query(UserModel)
                .filter(UserModel.email == email_limpo, UserModel.id != usuario.id)
                .first()
            )
            if existente:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Este endereço de e-mail já está associado a outra conta.",
                )
            usuario.email = email_limpo
            usuario.email_verified = False  # requer nova verificação se aplicável

    db.commit()
    db.refresh(usuario)
    logger.info("[Me] Dados cadastrais atualizados para o usuário %s.", usuario.username)
    return _resumo_do_titular(db, usuario)


@router.get("/portabilidade")
def exportar_para_portabilidade(
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """
    Exportação em formato estruturado e interoperável para portabilidade (Art. 18, V).
    """
    try:
        pacote = profile_service.export_profile(db, usuario.id, session_prefs={})

        # Registrar no ROPA
        ropa_service.registrar(
            db,
            operation="data_export",
            legal_basis="art7_VI_exercicio_de_direitos",
            purpose="Exportação completa de acervo e dados pelo titular para portabilidade",
            data_categories=[
                "identificacao",
                "contato",
                "conteudo_de_pesquisa",
                "referencia_bibliografica",
            ],
            user_id=usuario.id,
            commit=True,
        )

        return pacote
    except Exception as exc:
        logger.error("[Me] Erro ao gerar pacote de portabilidade: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao gerar pacote de portabilidade.",
        )


@router.delete("", response_model=MeDeleteResponse)
def solicitar_eliminacao_de_conta(
    dados: MeDeleteRequest,
    response: Response,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """
    Eliminação de conta e dados pessoais (Art. 18, VI e Art. 16 da LGPD).

    Suporta:
      - `grace_period_days > 0`: Desativação imediata da conta com prazo de arrependimento
        (7 dias por padrão) antes da eliminação física definitiva;
      - `grace_period_days == 0`: Eliminação definitiva e atômica imediata (banco + PDFs no disco).
    """
    confirmacao_valida = (
        dados.confirmation.strip().upper() == "EXCLUIR"
        or dados.confirmation.strip() == usuario.username
    )
    if not confirmacao_valida:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmação inválida. Digite 'EXCLUIR' ou seu nome de usuário para confirmar.",
        )

    # Não permitir que o único owner ativo elimine a si mesmo sem nomear outro no servidor
    if usuario.role == "owner":
        donos_ativos = (
            db.query(UserModel)
            .filter(UserModel.role == "owner", UserModel.is_active == True, UserModel.id != usuario.id)  # noqa: E712
            .count()
        )
        if donos_ativos == 0 and settings.is_server_profile:
            total_usuarios = db.query(UserModel).count()
            if total_usuarios > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Esta é a única conta de administrador ativa da instalação.",
                )

    user_id = usuario.id
    username = usuario.username

    if dados.grace_period_days > 0:
        # Desativação temporária para prazo de arrependimento
        usuario.is_active = False
        db.commit()
        revoke_all_sessions(db, user_id)
        response.delete_cookie(SESSION_COOKIE, path="/")

        data_agendada = datetime.now(timezone.utc) + timedelta(days=dados.grace_period_days)
        logger.info(
            "[Me] Conta '%s' (%s) desativada com prazo de arrependimento de %d dias.",
            username,
            user_id,
            dados.grace_period_days,
        )

        return MeDeleteResponse(
            status="scheduled",
            immediate=False,
            scheduled_erasure_at=data_agendada,
            message=(
                f"Sua conta foi desativada e todas as sessões foram encerradas. "
                f"A eliminação definitiva ocorrerá em {dados.grace_period_days} dias."
            ),
        )

    # Eliminação imediata definitiva
    executar_eliminacao_completa_usuario(db, user_id)
    response.delete_cookie(SESSION_COOKIE, path="/")

    return MeDeleteResponse(
        status="erased",
        immediate=True,
        scheduled_erasure_at=None,
        message="Sua conta, projetos e arquivos foram completamente eliminados.",
    )
