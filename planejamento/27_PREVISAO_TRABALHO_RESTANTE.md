# 27 — Previsão do Trabalho Restante

> Levantado em 18/08/2026 medindo o código, não estimando de memória. Cada
> número abaixo tem origem declarada; onde a origem é julgamento, está dito.
>
> Este documento existe porque os docs 25 e 26 descrevem *o que* fazer, e a
> pergunta em aberto passou a ser *quanto falta* e *em que ordem*.

---

## 27.1 Onde o plano está

Das sete fases do doc 25:

| Fase | Situação | O que falta |
|:-:|---|---|
| 1 — Tokens | ✅ | — |
| 2 — Componentes | ✅ biblioteca · 🟡 adoção | `<Tag>`, `<Field>`, `<Panel>`, `<Tabs>` não existem |
| 3 — Proporção e comando | 🟡 | ribbon não comprimido; Protocolo em 29% |
| 4 — Registro de comandos | ✅ | — |
| 5 — Acessibilidade | 🟡 | percurso por teclado (manual); ordem de tabulação |
| 6 — Conteúdo por diretriz | ✅ | — |
| 7 — Higiene e refino | 🟡 | decomposição dos arquivos grandes; acabamento óptico |
| doc 26 — Validação | 🟡 | 6 dos 7 scripts |

As nove regras do verificador estão fechadas em zero. O que resta **não é
dívida de token**: é estrutura de arquivo, cobertura de teste e julgamento
visual.

---

## 27.2 O orçamento de tela, medido

Critério da Fase 3: moldura ≤ 25% a 1440 × 900. Medição de 18/08:

| Tela | Moldura | % | Composição |
|---|:---:|:---:|---|
| Painel, Projetos, Config. | 217 px | **24%** | ribbon 145 · cabeçalho 44 · rodapé 28 |
| Coleta, Triagem, Extração, Exportação | 218 px | **24%** | ribbon 146 · cabeçalho 44 · rodapé 28 |
| **Protocolo** | 263 px | **29%** | ribbon 146 · cabeçalho 47 · **abas 42** · rodapé 28 |

Sete das oito já passam. Só o Protocolo excede, e por causa da faixa de abas do
Estúdio — que é navegação legítima, não desperdício.

**O gargalo é o ribbon: 146 px em todas as oito.**

> **Correção de 18/08.** Ao executar, li errado a tarefa 3.4 deste documento.
> Ela pede o **toolstrip** ≤ 96 px, não o ribbon inteiro — e o toolstrip, que
> media 118 px no diagnóstico (doc 23 § 23.4), já está em **80 px**. O critério
> de altura estava cumprido antes de eu começar.
>
> O que restava de 3.4 era a outra metade da linha: "estado de recolhimento
> lembrado entre sessões". Recolhido, o ribbon vai de 146 px para 66 px e o
> Protocolo cai de 29% para **20%**. Feito.
>
> Com precisão sobre o que isso fecha: **no estado padrão o Protocolo continua
> em 29%**; os 20% valem com a faixa recolhida, escolha que agora dura. Sete
> das oito telas passam por si; a oitava passa se a pessoa quiser. Deixar o
> ribbon recolhido POR PADRÃO no Protocolo fecharia o número, e seria pior:
> esconder a barra de comando sem que ninguém tenha pedido é decidir pelo
> outro. O que sobra para baixar os 29% por conta própria é a faixa de abas do
> Estúdio (42 px), e ela é navegação — cortar ali custa orientação, não
> desperdício.

---

## 27.3 Os arquivos grandes, e por que são grandes

Critério da Fase 7: nenhum arquivo de página acima de ~400 linhas.

| Arquivo | Linhas | Excede em |
|---|:---:|:---:|
| `ProtocolPage.tsx` | 3042 | 7,6× |
| `ScreeningPage.tsx` | 1548 | 3,9× |
| `SettingsPage.tsx` | 1377 | 3,4× |
| `ExtractionPage.tsx` | 1226 | 3,1× |
| `TopRibbonBar.tsx` | 1025 | (não é página, mas pesa) |

