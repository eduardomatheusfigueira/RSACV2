/**
 * RSAC V2 — Listas de Verificação das Diretrizes Metodológicas
 * ============================================================
 *
 * Matrizes de auditoria exibidas na aba "Checklist" do Estúdio de Protocolo.
 *
 * PROVENIÊNCIA — leia antes de editar
 * -----------------------------------
 * A numeração dos itens NÃO é uniforme entre as diretrizes, porque cada
 * documento oficial numera do seu próprio jeito. Este arquivo respeita isso em
 * vez de forçar um padrão único, e cada lista declara abaixo de qual regime
 * ela vem:
 *
 *   (A) NUMERAÇÃO OFICIAL REPRODUZIDA — o código do item corresponde ao do
 *       documento publicado, subitens inclusive ("10a", "13b", "1.1").
 *       Aplica-se a: PRISMA-ScR, PRISMA 2020, PRISMA-P, EBSE e
 *       Methodi Ordinatio.
 *
 *   (B) ORGANIZADA POR DOMÍNIOS — o documento oficial é um formulário por
 *       seções, sem uma numeração corrida citável. Os itens seguem os domínios
 *       e a ordem do original, mas o número exibido é sequencial desta
 *       ferramenta. Aplica-se a: ROSES (CEE) e à revisão guarda-chuva (PRIOR).
 *       Nesses casos a descrição da diretriz avisa o pesquisador e o campo
 *       `reference` traz a citação completa para conferência.
 *
 * Diretrizes que adotam o instrumento de relato de outra (Cochrane e Campbell
 * exigem PRISMA 2020; JBI para escopo usa PRISMA-ScR) REUTILIZAM a lista
 * correspondente em vez de manter uma cópia paralela — ver protocolCatalog.ts.
 *
 * `phase` separa o que se declara ANTES de coletar (a_priori, o protocolo
 * propriamente dito) do que só se pode escrever DEPOIS da extração
 * (a_posteriori, resultados e discussão). Itens sem `phase` contam como
 * a_priori.
 */

export type ChecklistPhase = 'a_priori' | 'a_posteriori'

export interface ProtocolChecklistItem {
  /** Código do item conforme a diretriz. Ver nota de proveniência acima. */
  id: string
  /** Seção do manuscrito a que o item pertence. */
  section: string
  /** Título curto do item. */
  item: string
  /** O que precisa estar relatado para o item ser considerado atendido. */
  desc: string
  /** `false` = item condicional ou recomendado, não obrigatório. */
  essential: boolean
  /** Momento do ciclo da revisão. Ausente equivale a `a_priori`. */
  phase?: ChecklistPhase
  /**
   * Campo do Estúdio de Protocolo que este item governa.
   *
   * Não é declarado aqui, e sim aplicado por `withFieldKeys` em
   * protocolCatalog.ts: a mesma lista é reaproveitada por diretrizes
   * diferentes (Cochrane e Campbell usam a do PRISMA 2020), e a ligação
   * campo → item pertence à diretriz, não à lista.
   *
   * Quando um campo do Estúdio não tem item correspondente na diretriz ativa,
   * fica sem `fieldKey` e a interface cai no texto genérico — melhor do que
   * exibir a numeração de um item que não trata daquilo.
   */
  fieldKey?: string
}

/* ═══════════════════════════════════════════════════════════════════════════
   PRISMA-ScR — 22 itens · numeração oficial (regime A)
   Tricco AC, Lillie E, Zarin W, et al. PRISMA Extension for Scoping Reviews
   (PRISMA-ScR): Checklist and Explanation. Ann Intern Med. 2018;169(7):467-473.

   Itens 12 e 16 (avaliação crítica) são opcionais em revisões de escopo: o
   objetivo é mapear a extensão da literatura, não julgar a força da evidência.
   ═══════════════════════════════════════════════════════════════════════════ */

