# 03 — Stack Tecnológica

> Decisões de tecnologia com justificativas para cada camada do RSAC V2.

---

## 3.1 Visão Geral da Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    ELECTRON SHELL (v33+)                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              RENDERER PROCESS (Chromium)               │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │           REACT 19 + TYPESCRIPT 5.x             │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌───────────────┐   │  │  │
│  │  │  │  Zustand  │ │React Qry │ │ React Router  │   │  │  │
│  │  │  │  (State)  │ │(Data)    │ │ (Navigation)  │   │  │  │
│  │  │  └──────────┘ └──────────┘ └───────────────┘   │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │ HTTP / WebSocket                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              MAIN PROCESS (Node.js)                    │  │
│  │  - Lifecycle management                                │  │
│  │  - Python process spawning                             │  │
│  │  - IPC bridge (Main ↔ Renderer)                       │  │
│  │  - Auto-updater                                        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │ HTTP localhost / stdio
┌─────────────────────────────────────────────────────────────┐
│               PYTHON BACKEND (FastAPI)                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │   Routers    │ │   Services   │ │   Harvesters     │    │
│  │  (REST API)  │ │  (Domain)    │ │  (Data Pipeline) │    │
│  └──────────────┘ └──────────────┘ └──────────────────┘    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │  SQLAlchemy  │ │    Alembic   │ │   AI Clients     │    │
│  │   (ORM)      │ │ (Migrations) │ │ (Gemini/Qwen/..) │    │
│  └──────────────┘ └──────────────┘ └──────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              SQLite (banco local unificado)            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3.2 Decisões por Camada

### 🐍 Backend Python

| Componente | Tecnologia | Versão | Justificativa |
|------------|-----------|--------|---------------|
| **Runtime** | Python | 3.12+ | Versão estável com performance melhorada, typing avançado |
| **Framework Web** | FastAPI | 0.115+ | Async nativo, OpenAPI auto-gerado, validação Pydantic, WebSocket nativo |
| **Validação** | Pydantic | 2.x | Modelos tipados, serialização JSON, validação de schema |
| **ORM** | SQLAlchemy | 2.x | ORM maduro, suporte async, migrations via Alembic |
| **Migrations** | Alembic | 1.x | Schema versioning, auto-generate, rollback |
| **Banco de Dados** | SQLite | 3.x | Zero-config, arquivo local, WAL mode para concorrência |
| **HTTP Client** | httpx | 0.27+ | Async/sync, HTTP/2, streaming, timeout configurável |
| **PDF Parsing** | PyMuPDF (fitz) | 1.24+ | Extração rápida de texto, metadados e imagens |
| **Task Queue** | asyncio + background tasks | nativo | Processamento assíncrono sem dependência externa |
| **WebSocket** | FastAPI WebSocket | nativo | Progresso em tempo real para harvesters e triagem |
| **Testes** | pytest + pytest-asyncio | 8.x | Framework padrão, fixtures async, coverage |
| **Linting** | Ruff | 0.8+ | Linter + formatter ultra-rápido (substitui flake8+black+isort) |
| **Typing** | mypy | 1.x | Verificação estática de tipos |

### ⚡ Electron Desktop Shell

| Componente | Tecnologia | Versão | Justificativa |
|------------|-----------|--------|---------------|
| **Shell Desktop** | Electron | 33+ | 📖 Referência livro — container Chromium + Node.js |
| **Build Tool** | Vite | 6.x | Dev server instantâneo, HMR, build otimizado |
| **Electron Tooling** | electron-vite | 3.x | Integração Vite + Electron com config unificada |
| **Empacotamento** | electron-builder | 25+ | Gera `.exe`, `.dmg`, `.AppImage` |
| **Auto-Update** | electron-updater | 6.x | Updates via GitHub Releases |

### ⚛️ Frontend React

