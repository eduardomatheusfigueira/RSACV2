# 36 — Correção: SciELO e BDTD voltando zeradas

> **Sintoma relatado (27/08/2026):** "os harvesters da SciELO e BDTD não estão
> recuperando nada, eles já começam zerados e não recuperam trabalhos".
>
> Este documento registra o que foi encontrado, o que foi corrigido e como
> confirmar a causa na máquina onde o problema aparece — a verificação em rede
> não pôde ser feita no ambiente de desenvolvimento (proxy bloqueia
> `search.scielo.org`, `bdtd.ibict.br` e `oasisbr.ibict.br`).

---

## 36.1 O ponto de partida: a coleta já funcionou

`estudo_validacao/project_target.json` guarda uma coleta real de **19/08/2026**:

| Fonte | Recuperados | Novos | Estado |
|---|---:|---:|---|
| BDTD | 94 | 87 | completed |
| SciELO | 24 | 17 | completed |
| OpenAlex | 1.560 | 1.465 | completed |

Os coletores parseavam corretamente o HTML e o JSON reais naquela data (os
`source_id` gravados, como `S1983-71512023000100154-scl`, vêm do portal). Ou
seja: **não é um parser que nunca funcionou** — é uma regressão de ambiente,
de recorte ou do lado do servidor, ocorrida depois daquela data.

## 36.2 Por que o sintoma é mudo

Antes desta correção, **qualquer** falha das duas fontes terminava igual: zero
registros, execução marcada `completed`, `error_message` vazio e nenhum sinal na
tela. Três defeitos empilhados:

1. **Coletor.** Esgotadas as tentativas, `break` encerrava o descritor
   (`scielo.py`, `bdtd.py`). Um `break` não é exceção, então o orquestrador —
   que só marca `failed` quando uma exceção sobe (`harvesting_service.py`) —
   registrava sucesso.
2. **API.** `GET /harvest/status` não devolvia `is_complete` nem `progress`,
   que é o que `HarvestPage.tsx` consulta a cada 1,5 s. O painel era zerado a
   cada consulta e a tela nunca saía de "coletando".
3. **Interface.** O WebSocket emitia `harvest_source_failed`, `harvest_error` e
   `harvest_progress`; a tela tratava apenas `paper_harvested` e
   `harvest_source_completed`. Uma fonte que falhava por completo não produzia
   sinal visível nenhum.

Numa revisão sistemática esse número zero vai para o fluxograma PRISMA. Falha
de rede virando dado publicado é o defeito mais grave do conjunto, e é o que
esta entrega ataca primeiro.

## 36.3 Causas prováveis do zero, e o que foi feito com cada uma

| # | Causa candidata | Efeito | Correção |
|:-:|---|---|---|
| 1 | **`lxml` ausente no executável empacotado.** O parser é escolhido por *string* (`BeautifulSoup(html, "lxml")`), então o PyInstaller não enxerga a dependência e não a empacota. Atinge exatamente as duas fontes que raspam HTML — as demais usam JSON/XML. | SciELO levanta `FeatureNotFound` e a fonte inteira falha; BDTD perde orientador e instituição | `app/harvesters/html_parser.py`: importa `lxml` explicitamente e degrada para `html.parser` se ele faltar; `--hidden-import=lxml` nos dois scripts de build |
| 2 | **Filtro de idioma do protocolo.** Desde 20/08 a tela passou a enviar `languages` do protocolo (`["pt","en","es"]`). O pós-filtro da BDTD comparava o valor cru: se a base devolve `"Português"` em vez de `"por"`, **todo** registro é descartado | BDTD zerada, sem aviso | `normalize_language()` compara por código canônico (`pt`, `pt-BR`, `Português`, `Portuguese` → `por`); quando o filtro zera a coleta, o motivo é anunciado |
| 3 | **Faixa de anos entre aspas.** `publishDate:"[1970 TO 2023]"` é lido pelo VuFind como frase literal, não como intervalo | BDTD zerada quando há recorte temporal | filtro montado sem aspas |
| 4 | **Bloqueio do portal (403 do WAF).** 403 não estava na lista de status com retry do SciELO: o descritor morria na primeira resposta | SciELO zerada | 403 entra em `RETRY_STATUS_CODES`, com reaquecimento da sessão entre tentativas; na BDTD, 401/403 são registrados como bloqueio |
| 5 | **Mudança de layout do portal.** Zero `div.item` era tratado como "fim dos registros" | SciELO zerada e silenciosa | página que anuncia `TotalHits > 0` sem itens reconhecidos vira falha explícita, distinta de busca legitimamente vazia |
| 6 | **BDTD e OasisBR tratados como espelhos.** A raspagem de detalhe apontava sempre para `bdtd.ibict.br`, mesmo com `id` vindo do OasisBR | perda muda de orientador/instituição | a URL de detalhe segue o host que respondeu, e o acervo de origem é gravado em `extra_metadata` |

## 36.4 O que passou a ser visível

- Nenhuma página lida com sucesso → `HarvestSourceError`, execução `failed`,
  motivo gravado em `error_message` e exibido na tela.
- Coleta parcial (alguns descritores incompletos) → execução `completed` **com
  aviso** gravado e anunciado na interface.
- Registros já recuperados antes de uma falha são gravados: o lote pendente é
  persistido no caminho de erro, em vez de descartado.
- `GET /harvest/status` devolve `is_complete`, `progress` por fonte, totais,
  `failures` e `warnings`.
- A tela trata `harvest_progress`, `harvest_source_failed`, `harvest_error`,
  `harvest_cancelled` e `harvest_all_completed`; o laço de polling é encerrado
  ao sair da página.

## 36.5 Como confirmar a causa na máquina afetada

```bash
python backend/scripts/diagnostico_coleta.py --descritor "turismo"
```

O script verifica, em uma execução: parser de HTML disponível e se o processo
está empacotado; alcance e status HTTP de cada endpoint; se a resposta tem a
estrutura que o coletor espera; o efeito da faixa de anos com e sem aspas; e os
dois coletores ponta a ponta. Cada linha aponta para uma das causas da tabela
§ 36.3.

## 36.6 O que permanece aberto

Itens do doc 34 que esta entrega **não** cobre e seguem no doc 35: concorrência
real dentro de cada fonte, contabilidade por descritor para o PRISMA, corrida
de deduplicação entre fontes, fusão indevida por similaridade de título,
retomada de coleta interrompida e as capacidades declaradas que nenhum coletor
lê (`document_types`, `institutions`, `open_access_only`).
