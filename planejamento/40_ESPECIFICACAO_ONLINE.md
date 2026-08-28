# 40 — Especificação do RSAC Online

> **Documento normativo.** Descreve o desenho alvo do RSAC V2 como serviço:
> persistência, titularidade, identidade com Google, infraestrutura, landing
> page e amarração com a LGPD. O que está aqui é decisão tomada; o *como fazer*
> e em que ordem está no [`41_PLANO_EXECUCAO_ONLINE.md`](./41_PLANO_EXECUCAO_ONLINE.md).
> **Motivação medida:** [`39_DIAGNOSTICO_ONLINE.md`](./39_DIAGNOSTICO_ONLINE.md).
> **Restrições de proteção de dados:** [`38_CHECKLIST_LGPD.md`](./38_CHECKLIST_LGPD.md).

---

## 40.1 Arquitetura alvo

```
                          Internet
                             │
                    ┌────────▼────────┐
                    │      Caddy      │  TLS automático (Let's Encrypt)
                    │  reverse proxy  │  HTTP/2 · compressão · cabeçalhos
                    └───┬────────┬────┘
             /          │        │        /api/*  ·  /app/*
      (estático)        │        │
   ┌─────────────┐      │        │   ┌──────────────────────┐
   │  landing/   │◄─────┘        └──►│  api (uvicorn, 1 w.) │
   │  dist/      │                   │  FastAPI + SQLAlchemy│
   └─────────────┘                   └───┬──────────────┬───┘
                                         │              │
                              ┌──────────▼───┐   ┌──────▼───────┐
                              │ PostgreSQL 16│   │ volume /pdfs │
                              └──────┬───────┘   └──────┬───────┘
                                     │                  │
                              ┌──────▼──────────────────▼───────┐
                              │ backup: pg_dump + tar, cifrado, │
                              │ enviado para armazenamento       │
                              │ externo (S3/B2), retenção 30 d   │
                              └──────────────────────────────────┘
```

**Princípios que a figura carrega:**

1. **O Python sai do caminho do arquivo estático.** Landing e SPA são servidas
   pelo Caddy. O *catch-all* de `main.py:288` continua existindo para o perfil
   `desktop`, onde é a solução certa, e fica inerte em produção.
2. **Um processo de aplicação.** Decorre de O-12 a O-15 e está justificado em
   §40.6, com o gatilho escrito para quando deixar de bastar.
3. **Estado só em dois lugares** — PostgreSQL e o volume de PDFs. É o que
   define o que o backup precisa cobrir, e nada além.
4. **Nenhum serviço exposto além do Caddy.** Postgres não publica porta; fala
   com a API pela rede interna do Compose.

### 40.1.1 Mapa de rotas do domínio

| Caminho | Serve | Cache |
|---|---|---|
| `/` | Landing estática | `public, max-age=3600` |
| `/privacidade`, `/termos` | Páginas estáticas | idem |
| `/app`, `/app/*` | SPA (React) | `index.html` sem cache; *assets* com *hash*, `immutable` |
| `/api/*` | Backend FastAPI | `no-store` (já aplicado em `middleware.py:53-57`) |
| `/api/v1/*/ws` | WebSocket | *upgrade* explícito no Caddy |

---

## 40.2 Persistência: PostgreSQL e migração versionada

### 40.2.1 Escolha

**PostgreSQL 16.** Não é preferência: o SQLite em WAL num único arquivo, com
coleta e triagem escrevendo em paralelo para vários assinantes, é contenção e
ponto único de corrupção (O-11). O RSAC já usa SQLAlchemy 2.0 com tipagem
declarativa, então a mudança concentra-se em três arquivos.

O perfil `desktop` **continua em SQLite**. O `effective_database_url` já
existe para isso (`config.py`) e é a única chave que decide.

### 40.2.2 `database.py` derivado do dialeto

O engine passa a ser construído a partir da URL, e não com argumentos de
SQLite fixos (O-08, O-09):

```python
url = settings.effective_database_url
is_sqlite = url.startswith("sqlite")

engine = create_engine(
    url,
    echo=settings.debug,
    pool_pre_ping=True,
    **({"connect_args": {"check_same_thread": False, "timeout": 30}}
       if is_sqlite else
       {"pool_size": 5, "max_overflow": 10, "pool_recycle": 1800}),
)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _):
        ...
```

**Regra:** nenhum `PRAGMA`, `check_same_thread` ou `timeout` fora do ramo
`is_sqlite`. O listener de `connect` só é registrado quando o dialeto é SQLite.

