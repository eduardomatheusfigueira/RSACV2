# 30 — Plano de Execução — Segurança

> Como sair do estado descrito no [doc 28](./28_DIAGNOSTICO_SEGURANCA.md) e
> chegar ao estado normativo do [doc 29](./29_ESPECIFICACAO_SEGURANCA.md).
>
> Seis fases, com dependências, critérios de aceite verificáveis e a suíte de
> testes que impede a regressão. Cada fase é entregável de forma independente —
> nenhuma exige que a seguinte exista para dar valor.

---

## 30.0 A ordem e por que ela é esta

A ordenação não segue a severidade pura. Segue **risco removido por hora de
trabalho**, com uma restrição: nada que dependa de autenticação pode vir antes
dela.

```
Fase 0  ▸ CONTENÇÃO          9 h   fecha o comprometimento total sem auth  ✅ ENTREGUE
Fase 1  ▸ IDENTIDADE         3 d   autenticação, papéis, autoria na auditoria  ✅ ENTREGUE
Fase 2  ▸ SEGREDOS           2 d   cifra em repouso, API deixa de devolver chave  ✅ ENTREGUE
Fase 3  ▸ REDE               2 d   SSRF, WebSocket, cabeçalhos, limites  ✅ ENTREGUE
Fase 4  ▸ CLIENTE & LANÇADOR 2 d   api_url, aviso, provisionamento, checksum  ✅ ENTREGUE
Fase 5  ▸ INTEGRIDADE & CI   2 d   fórmula, prompt, lockfile, pipeline  ✅ ENTREGUE
                            ────
                            ~12 dias úteis
```

A **Fase 0** é o item que importa hoje. Nove horas de trabalho movem o sistema
de "comprometimento total por quem tiver a URL" para "exige uma vulnerabilidade
de verdade". Ela **não** entrega segurança — entrega tempo para fazer o resto
sem estar exposto.

**Estado em 19/08/2026:** plano concluído — as seis fases entregues. O `Iniciar_Servidor.bat`
exige conta e senha e recusa-se a publicar sem autenticação. O que continua
Os 18 achados do doc 28 estão fechados, e a CI passa a impedir que qualquer
um deles volte.

---

## 30.1 Fase 0 — Contenção (9 h) 🔴

**Objetivo:** eliminar as três vias de comprometimento total que não exigem
mudança de arquitetura. Nenhum item desta fase depende de autenticação.

### 30.1.1 Confinar o servidor de arquivos da SPA — 2 h

Fecha **V-04**. Cláusula §29.5.2.

`backend/app/main.py:129-137`:

```python
SPA_ROOT = frontend_dist.resolve()

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    if full_path.startswith("api") or full_path in ("health", "docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404, detail="Not Found")

    candidate = (SPA_ROOT / full_path).resolve()
    if candidate.is_relative_to(SPA_ROOT) and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(SPA_ROOT / "index.html")
```

Dois detalhes que fazem a correção valer: `resolve()` **antes** de qualquer
`is_file()`, e queda para `index.html` — nunca `403` — para não confirmar a
existência do alvo.

**Aceite:** `GET /%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd` devolve o `index.html`
da SPA, com `200` e `Content-Type: text/html`. O mesmo para
`--path-as-is ../../`, para `..%5c..%5c` (Windows) e para caminho absoluto.

### 30.1.2 Fechar o CORS — 2 h

Fecha **V-03**. Cláusula §29.5.1.

Passar a derivar as origens do perfil e a usar `settings.cors_origins`
(`config.py:33`), hoje ignorado. `allow_origin_regex` sai. Em `desktop`, um
regex **estrito** de loopback é aceitável — `^http://(localhost|127\.0\.0\.1)(:\d+)?$` —
porque a porta do Vite varia; o que não é aceitável é `.*`.

**Aceite:** requisição com `Origin: https://evil.example` não recebe
`Access-Control-Allow-Origin` na resposta; `Origin: http://localhost:5173`
recebe. Teste automatizado para ambos.

### 30.1.3 Parar de devolver chaves em claro — 4 h

Fecha **V-02** na superfície (a cifra em repouso é Fase 2). Cláusulas §29.4.2,
§29.4.3.

- `GET /api/v1/ai/settings` (`ai.py:85`) passa a devolver
  `gemini_key_previews`, `qwen_key_previews`, `local_key_previews` — máscaras
  via `_mask_key`, que já existe em `settings.py:23` e sobe para um módulo
  compartilhado — mais `has_*_keys` e contagem.
