#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Aceite do aviso do BETA (doc 43 §43.10).

Três coisas a defender, e a terceira é a que motivou o resto:

1. **A trava prende de verdade.** Quem não deu ciência não alcança a API.
2. **A trava não prende demais.** Quem não deu ciência precisa alcançar o
   texto, o próprio aceite e a saída — trancar essas três deixaria a pessoa
   do lado de fora do único lugar onde poderia entrar.
3. **O aceite registrado corresponde a algo que aconteceu.** O código gravava
   `terms_accepted_at = agora` no instante em que a conta nascia por Google,
   sem que nada tivesse sido mostrado. Registrar aceite que não houve é pior
   do que não registrar: fabrica prova.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.config import DeploymentProfile, Settings
from app.infrastructure.persistence.models import ProcessingRecordModel, UserModel
from app.legal import aceite as texto_legal
from app.main import create_app
from tests.conftest import OWNER_ID_TESTE


@pytest.fixture
def app_servidor(db_session, monkeypatch):
    """Aplicação no perfil `server`, que é onde o aceite é exigido."""
    from app import config as config_module
    from app import main as main_module
    from app.api.v1 import aceite as aceite_module
    from app.security import dependencies as deps_module

    settings_obj = Settings(deployment_profile=DeploymentProfile.SERVER)
    for modulo in (config_module, main_module, aceite_module, deps_module):
        monkeypatch.setattr(modulo, "settings", settings_obj, raising=False)

    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    return application


@pytest.fixture
def dono(db_session) -> UserModel:
    return db_session.get(UserModel, OWNER_ID_TESTE)


def _autenticar(application, db_session, usuario):
    """Entra como `usuario`, contornando o login — o alvo aqui é o aceite."""
    from app.security.dependencies import require_session

    application.dependency_overrides[require_session] = lambda: usuario
    return TestClient(application)


# ══════════════════════════════════════════════════════════════════════
# 1. A trava prende
# ══════════════════════════════════════════════════════════════════════

def test_sem_aceite_a_api_responde_451(app_servidor, db_session, dono):
    dono.terms_accepted_at = None
    db_session.flush()

    with _autenticar(app_servidor, db_session, dono) as cliente:
        resposta = cliente.get("/api/v1/projects")

    assert resposta.status_code == 451, (
        "sem esta trava, a pessoa usa o serviço sem ter sido informada de nada"
    )
    assert "ciência" in resposta.json()["detail"]


def test_versao_antiga_volta_a_pedir_ciencia(app_servidor, db_session, dono):
    """
    Aceitar a versão de março não é aceitar a de dezembro.

    A comparação é por igualdade, e não por "existe alguma data": um aviso que
    muda o que a pessoa concordou precisa ser concordado de novo.
    """
    from datetime import datetime, timezone

    dono.terms_accepted_at = datetime.now(timezone.utc)
    dono.terms_version = "2020-01-1"
    db_session.flush()

    with _autenticar(app_servidor, db_session, dono) as cliente:
        assert cliente.get("/api/v1/projects").status_code == 451


def test_a_trava_cobre_todas_as_rotas_de_dado(app_servidor, db_session, dono):
    """
    Enumera a API em vez de conferir uma rota escolhida a dedo.

    Uma rota nova que nasça fora da trava é exatamente o defeito que a
    dependência no router existe para impedir — e o jeito de saber é
    perguntar ao OpenAPI, não confiar na memória.
    """
    dono.terms_accepted_at = None
    db_session.flush()

    livres = {"/api/v1/aceite", "/api/v1/health"}
    alvos = [
        (caminho, metodo)
        for caminho, metodos in app_servidor.openapi()["paths"].items()
        for metodo in metodos
        if caminho not in livres and not caminho.startswith("/api/v1/auth")
    ]
    assert len(alvos) >= 25, "a enumeração encontrou rotas de menos; conferir o OpenAPI"

    with _autenticar(app_servidor, db_session, dono) as cliente:
        for caminho, metodo in alvos:
            # O caminho com parâmetro vira um valor qualquer: a trava é
            # avaliada antes de a rota existir de fato, então o valor não
            # importa — o que importa é não receber 404 por caminho inválido.
            url = re.sub(r"\{[^}]+\}", "inexistente", caminho)
            resposta = cliente.request(metodo.upper(), url, json={})
            assert resposta.status_code == 451, (
                f"{metodo.upper()} {caminho} respondeu {resposta.status_code} "
                f"sem aceite — deveria ser 451"
            )


# ══════════════════════════════════════════════════════════════════════
# 2. A trava não prende demais
# ══════════════════════════════════════════════════════════════════════

def test_sem_aceite_ainda_se_alcanca_o_texto(app_servidor, db_session, dono):
    dono.terms_accepted_at = None
    db_session.flush()

    with _autenticar(app_servidor, db_session, dono) as cliente:
        resposta = cliente.get("/api/v1/aceite")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["aceito"] is False
    assert corpo["versao"] == texto_legal.VERSAO
    assert corpo["texto"].startswith("# Aviso e Termos do Revsist BETA")


def test_sem_aceite_ainda_se_consegue_sair(app_servidor, db_session, dono):
    """Ninguém pode ficar preso dentro de uma sessão que não consegue usar."""
    dono.terms_accepted_at = None
    db_session.flush()

    with _autenticar(app_servidor, db_session, dono) as cliente:
        assert cliente.post("/api/v1/auth/logout").status_code in (200, 204)


