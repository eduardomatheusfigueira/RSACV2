/**
 * Revsist — Gerador de Blog Estático e Feed RSS (doc 51 §51.5 A4)
 * =============================================================
 *
 * Compila arquivos Markdown em `landing/conteudo/blog/` para HTML estático em
 * `landing/blog/<slug>/index.html` e `landing/blog/index.html`, sem framework,
 * sem dependência de execução e com zero requisição a terceiros.
 *
 * Gera também `landing/public/feed.xml` (RSS 2.0) e `landing/public/sitemap.xml`.
 */

import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import MarkdownIt from 'markdown-it'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const ROOT_DIR = join(__dirname, '..')
const CONTENT_DIR = join(ROOT_DIR, 'conteudo', 'blog')
const BLOG_OUT_DIR = join(ROOT_DIR, 'blog')
const PUBLIC_DIR = join(ROOT_DIR, 'public')

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
})

function parseFrontMatter(content) {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/)
  if (!match) {
    return { data: {}, body: content }
  }

  const rawYaml = match[1]
  const body = match[2]
  const data = {}

  const lines = rawYaml.split(/\r?\n/)
  for (const line of lines) {
    const colonIdx = line.indexOf(':')
    if (colonIdx === -1) continue
    const key = line.slice(0, colonIdx).trim()
    let val = line.slice(colonIdx + 1).trim()

    if (val.startsWith('[') && val.endsWith(']')) {
      data[key] = val
        .slice(1, -1)
        .split(',')
        .map((s) => s.trim().replace(/^['"]|['"]$/g, ''))
    } else {
      data[key] = val.replace(/^['"]|['"]$/g, '')
    }
  }

  return { data, body }
}

function formatarData(isoStr) {
  if (!isoStr) return ''
  const partes = isoStr.split('-')
  if (partes.length === 3) {
    return `${partes[2]}/${partes[1]}/${partes[0]}`
  }
  return isoStr
}

function calcularTempoLeitura(texto) {
  const palavras = texto.trim().split(/\s+/).length
  const minutos = Math.max(1, Math.ceil(palavras / 200))
  return `${minutos} min de leitura`
}

function escaparXml(str) {
  return (str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function renderizarCabecalho(caminhoRaiz = '/') {
  return `
    <header class="site-header" id="topo">
      <div class="header-container">
        <a href="${caminhoRaiz}" class="brand-logo" aria-label="Revsist — Início">
          <svg class="brand-mark-svg" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" width="28" height="28">
            <rect width="32" height="32" rx="7" fill="var(--color-primary-main, #274c77)"/>
            <path d="M10 24V8h7a5 5 0 0 1 5 5c0 2.2-1.4 4-3.5 4.7L23 24h-3.8l-4-6h-2.2v6H10zm3-9h4a2 2 0 0 0 0-4h-4v4z" fill="#ffffff"/>
            <circle cx="21" cy="18" r="4.5" stroke="var(--color-primary-light, #6096ba)" stroke-width="2" fill="none"/>
            <line x1="24.5" y1="21.5" x2="28" y2="25" stroke="var(--color-primary-light, #6096ba)" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <span class="brand-name">Revsist</span>
        </a>

        <button class="nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="main-nav" aria-label="Abrir menu de navegação">
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
        </button>

        <nav class="main-nav" id="main-nav" aria-label="Navegação principal">
          <ul class="nav-list">
            <li><a href="${caminhoRaiz}#como-funciona" class="nav-link">Como funciona</a></li>
            <li><a href="${caminhoRaiz}#diretrizes" class="nav-link">Diretrizes</a></li>
            <li><a href="/blog" class="nav-link is-active">Blog</a></li>
          </ul>
          <div class="nav-actions">
            <a href="/app" class="btn btn-primary btn-sm">Entrar no Revsist</a>
          </div>
        </nav>
      </div>
    </header>
  `
}

function renderizarRodape(caminhoRaiz = '/') {
  return `
    <footer class="site-footer">
      <div class="footer-container">
        <div class="footer-top">
          <div class="footer-brand">
            <div class="footer-brand-header">
              <svg class="brand-mark-svg" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" width="24" height="24">
                <rect width="32" height="32" rx="7" fill="var(--color-primary-main, #274c77)"/>
                <path d="M10 24V8h7a5 5 0 0 1 5 5c0 2.2-1.4 4-3.5 4.7L23 24h-3.8l-4-6h-2.2v6H10zm3-9h4a2 2 0 0 0 0-4h-4v4z" fill="#ffffff"/>
                <circle cx="21" cy="18" r="4.5" stroke="var(--color-primary-light, #6096ba)" stroke-width="2" fill="none"/>
                <line x1="24.5" y1="21.5" x2="28" y2="25" stroke="var(--color-primary-light, #6096ba)" stroke-width="2" stroke-linecap="round"/>
              </svg>
              <span class="brand-name">Revsist</span>
              <span class="badge badge-sm badge-beta">BETA</span>
            </div>
            <p class="footer-tagline">
              Software para conduzir revisão sistemática do protocolo à exportação, com proveniência e rastro auditável.
            </p>
          </div>

          <div class="footer-nav">
            <div class="footer-nav-col">
              <h3 class="footer-heading">Navegação</h3>
              <ul class="footer-links">
                <li><a href="${caminhoRaiz}#como-funciona">Como funciona</a></li>
                <li><a href="${caminhoRaiz}#rastro">O rastro</a></li>
                <li><a href="${caminhoRaiz}#diretrizes">Diretrizes</a></li>
                <li><a href="/blog">Blog</a></li>
                <li><a href="/feed.xml">RSS Feed</a></li>
              </ul>
            </div>
            <div class="footer-nav-col">
              <h3 class="footer-heading">Governança</h3>
              <ul class="footer-links">
                <li><a href="/termos">Termos de uso</a></li>
                <li><a href="/privacidade">Privacidade (LGPD)</a></li>
                <li><a href="https://github.com/eduardomatheusfigueira/RSACV2" target="_blank" rel="noopener noreferrer">Código aberto (MIT)</a></li>
              </ul>
            </div>
          </div>
        </div>

        <div class="footer-bottom">
          <p class="footer-copy">
            &copy; 2026 Revsist. Distribuído sob licença livre MIT.
          </p>
        </div>
      </div>
    </footer>
  `
}

export function gerarBlog() {
  console.log('=== Compilando Blog e Feed RSS (A4) ===')
  if (!existsSync(CONTENT_DIR)) {
    mkdirSync(CONTENT_DIR, { recursive: true })
  }
  if (!existsSync(BLOG_OUT_DIR)) {
    mkdirSync(BLOG_OUT_DIR, { recursive: true })
  }
  if (!existsSync(PUBLIC_DIR)) {
    mkdirSync(PUBLIC_DIR, { recursive: true })
  }

  const arquivos = readdirSync(CONTENT_DIR).filter((f) => f.endsWith('.md'))
  const posts = []

  for (const arquivo of arquivos) {
    const rawContent = readFileSync(join(CONTENT_DIR, arquivo), 'utf8')
    const { data, body } = parseFrontMatter(rawContent)

    if (!data.slug || !data.titulo) {
      console.warn(`Post ignorado por falta de slug/titulo: ${arquivo}`)
      continue
    }

    const htmlBody = md.render(body)
    const tempoLeitura = calcularTempoLeitura(body)

    posts.push({
      ...data,
      htmlBody,
      tempoLeitura,
      tags: Array.isArray(data.tags) ? data.tags : [],
    })
  }

  // Ordenar posts do mais recente para o mais antigo
  posts.sort((a, b) => new Date(b.data).getTime() - new Date(a.data).getTime())

  // 1. Gerar páginas individuais dos posts: `landing/blog/<slug>/index.html`
  for (const post of posts) {
    const postDir = join(BLOG_OUT_DIR, post.slug)
    if (!existsSync(postDir)) {
      mkdirSync(postDir, { recursive: true })
    }

    const outrosPosts = posts.filter((p) => p.slug !== post.slug)
    const linksRelacionadosHtml = outrosPosts.length
      ? `
        <div class="post-related">
          <h3>Leituras recomendadas</h3>
          <ul>
            ${outrosPosts
              .map(
                (p) => `
              <li>
                <a href="/blog/${p.slug}/">${escaparXml(p.titulo)}</a>
                <span class="related-date">${formatarData(p.data)}</span>
              </li>
            `
              )
              .join('')}
          </ul>
        </div>
      `
      : ''

    const jsonLd = {
      '@context': 'https://schema.org',
      '@type': 'BlogPosting',
      headline: post.titulo,
      description: post.descricao || post.resumo,
      datePublished: post.data,
      dateModified: post.atualizado || post.data,
      author: {
        '@type': 'Person',
        name: post.autor || 'Eduardo Matheus Figueira',
      },
      inLanguage: 'pt-BR',
      mainEntityOfPage: `https://revsist.com/blog/${post.slug}/`,
    }

    const breadcrumbsLd = {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        {
          '@type': 'ListItem',
          position: 1,
          name: 'Início',
          item: 'https://revsist.com/',
        },
        {
          '@type': 'ListItem',
          position: 2,
          name: 'Blog',
          item: 'https://revsist.com/blog',
        },
        {
          '@type': 'ListItem',
          position: 3,
          name: post.titulo,
          item: `https://revsist.com/blog/${post.slug}/`,
        },
      ],
    }

    const htmlPost = `<!DOCTYPE html>
<html lang="pt-BR" data-theme="platinum-dusk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escaparXml(post.titulo)} · Blog Revsist</title>
  <meta name="description" content="${escaparXml(post.descricao || post.resumo)}">
  <link rel="canonical" href="https://revsist.com/blog/${post.slug}/">
  <meta property="og:type" content="article">
  <meta property="og:title" content="${escaparXml(post.titulo)} · Blog Revsist">
  <meta property="og:description" content="${escaparXml(post.descricao || post.resumo)}">
  <meta property="og:url" content="https://revsist.com/blog/${post.slug}/">
  <meta property="og:site_name" content="Revsist">
  <meta property="og:image" content="https://revsist.com/og-image.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${escaparXml(post.titulo)} · Blog Revsist">
  <meta name="twitter:description" content="${escaparXml(post.descricao || post.resumo)}">
  <meta name="twitter:image" content="https://revsist.com/og-image.png">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="alternate" type="application/rss+xml" title="Feed RSS do Blog Revsist" href="/feed.xml">
  <link rel="stylesheet" href="/src/styles/landing.css">
  <script type="application/ld+json">
    ${JSON.stringify(jsonLd)}
  </script>
  <script type="application/ld+json">
    ${JSON.stringify(breadcrumbsLd)}
  </script>
</head>
<body class="blog-body">
  <a href="#conteudo-artigo" class="skip-link">Pular para o conteúdo</a>
  ${renderizarCabecalho('/')}

  <main class="blog-article-layout" id="conteudo-artigo">
    <div class="container article-container">
      <nav class="breadcrumb-nav" aria-label="Caminho de navegação">
        <ol class="breadcrumb-list">
          <li><a href="/">Início</a></li>
          <li><span class="sep" aria-hidden="true">/</span></li>
          <li><a href="/blog">Blog</a></li>
          <li><span class="sep" aria-hidden="true">/</span></li>
          <li aria-current="page">${escaparXml(post.titulo)}</li>
        </ol>
      </nav>

      <article class="article-content">
        <header class="article-header">
          <div class="article-meta-top">
            <time datetime="${post.data}">${formatarData(post.data)}</time>
            <span class="meta-dot">·</span>
            <span>${post.tempoLeitura}</span>
            ${
              post.atualizado && post.atualizado !== post.data
                ? `<span class="meta-dot">·</span><span>Atualizado em ${formatarData(post.atualizado)}</span>`
                : ''
            }
          </div>
          <h1 class="article-title">${escaparXml(post.titulo)}</h1>
          <p class="article-lead">${escaparXml(post.resumo || post.descricao)}</p>
          <div class="article-tags">
            ${post.tags.map((t) => `<span class="article-tag">#${escaparXml(t)}</span>`).join(' ')}
          </div>
        </header>

        <div class="article-body prose">
          ${post.htmlBody}
        </div>

        <div class="article-cta-box">
          <h3>Conduza sua revisão com rigor metodológico</h3>
          <p>
            O Revsist automatiza a busca em bases brasileiras e internacionais, registra o rastro de cada decisão e gera o fluxograma PRISMA oficial diretamente do banco de dados.
          </p>
          <div class="article-cta-actions">
            <a href="/app" class="btn btn-primary">Entrar no Revsist</a>
            <a href="/#como-funciona" class="btn btn-outline">Ver demonstração</a>
          </div>
        </div>

        ${linksRelacionadosHtml}
      </article>
    </div>
  </main>

  ${renderizarRodape('/')}
  <script type="module" src="/src/scripts/landing.js"></script>
</body>
</html>`

    writeFileSync(join(postDir, 'index.html'), htmlPost, 'utf8')
    console.log(`  ✓ Post compilado: blog/${post.slug}/index.html`)
  }

  // 2. Gerar índice do blog: `landing/blog/index.html`
  const jsonLdBlog = {
    '@context': 'https://schema.org',
    '@type': 'Blog',
    name: 'Blog do Revsist',
    description: 'Artigos técnicos, guias metodológicos e análises sobre revisão sistemática de literatura acadêmica.',
    url: 'https://revsist.com/blog',
    inLanguage: 'pt-BR',
    publisher: {
      '@type': 'Organization',
      name: 'Revsist',
      url: 'https://revsist.com',
    },
  }

  const postsListHtml = posts
    .map(
      (post) => `
    <article class="blog-card reveal-on-scroll">
      <div class="blog-card-meta">
        <time datetime="${post.data}">${formatarData(post.data)}</time>
        <span class="meta-dot">·</span>
        <span>${post.tempoLeitura}</span>
      </div>
      <h2 class="blog-card-title">
        <a href="/blog/${post.slug}/">${escaparXml(post.titulo)}</a>
      </h2>
      <p class="blog-card-summary">
        ${escaparXml(post.resumo || post.descricao)}
      </p>
      <div class="blog-card-footer">
        <div class="blog-card-tags">
          ${post.tags.map((t) => `<span class="article-tag">#${escaparXml(t)}</span>`).join(' ')}
        </div>
        <a href="/blog/${post.slug}/" class="read-more-link" aria-label="Ler artigo: ${escaparXml(post.titulo)}">
          Ler artigo <span aria-hidden="true">&rarr;</span>
        </a>
      </div>
    </article>
  `
    )
    .join('\n')

  const htmlBlogIndex = `<!DOCTYPE html>
<html lang="pt-BR" data-theme="platinum-dusk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog · Revsist — Revisão Sistemática com Rastro</title>
  <meta name="description" content="Artigos, guias metodológicos e análises fundamentadas sobre condução rigorosa de revisões sistemáticas e de escopo.">
  <link rel="canonical" href="https://revsist.com/blog">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Blog · Revsist — Revisão Sistemática com Rastro">
  <meta property="og:description" content="Artigos, guias metodológicos e análises fundamentadas sobre condução rigorosa de revisões sistemáticas e de escopo.">
  <meta property="og:url" content="https://revsist.com/blog">
  <meta property="og:site_name" content="Revsist">
  <meta property="og:image" content="https://revsist.com/og-image.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Blog · Revsist">
  <meta name="twitter:description" content="Artigos, guias metodológicos e análises fundamentadas sobre condução rigorosa de revisões sistemáticas.">
  <meta name="twitter:image" content="https://revsist.com/og-image.png">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="alternate" type="application/rss+xml" title="Feed RSS do Blog Revsist" href="/feed.xml">
  <link rel="stylesheet" href="/src/styles/landing.css">
  <script type="application/ld+json">
    ${JSON.stringify(jsonLdBlog)}
  </script>
</head>
<body class="blog-index-body">
  <a href="#conteudo-blog" class="skip-link">Pular para os artigos</a>
  ${renderizarCabecalho('/')}

  <main class="blog-index-layout" id="conteudo-blog">
    <div class="container blog-container">
      <header class="blog-index-header">
        <p class="section-tag">Publicações & Metodologia</p>
        <h1 class="blog-index-title">Blog do Revsist</h1>
        <p class="blog-index-subtitle">
          Textos com base na literatura científica sobre condução, triagem, diretrizes e integridade em revisões sistemáticas.
        </p>
      </header>

      <section class="blog-grid" aria-label="Lista de artigos publicados">
        ${postsListHtml}
      </section>
    </div>
  </main>

  ${renderizarRodape('/')}
  <script type="module" src="/src/scripts/landing.js"></script>
</body>
</html>`

  writeFileSync(join(BLOG_OUT_DIR, 'index.html'), htmlBlogIndex, 'utf8')
  console.log(`  ✓ Índice gerado: blog/index.html (${posts.length} posts)`)

  // 3. Gerar feed RSS 2.0: `landing/public/feed.xml`
  const nowRfc822 = new Date().toUTCString()
  const rssItems = posts
    .map((p) => {
      const pubDate = new Date(p.data).toUTCString()
      return `    <item>
      <title>${escaparXml(p.titulo)}</title>
      <link>https://revsist.com/blog/${p.slug}/</link>
      <guid isPermaLink="true">https://revsist.com/blog/${p.slug}/</guid>
      <description>${escaparXml(p.resumo || p.descricao)}</description>
      <pubDate>${pubDate}</pubDate>
      <author>contato@revsist.org (${escaparXml(p.autor || 'Eduardo Matheus Figueira')})</author>
    </item>`
    })
    .join('\n')

  const rssFeed = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Blog Revsist · Revisão Sistemática com Rastro</title>
    <link>https://revsist.com/blog</link>
    <description>Artigos metodológicos e orientações técnicas sobre condução de revisões sistemáticas e de escopo.</description>
    <language>pt-BR</language>
    <lastBuildDate>${nowRfc822}</lastBuildDate>
    <atom:link href="https://revsist.com/feed.xml" rel="self" type="application/rss+xml" />
${rssItems}
  </channel>
</rss>`

  writeFileSync(join(PUBLIC_DIR, 'feed.xml'), rssFeed, 'utf8')
  console.log(`  ✓ Feed RSS gerado: public/feed.xml`)

  // 4. Gerar Sitemap XML: `landing/public/sitemap.xml`
  const rotasEstaticas = [
    { loc: 'https://revsist.com/', lastmod: '2026-09-02', priority: '1.0', changefreq: 'weekly' },
    { loc: 'https://revsist.com/blog', lastmod: '2026-09-02', priority: '0.9', changefreq: 'daily' },
    { loc: 'https://revsist.com/termos', lastmod: '2026-09-02', priority: '0.5', changefreq: 'monthly' },
    { loc: 'https://revsist.com/privacidade', lastmod: '2026-09-02', priority: '0.5', changefreq: 'monthly' },
  ]

  const rotasPosts = posts.map((p) => ({
    loc: `https://revsist.com/blog/${p.slug}/`,
    lastmod: p.atualizado || p.data,
    priority: '0.8',
    changefreq: 'monthly',
  }))

  const todasRotas = [...rotasEstaticas, ...rotasPosts]
  const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${todasRotas
  .map(
    (r) => `  <url>
    <loc>${r.loc}</loc>
    <lastmod>${r.lastmod}</lastmod>
    <changefreq>${r.changefreq}</changefreq>
    <priority>${r.priority}</priority>
  </url>`
  )
  .join('\n')}
</urlset>`

  writeFileSync(join(PUBLIC_DIR, 'sitemap.xml'), sitemapXml, 'utf8')
  console.log(`  ✓ Sitemap gerado: public/sitemap.xml (${todasRotas.length} URLs)`)

  // 5. Atualizar robots.txt garantindo liberação explícita de /blog e sitemap
  const robotsTxt = `# Revsist — Política de Rastreamento
User-agent: *
Allow: /
Allow: /blog
Allow: /blog/*
Allow: /termos
Allow: /privacidade
Allow: /feed.xml

# Áreas protegidas e rotas dinâmicas da aplicação SPA e API
Disallow: /app/
Disallow: /api/

Sitemap: https://revsist.com/sitemap.xml
`
  writeFileSync(join(PUBLIC_DIR, 'robots.txt'), robotsTxt, 'utf8')
  console.log(`  ✓ robots.txt atualizado: public/robots.txt`)

  console.log('=== Blog compilado com sucesso! ===\n')
  return { posts, todasRotas }
}

// Executar se chamado diretamente da linha de comando
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  gerarBlog()
}