### 40.2.3 Migração versionada com Alembic

`create_tables()` e `_migrate_missing_columns()` são **aposentados**
(O-06, O-07). Em seu lugar:

- `backend/alembic/` com `env.py` lendo `settings.effective_database_url` e
  `target_metadata = Base.metadata`;
- migração inicial gerada a partir do esquema atual, para que bancos existentes
  possam ser "carimbados" com `alembic stamp head`;
- toda alteração de modelo passa a exigir revisão versionada, com `upgrade` e
  `downgrade` escritos;
- a API aplica migração **na partida** (`alembic upgrade head` no `lifespan`),
  porque com um processo único não há corrida — e isso elimina o passo manual
  que se esquece em produção.

**Regra de revisão:** nenhum PR que altere `models.py` entra sem a revisão
Alembic correspondente. A CI verifica com `alembic check` (falha se o modelo
divergir da última revisão).

### 40.2.4 Tipos e fuso

- Todas as colunas de data passam a `DateTime(timezone=True)` →
  `timestamptz` em PostgreSQL, `TEXT` em SQLite (comportamento atual
  preservado).
- `security/sessions.py:_naive_utc` deixa de ser necessário em PostgreSQL, mas
  **continua** para SQLite. A função vira o ponto único de normalização e é
  coberta por teste nos dois bancos (risco nomeado em §39.7).
- Identificadores permanecem `String(36)` com UUID v4 em texto. Trocar por
  `UUID` nativo é otimização sem retorno aqui e quebraria a compatibilidade com
  o desktop.

### 40.2.5 Ponte do desktop para o serviço

Quem já usa o RSAC de mesa precisa levar o trabalho. O caminho oficial é o que
já existe: `POST /api/v1/profile/export` gera o pacote, `POST /profile/import`
o restaura — com duas mudanças obrigatórias na Fase 1:

- a importação passa a gravar **sob a titularidade de quem chamou**, nunca
  sobre o banco inteiro (O-05);
- a exportação passa a sair **apenas** com o que pertence a quem chamou.

---

## 40.3 Titularidade e isolamento

### 40.3.1 Modelo

```python
class ProjectModel(Base):
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
```

`AISettingsModel` e `SourceCredentialModel` deixam de ser globais (O-02, O-03):

| Modelo | Antes | Depois |
|---|---|---|
| `AISettingsModel` | uma linha global | `user_id` FK **único** — uma configuração por usuário |
| `SourceCredentialModel` | `source_name` único global | único composto `(user_id, source_name)` |

A migração de bases existentes atribui tudo à conta mais antiga ativa — que é,
por construção do perfil desktop, a única que existe.

### 40.3.2 A dependência que isola

Repete-se o padrão que já provou valer com a autenticação: a verificação entra
**no router**, não em cada rota.

```python
def projeto_do_usuario(
    project_id: str,
    usuario: UserModel = Depends(require_session),
    db: Session = Depends(get_db),
) -> ProjectModel:
    projeto = (
        db.query(ProjectModel)
        .filter(ProjectModel.id == project_id,
                ProjectModel.owner_id == usuario.id)
        .first()
    )
    if projeto is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return projeto
```

**404, nunca 403.** Um 403 confirmaria que o projeto existe, e o identificador é
um UUID: negar a existência é a resposta que não vaza nada. É a mesma decisão
já tomada no confinamento de caminho da SPA (`main.py:296-301`).

Aplica-se como dependência de router nos nove roteadores que já carregam
`/projects/{project_id}` no prefixo:

```python
router = APIRouter(
    prefix="/projects/{project_id}/papers",
    dependencies=[Depends(projeto_do_usuario)],
    tags=["papers"],
)
```

Os quatro roteadores sem `project_id` no prefixo tratam-se caso a caso:

| Router | Regra |
|---|---|
| `projects` | `GET`/`POST` filtram e gravam por `owner_id`; `{project_id}` usa a dependência |
| `ai` | Passa a operar sobre a linha do usuário corrente |
| `settings/sources` | Idem |
| `profile` | Exporta e importa apenas o que é do usuário corrente |

### 40.3.3 Papéis, revistos

`require_owner` (`security/dependencies.py`) hoje protege as rotas de
credencial. Com contas individuais, **todo assinante gere as próprias chaves**,
então `owner` deixa de ser o critério: a proteção certa é a titularidade do
recurso, que a §40.3.2 já dá (O-04).

`owner` permanece, com outro sentido: **administrador da instalação**. Rotas de
gestão de contas (`POST /auth/users`, `DELETE /auth/users/{id}`) continuam
exigindo-o. Autocadastro **jamais** concede `owner` (§40.4.5).

