# 32 — Especificação: Aba de B.I. e Bibliometria

Documento normativo. `DEVE`/`NÃO DEVE`/`PODE` seguem RFC 2119. Fundamentado no
diagnóstico (doc 31); qualquer item aqui listado tem lastro em campo real do
modelo de dados atual, salvo os itens explicitamente marcados como extensão
futura (§7).

## 1. Escopo

A aba (nome de interface: **"Indicadores"**, rota `/projects/:id/insights`)
mostra estatística descritiva e de processo sobre o projeto corrente:
composição da amostra por decisão/base/período, funil de critérios,
rankings de periódico/autor/instituição, saúde da aquisição de PDF, e
throughput de triagem humana vs. assistida por IA.

**NÃO É** bibliometria de citação (h-index, cocitação, acoplamento
bibliográfico) nem análise de conteúdo (nuvem de palavras, coocorrência de
termos) — o diagnóstico (doc 31 §4) mostra que o dado para isso não existe
hoje. Esses itens ficam em §7 como extensão futura, não como parte desta
especificação.

## 2. Posicionamento na navegação

A aba DEVE aparecer como sexto passo em `RIBBON_TABS`
(`frontend/src/components/layout/TopRibbonBar.tsx`), entre Extração
(`stepNumber: 4`) e Exportação, que passa de `stepNumber: 5` para `6`. A nova
entrada usa `stepNumber: 5`, rota `/projects/:id/insights`,
`requiresProject: true`.

A aba DEVE funcionar a qualquer momento do fluxo — mesmo com o projeto ainda
na fase de coleta ou triagem — mostrando "sem dado suficiente" para os
gráficos cujo insumo (ex.: decisões, extração) ainda não existe, em vez de
ficar bloqueada até a Extração terminar. Retirar o acesso condicionaria a
uma leitura útil só depois de a revisão estar pronta, que é exatamente o
cenário em que a aba tem menos serventia.

## 3. Contrato da API

### 3.1 Endpoint

`GET /api/v1/projects/{project_id}/insights` DEVE devolver, em uma única
resposta, todos os agregados descritos em §6 — não um endpoint por gráfico.
Uma revisão sistemática típica no RSAC não passa de poucos milhares de
registros (doc 31 §3.3); uma resposta única evita N requisições em paralelo
que multiplicariam round-trips sem ganho real de performance percebida.

A rota DEVE herdar `require_session` via `api_router`
(`app/api/v1/router.py`) como qualquer outra rota autenticada — nenhuma
exceção de autenticação se justifica aqui.

### 3.2 Parâmetros de filtro

O endpoint DEVE aceitar query params opcionais:

- `decision`: `Incluído` | `Excluído` | `Pendente` — restringe todos os
  agregados de conteúdo (rankings, funil de critérios, distribuição
  temporal) aos artigos com essa decisão. Sem o parâmetro, o padrão é
  `Incluído` para os agregados de conteúdo (doc 31 §3.2) — os agregados de
  processo (funil PRISMA, volume por base, throughput de triagem) NÃO DEVEM
  ser afetados por este filtro, porque descrevem o funil inteiro, não a
  amostra final.
- `source`: nome de uma base (`bdtd`, `scielo`, `pubmed`, ...) — restringe
  os agregados de conteúdo a artigos com pelo menos uma `PaperSourceModel`
  daquela base.
- `year_from`, `year_to`: recorte temporal por `PaperModel.year`.

Um parâmetro inválido (decisão fora do vocabulário, ano não numérico) DEVE
retornar `422`, não ser ignorado silenciosamente — o mesmo padrão de
validação fechada que o resto da API já segue.

### 3.3 Erros

Falha de agregação (ex.: projeto inexistente) segue o padrão já estabelecido
na Fase 3 do plano de segurança: `404` para projeto ausente, `erro_interno()`
(`app/security/middleware.py`) para qualquer exceção não prevista — nenhum
detalhe de stack trace ou caminho de arquivo na resposta.

## 4. Normalização de texto livre

Para os rankings de autor, periódico e instituição, o serviço de agregação
DEVE:

1. Dividir `authors` em nomes individuais pelo separador `"; "` — o padrão
   usado por todos os harvesters (doc 31 §3.1). Vírgula NÃO é um separador
   seguro de fallback: o formato "Sobrenome, Inicial" já usa vírgula dentro
   de um único nome, e dividir por ela fragmentaria "Silva, J." em dois
   autores fantasmas. Sem `"; "` no campo, o valor inteiro DEVE ser tratado
   como um único autor — inclusive em registros importados manualmente que
   não seguem a convenção dos harvesters.
2. Normalizar cada nome/periódico/instituição para chave de agrupamento via
   `trim` + colapso de espaços + `casefold()` — SEM alterar o texto exibido,
   que DEVE ser a forma mais frequente entre as variantes agrupadas.
3. Descartar strings vazias após o `trim` — não contam como "autor
   desconhecido" no ranking.

O agregado DEVE vir acompanhado de uma nota de interface (não um aviso
bloqueante) informando que a contagem de autor é aproximada por não haver
desambiguação — texto definido em §6.4.

## 5. Frontend

### 5.1 Biblioteca de gráficos

O projeto DEVE adotar **Recharts** (`recharts`, licença MIT) como
dependência nova de `frontend/package.json`. Critério de escolha: compõe com
componentes React (compatível com o padrão do repositório, ao contrário de
libs que manipulam um canvas imperativo à parte), aceita cor por prop em vez
de embutir paleta fixa — o que permite alimentar cada série com
`var(--nome-do-token)` e obedecer a regra R1 do design system sem hack —, e
tem build tree-shakeable. A alternativa de estender o padrão hoje usado no
diagrama PRISMA (HTML/CSS desenhado à mão) fica descartada para os gráficos
desta aba: funciona para um fluxograma fixo de 3 caixas, não para rankings
com N categorias variáveis nem para série temporal.

