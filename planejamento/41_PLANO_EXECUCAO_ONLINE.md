# 41 — Plano de Execução: Revsist Online

> **Este é o documento de trabalho.** Oito fases, cada uma com tarefas
> marcáveis, critério de aceite verificável e o que fazer se der errado.
> **Desenho alvo:** [`40_ESPECIFICACAO_ONLINE.md`](./40_ESPECIFICACAO_ONLINE.md).
> **Motivação medida:** [`39_DIAGNOSTICO_ONLINE.md`](./39_DIAGNOSTICO_ONLINE.md).
> **Restrições de dados:** [`38_CHECKLIST_LGPD.md`](./38_CHECKLIST_LGPD.md).
>
> **Estimativa total: 26 a 39 dias de trabalho focado.**

---

## Como executar

- **A ordem das Fases 0 → 1 → 2 não é negociável.** Alembic antes de tudo, ou
  toda alteração de esquema vira dívida; titularidade antes de identidade, ou
  se deixa entrar quem não terá acervo isolado; ambas antes da infraestrutura,
  ou se migra dado real depois.
- **Uma fase por branch, um PR por fase.** A CI é o portão.
- **Nenhuma fase fecha sem seu critério de aceite verde.**
- Fases **5** (landing) e **6** (observabilidade) são independentes das demais
  e podem correr em paralelo a qualquer momento — a landing não toca no backend.
- Ao fim de cada fase, **reaferir os itens correspondentes do doc 38** e datar.

### Trabalho preparatório (pode ser feito hoje, 1–2 h)

- [x] **P1** Registrar domínio — **Concluído: `revsist.com`** (Nome oficial do app: **Revsist**; logotipo e identidade visual mantidos)
- [ ] **P2** Criar projeto no Google Cloud Console e a credencial OAuth (§40.4.6) — URI de redirecionamento: `https://revsist.com/api/v1/auth/google/callback`
- [ ] **P3** Contratar VPS em **região brasileira** (§39.5) — 4 vCPU / 8 GB / 80 GB
- [ ] **P4** Criar conta de armazenamento de backup (Backblaze B2 ou S3)
- [ ] **P5** Gerar par de chaves `age` para cifra de backup; **guardar a chave privada fora do servidor**
- [ ] **P6** Definir o endereço de contato do encarregado (art. 41, §1º)

---

## Fase 0 — Fundação de persistência

> **Objetivo:** poder evoluir o esquema em produção sem risco, e rodar tanto em
> SQLite (desktop) quanto em PostgreSQL (servidor).
> **Esforço:** 3–5 dias · **Risco:** alto — toca o esquema inteiro.
> Fecha O-06 a O-11.
>
> ## ✅ **CONCLUÍDA** — 27/08/2026
>
> **431 testes verdes em PostgreSQL 16, 430 em SQLite** (eram 421 antes).
> Verificação feita contra um PostgreSQL real, não simulado.
>
> Três coisas que só apareceram na execução, e que o plano não previa:
>
> 1. **O código já era quase agnóstico de dialeto.** A suíte inteira passou em
>    PostgreSQL logo após a correção de `database.py`, sem uma única alteração
>    de consulta. O diagnóstico superestimou este risco.
> 2. **`%` na URL do banco quebrava a partida.** `Config.set_main_option` grava
>    no `configparser`, que trata `%` como interpolação: uma senha de banco
>    contendo `%` derrubaria o servidor com `ValueError: invalid interpolation
>    syntax`, sintoma que não sugere a causa em nada. A URL saiu do `.ini`; a
>    conexão viaja por `config.attributes`. Regressão fixada em teste.
> 3. **A conversão para `timestamptz` deslocava todo o banco.** `ALTER COLUMN
>    ... TYPE timestamptz` sem cláusula interpreta cada valor como hora local
>    *do servidor*: medido num servidor em `America/Sao_Paulo`, as 12:00 UTC
>    gravadas viravam 15:00 UTC. A revisão declara `postgresql_using="col AT
>    TIME ZONE 'UTC'"`, e o teste roda a migração com o servidor fora de UTC
>    para provar que o instante sobrevive.
>
> Os testes de *threadpool* foram verificados por mutação: desfazendo o desvio,
> ambos falham.

### Tarefas