export const PRISMA_SCR_CHECKLIST: ProtocolChecklistItem[] = [
  {
    id: '1', section: 'Título', item: 'Título',
    desc: 'Identificar o relatório como uma revisão de escopo (scoping review) no próprio título.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '2', section: 'Resumo', item: 'Resumo estruturado',
    desc: 'Resumo estruturado com contexto, objetivos, critérios de elegibilidade, fontes de evidência, métodos de charting, resultados e conclusões relacionadas à pergunta.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '3', section: 'Introdução', item: 'Justificativa',
    desc: 'Descrever a justificativa da revisão no contexto do que já se conhece. Explicar por que a pergunta se presta a uma revisão de escopo e não a outro desenho.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '4', section: 'Introdução', item: 'Objetivos',
    desc: 'Enunciar as perguntas e os objetivos explicitamente, relacionando-os aos elementos-chave (População, Conceito e Contexto — PCC) ou a outra formulação equivalente.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '5', section: 'Métodos', item: 'Protocolo e registro',
    desc: 'Indicar se existe protocolo prévio, onde ele pode ser acessado e, havendo registro, informar a plataforma e o número.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '6', section: 'Métodos', item: 'Critérios de elegibilidade',
    desc: 'Especificar as características das fontes usadas como critério (anos cobertos, idiomas, status de publicação) e justificá-las.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '7', section: 'Métodos', item: 'Fontes de informação',
    desc: 'Descrever todas as fontes consultadas (bases, contato com autores, literatura cinzenta) e a data da última busca em cada uma.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '8', section: 'Métodos', item: 'Estratégia de busca',
    desc: 'Apresentar a estratégia completa de pelo menos uma base, com todos os limites usados, de modo que a busca possa ser reproduzida.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '9', section: 'Métodos', item: 'Seleção das fontes de evidência',
    desc: 'Descrever o processo de seleção (triagem e elegibilidade) aplicado na revisão e, quando cabível, no processo de síntese.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '10', section: 'Métodos', item: 'Processo de charting dos dados',
    desc: 'Descrever o método de extração dos dados (formulário calibrado, extração independente por dois revisores, processo iterativo) e os procedimentos de obtenção e confirmação de dados junto aos autores.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '11', section: 'Métodos', item: 'Itens de dados',
    desc: 'Listar e definir todas as variáveis para as quais os dados foram buscados, bem como as suposições e simplificações adotadas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '12', section: 'Métodos', item: 'Avaliação crítica das fontes individuais',
    desc: 'Se realizada, descrever os métodos de avaliação crítica e como essa informação foi usada na síntese. Opcional em revisões de escopo.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '13', section: 'Métodos', item: 'Síntese dos resultados',
    desc: 'Descrever os métodos de manuseio e sumarização dos dados que foram extraídos.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '14', section: 'Resultados', item: 'Seleção das fontes de evidência',
    desc: 'Informar o número de fontes rastreadas, avaliadas quanto à elegibilidade e incluídas, com as razões das exclusões em cada etapa — idealmente em um diagrama de fluxo.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '15', section: 'Resultados', item: 'Características das fontes de evidência',
    desc: 'Apresentar, para cada fonte, as características para as quais os dados foram extraídos, com as respectivas citações.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '16', section: 'Resultados', item: 'Avaliação crítica dentro das fontes',
    desc: 'Se o item 12 foi realizado, apresentar os dados da avaliação crítica. Opcional em revisões de escopo.',
    essential: false, phase: 'a_posteriori',
  },
  {
    id: '17', section: 'Resultados', item: 'Resultados das fontes individuais',
    desc: 'Para cada fonte incluída, apresentar os dados relevantes que se relacionam com as perguntas e os objetivos da revisão.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '18', section: 'Resultados', item: 'Síntese dos resultados',
    desc: 'Sumarizar e/ou apresentar os resultados que se relacionam com as perguntas e os objetivos da revisão.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '19', section: 'Discussão', item: 'Síntese da evidência',
    desc: 'Sumarizar os achados principais, incluindo a força da evidência de cada resultado, e relacioná-los aos objetivos e aos grupos de interesse.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '20', section: 'Discussão', item: 'Limitações',
    desc: 'Discutir as limitações do processo de revisão de escopo.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '21', section: 'Discussão', item: 'Conclusões',
    desc: 'Apresentar interpretação geral dos resultados face aos objetivos e às perguntas, e apontar as implicações para a prática e para pesquisas futuras.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '22', section: 'Financiamento', item: 'Financiamento',
    desc: 'Descrever as fontes de financiamento das fontes incluídas e da própria revisão de escopo, além do papel dos financiadores.',
    essential: true, phase: 'a_posteriori',
  },
]

/* ═══════════════════════════════════════════════════════════════════════════
   PRISMA 2020 — 27 itens (42 linhas com subitens) · numeração oficial (A)
   Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an
   updated guideline for reporting systematic reviews. BMJ. 2021;372:n71.
   ═══════════════════════════════════════════════════════════════════════════ */

