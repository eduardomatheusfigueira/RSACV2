# 44 — Plano de Execução: Pesquisa em Equipe

> **Este é o documento de trabalho.** Oito fases, cada uma com tarefas
> marcáveis, critério de aceite verificável e o que fazer se der errado.
> **Desenho alvo:** [`43_ESPECIFICACAO_PESQUISA_EM_EQUIPE.md`](./43_ESPECIFICACAO_PESQUISA_EM_EQUIPE.md).
> **Motivação medida:** [`42_DIAGNOSTICO_PESQUISA_EM_EQUIPE.md`](./42_DIAGNOSTICO_PESQUISA_EM_EQUIPE.md).
> **Restrições herdadas:** [`38_CHECKLIST_LGPD.md`](./38_CHECKLIST_LGPD.md) e [`40_ESPECIFICACAO_ONLINE.md`](./40_ESPECIFICACAO_ONLINE.md).
>
> **Estimativa total: 24 a 36 dias de trabalho focado.**
> **Aberto em:** 30/08/2026.

---

## Como executar

- **A ordem 0 → 1 → 2 não é negociável.** Pertencimento antes de convite, ou se
  convida para um lugar onde ninguém entra; convite antes de política, ou não há
  segundo membro para exercer papel algum.
- **As Fases 3 e 4 podem trocar de ordem.** A 3 entrega a *triagem simples*, a 4
  entrega a *revisão cega*. Se a prioridade for publicar, comece pela 4 — mas a
  4 é maior, e a 3 aquece o caminho de código que ela usa.
- **Uma fase por branch, um PR por fase.** A CI é o portão.
- **Nenhuma fase fecha sem seu critério de aceite verde.**
- **Toda alteração de esquema é revisão Alembic**, gerada e depois **conferida
  linha a linha** — autogeração erra em índice e tipo (lição do doc 41 Fase 0).
- **Cada fase roda a suíte nos dois bancos** (SQLite e PostgreSQL). A matriz da
  CI já existe.
- Ao fim das Fases 1 e 6, **reaferir os itens correspondentes do doc 38** e datar.

### Antes da primeira linha de código

- [ ] **P1** Decidir **D-01** — coleta compartilhada ou individual na modalidade cega (§42.6). Recomendação: compartilhada. **Bloqueia a Fase 3.**
- [ ] **P2** Decidir **D-02** — equipe por projeto ou grupo durável. Recomendação: por projeto. **Bloqueia a Fase 0.**
- [ ] **P3** Decidir **D-03** — de quem é a chave de IA. Recomendação: de quem age. **Bloqueia a Fase 2.**
- [ ] **P4** Decidir **D-04** — nº de revisores e quem desempata. Recomendação: 2, coordenador. **Bloqueia a Fase 4.**
- [ ] **P5** Decidir **D-05** — troca de modalidade no meio. Recomendação: só antes da 1ª decisão. **Bloqueia a Fase 2.**
- [ ] **P6** Fazer cópia de `rsac.db` de desenvolvimento e de produção — **as Fases 0, 4 e 5 alteram o esquema de tabelas com dado real.**
- [ ] **P7** Redigir o parágrafo de compartilhamento em equipe em `PRIVACIDADE.md` (§43.14). **Bloqueia o primeiro convite em produção**, não a Fase 1.

---

## Fase 0 — Pertencimento

> **Objetivo:** a autorização deixa de perguntar *"é seu?"* e passa a perguntar
> *"você participa?"* — sem que nada mude de comportamento, porque todo projeto
> nasce com exatamente um participante.
> **Esforço:** 2–3 dias · **Risco:** alto — é a barreira de isolamento.
> Fecha **E-01** e **E-10**.

Esta fase é a mais perigosa e a mais curta. Ela toca a única função que separa o
acervo de um assinante do de outro. Merece PR próprio, sem nenhuma outra
alteração junto.

### Tarefas

