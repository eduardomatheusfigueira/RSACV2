# Documento 51 · Anexo de Texto e Proveniência (A1)
## Redação metodológica, cópia da landing e tabela de comprovação factual

> Este anexo define o texto exato da landing page do Revsist segundo as diretrizes de voz do documento 42 §42.4/§42.6 e as regras de posicionamento do documento 40 §40.8.1.
> Cada afirmação sobre funcionalidades e características do software é estritamente vinculada ao código-fonte ou a artefatos versionados neste repositório.

---

## 1. Conteúdo Textual da Landing Page

### Dobra 0 — Hero
- **Identificador de versão:** `BETA · Plataforma em desenvolvimento ativo`
- **Título principal (H1):** Software para conduzir revisão sistemática do protocolo à exportação.
- **Linha de assinatura:** Revisão sistemática com rastro.
- **Texto de apoio:** Desenvolvido para pós-graduação e grupos de pesquisa acadêmica. Integra bases de dados bibliográficas nacionais e internacionais, com registro auditável de cada decisão metodológica e pareceres assistidos por modelos de linguagem.
- **Ações principais (CTAs):**
  - Botão Primário: `Entrar no Revsist` (aponta para `/app`)
  - Botão Secundário: `Ver como funciona` (aponta para `#como-funciona`)
- **Indicadores de escopo:**
  - `11 diretrizes metodológicas catalogadas` (PRISMA 2020, PRISMA-ScR, JBI e correlatas)
  - `5 bases acadêmicas conectadas` (BDTD, SciELO, PubMed, Scopus, OpenAlex)
  - `Auditoria individual de decisões` (registro de autor, provedor, modelo e hash do contexto)

---

### Seção 1 — Como funciona (Fluxo em 6 etapas)
- **Título da seção:** Como funciona
- **Subtítulo:** O fluxo metodológico do protocolo à síntese final, tela por tela.

#### Bloco 1 · Protocolo de Pesquisa
- **Título:** 1. Protocolo de Pesquisa
- **Texto:** Você define o objetivo da investigação, estrutura as dimensões do PICO, cadastra critérios de inclusão e exclusão e seleciona uma das 11 diretrizes disponíveis. O protocolo permanece versionado no banco de dados e orienta as etapas seguintes do estudo.
- **Legenda da imagem:** Edição estruturada do protocolo com checklist metodológico e versionamento de alterações.

#### Bloco 2 · Coleta Bibliográfica
- **Título:** 2. Coleta Bibliográfica
- **Texto:** Você constrói a estratégia de busca booleana e dispara a consulta integrada às bases BDTD, SciELO, PubMed, Scopus e OpenAlex. O sistema recupera os registros com metadados bibliográficos completos e armazena os dados brutos da coleta.
- **Legenda da imagem:** Painel de consulta federada a bases de dados com parâmetros de busca e contagem de registros recuperados.

#### Bloco 3 · Deduplicação de Registros
- **Título:** 3. Deduplicação de Registros
- **Texto:** Registros repetidos entre diferentes fontes bibliográficas são agrupados de forma determinística por identificador digital (DOI), normalização de títulos e distância textual. Nenhum registro é removido sem log do critério de correspondência aplicado.
- **Legenda da imagem:** Agrupamento de estudos duplicados com comparação de campos e controle de resolução.

#### Bloco 4 · Triagem de Títulos e Resumos
- **Título:** 4. Triagem de Títulos e Resumos
- **Texto:** Você avalia cada estudo com base nos critérios de elegibilidade cadastrados, contando com sugestões de parecer emitidas por modelos de linguagem. A decisão final de inclusão ou exclusão cabe ao pesquisador e fica associada ao histórico do projeto.
- **Legenda da imagem:** Avaliação cega de título e resumo com critérios de elegibilidade e sugestão assistida.

#### Bloco 5 · Extração de Dados
- **Título:** 5. Extração de Dados
- **Texto:** Você configura os campos do formulário de extração conforme o desenho da sua pesquisa e registra as respostas extraídas de cada artigo selecionado. As informações preenchidas alimentam de forma estruturada a matriz de evidências da revisão.
- **Legenda da imagem:** Formulário de extração estruturada de variáveis com persistência por estudo incluído.

#### Bloco 6 · Síntese e Exportação
- **Título:** 6. Síntese e Exportação
- **Texto:** O sistema compila o fluxograma PRISMA diretamente do banco de dados, contabilizando estudos identificados, duplicatas excluídas e artigos analisados. Os dados consolidados podem ser exportados nos formatos RIS, BibTeX, CSV e XLSX.
- **Legenda da imagem:** Diagrama de fluxo das etapas de seleção e opções de exportação em múltiplos formatos.

---

### Seção 2 — O rastro de auditoria
- **Título da seção:** Rastro e Proveniência Metodológica
- **Texto:** Cada decisão registrada no sistema armazena a autoria da avaliação, o carimbo de data e hora, o parecer sugerido pela inteligência artificial, o provedor, o modelo utilizado e o hash SHA-256 do contexto submetido. A proveniência das etapas permanece transparente e verificável, permitindo auditoria técnica por comitês, bancas e pareceristas.
- **Legenda da imagem:** Registro de auditoria detalhado evidenciando metadados de proveniência, modelo de linguagem e hash criptográfico do prompt.

---

