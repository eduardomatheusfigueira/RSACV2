#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Router de Autenticação e Contas (doc 29 §29.3).

Este módulo tem duas metades com regimes opostos, e a distinção é deliberada:

  * `public_auth_router` — as três rotas que respondem sem sessão: `status`,
    `login` e `local`. É a lista de exceções de §29.3.1, e ela precisa ser
    curta o bastante para caber na cabeça de quem revisa.
  * `router` — gestão de contas, que exige sessão como todo o resto e, para
    criar ou remover usuários, papel `owner`.
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import (
    InviteCodeModel,
    ProjectInvitationModel,
    ProjectMemberModel,
    ProjectModel,
    UserModel,
    as_utc,
    utcnow,
)
from app.schemas.auth import (
    AuthStatusResponse,
    LocalTokenRequest,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    UserAdminResetPasswordRequest,
    UserAdminUpdateRequest,
    UserCreatedResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
)
from app.schemas.invites import (
    RegisterWithInviteRequest,
    ValidateInviteRequest,
    ValidateInviteResponse,
)
from app.security.dependencies import (
    ROLE_OWNER,
    ROLE_RESEARCHER,
    extrair_token,
    require_owner,
    require_session,
    usuario_atual_opcional,
)
from app.security import google_oauth, oauth_state
from app.security.local_token import matches_local_token, read_local_token
from app.security.provisioning import senha_inutilizavel
from app.security.passwords import (
    PasswordPolicyError,
    generate_password,
    hash_password,
    verify_password,
)
from app.security.sessions import (
    SESSION_COOKIE,
    create_session,
    login_bloqueado,
    register_login_attempt,
    revoke_all_sessions,
    revoke_session,
)
from app.services import ropa_service

logger = logging.getLogger(__name__)

from app.security import bilhete_de_canal

public_auth_router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter(prefix="/auth", tags=["auth"])


def _serializar(user: UserModel) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        email=user.email,
        full_name=user.full_name or "",
        phone=user.phone or "",
        institution=user.institution or "",
        academic_degree=user.academic_degree or "",
        is_studying=bool(user.is_studying),
        study_program=user.study_program or "",
        profession=user.profession or "",
        research_area=user.research_area or "",
        auth_provider=user.auth_provider or "password",
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _definir_cookie(response: Response, token: str, request: Request) -> None:
    """
    Grava o cookie de sessão.

    `HttpOnly` tira o token do alcance de qualquer script na página;
    `SameSite=strict` impede que outro site o envie junto de uma requisição
    forjada; `Secure` entra quando a conexão é HTTPS — que é o caso do túnel,
    e não o do `localhost` em desenvolvimento.
    """
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def _emitir_sessao(
    db: Session, user: UserModel, request: Request, response: Response
) -> LoginResponse:
    token, _ = create_session(db, user, user_agent=request.headers.get("User-Agent", ""))
    _definir_cookie(response, token, request)
    return LoginResponse(
        user=_serializar(user),
        access_token=token,
        expires_in_hours=settings.session_ttl_hours,
    )


# ── Rotas públicas (a lista de exceções de §29.3.1) ───────────────────

