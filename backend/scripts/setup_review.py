#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Script de Configuração e Estruturação da Revisão Sistemática.
Configura o projeto, protocolo, critérios, descritores em pares (regras VuFind/BDTD)
e matriz de extração completa para Ciências Sociais Aplicadas e Desenvolvimento Regional.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.infrastructure.persistence.models import (
    ProjectModel,
    ProtocolModel,
    CriterionModel,
    ExtractionQuestionModel,
)


def setup_systematic_review():
    db = SessionLocal()
    try:
        project = db.query(ProjectModel).first()
        if not project:
            project = ProjectModel(
                title="Revisão Sistemática e Bibliometria em Políticas Públicas e Desenvolvimento Regional",
                description="Mapeamento e auditoria metodológica da produção científica brasileira (SciELO, BDTD, OpenAlex) em Políticas Públicas e Desenvolvimento Regional.",
                methodology="PRISMA-ScR",
            )
            db.add(project)
            db.flush()
        else:
            project.title = "Revisão Sistemática e Bibliometria em Políticas Públicas e Desenvolvimento Regional"
            project.description = "Mapeamento e auditoria metodológica da produção científica brasileira (SciELO, BDTD, OpenAlex) em Políticas Públicas e Desenvolvimento Regional."
            project.methodology = "PRISMA-ScR"

        protocol = project.protocol
        if not protocol:
            protocol = ProtocolModel(project_id=project.id)
            db.add(protocol)
            db.flush()

        protocol.objective = (
            "Mapear, caracterizar e auditar a conformidade metodológica dos estudos que declaram o uso de revisão sistemática "
            "e bibliometria no campo das Ciências Sociais Aplicadas no Brasil, com foco em Políticas Públicas e Desenvolvimento Regional. "
            "A investigação analisa a adesão a protocolos formais (PRISMA, Methodi Ordinatio, ProKnow-C), a reprodutibilidade das estratégias "
            "de busca, o ferramental computacional empregado e a incidência de falsos positivos metodológicos."
        )

        protocol.pico_framework = json.dumps(
            {
                "population": "Pesquisadores, programas de pós-graduação (PPGs) e autores de artigos, dissertações e teses em Ciências Sociais Aplicadas.",
                "intervention": "Métodos, protocolos formais (PRISMA, Methodi Ordinatio, ProKnow-C), estratégias de busca e softwares de síntese/bibliometria (VOSviewer, Bibliometrix, CiteSpace, Gephi, Rayyan).",
                "comparison": "Revisões sistemáticas reais vs. bibliometrias reais vs. abordagens híbridas vs. falsos positivos metodológicos (ensaios teóricos autodeclarados sem método condizente).",
                "outcome": "Taxa de conformidade metodológica (% falsos positivos), reprodutibilidade de strings de busca, cobertura de bases de dados e ranking institucional/editorial.",
            },
            ensure_ascii=False,
        )

        # Regra de Ouro: Máximo 5 pares por idioma, máximo 2 termos por expressão combinados com AND
        descriptors = {
            "pt": [
                '"revisão sistemática" AND "desenvolvimento regional"',
                '"revisão sistemática" AND "políticas públicas"',
                '"bibliometria" AND "desenvolvimento regional"',
                '"bibliometria" AND "políticas públicas"',
                '"cienciometria" AND "planejamento regional"',
            ],
            "en": [
                '"systematic review" AND "regional development"',
                '"systematic review" AND "public policy"',
                '"bibliometrics" AND "regional development"',
                '"bibliometrics" AND "public policies"',
                '"scientometrics" AND "regional planning"',
            ],
            "es": [
                '"revisión sistemática" AND "desarrollo regional"',
                '"revisión sistemática" AND "políticas públicas"',
                '"bibliometría" AND "desarrollo regional"',
                '"bibliometría" AND "políticas públicas"',
                '"cienciometría" AND "planificación regional"',
            ],
        }
        protocol.search_descriptors = json.dumps(descriptors, ensure_ascii=False)

        # Seções do Manuscrito / Protocolo PRISMA-ScR (22 Itens)
        manuscript = {
            "manuscript_title": "Mapeamento e Rigor Metodológico de Revisões Sistemáticas e Bibliometrias em Políticas Públicas e Desenvolvimento Regional no Brasil: Uma Scoping Review",
            "structured_summary": "Contexto: Crescimento expressivo de revisões de literatura em Ciências Sociais Aplicadas. Objetivo: Mapear a conformidade metodológica e o ferramental de RS e bibliometrias. Métodos: Scoping review orientada por PRISMA-ScR consultando SciELO, BDTD e OpenAlex. Síntese: Categorização da tipologia real, protocolos e softwares.",
            "rationale": "A proliferação de estudos autodeclarados como revisões sistemáticas ou bibliométricas sem protocolo formal ou reprodutibilidade exige uma auditoria crítica em Políticas Públicas e Desenvolvimento Regional.",
            "protocol_registration": "Protocolo registrado no Open Science Framework (OSF) e repositório institucional do projeto RSAC.",
            "info_sources": "Bases eletrônicas indexadas: SciELO (artigos de periódicos), BDTD/IBICT (teses e dissertações defendidas) e OpenAlex (artigos revisados por pares).",
            "search_strategy_notes": "Descritores combinados rigorosamente em pares booleanos (máximo 2 termos por expressão com operador AND) atendendo às limitações do VuFind/BDTD.",
            "selection_process": "Triagem independente de títulos e resumos (Triagem 1) seguida por extração de texto integral (Triagem 2) com resolução de discrepâncias por consenso.",
            "data_charting_process": "Formulário padronizado com 11 variáveis cobrindo identificação, veículo/instituição, área CAPES, tipologia real, protocolo, reprodutibilidade, bases e softwares.",
            "critical_appraisal": "Avaliação de conformidade metodológica baseada no atendimento a critérios mínimos de sistematização e reprodutibilidade.",
            "synthesis_methods": "Síntese quantitativa descritiva, análises de frequência cruzada (Protocolo x Área; Software x Tipo) e mapeamento bibliométrico.",
            "summary_evidence": "Mapeamento do panorama da produção científica e identificação dos padrões de adoção de metodologias sistemáticas no país.",
            "limitations": "Foco em bases com cobertura da literatura brasileira/latino-americana e possíveis restrições no acesso a textos completos não depositados.",
            "conclusions": "Diretrizes e recomendações para o fortalecimento do rigor metodológico em pesquisas de pós-graduação e periódicos de Desenvolvimento Regional.",
            "funding": "Pesquisa conduzida com apoio institucional de pesquisa e pós-graduação.",
        }
        protocol.manuscript_sections = json.dumps(manuscript, ensure_ascii=False)

        # Critérios de Inclusão e Exclusão
        db.query(CriterionModel).filter(CriterionModel.protocol_id == protocol.id).delete()
        criteria_list = [
            ("Estudos que declarem explicitamente ou empreguem métodos de revisão sistemática da literatura, revisão de escopo, bibliometria ou cienciometria.", False),
            ("Publicações aplicadas ao campo de Políticas Públicas, Desenvolvimento Regional, Planejamento Urbano e Regional, Governança Territorial e temas afins de Ciências Sociais Aplicadas.", False),
            ("Artigos científicos originais e de revisão publicados em periódicos revisados por pares (SciELO / OpenAlex) e Dissertações de Mestrado ou Teses de Doutorado defendidas (BDTD).", False),
            ("Publicações nos idiomas português, inglês ou espanhol.", False),
            ("Estudos empíricos tradicionais ou ensaios teóricos que não utilizam revisão sistemática ou bibliometria como método central da pesquisa.", True),
            ("Estudos focados exclusivamente em ciências biomédicas, clínicas ou da saúde sem interface ou reflexão para as Ciências Sociais Aplicadas.", True),
            ("Editoriais, cartas, resenhas, erratas, notas de conferência, resumos de anais e trabalhos de conclusão de graduação (TCC) ou relatórios de qualificação.", True),
            ("Publicações cujo texto integral seja inacessível ou com metadados insuficientes para a extração dos dados.", True),
        ]
        for idx, (text, is_exc) in enumerate(criteria_list):
            db.add(CriterionModel(protocol_id=protocol.id, text=text, is_exclusion=is_exc, order=idx))

        # Perguntas de Extração de Dados (Matriz de Codificação com 11 variáveis)
        db.query(ExtractionQuestionModel).filter(ExtractionQuestionModel.protocol_id == protocol.id).delete()
        questions_list = [
            "[Veículo / Instituição] Nome do Periódico / Revista (para artigos) OU Instituição de Ensino Superior (IES) que conferiu o título (para Teses/Dissertações)",
            "[Veículo / Instituição] ISSN / e-ISSN do periódico OU Programa de Pós-Graduação (PPG) / Departamento da IES",
            "[Veículo / Instituição] Região Geográfica da IES / Periódico (Sul, Sudeste, Nordeste, Norte, Centro-Oeste, Internacional)",
            "[Área do Conhecimento] Área CAPES / CNPq (ex: Planejamento Urbano e Regional / Demografia, Ciência Política, Administração Pública, Economia, Interdisciplinar)",
            "[Tipologia Real] Classificação Metodológica Real: [1] Revisão Sistemática Real, [2] Bibliometria Real, [3] Híbrida (RS + Bibliometria), [4] Falso Positivo (Ensaio/Narrativa autodeclarada sem método)",
            "[Protocolo Declarado] Protocolo ou Diretriz Metodológica adotada (PRISMA, Cochrane, ProKnow-C, Methodi Ordinatio, Campbell, Outro, Nenhum)",
            "[Reprodutibilidade] String de Busca Reprodutível: Fornece sintaxe exata, operadores booleanos e campos de busca? (Sim / Não / Parcial)",
            "[Reprodutibilidade] Diagrama de Fluxo: Apresenta fluxograma de seleção/inclusão (ex: PRISMA flow diagram)? (Sim / Não)",
            "[Bases Consultadas] Bases de dados consultadas pelo estudo (ex: Scopus, Web of Science, SciELO, Google Scholar, BDTD, SPELL, PubMed, Outras)",
            "[Total de Bases] Quantidade numérica total de bases bibliográficas consultadas",
            "[Instrumental / Softwares] Softwares utilizados (VOSviewer, Bibliometrix R package, CiteSpace, Gephi, Rayyan, NVivo, IRAMUTEQ, Excel/Planilhas, Python/R, Nenhum)",
        ]
        for idx, q_text in enumerate(questions_list):
            db.add(ExtractionQuestionModel(protocol_id=protocol.id, text=q_text, order=idx))

        db.commit()
        print("Sucesso: Projeto, Protocolo e Matriz de Extração configurados com perfeição no banco de dados!")
    finally:
        db.close()


if __name__ == "__main__":
    setup_systematic_review()
