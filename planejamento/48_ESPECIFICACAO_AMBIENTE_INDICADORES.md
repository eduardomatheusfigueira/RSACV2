# 48 — Especificação do Ambiente de Indicadores

> **Revsist — Bibliometria auditável**
> **Status:** 🟢 Documento normativo vigente
> **Data:** 31/08/2026
> **Sucede:** [47 — Diagnóstico da Bibliometria](./47_DIAGNOSTICO_BIBLIOMETRIA.md)
> **Antecede:** [49 — Plano de Execução](./49_PLANO_EXECUCAO_BIBLIOMETRIA.md)
> **Depende de:** [45](./45_PLANO_QUALIFICACAO_PROTOCOLOS.md) (protocolo, versionamento, D11) · [32](./32_ESPECIFICACAO_BI.md) (aba de Indicadores v1) · [24](./24_ESPECIFICACAO_DESIGN_SYSTEM.md) (tokens)

---

## 1. A tese

Existem hoje ferramentas de bibliometria maduras e gratuitas — VOSviewer,
bibliometrix, CiteSpace, SciMAT. Construir uma décima que faça mapas de
coocorrência não interessa a ninguém, e não é o que a posição do Revsist
permite.

O que nenhuma delas faz é o que o Revsist está em posição única de fazer:
**produzir indicadores que a pessoa consegue defender**. Nas quatro ferramentas
acima, um número na tela é o fim da linha — não há como clicar nele e ver de
onde veio, não há como recomputá-lo idêntico seis meses depois, e não há
registro de que decisões de normalização o produziram.

O diferencial deste ambiente, portanto, não é a quantidade de indicadores. São
quatro garantias, e elas vêm antes de qualquer gráfico:

| Garantia | O que significa | Verificável por |
|---|---|---|
| **Reprodutível** | O mesmo instantâneo + a mesma semente + a mesma versão do instrumento produzem saída idêntica byte a byte | Teste automatizado (doc 49 §T-3) |
| **Rastreável** | Todo número é clicável até os documentos e, no texto, até as passagens que o compõem | `bib_ocorrencias` (§6.6) |
| **Declarado** | Todo indicador carrega denominador, parâmetros, tesauro e versão do motor | Rodapé de proveniência (§14.4) |
| **Honesto quanto à incerteza** | Rankings e índices vêm com intervalo, e a sensibilidade aos parâmetros é mostrada | §10 |

Estas quatro não são acabamento. São a especificação dos três princípios do
Manifesto de Leiden que se aplicam a uma ferramenta — manter a coleta e a
análise abertas e transparentes, permitir que os dados sejam verificados, e
reconhecer a variação por campo.

---

## 2. Os quatro pilares

Tudo neste documento se apoia em quatro objetos. Vale fixá-los antes do
detalhe, porque o vocabulário se repete.

```
   INSTANTÂNEO ────────► o corpus congelado. Que documentos, com que
   (§3)                  conteúdo, em que momento. Tem hash.

   INSTRUMENTO ────────► como um conceito vira número. Léxico proposto
   (§6)                  pela IA, aprovado por uma pessoa, versionado.

   INDICADOR ──────────► a conta em si. Sempre = f(instantâneo,
   (§7)                  instrumento, parâmetros declarados).

   EVIDÊNCIA ──────────► cada ocorrência que sustentou o número, com
   (§6.6)                documento, seção, página e posição.
```

A regra que governa os quatro, e que não admite exceção:

> **Nenhum número exibido pelo ambiente pode ter sido produzido por um modelo
> de linguagem.** A IA propõe vocabulário, sugere agrupamentos, nomeia clusters
> e traduz perguntas em especificações. Contar, somar, ordenar e medir é
> sempre código determinístico.

O porquê está no doc 47 §B-07 e não se repete aqui. O que se repete é a
consequência de projeto: toda funcionalidade de IA neste ambiente termina em um
**artefato que uma pessoa aprova**, nunca em um número.

---

## 3. Instantâneo — o corpus parado

### 3.1 Por que não basta consultar o banco

Um indicador bibliométrico é uma afirmação sobre um conjunto. Se o conjunto
muda, a afirmação muda, e a única defesa possível em banca é poder reconstituir
o conjunto exato. O acervo do Revsist muda por coleta, deduplicação, triagem e
resolução de conflito — todo dia, e legitimamente.

### 3.2 Contrato

Um instantâneo **não copia o acervo**. Copiar 87 mil linhas por análise é
inviável em SQLite e desnecessário. Ele guarda um **manifesto**: para cada
documento no escopo, o par `(paper_id, hash_do_conteúdo)`, onde o hash cobre
exatamente os campos que os indicadores leem.

```python
# Ordem canônica e separador explícito: sem isso, "ab"+"c" e "a"+"bc"
# produziriam o mesmo hash e dois corpora diferentes teriam a mesma
# identidade.
CAMPOS_DO_HASH = (
    "title", "authors", "year", "doi", "abstract",
    "journal", "institution", "research_type", "decision", "is_duplicate",
)
conteudo_hash = sha256("\x1f".join(campos).encode("utf-8"))
corpus_hash   = sha256(manifesto_ordenado_por_paper_id)
```

Custo medido para o acervo real: 87.108 pares × ~50 bytes ≈ **4,4 MB antes de
comprimir**. Aceitável.

### 3.3 A propriedade que o torna útil

