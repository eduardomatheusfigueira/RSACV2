# 19 — Especificação: Aquisição, Leitura e Uso do Texto Completo

> **Objetivo:** definir o comportamento correto do subsistema de PDF, de ponta a
> ponta, de forma verificável. Este documento é o contrato; o doc 20 é o plano
> de execução e o doc 21 é a suíte de validação.
>
> Responde ao diagnóstico do doc 18. Cada seção referencia os problemas que
> fecha (`D1.2`, `D4.1`, ...).

---

## 19.1 Princípios

1. **O link coletado é uma pista, não um endereço.** Todo o desenho parte de
   que `download_url` é a página do registro. O sistema tem que *procurar* o
   arquivo, como faria um bibliotecário. (D1.1)
2. **Várias vias, tentadas em ordem de probabilidade.** Uma falha nunca encerra
   a busca; encerra apenas aquela via. (D1.2)
3. **Falhar é resultado, não exceção.** Quando nenhuma via funciona, o sistema
   devolve a trilha do que tentou e a próxima ação recomendada. (D1.5)
4. **Procedência é dado de pesquisa.** De onde veio o arquivo, por qual via e
   quando, fica gravado junto do trabalho. (D1.7)
5. **Nada entra sem validação.** Só é gravado o que abre como PDF legível.
   (D2.6)
6. **A IA lê o que é relevante, não o que está no começo.** O contexto é
   selecionado pelas perguntas de extração. (D4.1)
7. **Toda resposta assistida carrega evidência.** Trecho literal e página.
   (D4.3)

---

## 19.2 Arquitetura do subsistema

```
              ┌──────────────────────────────────────────────┐
              │  API  /extraction/pdf/{acquire,status,text,   │
              │       candidates,upload,batch}               │
              └───────────────┬──────────────────────────────┘
                              │
        ┌─────────────────────┴───────────────────────┐
        │                                             │
┌───────▼─────────────┐                    ┌──────────▼──────────┐
│ pdf_acquisition.py  │  procedência,      │  extraction_service │
│ (ORM + lote)        │  lote, estado      │  (contexto + IA)    │
└───────┬─────────────┘                    └──────────┬──────────┘
        │                                             │
┌───────▼──────────────────────────────────────────────▼─────────┐
│ pdf_service.py — armazenamento, cache de texto, contexto        │
└───────┬─────────────────────────────────────┬───────────────────┘
        │                                     │
┌───────▼──────────────┐            ┌─────────▼────────────────────┐
│ pdf_resolver.py      │            │ pdf_text.py                  │
│ 9 vias de busca      │            │ limpeza, seções, chunks      │
└──────────────────────┘            └──────────────────────────────┘
```

Cada módulo tem uma responsabilidade e nenhuma dependência circular:
`pdf_resolver` e `pdf_text` não conhecem banco nem HTTP; `pdf_service` não
conhece ORM; `pdf_acquisition` é o único que fala com `PaperModel`.

---

## 19.3 Vias de busca (ordem de tentativa)

A ordem é por **probabilidade × custo**: o que é grátis e provável vem antes.

| # | Via | Entrada | Rede | O que produz |
|---|-----|---------|------|--------------|
| 1 | `direct` | `download_url` | 0 req. | A própria URL, se aparenta ser PDF |
| 2 | `pattern` | URL / DOI | 0 req. | Transformações conhecidas por domínio |
| 3 | `unpaywall` | DOI + e-mail | 1 req. | `url_for_pdf` de todos os depósitos abertos |
| 4 | `openalex` | DOI ou título | 1 req. | `pdf_url` de `best_oa_location` e demais |
| 5 | `semantic` | DOI | 1 req. | `openAccessPdf`, arXiv e PMC por identificador |
| 6 | `crossref` | DOI | 1 req. | `link[]` declarado pelo editor |
| 7 | `europepmc` | DOI ou PMID | 1 req. | `fullTextUrlList` e PMC |
| 8 | `landing` | `download_url` | 1 req. | Raspagem da página de origem |
| 9 | `doi_landing` | DOI | 1 req. | Raspagem de `https://doi.org/{doi}` |

### 19.3.1 Padrões por domínio (via 2)

Transformações que um pesquisador faz na mão, sem custo de rede:

