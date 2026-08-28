#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes das entidades de domínio do Revsist."""

from app.domain.entities import Decision, Methodology, Paper, Protocol, ScreeningSession


def test_paper_immutability():
    paper = Paper(id="p1", title="Estudo Original", decision=Decision.PENDING)
    updated = paper.with_decision(Decision.INCLUDED)

    assert updated.decision == Decision.INCLUDED
    assert paper.decision == Decision.PENDING  # O original permanece inalterado


def test_paper_criteria_update():
    paper = Paper(id="p1", title="Estudo")
    with_inc = paper.with_criterion("Critério 1", True, is_exclusion=False)
    with_exc = with_inc.with_criterion("Exclusão 1", True, is_exclusion=True)

    assert with_exc.inclusion_criteria["Critério 1"] is True
    assert with_exc.exclusion_criteria["Exclusão 1"] is True
    assert "Exclusão 1" not in paper.exclusion_criteria


def test_screening_session_counts():
    p1 = Paper(id="1", title="A", decision=Decision.INCLUDED)
    p2 = Paper(id="2", title="B", decision=Decision.EXCLUDED)
    p3 = Paper(id="3", title="C", decision=Decision.PENDING)

    session = ScreeningSession(papers=[p1, p2, p3])
    assert session.total_count == 3
    assert session.included_count == 1
    assert session.excluded_count == 1
    assert session.pending_count == 1
