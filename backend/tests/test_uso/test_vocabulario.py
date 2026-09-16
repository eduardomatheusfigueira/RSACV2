#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — O vocabulário fechado dos eventos de uso (doc 52 §6.2, T-01 e T-02).

A garantia de que o conteúdo da pesquisa não entra nos dados de uso é
estrutural: não existe tipo de propriedade que aceite texto livre. Estes
testes impedem que ela deixe de ser.
"""

import pytest

from app.services.uso import vocabulario


def test_catalogo_saudavel():
    assert vocabulario.problemas_do_catalogo() == []


def test_nao_existe_tipo_texto():
    """T-02: todo tipo é enum, int, faixa ou bool; todo evento cita uma pergunta (P1)."""
    for nome, spec in vocabulario.eventos().items():
        assert spec["perguntas"], nome
        for chave, prop in spec.get("propriedades", {}).items():
            assert prop["tipo"] in {"enum", "int", "faixa", "bool"}, f"{nome}.{chave}"


def test_evento_valido_passa():
    evento, motivo = vocabulario.validar("acao", "projeto.triagem", {"alvo": "triagem.lote.iniciar"})
    assert motivo == ""
    assert evento.nivel == "B"
    assert evento.propriedades == {"alvo": "triagem.lote.iniciar"}


@pytest.mark.parametrize(
    "nome,tela,props,motivo",
    [
        ("inventado", None, {}, "nome_desconhecido"),
        ("acao", "/projects/7847417c/screening", {"alvo": "projeto.criar"}, "tela_desconhecida"),
        ("acao", None, {"alvo": "Segurança pública em fronteiras fluviais"}, "propriedade_invalida"),
        ("acao", None, {"alvo": "projeto.criar", "titulo": "x"}, "propriedade_desconhecida"),
        ("sessao_uso.fim", None, {"tempo_ativo_s": "3600"}, "propriedade_invalida"),
        ("sessao_uso.fim", None, {"tempo_ativo_s": True}, "propriedade_invalida"),
        ("sessao_uso.fim", None, {"tempo_ativo_s": 999999}, "propriedade_invalida"),
        ("jornada.triagem_lote_concluida", None, {"estudos": 57}, "propriedade_invalida"),
        ("acao", None, ["projeto.criar"], "propriedades_nao_objeto"),
    ],
)
def test_fora_do_vocabulario_e_descartado(nome, tela, props, motivo):
    """T-01: descartado no modo normal, com a categoria do motivo — nunca o valor."""
    evento, obtido = vocabulario.validar(nome, tela, props)
    assert evento is None
    assert obtido == motivo


def test_modo_estrito_levanta():
    with pytest.raises(vocabulario.EventoInvalido):
        vocabulario.validar("acao", None, {"alvo": "texto livre"}, estrito=True)


@pytest.mark.parametrize("n,esperada", [(0, "0"), (1, "1-10"), (10, "1-10"), (11, "11-100"), (1000, "101-1000"), (1001, ">1000")])
def test_faixas(n, esperada):
    assert vocabulario.faixa(n) == esperada
