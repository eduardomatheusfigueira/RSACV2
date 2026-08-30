"""harvest_runs_run_by_user

Acrescenta autoria da coleta em `harvest_runs` (doc 43 §43.3.7, Fase 3).

Revision ID: 7e93a1e80f14
Revises: 6f92a1e80f13
Create Date: 2026-08-30 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e93a1e80f14'
down_revision: Union[str, Sequence[str], None] = '6f92a1e80f13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('harvest_runs') as batch_op:
        batch_op.add_column(
            sa.Column(
                'run_by_user_id',
                sa.String(length=36),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            'fk_harvest_runs_run_by_user_id_users',
            'users',
            ['run_by_user_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('harvest_runs') as batch_op:
        batch_op.drop_constraint('fk_harvest_runs_run_by_user_id_users', type_='foreignkey')
        batch_op.drop_column('run_by_user_id')
