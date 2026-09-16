# 52 — Plano de Coleta de Dados de Uso do Beta

> **Documento único — diagnóstico, especificação e execução.** Mesma forma do
> doc 50.
> **Estado:** 🟡 em discussão — oito decisões em aberto (§11), todas com
> recomendação. A D-07 foi fechada em 15/09/2026: o beta dura **1 ano**, de
> 12/09/2026 a **12/09/2027**.
> **Aberto em:** 15/09/2026. **Revisto em 15/09/2026:** acrescentada a aba
> **Sistema** (§6.6), onde o controlador visualiza e gerencia os dados e o
> ciclo do beta.
> **Depende de:** docs 37 e 38 (LGPD), 40 (perfil `server`), 41 (serviço
> online), 51 (textos publicados de `/termos` e `/privacidade`).
> **Normas:** Lei nº 13.709/2018 (LGPD), texto compilado; Resolução CD/ANPD nº
> 2/2022 (agente de pequeno porte); Resolução CNS nº 510/2016 (pesquisa em
> ciências humanas e sociais), para o Nível C.
> **Fecha, quando executado:** o item **L-10** do doc 38 (teste de
> balanceamento do legítimo interesse para métricas).

---

## Sumário

1. [Por que este documento existe](#1-por-que-este-documento-existe)
2. [Princípios](#2-princípios)
3. [As perguntas que o beta precisa responder](#3-as-perguntas-que-o-beta-precisa-responder)
4. [Três níveis de coleta e suas bases legais](#4-três-níveis-de-coleta-e-suas-bases-legais)
5. [Catálogo de dados](#5-catálogo-de-dados)
6. [Arquitetura](#6-arquitetura)
7. [Governança e LGPD](#7-governança-e-lgpd)
8. [Texto proposto para os documentos publicados](#8-texto-proposto-para-os-documentos-publicados)
9. [Fases de execução](#9-fases-de-execução)
10. [Testes](#10-testes)
11. [Decisões em aberto](#11-decisões-em-aberto)
12. [Riscos](#12-riscos)

---

## 1. Por que este documento existe

O Revsist está em beta fechado, por convite. O beta existe para descobrir o
que funciona, o que quebra e o que custa caro. Hoje, porém, o produto **não
mede quase nada disso**, e o pouco que mede fica espalhado:

| O que se quer saber | O que existe hoje | Onde | Lacuna |
|---|---|---|---|
| Quanto tempo a pessoa usa | `sessions.created_at`, `last_seen_at`; `users.last_login_at` | `models.py:920-922`, `models.py:801`, `security/sessions.py:127` | Sessão autenticada não é uso. Uma aba esquecida aberta por 8 h conta como 8 h |
| Onde clicou, que tela usou | Nada | — | Sem nenhum sinal de navegação ou ação |
| Erros encontrados | Log técnico rotativo (5 × 10 MB); `feedbacks` quando a pessoa escreve | `main.py:59`, `models.py:872` | Erro no navegador não chega ao servidor. Erro do servidor não se liga a quem sofreu nem à tela. Nada é agregado |
| Tokens usados | **Descartados.** A resposta do provedor traz a contagem, e o cliente lê só o texto | `gemini_client.py:347-356`; `openai_compatible_client.py:130-134` e `160-163` | Nem o pesquisador, que paga pela chave (BYOK), nem o controlador sabem quanto custa uma triagem |
| Proveniência de IA | Provedor, modelo, hash do contexto e validade, por decisão | `models.py:734-737` | Já basta para auditoria. Não tem custo, latência nem tentativas |
| Marcos da revisão | Deriváveis de `harvest_runs`, `protocol_versions`, `audit_logs`, `paper_screenings` | `models.py` | **Já existem.** Não precisam ser coletados de novo (princípio P2) |

### 1.1 A tensão com o que já foi publicado

Três textos em produção prometem, com palavras próximas, que não há telemetria:

- **Aviso de Privacidade**, seção 8 (`landing/privacidade/index.html:384-389`):
  *"Não há cookie de rastreio publicitário, métrica comportamental de terceiro
  nem pixel de telemetria"*.
- **Tela de aceite** (`frontend/src/components/aceite/AceiteDeTermos.tsx:84-89`
  e `landing/src/scripts/aceite.js:83-84`): *"Não há rastreador, anúncio, pixel
  de telemetria nem métrica de terceiros"*.
- **Rodapé** da landing, dos documentos e do blog: *"Sem rastreadores"*.

A coleta deste plano é **de primeira parte**: nenhum SDK externo e nenhum
destinatário novo, e o `connect-src 'self'` da CSP continua como está. Por
isso a essência das promessas sobrevive: nada acompanha a pessoa por outros
sites e nada vai para terceiro. A frase *"nem pixel de telemetria"*, porém,
deixa de ser verdadeira no sentido que um leitor comum lhe dá. **Os três textos
mudam antes de o primeiro evento ser gravado.** É a mesma regra que motivou o
`retencao.py`: *um aviso que promete o que o sistema não faz é pior do que um
aviso que não promete nada*. Vale também no sentido inverso: o sistema não
pode fazer o que o aviso nega.

---

## 2. Princípios

| # | Princípio | O que ele impõe |
|---|---|---|
| **P1** | **Pergunta antes do evento** | Todo dado coletado responde a uma pergunta do §3. Evento sem pergunta não entra no vocabulário. É a forma operacional do art. 6º, I e III (finalidade e necessidade) |
| **P2** | **Derivar antes de coletar** | O que já se calcula a partir de tabelas existentes (coletas, triagens, versões de protocolo) não é coletado de novo pelo cliente |
| **P3** | **Comportamento, nunca conteúdo** | Vocabulário fechado de eventos e de propriedades, validado no servidor. **Não existe tipo "texto livre"** em propriedade de evento. Mesmo desenho do `ropa_service.py:42-79`: a garantia não depende de disciplina, depende de não haver por onde passar o conteúdo |
| **P4** | **Primeira parte** | Nenhum serviço de analytics, replay ou captura de erros de terceiros (PostHog Cloud, Sentry SaaS, Hotjar, GA). O dado não sai do VPS. A CSP não ganha domínio novo |
| **P5** | **O servidor decide** | Desligamento, versão dos termos aceita e fim do beta são verificados no servidor. Um cliente adulterado ou desatualizado que envie eventos não consegue gravá-los |
| **P6** | **Só no perfil `server`** | `deployment_profile` (`config.py:67`) diferente de `SERVER` desliga tudo. A instalação de mesa não envia nada a lugar nenhum |
| **P7** | **Ninguém da equipe vê o uso do outro** | Dado de uso nunca aparece para dono de projeto, coautor ou equipe. Só o controlador vê, e no painel só em agregado. O Revsist não pode virar instrumento de orientador vigiar orientando |
| **P8** | **O consumo é do pesquisador primeiro** | Os tokens gastos aparecem para quem pagou por eles antes de servirem a qualquer análise |
| **P9** | **O beta tem fim** | O beta dura **365 dias**, de 12/09/2026 (vigência dos Termos 2.0, que declararam o BETA) a **12/09/2027** (`RSAC_BETA_INICIO`, `RSAC_BETA_DURACAO_DIAS`). Passada a data, o servidor recusa sozinho. O controlador pode **encerrar antes** pela aba Sistema. **Prorrogar não é um botão**: exige nova versão do Aviso com a nova data (§6.6.4) |
| **P10** | **Promessa e prática se confrontam por teste** | O vocabulário e os prazos no código são lidos contra o aviso publicado, como já faz `test_retencao.py:146-160` |

---

## 3. As perguntas que o beta precisa responder

Cada evento do §5 cita a pergunta que justifica a sua coleta. Mudar esta lista
é o momento certo para perguntar se o tratamento continua necessário.

| ID | Pergunta | Respondida por |
|---|---|---|
| **Q-01** | Em que etapa da revisão as pessoas param e não voltam? | Marcos da jornada (derivados) + última tela antes de 14 dias sem uso |
| **Q-02** | Quanto tempo leva do cadastro ao primeiro valor (protocolo congelado, primeira coleta, primeira exportação)? | Marcos derivados + `users.created_at` |
| **Q-03** | Quais erros mais atrapalham, e quantas pessoas cada um atinge? | Ocorrências de erro agrupadas por impressão digital |
| **Q-04** | Quanto custa, em tokens e tempo, triar N estudos, por provedor e modelo? | Registro de chamadas de IA |
| **Q-05** | Com que frequência a cota acaba, a cadeia de reserva é acionada ou a resposta do modelo vem inválida? | Registro de chamadas de IA (resultado, tentativa, modelo que respondeu) + `audit_logs.ai_response_valid` |
| **Q-06** | Quais recursos são usados e quais ninguém encontra? | Telas vistas e ações acionadas |
| **Q-07** | Onde a interface confunde? | Cliques repetidos, cliques em controle desabilitado, idas e voltas entre telas |
| **Q-08** | Quanto tempo ativo uma revisão exige, por etapa? | Tempo ativo por tela |
| **Q-09** | Quais fontes de coleta falham ou voltam zeradas em uso real? | `harvest_runs` (derivado); doc 36 |
| **Q-10** | Em que navegadores, sistemas e larguras de tela o Revsist é usado? | Ambiente reduzido, uma vez por sessão de uso |
| **Q-11** | A plataforma é lenta onde? | Desempenho agregado por rota e por tela |
| **Q-12** | As pessoas voltam? (retenção em 1, 7 e 30 dias) | Início de sessão de uso |

---

## 4. Três níveis de coleta e suas bases legais

A distinção principal deste plano é esta. Misturar os níveis é o que tornaria a
coleta ilegítima: consentimento embutido nos termos é nulo (art. 8º, §4º), e
dado coletado para melhorar o produto não pode ser reaproveitado num artigo
científico sem nova base (art. 6º, I).

| Nível | O que cobre | Base legal (art. 7º) | Ligado por padrão? | Pode desligar? |
|---|---|---|---|---|
| **A — Operacional** | Erros, desempenho agregado, consumo de IA | **IX** (legítimo interesse: manter o serviço funcionando e seguro) e **V** (execução do contrato: mostrar ao pesquisador o próprio consumo) | Sim | Não individualmente: é parte do funcionamento. O desempenho é agregado sem identificação desde a origem |
| **B — Uso do produto** | Telas, ações, tempo ativo, ambiente, sinais de frustração | **IX** (legítimo interesse: melhorar o produto durante o beta), com teste de balanceamento (§7.2) | Sim, durante o beta (D-02) | **Sim, a qualquer momento**, em Configurações, sem perder nenhum recurso |
| **C — Estudo** | Questionários (SUS, entrevistas), sessões moderadas, uso de dados do beta em publicação científica | **I** (consentimento específico, destacado, separado dos termos) + TCLE + aprovação de CEP quando houver publicação | **Não**, só por adesão (opt-in) | Sim, com revogação a qualquer momento |

### 4.1 Por que não consentimento para o Nível B

Seria possível, e é a alternativa registrada na D-01. A recomendação é
legítimo interesse com desligamento, por três razões:

1. **Consentimento como condição de acesso não é livre.** Um aceite "de tudo"
   na tela de entrada seria autorização genérica (art. 8º, §4º). Um opt-in
   separado, que ninguém marca, deixa o beta sem dado. O legítimo interesse com
   oposição fácil é o arranjo mais honesto entre esses dois extremos.
2. **A expectativa é compatível.** Quem entra num beta por convite, com o selo
   *beta* em toda tela, espera razoavelmente que o uso seja observado para
   melhorar o produto. Esse é o teste de expectativa do art. 10, II.
3. **O desligamento vai além do mínimo legal.** O art. 18, §2º só obriga a
   atender oposição em caso de descumprimento da lei. Oferecer o botão sempre
   é salvaguarda adicional, e ela conta no balanceamento.

### 4.2 Por que o Nível C não pode usar o art. 7º, IV

O art. 7º, IV (estudos por órgão de pesquisa) exige **pessoa jurídica** de
pesquisa (art. 5º, XVIII). O controlador do Revsist é pessoa natural
(`/privacidade#controlador`). Se os dados forem para um artigo, a base é o
consentimento, e a instituição do pesquisador pode exigir o CEP. A proposta em
[`estudo_validacao/PROPOSTA_PROJETO_PESQUISA.md`](../estudo_validacao/PROPOSTA_PROJETO_PESQUISA.md)
envolve pesquisadores como participantes (executores e trio de avaliadores),
em Ciências Sociais Aplicadas. Isso a coloca, em princípio, sob a Resolução CNS
nº 510/2016. **Conferir com o CEP da instituição** antes de reaproveitar
qualquer dado do beta nela (D-04).

---

## 5. Catálogo de dados

Convenções:

- **Nome** de evento em `dominio.acao`, em português, minúsculas.
- **Tela** é o identificador lógico da rota, nunca o caminho real. Assim
  `/projects/7847417c-…/screening` vira `projeto.triagem`, e **nenhum UUID sai
  do navegador em evento de uso**.
- **Faixa** substitui contagem exata quando o número exato não muda a resposta
  (`1-10`, `11-100`, `101-1000`, `>1000`). Isso reduz a chance de reconhecer um
  projeto pela combinação de números.
- Coluna **Nível**: A ou B, como no §4.

### 5.1 Tempo de uso

Três medidas diferentes, que não se confundem:

| Medida | Definição | Fonte |
|---|---|---|
| **Sessão autenticada** | De login a logout ou expiração | `sessions` (já existe; nada novo) |
| **Sessão de uso** | Começa na primeira interação com a aba visível. Termina após **30 min** sem interação, ou ao fechar | Cliente |
| **Tempo ativo** | Segundos em que a aba está visível **e** houve interação (tecla, clique, rolagem, toque) nos últimos **60 s**, contados em blocos de 15 s | Cliente |

O tempo ativo é o número que interessa para a Q-08. É ele que separa quem
trabalhou 40 minutos de quem deixou a aba aberta durante o almoço.

| Evento | Propriedades | Nível | Pergunta |
|---|---|---|---|
| `sessao_uso.inicio` | `origem` ∈ {`login`, `retorno`, `recarga`} | B | Q-12 |
| `sessao_uso.fim` | `tempo_ativo_s` (int), `tempo_total_s` (int), `telas_distintas` (int ≤ 20), `motivo` ∈ {`inatividade`, `fechamento`, `logout`} | B | Q-08, Q-12 |
| `tela.saida` | `tela` (enum), `tempo_ativo_s` (int) | B | Q-06, Q-08 |

Não se registra **a teclada, o que foi digitado, o movimento do mouse nem a
posição de rolagem**. A interação só alimenta o relógio de atividade e é
descartada no ato.

### 5.2 Navegação e ações ("onde clicou")

**Telas** (enum `tela`, mapeado das rotas de `App.tsx:279-338` por `matchPath`):
`inicio`, `projetos`, `projeto.protocolo`, `projeto.coleta`,
`projeto.triagem`, `projeto.extracao`, `projeto.indicadores`,
`projeto.exportacao`, `projeto.equipe`, `configuracoes`, `entrada`.

**Ações.** Cada controle que interessa recebe um atributo estável:

```tsx
<Button data-uso="triagem.lote.iniciar" onClick={iniciarLote}>Triar em lote</Button>
```

Um **único ouvinte delegado** no `document` sobe do alvo do clique até o
`[data-uso]` mais próximo e registra só esse identificador. Controle sem
atributo não gera evento de ação.

| Evento | Propriedades | Nível | Pergunta |
|---|---|---|---|
| `tela.vista` | `tela`, `anterior` (enum `tela` ou `nenhuma`) | B | Q-06 |
| `acao` | `alvo` (enum fechado de `data-uso`), `tela` | B | Q-06 |
| `frustracao.clique_repetido` | `tela`, `alvo` (enum ou `nao_instrumentado`), `cliques` (3–10) | B | Q-07 |
| `frustracao.clique_desabilitado` | `tela`, `alvo` | B | Q-07 |

**Primeiro lote de alvos** (≈40, a fechar na F4). Exemplos por tela:
`projeto.criar`, `protocolo.sugerir_ia`, `protocolo.congelar`,
`protocolo.emenda.abrir`, `coleta.iniciar`, `coleta.cancelar`,
`coleta.fonte.alternar`, `triagem.lote.iniciar`, `triagem.decisao.incluir`,
`triagem.decisao.excluir`, `triagem.sugestao_ia.aceitar`,
`triagem.sugestao_ia.rejeitar`, `triagem.filtro.alterar`,
`extracao.pdf.obter`, `extracao.ia.extrair`, `indicadores.instantaneo.criar`,
`exportacao.xlsx`, `exportacao.bib`, `exportacao.prisma`,
`equipe.convite.emitir`, `config.ia.testar_conexao`, `config.chave.adicionar`,
`feedback.abrir`, `ajuda.abrir`.

Para decisões de triagem, o evento de clique é **redundante** com
`paper_screenings`/`audit_logs` (P2). Ele só entra se a F4 mostrar que a
derivação não distingue *clique na sugestão da IA* de *decisão manual*. O
`audit_logs.source` provavelmente já distingue; conferir antes.

**O que "onde clicou" não é, neste plano:** coordenadas de clique, mapa de
calor, gravação de sessão (*session replay*), texto do elemento clicado,
valor de campo. Todas essas técnicas capturam, por construção, o conteúdo da
tela: títulos, resumos, critérios, nomes de coautores. Nenhuma sanitização
confiável separa conteúdo de interface num replay.

### 5.3 Marcos da jornada (servidor)

Emitidos pelo **backend**, no ponto em que a operação conclui. É mais
confiável que o clique: registra o que aconteceu, e não o que se tentou.

| Evento | Propriedades | Derivável hoje? | Pergunta |
|---|---|---|---|
| `jornada.conta_criada` | `via` ∈ {`senha`, `google`} | Sim: `users.created_at`, `auth_provider` | Q-02 |
| `jornada.projeto_criado` | `desenho` (enum do catálogo, doc 45) | Sim: `projects` | Q-01, Q-02 |
| `jornada.protocolo_congelado` | `modo` ∈ {`simplificado`, `completo`} | Sim: `protocol_versions` | Q-01, Q-02 |
| `jornada.coleta_concluida` | `fontes_n`, `fontes_zeradas_n`, `registros` (faixa), `duracao_s` | Sim: `harvest_runs` | Q-01, Q-09 |
| `jornada.triagem_lote_concluida` | `estudos` (faixa), `com_ia` (bool), `interrompida_por_cota` (bool) | Parcial | Q-01, Q-04, Q-05 |
| `jornada.exportacao` | `formato` ∈ {`xlsx`, `bib`, `json`, `prisma`} | **Não** | Q-01, Q-02 |
| `jornada.equipe_convite` | — | Sim: `project_invitations` | Q-06 |

**Regra:** marco derivável **não vira evento**. Vira consulta na aba Sistema (§6.6).
Só `jornada.exportacao` e a parte não derivável do lote de triagem pedem
emissão nova. A tabela está completa para que a derivação seja uma decisão
registrada, e não um esquecimento.

### 5.4 Erros

**No navegador** (`frontend/src/uso/erros.ts`):

| Origem | Como captura |
|---|---|
| Erro de renderização | `componentDidCatch` do `ErrorBoundary` (`components/ui/ErrorBoundary.tsx`; usado em `App.tsx:350` e nas seções de `InsightsPage`) |
| Exceção não tratada | `window.addEventListener('error')` |
| Promessa rejeitada sem tratamento | `window.addEventListener('unhandledrejection')` |
| Falha de API | `ApiError` em `api/client.ts`: status ≥ 500, 408, 429, erro de rede, tempo esgotado. **Não** 401 (é fluxo normal) nem 422 de validação de formulário, que só é agregado por rota |
| Erro mostrado ao usuário | Toast de erro (`Toaster`): o **identificador** da mensagem, nunca o texto interpolado |

**No servidor** (`backend/app/services/uso/erros.py`):

| Origem | Como captura |
|---|---|
| Exceção não tratada em rota | Manipulador de exceção global registrado em `main.py` |
| Falha de job | `harvest_job_manager.py`, `job_manager.py`: coleta, triagem em lote, aquisição de PDF |
| Provedor indisponível | `ProvedorIndisponivel` (`ai/base.py:177`), com `esgotado_por_cota` |
| Fonte zerada | O sinal de zero silencioso do doc 36 |

**Campos de uma ocorrência:**

| Campo | Conteúdo | Sanitização |
|---|---|---|
| `impressao` | SHA-256 de `tipo` + primeiro quadro da pilha pertencente ao app, com número de linha normalizado | — |
| `tipo` | `TypeError`, `ApiError:500`, `IntegrityError`… | — |
| `mensagem` | Máx. 300 caracteres | `mascarar()` (`security/log_filter.py:34`), mais remoção de e-mail, URL, sequência de dígitos ≥ 6 e texto entre aspas. **Erro de banco grava só o tipo**: a mensagem do SQLAlchemy carrega os parâmetros da consulta |
| `pilha` | Até 10 quadros, só `arquivo:linha:função` do próprio app | Sem argumentos e sem variáveis locais |
| `tela` / `rota` | Enum `tela` (cliente) ou modelo da rota FastAPI (`/api/v1/projects/{project_id}/papers`), nunca o caminho real | — |
| `status_http`, `correlacao` | Id de requisição devolvido em `X-Request-ID`, que liga o erro do navegador ao do servidor | Criar o middleware se não existir |
| `versao_app`, `navegador` | `settings.app_version`; família e versão maior | — |
| `user_id` | Da sessão, **nunca** do corpo | Nulo quando não há sessão |

**Ligação com o feedback.** O formulário de feedback (`api/v1/feedback.py`)
ganha a caixa *"Anexar o diagnóstico técnico desta sessão (últimos erros, tela
e versão)"*, **desmarcada** por padrão. Marcada, grava as impressões dos
últimos 5 erros da sessão de uso no feedback. Transforma "a triagem travou" em
algo reproduzível sem pedir à pessoa que descreva uma pilha.

### 5.5 Consumo de IA (tokens)

É o item de maior valor imediato e o mais fácil. O dado **já chega** e hoje é
jogado fora.

**Onde está a contagem na resposta:**

| Provedor | Campo | Onde é descartado hoje |
|---|---|---|
| Google Gemini (`generateContent`) | `usageMetadata.promptTokenCount`, `candidatesTokenCount`, `thoughtsTokenCount`, `cachedContentTokenCount`, `totalTokenCount` | `gemini_client.py:348-356` |
| Compatíveis com OpenAI: Qwen, Ollama, LM Studio | `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens` | `openai_compatible_client.py:131-134` e `160-163` |
| Resposta sem contagem | Estimativa por `ceil(caracteres / 4)`, com `estimado = true` | — |

**Como ligar sem reescrever as assinaturas.** Um `contextvars.ContextVar`
(`medidor_de_uso`) é aberto por quem inicia a operação (triagem em lote,
sugestão de protocolo, assistência de campo, extração, teste de conexão) com
`user_id`, `project_id` e `operacao`. Os clientes chamam
`registrar_chamada(...)` em `_tentar_uma_vez` e `_call_chat_completion`, **em
toda tentativa**, inclusive 429 e falha, porque tentativa recusada também gasta
cota. Fora de um medidor aberto, a chamada é contada com `operacao =
nao_atribuida`. Esse caso vira alerta de teste, não perda silenciosa.

**Campos de `uso_ia_chamadas`:**

| Campo | Observação |
|---|---|
| `user_id`, `project_id` | Da sessão e do medidor. `project_id` só aparece para o próprio pesquisador e é pseudonimizado em exportação (D-03) |
| `operacao` | ∈ {`triagem`, `sugestao_protocolo`, `assistencia_campo`, `extracao`, `teste_conexao`, `bibliometria_tesauro`, `nao_atribuida`} |
| `provedor`, `modelo_pedido`, `modelo_respondeu` | São diferentes quando a cadeia de reserva (`FALLBACK_MODELS`) entra, e é esse sinal que responde a Q-05 |
| `chave_ordinal` | 1..N: a posição da chave no rodízio. **Nunca a chave, nem hash dela.** Serve para ver se o rodízio distribui a carga |
| `tentativa`, `resultado` | `resultado` ∈ {`ok`, `limite_minuto`, `limite_diario`, `modelo_indisponivel`, `falha`, `resposta_invalida`} |
| `tokens_entrada`, `tokens_saida`, `tokens_raciocinio`, `tokens_cache`, `tokens_total` | Inteiros; nulos em falha sem resposta |
| `estimado` | Booleano |
| `latencia_ms` | Do envio ao fim da leitura |
| `ocorrido_em` | — |

**O que não se grava:** prompt, resposta, título, resumo, critério. O hash do
contexto já está em `audit_logs.ai_context_sha256` e não é duplicado.

**Custo em reais:** não é gravado. Preço de token muda sem aviso, e um valor
gravado envelhece errado. A tela mostra tokens. O custo estimado, se vier,
é calculado na exibição com uma tabela de preços datada e rotulada como
estimativa (D-08).

### 5.6 Desempenho (Nível A, anônimo desde a origem)

- **Servidor:** middleware que acumula, **em memória e sem `user_id`**,
  histogramas de duração por (`método`, `rota modelo`, `classe de status`) e
  grava um agregado a cada 5 minutos em `uso_desempenho_agregado`. Como não há
  identificação em nenhum momento, o dado não é pessoal (art. 12).
- **Navegador:** tempo até a primeira tela útil (Navigation Timing) e duração
  percebida das requisições lentas (> 2 s), por `tela`. Enviados como eventos
  do Nível B, porque saem do cliente autenticado. Usa-se `PerformanceObserver`
  nativo, sem biblioteca.

### 5.7 Ambiente (Nível B, uma vez por sessão de uso)

| Evento | Propriedades |
|---|---|
| `ambiente` | `navegador` ∈ {`chrome`, `edge`, `firefox`, `safari`, `outro`} + `navegador_versao` (major), `sistema` ∈ {`windows`, `macos`, `linux`, `android`, `ios`, `outro`}, `largura` ∈ {`<768`, `768-1279`, `>=1280`}, `tema` ∈ {`claro`, `escuro`}, `idioma` (primário, ex.: `pt`), `cliente` ∈ {`web`, `electron`} |

Não entram a *string* completa do agente de usuário, a resolução exata, o fuso
horário, a lista de fontes ou nada que componha impressão digital de
navegador.

### 5.8 Voz do usuário

| Instrumento | Quando | Nível | Base |
|---|---|---|---|
| Feedback livre | Já existe (`api/v1/feedback.py`) | — | I (já declarado) |
| Microavaliação | Após a **primeira** exportação: "De 1 a 5, quanto o Revsist ajudou nesta revisão?" + comentário opcional. Nunca mais de uma vez a cada 30 dias | B | I, a cada resposta: responder é o próprio ato voluntário |
| Questionário SUS (10 itens) | Convite após 21 dias de conta | **C** se for para publicação; B se só interno | I |
| Entrevista ou sessão moderada | Convite por e-mail | **C** | I + TCLE |

Toda pergunta tem **"agora não"** e **"não perguntar mais"**, e as duas são
respeitadas pelo servidor.

### 5.9 O que nunca é coletado

Esta lista vai, quase literalmente, para o Aviso (§8.1):

1. Conteúdo de pesquisa: protocolos, critérios, termos de busca, títulos,
   resumos, decisões com motivo, extrações, anotações.
2. O que é digitado em qualquer campo, e as teclas.
3. Gravação de tela, movimento do mouse, coordenadas de clique, mapa de calor.
4. Chaves de API ou qualquer credencial, nem em hash.
5. Identificadores de projeto, estudo ou pessoa **dentro dos eventos de uso**
   (a exceção é o registro de consumo de IA, visível só ao próprio pesquisador).
6. Endereço IP nos eventos de uso. Continua existindo só onde já existe: nas
   tentativas de login, por 90 dias.
7. Qualquer coisa na landing e no blog, onde não há conta nem aceite (D-06).
8. Qualquer coisa nas instalações de mesa.

---

## 6. Arquitetura

### 6.1 Visão geral

```
 NAVEGADOR (perfil server)                          SERVIDOR (VPS)
 ┌────────────────────────────────┐                ┌───────────────────────────────────────┐
 │ frontend/src/uso/              │                │ api/v1/uso.py                         │
 │  telas.ts    tela.vista/saida  │  POST lote     │  require_session                      │
 │  cliques.ts  [data-uso]        │ ─────────────▶ │  portão: perfil? coleta ativa? versão │
 │  atividade.ts tempo ativo      │  ≤50 ev, 32KB  │         dos termos? fim do beta?      │
 │  erros.ts    boundary/onerror  │  keepalive     │  services/uso/vocabulario.py          │
 │  ambiente.ts                   │                │   valida nome, props, tipos, faixas   │
 │  fila.ts  (sessionStorage)     │ ◀── 204 ────── │   descarta o que não conhece          │
 └────────────────────────────────┘  X-Uso-Coleta  │                    │                  │
                                                   │                    ▼                  │
 ┌────────────────────────────────┐                │  uso_eventos  uso_erros               │
 │ clientes de IA                 │ registrar_     │  uso_ia_chamadas                      │
 │  gemini / openai_compatible    │ chamada() ───▶ │  uso_desempenho_agregado (anônimo)    │
 │  (ContextVar medidor_de_uso)   │                │  uso_agregado_diario     (anônimo)    │
 └────────────────────────────────┘                │                    │                  │
                                                   │   retencao.py ─────┘  (descarte)      │
                                                   │   me.py  (acesso, portabilidade,      │
                                                   │           eliminação, oposição)       │
                                                   │   painel (require_owner, agregado,    │
                                                   │           grupos ≥ 5)                 │
                                                   └───────────────────────────────────────┘
```

### 6.2 Vocabulário único

Um arquivo, duas leituras:

- **Fonte:** `backend/app/services/uso/vocabulario.json`. Cada entrada tem
  `nome`, `nivel`, `perguntas` (Q-xx, obrigatório e não vazio: P1),
  `propriedades` (cada uma com `tipo` ∈ {`enum`, `int`, `faixa`, `bool`} e seus
  limites) e `descricao_publica` (a frase que aparece no Aviso).
- **Cliente:** `frontend/src/uso/vocabulario.gerado.ts`, gerado por
  `frontend/scripts/gerar-vocabulario-uso.mjs`. Dá tipagem: `registrar('acao',
  { alvo: 'triagem.lote.iniciar' })` com alvo errado não compila.
- **Guarda:** teste de deriva (T-03), no mesmo espírito de
  `test_versao_dos_termos.py:26`.

**Não existe tipo `texto`.** Quem precisar de texto livre num evento está, por
definição, pedindo conteúdo, e a resposta é mudar o evento.

### 6.3 Modelo de dados

Migração Alembic nova, depois de `cb01a1e80f24_feedback_do_beta.py`.

**`uso_eventos`**

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | UUID | — |
| `user_id` | `String(36)`, FK `users.id` **ON DELETE CASCADE** | Diferente do ROPA: este dado **deve** morrer com a conta |
| `sessao_uso_id` | `String(36)` | Gerado no cliente, aleatório, sem relação com o token de sessão |
| `nome` | `String(64)` | Validado contra o vocabulário |
| `tela` | `String(40)` | Nulo quando não se aplica |
| `propriedades` | `Text` (JSON) | Só chaves e valores validados |
| `ocorrido_em` | `DateTime(tz)` | Do cliente, limitado a [recebido − 24 h, recebido + 5 min] |
| `recebido_em` | `DateTime(tz)` | Do servidor |
| `versao_app` | `String(20)` | — |

Índices: (`user_id`, `ocorrido_em`), (`nome`, `ocorrido_em`), (`recebido_em`)
para a retenção.

**`uso_erros`**: colunas do §5.4 + `origem` ∈ {`cliente`, `servidor`} +
`user_id` FK CASCADE, nulo quando não há sessão. Índices em (`impressao`,
`ocorrido_em`).

**`uso_ia_chamadas`**: colunas do §5.5. `user_id` FK CASCADE; `project_id` sem
FK, para não bloquear a exclusão de projeto. Índices (`user_id`,
`ocorrido_em`), (`provedor`, `modelo_respondeu`, `ocorrido_em`).

**`uso_desempenho_agregado`**: `janela_inicio`, `metodo`, `rota`,
`classe_status`, `n`, `p50_ms`, `p95_ms`, `max_ms`. Sem `user_id`.

**`uso_agregado_diario`**: `dia`, `metrica`, `dimensao`, `valor`. Sem
`user_id`. É o que sobrevive à retenção dos brutos e à eliminação de contas
(art. 16, IV). Gerado por rotina diária **antes** do descarte dos brutos, e só
com grupos de pelo menos 5 pessoas.

**`sistema_estado_da_coleta`**: linha única, alterada só pela aba Sistema.

| Coluna | Tipo | Nota |
|---|---|---|
| `estado` | `String(20)` ∈ {`aguardando`, `ativa`, `pausada`, `encerrada`} | Nasce `aguardando`. `encerrada` é terminal (§6.6.4) |
| `alterado_em`, `alterado_por` | `DateTime(tz)`, `String(36)` | — |
| `motivo` | `String(300)` | Obrigatório para pausar e encerrar |

**`uso_erros_acompanhamento`**: uma linha por impressão digital, com o
tratamento do defeito, e não com a ocorrência.

| Coluna | Tipo | Nota |
|---|---|---|
| `impressao` | `String(64)`, PK | — |
| `situacao` | ∈ {`novo`, `investigando`, `resolvido`, `ignorado`} | — |
| `resolvido_na_versao` | `String(20)` | Se o erro voltar numa versão **posterior**, a situação volta sozinha para `novo` |
| `nota` | `Text` | Anotação técnica do controlador. Não pode conter dado de titular |
| `atualizado_em` | `DateTime(tz)` | — |

**`sistema_acoes`**: diário das ações administrativas da aba Sistema
(`acao`, `executada_em`, `executada_por`, `parametros` JSON sem dado de
titular, `resultado`). É retido por 5 anos como o ROPA, e pelo mesmo motivo:
provar que a gestão ocorreu de forma regular.

**`users`**: colunas novas

| Coluna | Tipo | Nota |
|---|---|---|
| `uso_coleta_ativa` | `Boolean`, default `True` | Nível B |
| `uso_coleta_alterada_em` | `DateTime(tz)` nulo | Prova da oposição |
| `estudo_consentido_em` | `DateTime(tz)` nulo | Nível C |
| `estudo_termo_versao` | `String(20)` | Versão do TCLE aceito |
| `pesquisa_nao_perguntar` | `Boolean`, default `False` | §5.8 |

### 6.4 Ingestão

**`POST /api/v1/uso/eventos`**, no `api_router` (sessão exigida por padrão).

- Corpo: `{ "sessao_uso_id": "...", "eventos": [ {nome, tela, propriedades, ocorrido_em} ] }`, com até 50 eventos e 32 KB.
- **Portão, na ordem:** perfil é `server` → `settings.uso_coleta_ativa` →
  `sistema_estado_da_coleta.estado == 'ativa'` → hoje < `settings.beta_fim`
  (`beta_inicio + beta_duracao_dias`) → `usuario.terms_version ==
  settings.terms_version` → `usuario.uso_coleta_ativa` (só para eventos do Nível
  B). O estado fica em cache de 30 s no processo, para não consultar o banco a
  cada lote. Barrado em qualquer passo: **204 sem gravar**, com cabeçalho
  `X-Uso-Coleta: desligada`, e o cliente para de enviar até recarregar. Não é
  403: a coleta desligada não é erro de quem usa.
- `user_id` vem **só** de `require_session`. Campo `user_id` no corpo é
  ignorado e contado como anomalia.
- Evento ou propriedade fora do vocabulário é **descartado** e contado em log
  agregado (`[Uso] 3 eventos descartados: nome desconhecido`), sem gravar o
  conteúdo descartado. Em teste o validador roda em modo estrito e levanta.
- Limite próprio: 120 lotes por hora por sessão, somado ao
  `RateLimitMiddleware` (`main.py:321`).

**`POST /api/v1/uso/erros`**: mesmo portão (Nível A, logo sem checar
`uso_coleta_ativa`), até 10 ocorrências por lote, sanitização do §5.4 **no
servidor**, mesmo que o cliente já tenha sanitizado.

**Emissão no servidor:** `uso.registrar(db, usuario, "jornada.exportacao",
{"formato": "xlsx"})`, com o mesmo portão e o mesmo validador.

### 6.5 Cliente

`frontend/src/uso/`, montado dentro do `AuthGate`, portanto só depois do
aceite e do login:

| Módulo | Responsabilidade |
|---|---|
| `fila.ts` | Acumula eventos; envia a cada 30 s, a cada 20 eventos ou em `visibilitychange → hidden`, com `fetch(..., { keepalive: true })`. `sendBeacon` não serve, porque não leva o cabeçalho do token no cliente hospedado em outra origem. Espelha a fila em `sessionStorage` (`rsac_uso_fila`) para sobreviver a uma recarga |
| `telas.ts` | `useLocation` → `matchPath` → enum `tela`; emite `tela.vista` e `tela.saida` |
| `cliques.ts` | Ouvinte delegado de `[data-uso]`; detecção de clique repetido e em controle desabilitado |
| `atividade.ts` | Relógio de tempo ativo (§5.1) |
| `erros.ts` | Ganchos globais + integração com `ErrorBoundary` e `ApiError` |
| `ambiente.ts` | Evento `ambiente` |
| `index.ts` | `registrar()` tipado; lê `uso_coleta_ativa` da resposta de `/auth/me`; respeita `navigator.globalPrivacyControl === true` como desligamento do Nível B (D-05) |

Falha de envio **nunca** aparece para o usuário e nunca tenta de novo em laço:
uma nova tentativa no próximo ciclo e, depois, descarte.

### 6.6 Aba Sistema: visualizar e gerenciar

**Onde.** *Ferramentas → Configurações*, nova aba principal **"6. Sistema"**,
depois de "5. Administração & Usuários" (`SettingsPage.tsx:1272-1280`). Aparece
só para `role === 'owner'`, com a mesma guarda `isOwner` da aba 5, e toda rota
que a alimenta exige `require_owner`. A aba 5 continua cuidando de **quem entra**
(convites, pedidos, contas, feedback). A aba 6 cuida de **como a plataforma
está sendo usada e do ciclo do beta**. Juntá-las faria de uma página que já tem
mais de 2.600 linhas um lugar onde ninguém acha nada.

**Implementação.** Componentes próprios em
`frontend/src/components/sistema/`, no padrão do `PainelFeedback`
(`components/feedback/`), e **não** mais estado dentro de `SettingsPage.tsx`,
que só ganha o botão da aba e `<AbaSistema />`. O valor `'sistema'` entra na
lista de abas persistidas em `rsac_settings_tab` (`SettingsPage.tsx:507-517`).
Os gráficos usam a mesma biblioteca da aba Indicadores (doc 32), sem
dependência nova.

**Atalho.** O grupo "Estado do Sistema" da barra superior
(`TopRibbonBar.tsx:1134`) ganha, para o dono, uma linha *Beta: N dias
restantes · coleta ativa* que abre a aba.

#### 6.6.1 Estrutura

Cabeçalho fixo com o **seletor de período**, que vale para todas as subabas:
*7 dias · 30 dias · 90 dias · Beta inteiro*. Filtro opcional por **versão do
app**. Não existe filtro por pessoa.

| Subaba | Perguntas | Natureza |
|---|---|---|
| **Visão geral** | Todas, em resumo | Visualizar |
| **Uso** | Q-01, Q-02, Q-06, Q-07, Q-08, Q-10, Q-12 | Visualizar |
| **Erros** | Q-03 | Visualizar + triar defeitos |
| **Consumo de IA** | Q-04, Q-05 | Visualizar |
| **Desempenho** | Q-09, Q-11 | Visualizar |
| **Dados e ciclo do beta** | — | **Gerenciar** |

#### 6.6.2 Visualizar

**Visão geral**

- **Cartão do ciclo do beta:** início (12/09/2026), fim previsto
  (12/09/2027), barra de progresso, **dias restantes**, estado da coleta
  (*Aguardando textos · Ativa · Pausada · Encerrada*) com a cor
  correspondente, e a data em que os dados brutos terminam de ser descartados
  (fim + 30 dias). A partir de 60 dias do fim, o cartão avisa: *"Decida até
  DD/MM se o beta será encerrado ou prorrogado. Prorrogar exige nova versão do
  Aviso."*
- **Portão de ativação ao vivo:** os itens verificáveis por máquina do portão
  do §9, cada um com ✅ ou ❌: perfil `server`; Aviso publicado na versão
  esperada; `terms_version` vigente; porcentagem de contas ativas que já
  reaceitaram; data de fim configurada; retenção executada nas últimas 24 h.
  Enquanto houver ❌, o botão *Ativar coleta* (§6.6.3) fica desabilitado e diz
  qual item falta.
- **Indicadores-chave do período:** participantes ativos, sessões de uso,
  tempo ativo mediano por sessão, erros novos, pessoas atingidas por erro,
  tokens consumidos, retenção em 7 dias. Cada número tem a variação contra o
  período anterior.
- **Participação:** contas com coleta de uso ligada, desligada pelo
  interruptor e desligada por GPC. É o termômetro de confiança: se o
  desligamento passar de 30%, algo no texto ou na coleta está incomodando.

**Uso**

- Funil da jornada: conta → projeto → protocolo congelado → coleta → triagem →
  extração → exportação. Mostra a porcentagem em cada passo e a **mediana de
  dias** entre passos (Q-01, Q-02). É derivado das tabelas de domínio (P2).
- Telas por tempo ativo e por visitas; ações mais e **menos** acionadas. A
  lista das nunca acionadas no período é a mais útil (Q-06).
- Mapa de frustração: cliques repetidos e em controle desabilitado por tela e
  alvo (Q-07).
- Tempo ativo mediano por etapa da revisão (Q-08).
- Retenção por coorte semanal de cadastro, em D1, D7 e D30 (Q-12).
- Ambiente: navegador, sistema, faixa de largura, web × desktop (Q-10).

**Erros**

- Lista agrupada por impressão digital, ordenada por **pessoas atingidas**:
  tipo, mensagem sanitizada, tela ou rota, origem (cliente/servidor),
  ocorrências, pessoas (ou "< 5"), primeira e última vez, versões afetadas e
  situação.
- Detalhe: pilha sanitizada, gráfico de ocorrências por dia, distribuição por
  navegador e versão, feedbacks que anexaram essa impressão (link para a
  subaba Feedback da aba 5) e correlação cliente↔servidor.

**Consumo de IA**

- Tokens por dia, empilhados por provedor; tabelas por modelo e por operação.
- **Tokens medianos por estudo triado**, por modelo. É o número que responde
  "quanto custa triar 1.000 estudos" (Q-04).
- Resultado das chamadas: `ok`, limite por minuto, limite diário, modelo
  indisponível, resposta inválida; porcentagem em que a cadeia de reserva
  respondeu no lugar do modelo pedido (Q-05).
- Latência p50/p95 por modelo; porcentagem de contagens estimadas.

**Desempenho**

- Rotas por p95, com `n` e tendência; telas com a primeira tela útil mais
  lenta (Q-11).
- Fontes de coleta: execuções, porcentagem de zeradas e duração mediana por
  fonte (Q-09, derivado de `harvest_runs`).

**Regras de toda a visualização:**

1. Nenhuma linha, gráfico ou exportação por pessoa. Célula com menos de 5
   pessoas aparece como **"< 5"**, e a supressão é aplicada **no servidor**,
   não no componente.
2. Nenhum filtro, busca ou ordenação por usuário, e-mail ou projeto.
3. As respostas das rotas de visualização não contêm `user_id`, `project_id`,
   e-mail nem nome. O teste T-18 varre o JSON à procura de UUID e e-mail.
4. Um erro relatado em feedback é investigado pela impressão que o próprio
   usuário anexou (§5.4), e não por busca de pessoa.

#### 6.6.3 Gerenciar: subaba "Dados e ciclo do beta"

**Controle da coleta**

| Ação | Efeito | Salvaguarda |
|---|---|---|
| **Ativar coleta** | `aguardando`/`pausada` → `ativa` | Só com o portão ao vivo todo ✅ |
| **Pausar coleta** | `ativa` → `pausada`. Nada é gravado; o que existe fica | Motivo obrigatório. Uso típico: incidente, bug na instrumentação, migração |
| **Encerrar o beta agora** | → `encerrada`, **terminal** (§6.6.4). Agenda o descarte dos dados brutos para daqui a 30 dias, como no encerramento pela data | Confirmação digitando `ENCERRAR`, e motivo |

**Inventário e retenção.** Uma linha por tabela (`uso_eventos`, `uso_erros`,
`uso_ia_chamadas`, agregados): quantidade de linhas, registro mais antigo,
prazo publicado, próximo descarte previsto e tamanho aproximado. Botão
**Aplicar retenção agora**: executa `retencao.aplicar_retencao` e mostra as
contagens eliminadas, sem os dados.

**Pedidos de titular recebidos por e-mail.** Para quem escreve ao canal do
controlador em vez de usar a própria tela:

- Seleção da conta **pelo e-mail informado no pedido**, e não por uma lista
  navegável de pessoas.
- Mostra **só contagens** por categoria (eventos, erros, chamadas de IA).
- Ações: **Exportar os dados de uso desta conta** (o mesmo pacote de
  `/me/portabilidade`, para enviar ao titular) e **Apagar os dados de uso desta
  conta**. As duas registram no ROPA (`data_export` / `usage_data_erased`) e
  em `sistema_acoes`.

**Exportação para análise.** Conjunto **pseudonimizado** (§7.7) do período
selecionado, em CSV ou JSON, com grupos < 5 suprimidos nas tabelas agregadas.
Pede a finalidade: *análise interna* ou *estudo (Nível C)*. A opção estudo só
fica habilitada com a D-04 resolvida e só inclui contas com
`estudo_consentido_em`. Registra `study_dataset_exported` no ROPA quando for
estudo.

**Triagem de defeitos.** Na subaba Erros, cada impressão pode ser marcada como
*investigando*, *resolvido na versão X* ou *ignorado*, com nota técnica
(`uso_erros_acompanhamento`). Resolvido que volta em versão posterior reabre
sozinho.

**Diário de ações.** Lista de `sistema_acoes`: o que foi feito, quando, por
qual conta de dono e com que resultado. Não é editável nem apagável pela
interface.

#### 6.6.4 O ciclo do beta: 1 ano

| Marco | Data | O que acontece |
|---|---|---|
| Início do beta | 12/09/2026 | Vigência dos Termos 2.0, que declararam o BETA |
| Ativação da coleta | Data do deploy da F5, com o portão ✅ | Estado `aguardando` → `ativa` pelo botão |
| Aviso de decisão | 14/07/2027 (fim − 60 dias) | Cartão da visão geral e e-mail ao controlador |
| **Fim do beta** | **12/09/2027** | O servidor recusa eventos (P9); o estado passa a `encerrada` na primeira verificação após a data |
| Descarte dos eventos brutos | até 12/10/2027 | Retenção "fim do beta + 30 dias"; os agregados anônimos permanecem |

**Configuração:** `RSAC_BETA_INICIO=2026-09-12` e
`RSAC_BETA_DURACAO_DIAS=365` em `config.py`; `beta_fim` é propriedade
calculada. A data aparece no Aviso e nos Termos, e o T-19 confronta as duas.

**Por que prorrogar não é um botão.** A data de fim está escrita no Aviso que
cada pessoa aceitou. Estendê-la por um clique seria continuar coletando além
do que foi informado, que é exatamente a divergência entre promessa e prática
que o P10 proíbe. Prorrogar é um procedimento: alterar `RSAC_BETA_DURACAO_DIAS`,
publicar o Aviso e os Termos com a nova data, subir `terms_version` e fazer
deploy. Como o portão compara a versão aceita, **a coleta de cada pessoa só
continua depois do reaceite dela**. A aba mostra esse roteiro no lugar do
botão.

**Por que encerrar é terminal.** Um estado `encerrada` que voltasse a `ativa`
seria uma prorrogação disfarçada. Um novo ciclo exige nova data de início na
configuração e nova versão dos documentos.

#### 6.6.5 Rotas

Todas em `api/v1/sistema.py`, com `require_owner`:

| Método e rota | Uso |
|---|---|
| `GET /sistema/beta` | Ciclo, estado da coleta, portão ao vivo, participação |
| `GET /sistema/uso/resumo?periodo=&versao=` | Indicadores-chave |
| `GET /sistema/uso/funil`, `/telas`, `/acoes`, `/frustracao`, `/retencao`, `/ambiente` | Subaba Uso |
| `GET /sistema/erros`, `GET /sistema/erros/{impressao}` | Subaba Erros |
| `PATCH /sistema/erros/{impressao}` | Situação e nota |
| `GET /sistema/ia` | Subaba Consumo de IA |
| `GET /sistema/desempenho` | Subaba Desempenho |
| `GET /sistema/dados` | Inventário e retenção |
| `POST /sistema/coleta/ativar`, `/pausar`, `/encerrar` | Controle da coleta |
| `POST /sistema/dados/retencao` | Aplicar retenção agora |
| `POST /sistema/dados/exportacao` | Conjunto pseudonimizado |
| `POST /sistema/titulares/consulta` | Contagens por e-mail informado. **POST, para o e-mail não ir para URL nem log de acesso** |
| `POST /sistema/titulares/exportacao`, `POST /sistema/titulares/eliminacao` | Atender pedido de titular |
| `GET /sistema/acoes` | Diário |

Do lado de quem usa (§6.7), as rotas são `GET`/`PATCH`/`DELETE /me/uso` e
`GET /me/uso/registros` — esta última é o "ver o que foi registrado" que o
Aviso promete, com os eventos traduzidos pela `descricao_publica` do próprio
vocabulário.

Toda rota de ação grava `sistema_acoes`. As rotas de visualização passam por
um único `suprimir_grupos_pequenos()` antes de responder.

### 6.7 Tela do pesquisador

**Configurações → Privacidade e dados de uso**, nova aba:

1. **Compartilhar dados de uso do beta** (interruptor, Nível B), com uma frase
   do que é e link para `/privacidade#uso-beta`. Desligar grava
   `uso_coleta_alterada_em`, registra no ROPA e oferece **"Apagar também o que
   já foi registrado"**.
2. **Ver o que foi registrado**: os últimos 200 eventos da própria conta,
   legíveis ("Abriu a tela Triagem", "Acionou Triar em lote"), mais contagens
   por categoria. É o acesso do art. 18, II, sem precisar pedir.
3. **Consumo de IA**: tokens por dia, provedor, modelo, operação e projeto;
   tentativas recusadas por cota. É o P8 em forma de tela.
4. **Estudos e pesquisas**: estado do consentimento do Nível C, com
   revogação.

---

## 7. Governança e LGPD

### 7.1 Finalidades e bases

| Finalidade | Dados | Base | Oposição |
|---|---|---|---|
| Corrigir defeitos e manter o serviço estável | Erros, desempenho | IX | Não individual; minimizado e com prazo curto |
| Mostrar ao pesquisador o próprio consumo de IA | Chamadas de IA | V | — |
| Dimensionar custo e confiabilidade da assistência | Chamadas de IA, em agregado | IX | Não individual |
| Melhorar o produto durante o beta | Eventos do Nível B | IX + balanceamento | **Interruptor** |
| Pesquisa de satisfação pontual | Respostas | I | "Não perguntar mais" |
| Estudo científico | Nível C | I + TCLE (+ CEP) | Revogação |

### 7.2 Teste de balanceamento (LIA)

Artefato: `planejamento/52_ANEXO_LIA.md`, escrito na F0. Fecha o **L-10**.
Esqueleto:

1. **Finalidade legítima (art. 10, I):** melhorar e manter um serviço gratuito
   em beta. É concreta, atual e declarada no §3.
2. **Necessidade (art. 10, §1º):** cada evento com pergunta (P1); derivação
   antes da coleta (P2); faixas em vez de números exatos; nenhum identificador
   de conteúdo; prazo curto; fim do beta.
3. **Balanceamento:** expectativa razoável (beta por convite, selo *beta*
   visível); ausência de conteúdo e de terceiros; impacto baixo (nenhuma
   decisão sobre a pessoa se baseia nesses dados); vulnerabilidade específica
   (estudantes em equipe com orientador) neutralizada pelo P7.
4. **Salvaguardas:** interruptor sempre disponível; GPC respeitado; tela "ver o
   que foi registrado"; exclusão sob demanda; painel só agregado com grupos
   ≥ 5; testes que confrontam o aviso com o código.

### 7.3 Relatório de impacto (RIPD)

Pela Resolução CD/ANPD nº 2/2022, art. 4º, tratamento de alto risco exige um
critério geral (larga escala ou efeito significativo sobre direitos) **e** um
específico (tecnologia inovadora, vigilância de área pública, decisão
unicamente automatizada, dado sensível ou de criança). Um beta de dezenas de
pessoas, sem decisão automatizada sobre elas e sem dado sensível, **não parece
se enquadrar**. A recomendação ainda assim é um RIPD **simplificado** de uma
página, no mesmo anexo da LIA. O art. 10, §3º permite à ANPD pedi-lo quando a
base é legítimo interesse, e ele custa pouco agora. *Leitura a validar com
assessoria jurídica.*

### 7.4 ROPA

**Não** se grava uma linha de ROPA por evento: seria volume sem prestação de
contas. Acrescentar a `ropa_service.py`:

- `OPERACOES` (`ropa_service.py:42`): `usage_opt_out`, `usage_opt_in`,
  `usage_data_erased`, `study_consent_given`, `study_consent_revoked`,
  `study_dataset_exported`, `usage_survey_answered`. Todas cabem em
  `String(32)`.
- `CATEGORIAS` (`ropa_service.py:60`): `uso_da_plataforma`,
  `diagnostico_tecnico`, `consumo_de_ia`, `resposta_de_pesquisa`.
- A linha "coleta de dados de uso do beta" entra no **inventário** do doc 37
  §37.3 como operação contínua, com finalidade, base e prazo.

### 7.5 Retenção

Constantes em `retencao.py`, ao lado de `DIAS_TENTATIVAS_DE_LOGIN`
(`retencao.py:42`), cada uma confrontada com o aviso publicado (T-10):

| Dado | Prazo | Por quê |
|---|---|---|
| Eventos de uso (Nível B) | **180 dias** ou **fim do beta + 30 dias** (12/10/2027), o que vier primeiro | Cobre as coortes de retenção de 30 dias e a análise de fechamento do beta. Num beta de 1 ano, a janela de 180 dias implica que a análise do ano inteiro vem dos **agregados diários**, e não dos eventos brutos. Por isso a agregação roda antes do descarte |
| Diário de ações da aba Sistema | 5 anos | Prestação de contas, como o ROPA. Não contém dado de titular |
| Ocorrências de erro | **90 dias** | Defeito não corrigido em 90 dias reaparece com impressão nova |
| Chamadas de IA | **12 meses** | Histórico de consumo que interessa ao próprio pesquisador |
| Agregados anônimos (desempenho, diário) | Indeterminado | Não são dado pessoal (art. 12; art. 16, IV) |
| Fila no navegador | Até fechar a aba | `sessionStorage` |
| Dados do Nível C | Pelo prazo do protocolo aprovado (a Res. CNS 510/2016 prevê 5 anos após o término; conferir com o CEP) | Exigência da ética em pesquisa |

`ResultadoDaRetencao` (`retencao.py:52`) ganha os três contadores novos.

### 7.6 Direitos do titular

| Direito | Onde | Mudança |
|---|---|---|
| Acesso (art. 18, II) | Tela §6.7 item 2; `GET /me/dados` (`me.py:173`) | A declaração passa a listar as categorias de uso, com contagens e prazos |
| Portabilidade (art. 18, V) | `GET /me/portabilidade` (`me.py:317`) | Inclui `uso_ia_chamadas` e `uso_eventos` da conta |
| Eliminação (art. 18, VI) | `executar_eliminacao_completa_usuario` (`me.py:91`) | O CASCADE cuida disso; o teste confirma **explicitamente**, como já é feito com `FeedbackModel` (`me.py:126`) |
| Oposição (art. 18, §2º) | Interruptor | Novo |
| Eliminação parcial | "Apagar o que já foi registrado" | Novo: `DELETE /me/uso` |
| Revogação (art. 8º, §5º) | Nível C e pesquisas | Novo |

Agregados anônimos gerados antes da eliminação **permanecem**, porque não
identificam ninguém. O Aviso diz isso explicitamente.

### 7.7 Acesso interno

- Só `require_owner` lê as tabelas de uso pela API, e só em agregado.
- Exportação para análise fora do sistema: `user_id` substituído por
  `HMAC-SHA256(user_id, RSAC_USO_SEGREDO_PSEUDONIMO)`, `project_id` idem, sem
  e-mail nem nome. Registrada no ROPA como `study_dataset_exported` quando for
  para o Nível C.
- O controlador tem acesso técnico ao banco. A LIA registra o compromisso de
  não consultar dados de uso por pessoa, salvo para atender pedido do próprio
  titular ou investigar incidente de segurança.

### 7.8 Nível C: o estudo

1. **Só com decisão D-04 fechada** e, havendo publicação, com o CEP consultado.
2. Termo próprio (TCLE ou RCLE), versionado (`estudo_termo_versao`), aceito
   numa tela à parte, **nunca** na tela de aceite dos Termos.
3. Recusar ou revogar não altera nada no acesso.
4. Dados dos Níveis A e B coletados **antes** do consentimento só entram no
   estudo se o TCLE disser expressamente que entram, e a pessoa aceitar.
5. O conjunto de dados do estudo sai do sistema **pseudonimizado** (§7.7) e é
   anonimizado antes da publicação, com grupos ≥ 5 em qualquer tabela
   publicada.

---

## 8. Texto proposto para os documentos publicados

A mudança altera finalidades, e por isso é **alteração relevante**. Os três
documentos mudam **juntos**, a versão sobe e o aceite volta a ser pedido.

### 8.0 Versão e reaceite

- `settings.terms_version` (`config.py:110`) passa de `2026-09` para a versão
  do mês de publicação (ex.: `2026-10`), **nas sete cópias** que
  `test_versao_dos_termos.py:26` guarda.
- Aviso e Termos: `VERSÃO 2.1`, com vigência na data do deploy.
- **Reaceite no servidor.** A rota `POST /auth/terms/accept` já existe
  (`auth.py:903`). A F5 confere se a tela de aceite do app a chama quando há
  sessão; se não chamar, passa a chamar. O portão do §6.4 compara
  `usuario.terms_version`, então **quem não reaceitou não tem nada coletado**,
  mesmo que o cliente envie.

### 8.1 Aviso de Privacidade (`landing/privacidade/index.html`)

**a) Resumo honesto** (callout, linhas 122-130). Substituir por:

> **O resumo honesto.** Não há publicidade, nem rastreador, pixel ou métrica de
> terceiros. O único cookie é técnico e serve para manter você conectado. O seu
> conteúdo de pesquisa é seu: não treinamos modelos com ele, não o vendemos e
> não o divulgamos. **Durante o beta, registramos no nosso próprio servidor
> como a plataforma é usada (telas, ações, erros e consumo de IA), nunca o que
> você escreve ou pesquisa. Você pode desligar essa parte a qualquer momento.**
> O que sai da plataforma para fora sai por decisão sua, quando você liga uma
> chave de IA ou consulta uma base científica.

**b) Índice:** novo item *"Dados de uso durante o beta"*, âncora `#uso-beta`,
logo após *"Decisões assistidas por IA"*.

**c) Tabela da seção 3:** três linhas novas.

| Categoria | Dados | Origem | Finalidade | Base legal (art. 7º) |
|---|---|---|---|---|
| Uso da plataforma (beta) | Telas abertas, ações acionadas (identificadas por nome fixo, sem o texto da tela), tempo ativo, navegador e sistema resumidos | Gerado pelo uso, no seu navegador | Entender onde a plataforma ajuda, onde confunde e o que corrigir primeiro | IX (legítimo interesse), **desligável** |
| Diagnóstico de erros | Tipo e mensagem do erro, com dados identificáveis removidos, tela, versão e navegador | Gerado quando algo falha, no navegador ou no servidor | Encontrar e corrigir defeitos | IX (legítimo interesse) |
| Consumo de IA | Provedor, modelo, tipo de operação, tokens de entrada e saída, duração e resultado de cada chamada | Gerado quando você usa a assistência | Mostrar a você o seu consumo; dimensionar custo e confiabilidade | V (execução de contrato) e IX |

**d) Seção nova: "Dados de uso durante o beta".** Texto integral proposto:

> ## Dados de uso durante o beta
>
> O Revsist está em beta, e um beta serve para descobrir o que funciona e o que
> não funciona. Para isso, registramos como a plataforma é usada. Esta seção diz
> exatamente o quê, e o que fica de fora.
>
> **O que registramos**
>
> 1. **Uso da plataforma.** Quais telas você abre, quais botões e comandos
>    aciona, quanto tempo fica ativo em cada etapa e sinais de dificuldade, como
>    clicar várias vezes seguidas no mesmo lugar. Cada ação é identificada por um
>    nome fixo definido por nós, como "Triar em lote", e não pelo que está
>    escrito na tela. Registramos também, uma vez por sessão, o tipo de navegador
>    e de sistema, a faixa de largura da tela, o idioma e o tema.
> 2. **Erros.** Quando algo falha no seu navegador ou no servidor, registramos
>    o tipo do erro, a tela, a versão da plataforma e uma mensagem técnica da
>    qual removemos e-mails, endereços, números longos e trechos entre aspas.
> 3. **Consumo de inteligência artificial.** Em cada chamada feita com a sua
>    chave: provedor, modelo, tipo de operação (por exemplo, triagem), número de
>    tokens enviados e recebidos, duração e resultado, inclusive recusas por
>    limite de cota. Você vê esse consumo em Configurações.
> 4. **Desempenho.** O tempo de resposta do servidor é medido de forma agregada,
>    sem identificar ninguém.
>
> **O que nunca registramos**
>
> - O conteúdo da sua pesquisa: protocolos, critérios, termos de busca, títulos,
>   resumos, decisões e seus motivos, extrações e anotações.
> - O que você digita em qualquer campo.
> - Gravação de tela, movimento do mouse ou posição dos cliques.
> - Chaves de API e senhas.
> - Seu endereço IP nesses registros.
> - Nada no site público e no blog, onde você não tem conta.
> - Nada nas instalações de mesa do Revsist.
>
> **Onde fica e quem vê.** Tudo fica no servidor do próprio Revsist. Nenhum
> serviço de análise de terceiros recebe esses dados. Outros membros das suas
> equipes, inclusive o responsável por um projeto, **não têm acesso** aos seus
> dados de uso. O controlador os consulta em forma agregada, e grupos com menos
> de cinco pessoas não são exibidos.
>
> **Base legal.** O registro de uso da plataforma e de erros se apoia no
> legítimo interesse (art. 7º, IX) de manter e melhorar um serviço gratuito em
> desenvolvimento. O teste de balanceamento está disponível mediante pedido. O
> registro de consumo de IA também serve para mostrar a você o seu próprio
> consumo (art. 7º, V).
>
> **Como desligar.** Em *Configurações → Privacidade e dados de uso*, desligue
> *Compartilhar dados de uso do beta*. O registro de uso da plataforma para na
> hora, e você pode apagar o que já foi registrado. Nenhum recurso deixa de
> funcionar. Se o seu navegador enviar o sinal *Global Privacy Control*, ele
> vale como desligamento. Erros e consumo de IA continuam registrados, porque
> são necessários para manter o serviço funcionando e para mostrar a você o
> que a sua chave gastou.
>
> **Ver o que foi registrado.** Na mesma tela, você vê os registros de uso da
> sua conta em linguagem comum.
>
> **Até quando.** O beta tem duração prevista de um ano e termina em **12 de
> setembro de 2027**. Pode terminar antes, mas não depois sem uma nova versão
> deste Aviso, que você será convidado a aceitar de novo. A coleta de uso
> termina com o beta. Os prazos de guarda estão na seção *Retenção e descarte*. Ao eliminar sua conta, esses
> registros são apagados. Permanecem apenas estatísticas agregadas que não
> identificam ninguém.
>
> **Pesquisas e estudos.** Às vezes poderemos convidar você para um
> questionário curto, uma entrevista ou um estudo científico sobre a
> plataforma. A participação é sempre opcional, pedida à parte e com termo
> próprio. Recusar não muda nada no seu acesso. Dados de uso só entram num
> estudo publicado com o seu consentimento específico para isso.

**e) Seção 6, "Com quem compartilhamos":** acrescentar ao fim:

> Os dados de uso do beta **não são compartilhados** com ninguém: ficam no
> servidor do Revsist.

**f) Seção 8, "Cookies e armazenamento no navegador":**

- Nova linha na tabela: `rsac_uso_fila` · Armazenamento de sessão · Guardar
  por instantes os registros de uso ainda não enviados, para não perdê-los ao
  recarregar a página · Apagado ao fechar a aba.
- Parágrafo das linhas 384-389 reescrito:

> Os itens de armazenamento local e de sessão ficam no seu navegador e não são
> legíveis por outro site. Não há cookie de rastreio publicitário, pixel nem
> métrica de terceiros, nada que acompanhe você por outros sites. O registro
> de uso do beta, descrito na seção *Dados de uso durante o beta*, é feito pelo
> próprio Revsist e enviado apenas ao servidor do Revsist.

**g) Seção 11, "Retenção e descarte":** linhas novas na tabela, com a redação
exata que T-10 procura:

| Dado | Prazo | Por quê |
|---|---|---|
| Registros de uso da plataforma | Até 180 dias, e nunca além de 12 de outubro de 2027 (30 dias após o fim do beta) | Analisar o uso ao longo do beta |
| Registros de erros | Até 90 dias | Corrigir defeitos |
| Registros de consumo de IA | Até 12 meses | Mostrar a você o histórico do seu consumo |
| Estatísticas agregadas de uso | Sem prazo | Não identificam ninguém |

**h) Seção 12, "Seus direitos":** acrescentar ao item *Oposição*:

> Para os dados de uso do beta, a oposição é exercida por você mesmo, no
> interruptor de Configurações, sem precisar justificar.

### 8.2 Termos de Uso (`landing/termos/index.html`)

**a) Seção 5, "Gratuidade e estágio BETA":** o item 3 ganha a duração, e
entram dois itens novos.

> 3. **BETA.** A plataforma está em desenvolvimento ativo. Comportamentos podem
>    mudar entre versões, recursos podem ser alterados ou removidos e defeitos
>    são esperados. **O BETA tem duração prevista de 12 meses, de 12 de setembro
>    de 2026 a 12 de setembro de 2027.** Ele pode ser encerrado antes, com
>    aviso. Uma prorrogação só ocorre com nova versão destes Termos e do Aviso
>    de Privacidade.
>
> 5. **Participação no beta e dados de uso.** Participar do BETA é usar uma
>    plataforma que ainda está sendo medida. Enquanto durar o BETA,
>    registramos como a plataforma é usada (telas, ações, tempo ativo, erros e
>    consumo de IA) nos termos da seção *Dados de uso durante o beta* do
>    [Aviso de Privacidade](/privacidade#uso-beta). Esse registro não inclui o
>    conteúdo da sua pesquisa, não é compartilhado com terceiros e não é
>    visível a outros membros das suas equipes. Você pode desligar o registro
>    de uso da plataforma a qualquer momento, sem perder acesso a nenhum
>    recurso.
> 6. **Pesquisas e estudos.** Convites para questionários, entrevistas ou
>    estudos científicos sobre a plataforma são sempre opcionais, feitos à
>    parte e acompanhados de termo próprio. Recusá-los não afeta o seu acesso.

**b) Seção 8, "Seu conteúdo de pesquisa":** novo item.

> 5. **Dados de uso não são conteúdo.** Os registros de uso do beta descrevem
>    como a plataforma foi usada, não o que você produziu nela, e não autorizam
>    a leitura do seu conteúdo de pesquisa.

**c) Seção 12, "Comunicações que enviamos":** acrescentar ao item 3:

> Convites para pesquisas sobre a plataforma não são publicidade, são
> opcionais e podem ser desligados com "não perguntar mais".

### 8.3 Tela de aceite

`AceiteDeTermos.tsx:84-89` e `landing/src/scripts/aceite.js:83-84`, mesmo
texto nos dois:

> O Revsist usa **um único cookie**, técnico, para manter você conectado. Não
> há anúncio, nem rastreador ou pixel de terceiros. **Durante o beta,
> registramos no nosso próprio servidor como a plataforma é usada (telas,
> ações, erros e consumo de IA), nunca o conteúdo da sua pesquisa.** Você pode
> desligar isso em Configurações.

O comentário de cabeçalho de `aceite.js:8` ("Analytics, pixel, nem métrica de
terceiro") é atualizado para não contradizer o código.

### 8.4 Rodapé

"Sem rastreadores" → **"Sem rastreadores de terceiros"** em
`landing/index.html:1302`, nas duas páginas legais e no gerador do blog
(`landing/scripts/gerar-blog.mjs`). Rodar `landing/scripts/verificar-landing.mjs`.

### 8.5 Documentos-fonte

`planejamento/PRIVACIDADE.md` e `planejamento/TERMOS.md` estão na versão 1.0 e
já divergem do publicado. Recomenda-se marcá-los como históricos, com um
cabeçalho que aponte para `/privacidade` e `/termos`. Atualizá-los em paralelo
criaria uma terceira fonte da verdade.

---

## 9. Fases de execução

A F5 (textos) é escrita cedo, mas **publicada no mesmo deploy** que liga a
coleta, e a coleta de cada pessoa só começa depois do reaceite dela (P5). Até
lá, `RSAC_USO_COLETA_ATIVA=false`.

### F0 — Decisões e artefatos (1–2 dias)

- [ ] Fechar D-01 a D-06, D-08 e D-09 (§11); a D-07 já está fechada
- [ ] `52_ANEXO_LIA.md`: teste de balanceamento + RIPD simplificado
- [ ] Fechar a lista de alvos `data-uso` (≈40) e a de telas
- [ ] Acrescentar ao doc 38 os itens **L-89 a L-96** (um por garantia do §7) e
      marcar L-10 como 🔜 dependente deste plano
- [ ] Atualizar o inventário do doc 37 §37.3

**Aceite:** nenhuma decisão aberta que mude o esquema de dados.

### F1 — Fundação no servidor (3–4 dias) — ✅ parcial, 15/09/2026

- [x] `services/uso/vocabulario.json` + `vocabulario.py` (validador fechado, sem tipo texto)
- [x] Migração Alembic `dc02a1e80f25`: `uso_eventos`, `uso_erros`, `uso_ia_chamadas`, colunas `uso_coleta_ativa` e `uso_coleta_alterada_em` em `users`
- [ ] `uso_desempenho_agregado` e `uso_agregado_diario` — adiadas para a F6b, junto com o middleware e a rotina que as alimentam; criar tabela sem quem escreva nela seria esquema morto
- [x] Configuração: `uso_coleta_ativa`, `uso_versao_dos_termos`, `beta_inicio` (2026-09-12), `beta_duracao_dias` (365), `beta_fim` calculado, `uso_segredo_pseudonimo` em `config.py`
- [x] Tabelas `sistema_estado_da_coleta` (nasce `aguardando`), `uso_erros_acompanhamento`, `sistema_acoes`
- [x] `api/v1/uso.py`: `POST /uso/eventos`, `POST /uso/erros`, portão do §6.4 (`services/uso/portao.py`)
- [ ] `uso.registrar()` para emissão no servidor — entra com a F4, que é quem emite `jornada.*`
- [x] ROPA: operações `usage_opt_out`, `usage_opt_in`, `usage_data_erased`, `usage_data_exported`, `usage_collection_changed` e as três categorias do §7.4
- [x] `retencao.py`: prazos do §7.5 (180 dias / fim do beta + 30, 90 dias, 12 meses, 5 anos) e `ultima_execucao_em`
- [ ] Rotina diária de agregação antes do descarte — F6b, pelo mesmo motivo das tabelas agregadas
- [x] `me.py`: `/me/dados` (finalidade e prazos), `/me/portabilidade` (inclui os dados de uso), `GET`/`PATCH`/`DELETE /me/uso`, eliminação da conta apagando os registros de uso

**Aceite:** T-01, T-02, T-04 a T-09 passando; coleta desligada por padrão. ✅
Suíte em `backend/tests/test_uso/` (82 testes).

**Divergência:** o estado da coleta e o `RSAC_USO_VERSAO_DOS_TERMOS` entraram
como travas próprias do portão (§6.4). Sem a segunda, uma implantação com
`RSAC_USO_COLETA_ATIVA=true` e o Aviso antigo coletaria para quem aceitou um
texto que diz o contrário.

### F2 — Consumo de IA (2–3 dias) — ✅ 15/09/2026

- [x] `ContextVar` + `medidor.medir()` / `medidor.anotar()` (`services/uso/medidor.py`)
- [x] Leitura de `usageMetadata` (Gemini) e `usage` (compatíveis com OpenAI) em toda tentativa, inclusive 429, modelo indisponível e resposta inválida; estimativa rotulada quando o provedor não conta
- [x] Medidor aberto em triagem, sugestão de protocolo, assistência de campo, extração e teste de conexão. O tesauro da bibliometria não chama provedor de IA hoje, então não há o que medir
- [x] Subaba *Consumo de IA* na aba Sistema (visão agregada do controlador)
- [x] Tela *Consumo de IA* do próprio pesquisador — entregue na aba *Privacidade e dados de uso* (F5), por dia, provedor, modelo e operação

**Aceite:** T-11, T-12. Triagem em lote de 20 estudos com Gemini gera 20+
linhas, com `modelo_respondeu` correto quando a reserva entra.

### F3 — Erros (2–3 dias) — ⬜ pendente

- [ ] Middleware de `X-Request-ID` (se não existir)
- [ ] Manipulador global de exceção + ganchos nos jobs
- [ ] `frontend/src/uso/erros.ts`: `ErrorBoundary`, `onerror`, `unhandledrejection`, `ApiError`
- [ ] Sanitização em duas camadas (cliente e servidor)
- [ ] Caixa "Anexar diagnóstico técnico" no feedback

**Aceite:** T-13. Um erro provocado na triagem aparece no painel com a mesma
correlação no cliente e no servidor e sem nenhum trecho de conteúdo.

### F4 — Uso do produto no cliente (3–4 dias)

- [ ] Gerador `vocabulario.gerado.ts` + teste de deriva
- [ ] `fila.ts`, `telas.ts`, `cliques.ts`, `atividade.ts`, `ambiente.ts`
- [ ] Atributos `data-uso` nos alvos fechados na F0
- [ ] `jornada.exportacao` e a parte não derivável do lote de triagem, no servidor
- [ ] GPC

**Aceite:** T-03, T-14. Uma sessão real de 10 minutos gera menos de 150
eventos, e nenhum deles contém UUID, texto livre ou caminho real.

### F5 — Textos, aceite e tela de privacidade (2 dias) — ✅ 15/09/2026

- [x] Aviso de Privacidade **2.1** publicado em `landing/privacidade/index.html`, com a seção nova *Dados de uso durante o beta* (`#uso-beta`), as três linhas na tabela de dados, a fila `rsac_uso_fila` no armazenamento do navegador, os quatro prazos na retenção e a oposição por interruptor nos direitos
- [x] Termos de Uso **2.1**: duração do BETA (12/09/2026 a 12/09/2027), participação no beta e dados de uso, pesquisas opcionais, *dados de uso não são conteúdo*
- [x] Tela de aceite reescrita nos dois lados (landing e aplicação); rodapés passam a dizer "Sem rastreadores **de terceiros**"; blog regenerado e `sitemap.xml` redatado
- [x] `terms_version` = `2026-09.2` nas sete cópias, e `uso_versao_dos_termos` com o mesmo valor — é o que fecha o item "Aviso e Termos declarando a coleta" do portão
- [x] **Reaceite na conta**: `ReaceiteDeTermos` aparece depois do login quando a versão aceita difere da vigente e grava por `POST /auth/terms/accept`; quem adia continua usando a plataforma e **não tem nada coletado**
- [x] Aba *5. Privacidade & Dados de uso* (§6.7): interruptor, contagens, "ver o que foi registrado" (`GET /me/uso/registros`), consumo de IA da própria conta e "apagar meus registros"
- [x] `PRIVACIDADE.md` e `TERMOS.md` marcados como históricos

**Aceite:** T-10 e T-19 em `tests/test_uso/test_aviso_publicado.py`, T-15 e
`test_versao_dos_termos.py` passando. ✅

**Divergência:** a versão dos documentos ficou `2026-09.2`, e não `2026-10` —
publicar em setembro com carimbo de outubro seria datar errado o aceite que as
pessoas dão hoje. O formato continua ordenável.

### F6 — Aba Sistema (5–7 dias)

A F6a vem **antes** da ativação da coleta, porque é ela que tem o botão
*Ativar coleta* e o portão ao vivo. As demais podem entrar depois, com dados já
chegando.

**F6a — Ciclo e gerenciamento (2–3 dias), pré-requisito do portão** — ✅ parcial, 15/09/2026

- [x] `api/v1/sistema.py`: `/sistema/beta`, `/sistema/resumo`, `/sistema/coleta/{ativar,pausar,encerrar}`, `/sistema/dados`, `/sistema/dados/retencao`, `/sistema/titulares/{consulta,exportacao,eliminacao}`, `/sistema/acoes`
- [x] Supressão de grupos com menos de 5 pessoas no servidor (`services/uso/painel.py`, `agregado()`)
- [x] `components/sistema/AbaSistema.tsx` + subabas *Visão geral* (ciclo, portão ao vivo, indicadores, participação) e *Dados e ciclo do beta* (controle da coleta, ciclo de um ano, inventário e retenção, pedido de titular, diário)
- [x] Botão "6. Sistema" em `SettingsPage.tsx`, `'sistema'` em `rsac_settings_tab`
- [ ] Linha "Beta: N dias restantes" no grupo "Estado do Sistema" do ribbon
- [x] Aviso de decisão a 60 dias do fim no cartão do ciclo
- [ ] Aviso de decisão por e-mail

**Divergência:** a eliminação a pedido de titular é `POST
/sistema/titulares/eliminacao`, e não `DELETE /sistema/titulares/uso` como no
§6.6.5 — o e-mail vai no corpo, e corpo em `DELETE` é descartado por parte dos
proxies e clientes HTTP.

**F6b — Visualização (3–4 dias)** — ⚠️ parcial

- [ ] Consultas derivadas do funil e das fontes de coleta (P2)
- [x] Subabas *Erros* (com triagem de defeitos e reabertura por versão) e *Consumo de IA* — adiantadas, porque o consumo de IA já é medido desde a F2
- [ ] Subabas *Uso* e *Desempenho* — hoje mostram estado vazio explicando a fase de que dependem
- [ ] Middleware de desempenho agregado
- [ ] Exportação pseudonimizada

**Aceite:** T-16 a T-20. Cada pergunta Q-01 a Q-12 tem uma visão que a
responde, ou um registro de por que ainda não tem. Uma conta `researcher`
não vê a aba nem alcança nenhuma rota `/sistema`.

### F7 — Nível C (fora do caminho crítico)

Só depois de D-04 e, havendo publicação, do CEP: TCLE versionado, tela de
consentimento, exportação pseudonimizada, questionário SUS.

### Portão de ativação

Antes de `RSAC_USO_COLETA_ATIVA=true` em produção e do clique em *Ativar
coleta* na aba Sistema, **todos** marcados. Os verificáveis por máquina
aparecem ao vivo na visão geral (§6.6.2):

- [x] Aviso e Termos 2.1 publicados em `/privacidade` e `/termos`, com a data de fim 12/09/2027 — **falta o deploy** para que o site sirva o texto novo
- [ ] T-01 a T-20 verdes na CI
- [ ] `RSAC_BETA_INICIO=2026-09-12` e `RSAC_BETA_DURACAO_DIAS=365` em produção
- [ ] F6a entregue
- [ ] Interruptor funcionando em produção, conferido com uma conta de teste
- [ ] `DELETE /me` de uma conta de teste apaga seus registros de uso (conferido no banco)
- [ ] LIA assinada e datada no anexo
- [ ] Backup antes da migração (`docs/PROCEDIMENTO_BACKUP_RESTAURACAO.md`)

**Estimativa (F0–F6):** 18 a 25 dias de trabalho.

**Ordem recomendada:** F0 → F1 → F2 → F6a → F3 → F4 → F5 (deploy + ativação)
→ F6b.

---

## 10. Testes

Em `backend/tests/test_uso/`, salvo indicação.

| ID | O que garante | Como |
|---|---|---|
| **T-01** | Vocabulário fechado | Evento desconhecido, propriedade desconhecida, valor fora do enum ou da faixa, string em campo `int` → descartados (modo normal) e exceção (modo estrito) |
| **T-02** | Não existe tipo texto | Varre `vocabulario.json`: todo `tipo` ∈ {`enum`, `int`, `faixa`, `bool`}; toda entrada tem `perguntas` não vazio (P1) |
| **T-03** | Cliente e servidor falam o mesmo vocabulário | Compara `vocabulario.gerado.ts` com o JSON (no espírito de `test_versao_dos_termos.py`) |
| **T-04** | O servidor decide (P5) | Com interruptor desligado, eventos B → 204 e zero linhas; eventos A continuam |
| **T-05** | Termos desatualizados não coletam | `usuario.terms_version` antigo → zero linhas |
| **T-06** | O beta tem fim (P9) | Relógio em 12/09/2027 00:00 (horário de Brasília) ou depois → zero linhas, e o estado passa a `encerrada`; 11/09/2027 23:59 → grava |
| **T-07** | Só no perfil `server` (P6) | Perfil `desktop` → zero linhas, e o cliente nem monta o módulo |
| **T-08** | `user_id` só da sessão | Corpo com `user_id` de outra conta → linha gravada com o da sessão |
| **T-09** | Eliminação apaga uso | `DELETE /me` → zero linhas em `uso_eventos`, `uso_erros`, `uso_ia_chamadas` para o id; agregados intactos |
| **T-10** | Promessa = prática (P10) | Lê `landing/privacidade/index.html`: prazos do §7.5 batem com as constantes; toda categoria de `descricao_publica` aparece; a frase "nem pixel de telemetria" **não** aparece mais |
| **T-11** | Tokens lidos | Respostas gravadas (sem rede) de Gemini e de compatível com OpenAI → contagens corretas; resposta sem `usage` → `estimado=true` |
| **T-12** | Tentativa recusada é contada | 429 simulado → linha com `resultado=limite_*` e tokens nulos |
| **T-13** | Erro não carrega conteúdo | Exceção cuja mensagem contém título de artigo entre aspas, e-mail e chave `AIzaSy…` → gravada sem os três; `IntegrityError` → só o tipo |
| **T-14** | Evento sem identificador | Frontend (Vitest): a fila nunca produz propriedade que case com regex de UUID ou com `/projects/` |
| **T-15** | Isolamento de equipe (P7) | Dono de projeto que não é owner chamando `/sistema/*` → 403; nenhuma rota de projeto expõe dado de uso de membro |
| **T-16** | O estado da coleta manda | Estados `aguardando`, `pausada` e `encerrada` → zero linhas; `ativa` → grava. Ativar com item do portão em ❌ → 409 |
| **T-17** | Encerrar é terminal | `encerrada` → `POST /sistema/coleta/ativar` → 409; nenhuma rota leva de volta a `ativa` |
| **T-18** | A aba não identifica ninguém | Base com 3 contas num segmento → célula "< 5"; varre o JSON de toda rota `GET /sistema/*` (exceto `titulares`) com regex de UUID e de e-mail → nenhuma ocorrência |
| **T-19** | Data do beta = data publicada | `settings.beta_fim` formatado ("12 de setembro de 2027") aparece no Aviso e nos Termos publicados; `beta_inicio + 365 dias == beta_fim` |
| **T-20** | Toda ação administrativa deixa rastro | Cada rota de ação de `/sistema` grava exatamente uma linha em `sistema_acoes`; consulta de titular não grava o e-mail consultado em `parametros` nem no log de acesso |

Verificação por mutação, como no doc 44, nos três portões mais importantes:
remover a checagem do interruptor (T-04), a de versão dos termos (T-05) e o
CASCADE (T-09) precisa fazer o teste correspondente falhar.

---

## 11. Decisões em aberto

| ID | Decisão | Opções | Recomendação |
|---|---|---|---|
| **D-01** | Base legal do Nível B | (a) legítimo interesse + interruptor; (b) consentimento opt-in | **(a)**, pelas razões do §4.1. Se a assessoria jurídica preferir (b), o esquema não muda: o default de `uso_coleta_ativa` vira `False` e a tela de aceite ganha uma caixa à parte |
| **D-02** | Nível B ligado por padrão? | Sim / não | **Sim**, com a frase na tela de aceite e o interruptor a um clique |
| **D-03** | `project_id` no registro de IA | Guardar / não guardar | **Guardar**: "quanto custou este projeto" é a pergunta que o pesquisador mais faz. Pseudonimizado em qualquer exportação |
| **D-04** | Dados do beta vão para publicação (o estudo de `estudo_validacao/` ou outro)? | Sim / não / depois | **Só pelo Nível C**, com TCLE e consulta ao CEP. Nunca pelos dados já coletados sob legítimo interesse sem consentimento específico |
| **D-05** | Respeitar Global Privacy Control? | Sim / não | **Sim**, para o Nível B. Custa uma linha e é salvaguarda que pesa na LIA |
| **D-06** | Medir a landing e o blog? | Sim / não | **Não.** Quem visita não tem conta nem aceite, e o "sem rastreadores" do site público continua literalmente verdadeiro. Se for preciso, contagem agregada a partir do log do Caddy, sem IP |
| **D-07** ✅ | Data do fim do beta | — | **Fechada em 15/09/2026:** 1 ano, de 12/09/2026 a **12/09/2027**. O início é a vigência dos Termos 2.0, que declararam o BETA. Encerramento antecipado pela aba Sistema; prorrogação só com nova versão dos documentos (§6.6.4) |
| **D-09** | Início do ciclo de 1 ano | (a) vigência dos Termos 2.0, 12/09/2026; (b) data de ativação da coleta | **(a)**: é a data que os documentos já publicados usam para o BETA. Com (b), o fim mudaria conforme a data do deploy e só seria conhecido depois do aceite |
| **D-08** | Custo em R$ na tela de consumo | Agora / depois / nunca | **Depois**: tokens agora; custo estimado com tabela datada numa segunda etapa |

---

## 12. Riscos

| Risco | Efeito | Mitigação |
|---|---|---|
| Conteúdo vaza por mensagem de erro | Título, critério ou e-mail gravado fora do alcance do `DELETE /me` percebido pelo usuário | Sanitização em duas camadas; erro de banco só com o tipo; T-13; prazo de 90 dias |
| Reidentificação por combinação | Faixas + ambiente + horário apontam uma pessoa num beta pequeno | Faixas; ambiente reduzido; painel sem linha por pessoa e com grupos ≥ 5; exportação pseudonimizada |
| Uso de dados para vigiar pessoas | Orientador ou coordenador avalia ritmo de trabalho de estudante | P7 imposto por rota e testado (T-15); tempo por decisão só em agregado |
| Coleta antes do texto | Tratamento sem transparência (art. 9º) | Portão por versão dos termos (T-05); portão de ativação do §9 |
| Deriva entre aviso e código | A mesma falha que o `retencao.py` corrigiu | T-03, T-10 |
| Volume e custo de armazenamento | Tabela de eventos cresce sem controle | Lote e limite por sessão; retenção de 180 dias; agregação diária; meta de menos de 150 eventos por 10 minutos |
| Instrumentação que degrada a interface | Ouvintes e envio pesam na triagem de milhares de estudos | Um ouvinte delegado; envio em lote ocioso; nenhum evento por decisão de triagem (P2) |
| Reaproveitamento acadêmico indevido | Artigo com dado sem consentimento específico; problema ético e de base legal | D-04; §7.8; exportação registrada no ROPA |
| Leitura jurídica equivocada | Base legal ou enquadramento contestados | As leituras dos §§4, 7.2 e 7.3 estão marcadas para validação com assessoria antes do portão de ativação |
