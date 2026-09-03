# Documento 51 · Plano de remodelagem da landing e criação do blog
## Explicar o que o app faz, com print do app ao lado — e um blog que rende busca orgânica

> **O que muda em uma frase:** a landing deixa de *argumentar* que o Revsist é
> rigoroso e passa a *mostrar* o que ele faz, tela por tela, em texto curto e
> literal; e ganha `/blog`, um diretório estático de textos sobre revisão
> sistemática construído para ser indexado.

**Documentos que este plano obedece e não pode contrariar:**
doc 40 §40.8 (especificação da landing), doc 41 Fase 5 (execução), doc 42
(marca, voz e tom). Onde este plano diverge do doc 40, a divergência está
declarada em §51.2 — não há divergência silenciosa.

**Framework de execução:** este documento é a aplicação dos *5 Pilares* de
engenharia de prompt ao problema. Cada pilar vira uma seção operacional:
âncora (§51.3), fan-out de agentes (§51.5), auditoria implacável (§51.6),
loop de refinamento (§51.7), stack rígida e gatilhos de profundidade (§51.8).

---

## 51.1 Diagnóstico medido da landing atual

Números conferidos no repositório em 02/09/2026, não estimados.

| Fato | Medida | Consequência |
|---|---|---|
| `landing/index.html` | 782 linhas, 40,8 kB | Documento longo para uma página que deveria explicar rápido |
| Imagens do produto | **zero** `<img>` na página inteira | Quem chega nunca vê o app antes de entrar |
| Seções no corpo | 8 + hero, 8 links no menu | Menu comprido para uma página de um assunto só |
| Densidade retórica | a seção 01 inteira (linhas 193‑246) é argumentação sobre o custo de revisar à mão | É contexto de artigo, não explicação de produto |
| `landing.css` | 1486 linhas | Já cobre o sistema visual; falta só componente de figura |
| Fontes | `@font-face` declarado em `landing.css:25‑38`, mas `landing/public/fonts/` **não existe** | Página cai na pilha do sistema; doc 41 item 5.3 segue aberto e agora vira bloqueio de CLS |
| Rotas estáticas | 3 (`/`, `/termos`, `/privacidade`), declaradas uma a uma em `landing/vite.config.ts` | Blog com N posts não cabe nesse arranjo manual |
| Entrega | `landing/dist` montado em `/srv/landing` (`docker-compose.yml:33`), servido pelo `Caddyfile` e, em modo local, por `backend/app/main.py:411‑424` | Qualquer rota nova precisa passar nos **dois** caminhos |
| Infra de captura já pronta | `frontend/scripts/seed-fixture.mjs` (fixture determinística), `shared/rsac-fixture.mjs` (8 telas × 13 paletas), `visual-baseline.mjs` (Playwright, 1440×900) | **Não se escreve pipeline de print do zero — reaproveita-se este** |
| Ferramentas disponíveis | `playwright-core`, `axe-core`, `pixelmatch`, `pngjs` já em `frontend/package.json` | Os portões do loop (§51.7) não precisam de dependência nova |

**Leitura:** a página não está mal-feita; está mal-endereçada. Ela foi escrita
para convencer um cético do método, e o visitante médio chega antes disso —
querendo saber o que a ferramenta faz. O trabalho é de subtração e de prova
visual, não de reconstrução.

---

## 51.2 Escopo

### Entra
1. Reescrita da estrutura e do texto de `landing/index.html`.
2. Seis capturas reais do app, geradas por script determinístico e versionadas.
3. `/blog` — índice, páginas de post, RSS, sitemap automático, JSON-LD.
4. Ajuste de build, `Caddyfile` e `backend/app/main.py` para as rotas novas.
5. Auto-hospedagem de Inter e JetBrains Mono (`woff2`), pendência do doc 41 item 5.3 que vira obrigatória: sem ela, cada print entra numa página cujo texto ainda vai remexer no carregamento.

### Sai (não-escopo, declarado para ninguém "aproveitar a viagem")
- Qualquer alteração no app React ou no backend além das rotas estáticas.
- Redesenho da identidade visual — doc 42 §42.7 diz que está resolvida.
- Analytics de terceiro, banner de cookie, formulário de captura de e-mail.
- Tradução para inglês (registrar como trabalho futuro; `hreflang` fica preparado, não usado).

### Divergências deliberadas do doc 40 §40.8.3
| # | Doc 40 pedia | Este plano faz | Por quê |
|---|---|---|---|
| D1 | Seção 2 "O problema" com três números e fonte | **Removida da landing**, convertida em post do blog | É argumento longo; ocupa a segunda dobra com texto que o visitante ainda não pediu. No blog ela rende busca orgânica em vez de atrito |
| D2 | Seção 3 "O fluxo" como diagrama SVG inline | Diagrama vira **fio condutor de seis blocos com print real** | O SVG afirma o fluxo; o print prova. O SVG compacto permanece, como sumário no topo da seção |
| D3 | 8 seções | **5 seções + rodapé** | Pedido direto do dono do produto: mais simples, mais direto |
| — | — | `/blog` (não previsto no doc 40) | Requisito novo |

