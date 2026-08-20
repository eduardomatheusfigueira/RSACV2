#!/usr/bin/env python

"""
Testes do serviço de B.I. e bibliometria (doc 31, doc 32, doc 33 Fase 0).

Cobre cada agregado do payload com um projeto de fixture variado (decisões,
critérios, fontes, status de PDF), o caso de projeto vazio (nada deve
quebrar) e a normalização de nomes de autor/periódico (doc 32 §4).
"""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    AuditLogModel,
    CriterionModel,
    ExtractionAnswerModel,
    ExtractionQuestionModel,
    HarvestRunModel,
    PaperCriterionModel,
    PaperModel,
    PaperSourceModel,
    ProjectModel,
    ProtocolModel,
)
from app.services.insights_service import _dividir_autores, _ranking, get_project_insights


def _novo_projeto(db_session, titulo="Projeto de indicadores"):
    proj = ProjectModel(title=titulo, methodology="PRISMA-P")
    db_session.add(proj)
    db_session.flush()
    proto = ProtocolModel(project_id=proj.id, objective="Obj")
    db_session.add(proto)
    db_session.flush()
    return proj, proto


# ── Divisão e normalização de nomes (doc 32 §4) ────────────────────────

def test_divide_autores_pelo_separador_dos_harvesters():
    assert _dividir_autores("Silva, J.; Costa, M.; Pereira, A.") == [
        "Silva, J.",
        "Costa, M.",
        "Pereira, A.",
    ]


def test_divide_autores_nao_quebra_sobrenome_inicial_por_virgula():
    """
    "Silva, J." é UM autor no formato Sobrenome, Inicial — sem "; " no campo,
    o texto inteiro é tratado como um único nome, não dividido pela vírgula.
    """
    assert _dividir_autores("Silva, J.") == ["Silva, J."]


def test_divide_autores_vazio():
    assert _dividir_autores("") == []
    assert _dividir_autores(None) == []


def test_ranking_agrupa_variantes_de_caixa_e_espaco():
    """
    "Universidade de São Paulo" e " universidade  de são paulo " são o mesmo
    grupo — mas o rótulo exibido é a grafia mais frequente, não a chave
    normalizada.
    """
    itens = _ranking([
        "Universidade de São Paulo",
        " universidade  de são paulo ",
        "Universidade de São Paulo",
        "UFRJ",
    ])
    assert itens[0]["name"] == "Universidade de São Paulo"
    assert itens[0]["count"] == 3
    assert itens[1]["name"] == "UFRJ"
    assert itens[1]["count"] == 1


def test_ranking_descarta_strings_vazias():
    assert _ranking(["", "  ", "Autor A"]) == [{"name": "Autor A", "count": 1}]


# ── Projeto vazio: nada deve quebrar (doc 33 Fase 0) ───────────────────

def test_projeto_vazio_devolve_agregados_zerados(db_session):
    proj, _ = _novo_projeto(db_session, "Projeto vazio")
    db_session.commit()

    dados = get_project_insights(db_session, proj.id)

    assert dados["criteria_funnel"] == []
    assert dados["composition_by_decision"] == {}
    assert dados["composition_by_source"] == []
    assert dados["composition_by_year"] == []
    assert dados["top_journals"] == []
    assert dados["top_authors"] == []
    assert dados["top_institutions"] == []
    assert dados["pdf_health"]["by_status"] == {}
    assert dados["pdf_health"]["scanned_ratio"] is None
    assert dados["pdf_health"]["extraction_completeness"] is None


# ── Projeto com dado variado ────────────────────────────────────────────

