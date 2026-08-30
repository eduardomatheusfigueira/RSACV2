#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Serviço de Estratégias de Busca Canônicas, Adaptadores por Base e Revisão PRESS (Doc 45 §10)."""

import json
import re
from itertools import product
from typing import Any, Dict, List, Tuple

from app.schemas.protocol import SearchStrategyBlock


def _quote_term(term: str) -> str:
    """Coloca aspas se o termo contiver espaços e não estiver com aspas."""
    t = term.strip()
    if not t:
        return ""
    if " " in t and not (t.startswith('"') and t.endswith('"')):
        return f'"{t}"'
    return t


def render_canonical_query(blocks: List[Dict[str, Any]], combination: str = "") -> str:
    """
    Renderiza a estratégia de busca canônica combinando blocos conceituais.
    """
    if not blocks:
        return ""

    block_expressions: Dict[str, str] = {}
    for idx, b in enumerate(blocks):
        key = b.get("key") or chr(ord("A") + idx)
        terms = b.get("terms", [])
        quoted_terms = [_quote_term(t) for t in terms if t.strip()]
        if quoted_terms:
            block_expressions[key] = f"({' OR '.join(quoted_terms)})"

    if not block_expressions:
        return ""

    if combination and combination.strip():
        # Substitui chaves na expressão de combinação (ex: "A AND B AND C")
        expr = combination.strip()
        for k, sub_expr in block_expressions.items():
            expr = re.sub(rf"\b{k}\b", sub_expr, expr)
        return expr

    # Padrão: AND entre todos os blocos disponíveis
    return " AND ".join(block_expressions.values())


def render_scopus_query(blocks: List[Dict[str, Any]], combination: str = "", limits: Dict[str, Any] = None) -> Tuple[str, str]:
    """
    Renderiza a estratégia adaptada para a sintaxe da API Scopus (TITLE-ABS-KEY).
    """
    canonical = render_canonical_query(blocks, combination)
    if not canonical:
        return "", "Nenhum bloco de termos configurado."

    query = f"TITLE-ABS-KEY({canonical})"
    note = "Estratégia encapsulada em campos TITLE-ABS-KEY para busca nos títulos, resumos e palavras-chave indexadas no Scopus."

    if limits:
        if limits.get("year_start"):
            query += f" AND PUBYEAR > {int(limits['year_start']) - 1}"
        if limits.get("year_end"):
            query += f" AND PUBYEAR < {int(limits['year_end']) + 1}"
        if limits.get("languages") and isinstance(limits["languages"], list):
            langs = [l.upper() for l in limits["languages"] if l]
            if langs:
                lang_clause = " OR ".join([f'LANGUAGE({l})' for l in langs])
                query += f" AND ({lang_clause})"

    return query, note


def render_pubmed_query(blocks: List[Dict[str, Any]], combination: str = "", limits: Dict[str, Any] = None) -> Tuple[str, str]:
    """
    Renderiza a estratégia adaptada para o PubMed / NCBI ([tiab]).
    """
    if not blocks:
        return "", "Nenhum bloco de termos configurado."

    block_expressions: Dict[str, str] = {}
    for idx, b in enumerate(blocks):
        key = b.get("key") or chr(ord("A") + idx)
        terms = b.get("terms", [])
        quoted_terms = [f"{_quote_term(t)}[tiab]" for t in terms if t.strip()]
        if quoted_terms:
            block_expressions[key] = f"({' OR '.join(quoted_terms)})"

    if not block_expressions:
        return "", "Nenhum termo válido para PubMed."

    if combination and combination.strip():
        expr = combination.strip()
        for k, sub_expr in block_expressions.items():
            expr = re.sub(rf"\b{k}\b", sub_expr, expr)
        query = expr
    else:
        query = " AND ".join(block_expressions.values())

    note = "Termos mapeados com qualificador de campo [tiab] (Title/Abstract) para precisão de recuperação no PubMed."
    return query, note


def render_openalex_query(blocks: List[Dict[str, Any]], combination: str = "", limits: Dict[str, Any] = None) -> Tuple[str, str]:
    """
    Renderiza a consulta textual para o OpenAlex Search Engine.
    """
    canonical = render_canonical_query(blocks, combination)
    note = "Estratégia booleana direta aplicada sobre os campos de título, resumo e conceitos no grafo OpenAlex."
    return canonical, note


def render_scielo_query(blocks: List[Dict[str, Any]], combination: str = "", limits: Dict[str, Any] = None) -> Tuple[str, str]:
    """
    Renderiza a consulta para o portal SciELO.
    """
    canonical = render_canonical_query(blocks, combination)
    note = "Consulta booleana estruturada enviada ao mecanismo de busca regional do SciELO."
    return canonical, note


