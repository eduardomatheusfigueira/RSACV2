# 13 — Diagnóstico Técnico da Coleta na V2

> **Objetivo deste documento:** explicar, com evidência em código, por que a coleta
> da RSAC V2 falha ou entrega menos que a RSAC V1, e por que o OpenAlex é a única
> fonte que "parece funcionar".
>
> Todas as afirmações abaixo apontam para `arquivo:linha`. Nada aqui é hipótese
> não verificada — quando algo não pôde ser confirmado por execução real, está
> marcado como **[A VALIDAR]**.

---

## 13.1 Resumo executivo

A V2 não tem um problema de coleta. Tem **cinco problemas independentes** que se
somam, e três deles atingem todas as fontes ao mesmo tempo:

| # | Problema | Fontes afetadas | Efeito percebido pelo usuário |
|---|----------|-----------------|-------------------------------|
| 1 | Dependências não declaradas (`beautifulsoup4`, `pandas`) | SciELO, Exportação | Backend não sobe / SciELO não importa |
| 2 | Progresso nunca chega ao WebSocket | Todas | "Travou", painel parado |
| 3 | Deduplicação O(N²) com `commit` por registro, síncrona dentro do event loop | Todas | Fica cada vez mais lento; WebSocket cai |
| 4 | Chaves de API nunca chegam aos coletores | PubMed, Scopus | Scopus retorna zero, silenciosamente |
| 5 | Paginação/parsing incorretos por fonte | BDTD, SciELO, PubMed, Scopus, OpenAlex | Poucos registros, sem resumo, sem orientador |

**Por que o OpenAlex "funciona":** é a única fonte cujo caminho feliz não depende
de nenhum dos cinco. Ela é JSON puro (não precisa de `bs4`), não tem WAF, não
precisa de chave de API, e o parser da V2 está correto. Ela também é rápida o
suficiente para que o gargalo de deduplicação só apareça em coletas grandes.
**Mas ela também está quebrada** — apenas de forma silenciosa: a paginação por
offset limita a coleta a 10.000 registros por descritor (§13.6).

O ponto central: **a V1 não é "mais simples" que a V2 — ela é mais completa.**
O coletor BDTD da V1 tem 1.325 linhas; o da V2 tem 228. A diferença não é
verbosidade, é comportamento ausente. O quadro comparativo está em §13.9.

---

## 13.2 P0 — Bloqueadores (a coleta não pode funcionar de forma confiável)

### P0-1 · `beautifulsoup4` e `pandas` não estão declarados

`backend/app/harvesters/scielo.py:15` importa `bs4`; `backend/app/services/export_service.py`
importa `pandas`. Nenhum dos dois aparece em `backend/pyproject.toml`.

A cadeia de importação é fatal:

```
api/v1/router.py → api/v1/harvest.py → services/harvesting_service.py
                 → harvesters/factory.py → harvesters/scielo.py → bs4  ❌
```

Se `bs4` não estiver instalado, **a API inteira não sobe** — não é só o SciELO
que falha. Se hoje funciona na máquina do autor, é porque `bs4` entrou no
ambiente por instalação manual ou transitiva. Em máquina limpa (e no instalador
Electron empacotado) isso quebra.

`pandas` tem impacto menor e localizado: o endpoint de exportação retorna 500.

> **Correção:** adicionar `beautifulsoup4>=4.12`, `lxml>=5.0` e `pandas>=2.2` às
> dependências. `lxml` porque `html.parser` é notoriamente tolerante demais com
> o HTML do SciELO e produz parsing inconsistente em páginas malformadas.

### P0-2 · O progresso nunca sai do backend

`backend/app/services/harvesting_service.py:116` define `on_progress_callback`.
`backend/app/services/harvesting_service.py:135-138` chama o coletor **sem passá-lo**:

```python
async for raw_record in harvester.harvest(
    descriptors=descriptors,
    max_records_per_descriptor=max_records_per_descriptor,
):     # ← on_progress ausente
```

