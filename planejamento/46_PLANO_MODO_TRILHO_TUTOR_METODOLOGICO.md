# 46 — Plano do Modo Trilho: Tutor Metodológico Guiado

> **Status:** 🟡 Proposta de Especificação e Arquitetura.
> **Conceito Central:** Modo de navegação assistida e tutoria metodológica passo a passo ("Modo Trilho"), operando como um tutor experiente ao lado do pesquisador, destacando elementos na tela, explicando o porquê de cada etapa e oferecendo bifurcações determinísticas de tomada de decisão.
> **Regra de Ouro:** **100% Determinístico, ZERO Inteligência Artificial.** Toda orientação, árvore de decisão, recomendação de bifurcação e checklist decorre estritamente da literatura metodológica consolidada (PRISMA, JBI, Cochrane, MECIR, Galvão & Pereira, CEE, SPAR-4-SLR).
> **Domínio de Aplicação:** Ciências Sociais Aplicadas & Desenvolvimento Regional (conforme `.agents/AGENTS.md`).

---

## 1. Sumário Executivo & Princípio de Concepção

Uma das maiores dores de pesquisadores em revisões sistemáticas e de escopo é a **ansiedade metodológica**: *O que devo preencher agora? Por que este campo é necessário? Qual caminho devo escolher entre desenho X e Y? Minha busca está correta? Como calibro a triagem?*.

O **Modo Trilho** transforma o Revsist em um **ambiente de tutoria metodológica ativa**. Não se trata de um simples "tour de onboarding" que o usuário fecha no primeiro clique, mas de uma **camada de acompanhamento contínuo e contextual** que pode ser ligada ou pausada a qualquer momento através do alternador `[ Modo Trilho: Ativo / Pausado ]`.

```
┌────────────────────────────────────────────────────────────────────────────┐
│ MODO TRILHO: TUTOR METODOLÓGICO ATIVO                                     │
│                                                                            │
│ ┌──────────────┐     ┌─────────────────────┐     ┌───────────────────────┐ │
│ │  Spotlight   │ ──> │   Painel do Tutor   │ ──> │ Árvore de Decisão     │ │
│ │ (Foco visual │     │ (Explicação 'o quê' │     │ (Bifurcação A vs B    │ │
│ │   no campo)  │     │   e 'por que')      │     │  sem IA, determinista)│ │
│ └──────────────┘     └─────────────────────┘     └───────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. As 7 Etapas da Jornada Metodológica no Modo Trilho

O Trilho organiza toda a construção da revisão em **7 Etapas Sequenciais**, baseadas nos 8 passos canônicos de Galvão & Pereira (2014) e nos portões do pipeline do Revsist:

```mermaid
flowchart LR
    E0["0. Intenção & Escopo"] --> E1["1. Desenho & Pergunta"]
    E1 --> E2["2. Modo do Protocolo"]
    E2 --> E3["3. Estratégia de Busca"]
    E3 --> E4["4. Coleta & Deduplicação"]
    E4 --> E5["5. Triagem & Calibração"]
    E5 --> E6["6. Extração de Evidências"]
    E6 --> E7["7. Síntese & Relato PRISMA"]
```

---

## 3. Fluxograma Completo de Bifurcações e Tomadas de Decisão

### 3.1. Etapa 0: Intenção & Escopo da Pesquisa

```mermaid
graph TD
    Start([Início da Jornada]) --> Q0{Qual é o objetivo principal do seu trabalho?}
    
    Q0 -->|A: Mapear conceitos, literatura e lacunas| D_Escopo[Caminho 1: Revisão de Escopo / Mapeamento]
    Q0 -->|B: Avaliar eficácia de políticas ou intervenções| D_Efetividade[Caminho 2: Revisão Sistemática de Efetividade / Políticas]
    Q0 -->|C: Analisar volume, redes de citação e coautoria| D_Biblio[Caminho 3: Estudo Bibliométrico]
    Q0 -->|D: Explorar percepções e experiências de atores locais| D_Quali[Caminho 4: Revisão Qualitativa / Mista]
    Q0 -->|E: Combinar estudos empíricos e teóricos diversos| D_Integ[Caminho 5: Revisão Integrativa]
    
    D_Escopo --> Sugere_D4[Recomenda Desenho D4 · PRISMA-ScR + Framework PCC]
    D_Efetividade --> Sugere_D14[Recomenda Desenho D14/D1 · PRISMA 2020 + Framework PICO/CIMO]
    D_Biblio --> Sugere_D9[Recomenda Desenho D9 · BIBLIO + Domínio-Recorte-Unidade]
    D_Quali --> Sugere_D5[Recomenda Desenho D5 · ENTREQ + Framework SPIDER/PICo]
    D_Integ --> Sugere_D11[Recomenda Desenho D11 · PRISMA 2020 + Framework PCC/PICO]
