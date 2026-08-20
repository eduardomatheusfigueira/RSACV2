# 29 — Especificação de Segurança

> Documento **normativo**. Define o perímetro de confiança do RSAC V2, o modelo
> de autenticação e autorização, a proteção de segredos, a política de rede de
> saída e os contratos que o código passa a ser obrigado a respeitar.
>
> Responde ao [doc 28 — Diagnóstico de Segurança](./28_DIAGNOSTICO_SEGURANCA.md).
> A ordem de implementação está no [doc 30](./30_PLANO_EXECUCAO_SEGURANCA.md).
>
> Vocabulário RFC 2119: **DEVE** (obrigatório), **NÃO DEVE** (proibido),
> **DEVERIA** (recomendado forte), **PODE** (opcional).

---

## 29.1 O princípio que faltava

O diagnóstico mostrou que o RSAC V2 nunca declarou seu perímetro de confiança —
e por isso o perímetro mudou (de `localhost` para a internet) sem que nada no
código mudasse junto. Esta especificação existe para que isso não se repita:

> **§0 — Princípio do perímetro explícito.** O RSAC V2 DEVE saber, em tempo de
> execução, em qual perfil de exposição está rodando. Todo controle de
> segurança DEVE derivar desse perfil, e não de suposição implícita no código.
> O perfil DEVE aparecer no log de inicialização e na interface.

Disso decorre a decisão estruturante deste documento: **três perfis de
implantação**, com controles diferentes, e um só código servindo aos três.

---

## 29.2 Os três perfis de implantação

`RSAC_DEPLOYMENT_PROFILE` — enumeração fechada, sem valor padrão implícito.

### 29.2.1 `desktop` (padrão)

Electron ou navegador local falando com backend em loopback. É o modo de
sempre, e o padrão quando a variável não é informada.

| Controle | Valor |
|---|---|
| Bind | `127.0.0.1` — **NÃO DEVE** aceitar bind em `0.0.0.0` neste perfil |
| Autenticação | Token local obrigatório (§29.3.2) |
| CORS | Somente `http://localhost:*` e `http://127.0.0.1:*` |
| OpenAPI | Exposto |
| Rotas de segredo | Liberadas para o token local |

### 29.2.2 `server` — o perfil que o `Iniciar_Servidor.bat` passa a exigir

Backend publicado por túnel, Netlify ou rede local. É onde vale o regime
completo.

| Controle | Valor |
|---|---|
| Bind | Qualquer, mas **DEVE** haver proxy TLS à frente |
| Autenticação | Sessão com senha + contas nomeadas (§29.3.3) — **obrigatória** |
| CORS | Lista de permissão explícita e finita (§29.5.1) |
| OpenAPI | **DEVE** exigir autenticação |
| Segredos | Cifrados em repouso (§29.4); rotas de exportação exigem reautenticação |
| Limite de taxa | Obrigatório (§29.7) |
| Cabeçalhos | Conjunto completo, incluindo HSTS (§29.6) |

### 29.2.3 `ci`

Testes automatizados. Autenticação por token fixo de teste, banco efêmero,
rede externa bloqueada.

### 29.2.4 A regra de partida segura

> **§29.2.4** Se `RSAC_DEPLOYMENT_PROFILE` for `server` e não houver segredo de
> sessão nem nenhuma conta cadastrada, o backend **DEVE recusar-se a subir**,
> com mensagem acionável apontando o comando de provisionamento. Um servidor
> público sem autenticação **NÃO DEVE** ser um estado alcançável do sistema.

Esta é a cláusula mais importante do documento: ela torna a falha de V-01
**impossível de reintroduzir por omissão**.

---

## 29.3 Autenticação e autorização

### 29.3.1 Regra geral

> **§29.3.1** Toda rota HTTP e todo WebSocket **DEVEM** exigir uma identidade
> autenticada, com exatamente três exceções: `GET /health` (sem dados de
> negócio), `GET /api/v1/auth/status` (informa se há contas provisionadas) e
> `POST /api/v1/auth/login`.