Consequência direta: a mensagem `harvest_progress` **nunca é emitida**. O painel
"Execução em Tempo Real" (`frontend/src/pages/HarvestPage.tsx:131`) só reage a
`paper_harvested`. Enquanto o coletor está paginando, buscando, sofrendo retry ou
esperando o WAF liberar, a interface fica **estática e silenciosa** — indistinguível
de um travamento. Esse é, provavelmente, o sintoma que mais fez a V2 parecer quebrada.

Há um segundo defeito acoplado: `on_progress_callback` é `async def`, mas o
contrato em `backend/app/harvesters/base.py:53` declara
`Callable[[HarvestProgress], None]` — síncrono. Os coletores chamam
`on_progress(...)` sem `await` (ex.: `harvesters/bdtd.py:120`). Se o callback
fosse passado como está, cada chamada criaria uma corrotina nunca aguardada:
nenhuma mensagem enviada e um `RuntimeWarning` por página.

> **Correção:** o contrato precisa ser explicitamente assíncrono
> (`Callable[[HarvestProgress], Awaitable[None]]`) e todas as chamadas nos
> coletores precisam de `await`. Corrigir só a passagem do parâmetro **não
> resolve** — introduz o segundo bug.

### P0-3 · Deduplicação O(N²), com commit por registro, bloqueando o event loop

Três defeitos no mesmo caminho quente.

**(a) Varredura completa por registro.** `backend/app/services/dedup_service.py:87-91`
carrega **todos** os papers do projeto a cada novo registro:

```python
candidates = (
    db.query(PaperModel.id, PaperModel.title_normalized, PaperModel.year)
    .filter(PaperModel.project_id == project_id)
    .all()
)
```

E em seguida roda `fuzz.token_sort_ratio` contra cada candidato
(`dedup_service.py:93-96`). Para *N* registros coletados, isso é *N²/2*
comparações de string. Com o volume real de uso do autor — os
`bdtd_config.json` e `scielo_config.json` da V1 trazem **140 descritores** com
`"limit": null` (ilimitado) — *N* facilmente passa de 20.000. Isso são
~200 milhões de comparações fuzzy, além de 20.000 varreduras completas da tabela.

**(b) Um `commit` por registro.** `dedup_service.py:152` e `dedup_service.py:183`
dão `db.commit()` a cada paper. Em SQLite sem WAL, cada commit é um `fsync`.
A V1 fazia o oposto — `insert_batch` com `executemany` e um único commit por
página, exatamente para evitar isso, e o código da V1 diz isso em voz alta:
"evita fsync a cada registro, aumentando a velocidade em até 100x"
(`bdtd_harvester/bdtd_harvester.py:704`). O comentário da V1 é a documentação
do erro cometido na V2.

Vale registrar: a V1 **também** habilita WAL explicitamente no SciELO
(`scielo_harvester/scielo_harvester.py:182`). A V2 não configura WAL em lugar nenhum.

**(c) Bloqueio do event loop.** `harvesting_service.py:140` chama
`self.dedup_service.process_record(db, ...)` — código SQLAlchemy **síncrono** —
de dentro de uma corrotina. Como a coleta roda via `BackgroundTasks`
(`api/v1/harvest.py:58`), ela compartilha o event loop do servidor. Cada chamada
de dedup congela o loop inteiro: o `ping/pong` do WebSocket
(`api/v1/harvest.py:136-140`) não é atendido, a conexão expira e o navegador
perde o canal. Aí nem o `paper_harvested` chega mais — a interface morre de vez.

Os três se reforçam: quanto mais o projeto cresce, mais tempo cada dedup leva,
mais tempo o loop fica travado, mais rápido o WebSocket cai.

### P0-4 · Chaves de API nunca chegam aos coletores

`harvesting_service.py:114`:

```python
harvester = HarvesterFactory.get_harvester(source_name)
```

A fábrica aceita `pubmed_api_key` e `scopus_api_key` (`harvesters/factory.py:20-23`),
mas ninguém os fornece. Resultado:

