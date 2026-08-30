# 42 — Diagnóstico: Pesquisa em Equipe

> **O que este documento mede:** o que existe hoje no código, e o que
> exatamente quebra quando duas pessoas passarem a trabalhar na mesma revisão.
> **Não** propõe solução — o desenho está em
> [`43_ESPECIFICACAO_PESQUISA_EM_EQUIPE.md`](./43_ESPECIFICACAO_PESQUISA_EM_EQUIPE.md)
> e a execução em
> [`44_PLANO_EXECUCAO_PESQUISA_EM_EQUIPE.md`](./44_PLANO_EXECUCAO_PESQUISA_EM_EQUIPE.md).
>
> Cada achado aponta `arquivo:linha`. Onde não aponta, não é achado — é
> opinião, e está marcado como tal.
> **Data da medição:** 30/08/2026, contra `b3f8ddf`.
> **Pressupõe entregues** as Fases 0 e 1 do doc 41 — Alembic e titularidade
> (`projects.owner_id`) —, concluídas em 27/08/2026. Sem elas nada aqui se
> sustenta.

---

## 42.1 O pedido, em uma frase

Um pesquisador cria uma revisão, convida outros, e a equipe escolhe entre duas
formas de trabalhar:

| Modalidade | Protocolo | Coleta | Triagem | Extração |
|---|---|---|---|---|
| **Triagem simples** (colaborativa) | conjunto | conjunta | conjunta — quem triou, triou; outro pode reeditar | conjunta |
| **Revisão cega** (por pares) | conjunto | *(ver D-01)* | independente, sem ver a do par | independente |

O que segue mede a distância entre isso e o código de hoje.

---

## 42.2 Por que a modalidade cega não é preferência de gosto

Vale registrar, porque muda a prioridade das fases: **triagem independente por
dois revisores não é um recurso a mais, é o que torna a revisão publicável.**

O PRISMA 2020 exige declarar quantos revisores triaram cada registro e se
trabalharam de forma independente (itens 8 e 9 da lista de verificação). A
Cochrane trata revisor único como limitação metodológica que precisa ser
justificada. Um periódico que receba uma revisão sistemática triada por uma
pessoa só vai pedir a taxa de concordância entre revisores — e hoje o Revsist
não tem como produzi-la, porque não tem como registrar duas opiniões sobre o
mesmo estudo.

Ou seja: a modalidade cega é o caminho que leva o Revsist de *ferramenta de
organização* a *instrumento de revisão sistemática*. A colaborativa é
conveniência; a cega é método.

---

## 42.3 Achados

Numerados **E-01** a **E-13** (E de Equipe). A coluna *gravidade* diz o que
acontece se a funcionalidade for ligada sem tratar o achado.

---

### E-01 · Não existe pertencimento — existe propriedade, e ela é 1:1
**Gravidade: bloqueante**

`ProjectModel.owner_id` (`models.py:86`) é uma coluna única. Toda a
autorização de projeto passa por uma comparação de igualdade com ela:

```
security/dependencies.py:230    ProjectModel.owner_id == (usuario.id if usuario else None)
security/dependencies.py:258    ProjectModel.owner_id == usuario.id      # canal WebSocket
api/v1/projects.py:46           ProjectModel.owner_id == usuario.id      # listagem
api/v1/me.py:102                ProjectModel.owner_id == user_id         # eliminação de conta
services/profile_service.py:325 ProjectModel.owner_id == user_id         # exportação de perfil
```

Não há tabela de participação, nem papel dentro do projeto, nem convite de
projeto. Um segundo pesquisador que abra o mesmo `project_id` recebe **404** —
e por decisão deliberada de projeto, documentada em `dependencies.py:216`, o
404 é a resposta correta hoje.

**O que isso tem de bom:** o ponto de decisão é **um só**. `projeto_do_usuario`
(`dependencies.py:198`) é declarado no *router*, não rota a rota, e por isso
alcança as 25 rotas com `{project_id}` de uma vez. Trocar propriedade por
pertencimento é uma alteração cirúrgica em uma função — não uma varredura por
25 arquivos. É o achado mais grave e, ao mesmo tempo, o mais barato de corrigir.

