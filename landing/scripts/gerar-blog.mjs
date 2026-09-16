/**
 * Revsist — Gerador de Blog Estático e Feed RSS (doc 51 §51.5 A4)
 * =============================================================
 *
 * Compila arquivos Markdown em `landing/conteudo/blog/` para HTML estático em
 * `landing/blog/<slug>/index.html` e `landing/blog/index.html`, sem framework,
 * sem dependência de execução e com zero requisição a terceiros.
 *
 * Gera também `landing/public/feed.xml` (RSS 2.0) e `landing/public/sitemap.xml`.
 * Alinhado esteticamente e arquiteturalmente à landing page v2.0 com vídeos Remotion.
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

/**
 * Mapeamento dos laços de vídeo em Remotion para cada artigo do blog.
 * Cada composição foi renderizada no Remotion em alta resolução com poster JPEG.
 */
const REMOTION_VIDEOS = {
  'checklist-prisma-2020-explicado': {
    src: '/videos/revsist-diagrama.mp4',
    poster: '/videos/revsist-diagrama-poster.jpg',
    largura: 1920,
    altura: 1080,
    label: 'Demonstração do fluxograma PRISMA 2020 montado a partir dos dados do banco no Revsist',
    legenda: 'Fluxograma PRISMA 2020 compilado automaticamente pelo Revsist com base no rastro de inclusão e exclusão salvo no banco.',
  },
  'como-escrever-um-protocolo-de-revisao-sistematica': {
    src: '/videos/revsist-busca.mp4',
    poster: '/videos/revsist-busca-poster.jpg',
    largura: 1600,
    altura: 900,
    label: 'Demonstração da busca federada em cinco bases acadêmicas simultâneas no Revsist',
    legenda: 'Execução automatizada da busca booleana simultânea em BDTD, SciELO, Scopus, OpenAlex e PubMed com contagem por base.',
  },
  'quanto-tempo-leva-uma-revisao-sistematica': {
    src: '/videos/revsist-hero.mp4',
    poster: '/videos/revsist-hero-poster.jpg',
    largura: 1920,
    altura: 1080,
    label: 'Demonstração do ciclo completo de uma revisão sistemática no Revsist',
    legenda: 'Visão panorâmica do fluxo metodológico: protocolo, busca federada, triagem com rastro auditável e síntese.',
  },
  'scoping-review-vs-revisao-sistematica': {
    src: '/videos/revsist-registro.mp4',
    poster: '/videos/revsist-registro-poster.jpg',
    largura: 1600,
    altura: 1000,
    label: 'Demonstração do registro de decisões e selo de integridade no Revsist',
    legenda: 'Registro estruturado de decisão com critérios atendidos, autoria e selo de integridade que comprova a imutabilidade.',
  },
}

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

function slugificar(texto) {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
}

