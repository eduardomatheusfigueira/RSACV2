"""bibliometria_camada_texto_tesauro

Cria as tabelas da camada de texto e tesauros controlados (doc 48 §5, §12, doc 49 Fase 4):
- `bib_textos`: texto limpo por documento, seções IMRaD, contagem de páginas/palavras, sha256 do PDF e versão do pipeline (fecha B-04)
- `bib_thesauri`: tesauros e vocabulários controlados por projeto (fecha B-06)
- `bib_thesaurus_entries`: entradas com termos preferidos e variantes aprovadas

Revision ID: cd96a1e80f19
Revises: bc95a1e80f18
Create Date: 2026-09-01 08:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd96a1e80f19'
down_revision: Union[str, Sequence[str], None] = 'bc95a1e80f18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. bib_textos
    op.create_table(
        'bib_textos',
        sa.Column('paper_id', sa.String(length=36), primary_key=True),
        sa.Column('pipeline_version', sa.String(length=32), server_default='2.0.0', nullable=False),
        sa.Column('pdf_sha256', sa.String(length=64), nullable=True),
        sa.Column('n_pages', sa.Integer(), server_default='0', nullable=False),
        sa.Column('n_words', sa.Integer(), server_default='0', nullable=False),
        sa.Column('text_clean', sa.Text(), nullable=False),
        sa.Column('sections', sa.Text(), server_default='[]', nullable=False),
        sa.Column(
            'extracted_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_bib_textos_pipeline_version', 'bib_textos', ['pipeline_version'])

    # 2. bib_thesauri
    op.create_table(
        'bib_thesauri',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
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
    op.create_index('ix_bib_thesauri_project_id', 'bib_thesauri', ['project_id'])

    # 3. bib_thesaurus_entries
    op.create_table(
        'bib_thesaurus_entries',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('thesaurus_id', sa.String(length=36), nullable=False),
        sa.Column('preferred_term', sa.String(length=255), nullable=False),
        sa.Column('variants', sa.Text(), server_default='[]', nullable=False),
        sa.Column('scope', sa.String(length=255), server_default='', nullable=False),
        sa.Column('proposed_by', sa.String(length=128), server_default='manual', nullable=False),
        sa.Column('approved_by', sa.String(length=36), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['thesaurus_id'], ['bib_thesauri.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_bib_thesaurus_entries_thesaurus_id', 'bib_thesaurus_entries', ['thesaurus_id'])
    op.create_index('ix_bib_thesaurus_entries_preferred_term', 'bib_thesaurus_entries', ['preferred_term'])


def downgrade() -> None:
    op.drop_index('ix_bib_thesaurus_entries_preferred_term', table_name='bib_thesaurus_entries')
    op.drop_index('ix_bib_thesaurus_entries_thesaurus_id', table_name='bib_thesaurus_entries')
    op.drop_table('bib_thesaurus_entries')

    op.drop_index('ix_bib_thesauri_project_id', table_name='bib_thesauri')
    op.drop_table('bib_thesauri')

    op.drop_index('ix_bib_textos_pipeline_version', table_name='bib_textos')
    op.drop_table('bib_textos')