```

---

### 3.2. Etapa 1: Desenho Metodológico & Framework de Pergunta

Quando o usuário está no Estúdio de Protocolo, o Tutor abre a **Bifurcação de Seleção de Framework**:

```mermaid
graph TD
    F_Start([Definição da Pergunta]) --> Q_Frame{Qual o foco da sua pergunta de pesquisa?}
    
    Q_Frame -->|Foco em População, Conceito Central e Contexto Territorial| PCC_Path[Estrutura PCC]
    Q_Frame -->|Foco em População, Intervenção, Comparação e Desfecho| PICO_Path[Estrutura PICO]
    Q_Frame -->|Foco em Contexto, Intervenção, Mecanismo e Resultado de Gestão| CIMO_Path[Estrutura CIMO]
    Q_Frame -->|Foco em Amostra, Fenômeno de Interesse, Desenho e Avaliação| SPIDER_Path[Estrutura SPIDER]

    PCC_Path --> PCC_Action[Aponta para campos: População/Atores, Conceito, Contexto]
    PICO_Path --> PICO_Action[Aponta para campos: População, Intervenção, Comparador, Desfecho]
    CIMO_Path --> CIMO_Action[Aponta para campos: Contexto, Intervenção, Mecanismo, Resultado]
    SPIDER_Path --> SPIDER_Action[Aponta para campos: Amostra, Fenômeno, Desenho, Avaliação]
```

**Explicação Metodológica do Tutor:**
- *Se Revisão de Escopo (D4)*: "Em Ciências Sociais e Desenvolvimento Regional, revisões de escopo utilizam prioritariamente o framework **PCC (População, Conceito e Contexto)** recomendado pelo JBI Manual 2024. Exemplo: *População*: Cooperativas da agricultura familiar; *Conceito*: Governança territorial e inovação; *Contexto*: Semiárido brasileiro."
- *Se Avaliação de Políticas (D14)*: "Para analisar políticas territoriais, o framework **CIMO (Contexto, Intervenção, Mecanismo e Outcome)** de Denyer & Tranfield (2009) é ideal para capturar o contexto institucional e os mecanismos de governança pública."

---

### 3.3. Etapa 2: Escolha do Modo do Protocolo (Simplificado vs. Completo)

```mermaid
graph TD
    M_Start([Definição de Profundidade do Protocolo]) --> Q_Mode{Qual é a finalidade imediata do seu protocolo?}
    
    Q_Mode -->|Opção A: Quero executar buscas reproduzíveis e triagem rapidamente com PRISMA-S| Mode_Simp[Modo Simplificado · 14 Campos]
    Q_Mode -->|Opção B: Quero redigir o protocolo integral para publicação ou registro formal| Mode_Comp[Modo Completo · Gabarito Oficial]
    
    Mode_Simp --> Simp_Desc[Explica Carimbo de Escopo: Cobre PRISMA-S 16 itens + PRISMA 2020 5-7 + Extração. Não cobre registro prospectivo nem risco de viés.]
    Mode_Comp --> Comp_Desc[Oferece gabaritos PRISMA-P, JBI, CEE/ROSES, PRIOR ou Protocolo Revsist.]
```

---

### 3.4. Etapa 3: Estúdio de Busca Canônica & Decomposição em Pares

```mermaid
graph TD
    S_Start([Construção da Busca]) --> S_Step1[Passo 1: Criar Bloco A - População / Atores]
    S_Step1 --> S_Step2[Passo 2: Criar Bloco B - Conceito Central / Política]
    S_Step2 --> S_Step3[Passo 3: Criar Bloco C - Contexto / Recorte Opcional]
    
    S_Step3 --> S_Test{Deseja auditar a estratégia antes da coleta?}
    S_Test -->|Sim| PRESS_Run[Executa Auditoria PRESS 2016 nos 6 Domínios]
    S_Test -->|Não| S_Adapt[Verifica Adaptadores por Base]
    
    PRESS_Run --> S_Adapt
    
    S_Adapt --> BDTD_Notice[Regra BDTD: Decomposição em pares de até 2 termos para conformidade VuFind]
