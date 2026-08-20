# 33 — Plano de Execução: Aba de B.I. e Bibliometria

Quatro fases, cada uma entregável e testável de forma independente. Ordem
pensada para que o backend exista e esteja testado antes de o frontend
consumi-lo, e para que a aba apareça navegável (ainda que incompleta) o
quanto antes.

## Fase 0 — Serviço de agregação e endpoint ✅ ENTREGUE

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

**Retrospectiva**: entregue conforme especificado — 24 testes novos, 397 no
total no backend, verificação manual contra servidor real (perfil desktop)
confirmando filtro, validação (422) e autenticação (401). Um defeito real
apareceu durante a implementação: o próprio doc 32 previa um *fallback* de
divisão de autores por vírgula quando o campo não tem `"; "` — mas
"Sobrenome, Inicial" já usa vírgula dentro de um único nome, e esse
fallback fragmentaria "Silva, J." em dois autores fantasmas. Corrigido no
código e no doc 32 §4 antes de entregar: sem `"; "`, o campo inteiro é um
autor só, sem fallback por vírgula.

## Fase 1 — Aba navegável com os agregados da Fase 0 ✅ ENTREGUE

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

**Retrospectiva**: entregue com nove blocos (não seis — o número final do
doc 32 §6.1–6.4, contando funil PRISMA, funil de critérios, composição por
decisão, composição por base, distribuição temporal, tipo de estudo e os
três rankings). Duas divergências do texto acima, ambas registradas aqui
porque mudam o que "testado" significa nesta fase:

1. **`InsightsPage.test.tsx` não existe** — existe
   `insightsFormat.ts`/`.test.ts`. O projeto não tem infraestrutura de teste
   de renderização de componente: nenhuma das 8 páginas existentes antes
   desta tem um teste próprio, só `api/backendUrl.test.ts`, e esse único
   precedente é sobre um módulo **sem import nenhum** — deliberadamente
   isolado para não precisar resolver o alias `@/` nem montar DOM. Importar
   `InsightsPage.tsx` (que puxa `recharts`, Radix e o cliente HTTP) na
   suíte confirmou o gap: `vitest run` não resolve `@/`, e mesmo resolvendo,
   nenhuma configuração de ambiente DOM existe para montar o componente.
   Introduzir `@testing-library/react` unilateralmente para esta única
   página teria sido uma mudança de infraestrutura de teste do projeto
   inteiro, não uma decisão de escopo desta fase. A escolha foi replicar o
   padrão existente: extrair a única lógica pura da página
   (`formatarPercentual`) para um módulo sem import, testável do mesmo jeito
   que `backendUrl.ts` — e verificar a renderização de verdade manualmente.
2. **A verificação manual não foi `npm run dev`** — esse comando sobe o
   shell do Electron, que falha em contêiner (`Running as root without
   --no-sandbox is not supported`). O projeto já tem a ferramenta certa para
   isso, usada pela suíte de validação visual/A11y (doc 26):
   `vite.config.testserver.mts` + `scripts/shared/rsac-fixture.mjs`, que
   sobe só o renderer numa porta fixa e abre com o mesmo binário Chromium
   do resto da suíte. Usada aqui com um projeto de dado real (decisões,
   critérios, três bases, quatro instituições/autores) — screenshot
   confirma os nove blocos renderizados, a cor por decisão batendo com os
   tokens `--color-included/-excluded/-pending`, o estado vazio funcionando
   de verdade (nenhum artigo tinha `journal` preenchido — "Periódicos"
   mostrou o estado vazio, não um gráfico quebrado), e nenhum erro de
   console além de uma falha de rede pré-existente e alheia ao trabalho
   desta fase (Google Fonts, sem acesso à internet no sandbox — reproduz
   idêntica na `ExportPage` já existente).

Custo registrado: adotar Recharts (doc 32 §5.1) pesou o bundle web de 725 KB
para 1120 KB minificados (203 KB → 319 KB gzip). Aceitável para uma
ferramenta de pesquisa desktop/self-hosted, mas é o preço real da decisão —
não um efeito colateral a esconder.

## Fase 2 — Filtros na interface e refinamento do funil de critérios ✅ ENTREGUE

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

**Retrospectiva**: entregue conforme especificado, com a ordenação por
impacto implementada no backend (`_criteria_funnel`, não no frontend) — é o
mesmo dado para qualquer cliente, e o backend já era o lugar que decidia a
ordem de exibição dos outros rankings. A definição de "impacto" exigiu uma
decisão que o doc 32 não detalhava: para um critério de EXCLUSÃO, atender é
o que reprova (`met_count`); para um critério de INCLUSÃO, é o oposto — não
atender é o que reprova (`not_met_count`). Invertida, a fórmula contaria o
critério mais permissivo como o mais decisivo. Testada com um cenário de
impacto bem distinto (não o `projeto_populado` de empate 1×1 da Fase 0, que
não provava a ordenação) e verificada por regressão: removida a chamada de
`sort`, o teste falhou como esperado, antes de a correção voltar.

