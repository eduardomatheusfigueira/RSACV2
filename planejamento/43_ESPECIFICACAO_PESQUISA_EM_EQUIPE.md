# 43 — Especificação: Pesquisa em Equipe

> **Documento normativo.** Descreve o desenho alvo: vocabulário, modelo de
> dados, política de colaboração, autorização, cegueira, consolidação e
> interface. Quem for implementar decide *como*; **o que** está aqui.
> **Motivação medida:** [`42_DIAGNOSTICO_PESQUISA_EM_EQUIPE.md`](./42_DIAGNOSTICO_PESQUISA_EM_EQUIPE.md).
> **Execução:** [`44_PLANO_EXECUCAO_PESQUISA_EM_EQUIPE.md`](./44_PLANO_EXECUCAO_PESQUISA_EM_EQUIPE.md).
> **Restrições herdadas:** doc 40 (titularidade e isolamento) e doc 38 (LGPD).

---

## 43.1 Vocabulário

Palavras com significado fixo neste documento e no código. Onde o português
corrente é ambíguo, o termo aqui manda.

| Termo | Significa | Não significa |
|---|---|---|
| **Equipe** | O conjunto de contas com participação ativa num projeto | Um grupo de pesquisa institucional (ver D-02) |
| **Papel de projeto** | `coordenador`, `revisor`, `observador` — vale dentro de um projeto | `UserModel.role` (`owner`/`researcher`), que é papel de plataforma |
| **Modalidade** | O preset de colaboração escolhido para a revisão | Uma permissão |
| **Política** | Os efeitos da modalidade, etapa por etapa | Um valor guardado no banco — é derivada |
| **Julgamento** | A decisão de UM revisor sobre UM estudo | A decisão do estudo |
| **Consolidação** | A decisão do estudo, derivada dos julgamentos | Uma média |
| **Conflito** | Julgamentos completos e divergentes sobre o mesmo estudo | Um erro |
| **Cegueira** | O revisor não consegue **obter** o julgamento do par | A interface não mostra |

A última linha é a mais importante do documento. Ver §43.7.

---

## 43.2 Os cinco princípios

Regras duras. Uma decisão de implementação que contrarie qualquer uma delas
está errada, mesmo que funcione.

**P1 · A decisão consolidada continua sendo `papers.decision`.**
São 43 leituras em 17 arquivos (E-02). Nenhuma delas muda. O que se acrescenta
é a camada de julgamentos **abaixo** dela, e um serviço que a deriva. Quem
consome a revisão — funil, exportação, fila de extração, contadores — continua
lendo o mesmo campo, com o mesmo significado: *o que a equipe decidiu sobre
este estudo*.

**P2 · Modo compartilhado é modo cego com um revisor e sem venda.**
Não existem dois caminhos de código. Existe uma política com
`revisores_por_estudo` e `triagem_cega`; a modalidade colaborativa é
`(1, False)` e a cega é `(2, True)`. Bifurcar o fluxo em `if modo == ...`
espalhado pelo código é como esta funcionalidade apodrece.

**P3 · A cegueira é do servidor.**
Se o dado sai na resposta HTTP, a cegueira não existe — independentemente do
que a interface desenhe. É verificado por teste que inspeciona o corpo da
resposta, não por revisão visual.

**P4 · Quem age paga.**
Chave de IA, credencial de base e cota são de quem aciona a operação, nunca do
dono do projeto por ser dono (E-06, D-03).

**P5 · O que já existe não ganha autor inventado.**
Decisões gravadas antes desta funcionalidade não têm revisor conhecido. A
migração **não** atribui essas decisões ao dono. Um `paper` sem julgamentos
registrados tem `papers.decision` como verdade e `screening_status =
'legado'`.

---

## 43.3 Modelo de dados

Cinco tabelas novas, três colunas novas em tabelas existentes. Todas as
alterações por revisão Alembic (doc 41 Fase 0 já entregou a fundação).

### 43.3.1 `project_members` — a participação

```python
class ProjectMemberModel(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        Index("ix_project_members_user", "user_id"),
        Index("ix_project_members_project", "project_id"),
    )

    id: str                       # uuid
    project_id: str               # FK projects.id
    user_id: str                  # FK users.id
    project_role: str             # 'coordenador' | 'revisor' | 'observador'
    is_active: bool = True        # desligar em vez de apagar — ver §43.13
    invited_by_user_id: str | None
    joined_at: datetime
    left_at: datetime | None
```

