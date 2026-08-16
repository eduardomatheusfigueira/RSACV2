# 15 — Plano de Execução do Desenvolvimento

> **Objetivo:** transformar o diagnóstico (doc 13) e a especificação (doc 14) em
> uma sequência executável de trabalho, com critérios de aceite verificáveis.
>
> Cada fase entrega valor observável e é independentemente reversível. A ordem
> **não é negociável** em dois pontos, marcados com ⛔ — há dependências onde
> inverter a ordem transforma bug silencioso em crash.

---

## 15.1 Estratégia

**Refatorar por dentro, não reescrever.** A arquitetura da V2 (FastAPI + camadas
+ ORM + Electron) está certa; o que falta é profundidade de comportamento. Cada
fase troca o miolo de um componente mantendo a fronteira, para que a aplicação
continue subindo entre fases.

**A V1 é o oráculo.** Ela roda em produção há tempo suficiente para que seu
comportamento seja a especificação de fato. Onde V1 e V2 divergem, **V1 vence
por padrão** — desvios exigem justificativa escrita. A Fase 6 mede isso
numericamente.

**Validação primeiro, funcionalidade depois.** A Fase 0 existe para que qualquer
afirmação sobre "funciona" passe a ser verificável. Sem isso, cada correção
posterior é fé.

### Sequência

```
Fase 0 ─ Estabilização e observabilidade         (~1 dia)   ⛔ bloqueia tudo
   │
Fase 1 ─ Contrato de coleta e filtros ponta a ponta (~4 dias)
   │
   ├── Fase 2 ─ Coletores em paridade com a V1   (~7 dias)  ← maior esforço
   │
   └── Fase 3 ─ Execução: jobs, cancelamento, progresso (~4 dias)
              │
        Fase 4 ─ Deduplicação e persistência escaláveis (~3 dias)
              │
        Fase 5 ─ Enriquecimento (detalhes BDTD, resumo Scopus) (~3 dias)
              │
        Fase 6 ─ Validação de paridade e fechamento PRISMA (~3 dias)
```

Fases 2 e 3 são paralelizáveis: tocam arquivos disjuntos (`harvesters/` vs
`services/` + `api/`), acopladas apenas pelo contrato congelado na Fase 1.

**Estimativa total: 21–25 dias úteis** para uma pessoa. Com Fases 2 e 3 em
paralelo, ~17 dias.

---

## 15.2 Escopo: dentro, fora, e por quê

**Dentro:**
- Correção completa de BDTD, SciELO e OpenAlex (as três fontes do caso de uso real)
- Contrato de coleta, filtros ponta a ponta, credenciais de fontes
- Execução de jobs com cancelamento, retomada e progresso real
- Deduplicação escalável e persistência em lote
- Suíte de validação de paridade V1↔V2

**Fora (registrado, não esquecido):**
- **PubMed em profundidade** — `.agents/AGENTS.md` define o domínio como Ciências
  Sociais Aplicadas, não saúde. Recebe as correções estruturais da Fase 2
  (paginação, rótulos de resumo) mas **não** entra na validação de paridade da
  Fase 6. Custo-benefício ruim para o uso real.
- **Migração de dados da V1** — os SQLite da V1 (`2_bdtd_metadata.db` etc.) não
  são importados. Se o autor quiser aproveitar coletas anteriores, isso é um
  épico próprio (mapear 5 esquemas distintos para o modelo unificado). **Decidir
  na Fase 1** se entra no escopo.
- **Novas bases** (Web of Science, Dimensions, CAPES) — só depois da paridade.
- **Redesenho da triagem por IA** — funciona; melhorias são backlog separado.

---

## 15.3 Decisões que precisam do autor antes da Fase 1

Três premissas mudam o dimensionamento do trabalho. Nenhuma bloqueia a Fase 0.

| # | Questão | Impacto se não decidida |
|---|---|---|
| 1 | **Descritores: par obrigatório ou orientação?** (§14.8) | 140 descritores × ilimitado vs 15 × 500 é uma ordem de grandeza no dimensionamento das Fases 3 e 4 |
| 2 | **Importar dados das coletas V1?** | Épico adicional de ~4 dias |
| 3 | **Scopus e PubMed continuam no produto?** | Se sim, Fase 2 cresce ~3 dias e credenciais viram P0 |

