#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Serviço de Triagem com Inteligência Artificial (Screening Service).
Executa a triagem automatizada (individual e em lote) com guardrails estritos
de zero alucinação e persistência de auditoria.
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

import json
from app.database import SessionLocal
from app.domain.collaboration import politica_de
from app.domain.entities import Decision, Methodology, Paper, Protocol
from app.infrastructure.ai.base import BaseAIClient, ProvedorIndisponivel, ScreeningResult
from app.infrastructure.ai.factory import AIFactory
from app.infrastructure.ai.prompts import build_screening_prompt
from app.domain.triabilidade import filtro_com_resumo
from app.services.acelerador import AceleradorAdaptativo
from app.infrastructure.persistence.models import (
    AuditLogModel,
    CriterionModel,
    PaperCriterionModel,
    PaperModel,
    PaperScreeningModel,
    ProtocolModel,
    utcnow,
)
from app.services.consolidation_service import consolidar
from app.services.harvesting_service import ws_manager
from app.services import ropa_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditActor:
    """
    Quem acionou uma operação assistida por IA.

    Existe como valor imutável, e não como o objeto ORM do usuário, porque a
    triagem em lote roda em segundo plano com outra sessão de banco — carregar
    o modelo para lá o deixaria destacado (`DetachedInstanceError`) na primeira
    leitura de atributo.
    """

    user_id: str
    username: str


# Prefixos de origem automática que jamais devem aparecer nas observações do revisor
# (ex.: "[IA - gemini-3.6-flash]:", "[I.A. gemini]:", "(AI) ", "IA:", "Assistente:").
_AI_PREFIX_PATTERNS = [
    re.compile(r"^\s*[\[\(]\s*(?:I\.?\s*A\.?|A\.?\s*I\.?|IA|AI)\b[^\]\)]*[\]\)]\s*[:\-–—]?\s*", re.IGNORECASE),
    re.compile(r"^\s*(?:I\.?\s*A\.?|A\.?\s*I\.?|IA|AI|Assistente(?:\s+de\s+IA)?|Modelo|Gemini|OpenAI|GPT|Claude)\s*[:\-–—]\s+", re.IGNORECASE),
    re.compile(r"^\s*(?:Justificativa|Parecer|An[áa]lise)\s*[:\-–—]\s+", re.IGNORECASE),
]


def _strip_ai_prefix(text: str) -> str:
    """Remove rótulos de origem automática do início do texto, de forma iterativa.

    A observação deve soar como a anotação de um pesquisador que triou o estudo,
    sem qualquer marca de ferramenta, modelo ou provedor.
    """
    cleaned = (text or "").strip()
    changed = True
    while changed and cleaned:
        changed = False
        for pattern in _AI_PREFIX_PATTERNS:
            new_text = pattern.sub("", cleaned, count=1).strip()
            if new_text != cleaned:
                cleaned = new_text
                changed = True
    return cleaned


def _normalize_key(value: str) -> str:
    """Normaliza uma chave de critério para comparação (maiúsculas, sem separadores)."""
    return re.sub(r"[\s_\-\.\:]+", "", str(value or "")).upper()


def _build_criterion_map(criteria_list: List[CriterionModel], prefixes: List[str]) -> Dict[str, str]:
    """Monta um mapa tolerante de chaves possíveis do modelo -> id do critério.

    Cobre as variações usuais devolvidas pelos provedores: "INC1", "INC_1",
    "Critério 1", "C1", o índice puro ("1") e o próprio texto do critério.
    """
    mapping: Dict[str, str] = {}
    for idx, crit in enumerate(criteria_list, 1):
        for prefix in prefixes:
            mapping[_normalize_key(f"{prefix}{idx}")] = crit.id
        mapping[_normalize_key(str(idx))] = crit.id
        if crit.text:
            mapping[_normalize_key(crit.text)] = crit.id
    return mapping


