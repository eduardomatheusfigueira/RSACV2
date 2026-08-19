# 28 — Diagnóstico da Coleta: SciELO e BDTD

> **Objetivo deste documento:** avaliar o estado real dos dois coletores
> nacionais — SciELO e BDTD — quanto a qualidade de engenharia, confiabilidade
> e velocidade, e estabelecer a linha de base numérica sobre a qual o plano do
> doc 29 será medido.
>
> Toda afirmação aponta para `arquivo:linha` no código de 19/08/2026, ou para
> uma medição reproduzível por `backend/scripts/bench_coleta.py`. Onde a
> verificação exige rede — e portanto não pôde ser feita aqui — está marcado
> **[A VALIDAR EM REDE]**.
>
> Este documento **não repete** o doc 13. Aquele diagnosticou a coleta antes
> das correções dos docs 14–16; quase tudo que ele apontou foi corrigido
> (§ 28.2). O que segue é o diagnóstico do código **depois** daquele ciclo.

---

## 28.1 Resumo executivo

A coleta da V2 hoje está **correta no caso feliz e frágil nas bordas**. As
correções dos docs 14–16 entraram e se sustentam: o contrato de coleta existe,
a persistência saiu do event loop, a deduplicação deixou de ser O(N²), o BDTD
raspa detalhes e respeita a regra do WAF, o SciELO tem retry. Nada disso é
pouco, e nada disso precisa ser refeito.

O que o código **não** tem é o que separa um coletor que funciona de um coletor
em que se pode confiar para uma revisão sistemática:

| # | Achado | Natureza | Onde dói |
|:-:|--------|----------|----------|
| 1 | Concorrência real é **1** dentro de cada fonte; o semáforo do BDTD nunca tem dois esperando | Velocidade | 4,8 registros/s no BDTD com detalhes |
| 2 | **80% do relógio do SciELO** é pausa fixa, não requisição | Velocidade | 10 descritores levam 51 s onde a rede custa 10 s |
| 3 | Falha definitiva de página **encerra o descritor em silêncio** e a run é marcada `completed` | Confiabilidade | Número do PRISMA fica errado sem aviso |
| 4 | Não existe contabilidade **por descritor** — só agregada por fonte | Rastreabilidade | PRISMA 2020 item 7 não é atendível |
| 5 | Dedup incremental tem **corrida entre fontes**: 1 duplicata escapou em 300 títulos com 2 fontes | Correção | Piora exatamente quando se aumenta paralelismo |
| 6 | Similaridade de título **funde trabalhos distintos** e o DOI divergente não veta | Correção | Estudo some da triagem, invisivelmente |
| 7 | Capacidades declaradas **mentem**: filtros anunciados na UI que nenhum coletor lê | Profissionalismo | Usuário acredita ter recortado a busca |
| 8 | O frontend **nunca sabe que a coleta terminou** — `/status` não devolve o que ele espera | Confiabilidade | Tela fica "coletando" para sempre |
| 9 | Sem retomada: interrupção em 90% recomeça do zero | Robustez | Coleta de horas vira aposta |
| 10 | Suíte de testes: 2 arquivos, ~7 casos, todos caminho feliz | Qualidade | Nenhuma borda acima é testada |

Os itens 1 e 2 são **latência ociosa**, não falta de capacidade: o ganho vem de
parar de esperar, não de pedir mais. Isso importa porque SciELO e BDTD são
infraestrutura pública sem contrato de API — a política correta é manter o
mesmo orçamento de requisições por segundo e eliminar o tempo parado (§ 29.3).

---

## 28.2 O que está bom — e deve ser preservado

Ser justo com o código existente é parte do diagnóstico. O seguinte está certo
e o plano do doc 29 não deve tocá-lo:

- **Contrato de coleta explícito.** `HarvestQuery` / `RawPaperRecord` /
  `HarvesterCapabilities` (`backend/app/harvesters/base.py`) separam recorte,
  registro e capacidade. É a peça que permite tudo que o doc 29 propõe.
- **Coerção defensiva na fronteira.** `RawPaperRecord.__post_init__`
  (`base.py:76-97`) impede que lista ou `None` chegue ao SQLite — a origem do
  P0-5 do doc 13 não pode voltar por outro coletor.
