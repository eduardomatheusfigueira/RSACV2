# 31 — Diagnóstico: B.I. e Bibliometria

## 1. Objetivo

Levantar o que o RSAC V2 já tem de dado para sustentar uma aba de indicadores
(Business Intelligence e bibliometria) após a Extração, e o que falta. O
diagnóstico é a base para a especificação (doc 32) e o plano de execução
(doc 33) — decide o que entra na v1 porque o dado já existe e é confiável, e o
que fica como extensão futura porque exigiria captura de dado novo.

Escopo da aba: estatísticas descritivas e de processo sobre um projeto de
revisão — não é um produto de bibliometria de citação (h-index, redes de
cocitação), porque essa camada de dado não existe no RSAC hoje. A seção 4
detalha a diferença.

## 2. Inventário de dados existentes

O modelo relacional (`backend/app/infrastructure/persistence/models.py`) já
carrega, por artigo, praticamente tudo que uma revisão sistemática precisa
reportar no PRISMA e nos indicadores de processo.

### 2.1 `PaperModel` — o registro central

| Campo | Uso em B.I. |
|---|---|
| `authors` (texto, `"; "` entre nomes — ver §3.1) | Ranking de autores mais frequentes |
| `journal` | Ranking de periódicos |
| `institution` | Ranking de instituições/afiliações |
| `year` | Distribuição temporal de publicações |
| `research_type` | Distribuição por tipo de estudo |
| `decision` (`Incluído`/`Excluído`/`Pendente`) | Funil PRISMA, taxa de inclusão |
| `is_duplicate` | Exclusão de duplicatas dos agregados (mesmo padrão do endpoint `/stats` existente) |
| `pdf_status`, `pdf_is_scanned`, `pdf_text_chars` | Indicadores de saúde da aquisição de PDF |
| `ai_confidence` | Distribuição de confiança das decisões assistidas |
| `created_at` | Linha do tempo de entrada de registros no projeto |

### 2.2 `PaperSourceModel` — proveniência por base

Um artigo pode ter vindo de mais de uma base (BDTD, SciELO, PubMed, Scopus,
OpenAlex, arXiv, importação de arquivo). Já é a fonte do agregado
`source_counts` em `GET /api/v1/projects/{id}/stats`
(`backend/app/api/v1/projects.py:169`) — a nova aba generaliza esse padrão:
volume por base, mas cruzado com decisão (quantos de cada base foram
incluídos, não só encontrados).

### 2.3 `CriterionModel` + `PaperCriterionModel` — funil de critérios

Cada critério (inclusão ou exclusão) tem uma avaliação booleana por artigo.
Isso é dado que hoje **não aparece em lugar nenhum da interface** fora da
ficha individual do artigo — é o material bruto para o pedido explícito do
usuário ("critérios de inclusão/exclusão"): quantos artigos atendem a cada
critério de inclusão, quantos caem em cada critério de exclusão. É o gráfico
de funil mais informativo que a aba pode ter, porque explica *por que* a
amostra ficou do tamanho que ficou.

### 2.4 `HarvestRunModel` — linha do tempo de coleta

`records_found`, `records_new`, `records_duplicate`, `started_at`,
`completed_at`, por base. Já alimenta `get_prisma_flow_data`
(`backend/app/services/export_service.py:240`) para os totais de
identificação; dá para expandir em uma visão temporal de quando cada base foi
consultada e quanto cada rodada trouxe.

### 2.5 `AuditLogModel` — quem decidiu, e como

Desde a Fase 5 do plano de segurança, todo registro carrega `user_id`,
`username`, `source` (`manual` vs `ia`), `ai_provider`, `ai_model` e
`ai_response_valid`. Isso habilita um indicador que nenhuma revisão
sistemática tradicional tem de graça: throughput de triagem por pessoa, e
proporção de decisões assistidas por IA que precisaram de revisão humana
(`ai_response_valid = false`, doc 28 V-16).

### 2.6 `ExtractionAnswerModel` — respostas da matriz de extração

Texto livre por pergunta de protocolo, sem vocabulário controlado. Não dá
para agregar em categorias (cada protocolo define suas próprias perguntas em
linguagem natural). O indicador viável aqui é de **completude**: percentual
de perguntas respondidas por artigo incluído, não o conteúdo das respostas.

## 3. Qualidade e riscos do dado

### 3.1 Nomes não normalizados

`authors`, `journal` e `institution` são texto livre vindo de bases
heterogêneas. Os harvesters usam `"; "` como separador de autores de forma
consistente (`app/harvesters/{bdtd,openalex,pubmed,scielo}.py`), mas:

- Registros importados manualmente (RIS/BibTeX/CSV) podem não seguir essa
  convenção.
- Não há desambiguação de autor: "Silva, J." e "Silva, João" contam como
  duas pessoas; um mesmo nome grafado com e sem acento também. O ranking de
  autores é **aproximado por construção**, e a interface precisa dizer isso
  — não é um erro a corrigir na v1, é uma propriedade do dado de origem.