### Três decisões que dependem de você (recomendação já marcada)
- **DEC‑1 — Motor do blog.** (a) HTML puro por post, zero dependência, como `/termos`; **(b) ✅ recomendado:** Markdown com *front-matter* compilado no build por script próprio (`markdown-it` como devDependency). (b) custa ~150 linhas de script uma vez e depois cada post é um `.md`; (a) obriga a repetir 40 linhas de `<head>` a cada texto e convida ao erro de SEO.
- **DEC‑2 — Conversão das imagens.** `sharp` como devDependency (WebP em duas larguras, ~120 kB por imagem) **✅ recomendado**, contra JPEG puro do Playwright (sem dependência nova, cerca do dobro do peso e texto de UI borrado). Nenhuma das duas viola a regra de "zero terceiro" do doc 40 — é build-time, não chega ao navegador.
- **DEC‑3 — Destino do conteúdo removido (D1).** Vira o primeiro post do blog **✅ recomendado**, ou é descartado.

---

## 51.3 · PILAR 1 — Âncora de excelência

**A âncora não é uma página de startup.** O doc 40 §40.8.1 proíbe explicitamente
mockup 3D, gradiente vibrante, contador animado e ilustração genérica. O "gold
standard" aqui, portanto, é medido em **clareza e indexabilidade**, não em brilho.

| Benchmark | O que se copia dele | O que **não** se copia |
|---|---|---|
| **Plausible Analytics** (site e blog) | Frase inicial literal do que o produto faz; print grande logo abaixo; postura "sem terceiros" declarada; blog que traz a maior parte do tráfego | Comparações nominais com concorrente |
| **Stripe Docs** | Texto e figura lado a lado, cada figura provando a frase ao lado dela | Densidade de referência de API |
| **Linear — páginas de recurso** | Enquadramento e recorte das capturas: sempre uma tela real, cortada no que importa | Animação, vídeo em laço, paralaxe |
| **Google Search Central** (checklists) | Regra de SEO on-page verificável item a item | — |
| **Cochrane Handbook / PRISMA** | Registro sóbrio, número com fonte, honestidade sobre limite | Prolixidade |

### Critérios de paridade — o que "ficou bom" significa, em número
Nada disso é subjetivo; tudo é verificado em §51.7.

| # | Critério | Alvo |
|---|---|---|
| P1 | Teste dos 8 segundos: quem nunca ouviu falar do produto diz o que ele faz depois de ler só a primeira dobra | acerto em 5 de 5 leitores-teste (ou 5 de 5 agentes cegos) |
| P2 | Densidade de adjetivo avaliativo no corpo | ≤ 1 a cada 150 palavras; zero da lista proibida do doc 42 §42.6 |
| P3 | Toda afirmação factual tem lastro | 100 % mapeadas na tabela de proveniência (§51.9) para arquivo/linha do código ou documento |
| P4 | Comprimento | `index.html` ≤ 26 kB (hoje 40,8); corpo de texto ≤ 900 palavras |
| P5 | Prints | 6, todos de tela real semeada por fixture, nenhum mockup |
| P6 | LCP em 4G simulado / CLS | < 1,5 s / < 0,05 |
| P7 | Lighthouse (4 categorias), landing e blog | ≥ 95 |
| P8 | Requisições a terceiros | **0** |
| P9 | axe-core, severidade *serious* ou *critical* | 0 |
| P10 | Peso total da primeira visita | ≤ 950 kB, dos quais ≤ 180 kB antes do primeiro scroll |

---

## 51.4 A estrutura-alvo da página

Cinco seções. O menu passa a ter quatro itens: **Como funciona · Diretrizes · Blog · Entrar**.

### Dobra 0 — Hero
- **H1:** o que é, literal, uma linha. Direção: *"Software para conduzir revisão sistemática do protocolo à exportação."* A assinatura de marca do doc 42 ("Revisão sistemática com rastro") desce para a linha de apoio — ela funciona como assinatura, mas não responde "o que é isso" para quem chega frio.
- **Apoio, 2 linhas:** para quem é (pós-graduação, grupos de pesquisa) e a diferença que dura (bases brasileiras + registro de cada decisão).
- **CTA:** `Entrar no Revsist` + `Ver como funciona`. O selo BETA permanece.
- **Print 1 (imagem do LCP):** a tela de triagem, largura total, imediatamente abaixo do CTA. É a única imagem com carregamento imediato.
- A faixa de 4 metadados atual encolhe para 3 e sai do topo da hierarquia visual.

