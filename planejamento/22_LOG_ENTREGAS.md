# 22 — Log de Entregas

> Consolidação do que os planos 01–21 previram e o que foi efetivamente
> entregue, verificado contra o código em 17/08/2026.
>
> Este documento existe para que os planos anteriores possam ser lidos como
> **histórico**, e não como lista de pendências. O que estiver marcado ✅ aqui
> está no repositório e foi verificado; o que estiver ⬜ continua aberto e foi
> transportado para o plano vigente.

---

## 22.1 Como este log foi levantado

Cada linha foi conferida contra o repositório, não contra a memória dos
documentos: existência de arquivo, importação efetiva do módulo, execução do
`tsc`, do `electron-vite build` e da suíte `pytest`, e inspeção visual do
aplicativo em execução com o backend Python ativo.

Onde a entrega divergiu do que o plano descrevia, a divergência está registrada
— um item entregue "de outro jeito" não é um item entregue conforme o plano, e
essa diferença importa para quem for ler os documentos antigos depois.

---

## 22.2 Roadmap original (doc 12) — situação por fase

### 🏗️ Fase 0 — Fundação ✅

| # | Tarefa | Situação |
|---|--------|:--------:|
| 0.1–0.2 | Estrutura de diretórios + `pyproject.toml` | ✅ |
| 0.3 | FastAPI app factory + `/health` | ✅ |
| 0.4 | SQLAlchemy + models | ✅ · **divergência**: sincronização de tabelas em vez de migrações Alembic |
| 0.5 | Scaffold Electron + React (`electron-vite`) | ✅ |
| 0.6 | `python-manager.ts` (spawn do backend) | ✅ |
| 0.7 | `preload.ts` (contextBridge) | ✅ |
| 0.8 | React consulta `/health` e exibe status | ✅ |

> **Dívida registrada**: o `alembic` é dependência declarada, mas não há
> diretório de migrações. O esquema é sincronizado no boot
> (`app/database.py`). Funciona para app local de usuário único; vira problema
> no primeiro `ALTER` destrutivo.

### 📦 Fase 1 — CRUD Core ✅ (com uma exceção estrutural)

| # | Tarefa | Situação |
|---|--------|:--------:|
| 1.1–1.2 | API CRUD de projetos e protocolos | ✅ |
| 1.3 | **Design system (Button, Card, Badge, Input)** | ⬜ **Não entregue como componentes** |
| 1.4 | AppShell (Sidebar + Header + Breadcrumbs) | ✅ · **divergência**: virou TopRibbonBar + StatusBar + LogPanel; `Header` e `Breadcrumbs` nunca existiram |
| 1.5 | Dashboard com contadores | ✅ |
| 1.6 | Lista / criação / detalhe de projeto | ✅ |
| 1.7 | Formulário de protocolo | ✅ |
| 1.8 | Geração de protocolo assistida por IA | ✅ |

> **A exceção estrutural é o item 1.3** e é a raiz da maior parte do que o
> plano de UX/UI vigente precisa resolver. O design system foi entregue como
> **tokens CSS + classes utilitárias**, não como componentes React. O
> resultado está medido no doc 23: 25 classes de botão distintas, 11 classes
> de estado vazio e o cabeçalho de página replicado em 8 arquivos.

### 🔍 Fase 2 — Harvesters ✅

| # | Tarefa | Situação |
|---|--------|:--------:|
| 2.1 | `BaseHarvester` + factory | ✅ `harvesters/base.py`, `factory.py` |
| 2.2–2.6 | BDTD, SciELO, OpenAlex, PubMed, Scopus | ✅ 5 coletores |
| 2.7 | Endpoints + WebSocket de progresso | ✅ |
| 2.8 | Tela de coleta | ✅ |
| 2.9 | Deduplicação (3 passes) | ✅ `dedup_service.py` |
| 2.10 | Testes unitários dos coletores | ✅ 5 suítes com mocks |

### ✅ Fase 3 — Triagem ✅

| # | Tarefa | Situação |
|---|--------|:--------:|
| 3.1–3.2 | Clientes Gemini, Qwen e local | ✅ |
| 3.3 | `ScreeningService` (individual + lote) | ✅ |
| 3.4 | Endpoints + WebSocket de lote | ✅ |
| 3.5–3.6 | Tela de triagem + lote | ✅ |
| 3.7 | Configuração de IA | ✅ · ampliado: isolamento estrito de chaves por provedor |
| 3.8 | Rotação de chaves + retry | ✅ |

