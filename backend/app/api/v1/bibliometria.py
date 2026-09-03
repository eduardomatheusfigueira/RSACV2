#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Router do Ambiente de Indicadores (docs 47, 48, 49).

Fase 1: instantâneo do corpus. As demais rotas do doc 48 §13 entram nas fases
seguintes, sempre sob este mesmo prefixo e a mesma dependência de titularidade.
"""

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.database import SessionLocal
from app.infrastructure.persistence.models import (
    BibAnaliseModel,
    BibGrafoModel,
    BibInstrumentoModel,
    BibMedidaModel,
    BibOcorrenciaModel,
    BibSnapshotModel,
    BibTextoModel,
    BibThesaurusEntryModel,
    BibThesaurusModel,
    PaperModel,
    ProjectModel,
    UserModel,
)
from app.schemas.bibliometria import (
    AnaliseSalvaResponse,
    AprovarEntradasBatch,
    AtualizarPlanoBibliometricoRequest,
    BibTextoResponse,
    BootstrapRankingsResponse,
    CoberturaCampoResponse,
    ConferenciaDoInstantaneo,
    CriarInstantaneo,
    DiagramaEstrategicoResponse,
    EspecificacaoEstatistica,
    ExecutarEspecificacaoRequest,
    ExecutarEspecificacaoResponse,
    GerarGrafoRequest,
    GrafoResponse,
    IndicadoresBibliometricosResponse,
    Instantaneo,
    InstrumentoCreate,
    InstrumentoResponse,
    InterpretarPerguntaRequest,
    InterpretarPerguntaResponse,
    JulgamentoAmostraRequest,
    LexicoPayload,
    MedidaResponse,
    MedidaResultado,
    MedirRequest,
    OcorrenciaResponse,
    PlanoBibliometricoSchema,
    RajadasResponse,
    RelatorioConformidadeBiblioResponse,
    SalvarAnaliseRequest,
    SensibilidadeParametrosResponse,
    SituacaoEnriquecimento,
    SugerirLexicoRequest,
    SugerirLexicoResponse,
    TesauroCreate,
    TesauroEntryCreate,
    TesauroEntryResponse,
    TesauroResponse,
)
from app.security.dependencies import projeto_do_usuario, require_session
from app.services.bibliometria import (
    ServicoDeAnalises,
    ServicoDeEnriquecimento,
    ServicoDeGrafos,
    ServicoDeInstrumentos,
    ServicoDePreRegistro,
    ServicoDeTesauro,
    ServicoDeVanguarda,
    extrair_e_persistir_texto,
    interpretar_pergunta,
    obter_indicadores_bibliometricos,
    obter_ou_extrair_texto,
    sugerir_lexico_conceitual,
)
from app.services.bibliometria import instantaneo as servico
from app.services.harvesting_service import ws_manager
from app.services.job_manager import AsyncJobManager
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/bibliometria",
    dependencies=[Depends(projeto_do_usuario)],
    tags=["bibliometria"],
)

enrichment_job_manager = AsyncJobManager("um enriquecimento bibliométrico")
servico_enriquecimento = ServicoDeEnriquecimento()
servico_tesauro = ServicoDeTesauro()
servico_instrumentos = ServicoDeInstrumentos()
servico_grafos = ServicoDeGrafos()
servico_analises = ServicoDeAnalises()
servico_vanguarda = ServicoDeVanguarda()
servico_preregistro = ServicoDePreRegistro()
pdf_service = PDFService()



def _para_schema(m: BibSnapshotModel) -> dict:
    return {
        "id": m.id,
        "project_id": m.project_id,
        "label": m.label,
        "scope": json.loads(m.scope or "{}"),
        "n_documents": m.n_documents,
        "corpus_hash": m.corpus_hash,
        "engine_version": m.engine_version,
        "created_at": m.created_at,
    }


def _buscar(db: Session, project_id: str, snapshot_id: str) -> BibSnapshotModel:
    """O instantâneo, conferido contra o projeto da rota.

    O filtro por `project_id` não é redundante com a dependência de
    titularidade: sem ele, quem tem acesso a um projeto leria o instantâneo de
    outro passando o id na URL.
    """
    m = (
        db.query(BibSnapshotModel)
        .filter(
            BibSnapshotModel.id == snapshot_id,
            BibSnapshotModel.project_id == project_id,
        )
        .first()
    )
    if not m:
        raise HTTPException(status_code=404, detail="Instantâneo não encontrado.")
    return m


@router.post("/instantaneos", response_model=Instantaneo, status_code=201)
def criar_instantaneo(
    project_id: str,
    corpo: CriarInstantaneo,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Congela o corpus definido pelo escopo (doc 48 §3).

    O instantâneo não copia o acervo: guarda um manifesto de pares
    `(documento, hash de conteúdo)` e o hash do conjunto. É o que permite,
    depois, dizer exatamente o que mudou — e não apenas que algo mudou.
    """
    if not db.query(ProjectModel).filter(ProjectModel.id == project_id).first():
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")

    criado = servico.criar(
        db,
        project_id,
        escopo=servico.Escopo(**corpo.escopo.model_dump()),
        rotulo=corpo.rotulo,
        criado_por=usuario.id if usuario else None,
    )
    logger.info(
        f"[Bibliometria] Instantâneo {criado.id} do projeto {project_id}: "
        f"{criado.n_documents} documentos, hash {criado.corpus_hash[:12]}."
    )
    return _para_schema(criado)