---

### E-02 · A decisão de triagem é uma coluna só, sem autor
**Gravidade: bloqueante para a modalidade cega**

```
models.py:191    decision: Mapped[str] = mapped_column(String(20), default="Pendente")
```

Um estudo tem **uma** decisão. Não há onde guardar "o revisor A incluiu e o
revisor B excluiu" — que é precisamente o estado que a modalidade cega precisa
representar, e do qual sai a taxa de concordância.

O raio de alcance é o que torna isto delicado: **43 leituras de `decision` em
17 arquivos**, entre elas o funil PRISMA (`services/insights_service.py`), a
exportação (`services/export_service.py`), a fila de extração
(`api/v1/extraction.py`), os contadores do projeto (`api/v1/projects.py:212`) e
a deduplicação (`services/dedup_service.py`).

Trocar a coluna por uma tabela de decisões-por-revisor **sem mais nada**
quebraria os 17 arquivos de uma vez. A saída — desenvolvida no doc 43 — é
manter `papers.decision` como a **decisão consolidada** e acrescentar a camada
por revisor abaixo dela.

A autoria, essa, já existe — mas só no registro histórico:
`AuditLogModel.user_id`/`username` (`models.py:347`) é preenchido a cada
mudança de decisão (`api/v1/papers.py:229`). O log sabe quem decidiu; a tabela
de estudos, não.

---

### E-03 · A avaliação de critério não tem autor
**Gravidade: alta**

```
models.py:254    class PaperCriterionModel     # (paper_id, criterion_id, value)
```

Não há `reviewer_id`. Marcar "atende ao critério de exclusão 3" é parte do
julgamento de um revisor, e em triagem cega dois revisores marcam critérios
diferentes para o mesmo estudo — hoje o segundo a gravar sobrescreve o
primeiro. 31 referências ao modelo no backend.

---

### E-04 · A resposta de extração não tem autor
**Gravidade: alta**

```
models.py:288    class ExtractionAnswerModel   # (paper_id, question_id, answer)
```

Mesmo problema, na etapa seguinte. A extração em duplicata independente é
exigência da Cochrane para desfechos, e é o que o pedido chama de "extração
individual". 32 referências no backend.

---

### E-05 · O convite que existe é de plataforma, não de projeto
**Gravidade: média**

`InviteCodeModel` (`models.py:426`) e `api/v1/invites.py` implementam um
convite de **cadastro**: código de uso único, emitido por `require_owner`
(`dependencies.py:119`), que autoriza alguém a criar uma conta no Revsist. Ele
não tem `project_id`, não tem papel, e é consumido no registro
(`auth.py:646`).

É a peça certa para a pergunta errada. "Entre na plataforma" e "entre nesta
revisão" são convites diferentes, com ciclos de vida diferentes — misturá-los
numa tabela só tornaria os dois mais difíceis de raciocinar. A gramática do
código (`RSAC-XXXX-YYYY`, `invites.py:40`) e o fluxo de aceite da
`LoginPage.tsx`, no entanto, são reaproveitáveis.

---

### E-06 · A chave de API é resolvida pelo **dono**, não por quem age
**Gravidade: alta — e é um problema de custo, não só de código**

Cinco pontos resolvem credencial e configuração de IA a partir de
`projeto.owner_id`:

```
api/v1/extraction.py:259     AISettingsModel.user_id == projeto.owner_id
api/v1/extraction.py:269     user_id=projeto.owner_id
api/v1/harvest.py:301        SourceCredentialModel.user_id == projeto.owner_id
services/harvesting_service.py:394-398   creds = self._load_credentials(db, owner_id=dono)
services/pdf_acquisition.py:121          owner_id = paper.project.owner_id
```