- **Persistência fora do event loop.** `asyncio.to_thread(_persist_batch_sync, …)`
  (`harvesting_service.py:177`) com lotes de 25 (`:173`). Medido: **~630
  registros/s, escala linear até 8.000** (§ 28.6). A deduplicação **não é** o
  gargalo, e otimizá-la seria trabalho desperdiçado.
- **SQLite bem configurado.** WAL, `synchronous=NORMAL`, cache de 64 MB
  (`database.py:30-38`) e índices compostos que casam com as consultas da dedup
  (`models.py:122-127`).
- **Reconciliação no lifespan.** Runs presas em `running` após queda do processo
  viram `failed` na subida (`main.py:52-69`). Muitos sistemas maiores não fazem.
- **BDTD com conhecimento operacional real.** Regra do WAF de 2 filtros
  (`bdtd.py:43, 90-96`), dedup intra-execução por `record_id` (`bdtd.py:331,
  411-416`), correção de resumo trocado com orientador (`bdtd.py:146-163`),
  limpeza de nomes (`:101-143`), ordenação determinística (`:371`).
- **SciELO com retry exponencial e aquecimento de sessão** (`scielo.py:213-231`,
  `:177`).
- **Cancelamento gerenciado** com estado por projeto e escrita do desfecho no
  banco (`harvest_job_manager.py`, `harvesting_service.py:233-246`).

---

## 28.3 Velocidade — o diagnóstico medido

### 28.3.1 A medição

`backend/scripts/bench_coleta.py` substitui a rede por `httpx.MockTransport`
com **200 ms de latência por requisição** — otimista para as duas bases. O que
importa não é o tempo absoluto, é a **concorrência de pico** e a fração do
relógio gasta fora da rede.

```
cenário                              reg   req    tempo    reg/s   pico
BDTD fetch_details=false             200     2    0.91s    220.1      1
BDTD fetch_details=true              200   202   41.30s      4.8      1
SciELO 10 descritores                600    51   50.99s     11.8      1

SciELO: 10.2s de rede em 51.0s de relógio — 80% do tempo é pausa fixa.
```

### 28.3.2 · O semáforo do BDTD é decorativo

`bdtd.py:278` cria `asyncio.Semaphore(4)` e `bdtd.py:285` o usa dentro de
`_scrape_record_details`. Mas a chamada está **em linha no laço de registros**:

```python
# bdtd.py:470-471
if fetch_details and record_id:
    details = await self._scrape_record_details(client, record_id)
```

Cada iteração aguarda a raspagem anterior terminar antes de começar a próxima.
**Nunca há dois esperando no semáforo** — a concorrência de pico medida é 1, com
o semáforo dimensionado para 4. O limite existe, a concorrência não.

O custo é o dominante da fonte: 200 registros → 202 requisições → 41,3 s, contra
0,91 s sem detalhes. **A raspagem é 45× o custo da busca.** O doc 14 § 14.3 já
havia previsto a correção — *"raspar detalhes… com concorrência limitada
(`asyncio.Semaphore(4)`) em vez de sequencial"* — e a previsão não chegou ao
código. Com 4 em voo, os mesmos 200 registros caem para ~10 s; com 8, para ~5 s.

Extrapolando para o caso real do doc 14 (5.000 registros, latência de campo mais
alta que a simulada): **~85 min hoje contra ~11–20 min** com um pool de
consumidores — sem aumentar a taxa de requisições por segundo, só sem esperar.

### 28.3.3 · O SciELO passa 80% do tempo dormindo

`scielo.py:287` pausa `default_delay` (1,0 s) **depois de cada página**,
incondicionalmente, sem descontar o tempo que a requisição já levou. Some-se
`asyncio.sleep(0.5)` do aquecimento (`:178`). No cenário medido: 10,2 s de rede
dentro de 51,0 s de relógio.

A pausa de cortesia é legítima; a forma é que está errada. O correto é
**intervalo mínimo entre requisições** — `sleep(max(0, intervalo − decorrido))` —
que preserva exatamente a mesma taxa contra o servidor e devolve o tempo em que
a rede já estava trabalhando.

### 28.3.4 · Página de 15 onde cabem 50

