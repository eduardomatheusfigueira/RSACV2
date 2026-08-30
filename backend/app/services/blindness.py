"""Serviço de Cegueira de Triagem e Serialização Segura (Doc 43 §43.7).

P3 · A cegueira é do servidor.
Se o dado sai na resposta HTTP/WebSocket, a cegueira não existe.
Esta camada garante que nenhum julgamento individual de outro revisor
seja transmitido antes da consolidação por consenso ou resolução.
"""

import json
from typing import Optional, List
from app.domain.collaboration import PoliticaDeColaboracao
from app.domain.enums import Decision
from app.infrastructure.persistence.models import PaperModel, PaperScreeningModel
from app.schemas.paper import PaperResponse, PaperScreeningResponse


def _serialize_screening(s: PaperScreeningModel) -> PaperScreeningResponse:
    """Serializa um julgamento individual garantindo JSON de critérios estruturado."""
    crit_dict = {}
    if s.criteria_evaluations:
        try:
            parsed = (
                json.loads(s.criteria_evaluations)
                if isinstance(s.criteria_evaluations, str)
                else s.criteria_evaluations
            )
            if isinstance(parsed, dict):
                crit_dict = {str(k): bool(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, TypeError):
            crit_dict = {}

    username = s.reviewer.username if s.reviewer else None

    return PaperScreeningResponse(
        id=s.id,
        paper_id=s.paper_id,
        reviewer_id=s.reviewer_id,
        reviewer_username=username,
        decision=s.decision or "Pendente",
        observations=s.observations or "",
        criteria_evaluations=crit_dict,
        ai_confidence=s.ai_confidence,
        ai_assisted=bool(s.ai_assisted),
        decided_at=s.decided_at,
        updated_at=s.updated_at,
    )


def visao_do_revisor(
    paper: PaperModel,
    usuario_id: Optional[str],
    is_coordinator: bool,
    politica: PoliticaDeColaboracao,
) -> PaperResponse:
    """
    Serializa o artigo aplicando a política de cegueira no servidor (§43.7.1).
    """
    sources = [s.source_name for s in paper.sources] if paper.sources else []
    screenings_list = paper.screenings or []

    # Encontrar o julgamento do próprio usuário requisitante
    my_screening_model = next((s for s in screenings_list if s.reviewer_id == usuario_id), None)
    my_screening = _serialize_screening(my_screening_model) if my_screening_model else None

    # Contagem neutra de revisores que já concluíram o parecer (sem revelar decisões)
    completed_screenings = [
        s for s in screenings_list if s.decision and s.decision != "Pendente"
    ]
    reviewers_completed_count = len(completed_screenings)
    reviewers_required_count = max(1, politica.revisores_por_estudo)

    # Determinar se a cegueira está ativa para esta requisição
    # Se o modo cego está desligado -> sem cegueira
    # Se o modo cego está ligado:
    #   - Em 'consenso' ou 'resolvido': a decisão é pública para a equipe
    #   - Em 'aguardando', 'parcial', 'conflito':
    #       - Revisor comum: CEGO (vê apenas seus próprios dados e decisão Pendente)
    #       - Coordenador: vê completo se em 'conflito' (para resolver) ou 'resolvido'/'consenso'.
    is_blind = False
    if politica.triagem_cega:
        if paper.screening_status in ("consenso", "resolvido"):
            is_blind = False
        elif paper.screening_status == "conflito" and is_coordinator:
            is_blind = False
        else:
            is_blind = True

    if is_blind:
        # Modo cego ativo: NÃO vazar decisões, notas ou critérios de terceiros
        decision_val = Decision.PENDING
        observations_val = my_screening.observations if my_screening else ""
        criteria_val = my_screening.criteria_evaluations if my_screening else {}
        ai_conf_val = my_screening.ai_confidence if my_screening else None
        visible_screenings = [my_screening] if my_screening else []
    else:
        # Sem cegueira: devolve os dados consolidados e a lista de julgamentos
        dec_str = paper.decision or "Pendente"
        try:
            decision_val = Decision(dec_str)
        except ValueError:
            decision_val = Decision.PENDING

        observations_val = paper.observations or ""
        criteria_val = {
            c.criterion_id: c.value for c in (paper.criteria_evaluations or [])
        }
        ai_conf_val = paper.ai_confidence
        visible_screenings = [_serialize_screening(s) for s in screenings_list]

    resolver_username = (
        paper.conflict_resolver.username if paper.conflict_resolver else None
    )

    return PaperResponse(
        id=paper.id,
        project_id=paper.project_id,
        title=paper.title,
        title_normalized=paper.title_normalized or "",
        authors=paper.authors or "",
        year=paper.year or "",
        doi=paper.doi,
        abstract=paper.abstract or "",
        research_type=paper.research_type or "",
        institution=paper.institution or "",
        download_url=paper.download_url or "",
        decision=decision_val,
        observations=observations_val,
        ai_confidence=ai_conf_val,
        criteria_evaluations=criteria_val,
        screening_status=paper.screening_status or "aguardando",
        reviewers_completed_count=reviewers_completed_count,
        reviewers_required_count=reviewers_required_count,
        my_screening=my_screening,
        screenings=visible_screenings,
        conflict_resolved_by_user_id=paper.conflict_resolved_by_user_id,
        conflict_resolved_by_username=resolver_username,
        conflict_resolved_at=paper.conflict_resolved_at,
        pdf_path=paper.pdf_path,
        pdf_text_extracted=paper.pdf_text_extracted,
        pdf_status=paper.pdf_status or ("obtido" if paper.pdf_path else "ausente"),
        pdf_strategy=paper.pdf_strategy or "",
        pdf_resolved_url=paper.pdf_resolved_url or "",
        pdf_page_count=paper.pdf_page_count or 0,
        pdf_is_scanned=bool(paper.pdf_is_scanned),
        sources=sources,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
    )