- [x] **0.1** Adicionar `psycopg[binary]>=3.2` a `backend/pyproject.toml`
- [x] **0.2** Reescrever `backend/app/database.py` derivando do dialeto (§40.2.2): `connect_args` e PRAGMAs **apenas** no ramo `is_sqlite`; `pool_size`/`max_overflow`/`pool_recycle` no ramo PostgreSQL
- [x] **0.3** Inicializar Alembic em `backend/alembic/`, com `env.py` lendo `settings.effective_database_url` e `target_metadata = Base.metadata`
- [x] **0.4** Gerar a revisão inicial a partir do esquema atual (`alembic revision --autogenerate -m "esquema inicial"`) e **conferir o arquivo gerado linha a linha** — autogeração erra em índices e tipos
- [x] **0.5** Remover `_migrate_missing_columns()` e trocar `create_tables()` por `alembic upgrade head` no `lifespan` (`main.py:79`)
- [x] **0.6** Migrar todas as colunas de data para `DateTime(timezone=True)`, em revisão própria e separada
- [x] **0.7** Revisar `security/sessions.py:_naive_utc` para funcionar nos dois dialetos, com teste que cria sessão, avança o relógio e confere a expiração em cada um
- [x] **0.8** Escrever `docs`/`README` do procedimento: `alembic stamp head` para bancos desktop preexistentes
- [x] **0.9** Adicionar serviço `postgres:16-alpine` ao `docker-compose.dev.yml` para desenvolvimento
- [x] **0.10** Estender a CI: matriz que roda a suíte inteira em **SQLite** e em **PostgreSQL**; passo `alembic check` que falha se o modelo divergir da última revisão
- [x] **0.11** Mover extração de texto de PDF e cálculo de *hash* para `run_in_threadpool` (§40.6)

### Critério de aceite

- [x] `pytest -q` verde nos dois bancos
- [x] `alembic upgrade head` e `alembic downgrade -1` funcionam numa base com dados
- [x] `alembic check` não acusa divergência
- [x] O app de mesa abre, lê um projeto antigo e grava — sem migração manual
- [x] Nenhuma ocorrência de `PRAGMA` ou `check_same_thread` fora do ramo SQLite

### Se der errado

A Fase 0 não toca dado de produção (ainda não há). O reparo é `git revert` do
PR e recomeçar da revisão inicial. **Antes de mexer, copiar o `rsac.db` de
desenvolvimento** — é a única base com dado real neste momento.

---

## Fase 1 — Titularidade e isolamento

> **Objetivo:** cada acervo pertence a um usuário e é inalcançável pelos demais.
> **Esforço:** 4–6 dias · **Risco:** alto — toca todas as rotas.
> Fecha O-01 a O-05 e o bloqueante **L-46**.
>
> ## ✅ **CONCLUÍDA** — 27/08/2026
>
> **438 testes verdes nos dois bancos** (eram 431 ao fim da Fase 0).
>
> A suíte de isolamento enumera as rotas pelo **esquema OpenAPI** — 25 rotas
> com `{project_id}` — e exige 404 de todas para um segundo usuário. Verificada
> por mutação: removendo a dependência de um único router, ela falha nomeando
> a rota exata que escapou.
>
> Três achados da execução:
>
> 1. **A migração quebrava o app de mesa de quem tinha dados.** O SQLite não
>    altera coluna sem recriar a tabela, e com `PRAGMA foreign_keys=ON` o
>    `DROP TABLE projects` falha porque `papers` e `protocols` a referenciam.
>    O primeiro teste passou só porque o banco tinha um projeto **vazio** —
>    qualquer instalação real teria morrido com `FOREIGN KEY constraint failed`
>    e deixado o pesquisador sem acesso ao próprio trabalho. A migração passou
>    a suspender a verificação e a conferir `PRAGMA foreign_key_check` ao
>    final; há teste de regressão com projeto, artigo e protocolo.
> 2. **Enumerar rotas por `app.routes` encontrava zero.** O FastAPI aninha as
>    rotas incluídas em `_IncludedRouter`, um objeto interno cuja forma já
>    mudou entre versões. A enumeração passou a sair do esquema OpenAPI, que é
>    API pública. O piso mínimo afirmado no teste (`>= 15`) foi o que impediu
>    que ele passasse verificando nada.
> 3. **`require_owner` deixou de ser o critério certo.** Com contas
>    individuais, todo assinante gere as próprias chaves; negar por papel
>    protegia a chave de quem convidava, mas só porque havia **uma**
>    configuração no banco inteiro. A garantia nova é mais forte e está em
>    `test_credencial_de_um_nao_vaza_para_outro`: a chave de A não aparece — nem
>    mascarada — para B.
>
> A migração recusa-se a adivinhar: com dados sem dono e mais de uma conta
> ativa, ela **falha** em vez de atribuir o acervo a alguém.

