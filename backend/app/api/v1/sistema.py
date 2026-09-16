#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Aba Sistema: visualizar e gerenciar os dados de uso e o ciclo do beta
(doc 52 §6.6).

Tudo aqui exige `require_owner`. As rotas de visualização nunca devolvem
identificador de pessoa ou de projeto, e toda célula que resulte de menos de
cinco pessoas sai suprimida — a regra mora em `services/uso/painel.py`. As
rotas de ação gravam o diário (`sistema_acoes`); as que tocam dados de uma
pessoa gravam também o ROPA.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.infrastructure.persistence.models import UserModel, as_utc
from app.schemas.uso import AcompanhamentoDeErroIn, MudancaDeEstadoIn, PedidoDeTitularIn
from app.security.dependencies import require_owner
from app.services import retencao, ropa_service
from app.services.uso import painel, portao

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sistema", tags=["sistema"], dependencies=[Depends(require_owner)])

PERIODOS_ACEITOS = ("7", "30", "90", "beta")
CONFIRMACAO_ENCERRAR = "ENCERRAR"
CONFIRMACAO_ELIMINAR = "APAGAR"
DIAS_AVISO_DE_DECISAO = 60


def _periodo(periodo: str) -> str:
    if periodo not in PERIODOS_ACEITOS:
        raise HTTPException(status_code=422, detail=f"Período inválido. Use: {', '.join(PERIODOS_ACEITOS)}.")
    return periodo


# ── Visualizar ────────────────────────────────────────────────────────


@router.get("/beta", summary="Ciclo do beta, estado da coleta e portão de ativação")
def ciclo_do_beta(db: Session = Depends(get_db)):
    estado = portao.estado_efetivo(db, usar_cache=False)
    linha = portao.obter_estado(db)
    alterado_por = db.get(UserModel, linha.alterado_por) if linha.alterado_por else None
    itens = portao.itens_do_portao(db)

    duracao = settings.beta_duracao_dias
    decorridos = max(0, min(duracao, duracao - portao.dias_restantes()))
    return {
        "inicio": settings.beta_inicio,
        "fim": settings.beta_fim,
        "duracao_dias": duracao,
        "dias_restantes": portao.dias_restantes(),
        "progresso": round(decorridos / duracao, 4) if duracao else 1.0,
        "aviso_de_decisao_em": settings.beta_fim - timedelta(days=DIAS_AVISO_DE_DECISAO),
        "descarte_final_em": settings.beta_fim + timedelta(days=retencao.DIAS_EVENTOS_APOS_FIM_DO_BETA),
        "estado": {
            "estado": estado,
            "alterado_em": as_utc(linha.alterado_em),
            "alterado_por": alterado_por.username if alterado_por else None,
            "motivo": linha.motivo,
            "transicoes": sorted(portao.TRANSICOES[estado]),
        },
        "portao": [
            {"chave": i.chave, "rotulo": i.rotulo, "ok": i.ok, "detalhe": i.detalhe, "bloqueante": i.bloqueante}
            for i in itens
        ],
        "pode_ativar": "ativa" in portao.TRANSICOES[estado] and all(i.ok for i in itens if i.bloqueante),
        "participacao": painel.participacao(db),
        "ultima_retencao_em": retencao.ultima_execucao_em,
    }


@router.get("/resumo", summary="Indicadores-chave do período")
def resumo(periodo: str = Query("30"), db: Session = Depends(get_db)):
    return painel.resumo(db, _periodo(periodo))


@router.get("/ia", summary="Consumo de IA agregado")
def consumo_de_ia(periodo: str = Query("30"), db: Session = Depends(get_db)):
    return painel.consumo_de_ia(db, _periodo(periodo))


@router.get("/erros", summary="Erros agrupados por impressão digital")
def erros(periodo: str = Query("30"), db: Session = Depends(get_db)):
    return {"itens": painel.erros_agrupados(db, _periodo(periodo))}