### 📄 Fase 4 — Extração e Exportação ✅

| # | Tarefa | Situação |
|---|--------|:--------:|
| 4.1–4.2 | Download e extração de texto de PDF | ✅ superado pelo subsistema do doc 19 |
| 4.3–4.4 | `ExtractionService` + endpoints | ✅ |
| 4.5 | Tela de extração | ✅ 3 modos: resumo, PDF renderizado, texto |
| 4.6–4.7 | Exportação (Excel, BibTeX, Markdown) + tela | ✅ |
| 4.8 | Fluxograma PRISMA | ✅ · **divergência**: construído em HTML/CSS, não em Recharts |
| 4.9 | Dashboard com gráficos reais | ⬜ **Não entregue** — o dashboard tem contadores, não gráficos |

### ✨ Fase 5 — Polimento e Distribuição — parcial

| # | Tarefa | Situação |
|---|--------|:--------:|
| 5.1 | Dark mode | ✅ **muito superado**: 13 paletas completas |
| 5.2 | Micro-animações | 🟡 parcial: `fade-in` e `spin`; sem sistema de movimento |
| 5.3 | Auto-updater | ⬜ `electron/updater.ts` não existe |
| 5.4 | electron-builder (instaladores) | ✅ entregue com a identidade visual (doc 22.4) |
| 5.5 | Testes E2E (Playwright) | ⬜ **zero** arquivos de teste no frontend |
| 5.6 | CI/CD (GitHub Actions) | ⬜ sem workflows |
| 5.7 | Documentação do usuário | ✅ `17_GUIA_DE_USO.md` |
| 5.8 | README | ✅ atualizado |

---

## 22.3 Planos temáticos (docs 13–21)

### Coleta (docs 13–16)

Entregue: contrato de coleta, os 5 coletores em paridade, execução com job
manager (`harvest_job_manager.py`), cancelamento, progresso por WebSocket,
deduplicação e persistência. Suítes de teste com mocks HTTP para os 5
coletores e para a deduplicação.

⬜ Aberto: validação de paridade V1 ↔ V2 em acervo real (doc 16 §6.1).

### PDF e extração (docs 18–21) ✅ Fases 1–6

| Fase | Entrega | Situação |
|:----:|---------|:--------:|
| 1 | Resolvedor multi-estratégia (`pdf_resolver.py`) | ✅ |
| 2 | Serviço de aquisição e cache (`pdf_service.py`) | ✅ |
| 3 | Pipeline de texto (`pdf_text.py`) | ✅ |
| 4 | Procedência + lote | ✅ |
| 5 | Contexto e evidência ancorada da IA | ✅ |
| 6 | Interface de 3 modos + trilha de diagnóstico | ✅ |
| 7 | Validação em acervo real | ⬜ |
| 8 | OCR opcional | ⬜ |
| 9 | Relato metodológico | ⬜ |

**Dívida nº 1 do doc 20 § 20.12 — resolvida.** O item estava marcado 🔴:
*"`frontend/src/data/protocolCatalog` não existe no repositório… o
`npm run build` falha por isso"*. Ver § 22.5.

As dívidas 2 a 5 do doc 20 seguem abertas e foram transportadas para o plano
vigente ou permanecem no backlog técnico.

---

## 22.4 Identidade visual — entrega de 17/08/2026 ✅

Não constava dos planos 01–21; o roadmap previa apenas "dark mode + tema
refinado" (5.1). Entregue como sistema completo, documentado em
[`brand/IDENTIDADE_VISUAL.md`](../brand/IDENTIDADE_VISUAL.md).

| Entrega | Descrição |
|---------|-----------|
| **Monograma R-Lupa** | "R" monolinear em que o laço é a lente e a perna diagonal é o cabo. Grade 80 × 100, quatro pontos de controle inteiros; caixa de tinta 4:5 por construção |
| **Gerador único** | `brand/generate_brand_assets.py` — toda arte deriva da mesma geometria |
| **Marca temática** | Haste e lente em `currentColor`, cabo em `--rsac-accent`: re-pigmenta nas 13 paletas |
| **Selo BETA** | Splash, barra de título, sidebar, barra de status e ícones de distribuição |
| **Ícones de distribuição** | `.ico` (7 tamanhos, com ajuste óptico por resolução), `.icns`, `.png`, artes do instalador NSIS |
| **Splash de inicialização** | Marca visível antes do React montar, removida pelo `main.tsx` |
| **`AppUserModelId`** | Alinhado ao `appId` do electron-builder |

