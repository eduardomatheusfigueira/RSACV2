#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Schemas do Ambiente de Indicadores (docs 47, 48, 49)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import Decision

#: O mesmo padrão do serviço (`instantaneo.Escopo`) e da aba de Indicadores.
DECISAO_PADRAO = Decision.INCLUDED.value


class EscopoDoInstantaneo(BaseModel):
    """Os filtros que definiram o corpus — os mesmos da aba de Indicadores.

    `decision` nasce em `Incluído`, o mesmo padrão do serviço e da aba: é a
    bibliometria **da revisão**. Passar `null` explicitamente abre o escopo
    para o acervo pós-deduplicação inteiro, que é a bibliometria **do campo** —
    outra análise, igualmente legítima (doc 48 §3.4).

    Os dois padrões precisam coincidir. Enquanto o schema abria em `null` e o
    serviço em `Incluído`, o mesmo pedido produzia corpora diferentes conforme
    o caminho — um instantâneo de 16.578 documentos onde se esperava a amostra
    incluída.
    """

    decision: str | None = DECISAO_PADRAO
    source: str | None = None
    year_from: int | None = None
    year_to: int | None = None


class CriarInstantaneo(BaseModel):
    rotulo: str = Field("", max_length=200, description="Como reconhecer este instantâneo depois")
    escopo: EscopoDoInstantaneo = Field(default_factory=EscopoDoInstantaneo)


class Instantaneo(BaseModel):
    """O corpus congelado (doc 48 §3).

    `corpus_hash` é a identidade do conjunto: dois instantâneos com o mesmo
    hash descrevem exatamente os mesmos documentos, com o mesmo conteúdo.
    """

    id: str
    project_id: str
    label: str
    scope: EscopoDoInstantaneo
    n_documents: int
    corpus_hash: str
    engine_version: str
    created_at: datetime | None = None


class ConferenciaDoInstantaneo(BaseModel):
    """O que mudou no acervo desde o congelamento (doc 48 §3.3).

    Três desfechos, e os três são informação. O que não pode acontecer — e era
    o comportamento anterior — é a tela mostrar um número diferente do de
    ontem sem dizer que o corpus mudou.
    """

    #: `identico` | `conteudo_alterado` | `conjunto_alterado`
    estado: str
    #: Se os números derivados deste instantâneo ainda descrevem o acervo.
    confiavel: bool
    documentos_alterados: list[str] = []
    documentos_adicionados: list[str] = []
    documentos_removidos: list[str] = []


class Proveniencia(BaseModel):
    """O carimbo que acompanha todo número derivado (doc 48 §14.4)."""

    snapshot_id: str
    corpus_hash: str
    n_documents: int
    scope: EscopoDoInstantaneo
    engine_version: str
    frozen_at: str | None = None


class UltimoEnriquecimento(BaseModel):
    id: str
    provider: str
    started_at: str | None = None
    completed_at: str | None = None
    n_consulted: int
    n_found: int
    status: str


class SituacaoEnriquecimento(BaseModel):
    """Situação e cobertura de enriquecimento externo do projeto."""

    project_id: str
    total_papers: int
    papers_with_doi: int
    papers_enriched: int
    papers_pending: int
    coverage_pct: float
    last_enrichment: UltimoEnriquecimento | None = None


# ── Indicadores Bibliométricos Nível 0 e 1 (Fase 3) ───────────────────


class ProducaoAnoItem(BaseModel):
    year: int
    count: int
    growth_yoy_pct: float | None = None


class ProducaoTemporalMetrics(BaseModel):
    series: list[ProducaoAnoItem] = []
    cagr_pct: float | None = None
    year_start: int | None = None
    year_end: int | None = None
    total_period: int = 0


class BradfordPeriodicoItem(BaseModel):
    name: str
    count: int


class BradfordZone(BaseModel):
    zone: int
    name: str
    journals: list[BradfordPeriodicoItem] = []
    total_articles: int
    n_journals: int
    pct_articles: float | None = None


class BradfordMetrics(BaseModel):
    total_journals: int
    total_articles: int
    zones: list[BradfordZone] = []
    k_multiplier: float | None = None
    formula_ratio: str = ""
    #: `False` quando o recorte não tem periódicos para as três zonas.
    #:
    #: Sem esta marca, um único periódico saía na tela como "Zona 1 (Núcleo):
    #: 1 periódico, 100%" e razão "1 : 0 : 0", com cara de resultado.
    confiavel: bool = True
    #: Por que a partição não foi feita — texto pronto para a interface.
    motivo: str = ""


class LotkaDistribuicaoItem(BaseModel):
    articles: int
    authors_observed: int
    authors_expected: float
    pct_observed: float
    pct_expected: float