export const PRISMA_2020_CHECKLIST: ProtocolChecklistItem[] = [
  {
    id: '1', section: 'Título', item: 'Título',
    desc: 'Identificar o relatório como uma revisão sistemática.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '2', section: 'Resumo', item: 'Resumo',
    desc: 'Elaborar o resumo seguindo a lista de verificação PRISMA 2020 for Abstracts.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '3', section: 'Introdução', item: 'Justificativa',
    desc: 'Descrever a justificativa da revisão no contexto do conhecimento existente.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '4', section: 'Introdução', item: 'Objetivos',
    desc: 'Apresentar uma declaração explícita das perguntas que a revisão pretende responder.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '5', section: 'Métodos', item: 'Critérios de elegibilidade',
    desc: 'Especificar os critérios de inclusão e exclusão e como os estudos foram agrupados nas sínteses.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '6', section: 'Métodos', item: 'Fontes de informação',
    desc: 'Especificar todas as bases, registros, sites, organizações e outras fontes consultadas, com a data da última busca em cada uma.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '7', section: 'Métodos', item: 'Estratégia de busca',
    desc: 'Apresentar a estratégia completa de todas as bases e registros, incluindo filtros e limites utilizados.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '8', section: 'Métodos', item: 'Processo de seleção',
    desc: 'Especificar os métodos de decisão sobre elegibilidade: quantos revisores rastrearam cada registro, se trabalharam de forma independente e que ferramentas de automação foram usadas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '9', section: 'Métodos', item: 'Processo de coleta de dados',
    desc: 'Especificar os métodos de extração: quantos revisores, se independentes, processos de confirmação junto aos investigadores e ferramentas de automação.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '10a', section: 'Métodos', item: 'Itens de dados — desfechos',
    desc: 'Listar e definir todos os desfechos buscados, e como foram tratados os resultados múltiplos compatíveis com cada domínio de desfecho.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '10b', section: 'Métodos', item: 'Itens de dados — outras variáveis',
    desc: 'Listar e definir todas as demais variáveis coletadas (participantes, intervenções, financiamento) e as suposições feitas sobre informação ausente ou ambígua.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '11', section: 'Métodos', item: 'Avaliação do risco de viés',
    desc: 'Especificar os métodos de avaliação do risco de viés, incluindo as ferramentas usadas, quantos revisores avaliaram cada estudo e se trabalharam de forma independente.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '12', section: 'Métodos', item: 'Medidas de efeito',
    desc: 'Especificar, para cada desfecho, as medidas de efeito (razão de risco, diferença de médias) usadas na síntese ou na apresentação dos resultados.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '13a', section: 'Métodos', item: 'Síntese — elegibilidade por síntese',
    desc: 'Descrever os processos de decisão sobre quais estudos entram em cada síntese, com o cruzamento entre características dos estudos e grupos de intervenção e desfecho.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '13b', section: 'Métodos', item: 'Síntese — preparo dos dados',
    desc: 'Descrever os métodos de preparação dos dados para apresentação ou síntese: conversões, imputação de dados ausentes.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '13c', section: 'Métodos', item: 'Síntese — tabulação e visualização',
    desc: 'Descrever os métodos usados para tabular ou exibir visualmente os resultados dos estudos individuais e das sínteses.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '13d', section: 'Métodos', item: 'Síntese — métodos de síntese',
    desc: 'Descrever os métodos de síntese e a justificativa da escolha. Havendo meta-análise, descrever o modelo, o método de identificação de heterogeneidade e o pacote estatístico utilizado.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '13e', section: 'Métodos', item: 'Síntese — heterogeneidade',
    desc: 'Descrever métodos de exploração de possíveis causas de heterogeneidade, como análise de subgrupos e meta-regressão.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '13f', section: 'Métodos', item: 'Síntese — análises de sensibilidade',
    desc: 'Descrever as análises de sensibilidade conduzidas para avaliar a robustez dos resultados sintetizados.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '14', section: 'Métodos', item: 'Avaliação de viés de relato',
    desc: 'Descrever os métodos de avaliação do risco de viés por dados faltantes em uma síntese, decorrente de viés de relato.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '15', section: 'Métodos', item: 'Avaliação da certeza',
    desc: 'Descrever os métodos usados para avaliar a certeza (ou confiança) no corpo de evidência de cada desfecho — tipicamente GRADE.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '16a', section: 'Resultados', item: 'Seleção dos estudos',
    desc: 'Descrever os números de registros rastreados, avaliados quanto à elegibilidade e incluídos, idealmente com um diagrama de fluxo.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '16b', section: 'Resultados', item: 'Estudos excluídos na leitura integral',
    desc: 'Citar os estudos que pareciam atender aos critérios mas foram excluídos, e explicar por que foram excluídos.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '17', section: 'Resultados', item: 'Características dos estudos',
    desc: 'Citar cada estudo incluído e apresentar suas características.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '18', section: 'Resultados', item: 'Risco de viés nos estudos',
    desc: 'Apresentar as avaliações de risco de viés de cada estudo incluído.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '19', section: 'Resultados', item: 'Resultados dos estudos individuais',
    desc: 'Para cada estudo e desfecho, apresentar estatísticas sumárias por grupo e uma estimativa de efeito com precisão (intervalo de confiança), idealmente em tabelas ou gráficos estruturados.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '20a', section: 'Resultados', item: 'Sínteses — características e risco de viés',
    desc: 'Para cada síntese, resumir brevemente as características e o risco de viés dos estudos que a compõem.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '20b', section: 'Resultados', item: 'Sínteses — resultados',
    desc: 'Apresentar os resultados de todas as sínteses estatísticas com estimativa sumária e precisão; havendo comparação de grupos, discutir direção do efeito.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '20c', section: 'Resultados', item: 'Sínteses — heterogeneidade',
    desc: 'Apresentar os resultados de todas as investigações de possíveis causas de heterogeneidade entre os resultados dos estudos.',
    essential: false, phase: 'a_posteriori',
  },
  {
    id: '20d', section: 'Resultados', item: 'Sínteses — sensibilidade',
    desc: 'Apresentar os resultados de todas as análises de sensibilidade conduzidas para avaliar a robustez dos resultados.',
    essential: false, phase: 'a_posteriori',
  },
  {
    id: '21', section: 'Resultados', item: 'Vieses de relato',
    desc: 'Apresentar as avaliações de risco de viés por dados faltantes em cada síntese.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '22', section: 'Resultados', item: 'Certeza da evidência',
    desc: 'Apresentar as avaliações de certeza (ou confiança) no corpo de evidência de cada desfecho.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '23a', section: 'Discussão', item: 'Interpretação geral',
    desc: 'Fornecer interpretação geral dos resultados no contexto de outras evidências.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '23b', section: 'Discussão', item: 'Limitações da evidência',
    desc: 'Discutir as limitações da evidência incluída na revisão.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '23c', section: 'Discussão', item: 'Limitações do processo',
    desc: 'Discutir as limitações dos processos de revisão utilizados.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '23d', section: 'Discussão', item: 'Implicações',
    desc: 'Discutir as implicações dos resultados para a prática, a política pública e a pesquisa futura.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '24a', section: 'Outras informações', item: 'Registro',
    desc: 'Informar o registro e o número, ou declarar que a revisão não foi registrada.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '24b', section: 'Outras informações', item: 'Acesso ao protocolo',
    desc: 'Indicar onde o protocolo pode ser acessado, ou declarar que não foi preparado protocolo.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '24c', section: 'Outras informações', item: 'Emendas ao protocolo',
    desc: 'Descrever e justificar quaisquer emendas às informações registradas ou ao protocolo.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '25', section: 'Outras informações', item: 'Apoio',
    desc: 'Descrever as fontes de apoio financeiro ou não financeiro à revisão, e o papel dos financiadores.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '26', section: 'Outras informações', item: 'Conflitos de interesse',
    desc: 'Declarar quaisquer interesses conflitantes dos autores da revisão.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '27', section: 'Outras informações', item: 'Disponibilidade de dados e código',
    desc: 'Informar quais dos seguintes estão publicamente disponíveis e onde: formulários de extração, dados extraídos, dados usados nas análises, código analítico e demais materiais.',
    essential: true, phase: 'a_posteriori',
  },
]