### 40.3.4 Prova de isolamento

Suíte nova, `backend/tests/test_security/test_tenancy_isolation.py`, com uma
regra mecânica: **para toda rota que aceite `{project_id}` ou `{paper_id}`, um
segundo usuário recebe 404**. O teste enumera as rotas a partir de
`app.routes` — assim, uma rota nova sem isolamento **quebra a suíte sem que
ninguém precise lembrar de adicioná-la**.

---

## 40.4 Identidade: login com Google

### 40.4.1 Desenho

**Authorization Code Flow com PKCE, executado no servidor.** O navegador nunca
vê `client_secret` nem `id_token`; o que ele recebe ao final é o mesmo cookie de
sessão que o login por senha já emite.

```
 navegador            backend                       Google
    │                    │                             │
    │ GET /auth/google/start                           │
    ├───────────────────►│                             │
    │                    │ grava state+nonce+verifier  │
    │                    │ no banco (TTL 10 min)       │
    │ 302 →              │                             │
    ├──────────────────────────────────────────────────►
    │                            consentimento          │
    │ 302 /auth/google/callback?code&state              │
    ├───────────────────►│                             │
    │                    │ valida state (uso único)    │
    │                    │ troca code+verifier ────────►
    │                    │◄──────────── id_token       │
    │                    │ verifica assinatura (JWKS), │
    │                    │ aud, iss, exp, nonce        │
    │                    │ exige email_verified        │
    │                    │ vincula ou cria conta       │
    │                    │ create_session() ──┐        │
    │ 302 /app + cookie  │◄───────────────────┘        │
    │◄───────────────────│                             │
```

**Por que estado no banco, e não em cookie assinado.** É a mesma razão que levou
o projeto a escolher sessão com estado em vez de JWT (`security/sessions.py`):
o que está no servidor pode ser invalidado na hora. O `state` é de **uso único**
— apagado ao ser consumido —, o que fecha a repetição de callback. Um cookie
assinado seria reutilizável até expirar.

### 40.4.2 Modelo

```python
class OAuthStateModel(Base):
    __tablename__ = "oauth_states"
    state: Mapped[str]          # 32 bytes urlsafe, chave primária
    code_verifier: Mapped[str]  # PKCE
    nonce: Mapped[str]
    redirect_after: Mapped[str] # caminho interno validado, nunca URL absoluta
    created_at / expires_at     # TTL de 10 minutos
```

`UserModel` ganha (O-17, O-18):

| Coluna | Regra |
|---|---|
| `email` | único, indexado, `nullable=True` (contas antigas do desktop não têm) |
| `email_verified` | booleano; só `true` vindo do Google com `email_verified` |
| `google_sub` | único, indexado, `nullable=True` — o identificador **estável** do Google |
| `display_name` | nome exibido, opcional |
| `auth_provider` | `"password"` \| `"google"` \| `"both"` |
| `password_hash` | passa a `nullable=True` |

**Não se coleta a foto do perfil.** Não serve a nada no produto, e o art. 6º, III
não deixa margem: dado desnecessário não se trata. O escopo pedido é
`openid email profile` porque `profile` traz o nome; a foto vem junto e é
**descartada na leitura**, sem chegar ao banco.

### 40.4.3 Validação do `id_token` — a lista que não pode ter buraco

| Verificação | Falha significa |
|---|---|
| Assinatura confere com a JWKS do Google, com cache respeitando `Cache-Control` | Token forjado |
| `iss` ∈ {`accounts.google.com`, `https://accounts.google.com`} | Emissor errado |
| `aud` == `client_id` do RSAC | Token emitido para **outro** aplicativo — o ataque clássico de reúso de token |
| `exp` no futuro, `iat` no passado, com folga de relógio de 60 s | Token vencido |
| `nonce` == o gravado no `OAuthStateModel` | Repetição |
| `email_verified` é `true` | **Recusa o login** |

**A regra do `email_verified` é a que impede tomada de conta.** Sem ela,
alguém que crie no Google Workspace uma conta com o e-mail de um assinante
existente e a use para entrar herdaria o acervo dele. Um e-mail não verificado
não vincula, não cria conta e não recebe sessão — recebe uma mensagem clara.

**O vínculo é por `google_sub`, não por e-mail.** O `sub` é estável; o e-mail
pode ser reatribuído dentro de um domínio corporativo. O e-mail só é usado
**uma vez**, no primeiro vínculo com uma conta preexistente, e apenas quando
verificado.

