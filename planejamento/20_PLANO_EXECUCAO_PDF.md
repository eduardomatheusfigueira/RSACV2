# 20 — Plano de Execução: Subsistema de PDF e Extração

> **O que este documento é:** a sequência de trabalho que transforma o
> diagnóstico (doc 18) na especificação implementada (doc 19), com o estado de
> cada fase e o que resta.
>
> As fases 1 a 6 estão **implementadas** nesta entrega. As fases 7 a 9 são o
> trabalho remanescente, priorizado.

---

## 20.1 Estratégia

**Consertar de baixo para cima.** Não adianta melhorar o prompt da IA enquanto
não há texto para ler (ver cadeia causal em 18.6). A ordem é obrigatória:
aquisição → texto → contexto → interface.

**Manter as fronteiras.** Nenhuma assinatura pública foi removida:
`PDFService.download_pdf`, `extract_text_from_pdf` e `extract_key_sections`
continuam existindo com o mesmo contrato, agora com miolo melhor. O endpoint
`/pdf/download` continua respondendo como antes. Isso mantém a aplicação
subindo entre fases e preserva testes existentes.

**Falha é informação.** Toda decisão de projeto aqui privilegia mostrar o que
aconteceu em vez de esconder num `None`.

---

## 20.2 Sequência

```
Fase 1 ─ Resolvedor multi-estratégia          ✅  pdf_resolver.py
   │
Fase 2 ─ Serviço de aquisição e cache         ✅  pdf_service.py
   │
Fase 3 ─ Pipeline de texto                    ✅  pdf_text.py
   │
   ├── Fase 4 ─ Procedência + lote            ✅  pdf_acquisition.py, models, API
   │
   └── Fase 5 ─ Contexto e evidência da IA    ✅  extraction_service.py
              │
        Fase 6 ─ Interface (3 modos + trilha) ✅  ExtractionPage, ScreeningPage
              │
        Fase 7 ─ Validação em acervo real     ⬜  pendente
              │
        Fase 8 ─ OCR opcional                 ⬜  pendente (decisão de produto)
              │
        Fase 9 ─ Relato metodológico PRISMA   ⬜  pendente
```

---

## 20.3 Fase 1 — Resolvedor multi-estratégia ✅

**Entrega:** `backend/app/services/pdf_resolver.py`.

- 9 vias em ordem de probabilidade × custo (spec 19.3).
- Padrões por domínio sem custo de rede: SciELO (dois formatos), arXiv, PMC,
  DSpace, OJS/SEER, Teses USP.
- Raspagem com `citation_pdf_url` em primeiro lugar e âncoras pontuadas.
- Salto de página intermediária (`+html`), um nível.
- Validação por assinatura, tamanho mínimo e teto.
- Trilha `ResolutionAttempt` para toda tentativa.

**Aceite:** `PaperRef(download_url=<landing page com citation_pdf_url>)`
resulta em PDF baixado; conteúdo HTML nunca é gravado como PDF; falha devolve
trilha não vazia. Coberto por `tests/test_services/test_pdf_resolver.py`
(32 casos).

**Nota de projeto:** a via Unpaywall é **pulada** — não falha — quando não há
e-mail de contato configurado. Um erro registrado ali seria ruído: a via
simplesmente não se aplica.

---

## 20.4 Fase 2 — Serviço de aquisição e cache ✅

**Entrega:** `backend/app/services/pdf_service.py` reescrito.

- `acquire_pdf()` orquestra resolvedor → validação → gravação → leitura, e
  devolve `PDFAcquisition` com procedência, diagnóstico e trilha.
- `save_uploaded_pdf()` valida assinatura antes de gravar (D2.6).
- Cache de texto em `.txt` ao lado do PDF, invalidado por mtime e por
  substituição/remoção.
- `_failure_message()` classifica a falha (restrito / HTML / inexistente) e
  devolve orientação acionável.
- `download_pdf()` mantido por compatibilidade, agora atravessando o
  resolvedor.

**Aceite:** `test_pdf_service.py` (10 casos) — procedência gravada, cache
efetivo e invalidado, upload inválido rejeitado, `download_pdf` resolvendo
landing page.

---

## 20.5 Fase 3 — Pipeline de texto ✅

**Entrega:** `backend/app/services/pdf_text.py`.

- Extração por blocos com ordem de leitura em duas colunas.
- Limpeza: ligaduras, de-hifenização, folios, cabeçalho/rodapé repetido.
- Paginação preservada; segmentação IMRaD trilíngue.
- Detecção de documento digitalizado.
- `build_question_context()` — seleção por relevância às perguntas.

**Aceite:** `test_pdf_text.py` (21 casos). O teste decisivo é
`test_build_question_context_traz_o_miolo_relevante`: num documento de 40
páginas com o método na p. 20 e os resultados na p. 30, o contexto de 9.000
caracteres precisa conter "137 municípios" e "18,4%" — exatamente o que o
recorte antigo (começo + fim) descartava.

**Risco tratado:** a remoção de cabeçalho/rodapé pode, em tese, comer
conteúdo. Mitigado por dois limites (só páginas com ≥ 4 linhas, só linhas de
borda) e coberto por
`test_strip_running_heads_nao_toca_no_miolo_do_texto`.