- **Scopus retorna zero, em silêncio.** `harvesters/scopus.py:34-36` faz
  `if not self.api_key: return` com log em nível `info`. Sem chave, o gerador
  encerra imediatamente; a run é marcada `completed` com 0 registros. Do ponto
  de vista do usuário, "o Scopus não achou nada" — não "o Scopus não foi configurado".
  (A UI já lista Scopus com `enabled: False` em `api/v1/harvest.py:125`, mas
  `HarvestPage.tsx:251-270` ignora esse campo e permite selecionar mesmo assim.)
- **PubMed fica no limite anônimo do NCBI** (3 req/s contra 10 req/s com chave),
  o que dispara HTTP 429 em coletas de 140 descritores.

Não existe, hoje, nenhum lugar no modelo de dados onde essas chaves possam ser
guardadas: `AISettingsModel` (`infrastructure/persistence/models.py:273`) só
cobre provedores de IA. Não há tabela nem configuração para credenciais de bases.

### P0-5 · BDTD: o resumo é uma lista, tratada como string

`backend/app/harvesters/bdtd.py:197`:

```python
abstract=rec.get("summary", "") or rec.get("description", "") or "",
```

Na API VuFind, `summary` é **uma lista de strings**, não uma string. A V1 sabe
disso e faz o join (`bdtd_harvester/bdtd_harvester.py:923-924`):

```python
summaries: List[str] = record.get('summary', [])
description: str = " ".join([s.strip() for s in summaries if s]).strip()
```

Na V2, o campo `abstract` do `RawPaperRecord` recebe um objeto `list`. Como
`RawPaperRecord` é uma `dataclass` sem validação (`harvesters/base.py:16`), nada
reclama. A lista segue até `PaperModel.abstract`, que é `Text` — o SQLAlchemy
grava a representação Python (`"['texto do resumo']"`) ou levanta erro de bind,
dependendo do driver. **[A VALIDAR]** qual dos dois ocorre no SQLite instalado.

De qualquer forma o efeito é o mesmo e é grave: **os resumos da BDTD chegam
corrompidos à triagem por IA**, que é justamente a etapa que depende deles.

---

## 13.3 P1 — Perda de cobertura e de qualidade de metadados

### P1-1 · BDTD sem raspagem de detalhes: perde orientador, instituição e tipo

Este é o maior salto de qualidade da V1 que a V2 não portou.

A V1 faz, para cada registro, uma segunda requisição à página pública do VuFind
(`bdtd_harvester/bdtd_harvester.py:577` — `scrape_record_details`), extrai as
metatags Dublin Core e as tabelas HTML de detalhe, e daí obtém:

| Campo | Função na V1 | Existe na V2? |
|---|---|---|
| Orientador(a) | `bdtd_harvester.py:945-949` + `clean_advisor_name:153` | ❌ |
| Instituição de defesa | `get_source_info:626` | ❌ (usa `institutions` cru da API) |
| Tipo de pesquisa traduzido | `translate_format:559` (Tese / Dissertação / Artigo) | ❌ (usa `formats[0]` cru) |
| Link de acesso real | `extract_url:546` + fallbacks `:964-969` | Parcial |
| Correção resumo↔orientador trocados | `process_record_fields:195` | ❌ |

Essa última merece destaque: a V1 detecta quando a BDTD devolve o nome do
orientador dentro do campo de resumo (acontece com frequência em registros de
certos repositórios), limpa o resumo e move o nome para o campo certo. Sem isso,
a V2 alimenta a triagem por IA com "Orientador: Fulano de Tal" no lugar do resumo.

A V1 também limpa nomes: remove anos de nascimento/morte
(`clean_creator_name:133`), descarta links Lattes/ORCID e nomes de instituições
que vazam para o campo de orientador (`clean_advisor_name:169-180`). A V2 aplica
apenas a limpeza de anos, e só em autores (`harvesters/bdtd.py:71`).

