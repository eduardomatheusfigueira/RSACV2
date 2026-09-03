#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Acelerador adaptativo — sobe enquanto aceitam, desce quando recusam."""

import asyncio

import pytest

from app.services.acelerador import AceleradorAdaptativo


@pytest.mark.anyio
async def test_nunca_passa_do_limite_vigente():
    """A garantia básica: o número de vagas é respeitado."""
    acelerador = AceleradorAdaptativo(teto=8, pausa_inicial=0, inicio=3)
    em_voo = 0
    pico = 0

    async def tarefa():
        nonlocal em_voo, pico
        async with acelerador:
            em_voo += 1
            pico = max(pico, em_voo)
            await asyncio.sleep(0.01)
            em_voo -= 1

    await asyncio.gather(*(tarefa() for _ in range(20)))
    assert pico <= 3, f"Chegou a {pico} em paralelo com limite 3."


@pytest.mark.anyio
async def test_recusa_derruba_o_paralelismo_pela_metade():
    """Recuo brusco: descobrir de novo o limite custa mais que perder vagas."""
    acelerador = AceleradorAdaptativo(teto=8, pausa_inicial=1.0, inicio=8)

    acelerador.registrar_recusa()
    assert acelerador.limite_atual == 4
    acelerador.registrar_recusa()
    assert acelerador.limite_atual == 2
    acelerador.registrar_recusa()
    assert acelerador.limite_atual == 1
    acelerador.registrar_recusa()
    assert acelerador.limite_atual == 1, "Não pode zerar: o lote pararia."


@pytest.mark.anyio
async def test_recusa_aumenta_a_pausa_e_respeita_o_pedido_do_provedor():
    acelerador = AceleradorAdaptativo(teto=4, pausa_inicial=1.0)

    acelerador.registrar_recusa()
    assert acelerador.pausa >= 2.0

    acelerador.registrar_recusa(espera_pedida=15.0)
    assert acelerador.pausa == 15.0, "Ignorou o tempo que o provedor pediu."

    for _ in range(10):
        acelerador.registrar_recusa(espera_pedida=999)
    assert acelerador.pausa <= AceleradorAdaptativo.PAUSA_MAXIMA


@pytest.mark.anyio
async def test_sucessos_recuperam_primeiro_o_ritmo_e_depois_as_vagas():
    """Aliviar a pausa é a mudança mais barata de desfazer: vem antes."""
    acelerador = AceleradorAdaptativo(teto=4, pausa_inicial=2.0, inicio=1)
    acelerador.pausa = 4.0

    for _ in range(AceleradorAdaptativo.SUCESSOS_PARA_SUBIR):
        acelerador.registrar_sucesso()
    assert acelerador.pausa == 2.0
    assert acelerador.limite_atual == 1, "Abriu vaga antes de aliviar a pausa."

    acelerador.pausa = 0.0
    for _ in range(AceleradorAdaptativo.SUCESSOS_PARA_SUBIR):
        acelerador.registrar_sucesso()
    assert acelerador.limite_atual == 2


@pytest.mark.anyio
async def test_nunca_passa_do_teto_escolhido():
    """O teto é do pesquisador; o acelerador só se move abaixo dele."""
    acelerador = AceleradorAdaptativo(teto=3, pausa_inicial=0, inicio=3)
    for _ in range(100):
        acelerador.registrar_sucesso()
    assert acelerador.limite_atual == 3


@pytest.mark.anyio
async def test_uma_recusa_no_meio_nao_zera_o_progresso_anterior():
    """Sucessos seguidos são o gatilho; um tropeço reinicia a contagem."""
    acelerador = AceleradorAdaptativo(teto=4, pausa_inicial=0, inicio=1)

    for _ in range(AceleradorAdaptativo.SUCESSOS_PARA_SUBIR - 1):
        acelerador.registrar_sucesso()
    acelerador.registrar_recusa()
    acelerador.registrar_sucesso()

    assert acelerador.limite_atual == 1, "Subiu com a contagem já interrompida."


@pytest.mark.anyio
async def test_a_pausa_espaca_os_disparos():
    acelerador = AceleradorAdaptativo(teto=1, pausa_inicial=0.2)
    instantes = []

    async def tarefa():
        async with acelerador:
            instantes.append(asyncio.get_running_loop().time())

    for _ in range(3):
        await tarefa()

    intervalos = [b - a for a, b in zip(instantes, instantes[1:])]
    assert all(i >= 0.15 for i in intervalos), f"Disparos colados: {intervalos}"
