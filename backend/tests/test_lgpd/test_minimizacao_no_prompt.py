#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Minimização no que sai para a IA (doc 38, L-11).

O prompt de triagem enviava `AUTORES:` ao provedor de IA. Nome de autor é dado
pessoal de terceiro: de gente que não usa o Revsist, não foi avisada e não tem
como se opor. A triagem, por outro lado, é decidida contra o título e o resumo
à luz dos critérios do protocolo — o nome não entra na decisão, entrava porque
estava à mão.

O art. 6º III da LGPD chama isso de necessidade: tratar o mínimo para a
finalidade. Mandar ao exterior o que não se usa é o oposto, e sem ganho nenhum
no parecer.

Estes testes existem porque a linha era fácil de repor: `authors` continua no
banco, continua na exportação, e reintroduzi-la no prompt seria uma linha de
diff que passaria em qualquer revisão distraída.
"""

from __future__ import annotations

import pytest

from app.infrastructure.ai.prompts import build_screening_prompt

# Nomes improváveis o bastante para não aparecerem por acaso em outro campo.
AUTORES = "Zwingli Q. Ashkenazy; Ptolemaia X. Vasconcellos-Krieger"

PROTOCOLO = {
    "objective": "Mapear políticas de turismo náutico",
    "inclusion_criteria": ["Estudos brasileiros"],
    "exclusion_criteria": ["Anteriores a 2010"],
    "pico_framework": {},
}


def _artigo(**extra) -> dict:
    base = {
        "title": "Governança costeira e turismo náutico no litoral catarinense",
        "authors": AUTORES,
        "year": 2021,
        "abstract": "Analisa instrumentos de gestão costeira em municípios do litoral.",
    }
    base.update(extra)
    return base


def test_nenhum_nome_de_autor_sai_no_prompt_de_triagem():
    """O critério de aceite da Fase 3 pede exatamente esta inspeção."""
    prompt = build_screening_prompt(_artigo(), PROTOCOLO)

    for pedaco in ("Zwingli", "Ashkenazy", "Ptolemaia", "Vasconcellos", "Krieger"):
        assert pedaco not in prompt, f"{pedaco!r} vazou para o provedor de IA"


def test_o_rotulo_AUTORES_nao_volta():
    """
    Sem o rótulo não há onde pendurar o dado de novo sem que se veja.

    Testar o rótulo além dos nomes é redundante de propósito: alguém que
    reintroduza a seção provavelmente o fará com o campo vazio primeiro, e aí
    o teste dos nomes ainda passaria.
    """
    prompt = build_screening_prompt(_artigo(), PROTOCOLO)
    assert "AUTORES:" not in prompt


def test_o_que_a_triagem_precisa_continua_no_prompt():
    """
    Minimizar não é esvaziar.

    Se este teste cair junto com os de cima, a remoção foi longe demais e o
    parecer perdeu base — que é o modo de errar mais provável ao mexer aqui.
    """
    prompt = build_screening_prompt(_artigo(), PROTOCOLO)

    assert "Governança costeira" in prompt
    assert "instrumentos de gestão costeira" in prompt
    assert "2021" in prompt
    assert "Estudos brasileiros" in prompt
    assert "Anteriores a 2010" in prompt


@pytest.mark.parametrize("campo", ["authors", "autores", "AUTHORS"])
def test_autor_em_qualquer_grafia_de_chave_nao_vaza(campo):
    """
    O dicionário do artigo vem de várias origens (coletores, importação de
    .bib, banco), e a chave nem sempre chega como `authors`. O prompt não pode
    ter um caminho por onde uma grafia diferente reentre.
    """
    artigo = _artigo()
    artigo.pop("authors", None)
    artigo[campo] = AUTORES

    prompt = build_screening_prompt(artigo, PROTOCOLO)
    assert "Ashkenazy" not in prompt


def test_objeto_com_atributo_authors_tambem_nao_vaza():
    """
    `build_screening_prompt` aceita objeto além de dicionário, e o caminho do
    objeto tem normalização própria — foi de lá que a cópia do campo saiu.
    """

    class PaperFalso:
        title = "Governança costeira e turismo náutico"
        authors = AUTORES
        year = 2021
        abstract = "Analisa instrumentos de gestão costeira."

    prompt = build_screening_prompt(PaperFalso(), PROTOCOLO)
    assert "Ashkenazy" not in prompt