def _iter_criteria_flags(raw) -> List[tuple]:
    """Converte a resposta de critérios em pares (chave, booleano).

    Aceita tanto o dicionário previsto no prompt ({"INC1": true}) quanto listas
    de códigos atendidos (["INC1", "INC3"]) devolvidas por alguns modelos.
    """
    if isinstance(raw, dict):
        return [(k, bool(v)) for k, v in raw.items()]
    if isinstance(raw, (list, tuple, set)):
        pairs = []
        for item in raw:
            if isinstance(item, dict):
                code = item.get("code") or item.get("codigo") or item.get("id")
                if code is None:
                    continue
                value = item.get("atendido", item.get("value", item.get("met", True)))
                pairs.append((code, bool(value)))
            elif isinstance(item, str) and item.strip():
                pairs.append((item, True))
        return pairs
    return []


def _to_paper_entity(model: PaperModel) -> Paper:
    dec = Decision.PENDING
    if model.decision == "Incluído":
        dec = Decision.INCLUDED
    elif model.decision == "Excluído":
        dec = Decision.EXCLUDED

    return Paper(
        id=model.id,
        title=model.title,
        authors=model.authors or "",
        year=model.year or "",
        abstract=model.abstract or "",
        doi=model.doi,
        download_url=model.download_url or "",
        decision=dec,
        observations=model.observations or "",
        ai_confidence=model.ai_confidence,
    )


def _to_protocol_entity(model: ProtocolModel) -> Protocol:
    inc_criteria = [c.text for c in model.criteria if not c.is_exclusion]
    exc_criteria = [c.text for c in model.criteria if c.is_exclusion]
    questions = [q.text for q in model.extraction_questions]

    try:
        methodology = Methodology(model.project.methodology) if model.project else Methodology.PRISMA_P
    except Exception:
        methodology = Methodology.PRISMA_P

    return Protocol(
        title=model.project.title if model.project else "",
        objective=model.objective or "",
        methodology=methodology,
        inclusion_criteria=inc_criteria,
        exclusion_criteria=exc_criteria,
        extraction_questions=questions,
    )


