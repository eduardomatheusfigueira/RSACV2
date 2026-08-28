# 37 — Diagnóstico de Conformidade à LGPD

> **Lei nº 13.709/2018 (LGPD), texto compilado** — inclui as alterações das
> Leis nº 13.853/2019, nº 14.010/2020, nº 14.460/2022 e nº 15.352/2026.
> **Objeto:** o RSAC V2 como está hoje (aplicativo de mesa) e como será quando
> for publicado como serviço com contas, dados pessoais de autores e cobrança.
> **Companheiro obrigatório:** [`38_CHECKLIST_LGPD.md`](./38_CHECKLIST_LGPD.md),
> que transforma este diagnóstico em itens verificáveis contra `arquivo:linha`.

---

## 37.1 Por que este documento existe

O planejamento de segurança (docs 28–30) respondeu a uma pergunta:
*quem consegue entrar?* Este documento responde a outra, que a primeira não
alcança: *o que estamos autorizados a fazer com o que está lá dentro, e o que
devemos ao titular daqueles dados?*

São perguntas independentes. Um sistema pode ter Argon2id, sessões revogáveis,
cifra de segredos e guarda de saída — o RSAC tem tudo isso — e ainda assim
tratar dado pessoal sem base legal, mandá-lo para fora do país sem salvaguarda
e não ter como responder a quem pedir sua eliminação. A LGPD não pergunta se o
sistema é seguro; pergunta se o tratamento é **legítimo, necessário,
transparente e reversível**. A segurança é um dos dez princípios do art. 6º,
não o conjunto deles.

O gatilho é a mudança de perímetro anunciada: sair do desktop, prestar serviço,
guardar dados pessoais dos autores e processar pagamentos. Essa mudança não
acrescenta uma camada de requisitos ao que existe — ela **troca o regime
jurídico aplicável**, como a §37.2 detalha.

---

## 37.2 A mudança de regime: de fora da lei para dentro dela

### 37.2.1 Hoje — o desenvolvedor não é agente de tratamento

No perfil `desktop`, o RSAC roda na máquina do pesquisador, grava em
`platformdirs.user_data_dir` (`app/config.py`, `data_dir`) e fala com o
provedor de IA usando **a chave do próprio usuário**. Nenhum dado pessoal
chega a quem escreveu o programa. Distribuir software não é tratar dados: o
agente de tratamento é o pesquisador que instala e opera.

Para esse pesquisador, duas exclusões do art. 4º costumam valer:

- **art. 4º, I** — tratamento por pessoa natural para fins exclusivamente
  particulares e não econômicos;
- **art. 4º, II, "b"** — tratamento para fins exclusivamente acadêmicos.

Aqui mora a armadilha mais comum. A exceção acadêmica **não é isenção**: o
próprio inciso determina que se apliquem os **arts. 7º e 11**. Ou seja, mesmo
a revisão sistemática puramente acadêmica precisa de **hipótese legal** para
tratar dado pessoal comum (art. 7º) e para tratar dado sensível (art. 11) — o
que, no caso, é confortável: art. 7º, IV (estudos por órgão de pesquisa, com
anonimização sempre que possível) e art. 11, II, "c" (equivalente para dado
sensível), quando o pesquisador estiver vinculado a órgão de pesquisa como
definido no art. 5º, XVIII.

### 37.2.2 Amanhã — duas funções ao mesmo tempo

Quando o RSAC for hospedado e cobrado, o desenvolvedor deixa de ser terceiro e
passa a ocupar **duas posições simultâneas**, com deveres diferentes:

| Conjunto de dados | Papel do RSAC | Por quê |
|---|---|---|
| Conta, e-mail, CPF, endereço de cobrança, histórico de pagamento, logs de acesso | **Controlador** (art. 5º, VI) | A decisão sobre finalidade e meios é do RSAC: ele decide cobrar, como cobrar, o que guardar e por quanto tempo. |
| Projetos, metadados bibliográficos, PDFs, matriz de extração — o conteúdo da revisão do assinante | **Operador** (art. 5º, VII) | Quem decide o que coletar, de quais bases e com que critérios é o pesquisador (ou a instituição dele). O RSAC executa em nome dele. |
| Métricas de uso agregadas para melhorar o produto | **Controlador** | Finalidade própria do RSAC — e por isso precisa de base legal própria (legítimo interesse, art. 7º, IX, com o teste do art. 10). |