/* ═══════════════════════════════════════════════════════════════════════════
   PRISMA-P 2015 — 17 itens (26 linhas com subitens) · numeração oficial (A)
   Moher D, Shamseer L, Clarke M, et al. Preferred Reporting Items for
   Systematic review and Meta-Analysis Protocols (PRISMA-P) 2015 statement.
   Syst Rev. 2015;4:1.

   Diretriz de PROTOCOLO: todos os itens são a_priori por definição.
   ═══════════════════════════════════════════════════════════════════════════ */

export const PRISMA_P_CHECKLIST: ProtocolChecklistItem[] = [
  {
    id: '1a', section: 'Informações administrativas', item: 'Título — identificação',
    desc: 'Identificar o relatório como protocolo de uma revisão sistemática.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '1b', section: 'Informações administrativas', item: 'Título — atualização',
    desc: 'Se for atualização de uma revisão anterior, identificá-la como tal.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '2', section: 'Informações administrativas', item: 'Registro',
    desc: 'Informar o nome do registro e o número, ou declarar que ainda não houve registro.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '3a', section: 'Informações administrativas', item: 'Autores — contato',
    desc: 'Fornecer nome, filiação institucional e endereço de correspondência dos autores do protocolo.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '3b', section: 'Informações administrativas', item: 'Autores — contribuições',
    desc: 'Descrever as contribuições de cada autor do protocolo e identificar o garantidor da revisão.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '4', section: 'Informações administrativas', item: 'Emendas',
    desc: 'Se for uma emenda a um protocolo já registrado, identificar as mudanças e sua justificativa. Caso contrário, planejar como as emendas serão documentadas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '5a', section: 'Informações administrativas', item: 'Apoio — fontes',
    desc: 'Indicar as fontes de apoio financeiro ou não financeiro à revisão.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '5b', section: 'Informações administrativas', item: 'Apoio — patrocinador',
    desc: 'Fornecer nome e contato do patrocinador da revisão.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '5c', section: 'Informações administrativas', item: 'Apoio — papel do financiador',
    desc: 'Descrever o papel do patrocinador ou financiador no protocolo e na revisão.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '6', section: 'Introdução', item: 'Justificativa',
    desc: 'Descrever a justificativa da revisão no contexto do conhecimento existente.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '7', section: 'Introdução', item: 'Objetivos',
    desc: 'Enunciar as perguntas de forma explícita, com referência aos participantes, intervenções, comparadores e desfechos (PICO).',
    essential: true, phase: 'a_priori',
  },
  {
    id: '8', section: 'Métodos', item: 'Critérios de elegibilidade',
    desc: 'Especificar as características do estudo e do relato que serão usadas como critério de elegibilidade, com justificativa.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '9', section: 'Métodos', item: 'Fontes de informação',
    desc: 'Descrever todas as fontes pretendidas (bases, registros de ensaios, contato com autores, literatura cinzenta), com a cobertura temporal planejada.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '10', section: 'Métodos', item: 'Estratégia de busca',
    desc: 'Apresentar a estratégia de busca pretendida para pelo menos uma base, incluindo limites planejados, de modo que possa ser repetida.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '11a', section: 'Métodos', item: 'Registros — gestão de dados',
    desc: 'Descrever os mecanismos de gestão dos registros e dos dados ao longo da revisão.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '11b', section: 'Métodos', item: 'Registros — processo de seleção',
    desc: 'Enunciar o processo planejado de seleção (triagem, elegibilidade, inclusão na meta-análise), incluindo quantos revisores atuarão em cada etapa.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '11c', section: 'Métodos', item: 'Registros — processo de coleta',
    desc: 'Descrever o método planejado de extração, incluindo formulários piloto, extração independente em duplicata e processos de obtenção de dados junto aos investigadores.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '12', section: 'Métodos', item: 'Itens de dados',
    desc: 'Listar e definir todas as variáveis para as quais os dados serão buscados, e quaisquer pré-planejadas simplificações de dados.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '13', section: 'Métodos', item: 'Desfechos e priorização',
    desc: 'Listar e definir os desfechos principais e adicionais, com a priorização entre eles e a justificativa.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '14', section: 'Métodos', item: 'Risco de viés nos estudos individuais',
    desc: 'Descrever os métodos planejados de avaliação do risco de viés, e como essa informação será usada na síntese.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '15a', section: 'Métodos', item: 'Síntese — critérios de agrupamento',
    desc: 'Descrever os critérios sob os quais os dados dos estudos serão quantitativamente sintetizados.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '15b', section: 'Métodos', item: 'Síntese — métodos quantitativos',
    desc: 'Se os dados forem apropriados para síntese quantitativa, descrever as medidas sumárias, os métodos de manuseio de dados e de combinação, e como a heterogeneidade será avaliada.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '15c', section: 'Métodos', item: 'Síntese — métodos qualitativos',
    desc: 'Descrever quaisquer métodos propostos de síntese qualitativa quando a síntese quantitativa não for apropriada.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '15d', section: 'Métodos', item: 'Síntese — análises adicionais',
    desc: 'Descrever análises adicionais planejadas: sensibilidade, subgrupos, meta-regressão.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '16', section: 'Métodos', item: 'Meta-vieses',
    desc: 'Especificar avaliações planejadas de meta-vieses, como viés de publicação entre estudos e relato seletivo dentro dos estudos.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '17', section: 'Métodos', item: 'Confiança na evidência cumulativa',
    desc: 'Descrever como será avaliada a força do corpo de evidência — tipicamente GRADE.',
    essential: true, phase: 'a_priori',
  },
]

