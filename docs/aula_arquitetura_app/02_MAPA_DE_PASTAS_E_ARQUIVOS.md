# 📁 Aula 02: Mapa Completo de Pastas e Arquivos

> **Guia Anatômico do Repositório do Revsist (RSAC V2)**

---

## 1. Visão Geral da Raiz do Projeto

A raiz do projeto é dividida entre os componentes de aplicação, ferramentas de automação e documentação:

```
RSACV2/
├── backend/               # Servidor e regras de negócio em Python (FastAPI)
├── frontend/              # Interface do usuário em React/TypeScript + Host Electron
├── scripts/               # Scripts de build, automação e deploy
├── planejamento/          # Especificações técnicas, conformidade LGPD e planos de execução
├── brand/                 # Identidade visual, logotipos e paletas de cores
├── dist_bin/              # Diretório de saída dos binários compilados (RSAC-Setup.exe)
├── .agents/               # Regras e diretrizes metodológicas do projeto
├── docker-compose.dev.yml # Ambiente Docker para PostgreSQL de desenvolvimento
├── Iniciar_RSAC.bat       # Atalho de execução rápida para desenvolvimento local
└── README.md              # Apresentação do repositório
```

---

## 2. Anatomia do Backend (`/backend`)

O backend segue rigorosamente os princípios de **Clean Architecture** (Arquitetura Limpa) e **Domain-Driven Design (DDD)**:

```
backend/
├── alembic/                      # Motor de migrações de banco de dados
│   ├── env.py                    # Configuração de conexão do Alembic com os modelos
│   └── versions/                 # Histórico imutável de revisões de banco (SQL / DDL)
├── app/                          # Código-fonte principal da aplicação
│   ├── api/                      # Camada de Apresentação (Interface HTTP REST)
│   │   └── v1/                   # Versão 1 da API pública e autenticada
│   │       ├── ai.py             # Configuração de chaves e testes de IA
│   │       ├── auth.py           # Login por senha e fluxo Google OAuth2 + PKCE
│   │       ├── deduplication.py  # Endpoints de detecção e fusão de duplicatas
│   │       ├── export.py         # Exportação de planilhas e relatórios PRISMA
│   │       ├── extraction.py     # Endpoints de dados extraídos de artigos
│   │       ├── harvest.py        # Disparo e monitoramento de coletas nas bases
│   │       ├── health.py         # Verificação de saúde da API e do banco
│   │       ├── insights.py       # Consultas analíticas para B.I. e bibliometria
│   │       ├── papers.py         # CRUD de artigos e upload de PDFs
│   │       ├── profile.py        # Backup e restauração de perfil do pesquisador
│   │       ├── projects.py       # Gestão de projetos de revisão sistemática
│   │       ├── protocols.py      # Gestão de critérios, questões e descritores
│   │       ├── router.py         # Agregador central de rotas públicas e autenticadas
│   │       ├── screening_ai.py   # Triagem assistida unitária e em lote
│   │       └── settings.py       # Configurações do sistema e parâmetros de IA
│   ├── harvesters/               # Camada de Integração Externa (Coletores Acadêmicos)
│   │   ├── base.py               # Classe abstrata BaseHarvester com contrato de busca
│   │   ├── scielo.py             # Harvester SciELO via CrossRef API com prefixos de periódicos
│   │   ├── bdtd.py               # Harvester BDTD via motor VuFind / OAI-PMH
│   │   ├── scopus.py             # Harvester Elsevier Scopus API
│   │   ├── pubmed.py             # Harvester NCBI PubMed / Entrez E-utilities
│   │   └── ieee.py               # Harvester IEEE Xplore API
│   ├── infrastructure/           # Camada de Infraestrutura e Persistência
│   │   ├── ai/                   # Adaptadores de Inteligência Artificial
│   │   │   ├── base.py           # Interface comum BaseAIClient
│   │   │   ├── factory.py        # Fábrica que instancia o cliente de IA configurado
│   │   │   ├── gemini_client.py  # Cliente Google Gemini (com rotação e fallback)
│   │   │   ├── openai_compatible_client.py # Cliente OpenAI / Groq / DeepSeek
│   │   │   ├── ollama_client.py  # Cliente Ollama para inferência 100% local
│   │   │   └── prompts.py        # Engenharia de prompts e templates de sistema
│   │   └── persistence/          # Mapeamento Objeto-Relacional (ORM)
│   │       └── models.py         # Definição das tabelas SQLAlchemy (Project, Paper, etc.)
│   ├── schemas/                  # Camada de Contratos de Dados (DTOs / Pydantic v2)
│   │   ├── auth.py, dedup.py, extraction.py, harvest.py, insights.py, 
│   │   ├── paper.py, project.py, protocol.py, screening.py, settings.py
│   ├── security/                 # Camada de Segurança e Proteção de Dados
│   │   ├── dependencies.py       # Injeção de dependência do usuário autenticado (`get_current_user`)
│   │   ├── google_oauth.py       # Validação e troca de tokens do Google OAuth2
│   │   ├── middleware.py         # Cabeçalhos de segurança HTTP (CSP, HSTS, X-Frame-Options)
│   │   ├── oauth_state.py        # Gestão de estados PKCE com tempo de expiração
│   │   ├── passwords.py          # Hashing criptográfico de senhas com Argon2id
│   │   ├── secret_box.py         # Criptografia autenticada AES-GCM para chaves de API e backups
│   │   └── sessions.py           # Gestão de sessões com cookies HttpOnly seguros
│   ├── services/                 # Camada de Domínio / Regras de Negócio Puras
│   │   ├── dedup_service.py      # Lógica de deduplicação exata e fuzzy com RapidFuzz
│   │   ├── export_service.py     # Gerador de relatórios Excel, CSV e PRISMA
│   │   ├── extraction_service.py # Gestão de formulários e extração de dados
│   │   ├── harvesting_service.py # Orquestrador assíncrono de coletas com persistência em lote
│   │   ├── insights_service.py   # Agregação estatística para B.I. e bibliometria
│   │   ├── pdf_service.py        # Manipulação e extração de texto de PDFs via PyMuPDF
│   │   ├── profile_service.py    # Exportação/importação de acervos cifrados
│   │   └── screening_service.py  # Orquestrador de triagem por IA com semáforo de concorrência
│   ├── config.py                 # Leitura tipada de variáveis de ambiente via Pydantic Settings
│   ├── database.py               # Motor de banco de dados híbrido (SQLite/PostgreSQL)
│   ├── main.py                   # Ponto de entrada FastAPI, lifespan e configuração CORS
│   ├── schema.py                 # Utilitários de migração e verificação de integridade
│   └── websocket.py              # Gerenciador de conexões WebSocket para feedback em tempo real
├── tests/                        # Suíte de Testes Automatizados (467 testes unitários e de integração)
└── pyproject.toml                # Gerenciamento de dependências e ferramentas Python
```

