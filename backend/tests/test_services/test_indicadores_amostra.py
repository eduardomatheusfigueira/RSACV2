#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Leis bibliométricas — amostra insuficiente não vira resultado.

Bradford e Lotka são afirmações sobre distribuições, e ambas precisam de
massa para significar alguma coisa. As funções se protegiam de entrada vazia e
de mais nada, então dado degenerado saía com aparência de achado:

  * um recorte com **um** periódico exibia "Zona 1 (Núcleo): 1 periódico, 100%"
    e razão "1 : 0 : 0";
  * **17** autores, quase todos com um artigo, produziam D_KS = 0,0 e o selo
    verde "Aderência aceita".

Os dois foram medidos na amostra incluída de um projeto real em 01/09/2026.
"""

from app.services.bibliometria.indicadores import (
    AUTORES_MINIMOS_PARA_ADERENCIA,
    PERIODICOS_MINIMOS_PARA_ZONAS,
    calcular_bradford,
    calcular_lotka_com_ks,
)


# ── Bradford ────────────────────────────────────────────────────────────


def test_um_periodico_nao_faz_tres_zonas():
    """O caso real: a amostra incluída tinha um único periódico."""
    r = calcular_bradford([("Sociedade e Estado", 1)])

    assert r["confiavel"] is False
    assert r["zones"] == []
    assert "três zonas" in r["motivo"]
    assert r["formula_ratio"] == "—", "Publicou uma razão a partir de um periódico."


def test_dois_periodicos_ainda_nao_bastam():
    r = calcular_bradford([("Revista A", 9), ("Revista B", 4)])
    assert r["confiavel"] is False


def test_periodicos_suficientes_produzem_as_zonas():
    periodicos = [(f"Revista {i}", n) for i, n in enumerate([30, 20, 12, 8, 5, 3, 2, 1, 1])]

    r = calcular_bradford(periodicos)

    assert r.get("confiavel") is not False
    assert len(r["zones"]) == 3
    assert sum(z["total_articles"] for z in r["zones"]) == 82


def test_o_piso_de_periodicos_e_o_declarado():
    """Se a constante mudar, o teste acompanha — não há número mágico solto."""
    minimo = [(f"Revista {i}", 1) for i in range(PERIODICOS_MINIMOS_PARA_ZONAS)]
    abaixo = minimo[:-1]

    assert calcular_bradford(abaixo)["confiavel"] is False
    assert calcular_bradford(minimo).get("confiavel") is not False


# ── Lotka ───────────────────────────────────────────────────────────────


def test_amostra_pequena_nao_recebe_veredicto():
    """Nem "aceita" nem "rejeita": o teste não decide com 17 autores.

    O valor crítico 1,36/√N é assintótico; com N pequeno ele aceita quase
    qualquer coisa (Clauset, Shalizi & Newman, 2009).
    """
    r = calcular_lotka_com_ks([1] * 15 + [2, 2])

    assert r["is_adherent"] is None, "Emitiu veredicto onde o teste não decide."
    assert r["sample_ok"] is False
    assert "insuficiente" in r["p_verdict"].lower()


def test_expoente_continua_disponivel_como_descricao():
    """Suprimir o veredicto não é apagar o ajuste — ele descreve, não afirma."""
    r = calcular_lotka_com_ks([1] * 15 + [2, 2])

    assert r["alpha"] is not None
    assert r["n_authors"] == 17
    assert r["distribution"], "Ficou sem a distribuição observada."


def test_amostra_suficiente_volta_a_decidir():
    r = calcular_lotka_com_ks([1] * 60 + [2] * 12 + [3] * 4)

    assert r["sample_ok"] is True
    assert r["is_adherent"] in (True, False)
    assert "insuficiente" not in r["p_verdict"].lower()


def test_o_piso_de_autores_e_o_declarado():
    no_piso = [1] * AUTORES_MINIMOS_PARA_ADERENCIA
    abaixo = [1] * (AUTORES_MINIMOS_PARA_ADERENCIA - 1)

    assert calcular_lotka_com_ks(abaixo)["is_adherent"] is None
    assert calcular_lotka_com_ks(no_piso)["is_adherent"] is not None


def test_corpus_vazio_continua_respondendo_sem_quebrar():
    r = calcular_lotka_com_ks([])
    assert r["n_authors"] == 0
    assert r["is_adherent"] is False
    assert calcular_bradford([])["total_journals"] == 0
