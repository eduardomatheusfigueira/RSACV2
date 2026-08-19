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
Fase 2  ▸ SEGREDOS           2 d   cifra em repouso, API deixa de devolver chave
Fase 3  ▸ REDE               2 d   SSRF, WebSocket, cabeçalhos, limites
Fase 4  ▸ CLIENTE & LANÇADOR 2 d   api_url, aviso, provisionamento, checksum
Fase 5  ▸ INTEGRIDADE & CI   2 d   fórmula, prompt, lockfile, pipeline
                            ────
                            ~12 dias úteis
```

A **Fase 0** é o item que importa hoje. Nove horas de trabalho movem o sistema
de "comprometimento total por quem tiver a URL" para "exige uma vulnerabilidade
de verdade". Ela **não** entrega segurança — entrega tempo para fazer o resto
sem estar exposto.

**Estado em 19/08/2026:** Fases 0 e 1 entregues. O `Iniciar_Servidor.bat`
exige conta e senha e recusa-se a publicar sem autenticação. O que continua
aberto está nas Fases 3 a 5 — SSRF, limites de recurso, cabeçalhos e a
sanitização das exportações.

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
| **Situação atual** | Fases 0 e 1 entregues: a API exige identidade, as chaves não trafegam em claro e o servidor não sobe desprotegido |
| **Ação imediata** | Rotacionar as chaves de API se o `Iniciar_Servidor.bat` já foi usado em rede aberta antes destas fases |
| **Fase 0** | ✅ entregue em 19/08/2026 — remove o comprometimento total |
| **Fase 1** | ✅ entregue em 19/08/2026 — a API inteira exige identidade |
| **Fase 2** | ~2 dias — cifra dos segredos em repouso |
| **Plano completo** | ~12 dias úteis — 18 de 18 achados fechados, com testes que impedem a volta |

---

*Plano de execução, 19/08/2026. Baseado no doc 28 (diagnóstico) e no doc 29
(especificação normativa), contra o commit `34b6a45`.*