class ScreeningService:
    """Serviço de Triagem com IA."""

    def __init__(self, ai_client: Optional[BaseAIClient] = None):
        self.ai_client = ai_client
        # Contadores do lote em andamento, por projeto. Existem porque o
        # progresso só viajava pelo WebSocket: quem recarregasse a tela no meio
        # da triagem perdia a barra, o botão de parar e qualquer sinal de que
        # havia algo correndo. Com o estado aqui, a tela se recompõe ao abrir.
        self._batch_state: Dict[str, dict] = {}

    def get_batch_state(self, project_id: str) -> Optional[dict]:
        """Situação do lote do projeto — em andamento **ou recém-encerrado**.

        O estado era descartado no instante em que o lote terminava, e isso
        quebrava a tela de quem acompanhava pela consulta periódica em vez do
        canal ao vivo: a última consulta antes do fim mostrava N-1 de N, a
        seguinte encontrava `null`, e o último estudo ficava eternamente
        "analisando". Era o relato de que "o último do lote sempre trava" —
        e o lote tinha terminado, só ninguém conseguia mais saber disso.

        Guardar o desfecho custa um dicionário por projeto, substituído no lote
        seguinte, e é o que permite fechar o quadro: N de N, com a decisão de
        cada estudo.
        """
        return self._batch_state.get(project_id)

    def _get_client(self, db: Session, user_id: Optional[str] = None) -> BaseAIClient:
        if self.ai_client:
            return self.ai_client
        return AIFactory.get_client(db, user_id=user_id)

    async def screen_single_paper(
        self,
        db: Session,
        project_id: str,
        paper_id: str,
        actor: Optional["AuditActor"] = None,
    ) -> ScreeningResult:
        """
        Executa a triagem com IA para um único artigo.

        `actor` é quem pediu a triagem. A decisão é da IA, mas a
        responsabilidade por tê-la acionado é de uma pessoa — e é isso que a
        auditoria precisa registrar (doc 29 §29.3.5).
        """
        paper_model = (
            db.query(PaperModel)
            .filter(PaperModel.project_id == project_id, PaperModel.id == paper_id)
            .first()
        )
        if not paper_model:
            raise ValueError(f"Artigo '{paper_id}' não encontrado.")

        protocol_model = (
            db.query(ProtocolModel)
            .filter(ProtocolModel.project_id == project_id)
            .first()
        )
        if not protocol_model:
            raise ValueError(f"Protocolo do projeto '{project_id}' não encontrado.")

        paper_entity = _to_paper_entity(paper_model)
        protocol_entity = _to_protocol_entity(protocol_model)

        client = self._get_client(db, user_id=actor.user_id if actor else None)
        result = await client.analyze_screening(paper_entity, protocol_entity)

        # Hash do contexto que produziu a decisão (doc 29 §29.9.3). Guardar o
        # texto inteiro inflaria o banco a cada triagem; o hash é o suficiente
        # para provar depois que a decisão veio *daquele* conteúdo — e para
        # detectar que o conteúdo mudou desde então.
        contexto_hash = hashlib.sha256(
            build_screening_prompt(paper_entity, protocol_entity).encode("utf-8")
        ).hexdigest()

        # Atualizar banco de dados
        old_decision = paper_model.decision
        paper_model.decision = result.decision
        paper_model.ai_confidence = result.confidence

        # Observações do revisor: apenas o parecer, sem rótulo de modelo ou provedor
        clean_just = _strip_ai_prefix(result.justification)
        if clean_just:
            paper_model.observations = clean_just

        # Log de Auditoria Metodológica
        audit = AuditLogModel(
            paper_id=paper_model.id,
            action="ai_screening",
            old_value=old_decision,
            new_value=result.decision,
            source=f"ai:{result.provider}",
            user_id=actor.user_id if actor else None,
            username=actor.username if actor else "",
            ai_provider=result.provider or "",
            ai_model=result.model_used or "",
            ai_context_sha256=contexto_hash,
            ai_response_valid=result.response_valid,
        )
        db.add(audit)

        # Registro ROPA da operação com IA (LGPD Art. 37, doc 40 §40.5.2)
        is_intl = (result.provider or "").lower() not in ("local", "ollama", "lmstudio")
        owner_id = actor.user_id if actor else (paper_model.project.owner_id if paper_model.project else None)
        ropa_service.registrar(
            db,
            operation="ai_dispatch",
            legal_basis="art7_V_execucao_de_contrato",
            purpose="Triagem de artigo científico assistida por inteligência artificial",
            data_categories=["conteudo_de_pesquisa", "referencia_bibliografica"],
            user_id=owner_id,
            recipient=result.provider or "ai_provider",
            international=is_intl,
            commit=False,
        )

        # Persistir avaliações de critérios, tolerando as variações de chave dos provedores
        inc_map = _build_criterion_map(
            [c for c in protocol_model.criteria if not c.is_exclusion],
            ["INC", "I", "CI", "CRIT", "CRITERIO", "CRITÉRIO", "C"],
        )
        exc_map = _build_criterion_map(
            [c for c in protocol_model.criteria if c.is_exclusion],
            ["EXC", "E", "CE", "CRIT", "CRITERIO", "CRITÉRIO", "C"],
        )

        crit_evals_dict = {}
        for raw_criteria, crit_map in (
            (result.inclusion_criteria, inc_map),
            (result.exclusion_criteria, exc_map),
        ):
            for key, bool_val in _iter_criteria_flags(raw_criteria):
                crit_id = crit_map.get(_normalize_key(key))
                if not crit_id:
                    logger.debug(f"[ScreeningAI] Critério '{key}' não corresponde a nenhum critério do protocolo.")
                    continue
                crit_evals_dict[crit_id] = bool_val

                eval_record = (
                    db.query(PaperCriterionModel)
                    .filter(
                        PaperCriterionModel.paper_id == paper_model.id,
                        PaperCriterionModel.criterion_id == crit_id,
                    )
                    .first()
                )
                if eval_record:
                    eval_record.value = bool_val
                else:
                    db.add(
                        PaperCriterionModel(
                            paper_id=paper_model.id,
                            criterion_id=crit_id,
                            value=bool_val,
                        )
                    )

        # Gravar julgamento individual do ator ou do proprietário do projeto (doc 43 §43.3.4, P4)
        target_reviewer_id = (
            actor.user_id
            if actor and actor.user_id
            else (paper_model.project.owner_id if paper_model.project else None)
        )

        if target_reviewer_id:
            screening = (
                db.query(PaperScreeningModel)
                .filter(
                    PaperScreeningModel.paper_id == paper_model.id,
                    PaperScreeningModel.reviewer_id == target_reviewer_id,
                )
                .first()
            )
            if not screening:
                screening = PaperScreeningModel(
                    paper_id=paper_model.id,
                    reviewer_id=target_reviewer_id,
                )
                db.add(screening)
                if paper_model.screenings is None:
                    paper_model.screenings = []
                paper_model.screenings.append(screening)

            screening.decision = result.decision
            screening.observations = clean_just
            screening.criteria_evaluations = json.dumps(crit_evals_dict)
            screening.ai_confidence = result.confidence
            screening.ai_assisted = True
            screening.decided_at = utcnow()
            screening.updated_at = utcnow()
        else:
            paper_model.decision = result.decision
            paper_model.screening_status = "consenso"

        politica = (
            politica_de(paper_model.project)
            if paper_model.project
            else politica_de(None)
        )
        consolidar(db, paper_model, politica)

        db.commit()
        db.refresh(paper_model)
        return result

    async def run_batch_screening(
        self,
        project_id: str,
        limit: int = 50,
        concurrency: int = 1,
        pausa_entre_estudos: float = 4.0,
        actor: Optional["AuditActor"] = None,
    ):
        """
        Executa a triagem em lote em segundo plano, com concorrência e ritmo.

        `concurrency` é o **teto** do paralelismo, e `pausa_entre_estudos` o
        ritmo inicial. Onde o lote se acomoda abaixo disso não é escolhido: o
        acelerador sobe enquanto o provedor aceita e recua assim que ele recusa
        (ver `acelerador.py`).

        Isso substitui o número fixo que o pesquisador escolhia antes de
        começar e que ninguém tinha como acertar — o limite real depende do
        plano, do modelo, de quantas chaves estão cadastradas e da hora do dia.
        Alto demais derrubava o lote em recusas; baixo demais desperdiçava
        minutos de espera à toa.
        """
        db = SessionLocal()
        try:
            # Duplicatas ficam de fora, pelo mesmo critério da fila de triagem
            # (`papers.py`) e do contador do projeto (`projects.py /stats`). Sem
            # este filtro o lote tria registros que o pesquisador já removeu do
            # acervo: gasta cota do provedor, não muda nada na tela — porque
            # aqueles registros não estão nela — e faz o lote parecer inerte.
            pending_papers = (
                db.query(PaperModel.id, PaperModel.title, PaperModel.authors, PaperModel.year)
                .filter(
                    PaperModel.project_id == project_id,
                    PaperModel.decision == "Pendente",
                    or_(PaperModel.is_duplicate == False, PaperModel.is_duplicate.is_(None)),  # noqa: E712
                    # Sem resumo não há triagem por título e resumo. Mandar o
                    # registro assim mesmo não gera uma decisão ruim: gera uma
                    # decisão sobre nada, com a mesma aparência de confiança de
                    # uma decisão real — e gasta cota do provedor para isso.
                    filtro_com_resumo(PaperModel),
                )
                .order_by(func.nullif(PaperModel.year, "").desc().nullslast(), PaperModel.created_at.desc())
                .limit(limit)
                .all()
            )
            total_papers = len(pending_papers)

            if total_papers == 0:
                await ws_manager.broadcast(
                    project_id,
                    {"type": "batch_screening_empty", "message": "Nenhum artigo pendente encontrado."},
                )
                return

            # A relação do lote, na ordem em que os estudos serão triados.
            # Nasce inteira e com todos "na fila": é o que permite à janela
            # mostrar o conjunto desde o primeiro segundo, em vez de revelá-lo
            # aos poucos conforme os eventos chegam.
            itens = [
                {
                    "id": pid,
                    "title": ptitle or "Sem título",
                    "authors": pauthors or "",
                    "year": str(pyear or ""),
                    "status": "na_fila",
                    "decision": None,
                    "confidence": None,
                    "justification": None,
                }
                for pid, ptitle, pauthors, pyear in pending_papers
            ]
            indice_do_item = {item["id"]: item for item in itens}

            estado = {
                "processed": 0,
                "total": total_papers,
                "percentage": 0.0,
                "included": 0,
                "excluded": 0,
                "pending": total_papers,
                "current_paper_title": "",
                "current_paper_id": "",
                "current_paper_authors": "",
                "current_paper_year": "",
                "itens": itens,
                "ritmo": None,
            }
            self._batch_state[project_id] = estado

            logger.info(f"[BatchScreening] Iniciando triagem de {total_papers} artigos para o projeto {project_id}...")

            await ws_manager.broadcast(
                project_id,
                {
                    "type": "batch_screening_started",
                    "total": total_papers,
                    "message": f"Iniciando triagem com IA para {total_papers} artigos pendentes...",
                    # A relação vai junto: a janela mostra o lote inteiro antes
                    # de a primeira resposta chegar, em vez de um vazio com
                    # "aguardando os primeiros estudos".
                    #
                    # Cópia, e não a lista viva: os itens são mutados conforme o
                    # lote anda, e mandar a referência faria a mensagem de
                    # INÍCIO descrever um estado futuro para qualquer receptor
                    # que a serialize depois — um registro de auditoria, um
                    # teste, um cliente lento.
                    "itens": [dict(item) for item in itens],
                },
            )

            # Recusa do provedor tem dois sabores, e o lote precisa separar.
            #
            # Passageira — o limite de taxa de um minuto — é o caso normal de
            # uma triagem em lote: o cliente do provedor já espera e repete
            # sozinho, e o artigo seguinte costuma passar. Desistir do lote aí
            # seria interromper um trabalho que ia terminar.
            #
            # Persistente — chave sem cota, credencial errada, provedor fora do
            # ar — vale para todos os artigos. Insistir transforma 100 estudos
            # em 100 falhas e faz o lote terminar "com sucesso" sem ter decidido
            # nada, que foi exatamente o que se via.
            #
            # A distinção é feita por recusas consecutivas em estudos
            # DIFERENTES: com o cliente já esperando entre as tentativas, três
            # estudos distintos recusados em sequência, sem nenhum sucesso
            # entre eles, não são mais um soluço de limite.
            #
            # A exigência de que sejam distintos não é detalhe. Desde que um
            # estudo recusado volta para uma passada seguinte, um único estudo
            # teimoso — mal formatado, resumo que dispara um filtro do provedor
            # — produziria sozinho as três recusas e condenaria um lote em que
            # todo o resto estava passando.
            # Recusas persistentes que justificam interromper o lote inteiro:
            # - Cota DIÁRIA esgotada em todas as chaves (não volta hoje)
            # - Credencial ou chave inválida / revogada
            # - Falha consecutiva nas primeiras 5 tentativas sem nenhum sucesso inicial
            provedor_caiu: dict = {"motivo": None, "recusados_seguidos": set()}

            # Uma recusa isolada ou limite de taxa por minuto (RPM / 429) não é motivo
            # para derrubar o lote. O estudo recusado é adiado para a próxima passada,
            # o acelerador reduz o ritmo e aguarda o alívio da janela.
            PASSADAS_ATE_DESISTIR = 4
            adiados: List[tuple] = []

            acelerador = AceleradorAdaptativo(
                teto=max(1, concurrency),
                pausa_inicial=max(0.0, float(pausa_entre_estudos or 0.0)),
                deve_parar=lambda: bool(provedor_caiu["motivo"]),
            )
            estado["ritmo"] = acelerador.situacao()

            processed_count = 0
            included_count = 0
            excluded_count = 0
            pending_count = 0

            def _registrar_recente(pid, titulo, decisao, confianca, justificativa):
                """Fecha o item na relação do lote.

                A justificativa é recortada de propósito: a relação inteira é
                serializada a cada consulta de situação, e um lote de 500
                estudos com o texto completo de cada um viraria uma resposta de
                centenas de milhares de caracteres. O texto integral fica no
                estudo, que é onde ele é lido com calma.
                """
                item = indice_do_item.get(pid)
                if item is None:
                    return
                item["status"] = "concluido"
                item["decision"] = decisao
                item["confidence"] = confianca
                item["justification"] = (justificativa or "")[:400]

            def _atualizar_estado():
                estado["processed"] = processed_count
                estado["percentage"] = round((processed_count / total_papers) * 100, 1)
                estado["included"] = included_count
                estado["excluded"] = excluded_count
                estado["pending"] = total_papers - processed_count

            async def process_one(paper_info):
                nonlocal processed_count, included_count, excluded_count, pending_count
                pid, ptitle, pauthors, pyear = paper_info
                if provedor_caiu["motivo"]:
                    return
                async with acelerador:
                    if provedor_caiu["motivo"]:
                        return
                    # Notificar início da análise deste estudo específico
                    await ws_manager.broadcast(
                        project_id,
                        {
                            "type": "batch_screening_item_start",
                            "paper_id": pid,
                            "paper_title": ptitle or "Sem título",
                            "paper_authors": pauthors or "",
                            "paper_year": pyear or "",
                            "total": total_papers,
                        },
                    )
                    estado["current_paper_title"] = ptitle or "Sem título"
                    estado["current_paper_id"] = pid
                    estado["current_paper_authors"] = pauthors or ""
                    estado["current_paper_year"] = str(pyear or "")
                    if pid in indice_do_item:
                        indice_do_item[pid]["status"] = "em_analise"

                    task_db = SessionLocal()
                    try:
                        res = await self.screen_single_paper(task_db, project_id, pid, actor=actor)
                        provedor_caiu["recusados_seguidos"].clear()
                        acelerador.registrar_sucesso()
                        estado["ritmo"] = acelerador.situacao()
                        processed_count += 1
                        if res.decision == "Incluído":
                            included_count += 1
                        elif res.decision == "Excluído":
                            excluded_count += 1
                        else:
                            pending_count += 1

                        _atualizar_estado()
                        _registrar_recente(pid, ptitle, res.decision, res.confidence, res.justification)
                        await ws_manager.broadcast(
                            project_id,
                            {
                                "type": "batch_screening_progress",
                                "processed": processed_count,
                                "total": total_papers,
                                "percentage": round((processed_count / total_papers) * 100, 1),
                                "current_paper_id": pid,
                                "current_paper_title": ptitle or "Sem título",
                                "decision": res.decision,
                                "confidence": res.confidence,
                                "justification": res.justification,
                                "included_count": included_count,
                                "excluded_count": excluded_count,
                                "pending_count": total_papers - processed_count,
                                "ritmo": acelerador.situacao(),
                            },
                        )
                    except ProvedorIndisponivel as e:
                        # Não é falha deste estudo: é o provedor recusando. O
                        # artigo não é contado como processado — continua
                        # pendente para a próxima passada se for limite temporário.
                        provedor_caiu["recusados_seguidos"].add(pid)
                        acelerador.registrar_recusa()
                        estado["ritmo"] = acelerador.situacao()

                        e_msg = str(e)
                        e_msg_upper = e_msg.upper()
                        e_fatal = (
                            ("DIÁRIA" in e_msg_upper or "DIARIA" in e_msg_upper)
                            or "NENHUMA" in e_msg_upper
                            or "INVÁLID" in e_msg_upper
                            or "INVALID" in e_msg_upper
                            or "REVOKED" in e_msg_upper
                            or "UNAUTHENTICATED" in e_msg_upper
                            or "PERMISSION_DENIED" in e_msg_upper
                        )
                        # Limite de taxa por minuto ou momentâneo NÃO é fatal (é passageiro):
                        if (
                            "POR MINUTO" in e_msg_upper
                            or "MOMENTÂNEO" in e_msg_upper
                            or "MOMENTANEO" in e_msg_upper
                            or ("LIMITE DE TAXA" in e_msg_upper and "DIÁRIA" not in e_msg_upper and "DIARIA" not in e_msg_upper)
                        ):
                            e_fatal = False

                        # Se for erro fatal de cota diária ou se falhou consecutivamente sem nenhum sucesso:
                        if e_fatal or (processed_count == 0 and len(provedor_caiu["recusados_seguidos"]) >= 5):
                            provedor_caiu["motivo"] = e_msg
                            logger.warning(
                                f"[BatchScreening] Provedor indisponível definitivamente no lote: {e_msg}"
                            )
                        else:
                            adiados.append(paper_info)
                            if pid in indice_do_item:
                                indice_do_item[pid]["status"] = "na_fila"
                            logger.warning(
                                f"[BatchScreening] Limite de taxa temporário no paper {pid}. "
                                f"Adiado para próxima passada (total adiados: {len(adiados)})."
                            )
                        return
                    except Exception as e:
                        logger.error(f"[BatchScreening] Erro no paper {pid}: {e}")
                        processed_count += 1
                        pending_count += 1
                        _atualizar_estado()
                        _registrar_recente(
                            pid, ptitle, "Pendente", 0.0, f"Falha na análise: {e}"
                        )
                        await ws_manager.broadcast(
                            project_id,
                            {
                                "type": "batch_screening_progress",
                                "processed": processed_count,
                                "total": total_papers,
                                "percentage": round((processed_count / total_papers) * 100, 1),
                                "current_paper_id": pid,
                                "current_paper_title": ptitle or "Sem título",
                                "decision": "Pendente",
                                "confidence": 0.0,
                                "justification": f"Falha na análise: {str(e)}",
                                "included_count": included_count,
                                "excluded_count": excluded_count,
                                "pending_count": total_papers - processed_count,
                                "error": str(e),
                            },
                        )
                    finally:
                        task_db.close()

            # A cada passada o acelerador já recuou uma vez por recusa, então
            # a repetição chega mais devagar que a tentativa que falhou.
            a_triar = list(pending_papers)
            for _passada in range(PASSADAS_ATE_DESISTIR):
                if not a_triar or provedor_caiu["motivo"]:
                    break
                if _passada > 0 and a_triar and (pausa_entre_estudos or 0.0) > 0:
                    # Pausa de recuperação da janela de 1 minuto antes de reprocessar os adiados
                    espera_janela = min(12.0, 4.0 * _passada)
                    logger.info(
                        f"[BatchScreening] Passada {_passada + 1}/{PASSADAS_ATE_DESISTIR}: "
                        f"Aguardando {espera_janela:.0f}s para alívio de limite de taxa antes de "
                        f"processar {len(a_triar)} estudo(s) adiado(s)..."
                    )
                    await asyncio.sleep(espera_janela)

                adiados = []
                await asyncio.gather(*[process_one(p_info) for p_info in a_triar])
                a_triar = adiados

            # O que não passou nem após todas as passadas é registrado como não triado.
            # Continua pendente no acervo e entra no próximo lote.
            concluidos_ids = {it["id"] for it in itens if it.get("status") == "concluido"}
            nao_triados = [p for p in pending_papers if p[0] not in concluidos_ids]
            for pid_n, ptitle_n, _autores_n, _ano_n in nao_triados:
                item = indice_do_item.get(pid_n)
                if item is not None:
                    item["status"] = "nao_triado"
                    item["justification"] = (
                        "O provedor de IA recusou as tentativas desta rodada por limite de uso. "
                        "O estudo segue pendente e entrará no próximo lote."
                    )
                await ws_manager.broadcast(
                    project_id,
                    {
                        "type": "batch_screening_item_skipped",
                        "paper_id": pid_n,
                        "paper_title": ptitle_n or "Sem título",
                        "message": "Não foi possível triar agora; segue pendente.",
                    },
                )

            if provedor_caiu["motivo"]:
                logger.warning(
                    f"[BatchScreening] Lote do projeto {project_id} interrompido pelo provedor "
                    f"após {processed_count} de {total_papers}."
                )
                await ws_manager.broadcast(
                    project_id,
                    {
                        "type": "batch_screening_failed",
                        "message": (
                            f"{provedor_caiu['motivo']} "
                            f"{processed_count} de {total_papers} estudos foram triados antes da "
                            "interrupção; os demais continuam pendentes."
                        ),
                        "processed": processed_count,
                        "total": total_papers,
                    },
                )
                return

            logger.info(f"[BatchScreening] Finalizada triagem em lote do projeto {project_id}.")
            await ws_manager.broadcast(
                project_id,
                {
                    "type": "batch_screening_completed",
                    "total_processed": processed_count,
                    "included": included_count,
                    "excluded": excluded_count,
                    "pending": total_papers - processed_count,
                    "nao_triados": len(nao_triados),
                    "message": (
                        f"{processed_count} de {total_papers} estudos triados."
                        + (
                            f" {len(nao_triados)} não puderam ser triados agora e seguem pendentes."
                            if nao_triados
                            else ""
                        )
                    ),
                },
            )

        except asyncio.CancelledError:
            # Quem pediu para parar já foi respondido pela rota de cancelamento,
            # que também avisa a tela. Aqui só se registra a interrupção e se
            # deixa o cancelamento seguir — engoli-lo deixaria a tarefa viva.
            logger.info(f"[BatchScreening] Lote do projeto {project_id} cancelado pelo usuário.")
            raise
        except Exception as e:
            # Sem isto, uma falha antes do primeiro progresso morria em silêncio
            # no segundo plano: o modal do lote ficava eternamente em 0/N,
            # esperando um evento que nunca viria.
            logger.exception(f"[BatchScreening] Lote interrompido no projeto {project_id}: {e}")
            await ws_manager.broadcast(
                project_id,
                {
                    "type": "batch_screening_failed",
                    "message": f"A triagem em lote foi interrompida: {e}",
                },
            )
        finally:
            # O estado NÃO é descartado: vira o registro do desfecho, que a
            # tela lê para fechar o quadro. Some sozinho quando outro lote
            # começa no mesmo projeto.
            encerramento = self._batch_state.get(project_id)
            if encerramento is not None:
                encerramento["encerrado"] = True
                encerramento["current_paper_title"] = ""
                encerramento["current_paper_id"] = ""
                # Nenhum estudo fica "em análise" depois que o lote acabou: o
                # que não chegou a ser decidido volta a constar como na fila.
                for item in encerramento.get("itens") or []:
                    if item.get("status") == "em_analise":
                        item["status"] = "na_fila"
            db.close()