### Tarefas

- [x] **1.1** `ProjectModel.owner_id` — FK `users.id`, `nullable=False`, indexado
- [x] **1.2** `AISettingsModel.user_id` — FK única: uma configuração por usuário
- [x] **1.3** `SourceCredentialModel` — chave única composta `(user_id, source_name)`
- [x] **1.4** Revisão Alembic que cria as colunas e **atribui tudo à conta ativa mais antiga** (a única, no desktop)
- [x] **1.5** Criar `projeto_do_usuario` em `security/dependencies.py`, devolvendo **404** e nunca 403 (§40.3.2)
- [x] **1.6** Aplicar a dependência nos nove roteadores com `/projects/{project_id}` no prefixo: `papers`, `protocols`, `harvest`, `deduplication`, `extraction` (os dois), `export`, `insights`, `screening_ai`
- [x] **1.7** `api/v1/projects.py` — `GET ""` e `GET "/{id}/stats"` filtram por `owner_id`; `POST ""` grava o dono
- [x] **1.8** `api/v1/ai.py` — trocar as dez ocorrências de `db.query(AISettingsModel).first()` por consulta escopada ao usuário corrente
- [x] **1.9** `api/v1/settings.py` — credenciais de fonte por usuário
- [x] **1.10** `infrastructure/ai/factory.py:25` — receber o usuário e resolver a configuração dele
- [x] **1.11** `services/profile_service.py` — exportação e importação restritas ao usuário corrente (O-05)
- [x] **1.12** Trocar `require_owner` por titularidade de recurso nas rotas de credencial; manter `require_owner` **apenas** na gestão de contas (§40.3.3)
- [x] **1.13** Corrigir a cascata de `DELETE /projects/{id}`: chamar `PDFService.delete_pdf` para cada paper (fecha **L-24**)
- [x] **1.14** Escrever `backend/tests/test_security/test_tenancy_isolation.py` que **enumera `app.routes`** e prova 404 para o segundo usuário em toda rota com `{project_id}`/`{paper_id}`
- [x] **1.15** Teste: usuário A salva chave de IA; usuário B não a vê nem a utiliza
- [x] **1.16** Frontend: nada muda (a API já é a mesma) — confirmar que nenhuma tela dependia de configuração global de IA

### Critério de aceite

- [x] `test_tenancy_isolation.py` verde, e **falha** se alguém adicionar rota sem isolamento (verificar com uma rota de teste propositalmente desprotegida)
- [x] Nenhuma consulta a `ProjectModel`, `AISettingsModel` ou `SourceCredentialModel` sem filtro de usuário: `grep -rn "query(ProjectModel)\|query(AISettingsModel)\|query(SourceCredentialModel)" backend/app` revisado item a item
- [x] Excluir projeto remove os PDFs do disco (teste confere o sistema de arquivos)
- [x] Perfil `desktop` intacto: uma conta, tudo dela

### Se der errado

O ponto delicado é 1.4 — atribuir dono a dados existentes. A revisão precisa
falhar explicitamente se houver mais de uma conta ativa, em vez de escolher uma.
`downgrade` remove as colunas sem perder dado.

---

## Fase 2 — Identidade: login com Google