Recomendação deste plano, caso a decisão não venha a tempo: (1) avisar sem
bloquear; (2) não importar; (3) manter ambos, mas fora da validação de paridade.

---

## Fase 0 — Estabilização e observabilidade ⛔

**Duração:** ~1 dia · **Objetivo:** a aplicação sobe em máquina limpa e é possível
observar o que a coleta faz.

Nada aqui muda comportamento de coleta. É o piso para tudo o que vem depois.

### Tarefas

**0.1 · Declarar as dependências ausentes** — corrige P0-1

```toml
# backend/pyproject.toml
"beautifulsoup4>=4.12.0",
"lxml>=5.3.0",
"pandas>=2.2.0",
```

`lxml` porque `html.parser` é tolerante demais com o HTML do SciELO e produz
parsing inconsistente em páginas malformadas. Trocar
`BeautifulSoup(res.text, "html.parser")` por `"lxml"` em `harvesters/scielo.py:175`.

**0.2 · Restabelecer a verificação TLS** — corrige P2-1

Remover `verify=False` de `harvesters/bdtd.py:108`. Se a cadeia do IBICT
realmente falhar, apontar um bundle de CA explícito — **nunca** desligar.
Registrar o resultado, é insumo do doc 16.

**0.3 · Corrigir o escopo de `total_for_desc`** — corrige P2-3 ⛔

Mover a inicialização para **antes** do laço de descritores nos cinco coletores
(`bdtd.py:115`, `scielo.py:147`, `openalex.py:56`, `pubmed.py:43`,
`scopus.py:46`).

> ⛔ **Precede obrigatoriamente 0.4.** Hoje o `NameError` está escondido atrás de
> `if on_progress:` com `on_progress` sempre `None`. Ligar o progresso antes de
> corrigir o escopo transforma um bug latente em crash de produção.

**0.4 · Ligar o progresso ponta a ponta** — corrige P0-2

Três mudanças que precisam entrar **juntas**:

1. `base.py:53` → `Callable[[HarvestProgress], Awaitable[None]] | None`
2. Todo `on_progress(...)` nos coletores → `await on_progress(...)`
3. `harvesting_service.py:135` → passar `on_progress=on_progress_callback`

**0.5 · Reconciliar runs fantasma na subida** — parte de P2-5

No `lifespan` de `app/main.py`: todo `HarvestRunModel` com `status == "running"`
vira `failed` com `error_message = "Interrompida por reinício do servidor."`
Sem isso, a UI mostra coletas eternamente "em execução".

**0.6 · Log estruturado da coleta**

Handler dedicado gravando em `settings.data_dir / "logs" / "harvest-{date}.log"`,
com nível ajustável. A V1 fazia isso por fonte (`setup_logging`,
`bdtd_harvester.py:30`) e foi o que permitiu diagnosticar problemas em produção.
Hoje a V2 loga para stdout, que no Electron empacotado **não vai para lugar nenhum**.

**0.7 · Corrigir o `enabled` ignorado na UI**

`HarvestPage.tsx:251-270` deve desabilitar visualmente fontes com
`enabled: false` e explicar o motivo ("requer chave de API").

### Critérios de aceite

- [ ] `pip install -e .` em venv limpo → `uvicorn app.main:app` sobe sem erro
- [ ] `python -c "from app.harvesters.factory import HarvesterFactory"` funciona
- [ ] Nenhum `verify=False` no código (`grep -rn "verify=False" backend/`)
- [ ] Coleta com `descriptors=[]` e `descriptors=["  "]` não levanta `NameError`
- [ ] `harvest_progress` chega ao navegador (visível no DevTools → Network → WS)
- [ ] Arquivo de log criado em `data_dir/logs/`
- [ ] Backend reiniciado no meio de uma coleta → run aparece como `failed`

---

## Fase 1 — Contrato de coleta e filtros ponta a ponta

**Duração:** ~4 dias · **Objetivo:** o recorte de busca do autor
(`1970–2023`, `pt/en/es`, teses+dissertações) passa a ser expressável e chega
até os coletores.