@public_auth_router.get("/status", response_model=AuthStatusResponse)
def auth_status(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Diz se há contas provisionadas e se esta requisição já está autenticada.

    Não revela nome de usuário nem nada que ajude a adivinhar credencial — só o
    necessário para o cliente decidir entre a tela de login e a aplicação, e
    para o lançador recusar-se a publicar um backend desprotegido.
    """
    total_contas = db.query(UserModel).filter(UserModel.is_active == True).count()  # noqa: E712
    usuario = usuario_atual_opcional(request, db)

    return AuthStatusResponse(
        authentication_enabled=True,
        deployment_profile=settings.deployment_profile.value,
        has_accounts=total_contas > 0,
        local_token_accepted=(not settings.is_server_profile) and bool(read_local_token()),
        google_login_enabled=google_oauth.esta_configurado(),
        authenticated=usuario is not None,
        user=_serializar(usuario) if usuario else None,
    )


@public_auth_router.post("/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Autentica por usuário e senha e abre uma sessão."""
    username = data.username.strip()
    client_host = request.client.host if request.client else ""

    if login_bloqueado(db, username):
        logger.warning("[Auth] Login bloqueado por excesso de tentativas: %s", username)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde 15 minutos e tente de novo.",
        )

    user = db.query(UserModel).filter(UserModel.username == username).first()

    # Conta sem senha utilizável — criada pelo Google, ou a conta local que a
    # instalação de mesa provisiona sozinha. `verify_password` já devolveria
    # `False`, mas a mensagem sairia como "usuário ou senha inválidos", e a
    # pessoa ficaria tentando lembrar de uma senha que nunca existiu. Aqui a
    # resposta diz o que fazer.
    if user and user.is_active and senha_inutilizavel(user.password_hash):
        register_login_attempt(db, username, client_host, successful=False)
        detalhe = (
            "Esta conta entra com Google. Use o botão “Entrar com Google”."
            if user.google_sub
            else "Esta conta não tem senha definida. Defina uma com "
            "`python -m app.cli reset-password %s`." % user.username
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detalhe)

    senha_confere = bool(user) and verify_password(user.password_hash or "", data.password)

    if not user or not senha_confere or not user.is_active:
        register_login_attempt(db, username, client_host, successful=False)
        # Mensagem única de propósito: distinguir "usuário não existe" de
        # "senha errada" entregaria a lista de contas a quem sondar.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos.",
        )

    register_login_attempt(db, username, client_host, successful=True)
    ropa_service.registrar(
        db,
        operation="login",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Autenticação de usuário no sistema",
        data_categories=["identificacao", "credencial", "conexao"],
        user_id=user.id,
        commit=True,
    )
    logger.info("[Auth] Login bem-sucedido: %s (%s)", user.username, user.role)
    return _emitir_sessao(db, user, request, response)


# ── Entrada com Google (doc 40 §40.4) ─────────────────────────────────


def _redirect_uri(request: Request) -> str:
    """
    Endereço de retorno registrado no Google Cloud.

    Preferimos `RSAC_PUBLIC_BASE_URL` a derivar da requisição: atrás de um
    túnel ou proxy, o `Host` que chega pode não ser o nome público, e o Google
    compara o `redirect_uri` **literalmente** com o que está cadastrado.
    """
    base = (settings.public_base_url or "").rstrip("/")
    if not base:
        base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/google/callback"


def _admitido(email: str) -> bool:
    """A lista de admissão aceita este endereço? Vazia = qualquer um."""
    admitidos = settings.dominios_admitidos
    if not admitidos:
        return True
    email = email.lower()
    dominio = "@" + email.split("@")[-1]
    return email in admitidos or dominio in admitidos


