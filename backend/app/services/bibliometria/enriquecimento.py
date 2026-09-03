#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Serviço de Enriquecimento Bibliométrico Externo (docs 47, 48, 49 Fase 2).

Consulta OpenAlex (com fallback Crossref) em lotes de 50 DOIs de forma
assíncrona, incremental e retomável.

Persiste:
- `bib_enrichments`: rodadas e estatísticas da sessão
- `bib_work_meta`: metadados estendidos, citações e payload bruto (raw JSON)
- `bib_references`: referências citadas
- `bib_authorships`: afiliações reais resolvidas por ROR (fecha B-01)
- `bib_topics`: tópicos temáticos
- `bib_keywords`: palavras-chave (fecha B-02)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple

import httpx
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    BibAuthorshipModel,
    BibEnrichmentModel,
    BibKeywordModel,
    BibReferenceModel,
    BibTopicModel,
    BibWorkMetaModel,
    PaperModel,
    generate_uuid,
    utcnow,
)
from app.services.acelerador import AceleradorAdaptativo

logger = logging.getLogger(__name__)

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
CROSSREF_WORKS_URL = "https://api.crossref.org/works"
BATCH_SIZE = 50


def normalizar_doi(doi_str: Optional[str]) -> str:
    """Normaliza um DOI para o formato canônico 10.xxxx/yyyy."""
    if not doi_str:
        return ""
    d = doi_str.strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.IGNORECASE)
    d = re.sub(r"^doi:\s*", "", d, flags=re.IGNORECASE)
    return d.strip()


def extrair_metadados_openalex(
    work: Dict[str, Any], paper_id: str, enrichment_id: str
) -> Tuple[
    BibWorkMetaModel,
    List[BibAuthorshipModel],
    List[BibReferenceModel],
    List[BibTopicModel],
    List[BibKeywordModel],
]:
    """Converte um item do OpenAlex para os modelos relacionais do Revsist."""
    # 1. BibWorkMetaModel
    oa_dict = work.get("open_access") or {}
    work_meta = BibWorkMetaModel(
        paper_id=paper_id,
        enrichment_id=enrichment_id,
        provider="openalex",
        external_id=work.get("id"),
        cited_by_count=work.get("cited_by_count") or 0,
        referenced_works_count=work.get("referenced_works_count") or len(work.get("referenced_works") or []),
        language=work.get("language"),
        doc_type=work.get("type"),
        is_oa=bool(oa_dict.get("is_oa", False)),
        oa_status=oa_dict.get("oa_status"),
        raw=json.dumps(work, ensure_ascii=False),
        obtained_at=utcnow(),
    )

    # 2. BibAuthorshipModel (fecha B-01)
    authorships: List[BibAuthorshipModel] = []
    for pos, auth in enumerate(work.get("authorships") or []):
        autor_obj = auth.get("author") or {}
        autor_id = autor_obj.get("id")
        autor_nome = autor_obj.get("display_name") or ""
        institutions = auth.get("institutions") or []
        countries = auth.get("countries") or []

        if institutions:
            for inst in institutions:
                authorships.append(
                    BibAuthorshipModel(
                        paper_id=paper_id,
                        position=pos,
                        author_external_id=autor_id,
                        author_name=autor_nome,
                        institution_ror=inst.get("ror"),
                        institution_name=inst.get("display_name") or "",
                        country=inst.get("country_code") or (countries[0] if countries else None),
                    )
                )
        else:
            authorships.append(
                BibAuthorshipModel(
                    paper_id=paper_id,
                    position=pos,
                    author_external_id=autor_id,
                    author_name=autor_nome,
                    institution_ror=None,
                    institution_name="",
                    country=countries[0] if countries else None,
                )
            )

    # 3. BibReferenceModel (fecha B-03)
    references: List[BibReferenceModel] = []
    for ref_id in work.get("referenced_works") or []:
        if ref_id:
            references.append(
                BibReferenceModel(
                    citing_paper_id=paper_id,
                    cited_external_id=str(ref_id),
                    cited_doi=None,
                )
            )

    # 4. BibTopicModel
    topics: List[BibTopicModel] = []
    for t in work.get("topics") or []:
        topic_id = t.get("id")
        topic_name = t.get("display_name") or ""
        subfield = t.get("subfield") or {}
        level = subfield.get("id") or 0
        if isinstance(level, str) and "/" in level:
            try:
                level = int(level.split("/")[-1])
            except ValueError:
                level = 0
        score = float(t.get("score") or 0.0)
        topics.append(
            BibTopicModel(
                paper_id=paper_id,
                topic_id=str(topic_id) if topic_id else None,
                topic_name=topic_name,
                level=int(level) if isinstance(level, (int, float)) else 0,
                score=score,
            )
        )

    # 5. BibKeywordModel (fecha B-02)
    keywords: List[BibKeywordModel] = []
    for idx, kw in enumerate(work.get("keywords") or []):
        term = kw.get("display_name") or kw.get("keyword") or ""
        if term:
            keywords.append(
                BibKeywordModel(
                    paper_id=paper_id,
                    term=term,
                    source="openalex",
                    position=idx,
                )
            )

    return work_meta, authorships, references, topics, keywords