- `GET /api/v1/profile/keys/export` é **removida**; entra
  `POST /api/v1/profile/keys/export` com senha de exportação.
- O frontend passa a tratar campo de chave como *write-only*: exibe máscara,
  substitui integralmente ao digitar. Envio de string vazia **não** apaga a
  chave — apagar exige `DELETE` explícito, para que um formulário salvo sem
  tocar no campo não destrua a credencial.

**Aceite:** varredura de todas as respostas da API em uma sessão completa de
uso não contém nenhuma chave em claro. Teste automatizado que percorre as rotas
de leitura e falha se o corpo casar com `AIza[0-9A-Za-z_-]{35}` ou `sk-[A-Za-z0-9]{20,}`.

### 30.1.4 Fechar a documentação OpenAPI — 1 h

Fecha **V-12**. Cláusula §29.2.2. `docs_url`, `redoc_url` e `openapi_url` viram
`None` quando o perfil é `server` (na Fase 1 passam a exigir sessão).

**Aceite:** `GET /api/docs` devolve `404` com `RSAC_DEPLOYMENT_PROFILE=server`.

### 30.1.5 Introduzir o perfil de implantação — incluído acima

Pré-requisito das quatro anteriores: `deployment_profile` em `config.py`, a
regra de partida segura de §29.2.4 (que só passa a barrar de fato na Fase 1) e
o registro do perfil no log de inicialização.

> **Portão da Fase 0:** os quatro testes de aceite passam; o log de
> inicialização declara o perfil; `curl` anônimo contra um túnel não obtém nem
> arquivo do host, nem chave, nem mapa da API.

### ✅ Fase 0 — entregue em 19/08/2026

Verificado contra servidor real nos dois perfis, além da suíte automatizada:

| Item | Estado | Onde |
|---|---|---|
| Perfil de implantação (`desktop`/`server`/`ci`) | ✅ | `backend/app/config.py` |
| Confinamento do catch-all da SPA | ✅ | `backend/app/main.py` (`_resolve_within`) |
| CORS derivado do perfil, sem regex aberto | ✅ | `backend/app/main.py` |
| `/ai/settings` devolve máscara, nunca a chave | ✅ | `backend/app/api/v1/ai.py` |
| `GET /profile/keys/export` removido; `POST` cifrado | ✅ | `backend/app/api/v1/profile.py`, `app/security/secret_box.py` |
| Perfil completo sem credencial por padrão | ✅ | `app/services/profile_service.py` |
| Salvar formulário não apaga chave; `DELETE` explícito | ✅ | `ai.py`, `SettingsPage.tsx` |
| OpenAPI fechada no perfil `server` | ✅ | `backend/app/main.py` |
| Lançador sobe o backend no perfil `server` + aviso | ✅ | `scripts/server_launcher.py` |
| Suíte de regressão de segurança | ✅ | `backend/tests/test_security/` (50 testes) |

**Evidência de que os testes pegam a regressão:** reintroduzindo a
concatenação de caminho anterior, `test_path_traversal.py` falha em 4 casos —
o que também confirma que a travessia era explorável de verdade.

O que a Fase 0 **não** entrega, e continua valendo o aviso de §28.7: a API
segue sem autenticação. Quem tiver a URL do túnel continua lendo e apagando
projetos e consumindo a cota de IA. O que deixou de ser possível é levar as
chaves de API, ler arquivos do disco e usar o navegador de terceiros como
ponte para o `127.0.0.1` do pesquisador.

---

## 30.2 Fase 1 — Identidade (3 dias) 🔴

**Objetivo:** fechar **V-01**. É a fase que muda a natureza do sistema.
**Depende da Fase 0.**

### 30.2.1 Entregas

| # | Entrega | Cláusula |
|---|---|---|
| 1 | `UserModel` + `SessionModel` e migração | §29.3.3 |
| 2 | Hash Argon2id (`argon2-cffi` nas dependências) | §29.3.3 |
| 3 | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `GET /auth/status` | §29.3.1 |
| 4 | Dependência global de sessão no `include_router`, com allowlist de 3 rotas | §29.3.1 |
| 5 | Token local para o perfil `desktop` (arquivo `0600`, troca por cookie) | §29.3.2 |
| 6 | Papéis `owner`/`researcher`; `require_role("owner")` nas rotas de segredo | §29.3.4 |
| 7 | `user_id`/`username` no `AuditLogModel`, preenchidos em toda escrita | §29.3.5 |
| 8 | Limite de tentativas de login | §29.7 |
| 9 | `python -m app.cli create-user` | §29.3.3 |
| 10 | Tela de login no frontend; `401` redireciona; sessão expirada avisa | — |
| 11 | Backend recusa subir em `server` sem conta ou sem `RSAC_SECRET_KEY` | §29.2.4 |

