# 18 — Diagnóstico: Obtenção de PDF, Leitura e Extração de Dados

> **Escopo:** tudo que acontece entre "o estudo foi incluído na Triagem 1" e "as
> perguntas de extração estão respondidas com evidência" — download do texto
> completo, armazenamento, extração de texto, exibição na interface e leitura
> pelo assistente de IA.
>
> **Método:** leitura do código em `b2baf3b` (backend `services/pdf_service.py`,
> `services/extraction_service.py`, `api/v1/extraction.py`; frontend
> `ExtractionPage.tsx`, `ScreeningPage.tsx`, `api/client.ts`), comparação com o
> comportamento da V1 (`config_app/main.py`, função `resolve_pdf_url`) e com as
> práticas correntes de recuperação de texto completo em revisão sistemática.

---

## 18.1 Resumo executivo

A funcionalidade existe ponta a ponta, mas **a etapa de aquisição do arquivo
falha na maioria dos casos reais** e todas as etapas seguintes herdam essa
falha. O diagnóstico identificou **14 problemas**, agrupados em quatro blocos:

| # | Bloco | Severidade | Efeito percebido pelo usuário |
|---|-------|-----------|-------------------------------|
| D1 | Aquisição do PDF | 🔴 Bloqueante | "Baixar" quase nunca funciona |
| D2 | Extração de texto | 🟠 Alta | Texto sujo, ilegível ou vazio |
| D3 | Exibição na interface | 🟠 Alta | Não dá para ler o documento no app |
| D4 | Leitura pelo assistente | 🔴 Bloqueante | Respostas rasas, sem evidência |

A causa-raiz do bloco D1 é uma **premissa errada no modelo de dados**: o campo
`download_url` é tratado como se fosse o endereço do arquivo PDF, quando na
prática é o endereço da *página do registro*.

---

## 18.2 D1 — Aquisição do PDF

### D1.1 🔴 `download_url` não é link de PDF (causa-raiz)

O que cada coletor grava em `download_url`:

| Fonte | Valor gravado | É PDF? |
|-------|---------------|--------|
| OpenAlex | `primary_location.landing_page_url` ou o DOI | ❌ página do editor |
| PubMed | `https://pubmed.ncbi.nlm.nih.gov/{pmid}/` | ❌ registro bibliográfico |
| SciELO | URL do artigo (`sci_arttext`) | ❌ artigo em HTML |
| BDTD | URL do registro no repositório | ❌ landing page do DSpace |
| Scopus | link `@ref == "scopus"` | ❌ página paga |

Nenhuma das cinco fontes entrega link direto de arquivo. A rigor, o campo
deveria se chamar `source_url`.

### D1.2 🔴 O download é uma única tentativa ingênua

`PDFService.download_pdf` (versão diagnosticada) fazia um `GET` na URL e
aceitava o resultado apenas se o `content-type` fosse `application/pdf` ou os
primeiros bytes fossem `%PDF`. Como a URL é uma landing page, o servidor
devolve HTML e a função retorna `None`. **Taxa de sucesso esperada: próxima de
zero** fora dos poucos registros cujo `download_url` termina em `.pdf`.

Não havia: consulta a DOI, consulta a bases de acesso aberto, transformação de
padrão de URL, raspagem da página, nem tentativa alternativa alguma.

### D1.3 🟠 Regressão frente à V1

A V1 tinha `resolve_pdf_url()` com heurísticas reais: `sci_arttext → sci_pdf`,
raspagem de DSpace com pontuação por `handle`, `bitstream`, `sequence=1`,
`isAllowed=y`, e caso especial para Teses USP. **A V2 nasceu sem esse
conhecimento** — o doc 15 estabelece "V1 é o oráculo", e aqui a regra foi
violada.

### D1.4 🟠 Nenhuma via de acesso aberto é consultada

Existem APIs públicas, gratuitas e estáveis que resolvem DOI → PDF aberto:
Unpaywall, OpenAlex (`best_oa_location.pdf_url`), Crossref (`link[]`),
Semantic Scholar (`openAccessPdf`), Europe PMC. Nenhuma era usada, embora o
projeto já consulte OpenAlex na coleta.

