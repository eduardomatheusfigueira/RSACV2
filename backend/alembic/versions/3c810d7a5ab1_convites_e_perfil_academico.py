"""convites_e_perfil_academico

Adiciona a tabela `invites` para controle de convites de uso único e
estende a tabela `users` com os dados do perfil acadêmico e cadastral do pesquisador.

Revision ID: 3c810d7a5ab1
Revises: 1b724bcfc68e
Create Date: 2026-08-29 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c810d7a5ab1'
down_revision: Union[str, Sequence[str], None] = '1b724bcfc68e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criação da tabela invites
    op.create_table(
        'invites',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_by_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('note', sa.String(length=255), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('used_by_user_id')
    )
    op.create_index('ix_invites_code', 'invites', ['code'])
    op.create_index('ix_invites_is_used', 'invites', ['is_used'])

    # 2. Adição dos campos acadêmicos e cadastrais na tabela users
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('full_name', sa.String(length=200), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('phone', sa.String(length=30), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('institution', sa.String(length=200), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('academic_degree', sa.String(length=50), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('is_studying', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        batch_op.add_column(sa.Column('study_program', sa.String(length=200), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('profession', sa.String(length=100), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('research_area', sa.String(length=200), nullable=False, server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('research_area')
        batch_op.drop_column('profession')
        batch_op.drop_column('study_program')
        batch_op.drop_column('is_studying')
        batch_op.drop_column('academic_degree')
        batch_op.drop_column('institution')
        batch_op.drop_column('phone')
        batch_op.drop_column('full_name')

    op.drop_index('ix_invites_is_used', table_name='invites')
    op.drop_index('ix_invites_code', table_name='invites')
    op.drop_table('invites')
