# 36 — Revisão de Consolidação do Aplicativo Instalado

> **Objetivo deste documento:** apurar por que o RSAC V2 instalado demora a
> abrir — e o que mais está fora do lugar no estado atual do produto — antes de
> a Beta ir para as mãos de quem vai validá-la (`estudo_validacao/`).
>
> Toda afirmação aqui foi **verificada por execução**, não por leitura: o
> Chromium foi carregado de `file://` contra o backend real, o Electron
> empacotado foi executado sob display virtual, e os tempos vieram de
> `-X importtime`, de relógio no processo e do relatório de build do Vite. O
> que não pôde ser medido nesta máquina — o binário congelado do PyInstaller no
> Windows, com antivírus — está marcado **[A MEDIR NO WINDOWS]**.
>
> Este documento **não repete** os docs 28–30. A segurança que aquele ciclo
> instalou está de pé; o que se descobriu aqui é que dois dos seus controles
> foram calibrados para uma origem que o navegador nunca envia, e por isso
> fechavam a porta do próprio aplicativo.

---

## 36.1 Resumo executivo

A lentidão relatada não é lentidão. São **três defeitos empilhados**, e só o
primeiro é de desempenho:

| # | Achado | Natureza | O que o usuário via |
|:-:|--------|----------|---------------------|
| B-01 | A janela só era criada **depois** do health check do backend | Arranque | Ícone salta na barra de tarefas e nada aparece por vários segundos |
| B-02 | O Chromium apresenta `file://` como origem **`null`**; o CORS só previa `file://` | Bloqueante | Tela de "Conectar ao Servidor Backend", repetindo a cada 5 s, para sempre |
| B-03 | Mesma origem `null` no *handshake* do WebSocket | Bloqueante | Coleta e painel de log mudos |
| B-04 | O Electron nunca lia o `runtime_token` | Bloqueante | Tela de acesso mandando "crie a conta pelo terminal" |
| B-05 | O `launcher.py` procurava o token em três caminhos, **nenhum deles** o que o backend usa | Bloqueante | O mesmo beco sem saída pelo caminho do navegador |

Empilhados, B-02 a B-04 significam que **o aplicativo instalado nunca chegava a
funcionar**. O sintoma que chega como "demora muito para abrir" é a soma de uma
janela que aparece tarde (B-01) com uma aplicação que, depois de aparecer,
nunca sai do estado de conexão (B-02).

Abaixo dos bloqueantes há custo de arranque real, esse sim de desempenho:

| # | Achado | Medido | Depois |
|:-:|--------|--------|--------|
| P-01 | `pandas` importado no caminho crítico do backend só para gerar planilha | `import app.main` = **1,39 s** | **1,01 s** (−27%) |
| P-02 | Pacote único de interface, sem divisão por rota | **1.147 kB** JS + **253 kB** CSS | **496 kB** + **95 kB** (−57% / −62%) |
| P-03 | Folha de estilo do Google Fonts bloqueando a pintura de um app local | 1 ida à internet antes do primeiro pixel | 0 — fontes no disco |
| P-04 | A splash saía no primeiro quadro do React, antes de haver tela | Marca → branco → interface | Marca → interface |

E, na revisão do estado geral, seis pontos de consolidação (§ 36.5) — de
dependências declaradas e nunca importadas a dois pipelines de instalador
concorrentes.

**Estado após este ciclo:** os cinco bloqueantes estão corrigidos e
verificados; P-01 a P-04 estão corrigidos e medidos; dos seis itens de
consolidação, quatro foram feitos e dois ficam registrados como decisão a
tomar (§ 36.6).

---

## 36.2 O arranque, cronometrado

### 36.2.1 O que acontecia

`app.whenReady()` em `frontend/electron/main.ts` esperava a promessa de
`pythonManager.start()` — que só resolve quando o backend responde ao health
check, com timeout de 30 s — e **só então** chamava `createWindow()`.

A ironia é que o produto já tinha a solução para essa espera: o `index.html`
carrega uma splash de marca, com um comentário explicando que ela existe porque
"o backend Python leva alguns segundos para subir". Ela nunca aparecia durante a
espera, porque não havia janela onde aparecer. A splash cobria o tempo *depois*
do problema, não o tempo *do* problema.

### 36.2.2 O que passou a acontecer

A partida do backend corre em paralelo com a janela. A interface pergunta pela
porta quando precisa dela, por um canal `ipcMain.handle('backend:info')` — e
não por um evento, porque o backend pode ficar pronto antes de o renderer
existir e um evento disparado nesse intervalo se perderia.