@router.get("/dados", summary="Inventário e retenção dos dados de uso")
def dados(db: Session = Depends(get_db)):
    return {"tabelas": painel.inventario(db), "ultima_retencao_em": retencao.ultima_execucao_em}


@router.get("/acoes", summary="Diário de ações administrativas")
def acoes(limite: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return {"itens": painel.diario(db, limite)}


# ── Gerenciar: coleta ─────────────────────────────────────────────────


def _mudar(db: Session, dono: UserModel, novo: str, acao: str, dados: MudancaDeEstadoIn) -> dict:
    anterior = portao.estado_efetivo(db, usar_cache=False)
    try:
        linha = portao.mudar_estado(db, novo, por=dono.id, motivo=dados.motivo)
    except portao.PortaoFechado as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O portão de ativação tem pendências: " + "; ".join(exc.pendencias) + ".",
        )
    except portao.TransicaoInvalida as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    painel.registrar_acao(
        db, acao, por=dono.id,
        parametros={"de": anterior, "para": novo, "motivo": dados.motivo.strip()},
        resultado=f"Coleta {novo}",
    )
    ropa_service.registrar(
        db,
        operation="usage_collection_changed",
        legal_basis="art7_IX_legitimo_interesse",
        purpose=f"Coleta de dados de uso do beta passou de '{anterior}' para '{novo}'",
        data_categories=["uso_da_plataforma", "diagnostico_tecnico", "consumo_de_ia"],
        user_id=dono.id,
    )
    logger.info("[Sistema] Coleta de uso: %s → %s por '%s'.", anterior, novo, dono.username)
    return {"estado": linha.estado, "alterado_em": as_utc(linha.alterado_em), "motivo": linha.motivo}


@router.post("/coleta/ativar", summary="Ativar a coleta de uso")
def ativar(dados: MudancaDeEstadoIn, db: Session = Depends(get_db), dono: UserModel = Depends(require_owner)):
    return _mudar(db, dono, "ativa", "coleta_ativar", dados)


@router.post("/coleta/pausar", summary="Pausar a coleta de uso")
def pausar(dados: MudancaDeEstadoIn, db: Session = Depends(get_db), dono: UserModel = Depends(require_owner)):
    return _mudar(db, dono, "pausada", "coleta_pausar", dados)


@router.post("/coleta/encerrar", summary="Encerrar o beta antes da data (irreversível)")
def encerrar(dados: MudancaDeEstadoIn, db: Session = Depends(get_db), dono: UserModel = Depends(require_owner)):
    if dados.confirmacao.strip() != CONFIRMACAO_ENCERRAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Para encerrar o beta, digite {CONFIRMACAO_ENCERRAR} na confirmação.",
        )
    return _mudar(db, dono, "encerrada", "coleta_encerrar", dados)


# ── Gerenciar: retenção e defeitos ────────────────────────────────────


@router.post("/dados/retencao", summary="Aplicar a retenção agora")
def aplicar_retencao(db: Session = Depends(get_db), dono: UserModel = Depends(require_owner)):
    resultado = retencao.aplicar_retencao(db)
    contagens = {
        "eventos_de_uso": resultado.eventos_de_uso,
        "ocorrencias_de_erro": resultado.ocorrencias_de_erro,
        "chamadas_de_ia": resultado.chamadas_de_ia,
        "acoes_do_sistema": resultado.acoes_do_sistema,
        "tentativas_de_login": resultado.tentativas_de_login,
        "pedidos_de_convite": resultado.pedidos_de_convite,
        "sessoes": resultado.sessoes,
        "estados_oauth": resultado.estados_oauth,
    }
    painel.registrar_acao(
        db, "retencao_aplicar", por=dono.id, parametros=contagens, resultado=f"{resultado.total} registro(s) eliminado(s)"
    )
    return {"eliminados": contagens, "total": resultado.total, "executada_em": retencao.ultima_execucao_em}