/* ═══════════════════════════════════════════════════════════════════════════
   ROSES (CEE) — organizada por domínios (regime B)
   Haddaway NR, Macura B, Whaley P, Pullin AS. ROSES RepOrting standards for
   Systematic Evidence Syntheses. Environ Evid. 2018;7:7.
   Ver também: CEE Guidelines and Standards for Evidence Synthesis in
   Environmental Management, versão 5.1.

   O ROSES é um formulário por seções, sem numeração corrida citável: os itens
   seguem os domínios e a ordem do original, mas o número exibido é sequencial
   desta ferramenta.
   ═══════════════════════════════════════════════════════════════════════════ */

export const ROSES_CHECKLIST: ProtocolChecklistItem[] = [
  {
    id: '1', section: 'Título', item: 'Título e tipo de síntese',
    desc: 'Identificar o trabalho como revisão sistemática ou mapa sistemático de evidências, refletindo os elementos da pergunta.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '2', section: 'Resumo', item: 'Resumo estruturado',
    desc: 'Resumo com contexto, objetivos, métodos, resultados e conclusões, permitindo julgar a relevância sem ler o texto integral.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '3', section: 'Contexto', item: 'Contexto e justificativa',
    desc: 'Descrever o contexto ambiental e de políticas públicas, e por que a síntese é necessária.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '4', section: 'Contexto', item: 'Envolvimento de interessados',
    desc: 'Descrever como as partes interessadas foram envolvidas na formulação da pergunta e do escopo.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '5', section: 'Objetivo', item: 'Pergunta e componentes',
    desc: 'Enunciar a pergunta primária e as secundárias, decompostas em população, exposição/intervenção, comparador e desfecho (PICO/PECO).',
    essential: true, phase: 'a_priori',
  },
  {
    id: '6', section: 'Métodos', item: 'Desvios do protocolo',
    desc: 'Declarar se a síntese seguiu um protocolo publicado e descrever qualquer desvio em relação a ele, com justificativa.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '7', section: 'Métodos · Busca', item: 'Termos de busca',
    desc: 'Listar os termos, operadores booleanos e truncamentos usados, com a estratégia completa de cada recurso.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '8', section: 'Métodos · Busca', item: 'Idiomas',
    desc: 'Declarar os idiomas em que se buscou e a competência linguística da equipe.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '9', section: 'Métodos · Busca', item: 'Bases bibliográficas',
    desc: 'Listar todas as bases consultadas, com plataforma, cobertura temporal e data de acesso.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '10', section: 'Métodos · Busca', item: 'Buscas na web e literatura cinzenta',
    desc: 'Descrever buscas em motores de busca e em sites de organizações, com os termos e o número de resultados considerados.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '11', section: 'Métodos · Busca', item: 'Outras fontes',
    desc: 'Descrever buscas em listas de referências, chamadas por evidência e contato com especialistas.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '12', section: 'Métodos · Busca', item: 'Abrangência da busca',
    desc: 'Descrever como a abrangência da busca foi estimada e testada — por exemplo, com uma lista de artigos-âncora conhecidos.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '13', section: 'Métodos · Triagem', item: 'Processo de triagem',
    desc: 'Descrever as etapas de triagem (título, resumo, texto completo), quantos revisores atuaram e como a consistência entre eles foi verificada.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '14', section: 'Métodos · Triagem', item: 'Critérios de elegibilidade',
    desc: 'Especificar os critérios de inclusão e exclusão para cada componente da pergunta.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '15', section: 'Métodos', item: 'Avaliação da validade dos estudos',
    desc: 'Descrever a ferramenta e os critérios de avaliação da validade interna e externa dos estudos, e como as decisões foram checadas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '16', section: 'Métodos', item: 'Codificação e extração de dados',
    desc: 'Descrever as variáveis extraídas, o formulário utilizado, quantos revisores extraíram e como a consistência foi verificada.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '17', section: 'Métodos', item: 'Modificadores de efeito e heterogeneidade',
    desc: 'Listar os potenciais modificadores de efeito e as fontes de heterogeneidade consideradas, e como foram registrados.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '18', section: 'Métodos', item: 'Síntese e apresentação',
    desc: 'Descrever os métodos de síntese (narrativa, quantitativa, qualitativa) e como os resultados serão apresentados.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '19', section: 'Resultados', item: 'Estatísticas descritivas da revisão',
    desc: 'Apresentar o número de registros em cada etapa, com um diagrama de fluxo e a lista de estudos excluídos no texto completo com as razões.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '20', section: 'Resultados', item: 'Síntese narrativa',
    desc: 'Descrever narrativamente as características dos estudos incluídos e os achados por componente da pergunta.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '21', section: 'Resultados', item: 'Validade dos estudos incluídos',
    desc: 'Apresentar o resultado da avaliação de validade de cada estudo e o efeito dela sobre as conclusões.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '22', section: 'Resultados', item: 'Síntese dos dados',
    desc: 'Apresentar os resultados sintetizados, com medidas de efeito e incerteza quando houver síntese quantitativa.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '23', section: 'Discussão', item: 'Razões da heterogeneidade',
    desc: 'Discutir as fontes de heterogeneidade observadas e o seu efeito sobre a interpretação.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '24', section: 'Discussão', item: 'Limitações da revisão',
    desc: 'Discutir as limitações da evidência e do processo de revisão, incluindo possíveis vieses.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '25', section: 'Conclusões', item: 'Implicações para política e gestão',
    desc: 'Apresentar as implicações dos achados para a política pública e a gestão ambiental, sem extrapolar a evidência.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '26', section: 'Conclusões', item: 'Implicações para pesquisa',
    desc: 'Identificar lacunas de conhecimento e prioridades para pesquisa futura.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '27', section: 'Outras informações', item: 'Conflitos, financiamento e dados',
    desc: 'Declarar conflitos de interesse, fontes de financiamento e o papel dos financiadores, e informar onde os dados e o código estão disponíveis.',
    essential: true, phase: 'a_posteriori',
  },
]