**Medição no Electron real** (Linux, display virtual, backend não congelado,
cache quente — `xvfb-run electron` com o `out/main` desta árvore):

| Marco | Antes | Depois |
|-------|------:|-------:|
| Janela com a marca na tela | ~1.970 ms | **229 ms** |
| Interface completa (`.app-shell`) | ~1.970 ms | **1.969 ms** |

O tempo total até a interface não mudou — não é ele que estava errado. O que
mudou é que os primeiros 1,7 s deixaram de ser tela nenhuma e passaram a ser a
marca com "Iniciando o servidor local".

**[A MEDIR NO WINDOWS]** No app instalado o backend é um binário `--onedir` do
PyInstaller: a primeira execução paga descompactação, carregamento de algumas
centenas de `.pyd`/`.dll` e a varredura do antivírus sobre cada um. É aí que a
janela em branco vira dezenas de segundos, e é exatamente esse o intervalo que
a splash agora cobre.

### 36.2.3 Custo de importação do backend

`python -X importtime -c "import app.main"`, mediana de três execuções:

| | Antes | Depois |
|---|------:|-------:|
| `app.main` (total) | 1,392 s | **1,019 s** |
| `pandas` (dentro do total) | 0,346 s | 0 — não é mais importado |

O `pandas` era alcançado por `router → app.api.v1.export → ExportService`, e
existe para montar quatro abas de uma planilha que o usuário pede clicando um
botão. Passou a ser importado dentro de `generate_excel`. No binário congelado
o ganho é maior que aqui, porque lá o custo não é só de `import` — é de ler
`numpy` e `pandas` do disco com o antivírus olhando.

As três sessões de banco abertas em sequência no `lifespan` (contagem de
contas, reconciliação de coletas, limpeza de observações antigas) viraram uma
só, com o trabalho extraído para `_reconciliar_coletas_interrompidas` e
`_limpar_prefixos_de_ia_legados`.

---

## 36.3 O bloqueante que ninguém tinha visto: a origem `null`

Este é o achado central da revisão, e ele merece ser contado com a evidência.

O app empacotado carrega a interface com `loadFile()`, ou seja, de `file://`.
A configuração de CORS previa isso — `app/config.py` listava `file://` entre as
origens de loopback autorizadas. Só que **o navegador não envia `file://`**: uma
página de `file://` tem origem opaca, e o Chromium a apresenta como a palavra
`null`.

Verificado carregando uma página real de `file://` no Chromium, com um `fetch`
para o backend em execução:

```
Access to fetch at 'http://127.0.0.1:8123/api/v1/auth/status' from origin 'null'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is
present on the requested resource.
```

Toda chamada da API — health, status de autenticação, lista de projetos — era
barrada pelo navegador antes de chegar ao Python. A aplicação caía em
`BackendUnavailableView`, que tenta de novo a cada 5 s, para sempre. Do lado de
fora isso é indistinguível de "o app não abre".

O mesmo vale para o `handshake` do WebSocket (`origem_do_websocket_e_permitida`
em `app/security/dependencies.py`, que usa o mesmo regex): coleta e painel de
log ficariam mudos mesmo depois de o HTTP passar.

**Por que ninguém viu.** Em desenvolvimento o renderer vem do Vite, em
`http://localhost:5173` — que casa com o regex. O caminho `file://` só existe no
pacote, e o empacotamento é recente (docs de commit `f26c464`…`15f3727`).

**A correção e o seu limite.** O regex passou a aceitar `null` **fora do perfil
`server`**. A concessão é segura, e a razão não é a origem — é o regime de
credencial. Um sítio hostil também consegue produzir origem `null`, por iframe
em sandbox; o que ele não consegue é levar credencial junto: o cookie de sessão
é `SameSite=Strict` e não acompanha requisição de outro sítio, e o token local
viaja em cabeçalho próprio, inalcançável de fora da página. O que sobra para
quem chegue por essa via é 401 em tudo, menos as três rotas públicas — que não
expõem dado de revisão. No perfil `server`, nada disso vale: lá o regex
continua sendo `None`.

Dois testes fixam o comportamento nos dois perfis
(`tests/test_security/test_cors_policy.py`) e um terceiro cobre o WebSocket
(`tests/test_security/test_websocket_auth.py`).

---

## 36.4 O token local que ninguém entregava