Ordem de resolução no callback:

1. Existe usuário com este `google_sub`? → é ele.
2. Existe usuário com este `email`, e o `email_verified` do Google é `true`? →
   vincula: grava `google_sub`, marca `auth_provider = "both"`.
3. Caso contrário → cria conta nova com `role = "researcher"`.

### 40.4.4 Convivência com o que já existe

- **Senha continua existindo**, como acesso de emergência do `owner` — se o
  OAuth do Google cair ou a credencial de aplicativo for revogada, você ainda
  entra. É a razão de o login por senha não ser removido.
- **Login por senha recusa hash vazio.** `verify_password` já devolve `False`
  quando o hash é falso (`security/passwords.py`), mas a rota passa a barrar
  explicitamente contas com `password_hash IS NULL`, para que a mensagem seja
  "esta conta entra com Google" e não "senha inválida".
- **O perfil `desktop` não usa Google.** Continua com o token local
  (`security/local_token.py`), que já é a resposta certa: quem tem o arquivo já
  tem o sistema de arquivos do usuário. Nada muda no Electron.
- **Limite de taxa.** `_familia_da_rota` (`security/middleware.py:83`) passa a
  casar `/auth/google`, caindo na família `auth` (10 por 15 min) e não em
  `geral` (O-20).
- **Sessões existentes continuam válidas.** O login com Google emite sessão pelo
  mesmo `create_session`; nada no restante da API sabe qual foi a via.

### 40.4.5 Autocadastro

Entrar com Google **cria a conta** se ela não existir. Três travas:

1. `role` é sempre `researcher`. `owner` só nasce por
   `python -m app.cli create-user <nome> --role owner` (O-19).
2. Lista de admissão opcional por variável de ambiente
   (`RSAC_SIGNUP_ALLOWLIST`: domínios ou e-mails). Vazia = aberto. É o que
   permite operar a v1 **por convite** sem escrever código de convite.
3. O aceite dos Termos e do Aviso de Privacidade é registrado com data, versão
   do documento e origem — é a prova exigida pelo art. 8º, §2º quando houver
   consentimento, e boa prática mesmo quando a base for contrato.

### 40.4.6 Configuração no Google Cloud

| Item | Valor |
|---|---|
| Tipo de credencial | OAuth 2.0 Client ID → *Web application* |
| Origem JavaScript autorizada | `https://<domínio>` |
| URI de redirecionamento | `https://<domínio>/api/v1/auth/google/callback` |
| Escopos | `openid`, `email`, `profile` — **nada além** |
| Tela de consentimento | *External*, publicada; logo do RSAC; links de Termos e Privacidade obrigatórios |
| Segredos | `RSAC_GOOGLE_CLIENT_ID`, `RSAC_GOOGLE_CLIENT_SECRET` no arquivo de ambiente (0600), nunca no repositório |

Escopos `openid email profile` **não** exigem verificação de aplicativo pelo
Google (não são escopos sensíveis nem restritos) — a tela de consentimento pode
ser publicada sem processo de revisão.

---

## 40.5 LGPD no código

O que o doc 38 pede e que precisa existir como rota, tabela ou rotina.

### 40.5.1 Rotas de direitos do titular (L-17 a L-23)

Prefixo `/api/v1/me`, autenticado, agindo sempre sobre o próprio usuário:

| Rota | Direito | Art. |
|---|---|---|
| `GET /me` | Confirmação de existência e acesso, formato simplificado, imediato | 18, I e II; 19, I |
| `GET /me/dados` | Declaração completa: origem, finalidade, base legal, com quem foi compartilhado, prazo de guarda | 18, I, II e VII; 19, II |
| `PATCH /me` | Correção de nome e e-mail | 18, III |
| `GET /me/portabilidade` | Pacote em formato de uso subsequente (JSON + CSV), reaproveitando o `ProfileService` já escoposto | 18, V; 19, §3º |
| `DELETE /me` | Eliminação da conta e de tudo que dela depende | 18, VI; 16 |

**`DELETE /me` é o que exige mais cuidado.** Precisa, numa transação:

1. apagar projetos, papers, extrações, auditoria, execuções de coleta;
2. **apagar os PDFs do disco** via `PDFService.delete_pdf` — o `L-24`/O da
   cascata incompleta (`api/v1/projects.py:110`), que é a mesma correção;
3. apagar configurações de IA e credenciais de fontes do usuário;
4. revogar todas as sessões (`revoke_all_sessions`, já existe);
5. apagar o `UserModel`;
6. registrar no ROPA **que houve eliminação**, sem guardar o que foi eliminado.

