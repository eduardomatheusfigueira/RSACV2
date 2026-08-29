# 43 — Publicar da própria máquina (Windows, túnel Cloudflare)

> **O que é.** Uma variante da Fase 4 do doc 41 para colocar o `revsist.com` no
> ar a partir de um computador Windows de uso pessoal, sem VPS e sem custo
> mensal.
>
> **Para que serve.** A **etapa 0** do plano de marca (doc 42 §42.9): 5 a 10
> revisões-piloto com pessoas que você conhece e que sabem que é BETA.
>
> **Para que não serve.** Cadastro público aberto. A razão está em §43.7, e não
> é técnica.
>
> **Data:** 29/08/2026 · **Status:** roteiro proposto. Não há daemon Docker
> neste ambiente, então a imagem de §43.4 não foi construída; o que **foi**
> verificado é o `pip install -e ./backend` que ela executa — e ele estava
> quebrado num diretório limpo, por dois motivos corrigidos no mesmo commit
> deste documento (ver §43.11).

---

## 43.1 Por que túnel, e não porta aberta

A maioria das conexões residenciais de fibra no Brasil está atrás de **CGNAT**:
o IP que aparece como seu é compartilhado com outros assinantes, e
redirecionamento de porta no roteador simplesmente não funciona, por mais
corretamente que seja configurado. Descobrir isso depois de uma tarde mexendo
no roteador é a forma cara de aprender.

**Como saber em 30 segundos.** Compare o que o roteador diz ser o IP da WAN com
o que um site de "qual é meu IP" mostra. Se forem diferentes, você está atrás
de CGNAT. O IP da WAN começando em `100.64.` a `100.127.` é o sinal clássico.

Mesmo com IP público, abrir a porta 443 do roteador doméstico significa expor o
endereço da sua casa, cuidar de certificado TLS e de DNS dinâmico por conta.

O túnel inverte a direção: **a sua máquina abre uma conexão de saída** e a
Cloudflare devolve o tráfego por dentro dela. Nenhuma porta aberta, TLS
resolvido do lado deles, IP de casa invisível, e funciona atrás de CGNAT.

```
navegador → https://revsist.com → Cloudflare → [conexão de saída] → cloudflared → api:8000
                                    TLS aqui                        sua máquina
```

---

## 43.2 O que já está pronto no projeto

Três coisas que não precisam ser construídas:

| Já existe | Onde | Consequência |
|---|---|---|
| O backend serve o SPA | `backend/app/main.py:308-332` | **Não precisa de Caddy nem nginx.** Um processo só atende `/`, `/app` e `/api` |
| A interface aceita túnel | `frontend/src/api/backendUrl.ts:21-24` e a CSP do `index.html` | O app de mesa consegue apontar para o servidor publicado |
| Perfil `server` | `RSAC_DEPLOYMENT_PROFILE=server` | Fecha a documentação da API, exige `RSAC_SECRET_KEY`, recusa token local |

**O que a Fase 4 perde nesta variante:** as tarefas 4.1 a 4.5 previam Caddy com
TLS automático. Com a Cloudflare terminando o TLS, o Caddy sai. Tarefas 4.7
(endurecer o hospedeiro por SSH/ufw/fail2ban) também saem — não há hospedeiro
remoto a endurecer. O que **não** sai é 4.8 (cifra em repouso), 4.11 e 4.12
(backup e restauração testada); em máquina de casa elas pesam mais, não menos.

---

## 43.3 Antes de começar

- [ ] Conta na Cloudflare (gratuita)
- [ ] `revsist.com` com os servidores DNS apontados para a Cloudflare — troca no
      registrador onde você comprou; leva de minutos a algumas horas
- [ ] Docker Desktop com WSL2 instalado
- [ ] **BitLocker ligado no disco** onde ficarão o banco e os PDFs. Windows Home
      não tem BitLocker completo; se for o seu caso, veja §43.6
- [ ] Um destino de backup **fora desta máquina**

---

## 43.4 Os arquivos

Tudo em contêiner, inclusive o túnel. Assim o mesmo comando sobe em casa hoje e
num VPS depois, sem nada reescrito.

### `Dockerfile` (na raiz)

