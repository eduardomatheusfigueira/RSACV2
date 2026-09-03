# 47 — Diagnóstico da Bibliometria

> **Revsist — Ambiente de Indicadores**
> **Status:** 🟢 Documento normativo vigente
> **Data:** 31/08/2026
> **Antecede:** [48 — Especificação do Ambiente de Indicadores](./48_ESPECIFICACAO_AMBIENTE_INDICADORES.md) · [49 — Plano de Execução](./49_PLANO_EXECUCAO_BIBLIOMETRIA.md)
> **Sucede:** [31](./31_DIAGNOSTICO_BI.md) · [32](./32_ESPECIFICACAO_BI.md) · [33](./33_PLANO_EXECUCAO_BI.md) — B.I. e Bibliometria v1, entregues
> **Relaciona-se com:** [45 §11](./45_PLANO_QUALIFICACAO_PROTOCOLOS.md) (desenho D11 — bibliometria)

---

## 1. Sumário — a frase que resume

A aba de Indicadores entregue nos docs 31–33 faz **B.I. do processo de
revisão** e faz bem: conta decisões, mede o funil, mostra a saúde da aquisição
de PDF. O que ela não faz — e nunca prometeu fazer — é **bibliometria**:
não há palavra-chave, não há referência citada, não há termo, não há grafo, e
não há como reproduzir um número depois que o acervo mudou.

A distância entre as duas coisas não é de quantidade de gráficos. É de
substância: bibliometria mede **a literatura**, e o que está armazenado hoje
descreve **o nosso trabalho sobre a literatura**. São dois objetos diferentes.

Este documento mede o tamanho exato dessa distância no acervo real do usuário —
87.108 registros — e identifica oito lacunas estruturais. A conclusão que
orienta o doc 48 é que **três das oito não são falta de funcionalidade, são
falta de garantia**: sem instantâneo, sem instrumento de medida e sem evidência
ligada ao número, qualquer indicador que o sistema produzir é indefensável em
banca — por mais bonito que seja o gráfico.

---

## 2. O que já existe, e funciona

Levantado em `app/services/insights_service.py` (392 linhas) e
`app/api/v1/insights.py`.

| Bloco | Conteúdo | Situação |
|---|---|---|
| Funil PRISMA | Reaproveita `get_prisma_flow_data` (`export_service.py:240`) | ✅ Correto |
| Funil de critérios | `PaperCriterionModel` por critério, inclusão vs exclusão | ✅ Correto |
| Composição | Decisão, base de coleta, distribuição temporal, tipo | ✅ Correto |
| Rankings | Periódicos, autores, instituições (`insights_service.py:381-383`) | ⚠️ Ver B-01 |
| Saúde de PDF | `pdf_status`, escaneados, completude de extração | ✅ Correto |
| Proveniência de IA | Decisões IA vs manual, confiança, resposta inválida | ✅ Correto — e raro |

O bloco de proveniência de IA merece registro: **medir quanto da própria
triagem foi assistida, com que confiança e com que taxa de resposta inválida**
é coisa que nenhuma ferramenta de bibliometria oferece, porque nenhuma delas
tria. É um ativo, e o doc 48 constrói em cima dele, não ao lado.

O doc 32 §7 já havia registrado como "extensões futuras" quase exatamente o
que este documento agora especifica: contagem de citações via OpenAlex/Crossref,
palavras-chave e coocorrência de termos, distribuição geográfica, e exportação
do painel. Este plano é a continuação declarada daquele, não uma virada.

---

## 3. Medições no acervo real

Executado em 31/08/2026 sobre `rsac.db` (leitura apenas), 87.108 registros em
três projetos.

| Campo | Preenchido | % | Consequência bibliométrica |
|---|---:|---:|---|
| `doi` | 85.725 | **98,4%** | Enriquecimento externo é viável (§5) |
| `journal` | 83.151 | 95,5% | Análise de fontes é viável hoje |
| `abstract` | 63.675 | 73,1% | Coocorrência de termos cobre ~3/4 do acervo |
| `institution` **útil** | ~249 | **0,3%** | Ranking de instituições é ficção (B-01) |
| `keywords` | — | **inexistente** | Sem coluna no banco (B-02) |
| referências citadas | — | **inexistente** | Sem cocitação, sem acoplamento (B-03) |
| texto completo extraído | 17 | **0,02%** | Contagem de termo só na amostra incluída (B-04) |

