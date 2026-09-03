#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de Estatística Sob Demanda, Compilador e Segurança (doc 48 §9, §12, doc 49 Fase 7)."""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibAnaliseModel,
    BibWorkMetaModel,
    PaperModel,
    ProjectModel,
)
from app.schemas.bibliometria import EspecificacaoEstatistica, FiltroEspecificacao
from app.services.bibliometria.analises import (
    ServicoDeAnalises,
    interpretar_pergunta,
)
from tests.conftest import OWNER_ID_TESTE


def test_especificacao_invalida_e_recusada(db_session):
    pid = "proj-spec-inv"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Spec Inv", methodology="PRISMA"))
    db_session.commit()

    servico = ServicoDeAnalises()

    # Medida inválida
    with pytest.raises(ValueError, match="Medida 'regressao_linear' inválida"):
        spec = EspecificacaoEstatistica(medida="regressao_linear", por=["ano"])
        servico.compilar_e_executar(db_session, project_id=pid, spec=spec)

    # Agrupador inválido
    with pytest.raises(ValueError, match="Agrupador 'campo_inventado' inválido"):
        spec = EspecificacaoEstatistica(medida="contagem", por=["campo_inventado"])
        servico.compilar_e_executar(db_session, project_id=pid, spec=spec)

    # Operador inválido
    with pytest.raises(ValueError, match="Operador 'LIKE' inválido"):
        spec = EspecificacaoEstatistica(
            medida="contagem",
            por=["ano"],
            onde=[FiltroEspecificacao(campo="decisao", op="LIKE", valor="Inc%")],
        )
        servico.compilar_e_executar(db_session, project_id=pid, spec=spec)


def test_injecao_na_pergunta_nao_alcanca_o_banco(db_session):
    """TESTE DE SEGURANÇA (doc 29, doc 48 §9.2): Pergunta maliciosa é recusada e a tabela papers permanece intocada."""
    pid = "proj-sec-inj"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Segurança", methodology="PRISMA"))
    paper = PaperModel(id="p-sec-1", project_id=pid, title="Paper Seguro", decision=Decision.INCLUDED.value)
    db_session.add(paper)
    db_session.commit()

    pergunta_maliciosa = "qual a média de citações; DROP TABLE papers; --"
    res_interp = interpretar_pergunta(pergunta_maliciosa)

    assert res_interp["supported"] is False
    assert "injeção" in res_interp["explanation"]
    assert res_interp["specification"] is None

    # Verifica que a tabela papers continua intacta
    assert db_session.query(PaperModel).filter(PaperModel.id == "p-sec-1").count() == 1


def test_pergunta_fora_do_vocabulario_recebe_recusa_com_alternativas():
    pergunta_aleatoria = "quantas borboletas azuis voam no parque?"
    res = interpretar_pergunta(pergunta_aleatoria)

    assert res["supported"] is False
    assert "Não foi possível identificar" in res["explanation"]
    assert res["supported_vocabulary"] is not None
    assert "medidas" in res["supported_vocabulary"]
    assert "agrupadores" in res["supported_vocabulary"]


def test_calculo_mediana_media_desvio_padrao_soma(db_session):
    """Valida a precisão matemática dos cálculos estatísticos agregados."""
    pid = "proj-math-stat"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Math", methodology="PRISMA"))

    # Criar 5 papers no ano 2020 com citações conhecidas: 10, 20, 30, 40, 50
    # Média = 30.0, Mediana = 30.0, Soma = 150.0, Stdev = 15.8114
    for i, cit in enumerate([10, 20, 30, 40, 50], start=1):
        p = PaperModel(id=f"p-math-{i}", project_id=pid, title=f"Estudo {i}", year="2020", decision=Decision.INCLUDED.value)
        db_session.add(p)
        db_session.add(BibWorkMetaModel(paper_id=p.id, cited_by_count=cit, is_oa=True))

    db_session.commit()

    servico = ServicoDeAnalises()

    # 1. Mediana
    spec_med = EspecificacaoEstatistica(medida="mediana", campo="citacoes_recebidas", por=["ano"])
    res_med, _, _ = servico.compilar_e_executar(db_session, project_id=pid, spec=spec_med)
    assert len(res_med) == 1
    assert res_med[0]["valor"] == 30.0
    assert res_med[0]["n_docs"] == 5

    # 2. Média
    spec_avg = EspecificacaoEstatistica(medida="media", campo="citacoes_recebidas", por=["ano"])
    res_avg, _, _ = servico.compilar_e_executar(db_session, project_id=pid, spec=spec_avg)
    assert res_avg[0]["valor"] == 30.0

    # 3. Soma
    spec_sum = EspecificacaoEstatistica(medida="soma", campo="citacoes_recebidas", por=["ano"])
    res_sum, _, _ = servico.compilar_e_executar(db_session, project_id=pid, spec=spec_sum)
    assert res_sum[0]["valor"] == 150.0

    # 4. Desvio Padrão
    spec_std = EspecificacaoEstatistica(medida="desvio_padrao", campo="citacoes_recebidas", por=["ano"])
    res_std, _, _ = servico.compilar_e_executar(db_session, project_id=pid, spec=spec_std)
    assert res_std[0]["valor"] == 15.8114


def test_mesma_especificacao_mesmo_instantaneo_mesmo_numero(db_session):
    """Determinismo: a mesma especificação executada duas vezes gera resultados idênticos."""
    pid = "proj-det-stat"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Det", methodology="PRISMA"))

    p1 = PaperModel(id="p-det-1", project_id=pid, title="APL 1", year="2021", decision=Decision.INCLUDED.value)
    p2 = PaperModel(id="p-det-2", project_id=pid, title="APL 2", year="2021", decision=Decision.INCLUDED.value)
    db_session.add_all([p1, p2])
    db_session.add(BibWorkMetaModel(paper_id=p1.id, cited_by_count=5))
    db_session.add(BibWorkMetaModel(paper_id=p2.id, cited_by_count=15))
    db_session.commit()

    servico = ServicoDeAnalises()
    spec = EspecificacaoEstatistica(medida="media", campo="citacoes_recebidas", por=["ano"])

    res1, _, _ = servico.compilar_e_executar(db_session, project_id=pid, spec=spec)
    res2, _, _ = servico.compilar_e_executar(db_session, project_id=pid, spec=spec)

    assert res1 == res2
    assert res1[0]["valor"] == 10.0