Com um dono só isso é indiferente. Com equipe, significa: **todo o consumo de
IA e toda a coleta autenticada de cinco pesquisadores correm na cota paga de
quem criou o projeto**, sem que ele tenha consentido nem consiga ver. O modelo
é BYOK — cada assinante traz a própria chave, cifrada em
`AISettingsModel.api_keys_encrypted` (`models.py:588`) — e essa premissa se
desfaz em silêncio no primeiro convite aceito.

`screening_service.py:257` já tem a forma certa e prova que a correção é
viável: usa `actor.user_id` quando há ator, e só cai no dono como último
recurso.

---

### E-07 · O canal de progresso ao vivo é do dono
**Gravidade: média**

`verificar_projeto_do_usuario` (`dependencies.py:244`) filtra por `owner_id`.
O WebSocket de coleta (`api/v1/harvest.py`) e o de triagem em lote
(`api/v1/screening_ai.py`) são por projeto e por dono.

É exatamente o canal por onde precisa passar o "se um já coletou, aparece para
todos" do pedido — e hoje ele fecha a conexão para qualquer um que não seja o
dono.

---

### E-08 · Excluir a conta apaga o projeto inteiro, com o trabalho dos outros
**Gravidade: alta — e é questão de LGPD, não só de dados**

```
api/v1/me.py:102    projetos = db.query(ProjectModel).filter(ProjectModel.owner_id == user_id).all()
                    ...
                    db.delete(proj)
```

`executar_eliminacao_completa_usuario` (`me.py:90`) cumpre corretamente os seis
passos de §40.5.1 — hoje. Com equipe, o titular que exerce o direito de
eliminação (art. 18, VI) levaria junto o acervo, as decisões e as extrações de
quatro colegas que não pediram nada.

Há um segundo lado, e é o que torna a decisão difícil: as decisões de triagem
do revisor que sai **são** dado dele, e ao mesmo tempo **são** o resultado
científico da equipe. Apagá-las muda o resultado da revisão em silêncio; mantê-las
com nome mantém dado pessoal depois da eliminação. O doc 43 §43.13 responde;
aqui só se registra que não há resposta no código.

---

### E-09 · Nada impede duas pessoas de gravarem o mesmo protocolo ao mesmo tempo
**Gravidade: média**

`api/v1/protocols.py` grava por sobreposição — a última escrita vence, sem
comparação de versão. O Estúdio de Protocolo salva seções inteiras. Duas
pessoas escrevendo o objetivo ao mesmo tempo é o cenário mais provável da
modalidade colaborativa ("todos constroem juntos o protocolo"), e o resultado
hoje é uma das duas perder o texto sem aviso.

---

### E-10 · `owner` já é um papel — o da plataforma
**Gravidade: baixa, mas é armadilha de nomenclatura**

`UserModel.role` (`models.py:382`) vale `owner` ou `researcher`
(`dependencies.py:37`), e `require_owner` protege rotas administrativas. Um
"papel no projeto" chamado `owner` colidiria com esse, e a confusão seria
silenciosa: `usuario.role == "owner"` continuaria compilando e passando nos
testes enquanto autorizasse a coisa errada.

---

### E-11 · O teto de projetos conta só os próprios — e nenhum teto conta membros
**Gravidade: baixa**

```
api/v1/projects.py:67    .filter(ProjectModel.owner_id == usuario.id).count()
config.py:78             max_projects_per_user: int = 20
```

O teto está certo para hoje. Falta o teto de **membros por projeto** e o de
**projetos dos quais participo**, sem os quais um convite em massa vira vetor
de abuso de recurso no perfil `server`.

---

### E-12 · O funil PRISMA não sabe quantos revisores houve
**Gravidade: média — é o que impede publicar**

`services/insights_service.py` e `services/export_service.py` produzem o
diagrama de fluxo e a planilha a partir de `papers.decision`. Não há campo para
"triado por 2 revisores independentes", nem para concordância, nem para
conflitos resolvidos — que são os três números que um periódico pede junto com
o fluxograma.

---

### E-13 · O projeto ativo vive no `localStorage` do navegador
**Gravidade: baixa**