**`project_role`, e não `role`.** A colisão com `UserModel.role` seria
silenciosa e perigosa (E-10): `usuario.role == "owner"` continuaria compilando.
O nome longo é barato.

**`is_active` em vez de `DELETE`.** Um revisor removido da equipe deixou
julgamentos que fazem parte do resultado. Apagar a linha de participação
deixaria julgamentos órfãos apontando para alguém que "nunca esteve lá".

**O dono continua existindo.** `projects.owner_id` **não** é removido: é quem
responde pelo projeto perante a LGPD (controlador), quem recebe a cobrança e
quem transfere a titularidade. Todo dono tem obrigatoriamente uma linha em
`project_members` com `project_role='coordenador'`, criada na mesma transação
do projeto — a autorização olha só a tabela de participação, nunca as duas.

### 43.3.2 `project_invitations` — o convite de projeto

Tabela **separada** de `invites` (E-05): ciclos de vida diferentes.

```python
class ProjectInvitationModel(Base):
    __tablename__ = "project_invitations"

    id: str
    project_id: str               # FK projects.id
    code: str                     # 'RSAC-EQ-XXXX-YYYY', único
    email: str | None             # destinatário pretendido, quando informado
    project_role: str             # papel com que a pessoa entra
    created_by_user_id: str
    created_at: datetime
    expires_at: datetime          # padrão: 14 dias
    accepted_at: datetime | None
    accepted_by_user_id: str | None
    revoked_at: datetime | None
    note: str = ""
```

O código carrega o prefixo `EQ` para ser distinguível a olho do convite de
plataforma — quem recebe os dois no mesmo e-mail precisa saber qual é qual.

### 43.3.3 `projects` — a modalidade

```python
    collaboration_mode: str = "individual"
        # 'individual' | 'colaborativa' | 'cega_por_pares'
    reviewers_per_paper: int = 1
    conflict_resolution: str = "coordenador"
        # 'coordenador' | 'terceiro_revisor'
```

Três colunas, não uma coluna JSON. São valores que a autorização consulta a
cada requisição; um JSON exigiria desserializar em todo pedido e não pode ser
indexado nem verificado por `CHECK`.

`reviewers_per_paper` e `conflict_resolution` são redundantes com o preset **de
propósito**: o preset define o padrão na criação, e as duas colunas são o que
vale. Assim a D-04 (quantos revisores) é resolvida por projeto sem inventar um
quarto preset.

### 43.3.4 `paper_screenings` — o julgamento

O coração da modalidade cega.

```python
class PaperScreeningModel(Base):
    __tablename__ = "paper_screenings"
    __table_args__ = (
        UniqueConstraint("paper_id", "reviewer_id", name="uq_paper_screenings_paper_reviewer"),
        Index("ix_paper_screenings_paper", "paper_id"),
        Index("ix_paper_screenings_reviewer", "reviewer_id"),
    )

    id: str
    paper_id: str                 # FK papers.id
    reviewer_id: str              # FK users.id
    decision: str = "Pendente"    # Decision enum
    observations: str = ""
    criteria_evaluations: str = "{}"   # JSON {criterion_id: bool}
    ai_confidence: float | None
    ai_assisted: bool = False
    decided_at: datetime | None
    updated_at: datetime
```

**`criteria_evaluations` como JSON dentro do julgamento**, e não uma quarta
tabela (E-03). A avaliação de critério só existe *como parte de* um julgamento
— nunca é consultada isoladamente, e nunca é agregada por critério fora do
contexto do revisor. A casa já usa JSON em `Text` onde a estrutura é lida
inteira (`protocols.pico_framework`, `search_filters`). `paper_criteria`
permanece intacta como a avaliação **consolidada**, que é o que a exportação lê.

**Escrito em todas as modalidades**, inclusive na individual (P2). O custo é
uma linha por (estudo, revisor); o ganho é um caminho de código só, a
possibilidade de trocar de modalidade (D-05) e a resposta direta a "quem triou
o quê" sem varrer o log de auditoria.

### 43.3.5 `papers` — o estado da consolidação

```python
    screening_status: str = "aguardando"
        # 'legado' | 'aguardando' | 'parcial' | 'consenso' | 'conflito' | 'resolvido'
    conflict_resolved_by_user_id: str | None
    conflict_resolved_at: datetime | None
```

`decision` **não muda de tipo nem de significado** (P1). Muda quem a escreve:
deixa de ser gravada direto pela rota e passa a ser gravada só pelo serviço de
consolidação (§43.8).

`legado` é o estado dos estudos decididos antes desta funcionalidade (P5).

