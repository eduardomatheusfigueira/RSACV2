# 39 — Diagnóstico da Passagem para Serviço Online

> **Pergunta deste documento:** o RSAC V2 funciona como aplicativo de mesa.
> O que exatamente quebra — ou passa a estar errado — quando o mesmo código
> atende vários pesquisadores pela internet?
> **Decisões de escopo já tomadas** (§39.2): VPS único com Docker Compose,
> contas individuais, chaves de IA do próprio usuário (BYOK), cobrança adiada.
> **Companheiros:** [`40_ESPECIFICACAO_ONLINE.md`](./40_ESPECIFICACAO_ONLINE.md)
> (o desenho alvo) e [`41_PLANO_EXECUCAO_ONLINE.md`](./41_PLANO_EXECUCAO_ONLINE.md)
> (as fases e o checklist de execução).

---

## 39.1 O erro de premissa que este documento desfaz

O RSAC nasceu com uma premissa que o `config.py` já reconhece e nomeia: *o
único cliente é o Electron na mesma máquina*. O plano de segurança (docs 28–30)
tratou a parte visível dessa premissa — o perímetro de rede — criando o
`DeploymentProfile` e derivando dele CORS, documentação da API, cifra de
segredos e partida segura. Foi um trabalho bem feito, e a §39.6 registra o
quanto dele se aproveita inteiro.

Mas o perfil `server` resolveu **quem entra**. Ele não tocou numa segunda
camada da mesma premissa, que só aparece quando entram *duas pessoas
diferentes*: o código inteiro assume que **existe um único usuário**, e por
isso trata o banco como se fosse a pasta pessoal dele.

Três exemplos medidos, em ordem de gravidade:

- `ProjectModel` (`models.py:47`) não tem dono. Qualquer conta autenticada lê,
  edita e apaga qualquer projeto.
- `AISettingsModel` é lido em toda parte como `db.query(AISettingsModel).first()`
  — dez ocorrências entre `api/v1/ai.py`, `services/profile_service.py` e
  `infrastructure/ai/factory.py`. Há **uma linha** de configuração de IA no
  banco inteiro. Com BYOK e dois assinantes, o segundo a salvar sobrescreve a
  chave do primeiro, e a triagem de um roda com a cota paga do outro.
- `SourceCredentialModel` tem `source_name` como chave única global
  (`models.py:389`): a credencial Scopus da universidade A é a credencial que a
  universidade B usa.

Nenhum desses é um *bug*. São consequências corretas de uma premissa que era
verdadeira e deixou de ser. É por isso que a passagem para serviço não é uma
tarefa de infraestrutura com um pouco de código — é uma **mudança de modelo de
dados** com infraestrutura em volta.

---

## 39.2 Decisões de escopo

| Decisão | Escolha | Consequência principal |
|---|---|---|
| Hospedagem | **VPS único com Docker Compose** | Volume persistente para PDFs resolvido de graça; operação e backup são responsabilidade sua; região do VPS vira questão de LGPD (§39.7) |
| Modelo de conta | **Individual** — projeto pertence a um usuário | Titularidade resolve-se com uma coluna e uma dependência de router; colaboração fica para v2 |
| Chaves de IA | **BYOK** — do próprio assinante | Custo variável zero para você; a transferência internacional continua sendo decisão informada do usuário; exige tornar as chaves *por usuário*, hoje globais |
| Cobrança | **Depois** — v1 gratuita/por convite | O Bloco J inteiro do checklist LGPD sai do caminho crítico; sem CPF, sem nota fiscal, sem antifraude, sem PCI-DSS |

A combinação é feliz: as duas decisões que mais aliviam a carga jurídica (BYOK
e cobrança adiada) são também as que reduzem o custo operacional. O que sobra é
trabalho de engenharia, e é o que este documento mede.

---

## 39.3 Achados de arquitetura

Cada achado tem evidência, o efeito concreto quando houver mais de um usuário,
e a fase do doc 41 que o fecha.

### A — Isolamento e titularidade