`LoginPage.tsx` abre com um comentário: *"no app de mesa o token local resolve
antes, e esta tela nunca chega a ser vista"*. A intenção estava certa e o
backend a implementava por inteiro (`POST /api/v1/auth/local`). Faltava a ponta:

- **No Electron** — `main.ts` passava para a interface apenas `?port=`. O
  `runtime_token` nunca era lido, e portanto nunca chegava ao `bootstrap`. O
  resultado é a tela de acesso, que no perfil desktop exibe "Nenhuma conta
  provisionada — crie a primeira no terminal": um beco sem saída para quem só
  instalou o programa.
- **No `launcher.py`** — `get_local_token()` procurava em
  `%LOCALAPPDATA%\RSAC`, em `~/.rsac` e em `backend/data`. O backend grava na
  pasta do `platformdirs`, que no Windows é `%LOCALAPPDATA%\RSAC\RSAC`. Nenhum
  dos três caminhos existia.

Adivinhar caminho era o erro comum aos dois. Quem sabe onde o arquivo está é o
processo que o escreveu, então é ele que informa: o backend passou a anunciar,
na saída padrão, duas linhas de handshake (`_anunciar_pasta_de_dados`, em
`app/main.py`):

```
RSAC_RUNTIME data_dir=<pasta>
RSAC_RUNTIME token_file=<pasta>/runtime_token
```

O que sai é o **caminho**, nunca o token: a saída padrão do backend vai para o
log do processo pai, e credencial não tem por que passar por lá. O
`PythonManager` lê essas linhas do `stdout` que já capturava, e o token chega à
interface pelo canal IPC — não pela URL, onde ficaria no histórico e em
qualquer captura de tela.

Como recuo, quando o handshake não chega, ambos os lados agora procuram nos
caminhos que o `platformdirs` realmente produz em cada sistema.

Verificado no Electron real, sob display virtual:

```
[Python] RSAC_RUNTIME token_file=…/RSAC/runtime_token
[Python] "GET  /api/v1/auth/status HTTP/1.1" 200 OK
[Python] "POST /api/v1/auth/local  HTTP/1.1" 200 OK
[Python] "GET  /api/v1/projects?archived=false HTTP/1.1" 200 OK
PROBE_APPSHELL true
```

Entra direto, sem tela de login — como o comentário do `LoginPage` sempre
prometeu.

### 36.4.1 `RSAC_DATA_DIR` passou a existir de verdade

O `launcher.py` já consultava `RSAC_DATA_DIR` para achar o token, mas
`Settings.data_dir` era uma propriedade fixa no `platformdirs`: o backend nunca
leu a variável. Quem a definisse mudava metade do sistema. Agora ela é um campo
(`data_dir_override`, alias `RSAC_DATA_DIR`) com precedência sobre o padrão do
sistema, e vale para os dois lados.

O **padrão não mudou**, de propósito: fixar a pasta no Electron moveria o banco
de quem já usa o `launcher.py`, e a revisão passaria a existir em duas
instalações sem o usuário perceber.

---

## 36.5 A interface, medida

`vite build`, comparando o pacote antes e depois da divisão por rota:

| Artefato inicial | Antes | Depois | |
|---|------:|------:|---|
| JS | 1.147 kB | **496 kB** | −57% |
| JS (gzip) | 326 kB | **147 kB** | −55% |
| CSS | 253 kB | **95 kB** | −62% |
| CSS (gzip) | 32 kB | **15 kB** | −53% |

As nove telas de trabalho entram por `React.lazy`. O maior ganho isolado é a
aba de Indicadores: **395 kB** só dela, quase tudo `recharts`, que estavam sendo
baixados e executados por quem abre o app no Painel e nunca vai a Indicadores.
As três telas maiores do produto — Protocolo (98 kB), Triagem (45 kB),
Configurações (35 kB) — saíram do caminho da primeira pintura.

`LoginPage` ficou estática de propósito: é uma das duas primeiras telas
possíveis, e adiar o seu código só acrescentaria um piscar à entrada.

### 36.5.1 Tipografia

O `index.html` carregava a folha do `fonts.googleapis.com` com
`<link rel="stylesheet">` — que **bloqueia a pintura**. Num aplicativo de mesa
isso significa que a primeira tela dependia de DNS e de uma viagem à internet:
sem rede o navegador falha rápido, mas numa rede lenta ou atrás de um portal
cativo a janela fica em branco até desistir. É um candidato clássico a "o app
demora a abrir" que varia de máquina para máquina.