| Domínio | Regra |
|---------|-------|
| SciELO clássico | `script=sci_arttext` → `script=sci_pdf` |
| SciELO novo | `/j/{periodico}/a/{id}/` → `?format=pdf&lang={pt,en}` |
| arXiv | DOI `10.48550/arXiv.N` ou URL `/abs/N` → `arxiv.org/pdf/N` |
| PubMed Central | `PMC{n}` → `/pmc/articles/PMC{n}/pdf/` |
| DSpace (BDTD) | `handle/{a}/{b}` → `/bitstream/handle/{a}/{b}` |
| OJS / SEER | `/article/view/{id}` → `/article/download/{id}` |
| Teses USP | `{url}` → `{url}/pt-br.php` |

### 19.3.2 Raspagem de landing page (vias 8–9)

Ordem de confiança dentro da página:

1. `<meta name="citation_pdf_url">` — padrão Highwire, respeitado por
   praticamente todo editor e pelo próprio Google Acadêmico.
2. `<link rel="alternate" type="application/pdf">`.
3. Âncoras `<a href>` pontuadas:

| Sinal | Peso |
|-------|------|
| Casa com o `handle` do DSpace da própria página | +10 |
| Termina em `.pdf` | +6 |
| Contém `?format=pdf` | +4 |
| Contém `bitstream` | +3 |
| `sequence=1` / `isAllowed=y` | +2 cada |
| Texto do link menciona "PDF" / "texto completo" | +2 cada |

**Descartes obrigatórios** (nunca são o trabalho): `thumbnail`, `licenca`,
`politica`, `logo`, `.png/.jpg`, `tutorial`, `guia`, `capa`, `ficha`,
`termo`, `autorizacao`, `declaracao`.

### 19.3.3 Salto de página intermediária

Se um candidato devolver HTML em vez de PDF — típico de `?format=pdf` que cai
num visualizador embutido — o resolvedor **raspa essa página e tenta os 3
melhores links dela**, um salto apenas. É o caso do "o PDF está ali do lado"
descrito pelo usuário. As tentativas derivadas aparecem na trilha com o
sufixo `+html`.

### 19.3.4 Validação de candidato

Um download só é aceito se **todas** valerem:

| Critério | Regra |
|----------|-------|
| Status | HTTP 200 |
| Assinatura | Começa com `%PDF` nos primeiros 1024 bytes (tolera lixo inicial) |
| Tamanho mínimo | ≥ 2 KB (abaixo disso é página de erro disfarçada) |
| Tamanho máximo | ≤ 120 MB |

### 19.3.5 Orçamentos

| Parâmetro | Padrão | Config |
|-----------|--------|--------|
| Tempo total por trabalho | 120 s | `RSAC_PDF_SEARCH_TIMEOUT` |
| Tempo por requisição | 25 s | `RSAC_PDF_REQUEST_TIMEOUT` |
| Máximo de candidatos testados | 18 | — |
| Concorrência no lote | 3 | `RSAC_PDF_BATCH_CONCURRENCY` |
| E-mail de contato | vazio | `RSAC_CONTACT_EMAIL` |

> **Sobre o e-mail:** Unpaywall **exige** identificação — sem ele, a via 3 é
> pulada (não falha). OpenAlex e Crossref dão prioridade de fila a quem se
> identifica. Configurar o e-mail institucional aumenta a taxa de sucesso e é
> a etiqueta correta de uso dessas APIs públicas.

---

## 19.4 Trilha de tentativas

Toda tentativa gera um registro persistido em `papers.pdf_attempts` (JSON):

```json
{
  "strategy": "landing",
  "url": "https://repositorio.exemplo.br/handle/1/2",
  "status": "nao_pdf",
  "detail": "HTML recebido no lugar do arquivo (landing page ou bloqueio).",
  "http_status": 200
}
```

| `status` | Significado | Orientação ao usuário |
|----------|-------------|-----------------------|
| `ok` | PDF válido obtido | — |
| `nao_pdf` | Veio HTML ou outro tipo | Abrir o link e copiar o endereço real |
| `http_erro` | 4xx/5xx (401/402/403 = restrito) | Acessar pela instituição e anexar |
| `timeout` | Fonte não respondeu | Tentar novamente mais tarde |
| `erro` | Falha de conexão/TLS | Verificar rede |
| `vazio` | Resposta sem corpo | — |
| `pequeno_demais` | PDF menor que 2 KB | Provável página de erro |

A mensagem final de falha é **classificada**, não genérica: bloqueio por
assinatura, devolução de HTML e ausência de arquivo geram orientações
distintas.

