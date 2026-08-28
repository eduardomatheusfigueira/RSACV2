# 38 — Checklist de Conformidade à LGPD

> **Instrumento de verificação.** Cada item é uma afirmação que se **confronta
> com o código** — há um caminho de arquivo, um comando ou um artefato a
> exibir. Item sem evidência verificável é item não atendido.
> **Base:** [`37_DIAGNOSTICO_LGPD.md`](./37_DIAGNOSTICO_LGPD.md).
> **Norma:** Lei nº 13.709/2018, texto compilado (até a Lei nº 15.352/2026).
> **Estado aferido em:** 27/08/2026, contra a árvore de trabalho do repositório.
> **Reaferido em 27/08/2026** após as Fases 0 e 1 do doc 41: **L-24** e **L-46**
> passaram a ✅, com teste de regressão e verificação por mutação.

---

## Como usar

1. **Consultar** antes de abrir qualquer trabalho que toque dado pessoal —
   conta, cobrança, envio a terceiro, log, exportação, exclusão.
2. **Confrontar** rodando a verificação da coluna *Como conferir*. Os comandos
   são executáveis a partir da raiz do repositório.
3. **Reaferir** a cada release e sempre que o perfil de implantação mudar.
   Datar a reaferição: o art. 52, §1º, VIII e IX transforma histórico
   documentado em redução de sanção.

### Legenda de estado

| Símbolo | Significado |
|---|---|
| ✅ | Atendido — verificado no código nesta data |
| ⚠️ | Parcial — existe, mas não cobre o exigido |
| ❌ | Ausente — exigível **hoje**, no app de mesa |
| 🔜 | Ausente — torna-se exigível **quando o serviço for publicado/cobrado** |
| 📄 | Depende de artefato jurídico ou processual, não de código |

### Corte por momento

> **Bloco imediato (app de mesa, hoje):** L-11, L-24, L-25, L-27, L-40, L-46.
> São correções de código pequenas e independentes de decisão jurídica.
>
> **Portão de publicação:** nenhum item ❌ ou 🔜 marcado como *Bloqueante*
> pode permanecer aberto quando o perfil `server` for exposto com mais de um
> assinante.

---

## Bloco A — Escopo, papéis e mapa de dados

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-01** | Está declarado por escrito em quais conjuntos o Revsist é **controlador** e em quais é **operador** | 5º, VI e VII | `37_DIAGNOSTICO_LGPD.md` §37.2.2 | ✅ |
| **L-02** | Existe inventário atualizado dos dados pessoais tratados, com onde vivem no código | 37; 6º, X | `37_DIAGNOSTICO_LGPD.md` §37.3; conferir contra `grep -n "Mapped\[str\]" backend/app/infrastructure/persistence/models.py` | ✅ |
| **L-03** | O inventário é reaferido a cada modelo novo com dado pessoal | 6º, X | Revisão de PR que altere `models.py` | 📄 |
| **L-04** | Os Termos de Uso contêm cláusula de operador com as instruções documentadas do controlador e proibição de uso próprio dos dados da revisão | 39; 42, §1º, I | Artefato jurídico | 📄 🔜 **Bloqueante** |
| **L-05** | Contrato com o gateway de pagamento define papel, finalidade e devolução/eliminação ao fim | 39; 16 | Artefato jurídico | 📄 🔜 **Bloqueante** |

---

