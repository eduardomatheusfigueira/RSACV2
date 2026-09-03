"""bibliometria_grafos

Cria a tabela de grafos bibliométricos determinísticos (doc 48 §8, §12, doc 49 Fase 6):
- `bib_grafos`: redes de coautoria, termos, acoplamento bibliográfico e cocitação com layout FR e clusters Louvain

Revision ID: ef98a1e80f21
Revises: de97a1e80f20
Create Date: 2026-09-01 08:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef98a1e80f21'
down_revision: Union[str, Sequence[str], None] = 'de97a1e80f20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bib_grafos',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('snapshot_id', sa.String(length=36), nullable=True),
        sa.Column('network_type', sa.String(length=50), nullable=False),  # coautoria / coocorrencia_termos / acoplamento_bibliografico / cocitacao
        sa.Column('parameters', sa.Text(), server_default='{}', nullable=False),  # normalizacao, resolucao, corte, semente, iteracoes
        sa.Column('nodes', sa.Text(), server_default='[]', nullable=False),  # JSON com lista de nós
        sa.Column('edges', sa.Text(), server_default='[]', nullable=False),  # JSON com lista de arestas
        sa.Column('coordinates', sa.Text(), server_default='{}', nullable=False),  # JSON com coordenadas { node_id: {x, y} }
        sa.Column('clusters', sa.Text(), server_default='{}', nullable=False),  # JSON com metadados de clusters
        sa.Column('seed', sa.Integer(), server_default='42', nullable=False),
        sa.Column(
            'calculated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['snapshot_id'], ['bib_snapshots.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_bib_grafos_project_id', 'bib_grafos', ['project_id'])
    op.create_index('ix_bib_grafos_snapshot_id', 'bib_grafos', ['snapshot_id'])
    op.create_index('ix_bib_grafos_network_type', 'bib_grafos', ['network_type'])


def downgrade() -> None:
    op.drop_index('ix_bib_grafos_network_type', table_name='bib_grafos')
    op.drop_index('ix_bib_grafos_snapshot_id', table_name='bib_grafos')
    op.drop_index('ix_bib_grafos_project_id', table_name='bib_grafos')
    op.drop_table('bib_grafos')
