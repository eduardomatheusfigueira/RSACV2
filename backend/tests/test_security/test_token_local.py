#!/usr/bin/env python

"""
O token local: como é gravado, como é comparado e o que ele autoriza.

Substitui `test_safe_start_and_local_token.py`. Metade daquele arquivo fixava
o "portão de partida segura" — a recusa do backend a subir publicado sem conta
provisionada. Esse portão protegia um estado que deixou de existir junto com a
publicação por túnel.

O que sobrou é o que passou a ser a autenticação inteira: um arquivo `0600` na
pasta do usuário, comparado em tempo constante, apresentado num cabeçalho.
"""

import os
import stat
import sys

import pytest

from app.infrastructure.persistence.models import AuditLogModel
from app.security.dependencies import LOCAL_TOKEN_HEADER, operador_local
from app.security.local_token import (
    ensure_local_token,
    matches_local_token,
    read_local_token,
    token_path,
)

# ── Gravação do arquivo ───────────────────────────────────────────────

def test_token_e_gravado_com_permissao_restrita():
    """
    O token é a credencial inteira do RSAC: se outro usuário da máquina o lê,
    lê também o banco, os PDFs e as chaves de API.

    No Windows `chmod` não representa ACL, e a proteção vem da pasta do perfil
    do usuário — por isso a verificação de bits só roda em POSIX.
    """
    token = ensure_local_token()
    caminho = token_path()

    assert token, "o token deveria ter sido criado"
    assert caminho.is_file()
    assert caminho.read_text(encoding="utf-8").strip() == token

    if sys.platform != "win32":
        modo = stat.S_IMODE(os.stat(caminho).st_mode)
        assert modo == 0o600, f"permissão {oct(modo)} deixa o token legível por outros"


def test_token_e_reaproveitado_entre_partidas():
    """Regerar a cada partida invalidaria a janela aberta do app."""
    primeiro = ensure_local_token()
    assert ensure_local_token() == primeiro
    assert read_local_token() == primeiro


def test_token_tem_entropia_suficiente():
    """
    Não há limite de tentativas contra o cabeçalho — a defesa é o tamanho.

    `secrets.token_urlsafe(32)` produz 256 bits; qualquer coisa
    substancialmente menor tornaria a força bruta uma conversa.
    """
    assert len(ensure_local_token()) >= 40


# ── Comparação ────────────────────────────────────────────────────────

def test_comparacao_e_resistente_a_tempo_e_a_lixo():
    token = ensure_local_token()

    assert matches_local_token(token)
    assert not matches_local_token(token + "a")
    assert not matches_local_token(token[:-1])
    assert not matches_local_token("")
    assert not matches_local_token(None)


# ── O que o token autoriza ────────────────────────────────────────────

@pytest.mark.anyio
async def test_rota_de_status_responde_sem_credencial(anon_client):
    """
    É a rota que permite ao app distinguir "backend não subiu" de "token não
    bate". Responde sem credencial, e por isso não pode dizer mais que isso.
    """
    res = await anon_client.get("/api/v1/auth/status")
    assert res.status_code == 200

    corpo = res.json()
    assert corpo["authenticated"] is False
    assert corpo["local_token_disponivel"] is True
    # Nada que ajude quem não tem o token.
    assert "token" not in str(corpo).lower().replace("local_token_disponivel", "")


@pytest.mark.anyio
async def test_status_confirma_credencial_valida(async_client):
    corpo = (await async_client.get("/api/v1/auth/status")).json()
    assert corpo["authenticated"] is True


@pytest.mark.anyio
async def test_token_errado_nao_abre_a_api(anon_client):
    res = await anon_client.get(
        "/api/v1/projects", headers={LOCAL_TOKEN_HEADER: "nao-e-o-token-desta-instalacao"}
    )
    assert res.status_code == 401


# ── Autoria na trilha de auditoria ────────────────────────────────────

@pytest.mark.anyio
async def test_decisao_de_triagem_registra_quem_decidiu(async_client, db_session):
    """
    Sem autoria, `source="manual"` não diz de quem foi a decisão — e numa
    revisão sistemática isso é parte do produto.

    Com as contas removidas, quem assina é o usuário do sistema operacional.
    Continua sendo uma identidade real: é a conta em que o aplicativo roda, e
    ela sobrevive à cópia do banco para outra máquina.
    """
    projeto = (
        await async_client.post(
            "/api/v1/projects", json={"title": "Projeto de auditoria", "methodology": "PRISMA-ScR"}
        )
    ).json()

    paper = (
        await async_client.post(
            f"/api/v1/projects/{projeto['id']}/papers",
            json={"title": "Estudo qualquer sobre território", "decision": "Pendente"},
        )
    ).json()

    res = await async_client.patch(
        f"/api/v1/projects/{projeto['id']}/papers/{paper['id']}",
        json={"decision": "Incluído"},
    )
    assert res.status_code == 200

    registro = (
        db_session.query(AuditLogModel)
        .filter(AuditLogModel.paper_id == paper["id"])
        .order_by(AuditLogModel.created_at.desc())
        .first()
    )
    assert registro is not None
    assert registro.action == "decision_changed"
    assert registro.new_value == "Incluído"
    assert registro.username == operador_local(), "a decisão foi gravada sem autor"


def test_operador_local_nunca_e_vazio():
    """
    A trilha de auditoria não pode ter linha sem autor.

    `getpass.getuser()` levanta em ambiente sem usuário resolvível (contêiner
    sem `/etc/passwd`, por exemplo), e um `username` vazio faria a aba de
    Indicadores contar decisões de "Desconhecido" sem explicar por quê.
    """
    assert operador_local()
