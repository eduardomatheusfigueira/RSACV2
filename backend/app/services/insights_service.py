#!/usr/bin/env python

"""
Revsist — Agregação de B.I. e Bibliometria (doc 31, doc 32).

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

from app.domain.afiliacao import filtrar_afiliacoes
from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    AuditLogModel,
    BibAuthorshipModel,
    BibSnapshotModel,
    CriterionModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    PaperCriterionModel,
    PaperModel,
    PaperSourceModel,
    ProtocolModel,
)
from app.services.export_service import ExportService
from app.services.bibliometria.instantaneo import (
    ler_manifesto,
    proveniencia as montar_proveniencia,
)

# Ações de `AuditLogModel` que representam uma decisão de triagem tomada —
# manual (`app/api/v1/papers.py`) ou assistida (`app/services/screening_service.py`).
# Outras ações (ex.: importação de perfil sem log completo) ficam de fora.
_ACOES_DE_DECISAO = ("ai_screening", "decision_changed")

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


def _impacto(item: dict) -> int:
    """
    Quantos artigos este critério tirou do caminho — a leitura que
    "atende"/"não atende" sozinho não dá (doc 33 Fase 2).

    Para um critério de EXCLUSÃO, atender é o que exclui (`met_count`). Para
    um critério de INCLUSÃO, é o contrário: não atender é o que barra
    (`not_met_count`). Inverter os dois contaria o critério mais permissivo
    como o mais decisivo.
    """
    return item["met_count"] if item["is_exclusion"] else item["not_met_count"]


def _criteria_funnel(db: Session, project_id: str) -> list[dict]:
    """
    Para cada critério do protocolo, quantos artigos avaliados o atendem —
    o gráfico que explica por que a amostra final tem o tamanho que tem
    (doc 32 §6.1). Não é afetado pelos filtros: é sempre sobre a avaliação
    completa, não sobre um recorte da amostra final.

    Ordenado por impacto (doc 33 Fase 2): o critério que mais tirou artigo do
    caminho aparece primeiro — é a ordem que responde à pergunta do bloco,
    não a ordem de cadastro no protocolo.
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
    funil.sort(key=_impacto, reverse=True)
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


# Largura dos intervalos de confiança do gráfico de distribuição — décimos
# fixos, não quantis: o eixo precisa significar a mesma coisa entre projetos.
_LARGURA_FAIXA_CONFIANCA = 0.1


def _faixa_de_confianca(valor: float) -> str:
    valor = min(max(valor, 0.0), 1.0)
    inicio = min(int(valor / _LARGURA_FAIXA_CONFIANCA), 9) * _LARGURA_FAIXA_CONFIANCA
    fim = inicio + _LARGURA_FAIXA_CONFIANCA
    return f"{inicio:.1f}–{fim:.1f}"


def _proveniencia_ia(db: Session, project_id: str) -> dict:
    """
    Processo e proveniência de IA (doc 32 §6.5, doc 33 Fase 3): quem decidiu,
    quanto veio de IA, e com que confiabilidade. Agregado de processo, como o
    funil PRISMA — não é afetado pelos filtros de conteúdo, porque descreve o
    trabalho de triagem em si, não a amostra final.
    """
    eventos = (
        db.query(AuditLogModel.username, AuditLogModel.source, AuditLogModel.action)
        .join(PaperModel, PaperModel.id == AuditLogModel.paper_id)
        .filter(PaperModel.project_id == project_id, AuditLogModel.action.in_(_ACOES_DE_DECISAO))
        .all()
    )

    throughput: Counter = Counter()
    origem: Counter = Counter()
    for username, source, _action in eventos:
        throughput[username or "Desconhecido"] += 1
        # Screening assistido grava `source="ai:<provedor>"` (doc 29 §29.9.3);
        # a troca manual grava `source="manual"`.
        origem["Assistida por IA" if source.startswith("ai:") else "Manual"] += 1

    throughput_por_usuario = [
        {"name": nome, "count": total}
        for nome, total in sorted(throughput.items(), key=lambda kv: kv[1], reverse=True)
    ]

    eventos_ia = (
        db.query(AuditLogModel.ai_response_valid)
        .join(PaperModel, PaperModel.id == AuditLogModel.paper_id)
        .filter(PaperModel.project_id == project_id, AuditLogModel.action == "ai_screening")
        .all()
    )
    total_ia = len(eventos_ia)
    invalidas = sum(1 for (valida,) in eventos_ia if not valida)
    taxa_resposta_invalida = (invalidas / total_ia) if total_ia else None

    confiancas = [
        valor for (valor,) in db.query(PaperModel.ai_confidence).filter(
            PaperModel.project_id == project_id,
            PaperModel.ai_confidence.is_not(None),
            or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)),  # noqa: E712
        ).all()
    ]
    distribuicao_confianca: Counter = Counter(_faixa_de_confianca(c) for c in confiancas)
    distribuicao_confianca_ia = [
        {"name": faixa, "count": distribuicao_confianca[faixa]}
        for faixa in sorted(distribuicao_confianca, key=lambda f: float(f.split("–")[0]))
    ]

    return {
        "throughput_by_user": throughput_por_usuario,
        "decisions_by_origin": dict(origem),
        "ai_invalid_response_rate": taxa_resposta_invalida,
        "ai_confidence_distribution": distribuicao_confianca_ia,
    }


