# 33 — Plano de Execução: Aba de B.I. e Bibliometria

Quatro fases, cada uma entregável e testável de forma independente. Ordem
pensada para que o backend exista e esteja testado antes de o frontend
consumi-lo, e para que a aba apareça navegável (ainda que incompleta) o
quanto antes.

## Fase 0 — Serviço de agregação e endpoint

**Objetivo**: `GET /api/v1/projects/{id}/insights` devolvendo todos os
agregados de §6.1–6.4 do doc 32 (funil PRISMA + critérios, composição da
amostra, rankings, saúde de PDF/extração) — throughput de IA (§6.5) fica
para a Fase 3, junto do resto de proveniência.

**Entregas**:
- `app/services/insights_service.py`: função de agregação, reaproveitando
  `get_prisma_flow_data` para os totais PRISMA (doc 32 §6.1) e usando
  `GROUP BY` no SQL para os agregados por base/decisão/ano (doc 31 §3.3).
  Normalização de autor/periódico/instituição conforme doc 32 §4.
- `app/api/v1/insights.py`: rota registrada no `api_router` (herda
  `require_session`), parâmetros de filtro (`decision`, `source`,
  `year_from`, `year_to`) com validação fechada (`422` em valor inválido).
- `app/schemas/insights.py`: schemas Pydantic de resposta.
- Testes: `backend/tests/test_services/test_insights.py` cobrindo cada
  agregado com um projeto de fixture (papers com decisões, critérios,
  fontes e status de PDF variados) — incluindo o caso de projeto vazio
  (todo agregado zerado, sem exceção) e o de nomes de autor com variação de
  caixa/espaço (verifica que a normalização agrupa corretamente).

**Critério de aceite**: suíte de testes do backend passando com a nova
suíte incluída; `curl` manual contra um projeto de teste confirma que os
filtros de query alteram os agregados de conteúdo e preservam os de
processo, como especificado em doc 32 §3.2.

## Fase 1 — Aba navegável com os agregados da Fase 0

**Objetivo**: a aba existe, aparece na navegação, mostra os gráficos cujo
dado já está pronto (Fase 0) com estado vazio correto onde não há dado.

**Entregas**:
- `frontend/package.json`: adiciona `recharts` (doc 32 §5.1).
- `frontend/src/components/layout/TopRibbonBar.tsx`: novo item
  `insights` em `RIBBON_TABS`, `stepNumber: 5`; Exportação passa para `6`.
- `frontend/src/pages/InsightsPage.tsx` + `.css`: funil PRISMA + critérios,
  composição da amostra, rankings de periódico/autor/instituição, saúde de
  PDF/extração — cada bloco com estado vazio (doc 32 §5.4) e tabela de dado
  alternativa acessível (doc 32 §5.3).
- `frontend/src/api/client.ts` / `types/api.ts`: método e tipos para o novo
  endpoint.
- `App.tsx`: rota `/projects/:id/insights`.
- Testes: `frontend/src/pages/InsightsPage.test.tsx` (Vitest) cobrindo
  renderização com dado presente e com agregados vazios; `npm run verify`
  passando sem novas violações de token.

**Critério de aceite**: navegação manual pela aba com um projeto real
(desktop, `npm run dev`) confirma que os seis blocos renderizam com dado
verdadeiro e que os filtros de decisão/base/ano (se já plugados na UI nesta
fase) refletem no gráfico. `npm run verify` e `npx vitest run` limpos.

## Fase 2 — Filtros na interface e refinamento do funil de critérios

**Objetivo**: os parâmetros de filtro do endpoint (doc 32 §3.2) ficam
acessíveis na interface, não só na API; o funil de critérios recebe
tratamento visual que deixa claro qual critério reprovou mais artigos.

**Entregas**:
- Controles de filtro (decisão, base, intervalo de ano) na `InsightsPage`,
  reexecutando a busca do endpoint ao mudar.
- Gráfico de funil de critérios com ordenação por impacto (critério que mais
  excluiu primeiro) — a leitura que efetivamente responde "por que a amostra
  ficou desse tamanho".
- Testes: cobertura dos filtros no frontend (muda o parâmetro, muda o
  gráfico) e no backend (combinação de filtros, doc 32 §3.2 — filtro de
  decisão não deve afetar agregados de processo).

**Critério de aceite**: suíte completa (backend + frontend) passando;
verificação manual de que aplicar um filtro de base restringe os rankings
sem alterar o funil PRISMA.

## Fase 3 — Indicadores de processo e proveniência de IA

**Objetivo**: throughput de triagem por pessoa, proporção de decisões
assistidas por IA e taxa de resposta fora do vocabulário esperado (doc 32
§6.5) — os indicadores que dependem de `AuditLogModel`, a peça mais nova do
modelo de dados (Fase 5 do plano de segurança).

**Entregas**:
- Extensão de `insights_service.py` com os agregados de `AuditLogModel`
  (throughput por `username`, proporção manual/IA, `ai_response_valid`,
  distribuição de `ai_confidence`).
- Bloco correspondente na `InsightsPage`.
- Testes cobrindo o novo agregado, incluindo o caso de projeto sem nenhuma
  decisão assistida por IA (bloco não deve quebrar, deve mostrar 0%).
- Atualização de `README.md` e `planejamento/00_INDICE.md` registrando a
  aba entregue, no mesmo padrão usado para a Fase 5 de segurança.

**Critério de aceite**: suíte completa do projeto (backend + frontend)
passando; verificação manual de que o indicador de throughput reflete
corretamente decisões tomadas por usuários diferentes em um projeto de
teste com mais de uma conta.

## Fora do plano

Os itens do doc 32 §7 (citações, palavras-chave, geografia, exportação do
painel) não entram em nenhuma fase deste plano — ficam registrados para
avaliação futura, não são pré-requisito de nenhuma fase acima.