Esta fase congela o contrato do qual as Fases 2 e 3 dependem. **Terminar antes
de paralelizar.**

### Tarefas

**1.1 · Contrato** (`backend/app/harvesters/base.py`) — §14.2

`HarvestQuery`, `HarvesterCapabilities`, `RawPaperRecord` ampliado com
`__post_init__` defensivo, `HarvestProgress` com fases.

**1.2 · Vocabulário canônico** (`backend/app/domain/enums.py`) — §14.2.4

`DocumentType` + `to_canonical(source, raw)` + `to_native(source, canonical)`.
Tabelas de mapeamento como dados, não `if/elif` — a V1 usava cadeias de `elif`
(`translate_format`, `bdtd_harvester.py:559`) e isso não escala para 5 fontes.

**1.3 · Persistir o recorte no protocolo** — §14.8

- `ProtocolModel.search_filters` (Text/JSON) + migração Alembic
- `ProtocolUpdate` / `ProtocolResponse` com `search_filters`
- Resolução: protocolo → sobrescrito por `HarvestStartRequest`

**1.4 · Credenciais de fontes** — §14.7, corrige P0-4

- `SourceCredentialModel` + migração
- `GET/PUT /api/v1/settings/sources` — resposta **nunca** inclui a chave, só
  `has_key` e 4 últimos dígitos
- `HarvesterFactory` passa a receber as credenciais resolvidas
- `MissingCredentialsError` em `domain/exceptions.py`

**1.5 · Registro em vez de `if/elif`** (`harvesters/factory.py`)

```python
_REGISTRY: dict[str, type[BaseHarvester]] = {}

def register(cls): _REGISTRY[cls.source_name.upper()] = cls; return cls
```

`GET /harvest/sources` passa a derivar de `capabilities` em vez da lista
hardcoded (`api/v1/harvest.py:96-127`), que hoje já diverge da fábrica.

**1.6 · UI de filtros**

- `ProtocolPage`: bloco "Recorte da Busca" (anos, idiomas, tipos, acesso aberto)
- `HarvestPage`: resumo do recorte vigente + aviso de pós-filtro local, dirigido
  por `capabilities` — o usuário precisa ver que "idioma na BDTD é filtrado
  depois de baixar"
- `SettingsPage`: chaves de API por base
- Aviso (não bloqueio) em descritores com 3+ termos — pendente da decisão §15.3

### Critérios de aceite

- [ ] Recorte salvo no protocolo sobrevive a reinício do backend
- [ ] `HarvestQuery` construído a partir do protocolo, com override por execução
- [ ] `GET /settings/sources` nunca devolve a chave em claro (teste automatizado)
- [ ] Chave do Scopus persiste e é lida pela fábrica
- [ ] UI desabilita filtros não suportados e explica o porquê
- [ ] `HarvestRunModel` grava o `HarvestQuery` efetivo serializado

---

## Fase 2 — Coletores em paridade com a V1

**Duração:** ~7 dias · **Objetivo:** cada coletor recupera o mesmo volume e a
mesma qualidade de metadados que o script V1 equivalente.

Maior fase e o coração do problema. Ordem por impacto no uso real.

### 2.1 · BDTD (~2,5 dias) — §14.3

| Correção | Refs |
|---|---|
| `summary` list → join | P0-5 · `bdtd.py:197` vs `bdtd_harvester.py:923` |
| Página 20 → 100 | P1-2 · `bdtd.py:117` |
| `sort` relevance → year | P1-2 · `bdtd.py:134` |
| Filtros + regra WAF (máx 2) | P1-3 · portar `sanitize_bdtd_filters:83` |
| Pós-filtro local de idioma | `bdtd_harvester.py:835-844` |
| Backoff de 15 s em 429 | P2-2 · `bdtd_harvester.py:858-860` |
| Espelho só após esgotar retry | P2-2 · `bdtd.py:142` |
| Logar respostas não-200 | P2-2 (ramo mudo) |
| Dedup intra-execução por `record_id` | P2-4 · `bdtd_harvester.py:873` |
| `matched_descriptor` | §14.2.3 |

Raspagem de detalhes fica na **Fase 5** (é opcional e cara).