@public_auth_router.get("/google/start")
def iniciar_login_com_google(
    request: Request,
    redirect_after: str | None = None,
    db: Session = Depends(get_db),
):
    """Inicia o fluxo: grava o estado e manda o navegador ao Google."""
    if not google_oauth.esta_configurado():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Entrada com Google não está disponível nesta instalação.",
        )

    verificador = google_oauth.gerar_verificador()
    nonce = secrets.token_urlsafe(24)
    estado = oauth_state.criar(
        db, code_verifier=verificador, nonce=nonce, redirect_after=redirect_after
    )

    destino = google_oauth.montar_url_de_autorizacao(
        state=estado.state,
        nonce=nonce,
        code_challenge=google_oauth.desafio_de(verificador),
        redirect_uri=_redirect_uri(request),
    )
    return RedirectResponse(destino, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@public_auth_router.get("/google/callback")
async def concluir_login_com_google(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Conclui o fluxo: valida o que voltou, resolve a conta e emite a sessão.

    Erros respondem com redirecionamento para a tela de login carregando um
    motivo curto, e não com JSON: quem está aqui é um navegador que acabou de
    voltar do Google, e uma página de erro de API seria um beco sem saída.
    """
    if error:
        logger.info("[OAuth] Fluxo cancelado no Google: %s", error)
        return _voltar_ao_login("cancelado")

    registro = oauth_state.consumir(db, state)
    if registro is None or not code:
        # Estado ausente, vencido ou já usado. Não se distingue qual: para quem
        # tenta reapresentar um callback, os três casos devem parecer o mesmo.
        return _voltar_ao_login("estado_invalido")

    try:
        id_token = await google_oauth.trocar_codigo_por_id_token(
            code=code,
            code_verifier=registro.code_verifier,
            redirect_uri=_redirect_uri(request),
        )
        identidade = await google_oauth.validar_id_token(
            id_token, nonce_esperado=registro.nonce
        )
    except google_oauth.IdentidadeRecusada as exc:
        logger.warning("[OAuth] Identidade recusada: %s", exc)
        return _voltar_ao_login("recusado")
    except google_oauth.GoogleOAuthIndisponivel:
        return _voltar_ao_login("indisponivel")

    usuario = _resolver_conta(db, identidade)
    if usuario is None:
        return _voltar_ao_login("nao_admitido")
    if not usuario.is_active:
        return _voltar_ao_login("conta_inativa")

    resposta = RedirectResponse(
        registro.redirect_after, status_code=status.HTTP_303_SEE_OTHER
    )
    token, _ = create_session(db, usuario, user_agent=request.headers.get("User-Agent", ""))
    _definir_cookie(resposta, token, request)
    ropa_service.registrar(
        db,
        operation="login",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Autenticação de usuário via Google OAuth",
        data_categories=["identificacao", "contato", "identificador_externo", "conexao"],
        user_id=usuario.id,
        commit=True,
    )
    logger.info("[Auth] Entrada com Google: %s", usuario.username)
    return resposta


@public_auth_router.post(
    "/invite/validate",
    response_model=ValidateInviteResponse,
    status_code=status.HTTP_200_OK,
    summary="Valida um código de convite para cadastro",
)
def validar_convite(
    payload: ValidateInviteRequest,
    db: Session = Depends(get_db),
):
    """
    Valida se um código de convite (plataforma ou equipe) é autêntico, está ativo e ainda não foi utilizado.
    """
    codigo = payload.invite_code.strip().upper()

    if codigo.startswith("RSAC-EQ-"):
        # Convite de equipe (doc 43 §43.10.2)
        convite_eq = db.query(ProjectInvitationModel).filter(ProjectInvitationModel.code == codigo).first()
        if not convite_eq:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Convite de equipe não encontrado. Verifique o código e tente novamente.",
            )
        if convite_eq.revoked_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este convite de equipe foi revogado pela coordenação do projeto.",
            )
        if convite_eq.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este convite de equipe já foi utilizado.",
            )
        agora = utcnow()
        expira = as_utc(convite_eq.expires_at)
        if expira and expira < agora:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este convite de equipe expirou.",
            )
        proj = db.query(ProjectModel).filter(ProjectModel.id == convite_eq.project_id).first()
        nome_proj = f" '{proj.title}'" if proj else ""
        return ValidateInviteResponse(
            valid=True,
            note=f"Convite de equipe ({convite_eq.project_role}) para o projeto{nome_proj}",
            expires_at=convite_eq.expires_at,
        )

    # Convite geral da plataforma (InviteCodeModel)
    convite = db.query(InviteCodeModel).filter(InviteCodeModel.code == codigo).first()

    if not convite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código de convite não encontrado. Verifique o código e tente novamente.",
        )

    if convite.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este convite foi revogado pela administração.",
        )

    if convite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este convite já foi utilizado e não pode ser reutilizado.",
        )

    agora = datetime.now(timezone.utc)
    if convite.expires_at:
        expira = as_utc(convite.expires_at)
        if expira and expira < agora:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este convite expirou.",
            )

    return ValidateInviteResponse(
        valid=True,
        note=convite.note or "Convite válido para cadastro",
        expires_at=convite.expires_at,
    )


@public_auth_router.post(
    "/register-with-invite",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo pesquisador com convite de uso único",
)
def registrar_com_convite(
    payload: RegisterWithInviteRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Cadastra um novo pesquisador utilizando um convite de plataforma ou de equipe.
    Executa a criação da conta, invalidação do convite e participação na mesma transação atômica.
    """
    codigo = payload.invite_code.strip().upper()
    agora = utcnow()

    is_team_invite = codigo.startswith("RSAC-EQ-")
    convite_plataforma = None
    convite_equipe = None

    # 1. Obter e bloquear o convite
    if is_team_invite:
        convite_equipe = (
            db.query(ProjectInvitationModel)
            .filter(ProjectInvitationModel.code == codigo)
            .with_for_update()
            .first()
        )
        if not convite_equipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Código de convite de equipe inválido.",
            )
        if convite_equipe.revoked_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este convite de equipe foi revogado pela coordenação.",
            )
        if convite_equipe.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este convite de equipe já foi utilizado.",
            )
        expira = as_utc(convite_equipe.expires_at)
        if expira and expira < agora:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este convite de equipe expirou.",
            )
    else:
        convite_plataforma = (
            db.query(InviteCodeModel)
            .filter(InviteCodeModel.code == codigo)
            .with_for_update()
            .first()
        )
        if not convite_plataforma:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Código de convite inválido.",
            )
        if convite_plataforma.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este convite foi revogado pela administração.",
            )
        if convite_plataforma.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este convite já foi utilizado para registrar outro usuário.",
            )
        if convite_plataforma.expires_at:
            expira = as_utc(convite_plataforma.expires_at)
            if expira and expira < agora:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este convite expirou.",
                )

    # 2. Verificar se o username já existe
    username_limpo = payload.username.strip().lower()
    existente_user = db.query(UserModel).filter(UserModel.username == username_limpo).first()
    if existente_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este nome de usuário já está em uso. Por favor, escolha outro.",
        )

    # 3. Verificar se o e-mail já existe
    email_limpo = str(payload.email).strip().lower()
    existente_email = db.query(UserModel).filter(UserModel.email == email_limpo).first()
    if existente_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado no sistema.",
        )

    # 4. Validar política de senha
    try:
        senha_hash = hash_password(payload.password)
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # 5. Criar o novo usuário com todos os dados acadêmicos
    novo_usuario = UserModel(
        username=username_limpo,
        password_hash=senha_hash,
        role=ROLE_RESEARCHER,
        is_active=True,
        email=email_limpo,
        email_verified=True,
        display_name=payload.full_name.strip(),
        full_name=payload.full_name.strip(),
        phone=payload.phone.strip(),
        institution=payload.institution.strip(),
        academic_degree=payload.academic_degree.strip(),
        is_studying=payload.is_studying,
        study_program=payload.study_program.strip(),
        profession=payload.profession.strip(),
        research_area=payload.research_area.strip(),
        auth_provider="password",
        terms_accepted_at=agora,
        terms_version="2026-08-29",
    )
    db.add(novo_usuario)
    db.flush()

    # 6. Atualizar o convite e, se for convite de equipe, criar a participação
    if convite_equipe:
        convite_equipe.accepted_at = agora
        convite_equipe.accepted_by_user_id = novo_usuario.id

        membro_equipe = ProjectMemberModel(
            project_id=convite_equipe.project_id,
            user_id=novo_usuario.id,
            project_role=convite_equipe.project_role,
            is_active=True,
            invited_by_user_id=convite_equipe.created_by_user_id,
            joined_at=agora,
        )
        db.add(membro_equipe)

        ropa_service.registrar(
            db,
            operation="team_membership_created",
            legal_basis="art7_V_execucao_de_contrato",
            purpose="Inclusão em equipe de projeto via cadastro com convite RSAC-EQ",
            data_categories=["identificacao"],
            user_id=novo_usuario.id,
            commit=False,
        )
    elif convite_plataforma:
        convite_plataforma.is_used = True
        convite_plataforma.used_at = agora
        convite_plataforma.used_by_user_id = novo_usuario.id

    # 7. Criar sessão e cookie de acesso
    token, _sessao = create_session(
        db, novo_usuario, user_agent=request.headers.get("User-Agent", "")
    )
    _definir_cookie(response, token, request)

    # 8. Registrar no ROPA (Art. 37 LGPD)
    ropa_service.registrar(
        db,
        operation="signup",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Cadastro de novo pesquisador através de convite de uso único",
        data_categories=[
            "identificacao",
            "contato",
            "credencial",
            "conexao",
        ],
        user_id=novo_usuario.id,
        commit=True,
    )

    logger.info(
        "[Cadastro] Novo usuário '%s' (%s) cadastrado com sucesso usando o convite '%s'.",
        novo_usuario.username,
        novo_usuario.email,
        codigo,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in_hours=settings.session_ttl_hours,
        user=_serializar(novo_usuario),
    )