Ao abrir qualquer análise, o ambiente recomputa o manifesto e compara. Três
desfechos, e os três são informação:

| Comparação | Significado | Comportamento |
|---|---|---|
| Hash idêntico | O corpus não mudou | Análise vale, sem aviso |
| Documentos iguais, conteúdo mudou | Alguém corrigiu metadado | Aviso: "3 documentos foram editados desde este instantâneo" com a lista |
| Conjunto mudou | Coleta ou triagem andou | Aviso e oferta de criar um instantâneo novo — **nunca recomputar em silêncio** |

O que não pode acontecer, e é o comportamento de hoje, é a tela mostrar um
número diferente do de ontem sem dizer que o corpus mudou.

### 3.4 Escopo

O instantâneo é criado a partir de um escopo declarado — os mesmos filtros da
aba de Indicadores (`decision`, `source`, `year_from`, `year_to`), guardados em
JSON. O escopo padrão para bibliometria da revisão é `decision = Incluído`; o
escopo padrão para bibliometria **do campo** é o acervo pós-deduplicação
inteiro. São análises diferentes e legítimas, e a interface precisa deixar
óbvio qual está aberta (§14.2).

---

## 4. Enriquecimento externo

### 4.1 Decisão: OpenAlex como fonte primária

Medido no doc 47 §5: 50 de 50 DOIs do acervo encontrados, 92% com referências,
100% com tópicos, 90% com instituição resolvida por ROR.

A escolha se justifica em quatro pontos, e o quarto é o decisivo:

1. **Cobertura medida** neste acervo, não prometida em folheto.
2. **Sem credencial** — o *polite pool* pede apenas um `mailto`, o que se
   encaixa numa instalação local sem gestão de segredo.
3. **Licença aberta** (CC0), o que permite guardar o dado derivado e exportá-lo
   junto do relatório sem restrição contratual — coisa que Scopus e Web of
   Science não permitem.
4. **Identificadores resolvidos** — ROR para instituição, OpenAlex ID para
   autor e obra. Isto é o que fecha B-01 sem heurística de string: duas
   afiliações escritas de formas diferentes viram a mesma instituição porque
   têm o mesmo ROR, não porque um algoritmo achou os nomes parecidos.

**Crossref** entra como reserva para DOIs que o OpenAlex não conheça (nenhum na
amostra, mas o acervo tem 85.725) e **OpenCitations** como terceira via para
referências. A ordem é declarada e registrada por documento: cada campo guarda
de onde veio.

### 4.2 O que se guarda

Além dos campos derivados, guarda-se o **JSON bruto da resposta**
(`bib_work_meta.raw`). Isto não é preciosismo: quando um número for questionado
dois anos depois, a pergunta será "de onde saiu essa afiliação?", e a resposta
tem de ser o documento que a sustentou, não uma coluna reprocessada.

### 4.3 Correção de B-01 — instituição

O campo `PaperModel.institution` **não será reaproveitado**. Ele contém o nome
do coletor em 99,7% dos registros e corrigi-lo por migração exigiria adivinhar
o que nunca foi coletado.

Em vez disso: `bib_authorships` passa a ser a origem da verdade sobre autoria e
afiliação, e o ranking de instituições da aba de Indicadores passa a lê-la.
Enquanto o enriquecimento não tiver rodado, o gráfico **não mostra dados
errados** — mostra o estado vazio previsto no doc 32 §5.4, com a explicação e o
botão que inicia o enriquecimento.

Deixar de exibir é a correção. Exibir o nome do coletor como instituição é o
defeito.