`scielo.py:131` fixa `default_page_size=15`, com `max_page_size=50` declarado na
linha seguinte. São **3,3× mais viagens de ida e volta** do que o necessário, e
a viagem é o item caro. O doc 14 § 14.4 registra 15 como *"fixo pelo portal"*;
a página de busca do SciELO oferece 15/30/50 no seletor. **[A VALIDAR EM REDE]**

⚠️ **Armadilha antes de mexer nisso:** `scielo.py:283` encerra o descritor com
`if len(items) < page_size: break`. Se o portal ignorar `count=50` e devolver 15,
o coletor conclui "acabaram os registros" **na primeira página** e trunca todo
descritor em 15 resultados — silenciosamente. Pior: `scielo.py:191` calcula o
offset como `(page-1)*page_size+1`, então a página 2 pularia 35 registros. Elevar
a página sem antes trocar o critério de parada troca lentidão por perda de dados.

### 28.3.5 · Tudo é serial, exceto as fontes

| Nível | Hoje | Ponto no código |
|---|---|---|
| Fontes | até 3 em paralelo | `harvesting_service.py:77, 347-353` |
| Descritores dentro de uma fonte | **serial** | `scielo.py:182`, `bdtd.py:346` |
| Páginas dentro de um descritor | **serial** | `scielo.py:190`, `bdtd.py:354` |
| Detalhes dentro de uma página | **serial** | `bdtd.py:471` |

Com SciELO + BDTD selecionados, o paralelismo efetivo é 2 — e cada um dos dois
é uma fila indiana. Os três níveis internos são naturalmente paralelizáveis:
descritores são independentes entre si; páginas são conhecidas assim que a
primeira responde (`TotalHits` no SciELO, `resultCount` no BDTD); detalhes são
requisições independentes por registro.

### 28.3.6 · Botões de ritmo que não ligam em nada

`HarvestQuery` declara `page_size` e `delay` (`base.py:36-37`). `delay` **não é
lido por nenhum coletor**. `page_size` é lido pelos coletores mas **nunca é
preenchido** — `harvesting_service.py:327-335` monta a `HarvestQuery` sem ele.
Não há como ajustar ritmo nem página sem editar código.

---

## 28.4 Confiabilidade — onde a coleta mente

### 28.4.1 · Falha parcial vira sucesso silencioso

É o achado mais grave do documento, porque contamina o produto científico.

**SciELO** (`scielo.py:233-235`): esgotadas as 5 tentativas, `break` — o
descritor termina ali, com as páginas restantes nunca buscadas.
**BDTD** (`bdtd.py:402-404`): idêntico.

Em nenhum dos dois casos o fato é propagado. `_harvest_single_source` só marca
`failed` se uma **exceção** subir (`harvesting_service.py:248`); um `break`
interno não é exceção. A run termina `completed`, com `error_message` vazio, e
`records_found` contando apenas o que veio antes da falha.

O usuário vê "SciELO: 1.240 registros — concluída". O número verdadeiro podia
ser 4.000. Numa revisão sistemática esse número **é publicado** no fluxograma
PRISMA. Um erro de rede transitório vira, sem intermediário, um dado falso num
artigo.

O mesmo vale para o caso "o portal mudou de layout": `scielo.py:238-241` trata
zero itens como fim natural dos registros. Layout quebrado e busca sem
resultados são indistinguíveis — apesar de o coletor já ter lido `TotalHits`
na página 1 (`:246-258`) e poder comparar. Hoje esse total é apenas **logado**
(`:260`) e descartado.

### 28.4.2 · A auditoria para na fonte, e o PRISMA precisa do descritor

`HarvestRunModel` guarda `descriptors_used` como um JSON e três contadores
agregados (`models.py:262-284`). Não há como responder "quantos registros o
descritor *X* trouxe da BDTD" — que é exatamente o que o PRISMA 2020 (item 7)
e a MECIR pedem: a estratégia completa **e o rendimento de cada busca**.

Sem isso também não há retomada possível (§ 28.4.7): não se sabe onde parou.

### 28.4.3 · Corrida na deduplicação entre fontes

`process_record_in_session` (`dedup_service.py:125-202`) lê e depois escreve, e
cada lote roda em **sessão própria** (`harvesting_service.py:159-167`) numa
thread própria. Duas fontes concorrentes podem ambas ler "não existe" para o
mesmo trabalho e ambas inserir. Não há defesa no esquema: os índices de
`models.py:122-127` **não são únicos**.