`frontend/src/stores/useSettingsStore.ts` persiste `activeProject`. Quem for
removido de uma equipe continua com o projeto selecionado até o
`ProjectRouteGuard` (`App.tsx`) falhar a verificação e redirecionar. O
comportamento já é seguro (o guarda consulta o backend), mas a experiência é
um erro em vez de um aviso.

---

## 42.4 O portão que já existe, e o que ele passará a ter de guardar

`backend/tests/test_security/test_tenancy_isolation.py` é a peça mais
importante desta análise, e é uma boa notícia. O teste
`test_nenhuma_rota_de_projeto_escapa_do_isolamento` **enumera `app.routes`** em
vez de listar rotas à mão, e exige 404 de todas para um segundo usuário. Uma
rota nova sem isolamento quebra a suíte sem que ninguém precise lembrar de
acrescentá-la.

Esse teste vai passar a significar outra coisa. Hoje ele afirma *"quem não é
dono não entra"*. Depois da Fase 0 ele terá de afirmar *"quem não é membro não
entra"* — e o teste antigo, sem alteração, continuaria verde mesmo se a
verificação de pertencimento fosse ligada errada, porque o intruso do teste
também não é membro.

**Portanto:** a Fase 0 não fecha com o teste existente verde. Fecha com um
terceiro personagem — o *convidado* — provando que ele entra onde deve e não
entra onde não deve.

A mesma lógica vale para a cegueira: nenhum teste de hoje consegue falhar por
vazamento da decisão do par, porque não existe par. É preciso um portão novo,
na forma de `test_no_secret_leak.py` — que já é o precedente da casa para
"este campo não pode sair na resposta".

---

## 42.5 O que quebra se ligarmos equipe sem plano

Em ordem de quando apareceria:

1. **Primeiro convite aceito.** O convidado vê 404 em tudo (E-01).
2. **Corrigido o 404.** O convidado dispara uma coleta e gasta a chave Scopus
   do dono, sem que nenhum dos dois veja (E-06).
3. **Dois triando.** O segundo a decidir sobrescreve o primeiro; a discordância
   — que era o dado a produzir — desaparece (E-02, E-03).
4. **Dois escrevendo o protocolo.** Uma das versões some (E-09).
5. **Fim da revisão.** A planilha exportada não distingue revisor único de
   dupla independente; a revisão não é publicável como dupla (E-12).
6. **Um membro exclui a conta.** O acervo dos outros vai junto (E-08).

Os itens 1 a 3 são intransponíveis. Os 4 a 6 produzem dano silencioso, que é
pior: ninguém percebe até a submissão.

---

## 42.6 Decisões em aberto

Estas **não** têm resposta no código nem no pedido. Cada uma traz a
recomendação e o que muda se for decidida ao contrário. São resolvidas antes da
fase que as consome, não antes de começar.

---

### D-01 · A coleta é individual ou compartilhada na modalidade cega?
**Consome:** Fase 3 · **Recomendação: compartilhada, sempre.**

O pedido diz "a coleta, triagem e extração são individuais". Para triagem e
extração isso é o método. Para a coleta, tem uma consequência que vale medir
antes de decidir: **o fluxograma PRISMA tem um único número de "registros
identificados"**. Se cada revisor coleta o próprio corpus, não existe esse
número — existem dois, e a revisão passa a ter dois corpora que se sobrepõem
parcialmente, sem forma canônica de reconciliá-los. A busca é parte do
protocolo (é reprodutível por definição: mesma string, mesma base, mesma data);
quem varia é o *julgamento*, não o *achado*.

O que a Cochrane faz: uma busca, executada uma vez, registrada; dois revisores
independentes triando o resultado dela.

**Recomendado:** corpus sempre compartilhado, com `harvest_runs.run_by_user_id`
registrando quem executou cada busca. A cegueira começa na triagem.

**Se for decidido ao contrário:** `papers` precisa de escopo por revisor, a
deduplicação passa a ter de rodar entre corpora, e o funil PRISMA precisa de um
passo novo de união. É trabalho da ordem de uma fase inteira a mais, e o doc 43
§43.18 registra o que seria preciso.

---

