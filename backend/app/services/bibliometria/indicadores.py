#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Indicadores Bibliométricos de Nível 0 e 1 (docs 47, 48 §7, doc 49 Fase 3).

Regra de ouro (doc 48 §2):
    Nenhum número exibido pode ter sido produzido por LLM. Contagem, agregação,
    ajuste de curvas e estatística de teste são código determinístico.

Este módulo implementa:
    - Nível 0 (Metadados): Produção temporal & CAGR, Bradford (1934),
      Lotka (1926) com teste de aderência KS (Clauset et al., 2009),
      Colaboração (Subramanyam, 1983), Concentração (Gini & HHI),
      Sobreposição entre bases.
    - Nível 1 (Citação & Enriquecimento): Distribuição de citações,
      Índice h (Hirsch, 2005), Acesso aberto, Geografia de autores & instituições ROR.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.afiliacao import filtrar_afiliacoes
from app.infrastructure.persistence.models import (
    BibAuthorshipModel,
    BibReferenceModel,
    BibSnapshotModel,
    BibWorkMetaModel,
    PaperModel,
    PaperSourceModel,
)
from app.services.bibliometria.instantaneo import ler_manifesto, proveniencia as montar_proveniencia

_ESPACOS = re.compile(r"\s+")


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para chave de agrupamento bibliométrico."""
    return _ESPACOS.sub(" ", (texto or "").strip()).casefold()


def dividir_autores(campo: str) -> list[str]:
    """Divide string de autores usando o separador padronizado dos coletores ('; ')."""
    bruto = (campo or "").strip()
    if not bruto:
        return []
    if "; " in bruto:
        return [p.strip() for p in bruto.split("; ") if p.strip()]
    return [bruto]


# ── 1. Produção Temporal e CAGR ─────────────────────────────────────────


def calcular_cagr(anos_contagem: list[tuple[int, int]]) -> dict[str, Any]:
    """Calcula a evolução temporal e a Taxa Composta de Crescimento Anual (CAGR).

    CAGR = (N_final / N_inicial) ** (1 / (t_final - t_inicial)) - 1
    """
    if not anos_contagem:
        return {
            "series": [],
            "cagr_pct": None,
            "year_start": None,
            "year_end": None,
            "total_period": 0,
        }

    # Ordenar por ano crescente
    ordenados = sorted(anos_contagem, key=lambda x: x[0])
    serie: list[dict[str, Any]] = []

    for i, (ano, qtd) in enumerate(ordenados):
        yoy: Optional[float] = None
        if i > 0 and ordenados[i - 1][1] > 0:
            qtd_ant = ordenados[i - 1][1]
            yoy = round(((qtd - qtd_ant) / qtd_ant) * 100.0, 2)
        serie.append({"year": ano, "count": qtd, "growth_yoy_pct": yoy})

    ano_ini, qtd_ini = ordenados[0]
    ano_fim, qtd_fim = ordenados[-1]
    diff_anos = ano_fim - ano_ini

    cagr: Optional[float] = None
    if diff_anos > 0 and qtd_ini > 0 and qtd_fim > 0:
        cagr = round(((qtd_fim / qtd_ini) ** (1.0 / diff_anos) - 1.0) * 100.0, 2)

    return {
        "series": serie,
        "cagr_pct": cagr,
        "year_start": ano_ini,
        "year_end": ano_fim,
        "total_period": sum(q for _, q in ordenados),
    }


# ── 2. Lei de Bradford (1934) ──────────────────────────────────────────


#: Abaixo disto não há três zonas de Bradford — há uma lista de periódicos.
#:
#: Medido num acervo real: a amostra incluída tinha **um** periódico, e o
#: painel exibia "Zona 1: 1 periódico, 100%" e razão "1 : 0 : 0" como se fosse
#: um resultado. Partição em terços exige, no mínimo, três elementos para
#: partir.
PERIODICOS_MINIMOS_PARA_ZONAS = 3

#: Abaixo disto o teste de aderência de Lotka não tem poder.
#:
#: O valor crítico 1,36/√N é a aproximação assintótica do Kolmogorov-Smirnov,
#: e com N pequeno ele aceita quase qualquer coisa: medido num acervo real,
#: 17 autores — quase todos com um artigo só — produziram D_KS = 0,0 e o
#: veredicto "Aderência aceita". Clauset, Shalizi & Newman (2009) recomendam
#: N >= 50 para ajuste de lei de potência, e é o piso adotado aqui.
#:
#: Abaixo do piso o alpha continua sendo devolvido, como descrição; o que se
#: suprime é o VEREDICTO — dizer "aceita" onde o teste não decide nada é pior
#: que não testar.
AUTORES_MINIMOS_PARA_ADERENCIA = 50


def calcular_bradford(periodicos_contagem: list[tuple[str, int]]) -> dict[str, Any]:
    """Particiona os periódicos em 3 zonas de Bradford (1/3 dos artigos cada).

    Retorna periódicos por zona, multiplicador empírico k = r2/r1 ~ r3/r2.
    """
    if not periodicos_contagem:
        return {
            "total_journals": 0,
            "total_articles": 0,
            "zones": [],
            "k_multiplier": None,
            "formula_ratio": "0 : 0 : 0",
        }

    ordenados = sorted(periodicos_contagem, key=lambda x: x[1], reverse=True)
    total_artigos = sum(qtd for _, qtd in ordenados)
    total_periodicos = len(ordenados)

    if total_periodicos < PERIODICOS_MINIMOS_PARA_ZONAS:
        return {
            "total_journals": total_periodicos,
            "total_articles": total_artigos,
            "zones": [],
            "k_multiplier": None,
            "formula_ratio": "—",
            "confiavel": False,
            "motivo": (
                f"A lei de Bradford parte os periódicos em três zonas, e há "
                f"{total_periodicos} no recorte. São necessários ao menos "
                f"{PERIODICOS_MINIMOS_PARA_ZONAS}."
            ),
        }

    if total_artigos == 0:
        return {
            "total_journals": 0,
            "total_articles": 0,
            "zones": [],
            "k_multiplier": None,
            "formula_ratio": "0 : 0 : 0",
        }

    meta_zona = total_artigos / 3.0

    zonas: list[dict[str, Any]] = [
        {"zone": 1, "name": "Zona 1 (Núcleo)", "journals": [], "total_articles": 0, "n_journals": 0},
        {"zone": 2, "name": "Zona 2 (Produtividade Média)", "journals": [], "total_articles": 0, "n_journals": 0},
        {"zone": 3, "name": "Zona 3 (Periféricos)", "journals": [], "total_articles": 0, "n_journals": 0},
    ]

    acumulado = 0
    idx_zona = 0

    for journal, qtd in ordenados:
        acumulado += qtd
        zonas[idx_zona]["journals"].append({"name": journal, "count": qtd})
        zonas[idx_zona]["total_articles"] += qtd

        # Transição de zona quando atinge 1/3 e 2/3 (salvo última zona)
        if idx_zona == 0 and acumulado >= meta_zona and len(zonas[0]["journals"]) > 0:
            idx_zona = 1
        elif idx_zona == 1 and acumulado >= (2.0 * meta_zona) and len(zonas[1]["journals"]) > 0:
            idx_zona = 2

    for z in zonas:
        z["n_journals"] = len(z["journals"])
        z["pct_articles"] = round((z["total_articles"] / total_artigos) * 100.0, 2)

    r1 = zonas[0]["n_journals"]
    r2 = zonas[1]["n_journals"]
    r3 = zonas[2]["n_journals"]

    k_mult: Optional[float] = None
    if r1 > 0 and r2 > 0 and r3 > 0:
        k1 = r2 / r1
        k2 = r3 / r2
        k_mult = round((k1 + k2) / 2.0, 2)

    return {
        "total_journals": total_periodicos,
        "total_articles": total_artigos,
        "zones": zonas,
        "k_multiplier": k_mult,
        "formula_ratio": f"{r1} : {r2} : {r3}",
    }


# ── 3. Lei de Lotka (1926) e Teste de Kolmogorov-Smirnov ────────────────


def _zeta(s: float, termos: int = 1000) -> float:
    """Aproximação numérica da função zeta de Riemann sum_{k=1}^N k^(-s)."""
    return sum(1.0 / (k**s) for k in range(1, termos + 1))


def calcular_lotka_com_ks(autores_producao: list[int]) -> dict[str, Any]:
    """Ajusta a Lei de Lotka f(x) = C * x^(-alpha) e aplica teste Kolmogorov-Smirnov (Clauset et al., 2009)."""
    if not autores_producao:
        return {
            "n_authors": 0,
            "alpha": None,
            "c_constant": None,
            "d_ks": None,
            "d_critical": None,
            "is_adherent": False,
            "p_verdict": "Sem autores para análise",
            "distribution": [],
        }

    n_total = len(autores_producao)
    contagem_freq = Counter(autores_producao)  # x (artigos) -> n_x (autores)
    max_x = max(contagem_freq.keys())

    # Estimação de alpha via MLE discreto sobre o suporte observado 1..max_x
    # log L(alpha) = -alpha * sum(ln(x_i)) - N * ln(sum_{k=1}^{max_x} k^(-alpha))
    soma_log_x = sum(math.log(x) for x in autores_producao)

    melhor_alpha = 2.0
    melhor_log_l = -float("inf")

    for passo in range(100, 500):
        a_cand = passo / 100.0
        z_cand = sum(1.0 / (k**a_cand) for k in range(1, max_x + 1))
        log_l = -a_cand * soma_log_x - n_total * math.log(z_cand)
        if log_l > melhor_log_l:
            melhor_log_l = log_l
            melhor_alpha = a_cand

    alpha_ajustado = round(melhor_alpha, 2)
    z_final = sum(1.0 / (k**alpha_ajustado) for k in range(1, max_x + 1))
    c_const = round(1.0 / z_final, 4)

    # Construção da distribuição observada vs esperada e cálculo KS
    distribuicao: list[dict[str, Any]] = []
    cdf_obs = 0.0
    cdf_esp = 0.0
    d_ks = 0.0

    for x in range(1, max_x + 1):
        obs_count = contagem_freq.get(x, 0)
        p_esp = (1.0 / (x**alpha_ajustado)) / z_final
        esp_count = round(n_total * p_esp, 2)

        cdf_obs += obs_count / n_total
        cdf_esp += p_esp

        diff = abs(cdf_obs - cdf_esp)
        if diff > d_ks:
            d_ks = diff

        distribuicao.append(
            {
                "articles": x,
                "authors_observed": obs_count,
                "authors_expected": esp_count,
                "pct_observed": round((obs_count / n_total) * 100.0, 2),
                "pct_expected": round(p_esp * 100.0, 2),
            }
        )

    # Valor crítico de Kolmogorov-Smirnov a 5% de significância: 1.36 / sqrt(N)
    d_critico = round(1.36 / math.sqrt(n_total), 4)
    d_ks = round(d_ks, 4)

    if n_total < AUTORES_MINIMOS_PARA_ADERENCIA:
        # Nem "aceita" nem "rejeita": o teste não decide com esta amostra, e
        # dizer qualquer uma das duas coisas seria inventar um resultado.
        aderente = None
        veredicto = (
            f"Amostra insuficiente para testar aderência: {n_total} autores "
            f"(mínimo {AUTORES_MINIMOS_PARA_ADERENCIA}). O expoente abaixo "
            f"descreve o ajuste, mas não sustenta afirmar que o corpus segue "
            f"a lei de Lotka."
        )
    else:
        aderente = bool(d_ks <= d_critico)
        veredicto = (
            f"Aderência aceita (D_KS={d_ks} <= D_crit={d_critico})"
            if aderente
            else f"Aderência rejeitada (D_KS={d_ks} > D_crit={d_critico})"
        )

    return {
        "n_authors": n_total,
        "sample_ok": n_total >= AUTORES_MINIMOS_PARA_ADERENCIA,
        "alpha": alpha_ajustado,
        "c_constant": c_const,
        "d_ks": d_ks,
        "d_critical": d_critico,
        "is_adherent": aderente,
        "p_verdict": veredicto,
        "distribution": distribuicao[:20],  # Primeiros 20 níveis
    }


# ── 4. Colaboração de Subramanyam (1983) ────────────────────────────────


def calcular_colaboracao(autores_por_artigo: list[int]) -> dict[str, Any]:
    """Calcula o índice de colaboração de Subramanyam (C = Nm / (Nm + Ns)) e métricas de coautoria."""
    if not autores_por_artigo:
        return {
            "total_articles": 0,
            "single_author_articles": 0,
            "multi_author_articles": 0,
            "subramanyam_index": None,
            "avg_authors_per_paper": 0.0,
            "max_authors": 0,
            "distribution": [],
        }

    total = len(autores_por_artigo)
    n_single = sum(1 for a in autores_por_artigo if a == 1)
    n_multi = sum(1 for a in autores_por_artigo if a > 1)
    n_zero = sum(1 for a in autores_por_artigo if a == 0)

    val_subramanyam = round(n_multi / (n_multi + n_single), 4) if (n_multi + n_single) > 0 else None
    media_autores = round(sum(autores_por_artigo) / total, 2) if total > 0 else 0.0

    contagem_coautores = Counter(autores_por_artigo)
    distribuicao = [
        {"num_authors": k, "count": v, "pct": round((v / total) * 100.0, 2)}
        for k, v in sorted(contagem_coautores.items())
    ]

    return {
        "total_articles": total,
        "single_author_articles": n_single,
        "multi_author_articles": n_multi,
        "no_author_articles": n_zero,
        "subramanyam_index": val_subramanyam,
        "avg_authors_per_paper": media_autores,
        "max_authors": max(autores_por_artigo) if autores_por_artigo else 0,
        "distribution": distribuicao,
    }


# ── 5. Concentração (Gini & HHI) ───────────────────────────────────────


def calcular_gini(valores: list[int | float]) -> Optional[float]:
    """Calcula o Coeficiente de Gini de uma distribuição (0 = perfeita igualdade, 1 = concentração máxima)."""
    if not valores or sum(valores) == 0:
        return None
    ordenados = sorted(valores)
    n = len(ordenados)
    soma_total = sum(ordenados)
    soma_ponderada = sum((i + 1) * v for i, v in enumerate(ordenados))
    gini = (2.0 * soma_ponderada) / (n * soma_total) - (n + 1.0) / n
    return round(max(0.0, min(1.0, gini)), 4)


def calcular_hhi(contagens: list[int]) -> Optional[float]:
    """Índice Herfindahl-Hirschman (soma dos quadrados das participações), de 0 a 10.000.

    Função matemática pura: com um único elemento o índice é 10.000, porque a
    participação é 100%. Se esse valor deve ou não ser EXIBIDO é decisão de
    apresentação, e mora em `obter_indicadores_bibliometricos` — não aqui.
    """
    total = sum(contagens)
    if total == 0:
        return None
    shares = [(c / total) * 100.0 for c in contagens]
    hhi = sum(s**2 for s in shares)
    return round(hhi, 2)


# ── 6. Sobreposição entre Bases (Overlap) ────────────────────────────────


def calcular_sobreposicao_fontes(artigos_fontes: list[list[str]]) -> dict[str, Any]:
    """Analisa a exclusividade e sobreposição entre fontes de coleta registradas em PaperSourceModel."""
    if not artigos_fontes:
        return {
            "sources": [],
            "exclusive_counts": {},
            "overlap_matrix": {},
            "total_papers": 0,
        }

    total_papers = len(artigos_fontes)
    todas_fontes: set[str] = set()
    for fs in artigos_fontes:
        todas_fontes.update(fs)

    fontes_ordenadas = sorted(todas_fontes)
    exclusivos: dict[str, int] = {f: 0 for f in fontes_ordenadas}
    compartilhados_grau: Counter = Counter()

    # Contagem de exclusivos e pares de sobreposição
    matriz: dict[str, dict[str, int]] = {f1: {f2: 0 for f2 in fontes_ordenadas} for f1 in fontes_ordenadas}

    for fs in artigos_fontes:
        grau = len(fs)
        compartilhados_grau[grau] += 1
        if grau == 1:
            exclusivos[fs[0]] = exclusivos.get(fs[0], 0) + 1

        for f1 in fs:
            for f2 in fs:
                matriz[f1][f2] += 1

    return {
        "sources": fontes_ordenadas,
        "exclusive_counts": exclusivos,
        "overlap_matrix": matriz,
        "multi_source_distribution": [
            {"num_sources": k, "count": v, "pct": round((v / total_papers) * 100.0, 2)}
            for k, v in sorted(compartilhados_grau.items())
        ],
        "total_papers": total_papers,
    }


# ── 7. Nível 1 — Citações, Índice h e Acesso Aberto ─────────────────────


def calcular_citacoes_e_h(citacoes_lista: list[int]) -> dict[str, Any]:
    """Calcula estatísticas de citações recebidas e o Índice h do corpus (Hirsch, 2005)."""
    if not citacoes_lista:
        return {
            "total_citations": 0,
            "mean_citations": 0.0,
            "median_citations": 0.0,
            "h_index": 0,
            "max_citations": 0,
            "citation_bands": [],
            "papers_with_citation_data": 0,
        }

    ordenadas = sorted(citacoes_lista, reverse=True)
    total_cit = sum(ordenadas)
    n = len(ordenadas)
    media = round(total_cit / n, 2)
    mediana = ordenadas[n // 2] if n % 2 != 0 else round((ordenadas[n // 2 - 1] + ordenadas[n // 2]) / 2.0, 2)

    # Índice h de Hirsch: maior h tal que h artigos possuem pelo menos h citações
    h_idx = 0
    for i, c in enumerate(ordenadas, start=1):
        if c >= i:
            h_idx = i
        else:
            break

    # Faixas de citação
    faixas: list[dict[str, Any]] = [
        {"label": "0 citações", "min": 0, "max": 0, "count": 0},
        {"label": "1 a 9 citações", "min": 1, "max": 9, "count": 0},
        {"label": "10 a 49 citações", "min": 10, "max": 49, "count": 0},
        {"label": "50 a 99 citações", "min": 50, "max": 99, "count": 0},
        {"label": "100+ citações", "min": 100, "max": None, "count": 0},
    ]

    for c in ordenadas:
        for f in faixas:
            if f["max"] is None:
                if c >= f["min"]:
                    f["count"] += 1
                    break
            elif f["min"] <= c <= f["max"]:
                f["count"] += 1
                break

    for f in faixas:
        f["pct"] = round((f["count"] / n) * 100.0, 2)

    return {
        "total_citations": total_cit,
        "mean_citations": media,
        "median_citations": mediana,
        "h_index": h_idx,
        "max_citations": ordenadas[0] if ordenadas else 0,
        "citation_bands": faixas,
        "papers_with_citation_data": n,
    }


def calcular_acesso_aberto(oa_lista: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula a proporção e modalidades de Acesso Aberto (Gold, Green, Hybrid, Bronze, Closed)."""
    if not oa_lista:
        return {
            "total_evaluated": 0,
            "open_access_count": 0,
            "open_access_pct": 0.0,
            "by_status": [],
        }

    total = len(oa_lista)
    oa_count = sum(1 for item in oa_lista if item.get("is_oa"))

    status_counts: Counter = Counter(item.get("oa_status") or "closed" for item in oa_lista)

    distribuicao = [
        {
            "status": st,
            "count": count,
            "pct": round((count / total) * 100.0, 2),
        }
        for st, count in status_counts.most_common()
    ]

    return {
        "total_evaluated": total,
        "open_access_count": oa_count,
        "open_access_pct": round((oa_count / total) * 100.0, 2) if total > 0 else 0.0,
        "by_status": distribuicao,
    }


