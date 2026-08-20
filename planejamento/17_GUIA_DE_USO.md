# 17 — Guia de Uso: o que o RSAC V2 deve ser

> **Objetivo:** descrever o produto do ponto de vista de quem faz a revisão.
> Serve como referência de intenção — quando uma decisão técnica for ambígua,
> a pergunta é "o que ajuda o pesquisador a concluir a revisão?".
>
> ⚠️ Este documento descreve o **estado-alvo**, depois de executado
> `15_PLANO_EXECUCAO.md`. As seções marcadas 🚧 ainda não funcionam assim.

---

## 17.1 O que o RSAC é

Uma aplicação **desktop, offline-first, mono-usuário** que conduz uma revisão
sistemática ou de escopo do começo ao fim: do protocolo à planilha final e ao
diagrama PRISMA.

O que ele resolve é um problema concreto e chato: uma revisão séria exige buscar
em várias bases, com o mesmo recorte, registrar tudo o que foi feito, eliminar
duplicatas entre bases, triar centenas ou milhares de resumos contra critérios
declarados, e depois provar cada número. Feito à mão, isso consome semanas e
produz planilhas que ninguém consegue auditar depois.

**A V1 automatizou a coleta.** Cinco scripts Python, um por base, cada um com seu
JSON de configuração, seu SQLite e seu Excel. Funciona bem — mas unificar os
cinco resultados, triar e montar o PRISMA continua sendo trabalho manual.

**A V2 automatiza a revisão inteira.** Mesma qualidade de coleta, mas dentro de
um projeto único, com deduplicação entre bases, triagem assistida por IA,
extração de dados e exportação pronta para publicação.

### Princípios do produto

1. **O pesquisador decide, a IA sugere.** Toda decisão de inclusão/exclusão é
   revisável e atribuível. A IA acelera a triagem; não a substitui.
2. **Tudo é auditável.** Qual descritor recuperou cada estudo, qual critério
   excluiu, quem decidiu, quando. O `AuditLogModel` existe para isso.
3. **Reprodutível.** Mesmo protocolo, mesma data, mesma base → mesmo conjunto.
   É por isso que a coleta ordena por ano e nunca por relevância (§14.1).
4. **Offline-first.** Os dados ficam na máquina. Só coleta e IA precisam de rede.
5. **Honesto sobre limites.** Se um filtro foi aplicado localmente e não na base,
   o relatório diz isso. Um método descrito errado invalida a publicação.

### Quem usa

Pesquisador de **Ciências Sociais Aplicadas e Desenvolvimento Regional**
(`.agents/AGENTS.md`): políticas públicas territoriais, arranjos produtivos
locais, governança regional, planejamento urbano. Fluente no método, **não**
programador. Nunca deve precisar editar JSON, abrir terminal ou ler log.

Isso tem consequência direta de design: **erro técnico precisa virar mensagem
acionável.** "Scopus requer chave de API. Configure em Configurações → Bases de
Dados." é aceitável; `HTTP 401 Unauthorized` não é.

---

## 17.2 O fluxo completo

```
1. Projeto  →  2. Protocolo  →  3. Coleta  →  4. Triagem  →  5. Extração  →  6. Exportação
                     ↑                            │
                     └──── refinar e recoletar ───┘
```

O ciclo de volta é normal e esperado: a primeira coleta quase sempre revela que
os descritores estão amplos ou estreitos demais. O app precisa tornar esse
refinamento barato — e a coleta idempotente (§14.1) é o que permite recoletar sem
duplicar.

---

## 17.2.1 Acesso: como o app sabe quem é você

A API exige identificação. Como isso aparece depende de onde o RSAC está
rodando.

**No aplicativo de mesa (Electron) e na interface local** não aparece nada: no
primeiro start o backend sorteia um token e o grava em um arquivo legível
apenas pelo seu usuário (`runtime_token`, na pasta de dados do app). O
aplicativo lê esse arquivo e entra sozinho. Quem não tem acesso ao seu sistema
de arquivos não consegue produzi-lo.

**No modo servidor** (`Iniciar_Servidor.bat`) o acesso é por usuário e senha.
Antes de abrir o túnel, o lançador verifica se existe conta; se não existir,
pede o nome de usuário e cria a primeira. A senha é sorteada e mostrada **uma
única vez** — anote-a.

