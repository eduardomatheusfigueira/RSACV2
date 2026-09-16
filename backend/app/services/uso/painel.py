#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Agregados e gestão dos dados de uso, para a aba Sistema (doc 52 §6.6).

Regra que atravessa o módulo inteiro: **nenhuma resposta identifica uma
pessoa**. Todo número que resulta de menos de cinco pessoas sai como `None`,
com `suprimido=True`, e a supressão acontece aqui, no servidor — um componente
de tela que esquecesse de esconder a célula não tem como mostrar o que nunca
chegou a ele.

As exceções são as operações de pedido de titular, que por definição tratam de
uma pessoa: elas recebem o e-mail informado no pedido, devolvem só contagens e
deixam rastro no ROPA e no diário de ações.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.persistence.models import (
    SistemaAcaoModel,
    UserModel,
    UsoChamadaIAModel,
    UsoErroAcompanhamentoModel,
    UsoErroModel,
    UsoEventoModel,
    as_utc,
    utcnow,
)
from app.services import retencao

MINIMO_DE_PESSOAS = 5

ACOES = frozenset({
    "coleta_ativar",
    "coleta_pausar",
    "coleta_encerrar",
    "retencao_aplicar",
    "erro_acompanhar",
    "titular_consultar",
    "titular_exportar",
    "titular_eliminar",
})

SITUACOES_DE_ERRO = ("novo", "investigando", "resolvido", "ignorado")

PERIODOS = {"7": 7, "30": 30, "90": 90}


@dataclass(frozen=True)
class Agregado:
    valor: Optional[float]
    pessoas: Optional[int]
    suprimido: bool


def agregado(valor: Optional[float], pessoas: int) -> Agregado:
    """Zero pessoas não identifica ninguém; de uma a quatro, sim."""
    if 0 < pessoas < MINIMO_DE_PESSOAS:
        return Agregado(valor=None, pessoas=None, suprimido=True)
    return Agregado(valor=valor, pessoas=pessoas, suprimido=False)


def contagem_de_pessoas(pessoas: int) -> Agregado:
    return agregado(float(pessoas), pessoas)


def inicio_do_periodo(periodo: str, agora: Optional[datetime] = None) -> datetime:
    from app.services.uso.portao import inicio_do_dia_em_utc

    agora = agora or datetime.now(timezone.utc)
    if periodo == "beta":
        return inicio_do_dia_em_utc(settings.beta_inicio)
    return agora - timedelta(days=PERIODOS.get(periodo, 30))


def _json(texto: Optional[str]) -> dict:
    try:
        valor = json.loads(texto or "{}")
    except json.JSONDecodeError:
        return {}
    return valor if isinstance(valor, dict) else {}


# ── Visão geral ───────────────────────────────────────────────────────


def resumo(db: Session, periodo: str, agora: Optional[datetime] = None) -> dict:
    desde = inicio_do_periodo(periodo, agora)

    participantes = (
        db.query(func.count(func.distinct(UsoEventoModel.user_id)))
        .filter(UsoEventoModel.ocorrido_em >= desde)
        .scalar()
        or 0
    )

    fins = (
        db.query(UsoEventoModel.user_id, UsoEventoModel.propriedades)
        .filter(UsoEventoModel.nome == "sessao_uso.fim", UsoEventoModel.ocorrido_em >= desde)
        .all()
    )
    tempos = [
        _json(p).get("tempo_ativo_s")
        for _u, p in fins
        if isinstance(_json(p).get("tempo_ativo_s"), int)
    ]
    pessoas_com_sessao = len({u for u, _p in fins})
    tempo_mediano_min = round(statistics.median(tempos) / 60, 1) if tempos else None

    primeiras = (
        db.query(UsoErroModel.impressao, func.min(UsoErroModel.ocorrido_em))
        .group_by(UsoErroModel.impressao)
        .all()
    )
    erros_novos = sum(1 for _i, primeira in primeiras if primeira and as_utc(primeira) >= desde)
    atingidos = (
        db.query(func.count(func.distinct(UsoErroModel.user_id)))
        .filter(UsoErroModel.ocorrido_em >= desde, UsoErroModel.user_id.isnot(None))
        .scalar()
        or 0
    )

    tokens, pessoas_ia = (
        db.query(
            func.coalesce(func.sum(UsoChamadaIAModel.tokens_total), 0),
            func.count(func.distinct(UsoChamadaIAModel.user_id)),
        )
        .filter(UsoChamadaIAModel.ocorrido_em >= desde)
        .one()
    )

    return {
        "periodo": periodo,
        "desde": desde,
        "participantes_ativos": asdict(contagem_de_pessoas(participantes)),
        "tempo_ativo_mediano_min": asdict(agregado(tempo_mediano_min, pessoas_com_sessao)),
        "erros_novos": erros_novos,
        "pessoas_atingidas_por_erro": asdict(contagem_de_pessoas(atingidos)),
        "tokens": asdict(agregado(float(tokens or 0), int(pessoas_ia or 0))),
    }


