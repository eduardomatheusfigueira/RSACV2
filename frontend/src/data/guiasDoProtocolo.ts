/**
 * RSAC V2 — Guias Estruturados do Estúdio de Protocolo
 *
 * Os guias que o Estúdio abre ao lado de cada campo — a estrutura esperada da
 * resposta e o modelo de texto inserível — eram 662 linhas de JSX espalhadas
 * pelos 18 cartões, 37% deles. Nada ali é marcação: é conteúdo metodológico,
 * do mesmo tipo que já vive em `protocolChecklists.ts`.
 *
 * Separar tem uma consequência prática além do tamanho do arquivo: revisar a
 * redação de um guia passa a ser abrir um módulo de texto, não caçar um bloco
 * de JSX no meio de 3000 linhas.
 *
 * O que NÃO entra aqui é o que depende da diretriz ativa em tempo de execução
 * — a referência ao item (`getFieldItemRef`) e os modelos que nomeiam a
 * diretriz. Esses continuam sendo montados na página, onde o
 * `currentProtocolDef` está disponível.
 */

export interface ItemDeGuia {
  /** Rótulo numerado da parte: "1. Panorama Geral". */
  tag: string
  /** O que se espera naquela parte, em uma frase. */
  desc: string
}

export interface ModeloDeTexto {
  /** Rótulo do botão: "Inserir Estrutura no Editor". */
  rotulo: string
  /** Pergunta de confirmação quando o campo já tem texto. */
  confirmacao: string
  /**
   * O texto em si. Função quando precisa nomear a diretriz ativa — foi assim
   * que os modelos deixaram de citar PRISMA-ScR sob CEE/ROSES (doc 25 § 6.7).
   */
  texto: string | ((ctx: ContextoDoModelo) => string)
}

export interface ContextoDoModelo {
  /** Nome completo da diretriz ativa. */
  diretriz: string
  /** Citação normativa da diretriz ativa. */
  referencia: string
  /** Framework de pergunta pressuposto pela diretriz (PCC, PICO, …). */
  framework: string
}

export interface GuiaEstruturado {
  /** Texto do botão que abre o guia: "Guia dos Achados (?)". */
  rotuloBotao: string
  /** `title` do botão, para quem passa o cursor. */
  tituloBotao: string
  /** Cabeçalho do guia aberto: "Estrutura da Síntese de Evidências". */
  titulo: string
  modelo?: ModeloDeTexto
  itens: ItemDeGuia[]
}

