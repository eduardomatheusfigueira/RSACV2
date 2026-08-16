# 05 — Backend Python — API

> Design da API REST, rotas, modelos Pydantic, ORM e serviços de domínio.

---

## 5.1 Estrutura do Backend

```
backend/
├── alembic/                    # Configuração e scripts de migração
│   ├── versions/               # Arquivos de migração gerados
│   └── env.py
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory
│   ├── config.py               # Settings (Pydantic BaseSettings)
│   ├── database.py             # Engine SQLAlchemy + session factory
│   │
│   ├── api/                    # Camada de API (Routers)
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependency injection (get_db, get_ai_client)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # Router principal agregando sub-routers
│   │   │   ├── projects.py     # CRUD de projetos de revisão
│   │   │   ├── protocols.py    # CRUD de protocolos metodológicos
│   │   │   ├── papers.py       # CRUD e busca de papers
│   │   │   ├── harvesting.py   # Iniciar/monitorar harvesters
│   │   │   ├── screening.py    # Triagem manual e em lote
│   │   │   ├── extraction.py   # Extração de dados de PDFs
│   │   │   ├── ai.py           # Configuração e teste de IA
│   │   │   ├── settings.py     # Configurações gerais da app
│   │   │   └── export.py       # Exportação (Excel, JSON, BibTeX)
│   │   └── ws/
│   │       ├── __init__.py
│   │       └── tasks.py        # WebSocket para progresso de tarefas
│   │
│   ├── domain/                 # Camada de Domínio (Regras de Negócio)
│   │   ├── __init__.py
│   │   ├── entities.py         # Entidades puras (Paper, Protocol, etc.)
│   │   ├── enums.py            # Enumeradores (Decision, Methodology, etc.)
│   │   ├── events.py           # Domain events
│   │   ├── exceptions.py       # Exceções de domínio
│   │   └── value_objects.py    # Value objects (SearchDescriptor, etc.)
│   │
│   ├── services/               # Serviços de Aplicação (Use Cases)
│   │   ├── __init__.py
│   │   ├── project_service.py
│   │   ├── protocol_service.py
│   │   ├── screening_service.py
│   │   ├── extraction_service.py
│   │   ├── harvest_service.py
│   │   ├── dedup_service.py
│   │   ├── export_service.py
│   │   └── ai_assistant_service.py
│   │
│   ├── infrastructure/         # Adaptadores de Saída
│   │   ├── __init__.py
│   │   ├── ai/                 # Clientes de IA
│   │   │   ├── __init__.py
│   │   │   ├── base_client.py  # ABC / Protocol
│   │   │   ├── gemini_client.py
│   │   │   ├── qwen_client.py
│   │   │   ├── local_client.py
│   │   │   └── response_parser.py
│   │   ├── harvesters/         # Coletores bibliográficos
│   │   │   ├── __init__.py
│   │   │   ├── base_harvester.py  # ABC com contrato unificado
│   │   │   ├── bdtd_harvester.py
│   │   │   ├── scielo_harvester.py
│   │   │   ├── openalex_harvester.py
│   │   │   ├── pubmed_harvester.py
│   │   │   └── scopus_harvester.py
│   │   ├── pdf/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_extractor.py
│   │   │   └── pdf_downloader.py
│   │   └── persistence/
│   │       ├── __init__.py
│   │       └── models.py       # SQLAlchemy models (ORM)
│   │
│   └── schemas/                # Pydantic Schemas (API I/O)
│       ├── __init__.py
│       ├── project.py
│       ├── protocol.py
│       ├── paper.py
│       ├── harvesting.py
│       ├── screening.py
│       ├── extraction.py
│       ├── ai.py
│       └── common.py           # PaginatedResponse, ErrorResponse, etc.
│
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   ├── test_harvesters/
│   └── test_domain/
│
├── pyproject.toml              # Dependências (uv/pip)
└── requirements.txt            # Lock file para produção
```

---

## 5.2 API Routes

### Base URL: `http://localhost:{port}/api/v1`

### 5.2.1 Projetos

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/projects` | Listar todos os projetos |
| `POST` | `/projects` | Criar novo projeto |
| `GET` | `/projects/{id}` | Detalhes de um projeto |
| `PUT` | `/projects/{id}` | Atualizar projeto |
| `DELETE` | `/projects/{id}` | Excluir projeto |
| `GET` | `/projects/{id}/stats` | Estatísticas (contadores PRISMA) |

### 5.2.2 Protocolos

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/projects/{id}/protocol` | Obter protocolo do projeto |
| `PUT` | `/projects/{id}/protocol` | Atualizar protocolo |
| `POST` | `/projects/{id}/protocol/generate` | Gerar protocolo com IA |

