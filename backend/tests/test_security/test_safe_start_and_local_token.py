#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Partida segura, token local e autoria na auditoria
(doc 29 §29.2.4, §29.3.2, §29.3.5).

A cláusula §29.2.4 é a que impede a falha original de voltar por omissão: um
servidor público sem autenticação deixa de ser um estado alcançável do sistema
— o processo se recusa a subir em vez de subir aberto.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.config import DeploymentProfile, Settings
from app.infrastructure.persistence.models import AuditLogModel
from app.main import create_app
from app.security import local_token as local_token_module


def _app_com_perfil(db_session, monkeypatch, perfil: DeploymentProfile):
    settings_obj = Settings(deployment_profile=perfil)
    import app.config as config_module
    import app.main as main_module
    import app.security.local_token as lt_module

    monkeypatch.setattr(config_module, "settings", settings_obj)
    monkeypatch.setattr(main_module, "settings", settings_obj)
    monkeypatch.setattr(lt_module, "settings", settings_obj)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return app


# ── Portão de partida segura ──────────────────────────────────────────

def test_perfil_server_sem_contas_recusa_subir(db_session_sem_contas, monkeypatch, tmp_path):
    """
    O caso que originou todo o diagnóstico: backend publicado sem autenticação.

    O `lifespan` roda ao entrar no `TestClient`; sem conta provisionada ele
    levanta, e o processo não chega a atender requisição nenhuma.
    """
    db_session = db_session_sem_contas
    monkeypatch.setattr(local_token_module, "TOKEN_FILENAME", "token_de_teste")
    app = _app_com_perfil(db_session, monkeypatch, DeploymentProfile.SERVER)

    import app.main as main_module

    monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    with pytest.raises(RuntimeError, match="Nenhuma conta de acesso provisionada"):
        with TestClient(app):
            pass


def test_perfil_server_com_conta_sobe(db_session, monkeypatch, contas):
    """Com conta provisionada, o mesmo perfil sobe normalmente."""
    app = _app_com_perfil(db_session, monkeypatch, DeploymentProfile.SERVER)

    import app.main as main_module

    monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200


def test_perfil_desktop_sem_contas_apenas_avisa(db_session, monkeypatch, caplog):
    """No desktop o app usa o token local — recusar-se a subir seria excessivo."""
    app = _app_com_perfil(db_session, monkeypatch, DeploymentProfile.DESKTOP)

    import app.main as main_module

    monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200


# ── Token local ───────────────────────────────────────────────────────

def test_token_local_e_gravado_com_permissao_restrita(monkeypatch, tmp_path):
    """O arquivo é a credencial do app de mesa — só o dono pode lê-lo."""
    import os
    import stat
    import sys

    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    monkeypatch.setattr(local_token_module, "settings", settings_obj)
    monkeypatch.setattr(local_token_module, "token_path", lambda: tmp_path / "runtime_token")

    token = local_token_module.ensure_local_token()
    assert token and len(token) >= 32

    caminho = tmp_path / "runtime_token"
    if sys.platform != "win32":
        modo = stat.S_IMODE(os.stat(caminho).st_mode)
        assert modo == 0o600, f"permissão {oct(modo)} — o token não pode ser legível por terceiros"

    # Chamar de novo devolve o mesmo token, não gera outro.
    assert local_token_module.ensure_local_token() == token


def test_token_local_nao_existe_no_perfil_server(monkeypatch, tmp_path):
    """No servidor a prova de identidade é a senha; um arquivo seria alvo a mais."""
    settings_obj = Settings(deployment_profile=DeploymentProfile.SERVER)
    monkeypatch.setattr(local_token_module, "settings", settings_obj)
    monkeypatch.setattr(local_token_module, "token_path", lambda: tmp_path / "runtime_token")

    assert local_token_module.ensure_local_token() is None
    assert not (tmp_path / "runtime_token").exists()
    assert local_token_module.matches_local_token("qualquer-coisa") is False