| # | Achado | Evidência | Efeito com dois assinantes | Fase |
|---|---|---|---|---|
| **O-01** | Projeto sem dono; nenhuma rota filtra por usuário | `models.py:47`; `api/v1/projects.py:33,76,88,110` | A entra na URL do projeto de B e lê o acervo inteiro — ou o apaga | **1** |
| **O-02** | Configuração de IA é uma linha global | `api/v1/ai.py:101,122,200,220,245,270`; `factory.py:25`; `profile_service.py:67,227,281,493` | A chave de A é usada e vista por B; salvar sobrescreve a do outro | **1** |
| **O-03** | Credencial de base científica é global por `source_name` | `models.py:389` | Token institucional de A serve a B — e viola o contrato de licença da base | **1** |
| **O-04** | `require_owner` protege as rotas de credencial | `security/dependencies.py`, `api/v1/settings.py:35`, `api/v1/ai.py` | Em serviço com contas individuais, **todo** assinante precisa gerir as próprias chaves; `owner` deixa de ser o critério certo — passa a ser "dono do recurso" | **1** |
| **O-05** | Exportação e importação de perfil operam sobre o banco inteiro | `services/profile_service.py`; `api/v1/profile.py:99,126` | `POST /profile/import` de um assinante sobrescreve dados de todos | **1** |

> **O-01 é o bloqueante crítico** (é o `L-46` do doc 38). Publicar sem ele para
> dois assinantes é entregar o acervo de um ao outro — e, como o RSAC será
> **operador**, é vazamento entre controladores distintos.

**A boa notícia estrutural.** Todo router com escopo de projeto já carrega
`/projects/{project_id}` no próprio prefixo:

```
deduplication  /projects/{project_id}/deduplicate
export         /projects/{project_id}/export
extraction     /projects/{project_id}/papers/{paper_id}/extraction
               /projects/{project_id}/extraction
harvest        /projects/{project_id}/harvest
insights       /projects/{project_id}/insights
papers         /projects/{project_id}/papers
protocols      /projects/{project_id}/protocol
screening_ai   /projects/{project_id}/screening/ai
```

Isso permite repetir exatamente a jogada que já deu certo com a autenticação: a
verificação entra como **dependência do router**, não como linha repetida em
cada rota. Uma rota nova nasce isolada, e esquecer deixa de ser possível. O
desenho está em §40.3.

### B — Persistência

| # | Achado | Evidência | Efeito | Fase |
|---|---|---|---|---|
| **O-06** | Não há Alembic configurado, apesar de estar nas dependências | `pyproject.toml` traz `alembic>=1.14.0`; não existe `backend/alembic/` | Não há como evoluir esquema em produção sem risco de perda | **0** |
| **O-07** | O esquema evolui por `create_all` + `ALTER TABLE` caseiro | `database.py:_migrate_missing_columns` | Só adiciona coluna: não renomeia, não altera tipo, não preenche dado, não reverte. Numa base com dados de terceiros, é inaceitável | **0** |
| **O-08** | O engine é SQLite por construção | `database.py:22-27` — `connect_args={"check_same_thread": False, "timeout": 30}` | Esses argumentos quebram em PostgreSQL; precisam ser derivados do dialeto | **0** |
| **O-09** | PRAGMAs de SQLite num listener global de `connect` | `database.py:30-39` | Em PostgreSQL, o listener falha em toda conexão nova | **0** |
| **O-10** | Datas gravadas *naive*, com conversão manual na fronteira | `security/sessions.py:_naive_utc`; `models.py` usa `DateTime` sem `timezone=True` | Em PostgreSQL o certo é `timestamptz`; migrar sem cuidado desloca expiração de sessão e retenção | **0** |
| **O-11** | SQLite com WAL num único arquivo | `database.py:33` | Aceitável em desktop; em servidor com escritas concorrentes de coleta e triagem, vira contenção e ponto único de corrupção | **0** |

### C — Concorrência e processos