## Bloco B — Bases legais

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-06** | Cada finalidade tem hipótese legal declarada; nenhuma finalidade roda "por omissão" | 7º | `37_DIAGNOSTICO_LGPD.md` §37.4 (tabela) | ⚠️ documentado, não implementado |
| **L-07** | O serviço contratado **não** se apoia em consentimento (que seria revogável e derrubaria a prestação) | 7º, V; 8º, §5º | Revisar o aviso de privacidade quando existir | 📄 🔜 |
| **L-08** | Onde houver consentimento (marketing), ele é específico, destacado, finalístico e **registrado com prova** — o ônus é do controlador | 8º, §2º e §4º | Não há modelo de consentimento no código: `grep -rn "consent" backend/app frontend/src` retorna vazio | ❌ 🔜 **Bloqueante** |
| **L-09** | Consentimento é revogável por procedimento gratuito e facilitado | 8º, §5º | Rota/tela de revogação | 🔜 |
| **L-10** | Uso de legítimo interesse (antifraude, métricas) tem **teste de balanceamento documentado** e só trata o estritamente necessário | 10; 10, §1º | Artefato + revisão do que é coletado | 📄 🔜 |
| **L-11** | Nenhum campo pessoal é enviado a terceiro sem necessidade funcional | 6º, III | `sed -n '125,160p' backend/app/infrastructure/ai/prompts.py` — hoje `AUTORES:` vai no prompt de triagem (linhas 129 e 156) sem função na decisão | ❌ **imediato** (F-05) |

---

## Bloco C — Transparência

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-12** | Existe aviso de privacidade acessível, informando finalidade específica, forma e duração do tratamento, identificação e contato do controlador, uso compartilhado e finalidade, responsabilidades dos agentes e **menção explícita aos direitos do art. 18** | 9º, I a VII | `ls frontend/src/pages` — não há `PrivacyPage`/`TermsPage` | ❌ 🔜 **Bloqueante** |
| **L-13** | Quando o tratamento for condição para o fornecimento do serviço, o titular é informado **com destaque** desse fato e dos meios de exercer seus direitos | 9º, §3º | Tela de cadastro | 🔜 |
| **L-14** | Mudança de finalidade incompatível é informada previamente, com opção de revogar | 9º, §2º; 8º, §6º | Processo de release | 📄 🔜 |
| **L-15** | A transparência do legítimo interesse é ativa, não apenas responsiva | 10, §2º | Aviso de privacidade | 📄 🔜 |
| **L-16** | O caráter internacional do tratamento é informado de forma destacada e distinta de outras finalidades | 33, VIII | Aviso de privacidade + tela de configuração de IA | ❌ 🔜 |

---

## Bloco D — Direitos do titular

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-17** | Existe canal de requisição de titular, funcionando e divulgado | 18; 41, §1º | Nenhuma rota: `grep -rn "titular\|data-subject" backend/app/api` | ❌ 🔜 **Bloqueante** |
| **L-18** | Confirmação de existência e acesso: formato simplificado **imediato**, ou declaração completa em **até 15 dias** | 19, I e II | Rota + medição de prazo | ❌ 🔜 |
| **L-19** | Correção de dados incompletos, inexatos ou desatualizados | 18, III | Rota autenticada de perfil | 🔜 |
| **L-20** | Anonimização, bloqueio ou eliminação de dado desnecessário, excessivo ou tratado em desconformidade | 18, IV | Rota + procedimento | 🔜 |
| **L-21** | Portabilidade a outro fornecedor, em formato de uso subsequente | 18, V; 19, §3º | `POST /api/v1/profile/export` (`api/v1/profile.py:99`) exporta o workspace, mas não é requisição de titular nem cobre dado de conta/cobrança | ⚠️ 🔜 |
| **L-22** | Eliminação dos dados tratados com consentimento, ressalvado o art. 16 | 18, VI | Rota de exclusão de conta | ❌ 🔜 **Bloqueante** |
| **L-23** | Informação sobre com quem houve uso compartilhado, e sobre a possibilidade e as consequências de não consentir | 18, VII e VIII | Aviso de privacidade + rota | ❌ 🔜 |
| **L-24** | A eliminação alcança **todos** os repositórios, inclusive arquivos fora do banco | 16; 18, IV e VI | `DELETE /projects/{id}` chama `PDFService.delete_pdf` para cada estudo; teste `test_excluir_projeto_apaga_os_pdfs_do_disco` confere o disco | ✅ (F-02 fechado, Fase 1) |
| **L-25** | A correção/eliminação é comunicada aos agentes com quem houve uso compartilhado, salvo impossibilidade comprovada | 18, §6º | Procedimento; hoje inexistente | ❌ 🔜 |
| **L-26** | Requisição de titular é atendida **sem custo** | 18, §5º | Política de atendimento | 📄 🔜 |
| **L-27** | Havendo requisição sobre dado de terceiro em que o Revsist não é o agente (autor de publicação), a resposta comunica isso e indica o agente | 18, §4º, I | Procedimento escrito | 📄 🔜 |