# ── 8. Orquestrador Principal de Indicadores Bibliométricos ─────────────


def obter_indicadores_bibliometricos(
    db: Session,
    project_id: str,
    *,
    snapshot_id: Optional[str] = None,
    decision: Optional[str] = None,
    source: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> dict[str, Any]:
    """Calcula e agrega os Indicadores Bibliométricos de Nível 0 e 1 sobre o corpus especificado."""
    proveniencia_meta: Optional[dict[str, Any]] = None

    if snapshot_id:
        snap = db.query(BibSnapshotModel).filter(
            BibSnapshotModel.id == snapshot_id,
            BibSnapshotModel.project_id == project_id,
        ).first()
        if not snap:
            raise ValueError(f"Instantâneo '{snapshot_id}' não encontrado para o projeto '{project_id}'.")

        manifesto = ler_manifesto(snap.manifest)
        paper_ids = list(manifesto.keys())
        query = db.query(PaperModel).filter(PaperModel.id.in_(paper_ids))
        proveniencia_meta = montar_proveniencia(snap)
    else:
        query = db.query(PaperModel).filter(PaperModel.project_id == project_id)
        if decision:
            query = query.filter(PaperModel.decision == decision)
        if source:
            query = query.join(PaperSourceModel, PaperSourceModel.paper_id == PaperModel.id).filter(
                PaperSourceModel.source_name == source
            )
        if year_from is not None:
            query = query.filter(PaperModel.year >= str(year_from))
        if year_to is not None:
            query = query.filter(PaperModel.year <= str(year_to))

    papers: list[PaperModel] = query.all()
    paper_ids = [p.id for p in papers]

    total_papers = len(papers)

    # 1. Produção Temporal
    anos_counter: Counter = Counter()
    for p in papers:
        if p.year and p.year.isdigit():
            anos_counter[int(p.year)] += 1
    producao_temporal = calcular_cagr([(ano, count) for ano, count in anos_counter.items()])

    # 2. Periódicos & Bradford
    periodicos_counter: Counter = Counter()
    for p in papers:
        if p.journal and p.journal.strip():
            chave = normalizar_texto(p.journal)
            periodicos_counter[p.journal.strip()] += 1
    bradford = calcular_bradford([(j, count) for j, count in periodicos_counter.items()])

    # 3. Autores & Lotka
    # Consulta se há bib_authorships para maior precisão, caso contrário divide p.authors
    authorships_db = (
        db.query(BibAuthorshipModel)
        .filter(BibAuthorshipModel.paper_id.in_(paper_ids))
        .all()
        if paper_ids
        else []
    )

    autores_por_artigo: list[int] = []
    autores_producao_counter: Counter = Counter()

    if authorships_db:
        # Agrupar por paper_id
        autores_por_paper_map = defaultdict(list)
        for a in authorships_db:
            if a.author_name:
                autores_por_paper_map[a.paper_id].append(normalizar_texto(a.author_name))
                autores_producao_counter[normalizar_texto(a.author_name)] += 1

        for pid in paper_ids:
            autores_por_artigo.append(len(autores_por_paper_map.get(pid, [])))
    else:
        for p in papers:
            lista_a = dividir_autores(p.authors)
            autores_por_artigo.append(len(lista_a))
            for a in lista_a:
                autores_producao_counter[normalizar_texto(a)] += 1

    lotka = calcular_lotka_com_ks(list(autores_producao_counter.values()))

    # 4. Colaboração (Subramanyam)
    colaboracao = calcular_colaboracao(autores_por_artigo)

    # 5. Concentração (Gini & HHI)
    gini_autores = calcular_gini(list(autores_producao_counter.values()))
    gini_periodicos = calcular_gini(list(periodicos_counter.values()))
    # Com um único periódico o HHI é 10.000 por definição — a participação é
    # 100%. Exibido ao lado de um Gini de 0, esse número sugeria concentração
    # máxima onde havia apenas ausência de comparação, então aqui ele não é
    # reportado. A conta em si continua correta em `calcular_hhi`.
    hhi_periodicos = (
        calcular_hhi(list(periodicos_counter.values()))
        if len(periodicos_counter) >= 2
        else None
    )

    # 6. Sobreposição de Fontes
    sources_db = (
        db.query(PaperSourceModel)
        .filter(PaperSourceModel.paper_id.in_(paper_ids))
        .all()
        if paper_ids
        else []
    )
    fontes_por_paper = defaultdict(list)
    for s in sources_db:
        if s.source_name:
            fontes_por_paper[s.paper_id].append(s.source_name)

    sobreposicao = calcular_sobreposicao_fontes(list(fontes_por_paper.values()))

    # 7. Nível 1 — Citações e Metadados Enriquecidos (OpenAlex)
    work_metas = (
        db.query(BibWorkMetaModel)
        .filter(BibWorkMetaModel.paper_id.in_(paper_ids))
        .all()
        if paper_ids
        else []
    )

    citacoes_lista = [wm.cited_by_count for wm in work_metas if wm.cited_by_count is not None]
    citacoes_metrics = calcular_citacoes_e_h(citacoes_lista)

    oa_lista = [
        {"is_oa": wm.is_oa, "oa_status": wm.oa_status}
        for wm in work_metas
        if wm.oa_status is not None or wm.is_oa is not None
    ]
    acesso_aberto = calcular_acesso_aberto(oa_lista)

    # Países dos Autores
    paises_counter: Counter = Counter()
    for a in authorships_db:
        if a.country:
            paises_counter[a.country.upper()] += 1

    distribuicao_paises = [
        {"country": c, "count": total}
        for c, total in paises_counter.most_common(20)
    ]

    return {
        "project_id": project_id,
        "total_papers": total_papers,
        "provenance": proveniencia_meta,
        "production_temporal": producao_temporal,
        "bradford": bradford,
        "lotka": lotka,
        "collaboration": colaboracao,
        "concentration": {
            "gini_authors": gini_autores,
            "gini_journals": gini_periodicos,
            "hhi_journals": hhi_periodicos,
        },
        "source_overlap": sobreposicao,
        "citations": citacoes_metrics,
        "open_access": acesso_aberto,
        "countries": distribuicao_paises,
    }
