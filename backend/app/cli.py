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
        description="Gestão de contas de acesso do Revsist",
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
