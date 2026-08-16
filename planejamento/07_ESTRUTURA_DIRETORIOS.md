# 07 — Estrutura de Diretórios

> Árvore completa e anotada de pastas e arquivos do projeto RSAC V2.

---

## 7.1 Visão Macro — Monorepo

```
RSAC V2/
│
├── Material de referência/             # 📚 Livros e papers de referência
│   └── Adam D. Scott - JavaScript Everywhere.pdf
│
├── planejamento/                       # 📋 Documentação de planejamento (este diretório)
│   ├── 00_INDICE.md
│   ├── 01_DIAGNOSTICO_V1.md
│   ├── ... (12 documentos)
│   └── 12_ROADMAP_FASES.md
│
├── backend/                            # 🐍 Python Backend (FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # App factory FastAPI
│   │   ├── config.py                   # Pydantic BaseSettings
│   │   ├── database.py                 # SQLAlchemy engine + session
│   │   │
│   │   ├── api/                        # Routers (endpoints HTTP)
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                 # Dependency injection
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py           # Router agregador
│   │   │   │   ├── projects.py
│   │   │   │   ├── protocols.py
│   │   │   │   ├── papers.py
│   │   │   │   ├── harvesting.py
│   │   │   │   ├── screening.py
│   │   │   │   ├── extraction.py
│   │   │   │   ├── ai.py
│   │   │   │   ├── settings.py
│   │   │   │   └── export.py
│   │   │   └── ws/
│   │   │       ├── __init__.py
│   │   │       └── tasks.py            # WebSocket handlers
│   │   │
│   │   ├── domain/                     # Entidades e regras de negócio
│   │   │   ├── __init__.py
│   │   │   ├── entities.py             # Paper, Protocol, ScreeningSession
│   │   │   ├── enums.py                # Decision, Methodology, HarvesterSource
│   │   │   ├── events.py               # Domain events
│   │   │   ├── exceptions.py           # DomainError, NotFoundError, etc.
│   │   │   └── value_objects.py         # SearchDescriptor, DOI, etc.
│   │   │
│   │   ├── services/                   # Application services (use cases)
│   │   │   ├── __init__.py
│   │   │   ├── project_service.py
│   │   │   ├── protocol_service.py
│   │   │   ├── screening_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── harvest_service.py
│   │   │   ├── dedup_service.py
│   │   │   ├── export_service.py
│   │   │   └── ai_assistant_service.py
│   │   │
│   │   ├── infrastructure/             # Adaptadores de saída
│   │   │   ├── __init__.py
│   │   │   ├── ai/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_client.py      # ABC / Protocol de IA
│   │   │   │   ├── gemini_client.py
│   │   │   │   ├── qwen_client.py
│   │   │   │   ├── local_client.py     # OpenAI-compatible local
│   │   │   │   └── response_parser.py
│   │   │   ├── harvesters/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_harvester.py   # ABC com contrato unificado
│   │   │   │   ├── bdtd_harvester.py
│   │   │   │   ├── scielo_harvester.py
│   │   │   │   ├── openalex_harvester.py
│   │   │   │   ├── pubmed_harvester.py
│   │   │   │   └── scopus_harvester.py
│   │   │   ├── pdf/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pdf_extractor.py    # PyMuPDF text extraction
│   │   │   │   └── pdf_downloader.py   # Download assíncrono
│   │   │   └── persistence/
│   │   │       ├── __init__.py
│   │   │       └── models.py           # SQLAlchemy ORM models
│   │   │
│   │   └── schemas/                    # Pydantic I/O schemas
│   │       ├── __init__.py
│   │       ├── project.py
│   │       ├── protocol.py
│   │       ├── paper.py
│   │       ├── harvesting.py
│   │       ├── screening.py
│   │       ├── extraction.py
│   │       ├── ai.py
│   │       └── common.py
│   │
│   ├── alembic/                        # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   │
│   ├── tests/                          # Testes Python
│   │   ├── conftest.py                 # Fixtures (test DB, mock AI, etc.)
│   │   ├── test_api/
│   │   │   ├── test_projects.py
│   │   │   ├── test_papers.py
│   │   │   ├── test_screening.py
│   │   │   └── test_harvesting.py
│   │   ├── test_services/
│   │   │   ├── test_screening_service.py
│   │   │   ├── test_dedup_service.py
│   │   │   └── test_harvest_service.py
│   │   ├── test_harvesters/
│   │   │   ├── test_bdtd.py
│   │   │   └── test_scielo.py
│   │   └── test_domain/
│   │       ├── test_entities.py
│   │       └── test_value_objects.py
│   │
│   ├── alembic.ini
│   ├── pyproject.toml                  # Dependências e configs (uv/pip)
│   ├── requirements.txt                # Lock para produção
│   └── run.py                          # Entry point (uvicorn runner)
│
├── frontend/                           # ⚡ Electron + React
│   ├── electron/                       # Main Process
│   │   ├── main.ts
│   │   ├── preload.ts
│   │   ├── python-manager.ts
│   │   ├── updater.ts
│   │   ├── menu.ts
│   │   └── ipc-handlers.ts
│   │
│   ├── src/                            # Renderer Process (React)
│   │   ├── main.tsx                    # React entry
│   │   ├── App.tsx                     # Root + Router
│   │   │
│   │   ├── api/                        # HTTP/WS client layer
│   │   │   ├── client.ts
│   │   │   ├── endpoints.ts
│   │   │   └── websocket.ts
│   │   │
│   │   ├── stores/                     # Zustand state management
│   │   │   ├── useProjectStore.ts
│   │   │   ├── useSettingsStore.ts
│   │   │   └── useTaskStore.ts
│   │   │
│   │   ├── hooks/                      # Custom React hooks
│   │   │   ├── useProjects.ts
│   │   │   ├── usePapers.ts
│   │   │   ├── useScreening.ts
│   │   │   ├── useHarvesting.ts
│   │   │   └── useWebSocket.ts
│   │   │
│   │   ├── pages/                      # Route-level components
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── ProjectListPage.tsx
│   │   │   ├── ProjectDetailPage.tsx
│   │   │   ├── ProtocolPage.tsx
│   │   │   ├── HarvestingPage.tsx
│   │   │   ├── ScreeningPage.tsx
│   │   │   ├── ExtractionPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   └── ExportPage.tsx
│   │   │
│   │   ├── components/                 # UI components
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   └── Breadcrumbs.tsx
│   │   │   ├── common/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Badge.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Select.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── DataTable.tsx
│   │   │   │   ├── ProgressBar.tsx
│   │   │   │   ├── EmptyState.tsx
│   │   │   │   ├── LoadingSpinner.tsx
│   │   │   │   └── SearchInput.tsx
│   │   │   ├── domain/
│   │   │   │   ├── PaperCard.tsx
│   │   │   │   ├── PaperDetailPanel.tsx
│   │   │   │   ├── ProtocolForm.tsx
│   │   │   │   ├── CriteriaEditor.tsx
│   │   │   │   ├── ScreeningControls.tsx
│   │   │   │   ├── HarvesterStatus.tsx
│   │   │   │   ├── PrismaFlowchart.tsx
│   │   │   │   ├── AIProviderConfig.tsx
│   │   │   │   └── MethodologySelector.tsx
│   │   │   └── charts/
│   │   │       ├── StatsCounter.tsx
│   │   │       ├── DecisionPieChart.tsx
│   │   │       └── TimelineChart.tsx
│   │   │
│   │   ├── styles/
│   │   │   ├── globals.css
│   │   │   ├── themes/
│   │   │   │   ├── light.css
│   │   │   │   └── dark.css
│   │   │   └── components/
│   │   │       └── *.module.css
│   │   │
│   │   ├── lib/                        # Utilitários
│   │   │   ├── constants.ts
│   │   │   ├── formatters.ts
│   │   │   └── validators.ts
│   │   │
│   │   └── types/                      # TypeScript definitions
│   │       ├── api.ts
│   │       ├── electron.d.ts
│   │       └── domain.ts
│   │
│   ├── public/
│   │   ├── icon.png
│   │   ├── icon.ico
│   │   └── splash.html
│   │
│   ├── resources/                      # Assets para electron-builder
│   │   ├── icon.icns                   # macOS
│   │   ├── icon.ico                    # Windows
│   │   └── icon.png                    # Linux
│   │
│   ├── electron-builder.yml
│   ├── electron.vite.config.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── .eslintrc.cjs
│
├── scripts/                            # Scripts de desenvolvimento
│   ├── dev.ps1                         # Inicia backend + frontend em paralelo
│   ├── build.ps1                       # Build de produção completo
│   ├── setup-python.ps1               # Setup do ambiente Python
│   └── package-backend.ps1            # Empacota backend para distribuição
│
├── docs/                               # Documentação do usuário
│   ├── guia-usuario.md
│   ├── guia-instalacao.md
│   └── changelog.md
│
├── .github/
│   └── workflows/
│       ├── ci.yml                      # Testes automatizados
│       └── release.yml                 # Build + release automático
│
├── .gitignore
├── README.md
└── LICENSE
```

---

## 7.2 Convenções de Nomenclatura

| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| **Pastas Python** | snake_case | `harvest_service.py` |
| **Pastas React** | camelCase | `useProjects.ts` |
| **Componentes React** | PascalCase | `PaperCard.tsx` |
| **CSS Modules** | PascalCase.module.css | `Button.module.css` |
| **Testes Python** | test_*.py | `test_screening_service.py` |
| **Testes React** | *.test.tsx | `PaperCard.test.tsx` |
| **Migrações Alembic** | NNN_descricao.py | `001_initial_schema.py` |
| **Endpoints API** | plural kebab-case | `/api/v1/projects/{id}/papers` |

---

## 7.3 Arquivos de Configuração Raiz

| Arquivo | Propósito |
|---------|-----------|
| `.gitignore` | Ignorar `node_modules`, `__pycache__`, `.env`, `*.db`, `dist/` |
| `README.md` | Documentação principal do projeto |
| `LICENSE` | Licença MIT |
| `scripts/dev.ps1` | Script PowerShell para iniciar desenvolvimento local |