### P1-2 · BDTD: página de 20 em vez de 100, ordenada por relevância

`harvesters/bdtd.py:117` fixa `page_size = 20`. A V1 usa 100
(`bdtd_harvester.py:763`). Para o mesmo volume, a V2 faz **5× mais requisições**
contra um servidor que já é conhecido por aplicar rate limit agressivo — o que
aumenta a chance de 429 na mesma proporção.

`harvesters/bdtd.py:134` usa `sort: "relevance"`; a V1 usa `year`
(`bdtd_harvester.py:775`). Para revisão sistemática, ordenação por relevância
é ativamente ruim: torna o resultado dependente do ranking interno do Solr e,
combinada com limite por descritor, produz recortes não reprodutíveis. Uma
revisão sistemática precisa ser **determinística**.

### P1-3 · BDTD: a regra do WAF (máximo 2 filtros) não foi portada

A V1 documenta uma restrição real e não óbvia do servidor
(`bdtd_harvester.py:72-80`): o WAF da BDTD devolve **HTTP 429 quando a requisição
tem 3 ou mais parâmetros `filter[]`**. A V1 contorna com `sanitize_bdtd_filters`
(`:83`): manda no máximo 2 filtros à API e aplica o filtro de idioma **localmente**,
depois de receber os registros (`:835-844`).

Isso é conhecimento operacional caro, obtido por tentativa e erro. A V2 não tem
nem os filtros nem a regra — hoje o problema está latente porque a V2 não envia
filtro nenhum, mas ele reaparece no instante em que os filtros forem implementados.

### P1-4 · OpenAlex: teto silencioso de 10.000 registros por descritor

Esta é a razão pela qual "o OpenAlex está funcionando" é enganoso.

`harvesters/openalex.py:71-76` pagina por offset (`page` + `per-page`). A API do
OpenAlex limita a paginação por offset a **10.000 resultados**; além disso é
preciso usar *cursor paging*. A V1 usa cursor desde sempre
(`openalex_harvester/openalex_harvester.py:512-515`):

```python
params = {"per_page": PAGE_SIZE, "cursor": "*"}
```

Além do teto, há duas diferenças de qualidade de busca:

| Aspecto | V1 | V2 |
|---|---|---|
| Paginação | cursor (`:515`) | offset, teto 10k (`openalex.py:74`) |
| Campo de busca | `filter=title_and_abstract.search:` (`:523`) | `search=` genérico (`openalex.py:72`) |
| Página | 50 (`:514`) | 25 (`openalex.py:57`) |
| Polite pool | `mailto` no User-Agent (`:450`) + `api_key` (`:485`) | só `mailto` em query string |
| Filtros | ano, `is_oa`, tipo de fonte, repositório, editora (`:248-268`) | nenhum |

O `search=` genérico do OpenAlex procura em título, resumo **e texto completo
indexado**, o que traz muito mais ruído que o `title_and_abstract.search` da V1.
Para uma revisão sistemática, isso muda materialmente o conjunto recuperado —
e explica por que os resultados da V2 podem parecer "menos precisos" mesmo
quando a fonte tecnicamente responde.

### P1-5 · PubMed: sem paginação, teto de 500

`harvesters/pubmed.py:44`:

```python
retmax = 500 if limit == float("inf") else min(int(limit), 500)
```

Quando o usuário pede "ilimitado", a V2 entrega **no máximo 500 PMIDs por
descritor** — e não há `retstart`, então não existe segunda página. A V1 usa
`retmax: 10000` (`pubmed_harvester.py:319`), 20× mais.

A V1 ainda faz duas coisas que a V2 não faz:

- **Pula PMIDs já coletados** antes de gastar requisição de `efetch`
  (`pubmed_harvester.py:_process_keyword`, via `db.record_exists`). Com 140
  descritores que se sobrepõem muito, isso corta a maior parte do tráfego.