def extrair_metadados_crossref(
    item: Dict[str, Any], paper_id: str, enrichment_id: str
) -> Tuple[
    BibWorkMetaModel,
    List[BibAuthorshipModel],
    List[BibReferenceModel],
    List[BibTopicModel],
    List[BibKeywordModel],
]:
    """Fallback: converte resposta Crossref para modelos relacionais."""
    cited_by = item.get("is-referenced-by-count") or 0
    ref_count = item.get("references-count") or len(item.get("reference") or [])
    doc_type = item.get("type")
    language = (item.get("language") or "")[:10] or None

    work_meta = BibWorkMetaModel(
        paper_id=paper_id,
        enrichment_id=enrichment_id,
        provider="crossref",
        external_id=item.get("DOI"),
        cited_by_count=cited_by,
        referenced_works_count=ref_count,
        language=language,
        doc_type=doc_type,
        is_oa=False,
        oa_status=None,
        raw=json.dumps(item, ensure_ascii=False),
        obtained_at=utcnow(),
    )

    authorships: List[BibAuthorshipModel] = []
    for pos, a in enumerate(item.get("author") or []):
        nome = f"{a.get('given', '')} {a.get('family', '')}".strip() or a.get("name") or ""
        affiliations = a.get("affiliation") or []
        if affiliations:
            for aff in affiliations:
                aff_name = aff.get("name") if isinstance(aff, dict) else str(aff)
                authorships.append(
                    BibAuthorshipModel(
                        paper_id=paper_id,
                        position=pos,
                        author_external_id=a.get("ORCID"),
                        author_name=nome,
                        institution_ror=None,
                        institution_name=aff_name or "",
                        country=None,
                    )
                )
        else:
            authorships.append(
                BibAuthorshipModel(
                    paper_id=paper_id,
                    position=pos,
                    author_external_id=a.get("ORCID"),
                    author_name=nome,
                    institution_ror=None,
                    institution_name="",
                    country=None,
                )
            )

    references: List[BibReferenceModel] = []
    for ref in item.get("reference") or []:
        ref_doi = ref.get("DOI")
        ref_key = ref.get("key")
        if ref_doi or ref_key:
            references.append(
                BibReferenceModel(
                    citing_paper_id=paper_id,
                    cited_external_id=ref_key,
                    cited_doi=ref_doi,
                )
            )

    # Crossref subject -> keywords
    keywords: List[BibKeywordModel] = []
    for idx, subj in enumerate(item.get("subject") or []):
        if subj:
            keywords.append(
                BibKeywordModel(
                    paper_id=paper_id,
                    term=str(subj),
                    source="crossref",
                    position=idx,
                )
            )

    return work_meta, authorships, references, [], keywords


