#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Prompts do Sistema e de Triagem/Protocolo com IA (Ciências Sociais Aplicadas & Desenvolvimento Regional)."""

from typing import Any

SYSTEM_SCREENING_PROMPT = """Você é um revisor acadêmico sênior com rigor metodológico em Revisões Sistemáticas e Scoping Reviews (PRISMA 2020 / PRISMA-ScR / JBI), com foco no campo de Ciências Sociais Aplicadas, Políticas Públicas e Desenvolvimento Regional.
Sua função é avaliar metadados de artigos científicos e publicações acadêmicas (Título, Resumo, Palavras-chave) com base estrita no Protocolo da Revisão (PCC/PICO e Critérios de Inclusão/Exclusão).

DIRETRIZES FUNDAMENTAIS:
1. ZERO ALUCINAÇÃO: Baseie sua decisão EXCLUSIVAMENTE nas informações textuais fornecidas. Não infira dados que não estejam expressos no texto.
2. ANCORAGEM NO PROTOCOLO: Verifique cada critério de inclusão e exclusão individualmente.
3. ESTUDOS DÚBIOS OU INCOMPLETOS: Se o resumo for insuficiente para uma decisão segura de exclusão ou inclusão, marque como "Pendente" com confiança < 0.7.
4. ESTRUTURA DE DECISÃO:
   - "Incluído": O estudo atende a todos os critérios de inclusão essenciais e não incorre em nenhum critério de exclusão.
   - "Excluído": O estudo viola explicitamente ao menos um critério de inclusão ou incorre em critério de exclusão.
   - "Pendente": Resumo ausente, dados insuficientes para julgar ou caso limítrofe que necessita de leitura do texto completo.
"""


