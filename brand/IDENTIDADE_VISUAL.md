# Revsist — Identidade Visual

Manual da marca do **Revsist — Revisão Sistemática Assistida por Computador**.
Este documento é normativo: descreve o que a marca é, como ela é construída e
onde ela aparece. Toda arte é derivada de uma única fonte de verdade,
[`generate_brand_assets.py`](generate_brand_assets.py) — nada é desenhado à mão
fora dele.

---

## 1. O símbolo — monograma "R-Lupa"

O símbolo é a letra **R** de *Revisão* — e, desde a mudança de nome, também o R de *Revsist*, construída com um traço monolinear em
que **o laço da letra é a lente de uma lupa** e **a perna diagonal é o cabo**.

A escolha não é decorativa. O Revsist existe para uma tarefa específica: procurar,
filtrar e examinar literatura científica com rigor. A lupa é o gesto dessa
tarefa; o R é o nome. Fundir os dois em um traço só significa que a marca diz o
que o produto faz sem precisar de uma segunda camada de ilustração.

### 1.1 Construção geométrica

Grade de **80 × 100**, traço **14**, três primitivas e quatro pontos de
controle inteiros:

| Elemento | Definição |
|---|---|
| **Haste** | Segmento vertical em `x = 7`, de `y = 7` até a linha-base `y = 93`. |
| **Lente** | Circunferência de centro `(32, 32)` e raio `25`. |
| **Cabo** | O raio da lente prolongado até `(73, 93)`. |

Traço monolinear de espessura 14, com pontas e junções arredondadas.

```
M 7 7 V 93                      ← haste
circle cx=32 cy=32 r=25         ← lente
M 45.946 52.749 L 73 93         ← cabo (radial)
```

### 1.2 Por que essas coordenadas

Duas junções do desenho são exatas por construção, não por ajuste manual:

- **Haste × lente.** A haste é tangente à lente, e a tangência acontece sobre a
  *linha-de-centro* de ambos os traços (`32 − 25 = 7`). A banda esquerda do anel
  coincide, portanto, com a banda da haste: as duas formas se fundem em um traço
  contínuo, sem emenda visível nem sobreposição a corrigir.
- **Lente × cabo.** O cabo é o próprio raio da lente prolongado, e não uma reta
  qualquer encostada nela. Por partir do centro, cruza o anel perpendicularmente
  à sua curvatura — a junção também é perfeita.

Consequência direta: a caixa de tinta resultante é **exatamente 0..80 × 0..100**.

- Proporção **4:5**, a mesma de um "R" de grotesca geométrica — é o que sustenta
  a leitura da letra.
- O laço ocupa **64%** da altura-de-caixa e a contra-forma (o furo da lente)
  **36%** — aberta o bastante para a lupa continuar legível a 16 px.
- O ângulo do cabo (**≈ 56°**) é uma *consequência* dos pontos de controle, não
  um parâmetro. Mais raso, a perna estoura a largura e o R vira um "p"; mais
  íngreme, o cabo deixa de parecer uma lupa.

### 1.3 Área de proteção e tamanho mínimo

- **Área de proteção:** uma espessura de traço (14 u, ou 17,5% da largura da
  marca) livre em todos os lados.
- **Tamanho mínimo:** **16 px** para o símbolo isolado; **20 px** quando
  acompanhado do logotipo.
- **Nunca:** reproporcionar a lente, mudar o ângulo do cabo, aplicar contorno,
  sombra, gradiente sobre o traço, ou girar a marca.

---

## 2. Cor

A marca **não tem cor própria fixa dentro do aplicativo**. Ela é pigmentada
pelos tokens do design system, e por isso acompanha automaticamente as **13
paletas** do Revsist.

| Parte | Origem da cor |
|---|---|
| Haste e lente | `currentColor` — a cor de texto da superfície |
| Cabo da lupa | `--rsac-accent` — resolvido por tom (abaixo) |

### 2.1 Os três tons

| Tom | Onde | Acento |
|---|---|---|
| `auto` | Superfícies de conteúdo | `--color-accent` |
| `brand` | Chrome escuro (barra de título, sidebar, splash) | `--sunlit-clay`, misturado com a cor de texto do chrome |
| `mono` | Alto contraste, impressão, favicon monocromático | `currentColor` |