> **Objetivo:** entrar com Google, sem quebrar senha nem token local.
> **Esforço:** 3–4 dias · **Risco:** médio. Fecha O-16 a O-20.
>
> ## ✅ **CONCLUÍDA** — 28/08/2026
>
> **465 testes verdes nos dois bancos** (eram 438 ao fim da Fase 1), sendo 25
> só do OAuth. A tela foi verificada no navegador, contra um servidor real.
>
> A suíte gera um par de chaves RSA próprio e finge ser o Google, o que permite
> derrubar **cada uma** das seis validações isoladamente. Verificada por
> mutação: removendo a checagem de `aud`, de `nonce` ou de `email_verified`, os
> testes correspondentes falham.
>
> Dois achados da execução:
>
> 1. **`RSAC_CORS_ORIGINS=https://rsac.exemplo.br` derrubava a partida.** O
>    comentário do `config.py` prometia aceitar valores separados por vírgula,
>    mas o pydantic-settings só desserializa JSON — e o erro
>    (`error parsing value for field "cors_origins"`) não diz o que ele quer.
>    O exemplo de `.env` do doc 40 §40.7.3 usava exatamente a forma que quebra:
>    a implantação da Fase 4 teria morrido na primeira subida. Corrigido com
>    `NoDecode` mais um validador; as duas formas passaram a funcionar.
> 2. **A autogeração do Alembic criava colunas `NOT NULL` sem valor padrão.**
>    Funciona em banco vazio e falha em qualquer instalação com uma conta — que
>    é justamente a que existe, porque o backend se recusa a subir sem conta no
>    perfil `server`. As colunas passaram a entrar com `server_default`, que é
>    removido em seguida.
>
> O `downgrade` desta revisão recusa-se a rodar se houver conta que só entra
> com Google: reverter a deixaria sem credencial nenhuma.

### Tarefas

- [x] **2.1** Adicionar dependências de verificação de JWT (`authlib` ou `joserfc` + `httpx`) — a verificação do `id_token` é **local**, contra a JWKS do Google, com cache
- [x] **2.2** `UserModel`: `email`, `email_verified`, `google_sub`, `display_name`, `auth_provider`; `password_hash` passa a `nullable=True` (§40.4.2)
- [x] **2.3** Criar `OAuthStateModel` com TTL de 10 min e uso único
- [x] **2.4** Revisão Alembic para 2.2 e 2.3
- [x] **2.5** `GET /api/v1/auth/google/start` no **`public_auth_router`** — gera `state`, `nonce` e `code_verifier` (PKCE S256), grava e redireciona
- [x] **2.6** `GET /api/v1/auth/google/callback` — consome o `state` (apagando-o), troca o código, e aplica **as seis validações** de §40.4.3
- [x] **2.7** Recusar login quando `email_verified` for falso, com mensagem clara — **a trava contra tomada de conta**
- [x] **2.8** Vínculo: `google_sub` → e-mail verificado → criação nova com `role="researcher"` (§40.4.3)
- [x] **2.9** Descartar a foto do perfil na leitura; **não** gravar (art. 6º, III)
- [x] **2.10** Emitir sessão pelo `create_session` existente e redirecionar para `/app`
- [x] **2.11** Lista de admissão opcional por `RSAC_SIGNUP_ALLOWLIST` (vazia = aberto) — é o modo "por convite" da v1
- [x] **2.12** Registrar aceite de Termos e Aviso com data, versão e origem
- [x] **2.13** `_familia_da_rota` (`security/middleware.py:83`) passa a casar `/auth/google` na família `auth`
- [x] **2.14** Login por senha recusa explicitamente conta sem hash, com mensagem "esta conta entra com Google"
- [x] **2.15** `AuthStatusResponse` ganha `google_login_enabled`, para a tela decidir o que mostrar
- [x] **2.16** Frontend: botão "Entrar com Google" na `LoginPage`, seguindo as diretrizes de marca do Google; senha recolhida atrás de "outras formas de entrar"
- [x] **2.17** Expurgo de `OAuthStateModel` vencido na rotina de retenção (Fase 3)
- [x] **2.18** Suíte `backend/tests/test_security/test_oauth_google.py`: `aud` errado, `iss` errado, `exp` vencido, `nonce` divergente, `state` reutilizado, `email_verified=false`, vínculo por e-mail, criação nova, e **tentativa de autocadastro com `role=owner`**

### Critério de aceite

- [x] Entrar com Google numa conta nova cria usuário `researcher` e sessão válida
- [x] Entrar com Google num e-mail já cadastrado **vincula**, não duplica
- [x] Cada uma das seis validações rejeitada isoladamente pela suíte
- [x] `email_verified=false` **não** entra
- [x] Login por senha do `owner` continua funcionando
- [x] Perfil `desktop` entra pelo token local, sem passar pelo Google
- [x] Rota de OAuth cai no limite de 10 tentativas por 15 min

