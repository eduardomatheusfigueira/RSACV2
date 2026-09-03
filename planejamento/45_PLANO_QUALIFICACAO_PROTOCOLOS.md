# 45 — Plano de Qualificação e Requalificação dos Protocolos

> **Status:** 🟢 Normativo — **as quatro decisões em aberto foram fechadas em
> 30/08/2026** (§19.1). A execução (F1 em diante) não começou.
> **Escopo:** o subsistema de Protocolo do Revsist — modelo de dados, catálogo
> metodológico, Estúdio de Protocolo, ligação com a Coleta, a Triagem, a
> Extração e os Indicadores, e a exportação do protocolo.
> **Substitui na prática:** o catálogo único de `Methodology`
> (`backend/app/domain/enums.py:19`) e o Estúdio de 17 campos fixos
> (`frontend/src/pages/ProtocolPage.tsx`).
> **Não altera:** coletores, deduplicação, mecanismo de IA, LGPD, autenticação.

---

## 1. Sumário executivo — a decisão em uma página

O protocolo do Revsist hoje é **uma escolha só** (`projects.methodology`), feita
na criação do projeto, que ao mesmo tempo tenta dizer *que tipo de revisão é*,
*como ela deve ser relatada* e *como ela deve ser conduzida*. Essas três coisas
não são a mesma coisa na literatura metodológica, e tratá-las como uma só é a
raiz de quase todos os problemas listados no §2.

Este plano propõe **decompor a escolha única em quatro eixos ortogonais**:

| Eixo | Pergunta que responde | Exemplo |
|---|---|---|
| **1. Desenho da revisão** | *O que esta pesquisa é?* | Revisão de escopo; RS de efetividade; estudo bibliométrico |
| **2. Diretriz de relato** | *Como ela será relatada?* | PRISMA 2020; PRISMA-ScR; BIBLIO; ROSES |
| **3. Padrão de condução** | *Sob que regras ela será feita?* | Cochrane/MECIR; JBI; CEE v5.1; EBSE; SPAR-4-SLR |
| **4. Modo de preenchimento** | *Com que profundidade?* | **Simplificado** \| **Completo** |

E propõe que o **Modo** (eixo 4) seja de fato uma alavanca de produto, e não um
"modo iniciante":

- **Simplificado — Núcleo de Busca.** 14 campos: o que é necessário para
  *executar e reproduzir* a busca nas bases, mais as **perguntas de extração**,
  que ficam no formulário para garantir o planejamento (decisão **D-C**). Não é
  um protocolo pior: é um protocolo de **escopo declarado**, que cobre
  integralmente o PRISMA-S (relato de buscas), os itens 5–7 do PRISMA 2020 e os
  dados a extrair (PRISMA-P i12), e que carimba em toda exportação o que cobre e
  o que não cobre. Seu produto exportável é o **Registro de Busca** — o confronto
  entre o configurado e o executado, base a base (decisão **D-B**, §10.5).
- **Completo.** O núcleo acima **mais** um dos três caminhos:
  **(a)** um protocolo-padrão externo (PRISMA-P, JBI Scoping, CEE/ROSES, PRIOR,
  BIBLIO, EBSE, SPAR-4-SLR) reproduzido na sua estrutura oficial;
  **(b)** o **Protocolo Revsist** — protocolo próprio, desenhado para casar 1:1
  com o pipeline do aplicativo, em que **todo campo tem consequência computável**;
  **(c)** um híbrido declarado, quando o campo do pesquisador exige.

Três peças ausentes hoje entram como parte inseparável da qualificação, porque
sem elas a palavra "protocolo" é imprecisa:

1. **Versionamento e congelamento** (protocolo *a priori* + registro de emendas);
2. **Estratégia de busca canônica** com adaptadores por base e registro da
   execução (data, string efetiva, contagem por base);
3. **Apreciação crítica como instrumento** (RoB 2, JBI, MMAT, AMSTAR-2), e não
   como campo de texto livre.

> **As quatro decisões em aberto foram fechadas em 30/08/2026** e já estão
> incorporadas ao corpo deste documento: **D-A** congelamento oferecido, não
> obrigatório (§12.1); **D-B** exportação da configuração de busca como
> **Registro de Busca** (§10.5); **D-C** perguntas de extração dentro do
> formulário Simplificado (§8.2–8.3); **D-D** `projects.methodology` mantido como
> campo derivado (§14.2). O histórico está no §19.1.

---

## 2. Diagnóstico do estado atual

O subsistema atual é **melhor que a média do mercado** em um ponto específico —
o catálogo de `frontend/src/data/protocolCatalog.ts` já distingue corretamente
condução de relato nos comentários, e já reaproveita a lista PRISMA em vez de
inventar checklists paralelas. O problema não é ignorância metodológica: é que o
**modelo de dados não comporta** a distinção que os comentários já reconhecem.

### 2.1 Achados

| # | Achado | Evidência | Gravidade |
|---|---|---|---|
| **P-01** | Três naturezas distintas convivem no mesmo enum de 11 valores: diretrizes de **relato** (PRISMA 2020/ScR/P, ROSES, PRIOR), padrões de **condução** (Cochrane, Campbell, JBI, EBSE) e método de **ordenação de portfólio** (Methodi Ordinatio). Escolher "Cochrane" e escolher "PRISMA 2020" não são escolhas do mesmo tipo. | `backend/app/domain/enums.py:19-30` | 🔴 |
| **P-02** | A consequência de P-01 é a duplicação: Cochrane e Campbell apontam para `PRISMA_2020_CHECKLIST`; JBI aponta para `PRISMA_SCR_CHECKLIST`. O app admite no comentário que está resolvendo uma ambiguidade do modelo. | `frontend/src/data/protocolCatalog.ts:17-24` | 🟠 |
| **P-03** | **Não existe "tipo de revisão" como conceito.** Uma revisão de escopo e uma RS de efetividade diferem em framework de pergunta, obrigatoriedade de apreciação crítica, elegibilidade de registro e tipo de síntese. Hoje isso só existe como texto de ajuda (`domainFocus`). | `protocolCatalog.ts:226-227` | 🔴 |
| **P-04** | A escolha vive em `projects.methodology`, decidida **na criação do projeto** — antes de o pesquisador saber que revisão vai fazer — e não tem trilha de mudança. | `models.py:92` | 🟠 |
| **P-05** | **Não há protocolo a priori de verdade.** `ProtocolModel` é um registro mutável, sem histórico, sem congelamento, sem log de emendas; `updated_at` é sobrescrito. Isso é o que separa um *protocolo* de um *formulário de configuração*. | `models.py:248-270`; `protocols.py:198` | 🔴 |
| **P-06** | A auditoria da checklist existe só em memória de sessão (`checkedScRItems`), não é persistida nem exportada. Some com um F5. | `ProtocolPage.tsx:264-267` | 🟠 |
| **P-07** | O framework de pergunta é binário `'PICO' \| 'PCC'`, e o estado tem chaves fixas `population/intervention/comparison/outcome` mesmo quando o rótulo diz PCC. Não existem PECO, PICOS, SPIDER, SPICE, CIMO de fato — embora `defaultFramework` já os declare no catálogo. | `ProtocolPage.tsx:211-218` vs. `protocolCatalog.ts:233` | 🟠 |
| **P-08** | **Uma regra da BDTD virou regra do protocolo:** a busca é limitada a pares de no máximo 2 termos, com erro 400 no backend. Não há booleana completa, truncamento, campos (título/resumo/palavra-chave) nem estratégia por base — justamente o item 3 do PRISMA-S ("full search strategies for each database, exactly as run"). | `protocols.py:140-149` | 🔴 |
| **P-09** | **Nada liga o protocolo à execução.** Não se grava data da busca, string efetivamente executada por base, nem número de registros por base. São itens obrigatórios do PRISMA 2020 (item 7) e do PRISMA-S (itens 3, 14). | `harvesting_service.py:420-465` | 🔴 |
| **P-10** | Não há distinção Simplificado/Completo: quem quer só rodar uma busca encara 7 abas e 17 campos de manuscrito. | `ProtocolPage.tsx:165-172` | 🟠 |
| **P-11** | Apreciação crítica e risco de viés são **campo de texto livre** (`critical_appraisal`), não um instrumento aplicável estudo a estudo. | `ProtocolPage.tsx:245-253` | 🟠 |
| **P-12** | **Bibliometria não existe como desenho.** A aba de Indicadores existe (`insights_service.py`), mas nenhum protocolo bibliométrico — e bibliometria tem exigências de reprodutibilidade que a RS não tem (data/hora da extração, versão do snapshot da base, desambiguação, limiares, software e versão). | `InsightsPage.tsx:2-7` | 🔴 |
| **P-13** | Os papéis de equipe já existem no projeto (`collaboration_mode`, `reviewers_per_paper`, `conflict_resolution`) mas **não são parte do protocolo**, embora sejam item de protocolo em PRISMA-P (11b), MECIR e JBI. | `models.py:98-106` | 🟡 |

