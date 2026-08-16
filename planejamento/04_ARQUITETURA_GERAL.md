# 04 — Arquitetura Geral

> Diagrama de camadas, fluxo de dados e contratos de comunicação Backend ↔ Electron.

---

## 4.1 Diagrama de Arquitetura em Camadas

```mermaid
graph TB
    subgraph ELECTRON["🖥️ Electron Shell"]
        subgraph MAIN["Main Process (Node.js)"]
            LM[Lifecycle Manager]
            PS[Python Spawner]
            IPC[IPC Bridge]
            AU[Auto-Updater]
        end

        subgraph RENDERER["Renderer Process (Chromium)"]
            subgraph REACT["⚛️ React Application"]
                PAGES[Pages / Routes]
                COMPONENTS[Components]
                HOOKS[Custom Hooks]
                STORE[Zustand Store]
                QUERY[TanStack Query]
            end
        end

        MAIN <-->|"contextBridge / preload.js"| RENDERER
    end

    subgraph BACKEND["🐍 Python Backend (FastAPI)"]
        subgraph API["API Layer"]
            ROUTERS[Routers / Endpoints]
            MIDDLEWARE[Middleware]
            WS[WebSocket Manager]
        end

        subgraph DOMAIN["Domain Layer (Core)"]
            ENTITIES[Entities]
            SERVICES[Domain Services]
            PORTS[Ports / Interfaces]
            COMMANDS[Commands / Use Cases]
        end

        subgraph INFRA["Infrastructure Layer"]
            AI_CLIENTS[AI Clients]
            HARVESTERS[Harvesters]
            REPOS[Repositories]
            PDF[PDF Processor]
        end

        subgraph DATA["Data Layer"]
            DB[(SQLite DB)]
            MIGRATIONS[Alembic Migrations]
        end

        API --> DOMAIN
        DOMAIN --> INFRA
        INFRA --> DATA
    end

    RENDERER <-->|"HTTP REST + WebSocket (localhost:8000)"| BACKEND

    style ELECTRON fill:#1a1a2e,color:#fff
    style MAIN fill:#16213e,color:#fff
    style RENDERER fill:#0f3460,color:#fff
    style BACKEND fill:#1a1a1a,color:#fff
    style DOMAIN fill:#2d2d2d,color:#fff
```

---

## 4.2 Fluxo de Inicialização

```mermaid
sequenceDiagram
    participant User
    participant Electron Main
    participant Python Backend
    participant React Renderer

    User->>Electron Main: Abre a aplicação (.exe)
    Electron Main->>Electron Main: Verifica auto-update
    Electron Main->>Python Backend: Spawn process (uvicorn)
    Python Backend->>Python Backend: Run migrations (Alembic)
    Python Backend->>Python Backend: Start HTTP server :8000
    Python Backend-->>Electron Main: Health check OK
    Electron Main->>React Renderer: Cria BrowserWindow
    React Renderer->>React Renderer: Carrega React SPA
    React Renderer->>Python Backend: GET /api/health
    Python Backend-->>React Renderer: { status: "ok" }
    React Renderer-->>User: Dashboard pronto
```

---

## 4.3 Modelo de Comunicação

### 4.3.1 Frontend ↔ Backend (HTTP REST)

O React (Renderer) se comunica com o Python (FastAPI) via HTTP local:

```
http://localhost:8000/api/v1/...
```

| Método | Padrão | Uso |
|--------|--------|-----|
| `GET` | Leitura | Listar projetos, papers, configurações |
| `POST` | Criação | Criar projeto, iniciar harvesting, iniciar triagem |
| `PUT` | Atualização | Atualizar paper, protocolo, configurações |
| `DELETE` | Remoção | Excluir projeto, paper |

### 4.3.2 Frontend ↔ Backend (WebSocket)

Para operações de longa duração com feedback em tempo real:

```
ws://localhost:8000/ws/tasks/{task_id}
```

| Evento | Payload | Uso |
|--------|---------|-----|
| `harvest:progress` | `{ source, current, total, paper_title }` | Progresso do harvester |
| `screening:progress` | `{ current, total, paper_id, decision }` | Progresso da triagem em lote |
| `extraction:progress` | `{ current, total, paper_id }` | Progresso da extração de PDFs |
| `task:completed` | `{ task_id, result_summary }` | Tarefa concluída |
| `task:error` | `{ task_id, error_message }` | Erro em tarefa |

### 4.3.3 Electron Main ↔ Renderer (IPC)

Comunicação via `contextBridge` (segura, sem `nodeIntegration`):

```typescript
// preload.ts — API exposta ao renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // Diálogos nativos
  showOpenDialog: (options) => ipcRenderer.invoke('dialog:open', options),
  showSaveDialog: (options) => ipcRenderer.invoke('dialog:save', options),

  // Sistema de arquivos (seleção de pastas)
  selectDirectory: () => ipcRenderer.invoke('fs:selectDirectory'),

  // Informações do sistema
  getAppVersion: () => ipcRenderer.invoke('app:version'),
  getPlatform: () => ipcRenderer.invoke('app:platform'),

  // Auto-update
  checkForUpdates: () => ipcRenderer.invoke('updater:check'),
  onUpdateAvailable: (callback) => ipcRenderer.on('updater:available', callback),
  onUpdateDownloaded: (callback) => ipcRenderer.on('updater:downloaded', callback),

  // Notificações nativas
  showNotification: (title, body) => ipcRenderer.invoke('notification:show', title, body),
})
```

---

## 4.4 Princípios Arquiteturais

### 🏗️ Clean Architecture (Backend)

```
┌─────────────────────────────────┐
│         API / Routers           │  ← Adaptadores de entrada (HTTP)
├─────────────────────────────────┤
│    Application / Use Cases      │  ← Orquestração de domínio
├─────────────────────────────────┤
│       Domain / Entities         │  ← Regras de negócio puras
├─────────────────────────────────┤
│   Infrastructure / Adapters     │  ← Adaptadores de saída (DB, AI, HTTP)
└─────────────────────────────────┘
```

**Regra de Dependência**: As camadas internas NUNCA dependem das externas.

### 📖 Separação API/Client (Livro "JavaScript Everywhere")

O livro de Adam D. Scott enfatiza:
> *"By building our API as a standalone code base, we can more easily evolve the code, debug, and test our application."*

No RSAC V2:
- O backend Python é **completamente independente** — pode rodar standalone como servidor
- O frontend React é **completamente independente** — pode conectar a qualquer instância do backend
- O Electron é apenas o **shell de distribuição** — gerencia lifecycle e empacotamento

---

## 4.5 Segurança

| Aspecto | Implementação |
|---------|---------------|
| **nodeIntegration** | `false` — nenhum acesso Node.js no renderer |
| **contextIsolation** | `true` — preload.js isolado via contextBridge |
| **Content Security Policy** | `default-src 'self'; connect-src http://localhost:8000 ws://localhost:8000` |
| **Credenciais** | Armazenadas encriptadas via `safeStorage` do Electron |
| **CORS** | Backend aceita apenas `http://localhost:*` (origem local) |
| **Porta do Backend** | Dinâmica (porta aleatória disponível) — evita conflito |
