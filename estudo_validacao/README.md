# Estudo de Validação Experimental do RSACV2

> **Protocolo em Comum**: *Impactos da Segurança Pública na Operacionalização do Turismo Náutico em Fronteiras Fluviais: Protocolo de Revisão de Escopo*  
> **Referência no Sistema**: Backup JSON (`rsac-perfil-backup-2026-08-19 (1).json` — Projeto ID `7847417c-79df-4892-bdec-2257d019f65e`)  
> **Diretriz Metodológica**: PRISMA-ScR (2018) / Joanna Briggs Institute (JBI)

---

## 🎯 Pergunta Central do Estudo de Validação
> **Como se comparam a triagem de trabalhos e a extração de informações em Revisão Sistemática Assistida por Computador (RSACV2) e a feita de forma manual sem o auxílio deste sistema?**

### Questões de Pesquisa (Research Questions)
1. **RQ1 (Coleta e Busca)**: Usando o mesmo protocolo de busca, em uma mesma base, os trabalhos encontrados são os mesmos?
2. **RQ2 (Concordância na Triagem)**: Em uma mesma lista de critérios de inclusão e exclusão, as marcações serão as mesmas? E as justificativas?
3. **RQ3 (Preferência em Divergências)**: Em caso de divergências de marcações e justificativas, qual seria preferida por um trio de revisores independentes em uma análise cega?
4. **RQ4 (Discernibilidade / Teste de Turing)**: Os revisores serão capazes de diferenciar o trabalho feito de forma assistida? Sob qual justificativa?
5. **RQ5 (Qualidade na Extração)**: Como se comparam as extrações de dados nos dois métodos sob avaliação cega por um trio de revisores independentes?
6. **RQ6 (Síntese Qualitativa)**: Quais observações os revisores declarariam sobre as diferenças percebidas entre o trabalho feito com e aqueles sem assistência?

---

## 📁 Documentos Gerados