A regra **DEVE** ser aplicada por dependência global no `include_router`, nunca
decorando rota por rota — o padrão precisa ser "protegido", e a exceção precisa
ser explícita e enumerável. Uma rota nova nasce protegida sem que o autor
precise lembrar.

### 29.3.2 Perfil `desktop` — token local

O token é gerado no primeiro start, com no mínimo 32 bytes de
`secrets.token_urlsafe`, e gravado em `<data_dir>/runtime_token` com permissão
`0600` (`0700` no diretório). O Electron o lê pelo processo principal e o injeta
no cliente; o `local_launcher.py` o passa na URL de abertura do navegador, que
o troca imediatamente por cookie de sessão e o remove da barra de endereço.

O token **NÃO DEVE** ser gravado em `localStorage` — cookie `HttpOnly`,
`SameSite=Strict`, `Secure` quando sobre HTTPS.

### 29.3.3 Perfil `server` — contas nomeadas

| Item | Regra |
|---|---|
| Modelo | `UserModel(id, username, password_hash, role, created_at, last_login_at, is_active)` |
| Hash | **Argon2id** (`argon2-cffi`). Se indisponível, `bcrypt` com custo ≥ 12. **NÃO DEVE** usar SHA/MD5, com ou sem sal |
| Senha mínima | 12 caracteres; a de provisionamento inicial **DEVE** ser aleatória, nunca fixa no código |
| Sessão | Cookie `HttpOnly`, `Secure`, `SameSite=Strict`; validade 12 h; renovação por atividade |
| Revogação | `POST /auth/logout` invalida no servidor — sessão **DEVE** ter estado no servidor, não ser um JWT auto-contido sem revogação |
| Força bruta | Máximo 5 tentativas por usuário em 15 min; atraso progressivo; toda tentativa registrada |
| Provisionamento | `python -m app.cli create-user <nome>` — imprime a senha uma única vez |

### 29.3.4 Papéis

Dois papéis, deliberadamente poucos:

| Papel | Pode |
|---|---|
| `owner` | Tudo, inclusive gerir contas, ler/gravar chaves de API e exportar perfil |
| `researcher` | Operar projetos: coletar, triar, extrair, exportar dados de pesquisa |

> **§29.3.4** As rotas que leem ou gravam credenciais — `/api/v1/ai/settings`,
> `/api/v1/settings/sources`, `/api/v1/profile/*` — **DEVEM** exigir papel
> `owner`. `researcher` **NÃO DEVE** ler chave alguma, nem mascarada.

### 29.3.5 Autoria nas trilhas de auditoria

> **§29.3.5** `AuditLogModel` **DEVE** ganhar `user_id` e `username`, e toda
> escrita de decisão de triagem, extração e alteração de protocolo **DEVE**
> preenchê-los. `source="manual"` sem autor não satisfaz esta cláusula.

Isto não é só segurança: é a condição para que a revisão continue auditável
quando mais de uma pessoa opera o mesmo servidor — que é exatamente o que o
modo servidor tornou possível.

### 29.3.6 WebSockets

> **§29.3.6** O handshake **DEVE** validar (a) sessão autenticada e (b)
> cabeçalho `Origin` contra a mesma lista de permissão do CORS. Falha em
> qualquer das duas **DEVE** resultar em `close(code=1008)` **antes** de
> `accept()`. Aceitar primeiro e checar depois **NÃO** satisfaz esta cláusula.

---

## 29.4 Proteção de segredos

### 29.4.1 Cifra em repouso

> **§29.4.1** Toda chave de API e todo token institucional **DEVEM** ser
> cifrados antes de tocar o banco, com AEAD (`cryptography.fernet`, AES-128-CBC
> + HMAC, ou AES-GCM).

| Item | Regra |
|---|---|
| Origem da chave-mestra | `RSAC_SECRET_KEY`; na ausência, arquivo `<data_dir>/master.key` gerado com `0600` |
| Perfil `server` | `RSAC_SECRET_KEY` **DEVE** vir do ambiente. Chave em arquivo **NÃO DEVE** ser aceita, porque V-04 mostrou que arquivo ao lado do banco não é segredo |
| Migração | Valores em claro existentes **DEVEM** ser cifrados no primeiro start após a atualização, e o formato **DEVE** ser autodescritivo (prefixo de versão) |
| Nomenclatura | As colunas `*_encrypted` **DEVEM** passar a merecer o nome. Se a cifra não for implementada numa coluna, o sufixo **DEVE** ser removido |

