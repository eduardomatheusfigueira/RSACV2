#!/usr/bin/env python

"""
RSAC V2 — Agregação de B.I. e Bibliometria (doc 31, doc 32).

Um único ponto de entrada, `get_project_insights`, monta tudo que a aba de
Indicadores mostra. Os agregados de processo (funil PRISMA, funil de
critérios, composição por decisão e por base) descrevem o projeto inteiro e
não são afetados pelos filtros de consulta — só os agregados de conteúdo
(rankings, distribuição temporal, saúde de PDF) respeitam `decision`,
`source`, `year_from` e `year_to` (doc 32 §3.2). A razão é que os primeiros
respondem "como o funil chegou a esse tamanho", pergunta que um recorte da
amostra final responderia mal.
"""

import re
from collections import Counter

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    CriterionModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    PaperCriterionModel,
    PaperModel,
    PaperSourceModel,
    ProtocolModel,
)
from app.services.export_service import ExportService

_ESPACOS = re.compile(r"\s+")


def _normalizar(texto: str) -> str:
    """Chave de agrupamento: trim + colapso de espaços + casefold (doc 32 §4)."""
    return _ESPACOS.sub(" ", (texto or "").strip()).casefold()


def _dividir_autores(campo: str) -> list[str]:
    """
    `"; "` é o separador usado por todos os harvesters (doc 32 §4.1). Vírgula
    NÃO é fallback seguro: o formato "Sobrenome, Inicial" — um único autor —
    já usa vírgula dentro do próprio nome, e dividir por ela fragmentaria
    "Silva, J." em dois autores fantasmas. Sem "; " no campo, o valor inteiro
    é tratado como um único autor.
    """
    bruto = (campo or "").strip()
    if not bruto:
        return []
    if "; " in bruto:
        return [p.strip() for p in bruto.split("; ") if p.strip()]
    return [bruto]


def _ranking(valores: list[str]) -> list[dict]:
    """
    Agrupa por chave normalizada, mas exibe a grafia mais frequente entre as
    variantes agrupadas — nunca a chave normalizada em si (doc 32 §4.2).
    """
    contagem_por_chave: Counter = Counter()
    grafias_por_chave: dict[str, Counter] = {}

    for valor in valores:
        valor = (valor or "").strip()
        if not valor:
            continue
        chave = _normalizar(valor)
        contagem_por_chave[chave] += 1
        grafias_por_chave.setdefault(chave, Counter())[valor] += 1

    itens = [
        {"name": grafias_por_chave[chave].most_common(1)[0][0], "count": total}
        for chave, total in contagem_por_chave.items()
    ]
    itens.sort(key=lambda item: item["count"], reverse=True)
    return itens


def _base_query_conteudo(
    db: Session,
    project_id: str,
    *,
    decision: str,
    source: str | None,
    year_from: int | None,
    year_to: int | None,
):
    """Consulta dos artigos que alimentam os agregados de conteúdo — os únicos
    que os filtros de query afetam (doc 32 §3.2)."""
    query = db.query(PaperModel).filter(
        PaperModel.project_id == project_id,
        PaperModel.decision == decision,
        or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)),  # noqa: E712
    )
    if source:
        query = query.join(PaperSourceModel).filter(PaperSourceModel.source_name == source)
    if year_from is not None:
        query = query.filter(PaperModel.year >= str(year_from))
    if year_to is not None:
        query = query.filter(PaperModel.year <= str(year_to))
    return query


def _criteria_funnel(db: Session, project_id: str) -> list[dict]:
    """
    Para cada critério do protocolo, quantos artigos avaliados o atendem —
    o gráfico que explica por que a amostra final tem o tamanho que tem
    (doc 32 §6.1). Não é afetado pelos filtros: é sempre sobre a avaliação
    completa, não sobre um recorte da amostra final.
    """
    criterios = (
        db.query(CriterionModel)
        .join(ProtocolModel)
        .filter(ProtocolModel.project_id == project_id)
        .order_by(CriterionModel.order)
        .all()
    )
    if not criterios:
        return []

    por_criterio: dict[str, dict[bool, int]] = {}
    rows = (
        db.query(
            PaperCriterionModel.criterion_id,
            PaperCriterionModel.value,
            func.count(PaperCriterionModel.id),
        )
        .join(PaperModel, PaperModel.id == PaperCriterionModel.paper_id)
        .filter(PaperModel.project_id == project_id)
        .group_by(PaperCriterionModel.criterion_id, PaperCriterionModel.value)
        .all()
    )
    for criterion_id, valor, total in rows:
        por_criterio.setdefault(criterion_id, {})[bool(valor)] = total

    funil = []
    for crit in criterios:
        contagem = por_criterio.get(crit.id, {})
        atendem = contagem.get(True, 0)
        nao_atendem = contagem.get(False, 0)
        funil.append({
            "criterion_id": crit.id,
            "text": crit.text,
            "is_exclusion": crit.is_exclusion,
            "evaluated_count": atendem + nao_atendem,
            "met_count": atendem,
            "not_met_count": nao_atendem,
        })
    return funil


