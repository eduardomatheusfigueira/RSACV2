"""bibliometria_enriquecimento_openalex

Cria as tabelas de enriquecimento externo do corpus (doc 48 §4, doc 49 Fase 2):
- `bib_enrichments`: sessões de enriquecimento por projeto
- `bib_work_meta`: metadados estendidos e raw JSON da obra (OpenAlex/Crossref)
- `bib_references`: referências citadas e grafos de citação
- `bib_authorships`: afiliação institucional resolvida por ROR e autoria (fecha B-01)
- `bib_topics`: tópicos e domínios com score de relevância
- `bib_keywords`: palavras-chave com procedência declarada (fecha B-02)

Revision ID: bc95a1e80f18
Revises: ab94a1e80f17
Create Date: 2026-09-01 00:38:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc95a1e80f18'
down_revision: Union[str, Sequence[str], None] = 'ab94a1e80f17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. bib_enrichments
    op.create_table(
        'bib_enrichments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.String(length=50), server_default='openalex', nullable=False),
        sa.Column(
            'started_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('n_consulted', sa.Integer(), server_default='0', nullable=False),
        sa.Column('n_found', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='em_andamento', nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index(
        'ix_bib_enrichments_project', 'bib_enrichments', ['project_id', 'started_at']
    )

    # 2. bib_work_meta
    op.create_table(
        'bib_work_meta',
        sa.Column('paper_id', sa.String(length=36), primary_key=True),
        sa.Column('enrichment_id', sa.String(length=36), nullable=True),
        sa.Column('provider', sa.String(length=50), server_default='openalex', nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('cited_by_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('referenced_works_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('doc_type', sa.String(length=50), nullable=True),
        sa.Column('is_oa', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('oa_status', sa.String(length=30), nullable=True),
        sa.Column('raw', sa.Text(), server_default='{}', nullable=False),
        sa.Column(
            'obtained_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['enrichment_id'], ['bib_enrichments.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_bib_work_meta_external_id', 'bib_work_meta', ['external_id'])

    # 3. bib_references
    op.create_table(
        'bib_references',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('citing_paper_id', sa.String(length=36), nullable=False),
        sa.Column('cited_external_id', sa.String(length=255), nullable=True),
        sa.Column('cited_doi', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['citing_paper_id'], ['papers.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_bib_references_citing', 'bib_references', ['citing_paper_id'])
    op.create_index('ix_bib_references_cited_external', 'bib_references', ['cited_external_id'])
    op.create_index('ix_bib_references_cited_doi', 'bib_references', ['cited_doi'])

    # 4. bib_authorships
    op.create_table(
        'bib_authorships',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('paper_id', sa.String(length=36), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('author_external_id', sa.String(length=255), nullable=True),
        sa.Column('author_name', sa.Text(), server_default='', nullable=False),
        sa.Column('institution_ror', sa.String(length=100), nullable=True),
        sa.Column('institution_name', sa.Text(), server_default='', nullable=False),
        sa.Column('country', sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_bib_authorships_paper', 'bib_authorships', ['paper_id'])
    op.create_index('ix_bib_authorships_ror', 'bib_authorships', ['institution_ror'])
    op.create_index('ix_bib_authorships_author', 'bib_authorships', ['author_external_id'])

    # 5. bib_topics
    op.create_table(
        'bib_topics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('paper_id', sa.String(length=36), nullable=False),
        sa.Column('topic_id', sa.String(length=255), nullable=True),
        sa.Column('topic_name', sa.Text(), server_default='', nullable=False),
        sa.Column('level', sa.Integer(), server_default='0', nullable=False),
        sa.Column('score', sa.Float(), server_default='0.0', nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_bib_topics_paper', 'bib_topics', ['paper_id'])
    op.create_index('ix_bib_topics_topic', 'bib_topics', ['topic_id'])

    # 6. bib_keywords
    op.create_table(
        'bib_keywords',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('paper_id', sa.String(length=36), nullable=False),
        sa.Column('term', sa.Text(), server_default='', nullable=False),
        sa.Column('source', sa.String(length=50), server_default='openalex', nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_bib_keywords_paper', 'bib_keywords', ['paper_id'])
    op.create_index('ix_bib_keywords_term', 'bib_keywords', ['term'])


def downgrade() -> None:
    op.drop_table('bib_keywords')
    op.drop_table('bib_topics')
    op.drop_table('bib_authorships')
    op.drop_table('bib_references')
    op.drop_table('bib_work_meta')
    op.drop_table('bib_enrichments')