Confirmação em dois passos na interface, e prazo de arrependimento **declarado**
(por exemplo 7 dias com a conta desativada antes do apagamento efetivo) — desde
que o aviso de privacidade diga exatamente isso.

### 40.5.2 Registro das operações de tratamento — ROPA (L-60)

Tabela `processing_records`, distinta do `AuditLogModel` (que registra decisões
metodológicas sobre estudos, e continua como está):

| Coluna | Conteúdo |
|---|---|
| `id`, `occurred_at` | — |
| `user_id` | titular ou operador envolvido |
| `operation` | `signup`, `login`, `data_export`, `data_erasure`, `ai_dispatch`, `pdf_fetch`, `consent_given`, `consent_revoked` |
| `legal_basis` | inciso do art. 7º aplicado |
| `purpose` | finalidade declarada |
| `data_categories` | categorias, **não** o dado |
| `recipient` | destinatário, quando houver (ex.: `google_gemini`) |
| `international` | booleano |

**Regra dura:** o ROPA registra *que* houve tratamento, nunca o conteúdo
tratado. Um registro de auditoria que copia o dado pessoal é mais um lugar de
onde ele vaza.

### 40.5.3 Retenção e expurgo (L-28 a L-35)

Rotina diária (`app/services/retention_service.py`), acionada por *scheduler*
simples no `lifespan`:

| Alvo | Prazo | Fundamento |
|---|---|---|
| `LoginAttemptModel` (contém IP) | 90 dias | A janela do limite é de 15 min |
| `SessionModel` expiradas | já eliminadas em `resolve_session` | — |
| `OAuthStateModel` | 10 minutos | Uso único |
| Log de aplicação | 90 dias, com rotação diária | Necessidade |
| Conta inativa (sem login) | aviso em 24 meses, eliminação em 36 | Necessidade; **declarar no aviso** |
| Conta excluída pelo titular | 7 dias desativada → eliminação | Art. 16 |
| ROPA | 5 anos | Prestação de contas (art. 6º, X) |

Log passa de `FileHandler` para `RotatingFileHandler` (ou saída em JSON para o
`stdout`, coletada pelo Docker com `max-size`/`max-file` — a opção
recomendada em contêiner). Resolve O-21 e L-32.

### 40.5.4 Transparência da IA (L-16, L-37)

Com BYOK, a transferência é decisão do assinante — e por isso a interface tem de
tornar essa decisão **informada**, não implícita:

- na tela de configuração de IA, um aviso permanente e destacado nomeando o
  destino de cada provedor e o país;
- ao acionar triagem ou extração assistida pela primeira vez num projeto,
  confirmação explícita, registrada no ROPA como `consent_given` para
  `ai_dispatch`;
- **remoção do campo `AUTORES:` do prompt de triagem**
  (`infrastructure/ai/prompts.py:129,156`) — L-11: o nome do autor não tem
  função na decisão por título e resumo, e é o dado pessoal enviado em maior
  volume;
- opção de provedor local (`factory.py:70`) apresentada como alternativa de
  privacidade, e não escondida como recurso avançado.

### 40.5.5 Páginas obrigatórias (L-12)

`/privacidade` e `/termos`, estáticas, versionadas no repositório, com data de
versão visível. O aviso de privacidade precisa cobrir, no mínimo: identificação
e contato do controlador; encarregado; dados coletados e origem (inclusive o que
vem do Google); finalidades e bases legais; compartilhamento e destinatários;
transferência internacional quando houver (VPS fora do Brasil e provedores de
IA); prazos de retenção; direitos do art. 18 e como exercê-los; e a política de
*cookies* — que, no desenho de §40.7, se resume a um cookie de sessão
estritamente necessário.

---

## 40.6 Concorrência: por que um worker

`HarvestJobManager` guarda tarefas num `dict` do processo (`:25`); o gestor de
WebSocket também é por processo; o limitador de taxa conta em memória
(`middleware.py:109`); e o `lifespan` marca como falho todo job `running` ao
subir (`main.py:129-146`). São quatro estados de processo. Com dois workers,
os quatro divergem.

**Decisão para a v1: `uvicorn --workers 1`, com escala vertical.**

A conta que sustenta: o trabalho pesado do RSAC é **espera de rede** — coleta em
bases bibliográficas, busca de PDF, chamada de IA — e tudo isso já é
`async`/`httpx`. Um único laço de eventos atende dezenas de requisições
concorrentes sem esforço. O que não é assíncrono e ocupa CPU é a extração de
texto de PDF (PyMuPDF), e essa é a única peça que pode travar o laço.