---

## 20.6 Fase 4 — Procedência e lote ✅

**Entrega:** `pdf_acquisition.py`, colunas novas em `PaperModel`, endpoints.

- 10 campos de procedência com migração automática de esquema.
- `PDFBatchManager` com concorrência limitada (padrão 3), progresso
  observável e cancelamento.
- `build_paper_ref()` reconstrói landing pages a partir do identificador da
  base (PubMed → PMID → abre a via PMC).
- Endpoints `acquire`, `status`, `candidates`, `batch` (POST/GET/DELETE).

**Aceite:** `tests/test_api/test_pdf_endpoints.py` (11 casos).

**Nota de projeto:** concorrência limitada é requisito, não detalhe — as APIs
de acesso aberto aplicam limite por origem e repositórios institucionais
pequenos derrubam a conexão sob rajada.

---

## 20.7 Fase 5 — Contexto e evidência da IA ✅

**Entrega:** `extraction_service.py` reescrito.

- Contexto por relevância com marcação `[[p. N]]`, orçamento configurável.
- Prompt exige evidência literal e página; regras de ancoragem explícitas.
- `evidence`, `page_ref` e `source_kind` persistidos por resposta.
- Fallback para resumo passa a ser **declarado**, nunca silencioso.

**Aceite:** respostas assistidas trazem trecho e página quando o PDF tem
texto; com PDF digitalizado, `source_kind = "resumo"` e a interface avisa.

---

## 20.8 Fase 6 — Interface ✅

**Entrega:** `ExtractionPage.tsx` (+CSS), `ScreeningPage.tsx` (+CSS),
`api/client.ts`, `types/api.ts`, `electron/main.ts`.

- Três modos de leitura, com o PDF renderizado dentro do app.
- Busca sempre disponível; selo de procedência; painel de diagnóstico com
  trilha, candidatos e quatro saídas manuais.
- Lote com barra de progresso e botão de parar.
- Evidência sob cada resposta, com chip que abre o PDF na página citada.
- `plugins: true` no Electron para o visualizador nativo do Chromium.

**Aceite:** `tsc --noEmit` limpo nos arquivos tocados.

---

## 20.9 Fase 7 — Validação em acervo real ⬜

**Por que existe:** todos os testes atuais usam transporte simulado. A taxa de
sucesso real depende do comportamento de repositórios brasileiros concretos,
que ninguém consegue prever de dentro de um teste.

**Trabalho:**

1. Selecionar 60 trabalhos incluídos de um projeto real, estratificados por
   fonte (BDTD, SciELO, OpenAlex, PubMed, Scopus).
2. Rodar o lote e apurar: taxa de sucesso global e por fonte, via vencedora,
   tempo médio, motivo predominante de falha.
3. Comparar com a V1 nos mesmos registros (a V1 é o oráculo — doc 15).
4. Ajustar pesos da raspagem e acrescentar padrões de domínio conforme o
   observado.

**Meta:** ≥ 70% nos registros de acesso aberto de BDTD e SciELO; ≥ 90% quando
há DOI com depósito aberto registrado no Unpaywall.

**Bloqueio:** exige rede e um projeto com dados reais — não roda no ambiente
de desenvolvimento isolado.

---

## 20.10 Fase 8 — OCR opcional ⬜

Só se a Fase 7 mostrar volume relevante de PDFs digitalizados (teses antigas
da BDTD são candidatas). Desenho preferido: detectar `ocrmypdf` no sistema e
oferecer o passo como ação explícita do usuário, sem empacotar o binário
(~300 MB) no instalador.

---

## 20.11 Fase 9 — Relato metodológico ⬜

Levar a procedência para a exportação: acrescentar ao relatório PRISMA e à
planilha as colunas de origem do texto completo, para que o método da revisão
possa declarar como os arquivos foram recuperados. Depende de nada além da
Fase 4, já pronta.

---

## 20.12 Dívidas e riscos conhecidos

| # | Item | Severidade | Observação |
|---|------|-----------|------------|
| 1 | `frontend/src/data/protocolCatalog` não existe no repositório | 🔴 | **Pré-existente**, não relacionado a esta entrega: `ProjectsPage.tsx` e `ProtocolPage.tsx` o importam e o `npm run build` falha por isso. Precisa ser commitado ou removido dos imports. |
| 2 | Sem teste de interface automatizado | 🟡 | Vitest está configurado, mas não há suíte. A trilha de diagnóstico e o alternador de modos merecem cobertura. |
| 3 | APIs externas sem cache local | 🟡 | Rebuscar o mesmo DOI repete as consultas. Um cache por DOI (TTL de dias) reduziria carga nas APIs públicas. |
| 4 | `download_url` continua com nome enganoso | 🟢 | Cosmético: o resolvedor já o trata como pista. Renomear exige migração e toque em 5 coletores. |
| 5 | Sem verificação de que o PDF é o trabalho certo | 🟡 | Um repositório pode servir arquivo trocado. Comparar título extraído × título do registro daria um alerta barato. |

**Próximo documento:** [21 — Testes e Validação](./21_TESTES_VALIDACAO_PDF.md).
