# 16 — Testes e Protocolo de Validação da Coleta

> **Objetivo:** tornar verificável cada afirmação de "está funcionando".
>
> A V2 chegou ao estado do doc 13 porque não havia teste algum de coleta:
> `backend/tests/` cobre entidades, dedup, triagem e endpoints, mas **nenhum
> teste toca `app/harvesters/`**. Cinco coletores, ~700 linhas, zero cobertura.
> Foi por isso que o `summary`-como-lista (P0-5) e o `on_progress` desconectado
> (P0-2) atravessaram até produção.

---

## 16.1 Estratégia em quatro camadas

| Camada | O que valida | Rede? | Quando roda |
|---|---|:---:|---|
| **1. Unidade** | Parsing e limpeza sobre fixtures salvas | não | Todo commit |
| **2. Contrato** | Requisições montadas corretamente (URL, params, headers) | não | Todo commit |
| **3. Canário** | A fonte real ainda responde no formato esperado | **sim** | Semanal + antes de release |
| **4. Paridade** | V2 recupera o mesmo que V1 | **sim** | Fim de fase, manual |

A separação importa: **1 e 2 nunca podem depender de rede.** Bases científicas
caem, mudam layout e aplicam rate limit — se o CI depender delas, a suíte vira
ruído e as pessoas param de olhar. As camadas 3 e 4 usam rede e **falham de
forma informativa**, não bloqueante.

> ⚠️ **Contexto de elaboração deste plano:** o ambiente onde esta análise foi
> feita tem rede restrita a registries de pacote (`bdtd.ibict.br` retorna 403 no
> proxy), então **nenhuma chamada real às bases foi executada**. Tudo em 13 e 14
> é análise estática de código. As camadas 3 e 4 abaixo existem justamente para
> confirmar empiricamente, na máquina do autor, os pontos listados em §13.8.

---

## 16.2 Camada 1 — Testes de unidade sobre fixtures

### Capturar as fixtures (uma vez, com rede)

`backend/tests/fixtures/harvesters/capture.py` — grava respostas reais em disco
para servirem de base a todos os testes offline:

```python
"""Captura respostas reais das bases. Rodar manualmente, com rede."""
import json, pathlib, httpx

OUT = pathlib.Path(__file__).parent
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"

def capture_bdtd():
    r = httpx.get(
        "https://bdtd.ibict.br/vufind/api/v1/search",
        params={"lookfor": "desenvolvimento regional", "type": "AllFields",
                "sort": "year", "page": 1, "limit": 100,
                "field[]": ["id", "title", "authors", "subjects", "languages",
                            "formats", "urls", "summary", "publicationDates",
                            "institutions"]},
        headers={"User-Agent": UA, "Cookie": "OasisbrVerify=verified_human"},
        timeout=60,
    )
    (OUT / "bdtd_search.json").write_text(r.text, encoding="utf-8")

    # Página de detalhe, para os testes de raspagem da Fase 5
    rid = r.json()["records"][0]["id"]
    d = httpx.get(f"https://bdtd.ibict.br/vufind/Record/{rid}",
                  headers={"User-Agent": UA, "Cookie": "OasisbrVerify=verified_human"},
                  timeout=60)
    (OUT / "bdtd_record_detail.html").write_text(d.text, encoding="utf-8")

def capture_scielo():
    r = httpx.get("https://search.scielo.org/",
                  params={"q": "desenvolvimento regional", "lang": "pt",
                          "count": "15", "from": "1", "output": "site"},
                  headers={"User-Agent": UA}, timeout=60, follow_redirects=True)
    (OUT / "scielo_search.html").write_text(r.text, encoding="utf-8")

def capture_openalex():
    r = httpx.get("https://api.openalex.org/works",
                  params={"filter": "title_and_abstract.search:regional development",
                          "per_page": 50, "cursor": "*"},
                  headers={"User-Agent": "mailto:seu@email"}, timeout=60)
    (OUT / "openalex_works.json").write_text(r.text, encoding="utf-8")

if __name__ == "__main__":
    capture_bdtd(); capture_scielo(); capture_openalex()
    print("Fixtures salvas em", OUT)
```

> **Versionar as fixtures.** São a memória do formato de cada fonte. Quando o
> canário (camada 3) acusar mudança, o diff contra a fixture mostra exatamente
> o que mudou.

### Testes que teriam pegado os bugs de hoje

`backend/tests/test_harvesters/test_bdtd_parsing.py`:

```python
def test_resumo_e_string_nunca_lista(bdtd_fixture):
    """Regressão do P0-5: VuFind devolve `summary` como lista."""
    records = list(parse_bdtd_records(bdtd_fixture))
    for r in records:
        assert isinstance(r.abstract, str), f"abstract virou {type(r.abstract)}"
        assert not r.abstract.startswith("["), "lista serializada como string"

def test_resumo_preserva_conteudo(bdtd_fixture):
    raw = bdtd_fixture["records"][0]
    esperado = " ".join(s.strip() for s in (raw.get("summary") or []) if s).strip()
    assert parse_bdtd_record(raw).abstract == esperado

def test_dedup_intra_execucao_por_record_id(bdtd_fixture):
    """Regressão do P2-4."""
    dobrado = {"records": bdtd_fixture["records"] * 2, "resultCount": 200}
    assert len({r.source_id for r in parse_bdtd_records(dobrado)}) == \
           len(list(parse_bdtd_records(dobrado)))
```

`backend/tests/test_harvesters/test_contract.py` — vale para os cinco:

```python
@pytest.mark.parametrize("cls", ALL_HARVESTERS)
async def test_descritores_vazios_nao_quebram(cls):
    """Regressão do P2-3: NameError com lista vazia ou em branco."""
    eventos = []
    async def spy(p): eventos.append(p)

    for descs in ([], ["   "], ["", None]):
        h = cls()
        async for _ in h.harvest(HarvestQuery(descriptors=descs), on_progress=spy):
            pass
    assert any(e.phase == "done" for e in eventos)

@pytest.mark.parametrize("cls", ALL_HARVESTERS)
async def test_progresso_e_awaitable(cls):
    """Regressão do P0-2: callback async precisa ser aguardado."""
    chamadas = []
    async def spy(p): chamadas.append(p)
    h = cls()
    async for _ in h.harvest(QUERY_MINIMA, on_progress=spy):
        break
    assert chamadas, "on_progress nunca foi chamado"
    assert all(isinstance(c, HarvestProgress) for c in chamadas)

@pytest.mark.parametrize("cls", ALL_HARVESTERS)
def test_record_coage_lista_para_string(cls):
    """Rede de segurança do __post_init__ (§14.2.3)."""
    r = RawPaperRecord(title="t", abstract=["a", "b"])   # type: ignore[arg-type]
    assert r.abstract == "a b"
```

---

## 16.3 Camada 2 — Testes de contrato de requisição

Interceptam a requisição com `httpx.MockTransport` e afirmam sobre o que **seria**
enviado. É a camada que protege as regras operacionais herdadas da V1 — as que
ninguém lembra de manter porque não são visíveis no resultado.

```python
async def test_bdtd_respeita_limite_de_2_filtros_do_waf():
    """Regressão do P1-3. O WAF devolve 429 com 3+ filter[]."""
    capturadas = []
    def handler(req):
        capturadas.append(req)
        return httpx.Response(200, json={"records": [], "resultCount": 0})

    h = BDTDHarvester(transport=httpx.MockTransport(handler))
    q = HarvestQuery(descriptors=["teste"], year_start=1970, year_end=2023,
                     document_types=["TESE"], institutions=["USP"],
                     languages=["pt", "en"])
    async for _ in h.harvest(q):
        pass

    filtros = capturadas[0].url.params.get_list("filter[]")
    assert len(filtros) <= 2, f"WAF será acionado: {filtros}"
    assert not any("language" in f for f in filtros), "idioma deve ser pós-filtro local"

async def test_bdtd_ordena_por_ano_nunca_relevancia():
    """Reprodutibilidade (§14.1, princípio 1)."""
    ...
    assert capturadas[0].url.params["sort"] == "year"

async def test_openalex_usa_cursor_nao_offset():
    """Regressão do P1-4: offset trava em 10.000."""
    ...
    assert "cursor" in capturadas[0].url.params
    assert "page" not in capturadas[0].url.params

async def test_openalex_busca_titulo_e_resumo():
    assert "title_and_abstract.search:" in capturadas[0].url.params["filter"]

async def test_scielo_repete_apos_500():
    """Regressão do P2-2: um 5xx transitório não pode matar o descritor."""
    n = 0
    def handler(req):
        nonlocal n; n += 1
        return httpx.Response(500) if n == 1 else httpx.Response(200, html=PAGINA_FIXTURE)
    ...
    assert n >= 2, "não houve retry"
    assert registros, "descritor foi perdido após um 500 transitório"

async def test_scopus_sem_chave_levanta_erro_visivel():
    """Regressão do P0-4: hoje retorna vazio em silêncio."""
    with pytest.raises(MissingCredentialsError):
        async for _ in ScopusHarvester(api_key=None).harvest(QUERY_MINIMA):
            pass

async def test_nenhum_cliente_desabilita_tls():
    """Regressão do P2-1."""
    import subprocess
    out = subprocess.run(["grep", "-rn", "verify=False", "backend/app/"],
                         capture_output=True, text=True).stdout
    assert not out.strip(), f"TLS desabilitado em:\n{out}"
```

---