Essa dupla função tem três consequências práticas que precisam existir **em
código e em contrato**, não só em política:

1. **Contrato de operador (art. 39).** O operador trata "segundo as instruções
   fornecidas pelo controlador". Os Termos de Uso precisam conter a cláusula
   que documenta essas instruções, os limites do tratamento e a proibição de
   uso próprio dos dados da revisão do assinante. Sem isso, o RSAC responde
   como controlador daquilo — e, pelo art. 42, §1º, I, o operador que
   descumpre as instruções **equipara-se ao controlador** e responde
   solidariamente.
2. **Isolamento entre assinantes.** É requisito de segurança (art. 46) e
   consequência direta do papel de operador: os dados de um controlador não
   podem alcançar outro. Ver achado **F-01**.
3. **Repasse de requisições.** Se um autor exercer o art. 18 contra o
   pesquisador, o RSAC precisa ter como cumprir a determinação do controlador
   — o que exige as rotas de acesso, correção e eliminação que hoje não
   existem (achado **F-03**).

### 37.2.3 O que a Lei nº 15.352/2026 mudou no texto compilado

O texto anexado traz quatro pontos de alteração pela Lei nº 15.352/2026. Três
são de estrutura da ANPD (Cap. IX, art. 55-A, art. 55-C, incisos V-A
Procuradoria, V-B Auditoria e VI) e um interessa diretamente ao RSAC:

> **art. 5º, VIII** — "encarregado: pessoa indicada **pelo controlador e
> operador** para atuar como canal de comunicação entre o controlador, os
> titulares dos dados e a Agência Nacional de Proteção de Dados (ANPD)."

A redação anterior falava apenas do controlador. A definição passou a alcançar
o operador. O art. 41, *caput*, continua redigido como dever do controlador —
mas a definição legal agora inclui o operador, o que recomenda tratar a
indicação do encarregado como exigível também na posição de operador. Como o
RSAC ocupará as duas posições, a questão é acadêmica: **haverá encarregado de
qualquer modo** (ver item L-31 do checklist).

---

## 37.3 Inventário de dados pessoais

O art. 5º, I define dado pessoal como "informação relacionada a pessoa natural
identificada ou **identificável**". O nome de um autor num registro
bibliográfico satisfaz a definição sem margem de dúvida — e o RSAC já os trata,
hoje, aos milhares.

### 37.3.1 O que o código já guarda (verificado)

| Dado | Onde vive | Titular | Categoria |
|---|---|---|---|
| Nome dos autores da publicação | `models.py:137` (`PaperModel.authors`) | Terceiro (autor) | Comum |
| Nome do orientador | `models.py:138` (`PaperModel.advisor`) | Terceiro | Comum |
| Instituição de vínculo | `models.py:143` | Terceiro | Comum (identificável em conjunto) |
| Texto integral do PDF | `settings.pdf_storage_dir`, `PaperModel.pdf_path` | Terceiros diversos | Comum e **potencialmente sensível** — teses de saúde trazem dados de participantes; agradecimentos trazem nomes, vínculos e às vezes convicções religiosas |
| Resumo, título | `models.py:136,144` | Terceiro | Comum |
| Usuário e papel da conta | `models.py:318` (`UserModel`) | Operador do sistema | Comum |
| Hash Argon2id da senha | `models.py:~326` | Operador | Comum (credencial) |
| `user_agent` da sessão | `models.py:361` | Operador | Comum |
| **Endereço IP** das tentativas de login | `models.py:380` (`LoginAttemptModel.client_host`) | Quem tentar entrar | Comum — IP é dado pessoal para os fins da LGPD |
| Autoria das decisões de triagem | `models.py:300-301` (`AuditLogModel.user_id`, `username`) | Operador | Comum |
| Log de execução | `<data_dir>/logs/harvest.log` (`main.py:44-56`) | Misto | Comum |

**Consequência que costuma passar despercebida:** o RSAC **já é** um sistema de
tratamento de dados pessoais de terceiros. A mudança para serviço online não
inaugura o tratamento — ela apenas transfere para o desenvolvedor a
responsabilidade por um tratamento que já acontece.

### 37.3.2 O que passará a existir quando houver serviço e cobrança

