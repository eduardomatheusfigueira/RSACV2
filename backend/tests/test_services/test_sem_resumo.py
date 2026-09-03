#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Registros sem resumo ficam fora da fila da triagem assistida.

Cerca de 28% dos pendentes deste acervo chegam sem resumo — repositórios
institucionais e catálogos de teses costumam não publicá-lo. E parte do que
chega no campo não é resumo: nome do orientador, contagem de páginas, ", .".
Mandar isso para a assistência não produz uma decisão ruim; produz uma decisão
sobre nada, com a mesma aparência de confiança de uma decisão real.
"""

import pytest

from app.domain.triabilidade import (
    TAMANHO_MINIMO_DE_RESUMO,
    resumo_e_triavel,
)
from app.infrastructure.persistence.models import PaperModel
from tests.conftest import OWNER_ID_TESTE


# ── O critério ────────────────────────────────────────────────────────


def test_ausencia_de_resumo_nao_e_triavel():
    assert resumo_e_triavel(None) is False
    assert resumo_e_triavel("") is False
    assert resumo_e_triavel("      ") is False


def test_metadado_desgarrado_nao_passa_por_resumo():
    """Os casos reais encontrados no acervo."""
    for lixo in (
        ", .",
        "106 f.",
        "Orientação: Profa. Dra. Marcela Barbosa de Moraes",
        "Orientador: Prof. Dr. Marcelo Souza Motta",
        "Acompanha prpdução técnica: Guia de Programação ESP32",
    ):
        assert resumo_e_triavel(lixo) is False, f"Aceitou como resumo: {lixo!r}"


def test_resumo_curto_porem_legitimo_continua_na_fila():
    """O custo de um falso negativo aqui é um estudo relevante sumindo.

    Entre 100 e 200 caracteres o acervo tem resumos verdadeiros, apenas curtos.
    O corte precisa ficar abaixo disso.
    """
    real = (
        "We overview our recent development and testing of the FIDO rover, an "
        "advanced technology prototype for Mars surface missions."
    )
    assert len(real) < 200
    assert resumo_e_triavel(real) is True


def test_o_corte_fica_abaixo_dos_resumos_curtos_reais():
    assert TAMANHO_MINIMO_DE_RESUMO < 100, (
        "Um corte de 100 ou mais descartaria resumos legítimos observados no acervo."
    )


# ── O efeito no lote ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_lote_ignora_quem_nao_tem_resumo(db_session, servico_de_lote):
    """A fila do lote é só o que a assistência consegue julgar."""
    from app.infrastructure.persistence.models import (
        CriterionModel,
        ProjectModel,
        ProtocolModel,
    )

    servico, cliente, _espiao = servico_de_lote

    db_session.add(
        ProjectModel(
            id="proj-sr", owner_id=OWNER_ID_TESTE, title="Sem resumo", methodology="PRISMA-ScR"
        )
    )
    db_session.add(ProtocolModel(id="proto-sr", project_id="proj-sr", objective="Mapear"))
    db_session.flush()
    db_session.add(
        CriterionModel(
            id="c-sr", protocol_id="proto-sr", text="Critério A", is_exclusion=False, order=0
        )
    )

    amostras = [
        ("com-resumo", "Estudo com resumo", "R" * 400),
        ("sem-resumo", "Estudo sem resumo", None),
        ("resumo-vazio", "Estudo com resumo vazio", "   "),
        ("resumo-lixo", "Estudo com metadado no lugar do resumo", "Orientador: Prof. Dr. Fulano"),
    ]
    for pid, titulo, resumo in amostras:
        db_session.add(
            PaperModel(
                id=pid,
                project_id="proj-sr",
                title=titulo,
                abstract=resumo,
                decision="Pendente",
                is_duplicate=False,
            )
        )
    db_session.commit()

    await servico.run_batch_screening("proj-sr", limit=50, concurrency=1, pausa_entre_estudos=0)

    assert cliente.chamadas == ["Estudo com resumo"], (
        f"O lote pegou registros sem resumo utilizável: {cliente.chamadas}"
    )

    # Os demais continuam no acervo, pendentes — não foram descartados.
    restantes = (
        db_session.query(PaperModel)
        .filter(PaperModel.project_id == "proj-sr", PaperModel.decision == "Pendente")
        .count()
    )
    assert restantes == 3, f"Registros sem resumo desapareceram: restaram {restantes}."