> A entrega tocou apenas o *chrome* da aplicação (barra de título, sidebar,
> barra de status) e um cartão em Configurações. **O interior das telas não foi
> revisado** — é exatamente o escopo do plano vigente.

---

## 22.5 Catálogo de diretrizes — correção de 17/08/2026 ✅

O `npm run build` falhava num clone limpo: `ProjectsPage` e `ProtocolPage`
importavam `@/data/protocolCatalog`, e o módulo nunca existiu no repositório.

**Causa raiz**: o `.gitignore` trazia `data/` na seção de persistência. Sem
barra inicial, o padrão casa em qualquer profundidade — inclusive
`frontend/src/data/`, que é código-fonte. O arquivo existia na máquina do
autor, o git o ignorou em silêncio e nunca foi versionado. Corrigido para
`/data/`, ancorado na raiz.

**Entregue**: catálogo com as 11 metodologias do enum do backend, cada uma com
sua matriz de auditoria — 8 listas de verificação e ~175 itens, com a
proveniência declarada por lista (numeração oficial reproduzida onde a diretriz
publica uma; organização por domínios, com citação da fonte, onde o documento é
formulário por seções).

Efeito colateral verificado: os 8 erros de `implicitly any` que o `tsc`
acusava eram consequência do módulo ausente e desapareceram. `tsc --noEmit`
está limpo.

---

## 22.6 Interface — entregas de 17/08/2026 ✅

Três frentes fechadas depois da consolidação do catálogo, todas verificadas com
o aplicativo em execução.

### Cabeçalho e estados canônicos (doc 25, Fase 3 parcial)

O `<PageHeader>` existia mas só o Estúdio de Protocolo o usava; as outras sete
páginas repetiam a mesma marcação `.page-header` local. Todas as 8 telas agora
medem **44 px de cabeçalho** (47 no Protocolo, por causa do seletor de
diretriz) e expõem **exatamente uma ação primária** — antes a Triagem tinha
três, a Coleta três e a Extração duas.

Os comandos que saíram do cabeçalho não sumiram: já eram despachados pelo
ribbon pelo registro tipado da Fase 4. A exceção era a auditoria de duplicatas,
que só existia no cabeçalho da Triagem; ganhou lugar no ribbon dessa aba, no
grupo Tratamento do Acervo.

Os estados vazios e de carregamento das seis telas que ainda os desenhavam à
mão passaram a `<EmptyState>`/`<LoadingState>`. Dois deles ganharam causa
declarada: em Projetos, filtro sem resultado deixou de dizer "crie um projeto";
na Extração, "conclua a Triagem 1" é diferente de "limpe a busca".

Removidas 112 linhas de CSS morto de `globals.css` mais os estados vazios locais
de Painel e Projetos. `.loading-spinner` morava em `DashboardPage.css` e era
usado por outras três páginas — dependência que sumiu junto.

### Controles e modais (doc 25, Fase 5 parcial)

Os **seis** modais da aplicação eram `<div className="modal-overlay">` escritos
à mão — o diagnóstico contava cinco; o relatório de deduplicação era o sexto.
Nenhum prendia o foco, fechava no Escape ou devolvia o foco ao fechar, e para
um leitor de tela o resto da página continuava presente por baixo. Todos
migraram para o `<Dialog>` do Radix. A janela de barra de título clássica virou
a variante `window` do `DialogContent`.

Catorze elementos não interativos com `onClick` viraram controles de verdade:
`<button>` onde o elemento é o comando, `<label>` onde havia caixa de seleção
dentro (o `onClick` do contêiner disparava junto com o `onChange` do input). O
cartão de projeto continua `<div>`, com papel e teclado declarados — ele contém
o botão de excluir, e controle dentro de controle é marcação inválida.

`sonner` estava no `package.json` desde o início e nunca fora importado. Entrou
com as cores da paleta ativa. Nível `error` do log store agora levanta aviso na
tela: o painel de logs fica fechado por padrão, e enquanto ele era o único
destino, uma falha ao registrar decisão de triagem não produzia sinal nenhum.
Fontes de diagnóstico (`API`, `WebSocket`) seguem só no painel — "DELETE
/projects/&lt;uuid&gt; falhou (500)" não é recado para quem está triando artigos.