- [ ] **0.1** Criar `ProjectMemberModel` em `infrastructure/persistence/models.py` conforme §43.3.1 — atenção ao nome `project_role`, nunca `role` (E-10)
- [ ] **0.2** Revisão Alembic: cria `project_members` **e** popula uma linha `coordenador` por projeto existente a partir de `projects.owner_id`, na mesma revisão
- [ ] **0.3** Escrever o `downgrade` da revisão e **executá-lo numa cópia com dados** antes de seguir
- [ ] **0.4** Trocar `projeto_do_usuario` (`security/dependencies.py:198`) pela junção de §43.6 — mantendo o **404** e o comentário que explica por quê
- [ ] **0.5** Trocar `verificar_projeto_do_usuario` (`dependencies.py:244`) pela mesma junção — é o canal WebSocket (E-07)
- [ ] **0.6** Trocar a listagem `GET /projects` (`api/v1/projects.py:46`) para listar por participação
- [ ] **0.7** `create_project` (`projects.py:79`) passa a criar projeto **e** participação na mesma transação; o teto de `max_projects_per_user` continua contando só `owner_id` (`projects.py:67`)
- [ ] **0.8** Acrescentar `my_role` e `member_count` a `ProjectResponse` (`schemas/project.py`) e ao tipo `Project` do front (`frontend/src/types/api.ts:41`)
- [ ] **0.9** Estender `test_tenancy_isolation.py` com o terceiro personagem — o **convidado**: participação ativa entra em todas as rotas; participação `is_active=False` recebe 404 em todas (§42.4)
- [ ] **0.10** Teste de migração em `tests/test_schema/test_migrations.py`: banco com 3 projetos de 2 donos → 3 linhas de participação, papéis corretos, e `downgrade` limpo

### Critério de aceite

- [ ] `pytest -q` verde nos dois bancos
- [ ] `alembic upgrade head` e `alembic downgrade -1` funcionam sobre cópia do banco de produção
- [ ] O teste de isolamento passa com os **três** personagens
- [ ] **Verificação por mutação:** removendo `is_active` do filtro de §43.6, o teste falha nomeando a rota
- [ ] `grep -rn "owner_id ==" backend/app` devolve **apenas** `me.py`, `profile_service.py` e `projects.py:67` — nenhuma ocorrência em `security/`
- [ ] O app de mesa abre um projeto antigo e grava, sem passo manual

### Se der errado

`git revert` do PR e `alembic downgrade -1`. A fase não apaga nada: a revisão só
acrescenta tabela e linhas. O risco real não é perda de dado — é **abrir
acesso demais**, e é por isso que o critério de mutação é obrigatório aqui.

---

## Fase 1 — Convites de projeto

> **Objetivo:** um segundo pesquisador entra numa revisão.
> **Esforço:** 3–4 dias · **Risco:** médio.
> Fecha **E-05** e **E-13**.

### Tarefas

- [ ] **1.1** Criar `ProjectInvitationModel` (§43.3.2) e revisão Alembic
- [ ] **1.2** `schemas/team.py` — `ProjectInvitationCreate`, `ProjectInvitationResponse`, `ProjectMemberResponse`, `TeamResponse`
- [ ] **1.3** `api/v1/team.py`: `GET/POST /projects/{id}/invitations`, `DELETE .../{invite_id}`, `GET /projects/{id}/members`, `DELETE /projects/{id}/members/{user_id}` — router com `Depends(projeto_do_usuario)`, como os outros nove
- [ ] **1.4** `POST /projects/invitations/{code}/aceitar` — **fora** do prefixo de projeto (quem aceita ainda não é membro); valida código, expiração, revogação, uso e teto
- [ ] **1.5** Encadear o registro (§43.10.2): `RSAC-EQ-...` em `LoginPage.tsx` leva ao formulário de registro e cria conta + participação na mesma transação
- [ ] **1.6** Registrar `team_invitation_issued`, `team_membership_created` e `team_membership_revoked` no ROPA (§43.14)
- [ ] **1.7** Tetos de `config.py` (§43.17) — os quatro de convite e participação
- [ ] **1.8** Front: `TeamPage` em `/projects/:id/team` — membros, convites com código copiável, remover membro
- [ ] **1.9** Front: grupo `Equipe` na aba **Arquivo** do ribbon (§43.16.2) e rota no `App.tsx` com `ProjectRouteGuard`
- [ ] **1.10** Front: `ProjectsPage` mostra selo de equipe, papel e filtro "meus / participo" (E-13 — o cartão passa a dizer o que o `localStorage` não sabe)
- [ ] **1.11** `tests/test_api/test_team_invitations.py` — os três casos de aceite, expirado, revogado, já usado, teto estourado, e convite de projeto alheio