def participacao(db: Session) -> dict:
    ativas = db.query(UserModel).filter(UserModel.is_active == True)  # noqa: E712
    total = ativas.count()
    desligadas = ativas.filter(UserModel.uso_coleta_ativa == False).count()  # noqa: E712
    return {
        "contas_ativas": total,
        "coleta_desligada": asdict(contagem_de_pessoas(desligadas)),
    }


# ── Consumo de IA ─────────────────────────────────────────────────────


def consumo_de_ia(db: Session, periodo: str, agora: Optional[datetime] = None) -> dict:
    desde = inicio_do_periodo(periodo, agora)
    base = db.query(UsoChamadaIAModel).filter(UsoChamadaIAModel.ocorrido_em >= desde)

    def grupos(*colunas) -> list[dict]:
        linhas = (
            base.with_entities(
                *colunas,
                func.count(UsoChamadaIAModel.id),
                func.coalesce(func.sum(UsoChamadaIAModel.tokens_total), 0),
                func.count(func.distinct(UsoChamadaIAModel.user_id)),
                func.avg(UsoChamadaIAModel.latencia_ms),
            )
            .group_by(*colunas)
            .all()
        )
        saida = []
        for linha in linhas:
            *chaves, chamadas, tokens, pessoas, latencia = linha
            protegido = agregado(float(tokens or 0), int(pessoas or 0))
            saida.append({
                "chaves": list(chaves),
                "chamadas": None if protegido.suprimido else int(chamadas),
                "tokens": protegido.valor,
                "latencia_media_ms": None if protegido.suprimido or latencia is None else round(float(latencia)),
                "suprimido": protegido.suprimido,
            })
        return sorted(saida, key=lambda g: -(g["tokens"] or 0))

    por_resultado = grupos(UsoChamadaIAModel.resultado)
    pessoas_total = base.with_entities(func.count(func.distinct(UsoChamadaIAModel.user_id))).scalar() or 0
    estimadas = base.filter(UsoChamadaIAModel.estimado == True).count()  # noqa: E712
    total = base.count()
    reserva = base.filter(
        UsoChamadaIAModel.resultado == "ok",
        UsoChamadaIAModel.modelo_respondeu != UsoChamadaIAModel.modelo_pedido,
    ).count()
    ok = base.filter(UsoChamadaIAModel.resultado == "ok").count()

    protegido = agregado(float(total), int(pessoas_total))
    return {
        "periodo": periodo,
        "total_de_chamadas": protegido.valor,
        "suprimido": protegido.suprimido,
        "por_provedor_e_modelo": grupos(UsoChamadaIAModel.provedor, UsoChamadaIAModel.modelo_respondeu),
        "por_operacao": grupos(UsoChamadaIAModel.operacao),
        "por_resultado": por_resultado,
        "porcentagem_estimada": None if protegido.suprimido or not total else round(100 * estimadas / total, 1),
        "porcentagem_reserva": None if protegido.suprimido or not ok else round(100 * reserva / ok, 1),
    }