Medido com duas fontes simultâneas e 300 títulos idênticos entre elas:
**301 papers gravados para 300 títulos — uma duplicata escapou.** É pouco em
proporção e muito em consequência: a duplicata só é percebida se o usuário
rodar a deduplicação em lote depois. E o defeito escala com o paralelismo, que
é justamente o que o doc 29 quer aumentar.

### 28.4.4 · A similaridade funde trabalhos distintos, e o DOI não a impede

`find_duplicate` passo 3 (`dedup_service.py:92-121`) aceita como duplicata
qualquer candidato com `token_sort_ratio ≥ 92` e ano a menos de 3 de distância.
Não há **veto por DOI divergente** — dois registros com DOIs diferentes, que é
prova forte de serem trabalhos distintos, são fundidos assim mesmo.

Medido em pares realistas que compartilham a mesma chave de bloqueio:

| ratio | efeito | par |
|---:|:--:|---|
| 98,9 | **funde** | "…: parte I" vs "…: parte II" |
| 97,7 | **funde** | "…: volume 1" vs "…: volume 2" |
| 93,3 | **funde** | "…entre 2010 e 2015" vs "…entre 2016 e 2020" |
| 87,6 | ok | "Efeitos da seca…" vs "Efeitos da chuva…" |
| 84,3 | ok | "…solo urbano…" vs "…solo rural…" |

Três de cinco. A direção do erro é a pior possível: **falso positivo remove um
estudo da triagem**, e diferente do falso negativo (uma duplicata a mais para o
usuário descartar) ele é invisível — o estudo simplesmente nunca aparece.

Agrava: a fusão feita **durante a coleta** não deixa registro. O relatório de
deduplicação (`dedup_service.py:248-476`) só descreve o que a passada em lote
encontrou; as fusões incrementais do caminho de coleta não entram em lugar
nenhum. O único vestígio é uma linha em `paper_sources`.

### 28.4.5 · Política de retry sem princípio

**SciELO** (`scielo.py:211-231`): 5 tentativas com `1.5**attempt` — sem *jitter*
(coletas simultâneas de fontes diferentes se realinham nos mesmos instantes) e
**ignorando `Retry-After`**, que é o único número que o servidor efetivamente
informou. Qualquer status fora de `RETRY_STATUS_CODES` (403 do WAF, por exemplo)
é tratado como fatal para o descritor inteiro, sem uma tentativa.

**BDTD** (`bdtd.py:381-400`): o laço percorre `BASE_URLS` e, em 429, dorme 15 s
fixos **dentro** do laço de espelhos, sem informar as outras corrotinas de que o
host está saturado. Cada tarefa descobre o 429 por conta própria, e todas
continuam batendo.

### 28.4.6 · Dois acervos sob um nome só, e a raspagem apontando para o errado

`bdtd.py:248-251` alterna entre `bdtd.ibict.br` e `oasisbr.ibict.br` como se
fossem espelhos. **Não são.** O OasisBR é um agregador mais amplo (inclui
artigos e outros repositórios); a BDTD é teses e dissertações. Registros dos
dois entram no acervo com `source_name="BDTD"` (`bdtd.py:494`), e qual dos dois
respondeu depende de qual estava no ar. Para reprodutibilidade — o valor central
do produto — isso é grave: repetir a mesma coleta pode dar um corpus diferente
sem que nada no registro explique por quê.

Efeito colateral concreto: `_scrape_record_details` monta a URL **sempre** com
`bdtd.ibict.br/vufind/Record/{id}` (`bdtd.py:282`). Um `id` que só existe no
OasisBR dá 404, a exceção é engolida em `logger.debug` (`:303-304`) e o registro
perde orientador e instituição de defesa — em silêncio.

### 28.4.7 · Sem retomada e sem orçamento de tempo

Interromper uma coleta de três horas em 90% significa recomeçar do zero: não há
checkpoint por descritor, nem `resume` de uma run existente. Também não há
prazo máximo — nem por descritor, nem por run. Uma fonte lenta pode segurar a
execução indefinidamente, e a única saída é o cancelamento manual.