## 16.4 Camada 3 — Canários contra as fontes reais

Confirmam que o **formato** da fonte não mudou. Marcados para não rodar no CI
padrão.

```python
pytestmark = [pytest.mark.canary, pytest.mark.skipif(
    not os.getenv("RSAC_CANARY"), reason="requer rede; RSAC_CANARY=1")]

async def test_bdtd_estrutura_intacta():
    dados = await buscar_bdtd_real("desenvolvimento regional", limit=5)
    assert "records" in dados and "resultCount" in dados
    r = dados["records"][0]
    for campo in ("id", "title", "authors", "publicationDates"):
        assert campo in r
    if "summary" in r:
        assert isinstance(r["summary"], list), \
            "BDTD mudou o tipo de `summary` — revisar §14.3"

async def test_scielo_seletores_html_intactos():
    """O mais frágil de todos: raspagem de HTML."""
    soup = await buscar_scielo_real("desenvolvimento regional")
    itens = soup.find_all(class_="item")
    assert itens, "seletor `.item` sumiu — parser do SciELO quebrou"
    primeiro = itens[0]
    for classe in ("title", "authors", "source"):
        assert primeiro.find(class_=classe), f"seletor `.{classe}` sumiu"
    assert soup.find(id="TotalHits"), "#TotalHits sumiu — usar RE_TOTAL_HITS"

async def test_bdtd_limite_de_filtros_do_waf_ainda_vale():
    """Confirma empiricamente §13.8 item 2."""
    r = await bdtd_cru(filtros=["format:doctoralThesis",
                                "institution:USP",
                                "publishDate:[2020 TO 2023]"])
    if r.status_code != 429:
        pytest.fail("WAF não bloqueou 3 filtros — regra da V1 pode ter mudado; "
                    "reavaliar max_native_filters em §14.3")
```

Rodar semanalmente. Falha de canário **não** quebra o build — abre issue.

---

## 16.5 Camada 4 — Paridade V1 ↔ V2

O critério de aceite final da Fase 6. Roda os dois sistemas contra a mesma base,
**no mesmo dia** — comparar contra números históricos é inválido, porque as bases
crescem.

### Conjunto de referência

Derivado dos configs reais do autor, reduzido para caber numa execução:

```jsonc
{
  "descritores": [
    "\"desenvolvimento regional\" AND \"políticas públicas\"",
    "\"arranjos produtivos locais\" AND \"inovação\"",
    "\"governança territorial\" AND \"sustentabilidade\"",
    "\"planejamento urbano\" AND \"participação social\"",
    "\"regional development\" AND \"public policy\""
  ],
  "recorte": {
    "year_start": 2010, "year_end": 2023,
    "languages": ["pt", "en", "es"],
    "document_types": ["TESE", "DISSERTACAO", "ARTIGO"]
  },
  "limite_por_descritor": 200
}
```

Limite de 200 para a execução caber em minutos. A validação de volume ilimitado
é separada (§16.6).

### Script comparador

`backend/scripts/validar_paridade.py`:

```python
"""
Roda V1 e V2 sobre o mesmo conjunto e emite relatório comparativo.

    python scripts/validar_paridade.py --fonte BDTD --v1-db ../RSAC/2_bdtd_metadata.db
"""

def comparar(v1_registros, v2_registros, fonte) -> dict:
    ids1 = {r["record_id"] for r in v1_registros}
    ids2 = {r.source_id for r in v2_registros}
    inter = ids1 & ids2

    def cobertura(regs, campo):
        if not regs: return 0.0
        return sum(1 for r in regs if str(_get(r, campo) or "").strip()) / len(regs)

    return {
        "fonte": fonte,
        "v1_total": len(ids1),
        "v2_total": len(ids2),
        "delta_pct": (len(ids2) - len(ids1)) / len(ids1) * 100 if ids1 else 0,
        "sobreposicao_pct": len(inter) / len(ids1) * 100 if ids1 else 0,
        "so_na_v1": len(ids1 - ids2),      # ⚠️ o número que mais importa
        "so_na_v2": len(ids2 - ids1),
        "cobertura": {
            campo: {"v1": cobertura(v1_registros, campo),
                    "v2": cobertura(v2_registros, campo)}
            for campo in ("abstract", "authors", "year", "doi", "advisor", "institution")
        },
    }
```

### Limiares de aprovação

| Métrica | Limiar | Por quê |
|---|---|---|
| `delta_pct` | −5% a +50% | V2 pode achar **mais** (cursor no OpenAlex remove o teto de 10k); achar menos é regressão |
| `sobreposicao_pct` | ≥ 95% | O que a V1 acha, a V2 tem de achar |
| `so_na_v1` | ≤ 5% do total da V1 | Métrica mais importante: registros perdidos |
| cobertura de `abstract` | ≥ V1 | P0-5 e P1-6 |
| cobertura de `authors`, `year` | ≥ V1 | — |
| cobertura de `advisor` (BDTD) | ≥ 90% da V1 | P1-1, após Fase 5 |
| cobertura de `institution` (BDTD) | ≥ 90% da V1 | P1-1, após Fase 5 |

