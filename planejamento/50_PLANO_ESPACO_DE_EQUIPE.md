# 50 — Plano: Espaço de Equipe, Trabalhos Compartilhados e Mural

> **Documento único: diagnóstico → especificação → execução.** Difere da
> gramática de três documentos dos planos anteriores porque o diagnóstico já
> foi feito — está no doc 42 — e o que se abre aqui é a **decisão D-02
> revertida**: o grupo de pesquisa durável, que o doc 43 §43.18 registrou como
> fora da v1, passa a ser o escopo.
> **Precedentes obrigatórios:** [`42`](./42_DIAGNOSTICO_PESQUISA_EM_EQUIPE.md),
> [`43`](./43_ESPECIFICACAO_PESQUISA_EM_EQUIPE.md),
> [`44`](./44_PLANO_EXECUCAO_PESQUISA_EM_EQUIPE.md).
> **Restrições herdadas:** [`38`](./38_CHECKLIST_LGPD.md) (LGPD),
> [`40`](./40_ESPECIFICACAO_ONLINE.md) (titularidade e isolamento),
> [`24`](./24_ESPECIFICACAO_DESIGN_SYSTEM.md) (tokens e móvel).
>
> **Estimativa total: 21 a 28 dias de trabalho focado.**
> **Aberto em:** 01/09/2026.

---

## 50.1 O que se pediu

Em uma frase: **a equipe deixa de ser um atributo de cada revisão e passa a ser
um lugar** — um perfil compartilhado, com identidade própria, onde ficam os
trabalhos da equipe, quem pode entrar em cada um, e um mural onde as pessoas
conversam.

Decomposto em quatro pedidos verificáveis:

| # | Pedido | O que significa tecnicamente |
|---|---|---|
| **R-1** | "um perfil que os membros compartilham" | Entidade durável, com nome, identificador, descrição e composição próprias — independente de qualquer revisão |
| **R-2** | "os trabalhos ali colocados podem ser trabalhados pelos seus membros" | Um projeto passa a poder **pertencer** a uma equipe, e o pertencimento à equipe é caminho de entrada no trabalho |
| **R-3** | "controle de quem está envolvido em cada trabalho específico, com permissões com papéis" | Duas camadas de autorização: papel **na equipe** e papel **no trabalho** — e uma política, por trabalho, de quanto a equipe alcança |
| **R-4** | "no início do perfil da equipe, um mural para comunicação" | Publicações, comentários, fixação, não lidos e tempo real — a tela inicial do perfil |

---

## 50.2 O que já existe — medido no código

Isto **não** é um começo do zero. As fases do doc 44 estão entregues, e metade
do que R-3 pede já roda:

| Peça | Onde | Estado |
|---|---|---|
| Participação em projeto | `ProjectMemberModel` (`backend/app/infrastructure/persistence/models.py:145`) | ✅ com `project_role`, `is_active`, `left_at` |
| Barreira de isolamento por participação | `projeto_do_usuario` (`backend/app/security/dependencies.py:218`) | ✅ junção, 404 e não 403 |
| Mesma barreira no WebSocket | `verificar_projeto_do_usuario` (`dependencies.py:274`) | ✅ |
| Papéis e matriz de permissões | `exige_papel` (`dependencies.py:303`), `exige_dono_do_projeto` (`dependencies.py:370`) | ✅ coordenador / revisor / observador |
| Convite de projeto | `ProjectInvitationModel` (`models.py:193`), `backend/app/api/v1/team.py` | ✅ código `RSAC-EQ-…`, TTL, revogação |
| Tela de equipe do projeto | `frontend/src/pages/TeamPage.tsx` (910 linhas) | ✅ membros, convites, modalidade |
| Canal ao vivo com presença | `ConnectionManager` (`backend/app/services/harvesting_service.py:42`), `ws_manager` (`:196`), rota em `backend/app/api/v1/projects.py:443` | ✅ chaveado por `project_id` |
| Bilhete de canal (credencial de WebSocket) | `backend/app/security/bilhete_de_canal.py` | ✅ |
| ROPA com vocabulário fechado | `backend/app/services/ropa_service.py` | ✅ já tem `team_membership_created` etc. |
| Tetos de equipe | `backend/app/config.py:80-81` | ✅ `max_members_per_project`, `max_active_invitations_per_project` |

**A conclusão que orienta tudo o que vem depois:** o trabalho pesado — a
barreira de isolamento por participação — já está feito e testado. O que falta
é uma entidade **acima** do projeto e um lugar de conversa. Nada do que este
plano acrescenta pode virar desculpa para mexer naquela junção.

---

## 50.3 A lacuna — sete achados

| # | Achado | Evidência | Gravidade | Fecha na fase |
|---|---|---|---|---|
| **Q-01** | Não existe entidade durável de equipe: a composição morre com o projeto | Não há tabela acima de `projects`; `project_members.project_id` é obrigatório (`models.py:154`) | bloqueante | 1 |
| **Q-02** | Convidar cinco pessoas para três revisões custa quinze convites | `team.py:293` emite convite **por projeto**; não há reaproveitamento de composição | alta | 3 |
| **Q-03** | Um projeto não sabe dizer a que grupo pertence | `ProjectModel` não tem coluna de pertencimento (`models.py:85`) | bloqueante | 3 |
| **Q-04** | Não há como declarar "este trabalho é aberto à equipe" nem "este é restrito" | A única política de acesso é a linha em `project_members` — tudo ou nada | alta | 3 |
| **Q-05** | Não há canal de comunicação: nem mural, nem recado, nem aviso | Nenhuma tabela de conteúdo escrito por usuário; o único texto livre é `note` do convite (`models.py:246`) | alta (é R-4) | 5 |
| **Q-06** | O canal ao vivo é chaveado por projeto e não atende agrupamento maior | `ws_manager` indexa por `project_id` (`harvesting_service.py:42`) | média | 6 |
| **Q-07** | A palavra "Equipe" já está tomada pela participação em projeto | `TeamPage.tsx`, grupo `Equipe` do ribbon (`frontend/src/components/layout/TopRibbonBar.tsx:435`) | baixa, mas contamina tudo | 0 |

**Q-07 é o achado que mais barato se fecha e mais caro se ignora.** Se a
palavra não for separada antes da primeira linha de código, o repositório passa
a ter dois significados de "equipe" convivendo em nome de arquivo, de rota e de
tela — o mesmo erro que o doc 43 evitou ao escolher `project_role` em vez de
`role` (E-10).

---

## 50.4 Vocabulário

Palavras com significado fixo neste documento e no código.

| Termo | Significa | Não significa |
|---|---|---|
| **Equipe** (ou **Espaço de Equipe**) | A entidade durável nova: perfil, composição e mural. Tabela `equipes` | O conjunto de participantes de uma revisão — isso passa a chamar-se *participação* |
| **Trabalho** | Uma revisão sistemática vista de dentro da equipe. É `ProjectModel`, sem tabela nova | Uma tarefa de processamento |
| **Participação** | A linha em `project_members`: quem está envolvido **naquele** trabalho | Pertencer à equipe |
| **Papel de equipe** | `administrador`, `membro`, `convidado` — vale no perfil e no mural | `project_role`, que vale dentro de um trabalho |
| **Titular da equipe** | `equipes.owner_id` — controlador dos dados perante a LGPD | Administrador; todo titular é administrador, nem todo administrador é titular |
| **Acesso da equipe** | A política, **por trabalho**, de quanto a equipe alcança: `restrito`, `listado`, `aberto` | Um papel |
| **Ingresso** | O ato de um membro da equipe passar a participar de um trabalho — que **grava uma linha** | Um cálculo feito na hora de autorizar |
| **Mural** | O quadro de comunicação da equipe: publicações, comentários e eventos | Um chat; não há mensagem direta nem sala por assunto |
| **Publicação** | Uma entrada do mural | Um artigo científico |