### Critério de aceite

- [ ] Dois usuários de teste: A cria, convida B, B aceita, B lê o protocolo e os estudos
- [ ] B removido volta a receber 404 em todas as rotas do projeto
- [ ] Convite expirado, revogado e já usado devolvem 4xx com mensagem distinta
- [ ] Um `RSAC-EQ-...` aceito por quem não tem conta cria conta **e** participação, ou nenhuma das duas
- [ ] Coordenador de um projeto não consegue emitir convite para outro
- [ ] Doc 38 reaferido nos itens de compartilhamento

### Se der errado

Nenhum dado preexistente é tocado. Reverter o PR e apagar as duas tabelas. O
ponto de atenção é 1.5: se o registro encadeado falhar pela metade, sobra conta
sem participação — é o que o teste de transação em 1.11 cobre.

---

## Fase 2 — Modalidade, papéis e a chave de quem age

> **Objetivo:** a equipe escolhe como vai trabalhar, e cada papel pode o que deve.
> **Esforço:** 3–4 dias · **Risco:** médio.
> Fecha **E-06**. Depende de **P3** e **P5**.

### Tarefas

- [ ] **2.1** Colunas `collaboration_mode`, `reviewers_per_paper`, `conflict_resolution` em `projects` (§43.3.3) + revisão Alembic com `server_default` `'individual'`, `1`, `'coordenador'`
- [ ] **2.2** Criar `domain/collaboration.py` — `PoliticaDeColaboracao` e `politica_de()` (§43.4.1). **Nenhum `collaboration_mode ==` fora deste módulo**
- [ ] **2.3** `exige_papel(*papeis)` em `security/dependencies.py` e ligação nos routers conforme a matriz de §43.5
- [ ] **2.4** `POST /projects` e `PUT /projects/{id}` aceitam modalidade; a troca é rejeitada com **409** se houver decisão diferente de `Pendente` (D-05)
- [ ] **2.5** `POST /projects/{id}/screening/reabrir` — coordenador, transação, um `AuditLogModel` por estudo com `action="screening_reopened"`
- [ ] **2.6** Trocar os cinco pontos de credencial por ator (§43.11) — `extraction.py:259`, `extraction.py:269`, `harvest.py:301`, `harvesting_service.py:394`, `pdf_acquisition.py:121`
- [ ] **2.7** Erro **412** com mensagem acionável quando o ator não tem chave — nunca cair no dono em silêncio
- [ ] **2.8** Front: escolha de modalidade na criação do projeto, com o texto que explica cada uma em uma frase
- [ ] **2.9** Front: `TeamPage` mostra modalidade, permite trocar (com aviso do 409) e lista quais membros têm chave por provedor
- [ ] **2.10** `tests/test_api/test_papeis_de_projeto.py` — matriz de §43.5 exercitada célula a célula
- [ ] **2.11** `tests/test_services/test_credencial_do_ator.py` — B dispara coleta e IA; a chave de A **não** é lida

### Critério de aceite

- [ ] Observador recebe 403 em toda escrita e 200 em toda leitura
- [ ] Revisor não convida, não remove, não troca modalidade, não resolve conflito
- [ ] Trocar modalidade com 1 estudo decidido devolve 409 dizendo quantos
- [ ] `grep -rn "collaboration_mode ==" backend/app | grep -v domain/collaboration.py` devolve vazio
- [ ] `grep -rn "projeto.owner_id\|project.owner_id" backend/app` não aparece em `harvest.py`, `extraction.py` nem `pdf_acquisition.py`
- [ ] Coleta disparada por B usa a credencial Scopus de B; sem ela, 412

