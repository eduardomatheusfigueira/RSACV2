"""titularidade de projetos e credenciais por usuario

Revision ID: 19550e83628b
Revises: eb25063c7237
Create Date: 2026-08-27

Fase 1 do doc 41. Dá dono a `projects` e passa a configuração de IA e as
credenciais de bases científicas a serem por usuário.

**O preenchimento é a parte que exige cuidado.** As três colunas nascem
obrigatórias, e os dados que já existem não têm dono — logo, é preciso
atribuir um. A escolha correta num banco de mesa é a conta ativa mais antiga,
que por construção do perfil `desktop` é a única que existe. Se houver mais de
uma, esta revisão **falha em vez de escolher**: atribuir o acervo à conta
errada é pior que interromper a atualização, porque entrega dados de uma pessoa
a outra e ninguém percebe. Nesse caso a atribuição tem de ser feita à mão, com
alguém que saiba de quem é cada projeto.

Bancos vazios (instalação nova) passam direto: não há nada a atribuir.
"""
from typing import Sequence, Union

import uuid

from alembic import op
import sqlalchemy as sa

from app.config import settings


revision: str = '19550e83628b'
down_revision: Union[str, Sequence[str], None] = 'eb25063c7237'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class AtribuicaoAmbigua(RuntimeError):
    """Há dados sem dono e mais de uma conta candidata."""


# Marcador de senha inutilizável, na convenção que o Django popularizou: não é
# um hash Argon2 válido, então `verify_password` recusa qualquer senha contra
# ele. A conta existe para o token local se ligar a alguma coisa, não para ser
# usada com senha.
SENHA_INUTILIZAVEL = "!"


def _criar_conta_local(conexao) -> str:
    """
    Provisiona a conta dona da instalação de mesa.

    O nome é `local` — ou `local-2`, `local-3`, se já houver colisão — e a conta
    nasce sem senha utilizável e com papel `owner`, porque é a dona do acervo
    daquela máquina. Quem tem o token local já tinha acesso a tudo; a conta
    apenas dá a esse acesso um titular, que é o que a Fase 1 passou a exigir.
    """
    base = "local"
    nome = base
    n = 1
    while conexao.execute(
        sa.text("SELECT 1 FROM users WHERE username = :nome"), {"nome": nome}
    ).first():
        n += 1
        nome = f"{base}-{n}"

    novo_id = str(uuid.uuid4())
    conexao.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role, is_active,"
            " created_at) VALUES (:id, :nome, :senha, 'owner', TRUE,"
            " CURRENT_TIMESTAMP)"
        ),
        {"id": novo_id, "nome": nome, "senha": SENHA_INUTILIZAVEL},
    )
    return novo_id


def _conta_para_adocao(conexao) -> str | None:
    """
    Conta que herda os dados existentes, ou `None` se não houver o que herdar.

    Levanta se a escolha for ambígua.
    """
    tem_dados = any(
        conexao.execute(sa.text(f"SELECT 1 FROM {tabela} LIMIT 1")).first() is not None
        for tabela in ("projects", "ai_settings", "source_credentials")
    )
    if not tem_dados:
        return None

    contas = conexao.execute(
        sa.text(
            "SELECT id FROM users WHERE is_active = TRUE ORDER BY created_at ASC, id ASC"
        )
    ).scalars().all()

    if not contas:
        # Sem nenhuma conta e com dados a adotar. A resposta certa depende de
        # onde isto está rodando, e a diferença é grande:
        #
        #   * No **servidor**, não há como saber de quem é o acervo, e chutar
        #     entregaria o trabalho de alguém a outra pessoa. Recusar é o certo.
        #   * No **desktop**, a pergunta nem existe: o dono é quem está sentado
        #     na máquina, o mesmo que já tem o token local e o sistema de
        #     arquivos inteiro. Recusar ali não protege nada — só impede a
        #     pessoa de abrir o próprio programa depois de atualizar, que foi
        #     exatamente o que aconteceu.
        if settings.is_server_profile:
            raise AtribuicaoAmbigua(
                "Há projetos ou credenciais no banco e nenhuma conta ativa para "
                "recebê-los. Crie a conta antes de migrar:\n"
                "    python -m app.cli create-user <usuario> --role owner"
            )
        return _criar_conta_local(conexao)
    if len(contas) > 1:
        raise AtribuicaoAmbigua(
            f"Há {len(contas)} contas ativas e dados sem dono. Esta migração não "
            "adivinha de quem é cada projeto — atribuir ao dono errado entregaria "
            "o acervo de um pesquisador a outro. Defina `owner_id` à mão em "
            "`projects`, `ai_settings` e `source_credentials` e rode novamente."
        )
    return contas[0]