```dockerfile
# Dois estágios: o primeiro compila a interface, o segundo roda a API — que
# também serve os arquivos compilados. Uma imagem, um processo.
FROM node:20-alpine AS interface
WORKDIR /front
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build:web

FROM python:3.12-slim
# Execução sem privilégio (tarefa 4.1 do doc 41).
RUN useradd --create-home --uid 10001 revsist
WORKDIR /app

COPY backend/pyproject.toml ./backend/
COPY backend/app ./backend/app
COPY backend/alembic ./backend/alembic
COPY backend/alembic.ini backend/run.py ./backend/
RUN pip install --no-cache-dir -e ./backend

COPY --from=interface /front/dist ./frontend/dist

USER revsist
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=4).status==200 else 1)"
CMD ["python", "backend/run.py", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.caseiro.yml`

```yaml
# Revsist em casa, atrás de túnel Cloudflare (doc 43).
#
#   docker compose -f docker-compose.caseiro.yml up -d
#
# `restart: unless-stopped` é o que traz tudo de volta depois de o Windows
# reiniciar por atualização — que ele vai fazer, com ou sem sua permissão.

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: revsist
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?defina no .env}
      POSTGRES_DB: revsist
    volumes:
      - pgdata:/var/lib/postgresql/data
    # Sem `ports:` de propósito (tarefa 4.5): o banco só é alcançável de
    # dentro da rede do compose. Publicá-lo exporia o Postgres à sua rede
    # doméstica inteira — a TV, o celular do visitante, tudo.
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U revsist -d revsist"]
      interval: 10s
      timeout: 5s
      retries: 10

  api:
    build: .
    restart: unless-stopped
    depends_on:
      db: { condition: service_healthy }
    environment:
      RSAC_DEPLOYMENT_PROFILE: server
      RSAC_DATABASE_URL: postgresql+psycopg://revsist:${POSTGRES_PASSWORD}@db:5432/revsist
      RSAC_SECRET_KEY: ${RSAC_SECRET_KEY:?defina no .env}
      RSAC_DATA_DIR: /dados
      RSAC_PUBLIC_BASE_URL: https://revsist.com
      RSAC_CORS_ORIGINS: https://revsist.com
      RSAC_TRUSTED_HOSTS: revsist.com
      RSAC_GOOGLE_CLIENT_ID: ${RSAC_GOOGLE_CLIENT_ID:-}
      RSAC_GOOGLE_CLIENT_SECRET: ${RSAC_GOOGLE_CLIENT_SECRET:-}
    volumes:
      - dados:/dados
    # Um worker só, e isto não é para "otimizar" (doc 40 §40.6).

  tunel:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    depends_on: [api]
    command: tunnel --no-autoupdate run --token ${TUNNEL_TOKEN:?defina no .env}

volumes:
  pgdata:
  dados:
```

### `.env` (fora do repositório, ao lado do compose)

```dotenv
POSTGRES_PASSWORD=<gere uma senha longa e aleatória>
RSAC_SECRET_KEY=<gere: python -c "import secrets; print(secrets.token_urlsafe(48))">
TUNNEL_TOKEN=<a Cloudflare te dá no passo 3 de §43.5>
RSAC_GOOGLE_CLIENT_ID=
RSAC_GOOGLE_CLIENT_SECRET=
```

> ⚠️ **Acrescente `.env` ao `.gitignore` antes de criá-lo.** Esse arquivo tem a
> chave que cifra as credenciais de IA dos seus usuários; num repositório
> público ele é o fim da história.

---

## 43.5 O roteiro

1. **Apontar o domínio.** No painel da Cloudflare, *Add a site* → `revsist.com`
   → plano Free. Ela mostra dois servidores DNS; troque-os no registrador.
   Confirme que ficou "Active" antes de seguir.

2. **Criar o túnel.** Painel → *Zero Trust* → *Networks* → *Tunnels* →
   *Create a tunnel* → tipo **Cloudflared** → nome `revsist`.

3. **Copiar o token.** A tela de instalação mostra um comando com um token
   longo. **Só o token** vai para o `.env` como `TUNNEL_TOKEN` — não rode o
   comando que ela sugere; quem roda o túnel é o compose.

4. **Rotear o domínio.** Ainda no túnel, aba *Public Hostname* → *Add*:
   - Subdomínio: vazio · Domínio: `revsist.com`
   - Serviço: `HTTP` → `api:8000`

   E repita para `www.revsist.com`, se quiser.

5. **Subir.**
   ```powershell
   docker compose -f docker-compose.caseiro.yml up -d --build
   docker compose -f docker-compose.caseiro.yml logs -f api
   ```

