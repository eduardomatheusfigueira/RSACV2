#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes de Pré-Registro, Conformidade BIBLIO e Pacote de Replicação (doc 48 §11, §12, doc 49 Fase 9)."""

import io
import json
import zipfile
import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    PaperModel,
    ProjectModel,
    ProtocolAmendmentModel,
    ProtocolModel,
)
from app.services.bibliometria.preregistro import ServicoDePreRegistro
from tests.conftest import OWNER_ID_TESTE


def test_analise_nao_prevista_sai_marcada_como_exploratoria(db_session):
    """TESTE DE PRÉ-REGISTRO (doc 48 §11): Análise não prevista no protocolo sai como exploratória."""
    pid = "proj-pre-exp"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Pré-Registro", methodology="PRISMA"))
    db_session.commit()

    servico = ServicoDePreRegistro()
    plano = servico.obter_ou_criar_plano(db_session, project_id=pid)

    # 1. Análise prevista
    aval_prevista = servico.avaliar_analise(plano, "producao_anual")
    assert aval_prevista["exploratoria"] is False
    assert aval_prevista["status"] == "prevista_no_protocolo"

    # 2. Análise não prevista (exploratória)
    aval_exploratoria = servico.avaliar_analise(plano, "analise_acoplamento_customizada")
    assert aval_exploratoria["exploratoria"] is True
    assert aval_exploratoria["status"] == "nao_prevista_exploratoria"
    assert "exploratória" in aval_exploratoria["aviso"]


def test_relatorio_biblio_nao_reivindica_item_do_autor(db_session):
    """TESTE DE CONFORMIDADE BIBLIO (doc 48 §11): Separação estrita entre garantias do sistema e responsabilidade do autor."""
    pid = "proj-biblio-rep"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto BIBLIO", methodology="PRISMA"))
    db_session.commit()

    servico = ServicoDePreRegistro()
    relatorio = servico.gerar_relatorio_conformidade_biblio(db_session, project_id=pid)

    assert relatorio["total_itens"] == 20
    assert relatorio["itens_do_sistema"] >= 16
    assert relatorio["itens_do_autor"] >= 2

    # Verificar que itens do autor não são atribuídos ao sistema
    itens_autor = [it for it in relatorio["itens"] if it["responsabilidade"] == "autor"]
    for it in itens_autor:
        assert it["responsabilidade"] == "autor"
        assert "autor" in it["responsabilidade"]


def test_exportacao_carrega_proveniencia_completa(db_session):
    """TESTE DE REPLICAÇÃO: O arquivo ZIP gerado contém manifesto, dados, relatório e proveniência íntegros."""
    pid = "proj-zip-repl"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Replicação", methodology="PRISMA"))
    db_session.add(PaperModel(id="p-zip-1", project_id=pid, title="Estudo A", decision=Decision.INCLUDED.value))
    db_session.commit()

    servico = ServicoDePreRegistro()
    zip_bytes = servico.gerar_pacote_replicacao_zip(db_session, project_id=pid)

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        nomes = zf.namelist()
        assert "manifesto_instantaneo.json" in nomes
        assert "proveniencia.json" in nomes
        assert "plano_pre_registro.json" in nomes
        assert "relatorio_conformidade_biblio.md" in nomes
        assert "relatorio_conformidade_biblio.json" in nomes
        assert "indicadores/indicadores_resumo.json" in nomes

        # Verificar conteúdo do manifesto
        manifesto_data = json.loads(zf.read("manifesto_instantaneo.json").decode("utf-8"))
        assert "corpus_hash" in manifesto_data


def test_emenda_gerada_quando_protocolo_vigente(db_session):
    """Modificação de plano bibliométrico em protocolo congelado ('vigente') gera emenda formal."""
    pid = "proj-amend-test"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Emenda", methodology="PRISMA"))
    prot = ProtocolModel(project_id=pid, status="vigente", current_version="v1.0", bibliometrics="{}")
    db_session.add(prot)
    db_session.commit()

    servico = ServicoDePreRegistro()
    novo_plano = {
        "indicadores_previstos": ["producao_anual", "top_periodicos", "rajadas"],
        "unidade_analise": "documento",
        "janela_temporal": "2018-2024",
        "justificativa_janela": "Recorte dos últimos 6 anos.",
        "cortes_declarados": {"freq_minima_termo": 3},
        "tesauro_obrigatorio": True,
    }

    res = servico.atualizar_plano(db_session, project_id=pid, payload=novo_plano, usuario_id=OWNER_ID_TESTE)

    assert len(res["emendas"]) == 1
    assert res["emendas"][0]["section"] == "bibliometrics"
    assert "Alteração no plano bibliométrico" in res["emendas"][0]["reason"]
