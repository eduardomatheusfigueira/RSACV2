# 24 — Especificação do Design System

> Documento **normativo**. Define o alvo contra o qual o plano de execução
> (doc 25) é medido e a validação (doc 26) é escrita.
>
> Princípio que organiza tudo o que segue: **o sistema descreve o produto que
> existe, e depois passa a governá-lo.** O erro do design system anterior foi
> declarar uma intenção que as telas não seguiam. A escala tipográfica aqui
> parte dos tamanhos que a aplicação de fato usa (doc 23 § 23.3), não dos que
> seria bonito usar.

---

## 24.1 Os cinco princípios

1. **Densidade é uma decisão, não um descuido.** O RSAC é uma ferramenta de
   trabalho prolongado, usada em telas de notebook, com muita informação
   simultânea. A interface é densa de propósito. O que o sistema exige é que a
   densidade seja **declarada e uniforme**, não improvisada por página.

2. **Nenhum pigmento fora do sistema.** Zero cor literal fora de
   `globals.css`. Toda cor é token, e todo token existe nas 13 paletas. Uma
   cor literal é um pedaço da interface que não tem tema.

3. **Um componente por padrão, uma vez.** Se dois lugares precisam de um
   botão, existe um `<Button>`. A classe CSS por página é a exceção
   justificada, não o padrão.

4. **O comando tem dono único.** Cada ação do aplicativo é invocável por um
   caminho canônico, tipado. Superfícies de comando (ribbon, cabeçalho,
   atalho) despacham para esse caminho — nunca para o DOM.

5. **O que a vista mostra, o teclado alcança e o leitor de tela anuncia.**
   Não como fase final de polimento: como requisito de aceite de cada
   componente.

---

## 24.2 Grade e espaçamento

Grade base de **4 px**, com degraus intermediários de 2 px nas três primeiras
posições — porque a interface real precisou deles 50 vezes (doc 23 § 23.3) e
inventá-los à mão é justamente o que se quer eliminar.

| Token | Valor | Uso canônico |
|---|:---:|---|
| `--space-0` | 0 | zerar |
| `--space-px` | 1 px | filetes, ajuste óptico de 1 px |
| `--space-0-5` | 2 px | respiro interno de etiqueta |
| `--space-1` | 4 px | respiro entre ícone e rótulo |
| `--space-1-5` | 6 px | respiro interno de controle compacto |
| `--space-2` | 8 px | respiro interno padrão na horizontal |
| `--space-3` | 12 px | separação entre controles irmãos |
| `--space-4` | 16 px | respiro interno de cartão |
| `--space-5` | 20 px | separação entre blocos |
| `--space-6` | 24 px | separação entre seções |
| `--space-8` | 32 px | separação entre regiões |
| `--space-10`, `--space-12`, `--space-16` | 40 / 48 / 64 px | folgas de página e estados vazios |

**Regra**: `padding`, `margin` e `gap` só aceitam token. `5px` e `3px` deixam
de existir — arredondam para o degrau vizinho.

---

## 24.3 Tipografia

A escala é **reescrita a partir do uso real**. Os três tamanhos abaixo do
antigo mínimo respondem por 168 ocorrências e passam a ser cidadãos de primeira
classe, com nome e propósito.

| Token | rem | px | Propósito |
|---|:---:|:---:|---|
| `--text-2xs` | 0.5625 | 9 | etiqueta em versalete, contador em pílula |
| `--text-xs` | 0.625 | 10 | rótulo de grupo, metadado, legenda |
| `--text-sm` | 0.6875 | **11** | **tamanho de trabalho da interface** — controles, abas, células |
| `--text-base` | 0.8125 | 13 | corpo de leitura curta, descrição de item |
| `--text-md` | 0.9375 | 15 | corpo de leitura longa (campos do manuscrito) |
| `--text-lg` | 1.0625 | 17 | título de página |
| `--text-xl` | 1.1875 | 19 | título de seção destacada |
| `--text-2xl` | 1.5 | 24 | número em destaque, métrica |
| `--text-3xl` | 1.875 | 30 | título de estado vazio, splash |