# ── Erros ─────────────────────────────────────────────────────────────


def erros_agrupados(db: Session, periodo: str, agora: Optional[datetime] = None) -> list[dict]:
    desde = inicio_do_periodo(periodo, agora)
    linhas = (
        db.query(
            UsoErroModel.impressao,
            func.count(UsoErroModel.id),
            func.count(func.distinct(UsoErroModel.user_id)),
            func.min(UsoErroModel.ocorrido_em),
            func.max(UsoErroModel.ocorrido_em),
        )
        .filter(UsoErroModel.ocorrido_em >= desde)
        .group_by(UsoErroModel.impressao)
        .all()
    )
    acompanhamentos = {a.impressao: a for a in db.query(UsoErroAcompanhamentoModel).all()}

    saida = []
    for impressao, ocorrencias, pessoas, primeira, ultima in linhas:
        exemplo = (
            db.query(UsoErroModel)
            .filter(UsoErroModel.impressao == impressao)
            .order_by(UsoErroModel.ocorrido_em.desc())
            .first()
        )
        versoes = sorted({
            v for (v,) in db.query(UsoErroModel.versao_app)
            .filter(UsoErroModel.impressao == impressao, UsoErroModel.ocorrido_em >= desde)
            .distinct()
            .all()
            if v
        })
        acomp = acompanhamentos.get(impressao)
        situacao = acomp.situacao if acomp else "novo"
        # Resolvido que reaparece numa versão posterior à da correção volta a
        # ser novo, sem ninguém precisar notar (doc 52 §6.6.3).
        if acomp and situacao == "resolvido" and acomp.resolvido_na_versao and exemplo and exemplo.versao_app:
            if _versao_maior(exemplo.versao_app, acomp.resolvido_na_versao):
                situacao = "novo"

        pessoas_protegido = contagem_de_pessoas(int(pessoas or 0))
        saida.append({
            "impressao": impressao,
            "tipo": exemplo.tipo if exemplo else "",
            "mensagem": exemplo.mensagem if exemplo else "",
            "pilha": exemplo.pilha if exemplo else "",
            "origem": exemplo.origem if exemplo else "",
            "tela": exemplo.tela if exemplo else None,
            "rota": exemplo.rota if exemplo else None,
            "ocorrencias": int(ocorrencias),
            "pessoas": pessoas_protegido.valor,
            "pessoas_suprimido": pessoas_protegido.suprimido,
            "primeira_vez": as_utc(primeira),
            "ultima_vez": as_utc(ultima),
            "versoes": versoes,
            "situacao": situacao,
            "resolvido_na_versao": acomp.resolvido_na_versao if acomp else "",
            "nota": acomp.nota if acomp else "",
        })
    # Ordenado por pessoas atingidas, e não por ocorrências: um laço num único
    # navegador não pode passar à frente de um defeito que atinge todo mundo.
    return sorted(saida, key=lambda e: (-(e["pessoas"] or 0), -e["ocorrencias"]))


def _versao_maior(a: str, b: str) -> bool:
    def partes(v: str) -> tuple:
        return tuple(int(p) if p.isdigit() else 0 for p in v.split("."))

    return partes(a) > partes(b)


def acompanhar_erro(db: Session, impressao: str, situacao: str, nota: Optional[str], versao: Optional[str]) -> UsoErroAcompanhamentoModel:
    if situacao not in SITUACOES_DE_ERRO:
        raise ValueError(f"Situação inválida: {situacao!r}")
    linha = db.get(UsoErroAcompanhamentoModel, impressao)
    if linha is None:
        linha = UsoErroAcompanhamentoModel(impressao=impressao, situacao="novo", resolvido_na_versao="", nota="")
        db.add(linha)
    linha.situacao = situacao
    if nota is not None:
        linha.nota = nota.strip()[:2000]
    if situacao == "resolvido":
        linha.resolvido_na_versao = (versao or settings.app_version)[:20]
    elif situacao == "novo":
        linha.resolvido_na_versao = ""
    linha.atualizado_em = utcnow()
    db.commit()
    db.refresh(linha)
    return linha


