# 49 — Plano de Execução — Ambiente de Indicadores

> **Revsist — Bibliometria auditável**
> **Status:** 🟢 Documento normativo vigente
> **Data:** 31/08/2026
> **Sucede:** [47 — Diagnóstico](./47_DIAGNOSTICO_BIBLIOMETRIA.md) · [48 — Especificação](./48_ESPECIFICACAO_AMBIENTE_INDICADORES.md)

---

## 1. Como ler este plano

Dez fases. Cada uma entrega algo que **funciona sozinho** e pode ser
interrompida sem deixar o produto pela metade — a mesma disciplina dos docs 33,
41 e 44.

A ordem não é a de valor percebido. É a de dependência, com uma exceção
deliberada: a **Fase 0 vem primeiro por ser correção de erro visível**, não por
ser pré-requisito de nada.

**Legenda:** ⬜ Aberto · 🟩 Em execução · ✅ Entregue e verificado

---

## 2. Sequência

```
  F0  Parar de mentir sobre instituição        ✅   independente
       │
  F1  Instantâneo                              ✅   espinha de tudo
       │
       ├──► F2  Enriquecimento OpenAlex        ✅   fecha B-01, B-02, B-03
       │         │
       │         └──► F3  Indicadores 0 e 1    ✅
       │                   │
       ├──► F4  Texto e tesauro                ✅   fecha B-04, B-06
       │         │
       │         └──► F5  Instrumento de medida ✅  fecha B-07  ◄── o núcleo
       │                   │
       │         ┌─────────┴──────────┐
       └──► F6  Grafos ✅        F7  Estatística sob demanda ✅
                 │                    │
                 └────────┬───────────┘
                          ▼
                    F8  Vanguarda ✅
                          │
                    F9  Pré-registro e exportação ✅
```

---

## Fase 0 — Parar de mentir sobre instituição ✅

> **Entregue em 31/08/2026.** `app/domain/afiliacao.py` reconhece os literais
> dos cinco coletores (com variação de caixa e acento); o ranking e a planilha
> de exportação passam a ignorá-los. Medido nos projetos reais logo depois:
> "Protocolos" 0/39 e "Rovers" 0/22 caem no estado vazio explicativo — antes
> exibiam *OpenAlex 25* e *SciELO 14* como instituições —, e "Mobilidade"
> revela **14 de 15 afiliações reais** (USP, UFRGS, UNIVALI, UFRRJ, UNIOESTE)
> que estavam soterradas. Ver o refinamento em doc 48 §4.3.

**Por que primeiro.** É o único achado do doc 47 que produz um número errado
na tela hoje. Um painel que erra o que o usuário sabe conferir perde autoridade
para afirmar o que ele não sabe conferir.

**Entregas**

1. `insights_service.py:383` deixa de derivar `top_institutions` de
   `PaperModel.institution`.
2. Enquanto não houver `bib_authorships` (Fase 2), o bloco exibe o estado vazio
   do doc 32 §5.4, com a explicação e o caminho: *"A afiliação não é coletada
   pelas bases usadas; o enriquecimento externo a obtém."*
3. Aviso equivalente no `ExportService` para quem já exportou o painel.

**Critério de aceite**
- Nenhum nome de coletor (`SciELO`, `OpenAlex`, `PubMed/NCBI`,
  `Scopus/Elsevier`, `BDTD/IBICT`) aparece como instituição em qualquer saída.
- O estado vazio explica a causa e oferece a ação.

**Testes**
- `test_insights_nao_reporta_coletor_como_instituicao` — monta projeto com os
  cinco literais e verifica que nenhum sai no ranking.
- Teste de regressão do estado vazio.

**Custo estimado:** meio dia. É subtração, não construção.

---

## Fase 1 — Instantâneo ✅