### 28.4.8 · O WebSocket empurra, e a coleta espera

`ws_manager.broadcast` é aguardado **dentro** do laço de coleta
(`harvesting_service.py:188`) e faz `await ws.send_json` por conexão
(`:61-63`). Um cliente lento aplica contrapressão TCP direto na coleta. O canal
de observação não pode ser capaz de frear o que observa.

---

## 28.5 Profissionalismo — as promessas que o código não cumpre

### 28.5.1 · Capacidades declaradas que ninguém lê

`/harvest/sources` (`harvest.py:170-228`) devolve as `capabilities` à UI, que as
exibe. Confrontando com o que os coletores fazem:

| Declarado | Fonte | Realidade no código |
|---|:--:|---|
| `supports_open_access=True` | SciELO | `query.open_access_only` **nunca é lido** (`scielo.py`) |
| `supports_language=True` | BDTD | ✅ pós-filtro local (`bdtd.py:419-422`) |
| `supports_document_type=True` | BDTD | `query.document_types` **nunca é lido** por nenhum coletor |
| `supports_institution=True` | BDTD | `query.institutions` **nunca é lido** |
| — | SciELO | `languages` e `document_types` ignorados, sem nem pós-filtro |

`harvesting_service.py:332` chega a passar `document_types` para a `HarvestQuery`,
e o campo morre ali. O usuário marca "só teses" e recebe tudo.

### 28.5.2 · O frontend não fecha o ciclo

`HarvestPage.tsx:221-254` inicia um `setInterval` de 1,5 s que só termina quando
`statusRes.is_complete` for verdadeiro. **O backend nunca devolve esse campo** —
`GET /harvest/status` (`harvest.py:125-149`) responde `{project_id, status,
started_at, sources}` ou `{status, last_run_id, completed_at}`. Consequências
encadeadas:

1. A tela fica "coletando" indefinidamente após o fim real da coleta.
2. O aviso de conclusão (`:242`) nunca dispara.
3. `setProgress(statusRes.progress || {})` (`:224`) **zera o painel por fonte** a
   cada 1,5 s, porque `progress` também não existe na resposta.
4. O intervalo não é limpo ao desmontar o componente — sai da tela e continua
   consultando o backend para sempre.
5. Só um erro HTTP encerra o laço — e aí a mensagem exibida é
   *"A coleta foi interrompida"*, quando ela pode ter terminado bem.

E as mensagens que o backend **de fato** emite — `harvest_progress`,
`harvest_source_failed`, `harvest_error`, `harvest_cancelled`,
`harvest_all_completed` — não têm tratamento nenhum em `HarvestPage.tsx:104-127`,
que só reage a `paper_harvested` e `harvest_source_completed`. **Uma fonte que
falha por completo não produz nenhum sinal visível na interface.**

### 28.5.3 · Os filtros não saem da tela

`api.startHarvest` é chamado com `sources` e `max_records_per_descriptor` apenas
(`HarvestPage.tsx:215-218`). `year_start`, `year_end`, `languages`,
`document_types` e `fetch_details` existem no schema (`schemas/harvest.py:11-24`),
são resolvidos contra o protocolo (`harvesting_service.py:322-325`) e **nunca são
enviados**. Todo o recorte temporal e linguístico construído no backend está
inalcançável pela interface — inclusive o `fetch_details=False`, que é o botão
"coleta rápida" previsto no doc 14 § 14.3 e que hoje é o único jeito de escapar
dos 4,8 registros/s do § 28.3.2.

### 28.5.4 · Detalhes de acabamento

- **Timeout do BDTD nunca é o declarado.** `BDTDHarvester.__init__` define 50 s
  (`bdtd.py:266`), mas a fábrica passa o seu próprio padrão de 35 s
  (`factory.py:154, 178`) e o serviço não informa nada. A fonte mais lenta roda
  com o timeout genérico.
- **Cookie de WAF fixo no código.** `"OasisbrVerify=verified_human"`
  (`bdtd.py:274`) — conhecimento operacional real, sem comentário explicando o
  que é, quando foi obtido e o que fazer quando parar de valer.
- **`HarvesterFactory.get_all_available`** (`factory.py:194-195`) devolve lista
  literal em vez do registro que o decorador preenche; uma fonte nova registrada
  não aparece.
