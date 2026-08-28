"""datas com fuso (timestamptz)

Revision ID: eb25063c7237
Revises: 48963bb8d65a
Create Date: 2026-08-27

Converte as 21 colunas de data para `timestamptz` no PostgreSQL.

**Por que a conversão não é trivial.** `ALTER COLUMN ... TYPE timestamptz` sem
mais nada faz o PostgreSQL interpretar cada valor armazenado como hora local
*do servidor* e convertê-la para UTC. O RSAC sempre gravou UTC, então num
servidor configurado em `America/Sao_Paulo` essa conversão somaria três horas a
toda data do banco — silenciosamente, sem erro, e o sintoma apareceria depois
como sessão que expira na hora errada e retenção que apaga cedo demais. O
`postgresql_using` abaixo declara o que os dados de fato são: UTC. O teste
`test_conversao_para_timestamptz_preserva_o_instante` demonstra a diferença.

**Por que o SQLite fica de fora.** Ele não tem tipo de data com fuso; o
`timezone=True` é ignorado pelo dialeto e a coluna continua exatamente a mesma.
Rodar `alter_column` ali só acionaria o modo em lote, que recria cada tabela e
copia os dados — risco real em troca de nenhuma mudança. Do lado do SQLite a
normalização é feita em Python, por `models.as_utc`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'eb25063c7237'
down_revision: Union[str, Sequence[str], None] = '48963bb8d65a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Passa as colunas de data para `timestamptz`, declarando que os dados são UTC."""
    if op.get_bind().dialect.name != "postgresql":
        return

    op.alter_column(
        'ai_settings',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'audit_logs',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'deduplication_reports',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'extraction_answers',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'harvest_runs',
        'started_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="started_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'harvest_runs',
        'completed_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="completed_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'login_attempts',
        'attempted_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="attempted_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'paper_sources',
        'harvested_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="harvested_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'papers',
        'pdf_acquired_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="pdf_acquired_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'papers',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'papers',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'projects',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'projects',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'protocols',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'protocols',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'sessions',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'sessions',
        'expires_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'sessions',
        'last_seen_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="last_seen_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'source_credentials',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'users',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'users',
        'last_login_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="last_login_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    """Volta a `timestamp` sem fuso, preservando a hora de parede em UTC."""
    if op.get_bind().dialect.name != "postgresql":
        return

    op.alter_column(
        'ai_settings',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'audit_logs',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'deduplication_reports',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'extraction_answers',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'harvest_runs',
        'started_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="started_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'harvest_runs',
        'completed_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=True,
        postgresql_using="completed_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'login_attempts',
        'attempted_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="attempted_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'paper_sources',
        'harvested_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="harvested_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'papers',
        'pdf_acquired_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=True,
        postgresql_using="pdf_acquired_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'papers',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'papers',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'projects',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'projects',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'protocols',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'protocols',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'sessions',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'sessions',
        'expires_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'sessions',
        'last_seen_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="last_seen_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'source_credentials',
        'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="updated_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'users',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'users',
        'last_login_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=True,
        postgresql_using="last_login_at AT TIME ZONE 'UTC'",
    )