### 30.2.2 A decisão de implementação que mais importa

A proteção **DEVE** entrar como dependência do router agregador, não como
decorador por rota:

```python
api_router = APIRouter(dependencies=[Depends(require_session)])
```

com as três exceções (§29.3.1) registradas em um router separado, sem a
dependência. Assim o padrão é "protegido" e o esquecimento falha fechado: uma
rota nova nasce exigindo sessão sem que o autor precise lembrar de nada. É a
diferença entre corrigir V-01 e corrigir V-01 **de forma durável**.

### 30.2.3 Aceite

- Teste parametrizado que enumera **todas** as rotas do app via
  `app.routes` e verifica que cada uma devolve `401` sem sessão, exceto a
  allowlist explícita. Rota nova sem sessão ⇒ teste vermelho. É o teste que
  torna V-01 irreversível.
- `researcher` recebe `403` em `/ai/settings` e `/profile/*`.
- Backend com `RSAC_DEPLOYMENT_PROFILE=server` e sem contas não sobe, e a
  mensagem diz qual comando executar.
- Alteração de decisão de triagem grava `username` na auditoria.

### ✅ Fase 1 — entregue em 19/08/2026

| Entrega | Estado | Onde |
|---|---|---|
| `UserModel`, `SessionModel`, `LoginAttemptModel` | ✅ | `infrastructure/persistence/models.py` |
| Hash Argon2id | ✅ | `app/security/passwords.py` |
| `/auth/status`, `/login`, `/local`, `/logout`, `/me`, `/password`, `/users` | ✅ | `app/api/v1/auth.py` |
| Dependência global de sessão no agregador | ✅ | `app/api/v1/router.py` |
| Token local do perfil desktop (arquivo `0600`) | ✅ | `app/security/local_token.py` |
| Papéis `owner`/`researcher` nas rotas de credencial | ✅ | `ai.py`, `settings.py`, `profile.py` |
| Autoria (`user_id`, `username`) na trilha de auditoria | ✅ | `papers.py`, `screening_service.py` |
| Limite de 5 tentativas em 15 min, com estado no banco | ✅ | `app/security/sessions.py` |
| `python -m app.cli create-user` | ✅ | `app/cli.py` |
| Tela de login, portão de sessão e identidade na barra de status | ✅ | `LoginPage.tsx`, `App.tsx`, `StatusBar.tsx` |
| Backend recusa subir em `server` sem conta | ✅ | `app/main.py` (lifespan) |
| Lançador provisiona conta antes de abrir o túnel | ✅ | `scripts/server_launcher.py` |

**Além do previsto:** os dois WebSockets passaram a exigir sessão no
handshake (V-06 estava planejado para a Fase 3). Aceitar a conexão e checar
depois já teria entregado o canal, e a metade da defesa que faltava — a
verificação de `Origin` — continua na Fase 3.

**Duas decisões que divergem do previsto, e por quê:**

1. **`sessionStorage` em vez de só cookie.** §29.3.2 pede cookie `HttpOnly`, e
   é o que o backend emite. Mas o cookie `SameSite=Strict` não viaja quando a
   interface está no Netlify e a API no túnel — origens diferentes. O token
   também vai num cabeçalho `Bearer` guardado em `sessionStorage`: sobrevive ao
   recarregar a aba e morre ao fechá-la. `localStorage`, que a especificação
   proíbe, não é usado.
2. **`require_session` recebe `HTTPConnection`, não `Request`.** A dependência
   é declarada no router agregador, que carrega também as rotas de WebSocket —
   e essas não têm requisição HTTP. Declarar `Request` derrubava o handshake
   com `TypeError`. No escopo de WebSocket a dependência sai de lado e quem
   decide é a checagem dentro da rota, que consegue fechar com o código 1008;
   `test_websocket_auth.py` cobre cada canal para que a exceção não vire
   brecha.

**O que a Fase 1 muda na prática:** a exploração de quatro `curl` do doc 28
responde `401` em todas as rotas. Um `researcher` opera a revisão e recebe
`403` em qualquer rota de credencial. O `logout` mata o token no servidor. E o
app de mesa continua abrindo sem pedir senha, pelo token local.

