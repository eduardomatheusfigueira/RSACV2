#!/usr/bin/env python

"""RSAC V2 — Router para Backup e Restauração de Chaves e Perfil de Workspace."""

import json
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.profile import (
    EncryptedEnvelope,
    KeysExportRequest,
    KeysImportRequest,
    KeysImportResponse,
    ProfileExportRequest,
    ProfileImportResponse,
)
from app.security.secret_box import (
    SecretBoxError,
    decrypt_envelope,
    encrypt_payload,
    is_envelope,
)
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])
profile_service = ProfileService()


@router.post("/keys/export", response_model=EncryptedEnvelope)
def export_keys(
    request: KeysExportRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Exporta as credenciais cadastradas em um arquivo **cifrado com senha**.

    Era `GET` e devolvia as chaves em texto claro — um endereço que qualquer
    navegação, `<img>` ou prefetch acionava, e cujo corpo era a credencial. É
    `POST` com senha no corpo justamente para não ser acionável por navegação,
    e o que sai é um envelope que ninguém abre sem a senha (doc 29 §29.4.3).
    """
    try:
        payload = profile_service.export_keys(db)
        return encrypt_payload(payload, request.export_password)
    except SecretBoxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"[Profile] Erro ao exportar chaves: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Falha ao exportar as chaves de API.") from e


@router.post("/keys/import", response_model=KeysImportResponse)
def import_keys(
    request: KeysImportRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Importa um arquivo de chaves — envelope cifrado ou backup legado em claro.

    Backups antigos (`rsac_api_keys_v1`, sem cifra) continuam sendo aceitos:
    quem já tem um arquivo salvo não fica sem caminho de restauração.
    """
    try:
        target_input: Any = request.payload if request.payload is not None else request.raw_content

        # Envelope cifrado pode chegar como objeto ou como texto do arquivo.
        candidate = target_input
        if isinstance(candidate, str):
            try:
                candidate = json.loads(candidate)
            except ValueError:
                candidate = target_input

        if is_envelope(candidate):
            target_input = decrypt_envelope(candidate, request.export_password or "")

        if target_input is None:
            raise ValueError("Nenhum conteúdo informado para importação.")

        return profile_service.import_keys(db, target_input)
    except SecretBoxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"[Profile] Erro ao importar chaves: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Falha ao importar as chaves de API. Confira o arquivo e a senha.") from e


@router.post("/export")
def export_full_profile(
    request: ProfileExportRequest = Body(default_factory=ProfileExportRequest),
    db: Session = Depends(get_db),
):
    """
    Exporta o perfil completo de sessão, preferências, configurações de IA,
    credenciais de fontes e todos os projetos com artigos, protocolos e extrações.
    """
    try:
        session_prefs = request.session_preferences.model_dump() if request.session_preferences else {}
        profile = profile_service.export_profile(db, session_prefs)

        # As credenciais saem do pacote por padrão; com `include_secrets` elas
        # voltam, mas dentro de um envelope cifrado (doc 29 §29.4.2).
        secrets = profile_service.extract_secrets(profile)
        if request.include_secrets:
            profile["secrets"] = encrypt_payload(secrets, request.export_password or "")
        return profile
    except SecretBoxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"[Profile] Erro ao exportar perfil completo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Falha ao exportar o perfil completo.") from e


@router.post("/import", response_model=ProfileImportResponse)
def import_full_profile(
    profile_data: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Restaura um perfil completo de sessão e workspace.
    Sincroniza projetos, protocolos, artigos, extrações, chaves e preferências.
    """
    try:
        if not isinstance(profile_data, dict):
            raise ValueError("O conteúdo do perfil deve ser um objeto JSON válido.")

        # Aceitar tanto envelope { "profile_data": { ... } } quanto { "schema_version": ... }
        data = profile_data.get("profile_data", profile_data)

        # Credenciais cifradas no pacote são reabertas com a senha informada e
        # devolvidas ao formato que o serviço já sabe restaurar.
        secrets = data.get("secrets")
        if is_envelope(secrets):
            password = profile_data.get("export_password") or data.get("export_password") or ""
            data = profile_service.restore_secrets(dict(data), decrypt_envelope(secrets, password))

        return profile_service.import_profile(db, data)
    except SecretBoxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"[Profile] Erro ao restaurar perfil completo: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Falha ao restaurar o perfil. Confira o arquivo e a senha.") from e
