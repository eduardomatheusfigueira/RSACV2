# 26 — Testes e Validação — UX e UI

> Como verificar que o plano do doc 25 chegou ao alvo do doc 24, e como impedir
> que o resultado se degrade depois.
>
> O frontend tem hoje **zero** arquivo de teste (doc 23 § 23.9) — `npm test`
> sai com erro por não achar nada. Este documento é também a primeira suíte de
> interface do projeto.

---

## 26.1 Princípio

Cada regra do doc 24 é escrita de modo a ser **verificável por máquina** ou
**verificável por roteiro**. Regra que depende de alguém "lembrar de olhar" não
sobrevive a três sprints.

A validação tem quatro camadas, da mais barata para a mais cara:

| Camada | O que pega | Custo | Quando roda |
|---|---|:---:|---|
| **1 · Verificador de tokens** | Violação de R-1, R-2, R-3, R-6, R-7 | milissegundos | a cada commit |
| **2 · Comparação visual** | Regressão não intencional de layout e cor | segundos | a cada PR |
| **3 · Auditoria automatizada** | Violação de acessibilidade e contraste | segundos | a cada PR |
| **4 · Roteiros manuais** | Fluxo, proporção, julgamento estético | minutos | a cada fase |

---

## 26.2 Camada 1 — Verificador de tokens

`scripts/lint-design-tokens.mjs`. Sem dependência externa: percorre
`frontend/src/**/*.{css,tsx}` e aplica as regras do doc 24 § 24.11.

| Regra | O que procura | Isento |
|:-:|---|---|
| **R-1** | `#rgb`, `#rrggbb`, `rgb()`, `rgba()`, `hsl()` em CSS | `styles/globals.css` |
| **R-2** | `font-size`, `padding`, `margin`, `gap`, `border-radius`, `z-index` com literal | `globals.css`; `0`; `100%`; `auto` |
| **R-3** | `document.querySelector` seguido de `.click()` em `.tsx` | — |
| **R-6** | Dependência em `package.json` sem nenhuma importação | `devDependencies` de build |
| **R-7** | `PRISMA`, `ScR`, `Cochrane`, `ROSES` literais em JSX | `src/data/protocol*` |

**Saída**: caminho, linha e o token sugerido, quando houver um óbvio.

**Modo de adoção** — o ponto que faz a diferença entre uma regra viva e uma
regra desligada:

```
--report   imprime e sai com 0   (durante a fase que ainda está migrando)
--strict   imprime e sai com 1   (a partir do commit que zera a categoria)
```

Cada categoria vira `--strict` **individualmente**, no commit que zera a última
violação dela. Regra que quebra o build sem caminho de saída é regra que vai
ser desligada por quem estiver com pressa.

**Baseline a bater** (medido em 17/08/2026, doc 23):

| Categoria | Diagnóstico | Hoje | Teto no verificador |
|---|:---:|:---:|:---:|
| Cores literais | 143 | **0** | 0 · fechada |
| `font-size` literais | 184 | **0** | 0 · fechada |
| `border-radius` literais | 21 | **0** | 0 · fechada |
| `z-index` ad hoc | 8 | **0** | 0 · fechada |
| Acionamento por DOM | 34 | **0** | 0 · fechada |
| Espaçamentos literais | 309 | **0** | 0 · fechada |
| Diretriz fixa em texto visível | — | 5 | 5 · dívida travada |
| Dependências não importadas | 9 | 9 | Fase 7 |

Implementado em `frontend/scripts/lint-design-tokens.mjs`, exposto por
`npm run lint:tokens`; `npm run verify` encadeia com o `tsc`.

> **Achado do próprio verificador.** Além dos literais, ele detecta token
> referenciado sem fallback que não existe em lugar nenhum. Eram **6
> declarações mortas** — `--color-bg-base`, `--transition-normal`,
> `--color-border-hover`, `--color-accent-bg`, `--weight-normal` — que não
> pintavam nada havia meses e ninguém tinha percebido.

> **Lição sobre escrever a própria regra.** As três primeiras versões dos
> padrões de `font-size`, `z-index` e `border-radius` acusavam 326 violações
> onde havia 189: o lookahead `(?!var\()` tem buraco de backtracking — o `\s*`
> recua para zero e a asserção passa no espaço. As regras passaram a **capturar
> o valor e testá-lo em código**. Verificador que dá falso positivo é
> verificador que alguém desliga.

---

## 26.3 Camada 2 — Comparação visual

Playwright com o Chromium já presente no ambiente.

