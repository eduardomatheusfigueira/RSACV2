#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes unitários de calibração de prompts e controle de extensão por campo."""

import pytest
from app.infrastructure.ai.prompts import (
    build_field_assist_prompt,
    build_protocol_suggestion_prompt,
    get_field_calibration,
    FIELD_CALIBRATION_SPECS,
)


def test_field_calibration_lookup():
    """Testa recuperação exata e por fallback dos metadados de calibração."""
    # Lookup exato por ID
    calib_pop = get_field_calibration("pico_population", "População")
    assert "População" in calib_pop["categoria"]
    assert "5 a 20 palavras" in calib_pop["extensao_recomendada"]
    assert "PROIBIDO" in calib_pop["proibicoes"]

    # Lookup por fallback de rótulo
    calib_pop_fallback = get_field_calibration("", "Participantes e População Alvo")
    assert "População" in calib_pop_fallback["categoria"]

    calib_obj = get_field_calibration("objective", "Pergunta e Objetivo")
    assert "35 a 70 palavras" in calib_obj["extensao_recomendada"]

    calib_crit = get_field_calibration("criteria", "Critérios de Elegibilidade")
    assert "INC:" in calib_crit["formato_alvo"] or "INC:" in calib_crit["exemplo_adequado"]


def test_pico_population_prompt_calibration():
    """Garante que campos curtos de framework recebam regras estritas de concisão no prompt."""
    prompt = build_field_assist_prompt(
        field_id="pico_population",
        field_label="População / Participantes (P)",
        field_guidelines="Descreva de forma sucinta a população",
        project_title="Políticas Públicas em APLs",
        methodology="PRISMA-ScR",
    )

    assert "CALIBRAÇÃO OBRIGATÓRIA DE EXTENSÃO E FORMATO DO CAMPO" in prompt
    assert "5 a 20 palavras" in prompt
    assert "PROIBIDO gerar parágrafos dissertativos" in prompt
    assert "RESPEITO ABSOLUTO À EXTENSÃO" in prompt


def test_title_prompt_calibration():
    """Garante que o campo de título exija 1 única linha."""
    prompt = build_field_assist_prompt(
        field_id="manuscript_title",
        field_label="Título Provisório",
        project_title="Desenvolvimento Regional",
    )

    assert "1 única linha contendo o título acadêmico" in prompt
    assert "Sem ponto final" in prompt


def test_objective_prompt_calibration():
    """Garante que o objetivo exija pergunta norteadora + objetivo conciso."""
    prompt = build_field_assist_prompt(
        field_id="objective",
        field_label="Pergunta Principal e Objetivo Geral",
        project_title="Desenvolvimento Regional",
    )

    assert "35 a 70 palavras" in prompt
    assert "PROIBIDO gerar resumos inteiros de artigos" in prompt


def test_criteria_prompt_calibration():
    """Garante que os critérios exijam lista formatada com prefixos INC: e EXC:."""
    prompt = build_field_assist_prompt(
        field_id="criteria",
        field_label="Critérios de Elegibilidade",
    )

    assert "INC: " in prompt
    assert "EXC: " in prompt
    assert "10 a 25 palavras" in prompt


def test_protocol_suggestion_prompt_contains_length_rules():
    """Garante que a sugestão geral de protocolo instrua o modelo a calibrar o tamanho dos campos do JSON."""
    prompt = build_protocol_suggestion_prompt(
        title="Inovação e APLs no Brasil",
        methodology="PRISMA-ScR",
        initial_description="Revisão sobre governança territorial.",
    )

    assert "REGRAS OBRIGATÓRIAS DE EXTENSÃO E FORMATO" in prompt
    assert "CAMPOS DE DECOMPOSIÇÃO (PCC/PICO): Devem ser ESTRITAMENTE CONCISOS" in prompt
    assert "DESCRITORES EM PARES" in prompt
    assert "NO MÁXIMO 5 pares por idioma" in prompt