A última linha é regra de honestidade de código, e vem direto do achado V-07: um
nome que mente sobre uma propriedade de segurança é pior que a ausência da
propriedade, porque desarma quem revisa.

### 29.4.2 Segredo nunca volta pela API

> **§29.4.2** Nenhuma resposta da API **DEVE** conter chave de API em texto
> claro. Todas as leituras devolvem apenas máscara (`••••••••` + 4 últimos
> caracteres), presença (`has_api_key`) e data de atualização.

Consequência de contrato — mudança incompatível, deliberada:

| Rota | Antes | Depois |
|---|---|---|
| `GET /api/v1/ai/settings` | chaves completas | `has_*_keys`, `*_key_previews[]`, contagem |
| `GET /api/v1/profile/keys/export` | JSON em claro | **removida**; ver §29.4.3 |

O frontend **DEVE** tratar campo de chave como *write-only*: exibe a máscara,
e o que o usuário digitar substitui integralmente. Não há "editar a chave
existente" — há "informar uma nova".

### 29.4.3 Backup de chaves

O backup continua existindo, com outro contrato:
`POST /api/v1/profile/keys/export` (não `GET`), papel `owner`, corpo com a
senha da conta, e resposta **cifrada com uma senha de exportação informada pelo
usuário**. O arquivo resultante **NÃO DEVE** ser legível sem essa senha.

Motivo de ser `POST`: um `GET` que devolve credenciais é acionável por
navegação, `<img>`, prefetch e histórico. `POST` com corpo, não.

### 29.4.4 Higiene em logs

> **§29.4.4** Chaves, tokens e cabeçalhos `Authorization` **NÃO DEVEM** ser
> escritos em log nem transmitidos por WebSocket, em nenhum nível, inclusive
> `debug`. Um filtro de log **DEVERIA** mascarar padrões conhecidos
> (`AIza…`, `sk-…`, `Bearer …`) como rede de segurança.

---

## 29.5 Política de origem e de rede

### 29.5.1 CORS

> **§29.5.1** `allow_origin_regex` **NÃO DEVE** ser usado com padrão aberto. A
> lista de origens **DEVE** ser finita, derivada do perfil, e o campo
> `settings.cors_origins` — hoje morto — **DEVE** ser a única fonte da verdade.

| Perfil | Origens |
|---|---|
| `desktop` | `http://localhost:*`, `http://127.0.0.1:*`, `file://` (Electron) |
| `server` | Somente o que estiver em `RSAC_CORS_ORIGINS`, com host e esquema explícitos |
| `ci` | `http://testserver` |

`allow_methods` e `allow_headers` **DEVEM** ser enumerados. `expose_headers`
**NÃO DEVE** ser `*`.

### 29.5.2 Confinamento do servidor de arquivos estáticos

> **§29.5.2** Todo caminho recebido do cliente e resolvido em disco **DEVE**
> ser normalizado com `Path.resolve()` e verificado com `is_relative_to()`
> contra a raiz permitida, **antes** de qualquer acesso ao sistema de arquivos.
> Caminho fora da raiz **DEVE** resultar em `404` — nunca em `403`, que
> confirmaria a existência do alvo.

Aplica-se ao catch-all da SPA (V-04) e a qualquer rota futura que sirva arquivo.
Normalização por prefixo de string (`startswith`) **NÃO** satisfaz esta
cláusula.

### 29.5.3 Requisições de saída — allowlist contra SSRF

> **§29.5.3** Toda requisição HTTP originada pelo servidor a partir de URL
> influenciada pelo usuário **DEVE** passar por um guarda único e central,
> antes da conexão **e a cada redirecionamento**.

O guarda **DEVE** recusar:

