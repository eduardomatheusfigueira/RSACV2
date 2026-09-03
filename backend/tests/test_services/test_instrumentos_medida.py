#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Testes dos Instrumentos de Medida, Contagem Determinística e Evidências Textuais (doc 48 §6, §12, doc 49 Fase 5)."""

import json
import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibInstrumentoModel,
    BibMedidaModel,
    BibOcorrenciaModel,
    BibTextoModel,
    PaperModel,
    ProjectModel,
)
from app.services.bibliometria.instrumentos import (
    ServicoDeInstrumentos,
    calcular_intervalo_wilson,
    sugerir_lexico_conceitual,
)
from tests.conftest import OWNER_ID_TESTE


def test_sugestao_lexico_retorna_rascunho_com_exclusao_e_motivo():
    sugestao = sugerir_lexico_conceitual(
        conceito="governança regional",
        definicao="Mecanismos de coordenação territorial entre atores públicos e privados.",
    )
    assert sugestao["concept"] == "governança regional"
    assert sugestao["proposed_by"] == "ai"
    assert sugestao["model_used"] == "gemini-2.5-flash"
    assert len(sugestao["prompt_hash"]) == 64

    lex = sugestao["lexicon"]
    assert lex["modo"] == "lema"
    assert len(lex["incluir"]) >= 1
    assert len(lex["excluir"]) >= 1
    assert "motivo" in lex["excluir"][0]
    assert len(lex["excluir"][0]["motivo"]) > 5


def test_rascunho_nao_mede_oficialmente(db_session):
    """PORTA OBRIGATÓRIA (doc 48 §6.1): Instrumento em rascunho recusa medição oficial."""
    pid = "proj-inst-1"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Inst", methodology="PRISMA"))
    db_session.commit()

    servico = ServicoDeInstrumentos()
    inst = servico.criar_instrumento(
        db_session,
        project_id=pid,
        concept="arranjos produtivos locais",
        status="rascunho",
    )

    with pytest.raises(ValueError, match="Instrumento em rascunho não produz número exportável"):
        servico.executar_medicao(db_session, instrument_id=inst.id, project_id=pid, preview=False)

    # Mas em modo preview (para calibragem), a execução é permitida sem salvar medida oficial
    res_prev, ocs_prev = servico.executar_medicao(db_session, instrument_id=inst.id, project_id=pid, preview=True)
    assert res_prev["is_preview"] is True
    # Garante que não gravou BibMedidaModel
    assert db_session.query(BibMedidaModel).filter(BibMedidaModel.instrument_id == inst.id).count() == 0


def test_contagem_e_identica_entre_execucoes(db_session):
    """Garante determinismo estrito (duas execuções sobre o mesmo corpus dão o mesmo resultado)."""
    pid = "proj-inst-2"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Determinismo", methodology="PRISMA"))
    paper1 = PaperModel(id="p-inst-1", project_id=pid, title="Estudo APLs", decision=Decision.INCLUDED.value)
    paper2 = PaperModel(id="p-inst-2", project_id=pid, title="Estudo Sustentabilidade", decision=Decision.INCLUDED.value)
    db_session.add_all([paper1, paper2])

    texto1 = BibTextoModel(
        paper_id=paper1.id,
        pipeline_version="2.0.0",
        pdf_sha256="sha1",
        n_pages=3,
        n_words=500,
        text_clean="Os arranjos produtivos locais promovem a inovação territorial.",
        sections=json.dumps([{"name": "Introdução", "canonical_type": "introducao", "start_page": 1, "end_page": 1, "char_offset": 0, "char_length": 65}]),
    )
    texto2 = BibTextoModel(
        paper_id=paper2.id,
        pipeline_version="2.0.0",
        pdf_sha256="sha2",
        n_pages=4,
        n_words=600,
        text_clean="A sustentabilidade regional depende de arranjos produtivos locais fortes.",
        sections=json.dumps([{"name": "Método", "canonical_type": "metodo", "start_page": 2, "end_page": 2, "char_offset": 0, "char_length": 75}]),
    )
    db_session.add_all([texto1, texto2])
    db_session.commit()

    servico = ServicoDeInstrumentos()
    inst = servico.criar_instrumento(
        db_session,
        project_id=pid,
        concept="Arranjo Produtivo Local",
        lexicon={
            "conceito": "Arranjo Produtivo Local",
            "modo": "lema",
            "incluir": [{"forma": "arranjo produtivo local"}],
            "excluir": [],
            "janela_de_coocorrencia": 10,
        },
        status="aprovado",
        approved_by="user-123",
    )

    # Execução 1
    res1, ocs1 = servico.executar_medicao(db_session, instrument_id=inst.id, project_id=pid)
    # Execução 2
    res2, ocs2 = servico.executar_medicao(db_session, instrument_id=inst.id, project_id=pid)

    assert res1["frequencia_bruta"] == res2["frequencia_bruta"] == 2
    assert res1["frequencia_documental"] == res2["frequencia_documental"] == 2
    assert res1["frequencia_relativa_por_mil"] == res2["frequencia_relativa_por_mil"]
    assert len(ocs1) == len(ocs2) == 2