O tom `brand` não usa `--color-accent` por um motivo concreto: em
`platinum-dusk`, `--color-accent` e `--black-forest` são **a mesma cor**
(`#274c77`), e o cabo desapareceria no fundo. Partindo de `--sunlit-clay` e
misturando 28% da cor de texto do chrome, o acento fica legível também nos temas
de acento escuro, como `lava-steel` (`--sunlit-clay: #c1121f`).

### 2.2 Paleta-mãe (assets estáticos)

Ícones de arquivo (`.ico`, `.icns`, `.png`, `.bmp`) não podem seguir o tema do
usuário — são binários. Eles usam a paleta **Organic Earth**, a paleta padrão do
app:

| Token | Hex | Uso no ícone |
|---|---|---|
| Forest Lift | `#3d5324` | Topo do gradiente do contêiner |
| Forest Deep | `#171f0d` | Base do gradiente |
| Black Forest | `#283618` | Texto sobre o selo |
| Cornsilk | `#fefae0` | Haste e lente |
| Sunlit Clay | `#dda15e` | Cabo da lupa e selo BETA |
| Olive Leaf | `#606c38` | Filetes e texto de apoio |
| Copperwood | `#bc6c25` | Acento da assinatura em fundo claro |

---

## 3. Logotipo e assinatura

O logotipo é composto em **JetBrains Mono Bold** — a mesma `--font-mono` do
design system, o que mantém a assinatura coerente com as etiquetas, versões e
identificadores exibidos na interface.

Nos assets estáticos os contornos são **vetorizados** a partir de
[`wordmark_glyphs.json`](wordmark_glyphs.json), extraído uma única vez da fonte
(licença SIL OFL 1.1). Assim, o resultado não depende de nenhuma fonte instalada
na máquina que gera os arquivos.

**Ordem da assinatura:** símbolo → `REVSIST` → selo `BETA`, com `V2` na
segunda linha, alinhado à esquerda do logotipo.

Variantes disponíveis: `sm` (22 px), `md` (34 px) e `lg` (56 px) de altura de
símbolo.

---

## 4. Selo BETA

O Revsist está em desenvolvimento, e o selo comunica isso de forma permanente
enquanto durar esse estágio.

Segue a linguagem de **etiqueta de engenharia** do design system — mono,
versalete, tracking largo, cantos cirúrgicos (`--radius-xs`) — e não a pílula
arredondada de app mobile. É sempre uma etiqueta **contornada com preenchimento
translúcido** (14% da própria cor), o que a mantém legível sobre qualquer um dos
13 fundos sem precisar de exceções por tema.

**Ajuste óptico nos ícones de arquivo:** o selo aparece a partir de **96 px**
(`BETA_MIN_PX`). Abaixo disso ele viraria uma mancha, e uma mancha comunica
menos que a ausência dela: o selo é suprimido e o monograma cresce de 54,5%
para 64% do lado do ícone. É por isso que o `.ico` guarda **arte diferente por
resolução**, em vez de um único bitmap reescalado — nos tamanhos que o Windows
mais usa (32 px na barra de tarefas, 48 px no atalho) o que se vê é o
monograma limpo; o selo reaparece nas visualizações grandes do Explorer.

Quando o produto sair de beta, remova o selo em três lugares: `RsacLockup`,
`Sidebar`/`TopRibbonBar`/`StatusBar`, e o parâmetro `beta` de `app_icon()`.

---

## 5. Onde a marca aparece

### No aplicativo em execução

| Local | Elemento |
|---|---|
| Splash de inicialização | Monograma + `Revsist` + selo, antes mesmo do React montar |
| Barra de título (ribbon) | Monograma 19 px, tom `brand`, `Revsist v2` + selo |
| Sidebar | Monograma 24 px, tom `brand`, `Revsist v2` + selo |
| Barra de status | Monograma 12 px, tom `auto`, `Revsist` + selo |
| Configurações → Aparência | Assinatura `lg` demonstrando a re-pigmentação pelo tema |
| Aba do navegador / dev | `favicon.svg` |
| Janela (Linux e dev) | `resources/icon.png` |