- **Preserva os rótulos das seções do resumo** (`BACKGROUND:`, `METHODS:` …) —
  `pubmed_harvester.py:430-434` monta `"RÓTULO: texto"`. A V2 concatena os
  `AbstractText` sem rótulo (`pubmed.py:116-120`), perdendo a estrutura que a
  IA de triagem usa para localizar método e resultado.

Lote de `efetch`: V2 usa 25 (`pubmed.py:79`), V1 usa 100 — 4× mais requisições.

### P1-6 · Scopus: sem resumo, portanto sem triagem possível

`harvesters/scopus.py:103` grava `abstract=""` — literalmente sempre vazio.
Isso ocorre porque `view=STANDARD` (`scopus.py:65`) não retorna `dc:description`.

A V1 resolve em duas frentes: usa `view: "COMPLETE"` por padrão
(`config_app/core/config_schemas.py:68`) e, quando o resumo mesmo assim não vem,
faz uma chamada dedicada à **Abstract Retrieval API**
(`scopus_harvester/scopus_harvester.py:173` — `fetch_abstract_retrieval`, com
`view=META_ABS`), tratando inclusive o caso em que `dc:description` chega como
dicionário `{"$": "..."}` em vez de string (`:193`).

A V1 também suporta `insttoken` (`scopus_harvester.py:391`), necessário para
entitlement institucional — sem ele, muitas contas não têm acesso ao `COMPLETE`.

Consequência prática: **todo paper vindo do Scopus na V2 chega à triagem sem
resumo.** A IA só vê o título. Como a triagem é o coração do produto, isso torna
a fonte inútil mesmo se a chave for configurada.

### P1-7 · Não existe nenhum filtro de busca em lugar nenhum

Nem `ProtocolUpdate` (`backend/app/schemas/protocol.py:46-59`) nem
`HarvestStartRequest` (`backend/app/schemas/harvest.py:11-19`) têm campos para
recorte de busca. A V2 só sabe pedir "tudo".

A V1 tem, por fonte (`config_app/core/config_schemas.py`):

| Fonte | Filtros disponíveis na V1 |
|---|---|
| BDTD | `format`, `institution`, `publishDate` (inclui faixa `[1970 TO 2023]`), `language` (multi), `search_type`, `sort_order` |
| SciELO | `search_field` |
| OpenAlex | `publication_year` (faixa), `language`, `type`, `is_oa`, IDs de repositório/editora/tipo de fonte |
| Scopus | `view`, `insttoken` |
| PubMed | `api_key`, `delay` dedicado |

O `bdtd_config.json` real do autor usa `"publishDate": "[1970 TO 2023]"` e
`"language": "Português, Inglês, Espanhol"`. **Esse recorte simplesmente não é
expressável na V2.** Não é um detalhe: sem recorte temporal e de idioma, uma
coleta de 140 descritores na BDTD traz um volume que inviabiliza a triagem.

---

## 13.4 P2 — Robustez, segurança e operação

### P2-1 · Verificação TLS desligada na BDTD

`harvesters/bdtd.py:108` usa `verify=False`. Isso desabilita a validação de
certificado — todo o tráfego BDTD fica exposto a interceptação, e o `httpx`
passa a emitir avisos a cada requisição. A V1 **não** faz isso; usa
`requests.Session` com verificação padrão (`bdtd_harvester.py:779`).

Se o motivo foi um erro de cadeia de certificados do IBICT, a solução correta é
apontar um bundle de CA (`verify="/caminho/ca.pem"`), nunca desligar a verificação.

### P2-2 · SciELO sem retry: um 500 mata o descritor inteiro

`harvesters/scielo.py:171-173` desiste na primeira resposta não-200:

```python
if res.status_code != 200:
    logger.warning(...)
    break
```

A V1 monta uma estratégia de retry na camada de transporte
(`scielo_harvester.py:341-349`): `total=5`, `backoff_factor=1.5`,
`status_forcelist=[429, 500, 502, 503, 504]`. O `search.scielo.org` devolve 500
e 503 intermitentes com frequência sob carga — sem retry, cada oscilação
momentânea descarta silenciosamente o restante das páginas daquele descritor.
Com 140 descritores, a coleta fica cheia de buracos invisíveis.

