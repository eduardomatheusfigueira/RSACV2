#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Seed Script — Criação do Projeto de Revisão de Escopo:
'Impactos da Segurança Pública na Operacionalização do Turismo Náutico em Fronteiras Fluviais'
Seguindo as diretrizes metodológicas do Revsist (PRISMA-ScR + BDTD/SciELO 2-Term Limit).
"""

import json
import os
import sys
from pathlib import Path

# Ajustar PYTHONPATH
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.database import SessionLocal
from app.infrastructure.persistence.models import (
    CriterionModel,
    ExtractionQuestionModel,
    ProjectModel,
    ProtocolModel,
)


def seed_project():
    db = SessionLocal()

    title = "Impactos da Segurança Pública na Operacionalização do Turismo Náutico em Fronteiras Fluviais: Protocolo de Revisão de Escopo"
    
    # Se já existir, remove para recriar limpo
    existing = db.query(ProjectModel).filter(ProjectModel.title == title).first()
    if existing:
        print(f"[*] Removendo versão anterior do projeto (ID: {existing.id})...")
        db.delete(existing)
        db.commit()

    print("[*] Criando novo projeto no Revsist...")
    project = ProjectModel(
        title=title,
        description=(
            "Revisão de escopo para mapear as problemáticas de segurança pública registradas em "
            "fronteiras fluviais e analisar como afetam o desenvolvimento, a governança e a dinâmica "
            "operacional do turismo náutico nessas regiões."
        ),
        methodology="PRISMA-ScR",
    )
    db.add(project)
    db.flush()

    pico = {
        "population": "Problemáticas de segurança pública, criminalidade transfronteiriça e atividade de turismo náutico",
        "intervention": "Modos, formas de impacto e entraves na atratividade, infraestrutura e dinâmica operacional",
        "comparison": "Estratégias de segurança pública, governança transfronteiriça e medidas mitigatórias",
        "outcome": "Mapeamento das evidências, tipologias criminais e diretrizes de ordenamento para o turismo em fronteiras fluviais",
    }

    descriptors = {
        "pt": [
            '"turismo náutico" AND "fronteira"',
            '"segurança pública" AND "fronteira fluvial"',
            '"turismo" AND "fronteira fluvial"',
            '"turismo" AND "tríplice fronteira"',
            '"segurança pública" AND "turismo náutico"',
        ],
        "en": [
            '"nautical tourism" AND "border"',
            '"public security" AND "river border"',
            '"tourism" AND "river border"',
            '"tourism" AND "cross-border"',
            '"water tourism" AND "border"',
        ],
        "es": [
            '"turismo náutico" AND "frontera"',
            '"seguridad pública" AND "frontera fluvial"',
            '"turismo" AND "frontera fluvial"',
            '"turismo" AND "triple frontera"',
            '"turismo fluvial" AND "frontera"',
        ],
    }

    filters = {
        "year_start": None,
        "year_end": None,
        "languages": ["pt", "en", "es"],
        "document_types": ["Artigo de Periódico", "Tese", "Dissertação"],
        "open_access_only": False,
    }

    manuscript = {
        "manuscript_title": title,
        "structured_summary": (
            "Este protocolo de revisão de escopo (PRISMA-ScR) tem como objetivo mapear a literatura científica "
            "sobre as problemáticas de segurança pública e criminalidade em fronteiras fluviais e seus impactos "
            "diretos e indiretos no desenvolvimento e na operacionalização do turismo náutico. A busca será "
            "conduzida nas bases BDTD, SciELO e fontes internacionais com descritores controlados em pares nos "
            "idiomas português, inglês e espanhol."
        ),
        "rationale": (
            "As regiões de fronteira fluvial e hidrovias transfronteiriças possuem alto potencial para o turismo náutico "
            "e ecoturismo, mas enfrentam desafios críticos de segurança pública (ilícitos transfronteiriços, contrabando, "
            "tráfico e deficiência de policiamento e fiscalização). Compreender como essas problemáticas impactam a gestão "
            "e a operação turística é fundamental para o planejamento regional e políticas públicas territoriais."
        ),
        "protocol_registration": (
            "Protocolo estruturado conforme as diretrizes PRISMA-ScR (2018) e recomendações metodológicas do "
            "Joanna Briggs Institute (JBI)."
        ),
        "info_sources": (
            "Bases de dados eletrônicas: BDTD (Biblioteca Digital Brasileira de Teses e Dissertações) e SciELO "
            "(Scientific Electronic Library Online), complementadas por literatura internacional e cinzenta."
        ),
        "search_strategy_notes": (
            "Estratégia de busca estruturada rigorosamente em pares de descritores (máximo 2 termos por expressão "
            "booleana), garantindo compatibilidade com os indexadores da BDTD (motor VuFind) e SciELO, sem "
            "sobrecarga de operadores booleanos."
        ),
        "selection_process": (
            "Triagem em duas fases: Fase 1 (títulos e resumos) com ancoragem estrita e regra de zero alucinação; "
            "Fase 2 (leitura integral e extração de evidências)."
        ),
        "data_charting_process": (
            "Extração estruturada de dados abrangendo localização geográfica, bacia hidrográfica, tipologia criminal, "
            "impactos na operação turística e mecanismos de governança transfronteiriça."
        ),
        "critical_appraisal": (
            "Conforme diretrizes PRISMA-ScR para revisões de escopo, a avaliação de risco de viés metodológico "
            "individual é opcional, priorizando o mapeamento abrangente da literatura."
        ),
        "synthesis_methods": (
            "Síntese narrativa, tabelas comparativas e categorização temática das tipologias de impactos e "
            "práticas de governança."
        ),
        "summary_evidence": "",
        "limitations": (
            "Limitações inerentes à disponibilidade de publicações com foco na intersecção entre segurança pública "
            "e turismo em ambientes estritamente fluviais de fronteira."
        ),
        "conclusions": "",
        "funding": "Financiamento institucional / Bolsa de Pesquisa.",
    }

    protocol = ProtocolModel(
        project_id=project.id,
        objective=(
            "Quais são as problemáticas de segurança pública registradas em fronteiras fluviais e de que "
            "maneira elas impactam o desenvolvimento e a operacionalização do turismo náutico nessas regiões?"
        ),
        pico_framework=json.dumps(pico, ensure_ascii=False),
        search_descriptors=json.dumps(descriptors, ensure_ascii=False),
        search_filters=json.dumps(filters, ensure_ascii=False),
        manuscript_sections=json.dumps(manuscript, ensure_ascii=False),
    )
    db.add(protocol)
    db.flush()

    # Critérios de Inclusão
    inclusions = [
        "Estudos que abordem a atividade turística, náutica, recreativa ou de navegação de passageiros em regiões de fronteira fluvial ou hidrovias transfronteiriças.",
        "Pesquisas que analisem aspectos de segurança pública, criminalidade transfronteiriça, fiscalização, policiamento ou governança em bacias hidrográficas de fronteira.",
        "Publicações científicas completas (artigos de periódicos, teses e dissertações) nos idiomas português, inglês ou espanhol.",
    ]
    for idx, text in enumerate(inclusions):
        db.add(CriterionModel(protocol_id=protocol.id, text=text, is_exclusion=False, order=idx))

    # Critérios de Exclusão
    exclusions = [
        "Estudos com foco exclusivo em transporte marítimo oceânico ou de alto-mar sem interface fluvial ou fronteiriça.",
        "Trabalhos sobre segurança pública puramente urbana ou rural sem qualquer conexão com hidrovias, cursos d'água de fronteira ou atividades turísticas.",
        "Documentos editoriais, resenhas de livros, resumos expandidos de eventos ou textos sem metodologia científica definida.",
    ]
    for idx, text in enumerate(exclusions):
        db.add(CriterionModel(protocol_id=protocol.id, text=text, is_exclusion=True, order=idx))

    # Questões de Extração (Triagem 2)
    questions = [
        "Qual é a localização geográfica, país e bacia hidrográfica/rio de fronteira analisado no estudo?",
        "Quais tipologias de ocorrências de segurança pública, crimes ou ilícitos transfronteiriços foram identificadas?",
        "Quais foram os impactos diretos ou indiretos na atratividade, infraestrutura e dinâmica operacional do turismo náutico?",
        "Quais estratégias de governança transfronteiriça, políticas públicas ou medidas de policiamento/mitigação foram recomendadas?",
        "Qual a metodologia de pesquisa empregada e quais fontes de dados foram utilizadas?",
    ]
    for idx, text in enumerate(questions):
        db.add(ExtractionQuestionModel(protocol_id=protocol.id, text=text, order=idx))

    db.commit()
    print(f"[✓] Projeto criado e estruturado com sucesso no Revsist!")
    print(f"    ID do Projeto: {project.id}")
    print(f"    Título: {project.title}")
    db.close()


if __name__ == "__main__":
    seed_project()