@pytest.fixture
def projeto_populado(db_session):
    proj, proto = _novo_projeto(db_session, "Território e políticas públicas")

    crit_inc = CriterionModel(
        protocol_id=proto.id, text="Estudo brasileiro", is_exclusion=False, order=0
    )
    crit_exc = CriterionModel(
        protocol_id=proto.id, text="Anterior a 2010", is_exclusion=True, order=1
    )
    db_session.add_all([crit_inc, crit_exc])
    db_session.flush()

    pergunta = ExtractionQuestionModel(protocol_id=proto.id, text="Qual o método?", order=0)
    db_session.add(pergunta)
    db_session.flush()

    papers = [
        PaperModel(
            project_id=proj.id, title="Incluído 1", authors="Silva, J.; Costa, M.",
            journal="Revista Brasileira de Território", institution="UFRJ", year="2020",
            research_type="Estudo de caso", decision=Decision.INCLUDED.value,
            pdf_status="obtido", pdf_is_scanned=False,
        ),
        PaperModel(
            project_id=proj.id, title="Incluído 2", authors="Silva, J.",
            journal="Revista Brasileira de Território", institution="UFRJ", year="2021",
            research_type="Estudo de caso", decision=Decision.INCLUDED.value,
            pdf_status="obtido", pdf_is_scanned=True,
        ),
        PaperModel(
            project_id=proj.id, title="Excluído 1", authors="Pereira, A.",
            journal="Outra Revista", institution="USP", year="2019",
            decision=Decision.EXCLUDED.value, pdf_status="ausente",
        ),
        PaperModel(
            project_id=proj.id, title="Pendente 1", authors="Costa, M.",
            journal="Outra Revista", institution="USP", year="2022",
            decision=Decision.PENDING.value, pdf_status="falhou",
        ),
        PaperModel(
            project_id=proj.id, title="Duplicata (ignorado)", authors="Ninguém",
            journal="X", institution="Y", year="2020",
            decision=Decision.INCLUDED.value, is_duplicate=True,
        ),
    ]
    db_session.add_all(papers)
    db_session.flush()

    p1, p2, p3, p4, _dup = papers

    db_session.add_all([
        PaperSourceModel(paper_id=p1.id, source_name="SciELO"),
        PaperSourceModel(paper_id=p2.id, source_name="SciELO"),
        PaperSourceModel(paper_id=p3.id, source_name="BDTD"),
        PaperSourceModel(paper_id=p4.id, source_name="SciELO"),
    ])
    db_session.add_all([
        PaperCriterionModel(paper_id=p1.id, criterion_id=crit_inc.id, value=True),
        PaperCriterionModel(paper_id=p1.id, criterion_id=crit_exc.id, value=False),
        PaperCriterionModel(paper_id=p2.id, criterion_id=crit_inc.id, value=True),
        PaperCriterionModel(paper_id=p2.id, criterion_id=crit_exc.id, value=False),
        PaperCriterionModel(paper_id=p3.id, criterion_id=crit_inc.id, value=False),
        PaperCriterionModel(paper_id=p3.id, criterion_id=crit_exc.id, value=True),
    ])
    db_session.add(
        ExtractionAnswerModel(paper_id=p1.id, question_id=pergunta.id, answer="Qualitativo")
    )
    # p2 (incluído) fica sem resposta — completude deve refletir 1 de 2.
    db_session.add(HarvestRunModel(
        project_id=proj.id, source_name="SciELO", records_found=3, records_duplicate=1,
    ))
    db_session.commit()

    return proj, proto, {"p1": p1, "p2": p2, "p3": p3, "p4": p4}


def test_composicao_por_decisao(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id)
    # A duplicata não entra na contagem.
    assert dados["composition_by_decision"] == {
        Decision.INCLUDED.value: 2,
        Decision.EXCLUDED.value: 1,
        Decision.PENDING.value: 1,
    }


def test_composicao_por_base_cruza_encontrados_e_incluidos(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id)
    por_base = {item["source_name"]: item for item in dados["composition_by_source"]}

    assert por_base["SciELO"]["found_count"] == 3
    assert por_base["SciELO"]["included_count"] == 2
    assert por_base["BDTD"]["found_count"] == 1
    assert por_base["BDTD"]["included_count"] == 0


def test_composicao_por_base_ignora_filtro_de_decisao(db_session, projeto_populado):
    """Doc 32 §3.2: volume por base é agregado de processo, não de conteúdo."""
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id, decision=Decision.EXCLUDED.value)
    por_base = {item["source_name"]: item for item in dados["composition_by_source"]}
    assert por_base["SciELO"]["found_count"] == 3