Distribuição por base: SciELO 79.745 · OpenAlex 7.175 · BDTD 251 — soma 87.171,
acima do total de registros porque a deduplicação funde procedências e um
registro pode ter mais de uma. Isso é correto e é, aliás, um dado bibliométrico
em si: **taxa de sobreposição entre bases**, hoje calculável e não calculada.

---

## 4. As oito lacunas

### B-01 — O ranking de instituições ordena coletores, não instituições

**Gravidade: alta. É o único achado que produz um número errado hoje, na tela.**

`insights_service.py:383` monta `top_institutions` a partir de
`PaperModel.institution`. Mas os coletores escrevem ali o **nome da própria
base**:

```
app/harvesters/scielo.py:115,199   institution="SciELO"
app/harvesters/openalex.py:232     institution="OpenAlex"
app/harvesters/pubmed.py:244       institution="PubMed/NCBI"
app/harvesters/scopus.py:219       institution="Scopus/Elsevier"
app/harvesters/bdtd.py:563         institution=inst_str or "BDTD/IBICT"   ← único correto
```

Medido: 79.692 registros dizem `SciELO` e 7.167 dizem `OpenAlex` — **86.859 de
87.108, ou 99,7%**. O gráfico "Top instituições" da aba de Indicadores,
portanto, informa ao pesquisador que a instituição mais produtiva do seu campo
é a biblioteca eletrônica de onde ele baixou os registros.

Só a BDTD preenche o campo com o que o campo diz ser. Os 249 registros restantes
são os únicos reais — e é por isso que o topo da lista fica com FCCN, IFPE,
UFRRJ, UFSC e USP com contagens de dois dígitos, atrás de duas entradas com
cinco.

Isto precisa ser corrigido antes de qualquer indicador novo, e por uma razão
que não é técnica: um painel que erra o que o usuário sabe conferir perde a
autoridade para afirmar o que ele não sabe conferir.

### B-02 — `keywords` existe em três camadas e morre no banco

O conceito atravessa o sistema inteiro e não chega ao disco:

```
app/domain/entities.py:102       keywords: List[str]          ← entidade de domínio
app/harvesters/base.py:99        keywords: str = ""           ← registro do coletor
app/schemas/protocol.py:82       target_fields = ["title", "abstract", "keywords"]
```

A estratégia de busca **declara que busca em palavras-chave**
(`schemas/protocol.py:82`), o coletor tem onde colocá-las, a entidade de domínio
as carrega — e `PaperModel` não tem a coluna. Confirmado por
`PRAGMA table_info(papers)`: 35 colunas, nenhuma `keywords`.

O efeito é duplo: a coocorrência de termos perde seu insumo mais limpo, e a
estratégia de busca registrada no protocolo descreve um alvo que o sistema não
armazena.

### B-03 — Não há referência citada em lugar nenhum

Nenhuma tabela guarda o que um artigo cita. Sem isso, ficam fora **toda a
metade da bibliometria que se apoia em citação**:

- cocitação (Small, 1973) — que autores/obras são citados juntos;
- acoplamento bibliográfico (Kessler, 1963) — que artigos citam as mesmas obras;
- caminho principal (Hummon & Doreian, 1989) — a espinha histórica de um campo;
- RPYS (Marx et al., 2014) — as raízes históricas por ano de publicação citada;
- qualquer indicador de impacto.

Esta é a maior lacuna em extensão, e a §5 mostra que também é a mais barata de
fechar.

### B-04 — O texto completo praticamente não existe, e não é persistido

Duas coisas distintas, ambas graves para o que o usuário pediu.

**Quantidade:** 17 registros de 87.108 têm texto extraído; 12 PDFs obtidos, 5
manuais, 3 falharam, 87.088 ausentes. Uma contagem de termos "no corpus" hoje
mediria 0,02% do corpus.

**Persistência:** `app/services/pdf_text.py` é um pipeline puro — extrai,
limpa, remove cabeçalho corrente, segmenta em IMRaD — mas **não guarda o
resultado**. O texto é reconstruído a partir do PDF a cada uso. `PaperModel`
guarda `pdf_text_extracted` (booleano) e `pdf_text_chars` (contagem), não o
texto.

A consequência é exatamente a que inviabiliza medida: contar termos sobre um
texto que é reproduzido a cada execução significa que **uma atualização da
biblioteca de extração muda os números publicados**, sem aviso e sem registro.
Uma contagem só é uma medida se o objeto medido estiver parado.

O lado positivo, e é grande: a segmentação IMRaD já existe
(`segment_sections`, `build_question_context`). Contar um termo **por seção** —
quantas vezes aparece no Método, e não no corpo inteiro — é um indicador que
quase nenhuma ferramenta oferece, e a peça mais difícil dele já está escrita.

