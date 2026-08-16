# 21 — Testes e Validação do Subsistema de PDF

> **Princípio:** o subsistema de PDF conversa com a internet aberta, que é
> instável e não reproduzível. Toda a suíte automatizada usa **transporte
> simulado** (`httpx.MockTransport`) e **PDFs gerados em memória** — nenhum
> teste depende de rede. A validação contra o mundo real é uma etapa separada
> e manual (§21.5).

---

## 21.1 Estado atual

```
102 testes, 100% verdes  (29 pré-existentes + 73 desta entrega)
```

| Arquivo | Casos | Cobre |
|---------|-------|-------|
| `tests/test_services/test_pdf_resolver.py` | 32 | Vias de busca, heurísticas, validação, trilha |
| `tests/test_services/test_pdf_text.py` | 21 | Limpeza, seções, seleção de contexto |
| `tests/test_services/test_pdf_service.py` | 10 | Armazenamento, cache, procedência |
| `tests/test_api/test_pdf_endpoints.py` | 11 | Contrato HTTP, lote, exibição |

Execução:

```bash
cd backend && python -m pytest -q                     # suíte completa
python -m pytest tests/test_services/test_pdf_*.py -q # só o subsistema de PDF
```

---

## 21.2 Como os testes evitam a rede

**Requisições HTTP.** `httpx.MockTransport` recebe um `handler` que decide a
resposta por URL. Isso permite encenar cenários que seriam impossíveis de
reproduzir de forma estável:

```python
def handler(request):
    if str(request.url) == landing:              # landing page devolve HTML
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})
    if str(request.url) == pdf_url:              # e o PDF está num link dela
        return httpx.Response(200, content=MIN_PDF,
                              headers={"content-type": "application/pdf"})
    return httpx.Response(404)
```

**Arquivos PDF.** Gerados com PyMuPDF dentro do teste (`_make_pdf(paginas)`),
com texto realista em português. Isso exercita extração, limpeza, segmentação
e detecção de digitalização de verdade — não com um esqueleto de PDF que
nenhum motor consegue ler.

---

## 21.3 Casos que traduzem o diagnóstico

Os testes abaixo existem porque um problema real do doc 18 precisava ficar
travado contra regressão.

| Teste | Trava o problema |
|-------|------------------|
| `test_acquire_via_landing_page_quando_url_e_html` | D1.1/D1.2 — o link coletado é landing page |
| `test_acquire_segue_pagina_intermediaria_html` | "o PDF está num link próximo" |
| `test_acquire_rejeita_html_e_registra_trilha` | Nunca salvar HTML como se fosse PDF |
| `test_acquire_descarta_pdf_minusculo` | Página de erro servida como `application/pdf` |
| `test_acquire_registra_bloqueio_por_assinatura` | D1.5 — 403 vira orientação, não silêncio |
| `test_unpaywall_e_pulado_sem_email_de_contato` | Via inaplicável é pulada, não falha |
| `test_extract_dspace_bitstream_pontua_handle` | D1.3 — heurística da V1 recuperada |
| `test_build_question_context_traz_o_miolo_relevante` | D4.1 — método/resultados no meio do texto |
| `test_strip_running_heads_nao_toca_no_miolo_do_texto` | Limpeza não pode comer conteúdo |
| `test_cache_e_invalidado_ao_substituir_arquivo` | D2.4 — cache não pode servir texto velho |
| `test_acquire_falha_devolve_trilha_sem_erro_http` | Contrato: falha de busca é 200 com trilha |
| `test_pdf_servido_inline_para_visualizador_embutido` | D3.2 — `inline` habilita a leitura embutida |
| `test_upload_rejeita_arquivo_invalido` | D2.6 — HTML renomeado para `.pdf` |

---

## 21.4 O que a suíte **não** cobre

Registrado honestamente, para que ninguém confunda verde com garantia:

| Lacuna | Por quê | Mitigação |
|--------|---------|-----------|
| Comportamento real de repositórios | Não é reproduzível offline | Fase 7 do doc 20 (validação manual) |
| Bloqueio antirrobô (Cloudflare, captcha) | Depende de rede e reputação de IP | Trilha registra 403; orientação manual |
| Qualidade das respostas da IA | Exige provedor real e julgamento humano | Conferência por revisor (§21.6) |
| Interface (React) | Vitest configurado, sem suíte | Dívida 2 do doc 20 |
| PDFs de layout exótico (3 colunas, tabelas grandes) | Sem corpus | Fase 7 |

---

## 21.5 Roteiro de validação manual (Fase 7)

**Preparo.** Configurar `RSAC_CONTACT_EMAIL` com o e-mail institucional e
selecionar um projeto real com ≥ 40 estudos incluídos.

**Execução.**

1. Extração → **Buscar PDFs de todos** → aguardar o lote.
2. Anotar da barra de progresso: obtidos × sem arquivo.
3. Para cada falha, abrir **Diagnóstico** e classificar o motivo predominante.

**Planilha de apuração** (uma linha por trabalho):

| Coluna | Origem |
|--------|--------|
| Fonte | base de coleta |
| Tem DOI | sim/não |
| Resultado | obtido / falhou |
| Via vencedora | `pdf_strategy` |
| Motivo da falha | status predominante na trilha |
| Digitalizado | `pdf_is_scanned` |

**Metas** (doc 20, §20.9): ≥ 70% em BDTD/SciELO de acesso aberto; ≥ 90% com
DOI de depósito aberto.

**Verificações pontuais.**

- Abrir 5 PDFs obtidos na aba "PDF" e conferir que o documento renderiza.
- Em um artigo de duas colunas, abrir "Texto" e conferir se a leitura corre na
  ordem certa (sem linhas intercaladas entre colunas).
- Em uma tese digitalizada, conferir o aviso de documento sem texto.

---

## 21.6 Validação da extração assistida

Não existe teste automatizado para qualidade de resposta de IA. O
procedimento é o mesmo da metodologia de revisão sistemática: **conferência
por revisor**.

1. Escolher 5 estudos incluídos com PDF de texto legível.
2. Rodar **Extrair com Assistência**.
3. Para cada resposta, clicar no chip de página e conferir se o trecho de
   evidência **existe literalmente** naquela página.
4. Registrar: respostas corretas / respostas com evidência inexistente
   (alucinação) / respostas "Não informado no texto" indevidas.

**Critério de aceite:** nenhuma evidência inexistente. Uma única evidência
fabricada invalida o uso assistido para fins metodológicos e exige revisão do
prompt em `extraction_service._build_prompt`.

---

## 21.7 Convenções para novos testes

- **Nunca** chamar a rede. Se um teste precisar de HTTP, use `MockTransport`.
- PDFs de teste devem ter corpo realista: um arquivo abaixo de 2 KB é
  rejeitado pela validação (corretamente), e uma página com menos de ~120
  caracteres é classificada como digitalizada.
- Nomes de teste em português, descrevendo o comportamento esperado — a suíte
  também é documentação do subsistema.
- Ao corrigir um defeito encontrado na Fase 7, **primeiro** escreva o teste
  que o reproduz com transporte simulado.
