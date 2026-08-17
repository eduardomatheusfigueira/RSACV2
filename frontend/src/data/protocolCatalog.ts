/**
 * RSAC V2 — Catálogo de Diretrizes Metodológicas
 * ==============================================
 *
 * Descreve, para cada metodologia aceita pelo backend, o que a interface
 * precisa saber: como chamá-la, que framework de pergunta ela pressupõe e qual
 * lista de verificação usar na auditoria do protocolo.
 *
 * As chaves são exatamente os valores de `Methodology` (frontend/src/types/api.ts),
 * que por sua vez espelham `backend/app/domain/enums.py`. O tipo `Record` abaixo
 * é deliberado: se alguém acrescentar uma metodologia ao enum sem cadastrar a
 * diretriz aqui, o TypeScript acusa em tempo de compilação, em vez de a tela
 * quebrar em produção.
 *
 * REAPROVEITAMENTO DE LISTAS
 * --------------------------
 * Cochrane, Campbell e JBI não publicam um instrumento de RELATO próprio: elas
 * publicam padrões de CONDUÇÃO (MECIR, MECCIR, JBI Manual) e exigem que o
 * relato siga o PRISMA. Por isso essas entradas apontam para a lista PRISMA
 * correspondente, em vez de manter uma cópia paralela que divergiria com o
 * tempo. O que é específico de cada corpo — os padrões de condução — está
 * descrito em `description` e citado em `reference`.
 *
 * `defaultFramework` alimenta o seletor de framework do Estúdio de Protocolo:
 * 'PCC' para revisões de escopo (População, Conceito, Contexto) e 'PICO' para
 * as demais (ver ProtocolPage.handleChangeMethodology).
 */

import type { Methodology } from '@/types/api'
import {
  EBSE_CHECKLIST,
  GENERIC_CHECKLIST,
  METHODI_ORDINATIO_CHECKLIST,
  PRISMA_2020_CHECKLIST,
  PRISMA_P_CHECKLIST,
  PRISMA_SCR_CHECKLIST,
  ROSES_CHECKLIST,
  UMBRELLA_CHECKLIST,
  type ProtocolChecklistItem,
} from './protocolChecklists'

export type { ProtocolChecklistItem } from './protocolChecklists'

/**
 * As seções de redação do Estúdio de Protocolo. Espelha `StudioTab`
 * (ProtocolPage.tsx) sem a aba 'checklist', que audita as demais em vez de ser
 * uma seção do manuscrito. Declarado aqui, e não importado de ProtocolPage,
 * para não criar dependência circular entre a página e os seus dados.
 */
export type ProtocolSectionKey =
  | 'ident_intro'
  | 'objectives'
  | 'search_eligibility'
  | 'methods_extraction'
  | 'synthesis_discussion'
  | 'final_summary'

export interface ProtocolDefinition {
  /** Nome completo, exibido nos seletores. */
  name: string
  /** Rótulo curto para abas e botões, onde não cabe o nome completo. */
  shortLabel: string
  /** Sigla exibida como etiqueta ao lado do título. */
  badge: string
  /** O que a diretriz é e para que serve — exibido na pré-visualização. */
  description: string
  /** Em que campo e para que tipo de pergunta a diretriz é adequada. */
  domainFocus: string
  /** Citação do documento normativo, para o pesquisador conferir a fonte. */
  reference: string
  /** Framework de estruturação da pergunta pressuposto pela diretriz. */
  defaultFramework: 'PCC' | 'PICO' | 'PICOS' | 'PECO' | 'SPIDER' | 'SPICE'
  /** Título da matriz de auditoria. */
  checklistTitle: string
  /** Itens da matriz de auditoria. */
  checklistItems: ProtocolChecklistItem[]
  /**
   * Quais itens da diretriz cada seção do estúdio cobre — exibido na etiqueta
   * de cada aba. A correspondência é específica de cada diretriz, então uma
   * seção sem entrada aqui simplesmente não mostra etiqueta: as seções do
   * estúdio têm formato PRISMA, e forçar um mapeamento para diretrizes de
   * outro formato (EBSE, Methodi Ordinatio) exibiria número errado.
   */
  sectionItems?: Partial<Record<ProtocolSectionKey, string>>
}