**Fontes obrigatórias:** BDTD, SciELO, OpenAlex. PubMed e Scopus ficam de fora
por decisão de escopo (§15.2).

---

## 16.6 Testes de carga e escala

Validam as Fases 3 e 4 sob o volume real do autor (140 descritores × ilimitado).

```python
@pytest.mark.slow
async def test_dedup_tempo_constante():
    """Regressão do P0-3(a): hoje o custo cresce com N."""
    tempos = []
    for bloco in range(10):                     # 10 blocos de 1.000
        t0 = time.perf_counter()
        await persistir_lote(gerar_registros(1000, offset=bloco * 1000))
        tempos.append(time.perf_counter() - t0)

    # Sem regressão quadrática: o último bloco não pode custar
    # muito mais que o primeiro.
    assert tempos[-1] < tempos[0] * 2, f"crescimento não-linear: {tempos}"

@pytest.mark.slow
async def test_event_loop_nao_bloqueia():
    """Regressão do P0-3(c): dedup síncrona congelava o WebSocket."""
    atrasos = []
    async def sonda():
        while True:
            t0 = time.perf_counter(); await asyncio.sleep(0.05)
            atrasos.append(time.perf_counter() - t0 - 0.05)

    t = asyncio.create_task(sonda())
    await coletar_com_mock(n_registros=5000)
    t.cancel()
    assert max(atrasos) < 0.1, f"loop bloqueado por {max(atrasos):.2f}s"

@pytest.mark.slow
async def test_cancelamento_responde_em_5s():
    job = await iniciar_coleta(descritores=CEM_DESCRITORES)
    await asyncio.sleep(10)
    t0 = time.perf_counter()
    await cancelar(job.run_id)
    assert time.perf_counter() - t0 < 5.0
    assert (await obter_run(job.run_id)).status == "cancelled"
```

**Marco de desempenho da Fase 4:** 20.000 registros persistidos e deduplicados em
**menos de 10 minutos**. Medir o número de hoje **antes** de otimizar — sem a
linha de base, não há como provar melhoria.

---

## 16.7 Script de diagnóstico rápido

`backend/scripts/diagnostico_fontes.py` — verifica em ~30 s se as cinco fontes
estão acessíveis e respondendo no formato esperado. Primeira coisa a rodar quando
o autor disser "parou de funcionar".

```python
"""
    python scripts/diagnostico_fontes.py

    BDTD ....... OK    HTTP 200   1.240ms   resultCount=3847   summary=list ✓
    SciELO ..... OK    HTTP 200     890ms   itens=15           #TotalHits ✓
    OpenAlex ... OK    HTTP 200     310ms   count=12903        next_cursor ✓
    PubMed ..... OK    HTTP 200     450ms   idlist=500
    Scopus ..... AVISO           sem chave de API configurada
"""

VERIFICACOES = [
    ("BDTD",     checar_bdtd),      # + tipo de `summary`
    ("SciELO",   checar_scielo),    # + seletores .item / #TotalHits
    ("OpenAlex", checar_openalex),  # + presença de next_cursor
    ("PubMed",   checar_pubmed),
    ("Scopus",   checar_scopus),    # + entitlement de view=COMPLETE
]
```

Cada verificação reporta: status HTTP, latência, contagem e **a asserção
estrutural específica daquela fonte** — é o que distingue "a fonte está fora do ar"
de "a fonte mudou de formato", dois problemas com soluções opostas.

---

## 16.8 Metas de cobertura

| Módulo | Hoje | Meta |
|---|:--:|:--:|
| `app/harvesters/` | **0%** | **85%** |
| `app/services/dedup_service.py` | parcial | 90% |
| `app/services/harvesting_service.py` | 0% | 75% |
| `app/domain/enums.py` (mapeamentos) | — | 100% |

O 0% em `harvesters/` é a causa-raiz organizacional do doc 13. Nenhum PR que
toque `app/harvesters/` deve ser aceito sem teste.

### Integração contínua

```yaml
# .github/workflows/ci.yml
- run: pytest -m "not canary and not slow" --cov=app --cov-fail-under=80
- run: ruff check . && mypy app/
- run: python scripts/checar_deps.py     # imports × pyproject (regressão do P0-1)
```

`checar_deps.py` percorre os imports de terceiros do backend e confere contra as
dependências declaradas. Teria pegado `bs4` e `pandas` no dia em que entraram.

---

**Próximo documento:** [`17_GUIA_DE_USO.md`](./17_GUIA_DE_USO.md)