### Contraste medido nas 13 paletas (doc 24 § 24.5)

A auditoria `axe-core` rodada nas 8 telas **× 13 paletas** — e não só na paleta
padrão — expôs um defeito sistêmico: **72 dos 91 pares semânticos** de cor
reprovavam em 4.5:1. O padrão era sempre o mesmo — `color: var(--color-X)`
sobre `background: var(--color-X-bg)`, um par escolhido a olho.

A correção derivou tokens de texto **medidos**, preservando o matiz:

| Família | Medido contra | Para quê |
|---|---|---|
| `--color-{X}-text` | a tinta `--color-{X}-bg`, composta sobre a superfície | etiquetas e faixas tingidas |
| `--color-{X}-on-surface` | as três superfícies de conteúdo | texto semântico solto |
| `--color-text-on-{X}` | o pigmento sólido | etiquetas preenchidas |
| `--color-accent-text` | a tinta do acento | etiquetas na tinta do acento |
| `--color-accent-on-surface` / `--color-accent-on-chrome` | conteúdo / chrome escuro | acento como texto |
| `--color-text-on-olive` | `--olive-leaf` de cada paleta | pílulas no verde de marca |

Quatro defeitos de raiz apareceram no caminho e foram corrigidos:

1. **Quatro paletas escuras não definiam as próprias tintas** (`lava-steel`,
   `indigo-rose`, `amethyst-deep`, `synthwave-neon`) e herdavam as tintas
   *claras* do `:root` — daí faixas claras com texto claro, a 1.57:1.
2. **O selo BETA se preenchia com 14% da própria cor**, aproximando fundo e
   texto. O contorno de 1px já era a identidade; o preenchimento saiu.
3. **A pílula da aba ativa** usava véu sobre o acento, mudando exatamente o
   fundo contra o qual `--color-text-on-accent` fora medido.
4. **`--color-text-tertiary` reprovava em 8 paletas** e
   `--color-chrome-text-muted` a 62% caía a 4.41:1 na synthwave-neon.

Resultado: `axe-core` **sem violação** nas 8 telas × 13 paletas.

A geração dos tokens vive em `frontend/scripts/derivar-tokens-de-contraste.py`,
e a regra **R8** do verificador — que analisa por bloco, não por linha — impede
que um par não medido volte: ela acusa `background: var(--color-X-bg)` com
`color: var(--color-X)` na mesma regra. Foi testada contra uma regressão
proposital antes de entrar.

---

## 22.7 O que segue aberto

Transportado para os documentos vigentes ou mantido no backlog.

| # | Item aberto | Origem | Destino |
|---|-------------|:------:|---------|
| 1 | Design system como componentes React | doc 12 § 1.3 | **doc 25, Fase 2** |
| 2 | Dashboard com gráficos reais | doc 12 § 4.9 | **doc 25, Fase 7** |
| 3 | Micro-animações como sistema | doc 12 § 5.2 | **doc 24 § 24.8** |
| 4 | Testes E2E / de interface | doc 12 § 5.5 | **doc 26** |
| 5 | Auto-updater | doc 12 § 5.3 | backlog técnico |
| 6 | CI/CD | doc 12 § 5.6 | backlog técnico |
| 7 | Migrações Alembic | doc 12 § 0.4 | backlog técnico |
| 8 | Validação de paridade da coleta em acervo real | doc 16 § 6.1 | backlog de validação |
| 9 | Validação de PDF em acervo real, OCR, relato metodológico | doc 20, fases 7–9 | backlog de validação |
| 10 | Cache local de APIs externas por DOI | doc 20 § 20.12 nº 3 | backlog técnico |
| 11 | Verificar se o PDF baixado é o trabalho certo | doc 20 § 20.12 nº 5 | backlog técnico |
| 12 | Renomear `download_url` | doc 20 § 20.12 nº 4 | backlog técnico |

---

## 22.8 Marco de consolidação

Em 17/08/2026 o RSAC V2 cobre o ciclo completo da revisão — protocolo, coleta
em 5 bases, triagem, aquisição de texto integral, extração com evidência
ancorada e exportação — com backend testado (17 suítes), build de instalador
funcionando e identidade visual própria.

O que **não** acompanhou esse avanço foi a camada de interface: ela cresceu por
adição, tela a tela, sem um vocabulário compartilhado. É um débito de forma, não
de função — e é o objeto dos documentos 23 a 26.
