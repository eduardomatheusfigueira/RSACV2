# 35 — Plano de Robustez e Velocidade da Coleta

> **Objetivo deste documento:** transformar os achados do doc 34 num plano
> executável, com ordem justificada, critérios de aceite verificáveis e alvos
> numéricos medidos pelo mesmo instrumento que produziu a linha de base
> (`backend/scripts/bench_coleta.py`).
>
> Escopo: SciELO e BDTD. Tudo que for construído aqui é infraestrutura comum
> (governador de host, escritor único, contabilidade por descritor) e serve
> igualmente a OpenAlex, PubMed e Scopus sem retrabalho.

---

## 35.1 As quatro afirmações que o plano precisa tornar verdadeiras

1. **A coleta diz a verdade.** Se uma página falhou, a run não é `completed`, e
   o relatório mostra qual descritor ficou incompleto.
2. **A coleta não perde estudo.** Nenhum trabalho distinto é fundido a outro, e
   toda fusão fica registrada.
3. **A coleta não espera à toa.** O tempo de relógio se aproxima do tempo de
   rede, sem aumentar a taxa de requisições contra as bases.
4. **A coleta pode ser retomada.** Interrupção não custa o que já foi feito.

Tudo abaixo serve a uma dessas quatro.

---

## 35.2 Ordem, e por que ela não é negociável

A tentação é começar pela velocidade — é o que incomoda. Seria errado:

```
verdade  →  correção  →  ritmo  →  paralelismo  →  retomada  →  interface
```

- **Paralelismo amplifica a corrida da dedup** (doc 34 § 34.4.3). Subir a
  concorrência antes de fechar a escrita multiplica duplicatas que escapam.
- **Paralelismo sem governador de host vira 429**, e 429 mal tratado (§ 34.4.5)
  vira coleta parcial silenciosa — ou seja, mais rápido para produzir um número
  errado.
- **Sem contabilidade por descritor não há retomada possível**, porque não se
  sabe onde parou; e não há como *provar* que o paralelismo não perdeu nada.

O ganho de velocidade da Fase 4 é o maior do plano e o mais fácil de escrever.
É também o único que depende de todos os anteriores.

---

## 35.3 O desenho de paralelismo

### 35.3.1 O princípio: gastar o mesmo, esperar menos

SciELO e BDTD são infraestrutura pública, sem contrato de API, sem cota
publicada. A regra do plano é explícita:

> **O orçamento de requisições por segundo contra cada host não aumenta.
> O que muda é quanto tempo se fica parado dentro desse orçamento.**

Hoje o BDTD faz ~1 requisição a cada 208 ms **em série** — o servidor vê
~4,8 req/s de um cliente que nunca tem duas em voo. Com 4 em voo respeitando o
mesmo intervalo mínimo, o servidor continua vendo a mesma taxa: o que sai é a
latência acumulada, não a carga. Esse é o argumento técnico e também o ético.

Orçamento inicial proposto, a calibrar com a Fase 0 (§ 35.4):

| Host | Intervalo mín. | Máx. em voo | Observação |
|---|:--:|:--:|---|
| `search.scielo.org` | 500 ms | 3 | raspagem de HTML; a mais frágil |
| `bdtd.ibict.br` (API) | 250 ms | 4 | JSON, barato para o servidor |
| `bdtd.ibict.br` (Record) | 250 ms | 6 | páginas estáticas de detalhe |

### 35.3.2 `HostGovernor` — um por host, compartilhado por todas as tarefas

A peça central. Sem ela, "paralelismo" é só descontrole distribuído.

