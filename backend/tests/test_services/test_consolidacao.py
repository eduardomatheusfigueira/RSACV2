"""Testes Unitários e de Integração da Máquina de Estados de Consolidação (Doc 43 §43.8)."""

import json
import pytest
from app.domain.collaboration import PoliticaDeColaboracao
from app.infrastructure.persistence.models import (
    PaperModel,
    PaperScreeningModel,
    PaperCriterionModel,
    CriterionModel,
    ProtocolModel,
    ProjectModel,
    UserModel,
    utcnow,
)
from app.services.consolidation_service import consolidar


def test_consolidacao_individual_ou_colaborativa_n1(db_session):
    """Em N==1 a última escrita vence e gera consenso imediatamente (§43.8.2)."""
    user = UserModel(username="u_n1", role="researcher")
    db_session.add(user)
    db_session.flush()

    proj = ProjectModel(title="Proj N1", owner_id=user.id)
    db_session.add(proj)
    db_session.flush()

    politica = PoliticaDeColaboracao(
        corpus_compartilhado=True,
        protocolo_coeditavel=True,
        revisores_por_estudo=1,
        triagem_cega=False,
        extracao_cega=False,
        resolucao_de_conflito="coordenador",
    )

    paper = PaperModel(project_id=proj.id, title="Paper N1", decision="Pendente", screening_status="aguardando")
    db_session.add(paper)
    db_session.flush()

    # 1. Sem julgamentos -> continua aguardando
    consolidar(db_session, paper, politica)
    assert paper.screening_status == "aguardando"
    assert paper.decision == "Pendente"

    # 2. Primeiro revisor inclui
    s1 = PaperScreeningModel(
        paper_id=paper.id,
        reviewer_id=user.id,
        decision="Incluído",
        observations="Nota 1",
        decided_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(s1)
    paper.screenings = [s1]
    consolidar(db_session, paper, politica)

    assert paper.screening_status == "consenso"
    assert paper.decision == "Incluído"
    assert paper.observations == "Nota 1"

    # 3. Segundo revisor edita para Excluído (colaborativa)
    user2 = UserModel(username="u_n1_b", role="researcher")
    db_session.add(user2)
    db_session.flush()

    s2 = PaperScreeningModel(
        paper_id=paper.id,
        reviewer_id=user2.id,
        decision="Excluído",
        observations="Nota 2",
        decided_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(s2)
    paper.screenings = [s1, s2]
    consolidar(db_session, paper, politica)

    assert paper.screening_status == "consenso"
    assert paper.decision == "Excluído"
    assert paper.observations == "Nota 2"


def test_consolidacao_duplo_cego_n2_consenso_e_conflito(db_session):
    """Em N==2: 1 voto=parcial, 2 votos concordantes=consenso, 2 votos divergentes=conflito."""
    user_a = UserModel(username="u_n2_a", role="researcher")
    user_b = UserModel(username="u_n2_b", role="researcher")
    db_session.add_all([user_a, user_b])
    db_session.flush()

    proj = ProjectModel(title="Proj N2", owner_id=user_a.id)
    db_session.add(proj)
    db_session.flush()

    politica = PoliticaDeColaboracao(
        corpus_compartilhado=True,
        protocolo_coeditavel=True,
        revisores_por_estudo=2,
        triagem_cega=True,
        extracao_cega=True,
        resolucao_de_conflito="coordenador",
    )

    paper = PaperModel(project_id=proj.id, title="Paper N2", decision="Pendente", screening_status="aguardando")
    db_session.add(paper)
    db_session.flush()

    # 1. Sem julgamentos
    consolidar(db_session, paper, politica)
    assert paper.screening_status == "aguardando"
    assert paper.decision == "Pendente"

    # 2. Revisor 1 vota 'Incluído' -> parcial
    s1 = PaperScreeningModel(
        paper_id=paper.id,
        reviewer_id=user_a.id,
        decision="Incluído",
        observations="Observacao A",
        decided_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(s1)
    paper.screenings = [s1]
    consolidar(db_session, paper, politica)

    assert paper.screening_status == "parcial"
    assert paper.decision == "Pendente"

    # 3. Revisor 2 vota 'Incluído' -> CONSENSO!
    s2 = PaperScreeningModel(
        paper_id=paper.id,
        reviewer_id=user_b.id,
        decision="Incluído",
        observations="Observacao B",
        decided_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(s2)
    paper.screenings = [s1, s2]
    consolidar(db_session, paper, politica)

    assert paper.screening_status == "consenso"
    assert paper.decision == "Incluído"
    assert "Observacao A" in paper.observations
    assert "Observacao B" in paper.observations

    # 4. Reversão: Revisor 2 muda de ideia e vota 'Excluído' -> CONFLITO!
    s2.decision = "Excluído"
    s2.updated_at = utcnow()
    consolidar(db_session, paper, politica)

    assert paper.screening_status == "conflito"
    assert paper.decision == "Pendente"