### 43.3.6 `reviewer_extraction_answers` — a extração em duplicata

```python
class ReviewerExtractionAnswerModel(Base):
    __tablename__ = "reviewer_extraction_answers"
    __table_args__ = (
        UniqueConstraint("paper_id", "question_id", "reviewer_id",
                         name="uq_reviewer_extraction_paper_question_reviewer"),
    )

    id: str
    paper_id: str
    question_id: str
    reviewer_id: str
    answer: str = ""
    evidence: str = ""
    page_ref: str = ""
    source_kind: str = ""         # pdf | resumo | manual
    ai_generated: bool = False
    updated_at: datetime
```

Simétrico a `paper_screenings`: `extraction_answers` (`models.py:288`)
permanece como a resposta **consolidada**, que é o que a exportação lê. Nenhum
dos 32 pontos que a referenciam muda.

> **Por que não uma coluna `reviewer_id` anulável na tabela existente.**
> Seria a mesma tabela com `NULL` significando "consolidada". `NULL` não
> participa de `UNIQUE` em PostgreSQL — a restrição não impediria duas
> consolidadas para a mesma pergunta —, e o esquema passaria a ter uma coluna
> cujo significado depende de ser nula. Duas tabelas com nomes honestos custam
> menos.

### 43.3.7 `harvest_runs` — a autoria da busca

```python
    run_by_user_id: str | None    # FK users.id, nulo para execuções legadas
```

O corpus é do projeto (D-01); a execução é de alguém. É este campo que o
fluxograma PRISMA cita ao declarar quem executou a busca e quando.

### 43.3.8 O que **não** muda

Registro explícito, porque a tentação de mexer é grande:

- `papers.decision`, `papers.observations` — consolidados (P1)
- `paper_criteria` — avaliação consolidada
- `extraction_answers` — resposta consolidada
- `audit_logs` — já tem autoria (`models.py:347`); continua sendo o log de
  eventos, complementar e não substituível pelos julgamentos, que são estado
- `projects.owner_id` — titularidade, não autorização (§43.3.1)
- `invites` / `InviteCodeModel` — convite de plataforma, intocado

---

## 43.4 Modalidades e política

### 43.4.1 A função pura

Um módulo novo, `backend/app/domain/collaboration.py`, sem dependência de
banco nem de FastAPI:

```python
@dataclass(frozen=True)
class PoliticaDeColaboracao:
    corpus_compartilhado: bool
    protocolo_coeditavel: bool
    revisores_por_estudo: int
    triagem_cega: bool
    extracao_cega: bool
    resolucao_de_conflito: str

def politica_de(projeto) -> PoliticaDeColaboracao: ...
```

Toda pergunta sobre o que a modalidade permite passa por aqui. **Nenhuma
comparação `collaboration_mode == "..."` fora deste módulo** — é a regra que
impede a bifurcação de P2 de se espalhar, e é verificável por lint
(`grep -rn 'collaboration_mode ==' backend/app | grep -v domain/collaboration.py`
deve devolver vazio).

### 43.4.2 Os três presets

| | `individual` | `colaborativa` | `cega_por_pares` |
|---|---|---|---|
| Nome na interface | Individual | Triagem simples | Revisão cega por pares |
| `corpus_compartilhado` | — | ✔ | ✔ |
| `protocolo_coeditavel` | — | ✔ | ✔ |
| `revisores_por_estudo` | 1 | 1 | 2 (configurável) |
| `triagem_cega` | ✗ | ✗ | ✔ |
| `extracao_cega` | ✗ | ✗ | ✔ |
| `resolucao_de_conflito` | — | — | coordenador \| terceiro revisor |

`individual` é o que todo projeto existente vira na migração, e é
comportamentalmente idêntico ao Revsist de hoje.

### 43.4.3 Troca de modalidade (D-05)

Livre enquanto `COUNT(papers WHERE decision != 'Pendente' AND project_id = ?) == 0`.

Depois disso, `PUT /projects/{id}` rejeita a troca com **409** e mensagem que
diz o número de estudos já decididos. A saída é a rota
`POST /projects/{id}/screening/reabrir`, que exige papel `coordenador`, grava um
instantâneo em `deduplication_reports`-like (nova tabela não é necessária: um
`AuditLogModel` por estudo com `action="screening_reopened"` já registra o
antes), zera as decisões e troca a modalidade — tudo numa transação.

---

## 43.5 Papéis e permissões