Para criar contas a qualquer momento, no computador que hospeda o servidor:

```bash
cd backend
python -m app.cli create-user nome_do_usuario --role researcher
python -m app.cli list-users
python -m app.cli reset-password nome_do_usuario
```

### Os dois papéis

| Papel | Pode |
|---|---|
| `owner` | Tudo: operar a revisão, gerir contas, ver e trocar as chaves de API |
| `researcher` | Operar a revisão — coletar, triar, extrair, exportar. **Não** alcança as chaves de API, nem mascaradas |

Convide colaboradores como `researcher`. É a diferença entre dar acesso ao
trabalho e dar acesso às suas credenciais de API.

### Por que isso importa para a revisão, não só para a segurança

Cada decisão de triagem passa a registrar **quem** a tomou. Antes, o log de
auditoria dizia apenas "manual" — o que, num servidor com duas pessoas, não
distinguia o seu julgamento do julgamento do coautor. Numa revisão sistemática,
cuja entrega é a reprodutibilidade do processo, isso é parte do produto.

O nome da conta ativa fica visível na barra de status, ao lado do botão de
sair.

---

## 17.3 Etapa 1 — Projeto

**Tela:** `ProjectsPage`

Um projeto é uma revisão. Título, descrição, metodologia (PRISMA-P, PRISMA-ScR).
Cada projeto tem seu protocolo, seu corpus e seus resultados, isolados dos demais.

Vale ter vários projetos simultâneos — típico de quem toca mais de uma frente.

---

## 17.4 Etapa 2 — Protocolo

**Tela:** `ProtocolPage` · **A etapa mais importante do produto.**

O protocolo é o que torna a revisão *sistemática*. Definido **antes** de coletar,
registrado, e qualquer alteração posterior fica datada.

### Objetivo e PICO

Pergunta de pesquisa e o enquadramento (População, Intervenção, Comparação,
Resultado — adaptado às Sociais Aplicadas). Alimenta os prompts da IA de triagem.

### Descritores de busca

Termos por idioma. Exemplo do domínio-alvo:

```
Português:  "desenvolvimento regional" AND "políticas públicas"
            "arranjos produtivos locais" AND "inovação"
            "governança territorial" AND "sustentabilidade"
Inglês:     "regional development" AND "public policy"
            "local productive arrangements" AND "innovation"
Espanhol:   "desarrollo regional" AND "políticas públicas"
```

`.agents/AGENTS.md` orienta: pares de 2 termos, até 5 pares por idioma. A razão
é prática — o motor VuFind da BDTD degrada com strings booleanas longas.

⚠️ Os configs reais da V1 usam **3 termos e 140 descritores**. Essa divergência
está registrada em §14.8 e **precisa de decisão do autor**. A postura recomendada
é a UI **avisar** sobre descritores com 3+ termos sem bloquear.

O botão de assistência por IA sugere descritores a partir do objetivo e do PICO,
seguindo as regras do `AGENTS.md` — mas quem aprova é o pesquisador.

### 🚧 Recorte da busca — a lacuna mais sentida hoje

O bloco que **falta** na V2 e existe na V1 (§14.8):

| Campo | Exemplo |
|---|---|
| Período | 1970 – 2023 |
| Idiomas | Português, Inglês, Espanhol |
| Tipos | Tese, Dissertação, Artigo |
| Instituições | *(vazio = todas)* |
| Apenas acesso aberto | não |

Definido **uma vez**, aplicado a **todas** as bases. Na V1, o mesmo recorte
precisava ser repetido em cinco arquivos JSON — e um esquecimento em um deles
corrompia silenciosamente a revisão.

A tela deve deixar claro, por base, quando o filtro será aplicado **depois** de
baixar (pós-filtro local), porque isso muda o tempo de coleta. Exemplo:
*"Idioma na BDTD é filtrado após o download (limitação do servidor). A coleta
baixa mais registros do que o resultado final."*

### Critérios de inclusão e exclusão

Cada critério é uma pergunta binária avaliada contra cada estudo:

- *Inclusão:* "O estudo trata de desenvolvimento regional em contexto brasileiro?"
- *Exclusão:* "O estudo é anterior a 2010?"