**Consequência de nomenclatura (Q-07):** `TeamPage.tsx` e o grupo `Equipe` do
ribbon passam a chamar-se **Participantes** na interface. As colunas, classes e
rotas existentes (`ProjectMemberModel`, `project_role`, `/projects/:id/team`)
**não são renomeadas** — renomear tabela e rota em produção custa migração e
quebra convite em trânsito, e o ganho seria estético. Rótulo muda; esquema não.

---

## 50.5 Os seis princípios

Regras duras. Uma decisão de implementação que contrarie qualquer uma delas
está errada, mesmo que funcione.

**PE1 · A barreira de isolamento não ganha um `OR`.**
`projeto_do_usuario` (`dependencies.py:218`) continua sendo *exatamente* a
junção com `project_members`. Pertencer à equipe **não** autoriza a ler um
trabalho: autoriza a **ingressar** nele, quando a política do trabalho permite,
e o ingresso grava a participação. A única função que separa o acervo de um
assinante do de outro não vira uma expressão com duas tabelas e três estados.
Verificável: `grep -rn "equipe" backend/app/security/` deve devolver vazio.

**PE2 · O ingresso é um ato, não uma consulta.**
Toda entrada em trabalho produz linha em `project_members`, com `joined_at`,
autoria do convite (ou marca de auto-ingresso) e registro em `audit_logs`.
Consequência prática: "quem trabalhou nesta revisão" continua sendo respondível
por uma consulta a uma tabela, e não por reconstituição de política.

**PE3 · Papel de equipe nunca sobrescreve papel de trabalho.**
Um administrador da equipe **não** é coordenador dos trabalhos dela. Ele pode
ver que existem, pode entrar nos que a política abre, e o que ele puder fazer
lá dentro é o que o `project_role` dele disser. As duas matrizes (§50.7.3 e
§43.5) se compõem por interseção, nunca por promoção.

**PE4 · Nenhum acesso silencioso.**
Ingresso, remoção, mudança de política de acesso e alteração de papel são
eventos **visíveis** — no mural como publicação de sistema, e em `audit_logs`.
Um perfil compartilhado só é confiável se ninguém aparece dentro do trabalho
alheio sem deixar rastro que os outros vejam sem procurar.

**PE5 · O mural é comunicação, não registro científico.**
Isto tem consequência jurídica direta, e é o inverso de §43.13.3: julgamento de
triagem se **pseudonimiza** ao eliminar a conta, porque alterá-lo falsearia um
resultado publicado; publicação de mural se **apaga**, porque é fala de uma
pessoa e não faz parte do método. Confundir os dois regimes é o erro de LGPD
mais provável deste plano.

**PE6 · `equipe_id` nulo é o Revsist de hoje.**
Todo projeto existente permanece sem equipe, e nada no seu comportamento muda.
Nenhuma migração move projeto para equipe alguma; nenhuma tela obriga a criar
equipe para trabalhar sozinho. A funcionalidade é aditiva ou não é.

---

## 50.6 Modelo de dados

Sete tabelas novas, duas colunas novas em `projects`. Tudo por revisão Alembic,
conferida linha a linha — a autogeração erra índice e tipo (lição do doc 41
Fase 0). Nomes em português, seguindo a convenção dos módulos recentes
(`bilhete_de_canal.py`, `triabilidade.py`, `acelerador.py`).

### 50.6.1 `equipes` — o perfil

```python
class EquipeModel(Base):
    __tablename__ = "equipes"
    __table_args__ = (
        UniqueConstraint("identificador", name="uq_equipes_identificador"),
        Index("ix_equipes_owner", "owner_id"),
    )

    id: str                        # uuid
    identificador: str             # 'lab-epidemio-ufmg' — [a-z0-9-]{3,32}, único
    nome: str                      # 'Laboratório de Epidemiologia — UFMG'
    descricao: str = ""            # texto livre, até 2000 caracteres
    instituicao: str = ""
    area_de_pesquisa: str = ""
    emblema: str = ""              # 2 letras ou 1 emoji — sem upload na v1
    cor_do_emblema: str = ""       # NOME de token do doc 24, nunca hexadecimal
    visibilidade: str = "privada"  # 'privada' | 'por_identificador'
    owner_id: str                  # FK users.id — o titular
    is_archived: bool = False
    created_at / updated_at: datetime
```

**`identificador`, e não `slug`.** É o que aparece no convite e o que a pessoa
digita para achar a equipe; merece nome que não exija saber inglês de
programador. É **imutável** depois de criado — mudá-lo invalidaria convites em
trânsito e links já compartilhados.

**Sem upload de imagem na v1.** Emblema é duas letras sobre um token de cor. Um
avatar exigiria armazenamento, cota, varredura de conteúdo e caminho de remoção
sob a LGPD — quatro problemas por um ganho estético. Fica em §50.15.

**`visibilidade`.** `privada` (padrão) não aparece em busca alguma: só se entra
por convite. `por_identificador` permite que quem sabe o identificador exato
peça para entrar. **Não existe diretório público de equipes na v1** — seria
publicar vínculo institucional de pesquisador, que é dado pessoal, sem base
legal para isso.

### 50.6.2 `equipe_membros` — a composição

```python
class EquipeMembroModel(Base):
    __tablename__ = "equipe_membros"
    __table_args__ = (
        UniqueConstraint("equipe_id", "user_id", name="uq_equipe_membros_equipe_user"),
        Index("ix_equipe_membros_user", "user_id"),
        Index("ix_equipe_membros_equipe", "equipe_id"),
    )

    id: str
    equipe_id: str                 # FK equipes.id ON DELETE CASCADE
    user_id: str                   # FK users.id ON DELETE CASCADE
    papel_de_equipe: str           # 'administrador' | 'membro' | 'convidado'
    is_active: bool = True
    convidado_por_user_id: str | None
    joined_at: datetime
    left_at: datetime | None
    titulo: str = ""               # 'Orientador', 'Bolsista PIBIC' — rótulo livre
```

Espelha `ProjectMemberModel` de propósito: mesma forma, mesmas garantias, mesmo
`is_active` em vez de `DELETE` (§43.3.1). Quem sai da equipe deixa publicações
no mural e participações em trabalhos que continuam válidas.

O titular tem obrigatoriamente linha com `papel_de_equipe='administrador'`,
criada na mesma transação da equipe — a autorização olha só esta tabela, nunca
`owner_id`. É o mesmo desenho de §43.3.1, pela mesma razão: duas fontes de
verdade para autorização divergem em produção, não em teste.

`titulo` é enfeite honesto: um laboratório real quer dizer quem é orientador e
quem é bolsista, e isso não é papel de permissão. Campo separado evita que
alguém invente papéis só para exibir hierarquia.

### 50.6.3 `equipe_convites` — o convite de equipe

```python
class EquipeConviteModel(Base):
    __tablename__ = "equipe_convites"

    id: str
    equipe_id: str
    codigo: str                    # 'RSAC-ESP-XXXX-YYYY', único
    email: str | None
    papel_de_equipe: str = "membro"
    criado_por_user_id: str
    created_at / expires_at        # TTL padrão 14 dias
    aceito_em: datetime | None
    aceito_por_user_id: str | None
    revogado_em: datetime | None
    nota: str = ""
```

**Prefixo `RSAC-ESP-` (espaço), e não um `RSAC-EQ…` estendido.** O convite de
projeto já usa `RSAC-EQ-`; um prefixo novo que **comece** por `RSAC-EQ` faria o
despachante de código depender de casar o prefixo mais longo primeiro — bug
silencioso esperando a primeira refatoração. Prefixos irmãos, nunca aninhados.
O campo único da tela de login despacha três famílias: `RSAC-` (conta,
`InviteCodeModel`), `RSAC-EQ-` (participação em trabalho), `RSAC-ESP-` (equipe).