> **Mudança de referencial**: `--text-sm` (11 px) é o tamanho **padrão** da
> interface, não uma redução. O antigo `--text-base` de 15 px passa a ser
> `--text-md` e fica reservado à leitura longa. Renomear é mais seguro do que
> redefinir: o `codemod` da Fase 1 (doc 25) faz a tradução de uma vez.

**Pesos**: 400 corpo · 500 rótulo · 600 ênfase · 700 título e etiqueta.
Abaixo de 11 px, **nunca** usar peso 400 — a haste desaparece nos temas
escuros.

**Famílias**: `--font-sans` (Inter) para prosa; `--font-mono` (JetBrains Mono)
para identificadores, versões, contadores, etiquetas em versalete e a marca.
A regra prática: **se o valor é lido, é sans; se é conferido, é mono.**

**Altura de linha**: 1.25 títulos · 1.45 interface · 1.6 prosa longa.

---

## 24.4 Alturas de controle e ritmo vertical

Três alturas apenas. Cada uma tem um lugar; não há quarta.

| Nome | Altura | Onde |
|---|:---:|---|
| `sm` | 24 px | dentro de linha de tabela, etiqueta acionável, filtro |
| `md` | 28 px | **padrão** — cabeçalho de página, barras de ferramenta, formulários |
| `lg` | 36 px | ação primária de diálogo e de estado vazio |

Os botões verticais do ribbon (ícone sobre rótulo) são a exceção declarada:
**56 px** para o grupo grande, **44 px** para o compacto.

**Orçamento vertical de moldura** — requisito de aceite, medido a 1440 × 900:

| Região | Máximo |
|---|:---:|
| Barra de título | 32 px |
| Abas do ribbon | 30 px |
| Toolstrip do ribbon | 96 px (recolhível, estado lembrado) |
| Cabeçalho da página | 44 px |
| Barra de status | 26 px |
| **Total de moldura** | **≤ 228 px — 25% de 900 px** |

Hoje o Estúdio de Protocolo usa 380 px (42%). O alvo de ≤ 25% em **todas** as
telas é o critério objetivo da Fase 3.

---

## 24.5 Cor

### Regra dura

**Zero cor literal fora de `globals.css`.** Verificado por script (doc 26).
Toda cor nova entra como token e é definida nas 13 paletas.

### Tokens que faltam e precisam existir

O vazamento de 143 cores não é indisciplina: é falta de token. O sistema
precisa ganhar:

| Token novo | Para quê |
|---|---|
| `--color-chrome-bg`, `--color-chrome-text`, `--color-chrome-border` | superfícies escuras de aplicação (ribbon, sidebar, splash) — hoje escritas como `var(--black-forest)` + `rgba()` literais |
| `--color-chrome-hover`, `--color-chrome-active` | estados sobre o chrome — hoje `rgba(255,255,255,0.07)` fixo |
| `--color-source-*` (uma por base acadêmica) | etiquetas BDTD / SciELO / Scopus / PubMed / OpenAlex, hoje em cores de marca fixas que ignoram o tema |
| `--color-overlay` | véu de modal — hoje `rgba(0,0,0,…)` variando por arquivo |
| `--rsac-accent` | já existe, vindo da identidade visual — generalizar para todo chrome |

### Contraste

Mínimo **4.5:1** para texto abaixo de 13 px e **3:1** para texto de 13 px ou
maior e para bordas de controle — em **todas as 13 paletas**. Não é aspiração:
é o que o verificador do doc 26 mede.

---

## 24.6 Forma: raio, borda, elevação

**Raio** — os cantos de 2 px são identidade e ficam. Só existem quatro valores:

| Token | Valor | Uso |
|---|:---:|---|
| `--radius-xs` | 1 px | etiquetas e pílulas |
| `--radius-sm` | 2 px | **padrão** — botões, campos, cartões |
| `--radius-md` | 3 px | contêineres de agrupamento |
| `--radius-lg` | 4 px | diálogos |

Sem `50%`: um elemento redondo é um ponto de estado (`--dot`), não um botão.