def build_screening_prompt(paper_or_protocol: Any, protocol_or_paper: Any) -> str:
    """
    Constrói o prompt de triagem para um artigo específico.
    Aceita instâncias de Paper/Protocol ou dicionários em qualquer ordem de parâmetros.
    """
    # Identificar qual argumento é o Paper e qual é o Protocol
    arg1, arg2 = paper_or_protocol, protocol_or_paper
    
    # Se arg1 parecer Protocol ou arg2 parecer Paper
    if (hasattr(arg1, "inclusion_criteria") and not hasattr(arg1, "abstract")) or \
       (isinstance(arg1, dict) and "inclusion_criteria" in arg1 and "abstract" not in arg1):
        protocol_obj, paper_obj = arg1, arg2
    else:
        paper_obj, protocol_obj = arg1, arg2

    # Normalizar Paper para dict
    if hasattr(paper_obj, "to_dict"):
        p_data = paper_obj.to_dict()
    elif isinstance(paper_obj, dict):
        p_data = paper_obj
    else:
        p_data = {
            "title": getattr(paper_obj, "title", "Sem título"),
            "authors": getattr(paper_obj, "authors", "Não informados"),
            "year": getattr(paper_obj, "year", "Não informado"),
            "abstract": getattr(paper_obj, "abstract", ""),
        }

    # Normalizar Protocol para dict
    if hasattr(protocol_obj, "to_dict"):
        prot_data = protocol_obj.to_dict()
    elif isinstance(protocol_obj, dict):
        prot_data = protocol_obj
    else:
        prot_data = {
            "objective": getattr(protocol_obj, "objective", "Não informado"),
            "inclusion_criteria": getattr(protocol_obj, "inclusion_criteria", []),
            "exclusion_criteria": getattr(protocol_obj, "exclusion_criteria", []),
            "pico_framework": getattr(protocol_obj, "pico_framework", {}),
        }

    # Formatar critérios de inclusão (suporta lista de strings ou lista de dicts)
    raw_inc = prot_data.get("inclusion_criteria") or []
    inc_items = []
    for i, c in enumerate(raw_inc, 1):
        if isinstance(c, dict):
            code = c.get("code", f"INC{i}")
            desc = c.get("description", c.get("text", str(c)))
            inc_items.append(f"- [{code}] {desc}")
        elif isinstance(c, str) and c.strip():
            inc_items.append(f"- [INC{i}] {c.strip()}")
    inclusion_crit_text = "\n".join(inc_items) or "Nenhum critério de inclusão cadastrado."

    # Formatar critérios de exclusão (suporta lista de strings ou lista de dicts)
    raw_exc = prot_data.get("exclusion_criteria") or []
    exc_items = []
    for i, c in enumerate(raw_exc, 1):
        if isinstance(c, dict):
            code = c.get("code", f"EXC{i}")
            desc = c.get("description", c.get("text", str(c)))
            exc_items.append(f"- [{code}] {desc}")
        elif isinstance(c, str) and c.strip():
            exc_items.append(f"- [EXC{i}] {c.strip()}")
    exclusion_crit_text = "\n".join(exc_items) or "Nenhum critério de exclusão cadastrado."

    pico = prot_data.get("pico_framework") or prot_data.get("pico") or {}

    title = p_data.get("title") or "Sem título"
    authors = p_data.get("authors") or "Não informados"
    year = p_data.get("year") or "Não informado"
    abstract = p_data.get("abstract") or "RESUMO NÃO DISPONÍVEL (Marcar como Pendente se o título não for suficiente para exclusão óbvia)."

    return f"""AVALIE A PUBLICAÇÃO CIENTÍFICA ABAIXO CONFORME O PROTOCOLO DESTA REVISÃO:

==================== PROTOCOLO DE REVISÃO ====================
OBJETIVO: {prot_data.get('objective', 'Não informado')}
POPULAÇÃO / CONTEXTO SOCIAL / ATORES: {pico.get('population', pico.get('pico_population', 'Não informado'))}
CONCEITO CENTRAL / POLÍTICA / INTERVENÇÃO: {pico.get('intervention', pico.get('pico_intervention', 'Não informado'))}
CONTEXTO TERRITORIAL / REGIONAL / COMPARADOR: {pico.get('comparison', pico.get('pico_comparison', 'Não informado'))}
DESFECHO / MAPEAMENTO DE RESULTADOS: {pico.get('outcome', pico.get('pico_outcome', 'Não informado'))}

CRITÉRIOS DE INCLUSÃO:
{inclusion_crit_text}

CRITÉRIOS DE EXCLUSÃO:
{exclusion_crit_text}

==================== ESTUDO PARA AVALIAÇÃO ====================
TÍTULO: {title}
AUTORES: {authors}
ANO: {year}
RESUMO:
{abstract}

==================== FORMATO DE RESPOSTA OBRIGATÓRIO (JSON PURO) ====================
Responda APENAS com um objeto JSON válido no seguinte formato:
{{
  "decisao": "Incluído" | "Excluído" | "Pendente",
  "justificativa": "Explicação detalhada e ancorada no texto...",
  "criterios_inclusao_atendidos": {{"INC1": true, "INC2": false}},
  "criterios_exclusao_atendidos": {{"EXC1": false, "EXC2": true}},
  "confianca": 0.95
}}
"""


