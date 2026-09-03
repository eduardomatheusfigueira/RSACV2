"""bibliometria_analises

Cria a tabela de análises estatísticas sob demanda (doc 48 §9, §12, doc 49 Fase 7):
- `bib_analises`: pergunta original em linguagem natural, especificação JSON com vocabulário fechado, autor e data

Revision ID: fa99a1e80f22
Revises: ef98a1e80f21
Create Date: 2026-09-01 09:16:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa99a1e80f22'
down_revision: Union[str, Sequence[str], None] = 'ef98a1e80f21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bib_analises',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('specification', sa.Text(), nullable=False),  # JSON validado contra esquema fechado
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_bib_analises_project_id', 'bib_analises', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_bib_analises_project_id', table_name='bib_analises')
    op.drop_table('bib_analises')
