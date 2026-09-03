#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes da Camada de Texto e Tesauro Controlado (doc 48 §5, §12, doc 49 Fase 4)."""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibTextoModel,
    BibThesaurusEntryModel,
    BibThesaurusModel,
    PaperModel,
    ProjectModel,
)
from app.services.bibliometria.tesauro import ServicoDeTesauro, normalizar_forma
from app.services.bibliometria.texto import (
    contar_palavras,
    extrair_e_persistir_texto,
    obter_ou_extrair_texto,
    obter_resumo_secoes,
)
from app.services.pdf_text import PDFDocument, PDFPage, Section
from tests.conftest import OWNER_ID_TESTE


# ── 1. Camada de Texto e IMRaD ──────────────────────────────────────────


def test_contar_palavras():
    assert contar_palavras("Desenvolvimento regional e sustentabilidade em Santa Catarina.") == 7
    assert contar_palavras("") == 0
    assert contar_palavras("   ") == 0


def test_texto_e_persistido_com_secoes_imrad_e_contagem_palavras(db_session):
    pid = "proj-txt-1"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Texto", methodology="PRISMA"))
    paper = PaperModel(
        id="paper-txt-101",
        project_id=pid,
        title="Estudo sobre APLs",
        decision=Decision.INCLUDED.value,
    )
    db_session.add(paper)
    db_session.commit()

    # Mock de PDFDocument e segment_sections
    doc_mock = PDFDocument(
        pages=[
            PDFPage(number=1, text="1. Introdução\nO presente estudo analisa os Arranjos Produtivos Locais."),
            PDFPage(number=2, text="2. Método\nA pesquisa adotou abordagem qualitativa com entrevistas."),
        ],
        is_scanned=False,
    )
    secoes_mock = [
        Section(title="1. Introdução", key="introducao", start_page=1, text="O presente estudo..."),
        Section(title="2. Método", key="metodo", start_page=2, text="A pesquisa adotou..."),
    ]

    with patch("app.services.bibliometria.texto.extract_document", return_value=doc_mock), \
         patch("app.services.bibliometria.texto.strip_running_heads", return_value=doc_mock), \
         patch("app.services.bibliometria.texto.segment_sections", return_value=secoes_mock):

        pdf_fake = b"%PDF-1.4 Fake PDF Content for Testing"
        texto = extrair_e_persistir_texto(db_session, paper.id, pdf_fake)

        assert texto.paper_id == paper.id
        assert texto.pipeline_version == "2.0.0"
        assert len(texto.pdf_sha256) == 64
        assert texto.n_pages == 2
        assert texto.n_words > 10
        assert "Arranjos Produtivos Locais" in texto.text_clean

        secoes = obter_resumo_secoes(db_session, paper.id)
        assert len(secoes) == 2
        assert secoes[0]["canonical_type"] == "introducao"
        assert secoes[1]["canonical_type"] == "metodo"


def test_texto_e_reusado_e_nao_reextraido(db_session):
    pid = "proj-txt-2"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Reuso", methodology="PRISMA"))
    paper = PaperModel(id="p-reuso-1", project_id=pid, title="Paper Cache", decision=Decision.INCLUDED.value)
    db_session.add(paper)
    # Já persiste texto existente
    db_session.add(
        BibTextoModel(
            paper_id=paper.id,
            pipeline_version="2.0.0",
            pdf_sha256="abc123sha",
            n_pages=5,
            n_words=1200,
            text_clean="Texto já extraído anteriormente e armazenado no banco.",
            sections="[]",
        )
    )
    db_session.commit()

    mock_pdf_service = MagicMock()
    # Chama obter_ou_extrair_texto
    resultado = obter_ou_extrair_texto(db_session, paper.id, pid, pdf_service=mock_pdf_service)

    assert resultado is not None
    assert resultado.n_words == 1200
    assert "armazenado no banco" in resultado.text_clean
    # Garante que o pdf_service NÃO foi acionado porque o texto já existia no banco
    assert mock_pdf_service.get_pdf_path.call_count == 0


# ── 2. Tesauro Controlado e Fusões Aprovadas ────────────────────────────


def test_tesauro_cria_e_propoe_fusoes_em_rascunho(db_session):
    pid = "proj-tesauro-1"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Tesauro", methodology="PRISMA"))
    db_session.commit()

    servico = ServicoDeTesauro()
    tesauro = servico.obter_ou_criar_tesauro_padrao(db_session, pid)
    assert tesauro.project_id == pid
    assert tesauro.name == "Tesauro Geral do Projeto"

    # Termos com variações de plural e caixa
    termos = [
        "desenvolvimento regional",
        "desenvolvimentos regionais",
        "arranjo produtivo local",
        "arranjos produtivos locais",
    ]

    sugestoes = servico.propor_fusoes_automaticas(db_session, tesauro.id, termos, proposed_by="ai")

    assert len(sugestoes) >= 1
    for s in sugestoes:
        # PORTA OBRIGATÓRIA: sugestões nascem SEM aprovação
        assert s.approved_by is None
        assert s.approved_at is None
        assert s.proposed_by == "ai"


def test_tesauro_nao_funde_sem_aprovacao_humana(db_session):
    """Garante que entradas de tesauro em rascunho não são aplicadas para unificar termos."""
    pid = "proj-tesauro-2"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Aprovacao", methodology="PRISMA"))
    db_session.commit()

    servico = ServicoDeTesauro()
    tesauro = servico.obter_ou_criar_tesauro_padrao(db_session, pid)

    # Adiciona entrada EM RASCUNHO (não aprovada)
    entrada_rascunho = servico.adicionar_entrada(
        db_session,
        thesaurus_id=tesauro.id,
        preferred_term="política pública territorial",
        variants=["políticas públicas territoriais", "política territorial"],
        approved_by=None,
    )

    entradas_aprovadas = servico.listar_entradas(db_session, tesauro.id, apenas_aprovadas=True)
    assert len(entradas_aprovadas) == 0

    termos_originais = ["políticas públicas territoriais", "desenvolvimento"]
    termos_processados = servico.aplicar_tesauro(termos_originais, entradas_aprovadas)

    # Como não houve aprovação, o termo original permanece intacto (não funde)
    assert termos_processados == termos_originais


def test_aplicacao_tesauro_substitui_variantes_aprovadas(db_session):
    """Valida a unificação determinística após aprovação formal pelo pesquisador."""
    pid = "proj-tesauro-3"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Unificacao", methodology="PRISMA"))
    db_session.commit()

    servico = ServicoDeTesauro()
    tesauro = servico.obter_ou_criar_tesauro_padrao(db_session, pid)

    # Adiciona e aprova entrada
    entrada = servico.adicionar_entrada(
        db_session,
        thesaurus_id=tesauro.id,
        preferred_term="Arranjo Produtivo Local",
        variants=["arranjos produtivos locais", "APL", "APLs"],
        approved_by="user-123",
    )

    entradas_aprovadas = servico.listar_entradas(db_session, tesauro.id, apenas_aprovadas=True)
    assert len(entradas_aprovadas) == 1

    termos_brutos = ["arranjos produtivos locais", "Inovação", "APLs", "outro termo"]
    termos_unificados = servico.aplicar_tesauro(termos_brutos, entradas_aprovadas)

    assert termos_unificados == ["Arranjo Produtivo Local", "Inovação", "Arranjo Produtivo Local", "outro termo"]
