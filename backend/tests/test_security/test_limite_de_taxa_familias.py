#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Classificação das rotas no limitador de taxa.

Escrito depois de a janela da triagem em lote derrubar a si mesma: a consulta
de progresso, que roda a cada poucos segundos, era contada na cota de IA (20
por minuto) e não sobrava orçamento para a triagem. O erro que aparecia —
"muitas requisições em pouco tempo" — vinha do próprio aplicativo, e era
naturalmente lido como recusa do provedor.
"""

from app.security.middleware import LIMITES, _familia_da_rota

BASE = "/api/v1/projects/proj-1/screening/ai"


def test_consulta_de_progresso_nao_gasta_cota_de_ia():
    """Ler o andamento não chama provedor: não pode disputar a mesma cota."""
    assert _familia_da_rota(f"{BASE}/batch/status", "GET") == "geral"


def test_disparar_o_lote_continua_na_cota_de_ia():
    """O que de fato chama o provedor continua limitado com rigor."""
    assert _familia_da_rota(f"{BASE}/batch", "POST") == "ai"
    assert _familia_da_rota(f"{BASE}/single/paper-1", "POST") == "ai"
    assert _familia_da_rota("/api/v1/ai/suggest-protocol", "POST") == "ai"


def test_a_cota_de_acompanhamento_e_folgada_o_bastante():
    """A consulta roda a cada poucos segundos; o teto precisa comportar isso."""
    limite, janela = LIMITES["geral"]
    por_minuto = limite / janela * 60
    assert por_minuto >= 60, f"Apenas {por_minuto:.0f}/min para acompanhamento."


def test_login_continua_com_a_cota_mais_estreita():
    assert _familia_da_rota("/api/v1/auth/login", "POST") == "auth"