### Seção 1 — "Como funciona": seis blocos com print
É o corpo da página. Cada bloco tem título curto, **duas a três frases** dizendo *o que você faz ali* e *o que o app faz*, e uma figura com legenda. Sem adjetivo, sem promessa.

| # | Etapa | Print | Rota da captura | O que a frase precisa dizer |
|---|---|---|---|---|
| 1 | Protocolo | Print 2 | `/projects/:id/protocol` | Você escreve objetivo, PICO e critérios, e escolhe uma das 11 diretrizes; o protocolo fica versionado |
| 2 | Coleta | Print 3 | `/projects/:id/harvest` | Você monta a string de busca; o app consulta BDTD, SciELO, PubMed, Scopus e OpenAlex e traz os registros |
| 3 | Deduplicação | recorte do Print 3 | idem | Duplicatas são agrupadas com o critério visível; nada some sem registro |
| 4 | Triagem | Print 1 no fio + **Print 4** do registro da decisão | `/projects/:id/screening` | Você inclui ou exclui por título e resumo; a IA sugere parecer com justificativa; a decisão é sua |
| 5 | Extração | Print 5 | `/projects/:id/extraction` | Você define as perguntas de extração; a resposta vem ancorada na página do PDF |
| 6 | Síntese e exportação | Print 6 | `/projects/:id/export` | Fluxograma PRISMA gerado do banco; exportação em RIS, BibTeX, CSV e XLSX |

O SVG de seis etapas que já existe (`index.html:259`) fica como sumário no início da seção — é barato e não custa requisição.

### Seção 2 — O rastro
Uma seção, um print (**Print 4**: o registro de auditoria de uma decisão real da fixture — quem decidiu, provedor, modelo, hash do contexto) e três frases. É a prova do doc 42 §42.4. O bloco `trace-demo-card` de hoje, que é uma simulação escrita à mão em HTML, é **substituído pela captura real** — é exatamente a diferença entre afirmar e mostrar.

### Seção 3 — Diretrizes, bases e o que o app não faz
Funde três seções de hoje em uma, em lista densa (não em cartão):
- 11 diretrizes, nomeadas com versão;
- 5 bases + importação RIS/BibTeX/CSV/XLSX;
- **o que não faz:** sem meta-análise, sem GRADE, sem risco de viés, sem decisão automática sem conferência. Doc 42 §42.12 item 4 — nesse público isso compra mais confiança do que mais uma alegação.

### Seção 4 — Dados, licença e acesso
Três frases e links: onde os dados ficam, o que sai para a IA e por quê, exportação e eliminação pelo titular, licença MIT, repositório. Liga para `/privacidade` e `/termos`.

### Rodapé
O de hoje, mais o link para `/blog` e para o RSS.

---

## 51.5 · PILAR 2 — Fan-out: seis agentes especialistas

Regra que torna o paralelismo seguro: **cada arquivo tem um único dono com
permissão de escrita.** Agente que precisa mexer em arquivo alheio abre pedido
ao dono; não edita.

| Agente | Domínio | Arquivos que possui (escrita exclusiva) | Lê |
|---|---|---|---|
| **A1 · Redação e método** | Todo o texto: hero, seis blocos, rastro, limites; tabela de proveniência | `planejamento/51_ANEXO_TEXTO.md` | doc 42, código do backend para conferir cada afirmação |
| **A2 · Capturas** | Fixture, script de captura, recorte, conversão, `alt` | `frontend/scripts/capturar-telas-landing.mjs`, `frontend/scripts/shared/rsac-fixture.mjs`, `landing/src/imagens/**` | app React |
| **A3 · Estrutura e CSS** | Marcação e estilo da landing | `landing/index.html`, `landing/src/styles/landing.css`, `landing/src/scripts/landing.js` | entregas de A1 e A2 |
| **A4 · Motor do blog** | Gerador, template, índice, RSS, rotas, build | `landing/scripts/gerar-blog.mjs`, `landing/conteudo/**`, `landing/blog/**`, `landing/vite.config.ts`, `landing/package.json`, `Caddyfile`, `backend/app/main.py` | — |
| **A5 · SEO e metadados** | `<head>` de todas as páginas, JSON-LD, canonical, sitemap, robots, OG, mapa de palavra-chave, malha de links internos | `landing/public/robots.txt`, `landing/scripts/gerar-sitemap.mjs`, blocos `<head>` (por pedido a A3/A4) | tudo |
| **A6 · Verificação** | Os portões do §51.7 e o relatório do loop | `landing/scripts/verificar-landing.mjs` e auxiliares | tudo; **não corrige nada** |

