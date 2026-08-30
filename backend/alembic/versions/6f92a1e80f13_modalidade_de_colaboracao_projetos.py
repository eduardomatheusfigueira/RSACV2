"""modalidade_de_colaboracao_projetos

Acrescenta colunas de modalidade de colaboração em `projects` (doc 43 §43.3.3, Fase 2).

Revision ID: 6f92a1e80f13
Revises: 5e81d7f39a04
Create Date: 2026-08-30 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f92a1e80f13'
down_revision: Union[str, Sequence[str], None] = '5e81d7f39a04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar colunas com server_default para retrocompatibilidade total
    op.add_column(
        'projects',
        sa.Column(
            'collaboration_mode',
            sa.String(length=30),
            nullable=False,
            server_default='individual',
        ),
    )
    op.add_column(
        'projects',
        sa.Column(
            'reviewers_per_paper',
            sa.Integer(),
            nullable=False,
            server_default='1',
        ),
    )
    op.add_column(
        'projects',
        sa.Column(
            'conflict_resolution',
            sa.String(length=30),
            nullable=False,
            server_default='coordenador',
        ),
    )


def downgrade() -> None:
    # Usar batch_alter_table para compatibilidade com SQLite
    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_column('conflict_resolution')
        batch_op.drop_column('reviewers_per_paper')
        batch_op.drop_column('collaboration_mode')
