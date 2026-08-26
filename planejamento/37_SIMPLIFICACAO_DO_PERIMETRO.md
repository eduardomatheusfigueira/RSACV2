# 37 — Simplificação do Perímetro: um app instalado, uma credencial

> **Objetivo deste documento:** registrar a remoção do perfil publicável, das
> contas de acesso e das sessões — e o raciocínio de segurança que sustenta o
> que ficou no lugar.
>
> Este documento **substitui** os docs 28–30 como referência vigente de
> segurança. Aqueles continuam válidos como história: os 18 achados do doc 28
> foram fechados e a maioria das correções continua de pé. O que mudou é o
> **perímetro** que eles normatizavam.
>
> Toda afirmação foi verificada por execução: a API foi exercitada com e sem
> credencial contra um backend real, e o app empacotado foi executado sob
> display virtual.

---

## 37.1 O que mudou, em uma frase

O RSAC deixou de ser *um backend que pode ser publicado* e passou a ser *um
aplicativo instalado*. Com isso, a prova de identidade deixou de precisar
atravessar a internet — e virou a posse de um arquivo.

| | Antes | Depois |
|---|---|---|
| Perímetro | `desktop` \| `server` \| `ci`, por variável de ambiente | Loopback, sem configuração |
| Credencial | Conta + senha Argon2id → sessão com cookie `HttpOnly` | `runtime_token` (256 bits, `0600`) no cabeçalho `X-RSAC-Local-Token` |
| Tela de login | Sim, no perfil `server` | Não existe |
| Contas | `owner` / `researcher`, CRUD e CLI | Não existem |
| Rotas públicas | 4 (`health`, `status`, `login`, `local`) | 2 (`health`, `status`) |
| Rotas de `/auth` | 9 | 1 |
| Origens no CORS | Lista configurável + regex de loopback | Regex fixo: loopback, `file://`, `null` |
| SPA servida pelo backend | Sim, com confinamento de caminho | Não |
| Módulos de segurança | 14 | 11 |
| Suíte de testes | 407 | 357 |

---

## 37.2 Por que isto não enfraquece a segurança

A pergunta certa não é "quantos controles restaram", e sim "o que um atacante
precisa fazer agora que antes não precisava". A resposta é: **nada mudou para
ele**, porque o alvo já era o mesmo.

**A senha nunca foi a barreira no app de mesa.** O perfil `desktop` já
autenticava por `runtime_token`, exatamente como agora — a senha só existia
para o caso publicado. Quem operava o RSAC instalado nunca digitou uma.

**O que protege o token protege tudo o mais.** O `runtime_token` é um arquivo
`0600` na pasta do usuário. Quem consegue lê-lo tem a conta do sistema
operacional — e portanto o `rsac.db` (com as chaves de API cifradas), o
`master.key` que as decifra, e os PDFs. Uma senha por cima disso não
acrescentava barreira nenhuma contra esse atacante; acrescentava uma tela.

É o mesmo raciocínio do Jupyter e do Docker Desktop, e a razão é a mesma: um
controle que atrapalha o uso legítimo sem deter o atacante real acaba
contornado, e aí não protege ninguém.

**O que um sítio hostil consegue.** Uma página em `evil.example` pode produzir
origem `null` (via iframe em sandbox) e varrer as portas do loopback. O que ela
não consegue é ler um arquivo do disco. Sem o token, o que ela alcança é 401 em
tudo, menos `/health` e `/auth/status` — que dizem, respectivamente, que existe
um RSAC nesta porta e que ela não está autenticada. Nenhum dado de revisão.

O que **melhorou**, e não é pouco:

| | Por quê |
|---|---|
| Sem tela de login | A tela era o beco sem saída do app instalado: mandava criar conta pelo terminal (§ 36.4) |
| Sem cookie de sessão | Some a classe inteira de CSRF; nada é enviado automaticamente pelo navegador |
| Sem catch-all de arquivos | A travessia de caminho do doc 28 não é mais mitigada, é impossível: a superfície deixou de existir |
| Sem `/auth/login` | Some a superfície de força bruta e a contabilidade de tentativas que existia para contê-la |
| Sem `RSAC_CORS_ORIGINS` | Não há configuração capaz de autorizar um host da internet |

---

## 37.3 O desenho da autenticação

```
  Primeira execução do backend
      └─ sorteia 256 bits, grava em <data_dir>/runtime_token com modo 0600
      └─ anuncia o CAMINHO (nunca o token) na saída padrão

  Electron (processo principal)
      └─ lê a linha de handshake, abre o arquivo
      └─ entrega o token ao renderer por IPC — nunca pela URL

  Interface
      └─ X-RSAC-Local-Token em toda chamada HTTP
      └─ ?local_token= no handshake do WebSocket, onde o navegador
         não permite cabeçalho personalizado
```

Três decisões merecem registro:

**O token sai por IPC, não pela URL.** O lançador de navegador o passava em
`?local_token=`, o que o deixava no histórico e em qualquer captura de tela.
Com o lançador removido (§ 36.6.2), essa via foi fechada também no cliente.

**Em HTTP, a query não é aceita.** `GET /api/v1/projects?local_token=…`
responde 401 mesmo com o token correto. A query é exceção do WebSocket, e só
dele. Há teste para isso.

