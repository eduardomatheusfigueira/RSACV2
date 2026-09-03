#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Acelerador adaptativo da triagem em lote.

O paralelismo da triagem era um número que o pesquisador escolhia antes de
começar, e que ninguém tinha como acertar: o limite de requisições do provedor
depende do plano, do modelo, de quantas chaves estão cadastradas e da hora do
dia. Escolher alto derrubava o lote com recusas; escolher baixo desperdiçava
minutos de espera à toa. As duas experiências foram vividas neste projeto, uma
depois da outra.

A saída é não escolher. O acelerador começa cauteloso, **sobe enquanto o
provedor aceita e desce assim que ele recusa** — o mesmo princípio de aumento
gradual e recuo brusco que o controle de congestionamento de rede usa há
décadas, e pelo mesmo motivo: a capacidade real não é conhecida de antemão, só
é descoberta usando.

O que o pesquisador escolhe passa a ser o **teto** e o ritmo mínimo; onde o lote
se acomoda abaixo disso é medido, não adivinhado.
"""

import asyncio
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AceleradorAdaptativo:
    """Regula quantas triagens correm juntas e a que velocidade partem."""

    #: Sucessos consecutivos antes de tentar uma vaga a mais. Sobe devagar de
    #: propósito: recuperar de uma recusa custa mais do que a vaga extra rende.
    SUCESSOS_PARA_SUBIR = 5

    #: Piso do intervalo entre disparos, em segundos, quando tudo vai bem.
    PAUSA_MINIMA = 0.0

    #: Teto do intervalo quando o provedor está recusando.
    PAUSA_MAXIMA = 20.0

    def __init__(
        self,
        teto: int = 4,
        pausa_inicial: float = 1.0,
        inicio: Optional[int] = None,
        deve_parar: Optional[Callable[[], bool]] = None,
    ):
        self.teto = max(1, int(teto))
        # Começa na metade do teto: subir custa cinco sucessos, e partir do
        # teto significaria descobrir o limite pela recusa — exatamente o que
        # se quer evitar.
        self.limite_atual = max(1, min(self.teto, inicio if inicio else max(1, self.teto // 2)))
        self.pausa = max(0.0, float(pausa_inicial))
        self._pausa_base = self.pausa

        self._em_uso = 0
        self._sucessos_seguidos = 0
        self._condicao = asyncio.Condition()
        self._trava_do_ritmo = asyncio.Lock()
        self._proximo_disparo = 0.0
        # Enquanto a pausa cresce por recusas, as tarefas já enfileiradas ficam
        # dormindo. Se o lote foi abortado nesse meio-tempo, esperar os 20s até
        # o fim só atrasa o encerramento — e, com dezenas de tarefas na fila,
        # atrasa muito. Este gancho é o que permite acordar antes.
        self._deve_parar = deve_parar or (lambda: False)

    # ── Controle de vagas ──────────────────────────────────────────────

    async def __aenter__(self):
        async with self._condicao:
            await self._condicao.wait_for(lambda: self._em_uso < self.limite_atual)
            self._em_uso += 1
        await self._aguardar_a_vez()
        return self

    async def __aexit__(self, *args):
        async with self._condicao:
            self._em_uso -= 1
            self._condicao.notify_all()
        return False

    async def _aguardar_a_vez(self) -> None:
        """Espaça os disparos entre si, e não ao fim de cada estudo.

        O que interessa ao provedor é o intervalo entre as chamadas que ele
        recebe. Uma chamada que já demorou não precisa de espera adicional.
        """
        if self.pausa <= 0:
            return
        async with self._trava_do_ritmo:
            agora = asyncio.get_running_loop().time()
            espera = max(0.0, self._proximo_disparo - agora)
            self._proximo_disparo = max(agora, self._proximo_disparo) + self.pausa

        # Espera em fatias, para poder desistir se o lote for interrompido.
        while espera > 0:
            if self._deve_parar():
                return
            fatia = min(0.25, espera)
            await asyncio.sleep(fatia)
            espera -= fatia

    # ── Realimentação ──────────────────────────────────────────────────

    def registrar_sucesso(self) -> None:
        """O provedor respondeu: talvez caiba mais um."""
        self._sucessos_seguidos += 1
        if self._sucessos_seguidos < self.SUCESSOS_PARA_SUBIR:
            return
        self._sucessos_seguidos = 0

        # Aliviar a pausa antes de abrir vaga: é a mudança mais barata de
        # desfazer se o provedor reclamar em seguida.
        if self.pausa > self.PAUSA_MINIMA:
            self.pausa = max(self.PAUSA_MINIMA, self.pausa / 2)
            logger.info("[Acelerador] Pausa reduzida para %.1fs.", self.pausa)
        elif self.limite_atual < self.teto:
            self.limite_atual += 1
            logger.info("[Acelerador] Paralelismo elevado para %d.", self.limite_atual)

    def registrar_recusa(self, espera_pedida: float = 0.0) -> None:
        """O provedor recusou por limite: recuar, e recuar de verdade."""
        self._sucessos_seguidos = 0

        anterior = self.limite_atual
        self.limite_atual = max(1, self.limite_atual // 2)

        # A pausa dobra, ou assume o que o provedor pediu — o que for maior.
        nova = max(self._pausa_base, self.pausa * 2 if self.pausa > 0 else 1.0)
        self.pausa = min(self.PAUSA_MAXIMA, max(nova, espera_pedida))

        logger.warning(
            "[Acelerador] Recusa por limite: paralelismo %d -> %d, pausa %.1fs.",
            anterior, self.limite_atual, self.pausa,
        )

    # ── Leitura ────────────────────────────────────────────────────────

    @property
    def em_uso(self) -> int:
        return self._em_uso

    def situacao(self) -> dict:
        """Estado atual, para a tela mostrar onde o lote se acomodou."""
        return {
            "paralelismo": self.limite_atual,
            "teto": self.teto,
            "pausa": round(self.pausa, 1),
        }