### Se der errado

2.6 é o risco: mudar a origem da credencial pode quebrar coleta e IA para
projetos individuais. Mitigação — o teste 2.11 roda **antes** com um único
usuário, provando que o caminho de um dono só continua idêntico.

---

## Fase 3 — Triagem simples (colaborativa) e trabalho ao vivo

> **Objetivo:** entregar a primeira das duas modalidades pedidas. Todos coletam,
> triam e extraem no mesmo acervo; o que um faz aparece para os outros.
> **Esforço:** 3–5 dias · **Risco:** médio.
> Fecha **E-07** e **E-09**. Depende de **P1**.

### Tarefas

- [ ] **3.1** `harvest_runs.run_by_user_id` (§43.3.7) + revisão Alembic; a coleta grava o ator
- [ ] **3.2** Eventos novos no `ws_manager` (§43.12.1) — `paper.decidido`, `protocolo.alterado`, `coleta.concluida`, `equipe.alterada`, `presenca`
- [ ] **3.3** `If-Match` / **409** em `PUT /projects/{id}/protocol` (§43.12.2) usando `protocols.updated_at`
- [ ] **3.4** `If-Match` / **409** em `PATCH /papers/{id}` quando a modalidade é colaborativa
- [ ] **3.5** Front: `useTeamChannel` — assina o WS do projeto e invalida as consultas do TanStack Query nos eventos que interessam a cada tela
- [ ] **3.6** Front: diálogo de conflito de versão — "recarregar" ou "sobrescrever", nunca perder texto em silêncio
- [ ] **3.7** Front: indicador de presença no `ProtocolPage` e na fila da Triagem
- [ ] **3.8** Front: na fila de estudos, marca de quem decidiu e quando
- [ ] **3.9** `tests/test_api/test_colaboracao.py` — A e B no mesmo projeto: A tria, B vê; B reedita, A vê; escrita concorrente do protocolo devolve 409

### Critério de aceite

- [ ] Duas sessões abertas no mesmo projeto: a decisão de uma aparece na outra sem recarregar
- [ ] Coleta disparada por A é acompanhada ao vivo por B
- [ ] Gravar o protocolo com versão obsoleta devolve 409 e o corpo atual — nunca sobrescreve calado
- [ ] Um estudo triado por A pode ser reeditado por B, e o log de auditoria mostra os dois
- [ ] **Modalidade `individual` inalterada:** a suíte anterior inteira continua verde

### Se der errado

O WebSocket é acessório: se 3.2/3.5 derem problema, a funcionalidade degrada
para "recarregue a página" sem perder correção. Os itens que **não** podem
degradar são 3.3 e 3.4 — sem eles, colaborar significa perder trabalho.

---

## Fase 4 — Revisão cega por pares

> **Objetivo:** a segunda modalidade, e a que torna a revisão publicável.
> **Esforço:** 5–7 dias · **Risco:** alto — muda quem escreve `papers.decision`.
> Fecha **E-02** e **E-03**. Depende de **P4**.

A maior fase. Vale ler §43.2 (P1, P2, P3) antes de começar.

### Tarefas