### Matriz de captura

**8 telas × 13 paletas = 104 imagens** por execução, a 1440 × 900.

| Telas | Paletas |
|---|---|
| Dashboard, Projetos, Protocolo, Coleta, Triagem, Extração, Exportação, Configurações | as 13 de `COLOR_THEMES` |

Mais **3 estados por tela** onde couber: vazio, carregado, erro.

### Fixture determinística

Comparação visual só funciona com dados estáveis. Antes da suíte, um script
semeia o banco com um projeto fixo: título, metodologia, 12 estudos com
decisões conhecidas, 3 com extração preenchida. Sem isso, cada execução
compara ruído.

### Referência antes de começar

> ⚠️ **As imagens de referência são tiradas ANTES da Fase 1.** É o único
> momento em que elas registram o estado que se quer preservar. Depois do
> primeiro codemod, a referência já contém o que se queria detectar.

### Fluxo

1. `npm run visual:baseline` — grava a referência (só na primeira vez e após
   mudança aprovada).
2. `npm run visual:check` — captura e compara pixel a pixel, com tolerância de
   0,1% para antialiasing.
3. Diferença acima da tolerância gera imagem de diff e falha o PR.
4. Mudança intencional se aprova regravando a referência **no mesmo commit** da
   mudança — assim o diff da referência fica revisável junto com o código.

---

## 26.4 Camada 3 — Auditoria automatizada

### Acessibilidade

`axe-core` injetado pelo Playwright nas 8 telas, em 2 paletas representativas
(uma clara, uma escura).

**Critério de aceite**: zero violação `critical` ou `serious`. Violações
`moderate` viram registro, não bloqueio.

### Contraste nas 13 paletas

O `axe` só mede o que está renderizado. Um verificador próprio lê os tokens de
`globals.css` e calcula a razão de contraste de cada par que o doc 24 § 24.5
exige, **nas 13 paletas** — inclusive combinações que nenhuma tela produz hoje
mas que um componente pode produzir amanhã.

| Par | Mínimo |
|---|:---:|
| `--color-text-primary` × `--color-bg-primary` / `-secondary` / `-tertiary` | 4.5:1 |
| `--color-text-secondary` × os mesmos fundos | 4.5:1 |
| `--color-text-sidebar` × `--color-bg-sidebar` | 4.5:1 |
| `--color-accent` × fundos de conteúdo | 3:1 |
| `--rsac-accent` × `--black-forest` | 3:1 |
| `--color-included` / `-excluded` / `-pending` × seus fundos | 4.5:1 |
| `--color-border` × `--color-bg-secondary` | 3:1 |

> Esse verificador teria pego, sozinho, o problema real encontrado na entrega
> da identidade visual: em `platinum-dusk`, `--color-accent` e `--black-forest`
> são a mesma cor (`#274c77`), e o cabo da lupa desapareceria no chrome.

### Orçamento de proporção

Roda com o app em execução e mede as regiões contra o doc 24 § 24.4:

```
moldura = titlebar + abas + toolstrip + cabeçalho + barra de status
falha se moldura / altura da janela > 0.25
```

Baseline: Protocolo **42%**, Triagem 25%, Coleta 26%. Alvo: ≤ 25% em todas.

---

## 26.5 Camada 4 — Roteiros manuais

O que máquina não julga.

### R1 · Percurso completo só com teclado

Sem tocar no mouse, do início ao fim:

1. Criar projeto, escolher diretriz, salvar
2. Abrir protocolo, percorrer as 6 seções, preencher 2 campos, salvar
3. Ir à Coleta, alternar bases, iniciar e cancelar
4. Ir à Triagem, navegar a fila, decidir 3 estudos com `I`/`E`/`P`
5. Abrir e fechar um modal — conferir que `Escape` fecha e o foco volta ao gatilho
6. Ir à Exportação, baixar planilha
7. Abrir Configurações, trocar de paleta

**Reprovação**: qualquer ponto em que o foco some, fique preso ou seja
invisível.

### R2 · Varredura por paleta

Com um projeto povoado, percorrer as 8 telas nas 13 paletas procurando o que a
comparação de imagem não sabe julgar: elemento que sumiu no fundo, ícone sem
contraste, etiqueta ilegível, cor que carrega significado sozinha.

### R3 · Densidade em tela pequena

A 1366 × 768 — o notebook institucional típico — conferir que cada tela ainda
mostra trabalho útil sem rolagem horizontal e que a moldura continua dentro do
orçamento.

