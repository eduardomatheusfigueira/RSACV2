"""feedback do beta

Cria `feedbacks`, a fila de retornos — problemas, sugestões, elogios — que
quem usa o aplicativo envia pelo botão de feedback do beta.

Revision ID: cb01a1e80f24
Revises: ba00a1e80f23
Create Date: 2026-09-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb01a1e80f24'
down_revision: Union[str, Sequence[str], None] = 'ba00a1e80f23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Mesmo cuidado da migração dos pedidos de convite: um banco local que já
    # criou a tabela por `create_all` não pode ficar preso atrás desta linha.
    inspetor = sa.inspect(op.get_bind())
    if 'feedbacks' in inspetor.get_table_names():
        return

    op.create_table(
        'feedbacks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('pagina', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('navegador', sa.String(length=300), nullable=False, server_default=''),
        sa.Column('versao', sa.String(length=20), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='novo'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_feedbacks_status', 'feedbacks', ['status'], unique=False)
    op.create_index('ix_feedbacks_created_at', 'feedbacks', ['created_at'], unique=False)
    op.create_index('ix_feedbacks_user_id', 'feedbacks', ['user_id'], unique=False)


def downgrade() -> None:
    inspetor = sa.inspect(op.get_bind())
    if 'feedbacks' not in inspetor.get_table_names():
        return

    op.drop_index('ix_feedbacks_user_id', table_name='feedbacks')
    op.drop_index('ix_feedbacks_created_at', table_name='feedbacks')
    op.drop_index('ix_feedbacks_status', table_name='feedbacks')
    op.drop_table('feedbacks')