A IA responde a cada critério individualmente e justifica. É isso que torna a
triagem auditável — não existe "excluído" sem motivo registrado.

### Perguntas de extração

O que se quer extrair dos estudos incluídos: "Qual o recorte territorial?",
"Qual metodologia foi empregada?", "Quais indicadores foram usados?".

### Seções do manuscrito

Os 22 itens do PRISMA-ScR, preenchíveis com apoio da IA. Vão para a exportação
final.

---

## 17.5 Etapa 3 — Coleta

**Tela:** `HarvestPage` · **A etapa que hoje não funciona (doc 13).**

### Como deve ser

1. **Escolher as bases.** BDTD, SciELO, OpenAlex, PubMed, Scopus. Bases que
   exigem chave aparecem desabilitadas até serem configuradas — nunca
   selecionáveis para depois retornar zero em silêncio.

2. **Conferir o recorte.** Resumo do que vem do protocolo, com aviso claro sobre
   pós-filtros locais.

3. **Escolher o volume.** *Ilimitado* é o padrão do uso real e precisa funcionar
   de verdade — hoje o PubMed trava em 500 e o OpenAlex em 10.000 (§13.3).

4. **Modo rápido (opcional).** Sem raspagem de detalhes: mais rápido, mas sem
   orientador nem instituição de defesa na BDTD. O app deve dizer exatamente o
   que se perde.

5. **Iniciar.** E a partir daí, **ver o que está acontecendo**:

```
[BDTD]     descritor 37/140  ·  página 12  ·  2.847 recuperados  ·  1.903 novos
[SciELO]   descritor 12/140  ·  página  3  ·    412 recuperados  ·    380 novos
[OpenAlex] concluído         ·                5.201 recuperados  ·  4.115 novos
```

Progresso por descritor, por página, com contadores. Em coletas de horas, o
usuário precisa saber que **há** avanço. Hoje a tela fica estática (P0-2) — é o
sintoma que mais fez a V2 parecer quebrada.

6. **Poder cancelar.** E retomar depois de onde parou.

7. **Recoletar sem medo.** Rodar de novo não duplica: registros já conhecidos são
   reconhecidos e apenas atualizados.

### Deduplicação

Rodando durante a coleta, em três passos: DOI exato → título normalizado →
similaridade fuzzy com verificação de ano. Um estudo encontrado na BDTD e no
OpenAlex vira **um** paper com **duas** fontes registradas — e o `PaperSourceModel`
guarda em quais bases apareceu, número que o PRISMA exige.

### O que fica registrado em cada execução

- Descritores e recorte efetivamente usados (não os do protocolo hoje — os de
  quando rodou)
- Registros recuperados, novos e duplicados, por base
- Filtros aplicados localmente em vez de nativamente
- Erros por base, em português

---

## 17.6 Etapa 4 — Triagem

**Tela:** `ScreeningPage`

Cada estudo é avaliado contra os critérios do protocolo — a partir de título,
resumo e metadados.

**É por isso que a qualidade dos metadados importa tanto.** Um resumo corrompido
(P0-5, BDTD) ou vazio (P1-6, Scopus) faz a IA decidir só pelo título. A triagem
é o gargalo do produto, e ela é tão boa quanto o que a coleta entregou.

### Como deve funcionar

- **Triagem em lote por IA**, com concorrência controlada e progresso visível
- **Por critério, com justificativa** — não um veredito opaco
- **Confiança declarada**; casos de baixa confiança sobem para revisão manual
- **Revisão humana** sempre disponível: incluir, excluir, marcar para discussão
- **Toda alteração vira log de auditoria** com origem (`manual` ou `ai`)

O pesquisador deve conseguir varrer 2.000 estudos triados pela IA revisando com
atenção os ~200 duvidosos — não revisando os 2.000.

---

## 17.7 Etapa 5 — Extração

**Tela:** `ExtractionPage`

Para os estudos incluídos, responder às perguntas de extração. A IA lê o PDF
(quando disponível) ou o resumo e propõe respostas; o pesquisador valida.

Aqui o texto completo importa: o `pdf_service` extrai texto via PyMuPDF e o
`download_url` correto (coletado na Etapa 3) é o que permite chegar ao PDF.
Mais um caso em que a qualidade da coleta se propaga adiante.

---