> **Entregue em 31/08/2026.** `bib_snapshots` (migração `ab94a1e80f17`),
> `app/services/bibliometria/instantaneo.py`, três rotas sob
> `/projects/{id}/bibliometria`, e a barra de instantâneo na aba de
> Indicadores com o semáforo de conferência. `GET /insights` aceita
> `?instantaneo=` e devolve `provenance`.
>
> **Divergência corrigida durante a implementação:** o schema da API abria o
> escopo em `decision = null` e o serviço em `Incluído` — dois padrões para a
> mesma coisa. O mesmo pedido produzia corpora diferentes conforme o caminho:
> um instantâneo de 16.578 documentos onde se esperava a amostra incluída de
> 15. Os dois passaram a apontar para `DECISAO_PADRAO`. A barra, por sua vez,
> congela **o corpus visível na tela**, e não um escopo próprio.

**Objetivo.** Dar aos indicadores um corpus que fica parado (doc 48 §3).

**Entregas**

1. Migração Alembic: `bib_snapshots`.
2. `app/services/bibliometria/instantaneo.py` — criação a partir de escopo,
   manifesto, `corpus_hash`, verificação.
3. Rotas `POST/GET /instantaneos` e `GET /instantaneos/{id}/conferir`.
4. Barra de instantâneo no topo da aba (doc 48 §14.2), com semáforo de
   conferência.
5. Os indicadores existentes (docs 31–33) passam a aceitar `instantaneo` como
   parâmetro opcional — **sem quebrar** quem chama sem ele.

**Critério de aceite**
- Criar instantâneo, alterar um `abstract`, verificar → âmbar, com o documento
  alterado nomeado.
- Excluir um documento do escopo → vermelho, com oferta de novo instantâneo.
- Nada é recomputado em silêncio.

**Testes**
- `test_hash_estavel_entre_execucoes` — mesmo corpus, dois processos, mesmo
  hash.
- `test_hash_muda_com_conteudo` / `test_hash_muda_com_conjunto`.
- `test_ordem_de_insercao_nao_afeta_o_hash` — o manifesto é ordenado.
- `test_separador_impede_colisao` — dois documentos com campos concatenáveis de
  formas diferentes não colidem (doc 48 §3.2).

---

## Fase 2 — Enriquecimento OpenAlex ✅

> **Entregue em 01/09/2026.** Migração Alembic `bc95a1e80f18` criando as 6
> tabelas relacionais (`bib_enrichments`, `bib_work_meta`, `bib_references`,
> `bib_authorships`, `bib_topics`, `bib_keywords`);
> `app/services/bibliometria/enriquecimento.py` com consulta em lotes de 50
> DOIs e fallback Crossref; `top_institutions` lendo primariamente
> `bib_authorships` (instituições com ROR real); integração no coletor OpenAlex
> e `dedup_service.py`; rotas HTTP sob `/projects/{id}/bibliometria/enriquecimento`
> e componente `PainelEnriquecimento.tsx` na aba de Indicadores. Validado com
> suíte automatizada de 72 testes cobrindo todo o subsistema de bibliometria.

**Objetivo.** Buscar o que já está disponível e é descartado hoje. Fecha B-01,
B-02 e B-03 de uma vez.

**Entregas**

1. Migração: `bib_enrichments`, `bib_work_meta`, `bib_references`,
   `bib_authorships`, `bib_topics`, `bib_keywords`.
2. `app/services/bibliometria/enriquecimento.py` — consulta em lotes de 50
   DOIs, incremental, retomável, com `AceleradorAdaptativo` e o canal ao vivo.
3. Reserva por Crossref para DOIs ausentes; procedência por campo.
4. Coletor OpenAlex passa a **aproveitar a resposta que já recebe**
   (`app/harvesters/openalex.py:221`) — o que vier na coleta não precisa ser
   pedido de novo.
5. `top_institutions` volta a existir, agora sobre `bib_authorships`.

**Critério de aceite**
- Enriquecer os três projetos reais e reportar cobertura observada; a amostra
  do doc 47 §5 prevê ≥90% de acerto por DOI.
