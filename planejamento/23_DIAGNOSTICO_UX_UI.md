# 23 — Diagnóstico de UX e UI

> Análise crítica da camada de interface do RSAC V2, medida contra o código e
> contra o aplicativo em execução em 17/08/2026.
>
> Todo número aqui foi contado, não estimado. Onde a avaliação é de julgamento
> — proporção, hierarquia, estética — está dito que é julgamento.

---

## 23.1 A tese

O RSAC V2 tem uma interface **competente e mal governada**.

Competente: as telas funcionam, a linguagem visual tem personalidade (o
neo-retrô de engenharia com cantos de 2 px é uma escolha real, não um tema
genérico), e as 13 paletas são bem construídas. Nada disso é acidente.

Mal governada: essa linguagem não está codificada em lugar nenhum que o código
seja obrigado a respeitar. Existe um arquivo de tokens — `globals.css`, 1.384
linhas — mas ele **descreve uma intenção que as telas não seguem**. Cada página
foi escrita resolvendo os próprios problemas de espaçamento, tipografia e
componente, e o resultado é que o design system existe como documento e não
como restrição.

O sintoma mais direto: **a escala tipográfica declarada não contém os tamanhos
que a aplicação mais usa**.

---

## 23.2 O buraco na fundação: componentes que nunca existiram

O doc 06 § 6.2 especificou 11 componentes comuns. O doc 12 § 1.3 os colocou na
Fase 1, antes de qualquer tela. Nenhum foi construído.

| Planejado (doc 06) | Existe? |
|---|:---:|
| `Button`, `Card`, `Badge`, `Input`, `Select`, `Modal`, `DataTable`, `ProgressBar`, `EmptyState`, `LoadingSpinner`, `SearchInput` | ⬜ nenhum |

O que existe em `components/common/` são dois componentes de domínio
(`AIAssistButton`, `DeduplicationReportModal`). **Todo o resto da interface é
markup direto com classes CSS por página.**

Isso não é uma questão de gosto arquitetural. É a causa mecânica de tudo o que
vem a seguir: sem um `<Button>`, não há onde impor a altura, o espaçamento
interno, o estado de foco e o estado desabilitado. Cada página reinventa, e as
reinvenções divergem.

**Consequências contadas:**

| Padrão | Ocorrências distintas |
|---|:---:|
| Classes de botão | **25** (`btn-secondary`, `btn-primary`, `tool-btn-vertical`, `btn-insert-template`, `btn-pdf-action`, `btn-study-step`, `btn-queue-scroll`, `btn-flow-nav`, …) |
| Classes de estado vazio | **11** (`empty-state`, `queue-empty-state`, `terminal-empty`, `log-empty`, `dashboard-empty`, `empty-abstract-state`, `empty-questions-card`, …) |
| Páginas que replicam `page-header` | **8 de 8** |
| Modais artesanais | **5**, nenhum com foco preso nem fechamento por `Escape` |

---

## 23.3 Os tokens não governam

### A escala tipográfica é ficção

`globals.css` declara 8 degraus, do `--text-xs` (0.75 rem) ao `--text-4xl`.
Medindo os `font-size` de todos os CSS exceto o próprio `globals.css`:

| | Ocorrências |
|---|:---:|
| Usam um token (`var(--text-*)`) | 126 |
| **Valor literal** | **184 — 59%** |

E os literais não são exceções pontuais. Os três mais frequentes são:

| Valor | Usos | Situação na escala |
|---|:---:|---|
| `0.6875rem` (11 px) | **76** | **abaixo do menor degrau declarado** |
| `0.625rem` (10 px) | **62** | **abaixo do menor degrau declarado** |
| `0.5625rem` (9 px) | **30** | **abaixo do menor degrau declarado** |

**168 usos de três tamanhos que a escala não reconhece.** A interface real é
consideravelmente mais densa do que o design system afirma ser. Não é o código
que está errado — a densidade alta é adequada a uma ferramenta de trabalho
prolongado. **É a escala que está desatualizada em relação ao produto.**