### 2.2 O que **não** vamos mexer

O catálogo textual atual (`description`, `domainFocus`, `reference`) é bom e
bem-citado; ele **migra**, não morre. Os arquivos `protocolChecklists.ts` e
`guiasDoProtocolo.ts` são ativos valiosos e continuam sendo a fonte dos textos
de item e dos modelos de redação.

---

## 3. Base de referência — o que a literatura efetivamente exige

As escolhas do §4 em diante são justificadas por três camadas de fontes.

### 3.1 As quatro fontes trazidas para esta discussão

| Fonte | O que fixa neste plano |
|---|---|
| **Galvão TF, Pereira MG.** *Revisões sistemáticas da literatura: passos para sua elaboração.* Epidemiol Serv Saúde. 2014;23(1):183-184 | Fixa os **8 passos canônicos** (pergunta → busca → seleção → extração → qualidade metodológica → síntese → certeza → redação). O pipeline do Revsist é mapeado passo a passo contra essa lista no §9.2, e é dela que sai a decisão de que **PICO/PICOS é o piso, não o teto** ("um quinto componente, o tipo de estudo"). |
| **Sampaio RF, Mancini MC.** *Estudos de revisão sistemática: um guia para síntese criteriosa da evidência científica.* Rev Bras Fisioter. 2007;11(1):83-89 | Justifica o módulo de **apreciação crítica como instrumento** (P-11): a avaliação da qualidade dos estudos é tratada ali como etapa obrigatória e instrumentada, não como parágrafo do método. |
| **Franca R.** *Revisão sistemática: definição, tipos e relevância para a PBE.* Arq Med Hosp Fac Cienc Med Santa Casa São Paulo. 2025;70:e12 | Traz a **tipologia e o fluxograma de decisão** (pergunta específica? → escopo/narrativa; requer só intervenção/observacionais? → integrativa/umbrella; usa estatística? → com/sem metanálise). É a base direta do **Assistente de Escolha do Desenho** (§5.3) e da tipologia do §5.1. |
| **Leal EAS, Souza GDD, Teixeira GS, Sousa EF, Ribeiro JT.** *Planejamento e desenvolvimento regional: uma revisão sistemática.* (IFES / Laboratório do Desenvolvimento Capixaba) | É o **caso de uso real do público-alvo**: PRISMA aplicado em Ciências Sociais Aplicadas, sobre Scopus e Web of Science, com recorte 2019–2023 e sem RoB 2/GRADE. Fixa uma decisão de produto importante: **os padrões do Revsist não podem ser clínicos por omissão** (§5.2). |

### 3.2 Diretrizes de relato (o que se escreve)

| Sigla | Cobre | Itens | Referência |
|---|---|---|---|
| **PRISMA 2020** | RS com/sem metanálise | 27 | Page MJ, McKenzie JE, Bossuyt PM, et al. BMJ. 2021;372:n71 |
| **PRISMA-P** | *Protocolo* de RS | 17 | Moher D, Shamseer L, Clarke M, et al. Syst Rev. 2015;4:1 |
| **PRISMA-ScR** | Revisão de escopo | 22 | Tricco AC, Lillie E, Zarin W, et al. Ann Intern Med. 2018;169(7):467-473 |
| **PRISMA-S** | **A busca**, em qualquer revisão | 16 | Rethlefsen ML, Kirtley S, Waffenschmidt S, et al. Syst Rev. 2021;10:39 |
| **PRIOR** | Revisão de revisões | 27 | Gates M, Gates A, Pieper D, et al. BMJ. 2022;378:e070849 |
| **ROSES** | Síntese socioambiental | por seção | Haddaway NR, Macura B, Whaley P, Pullin AS. Environ Evid. 2018;7:7 |
| **ENTREQ** | Síntese qualitativa | 21 | Tong A, Flemming K, McInnes E, et al. BMC Med Res Methodol. 2012;12:181 |
| **eMERGe** | Metaetnografia | 19 | France EF, Cunningham M, Ring N, et al. BMC Med Res Methodol. 2019;19:25 |
| **RAMESES** | Revisão realista / meta-narrativa | 20/19 | Wong G, Greenhalgh T, Westhorp G, et al. BMC Med. 2013;11:21 |
| **SANRA** | Revisão narrativa | 6 | Baethge C, Goldbeck-Wood S, Mertens S. Res Integr Peer Rev. 2019;4:5 |
| **BIBLIO** | Revisão bibliométrica | 20 | *Preliminary guideline for reporting bibliometric reviews of the biomedical literature (BIBLIO).* Syst Rev. 2023. doi:10.1186/s13643-023-02410-2 |

### 3.3 Padrões de condução (como se faz)