- Interromper no meio e retomar não reconsulta o que já veio.
- Toda linha de `bib_work_meta` tem `raw` preenchido.
- Nenhuma chave de API é exigida.

**Testes**
- Cliente HTTP simulado, sem rede, com respostas gravadas do OpenAlex.
- `test_enriquecimento_e_retomavel`, `test_dois_provedores_registram_procedencia`,
  `test_doi_desconhecido_nao_derruba_o_lote`.
- Um teste marcado `@pytest.mark.rede`, fora da suíte padrão, contra a API real.

**Risco.** Volume: ~1,3 M linhas em `bib_references` no acervo real. Mitigação
na §5.

---

## Fase 3 — Indicadores de nível 0 e 1 ✅

> **Entregue em 01/09/2026.** `app/services/bibliometria/indicadores.py` com
> produção temporal e CAGR, Bradford com 3 zonas e multiplicador $k$, Lotka via
> MLE com teste formal Kolmogorov-Smirnov (Clauset et al., 2009), índice de
> colaboração de Subramanyam (1983), Gini e HHI, citações, índice $h$ (Hirsch,
> 2005) e Acesso Aberto; rota HTTP `GET /projects/{id}/bibliometria/indicadores`;
> exportação Excel com abas `Bibliometria` e `Proveniência`; componente visual
> `SecaoBibliometria.tsx` com Recharts e carimbo de integridade numérica. Validado
> com 87 testes automatizados cobrindo todo o ambiente.

**Objetivo.** O catálogo do doc 48 §7.1 e §7.2 sobre o instantâneo.

**Entregas**

1. `app/services/bibliometria/indicadores.py` — produção temporal, Bradford,
   Lotka **com teste de aderência** (Clauset et al.), colaboração, Gini/HHI,
   sobreposição entre bases, citações, índice h, instituições, países, acesso
   aberto.
2. Seção **Bibliometria** na aba de Indicadores, com `recharts`.
3. Rodapé de proveniência (doc 48 §14.4) em toda figura.
4. Exportação `xlsx`/`csv` com a aba de proveniência junto.

**Critério de aceite**
- Todo indicador traz denominador e parâmetros.
- Lotka/Bradford nunca aparecem sem estatística de aderência.
- Indicador sem substrato mostra estado vazio explicativo, não zero.

**Testes**
- Corpus sintético com lei de potência conhecida → expoente recuperado dentro
  da tolerância.
- Corpus deliberadamente **não** power-law → o teste de aderência rejeita, e a
  interface diz que rejeita.
- `test_sobreposicao_entre_bases_bate_com_paper_sources`.

---

## Fase 4 — Camada de texto e tesauro ✅

> **Entregue em 01/09/2026.** Migração `cd96a1e80f19` criando `bib_textos`,
> `bib_thesauri` e `bib_thesaurus_entries`; serviços
> `app/services/bibliometria/texto.py` (extração com reuso, sha256 do PDF, versão do
> pipeline `2.0.0`, contagem de palavras e seções IMRaD) e
> `app/services/bibliometria/tesauro.py` (sugestões léxicas automáticas em
> rascunho com porta obrigatória de aprovação humana e substituição
> determinística); rotas HTTP completas sob `/projects/{id}/bibliometria/textos` e
> `/tesauros`; tipos TypeScript e métodos de API no frontend. Validado com 95
> testes automatizados (8 novos testes cobrindo persistência, IMRaD e não-fusão
> sem aprovação).

**Objetivo.** Fecha B-04 e B-06. Pré-requisito do núcleo.

**Entregas**

1. Migração: `bib_textos`, `bib_tesauros`, `bib_tesauro_entradas`.
2. Persistência do que `pdf_text.py` já produz — texto, seções IMRaD, contagem
   de páginas e palavras, `sha256` do PDF, versão do pipeline.
3. Reprocessamento explícito quando a versão do pipeline mudar — **nunca
   automático**.
4. Tesauro: proposta de fusões pela IA, aprovação em bloco, versionamento.