def _voltar_ao_login(motivo: str) -> RedirectResponse:
    return RedirectResponse(f"/app/login?erro={motivo}", status_code=status.HTTP_303_SEE_OTHER)


def _resolver_conta(db: Session, identidade) -> Optional[UserModel]:
    """
    Encontra ou cria a conta desta identidade.

    A ordem importa e está em doc 40 §40.4.3:

    1. Já existe alguém com este `google_sub`? É ele — o `sub` é estável, ao
       contrário do e-mail, que dentro de um domínio corporativo pode ser
       reatribuído a outra pessoa.
    2. Existe conta com este e-mail? Vincula. Só é seguro porque
       `validar_id_token` já exigiu `email_verified`; sem essa trava, este seria
       o passo por onde se toma a conta de outro.
    3. Não existe? Cria — sempre como `researcher`. Autocadastro **nunca**
       concede `owner`: essa conta nasce só pela linha de comando.
    """
    usuario = (
        db.query(UserModel).filter(UserModel.google_sub == identidade.sub).first()
    )
    if usuario:
        usuario.last_login_at = datetime.now(timezone.utc)
        db.commit()
        return usuario

    por_email = (
        db.query(UserModel).filter(UserModel.email == identidade.email).first()
    )
    if por_email:
        por_email.google_sub = identidade.sub
        por_email.email_verified = True
        por_email.auth_provider = "both" if por_email.password_hash else "google"
        if not por_email.display_name:
            por_email.display_name = identidade.nome
        db.commit()
        logger.info("[Auth] Conta %s vinculada ao Google.", por_email.username)
        return por_email

    if not _admitido(identidade.email):
        logger.info("[Auth] Autocadastro recusado pela lista de admissão.")
        return None

    novo = UserModel(
        username=_username_disponivel(db, identidade.email),
        password_hash=None,
        role=ROLE_RESEARCHER,
        email=identidade.email,
        email_verified=True,
        google_sub=identidade.sub,
        display_name=identidade.nome,
        auth_provider="google",
        terms_accepted_at=None,
        terms_version="",
    )
    db.add(novo)
    db.flush()
    ropa_service.registrar(
        db,
        operation="signup",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Cadastro de nova conta de usuário via Google OAuth",
        data_categories=["identificacao", "contato", "identificador_externo"],
        user_id=novo.id,
        commit=False,
    )
    db.commit()
    db.refresh(novo)
    logger.info("[Auth] Conta criada por entrada com Google: %s", novo.username)
    return novo


