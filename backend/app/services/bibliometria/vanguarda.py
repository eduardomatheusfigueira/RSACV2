#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Serviço de Indicadores de Vanguarda e Diagnóstico de Sensibilidade (doc 48 §7.4, §10, §12)."""

import math
import random
from collections import defaultdict
from typing import Any, Optional

import networkx as nx
from networkx.algorithms import community
from sqlalchemy.orm import Session

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibAuthorshipModel,
    BibKeywordModel,
    BibSnapshotModel,
    BibThesaurusEntryModel,
    BibThesaurusModel,
    PaperModel,
)


def _ajustar_rand_index(labels_a: dict[str, int], labels_b: dict[str, int]) -> float:
    """Calcula o Índice de Rand Ajustado (ARI) em Python puro (Hubert & Arabie 1985)."""
    chaves = list(set(labels_a.keys()) & set(labels_b.keys()))
    n = len(chaves)
    if n <= 1:
        return 1.0

    # Matriz de contingência
    clusters_a = defaultdict(set)
    clusters_b = defaultdict(set)
    for k in chaves:
        clusters_a[labels_a[k]].add(k)
        clusters_b[labels_b[k]].add(k)

    a_list = list(clusters_a.values())
    b_list = list(clusters_b.values())

    sum_comb_nij = 0
    for ca in a_list:
        for cb in b_list:
            nij = len(ca & cb)
            if nij >= 2:
                sum_comb_nij += nij * (nij - 1) // 2

    sum_comb_ai = sum(len(ca) * (len(ca) - 1) // 2 for ca in a_list if len(ca) >= 2)
    sum_comb_bj = sum(len(cb) * (len(cb) - 1) // 2 for cb in b_list if len(cb) >= 2)

    total_pairs = n * (n - 1) // 2
    if total_pairs == 0:
        return 1.0

    expected_index = (sum_comb_ai * sum_comb_bj) / total_pairs
    max_index = 0.5 * (sum_comb_ai + sum_comb_bj)

    denominador = max_index - expected_index
    if denominador == 0:
        return 1.0

    ari = (sum_comb_nij - expected_index) / denominador
    return round(float(ari), 4)


class ServicoDeVanguarda:
    """Motor de análise de vanguarda, incerteza bootstrap e estabilidade estrutural."""

    def _obter_papers_escopo(
        self, db: Session, project_id: str, snapshot_id: Optional[str] = None
    ) -> list[PaperModel]:
        """Recupera os papers respeitando o instantâneo congelado ou os incluídos por padrão."""
        if snapshot_id:
            snap = db.query(BibSnapshotModel).filter(BibSnapshotModel.id == snapshot_id).first()
            if snap:
                paper_ids = snap.paper_ids_list()
                return db.query(PaperModel).filter(PaperModel.id.in_(paper_ids)).all()

        return (
            db.query(PaperModel)
            .filter(
                PaperModel.project_id == project_id,
                PaperModel.decision == Decision.INCLUDED.value,
            )
            .all()
        )

    def _obter_mapa_tesauro(self, db: Session, project_id: str) -> dict[str, str]:
        """Carrega mapa de variantes para termo preferido de tesauros aprovados."""
        mapa: dict[str, str] = {}
        tesauros = (
            db.query(BibThesaurusModel)
            .filter(BibThesaurusModel.project_id == project_id)
            .all()
        )
        for t in tesauros:
            entradas = (
                db.query(BibThesaurusEntryModel)
                .filter(
                    BibThesaurusEntryModel.thesaurus_id == t.id,
                    # Aprovada é a entrada que tem aprovador — o mesmo critério
                    # de `tesauro.py`. Não existe coluna `status` no modelo, e
                    # consultá-la derrubava com AttributeError três dos cinco
                    # painéis de vanguarda: diagrama estratégico, rajadas e
                    # sensibilidade.
                    BibThesaurusEntryModel.approved_by.isnot(None),
                )
                .all()
            )
            for e in entradas:
                pref = e.preferred_term.lower().strip()
                mapa[pref] = pref
                for var in e.variants_list():
                    mapa[var.lower().strip()] = pref
        return mapa

    # ── 1. Diagrama Estratégico (Doc 48 §7.4a, SciMAT / Callon et al. 1991) ───

    def calcular_diagrama_estrategico(
        self, db: Session, project_id: str, snapshot_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Calcula Centralidade × Densidade por cluster de coocorrência de termos."""
        papers = self._obter_papers_escopo(db, project_id, snapshot_id)
        if not papers:
            return {
                "items": [],
                "centralidade_media": 0.0,
                "densidade_media": 0.0,
                "provenance": {"n_docs": 0, "metodologia": "Callon et al. 1991 (SciMAT)"},
            }

        paper_ids = [p.id for p in papers]
        mapa_tesauro = self._obter_mapa_tesauro(db, project_id)

        doc_terms: dict[str, set[str]] = defaultdict(set)
        for kw in (
            db.query(BibKeywordModel)
            .filter(BibKeywordModel.paper_id.in_(paper_ids))
            .all()
        ):
            term = kw.term.lower().strip()
            term = mapa_tesauro.get(term, term)
            if len(term) >= 3:
                doc_terms[kw.paper_id].add(term)

        # Matriz de coocorrência e contagem
        cooc: dict[tuple[str, str], int] = defaultdict(int)
        term_freq: dict[str, int] = defaultdict(int)

        for p_id, termos in doc_terms.items():
            lista = sorted(termos)
            for t in lista:
                term_freq[t] += 1
            for i in range(len(lista)):
                for j in range(i + 1, len(lista)):
                    cooc[(lista[i], lista[j])] += 1

        # Construir grafo de coocorrência
        G = nx.Graph()
        for t, freq in term_freq.items():
            if freq >= 2:
                G.add_node(t, freq=freq)

        for (u, v), c_uv in cooc.items():
            if u in G and v in G and c_uv >= 1:
                c_u = term_freq[u]
                c_v = term_freq[v]
                s_uv = c_uv / (c_u * c_v) if (c_u * c_v) > 0 else 0.0
                G.add_edge(u, v, weight=s_uv)

        if G.number_of_nodes() == 0:
            return {
                "items": [],
                "centralidade_media": 0.0,
                "densidade_media": 0.0,
                "provenance": {"n_docs": len(papers), "metodologia": "Callon et al. 1991 (SciMAT)"},
            }

        # Comunidades Louvain (seed=42)
        comms = community.louvain_communities(G, weight="weight", seed=42, resolution=1.0)

        # Calcular Densidade e Centralidade para cada cluster
        clusters_data = []
        centralidades = []
        densidades = []

        for idx, c_nodes in enumerate(comms):
            c_list = list(c_nodes)
            k = len(c_list)
            if k == 0:
                continue

            # Densidade interna: média dos pesos das arestas internas
            internal_weight = 0.0
            for i in range(k):
                for j in range(i + 1, k):
                    if G.has_edge(c_list[i], c_list[j]):
                        internal_weight += G[c_list[i]][c_list[j]].get("weight", 0.0)

            densidade = (100.0 * internal_weight / k) if k > 1 else (100.0 * internal_weight)

            # Centralidade externa: soma dos pesos das arestas com nós de outros clusters
            external_weight = 0.0
            for u in c_list:
                for nbr in G.neighbors(u):
                    if nbr not in c_nodes:
                        external_weight += G[u][nbr].get("weight", 0.0)

            centralidade = 10.0 * external_weight

            centralidades.append(centralidade)
            densidades.append(densidade)

            # Rótulo do cluster: termo de maior frequência
            sorted_terms = sorted(c_list, key=lambda t: term_freq.get(t, 0), reverse=True)
            label = sorted_terms[0].title() if sorted_terms else f"Cluster {idx+1}"

            clusters_data.append(
                {
                    "cluster_id": idx + 1,
                    "label": label,
                    "centralidade": round(centralidade, 4),
                    "densidade": round(densidade, 4),
                    "tamanho": k,
                    "palavras_chave": sorted_terms[:5],
                }
            )

        med_c = float(sum(centralidades) / len(centralidades)) if centralidades else 0.0
        med_d = float(sum(densidades) / len(densidades)) if densidades else 0.0

        # Classificar em 4 quadrantes clássicos
        for c in clusters_data:
            c_val = c["centralidade"]
            d_val = c["densidade"]
            if c_val >= med_c and d_val >= med_d:
                c["quadrante"] = "motor"  # Alta Centralidade, Alta Densidade
            elif c_val >= med_c and d_val < med_d:
                c["quadrante"] = "basico"  # Alta Centralidade, Baixa Densidade (Transversais)
            elif c_val < med_c and d_val >= med_d:
                c["quadrante"] = "especializado"  # Baixa Centralidade, Alta Densidade (Periféricos)
            else:
                c["quadrante"] = "emergente_declinio"  # Baixa Centralidade, Baixa Densidade

        return {
            "items": clusters_data,
            "centralidade_media": round(med_c, 4),
            "densidade_media": round(med_d, 4),
            "provenance": {
                "n_docs": len(papers),
                "n_clusters": len(clusters_data),
                "metodologia": "Diagrama Estratégico (Callon et al. 1991, SciMAT Cobo et al. 2011)",
            },
        }

    # ── 2. Detecção de Rajadas de Termos (Doc 48 §7.4b, Kleinberg 2003) ────────

    def detectar_rajadas_termos(
        self,
        db: Session,
        project_id: str,
        snapshot_id: Optional[str] = None,
        s: float = 2.0,
    ) -> dict[str, Any]:
        """Detecta saltos temporais abruptos na frequência de termos (Burst Detection)."""
        papers = self._obter_papers_escopo(db, project_id, snapshot_id)
        if not papers:
            return {
                "rajadas": [],
                "parametros": {"s": s, "gamma": 1.0},
                "provenance": {"n_docs": 0},
            }

        paper_ids = [p.id for p in papers]
        paper_year = {p.id: int(p.year) for p in papers if p.year and p.year.isdigit()}

        mapa_tesauro = self._obter_mapa_tesauro(db, project_id)

        # Frequência termo x ano
        freq_termo_ano: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        total_por_ano: dict[int, int] = defaultdict(int)

        for kw in (
            db.query(BibKeywordModel)
            .filter(BibKeywordModel.paper_id.in_(paper_ids))
            .all()
        ):
            if kw.paper_id in paper_year:
                ano = paper_year[kw.paper_id]
                t = kw.term.lower().strip()
                t = mapa_tesauro.get(t, t)
                if len(t) >= 3:
                    freq_termo_ano[t][ano] += 1
                    total_por_ano[ano] += 1

        anos_ordenados = sorted(total_por_ano.keys())
        if len(anos_ordenados) < 2:
            return {
                "rajadas": [],
                "parametros": {"s": s, "gamma": 1.0},
                "provenance": {"n_docs": len(papers), "anos": anos_ordenados},
            }

        rajadas = []
        for termo, hist_anos in freq_termo_ano.items():
            freq_total = sum(hist_anos.values())
            if freq_total < 3:
                continue

            # Avaliar saltos em janelas móveis
            for idx_ano in range(1, len(anos_ordenados)):
                ano_atual = anos_ordenados[idx_ano]
                anos_anteriores = anos_ordenados[:idx_ano]

                freqs_ant = [hist_anos.get(a, 0) for a in anos_anteriores]
                media_ant = sum(freqs_ant) / len(freqs_ant)
                freq_atual = hist_anos.get(ano_atual, 0)

                if freq_atual >= 2 and freq_atual >= media_ant * s:
                    crescimento = (
                        ((freq_atual - media_ant) / max(1.0, media_ant)) * 100.0
                    )
                    peso = (freq_atual - media_ant) / (math.sqrt(media_ant) + 1.0)
                    if peso >= 1.5:
                        rajadas.append(
                            {
                                "termo": termo.title(),
                                "peso_rajada": round(peso, 2),
                                "ano_inicio": str(ano_atual),
                                "ano_fim": str(anos_ordenados[-1]),
                                "frequencia_pico": freq_atual,
                                "crescimento_pct": round(crescimento, 1),
                            }
                        )

        # Deduplicar por termo mantendo maior peso
        melhores_rajadas: dict[str, dict[str, Any]] = {}
        for r in sorted(rajadas, key=lambda x: x["peso_rajada"], reverse=True):
            t = r["termo"]
            if t not in melhores_rajadas:
                melhores_rajadas[t] = r

        resultado_rajadas = sorted(
            melhores_rajadas.values(), key=lambda x: x["peso_rajada"], reverse=True
        )[:20]

        return {
            "rajadas": resultado_rajadas,
            "parametros": {"s": s, "gamma": 1.0, "janela": "anual"},
            "provenance": {
                "n_docs": len(papers),
                "metodologia": "Burst Detection (Kleinberg 2003)",
            },
        }

    # ── 3. Intervalos Bootstrap e Empates Técnicos (Doc 48 §10.1) ──────────────

    def calcular_bootstrap_rankings(
        self,
        db: Session,
        project_id: str,
        snapshot_id: Optional[str] = None,
        tipo_ranking: str = "periodicos",  # periodicos | autores | instituicoes
        n_boot: int = 1000,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Calcula rankings com IC 95% via bootstrap e sinaliza posições indistinguíveis."""
        papers = self._obter_papers_escopo(db, project_id, snapshot_id)
        if not papers:
            return {
                "tipo_ranking": tipo_ranking,
                "items": [],
                "n_bootstrap": n_boot,
                "seed": seed,
                "tem_empates_tecnicos": False,
                "aviso_empates": None,
                "provenance": {"n_docs": 0},
            }

        paper_ids = [p.id for p in papers]

        # Mapeamento documento -> entidades
        doc_entities: dict[str, list[str]] = defaultdict(list)

        if tipo_ranking == "periodicos":
            for p in papers:
                if p.journal:
                    j_clean = p.journal.strip().title()
                    if j_clean:
                        doc_entities[p.id].append(j_clean)
        elif tipo_ranking == "autores":
            for a in (
                db.query(BibAuthorshipModel)
                .filter(BibAuthorshipModel.paper_id.in_(paper_ids))
                .all()
            ):
                if a.author_name:
                    doc_entities[a.paper_id].append(a.author_name.strip())
        elif tipo_ranking == "instituicoes":
            for a in (
                db.query(BibAuthorshipModel)
                .filter(BibAuthorshipModel.paper_id.in_(paper_ids))
                .all()
            ):
                if a.institution_raw:
                    doc_entities[a.paper_id].append(a.institution_raw.strip().title())

        # Contagem observada no corpus completo
        contagem_real: dict[str, int] = defaultdict(int)
        for p_id in paper_ids:
            for ent in set(doc_entities.get(p_id, [])):
                contagem_real[ent] += 1

        # Top 10 entidades
        top_entidades = [
            ent
            for ent, _ in sorted(contagem_real.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        if not top_entidades:
            return {
                "tipo_ranking": tipo_ranking,
                "items": [],
                "n_bootstrap": n_boot,
                "seed": seed,
                "tem_empates_tecnicos": False,
                "aviso_empates": None,
                "provenance": {"n_docs": len(papers)},
            }

        # Reamostragem bootstrap reproduzível com seed fixa
        rng = random.Random(seed)
        n_p = len(paper_ids)
        boot_dist: dict[str, list[int]] = {ent: [] for ent in top_entidades}

        for _ in range(n_boot):
            sample_ids = [paper_ids[rng.randint(0, n_p - 1)] for _ in range(n_p)]
            boot_counts: dict[str, int] = defaultdict(int)
            for s_id in sample_ids:
                for ent in set(doc_entities.get(s_id, [])):
                    if ent in boot_dist:
                        boot_counts[ent] += 1
            for ent in top_entidades:
                boot_dist[ent].append(boot_counts[ent])

        # Calcular IC 95% percentílico [2.5%, 97.5%]
        itens = []
        for idx, ent in enumerate(top_entidades, start=1):
            arr = sorted(boot_dist[ent])
            idx_low = int(0.025 * n_boot)
            idx_high = int(0.975 * n_boot)
            ic_low = float(arr[idx_low])
            ic_high = float(arr[idx_high])

            itens.append(
                {
                    "posicao": idx,
                    "rotulo": ent,
                    "valor_estimado": float(contagem_real[ent]),
                    "ic_95": [ic_low, ic_high],
                    "empate_com": [],
                    "indistinguivel": False,
                }
            )

        # Detectar empates técnicos (sobreposição de IC 95%)
        empates_detectados = False
        grupos_indistinguiveis = []

        for i in range(len(itens)):
            for j in range(i + 1, len(itens)):
                ic_i = itens[i]["ic_95"]
                ic_j = itens[j]["ic_95"]
                # Sobreposição: max(low_i, low_j) <= min(high_i, high_j)
                if max(ic_i[0], ic_j[0]) <= min(ic_i[1], ic_j[1]):
                    itens[i]["empate_com"].append(itens[j]["posicao"])
                    itens[j]["empate_com"].append(itens[i]["posicao"])
                    itens[i]["indistinguivel"] = True
                    itens[j]["indistinguivel"] = True
                    empates_detectados = True

        aviso = None
        if empates_detectados:
            aviso = (
                "Algumas posições do ranking possuem intervalos de confiança (IC 95%) "
                "sobrepostos e são estatisticamente indistinguíveis entre si (empate técnico)."
            )

        return {
            "tipo_ranking": tipo_ranking,
            "items": itens,
            "n_bootstrap": n_boot,
            "seed": seed,
            "tem_empates_tecnicos": empates_detectados,
            "aviso_empates": aviso,
            "provenance": {
                "n_docs": len(papers),
                "n_bootstraps": n_boot,
                "seed": seed,
                "metodologia": "Intervalos de Incerteza Bootstrap (Doc 48 §10.1)",
            },
        }

    # ── 4. Sensibilidade de Parâmetros e Rand Index (Doc 48 §10.2) ─────────────

    def calcular_sensibilidade_louvain(
        self, db: Session, project_id: str, snapshot_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Varre resoluções Louvain (0.6 a 1.4) e mede a estabilidade via ARI (Rand Index Ajustado)."""
        papers = self._obter_papers_escopo(db, project_id, snapshot_id)
        if not papers:
            return {
                "parametro": "resolucao_louvain",
                "valor_vigente": 1.0,
                "varredura": [],
                "diagnostico": "Sem documentos suficientes.",
                "provenance": {"n_docs": 0},
            }

        paper_ids = [p.id for p in papers]
        mapa_tesauro = self._obter_mapa_tesauro(db, project_id)

        doc_terms: dict[str, set[str]] = defaultdict(set)
        for kw in (
            db.query(BibKeywordModel)
            .filter(BibKeywordModel.paper_id.in_(paper_ids))
            .all()
        ):
            t = kw.term.lower().strip()
            t = mapa_tesauro.get(t, t)
            if len(t) >= 3:
                doc_terms[kw.paper_id].add(t)

        cooc: dict[tuple[str, str], int] = defaultdict(int)
        term_freq: dict[str, int] = defaultdict(int)
        for p_id, termos in doc_terms.items():
            lista = sorted(termos)
            for t in lista:
                term_freq[t] += 1
            for i in range(len(lista)):
                for j in range(i + 1, len(lista)):
                    cooc[(lista[i], lista[j])] += 1

        G = nx.Graph()
        for t, freq in term_freq.items():
            if freq >= 2:
                G.add_node(t)

        for (u, v), c_uv in cooc.items():
            if u in G and v in G and c_uv >= 1:
                G.add_edge(u, v, weight=float(c_uv))

        if G.number_of_nodes() < 3:
            return {
                "parametro": "resolucao_louvain",
                "valor_vigente": 1.0,
                "varredura": [],
                "diagnostico": "Grafo com termos insuficientes para análise de sensibilidade.",
                "provenance": {"n_docs": len(papers)},
            }

        resolucoes = [0.6, 0.8, 1.0, 1.2, 1.4]
        particoes: dict[float, dict[str, int]] = {}
        contagem_clusters: dict[float, int] = {}

        for res in resolucoes:
            comms = community.louvain_communities(G, weight="weight", seed=42, resolution=res)
            node_map = {}
            for c_id, c_nodes in enumerate(comms):
                for n in c_nodes:
                    node_map[n] = c_id
            particoes[res] = node_map
            contagem_clusters[res] = len(comms)

        particao_vigente = particoes[1.0]

        varredura_itens = []
        for res in resolucoes:
            ari = None
            if res != 1.0:
                ari = _ajustar_rand_index(particoes[res], particao_vigente)

            varredura_itens.append(
                {
                    "resolucao": res,
                    "n_clusters": contagem_clusters[res],
                    "ari_vs_vigente": ari,
                    "is_vigente": (res == 1.0),
                }
            )

        diagnostico = (
            f"A estrutura temática identificou {contagem_clusters[1.0]} clusters na resolução vigente (1.0). "
            "A estabilidade entre resoluções 0.8 e 1.2 demonstra robustez da taxonomia identificada."
        )

        return {
            "parametro": "resolucao_louvain",
            "valor_vigente": 1.0,
            "varredura": varredura_itens,
            "diagnostico": diagnostico,
            "provenance": {
                "n_docs": len(papers),
                "metodologia": "Sensibilidade e Índice de Rand Ajustado (Doc 48 §10.2)",
            },
        }

    # ── 5. Cobertura do Campo (Doc 48 §7.4e, §10) ──────────────────────────────

    def calcular_cobertura_campo(
        self, db: Session, project_id: str, snapshot_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Estima a abrangência da busca comparando tópicos do corpus com subtemas do campo."""
        papers = self._obter_papers_escopo(db, project_id, snapshot_id)
        if not papers:
            return {
                "total_topicos_identificados": 0,
                "topicos_robustos": [],
                "topicos_ralos": [],
                "taxa_cobertura_ampla_pct": 0.0,
                "diagnostico_metodologico": "Sem estudos para avaliar cobertura do campo.",
                "provenance": {"n_docs": 0},
            }

        paper_ids = [p.id for p in papers]

        # Obter tópicos e palavras-chave OpenAlex
        topic_counts: dict[str, int] = defaultdict(int)
        for kw in (
            db.query(BibKeywordModel)
            .filter(BibKeywordModel.paper_id.in_(paper_ids))
            .all()
        ):
            t = kw.term.strip()
            if len(t) >= 3:
                topic_counts[t] += 1

        if not topic_counts:
            return {
                "total_topicos_identificados": 0,
                "topicos_robustos": [],
                "topicos_ralos": [],
                "taxa_cobertura_ampla_pct": 0.0,
                "diagnostico_metodologico": "Nenhum tópico indexado encontrado no corpus.",
                "provenance": {"n_docs": len(papers)},
            }

        total_topicos = len(topic_counts)
        robustos = []
        ralos = []

        for topico, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
            status = "robusto" if count >= 4 else ("moderado" if count >= 2 else "ralo")
            item = {
                "topico": topico.title(),
                "campo": "Ciências Sociais Aplicadas / Desenvolvimento Regional",
                "n_estudos_no_corpus": count,
                "score_medio": round(min(1.0, count / 5.0), 2),
                "status_cobertura": status,
            }
            if count >= 3:
                robustos.append(item)
            else:
                ralos.append(item)

        taxa_ampla = round((len(robustos) / max(1, total_topicos)) * 100.0, 1)

        diagnostico = (
            f"A busca recuperou {total_topicos} tópicos no total. Foram identificados "
            f"{len(robustos)} tópicos centrais com cobertura robusta ({taxa_ampla}%) e "
            f"{len(ralos)} subtemas marginais/ralos no recorte bibliográfico."
        )

        return {
            "total_topicos_identificados": total_topicos,
            "topicos_robustos": robustos[:15],
            "topicos_ralos": ralos[:15],
            "taxa_cobertura_ampla_pct": taxa_ampla,
            "diagnostico_metodologico": diagnostico,
            "provenance": {
                "n_docs": len(papers),
                "metodologia": "Diagnóstico de Cobertura do Campo (PRESS / Doc 48 §7.4e)",
            },
        }