### A grade de 4 px é seguida pela metade

| | Ocorrências |
|---|:---:|
| `padding` / `margin` / `gap` com token | 305 |
| **Literal** | **309 — 50%** |

Os literais mais frequentes: `4px` (41), `6px` (24), `3px` (17), `2px` (17),
`5px` (16). Note que `4px` **é** `--space-1` — está sendo escrito à mão em vez
de referenciado. Já `6px`, `3px`, `5px` e `2px` não existem na grade de 4 px:
são degraus intermediários que a interface precisou e o sistema não ofereceu.

### As cores vazam do sistema

**143 cores literais fora de `globals.css`** — 63 hexadecimais e 80 `rgba()`,
descontados os comentários.

| Arquivo | Cores literais |
|---|:---:|
| `TopRibbonBar.css` | **38** |
| `ProtocolPage.css` | 20 |
| `Sidebar.css` | 16 |
| `ScreeningPage.css` | 12 |
| `StatusBar.css` | 10 |
| demais | 47 |

Cada cor literal é um ponto que **não acompanha as 13 paletas**. As etiquetas
de base acadêmica no ribbon (BDTD, SciELO, Scopus, PubMed, OpenAlex) são o caso
mais visível: são rosa, vermelho, laranja e roxo fixos, alheios a qualquer tema
— e destoam da paleta Organic Earth mesmo no tema padrão.

### O `z-index` não tem escala

Valores em uso: **2, 10, 50, 100, 1000, 1001, 1050, 1200**. Escolhidos um a um,
por tentativa. Não há como responder "esse dropdown fica acima ou abaixo do
painel de logs?" sem abrir os dois arquivos.

---

## 23.4 Proporção: o chrome come a tela

Medido com o aplicativo em execução, viewport de 1440 × 900 — a altura útil de
um notebook comum:

| Tela | Chrome | Cabeçalho | Abas | **Total antes do conteúdo** |
|---|:---:|:---:|:---:|:---:|
| **Protocolo** | 182 px | 84 px | 114 px | **380 px — 42%** |
| Triagem | 171 px | 51 px | — | 222 px — 25% |
| Coleta | 182 px | 51 px | — | 233 px — 26% |

**No Estúdio de Protocolo — a tela onde o pesquisador escreve — 42% da altura
da janela é moldura.** Sobram 520 px para o trabalho, e neles cabem cerca de
dois campos. Escrever um protocolo de 22 itens nessas condições significa
rolar constantemente com a mão fora do texto.

O empilhamento é: barra de título (34) → abas do ribbon (30) → toolstrip do
ribbon (118) → cabeçalho da página (84) → abas do estúdio (114) → banner de
fase (40). **Seis faixas horizontais antes do primeiro campo editável.**

---

## 23.5 Comando duplicado: o ribbon disputa com a página

O ribbon foi projetado para ser a superfície de comando. Mas as páginas
mantiveram as próprias barras de ação, e as duas convivem na mesma tela.

| Tela | Botões no ribbon | Botões no cabeçalho da página | Sobreposição |
|---|:---:|:---:|---|
| Protocolo | 10 | 4 | "Salvar Tudo", "Copiar Artigo", "Sugerir com Assistência" — **as três ações principais aparecem duas vezes** |
| Triagem | 11 | 4 | "Triagem em Lote com Assistência"; e os filtros Todos/Pendentes/Incluídos/Excluídos aparecem **duas vezes simultaneamente na mesma tela** |
| Coleta | 4 | 3 | "Iniciar Coleta" e "Desduplicar" |

O usuário não tem como saber qual é o comando canônico. Pior: os dois conjuntos
não compartilham estado — na Triagem, os botões "Incluir / Excluir / Pendente"
do ribbon ficam habilitados mesmo com zero estudos carregados.

---

## 23.6 O ribbon aciona a interface simulando cliques

Este é o achado mais grave do diagnóstico, e é de arquitetura, não de estética.

