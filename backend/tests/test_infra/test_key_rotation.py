#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes da rotina de rotação de chave mestra (doc 40 §40.7.3, doc 41 Tarefa 4.14).
"""

import json
from cryptography.fernet import Fernet
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import UserModel, generate_uuid
from app.security.crypto import CIPHER_PREFIX, _derivar_chave
from app.security.key_rotation import rotacionar_chaves


def test_rotacao_de_chave_mestra_sucesso(db_session: Session):
    old_key = "chave-antiga-mestra-de-teste-12345"
    new_key = "nova-chave-mestra-de-teste-67890"

    old_fernet = Fernet(_derivar_chave(old_key.encode("utf-8")))
    new_fernet = Fernet(_derivar_chave(new_key.encode("utf-8")))

    user_id = generate_uuid()
    db_session.add(UserModel(id=user_id, username="usuario_rotacao", role="researcher"))
    db_session.commit()

    # 1. Inserir AISettings com token gerado por old_key via SQL direto
    gemini_plain = json.dumps(["AIzaSyMockKey1", "AIzaSyMockKey2"])
    gemini_enc = f"{CIPHER_PREFIX}{old_fernet.encrypt(gemini_plain.encode('utf-8')).decode('ascii')}"

    agora = "2026-08-29 12:00:00"

    db_session.execute(
        text(
            "INSERT INTO ai_settings (id, user_id, ai_enabled, provider, model, temperature, max_tokens, "
            "api_keys_encrypted, gemini_api_keys_encrypted, qwen_api_keys_encrypted, local_api_keys_encrypted, updated_at) "
            "VALUES (:id, :user_id, 1, 'gemini', 'gemini-2.5-flash', 0.2, 4096, '[]', :val, '[]', '[]', :t)"
        ),
        {"id": generate_uuid(), "user_id": user_id, "val": gemini_enc, "t": agora},
    )

    # 2. Inserir SourceCredential com token gerado por old_key via SQL direto
    scopus_plain = "scopus_secret_key_abc"
    scopus_enc = f"{CIPHER_PREFIX}{old_fernet.encrypt(scopus_plain.encode('utf-8')).decode('ascii')}"

    db_session.execute(
        text(
            "INSERT INTO source_credentials (id, user_id, source_name, api_key, inst_token, updated_at) "
            "VALUES (:id, :user_id, 'SCOPUS', :val, '', :t)"
        ),
        {"id": generate_uuid(), "user_id": user_id, "val": scopus_enc, "t": agora},
    )
    db_session.commit()

    # 3. Executar rotação
    conn = db_session.connection()
    relatorio = rotacionar_chaves(conn, old_key, new_key)
    assert relatorio["ai_settings_atualizados"] == 1
    assert relatorio["source_credentials_atualizadas"] == 1

    # 4. Verificar que a nova chave decifra os tokens recifrados
    gemini_novo = db_session.execute(
        text("SELECT gemini_api_keys_encrypted FROM ai_settings WHERE user_id = :u"),
        {"u": user_id},
    ).scalar()
    token_novo_gemini = gemini_novo[len(CIPHER_PREFIX) :].encode("ascii")
    decifrado_gemini = new_fernet.decrypt(token_novo_gemini).decode("utf-8")
    assert json.loads(decifrado_gemini) == ["AIzaSyMockKey1", "AIzaSyMockKey2"]

    scopus_novo = db_session.execute(
        text("SELECT api_key FROM source_credentials WHERE user_id = :u"),
        {"u": user_id},
    ).scalar()
    token_novo_scopus = scopus_novo[len(CIPHER_PREFIX) :].encode("ascii")
    decifrado_scopus = new_fernet.decrypt(token_novo_scopus).decode("utf-8")
    assert decifrado_scopus == "scopus_secret_key_abc"


def test_rotacao_rejeita_chaves_iguais_ou_vazias(db_session: Session):
    engine = db_session.get_bind()
    with pytest.raises(ValueError):
        rotacionar_chaves(engine, "", "nova_chave")

    with pytest.raises(ValueError):
        rotacionar_chaves(engine, "mesma_chave", "mesma_chave")
