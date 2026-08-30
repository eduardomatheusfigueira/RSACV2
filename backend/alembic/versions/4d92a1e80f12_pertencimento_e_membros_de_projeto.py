"""pertencimento_e_membros_de_projeto

Cria `project_members`, a tabela de participação em projetos (doc 43 §43.3.1, Fase 0).
Transfere a titularidade exclusiva de `owner_id` para pertinência ativa via `project_members`.
Popula automaticamente o dono de cada projeto existente como 'coordenador'.

Revision ID: 4d92a1e80f12
Revises: 3c810d7a5ab1
Create Date: 2026-08-30 00:50:00.000000

"""
from datetime import datetime, timezone
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d92a1e80f12'
down_revision: Union[str, Sequence[str], None] = '3c810d7a5ab1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criação da tabela project_members
    op.create_table(
        'project_members',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_role', sa.String(length=20), nullable=False, server_default='coordenador'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('invited_by_user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_project_members_project_user'),
    )
    op.create_index('ix_project_members_user', 'project_members', ['user_id'], unique=False)
    op.create_index('ix_project_members_project', 'project_members', ['project_id'], unique=False)

    # 2. Backfill de dados: associar os donos de todos os projetos existentes como coordenadores
    bind = op.get_bind()
    projects_meta = sa.Table(
        'projects',
        sa.MetaData(),
        sa.Column('id', sa.String(36)),
        sa.Column('owner_id', sa.String(36)),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    members_meta = sa.Table(
        'project_members',
        sa.MetaData(),
        sa.Column('id', sa.String(36)),
        sa.Column('project_id', sa.String(36)),
        sa.Column('user_id', sa.String(36)),
        sa.Column('project_role', sa.String(20)),
        sa.Column('is_active', sa.Boolean()),
        sa.Column('joined_at', sa.DateTime(timezone=True)),
    )

    rows = bind.execute(sa.select(projects_meta.c.id, projects_meta.c.owner_id, projects_meta.c.created_at)).fetchall()
    now_utc = datetime.now(timezone.utc)
    for row in rows:
        proj_id, owner_id, created_at = row[0], row[1], row[2]
        if owner_id:
            bind.execute(
                members_meta.insert().values(
                    id=str(uuid.uuid4()),
                    project_id=proj_id,
                    user_id=owner_id,
                    project_role='coordenador',
                    is_active=True,
                    joined_at=created_at or now_utc,
                )
            )


def downgrade() -> None:
    op.drop_index('ix_project_members_project', table_name='project_members')
    op.drop_index('ix_project_members_user', table_name='project_members')
    op.drop_table('project_members')