# ── Inventário e retenção ─────────────────────────────────────────────


def inventario(db: Session, agora: Optional[datetime] = None) -> list[dict]:
    agora = agora or datetime.now(timezone.utc)

    def linha(chave: str, rotulo: str, modelo, coluna, prazo: str, vence_em) -> dict:
        total = db.query(func.count()).select_from(modelo).scalar() or 0
        mais_antigo = as_utc(db.query(func.min(coluna)).scalar())
        return {
            "chave": chave,
            "rotulo": rotulo,
            "linhas": int(total),
            "mais_antigo": mais_antigo,
            "prazo": prazo,
            "proximo_descarte": vence_em(mais_antigo) if mais_antigo else None,
        }

    def eventos_vencem(mais_antigo: datetime) -> datetime:
        from app.services.uso.portao import inicio_do_dia_em_utc

        final = inicio_do_dia_em_utc(settings.beta_fim + timedelta(days=retencao.DIAS_EVENTOS_APOS_FIM_DO_BETA))
        return min(mais_antigo + timedelta(days=retencao.DIAS_EVENTOS_DE_USO), final)

    return [
        linha(
            "eventos", "Eventos de uso", UsoEventoModel, UsoEventoModel.recebido_em,
            f"Até {retencao.DIAS_EVENTOS_DE_USO} dias, nunca além de 30 dias após o fim do beta",
            eventos_vencem,
        ),
        linha(
            "erros", "Ocorrências de erro", UsoErroModel, UsoErroModel.recebido_em,
            f"Até {retencao.DIAS_OCORRENCIAS_DE_ERRO} dias",
            lambda m: m + timedelta(days=retencao.DIAS_OCORRENCIAS_DE_ERRO),
        ),
        linha(
            "chamadas_ia", "Chamadas de IA", UsoChamadaIAModel, UsoChamadaIAModel.ocorrido_em,
            f"Até {retencao.DIAS_CHAMADAS_DE_IA // 30} meses",
            lambda m: m + timedelta(days=retencao.DIAS_CHAMADAS_DE_IA),
        ),
        linha(
            "acoes", "Diário de ações do sistema", SistemaAcaoModel, SistemaAcaoModel.executada_em,
            "5 anos",
            lambda m: m + timedelta(days=retencao.DIAS_DIARIO_DE_ACOES),
        ),
    ]


# ── Dados de uma conta (titular) ──────────────────────────────────────


def conta_por_email(db: Session, email: str) -> Optional[UserModel]:
    alvo = (email or "").strip().lower()
    if not alvo:
        return None
    return db.query(UserModel).filter(func.lower(UserModel.email) == alvo).first()


def contagens_da_conta(db: Session, user_id: str) -> dict:
    return {
        "eventos": db.query(UsoEventoModel).filter(UsoEventoModel.user_id == user_id).count(),
        "erros": db.query(UsoErroModel).filter(UsoErroModel.user_id == user_id).count(),
        "chamadas_ia": db.query(UsoChamadaIAModel).filter(UsoChamadaIAModel.user_id == user_id).count(),
    }