> **Refinado na implementação (31/08/2026).** A especificação dizia "estado
> vazio até o enriquecimento rodar". Na prática existe um resto real: a BDTD
> preenche o campo com o que ele diz ser. Medido nos projetos do usuário — 0 de
> 39, 0 de 22 e **14 de 15**. Descartar esses catorze seria jogar fora dado
> bom.
>
> O que foi implementado, e é mais consistente com o §6.4 deste documento: o
> filtro tira o literal do coletor, o que sobra é exibido **com a cobertura
> declarada** ("Sobre 14 de 15 estudos — as bases de coleta raramente informam
> a afiliação dos autores"), e o estado vazio explicativo aparece quando não
> sobra nada. O denominador é o que impede a lista de ser lida como se
> descrevesse o acervo inteiro.

### 4.4 Custo e ritmo

Cerca de **1.700 requisições** para o acervo inteiro (listas de 50 DOIs por
consulta). O enriquecimento roda como trabalho de segundo plano, reaproveitando
o `AsyncJobManager` e o canal de WebSocket já existentes na coleta, com o mesmo
acelerador adaptativo da triagem em lote (`app/services/acelerador.py`) — que
já sabe recuar diante de recusa e voltar a subir.

Enriquecimento é **incremental e retomável**: um documento já enriquecido na
rodada vigente não é reconsultado.

---

## 5. Camada de texto

Fecha B-04. `bib_textos` guarda, por documento:

- o texto limpo, comprimido, como `pdf_text.py` já o produz;
- a **versão do pipeline** que o produziu;
- o **sha256 do PDF** de origem;
- o mapa de seções IMRaD (`segment_sections`), com deslocamentos;
- contagem de páginas e de palavras — o denominador de qualquer frequência
  relativa.

Duas consequências de projeto:

**A versão do pipeline entra no hash do instantâneo.** Se `pdf_text.py` mudar
— e vai mudar —, os textos antigos continuam válidos e identificados como
tendo sido produzidos pela versão anterior. Nada é recontado em silêncio.

**Contagem por seção passa a ser possível.** "Quantas vezes *estudo de caso*
aparece no Método" é uma pergunta diferente de "no artigo", e é a pergunta que
o metodologista realmente quer fazer. A segmentação já existe; falta apenas
persistir e indexar.

---

## 6. Instrumento de medida — o núcleo

Esta seção responde ao pedido de "usar IA para consultar os textos e contar
termos" de um jeito que sobreviva a arguição.

### 6.1 A divisão de trabalho

```
   PESSOA          declara o conceito
      │            "resiliência urbana"
      ▼
   IA              propõe o léxico
      │            incluir: resiliência urbana, resiliência das cidades,
      │                     urban resilience, cidade resiliente, ...
      │            excluir: resiliência (ciência dos materiais),
      │                     resiliência psicológica individual
      ▼
   PESSOA          revisa, edita e APROVA          ◄── porta obrigatória
      │            (o instrumento ganha versão e fica congelado)
      ▼
   CÓDIGO          conta, determinístico
      │            por documento, por seção, com posição de cada acerto
      ▼
   PESSOA          confere uma amostra dos acertos
                   (estima a precisão do instrumento — §6.7)
```

A porta do meio é obrigatória por desenho: um instrumento em rascunho **não
produz número**. A tela pode mostrar uma prévia sobre três documentos para
ajudar a calibrar, marcada como prévia e não exportável.

### 6.2 O léxico

```json
{
  "conceito": "resiliência urbana",
  "definicao": "Capacidade de sistemas urbanos absorverem perturbação e se reorganizarem.",
  "modo": "lema",
  "incluir": [
    {"forma": "resiliência urbana", "tipo": "expressao"},
    {"forma": "resiliência das cidades", "tipo": "expressao"},
    {"forma": "urban resilience", "tipo": "expressao", "idioma": "en"},
    {"forma": "cidade resiliente", "tipo": "expressao"}
  ],
  "excluir": [
    {"forma": "resiliência do material", "motivo": "sentido em ciência dos materiais"},
    {"forma": "resiliência psicológica", "motivo": "unidade de análise é o indivíduo"}
  ],
  "janela_de_coocorrencia": 10
}
```

Três decisões dentro deste objeto merecem justificativa.

**`modo`.** Três valores: `literal` (casa a forma exata), `lema` (casa flexões
por normalização morfológica leve — plural, gênero, conjugação) e `regex`
(para quem sabe o que está fazendo). O padrão é `lema`, porque `literal` erra
por baixo em português — que flexiona muito — e `regex` transfere a
responsabilidade a quem não pediu por ela.

**`excluir` com `motivo`.** A exclusão não é detalhe técnico: ela é a decisão
metodológica mais importante do instrumento, e é o que a banca vai perguntar.
O motivo é campo obrigatório e entra no relatório.

**A IA propõe, e a proposta guarda sua procedência.** `proposto_por`,
`modelo_usado` e `prompt_hash` ficam gravados. Se um dia o léxico for
contestado, é possível dizer qual modelo o sugeriu e o que foi perguntado a ele.

### 6.3 O contador

Determinístico, em Python, sem rede e sem modelo. Sobre a camada de texto (§5)
e sobre título + resumo + palavras-chave quando não houver texto completo.

Devolve, por documento e por seção:

| Medida | Definição | Por que não basta a anterior |
|---|---|---|
| **Frequência bruta** | Ocorrências | Um artigo de 40 páginas ganha de um de 8 sem dizer nada |
| **Frequência relativa** | Ocorrências por 1.000 palavras | Compara documentos de tamanhos diferentes |
| **Frequência documental** | Em quantos documentos aparece ao menos uma vez | Distingue "termo central do campo" de "obsessão de um autor" |
| **Distribuição por seção** | Ocorrências em cada seção IMRaD | Termo no Método é escolha metodológica; na Introdução é contexto |

As quatro são exibidas juntas, sempre. Mostrar frequência bruta sozinha é o
erro mais comum e mais difícil de desfazer depois de publicado.

### 6.4 O denominador, sempre

Nenhuma contagem é exibida sem o denominador ao lado:

> *resiliência urbana* — **312 ocorrências** em 34 documentos
> *contado em 34 dos 51 incluídos; 17 sem texto completo (§5)*

A segunda linha não é rodapé opcional. É parte do número.

### 6.5 Coocorrência de termos em janela

Com dois ou mais instrumentos, o contador registra coocorrência dentro de uma
janela de N palavras (padrão 10, declarado). Isto alimenta o grafo de termos do
§8 com arestas que significam proximidade textual real, e não apenas
"apareceram no mesmo resumo".

### 6.6 Evidência — o número clicável

Cada acerto grava uma linha em `bib_ocorrencias`: documento, seção, página,
deslocamento inicial e final, e **a forma efetivamente encontrada** — que pode
diferir da forma do léxico quando o modo é `lema`.

É isto que faz do ambiente algo diferente de um painel: clicar em "312" abre a
lista dos 34 documentos; clicar em um documento abre as passagens, destacadas
no texto, com a página. Nenhuma das ferramentas citadas no §1 permite isso.

Custo: um instrumento com 312 acertos gera 312 linhas. Mesmo um instrumento
agressivo sobre a amostra incluída fica na casa dos milhares. Não há problema
de escala porque **contagem em texto completo é operação sobre a amostra
incluída** (doc 47 §6), e o sistema recusa executá-la sobre corpus de dezenas de
milhares, explicando por quê.

### 6.7 Precisão do instrumento

Um instrumento aprovado ainda pode errar: casar homônimo, perder variante. O
ambiente oferece — não obriga — uma **conferência amostral**: sorteia *k*
ocorrências (padrão 30, semente registrada), a pessoa marca cada uma como
pertinente ou não, e o instrumento passa a carregar sua precisão estimada com
intervalo de confiança.

Um instrumento com precisão medida de 0,87 (IC 95% 0,70–0,96) é um instrumento
que se pode citar em métodos. É prática corrente em análise de conteúdo e
praticamente ausente em bibliometria — e é barata de oferecer.

---

## 7. Catálogo de indicadores

Organizado por substrato, porque é o substrato que decide se o indicador é
possível (doc 47 §6). Cada linha traz a referência de origem, porque um
indicador sem procedência não passa em revisão.

### 7.1 Nível 0 — Metadado (disponível assim que houver instantâneo)

| Indicador | O que responde | Origem |
|---|---|---|
| Produção anual e taxa de crescimento | O campo está crescendo? | Price (1963) |
| Concentração de fontes (Bradford) | Quantos periódicos concentram o núcleo? | Bradford (1934) |
| Produtividade de autores (Lotka) | A autoria segue lei de potência? | Lotka (1926) |
| Índice de colaboração e coautoria por documento | Trabalha-se junto? | Subramanyam (1983) |
| Rede de coautoria | Quem trabalha com quem | §8 |
| Coocorrência de termos | Que temas andam juntos | §8 |
| Sobreposição entre bases | O que cada base trouxe de exclusivo | Já calculável hoje (doc 47 §3) |
| Concentração (Gini, HHI) | A produção está concentrada? | Padrão em cientometria |

Sobre Bradford e Lotka, uma exigência que o ambiente impõe e a literatura
frequentemente ignora: **não basta ajustar a lei, é preciso testar a
aderência.** O ajuste vem com estatística de Kolmogorov–Smirnov e o
procedimento de Clauset, Shalizi & Newman (2009). Relatar "o campo segue a lei
de Lotka" sem teste é afirmação sem lastro, e o ambiente não a produzirá.

### 7.2 Nível 1 — Citação (depois do enriquecimento)

| Indicador | O que responde | Origem |
|---|---|---|
| Citações recebidas, mediana e distribuição | Qual o alcance do corpus? | — |
| Índice h do corpus | — | Hirsch (2005) |
| Cocitação de referências | Que obras fundamentam o campo | Small (1973) |
| Acoplamento bibliográfico | Que artigos partilham base teórica | Kessler (1963) |
| RPYS — espectroscopia de anos de referência | Quais são as raízes históricas | Marx et al. (2014) |
| Caminho principal | A espinha dorsal do desenvolvimento | Hummon & Doreian (1989) |
| Instituições e países | Geografia real da produção | ROR/OpenAlex, fecha B-01 |
| Situação de acesso aberto | Quanto do corpus é acessível | OpenAlex `open_access` |

**Deliberadamente fora:** indicadores normalizados por campo (MNCS, PP(top
10%)) — exigem universo de referência completo por campo e ano, e errar a
normalização produz número pior que não ter número. E **qualquer métrica de
periódico usada para julgar artigo**, por DORA e pelo Manifesto de Leiden. A
recusa é explícita na interface, com a razão — não é uma funcionalidade
faltando.

### 7.3 Nível 2 — Texto completo (amostra incluída)

Tudo o que o §6 produz: frequência bruta, relativa e documental; distribuição
por seção IMRaD; coocorrência em janela; evidência localizada.

E um indicador que só existe porque o Revsist tria antes de medir:
**frequência do termo cruzada com a decisão de triagem** — o termo aparece mais
nos incluídos ou nos excluídos? É um diagnóstico do próprio critério de
inclusão, e não há ferramenta de bibliometria que possa calculá-lo, porque
nenhuma tem a decisão.

### 7.4 Nível 3 — Vanguarda

Cinco itens. Os dois primeiros são consolidados na literatura e ausentes das
ferramentas livres; os três últimos são o que de fato distingue este ambiente.

**a) Diagrama estratégico e evolução temática.** Cada agrupamento de termos
recebe centralidade (força de ligação com outros temas) e densidade (coesão
interna), e é posicionado em quatro quadrantes — temas motores, básicos,
emergentes/em declínio, periféricos. Fatiando o corpus em períodos, obtém-se o
diagrama de evolução com índices de inclusão entre períodos.
Callon, Courtial & Laville (1991); Cobo et al. (2011), SciMAT.