---

## 3. Anatomia do Frontend (`/frontend`)

O frontend é uma aplicação de página única (**SPA**) desenvolvida com **React 18**, **TypeScript**, **Vite** e **Electron**:

```
frontend/
├── electron/                     # Processos nativos do Electron
│   ├── main/
│   │   └── index.ts              # Processo principal: gerencia janelas e subprocesso Python
│   └── preload/
│       └── index.ts              # Script de preload com contexto seguro IPC
├── src/                          # Código-fonte da interface web
│   ├── api/
│   │   └── client.ts             # Cliente Axios configurado com interceptors e autenticação
│   ├── components/               # Componentes visuais reutilizáveis
│   │   ├── common/               # Modais de confirmação, toasts, loaders, etc.
│   │   ├── layout/               # TopRibbonBar, NavigationMenu, StatusBar
│   │   ├── modal/                # Modais específicos (Triagem em Lote, Importação)
│   │   └── ui/                   # Botões, inputs, tabelas e cards estilizados
│   ├── hooks/                    # React Custom Hooks (WebSockets, estado de projetos)
│   ├── pages/                    # Páginas correspondentes a cada etapa da RSL
│   │   ├── ProjectsPage.tsx      # Listagem e criação de projetos
│   │   ├── ProtocolPage.tsx      # Configuração de critérios e descritores
│   │   ├── HarvestPage.tsx       # Disparo de busca com monitoramento em tempo real
│   │   ├── ScreeningPage.tsx     # Painel Kanban e triagem manual/assistida por IA
│   │   ├── ExtractionPage.tsx    # Formulários de extração e leitor de PDF embutido
│   │   ├── InsightsPage.tsx      # Gráficos interativos de bibliometria e B.I.
│   │   ├── ExportPage.tsx        # Exportação de dados e fluxo PRISMA
│   │   ├── SettingsPage.tsx      # Configuração de chaves de IA (Gemini, OpenAI, Ollama)
│   │   └── LoginPage.tsx         # Tela de autenticação local ou com Google
│   ├── theme/                    # Tokens de design, variáveis CSS de cores e tipografia
│   ├── types/                    # Tipos TypeScript espelhando os contratos da API
│   ├── App.tsx                   # Roteamento principal da aplicação e controle de contexto
│   ├── index.css                 # Folha de estilos globais e Design System
│   └── main.tsx                  # Ponto de entrada do React
├── electron-builder.yml          # Configuração de empacotamento do instalador Windows
├── package.json                  # Dependências do ecossistema Node.js / React
└── vite.config.ts                # Configurações de compilação do Vite
```

---

## 4. Pastas Auxiliares

- **`scripts/`**:
  - `build_installer.py`: Orquestra todo o processo de build (compila o backend com PyInstaller, compila o frontend com Vite/Electron e gera o `RSAC-Setup.exe` via Inno Setup).
  - `diagnostico_coleta.py`: Script de teste e auditoria isolada dos coletores acadêmicos.
- **`planejamento/`**:
  - Contém todo o histórico e documentação viva de arquitetura, segurança e LGPD (documentos `00_INDICE.md` a `41_PLANO_EXECUCAO_ONLINE.md`).
- **`.agents/`**:
  - `AGENTS.md`: Diretrizes metodológicas do projeto (ex: formulação de descritores de busca estritamente em pares e foco em Ciências Sociais Aplicadas e Desenvolvimento Regional).

---

Na próxima aula, vamos entender detalhadamente o funcionamento interno do Backend:  
👉 **[Aula 03: Arquitetura e Engenharia do Backend](./03_ARQUITETURA_BACKEND.md)**