| # | Achado | Evidência | Efeito | Fase |
|---|---|---|---|---|
| **O-12** | Jobs de coleta vivem na memória do processo | `services/harvest_job_manager.py:25` — `_active_tasks: Dict[str, asyncio.Task]` | Com mais de um *worker* uvicorn, o job criado no worker A é invisível ao B: "cancelar" não cancela e "status" mente | **4** |
| **O-13** | O WebSocket de progresso também é por processo | `api/v1/harvest.py:315`; `api/v1/screening_ai.py:106` | O navegador pode conectar num worker que não tem o job — a barra de progresso fica parada com o trabalho rodando | **4** |
| **O-14** | Reconciliação de jobs no `lifespan` marca **todos** os `running` como falhos | `main.py:129-146` | Correto com um processo; com vários, o worker que sobe mata o job vivo de outro | **4** |
| **O-15** | Limite de taxa contado em memória | `security/middleware.py:109` — `dict` por processo | Com N workers, o limite efetivo é N vezes maior; reiniciar zera | **4** |

> **Consequência de desenho, não defeito:** para a v1, a resposta certa é
> **um único worker** com escala vertical, e não uma fila. §40.6 mostra a
> conta que sustenta isso e o gatilho que obriga a mudar.

### D — Identidade

| # | Achado | Evidência | Efeito | Fase |
|---|---|---|---|---|
| **O-16** | Não há login com Google nem qualquer OAuth | `api/v1/auth.py` — só `login`, `local` e `status` | Cadastro por senha é atrito alto no público acadêmico e joga sobre você a guarda de senhas que o Google já faz melhor | **2** |
| **O-17** | `UserModel` não tem e-mail, nome nem identificador externo | `models.py:318-333` | Sem e-mail não há como responder a titular, recuperar conta, nem vincular a identidade do Google | **2** |
| **O-18** | `password_hash` é `nullable=False` | `models.py` | Conta criada por Google não tem senha; a coluna precisa aceitar ausência **e** o login por senha precisa recusar hash vazio | **2** |
| **O-19** | Não há autocadastro; contas só nascem por CLI | `app/cli.py`, `create-user` | É a postura certa hoje. Num serviço aberto, precisa de autocadastro **que jamais conceda `owner`** | **2** |
| **O-20** | O limitador de taxa não conhece rotas de OAuth | `security/middleware.py:83-92` — `_familia_da_rota` casa `/auth/login` e `/auth/local` | A rota nova de OAuth cairia na família `geral` (300/min), não em `auth` (10/15min) | **2** |

### E — Operação

| # | Achado | Evidência | Efeito | Fase |
|---|---|---|---|---|
| **O-21** | Log em `FileHandler` sem rotação | `main.py:44-56` | Enche o disco do VPS; e é o `L-32` do doc 38 (retenção) | **3** |
| **O-22** | Não há verificação de saúde profunda | `main.py:262`, `api/v1/router.py:43` — `/health` responde `"database": "connected"` **sem consultar o banco** | O monitor externo diz "no ar" com o Postgres caído | **6** |
| **O-23** | Não há backup, nem procedimento de restauração | ausência | Um disco perdido apaga o trabalho de revisão de todos os assinantes | **4** |
| **O-24** | Não há métrica nem alerta de disco | ausência | PDFs crescem sem teto; o serviço morre por disco cheio sem aviso | **6** |
| **O-25** | Não há teto de armazenamento por conta | `services/pdf_service.py` | Um assinante pode consumir o disco inteiro do VPS | **4** |
| **O-26** | `max_upload_mb: 100` é global e generoso | `config.py` | Combinado com O-25, é o vetor de esgotamento mais barato | **4** |

### F — Cliente e distribuição

| # | Achado | Evidência | Efeito | Fase |
|---|---|---|---|---|
| **O-27** | Não existe landing page | `frontend/src/pages/` só tem telas de aplicação | A raiz do domínio hoje serve a SPA ou o cartão de fallback do backend (`main.py:302-330`) | **5** |
| **O-28** | O backend serve a SPA no *catch-all* | `main.py:288-301` | Funciona, mas põe o Python no caminho de todo arquivo estático; num VPS, isso é trabalho do Caddy | **4/5** |
| **O-29** | A SPA descobre o backend por `sessionStorage` e query string | `frontend/src/api/client.ts:99-170`, `api/backendUrl.ts` | Desenho correto para o desktop; em produção a origem é fixa e essa flexibilidade vira superfície desnecessária | **5** |
| **O-30** | O app de mesa precisa continuar funcionando | `Iniciar_RSAC.bat`, `scripts/launcher.py`, `electron-vite` | Nenhuma mudança pode quebrar o perfil `desktop` — é o produto que já existe e tem usuários | **todas** |