### B-05 — Os indicadores são calculados sobre o banco vivo

`get_project_insights` consulta o estado atual. O acervo, porém, muda todo dia:
coleta, deduplicação, triagem, resolução de conflito. Um número obtido na terça
não é reproduzível na quinta, e nada na tela registra sobre que corpus ele foi
obtido.

Para B.I. de processo isso é aceitável — a pergunta "quantos faltam triar?" é
sobre o agora. Para bibliometria é fatal: o número vai para um artigo, o
artigo é avaliado meses depois, e a única defesa possível é poder recomputá-lo
idêntico. Hoje não é possível.

### B-06 — Não há vocabulário controlado

Coocorrência de termos sem tesauro produz ruído com aparência de resultado:
`resiliência` e `resiliencia`, singular e plural, sigla e extenso, português e
inglês entram como nós distintos. O VOSviewer exige um arquivo de tesauro
manual justamente por isso, e a maioria dos trabalhos publicados simplesmente
não o usa.

Não há, hoje, onde guardar equivalência de termos — nem por projeto, nem
global.

### B-07 — Contagem por IA não é medida

Esta lacuna não é de dados. É de método, e é a mais importante das oito.

O pedido "usar IA para consultar os textos e dizer quantas vezes um termo é
usado" descreve uma operação que um modelo de linguagem **não pode executar de
forma defensável**. Não é limitação de prompt nem de modelo: o modelo não tem
contador. Ele produz um número plausível, e produz um número diferente se
perguntado de novo. Se o Revsist exibir "a IA encontrou 47 ocorrências de
*resiliência*", esse 47 é ficção — e vai para uma dissertação.

A saída não é abandonar a IA. É **dividir a tarefa** entre quem sabe fazer cada
metade, e o doc 48 §6 constrói exatamente isso:

- **a IA propõe o vocabulário** — o que conta como o conceito: flexões,
  variantes ortográficas, traduções, siglas, e as formas que **não** contam
  (homônimos, o sentido de "resiliência" em ciência dos materiais);
- **o código conta** — determinístico, exato, repetível, com cada ocorrência
  localizada;
- **a pessoa aprova** o vocabulário antes de ele virar número, e confere uma
  amostra das ocorrências.

O mesmo raciocínio vale para "pedir uma estatística" em linguagem natural: a IA
traduz a pergunta em uma **especificação de consulta**, visível e editável, e o
código executa. O modelo nunca produz o número.

### B-08 — Não há como desenhar rede, e não deveria haver do jeito fácil

O frontend usa `recharts` (`InsightsPage.tsx:30`), que faz gráfico cartesiano e
não faz rede. Instalar uma biblioteca de grafo resolveria o desenho e criaria um
problema maior: **layout de força é aleatório**. Duas pessoas abrindo o mesmo
grafo veriam figuras diferentes, e a mesma pessoa veria uma figura diferente a
cada recarga. Uma figura que não se repete não pode ilustrar um resultado.

A decisão correspondente está no doc 48 §8: o layout é **cálculo**, feito no
servidor com semente fixa e guardado no instantâneo; o frontend apenas pinta.

---

## 5. O que está a uma requisição de distância

A lacuna B-03 parecia a mais cara e é a mais barata, porque 98,4% do acervo tem
DOI. Medição feita em 31/08/2026 contra a API pública do OpenAlex, com amostra
aleatória de 50 DOIs do acervo (semente 20260831):

| Verificação | Resultado |
|---|---|
| DOIs encontrados no OpenAlex | **50 de 50 (100%)** |
| Com lista de referências | 46 de 50 (92%) — **mediana de 17 referências** |
| Com tópicos atribuídos | 50 de 50 (100%) |
| Com instituição real (nome + país + ROR) | 45 de 50 (90%) |
| Com idioma declarado | 49 de 50 (98%) |
| Arestas de citação vindas de 50 artigos | 1.041 |

Os campos existem e vêm preenchidos: `cited_by_count`, `referenced_works`,
`counts_by_year`, `topics`, `keywords`, `concepts`,
`sustainable_development_goals`, `open_access`, `language`, e
`authorships[].institutions` com `display_name`, `country_code` e **`ror`** —
identificador resolvido, que é o que permite normalizar instituição sem
casar strings.

Extrapolando a amostra: cerca de **1,3 milhão de arestas de citação** para o
acervo inteiro, obtidas em aproximadamente **1.700 requisições** (o OpenAlex
aceita listas de 50 DOIs por consulta).