def _composicao_por_decisao(db: Session, project_id: str) -> dict[str, int]:
    linhas = (
        db.query(PaperModel.decision, func.count(PaperModel.id))
        .filter(
            PaperModel.project_id == project_id,
            or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)),  # noqa: E712
        )
        .group_by(PaperModel.decision)
        .all()
    )
    return dict(linhas)


def _composicao_por_base(db: Session, project_id: str) -> list[dict]:
    """Volume por base, cruzado com inclusão — generaliza o `source_counts`
    de `/projects/{id}/stats` (doc 32 §6.2)."""
    encontrados = dict(
        db.query(PaperSourceModel.source_name, func.count(func.distinct(PaperSourceModel.paper_id)))
        .join(PaperModel, PaperModel.id == PaperSourceModel.paper_id)
        .filter(PaperModel.project_id == project_id)
        .group_by(PaperSourceModel.source_name)
        .all()
    )
    incluidos = dict(
        db.query(PaperSourceModel.source_name, func.count(func.distinct(PaperSourceModel.paper_id)))
        .join(PaperModel, PaperModel.id == PaperSourceModel.paper_id)
        .filter(
            PaperModel.project_id == project_id,
            PaperModel.decision == Decision.INCLUDED.value,
        )
        .group_by(PaperSourceModel.source_name)
        .all()
    )
    return [
        {
            "source_name": nome,
            "found_count": total,
            "included_count": incluidos.get(nome, 0),
        }
        for nome, total in sorted(encontrados.items(), key=lambda kv: kv[1], reverse=True)
    ]


def _pdf_health(db: Session, project_id: str, papers_ids: list[str]) -> dict:
    if not papers_ids:
        return {"by_status": {}, "scanned_ratio": None, "extraction_completeness": None}

    linhas = (
        db.query(PaperModel.pdf_status, func.count(PaperModel.id))
        .filter(PaperModel.id.in_(papers_ids))
        .group_by(PaperModel.pdf_status)
        .all()
    )
    by_status = dict(linhas)

    obtidos = sum(v for k, v in by_status.items() if k in ("obtido", "manual"))
    escaneados = (
        db.query(func.count(PaperModel.id))
        .filter(
            PaperModel.id.in_(papers_ids),
            PaperModel.pdf_status.in_(["obtido", "manual"]),
            PaperModel.pdf_is_scanned.is_(True),
        )
        .scalar()
    )
    scanned_ratio = (escaneados / obtidos) if obtidos else None

    # Completude de extração é sempre sobre os artigos Incluídos — não sobre
    # o recorte de `decision` do filtro, porque a extração só existe para o
    # que a revisão vai de fato sintetizar (doc 32 §6.4).
    incluidos_ids = [
        pid for (pid,) in db.query(PaperModel.id).filter(
            PaperModel.project_id == project_id,
            PaperModel.decision == Decision.INCLUDED.value,
            or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)),  # noqa: E712
        ).all()
    ]
    n_perguntas = (
        db.query(func.count(ExtractionQuestionModel.id))
        .join(ProtocolModel)
        .filter(ProtocolModel.project_id == project_id)
        .scalar()
    )
    extraction_completeness = None
    if incluidos_ids and n_perguntas:
        possiveis = len(incluidos_ids) * n_perguntas
        respondidas = (
            db.query(func.count(ExtractionAnswerModel.id))
            .filter(
                ExtractionAnswerModel.paper_id.in_(incluidos_ids),
                ExtractionAnswerModel.answer != "",
            )
            .scalar()
        )
        extraction_completeness = respondidas / possiveis if possiveis else None

    return {
        "by_status": by_status,
        "scanned_ratio": scanned_ratio,
        "extraction_completeness": extraction_completeness,
    }


def get_project_insights(
    db: Session,
    project_id: str,
    *,
    decision: str = Decision.INCLUDED.value,
    source: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    """Monta o payload completo da aba de Indicadores (doc 32 §3.1)."""
    conteudo = _base_query_conteudo(
        db, project_id, decision=decision, source=source, year_from=year_from, year_to=year_to
    ).all()

    by_year = Counter(p.year for p in conteudo if p.year)
    by_research_type = Counter(p.research_type for p in conteudo if p.research_type)

    return {
        "prisma": ExportService.get_prisma_flow_data(db, project_id),
        "criteria_funnel": _criteria_funnel(db, project_id),
        "composition_by_decision": _composicao_por_decisao(db, project_id),
        "composition_by_source": _composicao_por_base(db, project_id),
        "composition_by_year": [
            {"year": ano, "count": total} for ano, total in sorted(by_year.items())
        ],
        "composition_by_research_type": [
            {"name": tipo, "count": total}
            for tipo, total in sorted(by_research_type.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "top_journals": _ranking([p.journal for p in conteudo]),
        "top_authors": _ranking([nome for p in conteudo for nome in _dividir_autores(p.authors)]),
        "top_institutions": _ranking([p.institution for p in conteudo]),
        "pdf_health": _pdf_health(db, project_id, [p.id for p in conteudo]),
        "filters_applied": {
            "decision": decision,
            "source": source,
            "year_from": year_from,
            "year_to": year_to,
        },
    }