---

## 19.5 Procedência persistida

Campos acrescentados a `papers` (migração automática via
`_migrate_missing_columns`):

| Campo | Tipo | Conteúdo |
|-------|------|----------|
| `pdf_status` | texto | `ausente` \| `obtido` \| `manual` \| `falhou` \| `indisponivel` |
| `pdf_resolved_url` | texto | URL final de onde o arquivo veio |
| `pdf_strategy` | texto | Via que teve sucesso |
| `pdf_attempts` | JSON | Trilha completa da última busca |
| `pdf_page_count` | inteiro | Páginas do documento |
| `pdf_size_bytes` | inteiro | Tamanho do arquivo |
| `pdf_sha256` | texto | Hash para conferência de integridade |
| `pdf_text_chars` | inteiro | Caracteres extraíveis |
| `pdf_is_scanned` | booleano | Documento sem camada de texto |
| `pdf_acquired_at` | data/hora | Quando foi obtido |

Esses campos alimentam o relato metodológico: "dos 62 estudos incluídos, 47
tiveram texto completo recuperado automaticamente (31 via depósito aberto, 16
via repositório institucional), 11 foram anexados manualmente e 4 não estavam
disponíveis".

---

## 19.6 Pipeline de texto

### 19.6.1 Extração (D2.1)

Extração por **blocos** (`get_text("blocks")`), com ordem de leitura
reconstruída: detecta layout de coluna única (mais de 35% dos blocos cruzam o
eixo central) e, quando são duas colunas, ordena por `(coluna, y, x)`. Motor
primário PyMuPDF, fallback pypdf.

### 19.6.2 Limpeza (D2.2)

| Passo | Regra |
|-------|-------|
| Ligaduras e aspas | `ﬁ→fi`, `ﬂ→fl`, aspas curvas → retas, NFKC |
| De-hifenização | `regio-\nnal` → `regional` (aplicada até estabilizar) |
| Linhas de folio | Linha contendo apenas número de página é descartada |
| Cabeçalho/rodapé | Linha de borda repetida em ≥ 60% das páginas é removida |
| Espaçamento | Espaços múltiplos colapsados; ≥ 3 quebras viram 2 |

**Guarda contra perda de conteúdo:** a detecção de cabeçalho/rodapé só
considera páginas com **4 ou mais linhas** de conteúdo, e só remove linhas nas
**bordas** da página. Numa página de duas linhas, toda linha seria "borda" — o
conteúdo seria confundido com diagramação.

### 19.6.3 Paginação e seções (D2.3)

O documento é preservado como lista de páginas numeradas. A segmentação em
IMRaD reconhece títulos em português, inglês e espanhol
(`resumo`, `introducao`, `referencial`, `metodo`, `resultados`, `discussao`,
`conclusao`, `referencias`), tolerando numeração (`3.`, `3.1`, `III -`). Uma
linha só é título se tiver **até 6 palavras** — assim "Metodologicamente, este
estudo..." não vira cabeçalho de seção.

### 19.6.4 Cache (D2.4)

O texto extraído é gravado em `{paper_id}.txt` (JSON com páginas e
diagnóstico) ao lado do PDF. O cache é usado se for **mais novo que o
arquivo**, e é invalidado ao substituir ou apagar o PDF.

### 19.6.5 Documento digitalizado (D2.5)

Média de caracteres por página abaixo de **120** marca `is_scanned = true`. A
interface avisa, a aba "PDF" continua utilizável para leitura humana e a
extração assistida cai explicitamente para o resumo.

---

## 19.7 Contexto enviado à IA (D4.1, D4.2)

Substitui o recorte "começo + fim" por seleção orientada às perguntas:

1. **Cabeça garantida** — os primeiros ~6.000 caracteres entram sempre
   (título, autoria, resumo, palavras-chave).
2. **Blocos pontuados** — o restante é dividido em blocos de ~1.400
   caracteres, pontuados pela sobreposição de termos com as perguntas de
   extração (sem palavras vazias de pt/en/es), normalizada pelo tamanho do
   bloco.
3. **Peso por seção** — método, resultados, discussão e conclusão recebem
   ×1,35; lista de referências recebe ×0,15.
4. **Remontagem em ordem** — os blocos selecionados voltam à ordem do
   documento, com marcação `[[p. N]]` e sinalização explícita dos cortes.