**b) Detecção de rajadas.** Termos cuja frequência sobe abruptamente num
intervalo — a assinatura de tema emergente. Algoritmo de estado de Kleinberg
(2003), com os parâmetros declarados.

**c) Incerteza declarada.** Ver §10. Rankings sem intervalo são o vício crônico
da área.

**d) Sensibilidade a parâmetro.** Ver §10.2. Quanto o resultado muda se o corte
de frequência, a janela ou a resolução de agrupamento mudarem.

**e) Cobertura do campo.** Cruzando os tópicos OpenAlex do corpus com o total
publicado nesses mesmos tópicos, estima-se **que fração do campo a busca
capturou** — e em que subtemas ela é rala. Isto não é decoração: é um
indicador de qualidade da estratégia de busca, exatamente o que o PRESS avalia
por julgamento humano, aqui com número. Numa revisão sistemática, responde à
pergunta que o avaliador sempre faz: *a busca foi abrangente?*

O item (e) é o mais valioso do documento e o menos óbvio. Ele liga a
bibliometria de volta ao protocolo (doc 45 §10) em vez de deixá-la como
apêndice ornamental no fim da revisão.

---

## 8. Grafos

### 8.1 Quatro redes, um motor

Coocorrência de termos, coautoria, acoplamento bibliográfico e cocitação são a
mesma estrutura — nós, arestas ponderadas, agrupamento, layout — sobre matrizes
de origem diferentes. Um motor só, quatro alimentadores.