def test_comparacao_do_token_e_resistente(monkeypatch, tmp_path):
    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    monkeypatch.setattr(local_token_module, "settings", settings_obj)
    monkeypatch.setattr(local_token_module, "token_path", lambda: tmp_path / "runtime_token")

    token = local_token_module.ensure_local_token()
    assert local_token_module.matches_local_token(token) is True
    assert local_token_module.matches_local_token(token[:-1]) is False
    assert local_token_module.matches_local_token("") is False
    assert local_token_module.matches_local_token(None) is False


@pytest.mark.anyio
async def test_troca_do_token_local_por_sessao(db_session, monkeypatch, contas, tmp_path):
    """O fluxo que mantém o app de mesa sem tela de login."""
    import httpx

    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    monkeypatch.setattr(local_token_module, "settings", settings_obj)
    monkeypatch.setattr(local_token_module, "token_path", lambda: tmp_path / "runtime_token")
    token = local_token_module.ensure_local_token()

    app = _app_com_perfil(db_session, monkeypatch, DeploymentProfile.DESKTOP)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.get("/api/v1/projects")).status_code == 401

        res = await client.post("/api/v1/auth/local", json={"token": token})
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "owner"

        # A sessão emitida vale como qualquer outra.
        client.headers["Authorization"] = f"Bearer {res.json()['access_token']}"
        assert (await client.get("/api/v1/projects")).status_code == 200

        # Token errado não passa.
        assert (await client.post("/api/v1/auth/local", json={"token": "x" * 40})).status_code == 401


# ── Autoria na trilha de auditoria ────────────────────────────────────