| Dado | Finalidade | Base legal proposta | Observação |
|---|---|---|---|
| Nome civil, e-mail | Identificação, contrato, suporte | art. 7º, V (execução de contrato) | Não usar consentimento: seria revogável a qualquer tempo (art. 8º, §5º) e derrubaria o serviço contratado |
| CPF / CNPJ | Emissão de nota fiscal | art. 7º, II (obrigação legal) | Coletar só na contratação paga, nunca no cadastro gratuito |
| Endereço de cobrança | Faturamento, apuração de tributo | art. 7º, II e V | — |
| Token do meio de pagamento | Cobrança recorrente | art. 7º, V | **Token do gateway, nunca o número do cartão** — ver §37.9 |
| Histórico de transações | Contrato, obrigação fiscal | art. 7º, V e II | Retenção fiscal de 5 anos |
| Sinais antifraude (IP, dispositivo) | Prevenção a fraude | art. 7º, IX (legítimo interesse) | Exige o teste do art. 10 documentado e transparência (art. 10, §2º) |
| Registros de acesso à aplicação | Segurança, prova, obrigação do Marco Civil | art. 7º, II e IX | Guarda mínima de 6 meses (art. 15 da Lei nº 12.965/2014) — e essa guarda é **piso**, não licença para guardar indefinidamente |
| Comunicações de suporte | Execução de contrato | art. 7º, V | — |

**Dado de menor de idade.** Um estudante de graduação pode ter menos de 18
anos. Se o serviço aceitar assinatura individual sem intermediação
institucional, o art. 14 entra em cena — inclusive o §5º, que exige "todos os
esforços razoáveis" para verificar o consentimento do responsável. A saída
mais limpa é contratual: restringir a contratação a maiores de 18 anos, com
declaração no aceite, e tratar assinaturas institucionais pela pessoa jurídica.

---

## 37.4 Bases legais por finalidade

O art. 7º exige uma hipótese **por finalidade**, não uma por sistema. O erro
mais caro é usar consentimento como base geral: ele é revogável a qualquer
momento por procedimento gratuito e facilitado (art. 8º, §5º), e autorizações
genéricas são **nulas** (art. 8º, §4º).

| Finalidade | Hipótese | Artigo |
|---|---|---|
| Manter a conta e prestar o serviço contratado | Execução de contrato | 7º, V |
| Cobrar, emitir nota, cumprir obrigação tributária | Obrigação legal | 7º, II |
| Tratar metadados bibliográficos e PDFs na revisão do assinante | **Como operador**, sob a base do controlador — tipicamente 7º, IV (estudos por órgão de pesquisa) ou 7º, IX | 7º, IV / IX; 39 |
| Prevenir fraude e abuso; segurança da plataforma | Legítimo interesse | 7º, IX + 10 |
| Guardar registros de acesso | Obrigação legal (Marco Civil) | 7º, II |
| Enviar comunicação de marketing | **Consentimento** | 7º, I + 8º |
| Melhorar o produto com métricas de uso | Legítimo interesse, se agregadas e minimizadas | 7º, IX + 10 |

**Dado sensível (art. 11).** O serviço não deveria coletar nenhum dado sensível
dos assinantes. O risco está em outra porta: o **conteúdo** que o assinante
carrega. Uma revisão sistemática em saúde traz PDFs com dados de saúde de
terceiros. Ali o RSAC é operador e a hipótese aplicável é a do controlador —
art. 11, II, "c" (estudos por órgão de pesquisa, com anonimização sempre que
possível). O art. 13, §2º acrescenta uma restrição dura para estudos em saúde
pública: **"não permitida, em circunstância alguma, a transferência dos dados a
terceiro"**. Esse dispositivo é o que torna o item **F-05** (envio de conteúdo
a provedores de IA) mais que uma formalidade quando o projeto for de saúde.

---

## 37.5 Ciclo de vida e eliminação

O art. 15 fixa quando o tratamento termina; o art. 16 determina que os dados
"serão eliminados após o término de seu tratamento", com quatro exceções
taxativas (obrigação legal, estudo por órgão de pesquisa, transferência a
terceiro conforme a lei, e uso exclusivo anonimizado).

O que existe hoje, medido no código:

- `DELETE /api/v1/projects/{id}` (`api/v1/projects.py:110`) apaga em cascata
  papers, fontes, critérios, extrações, auditoria, protocolo e execuções de
  coleta. A cascata é rigorosa **no banco**.
