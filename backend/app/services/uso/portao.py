#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Portão da coleta de uso (doc 52 §6.4, princípios P5, P6 e P9).

Toda gravação de dado de uso passa por `motivo_de_bloqueio`. O cliente pode
estar desatualizado, adulterado ou simplesmente errado: quem decide se um
evento vira linha no banco é o servidor, na hora, contra cinco condições.

  1. Perfil `server`. A instalação de mesa não registra nada (P6).
  2. `RSAC_USO_COLETA_ATIVA`. O interruptor de implantação.
  3. A versão dos termos vigente é a que **declara** a coleta.
  4. O estado da coleta é `ativa` — o que a aba Sistema controla — e o beta
     não passou da data de fim (P9).
  5. A pessoa aceitou a versão vigente e, no Nível B, não se opôs.

O estado mora no banco para sobreviver a reinício, mas é lido a cada lote de
eventos; um cache de 30 s evita uma consulta por requisição sem atrasar de
forma perceptível uma pausa.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import (
    SistemaEstadoDaColetaModel,
    UserModel,
    as_utc,
    utcnow,
)

logger = logging.getLogger(__name__)

ESTADOS = ("aguardando", "ativa", "pausada", "encerrada")

# `encerrada` não tem saída (doc 52 §6.6.4): voltar a `ativa` seria uma
# prorrogação do beta disfarçada de botão.
TRANSICOES: dict[str, frozenset[str]] = {
    "aguardando": frozenset({"ativa", "encerrada"}),
    "ativa": frozenset({"pausada", "encerrada"}),
    "pausada": frozenset({"ativa", "encerrada"}),
    "encerrada": frozenset(),
}

# O Brasil não tem horário de verão desde 2019. Um deslocamento fixo evita
# depender do pacote `tzdata`, que o Windows não traz.
FUSO_BRASILIA = timezone(timedelta(hours=-3))

CACHE_SEGUNDOS = 30.0
_cache: tuple[str, float] | None = None

MOTIVO_FIM_DO_BETA = "Fim do beta na data configurada"


class TransicaoInvalida(ValueError):
    """Mudança de estado que a máquina de estados não permite."""


class PortaoFechado(ValueError):
    """Tentativa de ativar a coleta com item bloqueante do portão em aberto."""

    def __init__(self, pendencias: list[str]):
        super().__init__("; ".join(pendencias))
        self.pendencias = pendencias


def hoje(agora: Optional[datetime] = None) -> date:
    """O dia corrente em Brasília, que é o dia que o Aviso publica."""
    return (agora or datetime.now(timezone.utc)).astimezone(FUSO_BRASILIA).date()


def inicio_do_dia_em_utc(dia: date) -> datetime:
    """00:00 de Brasília de `dia`, em UTC."""
    return datetime(dia.year, dia.month, dia.day, tzinfo=FUSO_BRASILIA).astimezone(timezone.utc)


def dias_restantes(agora: Optional[datetime] = None) -> int:
    return max(0, (settings.beta_fim - hoje(agora)).days)


def beta_no_prazo(agora: Optional[datetime] = None) -> bool:
    return hoje(agora) < settings.beta_fim


def perfil_permite_coleta() -> bool:
    """
    Só o servidor publicado coleta (P6).

    Função própria, e não `settings.is_server_profile` inline, para que os
    testes simulem o perfil publicado sem trocar o perfil do aplicativo
    inteiro — o que mudaria CORS, cookies e documentação no meio do teste.
    """
    return settings.is_server_profile


def termos_declaram_a_coleta() -> bool:
    versao = settings.uso_versao_dos_termos.strip()
    return bool(versao) and versao == settings.terms_version


def invalidar_cache() -> None:
    global _cache
    _cache = None


def obter_estado(db: Session) -> SistemaEstadoDaColetaModel:
    """A linha única do estado; criada como `aguardando` na primeira leitura."""
    linha = db.get(SistemaEstadoDaColetaModel, "unico")
    if linha is None:
        linha = SistemaEstadoDaColetaModel(id="unico", estado="aguardando", motivo="")
        db.add(linha)
        db.commit()
        db.refresh(linha)
    return linha


def estado_efetivo(db: Session, agora: Optional[datetime] = None, *, usar_cache: bool = True) -> str:
    """
    O estado que vale agora.

    Passada a data de fim, o estado vira `encerrada` sozinho, na primeira
    leitura — sem depender de alguém lembrar de clicar.
    """
    global _cache
    if usar_cache and agora is None and _cache and time.monotonic() - _cache[1] < CACHE_SEGUNDOS:
        return _cache[0]

    linha = obter_estado(db)
    if linha.estado != "encerrada" and not beta_no_prazo(agora):
        linha.estado = "encerrada"
        linha.alterado_em = utcnow()
        linha.alterado_por = None
        linha.motivo = MOTIVO_FIM_DO_BETA
        db.commit()
        logger.info("[Uso] Beta encerrado pela data configurada (%s).", settings.beta_fim.isoformat())

    if agora is None:
        _cache = (linha.estado, time.monotonic())
    return linha.estado


