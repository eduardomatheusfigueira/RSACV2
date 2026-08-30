"""convites_de_projeto

Cria `project_invitations`, a tabela de convites para participação em projetos (doc 43 §43.3.2, Fase 1).

Revision ID: 5e81d7f39a04
Revises: 4d92a1e80f12
Create Date: 2026-08-30 01:00:00.000000

"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e81d7f39a04'
down_revision: Union[str, Sequence[str], None] = '4d92a1e80f12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_invitations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('project_role', sa.String(length=20), nullable=False, server_default='revisor'),
        sa.Column('created_by_user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_by_user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('note', sa.Text(), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_project_invitations_code'),
    )
    op.create_index('ix_project_invitations_project', 'project_invitations', ['project_id'], unique=False)
    op.create_index('ix_project_invitations_code', 'project_invitations', ['code'], unique=False)
    op.create_index('ix_project_invitations_created_by', 'project_invitations', ['created_by_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_project_invitations_created_by', table_name='project_invitations')
    op.drop_index('ix_project_invitations_code', table_name='project_invitations')
    op.drop_index('ix_project_invitations_project', table_name='project_invitations')
    op.drop_table('project_invitations')