### Nos artefatos de distribuição

| Arquivo | Uso |
|---|---|
| `frontend/build/icon.ico` | Ícone do `.exe`, atalhos, barra de tarefas, Explorer, instalador e desinstalador |
| `frontend/build/icon.icns` | Bundle macOS |
| `frontend/build/icon.png` | AppImage / Linux e ícone da janela |
| `frontend/build/installerHeaderIcon.ico` | Ícone da janela do instalador (16/32/48) |
| `frontend/build/installerHeader.bmp` | Faixa superior do NSIS (150 × 57) |
| `frontend/build/installerSidebar.bmp` | Painel de boas-vindas e de desinstalação (164 × 314) |

O instalador e o desinstalador **apontam para os mesmos arquivos** no
`electron-builder.yml` (`installerIcon`/`uninstallerIcon` → `icon.ico`;
`uninstallerSidebar` → `installerSidebar.bmp`). Arte idêntica duplicada em
disco só engordaria o repositório.

---

## 6. Regenerar os assets

```bash
pip install cairosvg pillow
python3 brand/generate_brand_assets.py
```

O script reescreve `brand/svg/`, `frontend/build/`, `frontend/resources/` e
`frontend/public/favicon.svg`. Os binários resultantes **são versionados** —
`.gitignore` abre exceção explícita para `frontend/build/`, porque são
`buildResources` do electron-builder e precisam existir no clone para o
empacotamento funcionar.

### Alterou a geometria da marca?

A geometria vive em **dois** lugares que precisam permanecer idênticos:

1. `brand/generate_brand_assets.py` — bloco `GEOMETRIA CANÔNICA DO MONOGRAMA`
2. `frontend/src/components/brand/RsacMark.tsx` — os `<path>` do componente

E, como a splash roda antes do React, também em:

3. `frontend/index.html` — o SVG dentro de `#boot-splash`

Depois de qualquer alteração, rode o gerador novamente e confira o resultado a
**16, 24, 32 e 48 px** antes de dar o commit: é nesses tamanhos que erros de
proporção aparecem primeiro.

---

## O nome: de Revsist para Revsist

O produto passou a se chamar **Revsist** quando o domínio `revsist.com` foi
registrado. A identidade visual **não** foi refeita: o monograma continua sendo
o "R" construído como lupa, e a leitura só ficou mais direta — antes era o R de
*Revisão*, agora é também a inicial do próprio nome. O que mudou foi uma
palavra, e ela vive numa constante única (`WORDMARK`, em
[`generate_brand_assets.py`](generate_brand_assets.py)); antes estava escrita à
mão em cinco lugares.

A troca de quatro para sete letras teve uma consequência concreta: na faixa
superior do instalador, que tem largura fixa de 150 px, o logotipo empurrou o
selo `BETA` para fora da borda. O `installer_header` passou a calcular o corpo
do texto a partir do espaço que sobra — marca, respiro, palavra, selo e margem
—, de modo que a próxima mudança de nome não quebre o layout de novo.

### O que **não** foi renomeado, e por quê

A renomeação alcançou o que as pessoas veem. Não alcançou os identificadores
técnicos, e isso é deliberado:

| Identificador | Onde | Por que fica |
|---|---|---|
| `RSAC_` | prefixo das variáveis de ambiente | Trocar invalidaria todo `.env` existente e cada linha de documentação de implantação, em troca de nada visível |
| `Revsist` | `app_name`, que alimenta `platformdirs.user_data_dir` | **É o caminho da pasta de dados.** Trocar faria quem já tem o app instalado abrir o programa e não encontrar o próprio acervo |
| `rsac_session` | nome do cookie | Trocar desloga todo mundo uma vez, sem nenhum ganho |
| `rsac-*` | classes e variáveis CSS, nomes de componente, arquivos de `brand/svg/` | São identificadores internos; renomeá-los é churn com risco de quebrar referências que não se pode testar aqui (build do Windows) |

A regra que organiza tudo isso: **prosa muda, identificador fica**.