def get_project_insights(
    db: Session,
    project_id: str,
    *,
    decision: str = Decision.INCLUDED.value,
    source: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    snapshot_id: str | None = None,
) -> dict:
    """Monta o payload completo da aba de Indicadores (doc 32 §3.1).

    Com `snapshot_id`, os agregados de conteúdo passam a descrever o corpus
    congelado, e não o acervo de agora — é o que torna o número reproduzível
    (doc 48 §3). Os agregados de processo seguem descrevendo o projeto
    inteiro: a pergunta "como o funil chegou a esse tamanho" é sobre o
    projeto, não sobre um recorte dele.
    """
    conteudo = _base_query_conteudo(
        db, project_id, decision=decision, source=source, year_from=year_from, year_to=year_to
    ).all()

    proveniencia = None
    if snapshot_id:
        instantaneo = (
            db.query(BibSnapshotModel)
            .filter(
                BibSnapshotModel.id == snapshot_id,
                BibSnapshotModel.project_id == project_id,
            )
            .first()
        )
        if instantaneo is not None:
            do_instantaneo = set(ler_manifesto(instantaneo.manifest))
            conteudo = [p for p in conteudo if p.id in do_instantaneo]
            proveniencia = montar_proveniencia(instantaneo)

    # Se houver afiliações enriquecidas em bib_authorships (doc 48 §4.3, fecha B-01):
    pids_conteudo = [p.id for p in conteudo]
    authorships_enriquecidas = (
        db.query(BibAuthorshipModel.institution_name)
        .filter(
            BibAuthorshipModel.paper_id.in_(pids_conteudo),
            BibAuthorshipModel.institution_name != "",
            BibAuthorshipModel.institution_name.isnot(None),
        )
        .all()
        if pids_conteudo
        else []
    )
    if authorships_enriquecidas:
        afiliacoes = [inst for (inst,) in authorships_enriquecidas if inst]
    else:
        afiliacoes = filtrar_afiliacoes([p.institution for p in conteudo])

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
        # O campo `institution` traz o nome do COLETOR em 99,7% dos registros
        # (doc 47 §B-01). O ranking lê primariamente `bib_authorships` (onde
        # a instituição é resolvida por ROR) e, na sua ausência, o que sobrevive
        # ao filtro — sempre acompanhado da cobertura.
        "top_institutions": _ranking(afiliacoes),
        "institutions_coverage": {
            "with_affiliation": len(afiliacoes),
            "total": len(conteudo),
        },
        "pdf_health": _pdf_health(db, project_id, [p.id for p in conteudo]),
        "ai_provenance": _proveniencia_ia(db, project_id),
        # Sem instantâneo é `None`, e a tela diz que os números descrevem o
        # acervo de agora — que é verdade, e é o que faltava dizer.
        "provenance": proveniencia,
        "filters_applied": {
            "decision": decision,
            "source": source,
            "year_from": year_from,
            "year_to": year_to,
        },
    }