def render_bdtd_decomposition(blocks: List[Dict[str, Any]], max_pairs: int = 5) -> Tuple[List[str], str]:
    """
    Decompõe a estratégia canônica em N pares ('termo_a' AND 'termo_b') para a BDTD (Doc 45 §10.2).
    """
    if len(blocks) < 2:
        # Se houver apenas 1 bloco, usa termos individuais
        terms = blocks[0].get("terms", []) if blocks else []
        pairs = [f'"{t.strip()}"' for t in terms[:max_pairs] if t.strip()]
        note = f"Execução na BDTD com {len(pairs)} consultas unitárias por limitação do motor VuFind."
        return pairs, note

    # Pega os 2 primeiros blocos mais importantes (População x Conceito)
    terms_a = [t.strip() for t in blocks[0].get("terms", []) if t.strip()]
    terms_b = [t.strip() for t in blocks[1].get("terms", []) if t.strip()]

    if not terms_a or not terms_b:
        return [], "Blocos incompletos para produto cartesiano da BDTD."

    pairs_list = []
    for a, b in product(terms_a, terms_b):
        pair_str = f'{_quote_term(a)} AND {_quote_term(b)}'
        pairs_list.append(pair_str)
        if len(pairs_list) >= max_pairs:
            break

    note = (
        f"Estratégia canônica decomposta em {len(pairs_list)} pares binários de busca ('termo_1' AND 'termo_2') "
        "com união e deduplicação local de resultados, respeitando as restrições de sintaxe do motor VuFind da BDTD."
    )
    return pairs_list, note


def run_press_review(blocks: List[Dict[str, Any]], combination: str = "") -> Dict[str, Any]:
    """
    Executa a revisão heurística baseada nos 6 domínios do PRESS 2016 (Doc 45 §10.3).
    """
    results = {
        "score_percentage": 100,
        "domains": [],
        "suggestions": [],
    }

    all_terms = []
    for b in blocks:
        all_terms.extend(b.get("terms", []))

    # Domínio 1: Tradução da pergunta / Componentes
    d1_passed = len(blocks) >= 2
    d1_msg = "Ao menos 2 blocos de conceitos definidos." if d1_passed else "Recomenda-se definir ao menos 2 blocos (ex: População e Conceito)."
    results["domains"].append({
        "domain": "1. Tradução da Pergunta de Pesquisa",
        "passed": d1_passed,
        "message": d1_msg,
    })

    # Domínio 2: Operadores Booleanos
    d2_passed = True
    d2_issues = []
    for b in blocks:
        for t in b.get("terms", []):
            if " AND " in t.upper() and not (t.startswith('"') and t.endswith('"')):
                d2_passed = False
                d2_issues.append(f"Termo '{t}' contém 'AND' dentro de um bloco OR sem aspas.")
    results["domains"].append({
        "domain": "2. Operadores Booleanos e Proximidade",
        "passed": d2_passed,
        "message": "Operadores OR e AND estruturados corretamente." if d2_passed else "; ".join(d2_issues),
    })

    # Domínio 3: Termos de Texto Livre e Sinônimos
    has_synonyms = any(len(b.get("terms", [])) >= 2 for b in blocks)
    results["domains"].append({
        "domain": "3. Termos de Texto Livre e Variações",
        "passed": has_synonyms,
        "message": "Blocos incluem termos alternativos e sinônimos." if has_synonyms else "Adicione sinônimos e termos correlatos para aumentar a sensibilidade da busca.",
    })

    # Domínio 4: Ortografia, Truncamento e Aspas
    unbalanced_quotes = any(t.count('"') % 2 != 0 for t in all_terms)
    d4_passed = not unbalanced_quotes
    results["domains"].append({
        "domain": "4. Sintaxe, Truncamento e Aspas",
        "passed": d4_passed,
        "message": "Sintaxe de aspas e termos balanceada." if d4_passed else "Detectadas aspas desbalanceadas em alguns termos.",
    })

    # Domínio 5: Limites e Filtros
    results["domains"].append({
        "domain": "5. Limites e Filtros Metodológicos",
        "passed": True,
        "message": "Filtros de limite de busca aplicáveis por adaptador de base.",
    })

    # Domínio 6: Ajuste Geral e Abrangência
    d6_passed = len(all_terms) >= 3
    results["domains"].append({
        "domain": "6. Ajuste Geral da Estratégia",
        "passed": d6_passed,
        "message": f"Estratégia consolidada com {len(all_terms)} termos." if d6_passed else "Estratégia muito restrita (menos de 3 termos totais).",
    })

    passed_count = sum(1 for d in results["domains"] if d["passed"])
    results["score_percentage"] = int((passed_count / len(results["domains"])) * 100)

    return results