A BDTD da V2 tem retry (`bdtd.py:141-157`), mas com um defeito: o laço interno
percorre `BASE_URLS` e, quando a resposta é não-200 e não-429, **não faz nada** —
não loga, não espera, apenas segue para a próxima URL. Falhas 403/404 ficam mudas.

### P2-3 · `total_for_desc` fora de escopo — `NameError` latente

Em todos os cinco coletores, `total_for_desc` é inicializado **dentro** do laço
`for desc in descriptors` mas referenciado **fora** dele, no bloco final de
progresso:

| Arquivo | Inicialização | Uso fora do escopo |
|---|---|---|
| `harvesters/bdtd.py` | :115 | :225 |
| `harvesters/scielo.py` | :147 | :214 |
| `harvesters/openalex.py` | :56 | :153 |
| `harvesters/pubmed.py` | :43 | :178 |
| `harvesters/scopus.py` | :46 | :134 |

Se `descriptors` vier vazia — ou se todos forem string em branco, caso em que o
`continue` roda antes da atribuição — a linha final levanta `NameError`.

Hoje isso está **latente** porque o bloco está protegido por `if on_progress:` e
`on_progress` nunca é passado (P0-2). **Corrigir o P0-2 sem corrigir este item
transforma um bug silencioso em crash.** A ordem importa.

### P2-4 · Sem deduplicação intra-execução

A V1 mantém `seen_record_ids` durante a execução (`bdtd_harvester.py:873, 912-914`)
e pula o registro antes de gastar a requisição de scraping de detalhes. Com 140
descritores altamente sobrepostos — veja os `bdtd_config.json`, onde
`"movimento sanitarista" AND "crítica" AND "Brasil"` e
`"reforma sanitária" AND "crítica" AND "Brasil"` retornam muitos dos mesmos
trabalhos — a sobreposição é a norma, não a exceção.

A V2 manda **todo** registro repetido para o caminho caro de deduplicação
(P0-3), inclusive os que ela poderia descartar por `source_id` a custo zero.

### P2-5 · Coleta não pode ser cancelada, retomada, nem sobrevive a reinício

`api/v1/harvest.py:58` usa `BackgroundTasks`. Isso significa:

- **Sem cancelamento.** Não há endpoint de "parar". Iniciada uma coleta de 140
  descritores ilimitados, a única saída é matar o processo.
- **Sem retomada.** Reiniciou o backend, perdeu tudo o que estava em andamento.
- **Runs fantasma.** `HarvestRunModel.status` fica `"running"` para sempre se o
  processo cair (`models.py:245`). Nada reconcilia isso na subida.
- **Sem isolamento.** A tarefa divide o event loop do servidor da API (ver P0-3c).

A V1, sendo CLI, resolvia isso de outro jeito: o SQLite com `UPSERT`
(`bdtd_harvester.py:711-725`) tornava toda execução idempotente. Rodar de novo
retomava naturalmente, sem duplicar. A V2 perdeu essa propriedade sem substituí-la.

### P2-6 · Chaves de API versionadas no repositório da V1

`scopus_harvester/scopus_config.json` contém uma chave Elsevier em texto claro;
`openalex_harvester/openalex_config.json` contém uma chave OpenAlex. Ambos estão
commitados no repositório RSAC.

> **Ação imediata, independente da migração:** revogar e reemitir as duas chaves
> no portal do provedor, e remover os valores do histórico. A migração para a V2
> não deve replicar esse padrão — ver §14.7 sobre armazenamento de credenciais.

O `scopus_config.json` também traz caminhos absolutos de `OneDrive` corporativo,
o que confirma o ponto de §13.6: a V1 é operada como ferramenta pessoal.

---

## 13.5 Como os defeitos se combinam no uso real