- `journal`/`institution` têm a mesma limitação: variação de maiúsculas,
  abreviação (`"USP"` vs `"Universidade de São Paulo"`) fragmenta contagens
  que deveriam ser uma só. A normalização mínima viável é `trim` + colapso de
  espaços + comparação case-insensitive para agrupar, mantendo o rótulo mais
  frequente como exibição — não uma tentativa de desambiguação semântica.

### 3.2 Artigos pendentes distorcem indicadores de conteúdo

Enquanto a triagem não termina, boa parte dos artigos está com
`decision = "Pendente"` e sem os campos de extração preenchidos. Rankings de
periódico/autor/instituição fazem mais sentido restritos aos incluídos (ou
com filtro explícito por decisão) do que sobre a base bruta — do contrário o
gráfico mistura "o que a busca trouxe" com "o que a revisão vai de fato
sintetizar", que são perguntas diferentes.

### 3.3 Volume e performance

Revisões sistemáticas no RSAC giram tipicamente na casa de centenas a poucos
milhares de registros por projeto (a base é achado, não hipótese: os
harvesters existentes lidam com volumes dessa ordem). Agregação em Python
sobre a lista completa, como já acontece em `get_prisma_flow_data`, é viável
nesse volume. Não há indicação de que o projeto precise de cache ou de
pré-computação — mas os agregados por texto livre (autor/periódico/
instituição) devem ser feitos com `GROUP BY` no SQL sempre que possível
(mesmo padrão do `source_counts` em `projects.py:186`), não carregando todos
os `PaperModel` para memória e agrupando em Python, que é o que
`get_prisma_flow_data` faz hoje e que não escala tão bem quanto agregação no
banco.

## 4. O que não é possível hoje sem captura de dado novo

Bibliometria no sentido estrito (índice H, contagem de citações, redes de
cocitação, análise de acoplamento bibliográfico) depende de dado que o RSAC
não coleta:

- **Contagem de citações**: nenhum harvester grava `cited_by_count`. OpenAlex
  e Crossref — já integrados como fontes de resolução de PDF
  (`app/services/pdf_resolver.py`) — expõem esse campo; adicioná-lo seria
  uma extensão de escopo de coleta, não de exibição, e fica fora deste plano.
- **Palavras-chave por artigo**: não existe campo `keywords` em `PaperModel`.
  (Existe um campo `keywords` órfão em `Protocol`, no domínio —
  `app/domain/entities.py:102` — mas é o vocabulário de busca do protocolo,
  nunca persistido em `ProtocolModel` nem lido por ninguém; não tem relação
  com os artigos coletados.) Nuvem de palavras-chave ou coocorrência de
  termos ficam fora da v1.
- **País/afiliação estruturada**: `institution` é texto livre; não há campo
  de país. Mapas de distribuição geográfica não são viáveis sem
  geocodificação heurística do texto livre, que é um projeto à parte.

Essas três lacunas são anotadas como possíveis fases futuras na
especificação (doc 32, §7), não como bloqueio da v1.

## 5. Onde a aba entra na arquitetura atual

### 5.1 Navegação

A esteira de trabalho hoje é um `RIBBON_TABS` de 5 passos em
`frontend/src/components/layout/TopRibbonBar.tsx:79-88`: Protocolo → Coleta →
Triagem → Extração → Síntese & Exportar. O pedido do usuário ("uma aba após a
extração") encaixa como um sexto passo entre Extração e Exportação —
renumerando Exportação de `stepNumber: 5` para `6`.

### 5.2 Backend

Não existe hoje nenhum endpoint de agregação além de `/stats` (contadores
brutos) e `/export/prisma` (funil de identificação). A nova aba precisa de
endpoint(s) próprio(s) em `app/api/v1/`, cobertos pelo mesmo agregador de
sessão que protege todo o resto da API (`api_router` em
`app/api/v1/router.py`, dependência `require_session`) — não é preciso nada
novo em autenticação.

### 5.3 Frontend

**Não há biblioteca de gráficos no projeto** (`frontend/package.json` só
tem Radix UI, TanStack Query, Zustand, `lucide-react`). O único gráfico
existente hoje — o diagrama de fluxo PRISMA em `ExportPage.tsx` — é
desenhado à mão em HTML/CSS, o que funciona para um fluxograma fixo de poucas
caixas, mas não para séries temporais, rankings ou funis com N categorias
variáveis. A escolha de biblioteca é decisão da especificação (doc 32, §5).

Todo componente visual do RSAC está sob a regra de tokens de design
(`npm run verify`, `scripts/lint-design-tokens.mjs`, regras R1–R8 do doc 24)
— cor, espaçamento, raio e duração de movimento não podem ser literais soltos
no CSS. A biblioteca de gráficos escolhida precisa aceitar cor por variável
(token), não vir com paleta fixa embutida.