**Critério de aceite**
- Texto extraído uma vez é reusado; a versão fica registrada.
- Trocar a versão do pipeline não altera número já publicado sem aviso
  explícito.
- Nenhuma fusão de termos ocorre sem aprovação humana.

**Testes**
- `test_texto_e_reusado_e_nao_reextraido`.
- `test_versao_do_pipeline_entra_no_instantaneo`.
- `test_tesauro_nao_funde_sem_aprovacao`.
- `test_secoes_imrad_sobrevivem_a_persistencia`.

---

## Fase 5 — Instrumento de medida ✅ ◄ o núcleo

> **Entregue em 01/09/2026.** Migração `de97a1e80f20` criando `bib_instrumentos`,
> `bib_medidas` e `bib_ocorrencias`; serviço
> `app/services/bibliometria/instrumentos.py` com sugestão léxica em rascunho
> (`sugerir_lexico_conceitual`), porta obrigatória de aprovação humana
> (rascunho não mede e não produz número oficial), motor determinístico de
> contagem (bruta, relativa por mil, documental e por seção IMRaD), denominador
> explícito, evidência clicável ancorada em página e offset, e conferência
> amostral com Intervalo de Confiança Wilson (IC 95%); rotas HTTP sob
> `/projects/{id}/bibliometria/instrumentos` e `/medidas`; tipos TypeScript e
> métodos no cliente frontend. Validado com 103 testes automatizados (8 novos
> testes cobrindo determinismo, exclusão com motivo e recusa de medição em
> rascunho).

**Objetivo.** Doc 48 §6. É a resposta ao pedido original de contagem de termos
por IA, feita de um jeito defensável.

**Entregas**

1. Migração: `bib_instrumentos`, `bib_medidas`, `bib_ocorrencias`.
2. `POST /instrumentos/sugerir-lexico` — a IA propõe `incluir`/`excluir` com
   motivo; devolve **rascunho**, e a rota não mede.
3. Contador determinístico: bruta, relativa, documental, por seção, e
   coocorrência em janela.
4. Aprovação humana como porta obrigatória; versionamento do instrumento.
5. Evidência clicável: número → documentos → passagens destacadas com página.
6. Conferência amostral com precisão e IC (doc 48 §6.7).
7. Recusa explicada quando o escopo exceder o teto de texto completo.

**Critério de aceite**
- **Instrumento em rascunho não produz número exportável.** Prévia é marcada
  como prévia.
- Toda contagem exibe o denominador e quantos documentos ficaram sem texto.
- Toda ocorrência é localizável até a página.
- Duas execuções do mesmo instrumento sobre o mesmo instantâneo dão resultado
  **idêntico**.

**Testes**
- `test_rascunho_nao_mede` — a porta de aprovação é do servidor, não da tela.
- `test_contagem_e_identica_entre_execucoes`.
- `test_modo_lema_casa_flexoes_e_nao_casa_homonimo`.
- `test_exclusao_remove_ocorrencia_e_registra_motivo`.
- `test_denominador_conta_documentos_sem_texto`.
- `test_ocorrencia_aponta_para_a_pagina_certa` — com PDF de fixture.
- `test_nenhum_numero_vem_do_modelo` — o cliente de IA simulado devolve números
  absurdos no léxico; o resultado não muda.

O último é o teste que guarda a tese do doc 48 §2. Vale escrevê-lo primeiro.

---

## Fase 6 — Grafos ✅

> **Entregue em 01/09/2026.** Migração `ef98a1e80f21` criando `bib_grafos`; serviço
> `app/services/bibliometria/grafos.py` com quatro redes num motor unificado
> (coautoria, termos com tesauro aprovado, acoplamento bibliográfico e
> cocitação), normalização de força (*Association Strength* VOSviewer, Jaccard,
> Cosseno), agrupamento Louvain determinístico, layout Fruchterman-Reingold com
> semente fixa gravado no servidor (fecha B-08), exportação GraphML com
> coordenadas; rotas HTTP `/grafos/gerar`, `/grafos/{id}` e
> `/grafos/{id}/exportar`; componente frontend `VisualizadorGrafoCanvas.tsx`
> com Canvas interativo, pan/zoom, tabela equivalente acessível de nós e
> legenda metodológica. Validado com 109 testes automatizados (6 novos testes
> de grafos e reprodutibilidade espacial).