def build_protocol_suggestion_prompt(title: str, methodology: str, initial_description: str = "") -> str:
    """
    Constrói prompt para sugestão de protocolo no campo de Ciências Sociais Aplicadas / Desenvolvimento Regional,
    respeitando as regras RSAC e a metodologia selecionada (PRISMA 2020, PRISMA-ScR / Scoping Reviews - Tricco et al. 2018):
    - No máximo 5 pares de descritores por idioma (PT, EN, ES)
    - Cada expressão em no máximo 2 termos combinados ("termo1" AND "termo2") para compatibilidade BDTD/VuFind
    """
    is_scoping = "ScR" in methodology or "Scoping" in methodology

    framework_instructions = (
        "Esta é uma Revisão de Escopo (Scoping Review) segundo a extensão PRISMA-ScR (Tricco et al., 2018). "
        "Foque no mapeamento conceitual da literatura (PCC: População/Atores, Conceito Central e Contexto Territorial/Regional), "
        "identificação de lacunas de conhecimento e caracterização metodológica das fontes de evidência no campo de Ciências Sociais Aplicadas e Desenvolvimento Regional."
        if is_scoping
        else f"Esta é uma Revisão Sistemática estruturada segundo as diretrizes de {methodology} nas Ciências Sociais Aplicadas e Desenvolvimento Regional."
    )

    return f"""Você é um especialista sênior em metodologia de Revisões Acadêmicas ({methodology}) nas áreas de Ciências Sociais Aplicadas, Economia, Políticas Públicas e Desenvolvimento Regional.
{framework_instructions}
Elabore uma proposta de protocolo completa e estruturada para a revisão descrita abaixo.

TÍTULO DA REVISÃO:
{title}

DESCRIÇÃO / ESCOPO INICIAL:
{initial_description or "Revisão acadêmica em Ciências Sociais Aplicadas / Desenvolvimento Regional."}

==================== REGRAS OBRIGATÓRIAS DE DESCRITORES ====================
1. ESTRUTURA EM PARES: Cada descritor DEVE ter no máximo 2 termos combinados com AND.
   Exemplo correto: '"desenvolvimento regional" AND "arranjos produtivos"'
   Exemplo proibido: '"termo 1" AND "termo 2" AND "termo 3"' (NÃO use mais de 2 termos!)
2. LIMITE POR IDIOMA: Forneça NO MÁXIMO 5 pares de descritores por idioma (Português, Inglês, Espanhol).
3. ESPECIFICIDADE EQUILIBRADA: Evite termos excessivamente genéricos ou excessivamente restritos.

Responda OBRIGATORIAMENTE em formato JSON puro, sem textos adicionais:

{{
  "objective": "Objetivo geral claro e conciso da revisão...",
  "pico_population": "População, atores sociais, organizações ou territórios de interesse...",
  "pico_intervention": "Conceito Central / Política Pública / Instrumento avaliado...",
  "pico_comparison": "Contexto Territorial / Cenário Comparativo / Padrão de referência...",
  "pico_outcome": "Mapeamento de resultados / Desfechos socioeconômicos ou institucionais analisados...",
  "descriptors_pt": [
    "\"termo1\" AND \"termo2\"",
    "\"termo3\" AND \"termo4\""
  ],
  "descriptors_en": [
    "\"term1\" AND \"term2\"",
    "\"term3\" AND \"term4\""
  ],
  "descriptors_es": [
    "\"termino1\" AND \"termino2\""
  ],
  "inclusion_criteria": [
    "Critério de inclusão 1...",
    "Critério de inclusão 2..."
  ],
  "exclusion_criteria": [
    "Critério de exclusão 1...",
    "Critério de exclusão 2..."
  ],
  "extraction_questions": [
    "Pergunta de extração / mapeamento de dados 1...",
    "Pergunta de extração / mapeamento de dados 2..."
  ]
}}
"""


