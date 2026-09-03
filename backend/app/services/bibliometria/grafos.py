#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Grafos e Análise Estrutural (doc 48 §8, §12, doc 49 Fase 6).

Fecha B-08:
    - Quatro redes num só motor: coautoria, coocorrência de termos,
      acoplamento bibliográfico e cocitação.
    - Normalização de força: Força de Associação (VOSviewer / Van Eck & Waltman 2009),
      Jaccard e Cosseno.
    - Agrupamento Louvain com semente fixa e resolução ajustável.
    - Layout espacial Fruchterman-Reingold calculado no servidor com semente fixa.
    - Exportação para GraphML e GEXF com coordenadas.
"""

from __future__ import annotations

import io
import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
from sqlalchemy.orm import Session

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibAuthorshipModel,
    BibGrafoModel,
    BibKeywordModel,
    BibReferenceModel,
    BibSnapshotModel,
    BibThesaurusEntryModel,
    BibThesaurusModel,
    PaperModel,
    ProjectModel,
)
from app.services.bibliometria.indicadores import dividir_autores
from app.services.bibliometria.tesauro import ServicoDeTesauro, normalizar_forma

logger = logging.getLogger(__name__)

# Paleta cromática equilibrada para clusters
PALETA_CLUSTERS = [
    "#2563eb",  # Azul
    "#16a34a",  # Verde
    "#d97706",  # Âmbar
    "#9333ea",  # Roxo
    "#0d9488",  # Teal
    "#e11d48",  # Rosa
    "#0284c7",  # Ciano
    "#4f46e5",  # Índigo
    "#84cc16",  # Lima
    "#ea580c",  # Laranja
]


def calcular_forca_aresta(
    c_ij: int, c_i: int, c_j: int, total_coocorrencias: int, normalizacao: str = "association_strength"
) -> float:
    """Calcula o peso normalizado da aresta conforme o método escolhido."""
    if c_ij <= 0 or c_i <= 0 or c_j <= 0:
        return 0.0

    if normalizacao == "jaccard":
        den = c_i + c_j - c_ij
        return round(c_ij / den, 4) if den > 0 else 0.0

    if normalizacao == "cosine":
        den = math.sqrt(c_i * c_j)
        return round(c_ij / den, 4) if den > 0 else 0.0

    # Padrão VOSviewer: Força de Associação (Van Eck & Waltman, 2009)
    # s_ij = (c_ij * 2 * total) / (c_i * c_j) ou normalizado proporcional
    den = c_i * c_j
    s = (c_ij * 2 * max(1, total_coocorrencias)) / den if den > 0 else 0.0
    return round(s, 4)


class ServicoDeGrafos:
    """Motor unificado de análise de redes bibliométricas e layout determinístico."""

    def __init__(self):
        self.servico_tesauro = ServicoDeTesauro()

    def _obter_papers(
        self, db: Session, project_id: str, snapshot_id: Optional[str] = None
    ) -> list[PaperModel]:
        """Obtém lista de estudos do instantâneo ou os estudos incluídos do projeto."""
        if snapshot_id:
            snap = db.query(BibSnapshotModel).filter(BibSnapshotModel.id == snapshot_id).first()
            if snap and snap.scope:
                escopo = json.loads(snap.scope)
                q = db.query(PaperModel).filter(PaperModel.project_id == project_id)
                if escopo.get("decisions"):
                    q = q.filter(PaperModel.decision.in_(escopo["decisions"]))
                return q.all()

        return (
            db.query(PaperModel)
            .filter(
                PaperModel.project_id == project_id,
                PaperModel.decision == Decision.INCLUDED.value,
            )
            .all()
        )

    def extrair_rede_coautoria(
        self, db: Session, papers: list[PaperModel]
    ) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
        """Extrai contagens individuais e coautorias."""
        paper_ids = [p.id for p in papers]
        authorships = (
            db.query(BibAuthorshipModel)
            .filter(BibAuthorshipModel.paper_id.in_(paper_ids))
            .order_by(BibAuthorshipModel.paper_id, BibAuthorshipModel.position)
            .all()
        )

        autores_por_doc: dict[str, list[str]] = defaultdict(list)
        if authorships:
            for a in authorships:
                if a.author_name:
                    autores_por_doc[a.paper_id].append(a.author_name.strip())
        else:
            # Fallback para parsing em PaperModel.authors
            for p in papers:
                if p.authors:
                    autores_por_doc[p.id] = dividir_autores(p.authors)

        contagem_nos: dict[str, int] = defaultdict(int)
        coocorrencias: dict[tuple[str, str], int] = defaultdict(int)

        for doc_id, autores in autores_por_doc.items():
            autores_unicos = sorted(list(set(a for a in autores if a)))
            for a in autores_unicos:
                contagem_nos[a] += 1

            for i in range(len(autores_unicos)):
                for j in range(i + 1, len(autores_unicos)):
                    par = (autores_unicos[i], autores_unicos[j])
                    coocorrencias[par] += 1

        return contagem_nos, coocorrencias

    def extrair_rede_termos(
        self, db: Session, project_id: str, papers: list[PaperModel]
    ) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
        """Extrai rede de coocorrência de termos com normalização por tesauro aprovado."""
        paper_ids = [p.id for p in papers]
        keywords = (
            db.query(BibKeywordModel)
            .filter(BibKeywordModel.paper_id.in_(paper_ids))
            .all()
        )

        # Buscar tesauro e entradas aprovadas do projeto
        t_padrao = self.servico_tesauro.obter_ou_criar_tesauro_padrao(db, project_id)
        entradas_aprovadas = self.servico_tesauro.listar_entradas(db, t_padrao.id, apenas_aprovadas=True)

        termos_por_doc: dict[str, list[str]] = defaultdict(list)
        if keywords:
            for kw in keywords:
                if kw.term:
                    termos_por_doc[kw.paper_id].append(kw.term.strip())
        else:
            # Fallback para título e palavras-chave de PaperModel
            for p in papers:
                if p.title:
                    palavras = [w for w in normalizar_forma(p.title).split() if len(w) > 3]
                    termos_por_doc[p.id].extend(palavras)

        contagem_nos: dict[str, int] = defaultdict(int)
        coocorrencias: dict[tuple[str, str], int] = defaultdict(int)

        for doc_id, termos_brutos in termos_por_doc.items():
            termos_unificados = self.servico_tesauro.aplicar_tesauro(termos_brutos, entradas_aprovadas)
            termos_unicos = sorted(list(set(t for t in termos_unificados if t)))

            for t in termos_unicos:
                contagem_nos[t] += 1

            for i in range(len(termos_unicos)):
                for j in range(i + 1, len(termos_unicos)):
                    par = (termos_unicos[i], termos_unicos[j])
                    coocorrencias[par] += 1

        return contagem_nos, coocorrencias

    def extrair_rede_acoplamento(
        self, db: Session, papers: list[PaperModel], max_docs: int = 1000
    ) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
        """Extrai acoplamento bibliográfico (estudos conectados por referências compartilhadas)."""
        if len(papers) > max_docs:
            raise ValueError(
                f"O acoplamento bibliográfico sobre {len(papers)} documentos excede o teto computacional seguro ({max_docs}). "
                "Aplique filtros de ano ou decisão antes de gerar o acoplamento."
            )

        paper_ids = [p.id for p in papers]
        refs = (
            db.query(BibReferenceModel)
            .filter(BibReferenceModel.citing_paper_id.in_(paper_ids))
            .all()
        )

        refs_por_doc: dict[str, set[str]] = defaultdict(set)
        for r in refs:
            ref_id = r.cited_doi or r.cited_external_id
            if ref_id:
                refs_por_doc[r.citing_paper_id].add(ref_id)

        # Mapa paper_id -> rótulo (Sobrenome, Ano)
        rotulos: dict[str, str] = {}
        for p in papers:
            prim_autor = p.authors.split(";")[0].split(",")[0].strip() if p.authors else "Anon"
            rotulos[p.id] = f"{prim_autor} ({p.year or 's.d.'})"

        contagem_nos: dict[str, int] = {}
        for p in papers:
            contagem_nos[rotulos[p.id]] = len(refs_por_doc[p.id]) or 1

        coocorrencias: dict[tuple[str, str], int] = defaultdict(int)
        doc_ids = sorted(list(refs_por_doc.keys()))
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                id_a, id_b = doc_ids[i], doc_ids[j]
                intersec = len(refs_por_doc[id_a] & refs_por_doc[id_b])
                if intersec > 0:
                    par = (rotulos[id_a], rotulos[id_b])
                    coocorrencias[par] = intersec

        return contagem_nos, coocorrencias

    def extrair_rede_cocitacao(
        self, db: Session, papers: list[PaperModel]
    ) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
        """Extrai rede de cocitação (referências citadas conjuntamente no mesmo estudo)."""
        paper_ids = [p.id for p in papers]
        refs = (
            db.query(BibReferenceModel)
            .filter(BibReferenceModel.citing_paper_id.in_(paper_ids))
            .all()
        )

        refs_por_doc: dict[str, set[str]] = defaultdict(set)
        for r in refs:
            ref_id = r.cited_doi or r.cited_external_id
            if ref_id:
                refs_por_doc[r.citing_paper_id].add(ref_id)

        contagem_nos: dict[str, int] = defaultdict(int)
        coocorrencias: dict[tuple[str, str], int] = defaultdict(int)

        for doc_id, citadas in refs_por_doc.items():
            citadas_unicas = sorted(list(citadas))
            for c in citadas_unicas:
                contagem_nos[c] += 1

            for i in range(len(citadas_unicas)):
                for j in range(i + 1, len(citadas_unicas)):
                    par = (citadas_unicas[i], citadas_unicas[j])
                    coocorrencias[par] += 1

        return contagem_nos, coocorrencias

    def construir_grafo(
        self,
        db: Session,
        project_id: str,
        network_type: str = "coautoria",
        snapshot_id: Optional[str] = None,
        normalizacao: str = "association_strength",
        corte_minimo: int = 1,
        max_nos: int = 100,
        resolucao_louvain: float = 1.0,
        semente: int = 42,
        iteracoes_fr: int = 200,
    ) -> BibGrafoModel:
        """Gera a rede com layout determinístico Fruchterman-Reingold e clusters Louvain."""
        papers = self._obter_papers(db, project_id, snapshot_id)
        if not papers:
            raise ValueError("Nenhum estudo encontrado no escopo para geração do grafo.")

        # 1. Extração da rede
        if network_type == "coautoria":
            contagem_nos, coocorrencias = self.extrair_rede_coautoria(db, papers)
        elif network_type == "coocorrencia_termos":
            contagem_nos, coocorrencias = self.extrair_rede_termos(db, project_id, papers)
        elif network_type == "acoplamento_bibliografico":
            contagem_nos, coocorrencias = self.extrair_rede_acoplamento(db, papers)
        elif network_type == "cocitacao":
            contagem_nos, coocorrencias = self.extrair_rede_cocitacao(db, papers)
        else:
            raise ValueError(f"Tipo de rede desconhecido: '{network_type}'.")

        # Filtrar nós pelo corte mínimo e top N
        nos_filtrados = {k: v for k, v in contagem_nos.items() if v >= corte_minimo}
        nos_ordenados = sorted(nos_filtrados.items(), key=lambda x: x[1], reverse=True)[:max_nos]
        conjunto_nos_validos = set(k for k, _ in nos_ordenados)

        # Montar grafo NetworkX
        G = nx.Graph()
        for no_rotulo, peso_no in nos_ordenados:
            G.add_node(no_rotulo, weight=peso_no)

        total_cooc = sum(coocorrencias.values())
        arestas_lista = []
        for (u, v), c_ij in coocorrencias.items():
            if u in conjunto_nos_validos and v in conjunto_nos_validos and c_ij >= corte_minimo:
                forca = calcular_forca_aresta(
                    c_ij, contagem_nos[u], contagem_nos[v], total_cooc, normalizacao=normalizacao
                )
                G.add_edge(u, v, weight=forca, count=c_ij)
                arestas_lista.append(
                    {
                        "source": u,
                        "target": v,
                        "weight": forca,
                        "count": c_ij,
                    }
                )

        # 2. Agrupamento Louvain com semente fixa
        comunidades_map: dict[str, int] = {}
        if G.number_of_nodes() > 0:
            comunidades = nx.community.louvain_communities(
                G, weight="weight", resolution=resolucao_louvain, seed=semente
            )
            for idx_c, grupo in enumerate(comunidades):
                for no in grupo:
                    comunidades_map[no] = idx_c

        # 3. Layout Fruchterman-Reingold determinístico
        coordenadas: dict[str, dict[str, float]] = {}
        if G.number_of_nodes() > 0:
            pos = nx.spring_layout(G, weight="weight", iterations=iteracoes_fr, seed=semente)
            for no, (x, y) in pos.items():
                coordenadas[no] = {"x": round(float(x), 4), "y": round(float(y), 4)}

        # 4. Estruturação dos nós com clusters e graus
        nos_estruturados = []
        clusters_meta: dict[int, dict[str, Any]] = defaultdict(lambda: {"count": 0, "nodes": [], "color": ""})

        for no_rotulo, peso_no in nos_ordenados:
            cluster_id = comunidades_map.get(no_rotulo, 0)
            cor = PALETA_CLUSTERS[cluster_id % len(PALETA_CLUSTERS)]
            grau = G.degree(no_rotulo) if G.has_node(no_rotulo) else 0

            clusters_meta[cluster_id]["count"] += 1
            clusters_meta[cluster_id]["nodes"].append(no_rotulo)
            clusters_meta[cluster_id]["color"] = cor

            nos_estruturados.append(
                {
                    "id": no_rotulo,
                    "label": no_rotulo,
                    "size": peso_no,
                    "degree": grau,
                    "cluster": cluster_id,
                    "color": cor,
                    "x": coordenadas.get(no_rotulo, {}).get("x", 0.0),
                    "y": coordenadas.get(no_rotulo, {}).get("y", 0.0),
                }
            )

        parametros = {
            "network_type": network_type,
            "normalizacao": normalizacao,
            "corte_minimo": corte_minimo,
            "max_nos": max_nos,
            "resolucao_louvain": resolucao_louvain,
            "semente": semente,
            "iteracoes_fr": iteracoes_fr,
            "n_papers": len(papers),
        }

        # 5. Persistência
        grafo_model = BibGrafoModel(
            project_id=project_id,
            snapshot_id=snapshot_id,
            network_type=network_type,
            parameters=json.dumps(parametros, ensure_ascii=False),
            nodes=json.dumps(nos_estruturados, ensure_ascii=False),
            edges=json.dumps(arestas_lista, ensure_ascii=False),
            coordinates=json.dumps(coordenadas, ensure_ascii=False),
            clusters=json.dumps(dict(clusters_meta), ensure_ascii=False),
            seed=semente,
            calculated_at=datetime.now(timezone.utc),
        )
        db.add(grafo_model)
        db.commit()
        db.refresh(grafo_model)
        return grafo_model

    def exportar_graphml(self, grafo_model: BibGrafoModel) -> str:
        """Exporta o grafo para formato padrão GraphML com coordenadas e clusters embutidos."""
        nos = json.loads(grafo_model.nodes)
        arestas = json.loads(grafo_model.edges)

        G = nx.Graph()
        for n in nos:
            G.add_node(
                n["id"],
                label=n["label"],
                size=n["size"],
                cluster=n["cluster"],
                x=n["x"],
                y=n["y"],
            )

        for a in arestas:
            G.add_edge(a["source"], a["target"], weight=a["weight"], count=a["count"])

        out = io.BytesIO()
        nx.write_graphml(G, out)
        return out.getvalue().decode("utf-8")