### Ordem e paralelismo
```
Onda 1 (paralela):  A1 (texto) │ A2 (capturas) │ A4 (motor do blog)
Onda 2 (serial):    A3 (monta a página com o que A1 e A2 entregaram)
Onda 3 (serial):    A5 (metadados sobre a página montada e sobre o blog)
Onda 4 (loop):      A6 → auditores C1/C2 → correção pelo dono → A6 de novo
```
A2 é o caminho crítico: depende de backend e frontend no ar e de fixture semeada. Começa primeiro.

### Prompts de missão (prontos para despachar)

**A1 · Redação e método**
```
Você escreve o texto da landing do Revsist. Leia planejamento/42_PLANO_DE_MARCA.md
§42.4 e §42.6 e planejamento/40_ESPECIFICACAO_ONLINE.md §40.8.1 — as regras de voz
de lá são obrigatórias e não negociáveis.

Entregue planejamento/51_ANEXO_TEXTO.md com o texto final de cada bloco de §51.4
do doc 51, e mais uma tabela de proveniência: para CADA afirmação factual, o
arquivo:linha do código ou o documento que a sustenta. Afirmação sem lastro é
cortada, não suavizada.

Restrições duras: no máximo 900 palavras no corpo inteiro; 2 a 3 frases por
bloco; zero adjetivo avaliativo ("poderoso", "revolucionário", "simples",
"intuitivo", "completo", "robusto"); zero emoji; nenhum número de tração; nenhum
depoimento; nada que o produto não faça hoje. Cada bloco responde duas perguntas
e só elas: o que a pessoa faz nessa tela, e o que o app faz em resposta.
```

**A2 · Capturas**
```
Você produz as 6 capturas reais do app para a landing.

Reaproveite a infraestrutura existente: frontend/scripts/seed-fixture.mjs semeia
a fixture determinística e frontend/scripts/shared/rsac-fixture.mjs já abre o
Playwright e navega. NÃO escreva pipeline novo — estenda esse.

Crie frontend/scripts/capturar-telas-landing.mjs que: semeia a fixture; captura
protocolo, coleta, triagem, o registro de auditoria de uma decisão, extração e
exportação; viewport 1440×900 com DPR 2, paleta clara (a landing é clara-somente,
ver landing.js); recorta cada imagem no que a legenda promete; gera WebP em 1280
e 640 de largura (DEC-2) em landing/src/imagens/telas/ com nome estável; imprime
largura e altura de cada arquivo para o atributo do HTML.

Barreiras: nenhum dado pessoal na imagem — o usuário da fixture é "Revisora de
exemplo", com e-mail de exemplo, e você CONFERE isso olhando cada PNG antes de
converter. Nenhum tooltip, cursor ou estado de foco acidental. Nenhuma imagem
acima de 140 kB. O script tem de ser idempotente: rodar duas vezes produz bytes
equivalentes.

Entregue também planejamento/51_ANEXO_CAPTURAS.md com o texto `alt` de cada
imagem — descritivo do que a tela mostra, não "captura de tela do app".
```

**A3 · Estrutura e CSS**
```
Você monta a landing nova em landing/index.html e landing/src/styles/landing.css,
com o texto de 51_ANEXO_TEXTO.md e as imagens de landing/src/imagens/telas/.

Estrutura exata: §51.4 do doc 51. Cinco seções, menu de quatro itens. Remova as
seções que saem (a de estatísticas e as três que se fundem) — e remova o CSS
órfão junto; folha de estilo com regra morta é reprovada pelo auditor.

Componente novo: `figura-tela` — <figure> com <picture> (WebP 1280/640 via
srcset), width e height explícitos (CLS zero), loading="lazy" e decoding="async"
em todas menos a primeira, borda de 1 px na régua da paleta e <figcaption> com a
legenda. Referencie as imagens por caminho relativo a partir de src/ para o Vite
emitir em /assets com hash — é o único prefixo com cache imutável no Caddyfile.

Auto-hospede Inter e JetBrains Mono variáveis em landing/public/fonts/ (woff2):
o @font-face já existe em landing.css:25-38 e hoje aponta para arquivo
inexistente. Adicione <link rel="preload"> só para a fonte do texto.

As proibições do doc 40 §40.8.1 valem integralmente. A página tem de continuar
legível e navegável com o JavaScript desligado.
```