class LotkaMetrics(BaseModel):
    n_authors: int
    alpha: float | None = None
    c_constant: float | None = None
    d_ks: float | None = None
    d_critical: float | None = None
    #: `None` quando a amostra não decide.
    #:
    #: São três estados, e não dois: aceita, rejeitada e "o teste não tem poder
    #: com esta amostra". Enquanto era `bool`, 17 autores produziam
    #: "Aderência aceita" — e, depois que o serviço passou a devolver `None`,
    #: este mesmo campo derrubava a rota inteira com 500.
    is_adherent: bool | None = False
    #: A amostra atinge o piso do teste (ver `AUTORES_MINIMOS_PARA_ADERENCIA`).
    sample_ok: bool = True
    p_verdict: str = ""
    distribution: list[LotkaDistribuicaoItem] = []


class CoautoriaDistribuicaoItem(BaseModel):
    num_authors: int
    count: int
    pct: float


class ColaboracaoMetrics(BaseModel):
    total_articles: int
    single_author_articles: int
    multi_author_articles: int
    no_author_articles: int = 0
    subramanyam_index: float | None = None
    avg_authors_per_paper: float = 0.0
    max_authors: int = 0
    distribution: list[CoautoriaDistribuicaoItem] = []


class ConcentracaoMetrics(BaseModel):
    gini_authors: float | None = None
    gini_journals: float | None = None
    hhi_journals: float | None = None


class MultiSourceDistribuicaoItem(BaseModel):
    num_sources: int
    count: int
    pct: float


class SobreposicaoMetrics(BaseModel):
    sources: list[str] = []
    exclusive_counts: dict[str, int] = {}
    overlap_matrix: dict[str, dict[str, int]] = {}
    multi_source_distribution: list[MultiSourceDistribuicaoItem] = []
    total_papers: int = 0


class CitationBandItem(BaseModel):
    label: str
    min: float
    max: float | None = None
    count: int
    pct: float


class CitacoesMetrics(BaseModel):
    total_citations: int
    mean_citations: float
    median_citations: float
    h_index: int
    max_citations: int
    citation_bands: list[CitationBandItem] = []
    papers_with_citation_data: int = 0


class OpenAccessStatusItem(BaseModel):
    status: str
    count: int
    pct: float


class AcessoAbertoMetrics(BaseModel):
    total_evaluated: int
    open_access_count: int
    open_access_pct: float
    by_status: list[OpenAccessStatusItem] = []


class PaisItem(BaseModel):
    country: str
    count: int


class IndicadoresBibliometricosResponse(BaseModel):
    """Resposta estruturada dos Indicadores Bibliométricos de Nível 0 e 1 (doc 48 §7)."""

    project_id: str
    total_papers: int
    provenance: Proveniencia | None = None
    production_temporal: ProducaoTemporalMetrics
    bradford: BradfordMetrics
    lotka: LotkaMetrics
    collaboration: ColaboracaoMetrics
    concentration: ConcentracaoMetrics
    source_overlap: SobreposicaoMetrics
    citations: CitacoesMetrics
    open_access: AcessoAbertoMetrics
    countries: list[PaisItem] = []


# ── Camada de Texto e Tesauro (Fase 4, doc 48 §5, §12) ──────────────────


class SecaoItem(BaseModel):
    name: str
    canonical_type: str
    start_page: int
    end_page: int
    char_offset: int
    char_length: int


class BibTextoResponse(BaseModel):
    paper_id: str
    pipeline_version: str
    pdf_sha256: str | None = None
    n_pages: int
    n_words: int
    sections: list[SecaoItem] = []
    extracted_at: str | None = None


class TesauroCreate(BaseModel):
    name: str
    description: str = ""


class TesauroResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    created_by: str | None = None
    created_at: str | None = None


class TesauroEntryCreate(BaseModel):
    preferred_term: str
    variants: list[str] = []
    scope: str = ""


class TesauroEntryResponse(BaseModel):
    id: str
    thesaurus_id: str
    preferred_term: str
    variants: list[str] = []
    scope: str
    proposed_by: str
    approved_by: str | None = None
    approved_at: str | None = None
    created_at: str | None = None


class AprovarEntradasBatch(BaseModel):
    entry_ids: list[str]


# ── Instrumentos de Medida e Evidências (Fase 5, doc 48 §6, §12) ─────────


class TermoInclusao(BaseModel):
    forma: str
    tipo: str = "expressao"
    idioma: str = "pt"


class TermoExclusao(BaseModel):
    forma: str
    motivo: str  # Campo obrigatório: justificativa metodológica


class LexicoPayload(BaseModel):
    conceito: str
    definicao: str = ""
    modo: str = "lema"  # lema, literal, regex
    incluir: list[TermoInclusao] = []
    excluir: list[TermoExclusao] = []
    janela_de_coocorrencia: int = 10


class SugerirLexicoRequest(BaseModel):
    concept: str
    definition: str = ""
    language: str = "pt"