@router.get("/instantaneos", response_model=list[Instantaneo])
def listar_instantaneos(project_id: str, db: Session = Depends(get_db)):
    """Do mais recente para o mais antigo."""
    encontrados = (
        db.query(BibSnapshotModel)
        .filter(BibSnapshotModel.project_id == project_id)
        .order_by(BibSnapshotModel.created_at.desc())
        .all()
    )
    return [_para_schema(m) for m in encontrados]


@router.get(
    "/instantaneos/{snapshot_id}/conferir", response_model=ConferenciaDoInstantaneo
)
def conferir_instantaneo(project_id: str, snapshot_id: str, db: Session = Depends(get_db)):
    """Recomputa o manifesto e compara com o acervo de agora (doc 48 §3.3)."""
    conferencia = servico.conferir(db, _buscar(db, project_id, snapshot_id))
    return {
        "estado": conferencia.estado,
        "confiavel": conferencia.confiavel,
        "documentos_alterados": list(conferencia.documentos_alterados),
        "documentos_adicionados": list(conferencia.documentos_adicionados),
        "documentos_removidos": list(conferencia.documentos_removidos),
    }


# ─────────────────────────────────────────────────────────────────────
# Enriquecimento OpenAlex / Crossref (doc 48 §4, doc 49 Fase 2)
# ─────────────────────────────────────────────────────────────────────

@router.get("/enriquecimento/situacao", response_model=SituacaoEnriquecimento)
def obter_situacao_enriquecimento(project_id: str, db: Session = Depends(get_db)):
    """Retorna a cobertura de enriquecimento externa atual do projeto."""
    return servico_enriquecimento.obter_situacao(db, project_id)


