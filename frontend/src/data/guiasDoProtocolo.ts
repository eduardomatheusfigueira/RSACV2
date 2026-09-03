/**
 * Revsist — Guias Estruturados do Estúdio de Protocolo
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
A seleção dos estudos foi conduzida no software Revsist em duas fases: (1) avaliação inicial de títulos e resumos para exclusão de estudos fora do escopo temático/territorial; e (2) análise integral dos artigos pré-selecionados.

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
A extração de dados foi realizada por meio de formulário padronizado no Revsist, pré-testado em 10 estudos pelos pesquisadores.

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
Geração de gráficos de distribuição cronológica e geográfica das pesquisas, acompanhados pelo fluxograma de seleção (identificação, triagem, elegibilidade e inclusão) que o Revsist gera na Exportação.

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
[Extração em duplicata independente com formulário padronizado no Revsist]

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

/**
 * Guias dos campos abertos pelo doc 45 — o Núcleo de Busca do modo Simplificado,
 * o desenho da revisão, a estratégia canônica e as emendas.
 *
 * Foram escritos depois dos 14 originais, e por um motivo específico: o modo
 * Simplificado nasceu sem nenhum botão de guia, o que contradizia o que o
 * Estúdio já entregava no modo Completo. Um campo sem guia é um campo em que o
 * pesquisador adivinha o que se espera dele — e adivinhar é exatamente o que um
 * protocolo existe para evitar.
 */