- Ela **não** apaga os PDFs do disco. `PDFService.delete_pdf`
  (`services/pdf_service.py:222`) existe e funciona, mas nenhum caminho de
  exclusão de projeto o chama. O arquivo — a peça com maior densidade de dado
  pessoal do acervo — sobrevive à exclusão do projeto que o trouxe. Achado
  **F-02**.
- Não há política de retenção para `LoginAttemptModel` (IP) nem para
  `SessionModel.user_agent`; as linhas ficam até alguém apagar o banco.
- `harvest.log` (`main.py:50`) usa `FileHandler` sem rotação nem expurgo: um
  arquivo que cresce indefinidamente, é copiado em backups e costuma ser
  anexado em pedido de suporte — o próprio doc 29 §29.4.4 reconhece essa
  viagem ao justificar o filtro de segredos. O filtro cobre credenciais; **não
  cobre dado pessoal**.

Prazos de retenção a fixar (proposta):

| Classe | Prazo | Fundamento |
|---|---|---|
| Registros fiscais e de pagamento | 5 anos | Prescrição tributária |
| Registros de acesso à aplicação | 6 meses (mínimo legal) a 12 meses | Art. 15 da Lei nº 12.965/2014 |
| Tentativas de login (IP) | 90 dias | Necessidade — a janela do limite é de 15 minutos (`sessions.py`, `LOGIN_WINDOW_MINUTES`) |
| Sessões expiradas | Já são apagadas na resolução (`sessions.py:resolve_session`) ✅ | Necessidade |
| Conteúdo da revisão do assinante | Enquanto durar o contrato + janela de resgate declarada (ex.: 30 dias) | Execução de contrato |
| Logs de aplicação | 90 dias, com rotação | Necessidade |
| Backups | Ciclo declarado, com eliminação propagada | Art. 16 |

**Backup é ponto cego clássico.** Eliminar o dado do banco e mantê-lo no backup
não cumpre o art. 16. O procedimento precisa declarar o ciclo de sobrescrita e,
quando a eliminação imediata no backup for tecnicamente inviável, registrar o
bloqueio (art. 5º, XIII) do dado para restauração.

---

## 37.6 Transferência internacional (arts. 33 a 36)

Este é o ponto onde o RSAC tem exposição concreta **hoje**, não amanhã.

Destinos de saída medidos no código:

| Destino | Onde | O que sai |
|---|---|---|
| Google Gemini (EUA) | `infrastructure/ai/gemini_client.py:37` | Título, **autores**, ano, resumo, critérios do protocolo; na extração, trechos do PDF |
| Alibaba DashScope (`intl`, `us`, `cn`) | `infrastructure/ai/openai_compatible_client.py:34-36` | Idem |
| OpenRouter | `openai_compatible_client.py:37` | Idem |
| Bases bibliográficas (PubMed, Scopus, OpenAlex, arXiv, Crossref, Unpaywall) | `app/harvesters/*`, `services/pdf_resolver.py` | Consultas e, no caso do Unpaywall, o `contact_email` configurado (`config.py`, `contact_email`) |

Enquanto o app é de mesa, quem transfere é o pesquisador, com a chave dele —
e o desenvolvedor não é parte. **Hospedado, a transferência passa a ser feita
pelo RSAC**, e o art. 33 exige uma das hipóteses:

- **art. 33, I** — país com grau de proteção adequado. Não é utilizável de
  imediato: depende de reconhecimento pela ANPD, e os EUA e a China não contam
  com essa declaração.
- **art. 33, II, "b"** — **cláusulas-padrão contratuais**. É o caminho
  praticável. A ANPD aprovou as cláusulas-padrão por resolução própria em 2024
  (Resolução CD/ANPD nº 19/2024, que também trata de cláusulas específicas e
  do regime de adequação dos contratos existentes). O uso das cláusulas-padrão
  **não pode ser alterado nas partes essenciais** — verificar a redação vigente
  antes de assinar.
- **art. 33, VIII** — consentimento específico e destacado, "com informação
  prévia sobre o caráter internacional da operação, distinguindo claramente
  esta de outras finalidades". Serve como reforço, não como base única: é
  revogável e contamina a continuidade do serviço.