6. **Migrar o banco e criar a primeira conta** (tarefa 4.16):
   ```powershell
   docker compose -f docker-compose.caseiro.yml exec api alembic -c backend/alembic.ini upgrade head
   docker compose -f docker-compose.caseiro.yml exec api python -m app.cli create-user seu_usuario --role owner
   ```
   A senha aparece **uma única vez** no terminal. Guarde num gerenciador.

7. **Conferir de fora.** Abra `https://revsist.com` pelo 4G do celular, com o
   wi-fi desligado. Pela rede de casa não vale: pode funcionar por caminho que
   não existe para os outros.

---

## 43.6 Os cuidados específicos do Windows

Estes não estão no doc 41 porque lá o servidor é Linux. Em máquina de uso
pessoal, cada um deles já derrubou serviço de alguém:

| Cuidado | Por quê | O que fazer |
|---|---|---|
| **Suspensão** | Máquina dormindo é serviço fora do ar, e o Windows dorme por padrão | `powercfg /change standby-timeout-ac 0` e desligar a hibernação |
| **Inicialização rápida** | Atrapalha a volta dos serviços depois de desligar | Desligar em Opções de Energia |
| **Reinício por atualização** | Vai acontecer, provavelmente de madrugada | Definir horário ativo; o `restart: unless-stopped` traz tudo de volta |
| **Docker Desktop não sobe sozinho** | Sem isso, nada volta depois do reinício | Marcar "Start Docker Desktop when you sign in" — e **fazer login automático** ou os contêineres só sobem quando você logar |
| **Antivírus** | Varredura em tempo real na pasta de PDFs derruba muito o desempenho | Excluir os volumes do Docker da varredura |
| **BitLocker** | Item L-49: cifra em repouso. Windows Home não tem a versão completa | Se for Home: considerar Veracrypt no volume, ou aceitar que este é um limite conhecido do arranjo |

**Backup (tarefas 4.11 e 4.12).** Diário, e para fora desta máquina:

```powershell
docker compose -f docker-compose.caseiro.yml exec -T db pg_dump -U revsist -Fc revsist > backup.dump
docker run --rm -v revsistv2_dados:/d -v ${PWD}:/saida alpine tar czf /saida/pdfs.tar.gz -C /d .
```

Agende no Agendador de Tarefas e mande para um destino externo. **E teste a
restauração pelo menos uma vez** — backup nunca conferido é hipótese, não
salvaguarda.

---

## 43.7 O limite deste arranjo

Aqui está a parte que não é técnica, e ela merece uma decisão consciente.

**Enquanto o Revsist é só seu**, hospedar em casa é uma escolha razoável de
custo. **A partir da primeira conta de outra pessoa**, você passa a guardar dado
pessoal de terceiro — nome, e-mail, e o conteúdo da pesquisa dela — num
computador que você também usa para navegar, instalar programas e trabalhar.

Isso não é ilegal. Mas o art. 46 da LGPD exige medidas de segurança adequadas,
e você é o controlador. Se algo vazar, a pergunta será o que você fez para
evitar — e "estava no meu computador pessoal, com antivírus" é uma resposta
difícil de sustentar. Não pelo antivírus: pela **mistura**. Todo programa que
você instala para uso pessoal passa a ser risco para o dado de outra pessoa.

**A linha que eu proporia:**

| Situação | Máquina de casa serve? |
|---|---|
| Só você usando | ✅ sim |
| 5 a 10 pessoas que você conhece, avisadas de que é BETA | ⚠️ aceitável, com backup e cifra em dia |
| Cadastro público aberto | ❌ não |

Um VPS pequeno é a diferença entre "dado de terceiro no computador onde eu jogo
e leio e-mail" e "dado de terceiro numa máquina que só faz isso" — e o mesmo
compose sobe nos dois lugares.

---

## 43.8 Limites técnicos herdados

| Limite | Valor | Consequência |
|---|---|---|
| Corpo de requisição pela Cloudflare | **100 MB** (planos Free e Pro) | O teto de PDF de 50 MB (§40.7.5) cabe. Aumentar esse teto depois esbarra aqui |
| Túneis por conta | 1 000 | Irrelevante |
| WebSocket | funciona | A coleta com progresso ao vivo continua funcionando |
| Upload da sua internet | o que seu plano der | É o gargalo real: a banda de **subida** residencial costuma ser uma fração da descida, e é ela que serve as páginas |

---

## 43.9 Quando migrar para VPS