### 8.2 Normalização de força

Contagem bruta de coocorrência favorece o que é frequente, não o que é
associado. A força da aresta usa **força de associação**
(*association strength*), padrão do VOSviewer:

```
        c_ij
s_ij = ───────      c_ij = coocorrências;  c_i, c_j = ocorrências totais
       c_i · c_j
```

Van Eck & Waltman (2009) mostram que esta é a normalização probabilisticamente
adequada; Jaccard e cosseno ficam disponíveis como alternativa **declarada**,
porque trabalhos publicados usam as três e a comparação precisa ser possível.

### 8.3 Agrupamento

Louvain (Blondel et al., 2008) com semente fixa, via `networkx` — dependência
Python pura, que instala sem compilador em máquina de usuário final. A
resolução é parâmetro exposto e registrado; não há valor "certo", e escondê-lo
seria fingir que há.

Leiden (Traag, Waltman & van Eck, 2019) corrige o defeito conhecido do Louvain
de produzir comunidades mal conectadas, e fica como melhoria opcional para
quando `leidenalg` estiver disponível — nunca como requisito de instalação.

### 8.4 Layout determinístico — a decisão que fecha B-08

**O layout é calculado no servidor, com semente fixa, e guardado no
instantâneo.** O frontend recebe coordenadas e pinta em Canvas.

Três razões, em ordem de importância:

1. **A figura se repete.** Duas pessoas, dois computadores, seis meses de
   intervalo: o mesmo desenho. Uma figura de artigo que não se reproduz não é
   um resultado.
2. **As coordenadas viram dado exportável.** O grafo sai em GEXF/GraphML com
   posições, e abre no Gephi para quem quiser refinar — sem que o número mude.
3. **Nenhuma dependência nova de peso no frontend.** Canvas resolve; o
   `recharts` continua para o que é cartesiano.

O algoritmo (Fruchterman–Reingold com semente e número de iterações declarados)
e a semente aparecem na legenda da figura. Uma legenda que diz *"layout FR,
semente 42, 200 iterações, força de associação, Louvain res. 1,0"* é uma
legenda que um metodologista consegue avaliar.

### 8.5 Tesauro — fecha B-06

Sem vocabulário controlado, o grafo de termos mostra `resiliência` e
`resiliencia` como dois nós, e o resultado é ruído com aparência de achado.

O tesauro é um artefato de primeira classe: entradas com termo preferido,
variantes, escopo e quem aprovou. A IA **propõe fusões**, agrupando formas que
parecem a mesma coisa e apresentando cada grupo para aprovação em bloco. A
pessoa aceita, recusa ou edita. Nada é fundido automaticamente.

O tesauro é versionado e viaja com o instantâneo: um grafo sabe sob que versão
do tesauro foi construído.

---

## 9. Estatística sob demanda

Responde ao pedido de "poder pedir alguma estatística".

### 9.1 O pipeline

```
   pergunta em português
        │  "qual a mediana de citações por ano, só dos incluídos?"
        ▼
   IA traduz em ESPECIFICAÇÃO (JSON)  ─── nunca em SQL, nunca no número
        ▼
   especificação é VALIDADA contra esquema fechado
        ▼
   pessoa VÊ e pode EDITAR a especificação
        ▼
   código EXECUTA e devolve o número
        ▼
   pergunta + especificação + resultado ficam SALVOS e re-executáveis
```

### 9.2 A especificação

```json
{
  "medida": "mediana",
  "campo": "citacoes_recebidas",
  "por": ["ano"],
  "onde": [{"campo": "decisao", "op": "=", "valor": "Incluído"}],
  "ordenar_por": "grupo",
  "limite": 50,
  "instantaneo_id": "snp_a91f…"
}
```

Vocabulário **fechado**, validado por Pydantic:

- `medida` ∈ {contagem, distintos, soma, média, mediana, quantil, taxa,
  desvio-padrão}
- `campo` ∈ conjunto declarado de campos numéricos do instantâneo
- `por` ∈ {ano, fonte, decisão, periódico, instituição, país, idioma, tópico,
  acesso aberto, tipo, autor, termo, instrumento}
- `onde` — operadores `=`, `≠`, `>`, `<`, `entre`, `em`, `contém`

Um compilador traduz a especificação em consulta SQLAlchemy parametrizada.
**Em nenhum momento texto vindo do modelo chega ao banco.** Isto é decisão de
segurança tanto quanto de auditoria: SQL livre gerado por modelo é injeção com
outro nome, e o doc 29 não permitiria.