---

## Bloco E — Ciclo de vida, retenção e eliminação

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-28** | Há tabela de retenção por classe de dado, com prazo e fundamento | 15; 16 | `37_DIAGNOSTICO_LGPD.md` §37.5 (proposta); implementação pendente | ⚠️ |
| **L-29** | Sessões expiradas são eliminadas | 16 | `backend/app/security/sessions.py`, `resolve_session` apaga a linha vencida | ✅ |
| **L-30** | Tentativas de login (que gravam **IP**) têm expurgo automático | 15, I; 16 | `grep -n "class LoginAttemptModel" -A 12 backend/app/infrastructure/persistence/models.py` (linha 366) — nenhuma rotina de expurgo | ❌ **imediato** (F-10) |
| **L-31** | `user_agent` de sessão tem prazo de vida definido | 16 | `models.py:361` | ⚠️ (some com a sessão; sem política escrita) |
| **L-32** | Log de aplicação tem rotação e expurgo | 6º, III; 16 | `sed -n '40,58p' backend/app/main.py` — `FileHandler` sem rotação; sem expurgo de `harvest.log` | ❌ **imediato** (F-09) |
| **L-33** | Log não grava dado pessoal desnecessário; há filtro ativo | 6º, III | `backend/app/security/log_filter.py` cobre **credenciais**, não dado pessoal | ⚠️ |
| **L-34** | A eliminação se propaga aos backups, ou o bloqueio é registrado quando propagar for inviável | 16; 5º, XIII | Procedimento de backup | 📄 🔜 **Bloqueante** |
| **L-35** | Encerrada a assinatura, há janela de resgate declarada e eliminação efetiva ao fim dela | 15, II; 16 | Termos + rotina | 🔜 |

---

## Bloco F — Compartilhamento e transferência internacional

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-36** | O mapa de destinos externos está atualizado | 9º, V | `grep -rn "https://" backend/app/infrastructure/ai/*.py backend/app/harvesters/*.py backend/app/services/pdf_resolver.py` | ✅ (§37.6) |
| **L-37** | Toda transferência internacional tem hipótese do art. 33 identificada | 33 | Hoje nenhuma salvaguarda documentada para Gemini (`gemini_client.py:37`), DashScope (`openai_compatible_client.py:34-36`) e OpenRouter (linha 37) | ❌ 🔜 **Bloqueante** |
| **L-38** | Havendo cláusulas-padrão contratuais, elas estão assinadas e não alteradas em partes essenciais | 33, II, "b"; 35 | Artefato jurídico (Res. CD/ANPD nº 19/2024) | 📄 🔜 |
| **L-39** | Alterações nas garantias apresentadas são comunicadas à ANPD | 36 | Procedimento | 📄 🔜 |
| **L-40** | Há alternativa que dispensa a transferência para quem precisar dela (provedor local) | 6º, III; 46 | `backend/app/infrastructure/ai/factory.py:70` — endpoint local (Ollama) suportado | ✅ |
| **L-41** | Projetos com dado de saúde sob art. 13 podem operar **sem** enviar conteúdo a terceiro | 13, §2º | Combinação de L-40 com trava por projeto — a trava não existe | ⚠️ |
| **L-42** | O `contact_email` enviado a APIs externas (Unpaywall/OpenAlex/Crossref) é escolha informada do usuário | 9º | `backend/app/config.py`, `contact_email` — vazio por padrão, a via é pulada sem ele | ✅ |