- [ ] **4.1** `PaperScreeningModel` (§43.3.4) + colunas `screening_status`, `conflict_resolved_by_user_id`, `conflict_resolved_at` em `papers` (§43.3.5) + revisão Alembic
- [ ] **4.2** Migração marca **todo** estudo com `decision != 'Pendente'` como `screening_status='legado'` (P5) — **sem** criar julgamento algum
- [ ] **4.3** `services/consolidation_service.py` — a máquina de estados de §43.8.1, único ponto que escreve `papers.decision`
- [ ] **4.4** `PATCH /papers/{id}` passa a gravar `paper_screenings` do ator e a chamar a consolidação na mesma transação
- [ ] **4.5** `services/blindness.py` — `visao_do_revisor()` (§43.7.1) e ligação em `papers.py`, `extraction.py`, `insights.py`, `screening_ai.py` e no WS de triagem
- [ ] **4.6** A triagem assistida por IA grava julgamento **do ator**, com `ai_assisted=True` — nunca um julgamento "da IA" sem dono
- [ ] **4.7** `GET /projects/{id}/screening/conflitos` e `POST .../conflitos/{paper_id}/resolver` — restritos ao papel resolvedor (§43.8.3)
- [ ] **4.8** Consolidação dos critérios (§43.8.2) — regra determinística, porque a exportação a lê
- [ ] **4.9** Front: `ScreeningPage` em modalidade cega — "sua decisão", contador `1 de 2` sem julgamento, aviso antes de mudar decisão já consolidada
- [ ] **4.10** Front: aba **Conflitos** (quarta na navegação segmentada móvel) com os dois julgamentos — empilhados no celular (§43.16.3)
- [ ] **4.11** `tests/test_security/test_cegueira.py` — enumerando `app.routes`, varre o corpo de toda resposta de B procurando o julgamento de A (§43.7.2)
- [ ] **4.12** `tests/test_services/test_consolidacao.py` — a máquina de estados inteira, inclusive a reversão de consenso

### Critério de aceite

- [ ] A e B triam 10 estudos: 7 concordam → `consenso`; 3 divergem → `conflito` com `decision='Pendente'`
- [ ] O coordenador resolve os 3; `screening_status='resolvido'` e `decision` recebe a resolução
- [ ] **Verificação por mutação:** desligando `visao_do_revisor`, `test_cegueira.py` falha nomeando a rota que vazou
- [ ] Nenhuma resposta a B contém o `screening_id`, a decisão ou as observações de A antes da consolidação
- [ ] Estudos legados continuam com a decisão que tinham, e ninguém aparece como autor deles
- [ ] Funil PRISMA, exportação e fila de extração continuam corretos — leem `papers.decision`, que não mudou de significado (P1)

### Se der errado

É a fase com maior chance de precisar de reversão. O `downgrade` da revisão
4.1 apaga `paper_screenings` e as três colunas, e `papers.decision` sobrevive
intacta — foi essa a razão de P1. **Antes de subir para produção, rodar a fase
inteira sobre uma cópia do banco real e conferir os contadores do funil antes
e depois: têm de ser idênticos.**

---

## Fase 5 — Extração em duplicata e concordância

> **Objetivo:** a extração independente, e o número que a revisão precisa relatar.
> **Esforço:** 3–5 dias · **Risco:** médio.
> Fecha **E-04**.

### Tarefas

- [ ] **5.1** `ReviewerExtractionAnswerModel` (§43.3.6) + revisão Alembic
- [ ] **5.2** Extração grava a resposta do ator; a consolidação preenche `extraction_answers` quando há acordo, e marca divergência quando não há
- [ ] **5.3** `visao_do_revisor` estendida à extração (`politica.extracao_cega`)
- [ ] **5.4** `services/agreement_service.py` — concordância bruta, κ de Cohen (2), κ de Fleiss (3+), faixas de Landis & Koch (§43.9)
- [ ] **5.5** O κ só é calculado sobre estudos com julgamento completo, e só é devolvido depois de ambos concluírem — é vazamento agregado, se não (§43.7)
- [ ] **5.6** Bloco de concordância na `InsightsPage`: κ com faixa, matriz 3×3 cruzada, série de conflitos no tempo
- [ ] **5.7** Fila de divergência de extração, análoga à de triagem
- [ ] **5.8** `tests/test_services/test_concordancia.py` — κ conferido contra valores calculados à mão em 4 tabelas conhecidas, inclusive o caso degenerado `Pe = 1`

### Critério de aceite

- [ ] κ de uma tabela conhecida bate com o cálculo manual até a terceira casa
- [ ] `Pe = 1` (todos os julgamentos iguais em ambos) não divide por zero e devolve o caso tratado
- [ ] Extração de A não aparece para B antes da consolidação
- [ ] A exportação continua lendo `extraction_answers` sem alteração