### 5.2.3 Papers

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/projects/{id}/papers` | Listar papers (paginado, filtrável) |
| `GET` | `/projects/{id}/papers/{paper_id}` | Detalhes de um paper |
| `PUT` | `/projects/{id}/papers/{paper_id}` | Atualizar paper (decisão, critérios) |
| `DELETE` | `/projects/{id}/papers/{paper_id}` | Remover paper |
| `POST` | `/projects/{id}/papers/import` | Importar papers (JSON/BibTeX/RIS) |

### 5.2.4 Harvesting

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/projects/{id}/harvest` | Iniciar coleta (especificar bases) |
| `GET` | `/projects/{id}/harvest/status` | Status das coletas em andamento |
| `POST` | `/projects/{id}/harvest/cancel` | Cancelar coleta em andamento |
| `POST` | `/projects/{id}/deduplicate` | Executar deduplicação |

### 5.2.5 Triagem (Screening)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/projects/{id}/screening/single` | Triar um paper (manual ou IA) |
| `POST` | `/projects/{id}/screening/batch` | Triagem em lote com IA |
| `GET` | `/projects/{id}/screening/progress` | Progresso da triagem em lote |
| `POST` | `/projects/{id}/screening/cancel` | Cancelar triagem em lote |

### 5.2.6 Extração (Fase 2)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/projects/{id}/extraction/scan-pdfs` | Escanear PDFs na pasta |
| `POST` | `/projects/{id}/extraction/extract` | Extrair dados de um PDF |
| `POST` | `/projects/{id}/extraction/batch` | Extração em lote |
| `GET` | `/projects/{id}/extraction/{paper_id}` | Dados extraídos de um paper |

### 5.2.7 Exportação

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/projects/{id}/export/excel` | Exportar para Excel |
| `GET` | `/projects/{id}/export/json` | Exportar sessão JSON |
| `GET` | `/projects/{id}/export/bibtex` | Exportar BibTeX |
| `GET` | `/projects/{id}/export/prisma` | Dados do flowchart PRISMA |

### 5.2.8 Configurações de IA

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/settings/ai` | Obter configuração de IA atual |
| `PUT` | `/settings/ai` | Atualizar configuração de IA |
| `POST` | `/settings/ai/test` | Testar conexão com provedor |

### 5.2.9 Sistema

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI (auto-gerado pelo FastAPI) |

---

## 5.3 Modelos Pydantic (Schemas de I/O)

```python
# schemas/paper.py

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from app.domain.enums import Decision

class PaperBase(BaseModel):
    title: str
    authors: str
    year: Optional[str] = None
    source: str
    research_type: Optional[str] = None
    institution: Optional[str] = None
    abstract: Optional[str] = None
    download_url: Optional[str] = None
    doi: Optional[str] = None

class PaperCreate(PaperBase):
    pass

class PaperUpdate(BaseModel):
    decision: Optional[Decision] = None
    inclusion_criteria: Optional[Dict[str, bool]] = None
    exclusion_criteria: Optional[Dict[str, bool]] = None
    questions: Optional[Dict[str, str]] = None
    observations: Optional[str] = None

class PaperResponse(PaperBase):
    id: str
    decision: Decision = Decision.PENDING
    inclusion_criteria: Dict[str, bool] = Field(default_factory=dict)
    exclusion_criteria: Dict[str, bool] = Field(default_factory=dict)
    questions: Dict[str, str] = Field(default_factory=dict)
    observations: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class PaperListResponse(BaseModel):
    items: list[PaperResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

---

## 5.4 Padrão de Startup do Backend

```python
# app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import run_migrations, create_engine
from app.api.v1.router import api_router
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    run_migrations()
    yield
    # Shutdown
    # cleanup resources

def create_app() -> FastAPI:
    app = FastAPI(
        title="RSAC API",
        version="2.0.0",
        description="Revisão Sistemática Assistida por Computador",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    return app

app = create_app()
```

---

## 5.5 Contrato BaseHarvester (Interface Unificada)

```python
# infrastructure/harvesters/base_harvester.py

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, List
from app.domain.entities import Paper

class BaseHarvester(ABC):
    """Contrato unificado para todos os coletores bibliográficos."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Nome da base de dados (ex: 'BDTD', 'SciELO')."""
        ...

    @abstractmethod
    async def harvest(
        self,
        descriptors: List[str],
        year_start: int | None = None,
        year_end: int | None = None,
        languages: List[str] | None = None,
    ) -> AsyncIterator[Paper]:
        """
        Executa a coleta assíncrona, yielding papers um a um.
        Permite streaming de progresso via WebSocket.
        """
        ...

    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida se a configuração do harvester está correta."""
        ...
```
