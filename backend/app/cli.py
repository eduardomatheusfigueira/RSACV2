#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Utilitários de linha de comando para contas de acesso.

Provisionamento fora da API de propósito: a primeira conta precisa nascer antes
de existir qualquer sessão, e uma rota "criar o primeiro usuário" aberta na
internet é exatamente o buraco que a Fase 1 fecha.

Uso:
    python -m app.cli create-user pesquisador --role owner
    python -m app.cli list-users
    python -m app.cli reset-password pesquisador
"""

from __future__ import annotations

import argparse
import sys

from app.database import SessionLocal, engine
from app.schema import aplicar_migracoes
from app.infrastructure.persistence.models import UserModel
from app.security.passwords import (
    PasswordPolicyError,
    generate_password,
    hash_password,
)
from app.security.sessions import revoke_all_sessions


def _imprimir_credencial(username: str, senha: str, role: str) -> None:
    """A senha aparece uma única vez — não é guardada em lugar nenhum."""
    print()
    print("=" * 64)
    print("  CONTA CRIADA — anote a senha agora, ela não será exibida de novo")
    print("=" * 64)
    print(f"  Usuário: {username}")
    print(f"  Senha:   {senha}")
    print(f"  Papel:   {role}")
    print("=" * 64)
    print()


def create_user(args: argparse.Namespace) -> int:
    aplicar_migracoes(engine)
    db = SessionLocal()
    try:
        username = args.username.strip()
        if db.query(UserModel).filter(UserModel.username == username).first():
            print(f"[X] O usuário '{username}' já existe.", file=sys.stderr)
            return 1

        senha = args.password or generate_password()
        try:
            password_hash = hash_password(senha)
        except PasswordPolicyError as exc:
            print(f"[X] {exc}", file=sys.stderr)
            return 1

        user = UserModel(username=username, password_hash=password_hash, role=args.role)
        db.add(user)
        db.commit()

        _imprimir_credencial(username, senha, args.role)
        return 0
    finally:
        db.close()


def list_users(args: argparse.Namespace) -> int:
    aplicar_migracoes(engine)
    db = SessionLocal()
    try:
        usuarios = db.query(UserModel).order_by(UserModel.created_at.asc()).all()
        if not usuarios:
            print("Nenhuma conta provisionada.")
            return 0
        print(f"{'USUÁRIO':<24} {'PAPEL':<12} {'ATIVA':<6} ÚLTIMO LOGIN")
        for u in usuarios:
            ultimo = u.last_login_at.isoformat(sep=" ", timespec="minutes") if u.last_login_at else "—"
            print(f"{u.username:<24} {u.role:<12} {'sim' if u.is_active else 'não':<6} {ultimo}")
        return 0
    finally:
        db.close()


def reset_password(args: argparse.Namespace) -> int:
    aplicar_migracoes(engine)
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.username == args.username.strip()).first()
        if not user:
            print(f"[X] Usuário '{args.username}' não encontrado.", file=sys.stderr)
            return 1

        senha = args.password or generate_password()
        try:
            user.password_hash = hash_password(senha)
        except PasswordPolicyError as exc:
            print(f"[X] {exc}", file=sys.stderr)
            return 1

        user.is_active = True
        db.commit()
        # Trocar a senha sem derrubar as sessões abertas deixaria o acesso
        # antigo válido — inútil se a troca foi motivada por suspeita.
        revoke_all_sessions(db, user.id)

        _imprimir_credencial(user.username, senha, user.role)
        return 0
    finally:
        db.close()


from datetime import datetime, timedelta, timezone
import secrets

from app.database import SessionLocal, engine
from app.schema import aplicar_migracoes
from app.infrastructure.persistence.models import (
    InviteCodeModel,
    UserModel,
    as_utc,
    generate_uuid,
)
from app.security.passwords import (
    PasswordPolicyError,
    generate_password,
    hash_password,
)
from app.security.sessions import revoke_all_sessions


def _gerar_codigo_convite() -> str:
    p1 = secrets.token_hex(2).upper()
    p2 = secrets.token_hex(2).upper()
    return f"RSAC-{p1}-{p2}"


def create_invite(args: argparse.Namespace) -> int:
    aplicar_migracoes(engine)
    db = SessionLocal()
    try:
        codigo = args.code.strip().upper() if args.code else _gerar_codigo_convite()
        if db.query(InviteCodeModel).filter(InviteCodeModel.code == codigo).first():
            print(f"[X] Já existe um convite com o código '{codigo}'.", file=sys.stderr)
            return 1

        agora = datetime.now(timezone.utc)
        expira = agora + timedelta(days=args.expires_days) if args.expires_days else None

        convite = InviteCodeModel(
            id=generate_uuid(),
            code=codigo,
            created_at=agora,
            expires_at=expira,
            is_used=False,
            is_revoked=False,
            note=args.note.strip() if args.note else "",
        )
        db.add(convite)
        db.commit()

        print()
        print("=" * 68)
        print("  CONVITE DE USO ÚNICO GERADO COM SUCESSO")
        print("=" * 68)
        print(f"  Código:   {convite.code}")
        if convite.note:
            print(f"  Nota:     {convite.note}")
        if convite.expires_at:
            print(f"  Expira:   {convite.expires_at.strftime('%d/%m/%Y %H:%M UTC')}")
        print("=" * 68)
        print("  Envie este código ao pesquisador para que ele realize o cadastro.")
        print()
        return 0
    finally:
        db.close()


def list_invites(args: argparse.Namespace) -> int:
    aplicar_migracoes(engine)
    db = SessionLocal()
    try:
        convites = db.query(InviteCodeModel).order_by(InviteCodeModel.created_at.desc()).all()
        if not convites:
            print("Nenhum convite emitido até o momento.")
            return 0

        agora = datetime.now(timezone.utc)
        print(f"{'CÓDIGO':<18} {'STATUS':<16} {'EXPIRAÇÃO':<18} {'USUÁRIO REGISTRADO':<22} NOTA")
        print("-" * 90)
        for c in convites:
            if c.is_revoked:
                status_str = "REVOGADO"
            elif c.is_used:
                status_str = "UTILIZADO"
            elif c.expires_at and as_utc(c.expires_at) < agora:
                status_str = "EXPIRADO"
            else:
                status_str = "DISPONÍVEL"

            exp_str = c.expires_at.strftime("%d/%m/%Y %H:%M") if c.expires_at else "Sem expiração"

            usuario_str = "—"
            if c.used_by_user_id:
                u = db.query(UserModel).filter(UserModel.id == c.used_by_user_id).first()
                if u:
                    usuario_str = f"{u.username} ({u.email or ''})"

            print(f"{c.code:<18} {status_str:<16} {exp_str:<18} {usuario_str:<22} {c.note}")
        return 0
    finally:
        db.close()


def revoke_invite(args: argparse.Namespace) -> int:
    aplicar_migracoes(engine)
    db = SessionLocal()
    try:
        codigo = args.code.strip().upper()
        convite = db.query(InviteCodeModel).filter(InviteCodeModel.code == codigo).first()
        if not convite:
            print(f"[X] Convite com código '{codigo}' não encontrado.", file=sys.stderr)
            return 1
        if convite.is_used:
            print(f"[X] Não é possível revogar o convite '{codigo}' pois ele já foi utilizado.", file=sys.stderr)
            return 1

        convite.is_revoked = True
        db.commit()
        print(f"[OK] Convite '{codigo}' revogado com sucesso.")
        return 0
    finally:
        db.close()


def generate_secret_key(args: argparse.Namespace) -> int:
    """
    Gera uma chave-mestra para o perfil `server`.

    No modo servidor a chave precisa vir do ambiente — um arquivo ao lado do
    banco seria lido pela mesma falha que leria o banco (doc 29 §29.4.1).
    """
    import base64
    import os

    chave = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")

    print()
    print("=" * 72)
    print("  CHAVE-MESTRA GERADA — exporte-a antes de subir o servidor")
    print("=" * 72)
    print(f"  RSAC_SECRET_KEY={chave}")
    print("=" * 72)
    print("  Sem esta chave os segredos gravados não podem ser decifrados.")
    print("  Guarde-a fora do computador que hospeda o banco.")
    print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Gestão de contas de acesso e convites do Revsist",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_create = sub.add_parser("create-user", help="Cria uma conta de acesso")
    p_create.add_argument("username", help="Nome de usuário")
    p_create.add_argument(
        "--role", default="researcher", choices=["owner", "researcher"], help="Papel da conta"
    )
    p_create.add_argument(
        "--password", default=None, help="Senha (omita para o servidor sortear uma forte)"
    )
    p_create.set_defaults(func=create_user)

    p_list = sub.add_parser("list-users", help="Lista as contas cadastradas")
    p_list.set_defaults(func=list_users)

    p_reset = sub.add_parser("reset-password", help="Redefine a senha de uma conta")
    p_reset.add_argument("username", help="Nome de usuário")
    p_reset.add_argument("--password", default=None, help="Nova senha (omita para sortear)")
    p_reset.set_defaults(func=reset_password)

    p_cinv = sub.add_parser("create-invite", help="Gera um convite de uso único para cadastro")
    p_cinv.add_argument("--note", default="", help="Nota ou nome do destinatário do convite")
    p_cinv.add_argument("--expires-days", type=int, default=None, help="Dias de validade do convite (opcional)")
    p_cinv.add_argument("--code", default=None, help="Código personalizado (opcional)")
    p_cinv.set_defaults(func=create_invite)

    p_linv = sub.add_parser("list-invites", help="Lista todos os convites emitidos")
    p_linv.set_defaults(func=list_invites)

    p_rinv = sub.add_parser("revoke-invite", help="Revoga um convite não utilizado")
    p_rinv.add_argument("code", help="Código do convite a revogar")
    p_rinv.set_defaults(func=revoke_invite)

    p_key = sub.add_parser(
        "generate-secret-key", help="Gera a chave-mestra da cifra (perfil server)"
    )
    p_key.set_defaults(func=generate_secret_key)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
