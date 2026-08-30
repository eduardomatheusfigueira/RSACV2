# Termos de Uso da Plataforma Revsist

**Versão:** 1.0  
**Data de Vigência:** 29 de agosto de 2026  
**Última Atualização:** 29 de agosto de 2026  

Bem-vindo ao **Revsist** ("Revsist", "Plataforma" ou "Serviço"), software especializado para planejamento, coleta, triagem metodológica, extração e síntese de evidências em revisões sistemáticas de literatura científica.

Ao criar uma conta ou utilizar a Plataforma, você declara ter lido, compreendido e concordado integralmente com estes Termos de Uso e com o nosso [Aviso de Privacidade](./PRIVACIDADE.md).

---

## 1. Objeto e Funcionalidades

O Revsist disponibiliza aos pesquisadores um ecossistema integrado para:
1. Elaboração de protocolos científicos (pergunta de pesquisa, critérios de inclusão/exclusão, descritores de busca e estratégia PICO).
2. Conexão automatizada com repositórios e bases bibliográficas (ex: BDTD, SciELO, Scopus, PubMed, OpenAlex).
3. Deduplicação e gerenciamento de acervos bibliográficos.
4. Triagem de títulos e resumos, com parecer sugerido opcional por modelos de linguagem (IA) e conferência humana obrigatória.
5. Aquisição, leitura e extração de dados de textos integrais (PDFs).
6. Exportação da síntese em planilha `.xlsx`, referências em `.bib` e pacote de portabilidade em JSON.

> **Nota de escopo (30/08/2026).** Triagem em equipe com dupla avaliação cega e
> importação de arquivos `.ris`/`.bib` estão especificados nos docs 43 e 44, mas
> **não** implementados. Enquanto não estiverem, não integram o objeto destes
> termos. A versão publicada em `/termos` já reflete isso.

---

## 2. Cadastro, Acesso e Segurança da Conta

1. **Elegibilidade:** O acesso é destinado a pesquisadores, docentes, estudantes de graduação e pós-graduação e profissionais dedicados à produção acadêmica e científica.
2. **Modalidades de Autenticação:**
   - **Login Institucional via Google OAuth:** Requer endereço de e-mail verificado.
   - **Login por Senha Local:** Sujeito a políticas rígidas de complexidade (mínimo de 12 caracteres, derivação por Argon2id).
3. **Responsabilidade do Usuário:** O titular da conta é o único responsável pela confidencialidade de suas credenciais de acesso e pela veracidade das informações cadastradas.
4. **Encerramento e Exclusão:** O usuário pode requerer a exclusão voluntária de sua conta a qualquer momento na seção `/me`, com a opção de prazo de carência de 7 dias ou eliminação definitiva e imediata de dados e arquivos.

---

## 3. Modelo BYOK (Bring Your Own Key) e Uso de Inteligência Artificial

1. **Chaves Próprias de API:** Para uso de modelos proprietários de IA (Google Gemini, Alibaba Qwen), o pesquisador fornece suas próprias chaves de API obtidas junto aos respectivos provedores.
2. **Criptografia em Repouso:** Todas as chaves de API e credenciais de bases científicas são cifradas no banco de dados do Revsist com cifra autenticada AES-256-GCM / ChaCha20-Poly1305 e nunca são exibidas em texto claro ou compartilhadas com terceiros.
3. **Autonomia Metodológica:** O Revsist atua como ferramenta de assistência metodológica. As decisões finais de inclusão, exclusão e síntese científica cabem exclusivamente ao pesquisador responsável.

---

## 4. Direitos Autorais e Propriedade Intelectual

1. **Titularidade do Conteúdo:** Todo o acervo de pesquisa, protocolos, anotações e sínteses geradas pertencem integralmente aos seus respectivos autores e pesquisadores.
2. **Respeito aos Direitos Autorais dos Artigos:** O download e a guarda de arquivos PDF de artigos científicos devem respeitar as licenças de acesso aberto (Open Access) e os contratos de assinatura institucional do pesquisador com as editoras científicas.

---

## 5. Limitações de Responsabilidade e Disponibilidade

1. **Disponibilidade do Serviço:** Empregamos esforços técnicos contínuos para manter a estabilidade, segurança e disponibilidade da plataforma. No entanto, não garantimos funcionamento ininterrupto em face de quedas de serviços de terceiros, falhas de conectividade ou indisponibilidade de APIs externas (ex: Google, SciELO, BDTD).
2. **Backup e Exportação:** Recomendamos que os pesquisadores realizem exportações periódicas de seus projetos na ferramenta de portabilidade `/me/portabilidade` como medida de boa prática metodológica.

---

## 6. Alterações nos Termos de Uso

Estes Termos podem ser revisados periodicamente. Notificaremos os usuários cadastrados sobre alterações substanciais por meio de comunicados no sistema.

---

## 7. Foro e Legislação Aplicável

Estes Termos são regidos pela legislação brasileira, em especial o Marco Civil da Internet (Lei nº 12.965/2014) e a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018).