@router.patch("/erros/{impressao}", summary="Situação e nota de um defeito")
def acompanhar_erro(
    impressao: str,
    dados: AcompanhamentoDeErroIn,
    db: Session = Depends(get_db),
    dono: UserModel = Depends(require_owner),
):
    if len(impressao) != 64 or any(c not in "0123456789abcdef" for c in impressao):
        raise HTTPException(status_code=422, detail="Impressão digital inválida.")
    try:
        linha = painel.acompanhar_erro(db, impressao, dados.situacao, dados.nota, dados.versao)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    painel.registrar_acao(
        db, "erro_acompanhar", por=dono.id,
        parametros={"impressao": impressao[:12], "situacao": linha.situacao},
        resultado=f"Defeito marcado como {linha.situacao}",
    )
    return {
        "impressao": linha.impressao,
        "situacao": linha.situacao,
        "resolvido_na_versao": linha.resolvido_na_versao,
        "nota": linha.nota,
    }


# ── Gerenciar: pedidos de titular recebidos por e-mail ────────────────
#
# POST em todas, inclusive a consulta: o e-mail vai no corpo, e não na URL,
# para não parar em log de acesso do proxy nem no histórico do navegador. E
# o e-mail nunca é gravado no diário — só o fato de ter havido o pedido.


def _conta_do_pedido(db: Session, dados: PedidoDeTitularIn) -> UserModel:
    conta = painel.conta_por_email(db, dados.email)
    if conta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma conta com este e-mail.")
    return conta


@router.post("/titulares/consulta", summary="Contagens dos dados de uso de uma conta")
def consultar_titular(dados: PedidoDeTitularIn, db: Session = Depends(get_db), dono: UserModel = Depends(require_owner)):
    conta = _conta_do_pedido(db, dados)
    contagens = painel.contagens_da_conta(db, conta.id)
    painel.registrar_acao(db, "titular_consultar", por=dono.id, parametros=contagens, resultado="Contagens consultadas")
    return {"encontrada": True, "coleta_ativa": conta.uso_coleta_ativa, "contagens": contagens}


@router.post("/titulares/exportacao", summary="Exportar os dados de uso de uma conta, para enviar ao titular")
def exportar_titular(dados: PedidoDeTitularIn, db: Session = Depends(get_db), dono: UserModel = Depends(require_owner)):
    conta = _conta_do_pedido(db, dados)
    pacote = painel.exportar_uso_da_conta(db, conta.id)
    ropa_service.registrar(
        db,
        operation="usage_data_exported",
        legal_basis="art7_VI_exercicio_de_direitos",
        purpose="Exportação dos dados de uso do beta a pedido do titular, feita pelo controlador",
        data_categories=["uso_da_plataforma", "diagnostico_tecnico", "consumo_de_ia"],
        user_id=conta.id,
    )
    painel.registrar_acao(
        db, "titular_exportar", por=dono.id,
        parametros={k: len(v) for k, v in pacote.items()},
        resultado="Pacote gerado",
    )
    return pacote


@router.post("/titulares/eliminacao", summary="Apagar os dados de uso de uma conta")
def eliminar_titular(dados: PedidoDeTitularIn, db: Session = Depends(get_db), dono: UserModel = Depends(require_owner)):
    if dados.confirmacao.strip() != CONFIRMACAO_ELIMINAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Para apagar, digite {CONFIRMACAO_ELIMINAR} na confirmação.",
        )
    conta = _conta_do_pedido(db, dados)
    apagados = painel.apagar_uso_da_conta(db, conta.id)
    ropa_service.registrar(
        db,
        operation="usage_data_erased",
        legal_basis="art7_VI_exercicio_de_direitos",
        purpose="Eliminação dos dados de uso do beta a pedido do titular, feita pelo controlador",
        data_categories=["uso_da_plataforma", "diagnostico_tecnico", "consumo_de_ia"],
        user_id=conta.id,
    )
    painel.registrar_acao(db, "titular_eliminar", por=dono.id, parametros=apagados, resultado="Dados de uso apagados")
    return {"apagados": apagados}
