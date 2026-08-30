"""Serviço de Consolidação de Triagem (Doc 43 §43.8).

Único ponto do sistema autorizado a derivar e gravar:
- `papers.screening_status`
- `papers.decision` (P1 — a verdade consumida pelo funil e relatórios)
- `papers.observations` (quando consolidada)
- `paper_criteria` (avaliações consolidadas de critérios)
"""

import json
from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy.orm import Session

from app.domain.collaboration import PoliticaDeColaboracao
from app.infrastructure.persistence.models import (
    PaperModel,
    PaperScreeningModel,
    PaperCriterionModel,
    utcnow,
)


def _safe_dt(dt: datetime | None) -> datetime:
    """Normaliza datetime para UTC com timezone para ordenação segura."""
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def consolidar(db: Session, paper: PaperModel, politica: PoliticaDeColaboracao) -> None:
    """
    Aplica a máquina de estados de consolidação de triagem sobre um estudo (§43.8.1).
    """
    # Coleta todos os julgamentos válidos (com decisão preenchida diferente de 'Pendente')
    screenings = [s for s in (paper.screenings or []) if s.decision and s.decision != "Pendente"]

    # Se status for 'legado' e nenhum novo julgamento foi feito, mantém 'legado' (P5)
    if paper.screening_status == "legado" and len(screenings) == 0:
        return

    n_required = max(1, politica.revisores_por_estudo)

    if n_required == 1:
        # Modalidade individual ou colaborativa com 1 parecer por estudo
        if len(screenings) == 0:
            paper.screening_status = "aguardando"
            paper.decision = "Pendente"
            all_screenings = paper.screenings or []
            if all_screenings:
                _sincronizar_criterios_consolidados(db, paper, all_screenings, modo="direto")
        else:
            # Em N == 1 a última escrita vence (§43.8.2)
            latest = sorted(
                screenings,
                key=lambda s: _safe_dt(s.updated_at or s.decided_at),
                reverse=True,
            )[0]
            paper.screening_status = "consenso"
            paper.decision = latest.decision
            paper.observations = latest.observations or ""
            if latest.ai_confidence is not None:
                paper.ai_confidence = latest.ai_confidence

            _sincronizar_criterios_consolidados(db, paper, [latest], modo="direto")

    else:
        # Modalidade cega por pares ou N revisores (N >= 2)
        if len(screenings) == 0:
            paper.screening_status = "aguardando"
            paper.decision = "Pendente"
            paper.conflict_resolved_by_user_id = None
            paper.conflict_resolved_at = None
        elif len(screenings) < n_required:
            paper.screening_status = "parcial"
            paper.decision = "Pendente"
            paper.conflict_resolved_by_user_id = None
            paper.conflict_resolved_at = None
        else:
            # Temos N ou mais revisores com decisão tomada
            decisions = {s.decision for s in screenings}
            if len(decisions) == 1:
                # Todos os revisores concordam estritamente (ex: ambos 'Incluído' ou ambos 'Excluído')
                common_decision = list(decisions)[0]
                paper.screening_status = "consenso"
                paper.decision = common_decision
                paper.conflict_resolved_by_user_id = None
                paper.conflict_resolved_at = None

                # Observações consolidadas
                obs_list = [
                    s.observations.strip()
                    for s in screenings
                    if s.observations and s.observations.strip()
                ]
                paper.observations = "\n\n".join(obs_list)

                # Média de confiança de assistência
                confidences = [s.ai_confidence for s in screenings if s.ai_confidence is not None]
                if confidences:
                    paper.ai_confidence = sum(confidences) / len(confidences)

                # Critérios consolidados: união dos critérios marcados pelos revisores concordantes (§43.8.2)
                _sincronizar_criterios_consolidados(db, paper, screenings, modo="uniao")
            else:
                # Decisões divergentes (Conflito de triagem)
                # Se já havia sido resolvido e o conflito não foi modificado
                if paper.screening_status == "resolvido" and paper.conflict_resolved_by_user_id:
                    pass
                else:
                    paper.screening_status = "conflito"
                    paper.decision = "Pendente"

    paper.updated_at = utcnow()


def _sincronizar_criterios_consolidados(
    db: Session,
    paper: PaperModel,
    active_screenings: Sequence[PaperScreeningModel],
    modo: str = "direto",
) -> None:
    """Atualiza a tabela `paper_criteria` com base nas avaliações dos julgamentos ativos."""
    merged_criteria: dict[str, bool] = {}

    for s in active_screenings:
        if not s.criteria_evaluations:
            continue
        try:
            parsed = (
                json.loads(s.criteria_evaluations)
                if isinstance(s.criteria_evaluations, str)
                else s.criteria_evaluations
            )
            if isinstance(parsed, dict):
                for c_id, val in parsed.items():
                    bool_val = bool(val)
                    if modo == "uniao":
                        merged_criteria[c_id] = merged_criteria.get(c_id, False) or bool_val
                    else:
                        merged_criteria[c_id] = bool_val
        except (json.JSONDecodeError, TypeError):
            pass

    for crit_id, val in merged_criteria.items():
        eval_record = (
            db.query(PaperCriterionModel)
            .filter(
                PaperCriterionModel.paper_id == paper.id,
                PaperCriterionModel.criterion_id == crit_id,
            )
            .first()
        )
        if eval_record:
            eval_record.value = val
        else:
            db.add(
                PaperCriterionModel(
                    paper_id=paper.id,
                    criterion_id=crit_id,
                    value=val,
                )
            )
