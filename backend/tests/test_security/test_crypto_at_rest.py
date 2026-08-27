#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cifra dos segredos em repouso (doc 28 V-07, doc 29 §29.4.1).

As colunas chamadas `*_encrypted` guardavam `json.dumps(lista)` puro. O teste
central aqui é o de aceite da fase: gravar chaves pelas rotas reais, abrir o
**arquivo do banco em modo binário** e exigir que nenhum padrão de credencial
apareça nos bytes.
"""

import json
import re

import pytest
from sqlalchemy import create_engine, text

from app.security.crypto import CIPHER_PREFIX, MasterKeyError, SecretCipher, is_encrypted
from app.security.log_filter import mascarar
from app.security.migration import cifrar_segredos_legados

CHAVE_GEMINI = "AIzaSyCHAVE_DE_TESTE_MUITO_SECRETA_01"
CHAVE_QWEN = "sk-QWENCHAVEDETESTEMUITOSECRETA02"
CHAVE_SCOPUS = "scopus_credencial_secreta_de_teste"

PADROES = [re.compile(rb"AIzaSy[0-9A-Za-z_\-]{10,}"), re.compile(rb"sk-[0-9A-Za-z]{16,}")]


# ── O critério de aceite: os bytes do banco ───────────────────────────

@pytest.mark.anyio
async def test_arquivo_do_banco_nao_contem_chave_em_claro(async_client, tmp_path, monkeypatch):
    """
    Equivalente ao `strings rsac.db | grep AIza` do doc 30.

    Usa um banco em arquivo, não o in-memory dos outros testes, porque o que
    se está verificando é justamente o que fica gravado em disco — o arquivo
    que vai junto em backups e em pastas sincronizadas com a nuvem.
    """
    import httpx
    from sqlalchemy.orm import sessionmaker

    from app.api.deps import get_db
    from app.infrastructure.persistence.models import Base, UserModel
    from app.main import create_app
    from app.security.passwords import hash_password

    caminho = tmp_path / "rsac_teste.db"
    engine = create_engine(f"sqlite:///{caminho}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sessao = Session()

    sessao.add(
        UserModel(
            username="dono", password_hash=hash_password("senha-de-teste-12345"), role="owner"
        )
    )
    sessao.commit()

    app = create_app()
    app.dependency_overrides[get_db] = lambda: sessao
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        login = await client.post(
            "/api/v1/auth/login", json={"username": "dono", "password": "senha-de-teste-12345"}
        )
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        assert (
            await client.put(
                "/api/v1/ai/settings",
                json={
                    "ai_enabled": True,
                    "provider": "gemini",
                    "model": "gemini-3.6-flash",
                    "gemini_api_keys": [CHAVE_GEMINI],
                    "qwen_api_keys": [CHAVE_QWEN],
                    "temperature": 0.2,
                    "max_tokens": 4096,
                },
            )
        ).status_code == 200

        assert (
            await client.put(
                "/api/v1/settings/sources/Scopus", json={"api_key": CHAVE_SCOPUS}
            )
        ).status_code == 200

    sessao.close()
    engine.dispose()

    # Lê o arquivo principal **e** o journal WAL: em produção o engine sobe com
    # `journal_mode=WAL`, e uma gravação recente pode estar só no `-wal`.
    # Verificar apenas o `.db` deixaria o vazamento passar batido.
    arquivos = [caminho, *caminho.parent.glob(f"{caminho.name}-*")]
    bytes_do_banco = b"".join(f.read_bytes() for f in arquivos if f.is_file())

    for padrao in PADROES:
        achados = padrao.findall(bytes_do_banco)
        assert not achados, f"chave em claro no arquivo do banco: {achados[:2]}"
    assert CHAVE_SCOPUS.encode() not in bytes_do_banco

    # E o prefixo de versão está lá — prova de que foi cifrado, não apagado.
    assert CIPHER_PREFIX.encode() in bytes_do_banco


@pytest.mark.anyio
async def test_chave_cifrada_volta_pela_api(async_client):
    """A cifra é transparente: o que entra pela API volta utilizável."""
    assert (
        await async_client.put(
            "/api/v1/ai/settings",
            json={
                "ai_enabled": True,
                "provider": "gemini",
                "model": "gemini-3.6-flash",
                "gemini_api_keys": [CHAVE_GEMINI],
                "temperature": 0.2,
                "max_tokens": 4096,
            },
        )
    ).status_code == 200

    dados = (await async_client.get("/api/v1/ai/settings")).json()
    assert dados["gemini_keys_count"] == 1
    # Máscara dos 4 últimos caracteres — prova de que o valor decifrado é o
    # original, sem revelá-lo.
    assert dados["gemini_key_previews"] == ["••••••••" + CHAVE_GEMINI[-4:]]


# ── Migração de banco legado ──────────────────────────────────────────

def test_migracao_cifra_valores_legados(tmp_path):
    """
    Um banco da versão anterior sobe, migra e continua funcionando.

    Sem isto, atualizar o app apagaria as chaves de quem já usava o produto.
    """
    from sqlalchemy.orm import sessionmaker

    from app.infrastructure.persistence.models import AISettingsModel, Base, SourceCredentialModel

    caminho = tmp_path / "legado.db"
    engine = create_engine(f"sqlite:///{caminho}")
    Base.metadata.create_all(engine)

    # Grava em claro por SQL direto, como fazia a versão anterior. A conta
    # dona entra antes porque, desde a Fase 1 do doc 41, configuração de IA e
    # credencial de fonte têm titular.
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, role, is_active, "
                "created_at) VALUES ('u1', 'dono', 'x', 'owner', 1, "
                "'2026-08-19 10:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO ai_settings (id, user_id, ai_enabled, provider, model, "
                "api_keys_encrypted, gemini_api_keys_encrypted, qwen_api_keys_encrypted, "
                "local_api_keys_encrypted, temperature, max_tokens, updated_at) "
                "VALUES ('1', 'u1', 1, 'gemini', 'gemini-3.6-flash', :legado, :legado, "
                "'[]', '[]', 0.2, 4096, '2026-08-19 10:00:00')"
            ),
            {"legado": json.dumps([CHAVE_GEMINI])},
        )
        conn.execute(
            text(
                "INSERT INTO source_credentials (id, user_id, source_name, api_key, "
                "inst_token, updated_at) "
                "VALUES ('1', 'u1', 'SCOPUS', :chave, '', '2026-08-19 10:00:00')"
            ),
            {"chave": CHAVE_SCOPUS},
        )

    # Antes de migrar, o valor está legível no arquivo.
    assert CHAVE_SCOPUS.encode() in caminho.read_bytes()

    migrados = cifrar_segredos_legados(engine)
    assert migrados >= 3, f"esperava migrar ao menos 3 colunas, migrou {migrados}"

    # Depois, não está mais.
    bytes_depois = caminho.read_bytes()
    assert CHAVE_SCOPUS.encode() not in bytes_depois
    assert not PADROES[0].findall(bytes_depois)

    # E o ORM continua lendo o valor original.
    Session = sessionmaker(bind=engine)
    sessao = Session()
    settings_row = sessao.query(AISettingsModel).first()
    assert json.loads(settings_row.gemini_api_keys_encrypted) == [CHAVE_GEMINI]
    cred = sessao.query(SourceCredentialModel).first()
    assert cred.api_key == CHAVE_SCOPUS
    sessao.close()
    engine.dispose()


def test_migracao_e_idempotente(tmp_path):
    """Rodar de novo não recifra o que já está cifrado."""
    from app.infrastructure.persistence.models import Base

    caminho = tmp_path / "idempotente.db"
    engine = create_engine(f"sqlite:///{caminho}")
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, role, is_active, "
                "created_at) VALUES ('u1', 'dono', 'x', 'owner', 1, "
                "'2026-08-19 10:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO source_credentials (id, user_id, source_name, api_key, "
                "inst_token, updated_at) "
                "VALUES ('1', 'u1', 'SCOPUS', :chave, '', '2026-08-19 10:00:00')"
            ),
            {"chave": CHAVE_SCOPUS},
        )

    assert cifrar_segredos_legados(engine) == 1
    assert cifrar_segredos_legados(engine) == 0  # nada a fazer na segunda vez
    assert cifrar_segredos_legados(engine) == 0
    engine.dispose()


def test_migracao_em_banco_vazio_nao_falha(tmp_path):
    from app.infrastructure.persistence.models import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'vazio.db'}")
    Base.metadata.create_all(engine)
    assert cifrar_segredos_legados(engine) == 0
    engine.dispose()


# ── Comportamento da cifra ────────────────────────────────────────────

def test_ciclo_completo_da_cifra():
    cofre = SecretCipher(key_material=b"material-de-teste-abcdefgh")
    cifrado = cofre.encrypt(CHAVE_GEMINI)

    assert is_encrypted(cifrado)
    assert CHAVE_GEMINI not in cifrado
    assert cofre.decrypt(cifrado) == CHAVE_GEMINI


def test_cifra_e_idempotente():
    """Cifrar duas vezes não produz camada dupla."""
    cofre = SecretCipher(key_material=b"material-de-teste-abcdefgh")
    uma_vez = cofre.encrypt(CHAVE_GEMINI)
    assert cofre.encrypt(uma_vez) == uma_vez


def test_valor_legado_em_claro_e_lido_como_esta():
    """É o que permite o banco antigo subir antes de a migração rodar."""
    cofre = SecretCipher(key_material=b"material-de-teste-abcdefgh")
    assert cofre.decrypt(CHAVE_GEMINI) == CHAVE_GEMINI


def test_vazio_e_nulo_passam_intactos():
    cofre = SecretCipher(key_material=b"material-de-teste-abcdefgh")
    assert cofre.encrypt("") == ""
    assert cofre.encrypt(None) is None
    assert cofre.decrypt("") == ""
    assert cofre.decrypt(None) is None


def test_chave_mestra_errada_devolve_none_em_vez_de_lixo():
    """
    Devolver o texto cifrado viraria "chave de API" corrompida enviada ao
    provedor — pior que tratar como ausente.
    """
    cofre = SecretCipher(key_material=b"chave-original-1234567890")
    cifrado = cofre.encrypt(CHAVE_GEMINI)

    outro = SecretCipher(key_material=b"chave-diferente-098765432")
    assert outro.decrypt(cifrado) is None


def test_cada_cifra_produz_token_diferente():
    """Fernet inclui IV aleatório: dois valores iguais não ficam iguais no banco."""
    cofre = SecretCipher(key_material=b"material-de-teste-abcdefgh")
    assert cofre.encrypt(CHAVE_GEMINI) != cofre.encrypt(CHAVE_GEMINI)


# ── Chave-mestra e perfil ─────────────────────────────────────────────

def test_perfil_server_exige_chave_do_ambiente(monkeypatch, tmp_path):
    """
    Um arquivo de chave ao lado do banco seria lido pela mesma falha que leria
    o banco. No servidor, a chave vem do ambiente ou não vem (§29.4.1).
    """
    import app.security.crypto as crypto_module
    from app.config import DeploymentProfile, Settings

    settings_obj = Settings(deployment_profile=DeploymentProfile.SERVER, secret_key=None)
    monkeypatch.setattr(crypto_module, "settings", settings_obj)

    with pytest.raises(MasterKeyError, match="RSAC_SECRET_KEY"):
        crypto_module.obter_chave_mestra()


def test_perfil_server_aceita_chave_do_ambiente(monkeypatch):
    import app.security.crypto as crypto_module
    from app.config import DeploymentProfile, Settings

    settings_obj = Settings(
        deployment_profile=DeploymentProfile.SERVER, secret_key="chave-vinda-do-ambiente"
    )
    monkeypatch.setattr(crypto_module, "settings", settings_obj)

    assert crypto_module.obter_chave_mestra() == b"chave-vinda-do-ambiente"


def test_perfil_desktop_gera_arquivo_com_permissao_restrita(monkeypatch, tmp_path):
    import os
    import stat
    import sys

    import app.security.crypto as crypto_module
    from app.config import DeploymentProfile, Settings

    settings_obj = Settings(deployment_profile=DeploymentProfile.DESKTOP, secret_key=None)
    monkeypatch.setattr(crypto_module, "settings", settings_obj)
    monkeypatch.setattr(crypto_module, "master_key_path", lambda: tmp_path / "master.key")

    material = crypto_module.obter_chave_mestra()
    assert material

    caminho = tmp_path / "master.key"
    if sys.platform != "win32":
        modo = stat.S_IMODE(os.stat(caminho).st_mode)
        assert modo == 0o600, f"permissão {oct(modo)} — a chave-mestra ficaria legível a terceiros"

    # Chamar de novo reaproveita a mesma chave; do contrário, tudo o que já
    # foi cifrado deixaria de abrir a cada reinício.
    assert crypto_module.obter_chave_mestra() == material


# ── Filtro de log ─────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "texto",
    [
        f"chave configurada: {CHAVE_GEMINI}",
        f"Authorization: Bearer {CHAVE_QWEN}xyz123456",
        f'{{"api_key": "{CHAVE_SCOPUS}9876543210"}}',
        f"falha ao usar {CHAVE_QWEN}",
    ],
)
def test_filtro_de_log_mascara_credenciais(texto):
    mascarado = mascarar(texto)
    assert CHAVE_GEMINI not in mascarado
    assert CHAVE_QWEN not in mascarado
    assert "«segredo-mascarado»" in mascarado


def test_filtro_de_log_preserva_texto_comum():
    """Mascarar demais tornaria o log inútil para depurar."""
    texto = "Coleta concluída: 42 registros novos, 7 duplicados (SciELO)"
    assert mascarar(texto) == texto


def test_filtro_aplicado_ao_registro_de_log(caplog):
    """O segredo que chega por argumento também é mascarado."""
    import logging

    from app.security.log_filter import SecretMaskingFilter

    registro = logging.LogRecord(
        name="teste", level=logging.ERROR, pathname=__file__, lineno=1,
        msg="falhou com a chave %s", args=(CHAVE_GEMINI,), exc_info=None,
    )
    SecretMaskingFilter().filter(registro)

    assert CHAVE_GEMINI not in registro.getMessage()
    assert "«segredo-mascarado»" in registro.getMessage()