Cochrane Handbook v6.5 (2024) + **MECIR**; **MECCIR** (Campbell); **JBI Manual
for Evidence Synthesis** (2024); **CEE Guidelines and Standards** v5.1;
**Kitchenham & Charters** (EBSE-2007-01); **SPAR-4-SLR** (Paul J, Lim WM,
O'Cass A, et al. Int J Consum Stud. 2021;45(4):O1-O16); **Tranfield, Denyer &
Smart** (Br J Manag. 2003;14(3):207-222); **Cochrane RRMG** para revisões
rápidas (Garritty C, et al. J Clin Epidemiol. 2021;130:13-22).

### 3.4 Tipologias de revisão

**Grant MJ, Booth A.** *A typology of reviews.* Health Info Libr J.
2009;26(2):91-108 (14 tipos, framework **SALSA**) · **Sutton A, Clowes M,
Preston L, Booth A.** *Meeting the review family.* Health Info Libr J.
2019;36(3):202-222 (48 tipos, 7 famílias) · **Munn Z, Peters MDJ, Stern C, et
al.** *Systematic review or scoping review?* BMC Med Res Methodol.
2018;18:143 · **Franca R. (2025)**, §3.1.

### 3.5 Instrumentos de qualidade e certeza

**RoB 2** (Sterne JAC, et al. BMJ. 2019;366:l4898) · **ROBINS-I** (Sterne JA,
et al. BMJ. 2016;355:i4919) · **JBI Critical Appraisal Tools** · **MMAT 2018**
(Hong QN, et al.) · **AMSTAR 2** (Shea BJ, et al. BMJ. 2017;358:j4008) ·
**ROBIS** (Whiting P, et al. J Clin Epidemiol. 2016;69:225-234) · **GRADE**
(Guyatt GH, et al. J Clin Epidemiol. 2011;64(4):383-394) · **GRADE-CERQual**
(Lewin S, et al. Implement Sci. 2018;13(Suppl 1):2).

### 3.6 Bibliometria

**Zupic I, Čater T.** Organ Res Methods. 2015;18(3):429-472 (fluxo de 5 etapas)
· **Donthu N, Kumar S, Mukherjee D, Pandey N, Lim WM.** J Bus Res.
2021;133:285-296 · **Aria M, Cuccurullo C.** *bibliometrix.* J Informetr.
2017;11(4):959-975 · **van Eck NJ, Waltman L.** *VOSviewer.* Scientometrics.
2010;84(2):523-538 · **Pagani RN, Kovaleski JL, Resende LM.** *Methodi
Ordinatio.* Scientometrics. 2015;105(3):2109-2135 e **Methodi Ordinatio 2.0**
(Qual Quant. 2023; doi:10.1007/s11135-022-01562-y).

> ⚠️ **Nota de honestidade.** O BIBLIO se autodeclara *preliminary* e nasceu na
> literatura biomédica. Existe ainda revisão de escopo recente sobre orientação
> de relato bibliométrico em *Quantitative Science Studies* (2025) cujo conteúdo
> **não foi verificado** para este documento. A decisão adotada no §11 — usar o
> BIBLIO como espinha e o PRISMA-S para a parte de consulta — leva isso em conta
> e é revisável.

---

## 4. O modelo proposto — quatro eixos ortogonais

```
Projeto
 └── Protocolo (1:1)
      ├── modo:               'simplificado' | 'completo'          ← eixo 4
      ├── desenho:            review_design                        ← eixo 1
      ├── diretriz_relato:    reporting_guideline (derivada, trocável)   ← eixo 2
      ├── padrao_conducao:    conduct_standard[] (0..n, opcional)  ← eixo 3
      ├── pergunta:           question_framework tipado
      ├── estrategia_busca:   canônica + adaptações por base
      ├── elegibilidade:      criteria[] tipados
      ├── extracao:           extraction_questions[] tipadas
      ├── apreciacao:         instrumento + política
      ├── sintese:            tipo + parâmetros
      ├── versoes:            protocol_versions[]  (congelamento + hash)
      └── emendas:            protocol_amendments[]
```

**Por que ortogonais e não uma taxonomia única?** Porque as combinações reais
não são hierárquicas. Uma revisão de escopo pode ser conduzida pelo JBI **ou**
por Arksey & O'Malley + Levac, e em ambos os casos relatada em PRISMA-ScR. Uma
RS de efetividade pode ser conduzida sob MECIR e relatada em PRISMA 2020, ou
conduzida sem filiação e relatada igualmente em PRISMA 2020. Forçar uma árvore
única obriga a inventar nós que não existem na literatura — que é exatamente o
que o enum atual faz.

**Regra de derivação:** o eixo 1 **propõe** os eixos 2 e 3 e o framework de
pergunta; nunca os impõe. Toda derivação é visível na interface como "sugerido
porque você escolheu X", e reversível com um clique. O motivo: o público-alvo do
Revsist (Ciências Sociais Aplicadas, Desenvolvimento Regional — ver comentário
em `protocolCatalog.ts:481-484` e o caso de Leal et al.) trabalha com
combinações que a literatura de saúde não catalogou.

---

## 5. Eixo 1 — Catálogo de desenhos de revisão

### 5.1 O catálogo

Cada desenho declara: framework padrão, diretriz de relato padrão, padrões de
condução compatíveis, **obrigatoriedade** de apreciação crítica, tipo de síntese
esperado, unidade de análise e elegibilidade de registro.

| # | Desenho | Quando usar | Framework | Relato padrão | Condução | Apreciação crítica | Registro |
|---|---|---|---|---|---|---|---|
| D1 | **RS de efetividade** (com/sem metanálise) | Pergunta fechada de efeito de intervenção | PICO / PICOS | PRISMA 2020 + PRISMA-S | Cochrane/MECIR, Campbell/MECCIR | **Obrigatória** — RoB 2 / ROBINS-I + GRADE | PROSPERO |
| D2 | **RS de prevalência ou associação** | Frequência, exposição, associação (observacionais) | PECO / PEO / CoCoPop | PRISMA 2020 + PRISMA-S | JBI (prevalência), MECIR | **Obrigatória** — JBI, Newcastle-Ottawa | PROSPERO |
| D3 | **Síntese qualitativa / metassíntese** | Experiências, percepções, significados | SPIDER / PICo / SPICE | ENTREQ (ou eMERGe se metaetnografia) | JBI meta-agregação | **Obrigatória** — CASP / JBI + CERQual | PROSPERO |
| D4 | **Revisão de escopo** | Mapear extensão, natureza e lacunas | **PCC** | **PRISMA-ScR** | JBI cap. 10; Arksey & O'Malley + Levac | **Opcional** — se não fizer, declarar | OSF / Figshare (**não** PROSPERO) |
| D5 | **Mapa sistemático / mapa de lacunas** | Catalogar sem sintetizar efeito | PICO / PECO / PCC | **ROSES** | CEE v5.1 | Opcional | OSF |
| D6 | **Revisão de revisões (umbrella)** | Já existem várias RS sobre o tema | PICO | **PRIOR** | JBI Umbrella | **Obrigatória** — AMSTAR 2 / ROBIS **+ sobreposição (CCA)** | PROSPERO |
| D7 | **Revisão integrativa** | Desenhos mistos, teoria + empiria | PICo / SPIDER | PRISMA 2020 adaptado | Whittemore & Knafl (2005); Souza, Silva & Carvalho (2010) | Recomendada — MMAT | OSF |
| D8 | **Revisão rápida** | Decisão com prazo curto | PICO | PRISMA 2020 + **declaração de atalhos** | Cochrane RRMG (Garritty 2021) | Simplificada — declarar o atalho | PROSPERO |
| D9 | **RS em Engenharia de Software** | Comparar tecnologias, métodos, ferramentas | PICOC / PICOS | Relatório EBSE (+ PRISMA opcional) | Kitchenham & Charters 2007 | Critérios de qualidade EBSE | — |
| D10 | **RS em Gestão / Negócios** | Domínio, teoria, método, agenda futura | TCCM + framework livre | **SPAR-4-SLR** + PRISMA | Tranfield 2003; Paul 2021 | Opcional | — |
| D11 | **Estudo bibliométrico / cienciométrico** | Mapear a estrutura intelectual e social do campo | **Não-PICO**: domínio + recorte + unidade de análise | **BIBLIO** + PRISMA-S para a consulta | Zupic & Čater 2015; Donthu 2021 | **Não se aplica** (a validade está no dado, §11.3) | OSF |
| D12 | **Portfólio ordenado (Methodi Ordinatio)** | Construir referencial teórico hierarquizado | Livre | PRISMA para o fluxo | Pagani 2015 / 2.0 (2022) | InOrdinatio | — |
| D13 | **Revisão narrativa estruturada** | Panorama teórico assumidamente não exaustivo | Livre | **SANRA** | — | — | — |
| D14 | **Outro / híbrido declarado** | Combinação que o catálogo não cobre | Livre | Genérico (`GENERIC_CHECKLIST`) | Declarar em texto | Declarar | — |

**Fases:** D1, D2, D4, D6, D11, D12, D14 na Fase 3 (cobrem o enum atual + a
lacuna crítica da bibliometria). D3, D5, D7, D8, D9, D10, D13 na Fase 3b.

### 5.2 Decisões de produto embutidas no catálogo

**(a) Padrões não-clínicos.** O desenho pré-selecionado ao criar um projeto
**não** é D1. É D4 (escopo) quando o usuário não sabe, porque é o desenho de
entrada da literatura (Munn et al., 2018: *"se o objetivo é identificar o que
existe, é escopo"*) e porque é o desenho hoje default no código
(`PROTOCOL_OPTIONS[0] === 'PRISMA-ScR'`). O caso de Leal et al. mostra por quê:
uma RS PRISMA legítima em desenvolvimento regional, sem RoB 2 e sem GRADE, hoje
seria empurrada para uma checklist com itens que ela não tem como cumprir.

**(b) "Registro" é informativo, não um botão.** O Revsist **não** submete a
PROSPERO nem a OSF. Ele gera o documento pronto e informa a elegibilidade —
inclusive a restrição de que o PROSPERO não aceita revisões de escopo, e exige
ao menos um desfecho relacionado a saúde. Automatizar submissão a um registro
externo em nome do pesquisador seria assumir responsabilidade que não é do
software.

**(c) Apreciação crítica opcional é *declarada*, não omitida.** Em D4/D5/D11, se
o pesquisador não faz apreciação crítica, o protocolo grava a decisão e a
exportação a imprime — que é literalmente o item 12 do PRISMA-ScR ("if
performed, provide rationale... if not, state so").

### 5.3 Assistente de Escolha do Desenho

Árvore de decisão de 4 perguntas, transcrita de Franca (2025, Figura 1) e
complementada por Munn et al. (2018):

```
1. Você tem uma pergunta de pesquisa específica e fechada?
   ├── NÃO → 2. Quer mapear o que existe, com que conceitos e lacunas?
   │          ├── SIM → D4 Revisão de escopo   (ou D5 se o produto é um mapa)
   │          └── NÃO → D13 Revisão narrativa estruturada
   └── SIM → 3. A unidade de análise são estudos primários ou revisões?
              ├── REVISÕES → D6 Umbrella
              └── PRIMÁRIOS → 4. O que você quer produzir?
                   ├── Estimativa de efeito com estatística → D1 (com metanálise)
                   ├── Síntese sem estatística              → D1 (descritiva) / D7
                   ├── Compreensão de experiências          → D3
                   ├── Frequência / associação              → D2
                   ├── Mapa da estrutura do campo           → D11 Bibliometria
                   └── Portfólio teórico hierarquizado      → D12
```

Aparece na criação do projeto e é reabrível a qualquer momento pelo Estúdio.
**Nunca bloqueia:** há sempre "escolher manualmente".

---

## 6. Eixos 2 e 3 — relato e condução

### 6.1 Separação

`reporting_guideline` (0..1, obrigatório) e `conduct_standard` (0..n, opcional)
passam a ser campos distintos. Isso resolve P-01/P-02 sem perder nada: as
entradas Cochrane, Campbell, JBI, CEE e EBSE do catálogo atual **migram para o
eixo 3**, e as checklists que elas hoje "emprestam" passam a ser a diretriz de
relato de fato selecionada no eixo 2.

Ganho concreto: passa a ser possível dizer, na exportação, algo que hoje é
impossível — *"Revisão de escopo (D4), conduzida conforme o JBI Manual for
Evidence Synthesis (2024), cap. 10, e relatada conforme PRISMA-ScR"* — que é
exatamente a frase que uma seção de Métodos precisa ter.

### 6.2 O que cada padrão de condução acrescenta ao protocolo

Cada `conduct_standard` selecionado **injeta campos e regras adicionais** no
Estúdio, em vez de apenas mudar um texto:

| Padrão | Injeta |
|---|---|
| Cochrane/MECIR | Dupla triagem obrigatória; busca com bibliotecário declarada; RoB 2; GRADE; Summary of Findings |
| Campbell/MECCIR | Protocolo revisado por pares; literatura cinzenta obrigatória; seção de equidade (PROGRESS-Plus) |
| JBI | Instrumentos JBI de apreciação; fluxo SUMARI; para escopo, o gabarito de protocolo JBI 2024 |
| CEE v5.1 | Envolvimento de partes interessadas na pergunta; busca em sites de organizações; teste de abrangência |
| EBSE | Estrutura em 3 fases; critérios de qualidade EBSE; *search string* por base |
| SPAR-4-SLR | Estágios *Assembling → Arranging → Assessing*; justificativa explícita de cada decisão de recorte |
| Cochrane RRMG | Campo obrigatório "atalhos adotados e seu impacto declarado" |

---

## 7. Framework de pergunta tipado

Substitui `pico_framework: Dict[str, str]` com chaves fixas (P-07) por uma
estrutura declarada:

```jsonc
{
  "framework": "PCC",
  "components": [
    { "key": "population", "label": "População",  "value": "..." },
    { "key": "concept",    "label": "Conceito",   "value": "..." },
    { "key": "context",    "label": "Contexto",   "value": "..." }
  ],
  "question": "Texto corrido da pergunta, gerado ou editado à mão"
}
```

Frameworks catalogados, com fonte e uso:

| Sigla | Componentes | Indicado para | Fonte |
|---|---|---|---|
| **PICO** | População, Intervenção, Comparação, Desfecho | Efetividade | Richardson et al. 1995 |
| **PICOS** | + Desenho do estudo | Quando o desenho é critério | Galvão & Pereira 2014 |
| **PICOC** | + Contexto | Engenharia de Software | Petticrew & Roberts 2006 |
| **PECO / PEO** | Exposição no lugar de Intervenção | Observacional, ambiental | — |
| **PCC** | População, Conceito, Contexto | **Escopo** | JBI Manual 2024 |
| **SPIDER** | Sample, Phenomenon of Interest, Design, Evaluation, Research type | Qualitativo / misto | Cooke, Smith & Booth 2012 |
| **SPICE** | Setting, Perspective, Intervention, Comparison, Evaluation | Serviços e políticas | Booth 2006 |
| **CIMO** | Context, Intervention, Mechanism, Outcome | Gestão, realista | Denyer & Tranfield 2009 |
| **CoCoPop** | Condition, Context, Population | Prevalência | JBI |
| **Domínio-Recorte-Unidade** | Domínio temático, recorte, unidade de análise | **Bibliometria** | Adaptado de Zupic & Čater 2015 (§11) |
| **Livre** | Campos definidos pelo usuário | Híbridos | — |

**Justificativa da estrutura genérica:** cada framework é dado, não código. Um
framework novo (ou um do usuário) entra por cadastro, sem migração de schema —
o que é a condição para que o eixo 1 possa crescer de 7 para 14 desenhos sem
que o modelo de dados vire um pântano de colunas opcionais.

O framework **alimenta a estratégia de busca**: cada componente vira um bloco de
conceito no §10, com seus sinônimos. É essa ligação que faz o framework deixar
de ser decoração.

---

## 8. Eixo 4 — Modo **Simplificado** (Núcleo de Busca)

### 8.1 Definição e justificativa

> **Modo Simplificado = o conjunto mínimo de informações que torna uma busca
> em bases (a) executável pelo Revsist e (b) reproduzível por um terceiro.**

Esse recorte não é arbitrário: é **exatamente o escopo do PRISMA-S** — a extensão
do PRISMA dedicada ao relato de buscas, com 16 itens, desenvolvida por Delphi em
três rodadas justamente porque a busca "estabelece os dados disponíveis para
análise" e todo o resto do processo depende dela (Rethlefsen et al., 2021).
Somado aos itens 5–7 do PRISMA 2020 (elegibilidade, fontes de informação,
estratégia de busca), fecha um protocolo que é **incompleto por escolha
declarada, e não incompleto por descuido**.

### 8.2 Os campos

| # | Campo | Obrigatório | Ancoragem |
|---|---|---|---|
| S1 | Título de trabalho | ✔ | PRISMA 2020 i1 |
| S2 | Pergunta / objetivo (texto livre) | ✔ | PRISMA 2020 i4 |
| S3 | Framework da pergunta (§7) | ○ opcional | — |
| S4 | Desenho da revisão (§5) | ✔ | Define o pipeline |
| S5 | Bases-alvo + justificativa curta da escolha | ✔ | **PRISMA-S i1–i2** |
| S6 | Estratégia canônica: blocos de conceito × sinônimos × operadores | ✔ | **PRISMA-S i3–i4** |
| S7 | Adaptação por base (gerada, editável) | ✔ (gerada) | **PRISMA-S i3** |
| S8 | Recorte: anos, idiomas, tipos documentais, acesso aberto | ○ | **PRISMA-S i6** (limites) |
| S9 | Métodos complementares: citação regressiva/progressiva, contato com autores, literatura cinzenta, sites de organizações | ○ | **PRISMA-S i7–i10** |
| S10 | Critérios de elegibilidade (mín. 1 de inclusão) | ✔ | PRISMA 2020 i5 |
| S11 | **Perguntas de extração** (lista simples) — decisão **D-C** | ✔ | **PRISMA-P i12**, PRISMA 2020 i10a |
| S12 | **Data e hora de cada busca** | 🔒 automático | **PRISMA-S i14**, PRISMA 2020 i7 |
| S13 | **Nº de registros por base** | 🔒 automático | PRISMA 2020 i16a |
| S14 | Método de deduplicação | 🔒 automático + editável | **PRISMA-S i15** |

🔒 = preenchido pela execução, não digitado. É a resposta direta a P-09: o
protocolo passa a **registrar o que aconteceu**, não só o que se pretendia.

### 8.3 Perguntas de extração — dentro do formulário (decisão D-C)

As **perguntas de extração** são o caso limítrofe do modo Simplificado: não são
necessárias para *buscar*, mas são necessárias para a aba de Extração funcionar.
A alternativa examinada era revelá-las *just-in-time*, ao entrar na Extração.

**Decisão tomada (30/08/2026): ficam dentro do formulário Simplificado, para
garantir o planejamento.** Três consequências, e a razão de a decisão ser
metodologicamente a mais forte das duas:

1. **É um item de protocolo, não de execução.** O PRISMA-P item 12 (*data items*)
   exige listar e definir *a priori* todas as variáveis para as quais se buscará
   dado; o PRISMA 2020 item 10a repete a exigência no relato. Decidir o que se vai
   extrair **depois** de ver o que a busca trouxe é precisamente o comportamento
   que o protocolo a priori existe para impedir.
2. **Fecha a lacuna que sobraria no carimbo.** Com S11 dentro, o modo Simplificado
   passa a cobrir também PRISMA-P i12 / PRISMA 2020 i10a, e o bloco "não cobre"
   do §8.4 encolhe — o modo fica mais defensável, não mais pesado.
3. **O portão da Extração deixa de existir.** Todo protocolo Simplificado nasce
   com Extração habilitada (§13.1).

**Custo, e como é pago.** S11 é o único campo do núcleo que não serve à busca, e
sozinho ameaça a meta de "zero à coleta em menos de 5 minutos" (§16.1). Três
mitigações, todas na F2:

- **Conjunto inicial sugerido por desenho.** Cada desenho do §5 traz uma lista
  curta e editável — D4 abre com *população, conceito, contexto, tipo de fonte,
  achado principal*; D1 com *desenho do estudo, tamanho amostral, intervenção,
  comparador, desfecho, medida de efeito*; D11 com os campos de §11.2.
- **Sugestão por IA quando ativa**, derivada da pergunta em S2 e do desenho em S4,
  sempre rotulada como sugestão editável.
- **Tipagem fica no modo Completo.** No Simplificado a pergunta é só texto e
  ordem (`answer_type` assume `'texto'`); tipo de resposta, opções e
  obrigatoriedade só aparecem no Completo (§14.1).

Continua valendo a revelação progressiva para o que é genuinamente de execução:
critérios que só se aplicam a texto completo, conferência de extração e piloto de
calibração seguem aparecendo na etapa em que são usados.

### 8.4 O carimbo de escopo

Toda exportação de um protocolo Simplificado — PDF, DOCX, JSON, relatório —
carrega um bloco fixo:

> *Protocolo em modo Simplificado. Cobre integralmente os 16 itens do PRISMA-S
> (relato de buscas), os itens 5–7 do PRISMA 2020 e os itens de dados a extrair
> (PRISMA-P 12 / PRISMA 2020 10a). **Não cobre**: registro prospectivo,
> apreciação crítica, métodos de síntese, avaliação da certeza da evidência,
> vieses de relato e conflitos de interesse. Para submissão como revisão
> sistemática completa, migre para o modo Completo.*

**Por que isso é inegociável:** um formulário curto que se anuncia como
"protocolo de revisão sistemática" produz revisões que passam na aparência e
falham na revisão por pares. O carimbo é o que permite ao Revsist oferecer o
caminho rápido **sem** vender rigor que não entregou.

### 8.5 Migração de modo

`Simplificado → Completo` é **não-destrutivo**: os 13 campos permanecem e
viram o núcleo das seções correspondentes. `Completo → Simplificado`
**não apaga nada**; apenas oculta, com aviso explícito de que os campos
preenchidos continuam gravados e voltarão a aparecer.

---

## 9. Modo **Completo** e o Protocolo Revsist

No modo Completo, o pesquisador escolhe **um dos três caminhos**:

### 9.1 (a) Protocolo-padrão externo

Reproduz a estrutura oficial do gabarito escolhido, seção a seção, com o texto
de orientação do item e um exemplo de redação (é o papel atual de
`guiasDoProtocolo.ts`, estendido). Gabaritos da Fase 3:

| Gabarito | Estrutura |
|---|---|
| **PRISMA-P** | 17 itens em Administrative information / Introduction / Methods |
| **JBI Scoping Review Protocol** (gabarito 2024) | Título, Revisores, Objetivo, Pergunta, Critérios (PCC), Métodos (busca, seleção, extração, apresentação), Apêndices |
| **CEE / ROSES** | Formulário por seção da CEE v5.1 |
| **PRIOR** | 27 itens, com os domínios de sobreposição e qualidade das revisões |
| **BIBLIO** | 20 itens (§11) |
| **EBSE** | 3 fases × 13 passos |
| **SPAR-4-SLR** | 3 estágios × 6 subestágios, cada decisão com sua *rationale* |

### 9.2 (b) **Protocolo Revsist** — o protocolo próprio da ferramenta

**Princípio de desenho, e é ele que justifica a existência do protocolo próprio:**

> **Todo campo do Protocolo Revsist ou (i) altera o comportamento do sistema, ou
> (ii) é exigido por duas ou mais diretrizes reconhecidas. Campo que não passa
> nesse teste não entra no núcleo — vai para o gabarito externo do §9.1.**

Isso é o oposto de "inventar mais uma diretriz". O Protocolo Revsist não compete
com o PRISMA: ele é a **projeção do PRISMA (e do JBI, e do CEE) sobre o pipeline
real do aplicativo**, de modo que preencher o protocolo *configure a execução*, e
executar *preencha o protocolo de volta*.

Mapeamento contra os 8 passos de Galvão & Pereira (2014) e contra o pipeline
(`08_PIPELINE_DADOS.md`):

| Seção do Protocolo Revsist | Passo (Galvão & Pereira) | Tela do Revsist | Consequência computável |
|---|---|---|---|
| **0. Identificação e governança** — título, equipe e papéis, nº de revisores/artigo, regra de conflito, financiamento, conflitos de interesse | — | Projetos / Equipe | Configura `collaboration_mode`, `reviewers_per_paper`, `conflict_resolution` (resolve **P-13**) |
| **1. Justificativa e pergunta** — racional, pergunta tipada (§7), objetivos | 1 | Protocolo | Componentes viram blocos da estratégia (§10) |
| **2. Elegibilidade** — critérios tipados por eixo (população, desenho, período, idioma, tipo documental, contexto), cada um com `applies_at` (título-resumo \| texto completo) | 3 | Triagem | Motivo de exclusão auditável, exigido pelo PRISMA 2020 i16b |
| **3. Fontes e estratégia** — §10 | 2 | Coleta | Executa a busca; grava data e contagem |
| **4. Seleção** — piloto de calibração, nº de revisores, medida de concordância (κ de Cohen), resolução de divergência | 3 | Triagem | Ativa dupla triagem e o cálculo de κ |
| **5. Extração** — perguntas tipadas (texto / numérico / categórico / múltipla escolha), piloto, conferência | 4 | Extração | Define o formulário e valida a resposta da IA |
| **6. Apreciação crítica** — instrumento (§13.2), quem aplica, o que se faz com o resultado (excluir? ponderar? só descrever?) | 5 | Extração / Triagem | Instancia o instrumento por estudo (resolve **P-11**) |
| **7. Síntese** — tipo (narrativa / tabular / temática / metanálise / bibliométrica), agrupamentos, heterogeneidade | 6 | Indicadores / Exportação | Define os agrupamentos da aba de Indicadores |
| **8. Certeza e vieses do corpo** — GRADE / CERQual, viés de publicação | 7 | Exportação | Bloco do relatório |
| **9. Redação e emendas** — seções do manuscrito + log de emendas (§12) | 8 | Exportação | Gera o documento |

Cada seção é ligada aos itens da diretriz de relato ativa via o mesmo mecanismo
`fieldKey` que já existe (`protocolCatalog.ts:59-71`) — que é a razão de esse
mecanismo ser preservado e não reescrito.

### 9.3 (c) Híbrido declarado

Combina um gabarito externo com seções do Protocolo Revsist, e **obriga** um
campo "diretriz efetivamente seguida", que aparece na exportação. É o que hoje a
entrada `Other` já pede em texto (`protocolCatalog.ts:471-472`), formalizado.

---

## 10. Estratégia de busca — canônica + adaptadores

Este é o item de maior retorno técnico do plano, porque resolve P-08 e P-09 ao
mesmo tempo.

### 10.1 O problema

Hoje o protocolo aceita apenas pares de até 2 termos, com erro 400 no backend
(`protocols.py:140-149`), **porque a BDTD não suporta booleanas complexas**. Uma
limitação de uma fonte tornou-se a gramática do protocolo. O efeito colateral é
que Scopus, PubMed e OpenAlex — que aceitam booleanas completas, truncamento e
busca por campo — são subutilizados, e o PRISMA-S item 3 (a *string* exata,
como executada, por base) é impossível de cumprir.

### 10.2 O modelo

```
Estratégia canônica  (independente de base)
  Bloco A "População"   : [termo, termo*, "expressão exata"]  ← OR interno
  Bloco B "Conceito"    : [...]                                ← OR interno
  Bloco C "Contexto"    : [...]                                ← OR interno
  Combinação: A AND B AND C          (editável)
  Campos-alvo: título | resumo | palavras-chave | todos
  Limites: anos, idiomas, tipos documentais, acesso aberto
        │
        ▼  adaptadores por base
┌───────────────────────────────────────────────────────────────────────┐
│ Scopus   → TITLE-ABS-KEY( (a1 OR a2) AND (b1 OR b2) ) AND PUBYEAR>... │
│ PubMed   → (a1[tiab] OR a2[tiab]) AND (b1[tiab] OR b2[tiab])          │
│ OpenAlex → filtros da API + busca de texto                            │
│ SciELO   → sintaxe suportada                                          │
│ BDTD     → decomposta em N consultas-par (a_i AND b_j), união          │
│            das listas + deduplicação — DECOMPOSIÇÃO DECLARADA          │
└───────────────────────────────────────────────────────────────────────┘
```

**A decomposição da BDTD passa a ser um fato registrado, não uma amputação
silenciosa.** O protocolo grava: "estratégia canônica X; na BDTD, executada como
6 consultas-par, unidas e deduplicadas, por limitação da interface da base" —
que é uma frase perfeitamente publicável, e é o que o PRISMA-S item 4
("adaptações da estratégia para cada base") pede.

### 10.3 Revisão da estratégia — PRESS

Um painel "Revisar estratégia" aplica os 6 domínios do **PRESS** (McGowan J,
Sampson M, Salzwedel DM, et al. J Clin Epidemiol. 2016;75:40-46): tradução da
pergunta, operadores booleanos e de proximidade, termos de assunto, termos de
texto livre, ortografia/sintaxe/limites, e ajuste geral. Disponível como
**checklist manual** e, se a IA estiver ativa, como sugestão — sempre rotulada
como sugestão, nunca aplicada sozinha.

### 10.4 Registro da execução

Cada disparo de coleta grava um `search_execution`: base, string exata enviada,
filtros efetivos, data/hora (UTC), nº de registros retornados, nº após
deduplicação, e erros. Duas consequências:

1. Os campos S12–S14 do modo Simplificado preenchem-se sozinhos;
2. O **fluxograma PRISMA** (`export.py:68`) passa a ter números com procedência,
   em vez de contagens derivadas do banco sem rastro da origem.

### 10.5 O **Registro de Busca** — documento exportável (decisão D-B)

**Decisão tomada (30/08/2026):** o modo Simplificado não exporta "relatório de
revisão sistemática", mas exporta um documento próprio — o **Registro de Busca**
—, cuja função é provar *como exatamente a busca foi feita em relação ao que
estava configurado*.

Isso é mais do que o "relatório de busca" que este plano havia proposto: não é um
resumo do que foi encontrado, é o **confronto entre o planejado e o executado**,
que é justamente o que o §10.4 passou a ter dado para sustentar e o que nenhuma
ferramenta do mercado entrega bem.

**Estrutura do documento — duas colunas por base:**

| | Configurado (protocolo) | Executado (registro) |
|---|---|---|
| Estratégia | Estratégia canônica: blocos, sinônimos, combinação | *String* exata enviada à base |
| Adaptação | Regra do adaptador (§10.2) | Nota de adaptação — ex.: decomposição BDTD em N pares |
| Campos-alvo | título / resumo / palavras-chave / todos | Campos efetivamente aceitos pela base |
| Limites | Anos, idiomas, tipos documentais, acesso aberto | Filtros efetivamente aplicados |
| Momento | — | **Data e hora em UTC** de cada disparo |
| Volume | — | Registros retornados · após deduplicação · erros |

Acompanham o documento: identificação do projeto, desenho, versão do protocolo e
**hash** (§12.1), a justificativa da escolha das bases (S5), os métodos
complementares declarados (S9), a regra de deduplicação (S14) e o carimbo de
escopo (§8.4).

**Formatos:** DOCX e PDF para anexar como apêndice de manuscrito ou depósito;
**CSV** da tabela por base; **JSON** para arquivamento e reimportação.

**Justificativa.** É a materialização direta dos itens 3, 4, 6, 14 e 15 do
PRISMA-S e do item 7 do PRISMA 2020 — os itens que hoje o Revsist é
*estruturalmente incapaz* de cumprir (P-08, P-09). Um apêndice de busca com a
*string* como executada, a data e a contagem por base é, na prática, o anexo que
periódicos e pareceristas pedem e que quase nenhuma submissão traz.

**Disponibilidade:** existe nos **dois modos**. No Completo é um apêndice do
protocolo; no Simplificado é o produto principal, junto do protocolo carimbado.

---

## 11. Bibliometria (D11) — bloco próprio

> **O ambiente que executa este bloco** está especificado na série
> [47](./47_DIAGNOSTICO_BIBLIOMETRIA.md) →
> [48](./48_ESPECIFICACAO_AMBIENTE_INDICADORES.md) →
> [49](./49_PLANO_EXECUCAO_BIBLIOMETRIA.md). O pré-registro do plano
> bibliométrico — indicadores previstos, unidade de análise, janela, tesauro e
> cortes declarados antes de ver resultado — reaproveita o versionamento e as
> emendas do §12 deste documento (doc 48 §11).

### 11.1 Por que não é uma revisão sistemática com outro nome

Uma bibliometria não avalia estudos: avalia **registros**. Não há risco de viés
por estudo; há **cobertura e limpeza da base**. Não há síntese de achados; há
**indicadores e mapas**. Aplicar-lhe a checklist do PRISMA 2020 produz um
documento que responde a perguntas que não se aplicam — que é o que aconteceria
hoje, já que D11 simplesmente não existe no enum (P-12).

### 11.2 Campos do protocolo bibliométrico

Espinha: **BIBLIO** (20 itens: título 2, resumo 1, introdução 2, métodos 7,
resultados 4, discussão 4), com a parte de consulta detalhada pelo **PRISMA-S** e
o fluxo de trabalho de **Zupic & Čater (2015)**.

| Bloco | Campos |
|---|---|
| **Fonte de dados** | Base única ou combinada (Scopus / WoS / OpenAlex / Lens / SciELO); **justificativa da escolha**; cobertura e limitações conhecidas da base |
| **Extração** | *Query* exata; campos consultados; filtros de tipo documental e idioma; **data e hora da extração**; versão/snapshot; nº de registros exportados; formato do arquivo |
| **Tratamento** | Deduplicação; **regras de desambiguação** de autores, instituições e países; tesauro/normalização de palavras-chave; termos excluídos |
| **Análise** | Unidade de análise (documento, autor, fonte, palavra, instituição, país); técnica (produção, coautoria, cocitação, acoplamento bibliográfico, coocorrência de termos); **limiares** (ocorrência mínima, top-N); algoritmo e resolução de clusterização; medidas de rede |
| **Ferramentas** | Software e **versão** (VOSviewer, bibliometrix/R, CiteSpace, Bibliometrix Biblioshiny) |
| **Limitações** | Cobertura da base, viés de idioma, viés de indexação, janela de citação |

### 11.3 Decisões justificadas

- **Sem apreciação crítica por estudo.** Não há instrumento consagrado, e forçar
  um seria teatro metodológico. O que substitui é o bloco *Tratamento*: em
  bibliometria a validade está na procedência e limpeza do dado.
- **Data e hora da extração são obrigatórias, não opcionais.** Bases de citação
  mudam diariamente; sem *timestamp* o estudo é irreprodutível por construção.
  É o item mais citado como falha nas revisões de qualidade de bibliometrias.
- **Limiares são campo do protocolo, não parâmetro de tela.** "Mínimo de 5
  ocorrências" muda o mapa inteiro; declarado *a priori*, deixa de ser uma
  escolha estética feita depois de ver o resultado.
- **Ligação com a aba de Indicadores.** Os campos *Análise* configuram
  diretamente `insights_service.py`. Onde o Revsist ainda não calcula o
  indicador (cocitação, acoplamento), o protocolo grava a intenção e a exportação
  aponta a ferramenta externa — honesto e útil, em vez de campo morto.
- **Methodi Ordinatio (D12) é vizinho, não sinônimo.** Ordena portfólio via
  InOrdinatio; herda os blocos *Fonte* e *Extração* de D11 e acrescenta os pesos
  α da equação e a versão do método (2015 ou 2.0/2022, que admite pesos
  flexíveis e estimação do fator de impacto ausente).

---

## 12. Versionamento, congelamento e emendas

Resolve **P-05**, o achado mais grave.

### 12.1 Ciclo

```
Rascunho ──[Congelar v1.0]──► Vigente ──[Emenda]──► v1.1 ──► ... ──► Concluído
   │                             │
   └── edição livre              └── edição exige justificativa registrada
```

- **Congelamento** gera um `protocol_version`: JSON completo, `SHA-256` do
  conteúdo, rótulo, autor e data. É oferecido (não imposto) **antes da primeira
  coleta** — o momento em que "a priori" deixa de ser possível.
- **Emenda** exige: o que mudou (diff automático), **por quê**, em que fase do
  projeto, e quem autorizou. Gera nova versão.
- **Exportação** imprime o histórico e o hash da versão citada.

### 12.2 Justificativa

PRISMA-P item 3 exige registro de emendas; PRISMA 2020 item 24c exige descrever
e explicar emendas ao registro; o JBI Manual coloca o protocolo *a priori* como
requisito central; MECIR e MECCIR exigem protocolo revisado antes da busca. Nada
disso é satisfeito por um `updated_at` sobrescrito. Além do valor metodológico,
o histórico é a defesa do pesquisador na revisão por pares quando perguntarem
*"vocês mudaram os critérios depois de ver os resultados?"*.

### 12.3 Exportação do protocolo

Novo endpoint e nova aba, com **dois documentos distintos**:

1. **Protocolo** — em **DOCX/PDF** na estrutura do gabarito ativo, pronto para
   anexar a uma submissão PROSPERO ou a um depósito OSF, e em **JSON** para
   arquivamento e reimportação. Inclui identificação, data de congelamento, hash,
   histórico de emendas e a auditoria da checklist (§13.1).
2. **Registro de Busca** (§10.5, decisão D-B) — o confronto entre o configurado e
   o executado, por base. Disponível nos dois modos; no Simplificado é o produto
   principal.

---

## 13. Prontidão do protocolo, auditoria e instrumentos

### 13.1 Medidor de prontidão e portões por etapa

Cada etapa do pipeline declara o que o protocolo precisa ter:

| Etapa | Exige | Observação |
|---|---|---|
| Coleta | ≥1 bloco de conceito com ≥1 termo; ≥1 base selecionada | |
| Triagem | ≥1 critério de inclusão | Satisfeito por S10 |
| Extração | ≥1 pergunta de extração | **Sempre satisfeito** — S11 é obrigatório no núcleo (D-C) |
| Indicadores | (D11) unidade de análise e limiares declarados | |
| Registro de Busca | ≥1 execução de coleta registrada | §10.5 |
| Exportação de relatório | Auditoria da checklist preenchida | |

**Regra:** o portão **avisa e explica**; só bloqueia quando a execução é
tecnicamente impossível (buscar sem termo). Rigor imposto por trava produz
usuários que preenchem lixo para destravar. O que produz rigor é a **visibilidade
da lacuna** — o medidor mostra "13 de 22 itens do PRISMA-ScR com conteúdo" — e o
carimbo em toda exportação.

A auditoria da checklist passa a ser **persistida** (resolve P-06), com estado
por item: `atendido` / `não se aplica (+ justificativa)` / `pendente`, e o número
da página ou seção onde o item foi atendido — que é o formato em que o PRISMA
2020 pede a checklist submetida.

### 13.2 Apreciação crítica como instrumento

`critical_appraisal` deixa de ser texto (P-11) e passa a ser: **instrumento
escolhido** + **política de uso** + **aplicação por estudo**.

| Instrumento | Para | Fonte |
|---|---|---|
| RoB 2 | Ensaios randomizados | Sterne et al., BMJ 2019;366:l4898 |
| ROBINS-I | Não randomizados de intervenção | Sterne et al., BMJ 2016;355:i4919 |
| JBI Critical Appraisal | Por desenho (13 instrumentos) | JBI Manual 2024 |
| MMAT 2018 | Métodos mistos | Hong et al. |
| AMSTAR 2 / ROBIS | Revisões (D6) | Shea et al. 2017 / Whiting et al. 2016 |
| CASP | Qualitativo (D3) | CASP UK |
| Critérios EBSE | Engenharia de Software (D9) | Kitchenham & Charters 2007 |
| InOrdinatio | Portfólio (D12) | Pagani et al. 2015 / 2.0 |
| Nenhum (declarado) | D4, D5, D11 | PRISMA-ScR i12 |

A **política de uso** é campo obrigatório quando há instrumento: o resultado
serve para excluir estudos, para ponderar a síntese, ou apenas para descrever?
Diretrizes divergem, e deixar isso implícito é fonte conhecida de crítica em
revisão por pares.

> ⚠️ **Devida diligência de licenciamento (Fase 7).** O texto integral dos
> itens de RoB 2, AMSTAR 2, MMAT e dos instrumentos JBI tem condições de uso
> próprias. Antes de embutir texto literal, verificar cada licença; onde não for
> permitido, embutir **a estrutura de domínios e o link oficial**, não o texto.
> A mesma verificação vale retroativamente para as checklists já embarcadas em
> `protocolChecklists.ts` (PRISMA é CC BY; ROSES e PRIOR precisam de conferência).

---

## 14. Modelo de dados e migração

### 14.1 Alterações

```python
# protocols
mode                 : str   # 'simplificado' | 'completo'          NOT NULL default 'simplificado'
review_design        : str   # 'D1'..'D14'                          NOT NULL default 'D4'
reporting_guideline  : str   # 'PRISMA-2020' | 'PRISMA-ScR' | ...   NOT NULL
conduct_standards    : Text  # JSON list                            default '[]'
question_framework   : Text  # JSON tipado (§7)                     default '{}'
appraisal            : Text  # JSON {instrument, policy, notes}     default '{}'
synthesis            : Text  # JSON {type, groupings, params}       default '{}'
bibliometrics        : Text  # JSON (§11.2)                         default '{}'
status               : str   # 'rascunho'|'vigente'|'concluido'     default 'rascunho'
current_version      : str   # rótulo, ex. 'v1.2'                   nullable

# NOVA — search_strategies      (1 canônica + n adaptações por base)
id, protocol_id, kind('canonica'|'adaptacao'), database, blocks(JSON),
combination(str), target_fields(JSON), limits(JSON), rendered_query(Text),
adaptation_note(Text), updated_at

# NOVA — search_executions       (§10.4)
id, protocol_id, harvest_run_id, database, query_sent(Text), filters(JSON),
executed_at(UTC), records_returned(int), records_after_dedup(int), error(Text)

# NOVA — protocol_versions       (§12.1)
id, protocol_id, label, snapshot(JSON), content_hash(sha256), frozen_at,
frozen_by_user_id

# NOVA — protocol_amendments
id, protocol_id, from_version, to_version, diff(JSON), reason(Text),
project_phase(str), created_at, created_by_user_id

# NOVA — checklist_audit         (§13.1, resolve P-06)
id, protocol_id, guideline, item_id, state('atendido'|'nao_aplica'|'pendente'),
location(str), justification(Text), updated_at, updated_by_user_id

# ALTERADA — criteria
+ dimension(str)   # 'populacao'|'desenho'|'periodo'|'idioma'|'tipo_doc'|'contexto'|'outro'
+ applies_at(str)  # 'titulo_resumo' | 'texto_completo' | 'ambos'

# ALTERADA — extraction_questions
+ answer_type(str) # 'texto'|'numero'|'categoria'|'multipla'|'booleano'
+ options(JSON)
+ required(bool)
```

### 14.2 Migração retrocompatível de `projects.methodology`

`methodology` **permanece** (não se quebra API nem projetos existentes) e passa a
ser um campo derivado/legado. Migração Alembic determinística:

| `methodology` atual | → `review_design` | → `reporting_guideline` | → `conduct_standards` |
|---|---|---|---|
| `PRISMA-ScR` | D4 | PRISMA-ScR | [] |
| `PRISMA-2020` | D1 | PRISMA-2020 | [] |
| `PRISMA-P` | D1 | PRISMA-2020 | [] *(+ gabarito PRISMA-P no modo Completo)* |
| `Cochrane` | D1 | PRISMA-2020 | `["Cochrane/MECIR"]` |
| `Campbell` | D1 | PRISMA-2020 | `["Campbell/MECCIR"]` |
| `JBI (Scoping/Systematic)` | D4 | PRISMA-ScR | `["JBI"]` |
| `CEE/ROSES` | D5 | ROSES | `["CEE v5.1"]` |
| `EBSE` | D9 | EBSE | `["Kitchenham & Charters"]` |
| `Umbrella Review` | D6 | PRIOR | `["JBI Umbrella"]` |
| `Methodi Ordinatio` | D12 | Genérico | `["Methodi Ordinatio"]` |
| `Other` | D14 | Genérico | [] |

Todo protocolo existente nasce em **`mode='completo'`** (já preencheram campos de
manuscrito) e **`status='rascunho'`**, sem versão congelada. Nenhum dado é
perdido; `manuscript_sections` continua sendo lido pelas seções do §9.

---

## 15. Contratos de API

```
GET    /projects/{id}/protocol                     (estendido)
PUT    /projects/{id}/protocol                     (estendido, mantém If-Match)
GET    /protocol-catalog                           designs, guidelines, standards, frameworks, instruments
POST   /projects/{id}/protocol/mode                { mode }  → migração §8.5
POST   /projects/{id}/protocol/design              { design } → devolve derivações sugeridas

GET    /projects/{id}/protocol/search-strategy
PUT    /projects/{id}/protocol/search-strategy      canônica
POST   /projects/{id}/protocol/search-strategy/render  { database } → string adaptada
POST   /projects/{id}/protocol/search-strategy/press   revisão PRESS (heurística; IA opcional)

GET    /projects/{id}/protocol/readiness            medidor + portões (§13.1)
GET/PUT /projects/{id}/protocol/checklist-audit     (§13.1)

POST   /projects/{id}/protocol/freeze               { label } → congela
GET    /projects/{id}/protocol/versions
GET    /projects/{id}/protocol/versions/{v}
POST   /projects/{id}/protocol/amendments           { reason, phase }
GET    /projects/{id}/protocol/export?format=docx|pdf|json|prospero
GET    /projects/{id}/protocol/search-record?format=docx|pdf|csv|json   Registro de Busca (§10.5)
```

Preservados sem alteração: `projeto_do_usuario` como dependência do router,
`exige_escrita_protocolo`, `If-Match`/409 e o `ws_manager.broadcast` de
`protocolo.alterado` — as três garantias que o doc 43 estabeleceu.
`freeze` e `amendments` emitem eventos próprios no mesmo canal.

---

## 16. Interface

### 16.1 Estúdio em modo Simplificado

Página única, sem abas, **14 campos** (§8.2), com o medidor de prontidão e o
botão "Executar busca" ao final. Tempo alvo até a primeira coleta:
**< 5 minutos** — sustentado, apesar de S11, pelas três mitigações do §8.3
(conjunto sugerido por desenho, sugestão por IA e tipagem adiada para o
Completo). Ao final da primeira coleta, o botão **"Exportar Registro de Busca"**
(§10.5) aparece na mesma página.

### 16.2 Estúdio em modo Completo

Abas atuais preservadas (`StudioTab`) com duas mudanças:

- ordem e rótulos **derivam do gabarito ativo**, em vez de serem fixos em formato
  PRISMA-ScR — o que resolve o problema já admitido em `protocolCatalog.ts:243-246`
  ("forçar um mapeamento para diretrizes de outro formato exibiria número errado");
- nova aba **Estratégia de Busca** (§10) e nova aba **Versões e Emendas** (§12).

### 16.3 Elementos novos

- **Assistente de Escolha do Desenho** (§5.3), na criação do projeto e reabrível.
- **Cartão do desenho** no topo do Estúdio: desenho, diretriz, padrões,
  elegibilidade de registro, e o que é obrigatório neste desenho.
- **Medidor de prontidão** persistente, com link direto para cada lacuna.
- **Alternador de modo** com o aviso de não-destrutividade do §8.5.

### 16.4 IA

A sugestão de protocolo (`/ai/suggest-protocol`) passa a receber `review_design`,
`reporting_guideline` e `mode`, e a devolver estrutura compatível com o gabarito
ativo — hoje ela devolve um formato único independentemente da metodologia.
Toda saída continua rotulada como sugestão editável, nunca aplicada sozinha.

---

## 17. Plano de execução

| Fase | Entrega | Critério de aceite |
|---|---|---|
| **F0** | ✅ **Concluída (30/08/2026)** — documento validado; as quatro decisões do §19.1 fechadas | Aprovação do responsável |
| **F1** | Modelo de dados (§14) + migração Alembic + schemas Pydantic + catálogo servido pela API | Migração ida-e-volta sobre banco real sem perda; todos os projetos existentes mapeados; suíte atual verde |
| **F2** | **Modo Simplificado** completo — 14 campos, incluindo perguntas de extração com conjunto sugerido por desenho (§8.3) — + medidor e portões (§13.1) + carimbo de escopo | Projeto novo vai de zero a coleta em < 5 min **com S11 preenchido**; toda exportação carrega o carimbo |
| **F3** | Catálogo de desenhos D1, D2, D4, D6, D11, D12, D14 + derivação + Assistente (§5.3) + **Protocolo Revsist** (§9.2) | Cada desenho abre com framework, diretriz e obrigatoriedades corretos; troca de desenho não perde dado |
| **F3b** | Desenhos D3, D5, D7, D8, D9, D10, D13 + gabaritos externos restantes (§9.1) | Idem |
| **F4** | **Estratégia canônica + adaptadores + PRESS + registro de execução + Registro de Busca exportável** (§10, §10.5) | *String* executada em Scopus reproduz o resultado ao ser colada na base; decomposição BDTD registrada; fluxograma PRISMA com números de procedência; **Registro de Busca em DOCX/PDF/CSV/JSON com as colunas configurado × executado** |
| **F5** | **Bibliometria D11** (§11) + ligação com Indicadores | Protocolo bibliométrico completo exportável em BIBLIO; *timestamp* de extração obrigatório |
| **F6** | **Versionamento, congelamento, emendas, exportação** (§12) | Congelar → editar → emenda gera v1.1 com diff e justificativa; DOCX abre no Word com a estrutura do gabarito |
| **F7** | **Apreciação crítica instrumentada** (§13.2) + GRADE/CERQual + devida diligência de licenças | Instrumento aplicável por estudo; nenhum texto embutido sem licença verificada |
| **F8** | Testes, validação com corpus real, documentação (docs 17 e 00) | §18 integralmente atendido |

**Sequenciamento.** F1 → F2 é o caminho crítico e entrega valor sozinho (o modo
Simplificado é a demanda direta do usuário). F4 pode correr em paralelo a F3 —
é o mais independente e o de maior impacto na qualidade da coleta. F6 e F7 não
bloqueiam nada e podem ser adiadas sem prejuízo às anteriores.

---

## 18. Testes e validação

**Automatizados** (estendendo `backend/tests/`):

- Migração: cada um dos 11 valores de `methodology` → tripla correta (§14.2);
- Renderização da estratégia: caso conhecido por base, com *snapshot*, incluindo
  a decomposição BDTD em N pares e a união deduplicada;
- Portões: cada etapa recusa/avisa exatamente nas condições do §13.1;
- Versionamento: congelar → editar → emendar produz diff e hash estáveis;
- Isolamento multi-inquilino: os testes de `test_tenancy_isolation.py` estendidos
  às cinco tabelas novas — **sem exceção**;
- Concorrência: `If-Match`/409 preservado nos novos endpoints.

**Validação metodológica** — reconstruir no Revsist, e comparar com o publicado:

1. **Leal et al.** (PRISMA, Scopus + WoS, desenvolvimento regional, 2019–2023) →
   D1 em modo Completo. Verifica se o Revsist produz o protocolo que aquela
   revisão de fato usou, num domínio **não clínico**.
2. Uma revisão de escopo publicada com protocolo em OSF → D4, conferindo os 22
   itens do PRISMA-ScR.
3. Uma bibliometria publicada com VOSviewer → D11, conferindo os 20 itens do
   BIBLIO e a presença de todos os campos de reprodutibilidade do §11.2.

**Validação com usuário:** um pesquisador que nunca usou o Revsist vai de zero a
coleta em modo Simplificado sem ajuda, e depois migra para Completo sem perder
nada.

---

## 19. Decisões tomadas e riscos

### 19.1 Decisões — **as quatro estão fechadas (30/08/2026)**

| # | Questão | Decisão | Onde vive |
|---|---|---|---|
| **D-A** | Congelar o protocolo antes da primeira coleta: obrigatório ou oferecido? | ✅ **Oferecido**, com aviso persistente enquanto não houver versão congelada. Obrigar criaria congelamentos vazios só para destravar. | §12.1 |
| **D-B** | O modo Simplificado exporta o quê? | ✅ **A configuração de busca**, para registro de como exatamente a busca foi feita em relação ao configurado. Vai além do "relatório de busca" proposto: é o confronto **configurado × executado**, por base. | **§10.5** (novo) |
| **D-C** | Perguntas de extração: *just-in-time* ou dentro do formulário? | ✅ **Dentro do formulário**, para garantir o planejamento. Reverte a proposta original; ancorada em PRISMA-P i12 e PRISMA 2020 i10a. | **§8.2 (S11), §8.3** |
| **D-D** | Depreciar `projects.methodology` numa fase futura? | ✅ **Manter como campo derivado** por ora; reavaliar após a F3, com dados de uso. | §14.2 |

### 19.2 Riscos

| # | Risco | Encaminhamento |
|---|---|---|
| R-01 | **Excesso de engenharia.** 14 desenhos × 11 diretrizes × 7 padrões é combinatória grande demais para manter. | Fase 3 entrega 7 desenhos. Um desenho novo só entra com caso de uso real. Frameworks e diretrizes são **dados**, não código (§7). |
| R-02 | **Deriva das diretrizes.** PRISMA 2020 e JBI são atualizados; texto embutido envelhece. | Cada checklist ganha `version` e `retrieved_at` visíveis; conferência anual entra no doc 00. |
| R-03 | **Licenciamento de instrumentos** (§13.2). | Devida diligência na F7, **incluindo revisão retroativa** do que já está em `protocolChecklists.ts`. |
| R-04 | **A adaptação BDTD pode alterar o recall** em relação à canônica. | Registrar a decomposição, medir a diferença em um corpus de teste e **documentar como limitação**, não escondê-la. |
| R-05 | **Migração de banco em produção.** | Migração idempotente, ensaio em cópia do banco real, rollback documentado; nenhuma coluna existente é removida. |
| R-06 | O Revsist não é um *registro* de protocolos. | Explicitado na interface: o app **gera** o documento; o registro é feito pelo pesquisador em PROSPERO/OSF. |
| R-07 | **S11 atrasa a primeira coleta** (decorrente de D-C). | Conjunto sugerido por desenho, sugestão por IA e tipagem adiada para o Completo (§8.3). Medir o tempo real no teste com usuário da F8; se a meta de 5 min cair, reabrir D-C. |

---

## 20. Referências

Além das listadas nos §3.1–3.6, os documentos internos que este plano toca:
[08 — Pipeline de Dados](./08_PIPELINE_DADOS.md),
[10 — Banco de Dados](./10_BANCO_DE_DADOS.md),
[14 — Especificação da Coleta](./14_ESPECIFICACAO_COLETA.md),
[17 — Guia de Uso](./17_GUIA_DE_USO.md),
[31–33 — B.I. e Bibliometria](./32_ESPECIFICACAO_BI.md),
[43 — Especificação da Pesquisa em Equipe](./43_ESPECIFICACAO_PESQUISA_EM_EQUIPE.md).