### 2.2 · SciELO (~1,5 dia) — §14.4

| Correção | Refs |
|---|---|
| **Retry por status** (429/5xx, backoff 1.5, 5 tentativas) | P2-2 · `scielo_harvester.py:341-349` |
| `journal` fora de `institution` | §14.2.3 · `scielo.py:103` |
| `RE_TOTAL_HITS` como fallback | `scielo.py:25` (morta) vs `scielo_harvester.py:393` |
| DOI inválido → `None`, não texto cru | `scielo.py:91` |
| Pós-filtros locais (ano, idioma, tipo) | §14.4 |
| `matched_descriptor` | §14.2.3 |

⚠️ Único coletor por raspagem. Fixtures de HTML são obrigatórias (doc 16).

### 2.3 · OpenAlex (~1,5 dia) — §14.5

Sim, mesmo "funcionando".

| Correção | Refs |
|---|---|
| **Cursor paging** (remove teto de 10k) | P1-4 · `openalex.py:74` vs `openalex_harvester.py:515` |
| `title_and_abstract.search` | P1-4 · `openalex.py:72` |
| Página 25 → 50 | `openalex.py:57` |
| `title` `None` → `AttributeError` | `openalex.py:118` |
| `source_id` sem prefixo de URL | §14.5 |
| Filtros nativos (ano, idioma, tipo, OA) | P1-7 |
| `mailto` no User-Agent + `api_key` | `openalex_harvester.py:450, 485` |
| `journal` fora de `institution` | `openalex.py:115` |

### 2.4 · PubMed (~1 dia) — §14.6

`retmax=10000` + `retstart`; lote 25 → 100; rótulos do resumo preservados; pular
PMIDs já coletados; filtros por sintaxe de query.

### 2.5 · Scopus (~1 dia) — §14.7

`view=COMPLETE`; **Abstract Retrieval** quando o resumo vier vazio (P1-6);
cursor paging; `insttoken`; `MissingCredentialsError` em vez de retorno vazio
(P0-4).

### Critérios de aceite

- [ ] Para cada fonte, mesmo descritor e recorte da V1 → contagem dentro de **±5%**
- [ ] BDTD: 100% dos registros com resumo em `str` (nunca `list`)
- [ ] BDTD: 3 filtros pedidos → no máximo 2 `filter[]` na URL (asserção sobre a requisição)
- [ ] SciELO: HTTP 500 injetado → retry, sem perder o descritor
- [ ] OpenAlex: descritor com >10.000 resultados → passa dos 10.000
- [ ] Scopus: >90% dos registros com resumo não vazio
- [ ] Scopus sem chave → run `failed` com mensagem acionável, não `completed` 0
- [ ] Todo registro tem `matched_descriptor` preenchido

---

## Fase 3 — Execução: jobs, cancelamento e progresso

**Duração:** ~4 dias · **Objetivo:** coleta longa é observável, cancelável e não
derruba o servidor. Corrige P0-3(c) e P2-5.

### 3.1 · Tirar a coleta do event loop da API

`BackgroundTasks` (`api/v1/harvest.py:58`) compartilha o loop do servidor. Duas
opções:

| | A — `asyncio.Task` + executor | B — processo separado |
|---|---|---|
| Esforço | ~1 dia | ~3 dias |
| Cancelamento | `task.cancel()` | sinal IPC |
| Sobrevive a reload | não | sim |
| Complexidade Electron | nenhuma | `python-manager.ts` precisa gerenciar 2 processos |

**Recomendação: A.** O produto é desktop mono-usuário; um `asyncio.Task`
gerenciado com todo I/O de banco em `run_in_executor` resolve o bloqueio sem o
custo operacional de B. Reavaliar só se surgir necessidade multiusuário.

```python
class HarvestJobManager:
    _jobs: dict[str, asyncio.Task]
    async def start(self, run_id, coro) -> None
    async def cancel(self, run_id) -> bool
    def is_running(self, project_id) -> bool
```

### 3.2 · Endpoints de controle

- `POST /projects/{id}/harvest/cancel` → `status="cancelled"`
- `GET /projects/{id}/harvest/status` → estado atual (a UI não pode depender só
  do WebSocket, que pode cair)
