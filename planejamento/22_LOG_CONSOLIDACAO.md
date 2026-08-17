# 📋 22 — Log de Consolidação do Planejamento e Auditoria da UI

> **RSAC V2 — Revisão Sistemática Assistida por Computador**  
> **Data:** Agosto de 2026  
> **Status:** Vigente e Normativo  
> **Fronteira:** `01–21` Histórico de Evolução · `22` Log de Auditoria · `23–26` Especificação e Governança Vigente

---

## 1. Contexto e Metodologia da Auditoria

Este documento consolida o estado real do repositório RSAC V2 após confronto minucioso contra os documentos históricos de planejamento (01 a 21). 

A auditoria foi realizada **linha a linha contra a base de código real** e o aplicativo em execução (Backend FastAPI + Renderer Electron/React), utilizando:
1. Inspeção estática de arquivos e árvore de importações (`tsc`, `eslint`).
2. Execução da suíte de testes unitários (`pytest`, `vitest`).
3. Auditoria dinâmica de layout, renderização, densidade e contratos IPC.

---

## 2. Estado de Entrega por Frentes de Trabalho

| Frente de Trabalho | Documentos Base | Estado Real | Observações da Auditoria |
|---|---|---|---|
| **Fase 0 — Fundação & Arquitetura** | 01–07 | **Concluída** | FastAPI + Electron + React operando. IPC estruturado. |
| **Fase 1 — Modelagem & DB** | 05, 10 | **Concluída com Divergência** | SQLite operacional com repositórios e DTOs tipados. Sync direto no boot em vez de migrations Alembic. |
| **Fase 2 — Coleta & Harvesters** | 13–17 | **Concluída** | Harvesters BDTD, SciELO, Scopus, OpenAlex, PubMed com rate limiting, resiliência e paginação. |
| **Fase 3 — Triagem & Deduplicação** | 08, 11 | **Concluída** | Algoritmos de deduplicação (DOI + Title Levenshtein), Triagem 1 (Título/Resumo) com IA assistida. |
| **Fase 4 — Aquisição de PDF & Extração** | 18–21 | **Concluída** | Resolvedor multi-estratégia (DOI, SciELO, Unpaywall, BDTD), extração PDFMiner/PyPDF, ancoragem sem alucinações. |
| **Fase 5 — Empacotamento Desktop & CI/CD** | 06, 11, 12 | **Parcial** | Electron Builder empacota dev/preview; faltam Auto-updater, testes E2E Playwright e pipeline CI/CD remoto. |
| **Fase 6 / Item 1.3 — Design System React** | 03, 06 | **Dívida Técnica Estrutural** | Não entregue como componentes React reutilizáveis. Saiu como CSS disperso por página. |

---

## 3. Divergências Estruturais Identificadas

1. **AppShell em Formato Ribbon**:
   - *Planejado:* TopBar clássica com `Header` superior, `Breadcrumbs` de navegação e `Sidebar` retrátil vertical.
   - *Entregue:* Barra superior de ferramentas Ribbon densa de alta produtividade (`TopRibbonBar.tsx`), com abas por etapa de trabalho e acoplamento direto com a área central.
   - *Impacto:* A `Sidebar.tsx` (372 linhas) tornou-se código morto não renderizado.

2. **Fluxograma PRISMA**:
   - *Planejado:* Renderizado via biblioteca `Recharts` / componentes gráficos.
   - *Entregue:* Implementação vetorial/CSS manual dedicada, dispensando o overhead do Recharts para o fluxo.

3. **Sincronização de Banco de Dados**:
   - *Planejado:* Migrações geridas via Alembic.
   - *Entregue:* Inicialização declarativa com `init_db()` sincronizada na subida do backend FastAPI.

4. **Acoplamento Ribbon ↔ DOM (`clickDomByText`)**:
   - O Ribbon foi implementado acionando comandos através de busca de texto visível no DOM (`clickDomByText('button', 'Salvar Tudo')`), criando uma fragilidade onde a alteração de rótulos quebra silenciosamente os atalhos.

---

## 4. Decisões de Governança Vigente

1. **Aposentadoria de Código Morto**: Expurgo formal de `Sidebar.tsx` e `Sidebar.css`.
2. **Ativação dos Pacotes Instalados**: Adoção dos primitivos `@radix-ui/*` (Dialog, Tooltip, Select, Tabs, Separator) e `@tanstack/react-table` já listados no `package.json`.
3. **Desacoplamento de Ações do Ribbon**: Substituição do `clickDomByText` por barramento unificado de comandos ou store de ações.
4. **Governança Metodológica Multidiretriz**: Generalização dos componentes de Protocolo e Ribbon para responder dinamicamente ao `PROTOCOL_CATALOG` (atendendo CEE/ROSES, PRISMA 2020, Campbell, JBI, etc., sem referências engessadas).