**Elevação** — quatro níveis, e cada um significa uma distância do plano, não
uma intensidade de sombra escolhida no olho: `--elevation-flat` (no plano),
`--elevation-raised` (controle acionável), `--elevation-overlay` (dropdown,
tooltip), `--elevation-dialog` (modal).

**Escala de `z-index`** — nomeada, com folga de 100 entre camadas:

| Token | Valor | Camada |
|---|:---:|---|
| `--z-base` | 0 | conteúdo |
| `--z-sticky` | 100 | cabeçalhos fixos dentro de painéis |
| `--z-chrome` | 200 | ribbon, barra de status |
| `--z-drawer` | 300 | painel de logs |
| `--z-overlay` | 400 | dropdown, popover, tooltip |
| `--z-dialog` | 500 | modal e seu véu |
| `--z-toast` | 600 | notificações |
| `--z-splash` | 700 | splash de inicialização |

---

## 24.7 Biblioteca de componentes

Mínimo para desmontar as 25 classes de botão e as 11 de estado vazio.
Cada componente só é considerado pronto com **os cinco estados** (repouso,
foco visível, hover, ativo, desabilitado) e com o comportamento de teclado.

### Primitivos

| Componente | Substitui | Notas |
|---|---|---|
| `<Button>` | 25 classes de botão | `variant`: primary · secondary · ghost · danger. `size`: sm · md · lg. `icon`, `loading`, `disabled` |
| `<IconButton>` | `btn-icon` e derivados | `label` **obrigatório** → vira `aria-label` |
| `<Tag>` | `db-badge`, `tab-pill`, `*-badge` | `tone`: neutral · accent · success · warning · danger · info |
| `<Field>` | 35 `<label>` soltos | Associa `label`/`htmlFor`, texto de ajuda e erro via `aria-describedby` |
| `<TextInput>`, `<TextArea>`, `<Select>` | campos por página | Altura e foco do sistema |
| `<Card>` | `neo-card` e variantes | `header`, `footer`, `tone` |
| `<Panel>` | contêineres de coluna | Cabeçalho com título e ações |

### Composições

| Componente | Substitui | Notas |
|---|---|---|
| `<PageHeader>` | replicação em 8 páginas | Título, subtítulo, voltar, ações. **Fonte única da altura de 44 px** |
| `<Toolbar>` / `<ToolbarGroup>` | grupos do ribbon | Rótulo do grupo embaixo (padrão Office, preservado) |
| `<Tabs>` | 2 UIs de aba artesanais | `role="tablist"`, `aria-selected`, navegação por setas — **usar `@radix-ui/react-tabs`, já instalado** |
| `<Modal>` | 5 modais artesanais | Foco preso, `Escape` fecha, foco devolvido ao gatilho — **usar `@radix-ui/react-dialog`** |
| `<EmptyState>` | 11 classes distintas | Ícone, título, explicação, ação primária |
| `<StatusView>` | espalhado | Um componente para carregando · vazio · erro · sem permissão |
| `<Tooltip>` | `title=` nativo | **`@radix-ui/react-tooltip`** — o `title` nativo é lento e invisível ao teclado |
| `<Metric>` | contadores do dashboard e das barras | Valor, rótulo, tendência |

> **Decisão sobre Radix**: os 6 pacotes estão instalados desde o início e nunca
> foram importados (doc 23 § 23.9). Eles resolvem, prontos e acessíveis,
> exatamente diálogo, abas, select, tooltip e menu. **Adotar** — e remover o
> que sobrar sem uso.

---

## 24.8 Movimento

Movimento serve para explicar uma mudança de estado. Movimento decorativo não
entra.

| Token | Duração | Uso |
|---|:---:|---|
| `--motion-instant` | 80 ms | realimentação de toque (hover, active) |
| `--motion-fast` | 140 ms | abrir/fechar de elemento pequeno |
| `--motion-base` | 200 ms | transição de painel, troca de aba |
| `--motion-slow` | 320 ms | entrada de diálogo, splash |

Curva única: `cubic-bezier(0.2, 0, 0.2, 1)`. Saídas usam metade da duração de
entrada.

