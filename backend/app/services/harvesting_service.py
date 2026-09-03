#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Serviço Orquestrador de Coleta (Harvesting Service).
Coordena a execução concorrente de múltiplos coletores científicos com:
  - Resolução de credenciais do banco
  - Resolução de filtros de busca do protocolo (anos, idiomas, tipos)
  - Concorrência limitada via semáforo (até 3 fontes simultâneas)
  - Persistência em lote fora do event loop (batch dedup)
  - Stream de progresso e lotes via WebSockets
  - Suporte completo a cancelamento
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from fastapi import WebSocket

from app.database import SessionLocal
from app.harvesters.base import (
    HarvestProgress,
    HarvestQuery,
    RawPaperRecord,
)
from app.harvesters.factory import HarvesterFactory
from app.infrastructure.persistence.models import (
    HarvestRunModel,
    ProtocolModel,
    ProjectModel,
    SearchStrategyModel,
    SourceCredentialModel,
)
from app.services.dedup_service import DeduplicationService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerenciador de conexões WebSocket e presença para colaboração ao vivo (Doc 43 §43.12)."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.presence: Dict[str, Dict[str, dict]] = {}
        self.ws_meta: Dict[WebSocket, tuple[str, str]] = {}

    async def connect(
        self,
        project_id: str,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        screen: Optional[str] = "geral",
    ):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()
            self.presence[project_id] = {}
        self.active_connections[project_id].add(websocket)
        if user_id:
            self.ws_meta[websocket] = (project_id, user_id)
            self.presence[project_id][user_id] = {
                "user_id": user_id,
                "username": username or user_id,
                "screen": screen or "geral",
                "connected_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.broadcast(
                project_id,
                {
                    "type": "presenca",
                    "user_id": user_id,
                    "username": username or user_id,
                    "tela": screen or "geral",
                    "status": "online",
                    "active_users": list(self.presence[project_id].values()),
                },
            )

    async def update_presence(self, project_id: str, user_id: str, username: str, screen: str):
        if project_id in self.presence:
            self.presence[project_id][user_id] = {
                "user_id": user_id,
                "username": username,
                "screen": screen,
                "connected_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.broadcast(
                project_id,
                {
                    "type": "presenca",
                    "user_id": user_id,
                    "username": username,
                    "tela": screen,
                    "status": "online",
                    "active_users": list(self.presence[project_id].values()),
                },
            )

    def disconnect(self, project_id: str, websocket: WebSocket):
        if project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)
            meta = self.ws_meta.pop(websocket, None)
            if meta:
                _, u_id = meta
                still_connected = any(
                    self.ws_meta.get(ws) == (project_id, u_id)
                    for ws in self.active_connections.get(project_id, set())
                )
                if not still_connected and project_id in self.presence:
                    user_info = self.presence[project_id].pop(u_id, None)
                    if user_info:
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(
                                self.broadcast(
                                    project_id,
                                    {
                                        "type": "presenca",
                                        "user_id": u_id,
                                        "username": user_info.get("username", ""),
                                        "tela": user_info.get("screen", ""),
                                        "status": "offline",
                                        "active_users": list(self.presence[project_id].values()),
                                    },
                                )
                            )
                        except RuntimeError:
                            pass
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
                self.presence.pop(project_id, None)

    # Tempo máximo que UMA conexão pode segurar uma transmissão. Um socket
    # saudável entrega em milissegundos; passar disso significa que o outro
    # lado sumiu sem fechar — e nenhuma tela vale travar quem produz o evento.
    TIMEOUT_DE_ENVIO = 5.0

    async def broadcast(self, project_id: str, message: dict):
        """
        Envia a todos, sem deixar ninguém segurar o produtor.

        A versão anterior fazia `await ws.send_json(...)` em série e sem prazo.
        Um cliente que some sem fechar a conexão — aba encerrada à força, queda
        de rede, servidor reiniciado pelo `--reload` — deixa o objeto do socket
        vivo aqui dentro: o `send` não levanta exceção, ele escreve no buffer
        do transporte e fica esperando o outro lado confirmar. Quando o buffer
        enche, o `await` simplesmente não volta.

        Quem pagava por isso era a triagem em lote, que transmite duas vezes por
        artigo: anunciava o início e travava no primeiro estudo, sem erro no
        log e sem nada na tela. A triagem individual seguia funcionando porque
        responde pelo próprio HTTP, sem passar por aqui — foi essa assimetria
        que escondeu a causa.

        Agora cada envio tem prazo, e todos correm em paralelo: uma conexão
        ruim é descartada em vez de contaminar as outras.
        """
        conexoes = list(self.active_connections.get(project_id, ()))
        if not conexoes:
            return

        async def _enviar(ws):
            try:
                await asyncio.wait_for(ws.send_json(message), timeout=self.TIMEOUT_DE_ENVIO)
                return None
            except asyncio.TimeoutError:
                logger.warning(
                    "[WS] Conexão do projeto %s não recebeu em %.0fs; descartada.",
                    project_id, self.TIMEOUT_DE_ENVIO,
                )
                return ws
            except Exception:
                return ws

        resultados = await asyncio.gather(*(_enviar(ws) for ws in conexoes))

        for morto in filter(None, resultados):
            self.active_connections.get(project_id, set()).discard(morto)
            self.ws_meta.pop(morto, None)
            # Fechar libera o socket do lado do servidor; sem isto o descarte
            # tira da lista mas deixa o recurso pendurado.
            try:
                await morto.close(code=1011)
            except Exception:
                pass

        if project_id in self.active_connections and not self.active_connections[project_id]:
            del self.active_connections[project_id]
            self.presence.pop(project_id, None)