def exportar_uso_da_conta(db: Session, user_id: str) -> dict:
    """O pacote que o titular recebe: tudo sobre ele, sem o próprio identificador interno."""

    def data(v: Optional[datetime]) -> Optional[str]:
        return as_utc(v).isoformat() if v else None

    eventos = db.query(UsoEventoModel).filter(UsoEventoModel.user_id == user_id).order_by(UsoEventoModel.ocorrido_em).all()
    erros = db.query(UsoErroModel).filter(UsoErroModel.user_id == user_id).order_by(UsoErroModel.ocorrido_em).all()
    chamadas = (
        db.query(UsoChamadaIAModel)
        .filter(UsoChamadaIAModel.user_id == user_id)
        .order_by(UsoChamadaIAModel.ocorrido_em)
        .all()
    )
    return {
        "eventos_de_uso": [
            {"nome": e.nome, "tela": e.tela, "propriedades": _json(e.propriedades), "ocorrido_em": data(e.ocorrido_em)}
            for e in eventos
        ],
        "ocorrencias_de_erro": [
            {"tipo": e.tipo, "mensagem": e.mensagem, "tela": e.tela, "rota": e.rota, "ocorrido_em": data(e.ocorrido_em)}
            for e in erros
        ],
        "chamadas_de_ia": [
            {
                "operacao": c.operacao,
                "provedor": c.provedor,
                "modelo_pedido": c.modelo_pedido,
                "modelo_respondeu": c.modelo_respondeu,
                "resultado": c.resultado,
                "tokens_entrada": c.tokens_entrada,
                "tokens_saida": c.tokens_saida,
                "tokens_total": c.tokens_total,
                "estimado": c.estimado,
                "latencia_ms": c.latencia_ms,
                "ocorrido_em": data(c.ocorrido_em),
            }
            for c in chamadas
        ],
    }


def registros_legiveis_da_conta(db: Session, user_id: str, limite: int = 200) -> dict:
    """
    O que foi registrado sobre uma pessoa, em linguagem comum.

    É o "ver o que foi registrado" que o Aviso promete (§6.7, item 2). A
    tradução vem da `descricao_publica` do vocabulário — a mesma frase que o
    Aviso usa —, e não de um dicionário paralelo que envelheceria sozinho.
    """
    from app.services.uso import vocabulario

    catalogo = vocabulario.eventos()
    rotulos_de_tela = {
        "entrada": "Entrada",
        "inicio": "Início",
        "projetos": "Projetos",
        "projeto.protocolo": "Protocolo",
        "projeto.coleta": "Coleta",
        "projeto.triagem": "Triagem",
        "projeto.extracao": "Extração",
        "projeto.indicadores": "Indicadores",
        "projeto.exportacao": "Exportação",
        "projeto.equipe": "Equipe",
        "configuracoes": "Configurações",
    }

    eventos = (
        db.query(UsoEventoModel)
        .filter(UsoEventoModel.user_id == user_id)
        .order_by(UsoEventoModel.ocorrido_em.desc())
        .limit(limite)
        .all()
    )
    erros = (
        db.query(UsoErroModel)
        .filter(UsoErroModel.user_id == user_id)
        .order_by(UsoErroModel.ocorrido_em.desc())
        .limit(limite)
        .all()
    )

    def valor_legivel(chave: str, valor: object) -> str:
        """Segundos viram minutos, milissegundos viram segundos, booleano vira sim/não."""
        if isinstance(valor, bool):
            return "sim" if valor else "não"
        if chave.endswith("_s") and isinstance(valor, int):
            return "%d min" % round(valor / 60) if valor >= 60 else "%d s" % valor
        if chave.endswith("_ms") and isinstance(valor, int):
            return "%.1f s" % (valor / 1000)
        return str(valor)

    def rotulo_da_propriedade(chave: str) -> str:
        return {
            "tempo_ativo_s": "tempo ativo",
            "tempo_total_s": "tempo com a aba aberta",
            "telas_distintas": "telas visitadas",
            "duracao_ms": "duração",
            "alvo": "comando",
            "anterior": "tela anterior",
            "motivo": "motivo",
        }.get(chave, chave.replace("_", " "))

    def descrever(evento: UsoEventoModel) -> dict:
        spec = catalogo.get(evento.nome, {})
        descricao = spec.get("descricao_publica", evento.nome)
        partes = []
        if evento.tela:
            partes.append("tela %s" % rotulos_de_tela.get(evento.tela, evento.tela))
        for chave, valor in sorted(_json(evento.propriedades).items()):
            partes.append("%s: %s" % (rotulo_da_propriedade(chave), valor_legivel(chave, valor)))
        return {
            "ocorrido_em": as_utc(evento.ocorrido_em),
            "descricao": descricao,
            "detalhe": " · ".join(partes),
        }

    linhas_ia = (
        db.query(
            func.date(UsoChamadaIAModel.ocorrido_em),
            UsoChamadaIAModel.provedor,
            UsoChamadaIAModel.modelo_respondeu,
            UsoChamadaIAModel.operacao,
            func.count(UsoChamadaIAModel.id),
            func.coalesce(func.sum(UsoChamadaIAModel.tokens_total), 0),
        )
        .filter(UsoChamadaIAModel.user_id == user_id)
        .group_by(
            func.date(UsoChamadaIAModel.ocorrido_em),
            UsoChamadaIAModel.provedor,
            UsoChamadaIAModel.modelo_respondeu,
            UsoChamadaIAModel.operacao,
        )
        .order_by(func.date(UsoChamadaIAModel.ocorrido_em).desc())
        .all()
    )

    consumo = [
        {
            "dia": str(dia),
            "provedor": provedor,
            "modelo": modelo or "",
            "operacao": operacao,
            "chamadas": int(chamadas),
            "tokens": int(tokens or 0),
        }
        for dia, provedor, modelo, operacao, chamadas, tokens in linhas_ia
    ]

    return {
        "eventos": [descrever(e) for e in eventos],
        "erros": [
            {
                "ocorrido_em": as_utc(e.ocorrido_em),
                "descricao": "Erro registrado: %s" % e.tipo,
                "detalhe": e.mensagem or "",
            }
            for e in erros
        ],
        "consumo_de_ia": consumo,
        "tokens_total": sum(c["tokens"] for c in consumo),
        "contagens": contagens_da_conta(db, user_id),
    }


