"""bibliometria_instantaneo_do_corpus

Cria `bib_snapshots` — o corpus congelado sobre o qual um indicador é
calculado (doc 48 §3, doc 49 Fase 1).

Sem isto, um número obtido na terça não é reproduzível na quinta, porque o
acervo muda todo dia por coleta, deduplicação e triagem — e nada registrava
sobre que corpus o número havia sido obtido (doc 47 §B-05).

Revision ID: ab94a1e80f17
Revises: 9a93a1e80f16
Create Date: 2026-08-31 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab94a1e80f17'
down_revision: Union[str, Sequence[str], None] = '9a93a1e80f16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bib_snapshots',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('label', sa.Text(), server_default='', nullable=False),
        # Filtros que definiram o corpus, em JSON — é o que permite recriar o
        # escopo e conferir o instantâneo contra o acervo de hoje.
        sa.Column('scope', sa.Text(), server_default='{}', nullable=False),
        sa.Column('n_documents', sa.Integer(), server_default='0', nullable=False),
        # sha256 do manifesto ordenado: a identidade do corpus.
        sa.Column('corpus_hash', sa.String(length=64), nullable=False),
        # Manifesto comprimido (paper_id + hash de conteúdo, por linha). Guarda
        # os pares, e não só o agregado, porque a pergunta útil não é "mudou?"
        # e sim "o que mudou?".
        sa.Column('manifest', sa.LargeBinary(), nullable=False),
        sa.Column('engine_version', sa.String(length=20), server_default='', nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index(
        'ix_bib_snapshots_project', 'bib_snapshots', ['project_id', 'created_at']
    )


def downgrade() -> None:
    op.drop_index('ix_bib_snapshots_project', table_name='bib_snapshots')
    op.drop_table('bib_snapshots')