class ServicoDeEnriquecimento:
    """Orquestra o enriquecimento de artigos de um projeto com OpenAlex e Crossref."""

    def __init__(
        self,
        mailto: str = "revsist@ufsc.br",
        timeout: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.mailto = mailto
        self.timeout = timeout
        self._custom_client = http_client

    def obter_situacao(self, db: Session, project_id: str) -> Dict[str, Any]:
        """Calcula a cobertura atual de enriquecimento do projeto."""
        total_papers = (
            db.query(PaperModel)
            .filter(PaperModel.project_id == project_id)
            .count()
        )

        papers_with_doi = (
            db.query(PaperModel)
            .filter(
                PaperModel.project_id == project_id,
                PaperModel.doi.isnot(None),
                PaperModel.doi != "",
            )
            .count()
        )

        papers_enriched = (
            db.query(BibWorkMetaModel)
            .join(PaperModel, PaperModel.id == BibWorkMetaModel.paper_id)
            .filter(PaperModel.project_id == project_id)
            .count()
        )

        last_enrichment = (
            db.query(BibEnrichmentModel)
            .filter(BibEnrichmentModel.project_id == project_id)
            .order_by(BibEnrichmentModel.started_at.desc())
            .first()
        )

        return {
            "project_id": project_id,
            "total_papers": total_papers,
            "papers_with_doi": papers_with_doi,
            "papers_enriched": papers_enriched,
            "papers_pending": max(0, papers_with_doi - papers_enriched),
            "coverage_pct": round((papers_enriched / total_papers * 100), 1) if total_papers > 0 else 0.0,
            "last_enrichment": {
                "id": last_enrichment.id,
                "provider": last_enrichment.provider,
                "started_at": last_enrichment.started_at.isoformat() if last_enrichment.started_at else None,
                "completed_at": last_enrichment.completed_at.isoformat() if last_enrichment.completed_at else None,
                "n_consulted": last_enrichment.n_consulted,
                "n_found": last_enrichment.n_found,
                "status": last_enrichment.status,
            }
            if last_enrichment
            else None,
        }

    async def _consultar_openalex_lote(
        self, client: httpx.AsyncClient, doi_list: List[str]
    ) -> List[Dict[str, Any]]:
        """Consulta até 50 DOIs via OpenAlex filter."""
        if not doi_list:
            return []

        dois_param = "|".join(doi_list)
        url = f"{OPENALEX_WORKS_URL}?filter=doi:{dois_param}&per-page={len(doi_list)}"

        headers = {
            "User-Agent": f"Revsist/2.0 (mailto:{self.mailto})",
            "Accept": "application/json",
        }

        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results") or []
            else:
                logger.warning(f"[Enriquecimento] OpenAlex retornou HTTP {resp.status_code} para lote.")
                return []
        except Exception as e:
            logger.warning(f"[Enriquecimento] Falha ao consultar OpenAlex: {e}")
            return []

    async def _consultar_crossref_individual(
        self, client: httpx.AsyncClient, doi: str
    ) -> Optional[Dict[str, Any]]:
        """Consulta Crossref como fallback para um DOI."""
        url = f"{CROSSREF_WORKS_URL}/{doi}"
        headers = {
            "User-Agent": f"Revsist/2.0 (mailto:{self.mailto})",
            "Accept": "application/json",
        }
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message")
        except Exception:
            pass
        return None

    async def executar_enriquecimento(
        self,
        db: Session,
        project_id: str,
        user_id: Optional[str] = None,
        on_progress: Optional[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = None,
        pausa_entre_lotes: float = 0.2,
    ) -> BibEnrichmentModel:
        """Executa rodada de enriquecimento para todos os artigos pendentes com DOI."""
        # 1. Buscar papers com DOI que ainda não foram enriquecidos
        query_pendentes = (
            db.query(PaperModel.id, PaperModel.doi)
            .outerjoin(BibWorkMetaModel, PaperModel.id == BibWorkMetaModel.paper_id)
            .filter(
                PaperModel.project_id == project_id,
                PaperModel.doi.isnot(None),
                PaperModel.doi != "",
                BibWorkMetaModel.paper_id.is_(None),
            )
            .all()
        )

        total_a_processar = len(query_pendentes)
        logger.info(f"[Enriquecimento] Iniciando enriquecimento de {total_a_processar} artigos no projeto {project_id}.")

        enrichment = BibEnrichmentModel(
            id=generate_uuid(),
            project_id=project_id,
            provider="openalex",
            started_at=utcnow(),
            n_consulted=0,
            n_found=0,
            status="em_andamento",
            created_by_user_id=user_id,
        )
        db.add(enrichment)
        db.commit()

        if total_a_processar == 0:
            enrichment.status = "concluido"
            enrichment.completed_at = utcnow()
            db.commit()
            if on_progress:
                await on_progress({
                    "type": "enrichment_completed",
                    "project_id": project_id,
                    "enrichment_id": enrichment.id,
                    "n_consulted": 0,
                    "n_found": 0,
                    "total": 0,
                })
            return enrichment

        # Mapeamento normalizado de doi -> paper_id
        doi_para_paper_id: Dict[str, str] = {}
        for pid, doi_raw in query_pendentes:
            d_norm = normalizar_doi(doi_raw)
            if d_norm:
                doi_para_paper_id[d_norm] = pid

        dois_unicos = list(doi_para_paper_id.keys())
        acelerador = AceleradorAdaptativo(teto=4, pausa_inicial=pausa_entre_lotes)

        client_ctx = (
            self._custom_client
            if self._custom_client is not None
            else httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        )

        async with client_ctx as client:
            # Processa em lotes de 50 DOIs
            for i in range(0, len(dois_unicos), BATCH_SIZE):
                lote_dois = dois_unicos[i : i + BATCH_SIZE]
                enrichment.n_consulted += len(lote_dois)

                results = await self._consultar_openalex_lote(client, lote_dois)
                dois_encontrados_openalex: Set[str] = set()

                for work in results:
                    work_doi = normalizar_doi(work.get("doi"))
                    paper_id = doi_para_paper_id.get(work_doi)

                    # Se não bateu pelo DOI direto do work, tenta pelo id
                    if not paper_id:
                        for d in lote_dois:
                            if d.lower() in (work.get("doi") or "").lower():
                                paper_id = doi_para_paper_id.get(d)
                                work_doi = d
                                break

                    if paper_id:
                        dois_encontrados_openalex.add(work_doi)
                        meta, authors, refs, topics, kws = extrair_metadados_openalex(
                            work, paper_id, enrichment.id
                        )
                        db.add(meta)
                        for a in authors:
                            db.add(a)
                        for r in refs:
                            db.add(r)
                        for t in topics:
                            db.add(t)
                        for k in kws:
                            db.add(k)
                        enrichment.n_found += 1

                # Fallback Crossref para os DOIs do lote não encontrados no OpenAlex
                dois_faltantes = [d for d in lote_dois if d not in dois_encontrados_openalex]
                for d in dois_faltantes:
                    crossref_msg = await self._consultar_crossref_individual(client, d)
                    if crossref_msg:
                        paper_id = doi_para_paper_id[d]
                        meta, authors, refs, topics, kws = extrair_metadados_crossref(
                            crossref_msg, paper_id, enrichment.id
                        )
                        db.add(meta)
                        for a in authors:
                            db.add(a)
                        for r in refs:
                            db.add(r)
                        for k in kws:
                            db.add(k)
                        enrichment.n_found += 1

                db.commit()

                if on_progress:
                    await on_progress({
                        "type": "enrichment_progress",
                        "project_id": project_id,
                        "enrichment_id": enrichment.id,
                        "n_consulted": enrichment.n_consulted,
                        "n_found": enrichment.n_found,
                        "total": len(dois_unicos),
                        "pct": round((enrichment.n_consulted / len(dois_unicos)) * 100, 1),
                    })

                if pausa_entre_lotes > 0:
                    await asyncio.sleep(pausa_entre_lotes)

        enrichment.status = "concluido"
        enrichment.completed_at = utcnow()
        db.commit()

        if on_progress:
            await on_progress({
                "type": "enrichment_completed",
                "project_id": project_id,
                "enrichment_id": enrichment.id,
                "n_consulted": enrichment.n_consulted,
                "n_found": enrichment.n_found,
                "total": len(dois_unicos),
            })

        logger.info(
            f"[Enriquecimento] Concluído para o projeto {project_id}: "
            f"{enrichment.n_found}/{enrichment.n_consulted} DOIs enriquecidos com sucesso."
        )
        return enrichment
