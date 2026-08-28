#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Exceções de Domínio."""


class RSACError(Exception):
    """Exceção base do Revsist."""
    pass


class NotFoundError(RSACError):
    """Recurso não encontrado."""
    def __init__(self, resource: str, resource_id: str):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} com ID '{resource_id}' não encontrado.")


class DuplicateError(RSACError):
    """Recurso já existe."""
    pass


class ValidationError(RSACError):
    """Erro de validação de domínio."""
    pass


class AIClientError(RSACError):
    """Erro na comunicação com provedor de IA."""
    pass


class HarvesterError(RSACError):
    """Erro durante a coleta de dados."""
    pass