```python
class HostGovernor:
    """Governa taxa, concorrência e saúde de UM host, para TODAS as corrotinas."""

    def __init__(self, intervalo_min: float, max_em_voo: int):
        self._sem = asyncio.Semaphore(max_em_voo)
        self._intervalo = intervalo_min      # ajustado por AIMD
        self._intervalo_base = intervalo_min
        self._proximo_livre = 0.0            # relógio monotônico
        self._trava = asyncio.Lock()
        self._sucessos_seguidos = 0
        self._aberto_ate = 0.0               # disjuntor

    async def adquirir(self) -> None:
        if (espera := self._aberto_ate - time.monotonic()) > 0:
            raise HostIndisponivel(espera)
        await self._sem.acquire()
        async with self._trava:              # serializa só o cálculo do slot
            agora = time.monotonic()
            alvo = max(agora, self._proximo_livre)
            self._proximo_livre = alvo + self._intervalo
        if (dormir := alvo - agora) > 0:
            await asyncio.sleep(dormir)

    def registrar_sucesso(self) -> None:     # AIMD: aumento aditivo
        self._sucessos_seguidos += 1
        if self._sucessos_seguidos >= 20:
            self._intervalo = max(self._intervalo_base, self._intervalo * 0.9)
            self._sucessos_seguidos = 0

    def registrar_pressao(self, retry_after: float | None) -> None:  # 429/503
        self._sucessos_seguidos = 0
        self._intervalo = min(self._intervalo * 2, 10.0)   # redução multiplicativa
        if retry_after:
            self._proximo_livre = time.monotonic() + retry_after
```

Três propriedades que o código de hoje não tem:

- **A pausa é intervalo entre requisições, não sono depois da resposta.** Devolve
  os 80% de espera ociosa do SciELO (doc 34 § 34.3.3) sem tocar na taxa.
- **Um 429 desacelera todas as tarefas do host**, não só a que o recebeu.
- **`Retry-After` é obedecido** — é o único número que o servidor informou.

O disjuntor (`_aberto_ate`) fecha o host após N falhas consecutivas: as tarefas
daquela fonte param, a outra fonte continua, e a run termina como
`completed_with_errors` com o motivo registrado — nunca como `completed`.

### 35.3.3 Três níveis de sobreposição, na ordem do retorno

**Nível 1 — detalhes do BDTD (o maior ganho, o menor risco).**
Trocar o `await` em linha (`bdtd.py:471`) por estágio produtor/consumidor:

```
página de busca ──► fila de registros ──► K consumidores de detalhe ──► saída
                    (dedup intra-run já aplicada aqui)
```

O semáforo que já existe passa a ter função real. Ganho medido possível:
41,3 s → ~10 s com K=4 no cenário do doc 34 § 34.3.1. **Requisito de ordem:**
os registros saem do coletor conforme os detalhes chegam, então o `matched_
descriptor` e a ordem determinística de saída precisam ser preservados no
registro, não na sequência de emissão.

**Nível 2 — descritores em paralelo dentro da fonte.** Uma fila de descritores e
`D` trabalhadores (`D=3`), cada um percorrendo a paginação do seu descritor. São
independentes por construção; a dedup intra-execução passa a precisar de
`set` protegido, ou de ser feita no escritor único (§ 35.5.2) — preferível.

**Nível 3 — páginas em paralelo dentro do descritor.** A primeira página informa
o total (`TotalHits` no SciELO, `resultCount` no BDTD): dá para calcular todas as
páginas restantes e buscá-las com fan-out limitado, em vez da cadeia serial de
ida e volta. Fica por último porque é o que mais depende de detalhes de cada
portal (estabilidade da ordenação sob paginação profunda — doc 34 § 34.8 item 2)
e o que menos rende depois dos níveis 1 e 2.

> O paralelismo total é **limitado pelo governador**, não pela soma dos níveis.
> Aumentar `D` ou `K` acima do orçamento do host só enche a fila do semáforo —
> o que é exatamente o comportamento desejado.

---

## 35.4 Fase 0 — Verdade e instrumento

**Entregas**

1. `backend/scripts/bench_coleta.py` — ✅ entregue com o doc 34; passa a ser o
   portão de regressão de desempenho.
2. **Fixtures reais** de uma página de busca do SciELO, de uma resposta da API do
   BDTD e de uma página `Record` do VuFind, salvas em
   `backend/tests/fixtures/coleta/`, com data de captura.
