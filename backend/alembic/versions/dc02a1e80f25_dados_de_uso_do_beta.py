"""dados de uso do beta

Cria as tabelas do doc 52: eventos de uso, ocorrências de erro, chamadas de
IA com contagem de tokens, o estado da coleta, o acompanhamento de defeitos e
o diário de ações da aba Sistema. Acrescenta a `users` o interruptor com que
cada pessoa desliga a coleta de uso da plataforma.

Revision ID: dc02a1e80f25
Revises: cb01a1e80f24
Create Date: 2026-09-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc02a1e80f25'
down_revision: Union[str, Sequence[str], None] = 'cb01a1e80f24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tz() -> sa.DateTime:
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    inspetor = sa.inspect(op.get_bind())
    tabelas = set(inspetor.get_table_names())

    colunas_users = {c['name'] for c in inspetor.get_columns('users')}
    if 'uso_coleta_ativa' not in colunas_users:
        with op.batch_alter_table('users') as batch_op:
            batch_op.add_column(
                sa.Column('uso_coleta_ativa', sa.Boolean(), nullable=False, server_default=sa.true())
            )
            batch_op.add_column(sa.Column('uso_coleta_alterada_em', _tz(), nullable=True))

    if 'uso_eventos' not in tabelas:
        op.create_table(
            'uso_eventos',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('sessao_uso_id', sa.String(length=36), nullable=False),
            sa.Column('nome', sa.String(length=64), nullable=False),
            sa.Column('tela', sa.String(length=40), nullable=True),
            sa.Column('propriedades', sa.Text(), nullable=False),
            sa.Column('ocorrido_em', _tz(), nullable=False),
            sa.Column('recebido_em', _tz(), nullable=False),
            sa.Column('versao_app', sa.String(length=20), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_uso_eventos_user_ocorrido', 'uso_eventos', ['user_id', 'ocorrido_em'])
        op.create_index('ix_uso_eventos_nome_ocorrido', 'uso_eventos', ['nome', 'ocorrido_em'])
        op.create_index('ix_uso_eventos_recebido', 'uso_eventos', ['recebido_em'])

    if 'uso_erros' not in tabelas:
        op.create_table(
            'uso_erros',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=True),
            sa.Column('origem', sa.String(length=10), nullable=False),
            sa.Column('impressao', sa.String(length=64), nullable=False),
            sa.Column('tipo', sa.String(length=80), nullable=False),
            sa.Column('mensagem', sa.String(length=300), nullable=False),
            sa.Column('pilha', sa.Text(), nullable=False),
            sa.Column('tela', sa.String(length=40), nullable=True),
            sa.Column('rota', sa.String(length=200), nullable=True),
            sa.Column('status_http', sa.Integer(), nullable=True),
            sa.Column('correlacao', sa.String(length=36), nullable=True),
            sa.Column('versao_app', sa.String(length=20), nullable=False),
            sa.Column('navegador', sa.String(length=40), nullable=False),
            sa.Column('ocorrido_em', _tz(), nullable=False),
            sa.Column('recebido_em', _tz(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_uso_erros_impressao_ocorrido', 'uso_erros', ['impressao', 'ocorrido_em'])
        op.create_index('ix_uso_erros_user', 'uso_erros', ['user_id'])
        op.create_index('ix_uso_erros_recebido', 'uso_erros', ['recebido_em'])

    if 'uso_ia_chamadas' not in tabelas:
        op.create_table(
            'uso_ia_chamadas',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('project_id', sa.String(length=36), nullable=True),
            sa.Column('operacao', sa.String(length=32), nullable=False),
            sa.Column('provedor', sa.String(length=40), nullable=False),
            sa.Column('modelo_pedido', sa.String(length=100), nullable=False),
            sa.Column('modelo_respondeu', sa.String(length=100), nullable=False),
            sa.Column('chave_ordinal', sa.Integer(), nullable=True),
            sa.Column('tentativa', sa.Integer(), nullable=False),
            sa.Column('resultado', sa.String(length=24), nullable=False),
            sa.Column('tokens_entrada', sa.Integer(), nullable=True),
            sa.Column('tokens_saida', sa.Integer(), nullable=True),
            sa.Column('tokens_raciocinio', sa.Integer(), nullable=True),
            sa.Column('tokens_cache', sa.Integer(), nullable=True),
            sa.Column('tokens_total', sa.Integer(), nullable=True),
            sa.Column('estimado', sa.Boolean(), nullable=False),
            sa.Column('latencia_ms', sa.Integer(), nullable=False),
            sa.Column('ocorrido_em', _tz(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_uso_ia_user_ocorrido', 'uso_ia_chamadas', ['user_id', 'ocorrido_em'])
        op.create_index(
            'ix_uso_ia_modelo_ocorrido', 'uso_ia_chamadas', ['provedor', 'modelo_respondeu', 'ocorrido_em']
        )

    if 'sistema_estado_da_coleta' not in tabelas:
        op.create_table(
            'sistema_estado_da_coleta',
            sa.Column('id', sa.String(length=20), nullable=False),
            sa.Column('estado', sa.String(length=20), nullable=False),
            sa.Column('alterado_em', _tz(), nullable=False),
            sa.Column('alterado_por', sa.String(length=36), nullable=True),
            sa.Column('motivo', sa.String(length=300), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'uso_erros_acompanhamento' not in tabelas:
        op.create_table(
            'uso_erros_acompanhamento',
            sa.Column('impressao', sa.String(length=64), nullable=False),
            sa.Column('situacao', sa.String(length=20), nullable=False),
            sa.Column('resolvido_na_versao', sa.String(length=20), nullable=False),
            sa.Column('nota', sa.Text(), nullable=False),
            sa.Column('atualizado_em', _tz(), nullable=False),
            sa.PrimaryKeyConstraint('impressao'),
        )

    if 'sistema_acoes' not in tabelas:
        op.create_table(
            'sistema_acoes',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('acao', sa.String(length=40), nullable=False),
            sa.Column('executada_em', _tz(), nullable=False),
            sa.Column('executada_por', sa.String(length=36), nullable=True),
            sa.Column('parametros', sa.Text(), nullable=False),
            sa.Column('resultado', sa.String(length=300), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_sistema_acoes_executada', 'sistema_acoes', ['executada_em'])


def downgrade() -> None:
    inspetor = sa.inspect(op.get_bind())
    tabelas = set(inspetor.get_table_names())

    if 'sistema_acoes' in tabelas:
        op.drop_index('ix_sistema_acoes_executada', table_name='sistema_acoes')
        op.drop_table('sistema_acoes')
    if 'uso_erros_acompanhamento' in tabelas:
        op.drop_table('uso_erros_acompanhamento')
    if 'sistema_estado_da_coleta' in tabelas:
        op.drop_table('sistema_estado_da_coleta')
    if 'uso_ia_chamadas' in tabelas:
        op.drop_index('ix_uso_ia_modelo_ocorrido', table_name='uso_ia_chamadas')
        op.drop_index('ix_uso_ia_user_ocorrido', table_name='uso_ia_chamadas')
        op.drop_table('uso_ia_chamadas')
    if 'uso_erros' in tabelas:
        op.drop_index('ix_uso_erros_recebido', table_name='uso_erros')
        op.drop_index('ix_uso_erros_user', table_name='uso_erros')
        op.drop_index('ix_uso_erros_impressao_ocorrido', table_name='uso_erros')
        op.drop_table('uso_erros')
    if 'uso_eventos' in tabelas:
        op.drop_index('ix_uso_eventos_recebido', table_name='uso_eventos')
        op.drop_index('ix_uso_eventos_nome_ocorrido', table_name='uso_eventos')
        op.drop_index('ix_uso_eventos_user_ocorrido', table_name='uso_eventos')
        op.drop_table('uso_eventos')

    colunas_users = {c['name'] for c in inspetor.get_columns('users')}
    if 'uso_coleta_ativa' in colunas_users:
        with op.batch_alter_table('users') as batch_op:
            batch_op.drop_column('uso_coleta_alterada_em')
            batch_op.drop_column('uso_coleta_ativa')