- Recusar coleta concorrente no mesmo projeto (evita corrida na dedup)

### 3.3 · Fontes em paralelo, com limite

A UI já promete simultaneidade (`HarvestPage.tsx:2, 247`); o backend roda em
série (`harvesting_service.py:101`). Alinhar:

```python
sem = asyncio.Semaphore(3)   # 3 fontes simultâneas
await asyncio.gather(*(run_source(s) for s in sources))
```

Limite por fonte também — o `delay` de cada `capabilities` continua valendo
dentro de cada coletor. Falha de uma fonte **não** aborta as outras
(`return_exceptions=True`).

### 3.4 · Progresso em lote

Substituir o broadcast por registro (`harvesting_service.py:147-159`):

- `harvest_progress` a cada página
- `harvest_batch` a cada 25 registros **ou** 2 s, o que vier primeiro
- Amostra dos últimos 5 títulos, não todos — o feed da UI já trunca em 500
  (`HarvestPage.tsx:148`)
- Incluir `paper_id`, que a UI já espera e nunca recebe (`HarvestPage.tsx:151`)

Com 20.000 papers, isso troca 20.000 mensagens por ~800.

### 3.5 · Retomada

`HarvestRunModel` ganha `checkpoint` (JSON: descritor atual, página/cursor).
Coleta cancelada ou interrompida pode ser retomada do último descritor concluído.

### Critérios de aceite

- [ ] Coleta de 140 descritores → API continua respondendo (`GET /projects` < 200 ms)
- [ ] Cancelar interrompe em < 5 s e marca `cancelled`
- [ ] 3 fontes rodam simultaneamente (verificável no log)
- [ ] Falha em uma fonte não impede as demais
- [ ] WebSocket sobrevive a 30 min de coleta sem desconectar
- [ ] Retomada continua do checkpoint, sem reprocessar descritores concluídos

---

## Fase 4 — Deduplicação e persistência escaláveis

**Duração:** ~3 dias · **Objetivo:** eliminar o O(N²). Corrige P0-3(a) e (b).

### 4.1 · Bloqueio por chave (blocking key)

O passo 3 hoje compara contra **todos** os papers (`dedup_service.py:87-91`).
Substituir por candidatos filtrados:

```python
# coluna nova, indexada: primeiras 4 palavras do título normalizado
blocking_key: Mapped[str] = mapped_column(String(120), index=True)
```

Candidatos = mesmo `blocking_key` **ou** (mesmo ano **e** primeiro token igual).
Reduz de *N* para tipicamente < 20 comparações fuzzy por registro. Custo: um
índice e uma migração que recalcula a coluna para papers existentes.

### 4.2 · Índices e caminho rápido

- Índice único `(project_id, source_name, source_id)` em `paper_sources` →
  descarte O(1) de registro já visto da mesma fonte
- Índice `(project_id, doi)` — hoje `ix_papers_doi` não inclui `project_id`
  (`models.py:122`), então o passo 1 varre entre projetos
- Índice `(project_id, title_normalized)` pelo mesmo motivo (`models.py:123`)

### 4.3 · Persistência em lote

Espelhar `insert_batch` da V1 (`bdtd_harvester.py:701`): acumular 100 registros e
gravar em uma transação. Um `commit` por lote, não por registro
(`dedup_service.py:152, 183`).

### 4.4 · WAL no SQLite

`PRAGMA journal_mode=WAL` na inicialização — a V1 faz
(`scielo_harvester.py:182`), a V2 não faz em lugar nenhum. Permite leitura
concorrente durante a escrita da coleta (a UI consegue listar papers enquanto
coleta roda).

### 4.5 · Tirar o banco do event loop

Todo o bloco de dedup+persistência via
`await loop.run_in_executor(pool, persist_batch, ...)`, com uma `Session` por
lote. Fecha o P0-3(c) junto com a Fase 3.

### Critérios de aceite

- [ ] 20.000 registros processados em **< 10 min** (hoje: horas — medir antes)
- [ ] Tempo por lote **constante** ao longo da coleta (não cresce com *N*)
- [ ] Taxa de detecção de duplicatas **igual** à do algoritmo atual sobre o mesmo
      conjunto (o bloqueio não pode perder duplicata — teste com conjunto rotulado)
