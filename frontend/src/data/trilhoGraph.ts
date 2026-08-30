/**
 * Revsist — Grafo do Modo Trilho (Tutor Metodológico Guiado)
 * 100% Determinístico — ZERO Inteligência Artificial (Doc 46)
 *
 * Baseado estritamente na literatura canônica:
 * - Galvão & Pereira (2014) — 8 passos metodológicos
 * - PRISMA 2020 / PRISMA-ScR / PRISMA-S
 * - JBI Manual for Evidence Synthesis (2024)
 * - Cochrane Handbook / MECIR (2023)
 * - CEE Guidelines v5.1 / SPAR-4-SLR (2021)
 *
 * Domínio de aplicação: Ciências Sociais Aplicadas & Desenvolvimento Regional.
 */

export interface TrilhoBranchOption {
  id: string
  label: string
  badge?: string
  description: string
  example: string
  consequences: string
  actionPayload?: {
    reviewDesign?: string
    frameworkType?: 'PCC' | 'PICO' | 'CIMO' | 'SPIDER' | string
    protocolMode?: 'simplificado' | 'completo'
    collaborationMode?: 'individual' | 'double_blind'
    targetDatabases?: string[]
  }
  nextNodeId: string
}

export interface TrilhoNode {
  id: string
  phase: number
  phaseName: string
  title: string
  instruction: string
  rationale: string
  guidelineReference: string
  targetElementSelector?: string
  targetPageUrl?: string
  branchingQuestion?: {
    questionText: string
    helpContext?: string
    options: TrilhoBranchOption[]
  }
  actionButton?: {
    label: string
    targetSelector?: string
    targetUrl?: string
  }
  nextNodeId?: string
  previousNodeId?: string
}

export const TRILHO_PHASES = [
  { phase: 0, name: 'Concepção & Escopo', shortName: '0. Concepção' },
  { phase: 1, name: 'Desenho & Pergunta', shortName: '1. Pergunta' },
  { phase: 2, name: 'Modo do Protocolo', shortName: '2. Protocolo' },
  { phase: 3, name: 'Estratégia de Busca', shortName: '3. Busca Canônica' },
  { phase: 4, name: 'Coleta & Deduplicação', shortName: '4. Coleta' },
  { phase: 5, name: 'Triagem & Calibração', shortName: '5. Triagem' },
  { phase: 6, name: 'Extração de Evidências', shortName: '6. Extração' },
  { phase: 7, name: 'Síntese & Relato PRISMA', shortName: '7. Relato Final' },
]