```

**Regras e Dicas do Tutor:**
- **Diretriz de Descritores**: Máximo de 2 termos por expressão booleana (ex: `"termo_1" AND "termo_2"`), no máximo 5 pares por idioma, evitando termos excessivamente genéricos ou restritivos.
- **Auditoria PRESS**: Verifica se há truncamentos ausentes, operadores booleanos invertidos ou parênteses desbalanceados.

---

### 3.5. Etapa 4: Coleta de Dados nas Bases & Deduplicação

```mermaid
graph TD
    C_Start([Coleta nas Bases]) --> C_Select[Seleção de Bases: BDTD, SciELO, Scopus, PubMed, OpenAlex]
    C_Select --> C_Exec[Disparar Coleta Automática]
    C_Exec --> C_Dedup[Algoritmo Automático de Deduplicação: DOI + Levenshtein de Títulos]
    C_Dedup --> C_Check{Existem duplicatas suspeitas não resolvidas?}
    C_Check -->|Sim| C_Review[Abre Relatório de Deduplicação para Revisão Manual]
    C_Check -->|Não| C_Done[Avança para Triagem com Base Limpa]
```

---

### 3.6. Etapa 5: Triagem (Screening) & Calibração

```mermaid
graph TD
    T_Start([Início da Triagem]) --> Q_Team{Como será realizada a triagem?}
    
    Q_Team -->|Pesquisador Individual| T_Indiv[Modo Individual: Leitura sequencial com registro de motivos]
    Q_Team -->|Equipe com 2 ou mais revisores| T_Double[Modo Dupla Cega: 2 revisores independentes por estudo]
    
    T_Double --> T_Pilot{Deseja rodar piloto de calibração primeiro?}
    T_Pilot -->|Recomendado| T_Pilot_Run[Piloto em 50 estudos + Cálculo do Coeficiente Kappa de Cohen]
    T_Pilot -->|Pular| T_Blind_Run[Triagem Cega Integral]
    
    T_Pilot_Run --> T_Blind_Run
    T_Blind_Run --> T_Conflict[Painel de Resolução de Divergências pelo Terceiro Revisor / Coordenador]
    T_Conflict --> T_Done[Avança para Extração de Evidências]
    T_Indiv --> T_Done
```

---

### 3.7. Etapa 6: Extração de Evidências & Matriz de Dados

```mermaid
graph TD
    E_Start([Extração de Dados]) --> E_Questions[Carrega Perguntas a Priori S11 cadastradas no Protocolo]
    E_Questions --> E_Form[Formulário de Extração por Estudo Incluído]
    E_Form --> E_Assist{Deseja auxílio na localização dos trechos nos PDFs?}
    E_Assist -->|Sim| E_Assisted[Modo Assistido: Destaca parágrafos e sugere respostas com rastreabilidade de página]
    E_Assist -->|Não| E_Manual[Preenchimento Manual pelo Pesquisador]
    E_Assisted --> E_Matrix[Matriz Consolidada de Evidências]
    E_Manual --> E_Matrix
    E_Matrix --> E_Done[Avança para Síntese e Relato]
```

---

### 3.8. Etapa 7: Síntese, Indicadores & Relato PRISMA

```mermaid
graph TD
    R_Start([Síntese & Relato]) --> R_Prisma[Geração do Diagrama de Fluxo PRISMA 2020]
    R_Prisma --> R_SearchLog[Geração do Registro de Busca PRISMA-S: DOCX, PDF, CSV, JSON]
    R_SearchLog --> R_Export[Exportação do Manuscrito Completo / Pacote de Evidências]
    R_Export --> R_Done([Revisão Metodológica Concluída com Sucesso!])