| Operação | coordenador | revisor | observador |
|---|:---:|:---:|:---:|
| Ler projeto, protocolo, estudos | ✔ | ✔ | ✔ |
| Editar protocolo (objetivo, PICO, critérios, perguntas) | ✔ | ✔¹ | ✗ |
| Executar coleta | ✔ | ✔ | ✗ |
| Triar estudos | ✔ | ✔ | ✗ |
| Extrair dados | ✔ | ✔ | ✗ |
| Resolver conflito | ✔² | ✗ | ✗ |
| Reabrir triagem | ✔ | ✗ | ✗ |
| Convidar / remover membro | ✔ | ✗ | ✗ |
| Trocar modalidade | ✔ | ✗ | ✗ |
| Exportar | ✔ | ✔ | ✔ |
| Excluir projeto | ✔³ | ✗ | ✗ |
| Transferir titularidade | ✔³ | ✗ | ✗ |

¹ Se `protocolo_coeditavel`. É o "todos constroem juntos o protocolo" do pedido.
² Ou o terceiro revisor, se `resolucao_de_conflito == 'terceiro_revisor'`.
³ **Somente o dono** (`projects.owner_id`), não qualquer coordenador.

**Sobre `observador`:** existe porque orientador, bibliotecário e revisor
externo precisam ver sem poder alterar, e porque é o papel seguro para dar a
alguém enquanto se decide. Custa uma comparação.

---

## 43.6 Autorização — a mudança de uma função

`projeto_do_usuario` (`dependencies.py:198`) troca a igualdade por uma junção:

```python
projeto = (
    db.query(ProjectModel)
      .join(ProjectMemberModel, ProjectMemberModel.project_id == ProjectModel.id)
      .filter(
          ProjectModel.id == project_id,
          ProjectMemberModel.user_id == (usuario.id if usuario else None),
          ProjectMemberModel.is_active.is_(True),
      )
      .first()
)
```

**Continua devolvendo 404, nunca 403** — a razão de `dependencies.py:216` não
mudou: um 403 confirmaria que aquele UUID existe.

O papel entra como uma dependência **adicional**, não dentro desta:

```python
def exige_papel(*papeis: str) -> Callable: ...

# uso, no router:
router = APIRouter(
    prefix="/projects/{project_id}/protocol",
    dependencies=[Depends(projeto_do_usuario), Depends(exige_papel_de_escrita)],
)
```

Duas dependências separadas porque respondem a perguntas diferentes — *este
projeto é meu?* e *posso fazer isto nele?* — e porque a segunda varia por
router enquanto a primeira não.

`verificar_projeto_do_usuario` (`dependencies.py:244`, WebSocket) recebe a
mesma junção. É o que abre o canal ao vivo para a equipe (E-07).

`GET /projects` (`projects.py:46`) passa a listar por participação, e a
resposta ganha `my_role` e `member_count` — sem isso a lista de projetos não
sabe distinguir "meu" de "participo".

---

## 43.7 Cegueira

**P3 é o princípio; isto é o contrato.**

Enquanto `politica.triagem_cega` e o estudo não estiver em `consenso`,
`conflito` ou `resolvido`, a API **não devolve, sob nenhuma rota**:

1. `paper_screenings` de outro revisor — decisão, observações, critérios,
   confiança da IA;
2. `papers.decision` consolidada (é `Pendente` de fato, mas não pode nem
   sugerir progresso alheio);
3. `audit_logs` com `action="decision_changed"` de outro revisor;
4. qualquer agregado que permita inferir o julgamento individual — inclusive a
   contagem "1 de 2 revisores incluiu".

**Pode devolver**, porque não vaza julgamento e é necessário para trabalhar:

- quantos revisores já concluíram o estudo (`0 de 2`, `1 de 2`) — **sem** dizer
  qual foi a decisão nem quem;
- o próprio julgamento, integralmente;
- o progresso agregado da equipe no projeto (`320 de 900 estudos com dupla
  triagem concluída`).

> **Por que a contagem "1 de 2" é permitida e a contagem "1 incluiu" não é.**
> A primeira informa ritmo de trabalho. A segunda, com dois revisores e três
> decisões possíveis, revela o julgamento do par por eliminação assim que o
> segundo decide. Na dúvida, a regra é: se dá para reconstruir a decisão alheia
> a partir do agregado, não sai.

### 43.7.1 Onde a guarda mora

Numa função de serialização, não espalhada nas rotas:

```python
# app/services/blindness.py
def visao_do_revisor(paper, screenings, usuario_id, politica) -> PaperResponse: ...
```

Toda rota que devolve estudo passa por ela. As rotas afetadas são
`papers.py` (lista, detalhe, atualização), `extraction.py`, `insights.py`,
`screening_ai.py` e o WebSocket de triagem.