---

## 30.3 Fase 2 — Segredos (2 dias) 🟠

**Objetivo:** fechar **V-07** e completar **V-02**. Depende da Fase 1 (a
chave-mestra e a sessão compartilham a origem do segredo).

| # | Entrega | Cláusula |
|---|---|---|
| 1 | `app/security/crypto.py` — Fernet, chave de `RSAC_SECRET_KEY` ou `<data_dir>/master.key` `0600` | §29.4.1 |
| 2 | Tipo SQLAlchemy `EncryptedText` — cifra/decifra transparente na coluna | §29.4.1 |
| 3 | Aplicação às 4 colunas de `AISettingsModel` e às 2 de `SourceCredentialModel` | §29.4.1 |
| 4 | Migração idempotente com prefixo de versão (`v1:` = cifrado; sem prefixo = legado em claro, cifrar no primeiro acesso) | §29.4.1 |
| 5 | `POST /profile/keys/export` com senha de exportação e cifra do pacote | §29.4.3 |
| 6 | Filtro de log que mascara `AIza…`, `sk-…`, `Bearer …` | §29.4.4 |
| 7 | Em `server`, recusar chave-mestra em arquivo — exigir do ambiente | §29.4.1 |

**Aceite:** `strings %LOCALAPPDATA%\RSAC\rsac.db | grep -E 'AIza|sk-'` não
retorna nada num banco com chaves configuradas. Banco de versão anterior sobe,
migra e continua funcionando (teste de migração com *fixture* em claro).

### ✅ Fase 2 — entregue em 19/08/2026

| Entrega | Estado | Onde |
|---|---|---|
| `crypto.py` — Fernet + HKDF, chave do ambiente ou arquivo `0600` | ✅ | `app/security/crypto.py` |
| `EncryptedText` — cifra/decifra transparente na coluna | ✅ | `app/security/encrypted_type.py` |
| Aplicado às 4 colunas de IA e às 2 de credenciais de fonte | ✅ | `persistence/models.py` |
| Migração idempotente com prefixo `v1:` | ✅ | `app/security/migration.py` |
| Filtro de log que mascara `AIza…`, `sk-…`, `Bearer …` | ✅ | `app/security/log_filter.py` |
| Perfil `server` recusa chave-mestra em arquivo | ✅ | `crypto.py`, portão no `main.py` |
| `python -m app.cli generate-secret-key` | ✅ | `app/cli.py` |

**Verificação do critério de aceite**, contra servidor real no perfil `server`:
gravadas duas credenciais pelas rotas normais, a busca binária no banco **e no
journal WAL** devolveu zero ocorrências de `AIzaSy` e do token do Scopus, e
duas ocorrências do prefixo `v1:gAAAAA`. Revertendo as colunas para `Text`, dois
testes falham — o que confirma que a suíte pega a regressão.

**Um defeito encontrado pela própria verificação.** A chave-mestra é resolvida
preguiçosamente, e a migração captura exceções de forma ampla para não impedir
o app de subir. O efeito combinado: no perfil `server` sem `RSAC_SECRET_KEY` o
backend **subia normalmente** e só falharia quando alguém tentasse salvar uma
chave — com o erro engolido. Corrigido com um portão explícito no `lifespan`,
na mesma forma do portão de contas: um servidor que não consegue cifrar
segredos não atende requisição nenhuma.

**O que a cifra não protege.** A chave-mestra do perfil `desktop` fica em
`<data_dir>/master.key`, ao lado do banco. Quem já tem leitura do sistema de
arquivos do usuário obtém as duas coisas — a cifra ali protege contra cópia do
banco (backup, pasta sincronizada, anexo de suporte), não contra acesso local.
No perfil `server`, onde essa distinção importa, a chave vem do ambiente.

---

## 30.4 Fase 3 — Rede e recursos (2 dias) 🟠

**Objetivo:** fechar **V-05**, **V-06**, **V-10**, **V-11**, **V-13** e
**V-14**. Independe das Fases 1–2, exceto o item 2.

