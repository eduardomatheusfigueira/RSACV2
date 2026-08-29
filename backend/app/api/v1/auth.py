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
from app.infrastructure.persistence.models import UserModel
from app.schemas.auth import (
    AuthStatusResponse,
    LocalTokenRequest,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    UserCreatedResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
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

logger = logging.getLogger(__name__)

public_auth_router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter(prefix="/auth", tags=["auth"])


def _serializar(user: UserModel) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
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
    logger.info("[Auth] Entrada com Google: %s", usuario.username)
    return resposta


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
        terms_accepted_at=datetime.now(timezone.utc),
        terms_version=settings.terms_version,
    )
    db.add(novo)
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
    db.commit()
    revoke_all_sessions(db, user.id)
    return {"status": "ok", "message": f"Conta '{user.username}' desativada."}