O `TopRibbonBar` não chama funções. Ele procura elementos no DOM e dispara
`.click()` — **34 pontos de acionamento**, através de três auxiliares:

```ts
const clickDomByText = (selector: string, text: string) => {
  const els = Array.from(document.querySelectorAll(selector)) as HTMLElement[]
  const el = els.find((e) => e.textContent?.includes(text))
  if (el) el.click()
}
```

E os chamadores casam por **texto visível em português**:

```ts
onClick={() => clickDomByText('button', 'Salvar Tudo')}
onClick={() => clickDomByText('button', 'Sugerir com Assistência')}
onClick={() => clickDomByIndex('.studio-tab', 3)}
```

Três consequências, todas em produção hoje:

1. **Renomear um rótulo quebra o ribbon.** Trocar "Salvar Tudo" por "Salvar"
   desliga o botão do ribbon, silenciosamente. Nenhum teste pega, nenhum tipo
   protege.
2. **A falha é muda.** `if (el) el.click()` — se o alvo não existe, está
   desabilitado ou está atrás de outra aba, nada acontece e o usuário não
   recebe retorno. O botão parece quebrado.
3. **É intraduzível e inacessível.** Qualquer internacionalização futura
   quebra os 34 pontos de uma vez. E como o acionamento não passa pelo estado
   da aplicação, não há como anunciar o resultado a um leitor de tela.

O `clickDomByIndex('.studio-tab', 3)` é ainda mais frágil: depende da **ordem**
dos elementos na página.

---

## 23.7 Acessibilidade: praticamente ausente

Varredura completa de `src/**/*.{tsx,css}`:

| Recurso | Ocorrências |
|---|:---:|
| `aria-label` | **1** (no monograma da marca) |
| `role=` | **2** (marca + um cartão do dashboard) |
| `aria-live` | **0** |
| `aria-expanded` | **0** |
| `aria-selected` | **0** |
| `aria-current` | **0** |
| regras `:focus-visible` | **1** |
| tratamento de `Escape` | **0** |
| `onClick` em `<div>`/`<span>` não focáveis | **15** |

O que isso significa na prática:

- **Duas UIs de abas** (as 8 abas do ribbon e as 7 do estúdio) são botões sem
  `role="tab"` nem `aria-selected`. Um leitor de tela não sabe qual está ativa.
- **Nada é anunciado.** Progresso de coleta, triagem em lote, "Salvo com
  sucesso" — todos silenciosos, porque `aria-live` não é usado em lugar nenhum.
- **O foco é invisível.** Uma única regra `:focus-visible` no aplicativo
  inteiro: navegar por teclado é navegar às cegas.
- **Modais não prendem foco nem fecham com `Escape`.** Cinco deles.

Há um contraponto justo: a Triagem tem atalhos reais (`I`/`E`/`P`, setas) e a
Extração tem navegação por setas. A intenção de produtividade por teclado
existe — ela só não foi generalizada nem tornada perceptível.

---

## 23.8 Conteúdo preso a uma diretriz

Com o projeto configurado em **CEE/ROSES**, o aplicativo em execução exibe:

- No corpo do formulário: *"Conforme PRISMA-ScR Item 1: Identifique
  claramente o trabalho como uma Scoping Review…"*
- No ribbon: *"Verifique o checklist PRISMA-ScR (22 itens)"* — quando a
  diretriz ativa tem 27
- Na faixa de visualização: *"DIAGRAMA ATIVO: Fluxograma PRISMA 2020"*, fixo

As etiquetas das abas do estúdio já foram corrigidas (passaram a vir do
catálogo em 17/08/2026), mas **os textos de ajuda e os rótulos "ITEM n —
ESSENCIAL" do corpo continuam presos ao PRISMA-ScR**. Num aplicativo cujo valor
é o rigor metodológico, exibir a numeração de outra diretriz é pior do que não
exibir número nenhum.

---

## 23.9 Higiene: peso morto