def apagar_uso_da_conta(db: Session, user_id: str, *, commit: bool = True) -> dict:
    apagados = {
        "eventos": db.query(UsoEventoModel).filter(UsoEventoModel.user_id == user_id).delete(synchronize_session=False),
        "erros": db.query(UsoErroModel).filter(UsoErroModel.user_id == user_id).delete(synchronize_session=False),
        "chamadas_ia": db.query(UsoChamadaIAModel)
        .filter(UsoChamadaIAModel.user_id == user_id)
        .delete(synchronize_session=False),
    }
    if commit:
        db.commit()
    return apagados


# ── Diário de ações ───────────────────────────────────────────────────


def registrar_acao(
    db: Session,
    acao: str,
    *,
    por: Optional[str],
    parametros: Optional[dict[str, Any]] = None,
    resultado: str = "",
) -> SistemaAcaoModel:
    if acao not in ACOES:
        raise ValueError(f"Ação desconhecida: {acao!r}")
    linha = SistemaAcaoModel(
        acao=acao,
        executada_por=por,
        parametros=json.dumps(parametros or {}, ensure_ascii=False, default=str),
        resultado=resultado[:300],
    )
    db.add(linha)
    db.commit()
    return linha


def diario(db: Session, limite: int = 50) -> list[dict]:
    linhas = (
        db.query(SistemaAcaoModel, UserModel.username)
        .outerjoin(UserModel, UserModel.id == SistemaAcaoModel.executada_por)
        .order_by(SistemaAcaoModel.executada_em.desc())
        .limit(max(1, min(limite, 200)))
        .all()
    )
    return [
        {
            "acao": a.acao,
            "executada_em": as_utc(a.executada_em),
            "executada_por": usuario or "conta removida",
            "parametros": _json(a.parametros),
            "resultado": a.resultado,
        }
        for a, usuario in linhas
    ]
