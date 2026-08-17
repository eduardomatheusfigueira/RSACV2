# RSAC V2 — Revisão Sistemática Assistida por Computador

<div align="center">

<img src="brand/svg/rsac-lockup-dark.svg#gh-dark-mode-only" alt="RSAC V2" height="76" />
<img src="brand/svg/rsac-lockup-light.svg#gh-light-mode-only" alt="RSAC V2" height="76" />

![RSAC V2 Banner](https://img.shields.io/badge/RSAC_V2-v2.0.0-283618?style=for-the-badge&logo=electron&logoColor=fefae0)
![Estágio](https://img.shields.io/badge/Estágio-BETA-dda15e?style=for-the-badge&labelColor=283618)
![Python Version](https://img.shields.io/badge/Python-3.12+-606c38?style=for-the-badge&logo=python&logoColor=fefae0)
![React Version](https://img.shields.io/badge/React-19.0-bc6c25?style=for-the-badge&logo=react&logoColor=fefae0)
![License](https://img.shields.io/badge/License-MIT-dda15e?style=for-the-badge)

**Plataforma Desktop Profissional para Condução Rigorosa de Revisões Sistemáticas e de Escopo da Literatura Científica**

</div>

---

## 📖 Visão Geral

O **RSAC V2** é a evolução de segunda geração do ambiente de Revisões Sistemáticas Assistidas por Computador. Desenvolvido para pesquisadores, acadêmicos e cientistas de dados, o software combina a velocidade e robustez de um backend em **Python (FastAPI / SQLAlchemy)** com a fluidez de uma interface desktop moderna em **Electron / React 19 / TypeScript / Vite**.

A plataforma cobre integralmente o ciclo de vida da pesquisa secundária conforme as diretrizes internacionais (**PRISMA 2020**, **PRISMA-ScR**, **JBI**, **Cochrane**, **MECIR**, **ROSES**, **Campbell Collaboration** e **CEE**), com ênfase em rigor metodológico, reprodutibilidade e zero alucinação.

---

## ✨ Principais Funcionalidades

### 1. 🗂️ Gestão de Projetos & Diretrizes Metodológicas
- **11 diretrizes metodológicas pré-configuradas**, cada uma com sua matriz de auditoria de conformidade:
  - **PRISMA-ScR (Tricco et al., 2018)**: Revisões de Escopo (*Scoping Reviews*) — 22 itens
  - **PRISMA 2020 (Page et al., 2021)**: Revisão Sistemática com/sem Meta-análise — 27 itens
  - **PRISMA-P (Moher et al., 2015)**: Protocolo e registro prospectivo — 17 itens
  - **JBI (Joanna Briggs Institute)**: Metassíntese qualitativa e evidências mistas
  - **Cochrane Handbook & MECIR**: Padrão ouro em síntese de intervenções
  - **Campbell Collaboration (MECCIR)**: Políticas sociais, educação, economia e desenvolvimento
  - **CEE / ROSES**: Evidências socioambientais e gestão de recursos naturais
  - **EBSE (Kitchenham & Charters, 2007)**: Engenharia de software baseada em evidência
  - **Revisão Guarda-Chuva (PRIOR)**: Síntese de revisões, com controle de sobreposição
  - **Methodi Ordinatio (Pagani et al., 2015)**: Portfólio bibliográfico ordenado por InOrdinatio
  - **Outra / Personalizada**: Núcleo comum às diretrizes de síntese de evidência
- O catálogo declara a proveniência de cada lista: numeração oficial reproduzida onde a diretriz publica uma, e organização por domínios (com a citação da fonte) onde o documento é um formulário por seções — ver [`frontend/src/data/protocolChecklists.ts`](frontend/src/data/protocolChecklists.ts).
- Estruturação completa em frameworks de questão: **PICO**, **PCC**, **PICOS**, **SPICE** e **SPIDER**.
- Estratégia de descritores de busca estruturada em pares compatível com o motor **VuFind da BDTD**.

### 2. 🌐 Coleta Automatizada (*Harvesters*)
- Integração nativa e assíncrona com as principais bases científicas nacionais e internacionais:
  - **BDTD** (Biblioteca Digital Brasileira de Teses e Dissertações — OAI-PMH & VuFind)
  - **SciELO** (Scientific Electronic Library Online)
  - **PubMed / MEDLINE** (NCBI E-Utilities)
  - **Scopus / ScienceDirect** (Elsevier API)
  - **OpenAlex** (Scholarly Graph API)
  - **arXiv** & Importadores de arquivos **RIS / BibTeX / CSV / XLSX**
- Sistema de desduplicação probabilística e exata (DOI, Title Levenshtein Distance e Ano).

### 3. 🎯 Triagem de Estudos (Triagem 1 — Título & Resumo)
- Triagem com suporte a **Modo 100% Manual** ou **Assistido por I.A.** (com justificativa ancorada e zero alucinação).
- Atalhos de teclado para alta produtividade (`I` = Incluir, `E` = Excluir, `P` = Pendente).
- Filtros por decisão, base de dados, ano e busca textual instantânea.

### 4. 📊 Extração de Dados & Texto Integral (Triagem 2)
- **Localizador de PDF multi-estratégia**: o link coletado pelas bases raramente é o arquivo — é a página do registro (DOI, PubMed, SciELO, repositório institucional). O sistema busca o texto completo em 9 vias combinadas (padrões de repositório, Unpaywall, OpenAlex, Semantic Scholar, Crossref, Europe PMC e raspagem da página de origem), com validação de conteúdo e trilha auditável de cada tentativa.
- **Busca em lote** de todos os estudos incluídos, com progresso e cancelamento.
- **Leitor integrado** com três modos — Resumo, PDF renderizado no próprio app e Texto extraído — com paginação preservada, limpeza tipográfica (de-hifenização, remoção de cabeçalho/rodapé) e detecção de documentos digitalizados.
- Extração tabular estruturada com base no formulário configurado no protocolo, com **evidência ancorada**: cada resposta assistida traz o trecho literal e a página de origem no PDF.
- Análise de mecanismos causais, populações/atores, conceitos e contextos territoriais.

### 5. 📄 Exportação Científica
- Geração automática do **Diagrama de Fluxo PRISMA 2020** com contagem exata em cada fase.
- Exportação em **Markdown**, **Word (.docx)**, **Planilhas Excel/CSV** e pacotes de citações **BibTeX/RIS**.

### 6. 🎨 Identidade Visual, Design System & 13 Paletas de Cores
- **Monograma "R-Lupa"**: o "R" de *Revisão* desenhado em traço monolinear único, em que o laço da letra é a **lente** de uma lupa e a perna diagonal é o **cabo**. A geometria é declarada uma única vez e alimenta o ícone do executável, o instalador NSIS, o favicon e o símbolo dentro do app — ver [`brand/IDENTIDADE_VISUAL.md`](brand/IDENTIDADE_VISUAL.md).
- **Marca sem cor fixa**: dentro do app a haste e a lente herdam a cor de texto e o cabo herda a cor de acento, então o símbolo se re-pigmenta sozinho em qualquer uma das 13 paletas.
- **Selo BETA** presente na splash, no cabeçalho, na sidebar, na barra de status e nos ícones de distribuição — o produto ainda está em desenvolvimento.
- Identidade visual contemporânea de engenharia com cantos de precisão cirúrgica (`2px`).
- Catálogo com **13 paletas cromáticas harmônicas** ajustadas para leitura prolongada:
  - *Organic Earth (Florestal / Soft Warm)*
  - *Molten Lava & Deep Space*
  - *Pastel Dream & Thistle*
  - *Ink Black & Stormy Tangerine*
  - *Platinum & Dusk Blue*
  - *Indigo Bloom & Brilliant Rose*
  - *Dark Amethyst & Royal Violet*
  - *Parchment & Almond Silk*
  - *Alice Blue & Baby Blue Ice*
  - *Hot Fuchsia & Cotton Candy*
  - *Powder Blush & Icy Aqua*
  - *Synthwave Neon & Electric Sapphire*

### 7. 📡 Painel de Logs em Tempo Real
- Gaveta lateral de auditoria em tempo real via **WebSocket**.
- Detalhamento de cada etapa dos harvesters, deduplicação, chamadas de IA e persistência.

---

## 🏗️ Arquitetura Tecnológica

```
┌────────────────────────────────────────────────────────┐
│               RSAC V2 Desktop App                     │
├──────────────────────────┬─────────────────────────────┤
│   FRONTEND (Electron)    │     BACKEND (Python)        │
│   • Electron 33          │     • Python 3.12+          │
│   • React 19             │     • FastAPI (REST + WS)   │
│   • TypeScript 5         │     • SQLAlchemy 2.0        │
│   • Vite 6               │     • SQLite / Aiosqlite    │
│   • Zustand (State)      │     • Pydantic V2           │
│   • Lucide Icons         │     • Harvesters Assíncronos│
└──────────────────────────┴─────────────────────────────┘
```

---

## 🚀 Como Executar

### Pré-requisitos
- **Python 3.12+** instalado
- **Node.js 20+** e **npm 10+** instalados
- **Git**

### 1. Clonar o Repositório
```bash
git clone https://github.com/eduardomatheusfigueira/RSACV2.git
cd RSACV2
```

### 2. Configurar o Backend (Python)
```bash
cd backend
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate

pip install -e ".[dev]"
```

### 3. Configurar o Frontend (Electron/React)
```bash
cd ../frontend
npm install
```

### 4. (Opcional) Configurar o e-mail de contato para busca de PDF
As APIs de acesso aberto usadas na localização de PDFs (Unpaywall, OpenAlex, Crossref) dão prioridade — e no caso do Unpaywall, exigem — identificação por e-mail. Crie `backend/.env` com:
```
RSAC_CONTACT_EMAIL=seu-email@instituicao.br
```

### 5. Iniciar a Aplicação
```bash
# Opção 1: Usando o script unificado (Windows PowerShell)
.\scripts\dev.ps1

# Opção 2: Em terminais separados
# Terminal 1 (Backend):
cd backend
python run.py --port 8000 --reload --debug

# Terminal 2 (Frontend):
cd frontend
npm run dev
```

---

## 📚 Documentação Técnica

O diretório [`planejamento/`](./planejamento/) contém 22 especificações arquiteturais detalhadas:

1. `00_INDICE.md` — Índice e mapa do repositório
2. `01_DIAGNOSTICO_V1.md` — Lições aprendidas da V1
3. `02_VISAO_PRODUTO_V2.md` — Escopo do produto
4. `03_STACK_TECNOLOGICA.md` — Especificação das tecnologias
5. `04_ARQUITETURA_GERAL.md` — Diagramas de blocos e fluxo de dados
6. `05_BACKEND_PYTHON_API.md` — Rotas e contratos OpenAPI
7. `06_FRONTEND_ELECTRON.md` — Componentes e design system
8. `07_ESTRUTURA_DIRETORIOS.md` — Estrutura física de arquivos
9. `08_PIPELINE_DADOS.md` — Harvesters e processamento
10. `09_INTEGRACOES_IA.md` — Integrações com LLMs (Gemini, Qwen, Locais)
11. `10_BANCO_DE_DADOS.md` — Esquema relacional SQLite
12. `11_TESTES_QUALIDADE.md` — Estratégia de testes
13. `12_ROADMAP_FASES.md` — Histórico e fases de entrega
14. `13_DIAGNOSTICO_COLETA_V2.md` — Diagnóstico crítico dos coletores (harvesters)
15. `14_ESPECIFICACAO_COLETA.md` — Contrato de coleta, filtros e credenciais por fonte
16. `15_PLANO_EXECUCAO.md` — Plano de correção dos coletores
17. `16_TESTES_VALIDACAO.md` — Validação de paridade V1 ↔ V2 da coleta
18. `17_GUIA_DE_USO.md` — Manual de operação do aplicativo
19. `18_DIAGNOSTICO_PDF_EXTRACAO.md` — Diagnóstico da obtenção de PDF, leitura e extração assistida
20. `19_ESPECIFICACAO_AQUISICAO_PDF.md` — Contrato do resolvedor multi-estratégia de PDF e do pipeline de texto
21. `20_PLANO_EXECUCAO_PDF.md` — Fases de implementação do subsistema de PDF
22. `21_TESTES_VALIDACAO_PDF.md` — Estratégia de testes e roteiro de validação em acervo real

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte `LICENSE` para mais informações.