**Objetivo.** Doc 48 §8. Quatro redes, um motor, layout determinístico.

**Entregas**

1. Migração: `bib_grafos`. Dependência nova: `networkx` (Python puro).
2. Motor: matriz → força de associação (Jaccard e cosseno como alternativa
   declarada) → Louvain com semente → layout FR com semente → coordenadas.
3. Renderizador em Canvas lendo os tokens do doc 24; tema claro e escuro.
4. **Tabela equivalente** de nós, navegável por teclado.
5. Exportação GraphML/GEXF com coordenadas.
6. Legenda com algoritmo, semente, normalização, resolução e corte.

**Critério de aceite**
- Mesmo instantâneo + mesmos parâmetros → **coordenadas idênticas**, em
  qualquer máquina.
- O grafo nunca é o único caminho para o dado.
- Acoplamento sobre corpus acima do teto é recusado com explicação, não travado.

**Testes**
- `test_layout_e_identico_com_a_mesma_semente`.
- `test_forca_de_associacao_bate_com_o_calculo_manual` — grafo pequeno,
  conferido à mão.
- `test_grafo_tem_tabela_equivalente`.
- `test_corpus_grande_recusa_com_explicacao`.
- Verificação visual no navegador embutido, claro e escuro.

---

## Fase 7 — Estatística sob demanda ✅

> **Entregue em 01/09/2026.** Migração `fa99a1e80f22` criando `bib_analises`;
> serviço `app/services/bibliometria/analises.py` com pipeline em 4 etapas
> (tradução heurística/IA para especificação formal com vocabulário fechado,
> imunidade a injeção SQL, compilação parametrizada em SQLAlchemy e cálculo de
> mediana, média, quantil, soma, taxa e desvio-padrão determinísticos com
> carimbo de proveniência); rotas HTTP `/analises/interpretar`,
> `/analises/executar` e `/analises/salvas`; componente frontend
> `PainelEstatisticaSobDemanda.tsx` com editor JSON visível antes da execução,
> gráficos Recharts e histórico de consultas salvas. Validado com 115 testes
> automatizados (6 novos testes cobrindo segurança contra injeção SQL, recusa de
> vocabulário e exatidão dos agregados matemáticos).

**Objetivo.** Doc 48 §9. Pergunta → especificação → número.

**Entregas**

1. Esquema Pydantic da especificação, vocabulário fechado.
2. Compilador especificação → SQLAlchemy parametrizado.
3. `POST /analises/interpretar` (IA) e `POST /analises/executar` (código).
4. Interface: pergunta, especificação **visível e editável**, resultado,
   salvar, reexecutar sobre outro instantâneo.
5. Recusa honesta quando a pergunta não couber, com o que sabe responder.

**Critério de aceite**
- **Nenhum texto vindo do modelo chega ao banco.**
- A especificação é sempre mostrada antes do número.
- Análise salva reexecuta sobre instantâneo diferente e permite comparar.

**Testes**
- `test_especificacao_invalida_e_recusada`.
- `test_injecao_na_pergunta_nao_alcanca_o_banco` — a pergunta contém
  `"; DROP TABLE papers; --"`; verifica-se que a tabela existe e a
  especificação foi rejeitada.
- `test_pergunta_fora_do_vocabulario_recebe_recusa_com_alternativas`.
- `test_mesma_especificacao_mesmo_instantaneo_mesmo_numero`.

O segundo teste pertence tanto a este documento quanto ao doc 29.

---

## Fase 8 — Indicadores de vanguarda ✅