class SugerirLexicoResponse(BaseModel):
    concept: str
    definition: str
    lexicon: LexicoPayload
    proposed_by: str
    model_used: str | None = None
    prompt_hash: str | None = None


class InstrumentoCreate(BaseModel):
    concept: str
    definition: str = ""
    lexicon: LexicoPayload
    proposed_by: str = "manual"
    model_used: str | None = None
    prompt_hash: str | None = None


class InstrumentoResponse(BaseModel):
    id: str
    project_id: str
    concept: str
    definition: str
    lexicon: LexicoPayload
    version: str
    status: str  # rascunho / aprovado / arquivado
    proposed_by: str
    model_used: str | None = None
    prompt_hash: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    estimated_precision: float | None = None
    precision_ci: list[float] | None = None
    created_at: str | None = None


class MedirRequest(BaseModel):
    snapshot_id: str | None = None
    preview: bool = False


class OcorrenciaResponse(BaseModel):
    id: int | None = None
    paper_id: str
    section: str
    page: int
    char_start: int
    char_end: int
    matched_form: str
    context_snippet: str


class MedidaResultado(BaseModel):
    frequencia_bruta: int
    frequencia_relativa_por_mil: float
    frequencia_documental: int
    frequencia_documental_pct: float
    distribuicao_por_secao: dict[str, int]
    n_documents: int
    n_documents_with_text: int
    n_documents_without_text: int
    total_words_analyzed: int
    is_preview: bool = False
    measurement_id: str | None = None


class MedidaResponse(BaseModel):
    id: str | None = None
    snapshot_id: str | None = None
    instrument_id: str
    instrument_version: str
    result: MedidaResultado
    n_documents: int
    n_documents_with_text: int
    executed_at: str | None = None


class JulgamentoAmostraRequest(BaseModel):
    acertos_positivos: int
    total_avaliados: int


# ── Grafos e Análise Estrutural (Fase 6, doc 48 §8, §12) ─────────────────


class GerarGrafoRequest(BaseModel):
    network_type: str = "coautoria"  # coautoria / coocorrencia_termos / acoplamento_bibliografico / cocitacao
    snapshot_id: str | None = None
    normalizacao: str = "association_strength"  # association_strength / jaccard / cosine
    corte_minimo: int = 1
    max_nos: int = 100
    resolucao_louvain: float = 1.0
    semente: int = 42
    iteracoes_fr: int = 200


class NoGrafo(BaseModel):
    id: str
    label: str
    size: int
    degree: int
    cluster: int
    color: str
    x: float
    y: float


class ArestaGrafo(BaseModel):
    source: str
    target: str
    weight: float
    count: int


class ClusterGrafo(BaseModel):
    count: int
    nodes: list[str]
    color: str


class GrafoResponse(BaseModel):
    id: str
    project_id: str
    snapshot_id: str | None = None
    network_type: str
    parameters: dict[str, Any]
    nodes: list[NoGrafo]
    edges: list[ArestaGrafo]
    coordinates: dict[str, dict[str, float]]
    clusters: dict[str, ClusterGrafo]
    seed: int
    calculated_at: str | None = None


# ── Estatística Sob Demanda (Fase 7, doc 48 §9, §12) ─────────────────────

VOCABULARIO_MEDIDAS = [
    "contagem",
    "distintos",
    "soma",
    "media",
    "mediana",
    "quantil",
    "taxa",
    "desvio_padrao",
]

VOCABULARIO_CAMPOS_NUMERICOS = [
    "citacoes_recebidas",
    "ano",
    "n_palavras",
    "n_paginas",
]

VOCABULARIO_AGRUPADORES = [
    "ano",
    "fonte",
    "decisao",
    "periodico",
    "instituicao",
    "pais",
    "idioma",
    "topico",
    "acesso_aberto",
    "tipo",
    "autor",
]

VOCABULARIO_OPERADORES = [
    "=",
    "!=",
    ">",
    "<",
    ">=",
    "<=",
    "entre",
    "em",
    "contem",
]


class FiltroEspecificacao(BaseModel):
    campo: str
    op: str
    valor: Any


class EspecificacaoEstatistica(BaseModel):
    medida: str  # contagem, distintos, soma, media, mediana, quantil, taxa, desvio_padrao
    campo: str | None = None  # citacoes_recebidas, ano, n_palavras, etc.
    por: list[str] = Field(default_factory=list)  # ano, fonte, decisao, periodico, etc.
    onde: list[FiltroEspecificacao] = Field(default_factory=list)
    ordenar_por: str = "grupo"  # grupo | valor | valor_desc
    limite: int = 50
    quantil_p: float | None = 0.5
    snapshot_id: str | None = None


class InterpretarPerguntaRequest(BaseModel):
    question: str


