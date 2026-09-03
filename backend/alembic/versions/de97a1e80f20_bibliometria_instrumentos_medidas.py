"""bibliometria_instrumentos_medidas

Cria as tabelas de instrumentos conceituais, medições determinísticas e evidências textuais (doc 48 §6, §12, doc 49 Fase 5):
- `bib_instrumentos`: conceito, definição, léxico JSON com termos a incluir/excluir, modo de matching e porta de aprovação humana (fecha B-07)
- `bib_medidas`: execuções oficiais de contagem determinística sobre instantâneo/corpus com denominador
- `bib_ocorrencias`: acertos detalhados com ancoragem em seção, página, offset e forma exata encontrada

Revision ID: de97a1e80f20
Revises: cd96a1e80f19
Create Date: 2026-09-01 08:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de97a1e80f20'
down_revision: Union[str, Sequence[str], None] = 'cd96a1e80f19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. bib_instrumentos
    op.create_table(
        'bib_instrumentos',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('concept', sa.String(length=255), nullable=False),
        sa.Column('definition', sa.Text(), server_default='', nullable=False),
        sa.Column('lexicon', sa.Text(), server_default='{}', nullable=False),  # JSON com modo, incluir, excluir, janela
        sa.Column('version', sa.String(length=32), server_default='1.0', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='rascunho', nullable=False),  # rascunho / aprovado / arquivado
        sa.Column('proposed_by', sa.String(length=128), server_default='manual', nullable=False),
        sa.Column('model_used', sa.String(length=128), nullable=True),
        sa.Column('prompt_hash', sa.String(length=64), nullable=True),
        sa.Column('approved_by', sa.String(length=36), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_precision', sa.Float(), nullable=True),
        sa.Column('precision_ci', sa.Text(), nullable=True),  # JSON [lower, upper]
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_bib_instrumentos_project_id', 'bib_instrumentos', ['project_id'])
    op.create_index('ix_bib_instrumentos_concept', 'bib_instrumentos', ['concept'])
    op.create_index('ix_bib_instrumentos_status', 'bib_instrumentos', ['status'])

    # 2. bib_medidas
    op.create_table(
        'bib_medidas',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('snapshot_id', sa.String(length=36), nullable=True),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('instrument_version', sa.String(length=32), nullable=False),
        sa.Column('result', sa.Text(), server_default='{}', nullable=False),  # JSON com métricas consolidadas
        sa.Column('n_documents', sa.Integer(), server_default='0', nullable=False),
        sa.Column('n_documents_with_text', sa.Integer(), server_default='0', nullable=False),
        sa.Column(
            'executed_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['snapshot_id'], ['bib_snapshots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['instrument_id'], ['bib_instrumentos.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_bib_medidas_instrument_id', 'bib_medidas', ['instrument_id'])
    op.create_index('ix_bib_medidas_snapshot_id', 'bib_medidas', ['snapshot_id'])

    # 3. bib_ocorrencias
    op.create_table(
        'bib_ocorrencias',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('measurement_id', sa.String(length=36), nullable=False),
        sa.Column('paper_id', sa.String(length=36), nullable=False),
        sa.Column('section', sa.String(length=100), server_default='', nullable=False),
        sa.Column('page', sa.Integer(), server_default='1', nullable=False),
        sa.Column('char_start', sa.Integer(), server_default='0', nullable=False),
        sa.Column('char_end', sa.Integer(), server_default='0', nullable=False),
        sa.Column('matched_form', sa.Text(), nullable=False),
        sa.Column('context_snippet', sa.Text(), server_default='', nullable=False),
        sa.ForeignKeyConstraint(['measurement_id'], ['bib_medidas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_bib_ocorrencias_measurement_id', 'bib_ocorrencias', ['measurement_id'])
    op.create_index('ix_bib_ocorrencias_paper_id', 'bib_ocorrencias', ['paper_id'])


def downgrade() -> None:
    op.drop_index('ix_bib_ocorrencias_paper_id', table_name='bib_ocorrencias')
    op.drop_index('ix_bib_ocorrencias_measurement_id', table_name='bib_ocorrencias')
    op.drop_table('bib_ocorrencias')

    op.drop_index('ix_bib_medidas_snapshot_id', table_name='bib_medidas')
    op.drop_index('ix_bib_medidas_instrument_id', table_name='bib_medidas')
    op.drop_table('bib_medidas')

    op.drop_index('ix_bib_instrumentos_status', table_name='bib_instrumentos')
    op.drop_index('ix_bib_instrumentos_concept', table_name='bib_instrumentos')
    op.drop_index('ix_bib_instrumentos_project_id', table_name='bib_instrumentos')
    op.drop_table('bib_instrumentos')