def test_funil_de_criterios_conta_atende_e_nao_atende(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id)
    funil = {item["text"]: item for item in dados["criteria_funnel"]}

    assert funil["Estudo brasileiro"]["met_count"] == 2
    assert funil["Estudo brasileiro"]["not_met_count"] == 1
    assert funil["Estudo brasileiro"]["is_exclusion"] is False

    assert funil["Anterior a 2010"]["met_count"] == 1
    assert funil["Anterior a 2010"]["not_met_count"] == 2
    assert funil["Anterior a 2010"]["is_exclusion"] is True


def test_funil_de_criterios_ignora_filtro_de_decisao(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id, decision=Decision.EXCLUDED.value)
    funil = {item["text"]: item for item in dados["criteria_funnel"]}
    # Continua contando os três artigos avaliados, não só o Excluído.
    assert funil["Estudo brasileiro"]["evaluated_count"] == 3


def test_funil_de_criterios_ordena_por_impacto(db_session):
    """
    Doc 33 Fase 2: o critério que mais tirou artigo do caminho vem primeiro —
    não a ordem de cadastro no protocolo. Impacto de um critério de exclusão
    é `met_count` (atender = ser excluído); de um critério de inclusão é
    `not_met_count` (não atender = ser barrado). Cenário com valores bem
    distintos para não depender de empate.
    """
    proj, proto = _novo_projeto(db_session, "Projeto de impacto")

    pouco_impacto = CriterionModel(
        protocol_id=proto.id, text="Critério de baixo impacto", is_exclusion=False, order=0
    )
    muito_impacto = CriterionModel(
        protocol_id=proto.id, text="Critério de alto impacto", is_exclusion=True, order=1
    )
    db_session.add_all([pouco_impacto, muito_impacto])
    db_session.flush()

    papers = [
        PaperModel(project_id=proj.id, title=f"Artigo {i}", decision=Decision.PENDING.value)
        for i in range(4)
    ]
    db_session.add_all(papers)
    db_session.flush()

    # Baixo impacto: só 1 de 4 falha o critério de inclusão (not_met_count=1).
    # Alto impacto: 3 de 4 atendem o critério de exclusão (met_count=3).
    avaliacoes = [
        PaperCriterionModel(paper_id=papers[0].id, criterion_id=pouco_impacto.id, value=True),
        PaperCriterionModel(paper_id=papers[1].id, criterion_id=pouco_impacto.id, value=True),
        PaperCriterionModel(paper_id=papers[2].id, criterion_id=pouco_impacto.id, value=True),
        PaperCriterionModel(paper_id=papers[3].id, criterion_id=pouco_impacto.id, value=False),
        PaperCriterionModel(paper_id=papers[0].id, criterion_id=muito_impacto.id, value=True),
        PaperCriterionModel(paper_id=papers[1].id, criterion_id=muito_impacto.id, value=True),
        PaperCriterionModel(paper_id=papers[2].id, criterion_id=muito_impacto.id, value=True),
        PaperCriterionModel(paper_id=papers[3].id, criterion_id=muito_impacto.id, value=False),
    ]
    db_session.add_all(avaliacoes)
    db_session.commit()

    dados = get_project_insights(db_session, proj.id)
    textos_em_ordem = [item["text"] for item in dados["criteria_funnel"]]
    assert textos_em_ordem == ["Critério de alto impacto", "Critério de baixo impacto"]


def test_rankings_respeitam_filtro_de_decisao_padrao_incluido(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id)

    autores = {item["name"]: item["count"] for item in dados["top_authors"]}
    assert autores["Silva, J."] == 2
    assert "Pereira, A." not in autores  # é do artigo Excluído

    periodicos = {item["name"]: item["count"] for item in dados["top_journals"]}
    assert periodicos["Revista Brasileira de Território"] == 2
    assert "Outra Revista" not in periodicos


def test_rankings_respeitam_filtro_explicito_de_decisao(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id, decision=Decision.EXCLUDED.value)

    autores = {item["name"]: item["count"] for item in dados["top_authors"]}
    assert autores == {"Pereira, A.": 1}


