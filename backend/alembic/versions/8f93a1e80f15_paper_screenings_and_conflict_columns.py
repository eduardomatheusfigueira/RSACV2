"""paper_screenings_and_conflict_columns

Adiciona tabela `paper_screenings` e colunas de status de triagem e resolução de
conflito em `papers` com preservação do legado (doc 43 §43.3.4, §43.3.5, Fase 4).

Revision ID: 8f93a1e80f15
Revises: 7e93a1e80f14
Create Date: 2026-08-30 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f93a1e80f15'
down_revision: Union[str, Sequence[str], None] = '7e93a1e80f14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criação da tabela de julgamentos individuais (paper_screenings)
    op.create_table(
        'paper_screenings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('paper_id', sa.String(length=36), nullable=False),
        sa.Column('reviewer_id', sa.String(length=36), nullable=False),
        sa.Column('decision', sa.String(length=20), server_default='Pendente', nullable=False),
        sa.Column('observations', sa.Text(), server_default='', nullable=False),
        sa.Column('criteria_evaluations', sa.Text(), server_default='{}', nullable=False),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('ai_assisted', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['paper_id'], ['papers.id'],
            name='fk_paper_screenings_paper_id_papers',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['reviewer_id'], ['users.id'],
            name='fk_paper_screenings_reviewer_id_users',
            ondelete='CASCADE'
        ),
        sa.UniqueConstraint('paper_id', 'reviewer_id', name='uq_paper_screenings_paper_reviewer'),
    )
    op.create_index('ix_paper_screenings_paper', 'paper_screenings', ['paper_id'])
    op.create_index('ix_paper_screenings_reviewer', 'paper_screenings', ['reviewer_id'])

    # 2. Adição das colunas de estado de consolidação e resolução de conflito em papers
    with op.batch_alter_table('papers') as batch_op:
        batch_op.add_column(
            sa.Column('screening_status', sa.String(length=20), server_default='aguardando', nullable=False)
        )
        batch_op.add_column(
            sa.Column('conflict_resolved_by_user_id', sa.String(length=36), nullable=True)
        )
        batch_op.add_column(
            sa.Column('conflict_resolved_at', sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_papers_conflict_resolved_by_users',
            'users',
            ['conflict_resolved_by_user_id'],
            ['id'],
            ondelete='SET NULL'
        )

    # 3. Migração de dados de legado (P5: estudos já decididos ganham status 'legado' sem autor fictício)
    op.execute("UPDATE papers SET screening_status = 'legado' WHERE decision != 'Pendente'")
    op.execute("UPDATE papers SET screening_status = 'aguardando' WHERE decision = 'Pendente'")


def downgrade() -> None:
    with op.batch_alter_table('papers') as batch_op:
        batch_op.drop_constraint('fk_papers_conflict_resolved_by_users', type_='foreignkey')
        batch_op.drop_column('conflict_resolved_at')
        batch_op.drop_column('conflict_resolved_by_user_id')
        batch_op.drop_column('screening_status')

    op.drop_index('ix_paper_screenings_reviewer', table_name='paper_screenings')
    op.drop_index('ix_paper_screenings_paper', table_name='paper_screenings')
    op.drop_table('paper_screenings')