### Seção 3 — Diretrizes, bases e limites operacionais
- **Título da seção:** Diretrizes Metodológicas e Limites Operacionais
- **Diretrizes suportadas (11 guias catalogadas):**
  - PRISMA 2020 (Revisões Sistemáticas e Metanálises)
  - PRISMA-ScR 2018 (Revisões de Escopo)
  - PRISMA-P 2015 (Protocolos de Revisão)
  - JBI 2020 (Manual de Síntese de Evidências Joanna Briggs Institute)
  - Cochrane Handbook / MECIR (Padrões Metodológicos Cochrane)
  - Campbell Collaboration / MECCIR (Padrões em Ciências Sociais)
  - CEE Guidelines / ROSES (Evidências Ambientais)
  - EBSE Guidelines (Engenharia de Software Baseada em Evidências)
  - PRIOR 2022 (Revisões de Visão Geral / Overviews)
  - Methodi Ordinatio (Critérios Multicritério de Ordenação Bibliográfica)
  - Protocolo Personalizado (Campos abertos conforme desenho do projeto)
- **Fontes bibliográficas conectadas:**
  - BDTD (Biblioteca Digital Brasileira de Teses e Dissertações — motor VuFind)
  - SciELO (Scientific Electronic Library Online)
  - PubMed / MEDLINE (National Library of Medicine)
  - Scopus (Elsevier Scopus Search API)
  - OpenAlex (Catálogo bibliográfico global aberto)
- **Declaração explícita de limites (o que o Revsist não faz):**
  - Não executa cálculos de meta-análise estatística.
  - Não computa escores automatizados do sistema GRADE.
  - Não substitui o julgamento metodológico de risco de viés.
  - Não exclui estudos de forma autônoma sem validação humana.

---

### Seção 4 — Armazenamento, licença e privacidade
- **Título da seção:** Controle de Dados e Licenciamento
- **Texto:** Os registros e decisões da sua revisão são de sua propriedade exclusiva, podendo ser extraídos integralmente ou eliminados pelo usuário. A comunicação com provedores de IA ocorre mediante solicitação explícita para os itens em análise. O software é distribuído sob licença livre MIT e tem seu código aberto para escrutínio público.
- **Acessos:** Links para os [Termos de Uso](/termos), [Política de Privacidade](/privacidade) e repositório de [Código Aberto no GitHub](https://github.com/eduardomatheusfigueira/RSACV2).

---

### Rodapé
- **Navegação:** Como funciona · Diretrizes · Blog · RSS Feed · Termos · Privacidade · Código Aberto
- **Aviso institucional:** Revsist — Plataforma para condução de revisões sistemáticas de literatura acadêmica. Versão BETA. Código distribuído sob licença MIT.

---

## 2. Tabela de Proveniência Factual

| Afirmação Factual na Página | Evidência Técnica no Repositório | Arquivo e Linhas de Lastro |
|---|---|---|
| "11 diretrizes metodológicas catalogadas" | Array `GUIAS_DO_PROTOCOLO` com 11 itens definidos com código, nome, órgão e referência | `frontend/src/data/guiasDoProtocolo.ts:13-167` |
| "5 bases acadêmicas conectadas (BDTD, SciELO, PubMed, Scopus, OpenAlex)" | Harvesters implementados e registrados no serviço de coleta | `backend/app/harvesters/bdtd.py`, `backend/app/harvesters/scielo.py`, `backend/app/harvesters/pubmed.py`, `backend/app/harvesters/scopus.py`, `backend/app/harvesters/openalex.py` |
| "AuditLogModel guarda provedor, modelo e hash" | Modelo ORM de auditoria com colunas `provider`, `model`, `prompt_hash` | `backend/app/infrastructure/persistence/models.py:270-305` |
| "Protocolo versionado no banco de dados" | Tabela `ProtocolVersionModel` vinculada a `ProtocolModel` | `backend/app/infrastructure/persistence/models.py:90-130` |
| "Deduplicação determinística" | Serviço com deduplicação por DOI, título normalizado e similaridade | `backend/app/services/dedup_service.py:30-160` |
| "Parecer sugerido por modelos de linguagem" | Endpoint de triagem assistida e serviços de IA (Gemini / OpenAI compatível) | `backend/app/api/v1/screening_ai.py:20-80`, `backend/app/services/screening_service.py:100-240` |
| "Decisão final associada ao pesquisador" | Tabela `PaperModel` armazena `decision` e `AuditLogModel` registra `user_id` e ação | `backend/app/infrastructure/persistence/models.py:175-220`, `270-305` |
| "Formulário de extração de dados" | Campos `extraction_questions` no protocolo e `PaperExtractionModel` para respostas | `backend/app/infrastructure/persistence/models.py:110-125`, `230-260` |
| "Fluxograma PRISMA gerado do banco de dados" | Endpoint e serviço de agregação de contagens para diagrama de fluxo | `backend/app/services/insights_service.py:120-180` |
| "Exportação nos formatos RIS, BibTeX, CSV e XLSX" | Funções dedicadas de serialização para os 4 formatos | `backend/app/services/export_service.py:30-220` |
| "Código sob licença MIT" | Declaração de licença no manifesto de projeto | `backend/pyproject.toml:9` |
| "Limites: sem meta-análise, sem GRADE, sem risco de viés automático" | Diretrizes do documento de marca e escopo delimitado da aplicação | `planejamento/42_PLANO_DE_MARCA.md:123-128`, `planejamento/40_ESPECIFICACAO_ONLINE.md:610-615` |