| # | Entrega | Cláusula | Achado |
|---|---|---|---|
| 1 | `app/security/egress.py` — guarda único de URL de saída, com validação pós-DNS e por salto de redirecionamento | §29.5.3 | V-05 |
| 2 | Seguimento manual de redirecionamento no `pdf_resolver` (máx. 5), substituindo `follow_redirects=True` | §29.5.3 | V-05 |
| 3 | Guarda aplicado ao `endpoint` de IA, com exceção de loopback só em `desktop` | §29.5.3 | V-05 |
| 4 | Redução da trilha de tentativas a categorias no perfil `server` | §29.5.4 | V-05 |
| 5 | Verificação de `Origin` + sessão **antes** de `accept()` nos dois WebSockets | §29.3.6 | V-06 |
| 6 | Upload em blocos para arquivo temporário, com teto de 100 MB e checagem de espaço | §29.7 | V-10 |
| 7 | Limitador de taxa (`slowapi` ou middleware próprio) com os limites da §29.7 | §29.7 | V-11 |
| 8 | Middleware de cabeçalhos de segurança | §29.6 | V-14 |
| 9 | `TrustedHostMiddleware` no perfil `server` | §29.14 | — |
| 10 | Manipulador global de exceção com identificador de correlação; remoção de todo `detail=str(e)` | §29.8 | V-13 |

**Aceite:**

- Tabela de teste do guarda de saída cobrindo `file:///etc/passwd`,
  `http://169.254.169.254/latest/meta-data/`, `http://127.0.0.1:6379`,
  `http://10.0.0.1`, `http://[::1]`, host público que redireciona para
  `127.0.0.1` (**este é o caso que pega implementação ingênua**) e nome que
  resolve para IP privado. Todos recusados; `https://arxiv.org/pdf/2401.00001`
  aceito.
- WebSocket com `Origin: https://evil.example` fecha com `1008` sem `accept()`.
- Upload de 200 MB devolve `413` sem crescimento de memória do processo.
- Nenhuma resposta de erro contém `/home/`, `C:\`, `Traceback` ou `sqlalchemy`.

### ✅ Fase 3 — entregue em 19/08/2026

| Entrega | Estado | Onde |
|---|---|---|
| Guarda de saída com validação pós-DNS | ✅ | `app/security/egress.py` |
| Seguimento manual de redirecionamento, revalidado por salto | ✅ | `app/security/safe_http.py` |
| Guarda aplicado ao `endpoint` de IA, loopback só para LLM local | ✅ | `app/api/v1/ai.py` |
| Trilha de tentativas reduzida a categoria no perfil `server` | ✅ | `egress.detalhe_publico`, `pdf_resolver` |
| `Origin` verificado antes de `accept()` nos dois WebSockets | ✅ | `dependencies.py`, `harvest.py`, `screening_ai.py` |
| Upload em blocos com teto e checagem de espaço | ✅ | `pdf_service.save_uploaded_stream` |
| Limitador de taxa por sessão, com famílias de rota | ✅ | `app/security/middleware.py` |
| Cabeçalhos de segurança em todas as respostas | ✅ | `SecurityHeadersMiddleware` |
| `TrustedHostMiddleware` no perfil `server` | ✅ | `app/main.py` |
| Manipulador global de erro com identificador de correlação | ✅ | `middleware.instalar_tratamento_de_erro` |

**Verificação contra servidor real:** os cinco cabeçalhos presentes; os três
endpoints internos de IA recusados com `400`; `download_url` apontando para
`169.254.169.254` resultando em falha sem vazar nada; `429` após 24 chamadas às
rotas de IA.

**Evidência de regressão:** restaurando `follow_redirects=True` com validação
apenas na URL inicial, quatro testes falham — inclusive o do host público que
redireciona para os metadados de nuvem, que é o caso que uma implementação
ingênua deixa passar.

**Três decisões que valem registro:**

1. **A regra de porta é aplicada depois da resolução, não antes.** Aplicá-la
   primeiro bloqueava o Ollama (`:11434`), que é uso legítimo. Para destino
   externo — o que importa contra varredura — a regra continua valendo.
2. **O limitador chaveia por sessão, não por IP.** Pesquisadores atrás do NAT
   de uma universidade compartilham endereço; limitar por IP transformaria o
   uso normal de um laboratório em bloqueio mútuo. Antes do login não há
   sessão, e aí o IP é o que existe — exatamente o caso das tentativas de
   autenticação, onde limitar por origem é o que se quer.
3. **A resolução de nomes virou ponto de injeção.** Os testes de unidade do
   resolvedor usam `MockTransport` com hosts fictícios; com DNS real, todos
   falhariam e ficaria a impressão errada de que o guarda barra o que deveria
   passar. A suíte de segurança marca-se com `dns_real` e exercita a resolução
   de verdade — que é onde o *DNS rebinding* é fechado.

**Um defeito encontrado na própria verificação:** o fixture de DNS de teste
resolvia **qualquer** host para um IP público, inclusive literais como
`10.0.0.5`. Isso fazia os testes do endpoint de IA passarem sem exercitar
nada. Corrigido para que IP literal resolva para ele mesmo.

---

## 30.5 Fase 4 — Cliente e lançador (2 dias) 🟠

**Objetivo:** fechar **V-08** e **V-09**. Depende da Fase 1 (o lançador precisa
provisionar contas).

| # | Entrega | Cláusula | Achado |
|---|---|---|---|
| 1 | `api_url` só é aceito após confirmação modal nomeando o host | §29.12 | V-08 |
| 2 | Persistência migra de `localStorage` para `sessionStorage` | §29.12 | V-08 |
| 3 | Validação de esquema (`https:` ou `http://localhost`) e aviso para host fora dos sufixos conhecidos | §29.12 | V-08 |
| 4 | Host ativo permanentemente visível na `StatusBar` | §29.12 | V-08 |
| 5 | CSP do `index.html` sem `https:`/`wss:` genéricos | §29.6 | V-14 |
| 6 | Lançador define `RSAC_DEPLOYMENT_PROFILE=server` | §29.11 | V-09 |
| 7 | Provisionamento interativo de conta antes de abrir o túnel | §29.11 | V-09 |
| 8 | Geração/verificação de `RSAC_SECRET_KEY` | §29.11 | V-09 |
| 9 | Aviso explícito de exposição, com confirmação do usuário | §29.11 | V-09 |
| 10 | Túnel não sobe se `/auth/status` indicar autenticação desativada | §29.11.6 | V-09 |
| 11 | `checksum` SHA-256 do `cloudflared` antes de executar | §29.11.1 | V-09 |