| Regra | Motivo |
|---|---|
| Esquema ≠ `http`/`https` | `file://`, `gopher://`, `ftp://` |
| IP em faixa privada, loopback, link-local ou reservada (`127/8`, `10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `::1`, `fc00::/7`) | Rede interna e metadados de nuvem |
| Host que resolve para os acima (verificação **após** DNS) | Evita *rebinding* e nomes que apontam para dentro |
| Porta fora de `{80, 443, 8080, 8443}` | Varredura de serviços internos |
| Redirecionamento para destino que falhe qualquer regra acima | Contorno por `302` |

Implicações de implementação:

- `follow_redirects=True` (`pdf_resolver.py:428`) **DEVE** ser trocado por
  seguimento manual, com revalidação a cada salto e limite de 5 saltos.
- A resolução DNS **DEVE** ser feita uma vez e o IP validado reusado na
  conexão, para fechar a janela de *DNS rebinding*.
- O `endpoint` de IA (`factory.py:60,69`) **DEVE** passar pelo mesmo guarda,
  **com exceção explícita** para `localhost` quando `provider == "local"` — é o
  único caso legítimo de destino em loopback, e **DEVE** ser restrito ao perfil
  `desktop`.

### 29.5.4 A trilha de tentativas deixa de ser oráculo

> **§29.5.4** No perfil `server`, `ResolutionAttempt.detail` e `http_status`
> **DEVEM** ser reduzidos a categorias (`bloqueado`, `nao_encontrado`,
> `nao_e_pdf`, `tempo_esgotado`) para hosts que não estejam na lista de
> provedores acadêmicos conhecidos. A trilha detalhada continua no log do
> servidor.

Sem esta cláusula, a correção de §29.5.3 ainda deixa um canal de informação:
o atacante aprende pela mensagem de erro o que não conseguiu alcançar.

---

## 29.6 Cabeçalhos de resposta

> **§29.6** Um middleware **DEVE** aplicar, a **todas** as respostas:

| Cabeçalho | Valor | Contra |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Sniffing de PDF servido `inline` (V-14) |
| `X-Frame-Options` | `DENY` | Clickjacking |
| `Referrer-Policy` | `no-referrer` | Vazamento da URL do túnel para terceiros |
| `Cache-Control` | `no-store` em respostas com dado sensível | Cache de proxy/navegador |
| `Strict-Transport-Security` | `max-age=31536000` (perfil `server`, sobre HTTPS) | Downgrade |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` nas respostas de API | Enquadramento e injeção |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` | Superfície desnecessária |

E a CSP do documento (`frontend/index.html:7`) **DEVE** deixar de usar `https:`
e `wss:` genéricos em `connect-src`, passando a listar `'self'` mais os hosts
efetivamente necessários por ambiente de build.

---

## 29.7 Limites de recurso e de taxa

> **§29.7** O backend **DEVE** impor os limites abaixo. Exceder **DEVE**
> resultar em `413` (tamanho) ou `429` (taxa), com `Retry-After`.

| Limite | Valor | Achado |
|---|---|---|
| Corpo de requisição | 100 MB no upload de PDF, 2 MB nas demais | V-10 |
| Leitura de upload | Em blocos (*streaming*) para disco temporário, com teto — **NÃO DEVE** ser `await file.read()` integral | V-10 |
| Requisições por sessão | 300/min geral | V-11 |
| Rotas de IA | 20/min por sessão | V-11 |
| Disparo de coleta e lote de PDF | 5/hora por projeto | V-11 |
| Tentativas de login | 5/15 min por conta e por IP | V-01 |
| Espaço em disco | Recusar upload abaixo de 1 GB livre | V-10 |

---

## 29.8 Tratamento de erros

> **§29.8** Nenhuma resposta de erro **DEVE** conter mensagem de exceção
> interna, *traceback*, caminho de sistema de arquivos ou fragmento de SQL.

O padrão `raise HTTPException(500, detail=str(e))` — presente em `ai.py:207`,
`ai.py:246`, `extraction.py:262` e nas quatro rotas de `profile.py` — **DEVE**
ser substituído por: mensagem estável para o usuário + identificador de
correlação; o detalhe vai só para o log do servidor, indexado por esse
identificador.

```python
except Exception:
    ref = uuid4().hex[:8]
    logger.exception("[AI] falha ao sugerir protocolo (ref=%s)", ref)
    raise HTTPException(500, detail=f"Falha ao processar a solicitação. Referência: {ref}")
```

---

## 29.9 Integridade dos dados de pesquisa

Cláusulas cujo objetivo é a validade da revisão, não a confidencialidade.

### 29.9.1 Exportações

> **§29.9.1** Todo valor textual escrito em `.xlsx` ou `.csv` que comece com
> `=`, `+`, `-`, `@`, TAB ou CR **DEVE** ser prefixado com apóstrofo. O nome de
> arquivo em `Content-Disposition` **DEVE** ser sanitizado (`[A-Za-z0-9._-]`) e
> acompanhado de `filename*=UTF-8''…` para o nome legível.

### 29.9.2 Fronteira do conteúdo de terceiros no prompt

> **§29.9.2** Texto de PDF e resumo de terceiros **DEVE** entrar no prompt
> dentro de delimitador explícito, precedido de instrução de que é **dado a
> analisar, nunca instrução a seguir**. A resposta da IA **DEVE** ser validada
> contra esquema, e decisão fora do vocabulário fechado
> (`Incluído|Excluído|Pendente`) **DEVE** ser rejeitada, não coagida.

> **§29.9.3** Toda decisão sugerida por IA **DEVE** registrar em auditoria o
> provedor, o modelo e o *hash* do contexto enviado. É o que permite refazer a
> conta depois — inclusive descobrir que uma decisão veio de conteúdo
> adulterado.

---

## 29.10 Cadeia de suprimentos

| Item | Regra |
|---|---|
| Dependências Python | **DEVEM** ser fixadas por *lockfile* (`uv.lock` ou `requirements.lock`) com *hashes* |
| `cloudflared` | Binário baixado **DEVE** ter *checksum* verificado contra valor fixado; sem correspondência, **NÃO DEVE** ser executado |
| CI | **DEVE** rodar `pip-audit`, `npm audit --omit=dev`, `ruff`, `bandit` e varredura de segredos em todo *push* e PR |
| XML | `xml.etree` **DEVERIA** ser trocado por `defusedxml` no PubMed |

---

## 29.11 O que o lançador de servidor passa a fazer

> **§29.11** `scripts/server_launcher.py` **DEVE**, antes de abrir o túnel:

1. Definir `RSAC_DEPLOYMENT_PROFILE=server` no ambiente do backend.
2. Verificar que existe pelo menos uma conta; se não existir, **provisionar
   interativamente** — pedir nome de usuário e gerar senha forte, exibindo-a
   uma única vez.
3. Verificar `RSAC_SECRET_KEY`; se ausente, gerar, gravar em
   `server_config.json` com permissão restrita e avisar.
4. Exibir o aviso, sem eufemismo: *"Este link publica seus dados de pesquisa na
   internet. Só quem tiver usuário e senha entra. Não compartilhe o link em
   canais públicos."*
5. **NÃO DEVE** imprimir o link Netlify com `api_url` embutido sem que o
   frontend implemente §29.12.

> **§29.11.6** O túnel **NÃO DEVE** subir se o *health check* de segurança
> (`GET /api/v1/auth/status`) indicar que a autenticação está desativada.

### 29.11.1 Verificação de integridade do `cloudflared`

`download_cloudflared` (`server_launcher.py:136-152`) **DEVE** verificar o
SHA-256 do binário baixado contra um valor fixado no repositório antes de
gravá-lo em local executável.

---

## 29.12 Contrato do cliente web

> **§29.12** O frontend **NÃO DEVE** aceitar `api_url` de query ou fragmento
> sem confirmação humana explícita.

O fluxo obrigatório quando `?api_url=` ou `#/?api_url=` aparece:

1. **Não** persistir nada de imediato.
2. Exibir diálogo modal nomeando o host de destino: *"Conectar ao servidor
   `abc123.trycloudflare.com`? Suas credenciais e dados de pesquisa serão
   enviados a este endereço."*
3. Só depois de confirmação, gravar — em `sessionStorage`, não em
   `localStorage`, para que o sequestro não sobreviva ao fechamento da aba.
4. Manter o host ativo visível de forma permanente na `StatusBar`.

Adicionalmente: a URL **DEVE** ser validada como `https:` (ou
`http://localhost`), e o host **DEVERIA** ser conferido contra uma lista de
sufixos conhecidos (`trycloudflare.com`, mais os configurados pelo usuário),
com aviso claro fora dela.

---

## 29.13 Matriz cláusula × achado

| Achado | Cláusulas que o fecham |
|---|---|
| V-01 sem autenticação | §29.2.4, §29.3.1, §29.3.3, §29.3.4 |
| V-02 chaves em claro na API | §29.4.2, §29.4.3, §29.3.4 |
| V-03 CORS irrestrito | §29.5.1 |
| V-04 path traversal | §29.5.2 |
| V-05 SSRF | §29.5.3, §29.5.4 |
| V-06 CSWSH | §29.3.6, §29.5.1 |
| V-07 chaves em claro no banco | §29.4.1 |
| V-08 `api_url` sequestrável | §29.12 |
| V-09 túnel desprotegido | §29.2.2, §29.11 |
| V-10 upload sem limite | §29.7 |
| V-11 sem limite de taxa | §29.7 |
| V-12 OpenAPI público | §29.2.2 |
| V-13 vazamento por exceção | §29.8 |
| V-14 sem cabeçalhos | §29.6 |
| V-15 injeção de fórmula | §29.9.1 |
| V-16 injeção de prompt | §29.9.2, §29.9.3 |
| V-17 dependências | §29.10 |
| V-18 XML | §29.10 |

Cobertura: 18 de 18.

---

## 29.14 Variáveis de ambiente

| Variável | Perfis | Padrão | Descrição |
|---|---|---|---|
| `RSAC_DEPLOYMENT_PROFILE` | todos | `desktop` | `desktop` \| `server` \| `ci` |
| `RSAC_SECRET_KEY` | `server` **obrigatória** | — | Chave-mestra da cifra e da sessão |
| `RSAC_CORS_ORIGINS` | `server` | `[]` | Lista separada por vírgula |
| `RSAC_SESSION_TTL_HOURS` | todos | `12` | Validade da sessão |
| `RSAC_MAX_UPLOAD_MB` | todos | `100` | Teto de upload |
| `RSAC_RATE_LIMIT_ENABLED` | todos | `true` em `server` | Chave geral do limitador |
| `RSAC_ALLOW_PRIVATE_EGRESS` | `desktop` | `false` | Libera loopback para LLM local |
| `RSAC_TRUSTED_HOSTS` | `server` | — | `TrustedHostMiddleware` |

Todas seguem o `env_prefix = "RSAC_"` já vigente em `backend/app/config.py`.

---

## 29.15 O que esta especificação deliberadamente não faz

Registrado para que a ausência seja lida como decisão, não como esquecimento:

- **Sem multi-tenancy real.** Papéis, sim; isolamento de projetos por dono,
  não. O RSAC é um instrumento de equipe pequena, e tenancy completa custaria
  mais do que entrega neste estágio. Se o produto for para SaaS, isto vira o
  primeiro item do próximo plano.
- **Sem SSO/OIDC.** Contas locais bastam para o caso de uso; integração
  institucional entra depois, se houver demanda concreta.
- **Sem cifra do banco inteiro.** Cifram-se os segredos (§29.4.1). Cifra de
  volume é responsabilidade do sistema operacional (BitLocker, FileVault) e
  **DEVERIA** ser recomendada no doc 17.
- **Sem 2FA.** Fora de proporção para o perfil de usuário atual; a estrutura de
  contas de §29.3.3 não impede acrescentá-lo depois.

---

*Especificação normativa, 19/08/2026. Alterações neste documento exigem
atualização correspondente do doc 30 e da suíte de testes de segurança.*
