#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Bilhete de canal — a credencial que abre um WebSocket.

Existe porque abrir um WebSocket é a única requisição em que o navegador não
deixa mandar cabeçalho. O token de sessão mora em `sessionStorage`, que é por
aba; o cookie é `SameSite=strict` e não viaja entre origens diferentes. Uma aba
duplicada servida pelo Vite cai fora dos dois — e o canal era recusado com 403,
em silêncio, enquanto a triagem seguia no servidor sem nada aparecer na tela.
"""

import time

import pytest

from app.security import bilhete_de_canal


@pytest.fixture(autouse=True)
def sem_bilhetes_pendurados():
    bilhete_de_canal._BILHETES.clear()
    yield
    bilhete_de_canal._BILHETES.clear()


def test_bilhete_emitido_resgata_o_usuario():
    b = bilhete_de_canal.emitir("user-1")
    assert bilhete_de_canal.resgatar(b) == "user-1"


def test_bilhete_serve_uma_vez_so():
    """Reapresentá-lo — do histórico, de um log de proxy — não abre nada."""
    b = bilhete_de_canal.emitir("user-1")
    assert bilhete_de_canal.resgatar(b) == "user-1"
    assert bilhete_de_canal.resgatar(b) is None


def test_bilhete_vencido_nao_vale(monkeypatch):
    b = bilhete_de_canal.emitir("user-1")

    avancado = time.monotonic() + bilhete_de_canal.VALIDADE_SEGUNDOS + 1
    monkeypatch.setattr(bilhete_de_canal.time, "monotonic", lambda: avancado)

    assert bilhete_de_canal.resgatar(b) is None


def test_bilhete_inventado_nao_vale():
    assert bilhete_de_canal.resgatar("qualquer-coisa") is None
    assert bilhete_de_canal.resgatar(None) is None
    assert bilhete_de_canal.resgatar("") is None


def test_bilhetes_de_usuarios_diferentes_nao_se_confundem():
    a = bilhete_de_canal.emitir("user-a")
    b = bilhete_de_canal.emitir("user-b")
    assert bilhete_de_canal.resgatar(a) == "user-a"
    assert bilhete_de_canal.resgatar(b) == "user-b"


def test_acumulo_de_bilhetes_tem_teto():
    """Um cliente em laço de reconexão não pode encher a memória do processo."""
    for i in range(bilhete_de_canal.LIMITE_DE_BILHETES + 50):
        bilhete_de_canal.emitir(f"user-{i}")
    assert len(bilhete_de_canal._BILHETES) <= bilhete_de_canal.LIMITE_DE_BILHETES


def test_bilhete_e_longo_o_bastante():
    """É credencial: precisa ser impossível de adivinhar."""
    b = bilhete_de_canal.emitir("user-1")
    assert len(b) >= 32