### Se der errado

Independente das anteriores. Reverter só esta fase deixa a triagem cega
funcionando e a extração compartilhada — degradação aceitável.

---

## Fase 6 — Ciclo de vida da conta e da equipe

> **Objetivo:** alguém pode sair — da equipe ou da plataforma — sem destruir o
> trabalho de quem fica, e sem que o Revsist guarde o que não pode.
> **Esforço:** 3–4 dias · **Risco:** alto — mexe em eliminação de dado.
> Fecha **E-08** e **E-11**.

### Tarefas

- [ ] **6.1** `paper_screenings.reviewer_label` e `reviewer_extraction_answers.reviewer_label` (§43.13.4) + revisão Alembic
- [ ] **6.2** Tornar `reviewer_id` anulável nas duas tabelas — é o que a pseudonimização exige
- [ ] **6.3** `POST /projects/{id}/transferir` (§43.13.2) — só o dono, só para coordenador ativo
- [ ] **6.4** Reescrever `executar_eliminacao_completa_usuario` (`me.py:90`) conforme a tabela de §43.13.3 — os três casos
- [ ] **6.5** Pseudonimizar julgamentos, respostas e `audit_logs` do usuário eliminado; **nunca** apagá-los
- [ ] **6.6** Saída de membro devolve os estudos afetados para `parcial` e os põe na fila "precisa de novo revisor" (§43.13.1)
- [ ] **6.7** Base legal `art16_II_estudo_por_orgao_de_pesquisa` e a operação `reviewer_pseudonymised` na lista fechada de `ropa_service.py`
- [ ] **6.8** Registrar `project_ownership_transferred` e `reviewer_pseudonymised` no ROPA
- [ ] **6.9** Atualizar `PRIVACIDADE.md` com o parágrafo de P7 e o de retenção do julgamento pseudonimizado
- [ ] **6.10** `tests/test_lgpd/test_eliminacao_com_equipe.py` — os três casos de §43.13.3, mais: depois da eliminação, nenhuma tabela contém nome, e-mail ou `google_sub` do eliminado, **e** o κ do projeto não mudou

### Critério de aceite

- [ ] Dono com equipe elimina a conta → titularidade transferida, projeto intacto, κ inalterado
- [ ] Dono sozinho elimina a conta → projeto apagado, como hoje
- [ ] Membro elimina a conta → participação desativada, julgamentos pseudonimizados
- [ ] Varredura pós-eliminação não encontra o e-mail nem o nome do eliminado em tabela alguma
- [ ] Doc 38 reaferido e datado nos itens de eliminação e retenção
- [ ] `PRIVACIDADE.md` publicado **antes** de a fase ir a produção

### Se der errado

Fase que apaga dado real. **Ensaiar inteira sobre uma cópia**, com verificação
antes/depois dos contadores do funil e do κ. Se a pseudonimização falhar pela
metade, o reparo é manual e caro — por isso 6.4 e 6.5 são uma transação só.

---

## Fase 7 — Exportação e reprodutibilidade

> **Objetivo:** a revisão sai do Revsist declarando o método, não só o resultado.
> É o que a torna submissível.
> **Esforço:** 2–3 dias · **Risco:** baixo.
> Fecha **E-12**.

### Tarefas

- [ ] **7.1** Aba `Equipe e Concordância` na planilha (`services/export_service.py`) com os 11 campos de §43.15
- [ ] **7.2** Colunas `Decisão R1`, `Decisão R2`, `Conflito`, `Resolvido por` na aba de estudos
- [ ] **7.3** Nota de rodapé do fluxograma PRISMA com nº de revisores, forma de resolução e κ (§43.15)
- [ ] **7.4** Rótulo pseudonimizado respeitado na exportação (§43.13.4) — "Revisor 2 (conta removida)"
- [ ] **7.5** A exportação de projeto individual **não** ganha aba nem colunas novas — não há equipe a declarar
- [ ] **7.6** `tests/test_api/test_export_extraction.py` estendido: projeto cego exporta κ e conflitos; projeto individual exporta como antes

