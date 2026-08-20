# 📋 RSAC V2 — Índice do Planejamento

> **Revisão Sistemática Assistida por Computador — Versão 2.0**  
> **Arquitetura Python + Electron | Agosto 2026**  
> **Estrutura:** `01–21` Histórico · `22` Log de Auditoria · `23–27` Vigente (Design System & Governança) · `28–30` Concluído (Segurança) · `31–33` Concluído (B.I. e Bibliometria) · `34–35` Vigente (Coleta)

---

## Como ler esta pasta

Os documentos **01 a 21** são **histórico**. Descrevem o planejamento que levou
o produto ao estado consolidado de 17/08/2026 e devem ser lidos como registro
de decisão, não como lista de pendências.

O **doc 22** é a fronteira: consolida o que cada plano anterior previu, o que
foi entregue, o que divergiu e o que segue aberto.

Os documentos **23 a 27** são o **planejamento vigente** de UX, UI e
profissionalização da interface. Seguem a mesma gramática dos planos temáticos
anteriores — diagnóstico → especificação → execução → validação.

Os documentos **28 a 30** registram o **planejamento de segurança**, aberto
quando o aplicativo passou a ter um servidor publicado na internet
(`Iniciar_Servidor.bat`) e **concluído** — as seis fases estão entregues.

Os documentos **31 a 33** registram o **planejamento de B.I. e
bibliometria**, aberto para dar à revisão uma aba de indicadores após a
Extração, e **concluído** — as quatro fases estão entregues.

Os documentos **34 e 35** são o **planejamento vigente da coleta**:
diagnóstico medido dos coletores SciELO e BDTD, e o plano de robustez e
velocidade que dele decorre. Mesma gramática — diagnóstico → execução.

```
01–21   histórico          o que nos trouxe até aqui
  22    log de entregas    o que ficou pronto, o que divergiu, o que sobrou
23–27   vigente            design system e UX/UI
28–30   concluído          segurança — as seis fases entregues ✅
31–33   concluído          B.I. e bibliometria — as quatro fases entregues ✅
34–35   vigente            confiabilidade e velocidade da coleta
```

---

## 📌 Planejamento vigente — UX, UI e profissionalização

| # | Documento | Descrição |
|---|-----------|-----------|
| **22** | [Log de Entregas](./22_LOG_ENTREGAS.md) | Consolidação verificada dos planos 01–21: entregue, divergente e aberto |
| **23** | [Diagnóstico de UX e UI](./23_DIAGNOSTICO_UX_UI.md) | Análise crítica da interface, medida contra o código e o app em execução |
| **24** | [Especificação do Design System](./24_ESPECIFICACAO_DESIGN_SYSTEM.md) | Documento normativo: tokens, proporções, componentes, fluxo e acessibilidade |
| **25** | [Plano de Execução — UX e UI](./25_PLANO_EXECUCAO_UX_UI.md) | Sete fases com dependências, critérios de aceite e riscos |
| **26** | [Testes e Validação — UX e UI](./26_TESTES_VALIDACAO_UX_UI.md) | Quatro camadas de verificação e portões por fase |
| **27** | [Previsão do Trabalho Restante](./27_PREVISAO_TRABALHO_RESTANTE.md) | O que falta medido no código, em que ordem fazer e o que fica de fora |

> A identidade visual da marca tem documento próprio, fora desta pasta:
> [`brand/IDENTIDADE_VISUAL.md`](../brand/IDENTIDADE_VISUAL.md).

---

## ✅ Segurança do servidor — plano concluído

> O plano de segurança foi **concluído**: os 18 achados do doc 28 estão
> fechados, e a CI (`.github/workflows/ci.yml`) impede que voltem. O doc 28
> registra o estado que motivou o trabalho; o doc 30 registra o que foi
> entregue em cada fase, com as divergências justificadas.

| # | Documento | Descrição |
|---|-----------|-----------|
| **28** | [Diagnóstico de Segurança](./28_DIAGNOSTICO_SEGURANCA.md) | Modelo de ameaça, superfície de ataque medida e 18 vulnerabilidades com evidência em `arquivo:linha` |
| **29** | [Especificação de Segurança](./29_ESPECIFICACAO_SEGURANCA.md) | Documento normativo: perfis de implantação, autenticação, cifra de segredos, política de saída e cabeçalhos |
| **30** | [Plano de Execução — Segurança](./30_PLANO_EXECUCAO_SEGURANCA.md) | Seis fases, critérios de aceite e a suíte de testes que impede a regressão |