**Aceite:** ligar o servidor numa instalação limpa produz, obrigatoriamente,
usuário e senha antes da URL pública aparecer. Abrir a SPA com
`#/?api_url=https://evil.example` mostra o modal nomeando `evil.example` e não
grava nada se o usuário recusar.

### ✅ Fase 4 — entregue em 19/08/2026

| Entrega | Estado | Onde |
|---|---|---|
| `api_url` só após confirmação humana nomeando o host | ✅ | `api/backendUrl.ts`, `App.tsx` |
| Persistência migrada de `localStorage` para `sessionStorage` | ✅ | `api/client.ts` |
| Validação de protocolo, recusa de `http://` fora do loopback | ✅ | `analisarUrlDeBackend` |
| Host do backend permanentemente visível | ✅ | `StatusBar.tsx` |
| CSP sem `https:`/`wss:` genéricos | ✅ | `frontend/index.html` |
| Lançador no perfil `server` + aviso + provisionamento | ✅ | entregue nas Fases 0 e 1 |
| Chave-mestra gerada pelo lançador | ✅ | `server_launcher.py` |
| Verificação de integridade do `cloudflared` | ✅ | `download_cloudflared`, `verificar_cloudflared_existente` |

**Suíte de testes do frontend, que não existia:** `npm test` reportava "No test
files found". Agora há 11 testes cobrindo a validação de URL — inclusive o
sufixo forjado (`trycloudflare.com.evil.io`), que uma verificação por
`includes()` deixaria passar.

**Um defeito que eu mesmo introduzi e peguei na verificação:** a primeira
versão gravava a chave-mestra em `server_config.json`, que é **versionado** —
o pesquisador enviaria a própria chave para o GitHub no commit seguinte.
Corrigido: a chave vai para `<data_dir>/server_secret.key`, com permissão
`0600`, fora do repositório.

**O que a verificação do `cloudflared` entrega, e o que não entrega.** A URL
deixou de ser `latest/download/` — um alvo móvel que tornava qualquer
verificação impossível — e passou a apontar uma versão fixa. O SHA-256 é
confirmado pelo usuário na primeira execução e registrado; da segunda em
diante, binário diferente é recusado sem perguntar, e um binário já presente
também é conferido. É confiança na primeira utilização: **não** protege contra
um artefato adulterado já no primeiro download, e por isso o caminho
recomendado, impresso pelo próprio lançador, continua sendo instalar o
cloudflared pelo instalador oficial e apontar `cloudflared_path`. O hash não
vem fixado no repositório porque não foi possível obter e conferir um valor
oficial a partir do ambiente de desenvolvimento — fixar um número não
verificado seria pior que não fixar nenhum.