### Se der errado

O OAuth é isolado: enquanto as rotas novas não existirem no `public_router`,
nada muda. Se o vínculo por e-mail se mostrar arriscado no seu caso, a postura
conservadora é **desligá-lo** (só `google_sub`) e vincular contas manualmente
por CLI.

---

## Fase 3 — LGPD no código

> **Objetivo:** fechar os itens do doc 38 que dependem de código.
> **Esforço:** 4–6 dias · **Risco:** baixo.
> Fecha L-11, L-16, L-17 a L-25, L-28 a L-33, L-60 e O-21.

### Tarefas

- [ ] **3.1** Router `/api/v1/me` com as cinco rotas de §40.5.1
- [ ] **3.2** `DELETE /me` — transação com os seis passos de §40.5.1, incluindo apagar PDFs e revogar sessões
- [ ] **3.3** Prazo de arrependimento: conta desativada por 7 dias antes da eliminação, **declarado no aviso**
- [x] **3.4** ✅ Modelo `processing_records` (ROPA) e revisão Alembic `1b724bcfc68e`
- [ ] **3.5** Gravar ROPA em: `signup`, `login`, `data_export`, `data_erasure`, `ai_dispatch`, `pdf_fetch`, `consent_given`, `consent_revoked`
- [x] **3.6** ✅ **Regra dura** garantida por estrutura, não por disciplina: `ropa_service` tem vocabulário fechado, e um e-mail não é categoria válida — a gravação levanta exceção. Três testes por ângulos diferentes
- [ ] **3.7** `services/retention_service.py` com a tabela de prazos de §40.5.3, acionado diariamente pelo `lifespan`
- [ ] **3.8** Expurgo de `LoginAttemptModel` com mais de 90 dias (**L-30**)
- [ ] **3.9** Log para `stdout` em JSON, com limite pelo Docker (`max-size`, `max-file`) — encerra o `FileHandler` sem rotação (**L-32**, O-21)
- [x] **3.10** ✅ **Removido `AUTORES:` do prompt de triagem** (**L-11**). A extração não usava o campo, então nada ficou. O objeto normalizado também deixou de copiá-lo, para o dado não circular à toa dentro do processo. Cobertura em `tests/test_lgpd/test_minimizacao_no_prompt.py`, que testa as duas portas de entrada da função (dicionário e objeto) e três grafias da chave — repor a seção derruba três testes.
- [ ] **3.11** Aviso destacado de destino e país na tela de configuração de IA (**L-16**)
- [ ] **3.12** Confirmação explícita ao acionar IA pela primeira vez em cada projeto, registrada no ROPA
- [ ] **3.13** Provedor local apresentado como alternativa de privacidade, não escondido
- [ ] **3.14** Escrever `/privacidade` e `/termos` como páginas estáticas versionadas, com data de versão (**L-12**) — conteúdo mínimo em §40.5.5
- [ ] **3.15** Publicar identidade e contato do encarregado no rodapé e no aviso (**L-61**)
- [ ] **3.16** Verificar enquadramento em agente de tratamento de pequeno porte (Resolução CD/ANPD nº 2/2022)
- [ ] **3.17** Exportação de perfil sai cifrada por padrão quando contiver dado pessoal (**L-59**)

### Critério de aceite

- [ ] `GET /me/dados` devolve declaração completa; `GET /me` responde imediatamente
- [ ] `DELETE /me` deixa banco **e** disco sem rastro do usuário — teste confere ambos
- [ ] Nenhum nome de autor sai no prompt de triagem: teste que inspeciona o texto montado
- [ ] Rotina de retenção apaga o que deve e nada além — teste com relógio adiantado
- [ ] `/privacidade` e `/termos` no ar, datados
- [ ] Doc 38 reaferido: L-11, L-17, L-22, L-24, L-30, L-32, L-60 passam a ✅

---

## Fase 4 — Infraestrutura e implantação

> **Objetivo:** o serviço no ar, com TLS, backup testado e cifra em repouso.
> **Esforço:** 4–6 dias · **Risco:** médio. Fecha O-12 a O-15, O-23, O-25, O-26, O-28.

### Tarefas