CONTEXT_FIELD_LABELS = {
    "project_title": "TÍTULO DO PROJETO / REVISÃO",
    "title": "TÍTULO DO PROJETO / REVISÃO",
    "project_description": "RESUMO / ESCOPO DO PROJETO",
    "description": "RESUMO / ESCOPO DO PROJETO",
    "methodology": "DIRETRIZ METODOLÓGICA",
    "objective": "OBJETIVO GERAL DA REVISÃO (ITEM 4)",
    "pico_population": "POPULAÇÃO / ATORES SOCIAIS (PCC/PICO)",
    "pcc_population": "POPULAÇÃO / ATORES SOCIAIS (PCC/PICO)",
    "pico_intervention": "CONCEITO CENTRAL / POLÍTICA / INTERVENÇÃO (PCC/PICO)",
    "pcc_concept": "CONCEITO CENTRAL / POLÍTICA / INTERVENÇÃO (PCC/PICO)",
    "pico_comparison": "CONTEXTO COMPARATIVO / TERRITORIAL (PCC/PICO)",
    "pcc_context": "CONTEXTO COMPARATIVO / TERRITORIAL (PCC/PICO)",
    "pico_outcome": "DESFECHOS / RESULTADOS ESPERADOS (PCC/PICO)",
    "descriptors_pt": "DESCRITORES DE BUSCA (PORTUGUÊS)",
    "descriptors_en": "DESCRITORES DE BUSCA (INGLÊS)",
    "descriptors_es": "DESCRITORES DE BUSCA (ESPANHOL)",
    "inclusion_criteria": "CRITÉRIOS DE INCLUSÃO DE ESTUDOS",
    "exclusion_criteria": "CRITÉRIOS DE EXCLUSÃO DE ESTUDOS",
    "extraction_questions": "PERGUNTAS DE EXTRAÇÃO / VARIÁVEIS DE MAPEAMENTO",
    "rationale": "JUSTIFICATIVA TEÓRICA / CONTEXTUALIZAÇÃO (ITEM 3)",
    "selection_process": "PROCESSO DE SELEÇÃO E CALIBRAÇÃO (ITEM 9)",
    "data_charting_process": "PROCESSO DE EXTRAÇÃO DE DADOS (ITEM 10)",
    "critical_appraisal": "AVALIAÇÃO CRÍTICA DE QUALIDADE (ITEM 12)",
    "synthesis_methods": "MÉTODOS DE SÍNTESE E MAPEAMENTO (ITEM 14)",
    "summary_evidence": "SÍNTESE GERAL DAS EVIDÊNCIAS (ITEM 24)",
    "limitations": "LIMITAÇÕES DA REVISÃO (ITEM 25)",
    "conclusions": "CONCLUSÕES E LACUNAS DE CONHECIMENTO (ITEM 26)",
    "funding": "FINANCIAMENTO & DECLARAÇÃO DE CONFLITOS (ITEM 27)",
}