O `bdtd_config.json` do autor descreve o caso de uso verdadeiro: **140 descritores
booleanos de 3 termos, sem limite, em múltiplas bases.** Rastreando essa carga
pela V2:

1. Usuário seleciona BDTD + SciELO + OpenAlex, "Ilimitado", e clica em iniciar.
2. As fontes rodam **em sequência**, não em paralelo (`harvesting_service.py:101`)
   — apesar da UI prometer "Execução concorrente" (`HarvestPage.tsx:2`) e
   "bases consultadas simultaneamente" (`HarvestPage.tsx:247`).
3. BDTD começa. Páginas de 20 (P1-2), sem filtro de ano nem idioma (P1-7).
   Nenhum evento de progresso aparece (P0-2). **A tela fica parada.**
4. Cada registro passa pela dedup O(N²) com `fsync` (P0-3). Aos poucos milhares,
   cada inserção leva centenas de milissegundos.
5. O event loop trava; o `ping/pong` do WebSocket expira; o canal cai. **A tela
   fica parada de vez** — e agora nem os contadores sobem.
6. Os resumos da BDTD chegam corrompidos (P0-5). Os orientadores não chegam (P1-1).
7. SciELO entra. O primeiro HTTP 500 transitório encerra o descritor sem aviso (P2-2).
8. OpenAlex entra. Funciona — mas trunca em 10.000 por descritor e busca em
   texto completo em vez de título+resumo (P1-4).
9. Se o Scopus estiver marcado, ele registra `completed` com 0 registros (P0-4).

A percepção "o OpenAlex até está funcionando, o resto não" é **exatamente o que
esse encadeamento produz**. Não é impressão — é o comportamento esperado do
código atual.

---

## 13.6 O que a V1 acerta e precisa ser preservado

Vale nomear explicitamente, porque o risco de uma reescrita é jogar fora o
conhecimento operacional junto com o código:

1. **Regra do WAF da BDTD** (máx. 2 `filter[]`, idioma filtrado localmente) —
   `bdtd_harvester.py:72-130`. Conhecimento não documentado em lugar nenhum.
2. **Sanitização de descritor para o Lucene da BDTD** — remoção de aspas e
   normalização NFKD para ASCII (`bdtd_harvester.py:809-810`). A V2 portou isso
   corretamente (`harvesters/bdtd.py:26-33`); **manter**.
3. **Aquecimento de sessão no SciELO** — GET inicial para obter cookies antes de
   buscar (`scielo_harvester.py:354`). A V2 portou (`harvesters/scielo.py:135-137`);
   **manter**.
4. **Gravação em lote com UPSERT** — idempotência e velocidade
   (`bdtd_harvester.py:701-735`).
5. **Cursor paging no OpenAlex e no Scopus** — único jeito de passar dos 10k.
6. **Abstract Retrieval do Scopus** — `scopus_harvester.py:173`.
7. **Limpeza de campos** — `clean_creator_name`, `clean_advisor_name`,
   `process_record_fields`, `translate_format`, `get_source_info`.
8. **Backoff de 15s mínimo em HTTP 429** — `bdtd_harvester.py:858-860`. O backoff
   genérico da V2 (`bdtd.py:152`, `5.0 * attempt`) é curto demais para o WAF da BDTD.

Também vale dizer o que a V1 **não** tem e a V2 acerta em ter: modelo de projeto,
protocolo PRISMA-ScR, deduplicação entre fontes, triagem por IA, exportação
estruturada e uma interface. A V1 é uma coleção de cinco scripts CLI independentes,
cada um com seu SQLite e seu Excel; unificar os resultados é trabalho manual.
**A arquitetura da V2 é a direção certa** — o que falta é a profundidade da V1
dentro dela.

---

## 13.7 Divergências entre o que a interface promete e o que o backend faz

Registradas aqui porque afetam a confiança do usuário mesmo depois de a coleta
funcionar:

