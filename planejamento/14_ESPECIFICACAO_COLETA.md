# 14 — Especificação Técnica da Camada de Coleta (alvo V2)

> **Objetivo:** definir o contrato que todo coletor da V2 deve cumprir e a
> especificação exata de cada fonte, incorporando o conhecimento operacional
> validado da V1.
>
> Este documento é normativo: `13_DIAGNOSTICO_COLETA_V2.md` diz o que está
> errado, este diz o que deve passar a existir, e
> `15_PLANO_EXECUCAO.md` diz em que ordem construir.

---

## 14.1 Princípios de projeto

Cinco princípios que resolvem, na raiz, as classes de defeito do documento 13.

**1. Reprodutibilidade acima de tudo.**
Uma revisão sistemática precisa ser auditável: dado o mesmo protocolo, a mesma
data e a mesma base, a coleta deve retornar o mesmo conjunto. Isso proíbe
ordenação por relevância e exige que toda execução registre a query literal
enviada a cada fonte. Sem isso, o método não é publicável.

**2. A fonte declara o que sabe fazer.**
Nem toda base suporta todo filtro. Em vez de espalhar `if source == "BDTD"` pelo
serviço, cada coletor publica suas `HarvesterCapabilities`. A UI usa isso para
desabilitar controles; o orquestrador usa para decidir o que filtrar localmente.

**3. Degradar, nunca desistir em silêncio.**
Filtro não suportado nativamente vira pós-filtro local. Fonte sem credencial vira
erro **visível** na run, não `completed` com zero. Falha transitória vira retry.
Falha permanente vira `HarvestRunModel.error_message` legível em português.

**4. Coletar é I/O; persistir é lote.**
Coletores só produzem registros e nunca tocam o banco. A persistência acontece em
lotes, fora do event loop. Essa separação é o que torna possível testar coletor
com fixture de HTTP e testar persistência sem rede.

**5. Toda execução é retomável.**
Chave natural estável por fonte (`source_name` + `source_id`) e `UPSERT`. Rodar
duas vezes converge para o mesmo estado — a propriedade que a V1 tinha de graça
e a V2 perdeu.

---

## 14.2 O contrato

### 14.2.1 `HarvestQuery` — entrada única e explícita

Substitui os três parâmetros soltos de hoje (`descriptors`,
`max_records_per_descriptor`, `on_progress`).

```python
# backend/app/harvesters/base.py

@dataclass(frozen=True)
class HarvestQuery:
    """Recorte de busca, resolvido a partir do protocolo + overrides da execução."""

    descriptors: list[str]

    # Recorte
    year_start: int | None = None
    year_end: int | None = None
    languages: list[str] = field(default_factory=list)      # ISO 639-1: pt, en, es
    document_types: list[str] = field(default_factory=list) # ver 14.2.4
    institutions: list[str] = field(default_factory=list)
    open_access_only: bool = False

    # Volume e ritmo
    max_records_per_descriptor: int | None = None  # None = ilimitado
    page_size: int | None = None                   # None = padrão da fonte
    delay: float | None = None                     # None = padrão da fonte

    # Enriquecimento (custa uma requisição extra por registro)
    fetch_details: bool = True

    # Reprodutibilidade
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

> `frozen=True` é deliberado: nenhum coletor pode alterar o recorte durante a
> execução. O que foi pedido é o que fica registrado na run.

### 14.2.2 `HarvesterCapabilities` — o que a fonte suporta nativamente

```python
@dataclass(frozen=True)
class HarvesterCapabilities:
    supports_year_range: bool = False
    supports_language: bool = False
    supports_document_type: bool = False
    supports_institution: bool = False
    supports_open_access: bool = False
    supports_boolean_query: bool = True
    max_native_filters: int | None = None   # BDTD = 2 (regra do WAF)
    requires_api_key: bool = False
    default_page_size: int = 25
    max_page_size: int = 100
    default_delay: float = 1.0