### 43.7.2 Como se prova

`backend/tests/test_security/test_cegueira.py`, na forma de
`test_no_secret_leak.py`: monta uma revisão cega com dois revisores, faz o
revisor A julgar, e então **varre o corpo de toda resposta que o revisor B
recebe** procurando o `screening_id` de A, o valor da decisão de A e o texto
das observações de A. Enumerando `app.routes`, como o teste de isolamento
(§42.4) — para que uma rota nova nasça coberta.

Verificação por mutação obrigatória: desligando a guarda, o teste tem de
falhar nomeando a rota que vazou.

---

## 43.8 Consolidação e conflito

`backend/app/services/consolidation_service.py`. É o **único** lugar que grava
`papers.decision`, `papers.screening_status` e `paper_criteria`.

```
consolidar(db, paper, politica) -> None
```

Chamada depois de todo julgamento gravado, na mesma transação.

### 43.8.1 A máquina de estados

```
                        nenhum julgamento
                               │
                        ┌──────▼──────┐
                        │ aguardando  │
                        └──────┬──────┘
                               │ primeiro julgamento
              ┌────────────────┴───────────────┐
   N == 1     │                                │  N > 1 e faltam julgamentos
              ▼                                ▼
        ┌──────────┐                    ┌─────────────┐
        │ consenso │◄───────┐           │   parcial   │
        └──────────┘        │           └──────┬──────┘
     decision = julgamento  │                  │ último julgamento chega
     (última escrita vence) │        ┌─────────┴─────────┐
                            │   todos iguais        divergem
                            │        │                   │
                            └────────┘            ┌──────▼──────┐
                                                  │  conflito   │
                                       decision = │  'Pendente' │
                                                  └──────┬──────┘
                                                         │ coordenador ou 3º revisor decide
                                                  ┌──────▼──────┐
                                                  │ resolvido   │
                                                  └─────────────┘
                                             decision = decisão da resolução
```

`legado` é terminal e sai dele no primeiro julgamento registrado.

### 43.8.2 Regras

- **`Pendente` não conta como julgamento.** Um revisor que abriu o estudo e não
  decidiu não move o estado.
- **Consenso exige igualdade estrita** entre `Incluído` e `Incluído`, ou
  `Excluído` e `Excluído`. Não há "quase de acordo".
- **Em `N == 1` a última escrita vence** — é literalmente o "ou pode ser editado
  por outros" do pedido, e o log de auditoria guarda a sucessão.
- **Critérios consolidados:** em consenso, a união dos critérios marcados pelos
  revisores concordantes; em resolução, os do resolvedor. A regra precisa ser
  determinística porque a exportação a lê.
- **Reversão:** se um revisor mudar o julgamento depois do consenso, o estudo
  volta para `parcial` ou `conflito` conforme o caso, e `papers.decision` volta
  a `Pendente`. Isso é correto e vai surpreender — a interface precisa avisar
  antes de gravar.

### 43.8.3 A fila de conflitos

`GET /projects/{id}/screening/conflitos` devolve os estudos em `conflito`, e
**aqui a cegueira acaba**: quem resolve precisa ver os dois julgamentos lado a
lado, com observações e critérios. Acesso restrito ao papel resolvedor
(§43.5).

---

## 43.9 Concordância entre revisores

Sai da mesma tabela de julgamentos. É o número que o periódico pede.

- **Concordância bruta** = `estudos com julgamentos idênticos / estudos com
  julgamento completo`. Sempre exibida.
- **κ de Cohen**, para exatamente 2 revisores:
  `κ = (Po − Pe) / (1 − Pe)`, com `Po` a concordância observada e `Pe` a
  esperada ao acaso a partir das marginais de cada revisor.
- **κ de Fleiss**, para 3 ou mais.
- Faixas exibidas junto ao valor (Landis & Koch): `< 0` péssima, `0–0,20`
  ligeira, `0,21–0,40` razoável, `0,41–0,60` moderada, `0,61–0,80` substancial,
  `0,81–1` quase perfeita.

**Só é calculado sobre estudos com julgamento completo**, e só é exibido depois
que ambos os revisores concluíram o estudo — antes disso seria um vazamento
agregado (§43.7).

Onde aparece: um bloco novo na aba **Indicadores**, que já existe (doc 31–33), e
uma linha na exportação (§43.15).

---

## 43.10 Convites de projeto

Três casos, um fluxo.