- [ ] **4.1** `Dockerfile` da API em dois estágios, execução sem privilégio, com `HEALTHCHECK`
- [ ] **4.2** `docker-compose.yml` de produção com `caddy`, `api`, `db`, `backup` (§40.7.2)
- [ ] **4.3** `Caddyfile`: TLS automático, `/` → landing, `/app` → SPA, `/api` → API, *upgrade* de WebSocket, `request_body` de 60 MB
- [ ] **4.4** `api` com `--workers 1` e comentário no arquivo apontando §40.6 (para ninguém "otimizar" isso sem ler)
- [ ] **4.5** `db` **sem porta publicada**; volume `pgdata`
- [x] **4.6** ✅ **Feito antes da hora**, ao corrigir o app instalado: `RSAC_DATA_DIR` já era lida pelo `launcher.py` e ignorada pelo backend, o que fazia os dois lados discordarem sobre onde os dados estão. O campo chama-se `data_dir_configurado` e lê `RSAC_DATA_DIR` (não `RSAC_DATA_DIR_OVERRIDE`, como este item previa): a variável já existia e já tinha um leitor. Texto original: Tornar o diretório de dados configurável: hoje `Settings.data_dir` é uma `@property` sobre `platformdirs` (`config.py`), **não** um campo — logo não é ajustável por variável de ambiente. Acrescentar o campo `data_dir_override` (lido de `RSAC_DATA_DIR_OVERRIDE`) e montar o volume nele; sem isso, o volume tem de ser montado no caminho que o `platformdirs` inventar dentro do contêiner
- [ ] **4.7** Endurecer o hospedeiro: SSH só por chave, `ufw` (22/80/443), `fail2ban`, `unattended-upgrades`, fuso UTC
- [ ] **4.8** **Cifra do volume de dados em repouso** — LUKS ou recurso do provedor (**L-49**)
- [ ] **4.9** `.env` com permissão `0600`, dono `root`, fora do repositório; conferir que `RSAC_SECRET_KEY` está definida (a partida já recusa subir sem ela)
- [ ] **4.10** Limites de recurso de §40.7.5: PDF de 50 MB, 5 GB por conta, 20 projetos, 20 000 papers — com `413`/`429` explicativos
- [ ] **4.11** Rotina de backup diária: `pg_dump -Fc` + `tar` dos PDFs, cifrados com `age`, enviados ao armazenamento externo, retenção de 30 dias
- [ ] **4.12** **Testar a restauração** num VPS descartável e **anotar o tempo medido**
- [ ] **4.13** Declarar no aviso o ciclo de 30 dias dos backups (**L-34**)
- [ ] **4.14** Escrever o procedimento de rotação de `RSAC_SECRET_KEY` antes de precisar dele
- [ ] **4.15** Roteiro de implantação: `git pull` → `docker compose build` → `up -d` → verificar `/api/v1/health` → *rollback* documentado
- [ ] **4.16** Provisionar a primeira conta `owner` por CLI, com senha gerada e guardada em gerenciador de senhas

### Critério de aceite

- [ ] `https://revsist.com` responde com nota **A** no SSL Labs, HSTS ativo
- [ ] Postgres inacessível de fora: `nmap` do exterior não vê 5432
- [ ] Backup roda, é cifrado, chega ao destino — e a **restauração foi executada** com tempo anotado
- [ ] Enviar PDF de 60 MB devolve `413` com mensagem clara
- [ ] Reiniciar o servidor traz tudo de volta sem intervenção manual
- [ ] O WebSocket de coleta funciona através do Caddy

### Se der errado

*Rollback* de implantação é voltar a imagem anterior (`docker compose up -d`
com a etiqueta anterior) — por isso as imagens são etiquetadas por commit, não
`latest`. Migração de banco tem `downgrade`, mas **restauração de backup é o
plano real** se a migração corromper dado. É por isso que 4.12 é obrigatório
antes do go-live, não depois.

---

## Fase 5 — Landing page

> ⚠️ **Precedida pelo doc 42 (Plano de Marca).** A landing deixou de ser o
> primeiro artefato de comunicação: a posição, o público e a promessa são
> decididos antes, no doc 42. O sistema visual e a lista de proibições desta
> fase continuam valendo; o que muda é a dobra inicial, entra uma seção sobre
> o rastro de decisão, e entra uma seção sobre o que o Revsist **não** faz.
> Ver §42.12.