**Mitigação obrigatória:** extração de texto e cálculo de *hash* rodam em
`run_in_threadpool` (`starlette.concurrency`), nunca no laço.

**Gatilho escrito para mudar.** Passar a fila externa (Redis + `arq`/RQ, ou
`huey`) quando **qualquer** um ocorrer:

- p95 de latência das rotas interativas acima de 1 s por mais de 24 h;
- mais de 20 assinantes ativos por semana;
- necessidade de mais de um processo por razão de disponibilidade
  (implantação sem interrupção).

Até lá, a complexidade de uma fila não se paga.

---

## 40.7 Infraestrutura

### 40.7.1 Provedor e região

Conforme §39.5: **região brasileira**, para que não haja transferência
internacional dos dados de assinantes. Opções com presença em São Paulo:
Vultr, Magalu Cloud, Locaweb, Oracle Cloud. Se por custo optar-se por
provedor no exterior, é obrigatório assinar e arquivar as cláusulas-padrão
contratuais do provedor e declarar a transferência no aviso (L-37, L-38).

**Dimensionamento inicial:** 4 vCPU, 8 GB de RAM, 80 GB de SSD (NVMe). O disco
é o recurso que aperta primeiro — PDFs de teses passam de 5 MB com frequência.

### 40.7.2 Composição

| Serviço | Imagem | Notas |
|---|---|---|
| `caddy` | `caddy:2-alpine` | TLS automático; único a publicar 80/443; serve `landing/dist` e `frontend/dist` |
| `api` | construída do repositório | `uvicorn app.main:app --workers 1`; `RSAC_DEPLOYMENT_PROFILE=server` |
| `db` | `postgres:16-alpine` | **Sem porta publicada**; volume `pgdata` |
| `backup` | `alpine` + `cron` | `pg_dump` + `tar` dos PDFs, cifra e envia |

**Imagem da API:** construção em dois estágios, execução como usuário sem
privilégio, sem compilador na imagem final, `HEALTHCHECK` apontando para
`/api/v1/health`.

### 40.7.3 Segredos e configuração

Arquivo `.env` no servidor, permissão `0600`, dono `root`, **fora do
repositório** (o `.gitignore` já cobre `.env`). Mínimo obrigatório:

```
RSAC_DEPLOYMENT_PROFILE=server
RSAC_SECRET_KEY=<32+ bytes aleatórios>      # já obrigatório em server (main.py:88)
RSAC_DATABASE_URL=postgresql+psycopg://...
RSAC_CORS_ORIGINS=https://<domínio>       # aceita lista separada por vírgula
RSAC_TRUSTED_HOSTS=<domínio>
RSAC_GOOGLE_CLIENT_ID=...
RSAC_GOOGLE_CLIENT_SECRET=...
RSAC_CONTACT_EMAIL=<e-mail de contato acadêmico>
```

Rotação de `RSAC_SECRET_KEY` exige recifrar as colunas protegidas — procedimento
escrito antes de precisar, não durante.

### 40.7.4 Endurecimento do hospedeiro

- SSH só por chave, sem senha, sem `root` direto; porta padrão serve.
- `ufw`: apenas 22, 80, 443. Postgres nunca exposto.
- `fail2ban` no SSH.
- Atualizações de segurança automáticas (`unattended-upgrades`).
- Fuso `UTC` no servidor; a apresentação converte.
- **Cifra em repouso (L-49):** volume de dados em disco cifrado (LUKS ou o
  recurso equivalente do provedor). É o que sustenta o art. 48, §3º na
  hipótese de incidente.

### 40.7.5 Limites de recurso (O-25, O-26)

| Limite | Valor inicial | Onde |
|---|---|---|
| Tamanho de PDF | 50 MB (hoje 100) | `config.py:max_upload_mb` |
| Armazenamento por conta | 5 GB | novo, verificado em `PDFService` |
| Projetos por conta | 20 | novo |
| Papers por projeto | 20 000 | novo |
| Corpo de requisição | 60 MB | Caddy `request_body` |

Ao exceder, a resposta é `413`/`429` com mensagem que diz o que fazer — nunca
uma falha silenciosa.

### 40.7.6 Backup (L-34, O-23)

**Diário**, retenção de 30 dias:

1. `pg_dump -Fc` do banco;
2. `tar` do volume de PDFs (incremental por data de modificação);
3. cifra com `age` usando chave pública cujo par privado **não fica no
   servidor**;
4. envio para armazenamento externo (Backblaze B2 ou S3), em região que também
   deve ser considerada quanto à transferência internacional;