| Arquivo | Formato | Descrição |
| :--- | :---: | :--- |
| [`Artigo_Esqueleto_Validacao_RSACV2.docx`](file:///d:/Downloads/RSACV2/RSACV2/estudo_validacao/Artigo_Esqueleto_Validacao_RSACV2.docx) | Word (`.docx`) | Esqueleto completo do artigo científico formatado nas normas ABNT/APA, com fundamentação teórica, metodologia pareada cega, protocolo PRISMA-ScR de Turismo Náutico em Fronteiras Fluviais, tabelas para as 6 questões de pesquisa, referências e apêndices. |
| [`Formulario_Pesquisadores_Triagem_Extracao.xlsx`](file:///d:/Downloads/RSACV2/RSACV2/estudo_validacao/Formulario_Pesquisadores_Triagem_Extracao.xlsx) | Excel (`.xlsx`) | Planilha padronizada para os pesquisadores (Braço Manual e Braço RSACV2), contendo o protocolo de descritores em pares, critérios CI1-CI3 e CE1-CE3, registro de coleta, matriz de triagem e 5 questões de extração (QE1-QE5). |
| [`Formulario_Avaliadores_Revisao_Cega.xlsx`](file:///d:/Downloads/RSACV2/RSACV2/estudo_validacao/Formulario_Avaliadores_Revisao_Cega.xlsx) | Excel (`.xlsx`) | Planilha para o **Trio de Revisores Independentes**, com saídas anonimizadas e randomizadas (Método A vs. Método B), julgamento da coleta (Critério 1.1), preferência em divergências, escala de certeza de 1 a 5 (Teste de Turing), notas de extração e gabarito restrito da coordenação. |
| [`gerar_documentos_validacao.py`](file:///d:/Downloads/RSACV2/RSACV2/estudo_validacao/gerar_documentos_validacao.py) | Python (`.py`) | Script automatizado para regenerar e customizar os arquivos com validações de dados e estilos gráficos. |

---

## 🔍 Especificações do Protocolo em Teste

### 1. Objetivo do Protocolo
*"Quais são as problemáticas de segurança pública registradas em fronteiras fluviais e de que maneira elas impactam o desenvolvimento e a operacionalização do turismo náutico nessas regiões?"*

### 2. Estrutura PICO / PCC
* **População / Contexto**: Problemáticas de segurança pública, criminalidade transfronteiriça e atividade de turismo náutico em fronteiras fluviais.
* **Intervenção / Conceito**: Modos, formas de impacto e entraves na atratividade, infraestrutura e dinâmica operacional do turismo náutico.
* **Comparação**: Estratégias de segurança pública, governança transfronteiriça e medidas mitigatórias.
* **Desfecho (Outcome)**: Mapeamento das evidências, tipologias criminais e diretrizes de ordenamento para o turismo em fronteiras fluviais.

### 3. Descritores em Pares (Máximo 2 termos por expressão)
* **Português (5 pares)**:
  1. `"turismo náutico" AND "fronteira"`
  2. `"segurança pública" AND "fronteira fluvial"`
  3. `"turismo" AND "fronteira fluvial"`
  4. `"turismo" AND "tríplice fronteira"`
  5. `"segurança pública" AND "turismo náutico"`
* **Inglês (5 pares)**:
  1. `"nautical tourism" AND "border"`
  2. `"public security" AND "river border"`
  3. `"tourism" AND "river border"`
  4. `"tourism" AND "cross-border"`
  5. `"water tourism" AND "border"`
* **Espanhol (5 pares)**:
  1. `"turismo náutico" AND "frontera"`
  2. `"seguridad pública" AND "frontera fluvial"`
  3. `"turismo" AND "frontera fluvial"`
  4. `"turismo" AND "triple frontera"`
  5. `"turismo fluvial" AND "frontera"`

### 4. Critérios de Elegibilidade
* **Inclusão**:
  * **CI1**: Estudos que abordem a atividade turística, náutica, recreativa ou de navegação de passageiros em regiões de fronteira fluvial ou hidrovias transfronteiriças.
  * **CI2**: Pesquisas que analisem aspectos de segurança pública, criminalidade transfronteiriça, fiscalização, policiamento ou governança em bacias hidrográficas de fronteira.
  * **CI3**: Publicações científicas completas (artigos de periódicos, teses e dissertações) nos idiomas português, inglês ou espanhol.
* **Exclusão**:
  * **CE1**: Estudos com foco exclusivo em transporte marítimo oceânico ou de alto-mar sem interface fluvial ou fronteiriça.
  * **CE2**: Trabalhos sobre segurança pública puramente urbana ou rural sem qualquer conexão com hidrovias, cursos d'água de fronteira ou atividades turísticas.
  * **CE3**: Documentos editoriais, resenhas de livros, resumos expandidos de eventos ou textos sem metodologia científica definida.

### 5. Questões de Extração de Dados
* **QE1**: Qual é a localização geográfica, país e bacia hidrográfica/rio de fronteira analisado no estudo?
* **QE2**: Quais tipologias de ocorrências de segurança pública, crimes ou ilícitos transfronteiriços foram identificadas?
* **QE3**: Quais foram os impactos diretos ou indiretos na atratividade, infraestrutura e dinâmica operacional do turismo náutico?
* **QE4**: Quais estratégias de governança transfronteiriça, políticas públicas ou medidas de policiamento/mitigação foram recomendadas?
* **QE5**: Qual a metodologia de pesquisa empregada e quais fontes de dados foram utilizadas?

---

## ⚖️ Critérios de Julgamento Cego pelo Trio de Revisores

* **1.1 Coleta**:
  * `SIM`: 100% de igualdade na presença e ordem exata dos trabalhos.
  * `NÃO - POR PRESENÇA`: Presença de trabalhos distintos.
  * `NÃO - POR ORDEM`: Mesmos trabalhos, porém em ordem/ranqueamento diferente.
  * `NÃO INTEGRAL`: Divergência tanto na presença quanto na ordem.
* **2.1 & 2.2 Triagem**: Preenchimento independente das marcações e justificativas; comparação cega das justificativas.
* **3.1 Preferência em Divergências**: Nos casos divergentes, escolha fundamentada entre `Método A está correto`, `Método B está correto`, `Ambos divergem mas estão corretos` ou `Divergem mas ambos erram`, com justificativa por extenso obrigatória.
* **4.1 Teste de Percepção (Turing)**: Indicação de qual resposta parece ser a assistida pelo RSACV2, grau de certeza de 1 a 5 (`1 = Totalmente incerto / chute` até `5 = Certeza absoluta`) e justificativa obrigatória para notas 4 e 5.
* **5.1 & 5.2 Extração**: Registro de similaridades e diferenças, notas de concordância de 1 a 5 para cada método e extração preferida.
* **6.1 Síntese Global**: Parágrafos reflexivos estruturados avaliando profundidade, consistência e confiabilidade do sistema.