Se a pergunta não couber no vocabulário, o sistema **diz que não cabe** e mostra
o que sabe responder. Não improvisa.

### 9.3 Por que mostrar a especificação

Porque é ela, e não a pergunta em português, que define o número. "Mediana de
citações por ano" é ambíguo — mediana entre artigos daquele ano, ou entre anos?
A especificação desfaz a ambiguidade, e mostrá-la transfere à pessoa a chance
de perceber que perguntou outra coisa. Análises salvas guardam a especificação,
não o texto: é o que permite reexecutar sobre outro instantâneo e comparar.

---

## 10. Incerteza e sensibilidade

### 10.1 Intervalos

Rankings e índices agregados vêm com intervalo por reamostragem *bootstrap*
(1.000 reamostras, semente registrada) sobre os documentos do instantâneo.

O efeito na prática:

> **Top periódicos** — 1º *Cities* (18 artigos). As posições 2ª a 5ª são
> estatisticamente indistinguíveis entre si (IC 95% sobrepostos).

Sem isso, o pesquisador escreve "os cinco periódicos mais relevantes são, em
ordem…", e a ordem é ruído amostral. Este aviso é barato de calcular e evita
uma afirmação errada por trabalho.

### 10.2 Sensibilidade

Todo resultado que dependa de parâmetro arbitrário — corte mínimo de
frequência, janela de coocorrência, resolução de agrupamento, escolha de
normalização — ganha um painel curto que varre o parâmetro e mostra o quanto o
resultado se mexe:

```
   Nº de agrupamentos por resolução
   0,6 → 4 grupos     0,8 → 5      1,0 → 5  ◄ vigente      1,2 → 7     1,4 → 9
   Estabilidade dos pares (índice de Rand ajustado, vs. vigente): 0,91 · 0,96 · — · 0,88 · 0,71
```

Ler isso é aprender que a estrutura é estável entre 0,8 e 1,2 e se fragmenta
depois — o que é um resultado sobre o campo, não sobre o software. É o item de
vanguarda mais fácil de implementar e o mais difícil de encontrar em qualquer
ferramenta existente.

---

## 11. Pré-registro do plano bibliométrico

Análise bibliométrica é especialmente vulnerável a HARKing: com vinte
indicadores disponíveis e nenhum plano, escolhe-se depois o gráfico que ficou
bonito.

O doc 45 já construiu a máquina que resolve isto — `protocol_versions`,
`protocol_amendments`, congelamento. O desenho D11 (bibliometria) ganha, na
seção de análise do protocolo, os campos:

- indicadores previstos, marcados de uma lista;
- unidade de análise (documento, autor, fonte, termo);
- janela temporal e sua justificativa;
- tesauro previsto e critérios de normalização;
- **cortes e parâmetros declarados antes de ver o resultado**.

Rodar um indicador não previsto é permitido e normal — a análise é marcada como
**exploratória** e assim aparece em toda exportação. Alterar o plano depois de
ver resultado gera emenda, com data e motivo, como qualquer emenda de
protocolo.

Isto reaproveita máquina existente e é, provavelmente, o item que mais
distingue o Revsist de uma ferramenta de bibliometria: nenhuma delas tem
protocolo, porque nenhuma delas sabe o que é um.

---

## 12. Modelo de dados

Onze tabelas novas. Nenhuma coluna removida; `PaperModel.institution` fica onde
está, sem uso novo (§4.3).

```sql
-- ── Corpus congelado ─────────────────────────────────────────────
bib_snapshots        id, project_id, rotulo, escopo(JSON), n_documentos,
                     corpus_hash, manifesto(BLOB), versao_do_motor,
                     versao_do_pipeline_de_texto, enrichment_id,
                     criado_por, criado_em

-- ── Enriquecimento externo (§4) ──────────────────────────────────
bib_enrichments      id, project_id, provedor, iniciado_em, concluido_em,
                     n_consultados, n_encontrados, estado
bib_work_meta        paper_id PK, enrichment_id, provedor, external_id,
                     cited_by_count, referenced_works_count, language,
                     tipo, is_oa, oa_status, raw(JSON), obtido_em
bib_references       citing_paper_id, cited_external_id, cited_doi
                     -- índice nos dois lados; ~1,3 M linhas no acervo real
bib_authorships      paper_id, posicao, autor_external_id, autor_nome,
                     instituicao_ror, instituicao_nome, pais
                     -- fecha B-01
bib_topics           paper_id, topico_id, topico_nome, nivel, score

-- ── Termos (§5, §6, §8.5) ────────────────────────────────────────
bib_keywords         paper_id, termo, origem, posicao       -- fecha B-02
bib_textos           paper_id, versao_do_pipeline, sha256_do_pdf,
                     n_paginas, n_palavras, texto(BLOB),
                     secoes(JSON), extraido_em               -- fecha B-04
bib_tesauro_entradas tesauro_id, termo_preferido, variantes(JSON), escopo,
                     proposto_por, aprovado_por, aprovado_em -- fecha B-06

-- ── Medida (§6) ──────────────────────────────────────────────────
bib_instrumentos     id, project_id, conceito, definicao, lexico(JSON),
                     versao, estado, proposto_por, modelo_usado,
                     prompt_hash, aprovado_por, aprovado_em,
                     precisao_estimada, precisao_ic(JSON)    -- fecha B-07
bib_medidas          id, snapshot_id, instrumento_id, versao_do_instrumento,
                     resultado(JSON), n_documentos,
                     n_documentos_com_texto, executado_em
bib_ocorrencias      medida_id, paper_id, secao, pagina,
                     offset_inicio, offset_fim, forma_encontrada

-- ── Grafos e análises (§8, §9) ───────────────────────────────────
bib_grafos           id, snapshot_id, tipo, parametros(JSON), nos(JSON),
                     arestas(JSON), coordenadas(JSON), clusters(JSON),
                     semente, calculado_em
bib_analises         id, project_id, pergunta, especificacao(JSON),
                     criada_por, criada_em
```