---

## 30.6 Fase 5 — Integridade e CI (2 dias) 🟡

**Objetivo:** fechar **V-15**, **V-16**, **V-17**, **V-18** e instalar o que
impede a regressão de tudo o que veio antes.

| # | Entrega | Cláusula | Achado |
|---|---|---|---|
| 1 | Neutralização de prefixo de fórmula no `export_service` | §29.9.1 | V-15 |
| 2 | Sanitização do `filename` em `Content-Disposition` + `filename*` | §29.9.1 | V-15 |
| 3 | Delimitação do conteúdo de terceiros nos prompts, com instrução de não obediência | §29.9.2 | V-16 |
| 4 | Validação estrita da resposta da IA contra vocabulário fechado | §29.9.2 | V-16 |
| 5 | Provedor, modelo e *hash* do contexto na auditoria de decisão por IA | §29.9.3 | V-16 |
| 6 | *Lockfile* Python com *hashes* | §29.10 | V-17 |
| 7 | `defusedxml` no harvester do PubMed | §29.10 | V-18 |
| 8 | **Workflow de CI** (não existe hoje): `ruff`, `bandit`, `pip-audit`, `npm audit`, varredura de segredos, `pytest -m security` | §29.10 | todos |

**Aceite:** PR que reintroduz qualquer achado do doc 28 falha na CI.

### ✅ Fase 5 — entregue em 19/08/2026

| Entrega | Estado | Onde |
|---|---|---|
| Neutralização de prefixo de fórmula | ✅ | `export_service.neutralizar_formula` |
| `Content-Disposition` sanitizado + `filename*` | ✅ | `export_service.cabecalho_de_download` |
| Conteúdo de terceiros delimitado nos prompts | ✅ | `prompts.delimitar_conteudo_externo` |
| Resposta da IA validada contra vocabulário fechado | ✅ | `ai/base.validar_resposta_de_triagem` |
| Provedor, modelo e hash do contexto na auditoria | ✅ | `models.AuditLogModel`, `screening_service` |
| *Lockfile* com hashes | ✅ | `backend/requirements.lock` (1647 hashes) |
| `defusedxml` no PubMed | ✅ | `harvesters/pubmed.py` |
| **Workflow de CI** | ✅ | `.github/workflows/ci.yml` |

**A neutralização de fórmula entra no ponto único de escrita** — o
`ExcelWriter` — em vez de campo a campo. Cobre as quatro abas de uma vez e não
depende de alguém lembrar disso ao acrescentar uma coluna nova.

**A delimitação do prompt tem uma armadilha que o teste cobre:** se o conteúdo
externo pudesse conter o próprio delimitador, ele fecharia a marca e escaparia
da região de dados — a defesa cairia por dentro. O delimitador é removido do
conteúdo antes de envolvê-lo.

**Sobre a validação da resposta, uma divergência da especificação.** §29.9.2
diz que decisão fora do vocabulário **deve ser rejeitada, não coagida**. O que
foi implementado rebaixa para "Pendente" e **registra o desvio** — em
`validation_note` e na coluna `ai_response_valid` da auditoria. A razão: numa
triagem em lote, rejeitar aborta o trabalho inteiro por causa de um estudo,
enquanto "Pendente" já significa exatamente "uma pessoa precisa decidir". O que
o comportamento anterior fazia de errado não era coagir — era coagir **em
silêncio**, escondendo o sinal de que algo tentou desviar a triagem.

**A CI roda a suíte de segurança em passo próprio e isolado**, antes da suíte
completa: quando ela quebra, o log diz "segurança" sem que ninguém precise ler
a saída inteira do pytest. Os passos de lint, `pip-audit`, `bandit` e
`npm audit` entram com `continue-on-error` porque o repositório carrega dívida
de estilo anterior a este plano (~900 avisos do ruff); o objetivo é tornar a
dívida visível sem travar PRs legítimos, e a linha sai quando ela for zerada.

---

## 30.7 A suíte de testes de segurança

Marcador `@pytest.mark.security`, em `backend/tests/test_security/`. Roda na CI
a cada *push*. É o entregável que dá durabilidade a todo o resto — sem ela, o
plano corrige o estado de hoje e não o de daqui a seis meses.