As duas famílias passaram a ser servidas do disco: quatro arquivos `.woff2`
variáveis (Inter e JetBrains Mono, subconjuntos latin e latin-ext), **176 kB**
no total, em `frontend/src/assets/fonts/` — ambas sob SIL OFL 1.1, que permite
a redistribuição embutida. A CSP perdeu os dois domínios do Google.

Verificado no Electron: `Inter:loaded, JetBrains Mono:loaded`, sem rede.

### 36.5.2 O health check deixou de ser descoberta

`AppContent` tentava a porta corrente, e ao falhar recuava para a 8000 e
repetia a cada 2 s. Com a porta sorteada a cada execução
(`PythonManager.findFreePort`), esse recuo acertava por acaso; quando errava,
apontava o diagnóstico exibido ao usuário para o endereço errado. Quem resolve
a porta agora é o handshake IPC, e a repetição no `AppContent` voltou a ser o
que o nome diz: vigilância sobre um backend que caiu em uso.

---

## 36.6 Consolidação — o que foi feito e o que fica em aberto

### Feito

| # | Item | O que era |
|:-:|------|-----------|
| C-01 | `openai`, `google-genai` e `alembic` fora do `pyproject.toml` | Declaradas e **nunca importadas**: os dois provedores de IA falam REST por `httpx`; a migração de esquema é a caseira de `app/database.py` |
| C-02 | `RSAC_DATA_DIR` respeitada pelo backend | § 36.4.1 |
| C-03 | `server_config.json` reduzido ao que é lido | O arquivo prometia `port`, `auto_open_browser` e `cors_origins`; o `launcher.py` calculava o caminho e **não abria o arquivo**, com a porta fixa em 8000 no código. Agora a porta é lida; as outras duas chaves saíram, porque CORS e perfil vêm de variável de ambiente |
| C-04 | `--hidden-import=pandas` no build do backend | Com o import agora dentro da função, declarar a dependência a torna imune a uma reorganização futura do módulo |
| C-05 | Uma só definição de instalador (§ 36.6.1) | Havia duas — o alvo `nsis` do `electron-builder.yml`, que nenhum script invocava, e o `installer.iss` que o build realmente usa |

### 36.6.1 A escolha do empacotamento (C-05)

Havia **duas** definições de instalador do Windows para um instalador só:

- `electron-builder.yml` declarava um alvo `nsis` completo — ícones, atalhos,
  `oneClick`, nome de artefato — que **nenhum script invocava**;
- `scripts/installer.iss` (Inno Setup) é o que o `build_installer.py`
  realmente usa, depois de pedir ao electron-builder só o diretório (`--dir`).

A definição morta era justamente a que alguém leria primeiro ao procurar como
o RSAC é distribuído.

**A opção "apagar o `electron-builder.yml`" não existe.** O arquivo não é a
configuração do NSIS: é a configuração do **empacotador**, e o passo
`npx electron-builder --dir` depende dele para saber o `appId`, a pasta de
saída (`release/`) e, sobretudo, para copiar o backend congelado do
PyInstaller como `extraResources`. Sem ele o pacote sai sem o Python dentro —
e aí o instalador instala um aplicativo que não tem servidor para iniciar.

**Escolha: o Inno Setup continua sendo o instalador.** Duas razões, nesta
ordem:

1. É o caminho que funciona hoje e que foi adotado deliberadamente
   (`1ec5868`). Migrar para o NSIS trocaria um instalador em uso por um não
   verificado — e esta revisão existe porque uma mudança de empacotamento não
   verificada quebrou o produto.
2. O NSIS não pôde ser exercitado aqui: gerá-lo fora do Windows exige
   `wine`/`makensis`, ausentes nesta máquina. Entregar uma migração de build
   sem uma única execução seria repetir o erro.

O que mudou, então:

| Antes | Depois |
|---|---|
| Bloco `nsis:` completo, morto, no `electron-builder.yml` | Removido; `win.target` passa a ser `dir`, com comentário dizendo que trocá-lo por `nsis` **é** a decisão de abandonar o `installer.iss` |
| `productName` no `electron-builder.yml`, nome do executável repetido no `installer.iss`, versão repetida em ambos | `productName` e `version` só no `package.json`; o `build_installer.py` os lê de lá e os injeta no Inno Setup |
| `installer.iss` com nome, versão e caminho fixos no arquivo | `#ifndef` com padrões + inclusão de `installer_defs.generated.iss`, escrito pelo build |
| `electron-builder --dir` (alvo conforme a plataforma do build) | `electron-builder --win --dir`, explícito |
| Nada verificava se o `.exe` gerado é o que o instalador procura | O build falha, com a lista dos `.exe` encontrados, antes de chamar o Inno Setup |