> **Objetivo:** a porta de entrada — séria, minimalista, do tema.
> **Esforço:** 3–5 dias · **Risco:** nenhum — código novo e isolado.
> Fecha O-27. **Pode correr em paralelo desde já.**

### Tarefas

- [ ] **5.1** Criar `landing/` com Vite gerando HTML+CSS estáticos, **sem framework**
- [ ] **5.2** Importar os tokens de `platinum-dusk` (§40.8.2) e o tema escuro por `prefers-color-scheme`
- [ ] **5.3** **Auto-hospedar** JetBrains Mono e Inter em `woff2` — nunca CDN do Google (§40.8.2)
- [ ] **5.4** Reaproveitar os SVGs de `brand/svg/`; monograma uma vez no topo, uma no rodapé
- [ ] **5.5** Seção 1 — Hero, com `BETA` visível e **[Entrar com Google]** apontando para `/api/v1/auth/google/start`
- [ ] **5.6** Seção 2 — O problema, com três números honestos e **fonte citada**
- [ ] **5.7** Seção 3 — Diagrama SVG inline das seis etapas do fluxo
- [ ] **5.8** Seção 4 — As 11 diretrizes, nomeadas com versão (**a seção mais persuasiva**)
- [ ] **5.9** Seção 5 — IA com procedência: justificativa ancorada, página de referência, trilha de proveniência
- [ ] **5.10** Seção 6 — Bases integradas, com destaque para a cobertura nacional (BDTD, SciELO)
- [ ] **5.11** Seção 7 — Seus dados, com link ao aviso (**L-12**, **L-16**)
- [ ] **5.12** Rodapé — versão, MIT, repositório, **contato do encarregado**, Termos e Privacidade
- [ ] **5.13** JS abaixo de 5 KB: alternador de tema e revelação ao rolar, desligada sob `prefers-reduced-motion`; **a página funciona sem JS**
- [ ] **5.14** SEO: `title`, `description`, Open Graph com imagem do monograma, JSON-LD `SoftwareApplication`, `sitemap.xml`, `robots.txt`, `lang="pt-BR"`
- [ ] **5.15** Rodar `frontend/scripts/a11y-audit.mjs` contra a landing e corrigir tudo
- [ ] **5.16** Medir: LCP < 1,5 s em 4G simulado, CLS < 0,05, Lighthouse ≥ 95 nas quatro categorias, **zero requisição a terceiros**

### Critério de aceite

- [ ] As quatro metas de 5.16 batidas, com captura de tela do relatório
- [ ] Nenhuma requisição para fora do domínio — conferir na aba de rede
- [ ] Contraste WCAG 2.1 AA nos dois temas
- [ ] A página inteira legível e navegável com JavaScript desligado
- [ ] Nada da lista de proibições de §40.8.1 na página

---

## Fase 6 — Observabilidade e operação

> **Objetivo:** saber que quebrou antes que o usuário conte.
> **Esforço:** 2–3 dias · **Risco:** baixo. Fecha O-22, O-24 e **L-67**.

### Tarefas

- [ ] **6.1** `/api/v1/health` passa a executar `SELECT 1`, verificar o volume de PDFs e devolver `503` quando falhar (O-22)
- [ ] **6.2** Log em JSON no `stdout`, com o filtro de segredos ativo
- [ ] **6.3** Monitor externo no `/api/v1/health`, alerta após 2 falhas seguidas
- [ ] **6.4** Alerta de disco em 75% e 90% (O-24)
- [ ] **6.5** Alerta se não houver backup bem-sucedido em 48 h
- [ ] **6.6** Contagem de `5xx` por rota; limiar de investigação em 1%
- [ ] **6.7** **Plano de resposta a incidente** (**L-67**): responsável nomeado, árvore de decisão, e o prazo de **3 dias úteis** da Resolução CD/ANPD nº 15/2024
- [ ] **6.8** Modelo de comunicação de incidente cobrindo os seis itens do art. 48, §1º (**L-69**)
- [ ] **6.9** *Runbook* de operação: implantar, reverter, restaurar backup, rotacionar segredo, revogar sessão de um usuário, atender requisição de titular
- [ ] **6.10** Ensaio de incidente em mesa: simular vazamento de credencial e percorrer o plano cronometrando

### Critério de aceite