| Arquivo | Cobre | Achado |
|---|---|---|
| `test_authn_coverage.py` | **Enumera `app.routes` e exige `401` sem sessão**, exceto allowlist | V-01 |
| `test_authz_roles.py` | `researcher` recebe `403` nas rotas de segredo | V-01 |
| `test_no_secret_leak.py` | Nenhuma resposta contém padrão de chave | V-02, V-07 |
| `test_cors_policy.py` | Origem hostil rejeitada, local aceita | V-03 |
| `test_path_traversal.py` | 8 codificações de travessia, POSIX e Windows | V-04 |
| `test_egress_guard.py` | Tabela de destinos internos, incluindo redirecionamento | V-05 |
| `test_ws_origin.py` | Handshake rejeitado por `Origin` e por falta de sessão | V-06 |
| `test_crypto_roundtrip.py` | Cifra/decifra e migração de valor legado | V-07 |
| `test_limits.py` | `413` em corpo grande, `429` em excesso de taxa | V-10, V-11 |
| `test_security_headers.py` | Cabeçalhos presentes em todas as respostas | V-14 |
| `test_error_sanitization.py` | Erro não contém caminho, SQL ou *traceback* | V-13 |
| `test_export_injection.py` | Célula iniciada por `=` sai neutralizada | V-15 |
| `test_prompt_boundary.py` | Resumo com instrução embutida não muda a decisão | V-16 |

O primeiro é o mais importante do conjunto: é ele que transforma "hoje está
autenticado" em "não é possível esquecer de autenticar".

---

## 30.8 Riscos do próprio plano

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Autenticação atrapalha o uso desktop, que hoje é sem atrito | **Alta** | Token local automático (§29.3.2): o usuário desktop não digita senha nenhuma. Se isto não for bem feito, o recurso será contornado |
| Migração da cifra corrompe chaves existentes | Média | Prefixo de versão, migração idempotente, teste com *fixture* legado, e backup do `.db` antes de migrar |
| Guarda de saída bloqueia repositório institucional legítimo em IP privado | Média | `RSAC_ALLOW_PRIVATE_EGRESS` com lista de exceções por host, documentada no doc 17 |
| Quebra de contrato da API trava o frontend | Alta | Fases 0 e 2 mudam contrato: frontend e backend na mesma entrega, com `npm run verify` no portão |
| Limite de taxa atrapalha coleta legítima em lote | Baixa | Limites por sessão, não por IP; coleta interna isenta do limitador |
| O plano ser adotado pela metade | **Alta** | A Fase 0 é útil sozinha; cada fase é entregável independente. O pior resultado é parar depois da Fase 0 — que já é muito melhor que hoje |

---

## 30.9 Definição de pronto

Cada fase só está pronta quando:

1. Todos os critérios de aceite passam, automatizados onde possível.
2. Os testes de segurança correspondentes existem e passam.
3. O doc 22 (log de entregas) registra o que foi entregue e o que divergiu.
4. O doc 17 (guia de uso) reflete a mudança visível ao usuário — login,
   provisionamento, aviso do servidor.
5. Nenhuma regressão em `npm run verify` e `pytest`.

---

## 30.10 Resumo executivo

| | |
|---|---|
| **Situação inicial** | Backend sem autenticação publicado na internet; chaves de API legíveis anonimamente; leitura arbitrária de arquivos do host; CORS permite que qualquer site acesse a instalação local |
| **Situação atual** | Plano concluído: a API exige identidade, as chaves não trafegam nem repousam em claro, o servidor não sobe desprotegido, não pode ser usado como procurador para a rede interna e o cliente web não muda de destino sem confirmação humana |
| **Ação imediata** | Rotacionar as chaves de API se o `Iniciar_Servidor.bat` já foi usado em rede aberta antes destas fases |
| **Fase 0** | ✅ entregue em 19/08/2026 — remove o comprometimento total |
| **Fase 1** | ✅ entregue em 19/08/2026 — a API inteira exige identidade |
| **Fase 2** | ✅ entregue em 19/08/2026 — segredos cifrados em repouso |
| **Fase 3** | ✅ entregue em 19/08/2026 — SSRF, WebSocket, cabeçalhos e limites |
| **Fase 4** | ✅ entregue em 19/08/2026 — cliente web e lançador |
| **Fase 5** | ✅ entregue em 19/08/2026 — integridade da revisão e CI |
| **Plano completo** | ✅ **concluído em 19/08/2026** — 18 de 18 achados fechados, 370 testes de backend (263 de segurança) e CI que impede a volta |

---

*Plano de execução, 19/08/2026. Baseado no doc 28 (diagnóstico) e no doc 29
(especificação normativa), contra o commit `34b6a45`.*