class InterpretarPerguntaResponse(BaseModel):
    supported: bool
    question: str
    specification: EspecificacaoEstatistica | None = None
    explanation: str
    supported_vocabulary: dict[str, Any] | None = None


class LinhaResultadoEstatistica(BaseModel):
    grupo: dict[str, Any]
    valor: float | int | None
    n_docs: int


class ExecutarEspecificacaoRequest(BaseModel):
    specification: EspecificacaoEstatistica
    snapshot_id: str | None = None


class ExecutarEspecificacaoResponse(BaseModel):
    specification: EspecificacaoEstatistica
    results: list[LinhaResultadoEstatistica]
    total_documents_analyzed: int
    provenance: dict[str, Any]


class SalvarAnaliseRequest(BaseModel):
    question: str
    specification: EspecificacaoEstatistica


class AnaliseSalvaResponse(BaseModel):
    id: str
    project_id: str
    question: str
    specification: EspecificacaoEstatistica
    created_by: str | None = None
    created_at: str | None = None


# ── Indicadores de Vanguarda e Sensibilidade (Fase 8, doc 48 §7.4, §10, §12) ──


class ItemDiagramaEstrategico(BaseModel):
    cluster_id: int
    label: str
    centralidade: float
    densidade: float
    quadrante: str  # motor | basico | especializado | emergente_declinio
    tamanho: int
    palavras_chave: list[str]


class DiagramaEstrategicoResponse(BaseModel):
    items: list[ItemDiagramaEstrategico]
    centralidade_media: float
    densidade_media: float
    provenance: dict[str, Any]


class RajadaTermo(BaseModel):
    termo: str
    peso_rajada: float
    ano_inicio: str
    ano_fim: str
    frequencia_pico: int
    crescimento_pct: float


class RajadasResponse(BaseModel):
    rajadas: list[RajadaTermo]
    parametros: dict[str, Any]
    provenance: dict[str, Any]


class ItemRankingBootstrap(BaseModel):
    posicao: int
    rotulo: str
    valor_estimado: float
    ic_95: list[float]
    empate_com: list[int]
    indistinguivel: bool


class BootstrapRankingsResponse(BaseModel):
    tipo_ranking: str
    items: list[ItemRankingBootstrap]
    n_bootstrap: int
    seed: int
    tem_empates_tecnicos: bool
    aviso_empates: str | None = None
    provenance: dict[str, Any]


class SensibilidadeResolucaoItem(BaseModel):
    resolucao: float
    n_clusters: int
    ari_vs_vigente: float | None
    is_vigente: bool


class SensibilidadeParametrosResponse(BaseModel):
    parametro: str
    valor_vigente: float
    varredura: list[SensibilidadeResolucaoItem]
    diagnostico: str
    provenance: dict[str, Any]


class SubtemaCobertura(BaseModel):
    topico: str
    campo: str
    n_estudos_no_corpus: int
    score_medio: float
    status_cobertura: str  # robusto | moderado | ralo


class CoberturaCampoResponse(BaseModel):
    total_topicos_identificados: int
    topicos_robustos: list[SubtemaCobertura]
    topicos_ralos: list[SubtemaCobertura]
    taxa_cobertura_ampla_pct: float
    diagnostico_metodologico: str
    provenance: dict[str, Any]


# ── Pré-Registro e Relatório BIBLIO (Fase 9, doc 48 §11, §12) ─────────────


class PlanoBibliometricoSchema(BaseModel):
    indicadores_previstos: list[str] = Field(default_factory=list)
    unidade_analise: str = "documento"  # documento | autor | fonte | termo
    janela_temporal: str = ""
    justificativa_janela: str = ""
    cortes_declarados: dict[str, Any] = Field(default_factory=dict)
    tesauro_obrigatorio: bool = True
    status_protocolo: str = "rascunho"  # rascunho | vigente | concluido
    versao_protocolo: str | None = None
    emendas: list[dict[str, Any]] = Field(default_factory=list)


class AtualizarPlanoBibliometricoRequest(BaseModel):
    indicadores_previstos: list[str]
    unidade_analise: str = "documento"
    janela_temporal: str = ""
    justificativa_janela: str = ""
    cortes_declarados: dict[str, Any] = Field(default_factory=dict)
    tesauro_obrigatorio: bool = True


class ItemConformidadeBiblio(BaseModel):
    numero: int
    secao: str
    item: str
    descricao: str
    responsabilidade: str  # sistema | autor
    status: str  # conforme | pendente | nao_aplicavel
    evidencia: str


class RelatorioConformidadeBiblioResponse(BaseModel):
    total_itens: int
    itens_conformes: int
    itens_do_sistema: int
    itens_do_autor: int
    secoes: list[str]
    itens: list[ItemConformidadeBiblio]
    resumo_executivo: str
    provenance: dict[str, Any]








