"""solicitacoes_de_convite

Cria `invite_requests`, a fila de pedidos de acesso enviados pela tela de login
por quem ainda não tem convite.

Revision ID: ba00a1e80f23
Revises: fa99a1e80f22
Create Date: 2026-09-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba00a1e80f23'
down_revision: Union[str, Sequence[str], None] = 'fa99a1e80f22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Bancos locais que já rodaram com o `create_all` temporário podem ter a
    # tabela sem o carimbo desta revisão. Criar de novo abortaria a migração e
    # deixaria o banco preso atrás desta linha, então aqui só se cria o que
    # falta.
    inspetor = sa.inspect(op.get_bind())
    if 'invite_requests' in inspetor.get_table_names():
        return

    op.create_table(
        'invite_requests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('telefone', sa.String(length=50), nullable=False),
        sa.Column('onde_conheceu', sa.String(length=255), nullable=False),
        sa.Column('instituicao', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pendente'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invite_code_generated', sa.String(length=32), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_invite_requests_status', 'invite_requests', ['status'], unique=False)
    op.create_index('ix_invite_requests_created_at', 'invite_requests', ['created_at'], unique=False)
    op.create_index('ix_invite_requests_email', 'invite_requests', ['email'], unique=False)


def downgrade() -> None:
    inspetor = sa.inspect(op.get_bind())
    if 'invite_requests' not in inspetor.get_table_names():
        return

    op.drop_index('ix_invite_requests_email', table_name='invite_requests')
    op.drop_index('ix_invite_requests_created_at', table_name='invite_requests')
    op.drop_index('ix_invite_requests_status', table_name='invite_requests')
    op.drop_table('invite_requests')
