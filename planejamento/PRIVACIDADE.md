# Aviso de Privacidade e Tratamento de Dados Pessoais — Revsist

**Versão:** 1.0  
**Data de Vigência:** 29 de agosto de 2026  
**Última Atualização:** 29 de agosto de 2026  

O presente Aviso de Privacidade descreve, de forma clara, transparente e acessível, como a plataforma **Revsist** ("Revsist", "Nós" ou "Sistema") coleta, armazena, utiliza, compartilha e descarta dados pessoais de pesquisadores e usuários cadastrados ("Titulares" ou "Você"), em estrita conformidade com a **Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018 — LGPD)**.

---

## 1. Identificação do Controlador e Encarregado (DPO)

- **Controlador do Tratamento:** [INSERIR RAZÃO SOCIAL / NOME DO CONTROLADOR OU INSTITUIÇÃO]  
  - **CNPJ / Identificador:** [INSERIR CNPJ / IDENTIFICADOR INSTITUCIONAL]  
  - **Endereço / Sede:** [INSERIR ENDEREÇO DA SEDE / CAMPUS]  
- **Canal de Atendimento ao Titular e Encarregado (DPO):**  
  - **E-mail de Contato do Encarregado:** `[INSERIR EMAIL DO ENCARREGADO / DPO: ex: dpo@revsist.org / privacidade@revsist.org]`  
  - **Canal de Requisição de Direitos:** Disponível diretamente na interface da plataforma na seção `/me` e pelo e-mail institucional indicado.  
  - *Nota sobre Agente de Tratamento de Pequeno Porte:* Caso aplicável o enquadramento na Resolução CD/ANPD nº 2/2022, o Revsist mantém canal formal de atendimento eletrônico ao titular para o exercício dos direitos previstos no art. 18 da LGPD.

---

## 2. Dados Coletados, Origem e Finalidades de Tratamento

O Revsist adota o princípio da minimização da coleta (Art. 6º, III da LGPD), restringindo o tratamento aos dados estritamente necessários para a execução das funcionalidades da ferramenta:

| Categoria de Dados | Dados Específicos | Origem | Finalidade do Tratamento | Base Legal (Art. 7º LGPD) |
|---|---|---|---|---|
| **Identificação e Contato** | Nome completo/exibição, endereço de e-mail | Cadastro direto pelo usuário ou importação via Google OAuth | Identificação de autoria em revisões sistemáticas, comunicação e acesso | Art. 7º, V (Execução de Contrato) / Art. 7º, I (Consentimento) |
| **Credenciais e Acesso** | Hash criptográfico de senha (Argon2id), identificador Google Sub, tokens de sessão | Cadastro e autenticação do titular | Autenticação, controle de sessão seguro e prevenção a acessos não autorizados | Art. 7º, V (Execução de Contrato) / Art. 7º, II (Segurança) |
| **Conexão e Segurança** | Endereço IP de tentativas de login, data e hora | Cabeçalhos HTTP durante autenticação | Prevenção a ataques de força bruta, auditoria técnica e mitigação de incidentes | Art. 7º, IX (Legítimo Interesse) / Art. 7º, II (Marco Civil da Internet) |
| **Conteúdo de Pesquisa** | Protocolos de revisão, critérios PICO, artigos bibliográficos, extrações e anotações | Inserção direta pelo pesquisador ou colheita em bases públicas (BDTD, SciELO, Scopus, PubMed, OpenAlex) | Gestão, triagem metodológica e extração de síntese de evidências científicas | Art. 7º, V (Execução de Contrato) |
| **Credenciais de Fontes (BYOK)** | Chaves de API de provedores de IA (Gemini, Qwen) e bases científicas | Inserção explícita pelo titular | Habilitação de consultas externas autorizadas pelo próprio pesquisador | Art. 7º, V (Execução de Contrato) |