A divisão de responsabilidades passou a estar escrita nos dois arquivos:
o `electron-builder.yml` monta o diretório do aplicativo; o `installer.iss`
transforma esse diretório em instalador. Não se sobrepõem, e cada fato —
nome, versão, pasta de saída, executável — tem uma origem só.

**Por arquivo gerado, não por `/D`.** O nome do produto tem espaço no meio
("RSAC V2"). Passá-lo por `/DMyAppName=...` obrigaria shell, citação do
Windows e pré-processador do Inno a concordarem sobre aspas — três camadas
para produzir uma string que o Python escreve pronta, entre aspas, num arquivo
que o `.iss` inclui. O arquivo é gerado a cada build e não é versionado; se
faltar, os `#ifndef` assumem e compilar o `.iss` à mão continua funcionando.

**Verificado:** `npx electron-builder --win --dir` executado nesta máquina com
a configuração nova produz `release/win-unpacked/RSAC V2.exe` e os
`extraResources` (`backend/`, `icon.png`) no lugar — ou seja, o nome que o
`installer.iss` procura continua sendo o nome que o empacotador gera, agora
com uma origem única em vez de duas cópias que coincidiam por sorte.

**O que fica fora desta decisão.** Os dois *lançadores* — `launcher.py` (janela
do Edge/Chrome, SPA servida pelo FastAPI) e o Electron — continuam existindo,
e isso é deliberado: o primeiro é o caminho de desenvolvimento e de acesso pelo
navegador, o segundo é o produto instalado. O que se consolidou aqui é o
**empacotamento**, não o número de formas de abrir o RSAC.

---

### Em aberto — decisão do mantenedor

**C-06 — A SPA servida pelo backend eliminaria a classe do B-02.**
Se o backend empacotado carregasse a SPA (`--add-data` no PyInstaller) e o
Electron apontasse para `http://127.0.0.1:<porta>/` em vez de `loadFile`, a
origem da página passaria a ser a origem da API: **sem CORS, sem exceção de
origem opaca, cookie de sessão no regime normal, `Origin` do WebSocket casando
com o regex de loopback e uma só cópia da interface**. É a consolidação que
torna B-02 e B-03 impossíveis em vez de tratados.

Não foi feito aqui porque muda o pipeline de empacotamento do Windows, que não
pode ser exercitado nesta máquina — e uma mudança de build não verificada é
exatamente o tipo de coisa que produz o próximo "o app não abre".

### Dívida registrada, não tocada

| Item | Estado |
|---|---|
| `npm run lint:tokens` falha em `R8` (`--color-included` sobre `--color-included-bg`, `ProtocolPage.css`) | **Anterior a este ciclo** — verificado com a árvore limpa. O CI a marca `continue-on-error` |
| `ruff check` acusa 40 avisos nos arquivos tocados | **Anterior**; a contagem é idêntica antes e depois. O CI a marca `continue-on-error` |
| `uv.lock` e `requirements.lock` ainda listam as três dependências removidas | Regenerar num passo próprio (comandos no `pyproject.toml`): fazê-lo aqui arrastaria uma migração de formato do lockfile e a resolução inteira das dependências de desenvolvimento |
| `ProtocolPage.tsx` (129 kB), `ScreeningPage.tsx` (73 kB), `SettingsPage.tsx` (59 kB) em arquivo único | Manutenção. A divisão por rota já tirou as três do caminho de arranque; quebrá-las em componentes é trabalho de outra natureza |
| `datetime.utcnow()` depreciado em `dedup_service.py:461` | Um aviso, uma linha |

---

## 36.7 Como verificar

```bash
# Backend — 407 testes, 4 pulados
cd backend && RSAC_DEPLOYMENT_PROFILE=ci pytest -q

# Custo de importação do backend
python -X importtime -c "import app.main" 2>&1 | tail -1

# Frontend — tipos, testes e tamanho do pacote inicial
cd frontend && npx tsc --noEmit && npx vitest run && npm run build:web
```

Para reproduzir o bloqueante B-02 antes da correção: reverta o `null` do regex
em `app/config.py`, suba o backend e carregue uma página de `file://` que faça
`fetch` em `/api/v1/auth/status`. O console do navegador mostra o bloqueio de
CORS citado em § 36.3.