O gatilho não é técnico, é o de §43.7: **antes de abrir cadastro público.**

A migração é curta porque nada foi escrito de forma específica para casa:

1. Subir o mesmo `docker-compose.caseiro.yml` no VPS
2. Restaurar o `pg_dump` e o `pdfs.tar.gz`
3. Reapontar o *Public Hostname* do túnel para o novo destino — ou dispensar o
   túnel e usar Caddy, como o doc 41 previa
4. Desligar em casa

O DNS não muda, o domínio não muda, os usuários não percebem.

---

## 43.10 Antes de deixar a primeira pessoa entrar

- [ ] `https://revsist.com` responde de uma rede que não é a sua
- [ ] `RSAC_DEPLOYMENT_PROFILE=server` confirmado (a documentação da API tem de
      estar fechada em `/docs`)
- [ ] Postgres **não** acessível da rede local: `docker compose ps` não mostra
      porta publicada em `db`
- [ ] `.env` fora do repositório e no `.gitignore`
- [ ] Backup rodando **e restaurado uma vez**, com o tempo anotado
- [ ] BitLocker ou equivalente ativo
- [ ] Suspensão desligada; máquina volta sozinha depois de um reinício de teste
- [ ] **Os três marcadores do aviso preenchidos** — `[NOME COMPLETO]`,
      `[E-MAIL DE CONTATO]` e `[CIDADE/ESTADO]`, em
      `backend/app/legal/aceite.py`. Enquanto sobrarem, o teste
      `test_lacunas_de_identificacao_continuam_marcadas` falha de propósito
- [ ] Fases 3.1 a 3.3 concluídas — **sem `DELETE /me` não há como atender um
      pedido de eliminação**, e o art. 18 dá prazo para responder
- [ ] `/privacidade` e `/termos` no ar (tarefa 3.14), com o seu nome e contato

---

## 43.11 A ciência do aviso, exigida antes de tudo

Quem entra pela primeira vez no perfil `server` vê o aviso do BETA e precisa
marcar que o leu. O texto vive em `backend/app/legal/aceite.py`, versionado com
o código — o que a pessoa aceitou em março continua recuperável em dezembro,
pelo histórico do git.

Três decisões que não são estéticas:

- **A trava é do router**, como a de sessão: `api_router` exige
  `require_aceite`, e uma rota nova nasce protegida. Ficam de fora só as duas
  que alguém sem aceite precisa alcançar — ler o aviso e sair.
- **O botão só habilita depois de o texto ser rolado até o fim.** Não é para
  atrapalhar: é para que "li" tenha alguma chance de ser verdade.
- **O aviso não recolhe consentimento para a IA.** Envio ao provedor é
  transferência internacional e exige consentimento específico (art. 33, VIII);
  o art. 8º §4º anula autorização genérica. Juntar as duas coisas invalidaria
  justamente a que mais precisa valer. O consentimento da IA é pedido no
  momento do uso, por projeto (Fase 3.12).

Ao ligar isso apareceu um defeito anterior: `_resolver_conta` gravava
`terms_accepted_at = agora` no instante em que uma conta nascia por Google, sem
que nada tivesse sido mostrado a ninguém. Registrar aceite que não houve é pior
do que não registrar — fabrica prova. A migração `5be6edabe4f8` anula esses
registros, e as pessoas passam a ver a tela.

---

## 43.12 O que este documento consertou ao ser escrito

Escrever o `Dockerfile` obrigou a executar o `pip install -e ./backend` num
diretório limpo, e ele falhava:

```
error: Multiple top-level packages discovered in a flat-layout: ['app', 'alembic']
```

`alembic/` fica ao lado de `app/`, e o setuptools recente recusa o layout plano
por ambiguidade em vez de escolher sozinho. Não aparecia no dia a dia porque o
ambiente virtual do repositório foi criado antes de a checagem existir, e
porque nada mais instala o pacote a partir do zero.

Junto veio um segundo defeito: `readme = "README.md"` apontava para um arquivo
que não existe em `backend/`.

Os dois estão corrigidos em `backend/pyproject.toml`, com
`[tool.setuptools.packages.find]` restringindo a descoberta a `app*`. A
verificação é uma linha, e vale rodar depois de qualquer mexida em empacotamento:

```bash
python3.12 -m venv /tmp/v && /tmp/v/bin/pip install -e ./backend \
  && /tmp/v/bin/python -c "import app.main"
```