def test_rankings_respeitam_filtro_de_base(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id, source="BDTD")
    # Nenhum incluído veio de BDTD.
    assert dados["top_authors"] == []


def test_rankings_respeitam_recorte_de_ano(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id, year_from=2021, year_to=2021)
    autores = {item["name"] for item in dados["top_authors"]}
    assert autores == {"Silva, J."}  # só "Incluído 2" (2021)


def test_composicao_temporal_e_por_tipo(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id)
    anos = {item["year"]: item["count"] for item in dados["composition_by_year"]}
    assert anos == {"2020": 1, "2021": 1}
    tipos = {item["name"]: item["count"] for item in dados["composition_by_research_type"]}
    assert tipos == {"Estudo de caso": 2}


def test_saude_de_pdf_e_completude_de_extracao(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id)
    saude = dados["pdf_health"]

    assert saude["by_status"] == {"obtido": 2}
    assert saude["scanned_ratio"] == pytest.approx(0.5)  # 1 de 2 obtidos é escaneado
    # 1 resposta de 2 perguntas possíveis entre os 2 incluídos (1 pergunta cadastrada).
    assert saude["extraction_completeness"] == pytest.approx(0.5)


def test_completude_de_extracao_ignora_filtro_de_decisao(db_session, projeto_populado):
    """Doc 32 §6.4: completude é sempre sobre os Incluídos, não sobre o filtro."""
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id, decision=Decision.EXCLUDED.value)
    assert dados["pdf_health"]["extraction_completeness"] == pytest.approx(0.5)


def test_prisma_reaproveita_o_mesmo_calculo_do_export(db_session, projeto_populado):
    from app.services.export_service import ExportService

    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id)
    esperado = ExportService.get_prisma_flow_data(db_session, proj.id)
    assert dados["prisma"] == esperado


def test_filters_applied_refletem_o_que_foi_usado(db_session, projeto_populado):
    proj, _, _ = projeto_populado
    dados = get_project_insights(db_session, proj.id, source="SciELO", year_from=2020)
    assert dados["filters_applied"] == {
        "decision": Decision.INCLUDED.value,
        "source": "SciELO",
        "year_from": 2020,
        "year_to": None,
    }


# ── Proveniência de IA (doc 32 §6.5, doc 33 Fase 3) ────────────────────

@pytest.fixture
def projeto_com_auditoria(db_session):
    """Projeto isolado (não `projeto_populado`) para não herdar decisões sem
    auditoria — os totais de proveniência de IA precisam ser exatos."""
    proj, proto = _novo_projeto(db_session, "Projeto com auditoria de IA")

    papers = [
        PaperModel(
            project_id=proj.id, title=f"Artigo {i}",
            decision=Decision.INCLUDED.value, ai_confidence=conf,
        )
        for i, conf in enumerate([0.95, 0.92, 0.42, None])
    ]
    db_session.add_all(papers)
    db_session.flush()
    p_ia_1, p_ia_2, p_ia_3, p_manual = papers

    db_session.add_all([
        # Duas decisões assistidas pela pesquisadora Ana, uma delas inválida.
        AuditLogModel(
            paper_id=p_ia_1.id, action="ai_screening", new_value="Incluído",
            source="ai:gemini", username="ana", ai_response_valid=True,
        ),
        AuditLogModel(
            paper_id=p_ia_2.id, action="ai_screening", new_value="Incluído",
            source="ai:gemini", username="ana", ai_response_valid=False,
        ),
        # Uma decisão assistida revisada por Bruno, válida.
        AuditLogModel(
            paper_id=p_ia_3.id, action="ai_screening", new_value="Pendente",
            source="ai:qwen", username="bruno", ai_response_valid=True,
        ),
        # Uma decisão manual de Bruno.
        AuditLogModel(
            paper_id=p_manual.id, action="decision_changed", new_value="Incluído",
            source="manual", username="bruno",
        ),
        # Ação que não é decisão de triagem — não deve contar em nada aqui.
        AuditLogModel(
            paper_id=p_manual.id, action="observations_changed", new_value="nota",
            source="manual", username="bruno",
        ),
    ])
    db_session.commit()
    return proj, proto