- **Importações mortas.** `factory.py:158-162` e `:182-186` importam cinco
  coletores para efeito de registro e o linter marca todos como não usados; o
  padrão correto é um módulo de registro explícito.
- **Cancelamento não drena o que está no ar.** `to_thread` não é cancelável: o
  lote em voo pode ser gravado **depois** de a run ter sido marcada `cancelled`.
- **`cancel_job` captura `Exception` junto de `CancelledError`**
  (`harvest_job_manager.py:94`) — engolir `CancelledError` no chamador é receita
  de tarefa que não morre.

### 28.5.5 · A suíte de testes não cobre nenhuma borda

`test_scielo.py` (2 casos) e `test_bdtd.py` (5 casos). Ambos os testes de coleta
devolvem **a mesma página para qualquer requisição** e terminam porque a página
é menor que o tamanho pedido. Não existe teste para: segunda página, retry, 429,
`Retry-After`, falha definitiva, cancelamento, corrida de dedup, `fetch_details`,
espelho do BDTD, nem regressão do parser do SciELO contra HTML real salvo.

Para uma fonte que é **raspagem de HTML de um portal que pode mudar sem aviso**,
não ter teste-canário com fixture real é a lacuna mais cara da suíte.

---

## 28.6 O que **não** é o problema

Registrar isto vale tanto quanto registrar os defeitos, porque evita otimizar o
lugar errado:

| N acumulado | tempo (s) | reg/s no trecho |
|---:|---:|---:|
| 500 | 0,79 | 636 |
| 1.000 | 1,51 | 690 |
| 2.000 | 3,03 | 659 |
| 4.000 | 6,21 | 629 |
| 8.000 | 12,60 | 626 |

A deduplicação incremental custa **~1,6 ms por registro e escala linearmente** —
as chaves de bloqueio e os índices compostos fizeram o serviço. Contra os
~208 ms por registro da raspagem do BDTD, a dedup é **0,8% do custo**. O
gargalo é latência de rede não sobreposta; qualquer esforço em SQL ou em
`rapidfuzz` seria desperdício.

---

## 28.7 Veredito por dimensão

| Dimensão | Nota | Justificativa curta |
|---|:--:|---|
| Arquitetura | **Boa** | Contrato, fábrica, gerente de job e separação de camadas bem postos |
| Qualidade do parsing | **Boa** | BDTD trata casos reais que quase ninguém trata; SciELO é correto |
| Correção dos dados | **Frágil** | Fusão indevida por similaridade e corrida na dedup (§ 28.4.3–4) |
| Confiabilidade | **Insuficiente** | Falha parcial vira sucesso silencioso (§ 28.4.1) |
| Rastreabilidade | **Insuficiente** | Sem contabilidade por descritor (§ 28.4.2) |
| Velocidade | **Insuficiente** | Concorrência real 1; 80% de espera ociosa (§ 28.3) |
| Cobertura de teste | **Insuficiente** | Só caminho feliz (§ 28.5.5) |
| Coerência com a UI | **Insuficiente** | Filtros inalcançáveis, fim de coleta não detectado (§ 28.5.2–3) |

O sistema não precisa ser reescrito. Precisa de **quatro coisas**: dizer a
verdade sobre o que coletou, não fundir o que é distinto, sobrepor a espera, e
ser testado nas bordas. É o que o doc 29 organiza.

---

## 28.8 Verificações que exigem rede

Itens que este diagnóstico **não** pôde fechar sem sair para a internet, e que
abrem a fase 0 do doc 29:

1. `count=50` no `search.scielo.org` devolve 50 itens? (§ 28.3.4)
2. Qual o teto real de paginação profunda do VuFind da BDTD, e a ordenação por
   `year` é estável entre páginas (empates)?
3. `publishDate:"[1970 TO 2023]"` com aspas (`bdtd.py:339`) é interpretado como
   faixa pelo VuFind — como a URL de facetas do próprio VuFind sugere — ou como
   frase, anulando o filtro?
4. Qual a taxa de requisições que cada base tolera antes de 429/403, para
   calibrar o governador de host (§ 29.3)?
5. O cookie `OasisbrVerify` ainda é necessário?
