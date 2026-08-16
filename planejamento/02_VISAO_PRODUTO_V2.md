# 02 — Visão do Produto RSAC V2

> Objetivos estratégicos, diferenciais competitivos e escopo funcional da nova versão.

---

## 2.1 Declaração de Visão

O **RSAC V2** será uma plataforma desktop profissional de nova geração para condução de Revisões Sistemáticas da Literatura, construída sobre uma arquitetura de **backend Python desacoplado** + **frontend Electron/React**, oferecendo uma experiência visual e interativa no nível de aplicações SaaS modernas, mantendo 100% do processamento e dados no ambiente local do pesquisador.

---

## 2.2 Objetivos Estratégicos

### 🎯 OE-1: Interface de Classe Mundial
Substituir Tkinter por uma UI React renderizada em Electron com:
- Design system premium (dark/light mode, glassmorphism, micro-animações)
- Dashboard interativo com métricas em tempo real (PRISMA flowchart dinâmico)
- Componentes reutilizáveis e acessíveis (WCAG 2.1)

### 🎯 OE-2: Arquitetura Desacoplada (📖 Modelo "JavaScript Everywhere")
Inspirado no livro de referência, separar completamente:
- **Backend Python (FastAPI)**: API REST expondo todos os serviços de domínio
- **Frontend React**: SPA consumindo a API via HTTP/WebSocket
- **Electron Shell**: Container desktop empacotando frontend + backend

Isso permite, no futuro, reutilizar o backend para uma versão web ou mobile (React Native), exatamente como proposto no livro.

### 🎯 OE-3: Pipeline de Dados Unificado
- Banco de dados SQLite unificado com ORM (SQLAlchemy) e migrações (Alembic)
- Processamento assíncrono com filas de tarefas
- WebSocket para notificação de progresso em tempo real

### 🎯 OE-4: Extensibilidade
- Sistema de plugins para novos harvesters
- Interface padronizada `BaseHarvester` com contrato único
- Configuração de IA plugável (novos provedores sem alterar código)

### 🎯 OE-5: Distribuição Profissional
- Instalador nativo (Electron Builder: `.exe` Windows, `.dmg` macOS, `.AppImage` Linux)
- Auto-update via electron-updater
- Código assinado digitalmente

---

## 2.3 Escopo Funcional V2

### Funcionalidades Herdadas da V1 (Porting)

| Módulo | Status |
|--------|--------|
| Definição de Protocolo com 7 metodologias | 🟢 Portar |
| Parceiro de Pesquisa IA (geração de protocolo) | 🟢 Portar + melhorar |
| Harvester BDTD | 🟢 Portar + refatorar |
| Harvester SciELO | 🟢 Portar + refatorar |
| Harvester OpenAlex | 🟢 Portar + refatorar |
| Harvester PubMed | 🟢 Portar + refatorar |
| Harvester Scopus | 🟢 Portar + refatorar |
| Deduplicação de registros | 🟢 Portar |
| Triagem Fase 1 (título/resumo) | 🟢 Portar |
| Triagem Fase 2 (extração de PDFs) | 🟢 Portar |
| Multi-provedor IA (Gemini, Qwen, Local) | 🟢 Portar |

### Funcionalidades Novas na V2

| Módulo | Descrição |
|--------|-----------|
| **Dashboard analítico** | Painel com contadores, gráficos de progresso, flowchart PRISMA interativo |
| **Gerenciamento de projetos** | Múltiplas revisões simultâneas, listagem, arquivamento |
| **Histórico e auditoria** | Log imutável de todas as decisões (quem, quando, porquê) |
| **Colaboração local** | Exportação/importação de projetos para revisão por pares |
| **Visualização de PDFs** | Viewer de PDF integrado com highlighting de trechos relevantes |
| **Progresso em tempo real** | WebSocket para harvesters e triagem em lote (progress bars live) |
| **Busca e filtros avançados** | Full-text search, filtros multi-critério com facetas |
| **Temas visuais** | Dark mode / Light mode com transição animada |
| **Auto-update** | Atualização automática da aplicação via GitHub Releases |
| **Sistema de notificações** | Toast notifications para conclusão de tarefas e erros |

---

## 2.4 Público-Alvo

1. **Pesquisadores acadêmicos** (mestrado, doutorado, pós-doc) conduzindo revisões sistemáticas
2. **Grupos de pesquisa** que precisam de reprodutibilidade e padronização
3. **Professores orientadores** que acompanham múltiplas revisões de orientandos

---

## 2.5 Requisitos Não-Funcionais

| Requisito | Meta |
|-----------|------|
| Tempo de inicialização | < 3 segundos |
| Responsividade da UI | 60fps, sem congelamento |
| Tamanho do instalador | < 150 MB |
| Suporte offline | 100% funcional (exceto chamadas de IA em nuvem) |
| Plataformas | Windows 10+, macOS 12+, Linux (Ubuntu 22.04+) |