```
POST /projects/{id}/invitations   { email?, project_role, note? }   → coordenador
  ├─ gera 'RSAC-EQ-XXXX-YYYY', expira em 14 dias
  └─ devolve o código; o envio do e-mail é opcional (§43.10.1)

POST /projects/invitations/{code}/aceitar                            → autenticado
  ├─ caso 1: já tem conta e está autenticado  → cria project_members, pronto
  ├─ caso 2: já tem conta e não está          → login, e o código sobrevive à volta
  └─ caso 3: não tem conta                    → registro encadeado (§43.10.2)

DELETE /projects/{id}/invitations/{invite_id}                        → coordenador
GET    /projects/{id}/invitations                                    → coordenador
```

### 43.10.1 Envio

A v1 **não envia e-mail**. Devolve o código para o coordenador copiar e mandar
pelo canal que quiser. Motivo: infraestrutura de e-mail transacional
(remetente verificado, SPF/DKIM, tratamento de rejeição) é um projeto próprio,
e o convite funciona sem ela. O campo `email` existe para registrar a intenção
e para a fase futura de envio.

### 43.10.2 O caso 3 — quem ainda não tem conta

O convite de projeto **implica** o convite de plataforma. Aceitar um
`RSAC-EQ-...` sem conta leva ao mesmo formulário de registro da `LoginPage.tsx`
que hoje consome um `RSAC-...`, e ao fim dele a conta é criada **e** a
participação também, na mesma transação. Sem isso, o coordenador teria de
emitir dois códigos e explicar a ordem — atrito que faria a funcionalidade não
ser usada.

Consequência de segurança: um coordenador passa a poder criar contas na
plataforma indiretamente. É por isso que o teto de convites por projeto e por
conta (§43.17) não é opcional.

---

## 43.11 Credenciais, IA e custo

**P4.** Os cinco pontos de E-06 passam a resolver por ator:

| Ponto | Hoje | Passa a ser |
|---|---|---|
| `extraction.py:259` | `AISettingsModel.user_id == projeto.owner_id` | `== usuario.id` |
| `extraction.py:269` | `user_id=projeto.owner_id` | `user_id=usuario.id` |
| `harvest.py:301` | `SourceCredentialModel.user_id == projeto.owner_id` | `== usuario.id` |
| `harvesting_service.py:394` | dono do projeto | ator recebido por parâmetro |
| `pdf_acquisition.py:121` | `paper.project.owner_id` | ator, com o dono como fallback¹ |
| `screening_service.py:257` | já usa `actor.user_id` | mantém |

¹ A aquisição de PDF roda em segundo plano, disparada por lote. O ator é quem
disparou o lote; o fallback para o dono só cobre execuções retomadas sem ator
conhecido.

**Quando o ator não tem chave:** erro **412 Precondition Failed** com mensagem
nomeando o que falta e onde configurar. Nunca cair no dono em silêncio — é o
comportamento que se está corrigindo.

**Na interface:** a barra de status já mostra o modo de assistência. Passa a
mostrar também, na aba Equipe, quais membros têm chave configurada para quais
provedores — sem revelar nada da chave. Ninguém precisa descobrir por tentativa
que o colega não consegue usar a IA.

---

## 43.12 Colaboração ao vivo

O que faz "se um já coletou, aparece para todos" ser verdade sem recarregar a
página.

### 43.12.1 O canal

O WebSocket por projeto já existe (`services/harvesting_service.py:ws_manager`,
`api/v1/harvest.py`, `api/v1/screening_ai.py`) e passa a aceitar qualquer
membro ativo (§43.6). Ganha eventos novos:

| Evento | Carga | Quando |
|---|---|---|
| `paper.decidido` | `paper_id`, `screening_status`, `decision`¹ | julgamento gravado |
| `paper.conflito` | `paper_id` | consolidação detecta divergência |
| `protocolo.alterado` | `secao`, `por`, `updated_at` | protocolo gravado |
| `coleta.concluida` | `run_id`, `por`, `novos` | fim de coleta |
| `equipe.alterada` | `user_id`, `acao` | entrada/saída de membro |
| `presenca` | `user_id`, `tela` | entrada/saída de tela |

¹ `decision` é omitida quando a política é cega e o estudo não está consolidado
(§43.7). O evento não é exceção à cegueira.

### 43.12.2 Escrita concorrente (E-09)

`protocols.py` passa a exigir `If-Match` com o `updated_at` que o cliente leu.
Divergiu → **409** com o corpo atual, e a interface oferece "recarregar" ou
"sobrescrever". O mesmo vale para `PATCH /papers/{id}` em modalidade
colaborativa.