### D-02 · Equipe por projeto ou grupo de pesquisa durável?
**Consome:** Fase 0 · **Recomendação: equipe por projeto na v1.**

O pedido diz "grupo de pesquisa", o que sugere um laboratório com várias
revisões; mas descreve a modalidade como escolha *da pesquisa*, o que a prende
ao projeto. Equipe por projeto é a leitura mais próxima do que foi pedido e
custa uma tabela; grupo durável custa três, mais gestão de sincronia entre a
composição do grupo e a de cada revisão.

**Recomendado:** `project_members` na v1. A tabela nasce com `project_id`, e um
`research_groups`/`group_id` opcional pode ser acrescentado depois sem
migração destrutiva — só um preenchimento.

---

### D-03 · De quem é a chave de API quando cinco pessoas usam a IA?
**Consome:** Fase 2 · **Recomendação: de quem age.**

Alternativas: (a) chave de quem aciona; (b) chave do dono, com consentimento
explícito dele; (c) chave "do projeto", copiada na criação.

(c) está descartada — duplicar segredo cifrado em outro lugar é criar mais um
lugar de onde ele vaza. (b) é defensável para um laboratório com verba central,
mas exige tela de consentimento e teto de gasto para não virar surpresa na
fatura. (a) é o que o modelo BYOK já implica, é o que `screening_service.py:257`
já faz, e falha de forma legível: quem não tem chave recebe "configure uma
chave em Configurações" e continua trabalhando manualmente.

**Recomendado:** (a), com (b) como preferência opcional do dono numa fase
futura.

---

### D-04 · Quantos revisores por estudo, e quem desempata?
**Consome:** Fase 4 · **Recomendação: 2 revisores, desempate pelo coordenador.**

Dois é o padrão da área. Três é usado em revisões grandes com maioria simples.
O desempate por *terceiro revisor cego* é metodologicamente superior ao
desempate por coordenador, mas exige um terceiro membro disponível.

**Recomendado:** `revisores_por_estudo` configurável (padrão 2) e
`resolucao_de_conflito` com dois valores — `coordenador` (padrão) e
`terceiro_revisor` —, ambos definidos na criação da revisão.

---

### D-05 · Pode-se trocar de modalidade no meio da revisão?
**Consome:** Fase 2 · **Recomendação: só antes da primeira decisão.**

Trocar de colaborativa para cega depois de 400 estudos triados deixaria 400
estudos com um revisor e 200 com dois — e a revisão perde a declaração de
método uniforme, que é o que se publica.

**Recomendado:** a modalidade é livremente editável enquanto não houver
nenhuma decisão diferente de `Pendente`. Depois disso, só com "reabrir
triagem", que arquiva as decisões existentes num instantâneo e exige
confirmação escrita do coordenador.

---

## 42.7 Resumo

| # | Achado | Gravidade | Fecha na fase |
|---|---|---|---|
| E-01 | Propriedade 1:1, sem pertencimento | bloqueante | 0 |
| E-02 | Decisão é coluna única, sem autor | bloqueante | 4 |
| E-03 | Avaliação de critério sem autor | alta | 4 |
| E-04 | Resposta de extração sem autor | alta | 5 |
| E-05 | Convite é de plataforma, não de projeto | média | 1 |
| E-06 | Credencial e IA resolvidas pelo dono | alta | 2 |
| E-07 | Canal ao vivo restrito ao dono | média | 3 |
| E-08 | Eliminação de conta apaga o trabalho alheio | alta | 6 |
| E-09 | Escrita concorrente sem proteção | média | 3 |
| E-10 | Colisão de nome no papel `owner` | baixa | 0 |
| E-11 | Faltam tetos de membro e de participação | baixa | 6 |
| E-12 | Funil PRISMA não declara nº de revisores | média | 7 |
| E-13 | Projeto ativo obsoleto no `localStorage` | baixa | 1 |

**Dois bloqueantes, quatro altos.** O E-01 é o mais grave e o mais barato — uma
função. O E-02 é o mais caro, e é ele que dita a existência das Fases 4 e 5.
