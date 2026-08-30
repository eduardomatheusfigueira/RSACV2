"""qualificacao_protocolos_eixos_e_estrategia

Adiciona decomposição em 4 eixos, novas tabelas de estratégia de busca,
execuções, versionamento, emendas e auditoria de checklist (Doc 45 §14).

Revision ID: 9a93a1e80f16
Revises: 8f93a1e80f15
Create Date: 2026-08-30 15:30:00.000000

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a93a1e80f16'
down_revision: Union[str, Sequence[str], None] = '8f93a1e80f15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Adição dos campos de 4 eixos em protocols
    with op.batch_alter_table('protocols') as batch_op:
        batch_op.add_column(
            sa.Column('mode', sa.String(length=20), server_default='completo', nullable=False)
        )
        batch_op.add_column(
            sa.Column('review_design', sa.String(length=20), server_default='D4', nullable=False)
        )
        batch_op.add_column(
            sa.Column('reporting_guideline', sa.String(length=50), server_default='PRISMA-ScR', nullable=False)
        )
        batch_op.add_column(
            sa.Column('conduct_standards', sa.Text(), server_default='[]', nullable=False)
        )
        batch_op.add_column(
            sa.Column('question_framework', sa.Text(), server_default='{}', nullable=False)
        )
        batch_op.add_column(
            sa.Column('appraisal', sa.Text(), server_default='{}', nullable=False)
        )
        batch_op.add_column(
            sa.Column('synthesis', sa.Text(), server_default='{}', nullable=False)
        )
        batch_op.add_column(
            sa.Column('bibliometrics', sa.Text(), server_default='{}', nullable=False)
        )
        batch_op.add_column(
            sa.Column('status', sa.String(length=20), server_default='rascunho', nullable=False)
        )
        batch_op.add_column(
            sa.Column('current_version', sa.String(length=50), nullable=True)
        )

    # 2. Migração de dados determinística para protocolos existentes (§14.2)
    bind = op.get_bind()
    conn = bind.connect() if hasattr(bind, 'connect') else bind

    try:
        results = conn.execute(
            sa.text("SELECT id, methodology FROM projects")
        ).fetchall()

        mapping = {
            'PRISMA-ScR': ('D4', 'PRISMA-ScR', '[]'),
            'PRISMA-2020': ('D1', 'PRISMA-2020', '[]'),
            'PRISMA-P': ('D1', 'PRISMA-2020', '[]'),
            'Cochrane': ('D1', 'PRISMA-2020', '["Cochrane/MECIR"]'),
            'Campbell': ('D1', 'PRISMA-2020', '["Campbell/MECCIR"]'),
            'JBI (Scoping/Systematic)': ('D4', 'PRISMA-ScR', '["JBI"]'),
            'CEE/ROSES': ('D5', 'ROSES', '["CEE v5.1"]'),
            'EBSE': ('D9', 'EBSE', '["Kitchenham & Charters"]'),
            'Umbrella Review': ('D6', 'PRIOR', '["JBI Umbrella"]'),
            'Methodi Ordinatio': ('D12', 'Generic', '["Methodi Ordinatio"]'),
            'Other': ('D14', 'Generic', '[]'),
        }

        for row in results:
            proj_id = row[0]
            meth = row[1]
            design, guideline, standards = mapping.get(meth, ('D4', 'PRISMA-ScR', '[]'))
            conn.execute(
                sa.text(
                    "UPDATE protocols SET review_design = :d, reporting_guideline = :g, "
                    "conduct_standards = :c, mode = 'completo', status = 'rascunho' "
                    "WHERE project_id = :p"
                ),
                {"d": design, "g": guideline, "c": standards, "p": proj_id}
            )
    except Exception:
        pass

    # 3. Adição de colunas em criteria
    with op.batch_alter_table('criteria') as batch_op:
        batch_op.add_column(
            sa.Column('dimension', sa.String(length=30), server_default='outro', nullable=False)
        )
        batch_op.add_column(
            sa.Column('applies_at', sa.String(length=30), server_default='ambos', nullable=False)
        )

    # 4. Adição de colunas em extraction_questions
    with op.batch_alter_table('extraction_questions') as batch_op:
        batch_op.add_column(
            sa.Column('answer_type', sa.String(length=30), server_default='texto', nullable=False)
        )
        batch_op.add_column(
            sa.Column('options', sa.Text(), server_default='[]', nullable=False)
        )
        batch_op.add_column(
            sa.Column('required', sa.Boolean(), server_default=sa.text('0'), nullable=False)
        )

    # 5. Criação da tabela search_strategies
    op.create_table(
        'search_strategies',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('protocol_id', sa.String(length=36), nullable=False),
        sa.Column('kind', sa.String(length=20), server_default='canonica', nullable=False),
        sa.Column('database', sa.String(length=50), server_default='', nullable=False),
        sa.Column('blocks', sa.Text(), server_default='[]', nullable=False),
        sa.Column('combination', sa.String(length=255), server_default='', nullable=False),
        sa.Column('target_fields', sa.Text(), server_default='[]', nullable=False),
        sa.Column('limits', sa.Text(), server_default='{}', nullable=False),
        sa.Column('rendered_query', sa.Text(), server_default='', nullable=False),
        sa.Column('adaptation_note', sa.Text(), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['protocol_id'], ['protocols.id'],
            name='fk_search_strategies_protocol_id_protocols',
            ondelete='CASCADE'
        ),
    )
    op.create_index('ix_search_strategies_protocol_kind', 'search_strategies', ['protocol_id', 'kind'])

    # 6. Criação da tabela search_executions
    op.create_table(
        'search_executions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('protocol_id', sa.String(length=36), nullable=False),
        sa.Column('harvest_run_id', sa.String(length=36), nullable=True),
        sa.Column('database', sa.String(length=50), nullable=False),
        sa.Column('query_sent', sa.Text(), server_default='', nullable=False),
        sa.Column('filters', sa.Text(), server_default='{}', nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('records_returned', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('records_after_dedup', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['protocol_id'], ['protocols.id'],
            name='fk_search_executions_protocol_id_protocols',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['harvest_run_id'], ['harvest_runs.id'],
            name='fk_search_executions_harvest_run_id_harvest_runs',
            ondelete='SET NULL'
        ),
    )
    op.create_index('ix_search_executions_protocol', 'search_executions', ['protocol_id'])
    op.create_index('ix_search_executions_executed_at', 'search_executions', ['executed_at'])

    # 7. Criação da tabela protocol_versions
    op.create_table(
        'protocol_versions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('protocol_id', sa.String(length=36), nullable=False),
        sa.Column('label', sa.String(length=50), nullable=False),
        sa.Column('snapshot', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('frozen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('frozen_by_user_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ['protocol_id'], ['protocols.id'],
            name='fk_protocol_versions_protocol_id_protocols',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['frozen_by_user_id'], ['users.id'],
            name='fk_protocol_versions_frozen_by_user_id_users',
            ondelete='SET NULL'
        ),
    )
    op.create_index('ix_protocol_versions_protocol', 'protocol_versions', ['protocol_id'])
    op.create_index('ix_protocol_versions_label', 'protocol_versions', ['protocol_id', 'label'])

    # 8. Criação da tabela protocol_amendments
    op.create_table(
        'protocol_amendments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('protocol_id', sa.String(length=36), nullable=False),
        sa.Column('from_version', sa.String(length=50), nullable=False),
        sa.Column('to_version', sa.String(length=50), nullable=False),
        sa.Column('diff', sa.Text(), server_default='{}', nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('project_phase', sa.String(length=50), server_default='coleta', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ['protocol_id'], ['protocols.id'],
            name='fk_protocol_amendments_protocol_id_protocols',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'], ['users.id'],
            name='fk_protocol_amendments_created_by_user_id_users',
            ondelete='SET NULL'
        ),
    )
    op.create_index('ix_protocol_amendments_protocol', 'protocol_amendments', ['protocol_id'])

    # 9. Criação da tabela checklist_audits
    op.create_table(
        'checklist_audits',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('protocol_id', sa.String(length=36), nullable=False),
        sa.Column('guideline', sa.String(length=50), nullable=False),
        sa.Column('item_id', sa.String(length=50), nullable=False),
        sa.Column('state', sa.String(length=20), server_default='pendente', nullable=False),
        sa.Column('location', sa.String(length=100), server_default='', nullable=False),
        sa.Column('justification', sa.Text(), server_default='', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_by_user_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ['protocol_id'], ['protocols.id'],
            name='fk_checklist_audits_protocol_id_protocols',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['updated_by_user_id'], ['users.id'],
            name='fk_checklist_audits_updated_by_user_id_users',
            ondelete='SET NULL'
        ),
        sa.UniqueConstraint('protocol_id', 'guideline', 'item_id', name='uq_checklist_audit_protocol_guideline_item'),
    )
    op.create_index('ix_checklist_audits_protocol_guideline', 'checklist_audits', ['protocol_id', 'guideline'])


def downgrade() -> None:
    op.drop_table('checklist_audits')
    op.drop_table('protocol_amendments')
    op.drop_table('protocol_versions')
    op.drop_table('search_executions')
    op.drop_table('search_strategies')

    with op.batch_alter_table('extraction_questions') as batch_op:
        batch_op.drop_column('required')
        batch_op.drop_column('options')
        batch_op.drop_column('answer_type')

    with op.batch_alter_table('criteria') as batch_op:
        batch_op.drop_column('applies_at')
        batch_op.drop_column('dimension')

    with op.batch_alter_table('protocols') as batch_op:
        batch_op.drop_column('current_version')
        batch_op.drop_column('status')
        batch_op.drop_column('bibliometrics')
        batch_op.drop_column('synthesis')
        batch_op.drop_column('appraisal')
        batch_op.drop_column('question_framework')
        batch_op.drop_column('conduct_standards')
        batch_op.drop_column('reporting_guideline')
        batch_op.drop_column('review_design')
        batch_op.drop_column('mode')