| Achado | Detalhe |
|---|---|
| **Sidebar é código morto** | `Sidebar.tsx` (157 linhas) + `Sidebar.css` (215 linhas) não são renderizados por ninguém. O `AppShell` monta `TopRibbonBar`. Recebeu manutenção na entrega da marca — trabalho investido em código inalcançável |
| **9 dependências nunca importadas** | os 6 pacotes `@radix-ui/*`, `@tanstack/react-table`, `recharts` e `sonner`. O README anuncia "Radix UI" e "Recharts" na stack; nenhum é usado |
| **Arquivos grandes demais** | `ProtocolPage.tsx` **2.979 linhas**; `ScreeningPage.tsx` 1.475; `SettingsPage.tsx` 1.342; `ExtractionPage.tsx` 1.191 |
| **Zero testes de interface** | 17 suítes no backend, **0** no frontend. `npm test` sai com erro por não achar arquivo nenhum |

Os 6 pacotes Radix merecem nota: eles resolveriam, prontos e acessíveis,
exatamente os problemas do § 23.7 — diálogo com foco preso, abas com
`aria-selected`, tooltip, select. Estão instalados desde o início e nunca foram
tocados.

---

## 23.10 Estética: o que está bom e não deve ser mexido

Um diagnóstico só de problemas induz a refazer o que está certo. Não é o caso.

- **A linguagem neo-retrô de engenharia é boa e é distintiva.** Cantos de 2 px,
  bevels sutis, etiquetas em versalete monoespaçado. Parece uma ferramenta
  profissional de trabalho, não um site. Preservar.
- **As 13 paletas são bem construídas** — relações de contraste coerentes,
  semânticas mapeadas por tema, decisões de triagem com cor própria.
- **A tela de Coleta é a mais bem composta do aplicativo**: duas colunas,
  passos numerados, progresso ao lado dos parâmetros. Serve de referência de
  layout para as demais.
- **O agrupamento do ribbon por propósito** (rótulo do grupo embaixo, padrão
  Office) é uma decisão acertada. O problema não é o ribbon existir — é ele
  duplicar a página e acionar por DOM.
- **A densidade alta é adequada** ao uso. O problema não é a interface ser
  densa; é a densidade não estar declarada em lugar nenhum.

---

## 23.11 Síntese dos achados

| # | Achado | Gravidade | Natureza |
|:-:|---|:---:|---|
| **A1** | Ribbon aciona a UI por `querySelector` + texto visível (34 pontos) | 🔴 | Arquitetura |
| **A2** | Sem biblioteca de componentes: 25 classes de botão, 11 de estado vazio, cabeçalho replicado 8× | 🔴 | Estrutura |
| **A3** | Acessibilidade ausente: 1 `aria-label`, 0 `aria-live`, 1 `:focus-visible`, 0 `Escape` | 🔴 | Inclusão |
| **A4** | Escala tipográfica não contém os 3 tamanhos mais usados (168 ocorrências) | 🟠 | Tokens |
| **A5** | Comando duplicado entre ribbon e página; filtros de triagem em duplicata na tela | 🟠 | Fluxo |
| **A6** | 42% da altura é moldura no Estúdio de Protocolo | 🟠 | Proporção |
| **A7** | 143 cores literais fora do sistema de temas | 🟠 | Tokens |
| **A8** | Textos de ajuda presos ao PRISMA-ScR sob outra diretriz | 🟠 | Correção metodológica |
| **A9** | 50% dos espaçamentos são literais; grade de 4 px sem degraus intermediários | 🟡 | Tokens |
| **A10** | `z-index` sem escala (8 valores ad hoc) | 🟡 | Tokens |
| **A11** | Sidebar é código morto (372 linhas) | 🟡 | Higiene |
| **A12** | 9 dependências declaradas e nunca importadas | 🟡 | Higiene |
| **A13** | 4 páginas acima de 1.000 linhas; `ProtocolPage` com 2.979 | 🟡 | Manutenção |
| **A14** | Zero cobertura de teste de interface | 🟡 | Qualidade |

O tratamento de cada achado está no **doc 25**; o alvo normativo contra o qual
o tratamento é medido está no **doc 24**.