### D1.5 🟠 Falha opaca e não acionável

O endpoint devolvia `404 "Não foi possível obter o PDF na URL cadastrada."`. O
usuário não sabe: o que foi tentado, se o conteúdo é pago, se houve bloqueio
antirrobô, ou qual seria o próximo passo manual. Sem trilha, cada falha vira
tentativa e erro no navegador.

### D1.6 🟠 Sem operação em lote

Cada trabalho exige clique individual. Uma revisão com 60 estudos incluídos
significa 60 ciclos manuais de "clicar, esperar, falhar, procurar no
navegador".

### D1.7 🟡 Sem verificação de integridade nem procedência

Nada era gravado sobre o arquivo: de onde veio, por qual via, quantas páginas
tem, qual o hash. Em revisão sistemática, **procedência é requisito
metodológico** — o protocolo precisa poder declarar como o texto completo foi
obtido.

### D1.8 🟡 Botão condicionado ao campo errado

Na interface, o botão "Baixar" só aparecia se `download_url` existisse. Um
registro com DOI e sem `download_url` — situação comum — não oferecia nenhum
caminho automático, embora o DOI seja justamente a melhor pista.

---

## 18.3 D2 — Extração de texto

### D2.1 🟠 Extração linear ignora o layout

`page.get_text()` devolve o texto na ordem interna do arquivo. Em artigo de
**duas colunas** — padrão em periódicos de ciências sociais aplicadas — isso
intercala linhas das duas colunas, produzindo texto sintaticamente
embaralhado. O assistente recebe frases misturadas e responde mal.

### D2.2 🟠 Nenhuma limpeza tipográfica

Sem de-hifenização (`desenvolvi-\nmento` fica como duas palavras), sem
normalização de ligaduras (`eﬁciência`), sem remoção de cabeçalho/rodapé
repetido e de numeração de página. O ruído consome contexto da IA e prejudica
a busca textual do usuário.

### D2.3 🟠 Paginação descartada

O texto era concatenado sem qualquer marca de página. Isso torna impossível
pedir à IA que **cite a página** da evidência — que é o mínimo esperado numa
matriz de extração auditável.

### D2.4 🟠 Reextração a cada chamada

`GET /pdf/text` reextraía o documento inteiro toda vez. Alternar entre abas em
um PDF de 40 páginas repetia o trabalho, com latência visível.

### D2.5 🟡 PDF digitalizado não é detectado

Um PDF só de imagens extrai string vazia. O sistema tratava isso como "texto
vazio" e seguia adiante em silêncio, sem informar que o documento precisa de
OCR.

### D2.6 🟡 Upload sem validação

`save_uploaded_pdf` gravava qualquer conteúdo com a extensão `.pdf`, incluindo
uma página de login HTML salva pelo navegador. O erro só apareceria depois, na
leitura.

---

## 18.4 D3 — Exibição na interface

### D3.1 🟠 Não havia visualização do documento

A interface oferecia apenas "Resumo" e "Texto do PDF". Para ver o **documento
original** — tabelas, figuras, diagramação — era preciso abrir em aplicativo
externo, saindo do fluxo de trabalho. Para revisão sistemática, ler tabela e
figura é parte da extração de dados.

### D3.2 🟡 Arquivo servido como anexo

`FileResponse(..., filename=...)` produz `Content-Disposition: attachment`, o
que impede renderização embutida: qualquer visualizador embutido só ofereceria
"salvar arquivo".

### D3.3 🟡 Estado da interface dessincronizado do banco

`ExtractionPage` mantinha `hasPdf`/`pdfPath` em estados soltos, atualizados de
forma otimista após cada ação. Se o arquivo sumisse do disco (projeto movido,
pasta limpa), a interface continuaria mostrando "PDF Vinculado".

### D3.4 🟡 Triagem 1 com caminho morto