---

## Bloco G — Segurança (art. 46 a 49)

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-43** | Senha nunca em claro; hash moderno | 46 | `backend/app/security/passwords.py` — Argon2id, mínimo 12 caracteres | ✅ |
| **L-44** | Sessão revogável, token guardado só em hash | 46 | `backend/app/security/sessions.py` | ✅ |
| **L-45** | Autenticação é o padrão; rota nova nasce protegida | 46 | `backend/app/api/v1/router.py:39` (dependência no router agregador) | ✅ |
| **L-46** | **Isolamento entre assinantes**: cada acervo só é alcançável por quem tem direito a ele | 46; 6º, VII | `ProjectModel.owner_id` + dependência `projeto_do_usuario` nos nove routers; `backend/tests/test_security/test_tenancy_isolation.py` enumera as rotas pelo OpenAPI e exige 404 | ✅ (F-01 fechado, Fase 1) |
| **L-47** | Segregação de privilégio: quem tria não alcança credencial | 46 | `backend/app/security/dependencies.py`, `require_owner` | ✅ |
| **L-48** | Credenciais cifradas em repouso | 46 | `backend/app/security/encrypted_type.py`, `crypto.py` | ✅ |
| **L-49** | **Acervo** (banco e PDFs) cifrado em repouso no servidor — reduz gravidade de incidente | 46; 48, §3º | Só colunas de segredo usam `EncryptedText`; SQLite e `pdf_storage_dir` em claro | ❌ 🔜 **Bloqueante** (F-11) |
| **L-50** | Tráfego em HTTPS, com HSTS no perfil publicado | 46 | `backend/app/security/middleware.py:63-67` | ✅ |
| **L-51** | Cabeçalhos de segurança e CSP aplicados a toda resposta | 46 | `backend/app/security/middleware.py:43-58` | ✅ |
| **L-52** | Limite de taxa e de força bruta | 46 | `middleware.py:94`; `sessions.py` (`LOGIN_MAX_ATTEMPTS`) | ✅ |
| **L-53** | Guarda contra requisição de saída forjada (SSRF, *DNS rebinding*, redirecionamento) | 46 | `backend/app/security/egress.py` | ✅ |
| **L-54** | Confinamento de caminho: nenhuma travessia serve o banco | 46 | `backend/app/main.py:182-203`; teste em `backend/tests/test_security/test_path_traversal.py` | ✅ |
| **L-55** | Erro interno não vaza detalhe de implementação | 46 | `backend/app/security/middleware.py:165-200` | ✅ |
| **L-56** | Segurança verificada por testes automatizados que impedem regressão | 46; 50, §2º, I, "h" | `ls backend/tests/test_security/` — 12 arquivos; CI em `.github/workflows/` | ✅ |
| **L-57** | Segurança observada **desde a concepção** — a decisão de privacidade entra no desenho, não no fim | 46, §2º | Este checklist consultado antes de abrir trabalho novo | 📄 |
| **L-58** | Dever de sigilo alcança quem intervém em qualquer fase, mesmo após o término | 47 | Cláusula em contrato de prestador | 📄 🔜 |
| **L-59** | Exportação de dados pessoais sai protegida por padrão | 46 | `backend/app/schemas/profile.py` (`ProfileExportRequest.include_secrets=False`) — protege credencial, não o acervo com nomes de autores | ⚠️ (F-14) |

---