**Recomendação de desenho, e não só de contrato.** O art. 6º, III (necessidade)
resolve boa parte do problema antes de ele virar jurídico: a triagem por
título e resumo **não precisa do nome dos autores**. Hoje ela os envia —
`infrastructure/ai/prompts.py:129` monta a variável e a linha 156 a insere no
corpo do prompt sob o rótulo `AUTORES:`. Remover esse campo do prompt de
triagem (ou torná-lo opcional, desligado por padrão) reduz a transferência
internacional de dado pessoal a praticamente zero na etapa mais volumosa do
fluxo — milhares de registros por revisão. É a medida de maior efeito e menor
custo deste diagnóstico. Achado **F-05**.

Para a extração assistida, em que o trecho do PDF é indispensável, a
salvaguarda tem de ser contratual (cláusulas-padrão) somada à opção, já
suportada pela arquitetura, de **provedor local** (`factory.py:70`, Ollama em
`localhost`) — que mantém o dado dentro da máquina e é a resposta correta para
projetos com dado sensível ou sob art. 13, §2º.

---

## 37.7 Direitos do titular (arts. 18, 19 e 20)

O art. 18 lista nove direitos exercíveis "a qualquer momento e mediante
requisição". O art. 19 fixa o prazo: **formato simplificado, imediatamente**;
ou declaração clara e completa em **até 15 dias**. O art. 18, §5º manda atender
**sem custo** para o titular.

Estado atual do código: **não existe nenhuma rota de atendimento a titular**.
O que existe são funções de backup do próprio operador
(`POST /api/v1/profile/export`, `api/v1/profile.py:99`), que não cumprem o
art. 18 — são ferramenta de conveniência do usuário sobre o workspace dele, não
resposta a uma requisição de titular com prazo, registro e prova de
atendimento.

Dois grupos de titulares, com caminhos diferentes:

- **Assinante do serviço** (titular direto, RSAC controlador): precisa de
  acesso, correção, portabilidade, eliminação da conta e informação sobre
  compartilhamento. Cabe rota autenticada no produto.
- **Autor de publicação** (titular indireto, RSAC operador): a requisição
  chega ao controlador — o pesquisador — ou diretamente ao RSAC, que deve
  encaminhá-la. O art. 18, §4º cobre exatamente esse caso: quando a
  providência imediata é impossível, responder comunicando que **não é o
  agente de tratamento** e indicando quem é. Isso precisa de um canal público
  e de um procedimento escrito, não de código.

**Art. 20 — decisão automatizada.** A triagem assistida por IA classifica
estudos como incluídos ou excluídos. A revisão do art. 20 é do titular cujos
interesses sejam afetados pela decisão — o encaixe com o autor do estudo é
discutível, e não é onde está o risco real. O risco real aparece quando houver
cobrança: **decisão automatizada antifraude que recuse uma assinatura afeta o
titular de forma inequívoca** e dispara o direito de revisão e o dever de
informar critérios (art. 20, §1º, observados segredo comercial e industrial).

Vale registrar o que o RSAC já faz certo aqui: `AuditLogModel`
(`models.py:288-311`) grava `ai_provider`, `ai_model`, `ai_context_sha256`,
`ai_response_valid`, `user_id` e `username`. Essa é, em substância, a
infraestrutura de prestação de contas que o art. 6º, X exige e que o art. 20,
§1º pressupõe. Poucos sistemas têm isso; o RSAC construiu por razão
metodológica e colheu conformidade de brinde.

---

## 37.8 Segurança, boas práticas e governança (arts. 46 a 50)

O art. 46 exige medidas técnicas e administrativas aptas; o §2º exige que sejam
observadas **"desde a fase de concepção do produto ou do serviço até a sua
execução"** — *privacy by design* positivado. O art. 50, §2º, I descreve o
programa de governança em privacidade, com oito alíneas.

O doc 29 entregou uma base sólida, que se aproveita quase inteira:

| Medida | Onde | Estado |
|---|---|---|
| Senha em Argon2id, política de 12 caracteres | `security/passwords.py` | ✅ |
| Sessão com estado, token só em hash, revogação imediata | `security/sessions.py` | ✅ |
| Limite de força bruta persistido em banco | `security/sessions.py`, `models.py:366` | ✅ |
| Autenticação por padrão no router agregador | `api/v1/router.py:39` | ✅ |
| Papéis `owner`/`researcher` nas rotas de credencial | `security/dependencies.py:require_owner` | ✅ |
| Cifra de segredos em repouso | `security/encrypted_type.py`, `crypto.py` | ✅ (só colunas de segredo) |
| Mascaramento de credencial nas respostas | `security/masking.py` | ✅ |
| Filtro de segredo em log | `security/log_filter.py` | ✅ (não cobre dado pessoal) |
| Guarda de saída contra SSRF e *DNS rebinding* | `security/egress.py` | ✅ |
| Cabeçalhos de segurança, CSP, HSTS | `security/middleware.py:33-69` | ✅ |
| Limite de taxa por família de rota | `security/middleware.py:94` | ✅ |
| Confinamento de caminho na SPA | `main.py:182-203` | ✅ |
| Suíte de testes de segurança | `backend/tests/test_security/` (12 arquivos) | ✅ |