def upgrade() -> None:
    conexao = op.get_bind()
    dono = _conta_para_adocao(conexao)

    # ── projects.owner_id ─────────────────────────────────────────────
    # A coluna entra opcional, é preenchida e só então vira obrigatória: criar
    # `NOT NULL` de saída falharia em qualquer banco que já tenha uma linha.
    op.add_column("projects", sa.Column("owner_id", sa.String(length=36), nullable=True))
    if dono:
        conexao.execute(
            sa.text("UPDATE projects SET owner_id = :dono WHERE owner_id IS NULL"),
            {"dono": dono},
        )
    with op.batch_alter_table("projects") as lote:
        lote.alter_column("owner_id", existing_type=sa.String(length=36), nullable=False)
        lote.create_index("ix_projects_owner_id", ["owner_id"])
        lote.create_foreign_key("fk_projects_owner_id_users", "users", ["owner_id"], ["id"])

    # ── ai_settings.user_id ───────────────────────────────────────────
    # A coluna é única: se houver mais de uma linha herdada (não deveria, era
    # uma só por desenho), as excedentes são removidas — a configuração de IA é
    # reconstituível pela tela de configurações, e manter duplicata quebraria a
    # restrição.
    op.add_column("ai_settings", sa.Column("user_id", sa.String(length=36), nullable=True))
    if dono:
        conexao.execute(
            sa.text(
                "DELETE FROM ai_settings WHERE id NOT IN "
                "(SELECT id FROM ai_settings ORDER BY updated_at DESC LIMIT 1)"
            )
        )
        conexao.execute(
            sa.text("UPDATE ai_settings SET user_id = :dono WHERE user_id IS NULL"),
            {"dono": dono},
        )
    with op.batch_alter_table("ai_settings") as lote:
        lote.alter_column("user_id", existing_type=sa.String(length=36), nullable=False)
        lote.create_index("ix_ai_settings_user_id", ["user_id"], unique=True)
        lote.create_foreign_key("fk_ai_settings_user_id_users", "users", ["user_id"], ["id"])

    # ── source_credentials: único global vira único por usuário ───────
    op.add_column(
        "source_credentials", sa.Column("user_id", sa.String(length=36), nullable=True)
    )
    if dono:
        conexao.execute(
            sa.text("UPDATE source_credentials SET user_id = :dono WHERE user_id IS NULL"),
            {"dono": dono},
        )
    # A restrição única antiga precisa cair, e o nome dela depende do banco.
    # O PostgreSQL batizou-a `source_credentials_source_name_key` ao criar a
    # tabela; o SQLite gravou-a **sem nome**, embutida no `CREATE TABLE`, e o
    # modo em lote só consegue removê-la se uma convenção de nomes lhe der um
    # nome na reflexão. Sem essa distinção, a migração falha em SQLite com
    # "No such constraint" — que é onde o app de mesa quebraria.
    dialeto = conexao.dialect.name
    if dialeto == "sqlite":
        convencao = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
        nome_antigo = "uq_source_credentials_source_name"
    else:
        convencao = None
        nome_antigo = "source_credentials_source_name_key"

    with op.batch_alter_table(
        "source_credentials", naming_convention=convencao
    ) as lote:
        lote.alter_column("user_id", existing_type=sa.String(length=36), nullable=False)
        lote.drop_constraint(nome_antigo, type_="unique")
        lote.create_unique_constraint(
            "uq_source_credentials_user_source", ["user_id", "source_name"]
        )
        lote.create_index("ix_source_credentials_user_id", ["user_id"])
        lote.create_foreign_key(
            "fk_source_credentials_user_id_users", "users", ["user_id"], ["id"]
        )


def downgrade() -> None:
    nome_antigo = (
        "uq_source_credentials_source_name"
        if op.get_bind().dialect.name == "sqlite"
        else "source_credentials_source_name_key"
    )
    with op.batch_alter_table("source_credentials") as lote:
        lote.drop_constraint("fk_source_credentials_user_id_users", type_="foreignkey")
        lote.drop_index("ix_source_credentials_user_id")
        lote.drop_constraint("uq_source_credentials_user_source", type_="unique")
        lote.create_unique_constraint(nome_antigo, ["source_name"])
        lote.drop_column("user_id")

    with op.batch_alter_table("ai_settings") as lote:
        lote.drop_constraint("fk_ai_settings_user_id_users", type_="foreignkey")
        lote.drop_index("ix_ai_settings_user_id")
        lote.drop_column("user_id")

    with op.batch_alter_table("projects") as lote:
        lote.drop_constraint("fk_projects_owner_id_users", type_="foreignkey")
        lote.drop_index("ix_projects_owner_id")
        lote.drop_column("owner_id")