> **Entregue em 01/09/2026.** Serviço `app/services/bibliometria/vanguarda.py`
> implementando os 5 módulos de vanguarda:
> 1. Diagrama estratégico SciMAT (Callon et al. 1991 / Cobo et al. 2011) com
>    classificação em 4 quadrantes (motores, básicos, especializados e
>    emergentes/declínio);
> 2. Detecção de rajadas temporais de Kleinberg (2003) com $s=2.0$ e $\gamma=1.0$;
> 3. Incerteza amostral por reamostragem bootstrap (1.000 iterações, `seed=42`)
>    com cálculo de IC 95% e alerta explícito de empates técnicos / posições
>    estatisticamente indistinguíveis;
> 4. Painel de sensibilidade Louvain (0.6 a 1.4) com Índice de Rand Ajustado (ARI);
> 5. Diagnóstico de cobertura do campo (tópicos robustos vs. ralos).
> Rotas HTTP sob `/vanguarda/*`, schemas Pydantic, cliente frontend e componente
> `PainelVanguardaSensibilidade.tsx` com visualização interativa em 5 abas.
> Validado com 121 testes automatizados (6 novos testes unitários e de integração).

**Objetivo.** Doc 48 §7.4 e §10 — o que distingue o ambiente.

**Entregas**

1. Diagrama estratégico (centralidade × densidade) e evolução temática por
   período.
2. Detecção de rajadas (Kleinberg), com parâmetros declarados.
3. Intervalos por bootstrap em rankings e índices, com o aviso de posições
   indistinguíveis.
4. Painel de sensibilidade a parâmetro, com Rand ajustado.
5. **Cobertura do campo** — corpus × tópicos OpenAlex, com os subtemas ralos
   apontados.

**Critério de aceite**
- Nenhum ranking sai sem intervalo.
- Todo parâmetro arbitrário tem varredura de sensibilidade acessível.
- A cobertura do campo aparece também na tela de estratégia de busca (doc 45
  §10) — não só aqui.

**Testes**
- `test_bootstrap_com_semente_e_reprodutivel`.
- `test_posicoes_indistinguiveis_sao_sinalizadas` — corpus com empate técnico
  construído.
- `test_diagrama_estrategico_classifica_quadrantes_conhecidos`.
- `test_rajada_detecta_termo_com_salto_construido`.

**Nota de sequência.** O item 5 é o de maior valor e o de menor custo. Se
faltar tempo, é o que deve sobreviver ao corte — ele liga a bibliometria à
qualidade da busca, que é o que uma revisão sistemática precisa defender.

---

## Fase 9 — Pré-registro e exportação ✅

> **Entregue e verificado em 01/09/2026.**
> - `app/services/bibliometria/preregistro.py` implementa estruturação e versionamento do plano bibliométrico pré-registrado no protocolo D11.
> - Rotulagem automática de análises exploratórias (`exploratoria: true`) para qualquer cálculo ou indicador não previsto a priori.
> - Rastreabilidade com geração de `ProtocolAmendmentModel` quando o plano é editado após congelamento do protocolo (`status == 'vigente'`).
> - Relatório de Conformidade Metodológica BIBLIO com 20 itens normativos separando estritamente o que o software audita e garante deterministicamente (16+ itens) versus o que é de responsabilidade teórica exclusiva do autor (4 itens).
> - Gerador de Pacote de Replicação integral em arquivo `.zip` (`manifesto_instantaneo.json`, `proveniencia.json`, `plano_pre_registro.json`, `relatorio_conformidade_biblio.md/.json`, `indicadores/indicadores_resumo.json`, `grafos/*.graphml`).
> - Componente `PainelPreRegistroExportacao.tsx` e integração das 4 grandes abas de bibliometria em `SecaoBibliometria.tsx`.
> - Suíte de testes dedicada (`test_preregistro_exportacao.py`, `test_preregistro_api.py`) e validação de regressão integral com **849 testes passando**.

**Entregas**

1. Seção de análise bibliométrica no protocolo D11: indicadores previstos,
   unidade de análise, janela, tesauro, cortes.
