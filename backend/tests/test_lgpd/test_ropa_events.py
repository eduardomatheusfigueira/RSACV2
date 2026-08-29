#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Testes de integração dos 8 eventos do ROPA (LGPD Art. 37, doc 40 §40.5.2).
"""

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import ProcessingRecordModel, UserModel, generate_uuid
from app.services import ropa_service


def test_ropa_registra_oito_eventos(db_session: Session):
    user_id = generate_uuid()

    # 1. signup
    r_signup = ropa_service.registrar(
        db_session,
        operation="signup",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Cadastro de conta de usuário",
        data_categories=["identificacao", "contato", "credencial"],
        user_id=user_id,
    )
    assert r_signup.operation == "signup"

    # 2. login
    r_login = ropa_service.registrar(
        db_session,
        operation="login",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Autenticação no sistema",
        data_categories=["identificacao", "credencial", "conexao"],
        user_id=user_id,
    )
    assert r_login.operation == "login"

    # 3. data_export
    r_export = ropa_service.registrar(
        db_session,
        operation="data_export",
        legal_basis="art7_VI_exercicio_de_direitos",
        purpose="Portabilidade e exportação de perfil",
        data_categories=["identificacao", "conteudo_de_pesquisa"],
        user_id=user_id,
    )
    assert r_export.operation == "data_export"

    # 4. data_erasure
    r_erasure = ropa_service.registrar(
        db_session,
        operation="data_erasure",
        legal_basis="art7_VI_exercicio_de_direitos",
        purpose="Eliminação definitiva de dados",
        data_categories=["identificacao", "contato", "documento"],
        user_id=user_id,
    )
    assert r_erasure.operation == "data_erasure"

    # 5. ai_dispatch
    r_ai = ropa_service.registrar(
        db_session,
        operation="ai_dispatch",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Triagem metodológica com IA",
        data_categories=["conteudo_de_pesquisa", "referencia_bibliografica"],
        user_id=user_id,
        recipient="google_gemini",
        international=True,
    )
    assert r_ai.operation == "ai_dispatch"
    assert r_ai.international is True

    # 6. pdf_fetch
    r_pdf = ropa_service.registrar(
        db_session,
        operation="pdf_fetch",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Download de texto integral",
        data_categories=["documento", "referencia_bibliografica"],
        user_id=user_id,
        recipient="scielo_org",
        international=False,
    )
    assert r_pdf.operation == "pdf_fetch"

    # 7. consent_given
    r_consent_given = ropa_service.registrar(
        db_session,
        operation="consent_given",
        legal_basis="art7_I_consentimento",
        purpose="Aceite de termos e aviso de privacidade",
        data_categories=["consentimento"],
        user_id=user_id,
    )
    assert r_consent_given.operation == "consent_given"

    # 8. consent_revoked
    r_consent_revoked = ropa_service.registrar(
        db_session,
        operation="consent_revoked",
        legal_basis="art7_I_consentimento",
        purpose="Revogação de chaves e permissões",
        data_categories=["credencial"],
        user_id=user_id,
    )
    assert r_consent_revoked.operation == "consent_revoked"

    total = (
        db_session.query(ProcessingRecordModel)
        .filter(ProcessingRecordModel.user_id == user_id)
        .count()
    )
    assert total == 8