def test_modo_lema_casa_flexoes_e_exclusao_remove_falso_positivo(db_session):
    """Valida que o modo lema casa plurais e a lista de exclusão descarta homônimos/falsos positivos com motivo."""
    pid = "proj-inst-3"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Lema", methodology="PRISMA"))
    paper = PaperModel(id="p-lema-1", project_id=pid, title="Paper Lema", decision=Decision.INCLUDED.value)
    db_session.add(paper)

    texto = (
        "Analisamos os arranjos produtivos locais em Santa Catarina.\n"
        "Também foi observado um arranjo produtivo local individual isolado sem cooperação."
    )
    db_session.add(
        BibTextoModel(
            paper_id=paper.id,
            pipeline_version="2.0.0",
            pdf_sha256="sha3",
            n_pages=2,
            n_words=300,
            text_clean=texto,
            sections="[]",
        )
    )
    db_session.commit()

    servico = ServicoDeInstrumentos()
    inst = servico.criar_instrumento(
        db_session,
        project_id=pid,
        concept="Arranjo Produtivo Local",
        lexicon={
            "conceito": "Arranjo Produtivo Local",
            "modo": "lema",
            "incluir": [{"forma": "arranjo produtivo local"}],
            "excluir": [
                {
                    "forma": "arranjo produtivo local individual",
                    "motivo": "exclui caso individual sem dinâmica de cooperação coletiva",
                }
            ],
            "janela_de_coocorrencia": 10,
        },
        status="aprovado",
        approved_by="user-123",
    )

    res, ocs = servico.executar_medicao(db_session, instrument_id=inst.id, project_id=pid)

    # Deve casar 'arranjos produtivos locais' (plural via lema), mas descartar 'arranjo produtivo local individual'
    assert res["frequencia_bruta"] == 1
    assert len(ocs) == 1
    assert ocs[0]["matched_form"] == "arranjos produtivos locais"


def test_denominador_conta_documentos_com_e_sem_texto(db_session):
    pid = "proj-inst-4"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Denominador", methodology="PRISMA"))
    # p1 tem texto completo, p2 não tem
    p1 = PaperModel(id="p-den-1", project_id=pid, title="Paper Com Texto", decision=Decision.INCLUDED.value)
    p2 = PaperModel(id="p-den-2", project_id=pid, title="Inovação e governança territorial", abstract="Resumo sobre governança territorial.", decision=Decision.INCLUDED.value)
    db_session.add_all([p1, p2])

    db_session.add(
        BibTextoModel(
            paper_id=p1.id,
            pipeline_version="2.0.0",
            pdf_sha256="sha-den",
            n_pages=5,
            n_words=1000,
            text_clean="A governança territorial é a base do desenvolvimento.",
            sections="[]",
        )
    )
    db_session.commit()

    servico = ServicoDeInstrumentos()
    inst = servico.criar_instrumento(
        db_session,
        project_id=pid,
        concept="governança territorial",
        status="aprovado",
        approved_by="user-123",
    )

    res, ocs = servico.executar_medicao(db_session, instrument_id=inst.id, project_id=pid)

    assert res["n_documents"] == 2
    assert res["n_documents_with_text"] == 1
    assert res["n_documents_without_text"] == 1
    assert res["frequencia_documental"] == 2
    assert res["frequencia_bruta"] == 3


def test_conferencia_amostral_e_intervalo_wilson(db_session):
    p_hat, ic = calcular_intervalo_wilson(k=27, n=30)
    assert p_hat == 0.90
    assert len(ic) == 2
    assert 0.70 < ic[0] < 0.90
    assert 0.90 < ic[1] <= 1.0

    pid = "proj-inst-5"
    db_session.add(ProjectModel(id=pid, owner_id=OWNER_ID_TESTE, title="Projeto Wilson", methodology="PRISMA"))
    db_session.commit()

    servico = ServicoDeInstrumentos()
    inst = servico.criar_instrumento(db_session, project_id=pid, concept="Políticas Públicas", status="aprovado", approved_by="u1")
    p_est, ic_est = servico.registrar_julgamento_amostra(db_session, instrument_id=inst.id, acertos_positivos=26, total_avaliados=30)

    assert p_est == round(26 / 30, 4)
    assert inst.estimated_precision == p_est
    assert json.loads(inst.precision_ci) == ic_est