### Critério de aceite

- [ ] Planilha de projeto cego traz κ, conflitos e período, e os números batem com a `InsightsPage`
- [ ] Planilha de projeto individual é byte-a-byte equivalente à de hoje nas abas existentes
- [ ] O fluxograma declara a frase do item 8 do PRISMA 2020

### Se der errado

Fase isolada e reversível. Nenhum dado é alterado — só lido.

---

## Rastreabilidade

| Achado | Fase | Tarefas |
|---|---|---|
| E-01 Propriedade 1:1 | 0 | 0.1 – 0.10 |
| E-02 Decisão sem autor | 4 | 4.1 – 4.4 |
| E-03 Critério sem autor | 4 | 4.1, 4.8 |
| E-04 Extração sem autor | 5 | 5.1 – 5.3 |
| E-05 Convite de plataforma | 1 | 1.1 – 1.5 |
| E-06 Credencial do dono | 2 | 2.6, 2.7 |
| E-07 Canal restrito ao dono | 0, 3 | 0.5, 3.2 |
| E-08 Eliminação destrói equipe | 6 | 6.3 – 6.5 |
| E-09 Escrita concorrente | 3 | 3.3, 3.4 |
| E-10 Colisão de `owner` | 0 | 0.1 |
| E-11 Faltam tetos | 1, 6 | 1.7 |
| E-12 PRISMA sem nº de revisores | 7 | 7.1 – 7.3 |
| E-13 Projeto ativo obsoleto | 1 | 1.10 |

---

## Riscos

| # | Risco | Prob. | Impacto | Mitigação |
|---|---|:---:|:---:|---|
| R1 | A Fase 0 abre acesso demais e um assinante lê o acervo de outro | baixa | **crítico** | Critério de mutação obrigatório; PR isolado; 3 personagens no teste de isolamento |
| R2 | A cegueira vaza por uma rota não coberta | média | alto | `test_cegueira.py` enumera `app.routes`, como o de isolamento — rota nova nasce coberta |
| R3 | A Fase 4 muda os contadores do funil em produção | média | alto | P1 mantém `papers.decision`; ensaio sobre cópia com conferência antes/depois |
| R4 | A pseudonimização da Fase 6 falha pela metade | baixa | alto | 6.4 e 6.5 numa transação; ensaio sobre cópia |
| R5 | Convite encadeado vira vetor de criação de contas | média | médio | Tetos de §43.17 na Fase 1, não depois |
| R6 | A troca de credencial (2.6) quebra a coleta de projetos individuais | média | médio | Teste 2.11 roda primeiro com um usuário só |
| R7 | `if modo == ...` se espalha e a manutenção fica dobrada | alta | médio | `politica_de()` como único ponto, verificado por `grep` no critério de aceite da Fase 2 |
| R8 | Escopo cresce para grupo durável, comentários, e-mail | alta | médio | §43.18 lista o que fica fora, com o motivo |

---

## Estimativa

| Fase | Dias | Acumulado |
|---|:---:|:---:|
| 0 · Pertencimento | 2–3 | 2–3 |
| 1 · Convites | 3–4 | 5–7 |
| 2 · Modalidade e papéis | 3–4 | 8–11 |
| 3 · Triagem simples e ao vivo | 3–5 | 11–16 |
| 4 · Revisão cega | 5–7 | 16–23 |
| 5 · Extração e concordância | 3–5 | 19–28 |
| 6 · Ciclo de vida | 3–4 | 22–32 |
| 7 · Exportação | 2–3 | **24–36** |

**Primeiro valor entregável:** fim da Fase 3 (11–16 dias) — a *triagem simples*
completa, que é uma das duas modalidades pedidas.
**Valor metodológico completo:** fim da Fase 5 (19–28 dias).
As Fases 6 e 7 não são opcionais para produção: a 6 porque sem ela a primeira
eliminação de conta destrói trabalho alheio, a 7 porque sem ela a revisão cega
não se distingue da simples no que sai do sistema.