O que falta é de natureza distinta — não é *hardening*, é proteção de dados:

- **Cifra do acervo em repouso.** `EncryptedText` protege chaves de API. O
  SQLite com nomes de autores, resumos e a matriz de extração fica em claro, e
  os PDFs também. Em máquina do pesquisador isso é aceitável (o sistema
  operacional é a fronteira). Em servidor multiusuário, não é: exige cifra de
  volume ou de banco.
- **Isolamento por assinante.** Ver F-01.
- **Registro das operações de tratamento (art. 37).** `AuditLogModel` registra
  decisões sobre estudos, não operações de tratamento de dados pessoais. O
  art. 37 obriga controlador **e operador** a manter esse registro,
  "especialmente quando baseado no legítimo interesse".
- **Relatório de impacto (RIPD, art. 5º, XVII e art. 38).** A ANPD pode
  determinar sua elaboração; com legítimo interesse como base (art. 10, §3º) o
  pedido é previsível. Além disso, o art. 50, §2º, I, "d" já exige políticas e
  salvaguardas baseadas em "processo de avaliação sistemática de impactos e
  riscos à privacidade" para quem adota programa de governança.

---

## 37.9 Incidente de segurança (art. 48)

O art. 48 obriga o controlador a comunicar à ANPD **e ao titular** o incidente
que possa acarretar risco ou dano relevante, em prazo razoável definido pela
autoridade. A ANPD regulamentou a matéria pela **Resolução CD/ANPD nº 15/2024**,
que fixa o prazo de **3 (três) dias úteis** contados do conhecimento do
incidente, com formulário próprio, e admite complementação posterior.

O art. 48, §1º lista o conteúdo mínimo da comunicação: natureza dos dados
afetados, informações sobre os titulares envolvidos, medidas técnicas de
proteção adotadas, riscos, motivos da demora e medidas de mitigação.

Dois detalhes que mudam o desenho do sistema:

- **art. 48, §3º** — na gravidade do incidente, pesa a comprovação de que foram
  adotadas medidas técnicas que tornem os dados afetados **ininteligíveis para
  terceiros não autorizados**. Isto é: **cifra em repouso reduz sanção**. É o
  argumento econômico direto para o item de cifra da §37.8.
- **art. 52, §7º** — vazamentos individuais podem ser objeto de conciliação
  direta entre controlador e titular. Ter canal de atendimento funcionando é o
  que torna essa via possível.

O RSAC não tem hoje procedimento de resposta a incidente com responsável,
prazo e modelo de comunicação. O art. 50, §2º, I, "g" exige "planos de resposta
a incidentes e remediação" como parte do programa de governança.

---

## 37.10 Dados financeiros: desfazendo um mal-entendido

**Dado financeiro não é dado pessoal sensível na LGPD.** O art. 5º, II traz
rol taxativo: origem racial ou étnica, convicção religiosa, opinião política,
filiação a sindicato ou a organização de caráter religioso, filosófico ou
político, dado referente à saúde ou à vida sexual, dado genético ou biométrico.
Cartão, renda e histórico de pagamento não estão na lista.

Isso **não** os torna banais. Três consequências reais:

1. **Art. 46 é proporcional ao risco**, e o risco de dado financeiro é alto —
   fraude, dano patrimonial direto. A medida "apta" para cartão é mais rigorosa
   que para um resumo de artigo.
2. **PCI-DSS não é a LGPD, e incide de qualquer forma.** É norma contratual das
   bandeiras. O desenho que reduz o escopo a quase nada é conhecido:
   **nunca tocar no número do cartão**. Usar gateway com tokenização (campos
   hospedados ou *redirect*), guardar apenas o token, a bandeira e os quatro
   últimos dígitos. Nunca gravar PAN completo, CVV ou trilha magnética — o CVV
   não pode ser armazenado **nem cifrado**, em nenhuma hipótese.