O Protocolo não é grande por acidente. Ele tem **18 cartões de campo**, e os 18
compartilham a mesma anatomia:

| Parte | Presente em |
|---|:---:|
| etiqueta de item + seção | 18/18 |
| título com ações | 18/18 |
| `<AIAssistButton>` | 18/18 |
| ajuda por diretriz (`section-help`) | 18/18 |
| botão de guia estruturado | 17/18 |
| caixa de guia | 17/18 |
| inserção de modelo | 15/18 |

Esses 18 blocos somam **1755 linhas — 58% do arquivo**, com mediana de 88
linhas cada. Não é código diferente repetido: é o mesmo código com dados
diferentes.

> **Consequência para o plano**: a decomposição do Protocolo não é "quebrar em
> sete abas". É extrair **um** componente `<CampoDoProtocolo>` e passar os 18
> conjuntos de dados. As sete abas viram arquivos depois, e aí já são pequenas.

O ribbon tem estrutura análoga: 8 blocos por aba, de 80 a 149 linhas, com 95
ocorrências de `ribbon-group`.

---

## 27.4 Ordem proposta

A ordem não é por tamanho: é por **quanto cada item destrava dos outros**.

### 1º — `<CampoDoProtocolo>` e `<GrupoDoRibbon>`

Os dois maiores arquivos são 58% e ~80% repetição de uma estrutura só. Extrair
o componente resolve simultaneamente:

- o critério de 400 linhas da Fase 7 (a maior parte dele);
- a tarefa 2.x de `<Field>`, que é exatamente essa anatomia;
- a próxima mudança de campo do protocolo, que hoje custa 18 edições.

**Como**: escrever o componente a partir do bloco mediano (88 linhas), migrar
**um** cartão, comparar a captura, e só então converter os 17 restantes em lote
com o mesmo conversor por profundidade de aninhamento usado no `<Card>`. Migrar
por aba inteira, comparando a cada aba — nunca cartão avulso.

**Risco**: médio. Os 18 blocos não são idênticos (67 a 224 linhas); os
extremos vão precisar de `children` ou de props opcionais. O bloco de 224
linhas provavelmente não cabe e fica como está — e isso é aceitável.

### 2º — Ribbon: recolhimento persistente e `<GrupoDoRibbon>` ✅

Feito em 18/08. Duas coisas, com pesos bem diferentes do que eu previa aqui:

- **Recolhimento persistido** — era a metade de 3.4 que faltava, e é o que
  fecha o critério de 25% no Protocolo (29% → 20%). Efeito grande, mudança
  pequena.
- **`<GrupoDoRibbon>`** — 29 grupos convertidos, mas o ganho foi de **83
  linhas**, não das centenas que a proporção "55% do arquivo" sugeria. A
  previsão original justificava a extração dizendo que "mexer na altura vira
  mudar um componente, não 95 lugares" — o que estava errado: altura é CSS, e
  já era um lugar só. O ganho real é outro e mais modesto: a casca do grupo
  não pode mais divergir entre abas, e o rótulo embaixo — padrão que a barra
  herda do Office — deixa de depender de cada call site lembrar dele.

Inclui persistir o estado de recolhimento — hoje `ribbonCollapsed` é
`useState` local e se perde a cada troca de rota.

### 3º — `<Tabs>` do Radix (2.8 / 5.3)

Cinco arquivos têm UI de aba artesanal: ribbon, Protocolo, Coleta, Triagem,
Extração. O Protocolo e o ribbon já têm `role="tab"` e `aria-selected` à mão; o
que falta em todos é **navegação por setas**, que é o que a diretriz WAI-ARIA
exige e nenhum implementa.

Fazer **depois** do 1º e do 2º: os dois maiores consumidores de abas são
justamente os arquivos que serão reestruturados.

### 4º — Scripts do doc 26