Isto **não** é edição colaborativa em tempo real de texto (CRDT). É detecção
honesta de conflito. O doc §43.18 registra por quê.

---

## 43.13 Ciclo de vida: saída, transferência, eliminação

A parte mais delicada (E-08).

### 43.13.1 Sair da equipe

`DELETE /projects/{id}/members/{user_id}` (coordenador remove; ou o próprio
membro sai). Efeito: `is_active = False`, `left_at` preenchido. **Nada é
apagado.** Os julgamentos do revisor permanecem, e continuam contando para a
consolidação e para o κ — porque foram feitos, e a revisão os relata.

Se a saída deixar um estudo abaixo de `reviewers_per_paper`, ele volta a
`parcial` e entra numa fila "precisa de novo revisor". A alternativa —
manter o consenso obtido com quem saiu — também é defensável; a escolha aqui é
a conservadora, e ela é a que se declara no método.

### 43.13.2 Transferir a titularidade

`POST /projects/{id}/transferir` — só o dono, só para um coordenador ativo.
Move `projects.owner_id`. Existe porque o dono é o controlador dos dados e
quem responde pelo projeto; sem transferência, sair da plataforma seria
impossível sem destruir a revisão.

### 43.13.3 Eliminar a conta

`executar_eliminacao_completa_usuario` (`me.py:90`) ganha um passo **antes** de
tudo, e o comportamento passa a depender do projeto:

| Situação do projeto | O que acontece |
|---|---|
| Usuário é dono, é o único membro ativo | Apagado, como hoje |
| Usuário é dono, há outros membros ativos | **Titularidade transferida** para o coordenador ativo mais antigo; se não houver coordenador, para o revisor mais antigo, promovido |
| Usuário é membro, não é dono | Participação desativada; projeto intacto |

E, em todos os casos, os julgamentos e respostas do usuário são
**pseudonimizados, não apagados**:

```
paper_screenings.reviewer_id            → NULL
paper_screenings.reviewer_label         → 'Revisor 2 (conta removida)'   # coluna nova
reviewer_extraction_answers.reviewer_id → NULL   (idem)
audit_logs.user_id / username           → NULL / 'conta removida'
```

**Por que não apagar.** Apagar mudaria retroativamente o resultado de uma
revisão sistemática — o κ, o número de conflitos, o fluxograma. É alteração
silenciosa de registro científico produzido em conjunto. A base legal para
manter é o art. 16, II da LGPD (estudo por órgão de pesquisa, com
anonimização) somada ao art. 7º, IV. O que **é** apagado é tudo que identifica:
nome, e-mail, `google_sub`, credenciais, sessões — que já saem com a linha de
`users`.

**Isto precisa estar escrito na Política de Privacidade** (`planejamento/PRIVACIDADE.md`)
**antes** de o primeiro convite ser aceito. Não depois.

### 43.13.4 O rótulo do revisor

`paper_screenings.reviewer_label` (String, default `""`) é preenchido só na
pseudonimização. Enquanto há conta, o nome vem de `users`. É o campo que
permite a exportação continuar dizendo "Revisor 1 / Revisor 2" depois de uma
saída.

---

## 43.14 LGPD e ROPA

Operações novas a registrar em `ropa_service.registrar` (`services/ropa_service.py`):

| `operation` | `legal_basis` | `data_categories` |
|---|---|---|
| `team_invitation_issued` | `art7_V_execucao_de_contrato` | `identificacao`, `contato` |
| `team_membership_created` | `art7_V_execucao_de_contrato` | `identificacao` |
| `team_membership_revoked` | `art7_V_execucao_de_contrato` | `identificacao` |
| `project_ownership_transferred` | `art7_V_execucao_de_contrato` | `identificacao`, `conteudo_de_pesquisa` |
| `reviewer_pseudonymised` | `art16_II_estudo_por_orgao_de_pesquisa` | `identificacao` |

`data_categories` só aceita nomes de lista fechada (`ropa_service.py`) — a
categoria `art16_II_...` de base legal precisa ser acrescentada lá, e a lista
é a garantia de que nenhum e-mail entra por engano no ROPA.

Itens do doc 38 a reaferir ao fim da Fase 6: os de titularidade, eliminação e
compartilhamento com terceiros — o convite é **compartilhamento de dado de
pesquisa com outro titular**, e é a primeira vez que o Revsist faz isso.

---

## 43.15 Exportação e reprodutibilidade

É o que fecha o ciclo (E-12). A planilha e o fluxograma passam a declarar o
método, não só o resultado.