Ou seja: as lacunas B-01 (instituição), B-02 (palavras-chave) e B-03
(referências) são, as três, **a mesma lacuna** — a de nunca termos pedido ao
OpenAlex o que ele já devolve de graça. O coletor
(`app/harvesters/openalex.py:221-237`) monta o registro com sete campos e
descarta o resto da resposta, inclusive quando ele mesmo foi a origem do
registro.

---

## 6. As três substâncias, e o que temos de cada

Bibliometria se faz sobre três substratos, com custos e alcances diferentes. A
confusão entre eles é a origem da maioria dos pedidos impossíveis.

| Substrato | Cobertura hoje | Cobertura possível | O que sustenta |
|---|---|---|---|
| **Metadado** (título, resumo, autoria, fonte, ano) | 73–98% | igual | Produção temporal, coautoria, fontes, coocorrência de termos, leis de Bradford/Lotka |
| **Citação** (referências e citações recebidas) | 0% | ~92% via OpenAlex | Cocitação, acoplamento, caminho principal, RPYS, impacto |
| **Texto completo** | 0,02% | limitada à amostra incluída | Contagem de termo por seção, coocorrência em janela, evidência literal |

A leitura prática, que precisa estar clara na interface antes de estar clara
aqui: **contagem de termo em texto completo é análise de dezenas de
documentos, não de dezenas de milhares.** É uma ferramenta para a amostra
incluída de uma revisão — que é justamente onde ela é valiosa e onde ninguém a
oferece. Prometê-la sobre 87 mil registros seria prometer o que nem o acesso
editorial permitiria.

---

## 7. O que a literatura exige

Bibliometria não tem uma diretriz de relato com a força do PRISMA, mas tem
três referências que fazem as vezes:

1. **BIBLIO** (Montazeri et al., *Systematic Reviews*, 2023;12:239) — diretriz
   preliminar registrada na EQUATOR, 20 itens em seis seções, sendo **7 só em
   métodos**. Já adotada no doc 45 §11 como diretriz de relato do desenho D11.
   Os itens de método pedem, entre outras coisas, a declaração explícita da
   estratégia de busca, do software usado e dos critérios de normalização de
   termos — os três pontos onde o Revsist hoje não teria o que declarar.
2. **Donthu et al.** (*Journal of Business Research*, 2021) e **Zupic & Čater**
   (*Organizational Research Methods*, 2015) — as duas revisões metodológicas
   mais citadas sobre como conduzir análise bibliométrica; ambas insistem na
   separação entre análise de desempenho e mapeamento científico, e na
   declaração dos parâmetros de agrupamento.
3. **Manifesto de Leiden** (Hicks, Wouters, Waltman, de Rijcke & Rafols,
   *Nature*, 2015) — dez princípios para o uso de indicadores. Três deles são,
   literalmente, a especificação de auditabilidade que o doc 48 implementa:
   manter a coleta e a análise **abertas e transparentes**, permitir que os
   avaliados **verifiquem os dados**, e reconhecer a **variação por campo**.

Somam-se o **DORA** e o *Metric Tide*, que sustentam uma posição que o doc 48
adota de forma explícita: **o sistema não calculará indicador de periódico para
julgar artigo**. Não por incapacidade técnica — por ser uso que a própria área
classifica como incorreto.

---

## 8. Conclusão — o que precisa existir

Das oito lacunas, cinco são de dado e três são de garantia. Fechar só as de
dado produziria uma ferramenta com mais gráficos e a mesma fragilidade.

**De dado** — B-01 instituição, B-02 palavras-chave, B-03 referências, B-04
texto persistido, B-06 tesauro. Todas se resolvem com enriquecimento e
armazenamento; a §5 mostra que a maior parte cabe em um coletor de
enriquecimento e três tabelas.

**De garantia** — B-05 instantâneo, B-07 instrumento de medida, B-08
determinismo do desenho. São o que separa "painel bonito" de "resultado
defensável", e são o que o doc 48 chama de pilares.

A ordem importa: **B-01 primeiro**, porque é o único erro visível hoje; depois
as de garantia, porque tudo o que for construído sem elas terá de ser refeito;
os indicadores por último, porque são a parte fácil.

O desenho completo está no [doc 48](./48_ESPECIFICACAO_AMBIENTE_INDICADORES.md);
as fases e os critérios de aceite, no
[doc 49](./49_PLANO_EXECUCAO_BIBLIOMETRIA.md).
