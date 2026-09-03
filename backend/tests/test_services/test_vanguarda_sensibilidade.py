#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de Indicadores de Vanguarda e Diagnóstico de Sensibilidade (doc 48 §7.4, §10, §12, doc 49 Fase 8)."""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibKeywordModel,
    PaperModel,
    ProjectModel,
)
from app.services.bibliometria.vanguarda import (
    ServicoDeVanguarda,
    _ajustar_rand_index,
)
from tests.conftest import OWNER_ID_TESTE


def test_bootstrap_com_semente_e_reprodutivel(db_session):
    """Garante que a reamostragem bootstrap com seed fixa é estritamente reprodutível."""
    pid = "proj-boot-seed"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Seed", methodology="PRISMA"))

    for i in range(10):
        db_session.add(
            PaperModel(
                id=f"p-boot-{i}",
                project_id=pid,
                title=f"Paper {i}",
                journal="Revista Brasileira de Planejamento",
                decision=Decision.INCLUDED.value,
            )
        )
    db_session.commit()

    servico = ServicoDeVanguarda()
    res1 = servico.calcular_bootstrap_rankings(db_session, project_id=pid, n_boot=200, seed=42)
    res2 = servico.calcular_bootstrap_rankings(db_session, project_id=pid, n_boot=200, seed=42)

    assert res1["items"] == res2["items"]
    assert res1["items"][0]["ic_95"] == res2["items"][0]["ic_95"]


def test_posicoes_indistinguiveis_sao_sinalizadas(db_session):
    """TESTE DE METODOLOGIA (doc 48 §10.1): Periódicos com empate técnico recebem aviso de posições indistinguíveis."""
    pid = "proj-boot-empate"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Empate", methodology="PRISMA"))

    # 4 papers na Revista A, 4 papers na Revista B, 4 papers na Revista C
    for i in range(4):
        db_session.add(PaperModel(id=f"pa-{i}", project_id=pid, title=f"PA {i}", journal="Revista A", decision=Decision.INCLUDED.value))
        db_session.add(PaperModel(id=f"pb-{i}", project_id=pid, title=f"PB {i}", journal="Revista B", decision=Decision.INCLUDED.value))
        db_session.add(PaperModel(id=f"pc-{i}", project_id=pid, title=f"PC {i}", journal="Revista C", decision=Decision.INCLUDED.value))

    db_session.commit()

    servico = ServicoDeVanguarda()
    res = servico.calcular_bootstrap_rankings(db_session, project_id=pid, tipo_ranking="periodicos", n_boot=300, seed=42)

    assert res["tem_empates_tecnicos"] is True
    assert res["aviso_empates"] is not None
    assert any(item["indistinguivel"] is True for item in res["items"])


def test_diagrama_estrategico_classifica_quadrantes_conhecidos(db_session):
    """Calcula densidade e centralidade posicionando temas nos 4 quadrantes clássicos."""
    pid = "proj-diag-quad"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto SciMAT", methodology="PRISMA"))

    # Criar papers com palavras-chave formando clusters coesos
    for i in range(5):
        p = PaperModel(id=f"pd-{i}", project_id=pid, title=f"PD {i}", decision=Decision.INCLUDED.value)
        db_session.add(p)
        db_session.add(BibKeywordModel(paper_id=p.id, term="governança regional"))
        db_session.add(BibKeywordModel(paper_id=p.id, term="políticas territoriais"))

    for i in range(5, 10):
        p = PaperModel(id=f"pd-{i}", project_id=pid, title=f"PD {i}", decision=Decision.INCLUDED.value)
        db_session.add(p)
        db_session.add(BibKeywordModel(paper_id=p.id, term="arranjos produtivos locais"))
        db_session.add(BibKeywordModel(paper_id=p.id, term="inovação"))

    db_session.commit()

    servico = ServicoDeVanguarda()
    res = servico.calcular_diagrama_estrategico(db_session, project_id=pid)

    assert len(res["items"]) >= 1
    for item in res["items"]:
        assert item["quadrante"] in ["motor", "basico", "especializado", "emergente_declinio"]
        assert "centralidade" in item
        assert "densidade" in item


def test_rajada_detecta_termo_com_salto_construido(db_session):
    """TESTE DE BURST DETECTION (Kleinberg 2003): Termo que explode em frequência é detectado."""
    pid = "proj-burst-test"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Burst", methodology="PRISMA"))

    # 2020: 1 estudo com "desenvolvimento sustentável"
    p0 = PaperModel(id="pb-0", project_id=pid, title="P0", year="2020", decision=Decision.INCLUDED.value)
    db_session.add(p0)
    db_session.add(BibKeywordModel(paper_id=p0.id, term="desenvolvimento sustentável"))

    # 2021: 1 estudo com "desenvolvimento sustentável"
    p1 = PaperModel(id="pb-1", project_id=pid, title="P1", year="2021", decision=Decision.INCLUDED.value)
    db_session.add(p1)
    db_session.add(BibKeywordModel(paper_id=p1.id, term="desenvolvimento sustentável"))

    # 2022: 8 estudos com "desenvolvimento sustentável" (salto abrupto)
    for i in range(2, 10):
        p = PaperModel(id=f"pb-{i}", project_id=pid, title=f"P{i}", year="2022", decision=Decision.INCLUDED.value)
        db_session.add(p)
        db_session.add(BibKeywordModel(paper_id=p.id, term="desenvolvimento sustentável"))

    db_session.commit()

    servico = ServicoDeVanguarda()
    res = servico.detectar_rajadas_termos(db_session, project_id=pid, s=1.5)

    assert len(res["rajadas"]) >= 1
    assert any("Desenvolvimento Sustentável" in r["termo"] for r in res["rajadas"])
    assert res["rajadas"][0]["ano_inicio"] == "2022"


def test_sensibilidade_calcula_rand_index():
    """Valida o cálculo do Índice de Rand Ajustado (ARI) entre partições."""
    # Partição A idêntica a si mesma -> ARI = 1.0
    part_a = {"no1": 0, "no2": 0, "no3": 1, "no4": 1}
    assert _ajustar_rand_index(part_a, part_a) == 1.0

    # Partição completamente diferente
    part_b = {"no1": 0, "no2": 1, "no3": 0, "no4": 1}
    ari = _ajustar_rand_index(part_a, part_b)
    assert isinstance(ari, float)
    assert ari < 1.0