/* ═══════════════════════════════════════════════════════════════════════════
   REVISÃO GUARDA-CHUVA (Overview of Reviews) — por domínios (regime B)
   Gates M, Gates A, Pieper D, et al. Reporting guideline for overviews of
   reviews of healthcare interventions: development of the PRIOR statement.
   BMJ. 2022;378:e070849.
   Ver também: JBI Manual for Evidence Synthesis, capítulo de Umbrella Reviews.

   Os itens seguem os domínios do PRIOR — inclusive os que não existem no
   PRISMA 2020: sobreposição entre revisões e qualidade das revisões incluídas.
   O número exibido é sequencial desta ferramenta.
   ═══════════════════════════════════════════════════════════════════════════ */

export const UMBRELLA_CHECKLIST: ProtocolChecklistItem[] = [
  {
    id: '1', section: 'Título', item: 'Título',
    desc: 'Identificar o relatório como uma revisão guarda-chuva (overview of reviews), e não como uma revisão sistemática de estudos primários.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '2', section: 'Resumo', item: 'Resumo estruturado',
    desc: 'Resumo estruturado cobrindo objetivos, critérios de elegibilidade das revisões, métodos, resultados e conclusões.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '3', section: 'Introdução', item: 'Justificativa',
    desc: 'Justificar por que uma revisão guarda-chuva é o desenho adequado, dado o corpo de revisões sistemáticas já existente.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '4', section: 'Introdução', item: 'Objetivos',
    desc: 'Enunciar explicitamente as perguntas da revisão guarda-chuva.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '5', section: 'Métodos', item: 'Critérios de elegibilidade das revisões',
    desc: 'Especificar os critérios de inclusão das revisões, incluindo o desenho mínimo aceitável e como revisões desatualizadas são tratadas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '6', section: 'Métodos', item: 'Fontes de informação',
    desc: 'Especificar bases e registros de revisões sistemáticas consultados, com a data da última busca.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '7', section: 'Métodos', item: 'Estratégia de busca',
    desc: 'Apresentar a estratégia completa, incluindo os filtros usados para restringir os resultados a revisões sistemáticas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '8', section: 'Métodos', item: 'Processo de seleção',
    desc: 'Descrever o processo de triagem das revisões, com quantos revisores atuaram e se de forma independente.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '9', section: 'Métodos', item: 'Processo de coleta de dados',
    desc: 'Descrever a extração dos dados das revisões incluídas e, quando aplicável, dos estudos primários dentro delas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '10', section: 'Métodos', item: 'Itens de dados',
    desc: 'Listar e definir os desfechos e demais variáveis extraídas de cada revisão incluída.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '11', section: 'Métodos', item: 'Qualidade metodológica das revisões',
    desc: 'Descrever a ferramenta de avaliação da qualidade das revisões incluídas — tipicamente AMSTAR-2 ou ROBIS — e quantos revisores a aplicaram.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '12', section: 'Métodos', item: 'Risco de viés dos estudos primários',
    desc: 'Descrever se e como o risco de viés dos estudos primários dentro das revisões foi considerado ou reavaliado.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '13', section: 'Métodos', item: 'Avaliação da sobreposição',
    desc: 'Descrever o método de identificação e quantificação da sobreposição de estudos primários entre as revisões incluídas — por exemplo, matriz de evidência e área coberta corrigida (CCA).',
    essential: true, phase: 'a_priori',
  },
  {
    id: '14', section: 'Métodos', item: 'Métodos de síntese',
    desc: 'Descrever como os resultados das revisões foram sintetizados e como resultados discordantes entre revisões foram tratados.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '15', section: 'Métodos', item: 'Avaliação da certeza',
    desc: 'Descrever como a certeza da evidência foi avaliada ou reaproveitada das revisões incluídas — tipicamente GRADE.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '16', section: 'Resultados', item: 'Seleção das revisões',
    desc: 'Apresentar o número de revisões rastreadas e incluídas, com diagrama de fluxo e razões de exclusão no texto completo.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '17', section: 'Resultados', item: 'Características das revisões',
    desc: 'Citar cada revisão incluída e apresentar suas características, incluindo a data da busca de cada uma.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '18', section: 'Resultados', item: 'Sobreposição entre revisões',
    desc: 'Apresentar o grau de sobreposição de estudos primários entre as revisões e como ele foi tratado na síntese.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '19', section: 'Resultados', item: 'Qualidade das revisões incluídas',
    desc: 'Apresentar o resultado da avaliação de qualidade metodológica de cada revisão incluída.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '20', section: 'Resultados', item: 'Resultados das revisões individuais',
    desc: 'Para cada revisão e desfecho, apresentar as estimativas de efeito com medida de precisão.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '21', section: 'Resultados', item: 'Resultados das sínteses',
    desc: 'Apresentar os resultados de cada síntese entre revisões, explicitando divergências e sua provável origem.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '22', section: 'Resultados', item: 'Certeza da evidência',
    desc: 'Apresentar as avaliações de certeza da evidência para cada desfecho.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '23', section: 'Discussão', item: 'Interpretação e limitações',
    desc: 'Interpretar os resultados no contexto da evidência existente e discutir as limitações da evidência, das revisões incluídas e do próprio processo.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '24', section: 'Discussão', item: 'Implicações',
    desc: 'Discutir as implicações para a prática, a política pública e a pesquisa futura.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '25', section: 'Outras informações', item: 'Registro e protocolo',
    desc: 'Informar o registro e onde o protocolo pode ser acessado, ou declarar sua ausência, e descrever emendas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '26', section: 'Outras informações', item: 'Apoio e conflitos de interesse',
    desc: 'Descrever fontes de apoio, papel dos financiadores e conflitos de interesse dos autores.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '27', section: 'Outras informações', item: 'Disponibilidade de dados e código',
    desc: 'Informar onde os formulários, dados extraídos e código analítico estão disponíveis.',
    essential: true, phase: 'a_posteriori',
  },
]