3. **Sonda de rede** (`scripts/sondar_bases.py`, execução manual, fora da CI):
   responde às cinco perguntas do doc 34 § 34.8 — `count=50` no SciELO, teto de
   paginação profunda do VuFind, filtro `publishDate` com aspas, taxa tolerada
   antes de 429, necessidade do cookie `OasisbrVerify`.

**Aceite:** os números do § 35.3.1 deixam de ser proposta e passam a ser medidos.

---

## 35.5 Fase 1 — A coleta para de mentir

### 35.5.1 Contabilidade por descritor

Novo modelo `HarvestQueryRunModel` (1 linha por par run × descritor):

| Campo | Uso |
|---|---|
| `run_id`, `source_name`, `descriptor` | identidade |
| `hits_reported` | total que a fonte declarou (`TotalHits` / `resultCount`) |
| `pages_fetched`, `records_yielded` | o que efetivamente entrou |
| `status` | `completed` · `partial` · `failed` |
| `error_message`, `last_page_ok` | motivo e ponto de retomada |
| `http_requests`, `retries`, `rate_limit_hits` | telemetria de operação |

Isso fecha três buracos de uma vez: o relato PRISMA por busca, a base da
retomada (Fase 5) e a prova de que o paralelismo não perdeu registro.

### 35.5.2 `partial` deixa de virar `completed`

- Todo `break` por falha definitiva (`scielo.py:233-235`, `bdtd.py:402-404`)
  passa a marcar o descritor como `partial` com o motivo.
- A run agrega: qualquer descritor `partial`/`failed` → run
  `completed_with_errors`.
- **Alarme de zero inesperado:** fonte declarou `hits_reported > 0` e o parser
  extraiu 0 itens → erro explícito, nunca "fim dos registros". É a única defesa
  automática contra mudança de layout do SciELO.

### 35.5.3 Capacidades param de mentir

Para cada flag de `HarvesterCapabilities`: ou o coletor implementa (nativo ou
pós-filtro local, como o BDTD já faz com idioma), ou a flag vira `False`. Alvo
mínimo: `document_types` e `languages` com pós-filtro local no SciELO;
`open_access_only` implementado ou desligado.

**Aceite:** um teste percorre o registro de coletores e falha se uma capacidade
declarada não tiver efeito observável sobre um conjunto de registros sintético.

---

## 35.6 Fase 2 — Escritor único e dedup que não perde estudo

### 35.6.1 Escritor único

Uma tarefa dona da escrita, alimentada por fila por todas as fontes:

```
SciELO ──┐
         ├──► asyncio.Queue ──► escritor único ──► to_thread(dedup+commit)
BDTD ────┘                       lotes de 100        índice em memória
```

Resolve de uma vez: a corrida do doc 34 § 34.4.3 (só um escritor), a contenção
de escrita do SQLite (só um), e o custo de `SELECT` por registro (índice
`doi → id`, `titulo_norm → id`, `blocking_key → [ids]` carregado uma vez por run).
Também libera os produtores para correr no ritmo do governador.

Rede de segurança independente do código: **índices únicos**
`(project_id, doi)` e `(project_id, title_normalized)` com `UPSERT`, para que
uma regressão futura não reintroduza duplicatas silenciosas.

### 35.6.2 A similaridade para de fundir o que é distinto

Três mudanças em `find_duplicate` (`dedup_service.py:92-121`):

1. **Veto por DOI divergente.** Dois DOIs válidos e diferentes ⇒ não são o mesmo
   trabalho, qualquer que seja a similaridade do título.
2. **Guarda de token discriminante.** Se os títulos normalizados diferem apenas
   em um número, algarismo romano ou ordinal (`parte i`/`parte ii`,
   `volume 1`/`volume 2`, `2010`/`2016`), não fundir — os três falsos positivos
   medidos no doc 34 § 34.4.4 caem por esta regra.