3. **O gateway é operador ou controlador conjunto**, conforme o arranjo, e
   normalmente processa fora do país. Cai no art. 33 (§37.6) e exige
   Acordo de Tratamento de Dados no contrato.

Se houver biometria para autenticação de pagamento, aí sim há dado sensível —
art. 11, II, "g" (prevenção à fraude e à segurança do titular nos processos de
identificação e autenticação de cadastro em sistemas eletrônicos) é a hipótese,
e ela vem com a ressalva expressa dos direitos do art. 9º.

---

## 37.11 Exposição a sanção e o regime de pequeno porte

O art. 52 prevê advertência; **multa simples de até 2% do faturamento no
Brasil, limitada a R$ 50 milhões por infração**; multa diária; publicização da
infração; bloqueio e eliminação dos dados; e, para reincidentes, suspensão
parcial do banco de dados por até 6 meses, suspensão da atividade de tratamento
e proibição parcial ou total do exercício.

O art. 52, §1º lista os parâmetros de dosimetria. Três deles são construídos
por documentação e não podem ser improvisados depois do incidente:

- **VIII** — adoção reiterada e demonstrada de mecanismos internos de
  minimização do dano;
- **IX** — adoção de política de boas práticas e governança;
- **X** — pronta adoção de medidas corretivas.

Ou seja: este documento e o checklist companheiro, **mantidos e datados**, são
eles próprios um fator de redução de sanção.

**Regime de pequeno porte.** A ANPD editou, com base no art. 55-J, XVIII, a
**Resolução CD/ANPD nº 2/2022**, que estabelece regras simplificadas para
agentes de tratamento de pequeno porte — incluindo microempresas, empresas de
pequeno porte, *startups* e pessoas naturais que tratam dados com fins
econômicos. O regime traz flexibilizações relevantes (entre elas, a dispensa da
indicação formal de encarregado, desde que se mantenha **canal de comunicação
com o titular**, e prazos diferenciados). Verificar o enquadramento antes de
dimensionar o programa: se o RSAC nascer como microempresa, boa parte do custo
de conformidade formal é reduzida — **nenhuma** das obrigações substantivas
(base legal, transparência, direitos, segurança, comunicação de incidente) é
dispensada.

---

## 37.12 Achados medidos no código

Cada achado tem evidência em `arquivo:linha`, o dispositivo que o sustenta e o
momento em que se torna exigível.