## 17.8 Etapa 6 — Exportação

**Tela:** `ExportPage`

- **Excel** com abas: estudos incluídos, excluídos com motivo, extração, métricas
  PRISMA. Deve incluir `advisor` e `matched_descriptor`, hoje ausentes.
- **BibTeX** dos incluídos, para o gerenciador de referências.
- **Diagrama PRISMA 2020** com números que batem com o banco.

⚠️ O diagrama precisa distinguir **excluído na triagem** de **não elegível por
recorte** (removido por pós-filtro local). Confundir os dois descreve o método
errado — e isso reprova em revisão por pares.

---

## 17.9 Configurações

**Tela:** `SettingsPage`

- **IA:** provedor (Gemini, OpenAI-compatível, local), modelo, chaves, temperatura
- **🚧 Bases de dados:** chaves de API por base (§14.7). Não existe hoje — é a
  razão pela qual o Scopus retorna zero em silêncio (P0-4).
- **Aparência:** 13 temas de cor
- **Armazenamento:** onde ficam banco e PDFs

Regra firme: **nenhuma chave é devolvida pela API em texto claro.** A tela mostra
"configurada · ••••1234" e permite substituir. Isso vem de uma lição concreta —
a V1 tem duas chaves de API versionadas no repositório (P2-6), que devem ser
revogadas independentemente desta migração.

---

## 17.10 Cenário completo

*Pesquisadora estudando arranjos produtivos locais no Sul do Brasil.*

1. Cria o projeto **"APLs e Desenvolvimento Regional no Sul do Brasil"**, PRISMA-ScR.
2. Preenche objetivo e PICO. Pede sugestões à IA, ajusta, aprova 12 descritores
   em três idiomas.
3. Define o recorte: **2010–2024**, `pt/en/es`, teses + dissertações + artigos.
4. Cadastra 4 critérios de inclusão e 3 de exclusão.
5. Seleciona **BDTD + SciELO + OpenAlex**, ilimitado, com detalhes. Inicia.
6. Acompanha o progresso; almoça; volta. **8.400 recuperados, 5.100 únicos.**
7. Dispara a triagem por IA. 4.200 excluídos com justificativa, 900 incluídos.
8. Revisa os 340 de baixa confiança. Reverte 60 exclusões.
9. Baixa PDFs dos incluídos; extrai as respostas com apoio da IA.
10. Exporta Excel + BibTeX + PRISMA. Escreve o artigo com os números prontos.

**Nada nesse cenário exige terminal, JSON ou log.** É esse o padrão.

Na V1, os passos 5–6 seriam: editar três JSON à mão com o mesmo recorte repetido,
rodar três scripts, obter três SQLite e três Excel — e começar aí o trabalho
manual de unificar. Os passos 7–10 não existiriam.

---

## 17.11 Onde a V2 está hoje

| Etapa | Estado |
|---|---|
| 1 · Projeto | ✅ funciona |
| 2 · Protocolo | ⚠️ funciona, **sem recorte de busca** (§14.8) |
| 3 · Coleta | ❌ **quebrada** — doc 13 |
| 4 · Triagem | ⚠️ funciona, prejudicada por metadados ruins |
| 5 · Extração | ⚠️ funciona, prejudicada por `download_url` incompleto |
| 6 · Exportação | ⚠️ funciona; `pandas` não declarado (P0-1); PRISMA incompleto |
| Configurações | ⚠️ IA sim; **bases não** (P0-4) |

A etapa 3 é a que trava tudo. É por isso que `15_PLANO_EXECUCAO.md` concentra
seis fases nela — e por isso a percepção "a V1 funciona e a V2 não" está correta
mesmo com a V2 tendo, no papel, muito mais recurso.

**O objetivo final não é empatar com a V1. É que a V1 deixe de ser necessária.**

---

**Documentos relacionados:**
[`13_DIAGNOSTICO_COLETA_V2.md`](./13_DIAGNOSTICO_COLETA_V2.md) ·
[`14_ESPECIFICACAO_COLETA.md`](./14_ESPECIFICACAO_COLETA.md) ·
[`15_PLANO_EXECUCAO.md`](./15_PLANO_EXECUCAO.md) ·
[`16_TESTES_VALIDACAO.md`](./16_TESTES_VALIDACAO.md)