**A4 · Motor do blog**
```
Você constrói /blog como site estático, sem framework e sem JavaScript de
execução, dentro do projeto landing/.

1. Conteúdo: landing/conteudo/blog/<slug>.md com front-matter (titulo,
   descricao, slug, data, atualizado, autor, tags, palavra_chave_alvo, resumo).
2. Gerador: landing/scripts/gerar-blog.mjs, roda antes do vite build. Compila
   cada .md em landing/blog/<slug>/index.html a partir de um template único;
   gera landing/blog/index.html (lista, mais recente primeiro, com data e
   resumo); gera landing/public/feed.xml (RSS 2.0 válido); devolve a lista de
   rotas para o sitemap.
3. Build: landing/vite.config.ts passa a descobrir os inputs por varredura de
   **/index.html — hoje as três rotas estão escritas à mão, e isso não escala.
   Encadeie o gerador no script "build" do package.json da landing E confira que
   frontend/package.json "build:landing" continua produzindo o mesmo dist.
4. Rotas: /blog, /blog/<slug>/ e /feed.xml precisam responder pelos DOIS
   caminhos de entrega — o Caddyfile (bloco handle final, o try_files já cobre
   diretório) e backend/app/main.py:411-424. Confira os dois; não presuma.
5. Cabeçalho e rodapé do blog são os mesmos da landing, mesma folha de estilo,
   mesmo CSP. Nenhuma fonte, script ou imagem de fora da origem.

Escreva um post de exemplo completo para validar o motor de ponta a ponta.
```

**A5 · SEO e metadados**
```
Você responde pela indexabilidade. Sobre a landing montada e o blog gerado:

- <head> de cada página: title único de até 60 caracteres, description de 140 a
  160, canonical absoluto em https://revsist.com, OG e Twitter completos, pt-BR.
- JSON-LD: SoftwareApplication na landing (o de hoje já existe, atualize), Blog
  no índice, BlogPosting em cada post (headline, description, datePublished,
  dateModified, author, inLanguage, mainEntityOfPage) e BreadcrumbList nos posts.
- sitemap.xml passa a ser gerado (landing/scripts/gerar-sitemap.mjs), com lastmod
  vindo do front-matter — o arquivo estático de hoje sai do public/.
- robots.txt: liberar /blog explicitamente, manter /app e /api bloqueados,
  apontar o sitemap.
- Malha interna: cada post liga a pelo menos dois outros e a uma seção nomeada da
  landing; a landing liga ao blog em dois lugares (menu e rodapé).
- Mapa de palavra-chave em planejamento/51_ANEXO_SEO.md: para cada post da pauta,
  a expressão-alvo em português, a intenção de busca e o título proposto.

Regra: nenhuma técnica de manipulação. Sem texto escondido, sem repetição
artificial de palavra-chave, sem página-satélite. O conteúdo é o ativo; a
marcação só o descreve.
```

**A6 · Verificação** — a missão é o §51.7 inteiro: escrever os portões, rodá-los e reprovar com endereço. Não corrige nada.

---

## 51.6 · PILAR 3 — Os dois críticos implacáveis

Auditor não é revisor gentil. Ele **reprova por padrão** e só aprova o que
conseguir verificar sozinho. Nenhum dos dois pode ser o mesmo agente que
escreveu o que está auditando.

### C1 · Auditor metodológico e editorial
Persona: *metodologista sênior de revisão sistemática que já rejeitou artigo por
alegação sem lastro, e edita texto cortando palavra.*

Reprova, sem negociar:
- qualquer afirmação sobre o produto que ele não consiga confirmar abrindo o código;
- adjetivo avaliativo, superlativo, ou qualquer palavra da coluna "Evitar" do doc 42 §42.6;
- promessa proibida pelo doc 42 §42.4 (IA que decide sozinha, meta-análise, GRADE, risco de viés, número de tração);
- bloco que não responda "o que a pessoa faz" e "o que o app faz";
- legenda que descreva algo que a imagem não mostra;
- texto que só seria verdade depois de alguma fase futura ficar pronta.

Formato do veredito: `REPROVADO — arquivo:linha — o que está errado — o que provaria o contrário`. Sem elogio, sem resumo, sem "no geral ficou bom".

### C2 · Auditor de engenharia, desempenho e acessibilidade
Persona: *engenheiro de plataforma que trata cada kilobyte e cada violação de
axe como defeito de produção.*

Reprova:
- `<img>` sem `alt`, sem `width`/`height`, ou sem `loading="lazy"` fora da primeira dobra;
- CSS órfão deixado por seção removida;
- qualquer requisição para fora da origem — verificado interceptando a rede, não lendo o código;
- CSP afrouxado, `style` inline novo, script inline novo;
- rota que responde no Caddy e falha no backend, ou o contrário;
- página que quebra com JavaScript desligado;
- imagem acima do orçamento, ou soma acima de 950 kB;
- `dist` que não reproduz — dois builds seguidos têm de dar o mesmo conteúdo.

**Regra anti-complacência para os dois:** o veredito precisa citar o comando ou o
arquivo que o sustenta. "Parece bom" não é veredito. Auditor que aprova tudo na
primeira rodada é ele próprio suspeito — na dúvida, o dono do produto relê a rodada.