def build_field_assist_prompt(
    field_label: str,
    field_guidelines: str = "",
    current_value: str = "",
    project_title: str = "",
    methodology: str = "PRISMA-ScR",
    project_context: dict = None,
    action: str = "generate",
    custom_instruction: str = "",
) -> str:
    """
    Constrói prompt ultra-específico e contextualizado para preenchimento, correção ou aprimoramento
    de um campo específico do protocolo ou artigo, utilizando todos os dados já preenchidos
    (título, resumo, objetivos, critérios, descritores, seções) como base primária de coerência.
    """
    ctx = project_context or {}
    context_summary = []

    if project_title and "project_title" not in ctx and "title" not in ctx:
        context_summary.append(f"• TÍTULO DO PROJETO: {project_title}")
    if methodology and "methodology" not in ctx:
        context_summary.append(f"• METODOLOGIA / DIRETRIZ: {methodology}")

    for key, val in ctx.items():
        if val and isinstance(val, str) and val.strip():
            label = CONTEXT_FIELD_LABELS.get(key, key.upper().replace("_", " "))
            context_summary.append(f"• {label}:\n  {val.strip()}")

    context_block = "\n".join(context_summary) if context_summary else "Nenhum outro campo preenchido previamente. Utilize os conceitos fornecidos na instrução."

    action_instructions = {
        "generate": (
            "Sua tarefa é REDIGIR UMA PROPOSTA COMPLETA, RIGOROSA E ACADÊMICA para este campo, "
            "com base estrita no contexto dos dados já preenchidos no projeto e nas diretrizes metodológicas."
        ),
        "improve": (
            "Sua tarefa é APERFEIÇOAR O TEXTO EXISTENTE fornecido pelo pesquisador, melhorando a clareza, coesão, "
            "precisão terminológica e conformidade estrita com o checklist metodológico, preservando o sentido e as teses centrais do autor "
            "e alinhando-o perfeitamente aos demais campos do projeto."
        ),
        "grammar": (
            "Sua tarefa é REVISAR E CORRIGIR A GRAMÁTICA, PONTUAÇÃO, CONCORDÂNCIA E ESTILO ACADÊMICO do texto, "
            "tornando a escrita fluida, formal e sem erros, sem alterar o conteúdo técnico."
        ),
        "expand": (
            "Sua tarefa é EXPANDIR O CONTEÚDO com maior fundamentação teórica, detalhamento metodológico e contextualização, "
            "mantendo rigor, relevância técnica e sinergia com os outros itens do protocolo."
        ),
        "shorten": (
            "Sua tarefa é SINTETIZAR E TORNAR O TEXTO MAIS CONCISO E DIRETO, eliminando redundâncias "
            "sem perder nenhuma informação metodológica essencial."
        ),
    }.get(action, "Sua tarefa é redigir ou aprimorar o conteúdo com o mais alto padrão acadêmico.")

    return f"""Você é um redator acadêmico sênior e metodologista especializado em Revisões Sistemáticas e de Escopo ({methodology}) nas áreas de Ciências Sociais Aplicadas, Políticas Públicas, Economia e Desenvolvimento Regional.

==================== CONTEXTO INTEGRAL DA REVISÃO (DADOS JÁ PREENCHIDOS) ====================
{context_block}

==================== CAMPO A SER TRABALHADO AGORA ====================
ITEM / CAMPO: {field_label}
DIRETRIZES E ESTRUTURA RECOMENDADA DO ITEM:
{field_guidelines or "Estruture de forma clara, objetiva e metodologicamente rigorosa conforme os padrões acadêmicos internacionais."}

TEXTO ATUAL DO CAMPO (fornecido pelo pesquisador):
{current_value.strip() if current_value.strip() else "(Campo atualmente vazio - redigir proposta completa a partir do contexto acima)"}

INSTRUÇÃO ESPECÍFICA DO USUÁRIO:
{custom_instruction.strip() if custom_instruction.strip() else "Harmonize perfeitamente com todas as informações já preenchidas no projeto."}

OBJETIVO DA AÇÃO:
{action_instructions}

==================== REGRA FUNDAMENTAL DE COERÊNCIA TRANSVERSAL ====================
1. CONSISTÊNCIA TOTAL ENTRE OS ITENS: Você DEVE utilizar ativamente todos os dados já registrados no contexto (Título, Resumo/Descrição, Objetivos, PICO/PCC, Descritores, Critérios e Seções já escritas) para calibrar a geração deste campo.
   - O título define o escopo do resumo, da justificativa e do objetivo;
   - O resumo/justificativa e o objetivo delimitam os descritores, critérios de inclusão/exclusão e perguntas de mapeamento;
   - Os critérios e framework orientam os métodos de extração, calibração e síntese.
2. DOMÍNIO TEMÁTICO: Mantenha terminologia e abordagem nas Ciências Sociais Aplicadas e Desenvolvimento Regional (Políticas Públicas Territoriais, APLs, Governança Regional, Sustentabilidade Socioeconômica, Dinâmicas Territoriais). Não use termos clínicos/médicos.
3. SE FOR CAMPO DE DESCRITORES/BUSCA: Formule ESTRITAMENTE em pares combinados com AND (ex: "termo_1" AND "termo_2"), no máximo 2 termos por expressão e no máximo 5 pares por idioma, compatível com a BDTD (motor VuFind).
4. RIGOR E ZERO ALUCINAÇÃO: Forneça texto acadêmico substancial, elegante, metodologicamente preciso e pronto para publicação.

==================== FORMATO DE RESPOSTA (JSON PURO) ====================
Responda OBRIGATORIAMENTE em JSON puro, sem blocos de código adicionais:
{{
  "suggested_text": "Texto completo sugerido ou aprimorado para o campo...",
  "explanation": "Breve justificativa técnica (1-2 frases) de como o texto foi formulado/harmonizado com base no título, resumo e contexto do protocolo."
}}
"""