Migração Alembic, como tudo desde o doc 41 Fase 0.

**Sobre `bib_references` e escala:** 1,3 milhão de linhas em SQLite é
confortável com os dois índices, mas o acoplamento bibliográfico é uma
auto-junção que cresce com o quadrado do corpus. A regra é a mesma da contagem
em texto: **redes de citação se calculam sobre instantâneo, e a interface
recusa montar acoplamento sobre corpus acima de um teto configurável (padrão
5.000 documentos)**, explicando por quê e sugerindo restringir o escopo.
Recusar com explicação é melhor que travar o aplicativo.

---

## 13. Contratos de API

Sob `/api/v1/projects/{project_id}/bibliometria`, com a mesma dependência de
titularidade do router de insights.

| Método | Rota | Papel |
|---|---|---|
| `POST` | `/instantaneos` | Cria instantâneo a partir de um escopo |
| `GET` | `/instantaneos` | Lista, com estado de conferência do hash (§3.3) |
| `GET` | `/instantaneos/{id}/conferir` | Recomputa e compara |
| `POST` | `/enriquecimento` | Inicia rodada (202 + WebSocket) |
| `GET` | `/enriquecimento/situacao` | Progresso, retomável |
| `GET` | `/indicadores?instantaneo={id}&nivel=` | Catálogo do §7 |
| `POST` | `/instrumentos` · `PUT /{id}` · `POST /{id}/aprovar` | Ciclo do §6.1 |
| `POST` | `/instrumentos/sugerir-lexico` | IA propõe; devolve **rascunho**, nunca número |
| `POST` | `/instrumentos/{id}/medir` | Executa sobre um instantâneo |
| `GET` | `/medidas/{id}/ocorrencias` | Evidência paginada (§6.6) |
| `POST` | `/instrumentos/{id}/conferencia` | Amostra para precisão (§6.7) |
| `POST` | `/grafos` · `GET /grafos/{id}` | §8 |
| `POST` | `/analises/interpretar` | Pergunta → especificação (§9) |
| `POST` | `/analises/executar` | Especificação → número |
| `GET` | `/exportar?formato=` | `xlsx` · `csv` · `graphml` · `gexf` · `json` · `md` |

Duas invariantes de contrato:

1. Toda resposta que contenha número traz `proveniencia`: `snapshot_id`,
   `corpus_hash`, `versao_do_motor`, parâmetros e denominadores.
2. `/instrumentos/sugerir-lexico` **não tem** rota irmã que já meça. A
   aprovação humana é passo separado, por construção da API, e não apenas por
   disciplina de interface.

Limite de taxa: família `ai` para `sugerir-lexico` e `interpretar`; família
`geral` para leitura de indicador. As rotas de cálculo pesado (grafo, medida)
vão para o `AsyncJobManager`, com o mesmo canal ao vivo da triagem.

---

## 14. Interface

### 14.1 Onde mora

A aba **Indicadores** existente ganha duas seções irmãs, e não uma aba nova:

```
   Indicadores
   ├── Processo         ← o que os docs 31–33 entregaram (funil, triagem, PDF)
   ├── Bibliometria     ← §7 níveis 0–2, grafos, catálogo
   └── Laboratório      ← instrumentos, estatística sob demanda, sensibilidade
```

A separação é conceitual e vale a pena: **Processo** mede o nosso trabalho,
**Bibliometria** mede a literatura, **Laboratório** é onde se constrói medida
nova. Misturá-las foi o que fez a aba atual parecer bibliometria sem ser.

### 14.2 A barra de instantâneo

Fixa no topo das duas últimas seções: qual instantâneo está aberto, quantos
documentos, quando foi congelado, e o estado da conferência de hash — verde
(idêntico), âmbar (conteúdo mudou), vermelho (conjunto mudou). Clicável para
trocar ou criar.

Sem isto o usuário não tem como saber sobre o que está olhando, que é o defeito
de origem (B-05).

### 14.3 Estados vazios que ensinam

Cada indicador indisponível diz **por que** e **o que fazer**, no lugar do
gráfico:

> **Rede de cocitação — indisponível**
> Requer as referências citadas, que ainda não foram obtidas.
> 98,4% do acervo tem DOI; a amostragem indica ~92% de cobertura no OpenAlex.
> **[Enriquecer agora]** — cerca de 1.700 requisições, em segundo plano.

O doc 32 §5.4 já exigia estado vazio explicativo; aqui ele vira o principal
canal de ensino da funcionalidade.

### 14.4 Proveniência em toda figura

Rodapé discreto e sempre presente, e é ele que sai junto na exportação:

> *Instantâneo `snp_a91f` · 51 documentos · congelado 31/08/2026 14:22 ·
> tesauro v3 · força de associação · Louvain res. 1,0 semente 42 ·
> layout FR 200 it. · motor v1.0.0*

### 14.5 Tokens e acessibilidade

Sem exceção ao doc 24: cores por `--color-*`, espaçamento por `--space-*`. O
grafo em Canvas lê as variáveis CSS computadas para respeitar tema claro e
escuro — e não pode ser o único caminho para a informação: toda rede tem uma
**tabela equivalente** (nós, grau, força, agrupamento), navegável por teclado e
por leitor de tela. Um grafo é uma imagem; a tabela é o dado.

---

## 15. Fora de escopo, e por quê

| Item | Razão |
|---|---|
| Indicadores normalizados por campo (MNCS, PP top 10%) | Exigem universo de referência completo por campo e ano; errar a normalização é pior que não normalizar |
| Métricas de periódico para julgar artigo | DORA e Manifesto de Leiden; é uso que a área classifica como incorreto |
| Altmetria | Fonte instável, cobertura irregular em português, valor de evidência disputado |
| Scopus e Web of Science como fonte | Exigem assinatura e licença que proíbe redistribuir o derivado — inviabiliza a exportação auditável do §13 |
| Modelagem de tópicos (LDA/BERTopic) | Não determinística e difícil de auditar; o agrupamento do §8.3 cobre a necessidade com reprodutibilidade |
| Predição de tendência | Sai de medir e entra em prever; nada no ambiente sustentaria o erro |

A lista existe para que estas ausências sejam lidas como decisão, e não como
atraso.

---

## 16. Referências

**Diretrizes e princípios**

- Montazeri, A. et al. (2023). Preliminary guideline for reporting bibliometric
  reviews of the biomedical literature (BIBLIO). *Systematic Reviews*, 12:239.
  [systematicreviewsjournal.biomedcentral.com](https://systematicreviewsjournal.biomedcentral.com/articles/10.1186/s13643-023-02410-2)
  · [checklist na EQUATOR](https://www.equator-network.org/wp-content/uploads/2024/01/BIBLIO-Checklist.pdf)
- Hicks, D., Wouters, P., Waltman, L., de Rijcke, S. & Rafols, I. (2015). The
  Leiden Manifesto for research metrics. *Nature*, 520, 429–431.
- DORA — San Francisco Declaration on Research Assessment (2012).
- Wilsdon, J. et al. (2015). *The Metric Tide*.

**Método bibliométrico**

- Donthu, N. et al. (2021). How to conduct a bibliometric analysis. *Journal of
  Business Research*, 133, 285–296.
- Zupic, I. & Čater, T. (2015). Bibliometric methods in management and
  organization. *Organizational Research Methods*, 18(3), 429–472.
- Aria, M. & Cuccurullo, C. (2017). bibliometrix. *Journal of Informetrics*,
  11(4), 959–975.
- Moed, H. F. (2005). *Citation Analysis in Research Evaluation*.
- Waltman, L. (2016). A review of the literature on citation impact indicators.
  *Journal of Informetrics*, 10(2), 365–391.

**Indicadores e leis**

- Lotka, A. J. (1926); Bradford, S. C. (1934); Price, D. J. de S. (1963).
- Hirsch, J. E. (2005). *PNAS*, 102(46), 16569–16572.
- Clauset, A., Shalizi, C. R. & Newman, M. E. J. (2009). Power-law
  distributions in empirical data. *SIAM Review*, 51(4), 661–703.
- Subramanyam, K. (1983). Bibliometric studies of research collaboration.

**Redes e mapeamento**

- Small, H. (1973). Co-citation in the scientific literature. *JASIS*, 24(4).
- Kessler, M. M. (1963). Bibliographic coupling between scientific papers.
  *American Documentation*, 14(1).
- Callon, M., Courtial, J. P. & Laville, F. (1991). Co-word analysis.
  *Scientometrics*, 22(1), 155–205.
- Cobo, M. J. et al. (2011). SciMAT. *JASIST*, 62(7).
- van Eck, N. J. & Waltman, L. (2009). How to normalize cooccurrence data.
  *JASIST*, 60(8), 1635–1651.
- van Eck, N. J. & Waltman, L. (2010). Software survey: VOSviewer.
  *Scientometrics*, 84(2), 523–538.
- Blondel, V. D. et al. (2008). Fast unfolding of communities in large
  networks. *J. Stat. Mech.*
- Traag, V. A., Waltman, L. & van Eck, N. J. (2019). From Louvain to Leiden.
  *Scientific Reports*, 9:5233.
- Kleinberg, J. (2003). Bursty and hierarchical structure in streams.
  *Data Mining and Knowledge Discovery*, 7(4).
- Hummon, N. P. & Doreian, P. (1989). Connectivity in a citation network.
  *Social Networks*, 11(1).
- Marx, W. et al. (2014). Detecting the historical roots of research fields by
  RPYS. *JASIST*, 65(4).

**Fontes de dados**

- Priem, J., Piwowar, H. & Orr, R. (2022). OpenAlex: a fully-open index of
  scholarly works. arXiv:2205.01833.
- Gusenbauer, M. & Haddaway, N. R. (2020). Which academic search systems are
  suitable for systematic reviews? *Research Synthesis Methods*, 11(2).