def _username_disponivel(db: Session, email: str) -> str:
    """
    Nome de usuário a partir do e-mail, com sufixo se já houver colisão.

    O nome continua sendo a identificação visível nas trilhas de auditoria, e
    duas pessoas de instituições diferentes podem ter a mesma parte local.
    """
    base = re.sub(r"[^A-Za-z0-9._-]", "", email.split("@")[0])[:48] or "pesquisador"
    candidato = base
    sufixo = 1
    while db.query(UserModel).filter(UserModel.username == candidato).first():
        sufixo += 1
        candidato = f"{base}-{sufixo}"[:64]
    return candidato


@public_auth_router.post("/local", response_model=LoginResponse)
def login_com_token_local(
    data: LocalTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Troca o token local do perfil desktop por uma sessão.

    É o que mantém o app de mesa sem tela de login: o Electron lê o arquivo
    `runtime_token` e chama esta rota. No perfil `server` ela não existe como
    caminho válido — lá a prova é a senha.
    """
    if settings.is_server_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O token local não é aceito no perfil de servidor. Faça login com usuário e senha.",
        )
    if not matches_local_token(data.token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token local inválido.")

    user = (
        db.query(UserModel)
        .filter(UserModel.is_active == True)  # noqa: E712
        .order_by(UserModel.created_at.asc())
        .first()
    )
    if not user:
        user = UserModel(
            username="pesquisador",
            password_hash=hash_password(generate_password(20)),
            role=ROLE_OWNER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("[Auth] Conta inicial ('pesquisador') provisionada automaticamente via token local.")

    return _emitir_sessao(db, user, request, response)


# ── Rotas autenticadas ────────────────────────────────────────────────

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_session),
):
    """Encerra a sessão no servidor e apaga o cookie."""
    revoke_session(db, extrair_token(request))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "ok", "message": "Sessão encerrada."}


@router.get("/me", response_model=UserResponse)
def me(usuario: UserModel = Depends(require_session)):
    """Identidade da sessão corrente."""
    return _serializar(usuario)


@router.post("/ws-ticket", status_code=200)
def emitir_bilhete_de_canal(usuario: UserModel = Depends(require_session)):
    """
    Emite a credencial de uso único que abre um WebSocket.

    Existe porque abrir um WebSocket é a única requisição em que o navegador
    não deixa mandar cabeçalho: o token de sessão não tem por onde ir, e o
    cookie — `SameSite=strict`, de propósito — não viaja quando a interface
    está numa origem e a API em outra. Esta rota é uma requisição HTTP comum,
    autenticada pelo que houver (cookie ou token), e devolve um bilhete que
    vale por instantes e serve só para isto.

    Ver `app/security/bilhete_de_canal.py` para o porquê de não devolver
    simplesmente o token da sessão.
    """
    return {
        "ticket": bilhete_de_canal.emitir(usuario.id),
        "expires_in": int(bilhete_de_canal.VALIDADE_SEGUNDOS),
    }


@router.post("/terms/accept", response_model=UserResponse)
def aceitar_termos(
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """
    Registra o consentimento e aceite expresso dos Termos de Uso e do Aviso de Privacidade.
    """
    agora = datetime.now(timezone.utc)
    usuario.terms_accepted_at = agora
    usuario.terms_version = settings.terms_version

    ropa_service.registrar(
        db,
        operation="consent_given",
        legal_basis="art7_I_consentimento",
        purpose=f"Aceite expresso dos Termos de Uso e Aviso de Privacidade (versão {settings.terms_version})",
        data_categories=["identificacao", "contato"],
        user_id=usuario.id,
        commit=False,
    )
    db.commit()
    db.refresh(usuario)
    logger.info("[Auth] Aceite dos termos registrado para o usuário: %s", usuario.username)
    return _serializar(usuario)


@router.post("/password", status_code=200)
def alterar_senha(
    data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Troca a própria senha e encerra as demais sessões da conta."""
    if not verify_password(usuario.password_hash, data.current_password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Senha atual incorreta.")
    try:
        usuario.password_hash = hash_password(data.new_password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.commit()
    # Trocar a senha precisa derrubar sessões antigas: se a troca foi motivada
    # por suspeita de vazamento, manter as outras vivas anularia o gesto.
    revoke_all_sessions(db, usuario.id)
    return {"status": "ok", "message": "Senha alterada. Faça login novamente."}


@router.get("/users", response_model=UserListResponse)
def listar_usuarios(
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_owner),
):
    """Lista as contas da instalação. Exclusivo de `owner`."""
    usuarios = db.query(UserModel).order_by(UserModel.created_at.asc()).all()
    return UserListResponse(items=[_serializar(u) for u in usuarios], total=len(usuarios))


@router.post("/users", response_model=UserCreatedResponse, status_code=201)
def criar_usuario(
    data: UserCreateRequest,
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_owner),
):
    """Cria uma conta. Sem senha informada, sorteia uma e a devolve uma só vez."""
    username = data.username.strip()
    if db.query(UserModel).filter(UserModel.username == username).first():
        raise HTTPException(status_code=409, detail=f"O usuário '{username}' já existe.")

    senha_gerada = None
    senha = data.password
    if not senha:
        senha = generate_password()
        senha_gerada = senha

    try:
        user = UserModel(username=username, password_hash=hash_password(senha), role=data.role)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.add(user)
    db.flush()
    ropa_service.registrar(
        db,
        operation="signup",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Criação de conta de usuário por administrador",
        data_categories=["identificacao", "credencial"],
        user_id=user.id,
        commit=False,
    )
    db.commit()
    db.refresh(user)
    logger.info("[Auth] Conta criada: %s (%s)", user.username, user.role)

    return UserCreatedResponse(user=_serializar(user), generated_password=senha_gerada)


@router.delete("/users/{user_id}")
def desativar_usuario(
    user_id: str,
    db: Session = Depends(get_db),
    solicitante: UserModel = Depends(require_owner),
):
    """Desativa uma conta e encerra suas sessões."""
    if user_id == solicitante.id:
        raise HTTPException(status_code=400, detail="Não é possível desativar a própria conta.")

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    donos_ativos = (
        db.query(UserModel)
        .filter(UserModel.role == ROLE_OWNER, UserModel.is_active == True)  # noqa: E712
        .count()
    )
    if user.role == ROLE_OWNER and donos_ativos <= 1:
        raise HTTPException(
            status_code=400,
            detail="Esta é a última conta administradora ativa — a instalação ficaria sem dono.",
        )

    user.is_active = False
    ropa_service.registrar(
        db,
        operation="data_erasure",
        legal_basis="art7_II_obrigacao_legal",
        purpose="Desativação de conta de usuário por administrador",
        data_categories=["identificacao"],
        user_id=user.id,
        commit=False,
    )
    db.commit()
    revoke_all_sessions(db, user.id)
    return {"status": "ok", "message": f"Conta '{user.username}' desativada."}


@router.patch("/users/{user_id}", response_model=UserResponse)
def atualizar_usuario_admin(
    user_id: str,
    data: UserAdminUpdateRequest,
    db: Session = Depends(get_db),
    solicitante: UserModel = Depends(require_owner),
):
    """
    Atualiza papéis, nível de acesso (role), status ativo e dados cadastrais de um usuário.
    Exclusivo de administradores (`owner`).
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if data.role is not None:
        if data.role not in (ROLE_RESEARCHER, ROLE_OWNER):
            raise HTTPException(
                status_code=422,
                detail="Papel inválido. Deve ser 'researcher' ou 'owner'.",
            )

        # Evitar que o último dono ativo perca o papel
        if user.role == ROLE_OWNER and data.role != ROLE_OWNER:
            donos_ativos = (
                db.query(UserModel)
                .filter(UserModel.role == ROLE_OWNER, UserModel.is_active == True)  # noqa: E712
                .count()
            )
            if donos_ativos <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Não é possível alterar o papel do único administrador ativo da instalação.",
                )
        user.role = data.role

    if data.is_active is not None:
        if user.id == solicitante.id and not data.is_active:
            raise HTTPException(
                status_code=400, detail="Não é possível desativar a própria conta."
            )
        user.is_active = data.is_active
        if not data.is_active:
            revoke_all_sessions(db, user.id)

    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    if data.email is not None:
        user.email = data.email.strip().lower()
    if data.phone is not None:
        user.phone = data.phone.strip()
    if data.institution is not None:
        user.institution = data.institution.strip()
    if data.academic_degree is not None:
        user.academic_degree = data.academic_degree.strip()
    if data.is_studying is not None:
        user.is_studying = data.is_studying
    if data.study_program is not None:
        user.study_program = data.study_program.strip()
    if data.profession is not None:
        user.profession = data.profession.strip()
    if data.research_area is not None:
        user.research_area = data.research_area.strip()

    db.commit()
    db.refresh(user)
    logger.info(
        "[Auth] Usuário '%s' (%s) atualizado pelo administrador '%s'.",
        user.username,
        user.id,
        solicitante.username,
    )
    return _serializar(user)


@router.post("/users/{user_id}/reset-password", response_model=dict)
def redefinir_senha_usuario_admin(
    user_id: str,
    data: UserAdminResetPasswordRequest,
    db: Session = Depends(get_db),
    solicitante: UserModel = Depends(require_owner),
):
    """
    Redefine a senha de um usuário como administrador (`owner`).
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    senha = data.new_password if data.new_password else generate_password(12)
    try:
        user.password_hash = hash_password(senha)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.commit()
    revoke_all_sessions(db, user.id)
    logger.info(
        "[Auth] Senha do usuário '%s' redefinida pelo administrador '%s'.",
        user.username,
        solicitante.username,
    )
    return {
        "status": "ok",
        "message": f"Senha do usuário '{user.username}' redefinida com sucesso.",
        "temporary_password": senha,
    }