`ScreeningPage` declarava `readingViewMode`, `pdfExtractedText` e
`handleToggleReadingView`, mas **nenhum desses estados era usado no JSX** — a
caixa de leitura mostrava só o resumo. Código morto que aparentava uma
funcionalidade inexistente.

---

## 18.5 D4 — Leitura pelo assistente

### D4.1 🔴 Recorte de contexto joga fora o miolo do estudo

`extract_key_sections` cortava o texto em "primeiros 7.500 + últimos 7.500
caracteres". Em um artigo de 40 mil caracteres, **o que se perde é exatamente
a seção de método e a de resultados** — origem da resposta da maioria das
perguntas de extração. O fim do texto, aliás, costuma ser a lista de
referências, que não responde nada.

### D4.2 🟠 Orçamento de contexto irrealista

O limite de 15 mil caracteres (~4 mil tokens) foi dimensionado para janelas
antigas. Os modelos configuráveis no app (Gemini, Qwen, locais) trabalham hoje
com 32k tokens ou mais.

### D4.3 🟠 Resposta sem evidência

O prompt pedia só `question_id` e `answer`. Não havia trecho comprobatório nem
página. Numa revisão sistemática isso inviabiliza a conferência por segundo
revisor — a resposta da IA é indistinguível de alucinação bem escrita.

### D4.4 🟡 Fallback silencioso para o resumo

Quando não havia PDF (ou a leitura falhava), o serviço usava o resumo sem
avisar ninguém. O usuário recebe respostas rasas sem saber que elas não vieram
do texto completo.

---

## 18.6 Cadeia causal

```
download_url é landing page  (D1.1)
        │
        ▼
download de tentativa única falha  (D1.2, D1.3, D1.4)
        │
        ▼
sem PDF vinculado  ──►  falha opaca, sem lote  (D1.5, D1.6)
        │
        ▼
extração cai no resumo em silêncio  (D4.4)
        │
        ▼
IA responde a partir de 1 parágrafo, sem evidência  (D4.1, D4.3)
        │
        ▼
matriz de extração pobre e não auditável
```

Atacar apenas D4 (melhorar o prompt) não resolve nada enquanto D1 não for
resolvido: **não há texto para ler**.

---

## 18.7 O que já estava certo

Registrar para não regredir na refatoração:

- Separação em camadas (`api` → `services` → `infrastructure`) permitiu trocar
  o miolo da aquisição sem tocar na fronteira HTTP.
- Um diretório de PDFs por projeto (`pdfs/{project_id}/{paper_id}.pdf`) é
  simples, previsível e evita colisão entre projetos.
- Fallback PyMuPDF → pypdf já existia e é a escolha certa de motores.
- A ergonomia da tela de extração (fila horizontal, duas colunas com rolagem
  independente, navegação por teclado, zoom tipográfico) é boa e foi mantida.
- `_migrate_missing_columns` permite evoluir o esquema sem migração manual,
  o que viabilizou acrescentar os campos de procedência sem quebrar bancos
  existentes.

---

## 18.8 Referências dos arquivos diagnosticados

| Arquivo | Papel | Problemas |
|---------|-------|-----------|
| `backend/app/services/pdf_service.py` | Download e extração | D1.2, D1.7, D2.1–D2.6 |
| `backend/app/services/extraction_service.py` | Extração com IA | D4.1–D4.4 |
| `backend/app/api/v1/extraction.py` | Endpoints | D1.5, D1.6, D3.2 |
| `backend/app/harvesters/*.py` | Origem de `download_url` | D1.1 |
| `backend/app/infrastructure/persistence/models.py` | Modelo `PaperModel` | D1.7 |
| `frontend/src/pages/ExtractionPage.tsx` | Interface de extração | D1.8, D3.1, D3.3 |
| `frontend/src/pages/ScreeningPage.tsx` | Interface de triagem | D3.4 |

**Próximo documento:** [19 — Especificação da Aquisição e Leitura de
PDF](./19_ESPECIFICACAO_AQUISICAO_PDF.md).