---

## ✅ B.I. e Bibliometria — plano concluído

> O plano de B.I. foi **concluído**: a aba de Indicadores está entregue com
> funil PRISMA e de critérios, composição da amostra, rankings de
> periódico/autor/instituição, saúde de PDF, filtros de decisão/base/ano e
> proveniência de IA — coberta por 31 testes de backend e verificada ao
> vivo contra um servidor real. O doc 31 registra o que motivou o trabalho;
> o doc 33 registra o que foi entregue em cada fase, com as divergências
> justificadas.

| # | Documento | Descrição |
|---|-----------|-----------|
| **31** | [Diagnóstico de B.I.](./31_DIAGNOSTICO_BI.md) | Inventário do que o modelo de dados já sustenta, qualidade do dado e lacunas para bibliometria de citação |
| **32** | [Especificação de B.I.](./32_ESPECIFICACAO_BI.md) | Documento normativo: contrato da API, normalização de texto livre, biblioteca de gráficos e métricas da v1 |
| **33** | [Plano de Execução — B.I.](./33_PLANO_EXECUCAO_BI.md) | Quatro fases, do endpoint de agregação à aba navegável com filtros e proveniência de IA |

---

## 📌 Planejamento vigente — confiabilidade e velocidade da coleta

| # | Documento | Descrição |
|---|-----------|-----------|
| **34** | [Diagnóstico da Coleta — SciELO e BDTD](./34_DIAGNOSTICO_COLETA_SCIELO_BDTD.md) | Estado real dos dois coletores nacionais, com linha de base medida sem rede |
| **35** | [Plano de Robustez e Velocidade](./35_PLANO_ROBUSTEZ_VELOCIDADE_COLETA.md) | Sete fases: verdade → correção → ritmo → paralelismo → retomada → interface → testes |

> A linha de base numérica dos docs 34 e 35 é reproduzível por
> [`backend/scripts/bench_coleta.py`](../backend/scripts/bench_coleta.py),
> que roda sem rede e serve de portão de regressão de desempenho.

---

## 📚 Histórico — planejamento da V2 (01–21)

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
| 13 | [Diagnóstico da Coleta V2](./13_DIAGNOSTICO_COLETA_V2.md) | Análise crítica dos coletores e do pipeline de coleta da V2 |
| 14 | [Especificação da Coleta](./14_ESPECIFICACAO_COLETA.md) | Contrato de coleta, filtros e credenciais por fonte |
| 15 | [Plano de Execução da Coleta](./15_PLANO_EXECUCAO.md) | Fases de correção dos coletores, com critérios de aceite |
| 16 | [Testes e Validação da Coleta](./16_TESTES_VALIDACAO.md) | Estratégia de validação de paridade V1 ↔ V2 |
| 17 | [Guia de Uso](./17_GUIA_DE_USO.md) | Manual de operação do aplicativo |
| 18 | [Diagnóstico de PDF e Extração](./18_DIAGNOSTICO_PDF_EXTRACAO.md) | Análise crítica da obtenção do texto completo, leitura e extração assistida |
| 19 | [Especificação da Aquisição de PDF](./19_ESPECIFICACAO_AQUISICAO_PDF.md) | Resolvedor multi-estratégia, pipeline de texto, contexto de IA e contrato HTTP |
| 20 | [Plano de Execução — PDF](./20_PLANO_EXECUCAO_PDF.md) | Fases do subsistema de PDF, estado de cada uma e dívidas registradas |
| 21 | [Testes e Validação — PDF](./21_TESTES_VALIDACAO_PDF.md) | Suíte automatizada sem rede e roteiro de validação em acervo real |

---

## Referência Bibliográfica Base

- **Adam D. Scott** — *JavaScript Everywhere: Building Cross-Platform Applications with GraphQL, React, React Native, and Electron* (O'Reilly Media, 2020)
  - Modelo arquitetural: **FastAPI (Python Backend) → React (Frontend) → Electron (Desktop Shell)**

---

## Convenções de Status

- 🟢 = Documento normativo vigente
- 🏛️ = Documento de referência histórica
- 🟡 = Em discussão / aguardando validação
- 🔴 = Bloqueante / risco identificado
- 📖 = Referência ao livro *JavaScript Everywhere*
- ✅ = Entregue e verificado no repositório
- ⬜ = Aberto
- 🟠 = Gravidade média (docs 23–26)