**`require_local_token` é dependência do router agregador**, não decorador rota
a rota. É o que torna a proteção durável: uma rota nova nasce autenticada.
`test_authn_coverage.py` enumera o esquema OpenAPI inteiro e exige 401 de cada
rota fora de uma lista de exceções escrita à mão — se alguém acrescentar uma
rota desprotegida, o teste quebra sem que ninguém precise lembrar de cobri-la.

---

## 37.4 A trilha de auditoria continua tendo autor

`AuditLogModel.username` é o que permite a uma revisão sistemática dizer de
quem foi cada decisão — isso é produto, não detalhe operacional, e a aba de
Indicadores o reporta como throughput por pessoa.

Com as contas removidas, quem assina é o **usuário do sistema operacional**
(`getpass.getuser()`). Continua sendo uma identidade real: é a conta em que o
aplicativo roda, e ela sobrevive à cópia do banco para outra máquina. O campo
`user_id`, que apontava para a tabela `users`, saiu — um identificador que não
aponta para lugar nenhum faria a trilha parecer mais precisa do que é.

**Consequência a registrar:** o indicador "throughput de triagem por pessoa"
(doc 32) passa a ter, numa instalação típica, um único autor. Ele não perde
sentido — distingue decisões manuais de assistidas por IA, e distingue máquinas
quando bancos são consolidados —, mas deixa de distinguir coautores na mesma
instalação. Quem precise disso precisa de duas instalações, e a consolidação é
por exportação.

---

## 37.5 O que saiu do repositório

| Arquivo | Linhas | O que era |
|---|--:|---|
| `app/security/sessions.py` | 188 | Sessões com estado no servidor, hash do token, revogação |
| `app/security/passwords.py` | 84 | Hash e política de senha Argon2id |
| `app/cli.py` | ~180 | `create-user`, `list-users`, `reset-password`, `generate-secret-key` |
| `app/schemas/auth.py` | 9 schemas → 1 | Login, troca de senha, criação e listagem de contas |
| `src/pages/LoginPage.tsx` + `.css` | ~200 | A tela que o app de mesa nunca deveria ter visto |
| `tests/.../test_authz_and_sessions.py` | 16 testes | Papéis, sessões, força bruta, gestão de contas |
| `tests/.../test_deployment_profile.py` | 6 testes | Substituído por `test_perimetro_local.py` |
| `tests/.../test_safe_start_and_local_token.py` | 9 testes | Substituído por `test_token_local.py` |
| `tests/.../test_path_traversal.py` | 7 testes | O catch-all que ele protegia deixou de existir |
| `frontend/vite.config.web.ts` | — | Build da SPA para navegador |

Modelos `UserModel`, `SessionModel` e `LoginAttemptModel` saíram do ORM.
**As tabelas não são apagadas** de bancos existentes: a migração automática de
`app/database.py` só acrescenta coluna, e destruir dados de um banco que o
usuário talvez queira abrir numa versão anterior seria uma escolha dele, não
nossa. Elas simplesmente deixam de ser lidas e escritas.

E `argon2-cffi` saiu das dependências — o que, de quebra, fez a suíte de testes
cair de **64 s para 12 s**: o hash de senha era, sozinho, 80% do relógio.

---

## 37.6 Verificação

Contra um backend real:

```
sem credencial      GET /api/v1/projects      → 401
                    GET /api/v1/auth/status   → 200 {"authenticated": false}
token errado        GET /api/v1/projects      → 401
token correto       GET /api/v1/projects      → 200
                    GET /api/v1/auth/status   → 200 {"authenticated": true}
preflight null      OPTIONS /api/v1/projects  → allow-headers inclui X-RSAC-Local-Token
```

No Electron empacotado, sob display virtual:

```
janela criada em 182 ms
GET  /api/v1/auth/status            200
GET  /api/v1/projects?archived=false 200
app-shell montado
```

Note o que **não** aparece: o `POST /api/v1/auth/local` que existia para trocar
o token por uma sessão. São duas idas ao backend a menos na partida.

Suíte: **357 testes**, 2 pulados, 12 s. Lint de tokens do design system: sem
regressão, todas as oito regras fechadas — a primeira vez que isso acontece.

---

## 37.7 O que ficou de dívida

| Item | Estado |
|---|---|
| `ruff check app tests` | 955 → ~800 avisos. O que foi corrigido: os 30 falsos positivos de `B008` (o `Depends()` do FastAPI, agora declarado em `extend-immutable-calls`), e os achados reais nos arquivos tocados. O que resta é modernização de tipagem (`UP006`, `UP045`, `UP009`) em ~80 arquivos: é um `ruff check --fix` de um commit só, e misturá-lo aqui tornaria esta mudança de segurança impossível de revisar |
| `E501` (linha longa) | 276 ocorrências. Mesma razão |
| Páginas grandes | `ProtocolPage.tsx` (129 kB), `ScreeningPage.tsx` (73 kB). A divisão por rota já as tirou do arranque; quebrá-las em componentes é trabalho de outra natureza |
| Docs 28–30 | Continuam no repositório como história. Não foram reescritos: o registro do que foi encontrado e corrigido tem valor mesmo quando o perímetro muda |