## Bloco H — Governança e prestação de contas

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-60** | **Registro das operações de tratamento** mantido por controlador e operador | 37 | `AuditLogModel` (`models.py:288`) registra decisão sobre estudo, não operação de tratamento de dado pessoal | ❌ 🔜 **Bloqueante** (F-04) |
| **L-61** | Encarregado indicado, com identidade e contato divulgados de forma clara e objetiva, preferencialmente no sítio eletrônico | 41; 41, §1º; 5º, VIII (red. Lei nº 15.352/2026) | Ausente; verificar enquadramento em agente de pequeno porte (Res. CD/ANPD nº 2/2022), que pode dispensar a indicação formal **mantido o canal com o titular** | ❌ 🔜 |
| **L-62** | Programa de governança em privacidade com as oito alíneas do art. 50 | 50, §2º, I, "a" a "h" | Docs 37 e 38 cobrem parte; faltam plano de incidente ("g") e monitoramento contínuo ("h") | ⚠️ 🔜 |
| **L-63** | Avaliação sistemática de impactos e riscos à privacidade sustenta as salvaguardas | 50, §2º, I, "d" | Este diagnóstico é o primeiro ciclo; falta periodicidade definida | ⚠️ |
| **L-64** | RIPD elaborado quando o tratamento representar alto risco, ou a pedido da ANPD | 5º, XVII; 38; 10, §3º | Ausente; gatilho a definir | ❌ 🔜 (F-15) |
| **L-65** | Proveniência das decisões assistidas por IA é registrada e auditável | 6º, X; 20, §1º | `models.py:288-311` grava `ai_provider`, `ai_model`, `ai_context_sha256`, `ai_response_valid`, `user_id`, `username` | ✅ |
| **L-66** | Este checklist é reaferido e datado a cada release | 52, §1º, VIII, IX e X | Cabeçalho deste documento | 📄 |

---

## Bloco I — Incidente de segurança

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-67** | Existe plano de resposta a incidente, com responsável nomeado | 50, §2º, I, "g" | Ausente | ❌ 🔜 **Bloqueante** |
| **L-68** | Comunicação à ANPD e ao titular em prazo — **3 dias úteis** do conhecimento, conforme Resolução CD/ANPD nº 15/2024 | 48; 48, §1º | Procedimento + modelo | ❌ 🔜 |
| **L-69** | O modelo de comunicação cobre os seis itens do art. 48, §1º | 48, §1º, I a VI | Artefato | 📄 🔜 |
| **L-70** | Há capacidade de demonstrar que os dados afetados estavam ininteligíveis a terceiros (reduz a gravidade) | 48, §3º | Depende de L-49 | ❌ 🔜 |
| **L-71** | Há trilha suficiente para reconstituir o que foi acessado num incidente | 46; 48, §1º, II | Log de aplicação sem correlação por titular | ⚠️ |

---

## Bloco J — Cobrança e dados financeiros

> Dado financeiro **não** é dado sensível na LGPD (art. 5º, II é rol taxativo).
> O rigor vem do art. 46, proporcional ao risco, e do PCI-DSS, que é contratual.

| ID | Exigência | Referência | Como conferir | Estado |
|---|---|---|---|---|
| **L-72** | O sistema **nunca** recebe nem armazena número completo de cartão, CVV ou trilha magnética | 46; PCI-DSS | Gateway com tokenização (campos hospedados ou *redirect*); auditar ausência de campo de cartão no frontend | 🔜 **Bloqueante** |
| **L-73** | Guardam-se apenas token do gateway, bandeira e quatro últimos dígitos | 6º, III | Modelo de dados de cobrança | 🔜 |
| **L-74** | CPF só é coletado quando houver obrigação fiscal, nunca no cadastro gratuito | 6º, III; 7º, II | Tela de contratação | 🔜 |
| **L-75** | Dados de cobrança têm retenção fiscal declarada (5 anos) e não caem na eliminação por pedido do titular enquanto o prazo correr | 16, I | Tabela de retenção | 🔜 |
| **L-76** | O contrato com o gateway trata a transferência internacional, se ele processar fora do país | 33 | Ver L-37/L-38 | 📄 🔜 |
| **L-77** | Se houver biometria na autenticação de pagamento, a hipótese do art. 11, II, "g" está declarada e os direitos do art. 9º resguardados | 11, II, "g" | Só se aplicável | ⬜ |

---