ws_manager = ConnectionManager()


class HarvestingService:
    """Orquestrador de coleta com processamento concorrente e deduplicação em lote."""

    def __init__(self):
        self.dedup_service = DeduplicationService()
        self._source_semaphore = asyncio.Semaphore(3)  # Máximo de 3 fontes em paralelo

    def _load_credentials(self, db, owner_id: Optional[str] = None) -> Dict[str, dict]:
        """
        Carrega as credenciais das fontes para o usuário informado.

        Quando o usuário informa uma chave institucional (Doc 29 §29.3.2) ela é
        utilizada aqui; quando não há, o coletor roda em modo anônimo se a
        fonte permitir, ou é pulado com aviso quando a chave for obrigatória pelo
        contrato de licença da base.
        """
        creds = {}
        try:
            consulta = db.query(SourceCredentialModel)
            if owner_id:
                consulta = consulta.filter(SourceCredentialModel.user_id == owner_id)
            records = consulta.all()
            for r in records:
                creds[r.source_name.upper()] = {
                    "api_key": r.api_key,
                    "inst_token": r.inst_token,
                    "custom_endpoint": r.custom_endpoint,
                }
        except Exception as e:
            logger.warning(f"[Harvesting] Aviso ao carregar credenciais: {e}")
        return creds

    async def _harvest_single_source(
        self,
        project_id: str,
        source_name: str,
        query: HarvestQuery,
        creds: dict,
        user_id: Optional[str] = None,
    ):
        """Executa a coleta de uma fonte individual com persistência em lote."""
        async with self._source_semaphore:
            db = SessionLocal()
            run = HarvestRunModel(
                project_id=project_id,
                source_name=source_name,
                descriptors_used=json.dumps(query.descriptors, ensure_ascii=False),
                query_parameters=json.dumps(
                    {
                        "year_start": query.year_start,
                        "year_end": query.year_end,
                        "languages": query.languages,
                        "document_types": query.document_types,
                        "max_records": query.max_records_per_descriptor,
                    },
                    ensure_ascii=False,
                ),
                started_at=datetime.now(timezone.utc),
                status="running",
                run_by_user_id=user_id,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = run.id
            db.close()

            found_count = 0
            new_count = 0
            dup_count = 0

            # Coletar em lotes de 25 registros para evitar fsync O(N^2).
            # Definidos fora do `try` porque o tratamento de falha também
            # precisa gravar o lote pendente.
            batch_records: List[RawPaperRecord] = []

            def _persist_batch_sync(records: List[RawPaperRecord], cur_found: Optional[int] = None):
                session = SessionLocal()
                try:
                    n_c, d_c, summaries = self.dedup_service.process_batch(
                        session, project_id, records
                    )
                    # Atualiza o status intermediário do run para que o polling de /status mostre os números em tempo real
                    if cur_found is not None:
                        run_rec = session.query(HarvestRunModel).filter(HarvestRunModel.id == run_id).first()
                        if run_rec:
                            run_rec.records_found = cur_found
                            run_rec.records_new = (run_rec.records_new or 0) + n_c
                            run_rec.records_duplicate = (run_rec.records_duplicate or 0) + d_c
                            session.commit()
                    return n_c, d_c, summaries
                finally:
                    session.close()

            # Aviso de coleta parcial emitido pelo coletor no evento final —
            # é gravado na execução para que a incompletude fique registrada.
            aviso_do_coletor: Dict[str, Optional[str]] = {"mensagem": None}

            try:
                source_creds = creds.get(source_name.upper(), {})
                harvester = HarvesterFactory.get_harvester(
                    source=source_name,
                    api_key=source_creds.get("api_key") or None,
                    inst_token=source_creds.get("inst_token") or None,
                    custom_endpoint=source_creds.get("custom_endpoint") or None,
                )

                async def on_progress_callback(prog: HarvestProgress):
                    if prog.error:
                        aviso_do_coletor["mensagem"] = prog.error
                    await ws_manager.broadcast(
                        project_id,
                        {
                            "type": "harvest_progress",
                            "run_id": run_id,
                            "source": source_name,
                            "descriptor": prog.current_descriptor,
                            "page": prog.page,
                            "total_found": prog.total_found_so_far,
                            "phase": prog.phase,
                            "is_complete": prog.is_complete,
                            "error": prog.error,
                        },
                    )

                async for raw_record in harvester.harvest(query=query, on_progress=on_progress_callback):
                    found_count += 1
                    batch_records.append(raw_record)

                    if len(batch_records) >= 25:
                        batch_to_process = list(batch_records)
                        batch_records.clear()

                        b_new, b_dup, summaries = await asyncio.to_thread(
                            _persist_batch_sync, batch_to_process, found_count
                        )
                        new_count += b_new
                        dup_count += b_dup

                        # Emitir atualização em lote
                        last_items = [
                            {"paper_id": pid, "title": t, "is_new": is_n}
                            for pid, t, is_n in summaries[-5:]
                        ]
                        await ws_manager.broadcast(
                            project_id,
                            {
                                "type": "paper_harvested",
                                "run_id": run_id,
                                "source": source_name,
                                "total_found": found_count,
                                "total_new": new_count,
                                "total_duplicate": dup_count,
                                "recent_items": last_items,
                            },
                        )

                # Processar lote remanescente
                if batch_records:
                    b_new, b_dup, summaries = await asyncio.to_thread(
                        _persist_batch_sync, batch_records, found_count
                    )
                    new_count += b_new
                    dup_count += b_dup

                # Concluir run com sucesso
                db = SessionLocal()
                run_obj = db.query(HarvestRunModel).filter(HarvestRunModel.id == run_id).first()
                if run_obj:
                    run_obj.status = "completed"
                    run_obj.completed_at = datetime.now(timezone.utc)
                    run_obj.records_found = found_count
                    run_obj.records_new = new_count
                    run_obj.records_duplicate = dup_count
                    run_obj.error_message = aviso_do_coletor["mensagem"]
                    db.commit()
                db.close()

                await ws_manager.broadcast(
                    project_id,
                    {
                        "type": "harvest_source_completed",
                        "run_id": run_id,
                        "source": source_name,
                        "records_found": found_count,
                        "records_new": new_count,
                        "records_duplicate": dup_count,
                        "warning": aviso_do_coletor["mensagem"],
                    },
                )

            except asyncio.CancelledError:
                logger.info(f"[Harvesting] Coleta da fonte {source_name} cancelada.")
                db = SessionLocal()
                run_obj = db.query(HarvestRunModel).filter(HarvestRunModel.id == run_id).first()
                if run_obj:
                    run_obj.status = "cancelled"
                    run_obj.completed_at = datetime.now(timezone.utc)
                    run_obj.error_message = "Cancelada pelo usuário."
                    run_obj.records_found = found_count
                    run_obj.records_new = new_count
                    run_obj.records_duplicate = dup_count
                    db.commit()
                db.close()
                raise

            except Exception as e:
                logger.error(f"[Harvesting] Falha no coletor {source_name}: {e}")

                # Uma fonte pode falhar depois de já ter entregue registros. O
                # lote pendente (< 25) é gravado antes de marcar a execução como
                # falha: descartá-lo perderia trabalho já recuperado da base.
                if batch_records:
                    try:
                        b_new, b_dup, _ = await asyncio.to_thread(_persist_batch_sync, list(batch_records), found_count)
                        new_count += b_new
                        dup_count += b_dup
                    except Exception as persist_error:
                        logger.error(
                            f"[Harvesting] Falha ao gravar o lote pendente de {source_name}: {persist_error}"
                        )
                    finally:
                        batch_records.clear()

                db = SessionLocal()
                run_obj = db.query(HarvestRunModel).filter(HarvestRunModel.id == run_id).first()
                if run_obj:
                    run_obj.status = "failed"
                    run_obj.error_message = str(e)
                    run_obj.completed_at = datetime.now(timezone.utc)
                    run_obj.records_found = found_count
                    run_obj.records_new = new_count
                    run_obj.records_duplicate = dup_count
                    db.commit()
                db.close()

                await ws_manager.broadcast(
                    project_id,
                    {
                        "type": "harvest_source_failed",
                        "run_id": run_id,
                        "source": source_name,
                        "error": str(e),
                    },
                )

    async def run_harvest(
        self,
        project_id: str,
        sources: List[str],
        max_records_per_descriptor: Optional[int] = None,
        custom_descriptors: Optional[List[str]] = None,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        languages: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None,
        institutions: Optional[List[str]] = None,
        open_access_only: Optional[bool] = None,
        fetch_details: bool = True,
        user_id: Optional[str] = None,
    ):
        """Orquestra a coleta de múltiplos coletores em paralelo usando as credenciais do ator (Doc 43 §43.11)."""
        db = SessionLocal()
        try:
            protocol = db.query(ProtocolModel).filter(ProtocolModel.project_id == project_id).first()
            if not protocol:
                logger.error(f"[Harvesting] Protocolo não encontrado para projeto {project_id}")
                return

            descriptors: List[str] = []
            if custom_descriptors:
                descriptors = [d.strip() for d in custom_descriptors if d.strip()]
            elif protocol.search_descriptors:
                try:
                    desc_dict = json.loads(protocol.search_descriptors)
                    for lang, pairs in desc_dict.items():
                        descriptors.extend([p.strip() for p in pairs if p.strip()])
                except Exception:
                    pass

            # Fallback 1: Buscar da estratégia canônica salva no estúdio (SearchStrategyModel)
            if not descriptors:
                strat = db.query(SearchStrategyModel).filter(
                    SearchStrategyModel.protocol_id == protocol.id,
                    SearchStrategyModel.kind == "canonica",
                ).first()
                if strat and strat.blocks:
                    try:
                        from app.services.search_strategy_service import render_bdtd_decomposition
                        blocks = json.loads(strat.blocks)
                        pairs, _ = render_bdtd_decomposition(blocks, max_pairs=10)
                        descriptors.extend([p.strip() for p in pairs if p.strip()])
                    except Exception as e:
                        logger.warning(f"[Harvesting] Falha ao extrair descritores da estratégia: {e}")

            # Fallback 2: Se ainda vazio, sintetizar dos componentes da pergunta (PCC / PICO)
            if not descriptors and protocol.pico_framework:
                try:
                    from app.services.search_strategy_service import _quote_term
                    pico_dict = json.loads(protocol.pico_framework)
                    pop = pico_dict.get("population", "").strip()
                    con = (pico_dict.get("intervention") or pico_dict.get("concept", "")).strip()
                    if pop and con:
                        descriptors.append(f"{_quote_term(pop)} AND {_quote_term(con)}")
                    elif pop:
                        descriptors.append(_quote_term(pop))
                    elif con:
                        descriptors.append(_quote_term(con))
                except Exception as e:
                    logger.warning(f"[Harvesting] Falha ao extrair descritores do framework PICO/PCC: {e}")

            if not descriptors:
                logger.warning(f"[Harvesting] Nenhum descritor configurado para o projeto {project_id}")
                await ws_manager.broadcast(
                    project_id,
                    {
                        "type": "harvest_error",
                        "message": "Nenhum descritor de busca configurado no protocolo.",
                    },
                )
                return

            # Resolver filtros do protocolo
            proto_filters = {}
            if protocol.search_filters:
                try:
                    proto_filters = json.loads(protocol.search_filters)
                except Exception:
                    pass

            effective_year_start = year_start if year_start is not None else proto_filters.get("year_start")
            effective_year_end = year_end if year_end is not None else proto_filters.get("year_end")
            effective_languages = languages if languages is not None else proto_filters.get("languages", [])
            effective_doc_types = document_types if document_types is not None else proto_filters.get("document_types", [])
            effective_institutions = institutions if institutions is not None else proto_filters.get("institutions", [])
            effective_oa = open_access_only if open_access_only is not None else proto_filters.get("open_access_only", False)

            harvest_query = HarvestQuery(
                descriptors=descriptors,
                year_start=effective_year_start,
                year_end=effective_year_end,
                languages=effective_languages,
                document_types=effective_doc_types,
                institutions=effective_institutions,
                open_access_only=bool(effective_oa),
                max_records_per_descriptor=max_records_per_descriptor,
                fetch_details=fetch_details,
            )

            # O usuário que aciona a coleta utiliza as suas próprias credenciais (D-03)
            # com fallback para o dono do projeto se invocado em tarefa desacoplada.
            dono = (
                db.query(ProjectModel.owner_id)
                .filter(ProjectModel.id == project_id)
                .scalar()
            )
            creds = self._load_credentials(db, owner_id=user_id or dono)

        finally:
            db.close()

        logger.info(
            f"[Harvesting] Iniciando coleta paralela para projeto {project_id} nas fontes {sources} "
            f"com {len(descriptors)} descritores."
        )

        tasks = [
            self._harvest_single_source(project_id, s, harvest_query, creds, user_id=user_id)
            for s in sources
        ]

        # Execução concorrente de todas as fontes selecionadas
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"[Harvesting] Coleta finalizada para todas as fontes do projeto {project_id}.")
        await ws_manager.broadcast(
            project_id,
            {"type": "harvest_all_completed", "project_id": project_id},
        )