5. registro do resultado; falha gera alerta.

**Restauração testada mensalmente**, em VPS descartável, com o tempo medido e
anotado. Backup não testado não é backup — é a suposição de que existe um.

**Eliminação propagada (L-34):** o aviso de privacidade declara que os backups
têm ciclo de 30 dias e que a eliminação pedida pelo titular se completa nesse
prazo. É a formulação honesta e é o que o art. 16 admite.

---

## 40.8 Landing page

### 40.8.1 Posicionamento

O público é acadêmico: pesquisadores, pós-graduandos e orientadores que vão
julgar a ferramenta pelo **rigor metodológico**, não pela animação. A página
tem de parecer o que o produto é — um instrumento sério, em BETA, feito por
quem entende de revisão sistemática.

**A regra que organiza todas as decisões abaixo:** a landing se parece com um
*documento científico bem tipografado*, não com uma página de startup. Réguas
finas em vez de cartões com sombra; números reais em vez de contadores
animados; a lista das diretrizes suportadas em vez de depoimentos.

**Proibido, explicitamente:** depoimentos inventados, logotipos de
universidades sem autorização, métricas de tração falsas ("+10.000
pesquisadores"), contadores animados, ilustrações genéricas de pessoas em
escritório, gradientes vibrantes, *mockups* 3D flutuando. O produto está em
BETA — dizer isso com clareza vale mais, nesse público, do que qualquer
promessa.

### 40.8.2 Sistema visual

Paleta **Platinum & Dusk Blue**, que já existe no design system
(`frontend/src/styles/globals.css`, `[data-theme='platinum-dusk']`) e é a mais
"tech séria" das treze:

| Papel | Token | Hex |
|---|---|---|
| Fundo | Platinum | `#e7ecef` |
| Superfície | Branco | `#ffffff` |
| Texto | Deep Dusk Blue | `#152940` |
| Acento / marca | Dusk Blue | `#274c77` |
| Acento secundário | Air Superiority Blue | `#6096ba` |
| Régua | — | `#c4d3de` |
| Régua sutil | — | `#dbe5ec` |

Tema escuro obrigatório, respeitando `prefers-color-scheme`.

**Tipografia.** Duas famílias, **auto-hospedadas em `woff2`**:

- **JetBrains Mono** — sobrescritas, etiquetas, números, versão, identificadores.
  É a mesma `--font-mono` da aplicação, e é o que amarra a landing ao produto.
- **Inter** — títulos e corpo.

> **Nunca carregar fonte do CDN do Google.** Uma requisição a
> `fonts.googleapis.com` envia o IP de cada visitante ao Google, o que é
> tratamento de dado pessoal sem base legal declarada e transferência
> internacional. Auto-hospedar resolve os dois e ainda é mais rápido.

**Grade e ritmo.** Máximo de 1200 px, 12 colunas, espaçamento generoso, seções
separadas por régua de 1 px — não por blocos coloridos. A marca aparece **uma
vez** no topo e uma vez no rodapé.

**Movimento.** Apenas revelação suave ao rolar (`opacity`/`translateY`, 200 ms),
desligada sob `prefers-reduced-motion`. Nada mais.

### 40.8.3 Estrutura

| # | Seção | Conteúdo | Por que existe |
|---|---|---|---|
| 1 | **Hero** | Monograma; título em uma linha do que o RSAC faz; subtítulo com a promessa metodológica; **[Entrar com Google]** e [Ver como funciona]; etiqueta `BETA` visível | Quem chega precisa saber em 5 s o que é e entrar em 1 clique |
| 2 | **O problema** | Três números honestos sobre o custo de uma revisão manual, com fonte citada | Estabelece competência: quem cita fonte na landing cita no produto |
| 3 | **O fluxo** | Diagrama SVG **inline** das seis etapas: Protocolo → Coleta → Deduplicação → Triagem → Extração → Síntese | É o produto inteiro numa figura; SVG inline não custa requisição |
| 4 | **Diretrizes suportadas** | As 11, nomeadas com versão (PRISMA 2020, PRISMA-ScR 2018, PRISMA-P 2015, JBI, Cochrane/MECIR, Campbell/MECCIR, CEE/ROSES, EBSE, PRIOR, Methodi Ordinatio, Personalizada) | **A seção mais persuasiva para este público.** Ninguém finge suportar 11 diretrizes |
| 5 | **IA com procedência** | Cada sugestão traz justificativa ancorada no texto, página de referência e trilha (`provedor`, `modelo`, *hash* do contexto); o pesquisador decide sempre | Diferencial real e verificável — e responde à desconfiança legítima do meio acadêmico |
| 6 | **Bases integradas** | BDTD, SciELO, PubMed, Scopus, OpenAlex, arXiv + importação RIS/BibTeX/CSV/XLSX | Cobertura nacional é diferencial que ferramenta estrangeira não tem |
| 7 | **Seus dados** | Onde ficam, quem acessa, o que sai para a IA e por quê, com link ao aviso | Público acadêmico verifica isso — e cumpre L-12/L-16 |
| 8 | **Rodapé** | Versão, licença MIT, repositório, contato do encarregado, links de Termos e Privacidade | Obrigatório (art. 41, §1º) e sinal de seriedade |

### 40.8.4 Implementação

- Projeto próprio em `landing/`, construído por Vite para HTML+CSS estáticos.
  **Sem framework de interface**: a página não tem estado.
- JavaScript apenas para o alternador de tema e a revelação ao rolar —
  abaixo de 5 KB. A página funciona inteira sem JS.
- CSS crítico embutido no `<head>`; o restante em um único arquivo.
- SVGs da marca reaproveitados de `brand/svg/`.
- Metas: **LCP < 1,5 s** em 4G simulado, **CLS < 0,05**, Lighthouse ≥ 95 nas
  quatro categorias, **zero requisição a terceiros**.
- SEO: `title` e `description` próprios, Open Graph com imagem gerada a partir
  do monograma, JSON-LD `SoftwareApplication`, `sitemap.xml`, `robots.txt`,
  `lang="pt-BR"`.
- Acessibilidade: WCAG 2.1 AA, verificada com o `axe-core` que o repositório já
  usa (`frontend/scripts/a11y-audit.mjs`).
- **Sem cookie de rastreio, sem analytics de terceiros** → **não há banner de
  cookies**, porque o único cookie é o de sessão, estritamente necessário. Se
  houver necessidade de medição, usar contagem no lado do servidor a partir do
  log do Caddy, agregada e sem IP.

---

## 40.9 Observabilidade

| Sinal | Implementação |
|---|---|
| Saúde profunda | `/api/v1/health` passa a executar `SELECT 1`, verificar o volume de PDFs e devolver `503` quando algo falhar (O-22) |
| Log estruturado | JSON no `stdout`, coletado pelo Docker com `max-size=50m`, `max-file=5`; o filtro de segredos continua ativo |
| Disponibilidade externa | Monitor de terceiro (UptimeRobot/BetterStack) no `/api/v1/health`, alerta em 2 falhas seguidas |
| Disco | Alerta em 75% e 90% de uso — é o recurso que morre primeiro (O-24) |
| Erros | Contagem de `5xx` por rota no log; investigação obrigatória acima de 1% |
| Backup | Registro do resultado diário; ausência de sucesso em 48 h gera alerta |

**Sem APM de terceiro na v1.** Sentry e equivalentes capturam corpo de
requisição e contexto — isto é, dado pessoal enviado a um terceiro, quase sempre
no exterior, o que reabriria o art. 33 que o BYOK acabou de fechar. Se vier a
ser necessário, avaliar instância auto-hospedada com `send_default_pii=False`.

---

## 40.10 Portão de publicação

O serviço **não** vai ao ar com qualquer destes em aberto:

| # | Condição | Verificação |
|---|---|---|
| 1 | Isolamento provado | `test_tenancy_isolation.py` verde para toda rota com `{project_id}`/`{paper_id}` |
| 2 | Chaves de IA e credenciais por usuário | Teste: A salva chave, B não a vê nem a usa |
| 3 | Migração versionada | `alembic upgrade head` e `downgrade -1` em base com dado |
| 4 | Login com Google, com as seis validações de §40.4.3 | Suíte de OAuth, incluindo `aud` errado, `nonce` divergente e `email_verified=false` |
| 5 | `DELETE /me` elimina banco **e** PDFs | Teste que confere o disco depois |
| 6 | Aviso de privacidade e Termos publicados e datados | Inspeção |
| 7 | Backup executado e **restauração testada** | Registro do teste, com tempo medido |
| 8 | Cifra em repouso ativa | Inspeção do volume |
| 9 | TLS com nota A, HSTS ativo | SSL Labs |
| 10 | Suíte de segurança e testes verdes em PostgreSQL **e** SQLite | CI |
| 11 | Perfil `desktop` intacto | Roteiro manual do doc 17 |
| 12 | Checklist do doc 38 reaferido e datado | Doc 38 atualizado |
