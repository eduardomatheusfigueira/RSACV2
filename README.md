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
- **Frontend**: Interface construída em React 19, TypeScript e Vite, distribuída como aplicativo de mesa via Electron. Backend e interface viajam juntos no instalador e sobem e descem com a janela; não há versão publicada nem acesso pelo navegador.

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

### 5. Indicadores (B.I. e Bibliometria)
- Funil de identificação, triagem e critérios de inclusão/exclusão, ordenado por impacto na composição final da amostra.
- Composição da amostra por decisão, base de coleta, ano de publicação e tipo de estudo.
- Rankings de periódico, autor e instituição mais frequentes entre os artigos incluídos.
- Saúde de aquisição de PDF e completude da matriz de extração.
- Proveniência de IA: throughput de triagem por pessoa, proporção de decisões manuais vs. assistidas e taxa de resposta fora do vocabulário esperado.
- Filtros por decisão, base e intervalo de ano, aplicados aos agregados de conteúdo.

### 6. Síntese e Exportação de Resultados
- Construção automatizada do Diagrama de Fluxo PRISMA com contabilidade de registros em cada etapa.
- Exportação dos dados da revisão em formatos editáveis:
  - Documentos de texto (Markdown e DOCX)
  - Tabelas de extração e planilhas de triagem (CSV e XLSX)
  - Arquivos de bibliografia (BibTeX e RIS)

### 7. Interface e Acessibilidade
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

## Como Executar

O RSAC V2 é um aplicativo de mesa instalado. Não há versão para abrir no
navegador: a interface e o backend Python viajam juntos no instalador, e o
servidor sobe e desce com a janela.

### 1. Uso normal — instalar e abrir

Execute o instalador e abra o RSAC V2 pelo atalho da área de trabalho ou do
menu Iniciar:

```
dist_bin/RSAC-Setup.exe
```

Não é preciso instalar Python nem Node: o backend vai congelado dentro do
pacote. Na primeira execução o backend cria a pasta de dados do usuário
(banco, PDFs, logs e chaves) e a interface entra direto, sem tela de login —
o acesso é provado por um arquivo que só o dono da máquina consegue ler.

Para gerar o instalador a partir do código (requer Windows, Python, Node e o
[Inno Setup 6](https://jrsoftware.org/isdl.php)):

```bash
python scripts/build_installer.py
```

### 2. Ambiente de Desenvolvimento (Desktop Electron)
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

#### (Opcional) E-mail de contato para busca de PDF
As APIs de acesso aberto usadas na localização de PDFs (Unpaywall, OpenAlex, Crossref) dão prioridade — e no caso do Unpaywall, exigem — identificação por e-mail. Crie `backend/.env` com:
```
RSAC_CONTACT_EMAIL=seu-email@instituicao.br
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
│   └── electron/            # Processo principal, preload e ponte IPC
├── scripts/                  # Build do instalador (PyInstaller + electron-builder + Inno Setup)
├── brand/                    # Definições da identidade visual e ativos gráficos
└── planejamento/             # Documentação técnica de arquitetura e validações
```

---

## Segurança e Acesso

O RSAC V2 é um aplicativo de mesa, e o perímetro é o da máquina em que ele
está instalado: **o backend só atende em `127.0.0.1`, e não há como publicá-lo**.

A credencial é um arquivo. Na primeira execução o backend sorteia um token de
256 bits e o grava em `runtime_token`, na pasta de dados do usuário, legível só
pelo dono; o Electron lê esse arquivo e o apresenta em todas as chamadas da
API, num cabeçalho próprio. Para o usuário, isso significa abrir o aplicativo e
usá-lo — não há tela de login, conta a criar nem senha a lembrar.

O raciocínio é o do Jupyter e o do Docker Desktop: quem consegue ler um arquivo
`0600` na pasta do usuário já tem a conta do sistema operacional em que o banco,
os PDFs e as chaves de API vivem. Uma senha por cima disso não acrescentaria
barreira — acrescentaria uma tela que o app de mesa passaria a vida tentando
contornar.

Se o token precisar ser trocado, apague o arquivo e reabra o aplicativo:

| Sistema | Caminho |
|---|---|
| Windows | `%LOCALAPPDATA%\RSAC\RSAC\runtime_token` |
| macOS | `~/Library/Application Support/RSAC/runtime_token` |
| Linux | `~/.local/share/RSAC/runtime_token` |

`RSAC_DATA_DIR` muda a pasta inteira, para quem queira a revisão noutro disco.

As chaves de API das fontes e dos provedores de IA ficam **cifradas em
repouso** no banco, com uma chave-mestra gerada em `master.key` (também `0600`)
na primeira execução. `RSAC_SECRET_KEY` tem precedência, para quem prefira
guardá-la fora do disco da máquina.

O plano de segurança ([`30_PLANO_EXECUCAO_SEGURANCA.md`](./planejamento/30_PLANO_EXECUCAO_SEGURANCA.md))
foi **concluído**: os 18 achados do [`28_DIAGNOSTICO_SEGURANCA.md`](./planejamento/28_DIAGNOSTICO_SEGURANCA.md)
estão fechados, cobertos por testes dedicados e por uma CI que impede que
voltem. O que mudou depois deles — a remoção do perfil publicável, das contas e
das sessões — está registrado em
[`37_SIMPLIFICACAO_DO_PERIMETRO.md`](./planejamento/37_SIMPLIFICACAO_DO_PERIMETRO.md),
que é o documento vigente sobre o assunto.

---

## Indicadores (B.I. e Bibliometria)

A aba **Indicadores**, entre Extração e Exportação, mostra estatística descritiva e de processo da revisão: funil PRISMA e de critérios, composição da amostra, rankings de periódico/autor/instituição, saúde de aquisição de PDF e proveniência de IA. Não é bibliometria de citação — o RSAC não coleta contagem de citações nem palavras-chave por artigo hoje.

O plano de B.I. ([`33_PLANO_EXECUCAO_BI.md`](./planejamento/33_PLANO_EXECUCAO_BI.md)) foi **concluído** em quatro fases, cobertas por 31 testes de backend e verificadas ao vivo contra um servidor real. Diagnóstico do que o modelo de dados sustenta em [`31_DIAGNOSTICO_BI.md`](./planejamento/31_DIAGNOSTICO_BI.md); contrato normativo em [`32_ESPECIFICACAO_BI.md`](./planejamento/32_ESPECIFICACAO_BI.md).

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