| Promessa na UI | Realidade | Evidência |
|---|---|---|
| "Execução concorrente de harvesters" | Sequencial | `HarvestPage.tsx:2` vs `harvesting_service.py:101` |
| "bases consultadas simultaneamente" | Sequencial | `HarvestPage.tsx:247` |
| "deduplicação de 3 passes" | Existe, mas O(N²) | `HarvestPage.tsx:216`, `dedup_service.py:63-107` |
| Scopus selecionável | `enabled: false` é ignorado pela UI | `harvest.py:125` vs `HarvestPage.tsx:251` |
| `msg.paper_id` no log de sucesso | Backend nunca envia esse campo | `HarvestPage.tsx:151` vs `harvesting_service.py:147-159` |
| Painel "em tempo real" | Sem eventos de progresso | `HarvestPage.tsx:131` vs P0-2 |

O último item de `paper_id` é menor mas sintomático: o log mostra `ID: N/A` em
toda linha porque o backend nunca inclui o campo no broadcast.

---

## 13.8 Itens marcados **[A VALIDAR]**

O ambiente onde esta análise foi feita tem rede restrita a registries de pacote
(`bdtd.ibict.br` é bloqueado por política do proxy), então **nenhuma chamada real
às bases foi executada.** Toda a análise acima é estática e baseada em código e
configuração. Os pontos abaixo precisam de confirmação empírica na máquina do
autor — os scripts para isso estão em `16_TESTES_VALIDACAO.md`:

1. Comportamento exato do SQLAlchemy ao gravar `list` em coluna `Text` (P0-5):
   coerção para string ou erro de bind.
2. Se o WAF da BDTD ainda aplica o limite de 2 `filter[]` (regra da V1 pode ter
   mudado do lado do servidor).
3. Se `search.scielo.org` mantém o parâmetro `output=site` e a estrutura
   `div.item` / `#TotalHits` usada pelo parser — scraping é frágil por natureza.
4. Se a conta Elsevier do autor tem entitlement para `view=COMPLETE` sem `insttoken`.
5. Taxa real de 429 da BDTD com página de 100 versus 20.
6. Se `bs4` está presente no ambiente atual do autor por acaso (explicaria a V2
   subir hoje apesar do P0-1).

---

## 13.9 Quadro comparativo consolidado

| Capacidade | RSAC V1 | RSAC V2 | Doc de destino |
|---|---|---|---|
| BDTD — página | 100 | 20 | §14.3 |
| BDTD — ordenação | `year` | `relevance` | §14.3 |
| BDTD — filtros | 4 + regra WAF | nenhum | §14.3 |
| BDTD — detalhes (orientador/instituição) | sim | não | §14.3 |
| BDTD — resumo | join de lista | lista crua ❌ | §14.3 |
| SciELO — retry | 5 tentativas, backoff | nenhum | §14.4 |
| SciELO — campo de busca | configurável | fixo | §14.4 |
| OpenAlex — paginação | cursor | offset (teto 10k) | §14.5 |
| OpenAlex — campo | `title_and_abstract` | `search` genérico | §14.5 |
| OpenAlex — filtros | 6 | nenhum | §14.5 |
| PubMed — teto | 10.000 | 500 | §14.6 |
| PubMed — rótulos do resumo | preservados | perdidos | §14.6 |
| PubMed — pula já coletados | sim | não | §14.6 |
| Scopus — resumo | COMPLETE + Abstract API | sempre vazio ❌ | §14.7 |
| Scopus — insttoken | sim | não | §14.7 |
| Persistência | lote + UPSERT | 1 commit/registro | §15.4 |
| Dedup entre fontes | ❌ (só intra-fonte) | ✅ mas O(N²) | §15.4 |
| Cancelar / retomar | idempotente por UPSERT | nenhum | §15.5 |
| Progresso ao vivo | log de console | quebrado | §15.5 |
| Protocolo / triagem / exportação | ❌ | ✅ | — |

---

**Próximo documento:** [`14_ESPECIFICACAO_COLETA.md`](./14_ESPECIFICACAO_COLETA.md) —
o contrato-alvo de coleta e a especificação por fonte.