- [ ] Derrubar o Postgres faz `/health` responder `503` e o monitor alertar
- [ ] Encher o disco de teste dispara o alerta de 75%
- [ ] O ensaio de 6.10 foi feito e o tempo até a comunicação simulada cabe em 3 dias úteis
- [ ] O *runbook* foi executado por você **sem consultar o código**

---

## Fase 7 — Endurecimento e portão de publicação

> **Objetivo:** provar que está pronto, e só então abrir.
> **Esforço:** 3–4 dias.

### Tarefas

- [ ] **7.1** `pip-audit` e `bandit` (já nas dependências de desenvolvimento) sem achado alto
- [ ] **7.2** `npm audit` no frontend e na landing
- [ ] **7.3** Autoteste de invasão: com a conta de A, tentar alcançar cada recurso de B por URL direta, por WebSocket e por importação de perfil
- [ ] **7.4** Testar limites: 1 000 papers, PDF de 60 MB, coleta com 5 fontes simultâneas, 20 sessões concorrentes
- [ ] **7.5** Verificar cabeçalhos em produção (`securityheaders.com`) e TLS (SSL Labs)
- [ ] **7.6** Rodar o roteiro manual do doc 17 no perfil `desktop` — nada pode ter quebrado (**O-30**)
- [ ] **7.7** Percorrer os **12 itens do portão** de §40.10, um a um
- [ ] **7.8** Reaferir o doc 38 inteiro e **datar** o cabeçalho
- [ ] **7.9** Abrir para um grupo pequeno (5–10 pessoas) por 2 semanas antes de divulgar
- [ ] **7.10** Atualizar `00_INDICE.md` e `22_LOG_ENTREGAS.md` com o que foi entregue e o que divergiu

### Critério de aceite

- [ ] Os 12 itens do portão de §40.10 verdes
- [ ] Nada da autoinvasão de 7.3 teve sucesso
- [ ] Doc 38 reaferido e datado
- [ ] Perfil `desktop` intacto

---

## Checklist mestre

Uma linha por fase, para acompanhar de longe.

| Fase | Entrega | Bloqueia | Feito |
|---|---|---|---|
| **P** | Domínio, Google Cloud, VPS, backup, chave `age`, encarregado | Fases 2 e 4 | ⬜ |
| **0** | Alembic + PostgreSQL, dialeto derivado, CI em dois bancos | Tudo | ✅ |
| **1** | Titularidade, chaves por usuário, isolamento provado | Publicação | ✅ |
| **2** | Login com Google, PKCE, vínculo seguro, autocadastro travado | Publicação | ✅ |
| **3** | Direitos do titular, ROPA, retenção, prompt sem autores, aviso | Publicação | ⬜ |
| **4** | VPS, Compose, Caddy/TLS, cifra em repouso, backup **restaurado** | Publicação | ⬜ |
| **5** | Landing estática, auto-hospedada, sem terceiros | Publicação | ⬜ |
| **6** | Saúde profunda, alertas, plano de incidente, *runbook* | Publicação | ⬜ |
| **7** | Autoinvasão, portão de §40.10, doc 38 datado | Go-live | ⬜ |

---

## Os cinco erros que este plano evita

Vale deixar escrito por que a ordem é a que é — porque a tentação de inverter
aparece sempre no meio do caminho.

1. **Subir o servidor antes de resolver a titularidade.** É o erro caro: quando
   houver dado real de terceiros, a migração para o modelo isolado deixa de ser
   um `ALTER TABLE` e passa a ser uma operação com janela, aviso e risco.
2. **Trocar SQLite por PostgreSQL sem Alembic antes.** Sem migração versionada,
   a primeira alteração de esquema em produção é feita à mão, e a segunda já
   não se sabe qual foi.
3. **Vincular conta do Google por e-mail sem exigir `email_verified`.** É a
   porta de tomada de conta mais explorada em OAuth, e o custo de fechá-la é
   uma linha de código.
4. **Carregar fonte do Google na landing.** Transforma uma página institucional
   em transferência internacional de IP de visitante sem base legal — pelo
   preço de não hospedar dois arquivos `woff2`.
5. **Ter backup sem nunca ter restaurado.** É a suposição de que existe backup.
   O teste de restauração é a única prova, e é por isso que ele está no
   critério de aceite da Fase 4, não numa lista de intenções.