function processarHtmlDoPost(body) {
  // Remove eventual h1 redundante no início do markdown para garantir h1 único (G9 / SEO)
  const bodyLimpo = body.trimStart().replace(/^#\s+[^\r\n]+(?:\r?\n)+/, '')
  let html = md.render(bodyLimpo)
  const secoes = []

  html = html.replace(/<h2>(.*?)<\/h2>/g, (match, inner) => {
    const textoLimpo = inner.replace(/<[^>]+>/g, '').trim()
    const id = slugificar(textoLimpo)
    secoes.push({ titulo: textoLimpo, id })
    return `<h2 id="${id}">${inner}</h2>`
  })

  let tocHtml = ''
  if (secoes.length >= 3) {
    tocHtml = `
      <nav class="article-toc" aria-label="Sumário do artigo">
        <p class="toc-title"><svg class="icone icone--p" aria-hidden="true" focusable="false"><use href="#i-lista" /></svg> Neste artigo</p>
        <ol class="toc-list">
          ${secoes.map((s) => `<li><a href="#${s.id}">${escaparXml(s.titulo)}</a></li>`).join('\n')}
        </ol>
      </nav>
    `
    // Inserir sumário antes do primeiro <h2>
    const primeiroH2Idx = html.indexOf('<h2 ')
    if (primeiroH2Idx !== -1) {
      html = html.slice(0, primeiroH2Idx) + tocHtml + html.slice(primeiroH2Idx)
    }
  }

  return { htmlBody: html, secoes }
}

function renderizarSvgSprite() {
  return `
  <!-- Biblioteca central de ícones SVG compartilhada com a landing page -->
  <svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
    <defs>
      <symbol id="i-marca" viewBox="0 0 80 100">
        <g fill="none" stroke="currentColor" stroke-width="14" stroke-linecap="round" stroke-linejoin="round">
          <path d="M 7 7 V 93" />
          <circle cx="32" cy="32" r="25" />
          <path d="M 45.946 52.749 L 73 93" stroke="var(--marca-cabo, currentColor)" />
        </g>
      </symbol>
      <symbol id="i-check" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" /></symbol>
      <symbol id="i-x" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" /></symbol>
      <symbol id="i-escudo" viewBox="0 0 24 24"><path d="M12 3 4 6v6c0 5 3.4 8.3 8 9 4.6-.7 8-4 8-9V6l-8-3Z" /><path d="m9 12 2 2 4-4" /></symbol>
      <symbol id="i-lista" viewBox="0 0 24 24"><path d="M9 6h11M9 12h11M9 18h11" /><path d="m3 6 1.2 1.2L6.5 5M3 12l1.2 1.2L6.5 11M3 18l1.2 1.2L6.5 16" /></symbol>
      <symbol id="i-globo" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9S14.5 18.3 12 21c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3Z" /></symbol>
      <symbol id="i-base" viewBox="0 0 24 24"><ellipse cx="12" cy="6" rx="8" ry="3" /><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6" /><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></symbol>
      <symbol id="i-camadas" viewBox="0 0 24 24"><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" /></symbol>
      <symbol id="i-documento" viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" /><path d="M14 3v5h5M9 13h6M9 17h4" /></symbol>
      <symbol id="i-grafico" viewBox="0 0 24 24"><path d="M4 20V4M4 20h16" /><path d="M8 20v-6M13 20V8M18 20v-9" /></symbol>
      <symbol id="i-pessoas" viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.2" /><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5" /><path d="M16 5.5a3.2 3.2 0 0 1 0 6M18 14.8c2 .8 3.4 2.6 3.4 5.2" /></symbol>
      <symbol id="i-mais" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></symbol>
      <symbol id="i-seta" viewBox="0 0 24 24"><path d="M4 12h15M13 6l6 6-6 6" /></symbol>
      <symbol id="i-codigo" viewBox="0 0 24 24"><path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16" /></symbol>
      <symbol id="i-imagem" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="8.5" cy="9.5" r="1.6" /><path d="m4 17 5-4.5 4 3.2 3-2.4 4 3.4" /></symbol>
      <symbol id="i-pausa" viewBox="0 0 24 24"><path d="M9 5v14M15 5v14" /></symbol>
      <symbol id="i-play" viewBox="0 0 24 24"><path d="M7 4.5v15l13-7.5-13-7.5Z" /></symbol>
    </defs>
  </svg>
  `
}

function renderizarCabecalho(caminhoRaiz = '/') {
  return `
    <header class="site-header" id="topo">
      <div class="header-container">
        <a href="${caminhoRaiz}" class="brand-logo" aria-label="Revsist — página inicial">
          <svg class="brand-mark-svg" viewBox="0 0 80 100" aria-hidden="true" focusable="false"><use href="#i-marca" /></svg>
          <span class="brand-name">Revsist</span>
          <span class="badge badge-beta">v2.0 beta</span>
        </a>

        <button class="nav-toggle" id="nav-toggle" type="button" aria-expanded="false" aria-controls="main-nav" aria-label="Abrir menu de navegação">
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
        </button>

        <nav class="main-nav" id="main-nav" aria-label="Navegação principal">
          <ul class="nav-list">
            <li><a href="${caminhoRaiz}#como-funciona" class="nav-link">Como funciona</a></li>
            <li><a href="${caminhoRaiz}#registro" class="nav-link">O que fica guardado</a></li>
            <li><a href="${caminhoRaiz}#diretrizes" class="nav-link">Roteiros</a></li>
            <li><a href="${caminhoRaiz}#perguntas" class="nav-link">Dúvidas</a></li>
            <li><a href="/blog" class="nav-link is-active">Blog</a></li>
          </ul>
          <div class="nav-actions">
            <a href="/app" class="btn btn-chrome btn-sm">Entrar no Revsist</a>
          </div>
        </nav>
      </div>
    </header>
  `
}

function renderizarRodape(caminhoRaiz = '/') {
  return `
    <footer class="site-footer" role="contentinfo">
      <div class="footer-container">
        <div class="footer-top">
          <div>
            <div class="footer-brand-header">
              <svg class="brand-mark-svg" viewBox="0 0 80 100" aria-hidden="true" focusable="false"><use href="#i-marca" /></svg>
              <span class="brand-name">Revsist</span>
              <span class="badge badge-beta">v2.0 beta</span>
            </div>
            <p class="footer-tagline">
              Programa gratuito e de código aberto para fazer revisão sistemática e revisão de escopo,
              pensado para quem pesquisa no Brasil.
            </p>
          </div>

          <div>
            <p class="footer-heading">O programa</p>
            <ul class="footer-links">
              <li><a href="${caminhoRaiz}#como-funciona">Como funciona</a></li>
              <li><a href="${caminhoRaiz}#registro">O que fica guardado</a></li>
              <li><a href="${caminhoRaiz}#diagrama">O diagrama final</a></li>
              <li><a href="${caminhoRaiz}#diretrizes">Roteiros disponíveis</a></li>
              <li><a href="${caminhoRaiz}#limites">O que ele não faz</a></li>
            </ul>
          </div>

          <div>
            <p class="footer-heading">Aprender</p>
            <ul class="footer-links">
              <li><a href="/blog">Blog</a></li>
              <li><a href="/blog/como-escrever-um-protocolo-de-revisao-sistematica/">Escrever o plano</a></li>
              <li><a href="/blog/checklist-prisma-2020-explicado/">Checklist PRISMA 2020</a></li>
              <li><a href="/blog/quanto-tempo-leva-uma-revisao-sistematica/">Quanto tempo leva</a></li>
              <li><a href="${caminhoRaiz}#perguntas">Dúvidas comuns</a></li>
            </ul>
          </div>

          <div>
            <p class="footer-heading">Transparência</p>
            <ul class="footer-links">
              <li><a href="/termos">Termos de uso</a></li>
              <li><a href="/privacidade">Privacidade</a></li>
              <li><a href="/feed.xml">Feed RSS</a></li>
              <li><a href="${caminhoRaiz}#para-quem">Para quem é</a></li>
            </ul>
          </div>
        </div>

        <div class="footer-bottom">
          <span>© 2026 Revsist · Eduardo Matheus Figueira · Licença MIT</span>
          <span class="footer-estado">
            <span>Beta aberta</span>
            <span>Grátis</span>
            <span>Sem rastreadores de terceiros</span>
          </span>
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

    const { htmlBody, secoes } = processarHtmlDoPost(body)
    const tempoLeitura = calcularTempoLeitura(body)

    posts.push({
      ...data,
      htmlBody,
      secoes,
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

    const video = REMOTION_VIDEOS[post.slug]
    const videoHtml = video
      ? `
        <figure class="article-video-bloco">
          <div class="laco laco--faixa">
            <video
              class="laco-video"
              data-laco
              width="${video.largura}"
              height="${video.altura}"
              autoplay
              muted
              loop
              playsinline
              preload="none"
              poster="${video.poster}"
              aria-label="${escaparXml(video.label)}"
            >
              <source src="${video.src}" type="video/mp4" />
            </video>
            <button type="button" class="laco-pausa" data-laco-pausa aria-label="Pausar a animação">
              <svg class="icone icone--p" aria-hidden="true" focusable="false"><use href="#i-pausa" /></svg>
            </button>
          </div>
          <figcaption class="article-video-legenda">
            ${escaparXml(video.legenda)}
          </figcaption>
        </figure>
      `
      : ''

    const outrosPosts = posts.filter((p) => p.slug !== post.slug)
    const linksRelacionadosHtml = outrosPosts.length
      ? `
        <div class="post-related">
          <h3><svg class="icone icone--p" aria-hidden="true" focusable="false"><use href="#i-documento" /></svg> Leituras recomendadas</h3>
          <div class="post-related-grid">
            ${outrosPosts
              .map(
                (p) => `
              <a href="/blog/${p.slug}/" class="post-related-card">
                <div>
                  <span class="rel-date">${formatarData(p.data)} · ${p.tempoLeitura}</span>
                  <h4 class="rel-title">${escaparXml(p.titulo)}</h4>
                </div>
                <span class="rel-link">Ler artigo <svg class="icone icone--p" aria-hidden="true" focusable="false"><use href="#i-seta" /></svg></span>
              </a>
            `
              )
              .join('')}
          </div>
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
      publisher: {
        '@type': 'Organization',
        name: 'Revsist',
        url: 'https://revsist.com',
      },
      keywords: post.tags.join(', '),
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
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escaparXml(post.titulo)} · Blog Revsist</title>
  <meta name="description" content="${escaparXml(post.descricao || post.resumo)}">
  <meta name="robots" content="index, follow">
  <meta name="color-scheme" content="light">
  <meta name="theme-color" content="#274c77">
  <link rel="canonical" href="https://revsist.com/blog/${post.slug}/">

  <!-- Preload da fonte tipográfica principal auto-hospedada -->
  <link rel="preload" href="/fonts/inter-variable.woff2" as="font" type="font/woff2" crossorigin>

  <meta http-equiv="Content-Security-Policy"
    content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; media-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none';" />

  <!-- Open Graph -->
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="Revsist">
  <meta property="og:locale" content="pt_BR">
  <meta property="og:url" content="https://revsist.com/blog/${post.slug}/">
  <meta property="og:title" content="${escaparXml(post.titulo)} · Blog Revsist">
  <meta property="og:description" content="${escaparXml(post.descricao || post.resumo)}">
  <meta property="og:image" content="https://revsist.com/og-image.png">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${escaparXml(post.titulo)} · Blog Revsist">
  <meta name="twitter:description" content="${escaparXml(post.descricao || post.resumo)}">
  <meta name="twitter:image" content="https://revsist.com/og-image.png">

  <!-- Favicon -->
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <link rel="alternate" type="application/rss+xml" title="Feed RSS do Blog Revsist" href="/feed.xml">
  <script>
    /* Aceite de termos: marca o documento antes da primeira pintura. O véu e o
       texto vêm de src/scripts/aceite.js; aqui só se decide se a página nasce
       bloqueada, porque essa decisão não pode esperar o módulo carregar. */
    (function () {
      try {
        var p = location.pathname.replace(/\\/+$/, '') || '/';
        if (p === '/termos' || p === '/privacidade') return;
        var b = localStorage.getItem('rsac_aceite_termos');
        if (b && JSON.parse(b).versao === '2026-09.2') return;
      } catch (e) { return; }
      document.documentElement.setAttribute('data-aceite', 'pendente');
    })();
  </script>
  <link rel="stylesheet" href="/src/styles/landing.css">
  <noscript><link rel="stylesheet" href="/styles/nojs.css"></noscript>

  <script type="application/ld+json">
    ${JSON.stringify(jsonLd)}
  </script>
  <script type="application/ld+json">
    ${JSON.stringify(breadcrumbsLd)}
  </script>
</head>
<body class="blog-body">
  <a href="#conteudo-artigo" class="skip-link">Pular para o conteúdo</a>
  ${renderizarSvgSprite()}
  ${renderizarCabecalho('/')}

  <main class="blog-article-layout" id="conteudo-artigo">
    <div class="article-container">
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
            <span class="meta-dot">·</span>
            <span>${escaparXml(post.autor || 'Eduardo Matheus Figueira')}</span>
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

        ${videoHtml}

        <div class="article-body prose">
          ${post.htmlBody}
        </div>

        <div class="article-cta-box">
          <h3>Conduza sua revisão com rigor metodológico</h3>
          <p>
            O Revsist automatiza a busca em bases brasileiras e internacionais, registra o rastro de cada decisão e compila o fluxograma PRISMA oficial diretamente do banco de dados relacional.
          </p>
          <div class="article-cta-actions">
            <a href="/app" class="btn btn-accent">
              Começar agora, de graça
              <svg class="icone icone--p" aria-hidden="true" focusable="false"><use href="#i-seta" /></svg>
            </a>
            <a href="/#como-funciona" class="btn btn-secondary">Ver demonstração na página inicial</a>
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
    <article class="blog-card">
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
          Ler artigo <svg class="icone icone--p" aria-hidden="true" focusable="false"><use href="#i-seta" /></svg>
        </a>
      </div>
    </article>
  `
    )
    .join('\n')

  const htmlBlogIndex = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog · Revsist — Revisão Sistemática com Rastro</title>
  <meta name="description" content="Artigos, guias metodológicos e análises fundamentadas sobre condução rigorosa de revisões sistemáticas e de escopo.">
  <meta name="robots" content="index, follow">
  <meta name="color-scheme" content="light">
  <meta name="theme-color" content="#274c77">
  <link rel="canonical" href="https://revsist.com/blog">

  <!-- Preload da fonte tipográfica principal auto-hospedada -->
  <link rel="preload" href="/fonts/inter-variable.woff2" as="font" type="font/woff2" crossorigin>

  <meta http-equiv="Content-Security-Policy"
    content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; media-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none';" />

  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Revsist">
  <meta property="og:locale" content="pt_BR">
  <meta property="og:url" content="https://revsist.com/blog">
  <meta property="og:title" content="Blog · Revsist — Revisão Sistemática com Rastro">
  <meta property="og:description" content="Artigos, guias metodológicos e análises fundamentadas sobre condução rigorosa de revisões sistemáticas e de escopo.">
  <meta property="og:image" content="https://revsist.com/og-image.png">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Blog · Revsist">
  <meta name="twitter:description" content="Artigos, guias metodológicos e análises fundamentadas sobre condução rigorosa de revisões sistemáticas.">
  <meta name="twitter:image" content="https://revsist.com/og-image.png">

  <!-- Favicon -->
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <link rel="alternate" type="application/rss+xml" title="Feed RSS do Blog Revsist" href="/feed.xml">
  <script>
    /* Aceite de termos: marca o documento antes da primeira pintura. O véu e o
       texto vêm de src/scripts/aceite.js; aqui só se decide se a página nasce
       bloqueada, porque essa decisão não pode esperar o módulo carregar. */
    (function () {
      try {
        var p = location.pathname.replace(/\\/+$/, '') || '/';
        if (p === '/termos' || p === '/privacidade') return;
        var b = localStorage.getItem('rsac_aceite_termos');
        if (b && JSON.parse(b).versao === '2026-09.2') return;
      } catch (e) { return; }
      document.documentElement.setAttribute('data-aceite', 'pendente');
    })();
  </script>
  <link rel="stylesheet" href="/src/styles/landing.css">
  <noscript><link rel="stylesheet" href="/styles/nojs.css"></noscript>

  <script type="application/ld+json">
    ${JSON.stringify(jsonLdBlog)}
  </script>
</head>
<body class="blog-index-body">
  <a href="#conteudo-blog" class="skip-link">Pular para os artigos</a>
  ${renderizarSvgSprite()}
  ${renderizarCabecalho('/')}

  <main class="blog-index-layout" id="conteudo-blog">
    <div class="blog-container">
      <header class="blog-index-header">
        <p class="kicker">Publicações &amp; Metodologia</p>
        <h1 class="blog-index-title">Blog do Revsist</h1>
        <p class="blog-index-subtitle">
          Textos com base na literatura científica sobre condução, triagem, diretrizes e integridade em revisões sistemáticas e de escopo.
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
      <author>eduardomatheusfigueira@gmail.com (${escaparXml(p.autor || 'Eduardo Matheus Figueira')})</author>
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
    { loc: 'https://revsist.com/termos', lastmod: '2026-09-15', priority: '0.5', changefreq: 'monthly' },
    { loc: 'https://revsist.com/privacidade', lastmod: '2026-09-15', priority: '0.5', changefreq: 'monthly' },
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