/** Chave do campo do manuscrito → guia correspondente. */
export const GUIAS_DO_PROTOCOLO: Record<string, GuiaEstruturado> = {
  manuscript_title: {
    rotuloBotao: 'Guia do Título (?)',
    tituloBotao: 'Ver guia de elaboração do título',
    titulo: 'Estrutura Recomendada para o Título',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir título atual pelo modelo?',
      texto: `Políticas Públicas de [Instrumento / Política] e [Conceito Central] no [Contexto Regional / Território] para [Atores Sociais / Setor Produtivo]: Uma Revisão de Escopo`,
    },
    itens: [
      { tag: '1. Identificação do Método', desc: 'O subtítulo DEVE conter explicitamente "Uma Revisão de Escopo" ou "Scoping Review".' },
      { tag: '2. Elementos PCC', desc: 'Mencione o Conceito Central (ex: Arranjos Produtivos Locais), o Contexto Territorial e os Atores Sociais.' },
    ],
  },
  protocol_registration: {
    rotuloBotao: 'Guia de Registro (?)',
    tituloBotao: 'Ver guia de registro do protocolo',
    titulo: 'Estrutura de Registro do Protocolo',
    modelo: {
      rotulo: 'Inserir Modelo no Editor',
      confirmacao: 'Substituir dados de registro pelo modelo?',
      texto: `O protocolo desta revisão foi desenvolvido a priori em conformidade com \${currentProtocolDef.name}, registrado na plataforma Open Science Framework (OSF) sob o DOI: https://doi.org/10.17605/OSF.IO/XXXXX em DD/MM/AAAA.`,
    },
    itens: [
      { tag: '1. Plataforma Pública', desc: 'OSF (Open Science Framework), Figshare, Zenodo ou periódicos de protocolo acadêmico.' },
      { tag: '2. DOI / URL Permanente', desc: 'Link direto e identificador persistente para verificação e transparência científica.' },
    ],
  },
  rationale: {
    rotuloBotao: 'Guia da Justificativa (?)',
    tituloBotao: 'Ver tópicos recomendados para a justificativa',
    titulo: 'Estrutura Recomendada para a Justificativa',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir justificativa pelo modelo estruturado?',
      texto: `Contexto e Estado da Arte:
[Apresente o panorama atual da literatura em Ciências Sociais Aplicadas / Desenvolvimento Regional e as dinâmicas recentes]

Problema de Pesquisa e Lacuna Identificada:
[Explique qual desafio persiste nas políticas públicas ou na governança e quais aspectos ainda carecem de síntese estruturada]

Justificativa da Abordagem de Scoping Review:
[Fundamente por que uma Scoping Review é o método indicado face à heterogeneidade dos estudos territoriais e organizacionais]

Relevância e Contribuição Esperada:
[Destaque a relevância acadêmica, institucional e social dos achados para apoiar tomadas de decisão e planejamento regional]`,
    },
    itens: [
      { tag: '1. Estado da Arte', desc: 'Panorama do que já se conhece na literatura sobre o território ou setor produtivo.' },
      { tag: '2. Lacuna Crítica', desc: 'Por que os estudos anteriores não responderam plenamente às demandas regionais.' },
      { tag: '3. Por que Scoping Review', desc: 'Necessidade de mapear a amplitude conceitual e heterogeneidade empírica.' },
      { tag: '4. Relevância Prática', desc: 'Apoio à formulação de políticas públicas e governança territorial.' },
    ],
  },
  criteria: {
    rotuloBotao: 'Guia dos Critérios (?)',
    tituloBotao: 'Ver guia de formulação dos critérios',
    titulo: 'Diretrizes de Critérios de Elegibilidade',
    itens: [
      { tag: 'Critérios de Inclusão (INC)', desc: 'Estudos empíricos ou teóricos que analisem políticas públicas, arranjos produtivos ou governança regional no contexto delimitado.' },
      { tag: 'Critérios de Exclusão (EXC)', desc: 'Artigos de opinião sem dados, resumos simples de anais, trabalhos fora do escopo geográfico/temático ou duplicados.' },
    ],
  },
  info_sources: {
    rotuloBotao: 'Guia das Fontes (?)',
    tituloBotao: 'Ver guia de reporte das fontes de informação',
    titulo: 'Estrutura de Fontes de Informação',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir fontes pelo modelo estruturado?',
      texto: `Bases Bibliográficas Consultadas:
Foram realizadas buscas sistemáticas nas bases de dados BDTD (Teses e Dissertações), SciELO, Scopus e OpenAlex.

Período Cronológico de Cobertura:
Publicações compreendidas entre 2015 e agosto de 2026.

Literatura Cinzenta e Busca Manual:
Consulta ao repositório de teses da BDTD, relatórios técnicos institucionais e varredura das listas de referências dos estudos incluídos.

Data de Execução da Busca Mais Recente:
A estratégia de busca eletrônica definitiva foi executada em DD/MM/AAAA.`,
    },
    itens: [
      { tag: '1. Bases Eletrônicas', desc: 'Nome de todas as bases pesquisadas (BDTD, SciELO, Scopus, OpenAlex, etc.).' },
      { tag: '2. Período de Cobertura', desc: 'Janela temporal de publicação dos trabalhos considerados.' },
      { tag: '3. Literatura Cinzenta', desc: 'Teses, dissertações, relatórios técnicos governamentais ou de institutos de pesquisa.' },
      { tag: '4. Data da Busca Mais Recente', desc: 'Data exata da última rodada de busca para aferir a atualidade da revisão.' },
    ],
  },
  selection_process: {
    rotuloBotao: 'Guia da Seleção (?)',
    tituloBotao: 'Ver guia do processo de seleção',
    titulo: 'Estrutura do Processo de Seleção',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir seleção pelo modelo estruturado?',
      texto: `Etapas da Triagem:
A seleção dos estudos foi conduzida no software RSAC V2 em duas fases: (1) avaliação inicial de títulos e resumos para exclusão de estudos fora do escopo temático/territorial; e (2) análise integral dos artigos pré-selecionados.

Exercício Piloto de Calibração:
Antes do início da triagem definitiva, realizou-se um teste piloto com uma amostra de 50 artigos entre os revisores para calibração e refinamento dos critérios de inclusão e exclusão.

Revisores e Resolução de Divergências:
A seleção foi realizada de forma independente por dois pesquisadores. Discrepâncias na decisão foram resolvidas por consenso; havendo persistência, um terceiro revisor sênior foi acionado para decisão final.`,
    },
    itens: [
      { tag: '1. Triagem em Duas Fases', desc: 'Fase 1 (Títulos/Resumos) e Fase 2 (Texto Completo).' },
      { tag: '2. Teste Piloto', desc: 'Amostra prévia de calibração entre os revisores.' },
      { tag: '3. Duplo-Cego / Independente', desc: 'Número de pesquisadores e mecanismo de resolução de conflitos.' },
    ],
  },
  data_charting_process: {
    rotuloBotao: 'Guia do Charting (?)',
    tituloBotao: 'Ver guia do processo de extração',
    titulo: 'Estrutura do Processo de Data Charting',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir processo de charting pelo modelo?',
      texto: `Formulário de Extração Padronizado:
A extração de dados foi realizada por meio de formulário padronizado no RSAC V2, pré-testado em 10 estudos pelos pesquisadores.

Procedimento de Preenchimento:
Dois revisores extraíram independentemente as informações metodológicas, atores envolvidos, instrumentos de política pública e resultados socioeconômicos observados.

Consolidação e Contato com Autores:
Os dados foram cruzados e eventuais omissões foram esclarecidas por contato direto com os autores correspondentes.`,
    },
    itens: [
      { tag: '1. Formulário Calibrado', desc: 'Instrumento estruturado pré-testado para extração uniforme.' },
      { tag: '2. Extração em Duplicata', desc: 'Conduzida de forma independente por pares de revisores.' },
    ],
  },
  critical_appraisal: {
    rotuloBotao: 'Guia da Avaliação Crítica (?)',
    tituloBotao: 'Ver orientação sobre avaliação crítica em scoping reviews',
    titulo: 'Orientações sobre Avaliação Crítica',
    modelo: {
      rotulo: 'Inserir Justificativa Padrão',
      confirmacao: 'Substituir justificativa de dispensa pelo modelo?',
      texto: `Em conformidade com \${currentProtocolDef.name} (\${currentProtocolDef.reference}), a avaliação formal de risco de viés e qualidade metodológica individual não foi realizada, tendo em vista que o objetivo central desta revisão é mapear abrangentemente a literatura existente, independentemente do desenho metodológico das pesquisas primárias.`,
    },
    itens: [
      { tag: 'Dispensa Padrão em Scoping Review', desc: 'Revisões de escopo buscam amplitude temática e mapeamento abrangente.' },
      { tag: 'Se for Avaliar', desc: 'Especifique os critérios de consistência metodológica adotados.' },
    ],
  },
  synthesis_methods: {
    rotuloBotao: 'Guia da Síntese (?)',
    tituloBotao: 'Ver guia de métodos de síntese',
    titulo: 'Estrutura de Métodos de Síntese',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir métodos de síntese pelo modelo?',
      texto: `Síntese Narrativa e Temática:
Os dados extraídos serão agrupados por eixos temáticos (ex: tipologia de governança, setor produtivo, instrumentos de fomento) alinhados ao framework \${currentProtocolDef.defaultFramework}.

Apresentação Tabular e Mapeamento:
Elaboração de tabelas descritivas detalhando autoria, ano, território/região de estudo, metodologia empregada e principais achados socioeconômicos.

Diagramas e Representações Visuais:
Geração de gráficos de distribuição cronológica e geográfica das pesquisas, acompanhados pelo fluxograma de seleção (identificação, triagem, elegibilidade e inclusão) que o RSAC gera na Exportação.

Matriz de Identificação de Lacunas (Gap Analysis):
Construção de matriz estruturada para apontar territórios e temas com carência de evidências empíricas.`,
    },
    itens: [
      { tag: '1. Síntese Narrativa', desc: 'Descrição qualitativa dos padrões conceituais e institucionais identificados.' },
      { tag: '2. Mapas Tabulares', desc: 'Tabelas consolidadas com características e recortes territoriais dos estudos.' },
      { tag: '3. Matriz de Lacunas', desc: 'Mapeamento visual de lacunas na literatura acadêmica.' },
    ],
  },
  funding: {
    rotuloBotao: 'Guia do Financiamento (?)',
    tituloBotao: 'Ver guia de financiamento e conflitos',
    titulo: 'Estrutura de Financiamento e Conflitos',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir financiamento pelo modelo estruturado?',
      texto: `Fontes de Financiamento:
O presente trabalho foi realizado com apoio da Coordenação de Aperfeiçoamento de Pessoal de Nível Superior - Brasil (CAPES) - Código de Financiamento 001, e do Conselho Nacional de Desenvolvimento Científico e Tecnológico (CNPq).

Papel dos Financiadores:
As entidades financiadoras não exerceram qualquer influência na formulação do protocolo, na busca, análise ou interpretação dos dados, na redação deste manuscrito ou na decisão de publicação.

Declaração de Conflitos de Interesse:
Os autores declaram expressamente a inexistência de quaisquer conflitos de interesse financeiros, profissionais ou institucionais.`,
    },
    itens: [
      { tag: '1. Agências de Fomento', desc: 'Nome das agências financiadoras e números de processo / bolsas acadêmicas.' },
      { tag: '2. Papel dos Financiadores', desc: 'Declaração de total independência dos autores na condução da pesquisa.' },
      { tag: '3. Conflitos de Interesse', desc: 'Declaração formal de inexistência de conflitos.' },
    ],
  },
  limitations: {
    rotuloBotao: 'Guia das Limitações (?)',
    tituloBotao: 'Ver guia de limitações',
    titulo: 'Estrutura de Limitações da Revisão',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir limitações pelo modelo estruturado?',
      texto: `Limitações do Processo de Busca:
A busca foi restrita a publicações em português, inglês e espanhol, o que pode ter desconsiderado estudos relevantes em outras línguas.

Literatura Cinzenta e Documentos Institucionais:
Embora teses e dissertações tenham sido consultadas na BDTD, relatórios técnicos municipais e documentos institucionais não indexados podem não ter sido integralmente capturados.

Heterogeneidade dos Estudos Primários:
A diversidade metodológica e conceitual na caracterização dos territórios limitou a comparabilidade direta entre determinadas realidades regionais.`,
    },
    itens: [
      { tag: '1. Limitações de Busca', desc: 'Filtros de idioma, bases consultadas e período considerado.' },
      { tag: '2. Literatura Cinzenta', desc: 'Potencial não captura de relatórios governamentais não indexados.' },
      { tag: '3. Desvios do Protocolo', desc: 'Justifique qualquer ajuste metodológico feito durante a revisão.' },
    ],
  },
  conclusions: {
    rotuloBotao: 'Guia das Conclusões (?)',
    tituloBotao: 'Ver guia de conclusões e lacunas',
    titulo: 'Estrutura de Conclusões e Lacunas',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir conclusões pelo modelo estruturado?',
      texto: `Conclusão Geral:
Esta scoping review sintetizou com rigor a produção científica sobre [Conceito Central / Desenvolvimento Regional], demonstrando que...

Principais Lacunas Identificadas:
Constatou-se escassez de pesquisas que avaliem a sustentabilidade financeira de longo prazo dos arranjos locais e a integração com políticas de inovação aberta.

Recomendações para Estudos Futuros:
Sugere-se que investigações futuras priorizem estudos longitudinais de governança territorial e análises comparadas entre diferentes recortes regionais.`,
    },
    itens: [
      { tag: '1. Síntese Conclusiva', desc: 'Resposta direta aos objetivos e questão norteadora.' },
      { tag: '2. Lacunas Mapeadas', desc: 'O que ainda falta na literatura para avanço do conhecimento na área.' },
      { tag: '3. Próximos Passos', desc: 'Recomendações objetivas para futuras pesquisas e políticas públicas.' },
    ],
  },
  structured_summary: {
    rotuloBotao: 'Guia do Resumo (?)',
    tituloBotao: 'Ver tópicos sugeridos e guia estruturado do resumo',
    titulo: 'Estrutura Recomendada para o Resumo',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir resumo pelo modelo estruturado?',
      texto: `Contexto / Introdução:
[Descreva o panorama socioeconômico, as dinâmicas territoriais e a relevância do desenvolvimento regional no tema abordado]

Objetivo:
[Defina a questão central e o objetivo do mapeamento conceitual com base no framework PCC]

Critérios de Elegibilidade:
[Atores sociais, políticas públicas/conceitos avaliados, contextos territoriais e tipos de estudo aceitos]

Fontes de Informação:
[Bases consultadas: BDTD, SciELO, Scopus, OpenAlex, literatura cinzenta institucional e data da busca]

Métodos de Charting (Extração):
[Extração em duplicata independente com formulário padronizado no RSAC V2]

Resultados Esperados:
[Mapeamento das abordagens metodológicas, instrumentos de política pública e principais lacunas identificadas]

Conclusões:
[Síntese das implicações para a formulação de políticas públicas e direções para pesquisas futuras]`,
    },
    itens: [
      { tag: '1. Contexto / Background', desc: 'Panorama do problema socioeconômico, institucional ou territorial abordado.' },
      { tag: '2. Objetivos / Objectives', desc: 'Questão norteadora e finalidade de mapear a extensão da literatura.' },
      { tag: '3. Critérios de Elegibilidade', desc: 'Atores, conceitos centrais, cenários territoriais e limites temporais/idiomáticos.' },
      { tag: '4. Fontes de Informação', desc: 'Bases consultadas (BDTD, SciELO, etc.) e data da execução da busca.' },
      { tag: '5. Métodos de Charting', desc: 'Extração dos dados em duplicata com instrumento padronizado.' },
      { tag: '6. Resultados Esperados', desc: 'Mapeamento das características e lacunas teóricas/empíricas identificadas.' },
      { tag: '7. Conclusões', desc: 'Contribuições para o desenvolvimento regional e políticas públicas.' },
    ],
  },
  summary_evidence: {
    rotuloBotao: 'Guia dos Achados (?)',
    tituloBotao: 'Ver guia de síntese das evidências',
    titulo: 'Estrutura da Síntese de Evidências',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir síntese de evidências pelo modelo?',
      texto: `Panorama das Evidências Mapeadas:
A síntese dos estudos incluídos evidenciou a evolução das pesquisas sobre [Conceito Central / Desenvolvimento Regional], concentrada principalmente em...

Temas Dominantes e Padrões Identificados:
Observou-se predominância de abordagens voltadas para..., com relativa escassez de análises longitudinais sobre sustentabilidade institucional dos arranjos territoriais.

Relevância Prática e Institucional:
Os resultados oferecem um panorama estruturado para gestores públicos, formuladores de políticas e pesquisadores sobre as potencialidades e desafios do desenvolvimento regional.`,
    },
    itens: [
      { tag: '1. Panorama Geral', desc: 'Volume e amplitude das evidências encontradas na literatura.' },
      { tag: '2. Temas Dominantes', desc: 'Principais tendências teóricas ou territoriais mapeadas.' },
      { tag: '3. Relevância Prática', desc: 'Utilidade para planejamento governamental e desenvolvimento local.' },
    ],
  },
}
