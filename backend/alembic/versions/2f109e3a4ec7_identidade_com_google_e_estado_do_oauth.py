"""identidade com google e estado do oauth

Revision ID: 2f109e3a4ec7
Revises: 19550e83628b
Create Date: 2026-08-27

Fase 2 do doc 41: acrescenta a `users` o que o login com Google exige e cria a
tabela do estado de autenticação em curso.

**Duas correções sobre o que a autogeração produziu.**

1. As colunas obrigatórias entravam como `NOT NULL` sem valor padrão. Num banco
   vazio isso funciona; em qualquer instalação com uma conta já provisionada,
   falha na hora — e a instalação com conta é justamente a que existe, porque o
   backend se recusa a subir sem uma no perfil `server`. Aqui elas entram com
   `server_default`, que preenche as linhas existentes, e o padrão é removido
   em seguida para que o esquema volte a coincidir com o modelo (onde o padrão
   é do Python, não do banco).

2. `password_hash` passa a aceitar ausência, e em SQLite isso recria a tabela
   `users` — que `sessions` referencia. `app/schema.py` suspende a verificação
   de integridade durante a migração exatamente por causa disso, e confere
   `PRAGMA foreign_key_check` ao final.

As contas que já existem têm senha, então recebem `auth_provider='password'`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2f109e3a4ec7'
down_revision: Union[str, Sequence[str], None] = '19550e83628b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (coluna, tipo, valor com que as linhas existentes ficam)
COLUNAS_OBRIGATORIAS = [
    ("email_verified", sa.Boolean(), sa.false()),
    ("display_name", sa.String(length=200), sa.text("''")),
    ("auth_provider", sa.String(length=20), sa.text("'password'")),
    ("terms_version", sa.String(length=20), sa.text("''")),
]


def upgrade() -> None:
    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(length=64), nullable=False),
        sa.Column("code_verifier", sa.String(length=128), nullable=False),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("redirect_after", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("state"),
    )
    op.create_index("ix_oauth_states_expires_at", "oauth_states", ["expires_at"])

    op.add_column("users", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column("users", sa.Column("google_sub", sa.String(length=64), nullable=True))
    op.add_column(
        "users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True)
    )

    for nome, tipo, padrao in COLUNAS_OBRIGATORIAS:
        op.add_column(
            "users", sa.Column(nome, tipo, nullable=False, server_default=padrao)
        )

    # O padrão do banco cumpriu seu papel — preencher as linhas que já
    # existiam — e agora sai, para que o esquema volte a coincidir com o modelo,
    # onde o padrão é do Python. Como retirá-lo depende do dialeto: o SQLite não
    # implementa `ALTER COLUMN ... DROP DEFAULT`, mas recria a tabela inteira no
    # modo em lote, então o padrão sai junto com a reconstrução — na mesma
    # passagem em que `password_hash` deixa de ser obrigatória.
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("users") as lote:
            lote.alter_column("password_hash", existing_type=sa.Text(), nullable=True)
            for nome, tipo, _ in COLUNAS_OBRIGATORIAS:
                lote.alter_column(nome, existing_type=tipo, server_default=None)
    else:
        for nome, tipo, _ in COLUNAS_OBRIGATORIAS:
            op.alter_column("users", nome, existing_type=tipo, server_default=None)
        op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=True)

    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_index("ix_users_email", table_name="users")

    # A volta exige que nenhuma conta esteja sem senha: uma conta criada por
    # Google não tem como voltar a um esquema em que a senha é obrigatória.
    conexao = op.get_bind()
    sem_senha = conexao.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE password_hash IS NULL")
    ).scalar_one()
    if sem_senha:
        raise RuntimeError(
            f"{sem_senha} conta(s) entram apenas com Google e ficariam sem "
            "credencial nenhuma ao reverter esta migração. Defina uma senha "
            "para elas antes (`python -m app.cli reset-password <usuario>`)."
        )

    with op.batch_alter_table("users") as lote:
        lote.alter_column("password_hash", existing_type=sa.Text(), nullable=False)

    for nome, _, _ in reversed(COLUNAS_OBRIGATORIAS):
        op.drop_column("users", nome)
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "email")

    op.drop_index("ix_oauth_states_expires_at", table_name="oauth_states")
    op.drop_table("oauth_states")