---

## 39.4 O que a mudança de perímetro faz com a LGPD

O doc 37 já mediu isso; aqui fica só o que as decisões de §39.2 alteram.

**O que sai do caminho crítico** (por adiar a cobrança): Bloco J inteiro
(L-72 a L-77), coleta de CPF, nota fiscal, retenção fiscal de 5 anos,
antifraude e a decisão automatizada do art. 20 sobre recusa de pagamento
(L-82). São **onze** itens do checklist que passam a ser trabalho futuro.

**O que continua exigível, e vira portão de publicação:**

| Item do doc 38 | O que é | Fase |
|---|---|---|
| **L-46** | Isolamento entre assinantes | 1 |
| **L-12** | Aviso de privacidade acessível | 3/5 |
| **L-17, L-18, L-22** | Canal e rotas de direitos do titular | 3 |
| **L-24** | Eliminação alcança os PDFs no disco | 3 |
| **L-30, L-32** | Expurgo de IP e rotação de log | 3 |
| **L-34** | Eliminação propagada ao backup | 4 |
| **L-37** | Salvaguarda de transferência internacional | 3 |
| **L-49** | Acervo cifrado em repouso no servidor | 4 |
| **L-60** | Registro das operações de tratamento | 3 |
| **L-67** | Plano de resposta a incidente | 6 |
| **L-04, L-85** | Termos com cláusula de operador | 📄 jurídico |

**O que o BYOK muda a seu favor.** Mantendo a chave com o assinante, quem
decide enviar título e resumo ao Google continua sendo ele, com a chave dele —
você permanece intermediário técnico, não o responsável pela transferência.
Isso **não** dispensa L-37: o aviso de privacidade tem de dizer, de forma
destacada, para onde o conteúdo vai quando a IA é acionada, e a interface tem
de deixar claro que aquilo sai do país (art. 33, VIII). Mas dispensa as
cláusulas-padrão contratuais com Google e Alibaba, que seriam sua obrigação se
a chave fosse da plataforma.

**O que o login com Google acrescenta.** Você passa a receber do Google o
`sub`, o e-mail, o nome e a foto. Aí você é **controlador** desses dados, com
base no art. 7º, V (execução de contrato). Precisa constar do aviso, e a foto —
que não serve a nada no produto — é o exemplo canônico de dado a **não**
coletar (art. 6º, III). §40.4 trata disso no desenho.

---

## 39.5 Região do servidor: o detalhe que quase todo mundo erra

Um VPS na Alemanha ou na Finlândia é a opção mais barata do mercado. E é uma
**transferência internacional de dados pessoais** (art. 5º, XV), porque os dados
passam a ser armazenados fora do território nacional.

A intuição de que "a Europa tem GDPR, então está resolvido" **não funciona sob
a LGPD**. O art. 33, I exige que o país proporcione grau de proteção adequado
"ao previsto nesta Lei" — e essa adequação depende de reconhecimento formal
pela ANPD, que até aqui não foi concedido a nenhum país. Hospedar na União
Europeia, portanto, ainda exige uma hipótese do art. 33: na prática, as
**cláusulas-padrão contratuais** (art. 33, II, "b") no contrato com o provedor.

Isso não proíbe hospedar fora — apenas custa um contrato a mais e uma linha a
mais no aviso de privacidade. As duas saídas:

| Caminho | Custo | Obrigação |
|---|---|---|
| **VPS em região brasileira** — Vultr (São Paulo), Magalu Cloud, Locaweb, Oracle Cloud (São Paulo) | Um pouco mais caro que Hetzner | Nenhuma obrigação de art. 33. Latência menor para o público-alvo. **Recomendado** |
| **VPS fora do Brasil** — Hetzner, DigitalOcean | Mais barato | Assinar as cláusulas-padrão/DPA do provedor, arquivar o documento e declarar a transferência no aviso de privacidade (L-37, L-38) |

A recomendação é a primeira, e não por rigor jurídico: **o público do RSAC é
brasileiro**, e latência de rede aparece em cada requisição de triagem. A
conformidade vem junto de graça.

---

## 39.6 O que já está pronto e não precisa ser refeito

