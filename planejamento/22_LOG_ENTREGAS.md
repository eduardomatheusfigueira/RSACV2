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

## 22.6 O que segue aberto

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

## 22.7 Marco de consolidação

Em 17/08/2026 o RSAC V2 cobre o ciclo completo da revisão — protocolo, coleta
em 5 bases, triagem, aquisição de texto integral, extração com evidência
ancorada e exportação — com backend testado (17 suítes), build de instalador
funcionando e identidade visual própria.

O que **não** acompanhou esse avanço foi a camada de interface: ela cresceu por
adição, tela a tela, sem um vocabulário compartilhado. É um débito de forma, não
de função — e é o objeto dos documentos 23 a 26.