3. **Faixa de revisão humana.** Similaridade entre 85 e o limiar não funde:
   registra "possível duplicata" para conferência, prática padrão em revisão
   sistemática. O limiar vira configuração do protocolo, não constante.

E **toda fusão incremental passa a deixar rastro** no relatório de deduplicação,
não só na tabela `paper_sources`.

**Aceite:** os cinco pares do banco de medição resultam em 0 fusões; um par
genuinamente idêntico com DOIs iguais continua fundindo; a medição de corrida
com duas fontes fecha em exatamente 300/300.

---

## 35.7 Fase 3 — Ritmo e política de erro

- `HostGovernor` (§ 35.3.2) instanciado por host e injetado nos coletores.
- Cliente HTTP único por fonte, com `httpx.Limits` explícito e HTTP/2 quando o
  host suportar.
- Política de erro **classificada**, não por lista de códigos: `retryable`
  (429/5xx/timeout/rede), `fatal_descriptor` (400 malformado), `fatal_source`
  (403 persistente do WAF), `parse_error` (200 com corpo inesperado — nunca
  tratado como "acabou").
- Backoff exponencial **com jitter** e `Retry-After` obedecido.
- Corrigir o timeout do BDTD (`factory.py:154` sobrescreve os 50 s declarados em
  `bdtd.py:266`): timeout passa a ser propriedade do coletor.
- **Separar OasisBR do BDTD** (doc 34 § 34.4.6): fonte própria com `source_name`
  próprio, ou espelho declarado no registro da run e URL de detalhe amarrada ao
  host de origem. Não pode continuar dependendo de quem estava no ar.

---

## 35.8 Fase 4 — Paralelismo

Executa os três níveis do § 35.3.3 **nesta ordem**, medindo entre cada um:

| Passo | Mudança | Alvo no banco de medição |
|:--:|---|---|
| 4.1 | Detalhes do BDTD em pool de K=4 | 41,3 s → ≤ 12 s · pico ≥ 4 |
| 4.2 | Pausa vira intervalo mínimo (SciELO e BDTD) | SciELO 51,0 s → ≤ 20 s |
| 4.3 | Página do SciELO 15 → 50 **depois** de trocar o critério de parada | 51 req → ≤ 20 req |
| 4.4 | D=3 descritores em paralelo por fonte | SciELO ≤ 8 s · pico ≥ 3 |
| 4.5 | Fan-out de páginas a partir do total declarado | ganho residual, se houver |

⚠️ **4.3 depende de 4.3-a:** trocar `if len(items) < page_size: break`
(`scielo.py:283`) por parada em zero itens ou `offset > TotalHits`. Elevar a
página antes disso trunca todo descritor em 15 registros (doc 34 § 34.3.4).

**Alvo agregado:** no cenário do banco de medição, coleta BDTD+SciELO com
detalhes de **~92 s para ≤ 25 s**, com a mesma taxa de requisições por host.
Extrapolado ao caso real do doc 14 (5.000 registros na BDTD): **~85 min para
~15 min**.

**Aceite inegociável:** para o mesmo recorte, o conjunto de registros coletado
em série e em paralelo é **idêntico em conteúdo** (comparação por conjunto de
`source_id`). Paralelismo que muda o corpus é defeito, não otimização.

---

## 35.9 Fase 5 — Retomada e orçamento de tempo

- `POST /harvest/{run_id}/resume`: relê o `HarvestQueryRunModel`, pula descritores
  `completed`, retoma os `partial` a partir de `last_page_ok`.
- **Cache de identificadores por projeto**: um `source_id` do BDTD já presente no
  projeto não gasta requisição de detalhe. Numa recoleta, corta a maior parte do
  custo.
- Prazo máximo por descritor e por run, configurável; estouro marca `partial`
  com motivo — nunca trava.
- Cancelamento que **drena** a fila do escritor antes de fechar a run, para que
  nada seja gravado depois do desfecho.

---

## 35.10 Fase 6 — A interface fecha o ciclo