### 50.6.4 `projects` — duas colunas

```python
    equipe_id: str | None = None      # FK equipes.id ON DELETE SET NULL
    acesso_da_equipe: str = "listado" # 'restrito' | 'listado' | 'aberto'
```

| Valor | O membro da equipe que **não** participa | O membro que participa |
|---|---|---|
| `restrito` | Não vê o trabalho na aba Trabalhos; 404 em tudo | Trabalha normalmente |
| `listado` *(padrão)* | Vê título, área, coordenador e progresso agregado; pode **pedir** participação | Idem |
| `aberto` | Vê o mesmo e pode **ingressar sozinho**, com papel `revisor` | Idem |

Duas colunas, não uma tabela de política: são valores lidos em toda listagem do
perfil, e precisam de índice e de `CHECK`.

`ON DELETE SET NULL`, nunca `CASCADE`: **apagar uma equipe não apaga revisão
alguma.** Os trabalhos voltam a ser pessoais, de seus `owner_id`. É a diferença
entre desfazer um agrupamento e destruir meses de trabalho de outras pessoas.

**Nenhuma coluna `equipe_id` em `papers`, `protocols` ou qualquer filho.** O
pertencimento é do projeto; tudo abaixo já é isolado pelo `project_id`.

### 50.6.5 `pedidos_de_participacao` — o pedido de entrada

```python
class PedidoDeParticipacaoModel(Base):
    __tablename__ = "pedidos_de_participacao"
    __table_args__ = (
        Index("ix_pedidos_projeto_estado", "project_id", "estado"),
    )

    id: str
    project_id: str
    user_id: str
    mensagem: str = ""             # até 500 caracteres
    estado: str = "pendente"       # 'pendente' | 'aceito' | 'recusado' | 'cancelado'
    decidido_por_user_id: str | None
    decidido_em: datetime | None
    created_at: datetime
```

Só existe para trabalho `listado`. Em `aberto` o ingresso é direto; em
`restrito` a rota devolve **404** — não 403, pelo mesmo motivo de §43.6: um 403
confirmaria que aquele trabalho existe.

Índice parcial em vez de `UNIQUE(project_id, user_id)`: a pessoa pode pedir de
novo depois de uma recusa, mas não pode ter dois pedidos pendentes — o que a
rota garante em transação, porque `UNIQUE` com estado dentro da chave permitiria
"aceito" e "recusado" duplicados sem sentido.

### 50.6.6 `mural_publicacoes` — o mural

```python
class MuralPublicacaoModel(Base):
    __tablename__ = "mural_publicacoes"
    __table_args__ = (
        Index("ix_mural_equipe_criacao", "equipe_id", "created_at"),
        Index("ix_mural_equipe_fixada", "equipe_id", "fixada_em"),
    )

    id: str
    equipe_id: str                 # FK equipes.id ON DELETE CASCADE
    autor_user_id: str | None      # NULL quando a conta foi eliminada
    autor_rotulo: str = ""         # preenchido só na eliminação da conta
    tipo: str = "recado"           # 'recado' | 'aviso' | 'sistema'
    corpo: str                     # até 4000 caracteres, TEXTO PURO
    project_id: str | None         # publicação ancorada num trabalho
    exige_ciencia: bool = False    # só faz sentido em 'aviso'
    fixada_em: datetime | None
    fixada_por_user_id: str | None
    editada_em: datetime | None
    removida_em: datetime | None
    removida_por_user_id: str | None
    created_at: datetime
```

**`corpo` é texto puro, não HTML nem Markdown com HTML embutido.** A interface
reconhece quebra de linha, `@menção` e link — e nada mais. Aceitar HTML de
usuário num app que já tem sessão por cookie é abrir XSS armazenado no lugar
mais visitado do produto. A regra é do servidor, não do componente: a rota
rejeita marcação, e o teste prova com uma carga de `<script>`.