export const PROTOCOL_CATALOG: Record<Methodology, ProtocolDefinition> = {
  'PRISMA-ScR': {
    name: 'PRISMA-ScR — Revisão de Escopo (Scoping Review)',
    shortLabel: 'PRISMA-ScR',
    badge: 'PRISMA-ScR',
    description:
      'Extensão do PRISMA para revisões de escopo. Mapeia a extensão, a natureza e as lacunas de um corpo de literatura, sem pretender medir a força da evidência — por isso a avaliação crítica dos estudos é opcional.',
    domainFocus:
      'Perguntas amplas e exploratórias: o que já se produziu sobre um tema, com que conceitos e em que contextos.',
    reference:
      'Tricco AC, Lillie E, Zarin W, et al. Ann Intern Med. 2018;169(7):467-473',
    defaultFramework: 'PCC',
    checklistTitle: 'Auditoria de Conformidade PRISMA-ScR (22 itens)',
    checklistItems: PRISMA_SCR_CHECKLIST,
    sectionItems: {
      ident_intro: '1, 5, 3',
      objectives: '4',
      search_eligibility: '6-8',
      methods_extraction: '9-13, 17',
      synthesis_discussion: '14-16',
      final_summary: '2',
    },
  },

  'PRISMA-2020': {
    name: 'PRISMA 2020 — Revisão Sistemática & Meta-análise',
    shortLabel: 'PRISMA 2020',
    badge: 'PRISMA 2020',
    description:
      'Diretriz de relato para revisões sistemáticas, com ou sem meta-análise. Exige pergunta fechada, avaliação de risco de viés e avaliação da certeza do corpo de evidência.',
    domainFocus:
      'Perguntas fechadas de efeito, prevalência ou associação, com desfechos definidos a priori.',
    reference: 'Page MJ, McKenzie JE, Bossuyt PM, et al. BMJ. 2021;372:n71',
    defaultFramework: 'PICO',
    checklistTitle: 'Auditoria de Conformidade PRISMA 2020 (27 itens)',
    checklistItems: PRISMA_2020_CHECKLIST,
    sectionItems: {
      ident_intro: '1, 3, 24a-24b',
      objectives: '4',
      search_eligibility: '5-7',
      methods_extraction: '8-15',
      synthesis_discussion: '16a-23d',
      final_summary: '2',
    },
  },

  'PRISMA-P': {
    name: 'PRISMA-P — Protocolo de Revisão Sistemática',
    shortLabel: 'PRISMA-P',
    badge: 'PRISMA-P',
    description:
      'Diretriz de relato do PROTOCOLO, não da revisão concluída. Cobre o que precisa estar decidido e registrado antes de a busca começar; o relato da revisão em si segue depois o PRISMA 2020.',
    domainFocus:
      'Fase de planejamento e registro prospectivo (PROSPERO, OSF) de qualquer revisão sistemática.',
    reference: 'Moher D, Shamseer L, Clarke M, et al. Syst Rev. 2015;4:1',
    defaultFramework: 'PICO',
    checklistTitle: 'Auditoria de Conformidade PRISMA-P (17 itens)',
    checklistItems: PRISMA_P_CHECKLIST,
    sectionItems: {
      ident_intro: '1a-5c, 6',
      objectives: '7',
      search_eligibility: '8-10',
      methods_extraction: '11a-17',
    },
  },

  Cochrane: {
    name: 'Cochrane — Revisão de Intervenções (Handbook & MECIR)',
    shortLabel: 'Cochrane',
    badge: 'COCHRANE',
    description:
      'Padrão ouro em síntese de intervenções. A condução segue os padrões MECIR e o Cochrane Handbook — protocolo registrado, busca sensível com apoio de bibliotecário, dupla triagem e extração independentes, risco de viés por RoB 2 e certeza por GRADE. O RELATO segue o PRISMA 2020, reproduzido na matriz ao lado.',
    domainFocus:
      'Efetividade e segurança de intervenções em saúde, com ensaios clínicos randomizados como desenho preferencial.',
    reference:
      'Higgins JPT, Thomas J, Chandler J, et al. (eds). Cochrane Handbook for Systematic Reviews of Interventions, v6.5, 2024 · MECIR — Methodological Expectations of Cochrane Intervention Reviews · relato conforme PRISMA 2020 (BMJ. 2021;372:n71)',
    defaultFramework: 'PICO',
    checklistTitle: 'Auditoria de Conformidade Cochrane — relato PRISMA 2020 (27 itens)',
    checklistItems: PRISMA_2020_CHECKLIST,
    sectionItems: {
      ident_intro: '1, 3, 24a-24b',
      objectives: '4',
      search_eligibility: '5-7',
      methods_extraction: '8-15',
      synthesis_discussion: '16a-23d',
      final_summary: '2',
    },
  },

  'JBI (Scoping/Systematic)': {
    name: 'JBI — Joanna Briggs Institute (Escopo / Sistemática)',
    shortLabel: 'JBI',
    badge: 'JBI',
    description:
      'Metodologia do Joanna Briggs Institute, com forte tradição em evidências qualitativas e mistas. Para revisões de ESCOPO, o JBI coassina e adota o PRISMA-ScR, reproduzido na matriz ao lado; a condução acrescenta os instrumentos de apreciação crítica do JBI e o fluxo SUMARI. Para revisões SISTEMÁTICAS de efetividade, use a entrada PRISMA 2020.',
    domainFocus:
      'Metassíntese qualitativa, evidências mistas, viabilidade, adequação e significado de práticas (framework PCC ou PICo).',
    reference:
      'Aromataris E, Lockwood C, Porritt K, Pilla B, Jordan Z (eds). JBI Manual for Evidence Synthesis. JBI, 2024 · relato de escopo conforme PRISMA-ScR (Ann Intern Med. 2018;169(7):467-473)',
    defaultFramework: 'PCC',
    checklistTitle: 'Auditoria de Conformidade JBI — relato PRISMA-ScR (22 itens)',
    checklistItems: PRISMA_SCR_CHECKLIST,
    sectionItems: {
      ident_intro: '1, 5, 3',
      objectives: '4',
      search_eligibility: '6-8',
      methods_extraction: '9-13, 17',
      synthesis_discussion: '14-16',
      final_summary: '2',
    },
  },

  Campbell: {
    name: 'Campbell Collaboration — Políticas Sociais',
    shortLabel: 'Campbell',
    badge: 'CAMPBELL',
    description:
      'Síntese de evidências em políticas sociais, educação, justiça criminal, economia e desenvolvimento internacional. A condução segue o MECCIR — a adaptação Campbell do MECIR — que exige protocolo revisado por pares, busca extensiva em literatura cinzenta e tratamento explícito de equidade. O RELATO segue o PRISMA 2020, reproduzido na matriz ao lado.',
    domainFocus:
      'Efeitos de programas e políticas sociais sobre populações e territórios, frequentemente com desenhos quase-experimentais.',
    reference:
      'Campbell Collaboration. MECCIR — Methodological Expectations of Campbell Collaboration Intervention Reviews · Campbell Systematic Reviews policies · relato conforme PRISMA 2020 (BMJ. 2021;372:n71)',
    defaultFramework: 'PICO',
    checklistTitle: 'Auditoria de Conformidade Campbell — relato PRISMA 2020 (27 itens)',
    checklistItems: PRISMA_2020_CHECKLIST,
    sectionItems: {
      ident_intro: '1, 3, 24a-24b',
      objectives: '4',
      search_eligibility: '5-7',
      methods_extraction: '8-15',
      synthesis_discussion: '16a-23d',
      final_summary: '2',
    },
  },

  'CEE/ROSES': {
    name: 'CEE / ROSES — Evidências Socioambientais',
    shortLabel: 'ROSES',
    badge: 'CEE/ROSES',
    description:
      'Padrão da Collaboration for Environmental Evidence para revisões e mapas sistemáticos em gestão ambiental. O ROSES é um formulário por seções que dá peso especial à abrangência da busca (incluindo literatura cinzenta e sites de organizações) e ao envolvimento de partes interessadas na formulação da pergunta.',
    domainFocus:
      'Intervenções e impactos socioambientais, gestão de recursos naturais, sustentabilidade e políticas territoriais (PICO ou PECO).',
    reference:
      'Haddaway NR, Macura B, Whaley P, Pullin AS. Environ Evid. 2018;7:7 · CEE Guidelines and Standards for Evidence Synthesis in Environmental Management, v5.1',
    defaultFramework: 'PICO',
    checklistTitle: 'Auditoria de Conformidade ROSES (27 itens por domínio)',
    checklistItems: ROSES_CHECKLIST,
    sectionItems: {
      ident_intro: '1, 3, 4, 6',
      objectives: '5',
      search_eligibility: '7-14',
      methods_extraction: '15-18',
      synthesis_discussion: '19-26',
      final_summary: '2',
    },
  },

  EBSE: {
    name: 'EBSE — Engenharia de Software Baseada em Evidência',
    shortLabel: 'EBSE',
    badge: 'EBSE',
    description:
      'Guia de Kitchenham & Charters para revisões sistemáticas em engenharia de software, organizado em três fases — planejamento, condução e relato. É a referência dominante em computação e sistemas de informação.',
    domainFocus:
      'Comparação de tecnologias, métodos, ferramentas e práticas de engenharia de software e computação aplicada.',
    reference:
      'Kitchenham B, Charters S. Guidelines for performing Systematic Literature Reviews in Software Engineering. EBSE Technical Report EBSE-2007-01. Keele University & University of Durham, 2007',
    defaultFramework: 'PICOS',
    checklistTitle: 'Auditoria de Conformidade EBSE (13 passos em 3 fases)',
    checklistItems: EBSE_CHECKLIST,
  },

  'Umbrella Review': {
    name: 'Revisão Guarda-Chuva (Umbrella Review / PRIOR)',
    shortLabel: 'Guarda-Chuva',
    badge: 'UMBRELLA',
    description:
      'Síntese cujas unidades de análise são REVISÕES SISTEMÁTICAS, e não estudos primários. Traz dois problemas que não existem numa revisão comum e que a matriz cobre explicitamente: a sobreposição de estudos primários entre as revisões incluídas e a avaliação da qualidade metodológica dessas revisões (AMSTAR-2 ou ROBIS).',
    domainFocus:
      'Temas já cobertos por múltiplas revisões sistemáticas, quando o objetivo é comparar e reconciliar os achados delas.',
    reference:
      'Gates M, Gates A, Pieper D, et al. PRIOR statement. BMJ. 2022;378:e070849 · JBI Manual for Evidence Synthesis, cap. Umbrella Reviews',
    defaultFramework: 'PICO',
    checklistTitle: 'Auditoria de Conformidade PRIOR (27 itens por domínio)',
    checklistItems: UMBRELLA_CHECKLIST,
    sectionItems: {
      ident_intro: '1, 3, 25',
      objectives: '4',
      search_eligibility: '5-7',
      methods_extraction: '8-15',
      synthesis_discussion: '16-24',
      final_summary: '2',
    },
  },

  'Methodi Ordinatio': {
    name: 'Methodi Ordinatio — Portfólio Bibliográfico Ordenado',
    shortLabel: 'Methodi Ordinatio',
    badge: 'ORDINATIO',
    description:
      'Método brasileiro de seleção e ORDENAÇÃO de artigos por relevância científica, em nove fases. A equação InOrdinatio combina fator de impacto, ano de publicação e número de citações para hierarquizar o portfólio final. Não é uma diretriz de relato: produz o portfólio que será lido, e costuma ser combinado com PRISMA para o relato.',
    domainFocus:
      'Construção de referencial teórico e portfólio bibliográfico em engenharia de produção, gestão e áreas correlatas.',
    reference:
      'Pagani RN, Kovaleski JL, Resende LM. Scientometrics. 2015;105(3):2109-2135',
    defaultFramework: 'PICO',
    checklistTitle: 'Auditoria de Conformidade Methodi Ordinatio (9 fases)',
    checklistItems: METHODI_ORDINATIO_CHECKLIST,
  },

  Other: {
    name: 'Outra / Personalizada',
    shortLabel: 'Personalizada',
    badge: 'CUSTOM',
    description:
      'Para revisões que não seguem uma diretriz catalogada. A matriz reúne os requisitos comuns a praticamente todas as diretrizes de síntese de evidência — pergunta explícita, protocolo prévio, busca reproduzível, seleção auditável, extração padronizada e limitações declaradas.',
    domainFocus:
      'Desenhos híbridos, revisões narrativas estruturadas e sínteses que combinam diretrizes de mais de um campo.',
    reference:
      'Núcleo comum às diretrizes de síntese de evidência. Declare no manuscrito qual diretriz foi efetivamente seguida.',
    defaultFramework: 'PICO',
    checklistTitle: 'Auditoria de Requisitos Metodológicos Essenciais (15 itens)',
    checklistItems: GENERIC_CHECKLIST,
  },
}

/**
 * Ordem de apresentação nos seletores. Segue a frequência de uso esperada no
 * público-alvo do RSAC (Ciências Sociais Aplicadas e Desenvolvimento Regional):
 * as extensões PRISMA primeiro, depois os corpos metodológicos por campo, e
 * "Outra" por último.
 */
export const PROTOCOL_OPTIONS: Methodology[] = [
  'PRISMA-ScR',
  'PRISMA-2020',
  'PRISMA-P',
  'JBI (Scoping/Systematic)',
  'Cochrane',
  'Campbell',
  'CEE/ROSES',
  'EBSE',
  'Umbrella Review',
  'Methodi Ordinatio',
  'Other',
]