**`prefers-reduced-motion: reduce` desliga toda translação e escala**, mantendo
apenas opacidade. Já respeitado na splash; passa a ser regra global.

---

## 24.9 Padrões de fluxo

### Uma ação, um dono

Cada comando existe uma vez, num **registro tipado**. Superfícies despacham
para ele:

```ts
type CommandId = 'protocol.saveAll' | 'protocol.copyManuscript' | …

interface Command {
  id: CommandId
  label: string          // rótulo é dado, não seletor
  shortcut?: string
  enabled: boolean       // estado real, não presunção
  run(): void | Promise<void>
}
```

A página registra os comandos que sabe executar; o ribbon **lê o registro** e
desenha o que existe. Um comando ausente ou desabilitado aparece desabilitado —
nunca como botão que não faz nada.

Isso encerra, de uma vez, os três problemas do § 23.6: rótulo deixa de ser
seletor, falha deixa de ser muda, e o acionamento passa a ser anunciável.

### Hierarquia de comando

| Superfície | O que abriga |
|---|---|
| **Ribbon** | Comandos da etapa: os que valem para a tela inteira |
| **Cabeçalho da página** | **Somente** a ação primária da tela — no máximo uma, mais o voltar |
| **Contexto** | Ações de um item específico, junto do item |
| **Teclado** | Espelha o ribbon; atalho declarado no comando e exibido no tooltip |

Consequência direta: **os filtros de triagem saem do ribbon** (pertencem à
lista) e as ações duplicadas saem do cabeçalho.

### Estados canônicos

Toda região que carrega dados declara os quatro: **carregando** (esqueleto com
a forma do conteúdo, não spinner centralizado), **vazio** (`<EmptyState>` com
saída), **erro** (o que falhou, em português, e o que fazer), **conteúdo**.

### Retorno de ação

| Situação | Retorno |
|---|---|
| Ação instantânea bem-sucedida | Estado do próprio elemento (ex.: campo salvo) |
| Ação demorada | Progresso no lugar da ação, com cancelamento |
| Sucesso que sai da vista | Toast (`sonner`, já instalado) + `aria-live="polite"` |
| Erro | Junto da causa; nunca só no console |

---

## 24.10 Acessibilidade — critérios de aceite

Não é fase; é condição de pronto de cada componente.

| # | Critério |
|:-:|---|
| A-1 | Todo controle acionável é `<button>` ou `<a>`. Zero `onClick` em `<div>`/`<span>` |
| A-2 | `:focus-visible` visível em **todos** os controles, em **todas** as 13 paletas |
| A-3 | Ordem de tabulação segue a ordem visual; sem armadilha de foco fora de diálogo |
| A-4 | Diálogos prendem o foco, fecham com `Escape` e devolvem o foco ao gatilho |
| A-5 | Abas usam `role="tab"` / `aria-selected` e navegam por setas |
| A-6 | Progresso e confirmações anunciados por `aria-live="polite"`; erros por `assertive` |
| A-7 | Todo botão só de ícone tem `aria-label` |
| A-8 | Todo campo tem `<label>` associado; ajuda e erro por `aria-describedby` |
| A-9 | Contraste conforme § 24.5, verificado nas 13 paletas |
| A-10 | Cor nunca é o único portador de significado (decisões de triagem levam ícone) |

---

## 24.11 Regras de arquitetura da interface

| # | Regra |
|:-:|---|
| R-1 | Nenhuma cor literal fora de `globals.css` |
| R-2 | Nenhum `font-size`, `padding`, `margin`, `gap`, `border-radius` ou `z-index` literal fora de `globals.css` |
| R-3 | Nenhum `document.querySelector` para acionar interface |
| R-4 | Página não define classe para padrão que a biblioteca já resolve |
| R-5 | Componente de página com mais de ~400 linhas se decompõe em seções |
| R-6 | Dependência declarada e não importada é removida |
| R-7 | Texto de diretriz metodológica vem do catálogo, nunca fixo no JSX |

As regras R-1, R-2, R-3 e R-6 são verificáveis por script e entram na
validação (doc 26).