Seis faltam. Três deles já existem como scripts de trabalho no meu diretório de
apoio e precisam apenas ser formalizados no repositório:

| Script | Situação |
|---|---|
| `a11y-audit.mjs` | **existe** como ferramenta de apoio (axe-core, 8 telas × 13 paletas) |
| `layout-budget.mjs` | **existe** — é a medição de § 27.2 |
| `visual-check.mjs` | **existe** — é a comparação de capturas usada a cada commit |
| `seed-fixture.mjs` | a escrever — projeto de teste com acervo, hoje feito à mão |
| `visual-baseline.mjs` | a escrever — depende da fixture |
| `contrast-check.mjs` | a escrever — parte da lógica está em `derivar-tokens-de-contraste.py` |

**Por que não antes**: os três que existem foram usados em toda esta rodada e
funcionam. Formalizá-los é trabalho de empacotamento, não de descoberta —
rende mais depois que a estrutura parar de mudar.

### 5º — Percurso por teclado e acabamento óptico

Os dois pedem olho humano, não script:

- **§ 5.11** — percorrer criar projeto → protocolo → coleta → triagem →
  extração → exportar **só com teclado**. O `axe-core` não cobre isso: ele vê
  marcação, não ordem de foco vivida.
- **§ 7.10** — alinhamento óptico, ritmo, alinhamento de ícones.

Ficam por último porque julgam o resultado final; feitos antes, seriam
refeitos.

---

## 27.5 O que eu deixaria de fora

Registrado para não virar dívida silenciosa:

| Item | Por quê |
|---|---|
| `.queue-paper-card` no `<Card>` | Item de tamanho fixo em esteira de rolagem; passar pelo componente cria dependência de ordem de importação do CSS por ganho nenhum (doc 24 § 24.7.1) |
| Bloco de 224 linhas do Protocolo | Se não couber no `<CampoDoProtocolo>`, forçar encaixe piora os outros 17 |
| `SettingsPage` abaixo de 400 linhas | 1377 linhas, mas são 13 paletas + 4 provedores + portabilidade declarados como dados. Decompor por seção chega a ~600; o resto é conteúdo, não estrutura |

---

## 27.6 Sequência, em uma frase cada

1. Extrair `<CampoDoProtocolo>` — derruba 58% do maior arquivo e entrega o `<Field>` da Fase 2.
2. Extrair `<GrupoDoRibbon>` e comprimir o ribbon para ≤ 96 px — fecha o critério de 25% nas oito telas.
3. `<Tabs>` do Radix nas cinco UIs de aba — entrega a navegação por setas, que hoje não existe em nenhuma.
4. Formalizar os três scripts que já existem; escrever a fixture e os dois que dependem dela.
5. Percurso por teclado e passada de acabamento óptico, com o resultado já estável.

---

## 27.7 Como saber que acabou

Os portões do doc 26 § 26.8, com o estado de hoje:

| Fase | Portão | Hoje |
|:-:|---|---|
| 1 | `lint:tokens --strict` limpo | ✅ |
| 2 | Galeria nas 13 paletas · teclado na galeria | ⬜ galeria não existe |
| 3 | `test:layout` ≤ 25% nas 8 telas | 🟡 7/8 no estado padrão · 8/8 com a faixa recolhida (Protocolo 29% → 20%) |
| 4 | R-3 limpo · roteiro R4 | ✅ automatizado · ⬜ roteiro |
| 5 | `test:a11y` sem violação séria · contraste nas 13 paletas | ✅ 104/104 · ⬜ roteiro R1 |
| 6 | R-7 limpo · roteiro R5 nas 11 metodologias | ✅ automatizado · ⬜ roteiro |
| 7 | nenhuma página > ~400 linhas | ⬜ quatro acima |

Três portões dependem de **roteiro manual aprovado por pessoa**, não de script:
R1 (teclado), R4 (comandos) e R5 (as 11 metodologias). Nenhuma quantidade de
automação os fecha — e o doc 26 já dizia isso.