/* ═══════════════════════════════════════════════════════════════════════════
   EBSE — numeração oficial por fase.passo (regime A)
   Kitchenham B, Charters S. Guidelines for performing Systematic Literature
   Reviews in Software Engineering. EBSE Technical Report EBSE-2007-01.
   Keele University & University of Durham, 2007.
   ═══════════════════════════════════════════════════════════════════════════ */

export const EBSE_CHECKLIST: ProtocolChecklistItem[] = [
  {
    id: '1.1', section: '1. Planejamento', item: 'Identificação da necessidade da revisão',
    desc: 'Demonstrar a necessidade da revisão, verificando antes se já existe revisão sistemática publicada sobre a mesma pergunta.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '1.2', section: '1. Planejamento', item: 'Encomenda da revisão',
    desc: 'Quando a revisão é encomendada por terceiros, registrar o documento de encomenda e o escopo acordado. Opcional em revisões acadêmicas.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '1.3', section: '1. Planejamento', item: 'Especificação das perguntas de pesquisa',
    desc: 'Formular perguntas significativas para praticantes e pesquisadores, decompostas em população, intervenção, comparação, desfechos e contexto.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '1.4', section: '1. Planejamento', item: 'Desenvolvimento do protocolo',
    desc: 'Produzir o protocolo com estratégia de busca, critérios de seleção, critérios de qualidade, formulário de extração e estratégia de síntese, antes de iniciar a busca.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '1.5', section: '1. Planejamento', item: 'Avaliação do protocolo',
    desc: 'Submeter o protocolo a revisão por pares ou por um orientador, e registrar as alterações decorrentes.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '2.1', section: '2. Condução', item: 'Identificação da pesquisa',
    desc: 'Executar a busca conforme o protocolo, documentando strings, bases, datas e número de resultados por fonte, de modo auditável.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '2.2', section: '2. Condução', item: 'Seleção dos estudos primários',
    desc: 'Aplicar os critérios de inclusão e exclusão em etapas, registrar as razões de exclusão e medir a concordância entre revisores.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '2.3', section: '2. Condução', item: 'Avaliação da qualidade dos estudos',
    desc: 'Aplicar o instrumento de qualidade definido no protocolo e explicitar como o escore influencia a inclusão e a síntese.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '2.4', section: '2. Condução', item: 'Extração e monitoramento dos dados',
    desc: 'Extrair os dados com o formulário definido, com extração independente ou conferência por segundo revisor, e registrar dados ausentes.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '2.5', section: '2. Condução', item: 'Síntese dos dados',
    desc: 'Sintetizar os dados de forma descritiva e, quando apropriado, quantitativa, explicitando a heterogeneidade e a sensibilidade dos achados.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '3.1', section: '3. Relato', item: 'Mecanismos de disseminação',
    desc: 'Definir os veículos de disseminação para as audiências acadêmica e profissional.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '3.2', section: '3. Relato', item: 'Formatação do relatório principal',
    desc: 'Estruturar o relatório com contexto, perguntas, métodos, inclusão e exclusão, resultados, discussão e conclusões, com apêndices de reprodutibilidade.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '3.3', section: '3. Relato', item: 'Avaliação do relatório',
    desc: 'Submeter o relatório a revisão por pares e registrar como os comentários foram endereçados.',
    essential: true, phase: 'a_posteriori',
  },
]

/* ═══════════════════════════════════════════════════════════════════════════
   METHODI ORDINATIO — 9 fases · numeração oficial (regime A)
   Pagani RN, Kovaleski JL, Resende LM. Methodi Ordinatio: a proposed
   methodology to select and rank relevant scientific papers encompassing the
   impact factor, number of citations, and year of publication.
   Scientometrics. 2015;105(3):2109-2135.
   ═══════════════════════════════════════════════════════════════════════════ */