Os filtros (decisão/base/ano) ficaram acessíveis via `Select`/`Input` do
kit de UI, com uma nota fixa na página explicando quais blocos o filtro
afeta. Verificação manual (mesmo harness da Fase 1, doc 26) trocando o
filtro de decisão de "Incluído" para "Excluído" ao vivo: os seis blocos de
conteúdo mudaram (título, dado e estado vazio), os seis blocos de processo
— funil PRISMA, funil de critérios, composição por decisão, volume por
base, throughput e proveniência de IA — permaneceram pixel a pixel
idênticos entre as duas capturas, confirmando doc 32 §3.2 na prática, não só
no teste.

Teste do lado do frontend: a montagem da query (`?decision=...&source=...`)
foi extraída para `construirQueryDeInsights` em `insightsFormat.ts` —
mesmo módulo sem import da Fase 1 — e testada isoladamente. `client.ts`
passou a chamá-la em vez de montar a `URLSearchParams` inline. Não há teste
automatizado do clique no `<select>` em si (mesma limitação de
infraestrutura registrada na Fase 1); a garantia de "muda o parâmetro, muda
o gráfico" vem da combinação do teste de `construirQueryDeInsights` (o
parâmetro muda) com os testes de backend que já provam que cada valor de
filtro produz um agregado diferente (o gráfico muda) e a verificação manual
acima (as duas coisas juntas, ao vivo).

## Fase 3 — Indicadores de processo e proveniência de IA ✅ ENTREGUE

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

**Retrospectiva**: entregue conforme especificado, com uma correção sobre a
premissa do próprio doc 32 §6.5. O texto original descrevia
`source = "ia"` como o valor a contar; o código real
(`app/services/screening_service.py`) grava `source=f"ai:{provedor}"` (ex.:
`"ai:gemini"`), e a troca manual (`app/api/v1/papers.py`) grava
`source="manual"`. A classificação em `_proveniencia_ia` usa
`source.startswith("ai:")` contra o dado real, não contra a string do
documento — encontrado ao ler o código de gravação antes de escrever a
consulta, não depois de um teste falhar.

Throughput e proporção manual/IA contam **eventos de auditoria**
(`action IN ('ai_screening', 'decision_changed')`), não "papers" — um
mesmo artigo pode ter mais de um evento (a IA sugere, uma pessoa corrige
depois), e throughput mede trabalho de triagem feito, não o estado final
da amostra. A taxa de resposta inválida só entra no denominador quem foi
`ai_screening`; a decisão manual de correção não conta como "resposta de
IA que precisou de correção" — ela É a correção.

Testado com um projeto isolado (`projeto_com_auditoria`, não o
`projeto_populado` das fases anteriores, para não herdar decisões sem
auditoria e distorcer os totais): duas pessoas, três decisões assistidas
(uma inválida), uma manual, confiança em três faixas distintas. Sete testes
novos, incluindo o caso de projeto sem nenhuma decisão assistida (taxa e
distribuição devolvem vazio/`None`, não erro) e a confirmação de que o
agregado ignora o filtro de decisão, como os outros agregados de processo.

Verificação manual (mesmo harness, doc 26): decisões de IA e manuais
inseridas via ORM direto (reproduzindo os campos exatos que
`screening_service.py`/`papers.py` gravariam — não um mock), `ai_confidence`
setado em três artigos. Screenshot confirma throughput por pessoa, a
proporção 3×1 IA/manual, "33%" de taxa de resposta inválida (1 de 3 eventos
`ai_screening`) e a distribuição de confiança em três faixas — todos batendo
exatamente com o que a consulta HTTP direta ao endpoint já mostrava.

`README.md` e `planejamento/00_INDICE.md` não foram atualizados nesta
rodada — ficam para o fechamento do plano (quando não houver mais fase
aberta), no mesmo momento em que a Fase 5 de segurança atualizou os dois de
uma vez, para não registrar "concluído" em documento de topo enquanto o
plano de B.I. ainda está em andamento.

## Fora do plano

Os itens do doc 32 §7 (citações, palavras-chave, geografia, exportação do
painel) não entram em nenhuma fase deste plano — ficam registrados para
avaliação futura, não são pré-requisito de nenhuma fase acima.