### R4 · Integridade dos comandos (a partir da Fase 4)

1. Para cada botão do ribbon, acionar e confirmar que **algo observável
   acontece**.
2. Renomear um rótulo de botão da página e confirmar que o comando do ribbon
   **continua funcionando** — a prova direta de que o acionamento por DOM
   morreu.
3. Confirmar que comando sem alvo aparece **desabilitado**, não inerte.

### R5 · Consistência metodológica (a partir da Fase 6)

Para cada uma das 11 metodologias: ativar e percorrer Protocolo, Triagem e
Exportação conferindo que **nenhum texto cita outra diretriz**. É o roteiro que
pega o achado A8.

---

## 26.6 Testes de componente

Com a biblioteca da Fase 2, Vitest + Testing Library. Não é cobertura por
cobertura: cada teste ancora um critério do doc 24 § 24.10.

| Componente | O que o teste garante |
|---|---|
| `<Button>` | `disabled` não dispara `onClick`; `loading` não dispara duas vezes; renderiza `<button>` |
| `<IconButton>` | Sem `label` falha em tempo de tipo; com `label` gera `aria-label` |
| `<Modal>` | `Escape` fecha; foco vai ao primeiro elemento; foco volta ao gatilho; `Tab` circula dentro |
| `<Tabs>` | Setas navegam; `aria-selected` só na ativa |
| `<Field>` | `label` associado por `htmlFor`; ajuda e erro por `aria-describedby` |
| `<EmptyState>` | Renderiza ação quando informada; não renderiza contêiner vazio |
| `<StatusView>` | Os quatro estados são mutuamente exclusivos |
| Registro de comandos | Comando desregistra ao desmontar; duplicado substitui; `enabled` reflete o estado da página |

**Meta**: cada componente da biblioteca com pelo menos um teste de
comportamento e um de acessibilidade. **Não** perseguir percentual de cobertura
nas páginas — ali o valor está na comparação visual e nos roteiros.

---

## 26.7 Scripts a criar

| Script | Comando | Camada |
|---|---|:---:|
| `lint-design-tokens.mjs` | `npm run lint:tokens` | 1 |
| `seed-fixture.mjs` | `npm run test:seed` | 2 |
| `visual-baseline.mjs` | `npm run visual:baseline` | 2 |
| `visual-check.mjs` | `npm run visual:check` | 2 |
| `a11y-audit.mjs` | `npm run test:a11y` | 3 |
| `contrast-check.mjs` | `npm run test:contrast` | 3 |
| `layout-budget.mjs` | `npm run test:layout` | 3 |

Agregador: `npm run verify` encadeia 1 → 3. A camada 2 fica separada por
precisar da fixture e do servidor.

> **Nota de ambiente**: o Chromium do Playwright já está disponível em
> `/opt/pw-browsers`, com `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`. Os scripts
> devem usar `executablePath` em vez de baixar navegador.

---

## 26.8 Portões por fase

Nenhuma fase do doc 25 fecha sem o seu portão.

| Fase | Portão |
|:-:|---|
| **1** | `lint:tokens --strict` limpo nas 5 categorias de token · comparação visual sem diferença não intencional |
| **2** | Galeria completa nas 13 paletas · testes de componente passando · percurso da galeria por teclado |
| **3** | `test:layout` ≤ 25% nas 8 telas · nenhuma ação duplicada na mesma tela · comparação visual revisada tela a tela |
| **4** | `lint:tokens` R-3 limpo · roteiro **R4** aprovado |
| **5** | `test:a11y` sem violação séria · `test:contrast` limpo nas 13 paletas · roteiro **R1** aprovado |
| **6** | `lint:tokens` R-7 limpo · roteiro **R5** nas 11 metodologias |
| **7** | `lint:tokens` R-6 limpo · nenhum arquivo de página > ~400 linhas · roteiros **R2** e **R3** aprovados |

---

## 26.9 Manutenção

O que impede a degradação depois que o plano terminar:

1. **`npm run verify` no `pre-push`** — barato o bastante para não incomodar.
2. **Comparação visual obrigatória em PR que toque `.css` ou `.tsx`.**
3. **Referência visual regravada no mesmo commit da mudança**, nunca em commit
   separado — assim a mudança visual é revisável junto com o código.
4. **Componente novo entra pela galeria**, com os 5 estados e os critérios de
   acessibilidade, antes de aparecer em qualquer tela.
5. **A baseline do § 26.2 fica versionada.** Quando um número subir, o número
   mostra em qual PR subiu.