---

## 51.7 · PILAR 4 — O loop de revisão

### 51.7.1 Os portões
`node landing/scripts/verificar-landing.mjs` executa G0–G9 em sequência e imprime
uma tabela com um `✔`/`✘` por portão. G10 e G11 são julgamento, e rodam com agente.

| # | Portão | Como se verifica | Aprova quando | Dono do conserto |
|---|---|---|---|---|
| **G0** | Build | `npm --prefix landing run build`, duas vezes | Sai sem erro; toda página esperada existe em `dist`; a segunda execução é idêntica | A4 |
| **G1** | Rotas e links | Varre o `dist`, resolve todo `href` interno e toda âncora | Zero link quebrado, zero âncora órfã; menu igual em todas as páginas | A3/A4 |
| **G2** | Entrega dupla | Sobe backend e Caddy; requisita `/`, `/termos`, `/privacidade`, `/blog`, `/blog/<slug>/`, `/feed.xml`, `/sitemap.xml`, `/robots.txt`, `/app` | 200 em todas, nos dois caminhos; `/app` intacto | A4 |
| **G3** | Imagens | Existência, peso, dimensão, `alt`, `width`/`height`, `lazy`, `srcset` | Todos os itens; nenhuma acima de 140 kB | A2/A3 |
| **G4** | Orçamento de bytes | Playwright mede a transferência da primeira visita | ≤ 950 kB no total, ≤ 180 kB antes do primeiro scroll | A3 |
| **G5** | Zero terceiro | Playwright intercepta as requisições e compara o host de cada uma com a origem | Nenhuma requisição externa, em nenhuma página | A3/A4 |
| **G6** | Acessibilidade | `axe-core` em `/`, `/blog`, um post e `/termos` (reaproveita `a11y-audit.mjs`) | Zero *serious*/*critical*; foco visível; `skip-link` funciona; só com teclado se chega ao CTA | A3 |
| **G7** | Desempenho | Lighthouse, ou LCP/CLS medidos por Playwright em 4G simulado | ≥ 95 nas 4 categorias; LCP < 1,5 s; CLS < 0,05 | A3 |
| **G8** | Sem JavaScript e responsivo | Playwright com JS desligado; capturas em 360, 768 e 1440 | Página legível e navegável; nenhum rolamento horizontal | A3 |
| **G9** | SEO mecânico | Confere `title`, `description`, `canonical`, `h1` único, hierarquia de títulos, OG, forma do JSON-LD, sitemap ⊇ páginas e ⊆ páginas existentes, RSS bem formado | Todos os itens, em todas as páginas | A5 |
| **G10** | Tom e lastro (**C1**) | Leitura da página inteira contra a tabela de proveniência | Zero afirmação sem lastro; zero palavra proibida; P2 e P3 do §51.3 | A1 |
| **G11** | Teste dos 8 segundos (**A/B cego**) | Cinco agentes sem contexto veem só a primeira dobra por 8 s e respondem "o que este produto faz e para quem"; depois comparam a página, lado a lado e sem rótulo, com a landing atual | 5/5 acertam; a nova vence a atual em clareza no julgamento cego | A1/A3 |

### 51.7.2 O algoritmo do loop
```
i ← 1
repita:
    A6 roda G0…G9  →  relatório com o endereço de cada falha
    C1 roda G10    →  vereditos
    C2 revisa G3…G8 à mão, procurando o que o script não pega
    banca cega roda G11

    se todos os portões passaram:
        A6 grava a ATA DE APROVAÇÃO (§51.7.4) e o loop termina
        pare

    cada falha é despachada AO DONO do arquivo (tabela §51.5)
    os donos corrigem em paralelo; nenhum dono toca em arquivo alheio
    i ← i + 1
    se i > 3:
        pare e leve ao dono do produto o que não converge, com o histórico das
        três rodadas — três rodadas sem convergir é sinal de requisito errado,
        não de execução ruim
```

### 51.7.3 Regras que impedem o loop de virar teatro
1. **Quem corrige não aprova.** A6, C1 e C2 nunca editam arquivo de produto.
2. **Nenhum portão é dispensado por pressa.** Portão que não puder rodar conta como reprovado, não como "pulado".
3. **Regressão é falha.** Toda rodada roda os portões *inteiros*, não só os que falharam antes.
4. **Correção sem endereço é rejeitada.** Todo conserto cita o portão que fecha.
5. **O `dist` não é editado à mão. Nunca.**

### 51.7.4 Ata de aprovação
Ao fim, A6 grava `planejamento/51_ATA_DE_VERIFICACAO.md`: data, commit, uma linha
por portão **com a medida obtida** (não só `✔`), o número de rodadas e o que ficou
consciente e explicitamente de fora. É esse arquivo que autoriza publicar.

---

## 51.8 · PILAR 5 — Stack rígida e gatilhos de profundidade

### Pilha, sem margem
- Landing e blog: **HTML + CSS + Vite**, sem framework de interface, sem TypeScript, sem pré-processador de CSS.
- JavaScript de execução: apenas o `landing.js` atual (menu e revelação), abaixo de 5 kB e sempre opcional.
- Dependências permitidas: **build-time apenas** — `vite`, `markdown-it` (DEC‑1), `sharp` (DEC‑2). Zero dependência de execução, hoje e depois.
- Fontes auto-hospedadas em `woff2`; **nunca** `fonts.googleapis.com` (doc 40 §40.8.2, doc 41 §553).
- CSP inalterado: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:`.
- Imagens: WebP, duas larguras, `<picture>`, dimensão explícita.
- Português do Brasil em tudo, código e conteúdo, como no resto do repositório.

### Gatilhos de profundidade (o que reprova entrega rasa)
- **Nada de `<!-- restante aqui -->`, `TODO`, `lorem ipsum`, texto de exemplo ou caminho de imagem inexistente.** Cada entrega roda.
- O post de exemplo do blog é **um texto de verdade**, não um teste de tipografia.
- Script de captura entregue sem ter sido rodado é entrega inválida.
- CSS de seção removida sai junto com a seção.
- Toda contagem que aparece no texto (11 diretrizes, 5 bases) é reconferida contra o código na rodada final — número que envelhece na página é dívida.

---

## 51.9 Tabela de proveniência (A1 preenche, C1 audita)

Cada afirmação da página pública precisa de uma linha aqui. Modelo:

| Afirmação na página | Lastro | Conferido em |
|---|---|---|
| "11 diretrizes no catálogo" | `frontend/src/data/guiasDoProtocolo.ts` | |
| "5 bases com coletor próprio" | `backend/app/harvesters/` | |
| "registra provedor, modelo e hash do contexto" | `AuditLogModel`, em `backend/app/infrastructure/persistence/models.py` | |
| "exportação RIS, BibTeX, CSV, XLSX" | `backend/app/services/export_service.py` | |
| "fluxograma PRISMA gerado do banco" | `backend/app/services/insights_service.py` | |

---

## 51.10 O blog, em detalhe

### Rota e forma
- `/blog` — índice; `/blog/<slug>/` — post; `/feed.xml` — RSS. Diretório com `index.html`, igual a `/termos`, para funcionar sem extensão nos dois modos de entrega.
- Post: `<article>`, `h1` único, sumário por âncora quando passar de 1500 palavras (sem JavaScript), data de publicação e de atualização visíveis, tempo de leitura, autor, tags, e um bloco final curto ligando ao app.

### Front-matter obrigatório
```yaml
titulo: ...
descricao: ...        # 140 a 160 caracteres; vira a meta description
slug: ...
data: 2026-09-10
atualizado: 2026-09-10
autor: Eduardo Matheus Figueira
tags: [prisma, triagem]
palavra_chave_alvo: "como fazer revisão sistemática"
resumo: ...           # aparece no índice e no RSS
```

### Pauta inicial — seis textos que o público procura em português
Ordenados por (busca existente × credibilidade que constroem). Nenhum é texto de venda; o produto aparece no fim, quando couber.

| # | Título de trabalho | Expressão-alvo | Por que este |
|---|---|---|---|
| 1 | Quanto tempo leva uma revisão sistemática, segundo a literatura | "quanto tempo leva revisão sistemática" | É o conteúdo D1 que sai da landing, já com fonte citada |
| 2 | Como escrever um protocolo de revisão sistemática (com exemplo preenchido) | "protocolo de revisão sistemática exemplo" | Intenção alta, concorrência fraca em português |
| 3 | Checklist PRISMA 2020 explicado item a item, em português | "prisma 2020 português" | Termo com busca constante e quase nenhum material em pt-BR |
| 4 | Como montar string de busca para BDTD e SciELO | "string de busca scielo bdtd" | É a diferença regional do produto (doc 42 §42.5), e ninguém escreve isso |
| 5 | Revisão sistemática, integrativa e de escopo: qual é a diferença | "diferença revisão sistemática e integrativa" | Dúvida de entrada de todo pós-graduando |
| 6 | Usar IA na triagem sem violar o método: o que registrar | "inteligência artificial revisão sistemática" | Onde o produto e o assunto se encontram sem forçar |

**Regras editoriais:** 1200 a 2500 palavras; fonte citada com link em toda
afirmação metodológica; nenhuma comparação nominal com concorrente; nenhum texto
gerado e publicado sem leitura; atualizar `atualizado:` a cada revisão de
conteúdo — o campo alimenta `dateModified` e o `lastmod` do sitemap.

---

## 51.11 Riscos

| Risco | Efeito | Mitigação |
|---|---|---|
| Os prints envelhecem a cada mudança de UI | Landing mostrando tela que não existe mais | O script de captura é versionado; regravar entra na rotina de release, e G3 confere a data dos arquivos |
| Dado pessoal em captura | Incidente de LGPD em página pública | Fixture com identidade fictícia; A2 confere imagem a imagem; C2 confere de novo em G3 |
| Peso das imagens derruba o LCP | Perde P6 e P7 | Orçamento em G4, uma única imagem sem `lazy`, WebP em duas larguras |
| Blog cresce e o build vira manual | Post publicado que não entra no `dist` | Inputs por varredura, não à mão — item explícito de G0 |
| Rota nova funciona no Caddy e falha no backend | `/blog` quebrado em desenvolvimento ou no modo local | G2 testa os dois caminhos, sempre |
| A simplificação apaga a diferença do produto | Página clara e genérica | A seção 2 (rastro) e a lista de bases são intocáveis; C1 audita |
| Publicar conteúdo raso em volume por SEO | Perde a credibilidade que é o ativo do produto (doc 42 §42.10) | Pauta fechada em seis textos com fonte; nenhum texto sem revisão humana |

---

## 51.12 Rollback

Trabalho em `git checkout -b landing-v2`. A landing atual continua íntegra em
`main`, e o rollback é o `revert` de um merge — nada de guardar
`index.legacy.html` no repositório. Publicação só depois da ata (§51.7.4).

---

## 51.13 Checklist mestre

- [ ] **51.1** DEC‑1, DEC‑2 e DEC‑3 decididas pelo dono do produto
- [ ] **51.2** Branch `landing-v2` criada
- [ ] **51.3** A1 entrega `51_ANEXO_TEXTO.md` com a tabela de proveniência completa
- [ ] **51.4** A2 entrega o script de captura, rodado, e as 6 imagens em duas larguras
- [ ] **51.5** A2 entrega `51_ANEXO_CAPTURAS.md` com os `alt`
- [ ] **51.6** A4 entrega o motor do blog com um post real de ponta a ponta
- [ ] **51.7** A4 ajusta `vite.config.ts` (inputs por varredura), `Caddyfile` e `backend/app/main.py`
- [ ] **51.8** A3 monta a landing nova, remove o CSS órfão e auto-hospeda as fontes
- [ ] **51.9** A5 entrega metadados, sitemap gerado, RSS, robots e `51_ANEXO_SEO.md`
- [ ] **51.10** A6 entrega `verificar-landing.mjs` com G0–G9
- [ ] **51.11** Loop do §51.7 até todos os portões passarem (máximo 3 rodadas)
- [ ] **51.12** `51_ATA_DE_VERIFICACAO.md` gravada e assinada
- [ ] **51.13** Merge e publicação; doc 41 Fase 5 atualizado (item 5.3 e a landing nova)

---

## 51.14 O super-prompt de abertura

Para despachar o trabalho de uma vez, com este documento no repositório:

```text
Leia planejamento/51_PLANO_LANDING_E_BLOG.md por inteiro antes de qualquer coisa,
e mais os documentos que ele obedece: 40 §40.8, 41 Fase 5, 42 §42.4 e §42.6.

Execute o plano com o fan-out de §51.5: seis agentes, cada um dono exclusivo dos
seus arquivos, nas quatro ondas descritas. A âncora de qualidade é §51.3 — não é
uma página de startup: é uma página que explica, com print real ao lado de cada
frase, e um blog indexável. Os dez critérios de paridade de §51.3 são numéricos;
não são opinião.

Ao fim, rode o loop de §51.7 sem pular portão: A6 executa G0–G9, C1 audita tom e
lastro (G10), C2 audita engenharia à mão, e a banca cega roda G11. Quem escreveu
não aprova o que escreveu. Cada falha volta ao dono do arquivo com endereço. No
máximo três rodadas; se não convergir, pare e traga o histórico.

Proibido: placeholder, TODO, lorem ipsum, caminho de imagem inexistente, script
entregue sem ter rodado, CSS órfão, requisição a terceiro, e afirmação sobre o
produto que você não consiga confirmar abrindo o código. Entrega parcial que
"depois se completa" conta como reprovada.

Só encerre com a ata de §51.7.4 gravada, com a medida obtida em cada portão.
```

---

*Documento 51 do planejamento do Revsist · versionado em [`planejamento/51_PLANO_LANDING_E_BLOG.md`](./51_PLANO_LANDING_E_BLOG.md)*