Vale registrar, porque é bastante — e porque o plano de execução se apoia
inteiro nisso:

| Peça | Onde | Serve ao serviço online? |
|---|---|---|
| Perfis de implantação (`desktop`/`server`/`ci`) | `config.py` | ✅ A abstração inteira |
| Partida segura: recusa subir em `server` sem conta | `main.py:117-127` | ✅ |
| Chave-mestra obrigatória em `server` | `main.py:88-99`; `security/crypto.py` | ✅ |
| Sessões com estado, token só em hash, revogação | `security/sessions.py` | ✅ Base do login com Google |
| Argon2id + política de 12 caracteres | `security/passwords.py` | ✅ |
| Limite de força bruta persistido | `security/sessions.py`; `models.py:366` | ✅ |
| Autenticação por padrão no router agregador | `api/v1/router.py:39` | ✅ O padrão que a titularidade vai copiar |
| Cifra de segredos em coluna | `security/encrypted_type.py` | ✅ |
| Mascaramento de credencial nas respostas | `security/masking.py` | ✅ |
| Filtro de segredos no log | `security/log_filter.py` | ✅ |
| Guarda de saída (SSRF, *DNS rebinding*, redirecionamento) | `security/egress.py` | ✅ Mais importante ainda em servidor |
| Cabeçalhos, CSP, HSTS | `security/middleware.py:33-69` | ✅ |
| Confinamento de caminho | `main.py:182-203` | ✅ |
| CORS derivado do perfil | `main.py:233-248` | ✅ |
| Autenticação de WebSocket com verificação de `Origin` | `security/dependencies.py` | ✅ |
| Suíte de segurança (12 arquivos) + CI | `backend/tests/test_security/`, `.github/workflows/ci.yml` | ✅ O portão onde as novas suítes entram |
| Design system com WCAG 2.1 AA e 13 paletas | `frontend/src/styles/globals.css` | ✅ Base da landing page |
| Marca com fonte única de verdade | `brand/` | ✅ |

**Conclusão do inventário:** a camada de segurança de perímetro está pronta e é
de boa qualidade. O trabalho que falta é de **modelo de dados**
(titularidade, identidade, persistência), **operação** (infra, backup,
observabilidade) e **produto** (landing, direitos do titular). Nenhum deles
exige desmontar o que existe.

---

## 39.7 Estimativa de esforço e risco

| Fase | Conteúdo | Esforço | Risco de regressão |
|---|---|---|---|
| **0** | Alembic + PostgreSQL | 3–5 dias | **Alto** — toca o esquema inteiro |
| **1** | Titularidade e isolamento | 4–6 dias | **Alto** — toca todas as rotas |
| **2** | Login com Google | 3–4 dias | Médio |
| **3** | LGPD no código | 4–6 dias | Baixo |
| **4** | Infraestrutura, backup, deploy | 4–6 dias | Médio |
| **5** | Landing page | 3–5 dias | Nenhum — código novo e isolado |
| **6** | Observabilidade e operação | 2–3 dias | Baixo |
| **7** | Endurecimento e portão de publicação | 3–4 dias | — |

**Total: 26 a 39 dias de trabalho focado.** A ordem não é negociável nas três
primeiras: Alembic antes de tudo (sem migração versionada, todo o resto vira
dívida), titularidade antes de identidade (não faz sentido deixar entrar quem
não terá acervo isolado), e as duas antes da infraestrutura (subir o servidor
com o modelo errado significa migrar dado real depois).

**Riscos que merecem nome:**

- **Migração SQLite → PostgreSQL com dado real.** Bases de desktop existentes
  precisam de caminho de importação. Mitigação: o `/profile/export` já
  existente vira a ponte oficial (§40.2.4).
- **Quebrar o perfil `desktop`.** A CI precisa rodar as duas configurações;
  hoje roda só `ci`. Mitigação em Fase 0.
- **`timestamptz` deslocando expiração de sessão.** Mitigação: teste dedicado
  que cria sessão, avança o relógio e confere a expiração nos dois bancos.
- **Um worker só ser insuficiente.** Mitigação: métrica de saturação desde a
  Fase 6 e gatilho escrito (§40.6) para mover jobs a uma fila.