@router.post("/enriquecimento", status_code=202)
async def iniciar_enriquecimento(
    project_id: str,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Inicia a consulta assíncrona ao OpenAlex em lotes de 50 DOIs (doc 48 §4)."""
    if not db.query(ProjectModel).filter(ProjectModel.id == project_id).first():
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")

    if enrichment_job_manager.is_job_running(project_id):
        raise HTTPException(
            status_code=409,
            detail="Já existe um enriquecimento bibliométrico em andamento para este projeto.",
        )

    user_id = usuario.id if usuario else None

    async def _job():
        async def _on_progresso(evento: dict):
            await ws_manager.broadcast_to_project(project_id, evento)

        with SessionLocal() as session:
            try:
                await servico_enriquecimento.executar_enriquecimento(
                    session,
                    project_id=project_id,
                    user_id=user_id,
                    on_progress=_on_progresso,
                )
            except Exception as e:
                logger.error(f"[Enriquecimento] Erro durante execução do projeto {project_id}: {e}", exc_info=True)
                await ws_manager.broadcast_to_project(
                    project_id,
                    {"type": "enrichment_failed", "project_id": project_id, "error": str(e)},
                )

    enrichment_job_manager.start_job(project_id, _job())
    return {
        "status": "iniciado",
        "message": "Enriquecimento bibliométrico iniciado em segundo plano.",
        "project_id": project_id,
    }


@router.post("/enriquecimento/parar", status_code=200)
async def parar_enriquecimento(project_id: str):
    """Interrompe a rodada ativa de enriquecimento graciosamente."""
    if not enrichment_job_manager.is_job_running(project_id):
        return {"status": "sem_tarefa", "message": "Nenhum enriquecimento em andamento para parar."}

    enrichment_job_manager.cancel_job(project_id)
    return {"status": "parado", "message": "Enriquecimento interrompido com sucesso."}


@router.get("/indicadores", response_model=IndicadoresBibliometricosResponse)
def obter_indicadores(
    project_id: str,
    instantaneo: str | None = None,
    decision: str | None = None,
    source: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    db: Session = Depends(get_db),
):
    """Calcula indicadores bibliométricos de Nível 0 e 1 (Bradford, Lotka, Subramanyam, Gini/HHI, Citações)."""
    try:
        return obter_indicadores_bibliometricos(
            db,
            project_id=project_id,
            snapshot_id=instantaneo,
            decision=decision,
            source=source,
            year_from=year_from,
            year_to=year_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Camada de Texto e Tesauro (Fase 4, doc 48 §5, §12) ──────────────────


@router.get("/textos/{paper_id}", response_model=BibTextoResponse)
def obter_texto_do_artigo(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Obtém os metadados de texto limpo e seções IMRaD de um artigo."""
    texto = db.query(BibTextoModel).filter(BibTextoModel.paper_id == paper_id).first()
    if not texto:
        # Tenta obter ou extrair do arquivo em disco
        texto = obter_ou_extrair_texto(db, paper_id, project_id, pdf_service=pdf_service)
        if not texto:
            raise HTTPException(status_code=404, detail=f"Texto do artigo '{paper_id}' não encontrado.")

    secoes = []
    try:
        secoes = json.loads(texto.sections)
    except Exception:
        pass

    return {
        "paper_id": texto.paper_id,
        "pipeline_version": texto.pipeline_version,
        "pdf_sha256": texto.pdf_sha256,
        "n_pages": texto.n_pages,
        "n_words": texto.n_words,
        "sections": secoes,
        "extracted_at": texto.extracted_at.isoformat() if texto.extracted_at else None,
    }


@router.post("/textos/{paper_id}/extrair", response_model=BibTextoResponse)
def extrair_texto_do_artigo(
    project_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
):
    """Força extração e persistência do texto e seções IMRaD a partir do PDF."""
    caminho = pdf_service.get_pdf_path(project_id, paper_id)
    if not caminho or not caminho.exists():
        raise HTTPException(status_code=404, detail=f"PDF do artigo '{paper_id}' não encontrado em disco.")

    with open(caminho, "rb") as f:
        pdf_bytes = f.read()

    texto = extrair_e_persistir_texto(db, paper_id, pdf_bytes)
    secoes = []
    try:
        secoes = json.loads(texto.sections)
    except Exception:
        pass

    return {
        "paper_id": texto.paper_id,
        "pipeline_version": texto.pipeline_version,
        "pdf_sha256": texto.pdf_sha256,
        "n_pages": texto.n_pages,
        "n_words": texto.n_words,
        "sections": secoes,
        "extracted_at": texto.extracted_at.isoformat() if texto.extracted_at else None,
    }


@router.get("/tesauros", response_model=list[TesauroResponse])
def listar_tesauros(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Lista os tesauros e vocabulários controlados do projeto."""
    t_padrao = servico_tesauro.obter_ou_criar_tesauro_padrao(db, project_id)
    tesauros = db.query(BibThesaurusModel).filter(BibThesaurusModel.project_id == project_id).all()
    return [
        {
            "id": t.id,
            "project_id": t.project_id,
            "name": t.name,
            "description": t.description,
            "created_by": t.created_by,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tesauros
    ]


@router.post("/tesauros", response_model=TesauroResponse, status_code=201)
def criar_tesauro(
    project_id: str,
    payload: TesauroCreate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Cria um novo tesauro no projeto."""
    novo = BibThesaurusModel(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        created_by=usuario.id if usuario else None,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {
        "id": novo.id,
        "project_id": novo.project_id,
        "name": novo.name,
        "description": novo.description,
        "created_by": novo.created_by,
        "created_at": novo.created_at.isoformat() if novo.created_at else None,
    }


@router.get("/tesauros/{tesauro_id}/entradas", response_model=list[TesauroEntryResponse])
def listar_entradas_tesauro(
    project_id: str,
    tesauro_id: str,
    apenas_aprovadas: bool = False,
    db: Session = Depends(get_db),
):
    """Lista as entradas de um tesauro com suas variantes mapeadas."""
    entradas = servico_tesauro.listar_entradas(db, thesaurus_id=tesauro_id, apenas_aprovadas=apenas_aprovadas)
    res = []
    for e in entradas:
        vars_list = []
        try:
            vars_list = json.loads(e.variants)
        except Exception:
            pass
        res.append(
            {
                "id": e.id,
                "thesaurus_id": e.thesaurus_id,
                "preferred_term": e.preferred_term,
                "variants": vars_list,
                "scope": e.scope,
                "proposed_by": e.proposed_by,
                "approved_by": e.approved_by,
                "approved_at": e.approved_at.isoformat() if e.approved_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
        )
    return res


@router.post("/tesauros/{tesauro_id}/entradas", response_model=TesauroEntryResponse, status_code=201)
def adicionar_entrada_tesauro(
    project_id: str,
    tesauro_id: str,
    payload: TesauroEntryCreate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Adiciona manualmente uma entrada com aprovação imediata do autor."""
    user_id = usuario.id if usuario else None
    entrada = servico_tesauro.adicionar_entrada(
        db,
        thesaurus_id=tesauro_id,
        preferred_term=payload.preferred_term,
        variants=payload.variants,
        scope=payload.scope,
        proposed_by="manual",
        approved_by=user_id,
    )
    vars_list = []
    try:
        vars_list = json.loads(entrada.variants)
    except Exception:
        pass
    return {
        "id": entrada.id,
        "thesaurus_id": entrada.thesaurus_id,
        "preferred_term": entrada.preferred_term,
        "variants": vars_list,
        "scope": entrada.scope,
        "proposed_by": entrada.proposed_by,
        "approved_by": entrada.approved_by,
        "approved_at": entrada.approved_at.isoformat() if entrada.approved_at else None,
        "created_at": entrada.created_at.isoformat() if entrada.created_at else None,
    }


@router.post("/tesauros/{tesauro_id}/entradas/aprovar", response_model=list[TesauroEntryResponse])
def aprovar_entradas_tesauro(
    project_id: str,
    tesauro_id: str,
    payload: AprovarEntradasBatch,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Aprova formalmente entradas de tesauro que estavam em rascunho (porta obrigatória doc 48 §6.1)."""
    user_id = usuario.id if usuario else "usuario"
    aprovadas = servico_tesauro.aprovar_entradas(db, entry_ids=payload.entry_ids, user_id=user_id)
    res = []
    for e in aprovadas:
        vars_list = []
        try:
            vars_list = json.loads(e.variants)
        except Exception:
            pass
        res.append(
            {
                "id": e.id,
                "thesaurus_id": e.thesaurus_id,
                "preferred_term": e.preferred_term,
                "variants": vars_list,
                "scope": e.scope,
                "proposed_by": e.proposed_by,
                "approved_by": e.approved_by,
                "approved_at": e.approved_at.isoformat() if e.approved_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
        )
    return res


# ── Instrumentos de Medida e Evidências (Fase 5, doc 48 §6, §12) ─────────


def _instrumento_para_schema(inst: BibInstrumentoModel) -> dict[str, Any]:
    lex = {}
    try:
        lex = json.loads(inst.lexicon)
    except Exception:
        pass
    ci = None
    try:
        ci = json.loads(inst.precision_ci) if inst.precision_ci else None
    except Exception:
        pass
    return {
        "id": inst.id,
        "project_id": inst.project_id,
        "concept": inst.concept,
        "definition": inst.definition,
        "lexicon": lex,
        "version": inst.version,
        "status": inst.status,
        "proposed_by": inst.proposed_by,
        "model_used": inst.model_used,
        "prompt_hash": inst.prompt_hash,
        "approved_by": inst.approved_by,
        "approved_at": inst.approved_at.isoformat() if inst.approved_at else None,
        "estimated_precision": inst.estimated_precision,
        "precision_ci": ci,
        "created_at": inst.created_at.isoformat() if inst.created_at else None,
    }


@router.post("/instrumentos/sugerir-lexico", response_model=SugerirLexicoResponse)
def sugerir_lexico_endpoint(
    project_id: str,
    payload: SugerirLexicoRequest,
):
    """Gera proposta de léxico conceitual em rascunho com motivos de inclusão e exclusão."""
    return sugerir_lexico_conceitual(
        conceito=payload.concept,
        definicao=payload.definition,
        idioma=payload.language,
    )


@router.get("/instrumentos", response_model=list[InstrumentoResponse])
def listar_instrumentos(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Lista os instrumentos conceituais criados no projeto."""
    instrumentos = (
        db.query(BibInstrumentoModel)
        .filter(BibInstrumentoModel.project_id == project_id)
        .order_by(BibInstrumentoModel.created_at.desc())
        .all()
    )
    return [_instrumento_para_schema(i) for i in instrumentos]


@router.post("/instrumentos", response_model=InstrumentoResponse, status_code=201)
def criar_instrumento_endpoint(
    project_id: str,
    payload: InstrumentoCreate,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Cria um novo instrumento conceitual (nasce em estado de rascunho se não for explicitamente aprovado)."""
    user_id = usuario.id if usuario else None
    inst = servico_instrumentos.criar_instrumento(
        db,
        project_id=project_id,
        concept=payload.concept,
        definition=payload.definition,
        lexicon=payload.lexicon.model_dump(),
        proposed_by=payload.proposed_by,
        model_used=payload.model_used,
        prompt_hash=payload.prompt_hash,
        status="rascunho",
        approved_by=None,
    )
    return _instrumento_para_schema(inst)


@router.get("/instrumentos/{instrument_id}", response_model=InstrumentoResponse)
def obter_instrumento(
    project_id: str,
    instrument_id: str,
    db: Session = Depends(get_db),
):
    """Obtém os detalhes e léxico de um instrumento específico."""
    inst = db.query(BibInstrumentoModel).filter(BibInstrumentoModel.id == instrument_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail=f"Instrumento '{instrument_id}' não encontrado.")
    return _instrumento_para_schema(inst)


@router.patch("/instrumentos/{instrument_id}/aprovar", response_model=InstrumentoResponse)
def aprovar_instrumento_endpoint(
    project_id: str,
    instrument_id: str,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Aprova formalmente o instrumento para permitir medições oficiais (porta obrigatória doc 48 §6.1)."""
    user_id = usuario.id if usuario else "usuario"
    try:
        inst = servico_instrumentos.aprovar_instrumento(db, instrument_id=instrument_id, user_id=user_id)
        return _instrumento_para_schema(inst)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/instrumentos/{instrument_id}/medir", response_model=MedidaResultado)
def medir_instrumento_endpoint(
    project_id: str,
    instrument_id: str,
    payload: MedirRequest,
    db: Session = Depends(get_db),
):
    """Executa contagem determinística sobre os textos completos e metadados."""
    try:
        resultado, _ = servico_instrumentos.executar_medicao(
            db,
            instrument_id=instrument_id,
            project_id=project_id,
            snapshot_id=payload.snapshot_id,
            preview=payload.preview,
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/instrumentos/{instrument_id}/medidas", response_model=list[MedidaResponse])
def listar_medidas_instrumento(
    project_id: str,
    instrument_id: str,
    db: Session = Depends(get_db),
):
    """Lista as medições oficiais executadas para o instrumento."""
    medidas = (
        db.query(BibMedidaModel)
        .filter(BibMedidaModel.instrument_id == instrument_id)
        .order_by(BibMedidaModel.executed_at.desc())
        .all()
    )
    res = []
    for m in medidas:
        r = {}
        try:
            r = json.loads(m.result)
        except Exception:
            pass
        res.append(
            {
                "id": m.id,
                "snapshot_id": m.snapshot_id,
                "instrument_id": m.instrument_id,
                "instrument_version": m.instrument_version,
                "result": r,
                "n_documents": m.n_documents,
                "n_documents_with_text": m.n_documents_with_text,
                "executed_at": m.executed_at.isoformat() if m.executed_at else None,
            }
        )
    return res


@router.get("/medidas/{medida_id}/ocorrencias", response_model=list[OcorrenciaResponse])
def listar_ocorrencias_medida(
    project_id: str,
    medida_id: str,
    db: Session = Depends(get_db),
):
    """Retorna as ocorrências textuais detalhadas com página, seção IMRaD e snippet."""
    ocorrencias = (
        db.query(BibOcorrenciaModel)
        .filter(BibOcorrenciaModel.measurement_id == medida_id)
        .order_by(BibOcorrenciaModel.paper_id, BibOcorrenciaModel.page)
        .all()
    )
    return [
        {
            "id": oc.id,
            "paper_id": oc.paper_id,
            "section": oc.section,
            "page": oc.page,
            "char_start": oc.char_start,
            "char_end": oc.char_end,
            "matched_form": oc.matched_form,
            "context_snippet": oc.context_snippet,
        }
        for oc in ocorrencias
    ]


@router.post("/instrumentos/{instrument_id}/amostra-conferencia", response_model=list[OcorrenciaResponse])
def sortear_amostra_endpoint(
    project_id: str,
    instrument_id: str,
    k: int = 30,
    seed: int = 42,
    db: Session = Depends(get_db),
):
    """Sorteia k ocorrências registradas para validação humana (doc 48 §6.7)."""
    amostra = servico_instrumentos.sortear_amostra_conferencia(db, instrument_id=instrument_id, k=k, seed=seed)
    return [
        {
            "id": oc["id"],
            "paper_id": oc["paper_id"],
            "section": oc["section"],
            "page": oc["page"],
            "char_start": 0,
            "char_end": 0,
            "matched_form": oc["matched_form"],
            "context_snippet": oc["context_snippet"],
        }
        for oc in amostra
    ]


@router.post("/instrumentos/{instrument_id}/julgar-amostra")
def registrar_julgamento_endpoint(
    project_id: str,
    instrument_id: str,
    payload: JulgamentoAmostraRequest,
    db: Session = Depends(get_db),
):
    """Grava o julgamento humano da amostra e calcula a precisão estimada com IC 95% Wilson."""
    try:
        p_hat, ic = servico_instrumentos.registrar_julgamento_amostra(
            db,
            instrument_id=instrument_id,
            acertos_positivos=payload.acertos_positivos,
            total_avaliados=payload.total_avaliados,
        )
        return {"estimated_precision": p_hat, "precision_ci": ic}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Grafos e Análise Estrutural (Fase 6, doc 48 §8, §12) ─────────────────


def _grafo_para_schema(g: BibGrafoModel) -> dict[str, Any]:
    params = {}
    try:
        params = json.loads(g.parameters)
    except Exception:
        pass
    nodes = []
    try:
        nodes = json.loads(g.nodes)
    except Exception:
        pass
    edges = []
    try:
        edges = json.loads(g.edges)
    except Exception:
        pass
    coords = {}
    try:
        coords = json.loads(g.coordinates)
    except Exception:
        pass
    clusters = {}
    try:
        clusters = json.loads(g.clusters)
    except Exception:
        pass

    return {
        "id": g.id,
        "project_id": g.project_id,
        "snapshot_id": g.snapshot_id,
        "network_type": g.network_type,
        "parameters": params,
        "nodes": nodes,
        "edges": edges,
        "coordinates": coords,
        "clusters": clusters,
        "seed": g.seed,
        "calculated_at": g.calculated_at.isoformat() if g.calculated_at else None,
    }


@router.post("/grafos/gerar", response_model=GrafoResponse)
def gerar_grafo_endpoint(
    project_id: str,
    payload: GerarGrafoRequest,
    db: Session = Depends(get_db),
):
    """Gera rede bibliométrica determinística com clusters Louvain e layout Fruchterman-Reingold."""
    try:
        grafo_model = servico_grafos.construir_grafo(
            db,
            project_id=project_id,
            network_type=payload.network_type,
            snapshot_id=payload.snapshot_id,
            normalizacao=payload.normalizacao,
            corte_minimo=payload.corte_minimo,
            max_nos=payload.max_nos,
            resolucao_louvain=payload.resolucao_louvain,
            semente=payload.semente,
            iteracoes_fr=payload.iteracoes_fr,
        )
        return _grafo_para_schema(grafo_model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/grafos", response_model=list[GrafoResponse])
def listar_grafos(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Lista os grafos gerados para o projeto."""
    grafos = (
        db.query(BibGrafoModel)
        .filter(BibGrafoModel.project_id == project_id)
        .order_by(BibGrafoModel.calculated_at.desc())
        .all()
    )
    return [_grafo_para_schema(g) for g in grafos]


@router.get("/grafos/{grafo_id}", response_model=GrafoResponse)
def obter_grafo(
    project_id: str,
    grafo_id: str,
    db: Session = Depends(get_db),
):
    """Retorna os dados completos do grafo para visualização em Canvas e tabela acessível."""
    grafo = (
        db.query(BibGrafoModel)
        .filter(BibGrafoModel.id == grafo_id, BibGrafoModel.project_id == project_id)
        .first()
    )
    if not grafo:
        raise HTTPException(status_code=404, detail=f"Grafo '{grafo_id}' não encontrado.")
    return _grafo_para_schema(grafo)


@router.get("/grafos/{grafo_id}/exportar")
def exportar_grafo_endpoint(
    project_id: str,
    grafo_id: str,
    formato: str = "graphml",
    db: Session = Depends(get_db),
):
    """Exporta a rede em GraphML com coordenadas embutidas para Gephi e VOSviewer (doc 48 §8.4)."""
    grafo = (
        db.query(BibGrafoModel)
        .filter(BibGrafoModel.id == grafo_id, BibGrafoModel.project_id == project_id)
        .first()
    )
    if not grafo:
        raise HTTPException(status_code=404, detail=f"Grafo '{grafo_id}' não encontrado.")

    conteudo_graphml = servico_grafos.exportar_graphml(grafo)
    filename = f"grafo_{grafo.network_type}_{grafo.id[:8]}.graphml"
    return Response(
        content=conteudo_graphml,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Estatística Sob Demanda (Fase 7, doc 48 §9, §12) ─────────────────────


@router.post("/analises/interpretar", response_model=InterpretarPerguntaResponse)
def interpretar_pergunta_endpoint(
    project_id: str,
    payload: InterpretarPerguntaRequest,
):
    """Traduz pergunta em linguagem natural para especificação formal com vocabulário fechado (doc 48 §9.1)."""
    return interpretar_pergunta(payload.question)


@router.post("/analises/executar", response_model=ExecutarEspecificacaoResponse)
def executar_especificacao_endpoint(
    project_id: str,
    payload: ExecutarEspecificacaoRequest,
    db: Session = Depends(get_db),
):
    """Executa a especificação validada por meio de consultas SQLAlchemy parametrizadas (doc 48 §9.2)."""
    try:
        linhas, total_docs, proveniencia = servico_analises.compilar_e_executar(
            db,
            project_id=project_id,
            spec=payload.specification,
            snapshot_id=payload.snapshot_id,
        )
        return {
            "specification": payload.specification,
            "results": linhas,
            "total_documents_analyzed": total_docs,
            "provenance": proveniencia,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analises/salvas", response_model=AnaliseSalvaResponse, status_code=201)
def salvar_analise_endpoint(
    project_id: str,
    payload: SalvarAnaliseRequest,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Salva a análise formal para permitir reexecução sobre outros instantâneos (doc 48 §9.3)."""
    user_id = usuario.id if usuario else None
    analise = servico_analises.salvar_analise(
        db,
        project_id=project_id,
        question=payload.question,
        specification=payload.specification.model_dump(),
        user_id=user_id,
    )
    spec_dict = {}
    try:
        spec_dict = json.loads(analise.specification)
    except Exception:
        pass
    return {
        "id": analise.id,
        "project_id": analise.project_id,
        "question": analise.question,
        "specification": spec_dict,
        "created_by": analise.created_by,
        "created_at": analise.created_at.isoformat() if analise.created_at else None,
    }


@router.get("/analises/salvas", response_model=list[AnaliseSalvaResponse])
def listar_analises_salvas(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Lista as análises estatísticas salvas no projeto."""
    analises = servico_analises.listar_analises(db, project_id=project_id)
    res = []
    for a in analises:
        spec_dict = {}
        try:
            spec_dict = json.loads(a.specification)
        except Exception:
            pass
        res.append(
            {
                "id": a.id,
                "project_id": a.project_id,
                "question": a.question,
                "specification": spec_dict,
                "created_by": a.created_by,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )
    return res


@router.delete("/analises/salvas/{analise_id}")
def excluir_analise_salva(
    project_id: str,
    analise_id: str,
    db: Session = Depends(get_db),
):
    """Exclui uma análise salva."""
    sucesso = servico_analises.excluir_analise(db, analise_id=analise_id, project_id=project_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail=f"Análise '{analise_id}' não encontrada.")
    return {"ok": True}


# ── Indicadores de Vanguarda e Sensibilidade (Fase 8, doc 48 §7.4, §10, §12) ──


@router.get("/vanguarda/diagrama-estrategico", response_model=DiagramaEstrategicoResponse)
def obter_diagrama_estrategico_endpoint(
    project_id: str,
    snapshot_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Calcula Centralidade × Densidade e posiciona temas nos 4 quadrantes clássicos (Callon et al. 1991, SciMAT)."""
    return servico_vanguarda.calcular_diagrama_estrategico(
        db, project_id=project_id, snapshot_id=snapshot_id
    )


@router.get("/vanguarda/rajadas", response_model=RajadasResponse)
def obter_rajadas_endpoint(
    project_id: str,
    snapshot_id: str | None = None,
    s: float = 2.0,
    db: Session = Depends(get_db),
):
    """Detecta saltos temporais abruptos na frequência de termos (Burst Detection de Kleinberg 2003)."""
    return servico_vanguarda.detectar_rajadas_termos(
        db, project_id=project_id, snapshot_id=snapshot_id, s=s
    )


@router.get("/vanguarda/bootstrap-rankings", response_model=BootstrapRankingsResponse)
def obter_bootstrap_rankings_endpoint(
    project_id: str,
    tipo_ranking: str = "periodicos",
    snapshot_id: str | None = None,
    n_boot: int = 1000,
    seed: int = 42,
    db: Session = Depends(get_db),
):
    """Calcula intervalos IC 95% via bootstrap e sinaliza empates técnicos (posições indistinguíveis, doc 48 §10.1)."""
    if tipo_ranking not in ["periodicos", "autores", "instituicoes"]:
        raise HTTPException(
            status_code=400,
            detail="tipo_ranking deve ser 'periodicos', 'autores' ou 'instituicoes'",
        )
    return servico_vanguarda.calcular_bootstrap_rankings(
        db,
        project_id=project_id,
        snapshot_id=snapshot_id,
        tipo_ranking=tipo_ranking,
        n_boot=n_boot,
        seed=seed,
    )


@router.get("/vanguarda/sensibilidade", response_model=SensibilidadeParametrosResponse)
def obter_sensibilidade_parametros_endpoint(
    project_id: str,
    snapshot_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Varre resoluções de agrupamento e avalia estabilidade via Índice de Rand Ajustado (ARI, doc 48 §10.2)."""
    return servico_vanguarda.calcular_sensibilidade_louvain(
        db, project_id=project_id, snapshot_id=snapshot_id
    )


@router.get("/vanguarda/cobertura-campo", response_model=CoberturaCampoResponse)
def obter_cobertura_campo_endpoint(
    project_id: str,
    snapshot_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Mapeia cobertura do campo comparando tópicos do corpus com subtemas da literatura (doc 48 §7.4e)."""
    return servico_vanguarda.calcular_cobertura_campo(
        db, project_id=project_id, snapshot_id=snapshot_id
    )


# ── Pré-Registro e Relatório BIBLIO (Fase 9, doc 48 §11, §12) ─────────────


@router.get("/preregistro/plano", response_model=PlanoBibliometricoSchema)
def obter_plano_bibliometrico_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Obtém o plano bibliométrico pré-registrado no protocolo D11 com emendas (doc 48 §11)."""
    return servico_preregistro.obter_ou_criar_plano(db, project_id=project_id)


@router.put("/preregistro/plano", response_model=PlanoBibliometricoSchema)
def atualizar_plano_bibliometrico_endpoint(
    project_id: str,
    payload: AtualizarPlanoBibliometricoRequest,
    db: Session = Depends(get_db),
    usuario: UserModel = Depends(require_session),
):
    """Atualiza o plano pré-registrado. Se vigente, cria emenda rastreável com justificativa."""
    user_id = usuario.id if usuario else None
    return servico_preregistro.atualizar_plano(
        db,
        project_id=project_id,
        payload=payload.model_dump(),
        usuario_id=user_id,
    )


@router.get("/preregistro/relatorio-biblio", response_model=RelatorioConformidadeBiblioResponse)
def obter_relatorio_conformidade_biblio_endpoint(
    project_id: str,
    snapshot_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Gera o relatório de conformidade metodológica BIBLIO com 20 itens (doc 48 §11, §12)."""
    return servico_preregistro.gerar_relatorio_conformidade_biblio(
        db, project_id=project_id, snapshot_id=snapshot_id
    )


@router.get("/exportar-pacote")
def exportar_pacote_replicacao_endpoint(
    project_id: str,
    snapshot_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Gera o pacote de replicação completo em ZIP (dados, grafos, relatório BIBLIO e proveniência)."""
    zip_bytes = servico_preregistro.gerar_pacote_replicacao_zip(
        db, project_id=project_id, snapshot_id=snapshot_id
    )
    filename = f"pacote_replicacao_bibliometria_{project_id[:8]}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )








