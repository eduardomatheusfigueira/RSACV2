# Documento 51 · Anexo de Estratégia de SEO e Metadados (A5)
## Mapeamento de Palavras-Chave, Intenção de Busca e Estrutura Semântica

> Este anexo documenta a arquitetura de indexação orgânica, vocabulário acadêmico, intenções de busca e metadados estruturados implementados na Landing Page e no Blog do Revsist (doc 51 §51.5 e §51.10).

---

## 1. Mapeamento de Palavras-Chave por URL

| URL | Palavra-Chave Alvo Principal | Palavras-Chave Secundárias | Intenção de Busca | Volume Estimado / Concorrência | Meta Description (140–160 caracteres) |
|---|---|---|---|---|---|
| `https://revsist.com/` | `software revisão sistemática` | `revisão sistemática com rastro`, `ferramenta PRISMA 2020`, `triagem de artigos acadêmicos` | Transacional / Ferramental (pesquisadores, pós-graduandos e docentes buscando software gratuito e rigoroso) | Alta relevância acadêmica / Baixa concorrência direta em PT-BR | Software acadêmico para conduzir revisão sistemática do protocolo à exportação com rastro auditável de decisões, 11 diretrizes e bases integradas. (149 car.) |
| `https://revsist.com/blog` | `blog revisão sistemática` | `metodologia revisão de escopo`, `guias síntese de evidências`, `diretrizes PRISMA` | Informacional / Navegacional (exploração de boas práticas e metodologias) | Média relevância / Média concorrência | Artigos, guias metodológicos e análises fundamentadas sobre condução rigorosa de revisões sistemáticas e de escopo. (110 car.) |
| `https://revsist.com/blog/quanto-tempo-leva-uma-revisao-sistematica/` | `quanto tempo leva revisão sistemática` | `horas trabalho revisão sistemática`, `cronograma revisão sistemática`, `desatualização revisão sistemática` | Informacional / Investigativa (planejamento de prazos em dissertações/teses) | Alto interesse de pós-graduação / Zero saturação em PT-BR com fontes | Dados medidos em estudos revisados por pares sobre o tempo real, horas de trabalho e desatualização de revisões sistemáticas da literatura acadêmica. (149 car.) |
| `https://revsist.com/blog/como-escrever-um-protocolo-de-revisao-sistematica/` | `protocolo de revisão sistemática exemplo` | `como fazer protocolo revisão sistemática`, `modelo protocolo PRISMA-P`, `PICO desenvolvimento regional` | Educacional / Prática (redação de projeto de pesquisa e registro prévio) | Alto interesse / Poucos exemplos estruturados fora da área médica | Guia prático e estruturado para elaborar um protocolo de revisão sistemática ou de escopo em conformidade com PRISMA-P e PRISMA-ScR. (132 car.) |
| `https://revsist.com/termos` | `termos de uso revsist` | `licença MIT revsist`, `condições de uso software acadêmico` | Institucional / Legal | Baixa / Específica | Termos de uso da plataforma acadêmica Revsist. Direitos, responsabilidades e licença de código aberto MIT. (107 car.) |
| `https://revsist.com/privacidade` | `privacidade dados revsist` | `LGPD pesquisa acadêmica`, `segurança dados revisão sistemática` | Confiança / Conformidade regulatória | Média em instituições públicas / LGPD | Política de privacidade e conformidade com a LGPD da plataforma Revsist. Saiba como seus projetos e dados são protegidos. (118 car.) |

---

## 2. Esquema de Dados Estruturados (JSON-LD)

Todas as páginas incluem dados semânticos em formato JSON-LD, em conformidade com os padrões da `Schema.org`:

### 2.1. Home (`/`)
- `@type`: `SoftwareApplication`
- `applicationCategory`: `EducationalApplication`
- `applicationSubCategory`: `Síntese de evidências e revisão sistemática de literatura`
- `operatingSystem`: `Web, Windows, Linux, macOS`
- `offers`: `price: 0, priceCurrency: BRL`
- `license`: `https://opensource.org/licenses/MIT`
- `isAccessibleForFree`: `true`

### 2.2. Índice do Blog (`/blog`)
- `@type`: `Blog`
- `name`: `Blog do Revsist`
- `publisher`: `Organization (Revsist)`
- `inLanguage`: `pt-BR`

### 2.3. Artigos do Blog (`/blog/<slug>/`)
- `@type`: `BlogPosting`
- `headline`: Título do artigo
- `datePublished`: Data ISO (AAAA-MM-DD)
- `dateModified`: Data de atualização ISO
- `author`: `Person (Eduardo Matheus Figueira)`
- `mainEntityOfPage`: URL canônica do artigo
- Encadeamento semântico com `@type: BreadcrumbList`:
  - Posição 1: Início (`https://revsist.com/`)
  - Posição 2: Blog (`https://revsist.com/blog`)
  - Posição 3: Artigo (`https://revsist.com/blog/<slug>/`)

---

## 3. Políticas de Rastreamento e Sitemaps

1. **`public/robots.txt`**:
   - `User-agent: *`
   - Libera indexação de `/`, `/blog`, `/blog/*`, `/termos`, `/privacidade`, `/feed.xml`
   - Bloqueia `/app/` e `/api/` (rotas autenticadas da aplicação e endpoints REST internos)
   - Aponta explicitamente `Sitemap: https://revsist.com/sitemap.xml`

2. **`public/sitemap.xml`**:
   - Dinamicamente atualizado pelo build a cada compilação de novo post
   - Contém `loc`, `lastmod`, `changefreq` e `priority`

3. **`public/feed.xml`**:
   - Feed RSS 2.0 padrão internacional com `atom:link`
   - Permite sindicação e leitura via agregadores RSS/Atom sem depender de redes sociais ou rastreamento invasivo.