**Nova aba na planilha — `Equipe e Concordância`:**

| Campo | Exemplo |
|---|---|
| Modalidade | Revisão cega por pares |
| Revisores por estudo | 2 |
| Revisores | Revisor 1 (A. Silva), Revisor 2 (B. Costa) |
| Resolução de conflito | Coordenador |
| Estudos com dupla triagem | 900 |
| Concordância bruta | 87,3% |
| κ de Cohen | 0,74 (substancial) |
| Conflitos | 114 |
| Conflitos resolvidos | 114 |
| Período | 12/03/2026 a 02/05/2026 |

**Na aba de estudos**, colunas novas: `Decisão R1`, `Decisão R2`, `Conflito`,
`Resolvido por`.

**No fluxograma PRISMA**, a nota de rodapé passa a dizer: *"Registros triados
independentemente por 2 revisores; discordâncias resolvidas por consenso do
coordenador (κ = 0,74)."* É a frase que o item 8 do PRISMA 2020 pede.

---

## 43.16 Interface

### 43.16.1 Telas

**Nova página `TeamPage` — `/projects/:id/team`.** Membros com papel e último
acesso, convites pendentes com código copiável, modalidade e sua troca, quem
tem chave de IA configurada, botão de transferir titularidade.

**`ProjectsPage`.** Cada cartão ganha selo de equipe (`3 membros`), o papel de
quem olha (`você: revisor`) e a modalidade. Filtro "meus / participo".

**`ScreeningPage`.** Em modalidade cega: o cabeçalho passa a dizer *sua*
decisão; a fila mostra `1 de 2` sem revelar julgamento; some tudo que
indicaria a decisão do par. Para o coordenador, uma quarta aba na navegação
segmentada móvel — **Conflitos** — com os dois julgamentos lado a lado.

**`InsightsPage`.** Bloco de concordância: κ com faixa, matriz 3×3 de
julgamentos cruzados, série de conflitos ao longo do tempo.

**`ProtocolPage`.** Indicador de presença ("B. Costa está editando Critérios") e
o diálogo de conflito de versão do §43.12.2.

### 43.16.2 Ribbon

A aba **Arquivo** ganha um grupo `Equipe` com `Convidar` e `Membros`. Não é uma
aba nova do ribbon: a equipe é atributo do projeto, e o ribbon já tem nove abas
— a décima passaria a gaveta móvel de rolagem confortável para lista longa.

### 43.16.3 Móvel

Tudo acima nasce dentro da camada de adaptação móvel
(`frontend/src/styles/mobile.css`). Em particular: a lista de membros é grade de
uma coluna, a fila de conflitos usa o padrão de navegação segmentada que
Triagem e Extração já usam, e a exibição lado a lado dos dois julgamentos
empilha — nunca duas colunas em 375px.

---

## 43.17 Limites

Acrescentados a `config.py`, junto de `max_projects_per_user` (`config.py:78`):

```python
max_members_per_project: int = 12
max_memberships_per_user: int = 50      # projetos dos quais participo
max_pending_invitations_per_project: int = 20
max_invitations_per_user_per_day: int = 30
project_invitation_ttl_days: int = 14
```

`max_projects_per_user` continua contando **só os próprios** (`projects.py:67`):
participar não consome a cota de ninguém. `max_memberships_per_user` é o teto
do outro lado.

---

## 43.18 O que fica de fora da v1

Registrado para não ser reaberto a cada revisão de escopo:

- **Grupo de pesquisa durável** entre projetos (D-02). A tabela de participação
  aceita um `group_id` depois, sem migração destrutiva.
- **Coleta individual por revisor** (D-01). Se for decidido ao contrário,
  entra como fase própria: escopo por revisor em `papers`, deduplicação entre
  corpora, e um passo de união no funil.
- **Edição colaborativa de texto em tempo real** (CRDT/OT no protocolo). Custo
  desproporcional ao ganho: o protocolo é escrito em sessões, não a quatro mãos
  no mesmo parágrafo. Detecção de conflito por versão resolve o caso real.
- **Envio de e-mail de convite** (§43.10.1).
- **Comentários e discussão por estudo.** É o pedido seguinte mais provável, e
  é uma tabela nova independente de tudo que está aqui.
- **Cegueira de identidade** (revisor não saber *quem* é o par). Nenhuma
  diretriz exige, e complicaria a atribuição na exportação.
- **Papel por etapa** (ser revisor na triagem e observador na extração). Não há
  demanda; o papel único cobre o caso descrito.