export const GUIAS_DO_NUCLEO: Record<string, GuiaEstruturado> = {
  objective: {
    rotuloBotao: 'Guia da Pergunta (?)',
    tituloBotao: 'Ver guia de formulação da pergunta e do objetivo',
    titulo: 'Estrutura da Pergunta e do Objetivo',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir a pergunta e o objetivo pelo modelo estruturado?',
      texto: (ctx) => `Pergunta de Pesquisa:
Quais [conceito central] estão documentados na literatura sobre [população/fenômeno] em [contexto territorial e temporal]?

Objetivo Geral:
Mapear e sintetizar, conforme ${ctx.diretriz}, a produção científica que trata de [tema], identificando [o que se pretende caracterizar].

Objetivos Específicos:
(a) caracterizar a distribuição temporal, geográfica e institucional dos estudos;
(b) identificar as abordagens teóricas e metodológicas predominantes;
(c) apontar as lacunas que orientam a agenda futura de pesquisa.`,
    },
    itens: [
      { tag: '1. Pergunta única e respondível', desc: 'Uma pergunta central, não uma lista de temas. Se não for possível respondê-la com os estudos que a busca trará, ela ainda é ampla demais.' },
      { tag: '2. Alinhada ao desenho', desc: 'Pergunta aberta de mapeamento pede revisão de escopo; pergunta fechada de efeito pede revisão sistemática. A pergunta é que escolhe o desenho, não o contrário.' },
      { tag: '3. Objetivo no infinitivo', desc: 'Mapear, caracterizar, comparar, estimar — o verbo declara o que a revisão entrega.' },
      { tag: '4. Recorte explícito', desc: 'Território, período e população entram já na pergunta; é o que a torna verificável.' },
    ],
  },

  question_framework: {
    rotuloBotao: 'Guia do Framework (?)',
    tituloBotao: 'Ver guia de decomposição estruturada da pergunta',
    titulo: 'Como decompor a pergunta em componentes',
    itens: [
      { tag: 'PCC — escopo', desc: 'População, Conceito, Contexto. É o framework do JBI para revisões de escopo: não pede comparador nem desfecho, porque a revisão mapeia em vez de medir.' },
      { tag: 'PICO / PICOS — efetividade', desc: 'População, Intervenção, Comparação, Desfecho (e Desenho do estudo, quando ele próprio é critério de elegibilidade).' },
      { tag: 'PECO — observacional', desc: 'Troca Intervenção por Exposição. É o formato de perguntas ambientais, epidemiológicas e de política pública em que ninguém "aplicou" nada.' },
      { tag: 'SPIDER — qualitativa', desc: 'Sample, Phenomenon of Interest, Design, Evaluation, Research type. Fala em amostra, e não em população, porque a síntese qualitativa não busca representatividade.' },
      { tag: 'CIMO — gestão e políticas', desc: 'Contexto, Intervenção, Mecanismo, Desfecho. Responde "o que funciona, para quem, em que circunstâncias e por quê".' },
      { tag: 'Para que serve preencher', desc: 'Cada componente vira um bloco de conceito da estratégia de busca. É esta ligação que impede a busca de nascer desalinhada da pergunta.' },
    ],
  },

  review_design: {
    rotuloBotao: 'Guia dos Desenhos (?)',
    tituloBotao: 'Ver como escolher o desenho da revisão',
    titulo: 'Como escolher o desenho da revisão',
    itens: [
      { tag: '1. Sua pergunta é fechada?', desc: 'Não → revisão de escopo (mapear o que existe) ou mapa sistemático (catalogar sem sintetizar). Sim → siga adiante.' },
      { tag: '2. A unidade de análise', desc: 'Se você vai ler revisões sistemáticas em vez de estudos primários, o desenho é revisão de revisões (umbrella), com AMSTAR 2 e tratamento da sobreposição.' },
      { tag: '3. O que você quer produzir', desc: 'Estimativa de efeito → metanálise. Compreensão de experiências → síntese qualitativa. Frequência ou associação → revisão de prevalência. Mapa da estrutura do campo → estudo bibliométrico.' },
      { tag: '4. O que o desenho arrasta', desc: 'A escolha define o framework sugerido, a diretriz de relato, se a apreciação crítica é obrigatória e se a revisão é elegível a registro no PROSPERO.' },
      { tag: '5. Pode mudar depois', desc: 'Trocar o desenho não apaga nada do que já foi preenchido — mas, se a busca já rodou, a mudança é uma emenda e pede justificativa registrada.' },
    ],
  },

  search_strategy: {
    rotuloBotao: 'Guia da Estratégia (?)',
    tituloBotao: 'Ver guia de construção da estratégia de busca',
    titulo: 'Anatomia de uma estratégia reproduzível',
    itens: [
      { tag: '1. Um bloco por conceito', desc: 'Cada bloco corresponde a um componente da pergunta. Dois conceitos no mesmo bloco tornam a busca imprecisa; um conceito partido em dois blocos a torna estreita demais.' },
      { tag: '2. Sinônimos unidos por OR', desc: 'Dentro do bloco entram variantes, plurais, sinônimos e traduções. Esquecer um sinônimo é a causa mais comum de perda de estudos relevantes.' },
      { tag: '3. Blocos unidos por AND', desc: 'A combinação entre blocos é o que estreita o resultado. Comece por dois blocos; um terceiro só se o volume exigir.' },
      { tag: '4. Expressões entre aspas', desc: 'Termos compostos precisam de aspas para não serem quebrados pela base ("arranjo produtivo local").' },
      { tag: '5. Adaptação por base é declarada', desc: 'Cada base recebe a tradução do seu adaptador. Quando a base não aceita booleana completa, a decomposição é registrada — e vai para o Registro de Busca como nota de adaptação.' },
      { tag: '6. Revise antes de executar', desc: 'A revisão PRESS confere tradução da pergunta, operadores, termos de assunto, termos livres, sintaxe e limites.' },
    ],
  },

  search_filters: {
    rotuloBotao: 'Guia do Recorte (?)',
    tituloBotao: 'Ver guia de bases-alvo e limites da busca',
    titulo: 'Bases-alvo e limites do recorte',
    itens: [
      { tag: '1. Justifique as bases', desc: 'A escolha das bases precisa de razão declarada — cobertura temática, cobertura regional, acesso institucional. É item do PRISMA-S, e é o que separa uma busca desenhada de uma busca conveniente.' },
      { tag: '2. Combine cobertura', desc: 'Bases internacionais (Scopus, OpenAlex) e nacionais (SciELO, BDTD) cobrem literaturas diferentes. Em Ciências Sociais Aplicadas, deixar as nacionais de fora costuma ser perda real.' },
      { tag: '3. Todo limite exclui', desc: 'Ano, idioma e tipo documental cortam resultados. Cada corte precisa de razão metodológica — nunca "para reduzir o volume".' },
      { tag: '4. Restrição de idioma tem custo', desc: 'Limitar a português e inglês introduz viés de idioma, e isso deve ser declarado nas limitações.' },
      { tag: '5. Literatura cinzenta', desc: 'Teses, dissertações e relatórios técnicos entram pelo campo de métodos complementares, não pelos filtros das bases.' },
    ],
  },

  extraction_questions: {
    rotuloBotao: 'Guia da Extração (?)',
    tituloBotao: 'Ver guia de formulação das perguntas de extração',
    titulo: 'O que perguntar a cada estudo incluído',
    itens: [
      { tag: '1. Decidido antes da busca', desc: 'Listar a priori as variáveis para as quais se buscará dado é exigência das diretrizes de protocolo. Definir depois de ver os resultados é o viés que o protocolo existe para impedir.' },
      { tag: '2. Uma variável por pergunta', desc: 'Perguntas compostas produzem respostas que não se tabulam. Separe "qual o método" de "qual a amostra".' },
      { tag: '3. Blocos usuais', desc: 'Identificação (autoria, ano, país), método (desenho, amostra, instrumento), conteúdo (conceitos, marco teórico), resultados (achados, limitações declaradas).' },
      { tag: '4. Tipo de resposta orienta a síntese', desc: 'Categórica e numérica tabulam e viram gráfico; texto livre alimenta a síntese narrativa. Escolher o tipo agora poupa retrabalho na análise.' },
      { tag: '5. Comece pelo conjunto sugerido', desc: 'Cada desenho traz um conjunto inicial coerente com o que aquele tipo de revisão precisa relatar. Ajuste em vez de partir do zero.' },
    ],
  },

  deduplication: {
    rotuloBotao: 'Guia da Deduplicação (?)',
    tituloBotao: 'Ver guia de relato da deduplicação',
    titulo: 'Como relatar a deduplicação',
    modelo: {
      rotulo: 'Inserir Estrutura no Editor',
      confirmacao: 'Substituir o texto de deduplicação pelo modelo?',
      texto: `Procedimento de Deduplicação:
Os registros recuperados nas bases foram reunidos e deduplicados automaticamente pelo Revsist, por correspondência exata de DOI e por similaridade de título normalizado.

Conferência Manual:
Os pares sinalizados como prováveis duplicatas foram conferidos manualmente antes da remoção.

Registro Quantitativo:
Foram identificados N registros; após a remoção de D duplicatas, restaram N-D registros únicos submetidos à triagem por título e resumo.`,
    },
    itens: [
      { tag: '1. Método declarado', desc: 'Automática, manual ou combinada — e por qual chave (DOI, título normalizado, autoria e ano).' },
      { tag: '2. Números registrados', desc: 'Quantos registros entraram, quantas duplicatas saíram e quantos seguiram para a triagem. São os números do topo do fluxograma PRISMA.' },
      { tag: '3. Conferência', desc: 'Deduplicação automática sem conferência descarta estudos legítimos. Declare se houve verificação humana.' },
    ],
  },

  amendment_reason: {
    rotuloBotao: 'Guia da Emenda (?)',
    tituloBotao: 'Ver guia de justificativa de emenda ao protocolo',
    titulo: 'Como justificar uma emenda',
    itens: [
      { tag: '1. O que mudou', desc: 'Nomeie o campo alterado e o valor anterior. "Ampliamos o recorte" não é registro; "recorte inicial 2015–2026 ampliado para 2012–2026" é.' },
      { tag: '2. Por que mudou', desc: 'A razão metodológica, não a operacional. "Marcos regulatórios anteriores a 2015 foram identificados na busca-piloto" justifica; "vieram poucos resultados" não.' },
      { tag: '3. Quando mudou', desc: 'A fase do projeto importa: emenda no planejamento é ajuste; emenda depois da triagem exige explicar por que não compromete a seleção já feita.' },
      { tag: '4. O efeito sobre o já feito', desc: 'Diga se a mudança obriga a repetir a busca, a reavaliar estudos já triados, ou nenhum dos dois.' },
      { tag: '5. Para que serve', desc: 'É esta justificativa que responde, na revisão por pares, se os critérios mudaram depois de ver os resultados.' },
    ],
  },

  registro_execucao: {
    rotuloBotao: 'Guia do Registro (?)',
    tituloBotao: 'Ver o que o sistema registra da execução da busca',
    titulo: 'O que a execução registra, e por que importa',
    itens: [
      { tag: '1. Por que é automático', desc: 'Data, hora e contagem por base são fatos da execução, não decisões do pesquisador. Digitá-los à mão abriria espaço para divergência entre o que foi relatado e o que aconteceu.' },
      { tag: '2. Data e hora de cada busca', desc: 'Bases mudam diariamente. Sem o momento exato da execução, ninguém consegue reproduzir o conjunto de registros recuperado — e a revisão deixa de ser reproduzível por construção.' },
      { tag: '3. Registros por base', desc: 'Quantos vieram de cada base, antes e depois da deduplicação. São os números do topo do fluxograma, e é o que permite mostrar a contribuição de cada fonte.' },
      { tag: '4. Vai para o Registro de Busca', desc: 'Estes campos formam a coluna "executado" do documento exportável, ao lado da coluna "configurado" — o confronto entre o que foi planejado e o que de fato rodou.' },
      { tag: '5. Enquanto está vazio', desc: 'Nada foi coletado ainda. Os campos se preenchem sozinhos no primeiro disparo da coleta, base a base.' },
    ],
  },
}

/**
 * Registro único consultado pelo Estúdio. Mantém `GUIAS_DO_PROTOCOLO` como
 * estava — os 14 campos do manuscrito — e acrescenta os do Núcleo de Busca, sem
 * obrigar quem consulta a saber em qual dos dois mapas procurar.
 */
export const GUIAS: Record<string, GuiaEstruturado> = {
  ...GUIAS_DO_PROTOCOLO,
  ...GUIAS_DO_NUCLEO,
}
