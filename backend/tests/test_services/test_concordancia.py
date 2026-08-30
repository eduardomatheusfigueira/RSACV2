"""Testes de Concordância Interobservador e Kappa de Cohen (Doc 43 §43.9)."""

import pytest
from app.infrastructure.persistence.models import (
    PaperModel,
    PaperScreeningModel,
    ProjectModel,
    UserModel,
    utcnow,
)
from app.services.agreement_service import calcular_concordancia_projeto, classificar_kappa


def test_classificacao_landis_koch():
    """Valida as faixas canônicas de Landis & Koch (1977)."""
    assert "Péssima" in classificar_kappa(-0.1)
    assert classificar_kappa(0.15) == "Ligeira"
    assert classificar_kappa(0.35) == "Razoável"
    assert classificar_kappa(0.55) == "Moderada"
    assert classificar_kappa(0.75) == "Substancial"
    assert classificar_kappa(0.95) == "Quase Perfeita"


def test_calculo_kappa_tabela_conhecida(db_session):
    """
    Valida o cálculo do Kappa em uma matriz 2x2 com valores conhecidos:
    - 6 ambos Incluídos
    - 2 ambos Excluídos
    - 1 R1 Incluído / R2 Excluído
    - 1 R1 Excluído / R2 Incluído
    Po = 8/10 = 0.8
    Pe = (7*7 + 3*3)/100 = (49+9)/100 = 0.58
    Kappa = (0.8 - 0.58) / (1 - 0.58) = 0.22 / 0.42 ≈ 0.5238 (Moderada)
    """
    u1 = UserModel(username="rev1_stat", role="researcher")
    u2 = UserModel(username="rev2_stat", role="researcher")
    db_session.add_all([u1, u2])
    db_session.flush()

    proj = ProjectModel(title="Projeto Estatístico", owner_id=u1.id)
    db_session.add(proj)
    db_session.flush()

    # Criar 10 artigos com os pares de julgamento
    cenarios = [
        ("Incluído", "Incluído"),
        ("Incluído", "Incluído"),
        ("Incluído", "Incluído"),
        ("Incluído", "Incluído"),
        ("Incluído", "Incluído"),
        ("Incluído", "Incluído"),
        ("Excluído", "Excluído"),
        ("Excluído", "Excluído"),
        ("Incluído", "Excluído"),
        ("Excluído", "Incluído"),
    ]

    for i, (d1, d2) in enumerate(cenarios):
        p = PaperModel(project_id=proj.id, title=f"Estudo {i+1}", decision="Pendente")
        db_session.add(p)
        db_session.flush()

        s1 = PaperScreeningModel(paper_id=p.id, reviewer_id=u1.id, decision=d1, decided_at=utcnow(), updated_at=utcnow())
        s2 = PaperScreeningModel(paper_id=p.id, reviewer_id=u2.id, decision=d2, decided_at=utcnow(), updated_at=utcnow())
        db_session.add_all([s1, s2])

    db_session.commit()

    resultado = calcular_concordancia_projeto(db_session, proj.id)

    assert resultado["evaluated_papers_count"] == 10
    assert resultado["raw_agreement"] == 0.8
    assert resultado["raw_agreement_percent"] == 80.0
    assert resultado["cohen_kappa"] == 0.5238
    assert resultado["kappa_classification"] == "Moderada"
    assert resultado["concordant_count"] == 8
    assert resultado["discordant_count"] == 2
    assert resultado["contingency_matrix"]["both_included"] == 6
    assert resultado["contingency_matrix"]["both_excluded"] == 2


def test_caso_degenerado_pe_1(db_session):
    """Quando 100% dos estudos são julgados com a mesma categoria por ambos (Pe=1), não deve haver divisão por zero."""
    u1 = UserModel(username="rev1_deg", role="researcher")
    u2 = UserModel(username="rev2_deg", role="researcher")
    db_session.add_all([u1, u2])
    db_session.flush()

    proj = ProjectModel(title="Projeto Degenerado", owner_id=u1.id)
    db_session.add(proj)
    db_session.flush()

    for i in range(5):
        p = PaperModel(project_id=proj.id, title=f"Estudo Unânime {i+1}", decision="Incluído")
        db_session.add(p)
        db_session.flush()

        s1 = PaperScreeningModel(paper_id=p.id, reviewer_id=u1.id, decision="Incluído", decided_at=utcnow(), updated_at=utcnow())
        s2 = PaperScreeningModel(paper_id=p.id, reviewer_id=u2.id, decision="Incluído", decided_at=utcnow(), updated_at=utcnow())
        db_session.add_all([s1, s2])

    db_session.commit()

    resultado = calcular_concordancia_projeto(db_session, proj.id)
    assert resultado["raw_agreement"] == 1.0
    assert resultado["cohen_kappa"] == 1.0
    assert resultado["kappa_classification"] == "Quase Perfeita"