export const TRILHO_GRAPH: Record<string, TrilhoNode> = {
  // ═════════════════════════════════════════════════════════════════════════
  // FASE 0: CONCEPÇÃO & ESCOPO DA PESQUISA
  // ═════════════════════════════════════════════════════════════════════════
  'intro_welcome': {
    id: 'intro_welcome',
    phase: 0,
    phaseName: 'Concepção & Escopo',
    title: 'Bem-vindo ao Modo Trilho',
    instruction: 'Vamos construir sua revisão sistemática passo a passo. Como primeiro passo, vamos definir a intenção central do seu trabalho.',
    rationale: 'Uma revisão rigorosa inicia pela delimitação do tipo de contribuição científica pretendida antes de qualquer busca nas bases (Galvão & Pereira, 2014).',
    guidelineReference: 'Galvão & Pereira (2014, Passo 1) · PRISMA 2020 (Item 1)',
    targetElementSelector: '[data-trilho-target="protocol-title"]',
    targetPageUrl: '/projects/:id/protocol',
    nextNodeId: 'decision_review_goal',
  },

  'decision_review_goal': {
    id: 'decision_review_goal',
    phase: 0,
    phaseName: 'Concepção & Escopo',
    title: 'Bifurcação 1: Qual é o objetivo primordial da sua revisão?',
    instruction: 'Selecione a alternativa que melhor descreve o propósito do seu estudo para direcionarmos o desenho e o framework corretos.',
    rationale: 'O tipo de revisão determina se haverá avaliação de risco de viés, qual o framework da pergunta e qual diretriz de relato utilizar (PRISMA-ScR vs. PRISMA 2020).',
    guidelineReference: 'JBI Manual 2024 · PRISMA 2020 Item 4',
    branchingQuestion: {
      questionText: 'Qual é a natureza e a finalidade principal da sua revisão?',
      helpContext: 'Escolha a opção que mais se alinha ao seu objetivo acadêmico.',
      options: [
        {
          id: 'opt_scoping',
          label: 'Mapear conceitos, extensão da literatura e lacunas',
          badge: 'Revisão de Escopo (D4)',
          description: 'Ideal para mapear temas emergentes, conceitos multifacetados e identificar lacunas de pesquisa.',
          example: 'Ex.: Mapear os arranjos de governança territorial e inovação socioeconômica em APLs na América Latina.',
          consequences: 'Direciona para o Desenho D4 (Scoping Review), Diretriz PRISMA-ScR e Framework PCC.',
          actionPayload: { reviewDesign: 'D4', frameworkType: 'PCC' },
          nextNodeId: 'step_pcc_formulation',
        },
        {
          id: 'opt_policy_effect',
          label: 'Avaliar impacto ou eficácia de políticas públicas/intervenções',
          badge: 'Políticas Territoriais (D14) / Sistemática (D1)',
          description: 'Focada em avaliar resultados concretos, programas governamentais e instrumentos de intervenção territorial.',
          example: 'Ex.: Avaliar a eficácia de políticas de desenvolvimento regional e incentivos fiscais sobre o emprego local.',
          consequences: 'Direciona para o Desenho D14/D1, Diretriz PRISMA 2020 e Framework PICO/CIMO.',
          actionPayload: { reviewDesign: 'D14', frameworkType: 'CIMO' },
          nextNodeId: 'step_pico_cimo_formulation',
        },
        {
          id: 'opt_bibliometrics',
          label: 'Análise bibliométrica de produção científica e redes',
          badge: 'Bibliometria (D9)',
          description: 'Mapeamento quantitativo de redes de coautoria, acoplamento bibliográfico e evolução temporal da produção.',
          example: 'Ex.: Análise bibliométrica da produção científica sobre desenvolvimento territorial sustentável (2010–2025).',
          consequences: 'Direciona para o Desenho D9, Diretriz BIBLIO e Framework Domínio-Recorte-Unidade.',
          actionPayload: { reviewDesign: 'D9', frameworkType: 'Domínio-Recorte-Unidade' },
          nextNodeId: 'step_biblio_formulation',
        },
        {
          id: 'opt_qualitative',
          label: 'Sintetizar percepções e experiências de atores locais',
          badge: 'Qualitativa / Metaetnografia (D5)',
          description: 'Síntese interpretativa de estudos qualitativos sobre dinâmicas sociais e percepções comunitárias.',
          example: 'Ex.: Percepções de comunidades tradicionais sobre impactos socioambientais de grandes empreendimentos.',
          consequences: 'Direciona para o Desenho D5, Diretriz ENTREQ e Framework SPIDER/PICo.',
          actionPayload: { reviewDesign: 'D5', frameworkType: 'SPIDER' },
          nextNodeId: 'step_qual_formulation',
        },
      ],
    },
    previousNodeId: 'intro_welcome',
  },

  // ═════════════════════════════════════════════════════════════════════════
  // FASE 1: DESENHO & PERGUNTA METODOLÓGICA
  // ═════════════════════════════════════════════════════════════════════════
  'step_pcc_formulation': {
    id: 'step_pcc_formulation',
    phase: 1,
    phaseName: 'Desenho & Pergunta',
    title: 'Estruturação da Pergunta com Framework PCC',
    instruction: 'Preencha os três componentes do PCC: População/Atores (P), Conceito Central (C) e Contexto Territorial (C).',
    rationale: 'Revisões de escopo utilizam o mnemônico PCC para garantir que os limites da busca sejam conceitual e geograficamente claros sem restringir prematuramente os tipos de estudo (JBI Manual 2024).',
    guidelineReference: 'JBI Scoping Review Guidance (2024) · PRISMA-ScR (Item 4)',
    targetElementSelector: '[data-trilho-target="protocol-framework"]',
    targetPageUrl: '/projects/:id/protocol',
    actionButton: {
      label: 'Preencher Componentes PCC',
      targetSelector: '[data-trilho-target="protocol-framework"]',
    },
    nextNodeId: 'decision_protocol_mode',
    previousNodeId: 'decision_review_goal',
  },

  'step_pico_cimo_formulation': {
    id: 'step_pico_cimo_formulation',
    phase: 1,
    phaseName: 'Desenho & Pergunta',
    title: 'Estruturação da Pergunta com Framework PICO / CIMO',
    instruction: 'Decomponha a pergunta nos eixos: Contexto institucional (C), Intervenção/Política (I), Mecanismo de governança (M) e Desfechos socioeconômicos (O).',
    rationale: 'Para avaliação de políticas públicas e intervenções territoriais, o framework CIMO (Denyer & Tranfield, 2009) conecta os mecanismos causais às condições contextuais de implementação.',
    guidelineReference: 'Denyer & Tranfield (2009) · PRISMA 2020 (Item 4)',
    targetElementSelector: '[data-trilho-target="protocol-framework"]',
    targetPageUrl: '/projects/:id/protocol',
    actionButton: {
      label: 'Preencher Componentes CIMO/PICO',
      targetSelector: '[data-trilho-target="protocol-framework"]',
    },
    nextNodeId: 'decision_protocol_mode',
    previousNodeId: 'decision_review_goal',
  },

  'step_biblio_formulation': {
    id: 'step_biblio_formulation',
    phase: 1,
    phaseName: 'Desenho & Pergunta',
    title: 'Definição do Domínio, Recorte e Unidade Bibliométrica',
    instruction: 'Defina o domínio temático principal, o recorte temporal exato e as unidades de análise bibliométrica (autores, periódicos, palavras-chave, citações).',
    rationale: 'Estudos bibliométricos exigem delimitação explícita dos limiares de inclusão e das unidades bibliométricas analisadas para garantir reprodutibilidade matemática (Zupic & Čater, 2015; Diretriz BIBLIO).',
    guidelineReference: 'Diretriz BIBLIO · Zupic & Čater (2015)',
    targetElementSelector: '[data-trilho-target="protocol-framework"]',
    targetPageUrl: '/projects/:id/protocol',
    nextNodeId: 'decision_protocol_mode',
    previousNodeId: 'decision_review_goal',
  },

  'step_qual_formulation': {
    id: 'step_qual_formulation',
    phase: 1,
    phaseName: 'Desenho & Pergunta',
    title: 'Estruturação com Framework SPIDER / PICo',
    instruction: 'Defina a Amostra/Atores (Sample), Fenômeno de Interesse (Phenomenon of Interest), Desenho metodológico (Design) e Avaliação/Experiência (Evaluation).',
    rationale: 'Para evidências qualitativas em ciências sociais, o framework SPIDER (Cooke et al., 2012) supera limitações do PICO em capturar atitudes, percepções e significados sociais.',
    guidelineReference: 'Cooke, Smith & Booth (2012) · ENTREQ Statement',
    targetElementSelector: '[data-trilho-target="protocol-framework"]',
    targetPageUrl: '/projects/:id/protocol',
    nextNodeId: 'decision_protocol_mode',
    previousNodeId: 'decision_review_goal',
  },

  // ═════════════════════════════════════════════════════════════════════════
  // FASE 2: MODO DO PROTOCOLO (SIMPLIFICADO VS. COMPLETO)
  // ═════════════════════════════════════════════════════════════════════════
  'decision_protocol_mode': {
    id: 'decision_protocol_mode',
    phase: 2,
    phaseName: 'Modo do Protocolo',
    title: 'Bifurcação 2: Qual a profundidade necessária para o seu protocolo?',
    instruction: 'Escolha entre o Modo Simplificado (Núcleo de Busca com 14 campos) ou o Modo Completo (Gabarito PRISMA Oficial).',
    rationale: 'O Revsist permite trabalhar com escopo declarado: o modo Simplificado cobre integralmente o PRISMA-S e dados a extrair, carimbando formalmente o que cobre e o que não cobre (Doc 45 §8.4).',
    guidelineReference: 'Doc 45 §8 · PRISMA-S (Rethlefsen et al., 2021)',
    branchingQuestion: {
      questionText: 'Qual modalidade de trabalho atende melhor ao seu cronograma e finalidade?',
      helpContext: 'Você pode migrar entre os modos a qualquer momento sem perda de dados.',
      options: [
        {
          id: 'opt_mode_simplified',
          label: 'Modo Simplificado (14 Campos Essenciais)',
          badge: 'Recomendado para Execução Ágil',
          description: 'Conjunto focado no planejamento da busca e extração (PRISMA-S + PRISMA 2020 5-7 + S11 Extração).',
          example: 'Ideal para dissertações, teses e artigos em que a execução ágil com rigor de busca é prioritária.',
          consequences: 'Ativa formulário direto de 14 campos com carimbo normativo e exportação de Registro de Busca.',
          actionPayload: { protocolMode: 'simplificado' },
          nextNodeId: 'step_search_strategy_intro',
        },
        {
          id: 'opt_mode_complete',
          label: 'Modo Completo (Gabarito PRISMA Oficial)',
          badge: 'Para Registro PROSPERO / Publicação',
          description: 'Gabarito formal completo com 7 seções cronológicas, governança de equipe, risco de viés e seções de manuscrito.',
          example: 'Essencial se você planeja registrar o protocolo em repositórios abertos (OSF, PROSPERO) ou submetê-lo a periódicos.',
          consequences: 'Ativa o estúdio de redação integral com todas as abas e checklist de conformidade.',
          actionPayload: { protocolMode: 'completo' },
          nextNodeId: 'step_search_strategy_intro',
        },
      ],
    },
    previousNodeId: 'step_pcc_formulation',
  },

  // ═════════════════════════════════════════════════════════════════════════
  // FASE 3: ESTRATÉGIA DE BUSCA CANÔNICA & PRESS 2016
  // ═════════════════════════════════════════════════════════════════════════
  'step_search_strategy_intro': {
    id: 'step_search_strategy_intro',
    phase: 3,
    phaseName: 'Estratégia de Busca',
    title: 'Construção da Estratégia Canônica por Blocos Conceituais',
    instruction: 'No Estúdio de Busca, crie um bloco de termos para cada componente da sua pergunta. Dentro de cada bloco, use sinônimos (OR). Os blocos serão combinados por (AND).',
    rationale: 'A estratégia em blocos modulares permite que o Revsist gere a sintaxe correta para cada base de dados (Scopus, PubMed, SciELO) e faça a decomposição em pares para a BDTD (PRISMA-S Item 3).',
    guidelineReference: 'PRISMA-S Item 3 · PRESS 2016 (McGowan et al., 2016)',
    targetElementSelector: '[data-trilho-target="search-blocks-container"]',
    targetPageUrl: '/projects/:id/protocol',
    actionButton: {
      label: 'Abrir Estúdio de Busca Canônica',
      targetSelector: '[data-trilho-target="search-blocks-container"]',
    },
    nextNodeId: 'step_bdtd_descriptor_rules',
    previousNodeId: 'decision_protocol_mode',
  },

  'step_bdtd_descriptor_rules': {
    id: 'step_bdtd_descriptor_rules',
    phase: 3,
    phaseName: 'Estratégia de Busca',
    title: 'Regras de Descritores & Conformidade BDTD (VuFind)',
    instruction: 'Certifique-se de que os descritores estão formulados no máximo em pares (ex.: "governança territorial" AND "arranjos produtivos"), com até 5 pares por idioma.',
    rationale: 'O motor VuFind da BDTD não processa consultas booleanas aninhadas com 3 ou mais termos. O Revsist realiza a decomposição cartesiana em pares para garantir que todas as teses e dissertações relevantes sejam recuperadas sem falhas.',
    guidelineReference: 'Diretrizes Revsist (.agents/AGENTS.md) · VuFind Search Protocol',
    targetElementSelector: '[data-trilho-target="search-preview"]',
    targetPageUrl: '/projects/:id/protocol',
    nextNodeId: 'step_press_review',
    previousNodeId: 'step_search_strategy_intro',
  },

  'step_press_review': {
    id: 'step_press_review',
    phase: 3,
    phaseName: 'Estratégia de Busca',
    title: 'Autoavaliação Heurística PRESS 2016',
    instruction: 'Clique em "Avaliar Estratégia (PRESS 2016)" para inspecionar os 6 domínios de qualidade da sua busca antes de disparar a coleta.',
    rationale: 'O guideline PRESS (Peer Review of Electronic Search Strategies) é o padrão-ouro internacional para validar a eficácia e ausência de erros em estratégias de busca acadêmica.',
    guidelineReference: 'PRESS 2016 Guideline (McGowan et al., 2016)',
    targetElementSelector: '[data-trilho-target="search-press-btn"]',
    targetPageUrl: '/projects/:id/protocol',
    actionButton: {
      label: 'Executar Auditoria PRESS 2016',
      targetSelector: '[data-trilho-target="search-press-btn"]',
    },
    nextNodeId: 'step_eligibility_criteria',
    previousNodeId: 'step_bdtd_descriptor_rules',
  },

  'step_eligibility_criteria': {
    id: 'step_eligibility_criteria',
    phase: 3,
    phaseName: 'Estratégia de Busca',
    title: 'Critérios de Elegibilidade (Inclusão & Exclusão)',
    instruction: 'Cadastre ao menos 1 critério de inclusão e declare em que momento se aplica (Título/Resumo, Texto Completo ou Ambos).',
    rationale: 'Critérios explícitos evitam viés de seleção e viabilizam o relato do motivo de exclusão de cada estudo no diagrama PRISMA (PRISMA 2020 Item 5 e 16b).',
    guidelineReference: 'PRISMA 2020 (Item 5) · MECIR Standard C14-C17',
    targetElementSelector: '[data-trilho-target="protocol-criteria"]',
    targetPageUrl: '/projects/:id/protocol',
    nextNodeId: 'step_extraction_questions_setup',
    previousNodeId: 'step_press_review',
  },

  'step_extraction_questions_setup': {
    id: 'step_extraction_questions_setup',
    phase: 3,
    phaseName: 'Estratégia de Busca',
    title: 'Definição a Priori das Perguntas de Extração (S11)',
    instruction: 'Defina a lista de variáveis e perguntas que serão respondidas para cada estudo incluído. Utilize o botão "Sugeridas pelo desenho" para partir de um conjunto inicial.',
    rationale: 'O PRISMA-P item 12 exige listar e definir a priori todas as variáveis a extrair. Definir as perguntas antes da coleta impede o viés de dragagem de dados (Decisão D-C, Doc 45 §8.3).',
    guidelineReference: 'PRISMA-P (Item 12) · PRISMA 2020 (Item 10a)',
    targetElementSelector: '[data-trilho-target="protocol-questions"]',
    targetPageUrl: '/projects/:id/protocol',
    actionButton: {
      label: 'Carregar Perguntas Sugeridas pelo Desenho',
      targetSelector: '[data-trilho-target="protocol-questions"]',
    },
    nextNodeId: 'step_harvest_execution',
    previousNodeId: 'step_eligibility_criteria',
  },

  // ═════════════════════════════════════════════════════════════════════════
  // FASE 4: COLETA NAS BASES & DEDUPLICAÇÃO
  // ═════════════════════════════════════════════════════════════════════════
  'step_harvest_execution': {
    id: 'step_harvest_execution',
    phase: 4,
    phaseName: 'Coleta & Deduplicação',
    title: 'Execução da Coleta nas Bases Acadêmicas',
    instruction: 'Navegue para a tela de Coleta, selecione as bases-alvo (BDTD, SciELO, Scopus, PubMed, OpenAlex) e inicie a busca automatizada.',
    rationale: 'O sistema executará as consultas traduzidas por adaptador em cada base, registrando data/hora, query enviada e contagem bruta para o PRISMA-S Item 14.',
    guidelineReference: 'PRISMA-S (Itens 1, 2, 14) · PRISMA 2020 (Item 7)',
    targetElementSelector: '[data-trilho-target="harvest-run-btn"]',
    targetPageUrl: '/projects/:id/harvesting',
    actionButton: {
      label: 'Ir para Tela de Coleta',
      targetUrl: '/projects/:id/harvesting',
    },
    nextNodeId: 'step_deduplication_audit',
    previousNodeId: 'step_extraction_questions_setup',
  },

  'step_deduplication_audit': {
    id: 'step_deduplication_audit',
    phase: 4,
    phaseName: 'Coleta & Deduplicação',
    title: 'Auditoria da Deduplicação Automática',
    instruction: 'Verifique o número de duplicatas removidas pelo algoritmo do Revsist (DOI + normalização de títulos + Levenshtein). Se houver duplicatas suspeitas, faça a revisão manual.',
    rationale: 'A remoção rigorosa de duplicatas é o primeiro nó do fluxo PRISMA 2020 e evita inflar artificialmente a contagem de evidências (PRISMA 2020 Item 16a).',
    guidelineReference: 'PRISMA 2020 (Item 16a) · PRISMA-S (Item 15)',
    targetElementSelector: '[data-trilho-target="dedup-summary-card"]',
    targetPageUrl: '/projects/:id/harvesting',
    nextNodeId: 'decision_screening_mode',
    previousNodeId: 'step_harvest_execution',
  },

  // ═════════════════════════════════════════════════════════════════════════
  // FASE 5: TRIAGEM (SCREENING) & CALIBRAÇÃO
  // ═════════════════════════════════════════════════════════════════════════
  'decision_screening_mode': {
    id: 'decision_screening_mode',
    phase: 5,
    phaseName: 'Triagem & Calibração',
    title: 'Bifurcação 3: Como será organizada a equipe de triagem?',
    instruction: 'Defina se a triagem será individual ou conduzida por dois revisores independentes em dupla cega.',
    rationale: 'Para revisões sistemáticas e de escopo de alto impacto, a triagem em dupla cega com cálculo do coeficiente de concordância Kappa de Cohen reduz significativamente o viés de seleção (MECIR C39; JBI Manual 2024).',
    guidelineReference: 'MECIR Standard C39 · JBI Evidence Synthesis Manual',
    branchingQuestion: {
      questionText: 'Qual modalidade de triagem será aplicada ao corpus de estudos?',
      options: [
        {
          id: 'opt_screening_single',
          label: 'Triagem Individual (1 Pesquisador)',
          badge: 'Pesquisa Individual / Rápida',
          description: 'O pesquisador avalia os estudos sequencialmente registrando os motivos de exclusão.',
          example: 'Comum em pesquisas de mestrado ou revisões rápidas com tempo limitado.',
          consequences: 'A triagem prossegue de forma direta sem necessidade de reconciliação de conflitos.',
          actionPayload: { collaborationMode: 'individual' },
          nextNodeId: 'step_screening_execution',
        },
        {
          id: 'opt_screening_double_blind',
          label: 'Dupla Cega com Calibração (2 Revisores)',
          badge: 'Padrão-Ouro de Rigor',
          description: 'Dois revisores avaliam cada estudo sem ver o voto do colega. Conflitos são resolvidos por um terceiro revisor.',
          example: 'Recomendado para artigos em periódicos Qualis A e projetos em equipe com múltiplos pesquisadores.',
          consequences: 'Ativa painel de concordância, cálculo de Kappa de Cohen e fluxo de resolução de divergências.',
          actionPayload: { collaborationMode: 'double_blind' },
          nextNodeId: 'step_screening_calibration_pilot',
        },
      ],
    },
    previousNodeId: 'step_deduplication_audit',
  },

  'step_screening_calibration_pilot': {
    id: 'step_screening_calibration_pilot',
    phase: 5,
    phaseName: 'Triagem & Calibração',
    title: 'Piloto de Calibração da Triagem (Lote de 50 Estudos)',
    instruction: 'Realize o teste piloto em um lote inicial de 50 estudos. Discuta as divergências para alinhar o entendimento dos critérios de elegibilidade.',
    rationale: 'O teste de calibração preliminar assegura consistência entre os revisores e calibra a interpretação dos critérios antes de triar o restante da base (JBI Manual 2024; Cochrane MECIR C37).',
    guidelineReference: 'JBI Manual (Cap. 11.2.4) · Cochrane MECIR Standard C37',
    targetElementSelector: '[data-trilho-target="screening-pilot-btn"]',
    targetPageUrl: '/projects/:id/screening',
    actionButton: {
      label: 'Iniciar Piloto de Calibração',
      targetSelector: '[data-trilho-target="screening-pilot-btn"]',
    },
    nextNodeId: 'step_screening_execution',
    previousNodeId: 'decision_screening_mode',
  },

  'step_screening_execution': {
    id: 'step_screening_execution',
    phase: 5,
    phaseName: 'Triagem & Calibração',
    title: 'Triagem de Títulos e Resumos',
    instruction: 'Avalie cada estudo contra os critérios de inclusão e exclusão. Utilize os atalhos de teclado (I para Incluir, E para Excluir, P para Pendente).',
    rationale: 'O registro transparente da decisão e do critério violado é fundamental para a auditabilidade do processo e geração do diagrama de fluxo PRISMA 2020.',
    guidelineReference: 'PRISMA 2020 (Item 8 e 16b)',
    targetElementSelector: '[data-trilho-target="screening-decision-buttons"]',
    targetPageUrl: '/projects/:id/screening',
    actionButton: {
      label: 'Ir para Triagem',
      targetUrl: '/projects/:id/screening',
    },
    nextNodeId: 'step_extraction_workflow',
    previousNodeId: 'decision_screening_mode',
  },

  // ═════════════════════════════════════════════════════════════════════════
  // FASE 6: EXTRAÇÃO DE EVIDÊNCIAS (DATA EXTRACTION)
  // ═════════════════════════════════════════════════════════════════════════
  'step_extraction_workflow': {
    id: 'step_extraction_workflow',
    phase: 6,
    phaseName: 'Extração de Evidências',
    title: 'Extração de Dados dos Estudos Incluídos',
    instruction: 'Acesse a aba de Extração e preencha as respostas das perguntas do protocolo para cada estudo aprovado. Se desejar, utilize o modo assistido para localizar trechos no PDF.',
    rationale: 'A matriz de extração estruturada é a base factual para a síntese dos resultados e para responder à pergunta de pesquisa (PRISMA 2020 Item 10a e 20).',
    guidelineReference: 'PRISMA 2020 (Item 10a, 20) · JBI Evidence Synthesis Manual',
    targetElementSelector: '[data-trilho-target="extraction-matrix-table"]',
    targetPageUrl: '/projects/:id/extraction',
    actionButton: {
      label: 'Ir para Tela de Extração',
      targetUrl: '/projects/:id/extraction',
    },
    nextNodeId: 'step_synthesis_and_reporting',
    previousNodeId: 'step_screening_execution',
  },

  // ═════════════════════════════════════════════════════════════════════════
  // FASE 7: SÍNTESE, INDICADORES & RELATO FINAL PRISMA
  // ═════════════════════════════════════════════════════════════════════════
  'step_synthesis_and_reporting': {
    id: 'step_synthesis_and_reporting',
    phase: 7,
    phaseName: 'Síntese & Relato PRISMA',
    title: 'Síntese, Diagrama de Fluxo e Exportação de Resultados',
    instruction: 'Na aba de Indicadores, confira o Diagrama de Fluxo PRISMA 2020 gerado automaticamente e exporte o Registro de Busca nos formatos DOCX, PDF, CSV ou JSON.',
    rationale: 'A etapa final consolida toda a rastreabilidade metodológica, garantindo que o manuscrito e os materiais suplementares atendam integralmente às exigências de transparência e reprodutibilidade científica.',
    guidelineReference: 'PRISMA 2020 Statement (Page et al., 2021) · PRISMA-S (Item 16)',
    targetElementSelector: '[data-trilho-target="prisma-flowchart"]',
    targetPageUrl: '/projects/:id/insights',
    actionButton: {
      label: 'Ver Indicadores e Diagrama PRISMA',
      targetUrl: '/projects/:id/insights',
    },
    nextNodeId: 'step_conclusion_congrats',
    previousNodeId: 'step_extraction_workflow',
  },

  'step_conclusion_congrats': {
    id: 'step_conclusion_congrats',
    phase: 7,
    phaseName: 'Síntese & Relato PRISMA',
    title: 'Jornada Metodológica Concluída!',
    instruction: 'Parabéns! Você construiu uma revisão sistemática metodologicamente sólida, auditável e alinhada às melhores práticas internacionais de pesquisa.',
    rationale: 'O cumprimento rigoroso de cada etapa assegura alta probabilidade de aprovação na revisão por pares e máximo impacto científico.',
    guidelineReference: 'PRISMA 2020 · JBI · Cochrane · CEE Guidelines',
    targetElementSelector: '[data-trilho-target="export-manuscript-btn"]',
    targetPageUrl: '/projects/:id/protocol',
    previousNodeId: 'step_synthesis_and_reporting',
  },
}