def motivo_de_bloqueio(
    db: Session,
    usuario: Optional[UserModel],
    nivel: str,
    *,
    sinal_gpc: bool = False,
    agora: Optional[datetime] = None,
) -> Optional[str]:
    """
    `None` quando a gravação pode acontecer; senão, a categoria do bloqueio.

    `usuario` só pode ser `None` no Nível A — um erro na tela de entrada, antes
    de haver conta —, e nesse caso não há aceite a conferir.
    """
    if not perfil_permite_coleta():
        return "perfil"
    if not settings.uso_coleta_ativa:
        return "desligada_na_implantacao"
    if not termos_declaram_a_coleta():
        return "termos_nao_declaram"

    estado = estado_efetivo(db, agora)
    if estado != "ativa":
        return f"estado_{estado}"

    if usuario is None:
        return None if nivel == "A" else "sem_conta"
    if (usuario.terms_version or "") != settings.terms_version:
        return "termos_nao_aceitos"
    if nivel == "B":
        if not usuario.uso_coleta_ativa:
            return "oposicao"
        if sinal_gpc:
            return "gpc"
    return None


# ── Portão de ativação, ao vivo (doc 52 §6.6.2) ───────────────────────


@dataclass(frozen=True)
class ItemDoPortao:
    chave: str
    rotulo: str
    ok: bool
    detalhe: str
    bloqueante: bool = True


def itens_do_portao(db: Session, agora: Optional[datetime] = None) -> list[ItemDoPortao]:
    from app.services import retencao

    agora = agora or datetime.now(timezone.utc)

    ultima = retencao.ultima_execucao_em
    retencao_ok = ultima is not None and agora - as_utc(ultima) <= timedelta(hours=24)

    contas_ativas = db.query(UserModel).filter(UserModel.is_active == True).count()  # noqa: E712
    reaceitaram = (
        db.query(UserModel)
        .filter(
            UserModel.is_active == True,  # noqa: E712
            UserModel.terms_version == settings.terms_version,
        )
        .count()
    )

    return [
        ItemDoPortao(
            "perfil",
            "Servidor publicado (perfil server)",
            perfil_permite_coleta(),
            f"Perfil atual: {settings.deployment_profile.value}",
        ),
        ItemDoPortao(
            "implantacao",
            "Coleta liberada na implantação",
            settings.uso_coleta_ativa,
            "RSAC_USO_COLETA_ATIVA=true" if settings.uso_coleta_ativa else "Defina RSAC_USO_COLETA_ATIVA=true",
        ),
        ItemDoPortao(
            "termos",
            "Aviso e Termos publicados declarando a coleta",
            termos_declaram_a_coleta(),
            (
                f"Versão {settings.terms_version}"
                if termos_declaram_a_coleta()
                else "Publique o Aviso 2.1 e defina RSAC_USO_VERSAO_DOS_TERMOS com a versão vigente"
            ),
        ),
        ItemDoPortao(
            "prazo",
            "Beta dentro do prazo",
            beta_no_prazo(agora),
            f"Fim em {settings.beta_fim.strftime('%d/%m/%Y')}",
        ),
        ItemDoPortao(
            "retencao",
            "Retenção executada nas últimas 24 horas",
            retencao_ok,
            (
                as_utc(ultima).astimezone(FUSO_BRASILIA).strftime("Última: %d/%m/%Y %H:%M")
                if ultima
                else "Ainda não executada neste processo"
            ),
        ),
        ItemDoPortao(
            "reaceite",
            "Contas que aceitaram a versão vigente",
            contas_ativas > 0 and reaceitaram == contas_ativas,
            f"{reaceitaram} de {contas_ativas}",
            bloqueante=False,
        ),
    ]


def mudar_estado(
    db: Session,
    novo: str,
    *,
    por: Optional[str],
    motivo: str = "",
    agora: Optional[datetime] = None,
) -> SistemaEstadoDaColetaModel:
    """Aplica uma transição; não faz commit do diário — quem chama registra a ação."""
    if novo not in ESTADOS:
        raise TransicaoInvalida(f"Estado desconhecido: {novo!r}")

    atual = estado_efetivo(db, agora, usar_cache=False)
    if novo not in TRANSICOES[atual]:
        if atual == "encerrada":
            raise TransicaoInvalida(
                "O beta foi encerrado e não pode ser reaberto. Um novo ciclo exige "
                "nova data de início e nova versão do Aviso e dos Termos."
            )
        raise TransicaoInvalida(f"Não é possível passar de '{atual}' para '{novo}'.")

    if novo == "ativa":
        pendencias = [i.rotulo for i in itens_do_portao(db, agora) if i.bloqueante and not i.ok]
        if pendencias:
            raise PortaoFechado(pendencias)

    if novo in ("pausada", "encerrada") and not motivo.strip():
        raise TransicaoInvalida("Informe o motivo para pausar ou encerrar a coleta.")

    linha = obter_estado(db)
    linha.estado = novo
    linha.alterado_em = agora or utcnow()
    linha.alterado_por = por
    linha.motivo = motivo.strip()[:300]
    db.commit()
    db.refresh(linha)
    invalidar_cache()
    return linha
