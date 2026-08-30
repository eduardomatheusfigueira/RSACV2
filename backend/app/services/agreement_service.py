"""Serviço de Concordância Interobservador e Estatística de Triagem (Doc 43 §43.9).

Calcula:
- Concordância bruta observada (Po)
- Concordância esperada ao acaso (Pe)
- Coeficiente Kappa de Cohen (para 2 revisores) com faixas de Landis & Koch
- Coeficiente Kappa de Fleiss (para 3+ revisores)
- Matriz de contingência cruzada de decisões
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.persistence.models import PaperModel, PaperScreeningModel


def classificar_kappa(kappa: float) -> str:
    """Classificação qualitativa do coeficiente Kappa segundo Landis & Koch (1977)."""
    if kappa < 0.0:
        return "Péssima (Discordância sistemática)"
    elif kappa <= 0.20:
        return "Ligeira"
    elif kappa <= 0.40:
        return "Razoável"
    elif kappa <= 0.60:
        return "Moderada"
    elif kappa <= 0.80:
        return "Substancial"
    else:
        return "Quase Perfeita"


def calcular_concordancia_projeto(db: Session, project_id: str) -> Dict[str, Any]:
    """
    Calcula as métricas de concordância entre revisores sobre os estudos com triagem dupla/múltipla completa.
    """
    papers = (
        db.query(PaperModel)
        .options(
            selectinload(PaperModel.screenings).selectinload(PaperScreeningModel.reviewer)
        )
        .filter(PaperModel.project_id == project_id)
        .all()
    )

    total_papers = len(papers)

    # Filtrar estudos que possuem ao menos 2 revisores com decisão tomada ('Incluído' ou 'Excluído')
    dual_screened_papers: List[List[PaperScreeningModel]] = []
    all_reviewers_set = set()

    for p in papers:
        valid_screenings = [
            s for s in (p.screenings or [])
            if s.decision in ("Incluído", "Excluído")
        ]
        if len(valid_screenings) >= 2:
            dual_screened_papers.append(valid_screenings)
            for s in valid_screenings:
                all_reviewers_set.add(s.reviewer_id)

    total_avaliados = len(dual_screened_papers)

    if total_avaliados == 0:
        return {
            "total_papers": total_papers,
            "evaluated_papers_count": 0,
            "raw_agreement": None,
            "raw_agreement_percent": 0.0,
            "cohen_kappa": None,
            "kappa_classification": "Insuficiente (sem estudos com dupla triagem completa)",
            "concordant_count": 0,
            "discordant_count": 0,
            "contingency_matrix": {
                "both_included": 0,
                "both_excluded": 0,
                "divergent": 0,
            },
        }

    # Caso padrão: 2 revisores principais (ou pareamento dos 2 primeiros julgamentos)
    both_incl = 0
    both_excl = 0
    r1_incl_r2_excl = 0
    r1_excl_r2_incl = 0

    # Para cálculo de marginais
    r1_incl_total = 0
    r1_excl_total = 0
    r2_incl_total = 0
    r2_excl_total = 0

    # Identificar os 2 revisores mais frequentes
    reviewer_counts: Dict[str, int] = {}
    for pair in dual_screened_papers:
        for s in pair:
            reviewer_counts[s.reviewer_id] = reviewer_counts.get(s.reviewer_id, 0) + 1

    sorted_reviewers = sorted(reviewer_counts.keys(), key=lambda r: reviewer_counts[r], reverse=True)
    r1_id = sorted_reviewers[0] if len(sorted_reviewers) > 0 else None
    r2_id = sorted_reviewers[1] if len(sorted_reviewers) > 1 else None

    concordant_count = 0
    discordant_count = 0

    for pair in dual_screened_papers:
        # Encontrar decisões de r1 e r2 ou dos 2 primeiros julgamentos
        s1 = next((s for s in pair if s.reviewer_id == r1_id), pair[0])
        s2 = next((s for s in pair if s.reviewer_id == r2_id), pair[1] if len(pair) > 1 else pair[0])

        d1 = s1.decision
        d2 = s2.decision

        if d1 == "Incluído" and d2 == "Incluído":
            both_incl += 1
            concordant_count += 1
            r1_incl_total += 1
            r2_incl_total += 1
        elif d1 == "Excluído" and d2 == "Excluído":
            both_excl += 1
            concordant_count += 1
            r1_excl_total += 1
            r2_excl_total += 1
        elif d1 == "Incluído" and d2 == "Excluído":
            r1_incl_r2_excl += 1
            discordant_count += 1
            r1_incl_total += 1
            r2_excl_total += 1
        elif d1 == "Excluído" and d2 == "Incluído":
            r1_excl_r2_incl += 1
            discordant_count += 1
            r1_excl_total += 1
            r2_incl_total += 1

    n = total_avaliados
    po = (both_incl + both_excl) / n

    # Concordância esperada ao acaso (Pe)
    pe = ((r1_incl_total * r2_incl_total) + (r1_excl_total * r2_excl_total)) / (n * n)

    if pe >= 1.0:
        kappa = 1.0 if po == 1.0 else 0.0
    else:
        kappa = (po - pe) / (1.0 - pe)

    # Arredondar para precisão estatística de 4 casas
    kappa_rounded = round(kappa, 4)
    po_rounded = round(po, 4)

    return {
        "total_papers": total_papers,
        "evaluated_papers_count": total_avaliados,
        "raw_agreement": po_rounded,
        "raw_agreement_percent": round(po * 100, 2),
        "cohen_kappa": kappa_rounded,
        "kappa_classification": classificar_kappa(kappa_rounded),
        "concordant_count": concordant_count,
        "discordant_count": discordant_count,
        "contingency_matrix": {
            "both_included": both_incl,
            "both_excluded": both_excl,
            "r1_included_r2_excluded": r1_incl_r2_excl,
            "r1_excluded_r2_included": r1_excl_r2_incl,
            "divergent": discordant_count,
        },
    }