**`project_id` anulável** liga a publicação a um trabalho ("terminei a triagem
do lote 3"). Quando o trabalho é `restrito`, a publicação **não** é entregue a
quem não participa — a guarda de §50.7.5 vale também para o mural.

### 50.6.7 `mural_comentarios`

```python
    id / publicacao_id / autor_user_id / autor_rotulo
    corpo: str                     # até 2000 caracteres
    editado_em / removido_em / removido_por_user_id / created_at
```

Um nível só: comentário responde à publicação, nunca a outro comentário. Fio
aninhado é a diferença entre um quadro de recados e um fórum, e um fórum pede
moderação que uma equipe de laboratório não vai exercer.

### 50.6.8 `mural_leituras` e `mural_ciencias`

```python
class MuralLeituraModel(Base):        # o "não lidos"
    __tablename__ = "mural_leituras"
    # UNIQUE(equipe_id, user_id)
    equipe_id / user_id / visto_ate: datetime

class MuralCienciaModel(Base):        # o "li e estou ciente"
    __tablename__ = "mural_ciencias"
    # UNIQUE(publicacao_id, user_id)
    publicacao_id / user_id / created_at
```

`visto_ate` é um carimbo por usuário e equipe — não uma linha por publicação
lida. Cem publicações e vinte membros dariam duas mil linhas só para exibir um
número numa bolinha.

`mural_ciencias` existe porque, num laboratório real, "leram o aviso da
submissão?" é pergunta operacional, e responder por ausência de resposta não
funciona.

### 50.6.9 O que **não** muda

Registro explícito, porque a tentação de mexer é grande:

- `projeto_do_usuario` e `verificar_projeto_do_usuario` — **nem uma linha** (PE1)
- `project_members`, `project_role` e a matriz de §43.5
- `projects.owner_id` — titularidade do trabalho, independente da equipe
- `project_invitations` e o prefixo `RSAC-EQ-`
- `papers`, `paper_screenings`, `extraction_answers` e todo o pipeline
- `max_projects_per_user`, que continua contando **só** `owner_id`
  (`backend/app/api/v1/projects.py:104`): trabalho de equipe consome a cota de
  quem o criou, e participar não consome a de ninguém

---

## 50.7 Autorização em duas camadas

### 50.7.1 A regra, inteira

```
Ler ou escrever DENTRO de um trabalho
    ⟺ existe project_members(project_id, user_id, is_active=True)
      E o project_role autoriza aquela operação (§43.5)

Ver que um trabalho EXISTE, no perfil da equipe
    ⟺ equipe_membros(equipe_id, user_id, is_active=True)
      E projects.acesso_da_equipe != 'restrito'

Passar de "ver que existe" para "participar"
    ⟺ ato explícito: ingresso (aberto), pedido aceito (listado)
      ou adição por um coordenador do trabalho
```

Três perguntas diferentes, três respostas de fontes diferentes. O que as mantém
separadas é PE1: a primeira nunca consulta `equipes`.

### 50.7.2 Por que não um `OR` na junção

A tentação é óbvia — bastaria trocar o filtro de `projeto_do_usuario` por
"participa do projeto **ou** pertence à equipe do projeto e o acesso não é
restrito". Custaria uma linha e entregaria R-2 numa tarde.

Três razões para não fazer:

1. **A superfície de erro.** Aquela função é a única coisa entre o acervo de um
   assinante e o de outro. Hoje o teste de mutação do doc 44 Fase 0 prova que
   remover `is_active` quebra a suíte. Com um `OR` de três condições sobre duas
   tabelas, o espaço de mutações que *não* quebram nada cresce — e a prova
   enfraquece exatamente onde precisa ser mais forte.
2. **A pergunta do revisor.** "Quem trabalhou nesta revisão?" precisa ser uma
   consulta a `project_members`. Com acesso derivado de política, a resposta
   vira "todo mundo que pertencia à equipe entre março e maio, se a política
   fosse aberta naquele intervalo" — e ninguém guarda o histórico da política.
3. **A LGPD.** O doc 38 exige saber quem teve acesso a que dado de pesquisa.
   Uma linha com `joined_at` responde; uma política avaliada em tempo de
   requisição, não.

O custo do ingresso materializado é uma requisição a mais na primeira vez que
alguém abre um trabalho aberto. É barato.

### 50.7.3 Matriz de permissões da equipe

| Operação | titular | administrador | membro | convidado |
|---|:---:|:---:|:---:|:---:|
| Ver o perfil e o mural | ✔ | ✔ | ✔ | ✔ |
| Publicar no mural | ✔ | ✔ | ✔ | ✗ |
| Comentar | ✔ | ✔ | ✔ | ✔ |
| Fixar / desafixar publicação | ✔ | ✔ | ✗ | ✗ |
| Remover publicação de outro | ✔ | ✔ | ✗ | ✗ |
| Remover a própria publicação | ✔ | ✔ | ✔ | ✔ |
| Ver a lista de trabalhos não restritos | ✔ | ✔ | ✔ | ✗¹ |
| Criar trabalho dentro da equipe | ✔ | ✔ | ✔ | ✗ |
| Ingressar em trabalho `aberto` | ✔ | ✔ | ✔ | ✗ |
| Pedir participação em `listado` | ✔ | ✔ | ✔ | ✗ |
| Mover trabalho **próprio** para a equipe | ✔ | ✔ | ✔ | ✗ |
| Tirar trabalho da equipe | ✔² | ✔² | ✔² | ✗ |
| Mudar `acesso_da_equipe` de um trabalho | ✗³ | ✗³ | ✗³ | ✗ |
| Convidar / remover membro da equipe | ✔ | ✔ | ✗ | ✗ |
| Trocar papel de membro | ✔ | ✔⁴ | ✗ | ✗ |
| Editar o perfil da equipe | ✔ | ✔ | ✗ | ✗ |
| Arquivar / excluir a equipe | ✔ | ✗ | ✗ | ✗ |
| Transferir a titularidade | ✔ | ✗ | ✗ | ✗ |

¹ O convidado vê só os trabalhos em que participa. É o papel do orientador
externo e do bibliotecário: entra pelo mural, não pelo acervo.
² Só o dono do trabalho (`projects.owner_id`).
³ **Nem o titular da equipe.** É atributo do trabalho, e quem o define é o
coordenador dele (§50.7.5).
⁴ Administrador não promove nem rebaixa outro administrador — só o titular.

### 50.7.4 Como as duas matrizes se compõem

Por **interseção**, nunca por promoção (PE3). Dois exemplos que fecham a dúvida:

- Titular da equipe, `observador` num trabalho → **lê e não escreve** naquele
  trabalho. Ser dono do laboratório não dá direito de triar.
- `convidado` na equipe, `coordenador` num trabalho → **coordena** aquele
  trabalho por inteiro, e continua sem poder publicar no mural.

Implementação: nenhuma dependência nova nas rotas de projeto. As rotas de equipe
ganham `exige_papel_de_equipe(*papeis)`, gêmea de `exige_papel`
(`dependencies.py:303`), e é só.

### 50.7.5 O administrador não é onisciente

Um administrador **não** lê o conteúdo de um trabalho da equipe em que não
participa. Ele pode:

- ver que existe (título, coordenador, contagem de estudos, progresso);
- ingressar, se o acesso for `aberto`;
- pedir participação, se for `listado`;
- nada, se for `restrito`.

E toda entrada dele — como a de qualquer um — vira publicação de sistema no
mural (PE4). A alternativa "administrador vê tudo" é o desenho comum em
ferramenta corporativa e o errado aqui: uma revisão cega por pares (§43.7) com
um administrador capaz de ler os julgamentos dos dois revisores **não é cega**.

**A cegueira do doc 43 §43.7 não admite exceção por papel de equipe.** É o
ponto em que este plano poderia destruir uma garantia metodológica já entregue,
e por isso ganha teste próprio na Fase 3.

---

## 50.8 O mural

### 50.8.1 O que é, e o que não é

É um **quadro de recados com histórico**: publicações em ordem cronológica
inversa, as fixadas no topo, comentários de um nível, e eventos do sistema
misturados aos recados humanos.

Não é um chat. Não há indicação de digitação, entrega individual, mensagem
direta nem sala por assunto. Um laboratório que precisa de chat já tem um; o
que ele não tem é um lugar onde "combinamos incluir estudos qualitativos" fique
escrito ao lado da revisão em que isso foi combinado.

### 50.8.2 Os três tipos

| Tipo | Quem cria | Comportamento |
|---|---|---|
| `recado` | Membro | Publicação comum, comentável |
| `aviso` | Administrador | Aparece destacado; com `exige_ciencia`, mostra quem já deu ciência e quem falta |
| `sistema` | O servidor | Não editável, não comentável, gerada por evento |

### 50.8.3 Publicações de sistema

São o que faz o mural ser também o registro vivo da equipe — e são o
cumprimento de PE4.

| Evento | Texto | Condição |
|---|---|---|
| `equipe.membro_entrou` | "B. Costa entrou na equipe" | sempre |
| `equipe.membro_saiu` | "B. Costa saiu da equipe" | sempre |
| `trabalho.criado` | "A. Silva criou o trabalho *Ansiedade em universitários*" | acesso ≠ `restrito` |
| `trabalho.movido` | "*Título* passou a pertencer à equipe" | idem |
| `trabalho.ingresso` | "B. Costa entrou no trabalho *Título* como revisor" | idem |
| `trabalho.acesso_alterado` | "*Título* agora é aberto à equipe" | idem |
| `trabalho.marco` | "*Título*: triagem concluída — 412 incluídos" | idem |

**A condição não é enfeite.** Publicação de sistema sobre trabalho `restrito`
não é gerada — nem para administrador. Vazaria pelo título o que a política
fechou.

**Marcos, não atividade.** Não existe publicação por estudo triado: seriam
milhares. Os marcos da v1 são três — coleta concluída, triagem concluída,
extração concluída.

### 50.8.4 Edição, remoção e moderação

- O autor edita a própria publicação; fica `editada_em` visível ("editado").
- O autor remove a própria; administrador remove qualquer uma. A remoção é
  **suave**: `removida_em` preenchido, corpo substituído na resposta por
  "publicação removida", linha preservada para o registro de moderação.
- **Ninguém edita o texto de outro.** Nunca. Não existe rota que permita.
- Publicação de sistema não é editável nem removível por pessoa alguma; sai
  junto com a equipe.

### 50.8.5 Não lidos e ao vivo

`GET /equipes/{id}/mural` devolve `nao_lidas: int`, calculado contra
`mural_leituras.visto_ate`. Abrir a aba manda `POST .../mural/lido`.

O canal ao vivo reaproveita `ConnectionManager` (`harvesting_service.py:42`)
**sem refatoração**: a chave do dicionário é uma string qualquer, e a rota de
equipe usa `f"equipe:{equipe_id}"`. Projeto continua usando o UUID cru — as
duas famílias de chave não colidem, e nenhum dos pontos que já chamam
`ws_manager.broadcast` muda.

Eventos do canal: `mural.publicacao`, `mural.comentario`, `mural.removida`,
`presenca`. A autenticação é a que já existe — bilhete de canal
(`backend/app/security/bilhete_de_canal.py`) —, com a verificação de
participação no projeto trocada por participação **na equipe**.

### 50.8.6 Limites e abuso

Um campo de texto livre num serviço com contas é superfície nova. As guardas da
v1:

- 4000 caracteres na publicação, 2000 no comentário — rejeitados no servidor;
- 50 publicações por usuário por dia, por equipe (o limitador de taxa já existe
  em `backend/app/security/middleware.py`);
- 5 publicações fixadas por equipe;
- texto puro, marcação rejeitada (§50.6.6);
- `@menção` resolvida **só** contra a composição da equipe: mencionar quem não
  é membro não notifica ninguém nem confirma que a conta existe;
- sem anexo, sem imagem e **sem pré-visualização de link buscada pelo
  servidor** — este último seria um SSRF de graça.

---

## 50.9 Ciclo de vida

### 50.9.1 Sair da equipe

`DELETE /equipes/{id}/membros/{user_id}` — administrador remove, ou o próprio
sai. Efeito: `is_active=False`, `left_at` preenchido.

**As participações em trabalhos não são desligadas em cascata.** Sair do
laboratório não é abandonar a revisão da qual se é coautor. O que muda é o
caminho de entrada: sem a equipe, o acesso passa a depender só da participação
que já existe. A interface avisa disso na confirmação, com a lista dos trabalhos
afetados.

Se a intenção for tirar a pessoa de tudo, é uma segunda ação explícita
("remover também dos 3 trabalhos"), que executa a remoção de §43.13.1 em cada um
— com a consequência já especificada lá: um estudo pode voltar a `parcial`.

### 50.9.2 Transferir a titularidade da equipe

`POST /equipes/{id}/transferir` — só o titular, só para um administrador ativo.
Mesma razão de §43.13.2: o titular é o controlador dos dados, e sem
transferência sair da plataforma exigiria destruir o espaço.

### 50.9.3 Arquivar e excluir a equipe

- **Arquivar** (`is_archived`): perfil e mural em leitura; trabalhos intactos.
- **Excluir**: só o titular, com confirmação escrita do nome da equipe. Apaga
  `equipes`, `equipe_membros`, `equipe_convites` e o mural inteiro (cascata);
  põe `projects.equipe_id = NULL` e **não toca em revisão alguma**. A tela diz,
  antes, quantos trabalhos voltarão a ser pessoais e de quem.

### 50.9.4 Eliminar a conta

`executar_eliminacao_completa_usuario` (`backend/app/api/v1/me.py:90`) ganha
passos novos, e é aqui que PE5 vira código:

| Situação | O que acontece |
|---|---|
| Titular de equipe com outros membros ativos | Titularidade transferida ao administrador ativo mais antigo; se não houver, ao membro mais antigo, promovido |
| Titular de equipe sem outros membros ativos | Equipe excluída; trabalhos voltam a pessoais (`equipe_id = NULL`) |
| Membro de equipe | Participação desativada |
| Autor de publicações e comentários | **Corpo apagado**, `autor_user_id = NULL`, `autor_rotulo = 'conta removida'` — some da tela como "publicação removida" |
| Autor de julgamentos de triagem | **Pseudonimizado, não apagado** — exatamente como §43.13.3 |

A assimetria das duas últimas linhas é deliberada, e precisa estar escrita em
`planejamento/PRIVACIDADE.md` **antes** do primeiro convite de equipe em
produção: o julgamento fica porque apagá-lo falsearia um resultado científico
(art. 16, II); o recado sai porque é fala pessoal e nenhuma base legal sustenta
mantê-la.

---

## 50.10 LGPD e ROPA

Operações a acrescentar em `ropa_service.OPERACOES`
(`backend/app/services/ropa_service.py:24`):

| `operation` | `legal_basis` | `data_categories` |
|---|---|---|
| `equipe_created` | `art7_V_execucao_de_contrato` | `identificacao` |
| `equipe_invitation_issued` | `art7_V_execucao_de_contrato` | `identificacao`, `contato` |
| `equipe_membership_created` | `art7_V_execucao_de_contrato` | `identificacao` |
| `equipe_membership_revoked` | `art7_V_execucao_de_contrato` | `identificacao` |
| `equipe_ownership_transferred` | `art7_V_execucao_de_contrato` | `identificacao` |
| `trabalho_ingresso` | `art7_V_execucao_de_contrato` | `identificacao`, `conteudo_de_pesquisa` |
| `mural_post_created` | `art7_IX_legitimo_interesse` | `identificacao`, `conteudo_de_comunicacao` |
| `mural_post_erased` | `art7_VI_exercicio_de_direitos` | `conteudo_de_comunicacao` |

**Categoria nova em `CATEGORIAS`:** `conteudo_de_comunicacao` — "texto escrito
por um titular e destinado a outros titulares". Não existe hoje e não cabe em
`conteudo_de_pesquisa`: os dois têm regimes de eliminação opostos (PE5).

**Dois parágrafos novos em `PRIVACIDADE.md`**, redigidos antes da Fase 5:
o que a equipe compartilha (composição, trabalhos não restritos, mural), e o que
acontece com o que a pessoa escreveu quando ela elimina a conta.

**Itens do doc 38 a reaferir** ao fim da Fase 7: compartilhamento com
terceiros, eliminação, minimização e o inventário de dados pessoais — o mural é
a primeira vez que o Revsist guarda texto livre escrito por um titular a
respeito de outros.

---

## 50.11 Interface

### 50.11.1 Telas

| Rota | Tela | Conteúdo |
|---|---|---|
| `/equipes` | `EquipesPage` | Minhas equipes (emblema, nº de membros, nº de trabalhos, não lidos), criar, e campo "entrar com código" |
| `/equipes/:identificador` | `PerfilDaEquipePage` | Cabeçalho + quatro abas |
| — aba **Mural** *(inicial)* | `MuralDaEquipe` | Compositor no topo, fixadas, feed, comentários, ciência de aviso |
| — aba **Trabalhos** | `TrabalhosDaEquipe` | Cartões com acesso, participantes, meu papel, botão Entrar / Pedir acesso / Abrir |
| — aba **Membros** | `MembrosDaEquipe` | Papel, título, convites pendentes com código copiável |
| — aba **Ajustes** | `AjustesDaEquipe` | Perfil, visibilidade, transferência, arquivar, excluir |

**A aba Mural é a inicial** — é literalmente o pedido R-4, e é também a escolha
certa: o que muda todo dia é a conversa, não a lista de trabalhos.

**Alterações em telas existentes:**

- `DashboardPage` — bloco "Suas equipes" com não lidos, acima dos projetos
  recentes;
- `ProjectsPage` — selo da equipe no cartão e filtro "pessoais / da equipe X";
- `TeamPage.tsx` — passa a chamar-se **Participantes do trabalho** no título e
  no ribbon (Q-07); ganha, quando `equipe_id` não é nulo, o bloco "Adicionar do
  quadro da equipe" e o controle de `acesso_da_equipe`;
- `TopRibbonBar.tsx:435` — grupo `Equipe` renomeado para `Participantes`, e
  entrada `Espaço de equipe` acrescentada na aba **Arquivo**.

### 50.11.2 Móvel e tokens

Tudo nasce dentro de `frontend/src/styles/mobile.css` e do doc 24: o mural é
coluna única em qualquer largura (feed nunca vira grade), o compositor abre como
folha inferior no móvel, e as quatro abas do perfil usam o padrão de navegação
segmentada que Triagem e Extração já usam.

`node frontend/scripts/lint-design-tokens.mjs --strict` continua verde: nenhuma
cor literal nova, inclusive na paleta de emblemas — que é lista de **nomes de
token**, não de hexadecimais (§50.6.1).

---

## 50.12 Limites

Acrescentados a `backend/app/config.py`, junto dos de projeto (`config.py:76-81`):

```python
max_equipes_por_usuario: int = 5           # equipes das quais é titular
max_participacoes_em_equipe: int = 20      # equipes das quais participa
max_membros_por_equipe: int = 50
max_trabalhos_por_equipe: int = 60
max_convites_ativos_por_equipe: int = 30
equipe_convite_ttl_dias: int = 14
max_publicacoes_por_dia: int = 50
max_publicacoes_fixadas: int = 5
tamanho_maximo_publicacao: int = 4000
tamanho_maximo_comentario: int = 2000
```

`max_projects_per_user` **não** muda de semântica: continua contando só os
projetos de que a conta é dona (`projects.py:104`). Um trabalho criado dentro da
equipe consome a cota de quem o criou.

---

## 50.13 Fases de execução

> **A ordem 0 → 1 → 2 → 3 não é negociável.** Vocabulário antes de tabela, ou
> nasce a segunda "equipe" no código; entidade antes de convite, ou se convida
> para um lugar que não existe; convite antes de trabalho, ou não há segundo
> membro para exercer papel algum.
> **As Fases 5 e 6 podem trocar de ordem com a 4.** O mural não depende de
> pedido de participação.
> **Uma fase por branch, um PR por fase.** A CI é o portão.
> **Toda alteração de esquema é revisão Alembic**, conferida linha a linha.
> **Cada fase roda a suíte nos dois bancos** (SQLite e PostgreSQL).

### Antes da primeira linha de código

- [ ] **P1** Decidir **D-06** — um trabalho pode pertencer a mais de uma equipe? Recomendação: não. **Bloqueia a Fase 3.**
- [ ] **P2** Decidir **D-07** — padrão de `acesso_da_equipe`. Recomendação: `listado`. **Bloqueia a Fase 3.**
- [ ] **P3** Decidir **D-08** — administrador lê tudo? Recomendação: não. **Bloqueia a Fase 3.**
- [ ] **P4** Decidir **D-09** — regime de eliminação do mural. Recomendação: apagar o corpo. **Bloqueia a Fase 7.**
- [ ] **P5** Decidir **D-10** — chave de IA da equipe. Recomendação: manter P4 do doc 43 (quem age paga). **Bloqueia a Fase 3.**
- [ ] **P6** Cópia de `rsac.db` de desenvolvimento e de produção — as Fases 1, 3 e 5 alteram o esquema com dado real.
- [ ] **P7** Redigir os dois parágrafos de `PRIVACIDADE.md` (§50.10). **Bloqueia o primeiro convite de equipe em produção**, não a Fase 2.

---

### Fase 0 — A fronteira da palavra

> **Objetivo:** "Equipe" passa a significar uma coisa só no produto, antes de
> existir a tabela que a disputaria. Fecha **Q-07**.
> **Esforço:** 0,5–1 dia · **Risco:** nenhum — não há alteração de esquema nem
> de comportamento.

- [ ] **0.1** `TeamPage.tsx`: título, textos e `<h1>` passam de "Equipe" para "Participantes do trabalho" — arquivo e rota **não** mudam
- [ ] **0.2** `TopRibbonBar.tsx:435`: grupo `Equipe` → `Participantes`
- [ ] **0.3** Varredura de rótulos: `grep -rn "Equipe" frontend/src --include=*.tsx` revisado item a item
- [ ] **0.4** Nota de duas linhas no doc 43 §43.18 apontando que D-02 foi reaberta por este documento

**Aceite:** nenhuma tela diz "Equipe" referindo-se a participação em projeto; `npm run build` verde; nenhuma alteração em `backend/`.

---

### Fase 1 — A equipe existe

> **Objetivo:** criar, ver e editar um perfil de equipe com um membro — o
> próprio titular. Fecha **Q-01**.
> **Esforço:** 3–4 dias · **Risco:** médio (tabela nova com barreira de
> isolamento própria).

- [ ] **1.1** `EquipeModel` e `EquipeMembroModel` (§50.6.1, §50.6.2) + revisão Alembic com `downgrade` executado sobre cópia com dados
- [ ] **1.2** `schemas/equipe.py` — `EquipeCreate`, `EquipeUpdate`, `EquipeResponse`, `EquipeMembroResponse`
- [ ] **1.3** `security/dependencies.py`: `equipe_do_usuario` (junção com `equipe_membros`, **404 e não 403**) e `exige_papel_de_equipe(*papeis)` — gêmeas de `:218` e `:303`, **sem tocar nas originais**
- [ ] **1.4** `api/v1/equipes.py`: `POST /equipes`, `GET /equipes`, `GET /equipes/{id}`, `PATCH /equipes/{id}`, `POST /equipes/{id}/arquivar`, `DELETE /equipes/{id}`
- [ ] **1.5** Criação em transação única: equipe + linha de `administrador` para o titular
- [ ] **1.6** Validação de `identificador` (`[a-z0-9-]{3,32}`, único, imutável) com 409 legível
- [ ] **1.7** Tetos `max_equipes_por_usuario` e `max_participacoes_em_equipe` em `config.py`
- [ ] **1.8** ROPA: `equipe_created` (§50.10)
- [ ] **1.9** Front: `EquipesPage`, `PerfilDaEquipePage` com o cabeçalho e as abas vazias, rotas em `App.tsx`
- [ ] **1.10** `tests/test_api/test_equipes.py` — CRUD, identificador duplicado, teto, e o **teste de isolamento**: quem não é membro recebe 404 em toda rota de equipe

**Aceite:**
- [ ] `pytest -q` verde nos dois bancos
- [ ] `alembic upgrade head` e `downgrade -1` sobre cópia de produção
- [ ] `grep -rn "equipe" backend/app/security/dependencies.py` mostra **só** as duas funções novas — nenhuma linha dentro de `projeto_do_usuario` ou `verificar_projeto_do_usuario` (PE1)
- [ ] Um usuário sem equipe alguma usa o Revsist exatamente como antes (PE6)

**Se der errado:** `git revert` do PR e `alembic downgrade -1`. Nada preexistente é tocado.

---

### Fase 2 — Composição da equipe

> **Objetivo:** um segundo pesquisador entra na equipe. Fecha **Q-02**.
> **Esforço:** 3–4 dias · **Risco:** médio.

- [ ] **2.1** `EquipeConviteModel` (§50.6.3) + revisão Alembic
- [ ] **2.2** `GET/POST /equipes/{id}/convites`, `DELETE /equipes/{id}/convites/{id}`
- [ ] **2.3** `POST /equipes/convites/{codigo}/aceitar` — **fora** do prefixo de equipe (quem aceita ainda não é membro); valida código, expiração, revogação, uso e teto
- [ ] **2.4** Despachante de código único na `LoginPage.tsx`: `RSAC-`, `RSAC-EQ-`, `RSAC-ESP-` — com teste que prova que os três caem no fluxo certo (§50.6.3)
- [ ] **2.5** `GET/DELETE /equipes/{id}/membros`, `PATCH /equipes/{id}/membros/{user_id}` (papel e título), com a matriz de §50.7.3
- [ ] **2.6** `POST /equipes/{id}/transferir` (§50.9.2)
- [ ] **2.7** ROPA: os quatro eventos de convite e participação
- [ ] **2.8** Front: aba **Membros** completa — papéis, títulos, convites com código copiável, sair da equipe
- [ ] **2.9** `tests/test_api/test_equipe_convites.py` — aceite, expirado, revogado, já usado, teto estourado, convite de equipe alheia

**Aceite:**
- [ ] A convida B; B aceita; B vê o perfil e **não** vê trabalho algum (a Fase 3 ainda não existe)
- [ ] B removido volta a receber 404 em toda rota da equipe
- [ ] Membro não convida, não remove, não edita perfil; convidado não publica
- [ ] Administrador não rebaixa outro administrador; titular sim

**Se der errado:** reverter o PR e apagar a tabela. Ponto de atenção: 2.4 — um despacho errado manda o código de equipe para o fluxo de conta.

---

### Fase 3 — Trabalhos na equipe

> **Objetivo:** R-2 e R-3 inteiros. Fecha **Q-03** e **Q-04**.
> **Esforço:** 4–5 dias · **Risco: alto** — é a fase que toca a fronteira entre
> equipe e acervo. PR próprio, sem nada junto.

- [ ] **3.1** Colunas `equipe_id` e `acesso_da_equipe` em `projects` (§50.6.4) + Alembic com `server_default` `NULL` e `'listado'`, e `ON DELETE SET NULL` conferido à mão
- [ ] **3.2** `GET /equipes/{id}/trabalhos` — devolve **metadados**: título, área, coordenador, contagens, meu vínculo. Nunca protocolo, nunca estudo
- [ ] **3.3** `POST /projects` aceita `equipe_id` (só de equipe de que o criador participa) e `acesso_da_equipe`
- [ ] **3.4** `POST /projects/{id}/mover-para-equipe` e `.../remover-da-equipe` — só o dono do trabalho; teto `max_trabalhos_por_equipe`
- [ ] **3.5** `PATCH /projects/{id}` aceita `acesso_da_equipe` — **só coordenador do trabalho** (§50.7.3, nota ³)
- [ ] **3.6** `POST /projects/{id}/ingressar` — o ingresso materializado (PE2): valida participação ativa na equipe e `acesso_da_equipe == 'aberto'`, grava `project_members` com `revisor`, `audit_logs` e publicação de sistema; idempotente
- [ ] **3.7** `POST /projects/{id}/members` — coordenador adiciona alguém **do quadro da equipe**, sem convite (é o atalho que Q-02 pedia)
- [ ] **3.8** `ProjectResponse` ganha `equipe_id`, `equipe_nome`, `acesso_da_equipe`; `Project` do front idem (`frontend/src/types/api.ts`)
- [ ] **3.9** Front: aba **Trabalhos** do perfil, com Entrar / Pedir acesso / Abrir por política; selo de equipe em `ProjectsPage`
- [ ] **3.10** `tests/test_api/test_trabalhos_da_equipe.py` — as três políticas × (participante, membro da equipe, administrador, estranho) = 12 células
- [ ] **3.11** **Teste da cegueira sob equipe:** projeto `cega_por_pares` com política `aberto`; um administrador que ingressa recebe a mesma resposta cega que qualquer revisor — §43.7 intacto
- [ ] **3.12** Estender `test_tenancy_isolation.py` com o **quarto personagem**: colega de equipe que não participa do trabalho → 404 em toda rota de conteúdo

**Aceite:**
- [ ] `grep -rn "equipe" backend/app/security/dependencies.py` continua mostrando só as duas funções da Fase 1 (PE1)
- [ ] Membro da equipe sem participação recebe **404** em `/projects/{id}/papers`, mesmo com política `aberto` — antes de ingressar
- [ ] Depois de `POST .../ingressar`, existe linha em `project_members` e o acesso funciona
- [ ] Trabalho `restrito` não aparece em `GET /equipes/{id}/trabalhos` nem para o titular
- [ ] **Verificação por mutação:** remover a checagem de `acesso_da_equipe` da rota de ingresso faz o teste falhar nomeando a rota
- [ ] Excluir a equipe (Fase 1) deixa os trabalhos vivos com `equipe_id = NULL`

**Se der errado:** `git revert` e `alembic downgrade -1`. O risco real não é perda de dado — é **abrir acesso demais**, e por isso o critério de mutação é obrigatório aqui, como foi na Fase 0 do doc 44.

---

### Fase 4 — Pedido de participação

> **Objetivo:** o trabalho `listado` ganha porta de entrada com aprovação.
> **Esforço:** 2–3 dias · **Risco:** baixo.

- [ ] **4.1** `PedidoDeParticipacaoModel` (§50.6.5) + Alembic
- [ ] **4.2** `POST /projects/{id}/pedidos` (membro da equipe), `GET /projects/{id}/pedidos` (coordenador), `POST /projects/{id}/pedidos/{id}/aceitar|recusar`, `DELETE` (cancelar o próprio)
- [ ] **4.3** Aceite grava participação na mesma transação, com papel escolhido pelo coordenador
- [ ] **4.4** Trabalho `restrito` devolve **404** na criação de pedido; `aberto` devolve 409 dizendo "entre direto"
- [ ] **4.5** Front: botão "Pedir acesso" com mensagem, e bandeja de pedidos em `TeamPage.tsx`
- [ ] **4.6** `tests/test_api/test_pedidos_de_participacao.py` — inclusive dois pedidos pendentes do mesmo usuário (deve falhar)

**Aceite:** pedido aceito cria participação e publicação de sistema; pedido recusado não deixa acesso algum; estranho à equipe recebe 404.

---

### Fase 5 — O mural

> **Objetivo:** R-4. Fecha **Q-05**.
> **Esforço:** 4–5 dias · **Risco:** médio — é a primeira superfície de texto
> livre do produto.

- [ ] **5.1** `MuralPublicacaoModel`, `MuralComentarioModel`, `MuralLeituraModel`, `MuralCienciaModel` (§50.6.6–50.6.8) + Alembic
- [ ] **5.2** `GET /equipes/{id}/mural` (paginado por cursor, fixadas primeiro, `nao_lidas`), `POST`, `PATCH`, `DELETE`
- [ ] **5.3** `POST /equipes/{id}/mural/{pid}/comentarios`, `PATCH`, `DELETE`
- [ ] **5.4** `POST .../fixar` e `.../desafixar` (administrador, teto de 5)
- [ ] **5.5** `POST .../ciencia` e a contagem de quem falta, em `aviso` com `exige_ciencia`
- [ ] **5.6** `POST /equipes/{id}/mural/lido` — grava `visto_ate`
- [ ] **5.7** Sanitização no servidor (§50.6.6) e limites de tamanho e de taxa (§50.8.6)
- [ ] **5.8** Filtro de entrega: publicação ancorada em trabalho `restrito` sai da resposta para quem não participa
- [ ] **5.9** ROPA: `mural_post_created`; categoria `conteudo_de_comunicacao` acrescentada a `CATEGORIAS`
- [ ] **5.10** Front: `MuralDaEquipe` como aba inicial — compositor, feed, fixadas, comentários, ciência, bolinha de não lidos
- [ ] **5.11** `tests/test_api/test_mural.py` — permissões por papel, XSS armazenado (`<script>` volta escapado ou é rejeitado), teto diário, fixadas, não lidos, filtro de trabalho restrito

**Aceite:**
- [ ] Convidado comenta e não publica; membro publica; só administrador fixa e remove alheia
- [ ] Carga com `<script>` não volta executável em resposta alguma
- [ ] Publicação ancorada em trabalho `restrito` não aparece para não participante — **nem para o titular da equipe**
- [ ] 51ª publicação no mesmo dia recebe 429
- [ ] `lint-design-tokens.mjs --strict` verde

**Se der errado:** a fase é aditiva e isolada; reverter o PR remove o mural sem tocar em equipe nem em trabalho.

---

### Fase 6 — Mural ao vivo e eventos do sistema

> **Objetivo:** o mural se atualiza sozinho e passa a registrar o que a equipe
> faz. Fecha **Q-06** e entrega PE4.
> **Esforço:** 2–3 dias · **Risco:** baixo.

- [ ] **6.1** `WS /equipes/{id}/ws` com bilhete de canal e chave `f"equipe:{id}"` — **sem refatorar** `ConnectionManager` (§50.8.5)
- [ ] **6.2** Emissão de `mural.publicacao`, `mural.comentario`, `mural.removida`, `presenca`
- [ ] **6.3** `servico de mural`: função única que grava publicação de sistema — **um só ponto de chamada por evento**, com a guarda de `restrito` dentro dela
- [ ] **6.4** Ligar os sete eventos de §50.8.3
- [ ] **6.5** Marcos: coleta, triagem e extração concluídas — e nada por estudo
- [ ] **6.6** Front: `useEquipeChannel`, espelhando `useProjectChannel.ts`
- [ ] **6.7** `tests/test_api/test_mural_eventos.py` — evento de trabalho restrito **não** gera publicação; ingresso gera; canal não entrega a quem saiu da equipe

**Aceite:** dois navegadores, uma equipe: publicação aparece no outro sem recarregar; nenhum evento de trabalho `restrito` no mural; `ws_manager` continua servindo projetos sem alteração de assinatura.

---

### Fase 7 — Ciclo de vida, LGPD e fechamento

> **Objetivo:** sair, transferir, excluir e eliminar conta sem deixar órfão nem
> vazamento. Entrega PE5.
> **Esforço:** 2–3 dias · **Risco:** alto — mexe em eliminação de conta.

- [ ] **7.1** `executar_eliminacao_completa_usuario` (`me.py:90`) ganha os cinco casos de §50.9.4, em transação única
- [ ] **7.2** Exclusão de equipe com `equipe_id = NULL` nos trabalhos, verificada por teste com 3 trabalhos de 2 donos
- [ ] **7.3** Saída da equipe **não** desliga participações; a segunda ação explícita ("remover de N trabalhos") desliga
- [ ] **7.4** Exportação de portabilidade (`me.py:305`) inclui equipes, papéis e publicações do titular
- [ ] **7.5** `PRIVACIDADE.md` com os dois parágrafos de §50.10
- [ ] **7.6** Doc 38 reaferido e datado nos itens de compartilhamento, eliminação, minimização e inventário
- [ ] **7.7** `tests/test_lgpd/test_eliminacao_com_equipe.py` — titular com e sem membros, autor de mural, autor de julgamento (que **permanece** pseudonimizado)
- [ ] **7.8** Atualizar `planejamento/00_INDICE.md` e marcar as caixas deste documento

**Aceite:**
- [ ] Eliminar conta de titular com 2 membros transfere a equipe e não apaga trabalho algum
- [ ] Publicações do eliminado somem; julgamentos dele continuam contando para o κ (§43.13.3)
- [ ] Exportação de portabilidade abre e contém as equipes
- [ ] Suíte completa verde nos dois bancos

---

## 50.14 Decisões em aberto

Continuam a numeração do doc 42 (D-01 a D-05). Cada uma traz recomendação e o
que muda se for decidida ao contrário.

### D-06 · Um trabalho pode pertencer a mais de uma equipe?
**Consome:** Fase 3 · **Recomendação: não — no máximo uma.**
Duas equipes num trabalho exigiriam tabela de junção, política de acesso por
equipe e uma regra de precedência quando as duas discordarem. O caso real
(revisão conjunta entre dois laboratórios) resolve-se convidando as pessoas da
outra equipe para o trabalho, que é o que já existe. **Ao contrário:** `equipe_id`
vira tabela `equipe_trabalhos`, e §50.7.1 ganha um quantificador.

### D-07 · Qual o padrão de `acesso_da_equipe`?
**Consome:** Fase 3 · **Recomendação: `listado`.**
`aberto` por padrão faria toda revisão nova ficar acessível a até 50 pessoas sem
que ninguém decidisse isso — e uma revisão cega por pares com ingresso livre é
um problema metodológico, não só de privacidade. `restrito` por padrão anularia
o pedido R-2 no caso comum. `listado` mostra que existe e exige um ato para
entrar.

### D-08 · O administrador da equipe lê qualquer trabalho?
**Consome:** Fase 3 · **Recomendação: não (§50.7.5).**
É a decisão mais consequente do documento. "Administrador vê tudo" é o padrão
das ferramentas corporativas e quebra a cegueira do doc 43 §43.7. **Ao
contrário:** seria preciso excetuar explicitamente projetos `cega_por_pares`, e
declarar isso na exportação — o que enfraquece a declaração de método.

### D-09 · O que acontece com o mural quando a conta é eliminada?
**Consome:** Fase 7 · **Recomendação: apagar o corpo, manter a linha como lápide.**
Manter o texto de alguém que pediu eliminação exigiria base legal que não temos.
Apagar a linha inteira quebraria fios de comentário e deixaria respostas sem
pergunta. **Ao contrário** (manter o texto): exige consentimento específico no
aceite dos Termos, e vira item novo no doc 38.

### D-10 · De quem é a chave de IA num trabalho de equipe?
**Consome:** Fase 3 · **Recomendação: manter P4 do doc 43 — quem age paga.**
Uma "chave da equipe" seria um segredo cifrado copiado para mais um lugar (o que
o doc 42 D-03 já descartou) e criaria gasto sem teto atribuível. **Ao
contrário:** exige tela de consentimento do titular, teto de gasto por equipe e
atribuição de custo por membro — uma fase inteira a mais.

### D-11 · Existe diretório público de equipes?
**Consome:** Fase 1 · **Recomendação: não na v1 (§50.6.1).**
Um diretório publicaria vínculo institucional de pesquisador. A visibilidade
`por_identificador` cobre o caso real — divulgar o identificador num e-mail ou
num rodapé de artigo — sem tornar a base enumerável.

---

## 50.15 O que fica de fora da v1

Registrado para não ser reaberto a cada revisão de escopo:

- **Imagem de perfil e de capa da equipe.** Armazenamento, cota, moderação de
  conteúdo e caminho de remoção — quatro problemas por ganho estético.
- **Mensagem direta entre membros.** É chat, e chat pede notificação, entrega e
  bloqueio de usuário. O mural resolve comunicação de equipe.
- **Notificação por e-mail** (de convite, menção ou aviso). O envio de e-mail
  ainda não existe no produto — §43.10.1 já registrou isso.
- **Comentário por estudo dentro do trabalho.** Continua fora, como no doc 43
  §43.18. É tabela independente de tudo o que está aqui.
- **Hierarquia de equipes** (departamento → laboratório → grupo). Nenhuma
  demanda; a composição plana cobre o caso descrito.
- **Papéis personalizados** com permissões marcáveis uma a uma. Três papéis
  cobrem o que foi pedido; permissão granular exige tela de administração e um
  modelo de autorização que não é mais uma matriz legível em documento.
- **Trabalho pertencente a duas equipes** (D-06).
- **Chave de IA e cota compartilhadas pela equipe** (D-10).
- **Busca pública de equipes** (D-11).

---

## 50.16 Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Alguém "simplifica" a Fase 3 pondo o `OR` na junção de isolamento | média | **crítico** — vazamento entre assinantes | PE1 escrito, grep no critério de aceite, teste de mutação obrigatório |
| Administrador de equipe furando a cegueira do doc 43 | média | alto — invalida revisão publicada | Tarefa 3.11 é teste dedicado, não inspeção visual |
| Mural vira superfície de XSS armazenado | média | alto | Texto puro validado no servidor; teste com carga real |
| Publicação de sistema vazando título de trabalho restrito | alta se esquecido | médio | A guarda mora **dentro** do serviço de mural (6.3), num ponto só |
| Eliminação de conta quebrando pela metade em equipe com trabalhos | baixa | alto | 7.1 em transação única e teste com os cinco casos |
| Duas palavras "equipe" no código | alta se a Fase 0 for pulada | médio | Fase 0 antes de tudo, e ela não custa um dia |
| Escopo crescendo para chat | alta | médio | §50.15 é a resposta pronta |
