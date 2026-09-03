#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Transmissão pelo canal: uma conexão morta não pode travar quem produz.

Escrito depois de a triagem em lote parar no primeiro estudo — anunciava o
início e nunca mais emitia nada, sem erro no log. A causa não estava na
triagem: estava aqui. `broadcast` esperava indefinidamente por cada socket, em
série, e um cliente que sumiu sem fechar a conexão segurava o lote inteiro.

A triagem individual continuava funcionando porque responde pelo próprio HTTP
e não passa por aqui. Foi essa assimetria que escondeu a causa por tanto tempo.
"""

import asyncio
import time

import pytest

from app.services.harvesting_service import ConnectionManager


class SocketQueTrava:
    """Aceita o envio e nunca conclui — o cliente que sumiu sem fechar."""

    def __init__(self):
        self.enviados = 0

    async def send_json(self, mensagem):
        self.enviados += 1
        await asyncio.sleep(3600)

    async def close(self, code=1000):
        return None


class SocketSaudavel:
    def __init__(self):
        self.recebidos = []

    async def send_json(self, mensagem):
        self.recebidos.append(mensagem)

    async def close(self, code=1000):
        return None


class SocketQueLevanta:
    async def send_json(self, mensagem):
        raise ConnectionResetError("conexão encerrada pelo par")

    async def close(self, code=1000):
        return None


@pytest.fixture
def gerente(monkeypatch):
    ger = ConnectionManager()
    # O prazo real é de segundos; no teste basta ser curto.
    monkeypatch.setattr(ConnectionManager, "TIMEOUT_DE_ENVIO", 0.05)
    return ger


@pytest.mark.anyio
async def test_conexao_travada_nao_segura_a_transmissao(gerente):
    """O caso que parou a triagem em lote."""
    travado = SocketQueTrava()
    gerente.active_connections["proj"] = {travado}

    inicio = time.monotonic()
    await gerente.broadcast("proj", {"type": "batch_screening_item_start"})
    duracao = time.monotonic() - inicio

    assert duracao < 1.0, f"A transmissão ficou presa por {duracao:.1f}s."


@pytest.mark.anyio
async def test_conexao_travada_e_descartada(gerente):
    """Não basta não travar: a conexão morta precisa sair da lista.

    Sem o descarte, cada transmissão seguinte pagaria o prazo de novo — duas
    vezes por artigo, ao longo de um lote inteiro.
    """
    travado = SocketQueTrava()
    gerente.active_connections["proj"] = {travado}

    await gerente.broadcast("proj", {"type": "x"})

    assert "proj" not in gerente.active_connections, "A conexão morta continuou registrada."


@pytest.mark.anyio
async def test_conexao_boa_recebe_apesar_da_ruim(gerente):
    """Uma conexão ruim não pode calar as outras."""
    travado, bom = SocketQueTrava(), SocketSaudavel()
    gerente.active_connections["proj"] = {travado, bom}

    await gerente.broadcast("proj", {"type": "progresso", "n": 1})

    assert bom.recebidos == [{"type": "progresso", "n": 1}]
    assert gerente.active_connections["proj"] == {bom}


@pytest.mark.anyio
async def test_conexao_que_levanta_tambem_sai(gerente):
    """O caso que já funcionava antes continua funcionando."""
    ruim, bom = SocketQueLevanta(), SocketSaudavel()
    gerente.active_connections["proj"] = {ruim, bom}

    await gerente.broadcast("proj", {"type": "x"})

    assert gerente.active_connections["proj"] == {bom}


@pytest.mark.anyio
async def test_muitas_conexoes_nao_somam_o_prazo(gerente):
    """Cinco conexões travadas custam um prazo, não cinco.

    Em série, cinco abas esquecidas somariam cinco vezes o tempo limite a cada
    evento — e a triagem em lote emite dois eventos por artigo.
    """
    gerente.active_connections["proj"] = {SocketQueTrava() for _ in range(5)}

    inicio = time.monotonic()
    await gerente.broadcast("proj", {"type": "x"})
    duracao = time.monotonic() - inicio

    assert duracao < 0.5, f"Os prazos foram somados: {duracao:.2f}s."


@pytest.mark.anyio
async def test_projeto_sem_conexao_nao_faz_nada(gerente):
    await gerente.broadcast("inexistente", {"type": "x"})
