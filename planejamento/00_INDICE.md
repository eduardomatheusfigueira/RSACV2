# 📋 RSAC V2 — Índice do Planejamento

> **Revisão Sistemática Assistida por Computador — Versão 2.0**
> Arquitetura Python + Electron | Agosto 2026

---

## Documentos de Planejamento

| # | Documento | Descrição |
|---|-----------|-----------|
| 01 | [Diagnóstico da V1](./01_DIAGNOSTICO_V1.md) | Análise crítica da versão atual, limitações arquiteturais e dívidas técnicas |
| 02 | [Visão do Produto V2](./02_VISAO_PRODUTO_V2.md) | Objetivos estratégicos, diferenciais e escopo funcional da V2 |
| 03 | [Stack Tecnológica](./03_STACK_TECNOLOGICA.md) | Decisões de tecnologia, justificativas e versões de cada componente |
| 04 | [Arquitetura Geral](./04_ARQUITETURA_GERAL.md) | Diagrama de camadas, fluxo de dados Backend ↔ Electron e contratos IPC |
| 05 | [Backend Python — API](./05_BACKEND_PYTHON_API.md) | Design da API REST/GraphQL, rotas, modelos, ORM e autenticação |
| 06 | [Frontend Electron](./06_FRONTEND_ELECTRON.md) | Estrutura do Electron, processo Main/Renderer, React, navegação e UX |
| 07 | [Estrutura de Diretórios](./07_ESTRUTURA_DIRETORIOS.md) | Árvore completa de pastas e arquivos do projeto V2 |
| 08 | [Pipeline de Dados](./08_PIPELINE_DADOS.md) | Fluxo end-to-end: Harvesters → Deduplicação → Triagem → Extração |
| 09 | [Integrações de IA](./09_INTEGRACOES_IA.md) | Provedores de IA, contratos, fallback, retry e streaming |
| 10 | [Banco de Dados](./10_BANCO_DE_DADOS.md) | Modelagem relacional, migrações, SQLite/PostgreSQL e cache |
| 11 | [Testes e Qualidade](./11_TESTES_QUALIDADE.md) | Estratégia de testes unitários, integração, E2E e CI/CD |
| 12 | [Roadmap e Fases](./12_ROADMAP_FASES.md) | Cronograma de implementação dividido em fases incrementais |

---

## Referência Bibliográfica Base

- **Adam D. Scott** — *JavaScript Everywhere: Building Cross-Platform Applications with GraphQL, React, React Native, and Electron* (O'Reilly Media, 2020)
  - Modelo arquitetural: **GraphQL API (Backend) → React (Frontend) → Electron (Desktop)**
  - Adaptação para RSAC V2: **FastAPI (Python Backend) → React (Frontend) → Electron (Desktop Shell)**

---

## Convenções

- 🟢 = Decisão confirmada
- 🟡 = Em discussão / aguardando validação
- 🔴 = Bloqueante / risco identificado
- 📖 = Referência ao livro *JavaScript Everywhere*