- [ ] `EXPLAIN QUERY PLAN` mostra uso de índice em todas as consultas de dedup
- [ ] Event loop nunca bloqueado > 100 ms (medir com `asyncio` debug mode)

---

## Fase 5 — Enriquecimento de metadados

**Duração:** ~3 dias · **Objetivo:** recuperar a qualidade de metadados da V1
que a V2 nunca teve. Corrige P1-1 e P1-6.

### 5.1 · Raspagem de detalhes da BDTD (~2 dias) — §14.3

Portar `scrape_record_details` (`bdtd_harvester.py:577`) e as funções de limpeza:
`clean_advisor_name:153`, `clean_creator_name:133`, `process_record_fields:195`,
`get_source_info:626`, `translate_format:559`.

Melhorias sobre a V1:

- Raspar **só** o que sobreviveu à dedup intra-execução
- `asyncio.Semaphore(4)` em vez de sequencial (V1 é serial com 1 s de pausa)
- Cache por `record_id` no disco, para retomada sem re-raspar
- Flag `fetch_details` na UI: *"Coleta rápida (sem orientador e instituição)"*

`advisor` precisa aparecer em `PaperModel`, na exportação e na UI — não adianta
coletar e não mostrar.

### 5.2 · Resumo do Scopus (~1 dia) — §14.7

`view=COMPLETE`; quando `dc:description` vier vazio, chamar Abstract Retrieval
por EID (`scopus_harvester.py:173`), tratando o caso `{"$": "..."}` (`:193`).

### Critérios de aceite

- [ ] >90% dos registros BDTD com `advisor` preenchido (quando existe na fonte)
- [ ] >95% com `institution` = instituição de defesa (não "BDTD/IBICT" genérico)
- [ ] `research_type` no vocabulário canônico, nunca `masterThesis` cru
- [ ] Zero casos de "Orientador: …" dentro do campo de resumo
- [ ] `fetch_details=False` → coleta ao menos 5× mais rápida
- [ ] Scopus: >90% com resumo

---

## Fase 6 — Validação de paridade e fechamento

**Duração:** ~3 dias · **Objetivo:** provar numericamente que a V2 ≥ V1.

### 6.1 · Suíte de paridade

Detalhada em `16_TESTES_VALIDACAO.md`. Para um conjunto fixo de descritores e
recorte, roda V1 e V2 contra a mesma base e compara volume, cobertura de campos
e sobreposição de identificadores.

**Critério de aprovação:** para BDTD, SciELO e OpenAlex —
volume dentro de ±5%, sobreposição de IDs ≥ 95%, e cobertura de campo
(resumo, autores, ano, DOI) **maior ou igual** à da V1.

### 6.2 · Fluxo PRISMA correto

`export_service.get_prisma_flow_data` precisa refletir a nova realidade:
identificados por base, duplicatas removidas, excluídos por filtro **local**
(hoje não existe esse número), triados, incluídos.

Registros removidos por pós-filtro local **não** são "excluídos na triagem" — são
"não elegíveis por critério de recorte". Confundir os dois invalida o diagrama.

### 6.3 · Documentação

Atualizar `README.md` e `00_INDICE.md`; escrever `17_GUIA_DE_USO.md` (já entregue
neste pacote); registrar em `08_PIPELINE_DADOS.md` o pipeline real.

### Critérios de aceite

- [ ] Paridade aprovada nas 3 fontes prioritárias
- [ ] Diagrama PRISMA bate com a contagem do banco
- [ ] Exportação Excel com todas as abas, incluindo `advisor` e `matched_descriptor`
- [ ] Ciclo completo em máquina limpa: criar projeto → protocolo → coletar →
      triar → extrair → exportar

---

## 15.4 Mapa de arquivos por fase