| # | Achado | Evidência | Artigo | Severidade | Exigível |
|---|---|---|---|---|---|
| **F-01** | Não há titularidade de projeto. `ProjectModel` não tem dono; qualquer conta autenticada, inclusive `researcher`, lê e apaga o acervo de qualquer outra. Como operador, isso é vazamento entre controladores. | `models.py:47`; `api/v1/projects.py` (nenhum filtro por usuário) | 46; 6º, VII | **Crítica** | Ao publicar com mais de um assinante |
| **F-02** | Exclusão de projeto não apaga os PDFs do disco. O arquivo com maior densidade de dado pessoal sobrevive à exclusão. | `api/v1/projects.py:110-155` não chama `services/pdf_service.py:222` | 16; 18, IV e VI | **Alta** | Já hoje |
| **F-03** | Não há rota de atendimento a requisição de titular (acesso, correção, portabilidade, eliminação, informação de compartilhamento). `/profile/export` é backup do workspace, não resposta a titular. | `api/v1/profile.py:99`; ausência de rotas em `api/v1/` | 18; 19 | **Alta** | Ao publicar |
| **F-04** | Não há registro das operações de tratamento (art. 37). `AuditLogModel` registra decisões sobre estudos, não operações sobre dados pessoais. | `models.py:288` | 37 | **Alta** | Ao publicar |
| **F-05** | O nome dos autores é enviado ao provedor de IA na triagem, sem necessidade funcional — em volume de milhares de registros por revisão, para fora do país. | `infrastructure/ai/prompts.py:129,156`; `gemini_client.py:37`; `openai_compatible_client.py:34-37` | 6º, III; 33 | **Alta** | Já hoje |
| **F-06** | Transferência internacional sem salvaguarda documentada (cláusulas-padrão ou consentimento específico e destacado). | mesmos destinos de F-05 | 33; 35 | **Alta** | Ao publicar |
| **F-07** | Não há aviso de privacidade nem página de política; nenhuma tela informa finalidade, duração, compartilhamento e direitos. | `frontend/src/pages/` — não há `PrivacyPage`/`TermsPage` | 9º; 6º, VI | **Alta** | Ao publicar |
| **F-08** | Nenhuma base legal é registrada ou apresentada; não há modelo de consentimento nem prova de obtenção (o ônus é do controlador). | ausência de modelo/rota | 7º; 8º, §2º | **Alta** | Ao publicar |
| **F-09** | Log de aplicação sem rotação nem expurgo, gravando indefinidamente em arquivo que viaja em backups e em pedidos de suporte. O filtro de segredos não cobre dado pessoal. | `main.py:44-56`; `security/log_filter.py` | 15; 16; 6º, III | **Média** | Já hoje |
| **F-10** | IP das tentativas de login e `user_agent` das sessões sem prazo de expurgo. | `models.py:361,380` | 15; 16 | **Média** | Já hoje |
| **F-11** | Acervo em claro no disco: só as colunas de segredo são cifradas; banco e PDFs não. Em servidor, art. 48, §3º torna isso caro. | `models.py` (`EncryptedText` só em `SourceCredentialModel`/`AISettingsModel`); `settings.pdf_storage_dir` | 46; 48, §3º | **Média** (Alta em servidor) | Ao publicar |
| **F-12** | Não há procedimento de resposta a incidente com responsável, prazo de 3 dias úteis e modelo de comunicação. | ausência documental | 48; Res. CD/ANPD 15/2024; 50, §2º, I, "g" | **Média** | Ao publicar |
| **F-13** | Não há encarregado indicado nem canal de comunicação publicado. | ausência | 41; 5º, VIII | **Média** | Ao publicar |
| **F-14** | Exportação de perfil sai em JSON claro com nomes de autores por padrão; a proteção por senha cobre apenas as credenciais (`include_secrets`). | `schemas/profile.py` (`ProfileExportRequest`); `api/v1/profile.py:99` | 46 | **Baixa** | Já hoje |
| **F-15** | Não há RIPD, nem gatilho definido para elaborá-lo quando o tratamento se apoiar em legítimo interesse. | ausência | 5º, XVII; 38; 10, §3º | **Baixa** | Ao publicar |

**Leitura do quadro.** Cinco achados já são exigíveis hoje, com o app de mesa —
e três deles (F-02, F-05, F-09) são correções de código pequenas, localizadas,
sem dependência de decisão jurídica ou comercial. São o ponto de partida
natural.

---

## 37.13 O que este documento não cobre

- **Redação dos instrumentos jurídicos.** Termos de Uso, Aviso de Privacidade,
  Acordo de Tratamento de Dados com o gateway e cláusulas-padrão de
  transferência internacional precisam de revisão por advogado. Este
  diagnóstico diz *o que* precisa constar e *por quê*; não substitui a peça.
- **Enquadramento societário e tributário** do serviço, que determina o
  regime de pequeno porte da Resolução CD/ANPD nº 2/2022.
- **PCI-DSS na íntegra.** A §37.10 fixa o desenho que mantém o escopo mínimo;
  a certificação, se exigida pelo adquirente, tem trilha própria.
- **Direito do consumidor.** O art. 45 preserva as regras do CDC para as
  relações de consumo, e o serviço pago será uma. O CDC é outro eixo de
  conformidade, com deveres próprios de informação e arrependimento.
- **Normas setoriais de ética em pesquisa** (CEP/CONEP), que podem incidir
  sobre o assinante e não sobre a plataforma, mas moldam o que ele pode
  carregar.

---

## 37.14 Fonte normativa

- **Lei nº 13.709/2018**, texto compilado, `planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm`,
  com as alterações das Leis nº 13.853/2019, nº 14.010/2020, nº 14.460/2022 e
  nº 15.352/2026 — versão consultada e anexada ao repositório de planejamento.
- **Lei nº 12.965/2014** (Marco Civil da Internet), arts. 7º e 15, alterados
  pelo art. 60 da LGPD.
- **Resoluções CD/ANPD** citadas: nº 2/2022 (agentes de pequeno porte),
  nº 4/2023 (dosimetria de sanções), nº 15/2024 (comunicação de incidente),
  nº 19/2024 (transferência internacional). **Confirmar a redação vigente na
  ANPD antes de aplicar** — o regulamento infralegal muda com frequência maior
  que a lei, e este documento fixa o estado de agosto de 2026.