### 5.2 Componente e rota

Nova página `frontend/src/pages/InsightsPage.tsx` (+ `.css`), registrada em
`App.tsx` na rota `/projects/:id/insights`, seguindo o mesmo padrão de
carregamento de dado das páginas irmãs (`ExportPage.tsx` como referência
mais próxima: busca no `useEffect`, estado de `loading`, integração com
`useSettingsStore`/`activeProject`).

### 5.3 Tokens e acessibilidade

Todo elemento visual DEVE usar cor/espaçamento/raio de `globals.css` — sem
literal solto, sob pena de falhar `npm run verify` (regras R1/R2 do design
system, já aplicadas ao restante do projeto). Cada gráfico DEVE ter uma
representação textual alternativa acessível — tabela de dado subjacente
alcançável por teclado ou `aria-label` com o resumo numérico —, para não
depender só de cor para carregar informação (WCAG 2.1 AA, já é requisito de
todo o produto conforme README).

### 5.4 Estado vazio

Cada bloco de gráfico DEVE mostrar um estado vazio explícito ("nenhuma
decisão registrada ainda", "nenhum critério de exclusão configurado") quando
o agregado correspondente vier zerado — não um gráfico em branco ou quebrado.

## 6. Métricas da v1

### 6.1 Funil PRISMA e de critérios

- Funil de identificação → triagem → elegibilidade → inclusão: reaproveita
  `get_prisma_flow_data` (`app/services/export_service.py:240`), exposto
  também pelo novo endpoint para não duplicar o cálculo do `/export/prisma`
  (o serviço de agregação DEVE chamar a mesma função, não reimplementá-la).
- Funil de critérios: para cada `CriterionModel` do protocolo ativo,
  contagem de `PaperCriterionModel.value = true` vs `false` entre os artigos
  avaliados, separado por critérios de inclusão e de exclusão. Este é o
  gráfico que explica *por que* a amostra final tem o tamanho que tem — item
  pedido explicitamente pelo usuário.

### 6.2 Composição da amostra

- Distribuição de decisão (`Incluído`/`Excluído`/`Pendente`) — contagem e
  percentual.
- Volume por base de coleta (`PaperSourceModel.source_name`), cruzado com
  decisão: quantos cada base trouxe vs. quantos dela foram incluídos (taxa
  de conversão por base) — generaliza o `source_counts` que hoje só conta
  volume bruto.
- Distribuição temporal: contagem de artigos incluídos por `year`.
- Distribuição por `research_type`.

### 6.3 Rankings (sujeitos ao filtro de decisão, padrão `Incluído`)

- Top N periódicos (`journal`).
- Top N autores (`authors`, após a normalização de §4).
- Top N instituições (`institution`).

`N` DEVE ser configurável na interface (dez por padrão), não fixo no
backend — o endpoint devolve a lista ordenada completa (ou um teto alto, ex.
50), e o corte de exibição é decisão do componente.

### 6.4 Saúde de aquisição e extração

- Distribuição de `pdf_status` (`ausente`/`obtido`/`manual`/`falhou`/
  `indisponivel`).
- Percentual de PDFs escaneados (`pdf_is_scanned`) sobre os obtidos —
  indicador de quanto do corpus depende de OCR.
- Completude de extração: para os artigos incluídos, percentual de
  `ExtractionQuestionModel` do protocolo com `ExtractionAnswerModel`
  preenchida (doc 31 §2.6) — não o conteúdo, só a completude.

### 6.5 Processo e proveniência de IA

- Throughput de triagem por `AuditLogModel.username`, contagem de decisões
  no período do projeto.
- Proporção de decisões com `source = "ia"` vs. `"manual"`.
- Proporção de `ai_response_valid = false` entre as decisões assistidas —
  é o indicador direto de quanto a IA "chutou" fora do vocabulário esperado
  (doc 28 V-16, doc 29 §29.9.2) e precisou de correção humana.
- Distribuição de `ai_confidence` das decisões assistidas.

## 7. Fora de escopo (extensões futuras)

> **Retomado em 31/08/2026.** Os quatro itens desta seção foram diagnosticados
> e especificados na série [47](./47_DIAGNOSTICO_BIBLIOMETRIA.md) →
> [48](./48_ESPECIFICACAO_AMBIENTE_INDICADORES.md) →
> [49](./49_PLANO_EXECUCAO_BIBLIOMETRIA.md). A medição do acervo real mostrou
> que os três primeiros são, na prática, a mesma lacuna: nunca termos pedido ao
> OpenAlex o que ele já devolve (doc 47 §5).

Registrado aqui para não ser esquecido, não para ser implementado nesta
rodada:

- Contagem de citações via OpenAlex/Crossref (doc 31 §4) — exigiria mudança
  no pipeline de coleta, não só de exibição.
- Palavras-chave por artigo e nuvem/coocorrência de termos — exigiria novo
  campo persistido e captura por harvester.
- Distribuição geográfica por país/afiliação — exigiria normalização ou
  geocodificação de `institution`, hoje texto livre sem estrutura.
- Exportação do próprio painel de indicadores como parte do relatório
  (`ExportPage`) — natural como próximo passo depois que a aba existir, mas
  não é pré-requisito para a v1.