export const METHODI_ORDINATIO_CHECKLIST: ProtocolChecklistItem[] = [
  {
    id: '1', section: 'Fase 1', item: 'Estabelecimento da intenção de pesquisa',
    desc: 'Declarar a intenção de pesquisa e o problema que motiva o levantamento bibliográfico.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '2', section: 'Fase 2', item: 'Pesquisa exploratória preliminar',
    desc: 'Realizar buscas exploratórias com palavras-chave provisórias nas bases candidatas, para calibrar termos e delimitar o escopo.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '3', section: 'Fase 3', item: 'Definição das palavras-chave e das bases',
    desc: 'Fixar em definitivo as palavras-chave, as combinações booleanas e as bases de dados que serão usadas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '4', section: 'Fase 4', item: 'Buscas definitivas',
    desc: 'Executar as buscas definitivas nas bases escolhidas, registrando data, string e número de resultados por base.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '5', section: 'Fase 5', item: 'Procedimentos de filtragem',
    desc: 'Remover duplicatas, eliminar registros sem aderência por título e resumo, e descartar os que não atendem ao alinhamento com a intenção de pesquisa.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '6', section: 'Fase 6', item: 'Levantamento de fator de impacto, ano e citações',
    desc: 'Coletar, para cada artigo remanescente, o fator de impacto do periódico, o ano de publicação e o número de citações.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '7', section: 'Fase 7', item: 'Ordenação pela equação InOrdinatio',
    desc: 'Aplicar InOrdinatio = (FI/1000) + α·[10 − (AnoPesq − AnoPubl)] + ΣCi, declarando o valor de α adotado (peso dado à atualidade, de 1 a 10) e sua justificativa.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '8', section: 'Fase 8', item: 'Obtenção dos textos completos',
    desc: 'Localizar e arquivar os textos completos dos artigos ordenados, registrando os que não puderam ser obtidos.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '9', section: 'Fase 9', item: 'Leitura sistemática e análise',
    desc: 'Ler sistematicamente o portfólio final na ordem do ranking e analisar os achados em relação à intenção de pesquisa.',
    essential: true, phase: 'a_posteriori',
  },
]

/* ═══════════════════════════════════════════════════════════════════════════
   NÚCLEO GENÉRICO — para revisões que não seguem uma diretriz catalogada.
   Reúne os requisitos comuns a praticamente todas as diretrizes de síntese de
   evidência: pergunta explícita, protocolo prévio, busca reproduzível, seleção
   auditável, extração padronizada e limitações declaradas.
   ═══════════════════════════════════════════════════════════════════════════ */

export const GENERIC_CHECKLIST: ProtocolChecklistItem[] = [
  {
    id: '1', section: 'Título e Resumo', item: 'Identificação do desenho',
    desc: 'Identificar no título e no resumo o tipo de síntese realizada e a diretriz metodológica adotada, se houver.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '2', section: 'Introdução', item: 'Justificativa e objetivos',
    desc: 'Descrever a justificativa da revisão e enunciar as perguntas de forma explícita e decomposta em elementos.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '3', section: 'Métodos', item: 'Protocolo prévio',
    desc: 'Declarar se houve protocolo definido antes da coleta, onde ele está acessível e quais emendas ocorreram.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '4', section: 'Métodos', item: 'Critérios de elegibilidade',
    desc: 'Especificar os critérios de inclusão e exclusão, com justificativa para recortes de idioma, período e tipo de documento.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '5', section: 'Métodos', item: 'Fontes e estratégia de busca',
    desc: 'Listar todas as fontes consultadas com data de acesso, e apresentar a estratégia completa de pelo menos uma delas, de modo reproduzível.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '6', section: 'Métodos', item: 'Processo de seleção',
    desc: 'Descrever as etapas de triagem, quantos revisores atuaram, se de forma independente, e como as divergências foram resolvidas.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '7', section: 'Métodos', item: 'Extração de dados',
    desc: 'Descrever o formulário de extração, as variáveis coletadas e os procedimentos de conferência.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '8', section: 'Métodos', item: 'Avaliação de qualidade',
    desc: 'Descrever se e como a qualidade metodológica ou o risco de viés dos estudos incluídos foi avaliado.',
    essential: false, phase: 'a_priori',
  },
  {
    id: '9', section: 'Métodos', item: 'Estratégia de síntese',
    desc: 'Descrever como os dados extraídos serão agrupados, comparados e sintetizados.',
    essential: true, phase: 'a_priori',
  },
  {
    id: '10', section: 'Resultados', item: 'Fluxo de seleção',
    desc: 'Apresentar o número de registros identificados, triados, avaliados e incluídos, com as razões das exclusões — idealmente em diagrama de fluxo.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '11', section: 'Resultados', item: 'Características dos estudos incluídos',
    desc: 'Citar cada estudo incluído e apresentar as características extraídas.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '12', section: 'Resultados', item: 'Síntese dos achados',
    desc: 'Apresentar os resultados sintetizados em relação a cada pergunta da revisão.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '13', section: 'Discussão', item: 'Interpretação',
    desc: 'Interpretar os achados no contexto da literatura existente, sem extrapolar além da evidência reunida.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '14', section: 'Discussão', item: 'Limitações',
    desc: 'Declarar as limitações da evidência incluída e do processo de revisão.',
    essential: true, phase: 'a_posteriori',
  },
  {
    id: '15', section: 'Outras informações', item: 'Financiamento, conflitos e dados',
    desc: 'Declarar fontes de financiamento, conflitos de interesse e onde os dados e materiais da revisão estão disponíveis.',
    essential: true, phase: 'a_posteriori',
  },
]