2. Análise não prevista é marcada **exploratória** em toda saída.
3. Mudança depois de ver resultado gera emenda (`protocol_amendments`).
4. Exportação completa: indicadores, grafos, medidas, evidência, proveniência,
   e o **relatório de conformidade BIBLIO** com os 20 itens, apontando o que o
   sistema preenche e o que cabe ao autor.

**Critério de aceite**
- Exportação abre em Excel e no Gephi sem retrabalho.
- Toda análise exploratória está identificada como tal.
- O relatório BIBLIO não afirma cobrir item que dependa do autor.

**Testes**
- `test_analise_nao_prevista_sai_marcada_como_exploratoria`.
- `test_exportacao_carrega_proveniencia_completa`.
- `test_relatorio_biblio_nao_reivindica_item_do_autor`.

---

## 3. Estratégia de testes

Além dos testes por fase, quatro transversais. São eles que sustentam as
garantias do doc 48 §1, e nenhuma fase é considerada entregue se um deles
regredir.

**T-1 — Reprodutibilidade byte a byte.** Todo o pipeline (instantâneo →
indicadores → grafo → medida) executado duas vezes em processos distintos
produz saída idêntica. É o teste mais importante da suíte.

**T-2 — Nenhum número vem do modelo.** Cliente de IA simulado que devolve
números absurdos em toda resposta. Nenhum indicador, contagem ou estatística
pode mudar.

**T-3 — Denominador presente.** Varredura de todas as respostas de API que
contenham contagem, verificando `proveniencia` e denominador.

**T-4 — Tokens e acessibilidade.** O linter do doc 24 continua fechado nas nove
regras; toda rede tem tabela equivalente.

---

## 4. Dependências novas

Uma só: **`networkx`** (Python puro, sem compilador, licença BSD). `leidenalg`
fica como melhoria opcional, jamais requisito de instalação — exige compilação
e quebraria a instalação em máquina de usuário final.

No frontend, **nenhuma**. Canvas com os tokens do doc 24; `recharts` segue para
o cartesiano.

Esta contenção é deliberada: o produto é instalável em máquina de pesquisador,
e cada dependência que exige compilador é uma instalação que falha na casa de
alguém.

---

## 5. Riscos

| # | Risco | Mitigação |
|---|---|---|
| R-1 | `bib_references` cresce a ~1,3 M linhas; acoplamento é auto-junção quadrática | Cálculo só sobre instantâneo; teto configurável (padrão 5.000 documentos) com recusa explicada; índices nos dois lados |
| R-2 | OpenAlex muda contrato ou fica fora do ar | `raw` guardado; Crossref e OpenCitations como reserva; enriquecimento é assíncrono e retomável |
| R-3 | O usuário quer contar termos em 87 mil documentos | Recusa explicada com o número real (doc 47 §3: 17 textos); a interface diz o que seria preciso |
| R-4 | Léxico aprovado às pressas produz número ruim com aparência boa | Conferência amostral com precisão e IC; a precisão viaja com o instrumento em toda saída |
| R-5 | Bibliometria vira apêndice ornamental no fim da revisão | Fase 8 item 5 e Fase 9 ligam os indicadores à estratégia de busca e ao protocolo |
| R-6 | Escopo grande demais para uma rodada | Fases independentes; F0 sozinha já corrige o erro visível, F1+F2+F3 já entregam bibliometria real |

---

## 6. O que muda para quem usa

Ao fim da Fase 3, o pesquisador tem bibliometria descritiva com procedência.
Ao fim da Fase 5, tem medida própria, aprovada por ele e auditável até a
passagem. Ao fim da Fase 8, tem indicadores que quase nenhuma ferramenta livre
oferece — e, mais importante, tem como responder à pergunta que encerra toda
banca:

> *De onde veio esse número?*

Hoje, na aba de Indicadores, a resposta honesta seria "do banco, naquele dia".
Ao fim deste plano, é o instantâneo, o instrumento, a versão e as passagens.