## Bloco K — Crianças e adolescentes

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-78** | Está definido se o serviço aceita titular menor de 18 anos | 14 | Termos de Uso | 📄 🔜 **Bloqueante** |
| **L-79** | Havendo criança, o consentimento é específico, destacado e dado por ao menos um dos pais ou responsável, com esforços razoáveis de verificação | 14, §1º e §5º | Fluxo de cadastro | ⬜ 🔜 |
| **L-80** | Não se condiciona o uso ao fornecimento de dado além do estritamente necessário | 14, §4º | Tela de cadastro | 🔜 |
| **L-81** | Informação apresentada de forma simples, clara e acessível, adequada ao entendimento | 14, §6º | Aviso de privacidade | 📄 🔜 |

---

## Bloco L — Decisão automatizada

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-82** | Decisão automatizada que afete interesses do titular admite pedido de revisão | 20 | Aplicável à recusa antifraude na cobrança; inexistente hoje | 🔜 |
| **L-83** | São fornecidos, quando solicitados, critérios e procedimentos da decisão automatizada, observados os segredos comercial e industrial | 20, §1º | Aviso de privacidade + trilha de `AuditLogModel` | ⚠️ 🔜 |
| **L-84** | A triagem assistida jamais é apresentada como decisão sem responsável humano identificado | 20; 6º, X | `models.py:300-301` grava `user_id`/`username` da decisão | ✅ |

---

## Bloco M — Conteúdo carregado pelo assinante

| ID | Exigência | Art. | Como conferir | Estado |
|---|---|---|---|---|
| **L-85** | Os Termos deixam claro que o assinante é o controlador do que carrega e responde pela licitude daquele tratamento | 39; 42 | Artefato jurídico | 📄 🔜 **Bloqueante** |
| **L-86** | O Revsist não usa o conteúdo do assinante para finalidade própria (treinar modelo, gerar métrica identificável) | 39; 6º, I | Revisão de código de qualquer rotina que leia acervo de terceiro | 🔜 |
| **L-87** | Anonimização ou pseudonimização é oferecida sempre que possível nos estudos | 7º, IV; 11, II, "c"; 13, §4º | Não há função de anonimização no acervo | ⚠️ |
| **L-88** | Há trava por projeto que impede envio de conteúdo a terceiro quando o projeto for de saúde sob art. 13 | 13, §2º | Inexistente — ver L-41 | ❌ 🔜 |

---

## Resumo aferido em 27/08/2026

**88 itens.** Estado predominante de cada um:

| Estado | Quantidade |
|---|---|
| ✅ Atendido — verificado no código | 20 |
| ⚠️ Parcial | 12 |
| ❌ Ausente | 22 |
| 📄 Depende de artefato jurídico ou processual | 20 |
| 🔜 Pendente, exigível só ao publicar | 12 |
| ⬜ Não aplicável hoje | 2 |

Dos 88, **51 só se tornam exigíveis quando o serviço for publicado** — o que
mede o tamanho real do trabalho que a mudança de perímetro traz.

**Exigíveis hoje, no app de mesa (correção de código, sem dependência
jurídica):**

- **L-11** — remover `AUTORES:` do prompt de triagem (`prompts.py:129,156`)
- **L-24** — chamar `PDFService.delete_pdf` na exclusão de projeto (`projects.py:110`)
- **L-30** — expurgo de `LoginAttemptModel` (IP)
- **L-32** — rotação e expurgo de `harvest.log` (`main.py:44-56`)

**Bloqueantes do portão de publicação** (nenhum pode permanecer aberto quando
o perfil `server` for exposto com mais de um assinante):

L-04, L-05, L-08, L-12, L-17, L-22, L-34, L-37, **L-46**, L-49, L-60, L-67,
L-72, L-78, L-85.

> **L-46 é o crítico.** Sem titularidade de projeto, publicar o serviço para
> dois assinantes é entregar o acervo de um ao outro — e, na posição de
> operador, vazamento entre controladores distintos.
