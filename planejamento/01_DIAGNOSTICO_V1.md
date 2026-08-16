# 01 — Diagnóstico Crítico da V1 (RSAC)

> Análise técnica das limitações arquiteturais, dívidas técnicas e pontos de dor da versão atual.

---

## 1.1 Resumo Executivo

O RSAC V1 é uma aplicação desktop Python/Tkinter que automatiza revisões sistemáticas da literatura. Embora funcional e com um domínio bem modelado (Clean Architecture parcial), a V1 apresenta limitações estruturais severas que justificam uma reescrita completa.

---

## 1.2 Pontos Fortes da V1 (Preservar na V2)

| Aspecto | Detalhe |
|---------|---------|
| **Modelagem de Domínio** | Entidades imutáveis (`Paper`, `Protocol`, `ScreeningSession`), enum de decisões, padrão Repository |
| **Ports & Adapters** | Interface `AIClient` (Protocol), `ProjectRepository` (ABC) — desacoplamento entre core e infra |
| **Multi-provedor de IA** | Suporte a Gemini, Qwen, Bonsai local — com rotação de chaves e fallback |
| **Harvesters robustos** | 5 coletores (BDTD, SciELO, OpenAlex, PubMed, Scopus) com persistência em SQLite/Excel |
| **Suporte a 7 metodologias** | PRISMA-P, Campbell, CEE/ROSES, EBSE, Umbrella, Scoping, Methodi Ordinatio |
| **Algoritmo de deduplicação** | Normalização de títulos, DOI e similaridade textual |

---

## 1.3 Limitações Críticas

### 🔴 1.3.1 Monólito de UI — `main.py` com 8.029 linhas

O arquivo `config_app/main.py` concentra **toda** a lógica de apresentação, bindings, estado e parte da lógica de negócio em um único arquivo Python. Isso resulta em:

- Impossibilidade prática de testes unitários na camada de UI
- Acoplamento entre lógica de negócio e widgets Tkinter
- Dificuldade extrema de onboarding para novos desenvolvedores
- Alto risco de regressão em qualquer alteração

### 🔴 1.3.2 Tkinter como Framework de UI

- **Estética limitada**: Sem suporte nativo a animações, gradientes, sombras ou design systems modernos
- **Renderização**: Single-threaded, bloqueia a UI durante operações pesadas
- **Responsividade**: Layout gerenciado por `pack`/`grid` sem breakpoints ou media queries
- **Ecossistema**: Sem gerenciador de estado reativo, sem component library, sem hot-reload

### 🔴 1.3.3 Persistência Fragmentada

- Sessões salvas em JSON flat files (sem transações, sem índices)
- Harvesters usam SQLite independente (bancos separados por base)
- Sem schema migration — quebra silenciosa ao evoluir estrutura

### 🟡 1.3.4 Processamento Síncrono

- `screen_paper_sync` / `screen_batch_sync` — bloqueio sequencial
- Sem filas de tarefas assíncronas
- Sem websockets para notificação de progresso em tempo real

### 🟡 1.3.5 Harvesters como Scripts Isolados

- Cada harvester é um script Python standalone (~40-76k linhas)
- Sem interface unificada (cada um define seu próprio `run_harvest`)
- Duplicação de lógica de HTTP, retry, parsing e persistência entre harvesters

### 🟡 1.3.6 Distribuição

- Build via PyInstaller (`ConfiguradorRevisao.spec`) gerando executável Windows
- Sem auto-update
- Sem instalador cross-platform

---

## 1.4 Métricas Quantitativas

| Métrica | Valor |
|---------|-------|
| Linhas em `main.py` | 8.029 |
| Linhas totais estimadas (harvesters) | ~210.000+ |
| Entidades de domínio | 4 (Paper, Protocol, ScreeningSession, Decision) |
| Portas (interfaces) | 3 (AIClient, ProjectRepository, PDFRepository) |
| Serviços de domínio | 3 (ScreeningService, ExtractionService, HarvestOrchestrator) |
| Harvesters | 5 (BDTD, SciELO, OpenAlex, PubMed, Scopus) |
| Widgets customizados | 7 (Badge, Button, Card, Input, PaperCard, Progress, StatusBar) |
| Views | 3 (ProtocolView, ScreeningView, ExtractionView) |

---

## 1.5 Decisão: Reescrever vs. Refatorar

| Critério | Refatorar V1 | Reescrever V2 |
|----------|:---:|:---:|
| Preservar domínio | ✅ | ✅ (portar) |
| UI moderna (Electron/React) | ❌ | ✅ |
| Banco relacional unificado | Difícil | ✅ |
| API desacoplada | Muito difícil | ✅ |
| Testes E2E | ❌ | ✅ |
| Auto-update | ❌ | ✅ |

**Veredicto**: 🟢 **Reescrita completa** com portabilidade do domínio e lógica de negócio Python.
