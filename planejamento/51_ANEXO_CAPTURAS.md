# Documento 51 · Anexo de Capturas e Textos Alternativos (A2)
## Registro de imagens geradas, dimensões, pesos e textos alternativos acessíveis

> As 6 capturas de tela foram extraídas deterministicamente do projeto fixture (`053ac293-f441-4807-8ccd-998318728be0`) sem qualquer dado pessoal identificado.
> Todas as imagens estão em formato WebP moderno em duas larguras (1280w e 640w), atendendo estritamente ao teto de 140 kB do critério P10 / G3.

---

## 1. Tabela de Dimensões e Orçamento de Bytes

| Identificador | Rota do App | Resolução 1280 | Peso 1280w | Resolução 640 | Peso 640w | Status Orçamento (≤140 kB) |
|---|---|---|---|---|---|---|
| `01-triagem` | `/projects/:id/screening` | 1280 × 800 | 85.4 kB | 640 × 400 | 26.2 kB | ✔ Aprovado |
| `02-protocolo` | `/projects/:id/protocol` | 1280 × 800 | 69.3 kB | 640 × 400 | 20.7 kB | ✔ Aprovado |
| `03-coleta` | `/projects/:id/harvest` | 1280 × 800 | 76.0 kB | 640 × 400 | 23.9 kB | ✔ Aprovado |
| `04-rastro` | `/projects/:id/screening` | 1280 × 645 | 61.9 kB | 640 × 323 | 19.6 kB | ✔ Aprovado |
| `05-extracao` | `/projects/:id/extraction` | 1280 × 800 | 69.8 kB | 640 × 400 | 21.8 kB | ✔ Aprovado |
| `06-exportacao` | `/projects/:id/export` | 1280 × 800 | 62.5 kB | 640 × 400 | 18.9 kB | ✔ Aprovado |

---

## 2. Textos Alternativos Descritivos (`alt`) e Legendas

### Print 1 · Triagem (Hero e Bloco 4)
- **Caminho:** `src/imagens/telas/01-triagem-1280.webp` e `src/imagens/telas/01-triagem-640.webp`
- **Largura/Altura (1280):** `width="1280" height="800"`
- **Texto `alt` acessível:**  
  `Interface de triagem do Revsist dividida em duas colunas: à esquerda, título, autores e resumo de um estudo científico com botões de decisão Incluído e Excluído; à direita, checklist interativo com quatro critérios de elegibilidade metodológica.`
- **Legenda (`<figcaption>`):**  
  `Ambiente de avaliação de títulos e resumos com metadados do estudo, checklist de critérios de inclusão e histórico do revisor.`

### Print 2 · Protocolo de Pesquisa (Bloco 1)
- **Caminho:** `src/imagens/telas/02-protocolo-1280.webp` e `src/imagens/telas/02-protocolo-640.webp`
- **Largura/Altura (1280):** `width="1280" height="800"`
- **Texto `alt` acessível:**  
  `Formulário de edição do protocolo de revisão com campos estruturados para objetivo, estratégia PICO, descritores de busca e lista de 11 diretrizes metodológicas selecionáveis.`
- **Legenda (`<figcaption>`):**  
  `Edição estruturada do protocolo com parâmetros conceituais, critérios de elegibilidade e versionamento formal.`

### Print 3 · Coleta Bibliográfica (Bloco 2 e 3)
- **Caminho:** `src/imagens/telas/03-coleta-1280.webp` e `src/imagens/telas/03-coleta-640.webp`
- **Largura/Altura (1280):** `width="1280" height="800"`
- **Texto `alt` acessível:**  
  `Painel de coleta federada exibindo campo para string de busca booleana e cartões de conexão simultânea com BDTD, SciELO, PubMed, Scopus e OpenAlex, indicando registros recuperados.`
- **Legenda (`<figcaption>`):**  
  `Busca federada em bases bibliográficas nacionais e internacionais com contagem de registros e controle de deduplicação.`

### Print 4 · Rastro e Auditoria da Decisão (Seção 2)
- **Caminho:** `src/imagens/telas/04-rastro-1280.webp` e `src/imagens/telas/04-rastro-640.webp`
- **Largura/Altura (1280):** `width="1280" height="645"`
- **Texto `alt` acessível:**  
  `Painel de auditoria metodológica evidenciando a decisão tomada pelo pesquisador, carimbo temporal, modelo de linguagem utilizado, parecer técnico emitido e hash SHA-256 do contexto analisado.`
- **Legenda (`<figcaption>`):**  
  `Registro auditável de proveniência de cada decisão de triagem, associando autor, parecer assistido e hash do texto.`

### Print 5 · Extração de Dados (Bloco 5)
- **Caminho:** `src/imagens/telas/05-extracao-1280.webp` e `src/imagens/telas/05-extracao-640.webp`
- **Largura/Altura (1280):** `width="1280" height="800"`
- **Texto `alt` acessível:**  
  `Tabela e formulário de extração estruturada de dados contendo perguntas metodológicas sobre desenho de estudo, instrumentos identificados e escala territorial, com campos de evidência textual preenchidos.`
- **Legenda (`<figcaption>`):**  
  `Formulário padronizado de extração com perguntas vinculadas ao protocolo e matriz de evidências por artigo.`

### Print 6 · Síntese e Exportação (Bloco 6)
- **Caminho:** `src/imagens/telas/06-exportacao-1280.webp` e `src/imagens/telas/06-exportacao-640.webp`
- **Largura/Altura (1280):** `width="1280" height="800"`
- **Texto `alt` acessível:**  
  `Visualização do fluxograma PRISMA oficial gerado a partir dos dados do projeto, acompanhado de botões para download do acervo nos formatos RIS, BibTeX, CSV e XLSX.`
- **Legenda (`<figcaption>`):**  
  `Fluxograma PRISMA gerado automaticamente do banco de dados e opções para exportação padronizada dos estudos.`