1. `GET /harvest/status` passa a devolver o que o cliente já espera:
   `is_complete`, `progress` por fonte, totais e lista de descritores com
   problema (`HarvestPage.tsx:221-254`).
2. `HarvestPage.tsx` trata `harvest_progress`, `harvest_source_failed`,
   `harvest_error`, `harvest_cancelled` e `harvest_all_completed`; hoje ignora
   todos (doc 34 § 34.5.2). Uma fonte que falha **precisa** aparecer na tela.
3. Limpar o `setInterval` no desmonte e reduzir o polling a rede de segurança do
   WebSocket, não a fonte primária.
4. Enviar os filtros que já existem no schema — ano, idiomas, tipos e
   `fetch_details` (o "coleta rápida" do doc 14) — hoje nunca enviados
   (`HarvestPage.tsx:215-218`).
5. Expor ritmo e página como ajuste avançado, ligados a `HarvestQuery.delay` e
   `page_size`, hoje inertes.
6. `ws_manager.broadcast` com fila limitada por conexão e descarte do mais
   antigo: o observador nunca freia a coleta (doc 34 § 34.4.8).

---

## 35.11 Fase 7 — Testes das bordas

| Teste | O que trava se faltar |
|---|---|
| Canário de parser com fixture real (SciELO e BDTD) | mudança de layout vira "0 resultados" |
| Paginação de 3 páginas com totais coerentes | truncamento silencioso |
| 429 com `Retry-After` e 500 intermitente | política de retry |
| Falha definitiva ⇒ descritor `partial` ⇒ run `completed_with_errors` | o achado nº 1 do doc 34 |
| Cancelamento no meio de um lote | escrita depois do desfecho |
| Corrida de dedup com 4 fontes simultâneas | § 35.6.1 |
| Falsos positivos de similaridade (5 pares) | § 35.6.2 |
| Paridade série × paralelo por conjunto de `source_id` | § 35.8 |
| Regressão de desempenho pelo banco de medição | ganho que se perde sem ninguém ver |

---

## 35.12 Riscos

| Risco | Probabilidade | Mitigação |
|---|:--:|---|
| Bloqueio de IP por paralelismo | Média | Orçamento por host inalterado; governador com AIMD e disjuntor; sonda da Fase 0 calibra antes |
| Página 50 do SciELO não suportada | Média | Critério de parada corrigido **antes** (4.3-a); sonda confirma |
| Ordenação instável quebra paginação profunda | Média | Sonda da Fase 0; fan-out de páginas (4.5) só entra se estável |
| Escritor único vira gargalo | Baixa | Medido em ~630 reg/s contra ~5 reg/s de produção; folga de 100× |
| Regra nova de dedup deixa passar duplicata real | Baixa | Faixa de revisão humana (85–92) expõe os casos limítrofes |
| Refatoração quebra o que funciona | Média | Paridade de conjunto como critério de aceite em toda fase |

---

## 35.13 Sequência sugerida

```
Fase 0  instrumento e sonda        ▸ 1 dia    (bench entregue; falta fixture + sonda)
Fase 1  contabilidade e verdade    ▸ 2 dias
Fase 2  escritor único e dedup     ▸ 2 dias
Fase 3  governador e política      ▸ 2 dias
Fase 4  paralelismo (4.1 → 4.5)    ▸ 3 dias   ◄ o ganho de velocidade está aqui
Fase 5  retomada e prazos          ▸ 2 dias
Fase 6  interface                  ▸ 2 dias
Fase 7  testes de borda            ▸ 2 dias   (parcialmente junto das fases)
```

Fases 1–3 são pré-requisito da 4. As fases 5 e 6 podem correr em paralelo com a
4 — tocam arquivos disjuntos.

**Se houver tempo para apenas uma coisa:** Fase 4.1 (pool de detalhes do BDTD)
é a maior mudança de velocidade por linha escrita. **Se houver tempo para apenas
uma correção:** § 35.5.2 (`partial` deixar de virar `completed`), porque é a que
protege o dado publicado.