@pytest.mark.anyio
async def test_decisao_de_triagem_registra_quem_decidiu(async_client, db_session):
    """
    Sem autoria, `source="manual"` não distingue o pesquisador do coautor — e
    numa revisão sistemática saber de quem foi a decisão é parte do produto.
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
    assert registro.username == "dono_teste", "a decisão foi gravada sem autor"
    assert registro.user_id


@pytest.mark.anyio
async def test_autoria_distingue_dois_operadores(async_client, researcher_client, db_session):
    """
    Dois operadores no mesmo servidor deixam trilhas distinguíveis.

    Antes da Fase 1 do doc 41 este teste operava sobre **um** projeto, porque
    não havia titularidade e qualquer conta alcançava o acervo de qualquer
    outra. Com contas individuais, cada um trabalha no próprio projeto — e a
    trilha de auditoria continua tendo de dizer de quem foi cada decisão, que é
    o que sustenta a reprodutibilidade da revisão.
    """
    async def _projeto_com_estudo(cliente, titulo):
        projeto = (
            await cliente.post(
                "/api/v1/projects", json={"title": titulo, "methodology": "PRISMA-ScR"}
            )
        ).json()
        paper = (
            await cliente.post(
                f"/api/v1/projects/{projeto['id']}/papers",
                json={"title": "Estudo em avaliação", "decision": "Pendente"},
            )
        ).json()
        return projeto, paper

    projeto_dono, paper_dono = await _projeto_com_estudo(async_client, "Revisão do dono")
    projeto_pesq, paper_pesq = await _projeto_com_estudo(
        researcher_client, "Revisão do pesquisador"
    )

    await async_client.patch(
        f"/api/v1/projects/{projeto_dono['id']}/papers/{paper_dono['id']}",
        json={"decision": "Incluído"},
    )
    await researcher_client.patch(
        f"/api/v1/projects/{projeto_pesq['id']}/papers/{paper_pesq['id']}",
        json={"decision": "Excluído"},
    )

    autoria = {
        r.paper_id: r.username
        for r in db_session.query(AuditLogModel)
        .filter(AuditLogModel.paper_id.in_([paper_dono["id"], paper_pesq["id"]]))
        .all()
    }
    assert autoria.get(paper_dono["id"]) == "dono_teste"
    assert autoria.get(paper_pesq["id"]) == "pesquisador_teste"


# ══════════════════════════════════════════════════════════════════════════
# Onde o token fica, e quem diz onde ele fica
# ══════════════════════════════════════════════════════════════════════════
#
# O app de mesa precisa achar o arquivo do token, e até aqui cada lado deduzia
# o caminho por conta própria — `scripts/launcher.py` em Python, o processo
# principal do Electron em TypeScript. Os dois erraram do mesmo jeito no
# Windows, onde `platformdirs`, sem `appauthor`, usa o `appname` como autor e
# duplica o nome: `%LOCALAPPDATA%\RSAC\RSAC`, não `%LOCALAPPDATA%\RSAC`.
# Procurando um nível acima, ninguém achava o arquivo, e o app abria na tela de
# login com o token intacto no disco.
#
# Nem Linux nem macOS têm esse nível extra, então em desenvolvimento nada
# aparecia. Estes testes fixam as duas metades da correção: o backend passa a
# aceitar uma pasta escolhida à mão, e a anunciar onde gravou.


def test_data_dir_respeita_a_variavel_de_ambiente(tmp_path, monkeypatch):
    """
    `RSAC_DATA_DIR` era lida pelo launcher e ignorada pelo backend.

    Os dois lados podiam portanto discordar sobre onde os dados estão — um
    procurando numa pasta, o outro gravando noutra.
    """
    from app.config import Settings

    escolhida = tmp_path / "pasta escolhida"
    settings_obj = Settings(data_dir_configurado=str(escolhida))
    assert settings_obj.data_dir == escolhida
    assert escolhida.is_dir(), "a pasta deve ser criada, não só devolvida"


def test_data_dir_vazio_cai_no_padrao_do_sistema():
    """Vazio não pode virar uma pasta chamada "" na raiz."""
    from app.config import Settings

    import platformdirs

    settings_obj = Settings(data_dir_configurado="   ")
    assert settings_obj.data_dir == Path(platformdirs.user_data_dir(settings_obj.app_name))


def test_backend_anuncia_o_caminho_do_token(tmp_path, monkeypatch, capsys):
    """
    O anúncio é o que dispensa a dedução do lado do cliente.

    O prefixo é contrato com `frontend/electron/python-manager.ts`: mudá-lo
    quebra o app de mesa sem quebrar teste nenhum do servidor — daí fixá-lo
    aqui, literal.
    """
    from app.config import Settings
    from app.security import local_token as lt

    settings_obj = Settings(
        deployment_profile=DeploymentProfile.DESKTOP,
        data_dir_configurado=str(tmp_path / "dados"),
    )
    monkeypatch.setattr(lt, "settings", settings_obj)

    lt.anunciar_caminho_do_token()
    saida = capsys.readouterr().out

    assert saida.startswith("RSAC_RUNTIME_TOKEN_PATH=")
    caminho = Path(saida.split("=", 1)[1].strip())
    assert caminho == settings_obj.data_dir / "runtime_token"
    assert caminho.is_absolute(), "caminho relativo não serve a quem roda noutro cwd"


def test_anuncio_nunca_revela_o_token(tmp_path, monkeypatch, capsys):
    """O caminho não é segredo; o token é. Um não pode carregar o outro."""
    from app.config import Settings
    from app.security import local_token as lt

    settings_obj = Settings(
        deployment_profile=DeploymentProfile.DESKTOP,
        data_dir_configurado=str(tmp_path / "dados"),
    )
    monkeypatch.setattr(lt, "settings", settings_obj)

    token = lt.ensure_local_token()
    assert token, "sem token não há o que vazar, e o teste não valeria nada"

    capsys.readouterr()
    lt.anunciar_caminho_do_token()
    assert token not in capsys.readouterr().out


def test_perfil_server_nao_anuncia_nada(monkeypatch, capsys):
    """Lá não há token local — anunciar um caminho seria apontar para o nada."""
    from app.config import Settings
    from app.security import local_token as lt

    monkeypatch.setattr(lt, "settings", Settings(deployment_profile=DeploymentProfile.SERVER))
    lt.anunciar_caminho_do_token()
    assert capsys.readouterr().out == ""