| Componente | Tecnologia | Versão | Justificativa |
|------------|-----------|--------|---------------|
| **UI Library** | React | 19.x | 📖 Referência livro — component model, hooks, concurrent features |
| **Linguagem** | TypeScript | 5.x | Type safety, intellisense, refactoring seguro |
| **Roteamento** | React Router | 7.x | Navegação SPA, nested routes, loaders |
| **Estado Global** | Zustand | 5.x | Lightweight, sem boilerplate, integração com React DevTools |
| **Data Fetching** | TanStack Query | 5.x | Cache, refetch, optimistic updates, polling |
| **HTTP Client** | ky / fetch | nativo | Lightweight HTTP para comunicação com backend local |
| **Formulários** | React Hook Form + Zod | 7.x / 3.x | Validação declarativa, performance |
| **Componentes UI** | Radix UI + CSS Modules | latest | Primitivos acessíveis (WCAG), sem opinião visual |
| **Ícones** | Lucide React | latest | Ícones SVG consistentes, tree-shakeable |
| **Gráficos** | Recharts | 2.x | Gráficos React nativos para dashboard |
| **Toast/Notifs** | Sonner | 2.x | Toasts animados e elegantes |
| **Tabelas** | TanStack Table | 8.x | Tabelas headless com sorting, filtering, pagination |

### 🧪 Ferramentas de Desenvolvimento

| Componente | Tecnologia | Justificativa |
|------------|-----------|---------------|
| **Monorepo** | npm workspaces | Gerenciamento de pacotes frontend/electron |
| **Python Env** | uv | Gerenciador de pacotes Python ultra-rápido |
| **Testes E2E** | Playwright | Testes end-to-end no Electron |
| **Testes Frontend** | Vitest + Testing Library | Unit tests React |
| **CI/CD** | GitHub Actions | Build, test e release automatizados |
| **Versionamento** | Conventional Commits | Changelog automatizado |

---

## 3.3 Mapeamento: Livro "JavaScript Everywhere" → RSAC V2

O livro de Adam D. Scott propõe a arquitetura:

```
GraphQL API (Express.js) → React Web → Electron Desktop → React Native Mobile
```

No RSAC V2, adaptamos para:

```
REST API (FastAPI/Python) → React Web (Renderer) → Electron Desktop → (futuro: React Native)
```

| Conceito do Livro | Adaptação RSAC V2 |
|-------------------|-------------------|
| Express.js + Apollo Server (GraphQL) | **FastAPI** (REST + OpenAPI) — Python permite reutilizar toda a lógica de domínio e harvesters existentes |
| MongoDB + Mongoose | **SQLite + SQLAlchemy** — dados estruturados e relacionais são mais adequados para metadados bibliográficos |
| React Web App (standalone) | **React no Renderer Process** do Electron — SPA completa consumindo a API local |
| Electron Main Process | **Electron Main** — gerencia lifecycle, spawn do backend Python, IPC e auto-update |
| JWT Authentication | **Não necessário na V2** — aplicação single-user local (pode ser adicionado no futuro para versão web) |
| React Native | **Futuro** — a separação Backend/Frontend permitirá criar um cliente mobile |

> 📖 **Princípio-chave do livro preservado**: a separação completa entre API e clientes permite que o mesmo backend sirva múltiplas interfaces (desktop, web, mobile) — exatamente o que queremos para evolução futura do RSAC.

---

## 3.4 Por que NÃO usar GraphQL?

O livro recomenda GraphQL, mas para o RSAC V2 optamos por **REST** pelas seguintes razões:

1. **Complexidade desnecessária**: O RSAC tem um único cliente (Electron), não precisa da flexibilidade de queries do GraphQL
2. **FastAPI é REST-first**: OpenAPI spec auto-gerada, Swagger UI gratuito
3. **Curva de aprendizado**: REST é universalmente conhecido; GraphQL adiciona complexidade de schema + resolvers
4. **Performance**: Para operações batch (triagem em lote), REST com WebSocket é mais eficiente

> Se no futuro houver necessidade de múltiplos clientes com requisitos de dados diferentes, GraphQL pode ser adotado como evolução.

---

## 3.5 Por que Python no Backend (e não Node.js puro)?

1. **Preservação de investimento**: Toda a lógica de domínio, harvesters e integrações de IA já estão em Python
2. **Ecossistema científico**: PyMuPDF, pandas, scikit-learn — ferramentas essenciais para processamento acadêmico
3. **LLM SDKs**: Google Generative AI, OpenAI SDK, Alibaba DashScope — todos Python-first
4. **Performance I/O**: FastAPI com uvicorn é competitivo com Express.js para APIs HTTP
5. **Tipagem**: Python 3.12 + Pydantic v2 oferece tipagem robusta comparável a TypeScript