Orçamento padrão: **28.000 caracteres** (~7–9 mil tokens), configurável em
`RSAC_AI_CONTEXT_BUDGET_CHARS`.

---

## 19.8 Extração assistida com evidência (D4.3, D4.4)

O prompt passa a exigir, por resposta:

```json
{
  "question_id": "...",
  "answer": "Resposta sintetizada e ancorada no texto",
  "evidencia": "Trecho literal do estudo (até 300 caracteres)",
  "pagina": "12"
}
```

Regras declaradas ao modelo: ancoragem estrita (`Não informado no texto`
quando ausente), preservação de números/unidades/recortes territoriais,
proibição de completar por conhecimento externo.

Persistência em `extraction_answers`: `evidence`, `page_ref`, `source_kind`
(`pdf` | `resumo` | `manual`). Na interface, a evidência aparece sob a
resposta e o chip de página abre o documento naquela página (`#page=N`).

Quando o contexto não veio do PDF, `source_kind = "resumo"` e a interface
avisa — nunca mais fallback silencioso.

---

## 19.9 Contrato HTTP

| Método | Rota | Papel |
|--------|------|-------|
| `POST` | `…/extraction/pdf/acquire` | Busca multi-estratégia; **200 sempre**, com `success` e trilha |
| `POST` | `…/extraction/pdf/download` | Alias histórico; 404 em falha (compatibilidade) |
| `GET` | `…/extraction/pdf/status` | Estado e procedência, sem tocar na rede |
| `GET` | `…/extraction/pdf/candidates` | Diagnóstico: candidatos sem baixar |
| `POST` | `…/extraction/pdf/upload` | Anexo manual, com validação de assinatura |
| `GET` | `…/extraction/pdf` | Arquivo, `inline` (ou `?download=true`) |
| `GET` | `…/extraction/pdf/text` | Texto paginado + seções + diagnóstico (`?refresh=true`) |
| `DELETE` | `…/extraction/pdf` | Desvincula: arquivo, cache e procedência |
| `POST` | `…/extraction/pdf/batch` | Lote nos elegíveis (`only_missing`, `decision`) |
| `GET` | `…/extraction/pdf/batch` | Progresso do lote |
| `DELETE` | `…/extraction/pdf/batch` | Cancela o lote |

**Decisão de contrato:** `acquire` devolve 200 mesmo sem achar o arquivo. Não
encontrar não é erro do servidor — é o resultado da busca, e o corpo carrega a
informação de que a interface precisa. O alias `download` mantém 404 para não
quebrar integrações existentes.

---

## 19.10 Interface

### Extração (Triagem 2)

- **Três modos de leitura:** Resumo | PDF (documento renderizado) | Texto
  extraído. (D3.1)
- **Busca sempre disponível**, inclusive sem `download_url` — o DOI basta.
  (D1.8)
- **Selo de procedência** com via de origem, número de páginas e alerta de
  documento digitalizado.
- **Painel de diagnóstico** com a trilha, links candidatos e quatro ações de
  saída: abrir DOI, buscar no Google Acadêmico, colar link direto, anexar
  arquivo. (D1.5)
- **Lote com progresso** e cancelamento. (D1.6)
- **Evidência por resposta**, com chip de página. (D4.3)

### Triagem 1

Mesmos três modos de leitura e o botão de busca, para quem decide elegibilidade
lendo além do resumo. Remove o caminho morto descrito em D3.4.

### Electron

`webPreferences.plugins = true` — habilita o visualizador de PDF nativo do
Chromium, que é o que permite renderizar o documento embutido sem biblioteca
de terceiros no renderer.

---

## 19.11 Fora de escopo (registrado)

- **OCR embutido.** PDFs digitalizados são detectados e sinalizados, mas o app
  não roda OCR. Exigiria empacotar Tesseract/ocrmypdf (~300 MB) no instalador.
  Reavaliar se aparecer com frequência no acervo real da BDTD.
- **Acesso por assinatura institucional (proxy EZproxy/CAFe).** Exigiria
  gerenciar credenciais e sessão autenticada — decisão de produto, não de
  implementação.
- **Sci-Hub e afins.** Fora de questão por razões legais.
- **Reprocessar `download_url` já coletados** para gravar `source_url`
  separado. O resolvedor trata o campo como pista, o que torna a renomeação
  cosmética; fica para uma limpeza de esquema futura.

**Próximo documento:** [20 — Plano de Execução](./20_PLANO_EXECUCAO_PDF.md).