def test_no_perfil_desktop_nao_ha_trava(db_session, dono, monkeypatch):
    """
    No app de mesa não há terceiro cujos dados proteger.

    A única conta é a de quem instalou o programa na própria máquina;
    interpor uma tela de aceite ali seria atrito sem função.
    """
    from app import config as config_module
    from app import main as main_module
    from app.api.v1 import aceite as aceite_module
    from app.security import dependencies as deps_module

    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP)
    for modulo in (config_module, main_module, aceite_module, deps_module):
        monkeypatch.setattr(modulo, "settings", settings_obj, raising=False)

    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    dono.terms_accepted_at = None
    db_session.flush()

    with _autenticar(application, db_session, dono) as cliente:
        assert cliente.get("/api/v1/projects").status_code == 200


# ══════════════════════════════════════════════════════════════════════
# 3. O aceite registrado corresponde a algo que aconteceu
# ══════════════════════════════════════════════════════════════════════

def test_aceitar_libera_e_grava_versao_e_resumo(app_servidor, db_session, dono):
    dono.terms_accepted_at = None
    db_session.flush()

    with _autenticar(app_servidor, db_session, dono) as cliente:
        aceite = cliente.post("/api/v1/aceite", json={"versao": texto_legal.VERSAO})
        assert aceite.status_code == 200
        assert aceite.json()["aceito"] is True
        assert cliente.get("/api/v1/projects").status_code == 200

    db_session.refresh(dono)
    assert dono.terms_accepted_at is not None
    assert dono.terms_version == texto_legal.VERSAO
    assert dono.terms_sha256 == texto_legal.sha256(), (
        "o resumo é o que responde 'o que exatamente essa pessoa leu'"
    )


def test_versao_divergente_e_recusada(app_servidor, db_session, dono):
    """
    Uma aba aberta há uma semana não pode registrar aceite do texto novo.

    Sem esta conferência, a pessoa concordaria com um texto e o banco
    registraria outro — que é o defeito que este módulo inteiro existe para
    não ter.
    """
    dono.terms_accepted_at = None
    db_session.flush()

    with _autenticar(app_servidor, db_session, dono) as cliente:
        resposta = cliente.post("/api/v1/aceite", json={"versao": "2020-01-1"})

    assert resposta.status_code == 409
    db_session.refresh(dono)
    assert dono.terms_accepted_at is None


def test_aceite_entra_no_ropa_como_consentimento(app_servidor, db_session, dono):
    dono.terms_accepted_at = None
    db_session.flush()
    db_session.query(ProcessingRecordModel).delete()

    with _autenticar(app_servidor, db_session, dono) as cliente:
        cliente.post("/api/v1/aceite", json={"versao": texto_legal.VERSAO})

    registros = db_session.query(ProcessingRecordModel).all()
    assert len(registros) == 1
    assert registros[0].operation == "consent_given"
    assert registros[0].user_id == dono.id
    assert texto_legal.VERSAO in registros[0].purpose


def test_conta_nova_por_google_nasce_sem_aceite():
    """
    O defeito que originou este arquivo.

    `_resolver_conta` gravava `terms_accepted_at = agora` no instante
    do cadastro. A pessoa nunca tinha visto texto nenhum, e o banco afirmava
    que ela concordara. Este teste lê o código-fonte porque a função depende
    de uma identidade Google válida para ser exercitada, e o que se quer
    garantir é a **ausência** de duas linhas.
    """
    from pathlib import Path

    import app.api.v1.auth as modulo

    fonte = Path(modulo.__file__).read_text(encoding="utf-8")
    trecho = fonte[fonte.index("def _resolver_conta"):]
    trecho = trecho[: trecho.index("\ndef ", 10)]

    assert "terms_accepted_at=" not in trecho, (
        "conta criada por Google não pode nascer com aceite: ninguém mostrou nada a ninguém"
    )
    assert "terms_version=" not in trecho


# ══════════════════════════════════════════════════════════════════════
# O texto
# ══════════════════════════════════════════════════════════════════════

def test_o_texto_cobre_o_que_o_artigo_9_exige():
    """
    O art. 9º dá ao titular direito a informação clara sobre o tratamento.
    Estas são as perguntas que ele manda responder.
    """
    t = texto_legal.TEXTO
    for exigido, onde in [
        ("computador pessoal", "onde os dados ficam"),
        ("backup", "retenção e perda possível"),
        ("90 dias", "prazo do registro de acesso"),
        ("art. 18", "direitos do titular"),
        ("ANPD", "direito de reclamar"),
        ("15 dias", "prazo de resposta"),
        ("sensível", "o que não deve ser colocado ali"),
        ("30 dias", "aviso de encerramento"),
    ]:
        assert exigido in t, f"o aviso não trata de: {onde}"


def test_o_texto_nao_recolhe_consentimento_de_ia():
    """
    Juntar as duas coisas invalidaria a que mais precisa valer.

    O envio ao provedor de IA é transferência internacional e exige
    consentimento específico (art. 33, VIII); o art. 8º §4º diz que
    autorização genérica é nula. O aviso informa sobre a IA e diz
    explicitamente que não é ali que ela é autorizada.
    """
    t = texto_legal.TEXTO
    assert "não está sendo autorizado por este aviso" in t
    assert "consentimento específico" in t


def test_lacunas_de_identificacao_continuam_marcadas():
    """
    Enquanto não forem preenchidas, este teste falha de propósito.

    Preenchê-las com dado plausível produziria um documento jurídico com
    informação falsa publicado sob o nome de alguém. O aviso de privacidade é
    declaração vinculante, não texto de vitrine — quem preenche é o
    controlador.
    """
    faltando = texto_legal.verificar_lacunas()
    assert faltando == list(texto_legal.MARCADORES), (
        f"lacunas parcialmente preenchidas: {faltando}. "
        f"Preencha todas e troque este teste por `assert faltando == []`."
    )