| Arquivo | F0 | F1 | F2 | F3 | F4 | F5 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `backend/pyproject.toml` | ✏️ | | | | | |
| `app/harvesters/base.py` | ✏️ | 🔨 | | | | |
| `app/harvesters/factory.py` | | 🔨 | | | | |
| `app/harvesters/bdtd.py` | ✏️ | | 🔨 | | | ✏️ |
| `app/harvesters/scielo.py` | ✏️ | | 🔨 | | | |
| `app/harvesters/openalex.py` | ✏️ | | 🔨 | | | |
| `app/harvesters/pubmed.py` | ✏️ | | ✏️ | | | |
| `app/harvesters/scopus.py` | ✏️ | | ✏️ | | | ✏️ |
| `app/services/harvesting_service.py` | ✏️ | ✏️ | | 🔨 | ✏️ | |
| `app/services/dedup_service.py` | | | | | 🔨 | |
| `app/services/export_service.py` | | | | | | ✏️ |
| `app/api/v1/harvest.py` | ✏️ | ✏️ | | 🔨 | | |
| `app/api/v1/protocols.py` | | ✏️ | | | | |
| `app/schemas/harvest.py` | | 🔨 | | | | |
| `app/schemas/protocol.py` | | ✏️ | | | | |
| `app/domain/enums.py` | | 🔨 | | | | |
| `app/infrastructure/persistence/models.py` | | ✏️ | | ✏️ | ✏️ | ✏️ |
| `app/config.py` | ✏️ | | | | | |
| `app/main.py` | ✏️ | | | | ✏️ | |
| `frontend/…/HarvestPage.tsx` | ✏️ | ✏️ | | ✏️ | | ✏️ |
| `frontend/…/ProtocolPage.tsx` | | 🔨 | | | | |
| `frontend/…/SettingsPage.tsx` | | ✏️ | | | | |
| `frontend/src/types/api.ts` | | ✏️ | | ✏️ | | |

🔨 reescrita substancial · ✏️ alteração pontual

**Migrações Alembic:** F1 (`search_filters`, `source_credentials`),
F3 (`checkpoint`), F4 (`blocking_key` + índices), F5 (`advisor`,
`matched_descriptor`, `journal`, `language`).

Hoje o projeto declara `alembic` mas não tem diretório de migrações — a Fase 1
precisa inicializar (`alembic init`) e criar a baseline do esquema atual **antes**
da primeira migração real.

---

## 15.5 Riscos

| Risco | P | Impacto | Mitigação |
|---|:--:|:--:|---|
| SciELO muda o HTML e quebra o parser | Alta | Alto | Fixtures + teste canário semanal (§16.4); parser tolerante com log de campo faltante |
| WAF da BDTD endurece (limites diferentes dos da V1) | Média | Alto | Limites em `capabilities`, ajustáveis sem deploy; medir na Fase 0 |
| Bloqueio da dedup perde duplicata real | Média | Alto | Conjunto rotulado; comparar contra o algoritmo atual antes de trocar |
| Sem entitlement para `view=COMPLETE` no Scopus | Média | Médio | Fallback para Abstract Retrieval; se falhar, degradar com aviso explícito |
| Volume real (140 desc. × ilimitado) inviável mesmo otimizado | Média | Alto | Medir cedo na Fase 4; se necessário, coleta incremental por descritor com retomada |
| Paridade não atingida por mudança do lado da fonte | Baixa | Médio | Rodar V1 no mesmo dia da V2 na Fase 6 — comparar contra V1 de hoje, não contra números históricos |
| Chaves versionadas na V1 já comprometidas | **Alta** | Alto | **Revogar hoje**, independente do plano (P2-6) |

---

## 15.6 O que muda para o usuário, fase a fase

| Depois de | O autor passa a conseguir |
|---|---|
| **F0** | Ver que a coleta está progredindo, em vez de tela parada |
| **F1** | Definir "1970–2023, pt/en/es, teses e dissertações" uma vez, valendo para todas as bases |
| **F2** | Confiar que BDTD, SciELO e OpenAlex trazem o mesmo que os scripts da V1 |
| **F3** | Rodar 140 descritores sem travar o app; cancelar e retomar |
| **F4** | Coletas grandes que terminam em minutos, não horas |
| **F5** | Orientador e instituição de defesa de volta; Scopus com resumo |
| **F6** | Publicar a revisão com diagrama PRISMA correto e auditável |

---

**Próximo documento:** [`16_TESTES_VALIDACAO.md`](./16_TESTES_VALIDACAO.md)