> **Atenção sobre Minimização em Inteligência Artificial:**  
> O Revsist **não envia nomes de autores de artigos científicos** para provedores de IA durante a triagem automatizada. Apenas o título, o resumo e os critérios metodológicos do protocolo são encaminhados para a avaliação de elegibilidade.

---

## 3. Transferência Internacional de Dados (LGPD Art. 33)

1. **Serviços de Terceiros e Modelos de IA (BYOK — Bring Your Own Key):**
   - **Google Gemini:** O envio de títulos e resumos para análise ocorre mediante uso de chave de API configurada pelo próprio pesquisador, com processamento em servidores da Google LLC nos **Estados Unidos**.
   - **Alibaba Qwen:** O processamento ocorre na região configurada pelo usuário (ex: Singapura ou região internacional).
   - **Modelos Locais (Ollama / LM Studio):** Não há transferência externa; o processamento ocorre 100% no ambiente local do próprio pesquisador.
2. **Salvaguardas:**
   - As transferências de metadados de estudos ocorrem por decisão explícita do titular ao habilitar suas chaves de API, cumprindo o disposto no Art. 33, VIII e IX da LGPD.

---

## 4. Política de Retenção e Descarte de Dados (LGPD Art. 15 e 16)

Os dados pessoais tratados pelo Revsist são mantidos apenas pelo período necessário para atender às finalidades de pesquisa e obrigações legais de segurança:

- **Tentativas de Login e Logs de IP:** Mantidos por até **90 dias** e expurgados automaticamente para cumprimento do princípio da necessidade.
- **Tokens Temporários de OAuth (PKCE):** Mantidos por no máximo **10 minutos** com expurgo automático após utilização.
- **Sessões Web Encerradas/Expiradas:** Eliminadas de forma contínua do banco de dados.
- **Backups Criptografados do Sistema:** Retidos em armazenamento seguro por até **30 dias**, sendo sobrescritos ciclicamente.
- **Registros de ROPA (Registro de Operações de Tratamento):** Retidos pelo prazo prescricional de **5 anos** (Art. 37 c/c Art. 16, I da LGPD) contendo exclusivamente metadados operacionais estruturados (sem armazenamento de conteúdo pessoal ou acadêmico).

---

## 5. Direitos do Titular de Dados e Canais de Atendimento (LGPD Art. 18 e 19)

Você pode exercer seus direitos de privacidade a qualquer momento diretamente pela interface da aplicação ou por contato com o Encarregado:

1. **Confirmação e Acesso (`GET /api/v1/me` e `GET /api/v1/me/dados`):** Obtenha confirmação imediata de tratamento e a declaração detalhada de origens, finalidades e histórico de operações.
2. **Correção e Retificação (`PATCH /api/v1/me`):** Altere seu nome de exibição e e-mail cadastrado.
3. **Portabilidade de Dados (`GET /api/v1/me/portabilidade`):** Exporte todos os seus projetos, protocolos, artigos, notas e configurações em formato interoperável (JSON/CSV).
4. **Eliminação Definitiva da Conta (`DELETE /api/v1/me`):**  
   - É possível solicitar o apagamento com **prazo de arrependimento de 7 dias** (com desativação prévia) ou a **eliminação atômica e definitiva imediata**.
   - A eliminação definitiva apaga permanentemente todos os registros do banco de dados e remove fisicamente todos os arquivos de PDF associados aos seus projetos no disco do servidor.

---

## 6. Política de Cookies

O Revsist utiliza exclusivamente cookies **estritamente necessários** para autenticação e segurança da sessão HTTP (`rsac_session`), configurados com as diretivas de proteção `HttpOnly`, `SameSite=Strict` e `Secure` (em conexões HTTPS). Não utilizamos cookies de rastreamento publicitário, métricas comportamentais de terceiros ou pixels de telemetria invasiva.

---

## 7. Alterações neste Aviso de Privacidade

Este documento pode ser atualizado periodicamente para refletir melhorias no sistema ou exigências regulatórias da ANPD. Qualquer alteração relevante será notificada na interface do usuário com indicação destacada da nova versão e data de vigência.
