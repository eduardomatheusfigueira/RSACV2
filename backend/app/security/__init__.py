#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Camada de Segurança.

Reúne o que protege credenciais e o perímetro da aplicação. Ver
`planejamento/29_ESPECIFICACAO_SEGURANCA.md` para o documento normativo.
"""

from app.security.masking import mask_secret, mask_secret_list

__all__ = ["mask_secret", "mask_secret_list"]