```

---

## 4. Especificação de Interface & Componentes Visuais (UI/UX)

### 4.1. Barra Flutuante / Dockable do Tutor (`TrilhoTutorBar`)
- **Posicionamento**: Barra inferior ou lateral retrátil, com visual Neo-Retro contemporâneo.
- **Elementos**:
  1. **Indicador de Fase & Progresso**: `[ Etapa 2 de 7: Estúdio de Busca Canônica ]` com barra de progresso.
  2. **Card "O que fazer agora"**: Instrução direta em 1 frase imperativa e clara.
  3. **Card "Por que fazer assim"**: Justificativa acadêmica curta com citação da diretriz (ex: *PRISMA-S item 3*).
  4. **Botão de Ação Direta**: `[ Focar no Campo ]` / `[ Abrir Bifurcação de Decisão ]`.
  5. **Controles de Navegação**: `[ < Anterior ]`, `[ Próximo > ]`, `[ Pausar Trilho ]`.

### 4.2. Sistema de Destaque Visual (`TrilhoSpotlight`)
- Utiliza atributos de dados nos elementos da interface: `data-trilho-target="protocol-objective"`, `data-trilho-target="search-blocks"`, `data-trilho-target="criteria-list"`, etc.
- Efeito de **coachmark com contorno de foco acolhedor** e badge indicativo flutuante sem escurecer agressivamente a tela, mantendo a legibilidade integral.

### 4.3. Modal de Bifurcação Metodológica (`TrilhoDecisionModal`)
- Quando a jornada atinge um ponto de escolha (ex: Escolha de Desenho, PCC vs PICO, Individual vs Dupla Cega), o modal apresenta **cartões comparativos lado a lado**:
  - **Opção A** vs **Opção B**.
  - *Quando escolher cada uma*.
  - *Exemplo prático em Ciências Sociais / Desenvolvimento Regional*.
  - *Impacto no fluxo de trabalho*.
  - Botão de aplicação direta que atualiza a configuração do projeto de forma transparente.

---

## 5. Arquitetura de Dados e Gerenciamento de Estado

### 5.1. Grafo do Trilho (`frontend/src/data/trilhoGraph.ts`)
Cada nó do grafo contém:
```typescript
export interface TrilhoNode {
  id: string
  phase: number
  title: string
  instruction: string
  rationale: string
  guidelineReference: string
  targetElementSelector?: string
  targetPageUrl?: string
  branchingQuestion?: {
    questionText: string
    options: {
      id: string
      label: string
      badge?: string
      description: string
      example: string
      consequences: string
      onSelectAction: (context: any) => Promise<void> | void
      nextNodeId: string
    }[]
  }
  validationRule?: (context: any) => { passed: boolean; message?: string }
  nextNodeId?: string
  previousNodeId?: string
}
```

### 5.2. Store Zustand (`frontend/src/stores/useTrilhoStore.ts`)
- `isActive: boolean`
- `currentNodeId: string`
- `completedNodes: string[]`
- `decisionHistory: Record<string, string>`
- `isMinimized: boolean`
- Ações: `startTrilho(nodeId?)`, `goToNext()`, `goToPrevious()`, `chooseBranch(optionId)`, `toggleTrilho()`, `minimize()`.
- Persistência sincronizada com o projeto ativo.

---

## 6. Plano de Execução em 4 Fases

| Fase | Escopo | Entregáveis |
|---|---|---|
| **Fase 1** | **Grafo Metodológico & Árvore de Decisão** | Arquivo `trilhoGraph.ts` completo com todos os nós, bifurcações, racional metodológico e validações determinísticas. |
| **Fase 2** | **Estado & Componentes de UI do Trilho** | `useTrilhoStore.ts`, `TrilhoTutorBar.tsx`, `TrilhoDecisionModal.tsx`, `TrilhoSpotlight.tsx` e `Trilho.css`. |
| **Fase 3** | **Instrumentação das Telas do Revsist** | Inclusão de `data-trilho-target` em `ProtocolPage`, `SearchStrategyStudio`, `HarvestingPage`, `ScreeningPage`, `ExtractionPage`, `InsightsPage`. |
| **Fase 4** | **Testes de Usabilidade, Acessibilidade & Validação** | Testes de navegação em todos os caminhos da árvore de decisão, validação de contrastes, modo teclado e build limpo. |

---

## 7. Critérios de Aceite e Conformidade

1. **Determinismo Absoluto**: Nenhuma chamada a modelos generativos ou provedores de IA para direcionar o Trilho. Todas as decisões e caminhos são regras metodológicas transparentes e auditáveis.
2. **Não-intrusividade**: O pesquisador pode ativar, pausar, avançar ou retroceder no Trilho a qualquer momento sem perder o trabalho preenchido.
3. **Aderência Normativa**: Toda justificativa ("por que fazer assim") cita diretrizes acadêmicas reconhecidas (PRISMA, JBI, Cochrane, etc.).
4. **Design System Integrado**: Todos os estilos utilizam estritamente a paleta e os tokens do Design System Neo-Retro Contemporâneo do Revsist.