```

O orquestrador aplica a regra: **filtro pedido e não suportado nativamente vira
pós-filtro local**, e o fato é registrado na run (`filters_applied_locally`),
para que o relatório PRISMA descreva o método honestamente.

`max_native_filters` é a generalização direta de `sanitize_bdtd_filters`
(`bdtd_harvester.py:83`): quando o número de filtros nativos excede o teto, os
excedentes descem para pós-filtro local em vez de serem descartados — melhoria
sobre a V1, que os descartava com aviso (`bdtd_harvester.py:121-128`).

### 14.2.3 `RawPaperRecord` — campos ampliados

Adições sobre o modelo atual (`harvesters/base.py:16`), para não perder o que a
V1 extrai:

```python
@dataclass
class RawPaperRecord:
    title: str
    authors: str = ""
    year: str = ""
    abstract: str = ""
    doi: str | None = None
    source_name: str = ""
    source_id: str = ""
    download_url: str = ""
    research_type: str = ""
    institution: str = ""

    # ── Novos ──────────────────────────────────────────────────
    advisor: str = ""              # BDTD: orientador (P1-1)
    journal: str = ""              # separado de `institution`
    language: str = ""             # ISO 639-1, para pós-filtro
    keywords: str = ""             # assuntos/descritores da fonte
    matched_descriptor: str = ""   # qual descritor recuperou este registro
    extra_metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Coerção defensiva: nenhuma fonte entrega list onde se espera str."""
        for f in ("title", "authors", "abstract", "institution", "journal"):
            v = getattr(self, f)
            if isinstance(v, (list, tuple)):
                setattr(self, f, " ".join(str(x).strip() for x in v if x).strip())
            elif v is None:
                setattr(self, f, "")
```

O `__post_init__` é a rede de segurança contra a classe inteira de defeitos do
P0-5 (`summary` da BDTD chegando como lista). Não substitui a correção no parser
— **corrija o parser também** — mas garante que o erro nunca volte a atravessar
até o banco em silêncio.

`matched_descriptor` é requisito de auditoria PRISMA: é preciso saber qual termo
de busca recuperou cada estudo. A V1 já guardava isso (`keyword_query`,
`scielo_harvester.py:430`); a V2 perdeu.

`institution` e `journal` são coisas diferentes e hoje estão fundidos: em
`harvesters/scielo.py:103` o nome do periódico é gravado no campo de instituição.
Isso corrompe a exportação, que espera "Universidade / Editora / Revista" com
semântica clara (`scielo_harvester.py:501`).

### 14.2.4 Vocabulário canônico de tipos de documento

Cada base usa nomenclatura própria. A normalização é obrigatória, senão o filtro
por tipo não funciona entre fontes e a exportação fica ilegível — é o papel que
`translate_format` (`bdtd_harvester.py:559`) e `translate_publication_type`
cumpriam na V1, agora unificado num único enum.

| Canônico | BDTD (VuFind) | OpenAlex | PubMed | Scopus | SciELO |
|---|---|---|---|---|---|
| `TESE` | `doctoralThesis` | `dissertation` | — | — | — |
| `DISSERTACAO` | `masterThesis` | `dissertation` | — | — | — |
| `ARTIGO` | `article` | `article` | `Journal Article` | `Article` | `Artigo` |
| `REVISAO` | — | `review` | `Review` | `Review` | — |
| `CAPITULO` | `bookPart` | `book-chapter` | — | `Chapter` | — |
| `LIVRO` | `book` | `book` | — | `Book` | — |
| `ANAIS` | — | `proceedings-article` | — | `Conference Paper` | — |
| `PREPRINT` | — | `preprint` | `Preprint` | — | `Preprint` |
| `OUTRO` | *(fallback)* | *(fallback)* | *(fallback)* | *(fallback)* | *(fallback)* |

Implementar em `backend/app/domain/enums.py`, com `to_canonical(source, raw)` e
`to_native(source, canonical)` — o segundo é necessário para montar o filtro
nativo de cada base.

### 14.2.5 A interface

```python
class BaseHarvester(ABC):
    source_name: ClassVar[str]
    capabilities: ClassVar[HarvesterCapabilities]

    @abstractmethod
    async def harvest(
        self,
        query: HarvestQuery,
        on_progress: Callable[[HarvestProgress], Awaitable[None]] | None = None,
    ) -> AsyncGenerator[RawPaperRecord, None]:
        ...
```

Três mudanças obrigatórias em relação a hoje:

1. `on_progress` é **`Awaitable`** e todo `on_progress(...)` vira
   `await on_progress(...)` (corrige P0-2, segunda metade).
2. Contadores agregados (`total_for_desc`) inicializam **antes** do laço de
   descritores (corrige P2-3 — e isso precisa entrar **junto** com a correção do
   P0-2, nunca depois).
3. Nenhum coletor recebe `Session` do banco. Coletor não persiste.

### 14.2.6 `HarvestProgress` — eventos com granularidade útil

```python
@dataclass
class HarvestProgress:
    source_name: str
    phase: Literal["starting", "searching", "fetching_details", "done", "error"]
    current_descriptor: str = ""
    descriptor_index: int = 0
    descriptor_total: int = 0
    page: int = 0
    records_this_descriptor: int = 0
    records_total: int = 0
    estimated_total: int | None = None   # resultCount / meta.count / TotalHits
    retry_attempt: int = 0
    message: str = ""
    error: str | None = None
```

`descriptor_index/descriptor_total` é o que permite uma barra de progresso real
("descritor 37 de 140"). Com 140 descritores e coleta ilimitada, saber que existe
avanço é a diferença entre esperar e reiniciar o app. `estimated_total` já é lido
por todas as fontes hoje, mas descartado — a BDTD lê `resultCount`
(`bdtd.py:212`), o SciELO lê `#TotalHits` e apenas loga (`scielo.py:183-189`),
o OpenAlex lê `meta.count` (`openalex.py:136-137`).

**Regra de emissão:** progresso a cada página, **nunca por registro**. O
`paper_harvested` por registro de hoje (`harvesting_service.py:147`) é uma
mensagem WebSocket para cada paper — com 20.000 papers são 20.000 mensagens.
Substituir por lote agregado a cada N registros ou T segundos (§15.5).

---

## 14.3 Especificação — BDTD (IBICT / VuFind)

**Fonte da verdade da V1:** `bdtd_harvester/bdtd_harvester.py`

### Endpoint e sessão

| Item | Valor |
|---|---|
| Busca | `GET https://bdtd.ibict.br/vufind/api/v1/search` |
| Espelho | `https://oasisbr.ibict.br/vufind/api/v1/search` |
| Detalhe (HTML) | `GET https://bdtd.ibict.br/vufind/Record/{record_id}` |
| Cookie obrigatório | `OasisbrVerify=verified_human` |
| User-Agent | navegador realista |
| **TLS** | **`verify` habilitado** (corrige P2-1) |

### Parâmetros

```python
params = {
    "lookfor": sanitize_bdtd_keyword(descriptor),
    "type": "AllFields",       # ou Title, Author, Subject, Advisor
    "sort": "year",            # NUNCA relevance (§14.1, princípio 1)
    "page": page,
    "limit": 100,              # padrão V1; 20 é 5x mais requisições
    "field[]": REQUEST_FIELDS,
}
```

`REQUEST_FIELDS` = `id, title, authors, subjects, languages, formats, urls,
summary, publicationDates, institutions`.

### Sanitização do descritor — **preservar exatamente**

`harvesters/bdtd.py:26-33` já está correto e replica `bdtd_harvester.py:809-810`:
remove aspas simples e duplas, normaliza NFKD para ASCII. O Lucene da BDTD
degrada muito com acentos e busca por proximidade. **Não "melhorar" isso** sem
medir — é um comportamento aprendido em produção.

### Filtros e a regra do WAF

O servidor rejeita com **HTTP 429** requisições com **3 ou mais `filter[]`**
(`bdtd_harvester.py:72-80`). A regra:

| Filtro | Nativo | Formato Solr |
|---|---|---|
| Ano | ✅ | `publishDate:[1970 TO 2023]` |
| Tipo | ✅ | `format:doctoralThesis` |
| Instituição | ✅ | `institution:USP` |
| Idioma | ⚠️ **local** | pós-filtro sobre `languages` do registro |

Idioma **sempre** desce para pós-filtro local, mesmo com folga no orçamento de
filtros — foi a decisão da V1 (`bdtd_harvester.py:107-110`) e ela reduz a
superfície de 429. Se ainda restarem mais de 2 filtros nativos, os excedentes
(na ordem ano → tipo → instituição) também descem para local.

```python
capabilities = HarvesterCapabilities(
    supports_year_range=True,
    supports_document_type=True,
    supports_institution=True,
    supports_language=False,      # forçado a pós-filtro local
    max_native_filters=2,
    default_page_size=100, max_page_size=100,
    default_delay=2.5,
)
```

### Retry e rate limit

- 5 tentativas, backoff exponencial fator 2,0 sobre o `delay` base.
- **HTTP 429 → espera mínima de 15 s** (`bdtd_harvester.py:858-860`). O
  `5.0 * attempt` atual (`bdtd.py:152`) é curto demais para o WAF.
- Alternar entre `bdtd.ibict.br` e `oasisbr.ibict.br` só depois de esgotar o
  retry na primária — não a cada tentativa como hoje (`bdtd.py:142`), que
  mascara a origem da falha.
- Toda resposta não-200 é **logada com status e corpo truncado** (corrige o
  ramo mudo de P2-2).

### Enriquecimento por raspagem (`fetch_details=True`)

Portar `scrape_record_details` (`bdtd_harvester.py:577`): metatags Dublin Core
do `<head>` mais os pares `<th>/<td>` das tabelas de detalhe. Daí derivar:

| Campo alvo | Origem | Função da V1 a portar |
|---|---|---|
| `advisor` | `Orientador(a):` → fallback `dc.contributor.none.fl_str_mv` | `clean_advisor_name:153` |
| `institution` | `instname_str` / `Instituição de defesa:` / … | `get_source_info:626` |
| `research_type` | `format` do detalhe → fallback `formats[0]` | `translate_format:559` |
| `authors` | `authors` da API | `clean_creator_name:133` |
| `download_url` | `urls[0]` → `Link de acesso:` → `url` → URL do registro | `extract_url:546` + `:964-969` |
| `abstract` + `advisor` | correção de campos trocados | `process_record_fields:195` |

**Custo:** uma requisição HTTP extra por registro, com pausa de cortesia de 1 s
(`bdtd_harvester.py:934`). Numa coleta de 5.000 registros são ~85 minutos só de
raspagem. Por isso `fetch_details` é opcional e exposto na UI como
*"Coleta rápida (sem orientador e instituição de defesa)"*.

**Otimização que a V1 não tem:** raspar detalhes **apenas** de registros que
sobreviveram à deduplicação intra-execução, e com concorrência limitada
(`asyncio.Semaphore(4)`) em vez de sequencial. Isso corta a maior parte do custo
com os 140 descritores sobrepostos do caso real.

### Parsing — correções obrigatórias

```python
# ❌ hoje (bdtd.py:197) — summary é list
abstract=rec.get("summary", "") or ...

# ✅ alvo (paridade com bdtd_harvester.py:923-924)
summaries = rec.get("summary") or []
abstract = " ".join(s.strip() for s in summaries if s).strip()
```

Deduplicação intra-execução por `record_id` antes de qualquer trabalho caro
(`seen_record_ids`, `bdtd_harvester.py:873`) — corrige P2-4.

---

## 14.4 Especificação — SciELO

**Fonte da verdade da V1:** `scielo_harvester/scielo_harvester.py`

| Item | Valor |
|---|---|
| Busca | `GET https://search.scielo.org/` |
| Página | 15 (fixo pelo portal) |
| Paginação | `from` = offset **começando em 1**, `count` = 15 |
| Parâmetros | `q`, `lang=pt`, `count`, `from`, `output=site`, `where` (opcional) |
| Aquecimento | GET na raiz antes de buscar — **manter** (`scielo.py:135`) |

⚠️ SciELO é a única fonte por **raspagem de HTML**, portanto a mais frágil.
Qualquer mudança de layout do portal quebra o parser em silêncio. Mitigação em
§16.4 (teste canário).

### Retry — a correção mais importante desta fonte

Portar a estratégia da V1 (`scielo_harvester.py:341-349`) para `httpx`:

```python
transport = httpx.AsyncHTTPTransport(retries=3)
RETRY_STATUS = {429, 500, 502, 503, 504}
# backoff 1.5 ** tentativa, até 5 tentativas
```

`httpx.AsyncHTTPTransport(retries=)` só cobre erros de **conexão**, não status
HTTP. O retry por status precisa ser um laço explícito no coletor — não basta
configurar o transporte. Isso corrige P2-2, o defeito que silenciosamente
esburaca a coleta do SciELO.

### Filtros

O portal expõe pouco de forma estável. Postura conservadora:

```python
capabilities = HarvesterCapabilities(
    supports_year_range=False,     # pós-filtro local sobre `year`
    supports_language=False,       # pós-filtro local
    supports_document_type=False,  # pós-filtro (Artigo vs Preprint)
    default_page_size=15, max_page_size=15,
    default_delay=2.5,
)
```

Tudo local. Com `estimated_total` vindo de `#TotalHits`, dá para avisar o usuário
quando o pós-filtro descarta a maior parte do recuperado.

### Parsing

`parse_scielo_item` (`harvesters/scielo.py:29`) é uma porta fiel de
`parse_item` (`scielo_harvester.py:236`) e está **correta**. Ajustes:

1. `journal` no campo `journal`, **não** em `institution` (§14.2.3).
2. Usar `RE_TOTAL_HITS` (`scielo.py:25`), hoje declarada e nunca usada, como
   fallback quando `#TotalHits` não existir — a V1 faz isso
   (`scielo_harvester.py:393-396`).
3. Preencher `matched_descriptor` (equivalente a `keyword_query` da V1).
4. `doi`: hoje cai para `doi_text` cru quando a regex não casa
   (`scielo.py:91`). Preferir `None` a gravar lixo no campo de DOI — DOI sujo
   contamina o passo 1 da deduplicação.

---

## 14.5 Especificação — OpenAlex

**Fonte da verdade da V1:** `openalex_harvester/openalex_harvester.py`

Esta é a fonte que "funciona" e que, mesmo assim, precisa de três correções
estruturais.

### Paginação — cursor, obrigatoriamente

```python
# ❌ hoje (openalex.py:71-76): teto de 10.000
params = {"search": desc, "per-page": 25, "page": page, "mailto": mail}

# ✅ alvo (paridade com openalex_harvester.py:512-515)
params = {"per_page": 50, "cursor": cursor}   # cursor inicial "*"
# a cada resposta: cursor = data["meta"]["next_cursor"]; parar quando None
```

### Query — título e resumo, não texto completo

```python
filter_parts = [f"title_and_abstract.search:{descriptor}"]
```

`search=` genérico busca em texto completo indexado e traz ruído
desproporcional. Para revisão sistemática, o recorte título+resumo é o padrão
metodológico — e é o que a V1 usa (`openalex_harvester.py:523`).

### Filtros nativos (todos suportados)

| Filtro | Expressão |
|---|---|
| Faixa de anos | `publication_year:1970-2023` |
| A partir de | `publication_year:>=2015` |
| Idioma (multi) | `language:pt\|en\|es` |
| Tipo | `type:article` |
| Acesso aberto | `is_oa:true` |

Todos concatenados por vírgula em `filter=` (`openalex_harvester.py:526-534`).

```python
capabilities = HarvesterCapabilities(
    supports_year_range=True, supports_language=True,
    supports_document_type=True, supports_open_access=True,
    default_page_size=50, max_page_size=200, default_delay=0.3,
)
```

### Polite pool

`mailto` no **User-Agent** (`openalex_harvester.py:450`), não só na query string,
e `api_key` quando houver (`:485`). Sem isso, o OpenAlex despriorizará requisições
em volume alto.

### Parsing

`_reconstruct_abstract` (`openalex.py:28`) está correta — mantém. Ajustes:

1. `title` pode ser `None` no OpenAlex; `openalex.py:118` faz
   `work.get("title", "").strip()`, que levanta `AttributeError` quando a chave
   existe com valor `None`. A V1 protege com
   `work.get("title") or work.get("display_name") or ""`
   (`openalex_harvester.py:~580`). **Corrigir.**
2. `source_id`: normalizar removendo o prefixo de URL (`W2741809807`, não
   `https://openalex.org/W2741809807`) — `openalex_harvester.py:~576`.
3. `language` do trabalho para o campo novo.
4. Separar `journal` (`primary_location.source.display_name`) de `institution`
   (afiliação do primeiro autor) — hoje o nome do periódico vai para
   `institution` (`openalex.py:115`).

---

## 14.6 Especificação — PubMed (NCBI E-utilities)

**Fonte da verdade da V1:** `pubmed_harvester/pubmed_harvester.py`

> Nota de escopo: `.agents/AGENTS.md` registra que o domínio-alvo do produto é
> Ciências Sociais Aplicadas e Desenvolvimento Regional, **não** saúde. O PubMed
> é secundário aqui — deve funcionar corretamente, mas não é prioridade de
> validação. Ver §15.2.

| Item | Valor |
|---|---|
| Busca | `esearch.fcgi` — `db=pubmed`, `retmode=json`, `retmax=10000` |
| Detalhe | `efetch.fcgi` — `retmode=xml`, lotes de **100** PMIDs |
| Ritmo | 0,35 s sem chave; 0,15 s com chave |
| Chave | `api_key` → 10 req/s |

Correções sobre a V2:

1. **`retmax=10000`** e paginação por `retstart` quando o total exceder — hoje
   trava em 500 (`pubmed.py:44`).
2. **Lote de 100** no `efetch` (V2 usa 25 — `pubmed.py:79`).
3. **Preservar rótulos das seções do resumo**: `AbstractText` tem atributo
   `Label` (`BACKGROUND`, `METHODS`, `RESULTS`, `CONCLUSIONS`). A V1 monta
   `"RÓTULO: texto"` (`pubmed_harvester.py:430-434`); a V2 descarta
   (`pubmed.py:116-120`). A triagem por IA usa essa estrutura.
4. **Pular PMIDs já coletados** antes do `efetch` (§13.3, P1-5).
5. Filtros nativos por sintaxe de query, não por parâmetro:
   `("2015"[PDAT] : "2023"[PDAT])`, `AND english[LANG]`, `AND Review[PT]`.

```python
capabilities = HarvesterCapabilities(
    supports_year_range=True, supports_language=True, supports_document_type=True,
    requires_api_key=False,   # opcional, mas fortemente recomendada
    default_page_size=100, max_page_size=10000, default_delay=0.35,
)
```

---

## 14.7 Especificação — Scopus (Elsevier)

**Fonte da verdade da V1:** `scopus_harvester/scopus_harvester.py`

| Item | Valor |
|---|---|
| Busca | `GET https://api.elsevier.com/content/search/scopus` |
| Resumo | `GET https://api.elsevier.com/content/abstract/eid/{eid}?view=META_ABS` |
| Cabeçalhos | `X-ELS-APIKey`, `X-ELS-Insttoken` (opcional) |
| View | **`COMPLETE`** (V2 usa `STANDARD`) |
| Paginação | cursor (`cursor=*`), offset como fallback |

### O problema do resumo — correção crítica

`scopus.py:103` grava `abstract=""` sempre. Solução em dois níveis, como na V1:

1. `view=COMPLETE` retorna `dc:description` na própria busca.
2. Quando ainda vier vazio, chamar a **Abstract Retrieval API** por EID
   (`scopus_harvester.py:173`), tratando `dc:description` que chega ora como
   `str`, ora como `{"$": "..."}` (`:193`).

Sem resumo, o Scopus é inútil para triagem — o produto inteiro depende disso.

### Credenciais e falha visível

```python
capabilities = HarvesterCapabilities(
    supports_year_range=True, supports_document_type=True, supports_open_access=True,
    requires_api_key=True,
    default_page_size=25, max_page_size=200, default_delay=1.0,
)
```

Sem chave, o coletor deve **levantar `MissingCredentialsError`**, não retornar
vazio (`scopus.py:34-36`). O orquestrador marca a run como `failed` com
`error_message` acionável: *"Scopus requer chave de API. Configure em
Configurações → Bases de Dados."* Corrige o "zero silencioso" do P0-4.

Filtros nativos: `PUBYEAR > 2014 AND PUBYEAR < 2024`, `AND DOCTYPE(ar)`,
`AND OPENACCESS(1)`, dentro da própria string de query.

### Armazenamento de credenciais

Hoje não há onde guardá-las (§13.2, P0-4). Proposta — nova tabela, em vez de
esticar `AISettingsModel`:

```python
class SourceCredentialModel(Base):
    __tablename__ = "source_credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_name: Mapped[str] = mapped_column(String(50), unique=True)   # SCOPUS, PUBMED, OPENALEX
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    extra_encrypted: Mapped[str] = mapped_column(Text, default="{}")    # insttoken, mailto
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
```

Regras não negociáveis, dado o precedente de chaves versionadas da V1 (P2-6):

- Criptografia em repouso com a mesma estratégia já usada em
  `AISettingsModel.api_keys_encrypted`.
- A API **nunca** devolve a chave; devolve `has_key: bool` e os 4 últimos dígitos.
- Nenhuma chave em log, nem em `error_message` de run.
- Nenhum arquivo de exemplo com chave real — e as duas chaves atualmente
  versionadas na V1 devem ser **revogadas hoje**, sem esperar a migração.

---

## 14.8 Resolução do recorte de busca (protocolo → query)

Hoje o protocolo só guarda descritores (`schemas/protocol.py:50`). O recorte
precisa virar parte do protocolo — é decisão metodológica registrável, não
parâmetro de execução.

### Novo bloco em `ProtocolModel`

```python
search_filters: Mapped[str] = mapped_column(Text, default="{}")  # JSON
```

```jsonc
{
  "year_start": 1970,
  "year_end": 2023,
  "languages": ["pt", "en", "es"],
  "document_types": ["TESE", "DISSERTACAO", "ARTIGO"],
  "institutions": [],
  "open_access_only": false
}
```

Esse é exatamente o recorte do `bdtd_config.json` real do autor
(`publishDate: "[1970 TO 2023]"`, `language: "Português, Inglês, Espanhol"`),
agora expressável na V2 e aplicável a **todas** as fontes de uma vez — ganho
sobre a V1, onde o mesmo recorte precisava ser repetido em cinco arquivos JSON.

### Precedência

`HarvestStartRequest` pode sobrescrever por execução (para testes-piloto), mas o
padrão vem do protocolo:

```
HarvestQuery = protocolo.search_filters ← sobrescrito por → HarvestStartRequest
```

A run grava o `HarvestQuery` **efetivo** serializado, não o do protocolo — o
protocolo muda ao longo do projeto e a run precisa registrar o que de fato rodou.

### Sobre a regra dos pares de descritores

`.agents/AGENTS.md` estabelece: máximo 2 termos por par, máximo 5 pares por
idioma. Mas os configs reais da V1 usam **3 termos** e **140 descritores**
(`"movimento sanitarista" AND "crítica" AND "Brasil"`).

Essa tensão precisa de decisão explícita — ela muda o dimensionamento de todo o
resto (140 descritores × ilimitado é uma ordem de grandeza distinta de 15 × 500):

- **A regra é limite duro da BDTD?** Então a V2 deve validar e recusar strings
  com 3+ termos, e o autor precisa ajustar seus configs.
- **A regra é orientação para a IA que *sugere* descritores?** Então a validação
  não se aplica a descritores escritos à mão, e o campo aceita o que o usuário
  digitar.

A leitura do texto do `AGENTS.md` ("Ao sugerir, elaborar ou configurar…") aponta
para a **segunda** — é guia de geração, não invariante de sistema. A recomendação
deste plano é: **avisar, não bloquear** — a UI mostra alerta em descritores com
3+ termos, explicando o risco de sobrecarga do VuFind, e permite prosseguir.
⚠️ **Confirmar com o autor antes da Fase 1** (§15.3), pois é premissa de escala.

---

## 14.9 Matriz consolidada de capacidades

| | BDTD | SciELO | OpenAlex | PubMed | Scopus |
|---|:---:|:---:|:---:|:---:|:---:|
| Faixa de anos | ✅ nativo | 🔄 local | ✅ nativo | ✅ query | ✅ query |
| Idioma | 🔄 local (WAF) | 🔄 local | ✅ nativo | ✅ query | 🔄 local |
| Tipo de documento | ✅ nativo | 🔄 local | ✅ nativo | ✅ query | ✅ query |
| Instituição | ✅ nativo | ❌ | 🔄 local | ❌ | 🔄 local |
| Acesso aberto | ❌ | ❌ | ✅ nativo | ❌ | ✅ query |
| Máx. filtros nativos | **2** | — | ilimitado | ilimitado | ilimitado |
| Paginação | offset | offset | **cursor** | retstart | **cursor** |
| Página padrão | 100 | 15 | 50 | 100 | 25 |
| Requer chave | não | não | opcional | opcional | **sim** |
| Resumo na busca | ✅ | ✅ | ✅ | ✅ | ⚠️ 2ª chamada |
| Requisição extra/registro | ⚠️ detalhes | não | não | não | ⚠️ resumo |
| Delay padrão | 2,5 s | 2,5 s | 0,3 s | 0,35 s | 1,0 s |

✅ nativo · 🔄 pós-filtro local · ❌ não suportado · ⚠️ custo extra

---

**Próximo documento:** [`15_PLANO_EXECUCAO.md`](./15_PLANO_EXECUCAO.md) — fases,
tarefas e critérios de aceite.