def test_throughput_por_usuario_conta_decisoes_por_pessoa(db_session, projeto_com_auditoria):
    proj, _ = projeto_com_auditoria
    dados = get_project_insights(db_session, proj.id)
    throughput = {
        item["name"]: item["count"] for item in dados["ai_provenance"]["throughput_by_user"]
    }
    assert throughput == {"ana": 2, "bruno": 2}


def test_decisoes_por_origem_classifica_ia_e_manual(db_session, projeto_com_auditoria):
    proj, _ = projeto_com_auditoria
    dados = get_project_insights(db_session, proj.id)
    assert dados["ai_provenance"]["decisions_by_origin"] == {"Assistida por IA": 3, "Manual": 1}


def test_taxa_de_resposta_invalida_so_conta_eventos_de_ia_screening(
    db_session, projeto_com_auditoria
):
    proj, _ = projeto_com_auditoria
    dados = get_project_insights(db_session, proj.id)
    # 1 de 3 eventos ai_screening foi inválida — a decisão manual não entra
    # no denominador, só a assistida.
    assert dados["ai_provenance"]["ai_invalid_response_rate"] == pytest.approx(1 / 3)


def test_taxa_de_resposta_invalida_e_none_sem_triagem_assistida(db_session):
    proj, _ = _novo_projeto(db_session, "Projeto sem IA")
    db_session.commit()
    dados = get_project_insights(db_session, proj.id)
    assert dados["ai_provenance"]["ai_invalid_response_rate"] is None
    assert dados["ai_provenance"]["throughput_by_user"] == []
    assert dados["ai_provenance"]["decisions_by_origin"] == {}
    assert dados["ai_provenance"]["ai_confidence_distribution"] == []


def test_distribuicao_de_confianca_agrupa_em_faixas_de_decimo(db_session, projeto_com_auditoria):
    proj, _ = projeto_com_auditoria
    dados = get_project_insights(db_session, proj.id)
    faixas = {
        item["name"]: item["count"]
        for item in dados["ai_provenance"]["ai_confidence_distribution"]
    }
    # 0.95 e 0.92 caem em 0.9–1.0; 0.42 cai em 0.4–0.5; o paper sem
    # ai_confidence (None) não entra em faixa nenhuma.
    assert faixas == {"0.9–1.0": 2, "0.4–0.5": 1}


def test_proveniencia_de_ia_ignora_filtro_de_decisao(db_session, projeto_com_auditoria):
    """Doc 32 §3.2: agregado de processo, sempre sobre o projeto inteiro."""
    proj, _ = projeto_com_auditoria
    dados = get_project_insights(db_session, proj.id, decision=Decision.EXCLUDED.value)
    assert dados["ai_provenance"]["decisions_by_origin"] == {"Assistida por IA": 3, "Manual": 1}


# ── Endpoint (autenticação e validação) ─────────────────────────────────

@pytest.mark.anyio
async def test_endpoint_exige_sessao(anon_client, projeto_populado):
    proj, _, _ = projeto_populado
    resposta = await anon_client.get(f"/api/v1/projects/{proj.id}/insights")
    assert resposta.status_code == 401


@pytest.mark.anyio
async def test_endpoint_devolve_404_para_projeto_inexistente(async_client):
    resposta = await async_client.get("/api/v1/projects/inexistente/insights")
    assert resposta.status_code == 404


@pytest.mark.anyio
async def test_endpoint_recusa_decisao_fora_do_vocabulario(async_client, projeto_populado):
    proj, _, _ = projeto_populado
    resposta = await async_client.get(
        f"/api/v1/projects/{proj.id}/insights", params={"decision": "Talvez"}
    )
    assert resposta.status_code == 422


@pytest.mark.anyio
async def test_endpoint_aplica_filtros_via_query(async_client, projeto_populado):
    proj, _, _ = projeto_populado
    resposta = await async_client.get(
        f"/api/v1/projects/{proj.id}/insights", params={"decision": "Excluído"}
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["filters_applied"]["decision"] == "Excluído"
    assert {item["name"] for item in corpo["top_authors"]} == {"Pereira, A."}
