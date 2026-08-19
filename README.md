# RSAC V2 — Revisão Sistemática Assistida por Computador

<div align="center">

<img src="brand/svg/rsac-lockup-dark.svg#gh-dark-mode-only" alt="RSAC V2" height="76" />
<img src="brand/svg/rsac-lockup-light.svg#gh-light-mode-only" alt="RSAC V2" height="76" />

![RSAC V2 Release](https://img.shields.io/badge/RSAC_V2-v2.0.0-274c77?style=flat-square)
![Estágio](https://img.shields.io/badge/Estágio-BETA-6096ba?style=flat-square)
![Python Version](https://img.shields.io/badge/Python-3.12+-274c77?style=flat-square)
![Node Version](https://img.shields.io/badge/Node-20+-274c77?style=flat-square)
![License](https://img.shields.io/badge/Licença-MIT-8b8c89?style=flat-square)

**Ambiente computacional para planejamento, coleta, triagem, extração e síntese de revisões sistemáticas e revisões de escopo da literatura científica.**

</div>

---

## Visão Geral

O RSAC V2 é uma ferramenta desenvolvida para apoiar a condução de revisões sistemáticas e revisões de escopo da literatura. O sistema implementa fluxos de trabalho alinhados aos principais padrões metodológicos internacionais de síntese de evidências, integrando coleta em bases de dados, desduplicação de registros, leitura de documentos completos em formato PDF, triagem por critérios explícitos e extração estruturada de dados.

A arquitetura é dividida em:
- **Backend**: API construída em Python (FastAPI, SQLAlchemy 2.0 e SQLite), responsável pela persistência, rotinas de coleta assíncrona, desduplicação e processamento de arquivos.
- **Frontend**: Interface construída em React 19, TypeScript e Vite, disponibilizada como aplicativo desktop via Electron ou como Single Page Application (SPA) acessível via navegador web e dispositivos móveis.

---

## Módulos do Sistema

### 1. Gestão de Projetos e Protocolos
- Suporte a 11 diretrizes metodológicas com listas de verificação estruturadas:
  - **PRISMA-ScR (2018)**: Revisões de Escopo (*Scoping Reviews*) — 22 itens
  - **PRISMA 2020**: Revisões Sistemáticas com ou sem meta-análise — 27 itens
  - **PRISMA-P (2015)**: Protocolos de revisão sistemática — 17 itens
  - **JBI (Joanna Briggs Institute)**: Revisões de métodos mistos e síntese qualitativa
  - **Cochrane Handbook / MECIR**: Síntese de intervenções
  - **Campbell Collaboration (MECCIR)**: Políticas sociais, educação e desenvolvimento
  - **CEE / ROSES**: Evidências ambientais e conservação
  - **EBSE (Kitchenham & Charters)**: Engenharia de software baseada em evidências
  - **PRIOR**: Revisões guarda-chuva (*overview of reviews*)
  - **Methodi Ordinatio (Pagani et al.)**: Ranqueamento bibliográfico por InOrdinatio
  - **Personalizada**: Estrutura aberta para outros delineamentos de pesquisa
- Configuração de frameworks de formulação de pergunta de pesquisa: PICO, PCC, PICOS, SPICE e SPIDER.
- Definição de critérios formais de inclusão e exclusão e questões de extração de dados.
- Estruturação de descritores de busca em pares booleanos, otimizados para motores de indexação como o VuFind (BDTD) e SciELO.

### 2. Coleta de Dados (Harvesters)
- Módulos assíncronos de busca direta em fontes bibliográficas:
  - **BDTD** (Biblioteca Digital Brasileira de Teses e Dissertações — OAI-PMH e VuFind API)
  - **SciELO** (Scientific Electronic Library Online)
  - **PubMed / MEDLINE** (NCBI E-Utilities)
  - **Scopus / ScienceDirect** (Elsevier API)
  - **OpenAlex** (Scholarly Graph API)
  - **arXiv** (API de pré-prints)
  - **Importação de arquivos**: formatos RIS, BibTeX, CSV e XLSX.
- Rotina de desduplicação em múltiplos níveis: comparação exata por identificador persistente (DOI), normalização de títulos e cálculo de distância de Levenshtein combinada ao ano de publicação.

### 3. Triagem de Estudos (Fase 1 — Título e Resumo)
- Operação em modo manual ou assistido por modelos computacionais de linguagem.
- Na modalidade assistida, cada sugestão de inclusão ou exclusão apresenta justificativa ancorada diretamente no texto dos metadados, mapeando a correspondência com os critérios cadastrados.
- Controles por atalhos de teclado (`I` = Incluir, `E` = Excluir, `P` = Pendente).
- Filtros por decisão, base de dados de origem, ano de publicação e busca textual.

### 4. Obtenção de Texto Completo e Extração de Dados (Fase 2)
- Mecanismo de localização de artigos em texto completo (PDF) com tentativas estruturadas em repositórios institucionais, diretórios de acesso aberto (Unpaywall, OpenAlex, Semantic Scholar, Crossref, Europe PMC) e páginas de origem.
- Visualizador integrado de documentos com suporte a PDF renderizado, extração textual com paginação preservada e remoção de artefatos de digitalização.
- Matriz de extração estruturada baseada no formulário definido no protocolo, com ancoragem de trechos literais e indicação da página de referência.

### 5. Síntese e Exportação de Resultados
- Construção automatizada do Diagrama de Fluxo PRISMA com contabilidade de registros em cada etapa.
- Exportação dos dados da revisão em formatos editáveis:
  - Documentos de texto (Markdown e DOCX)
  - Tabelas de extração e planilhas de triagem (CSV e XLSX)
  - Arquivos de bibliografia (BibTeX e RIS)

### 6. Interface e Acessibilidade
- Design system com conformidade estrita de contraste (WCAG 2.1 AA) e tokens padronizados.
- Tema padrão: **Platinum & Dusk Blue**, com suporte a seleção de paletas alternativas na página de configurações.
- Monitoramento de tarefas em segundo plano e logs de execução via WebSocket.

---

## Arquitetura de Software

```
+-------------------------------------------------------------+
|                      RSAC V2 Sistema                        |
+------------------------------+------------------------------+
|      Camada de Interface     |      Camada de Serviços      |
|                              |                              |
|  - Electron 33 (Desktop)     |  - Python 3.12+              |
|  - React 19 / TypeScript 5   |  - FastAPI (REST & WebSocket)|
|  - Vite 6                    |  - SQLAlchemy 2.0 (ORM)      |
|  - Zustand (Gerenciamento)   |  - SQLite (Persistência)     |
|  - Design System / Tokens    |  - Harvesters Assíncronos    |
+------------------------------+------------------------------+
```

---

## Modos de Execução

O RSAC V2 pode ser executado em três modalidades distintas, dependendo do ambiente de uso:

### 1. Interface Local Desktop
Inicia o backend em segundo plano e abre a interface diretamente em janela dedicada de aplicativo (Chrome/Edge App Mode):
```bat
Iniciar_Interface_Local.bat
```
Ou via linha de comando:
```bash
python scripts/local_launcher.py
```

### 2. Servidor com Acesso Remoto (Nuvem / Dispositivos Móveis)
Inicia o backend e estabelece um túnel seguro (HTTPS) via Cloudflare Tunnel, exibindo no terminal o endereço público e o código QR para acesso em smartphones ou tablets:
```bat
Iniciar_Servidor.bat
```
Ou via linha de comando:
```bash
python scripts/server_launcher.py
```

### 3. Ambiente de Desenvolvimento (Desktop Electron)
Para desenvolvimento ativo com recarregamento em tempo real (*hot reload*):

#### Pré-requisitos
- Python 3.12 ou superior
- Node.js 20 ou superior e npm 10 ou superior
- Git

#### Instalação do Backend
```bash
cd backend
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate

pip install -e ".[dev]"
```

#### Instalação do Frontend
```bash
cd ../frontend
npm install
```

#### Execução Unificada
```powershell
# Windows PowerShell
.\scripts\dev.ps1
```

Ou em dois terminais separados:
```bash
# Terminal 1 — Backend:
cd backend
python run.py --port 8000 --reload --debug

# Terminal 2 — Frontend:
cd frontend
npm run dev
```

---

## Estrutura de Diretórios

```
RSACV2/
├── backend/                  # Código-fonte do servidor Python (FastAPI)
│   ├── app/
│   │   ├── api/v1/          # Endpoints REST e WebSockets
│   │   ├── core/            # Configurações gerais e segurança
│   │   ├── harvesters/      # Coletores de dados (BDTD, SciELO, etc.)
│   │   ├── infrastructure/  # Modelos de assistência computacional e persistência
│   │   ├── schemas/         # Esquemas de validação Pydantic
│   │   └── services/        # Regras de negócio de triagem e extração
│   ├── tests/               # Testes unitários e de integração (pytest)
│   └── run.py               # Ponto de entrada do servidor backend
├── frontend/                 # Código-fonte da interface (React / Electron)
│   ├── src/
│   │   ├── api/             # Cliente HTTP e integração com a API
│   │   ├── components/      # Componentes de interface do usuário
│   │   ├── data/            # Listas de verificação das diretrizes metodológicas
│   │   ├── pages/           # Telas do fluxo da revisão
│   │   ├── stores/          # Estados globais (Zustand)
│   │   └── styles/          # Tokens e folhas de estilo globais
│   └── vite.config.web.ts   # Configuração de build para distribuição Web SPA
├── scripts/                  # Scripts de automação, launchers e geração de executáveis
├── brand/                    # Definições da identidade visual e ativos gráficos
└── planejamento/             # Documentação técnica de arquitetura e validações
```

---

## Testes e Validação de Qualidade

Para executar as suítes de validação automatizadas:

```bash
# Testes do backend (pytest)
cd backend
pytest

# Validação estrita de design tokens e TypeScript no frontend
cd frontend
npm run verify

# Testes de unidade do frontend
npm run test
```

---

## Licença

Este projeto é distribuído sob a licença **MIT**. Para mais detalhes, consulte o arquivo `LICENSE`.
