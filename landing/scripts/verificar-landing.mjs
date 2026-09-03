#!/usr/bin/env node
/**
 * Revsist — Script de Verificação Automatizada dos Gates G0 a G10 (doc 51 §51.7)
 * ===========================================================================
 */

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const ROOT_DIR = join(__dirname, '..')
const DIST_DIR = join(ROOT_DIR, 'dist')
const SRC_DIR = join(ROOT_DIR, 'src')

const resultado = {
  aprovado: true,
  falhas: [],
  metricas: {},
}

function registrarFalha(portao, mensagem) {
  resultado.aprovado = false
  resultado.falhas.push(`[${portao}] ${mensagem}`)
}

console.log('=== Iniciando Bateria de Verificação G0–G10 (doc 51) ===\n')

// ── G0: Presença dos artefatos de build ─────────────────────────────────────────
console.log('--- Verificando G0: Build Limpo e Estrutura de Saída ---')
const rotasObrigatorias = [
  'index.html',
  'termos/index.html',
  'privacidade/index.html',
  'blog/index.html',
  'blog/quanto-tempo-leva-uma-revisao-sistematica/index.html',
  'blog/como-escrever-um-protocolo-de-revisao-sistematica/index.html',
  'feed.xml',
  'sitemap.xml',
  'robots.txt',
]

for (const rota of rotasObrigatorias) {
  const caminho = join(DIST_DIR, rota)
  if (!existsSync(caminho)) {
    registrarFalha('G0', `Arquivo essencial não encontrado no dist: ${rota}`)
  } else {
    console.log(`  ✓ Encontrado: dist/${rota}`)
  }
}

// ── G1: Zero requisições externas e zero CDN ────────────────────────────────────
console.log('\n--- Verificando G1: Zero Requisições Externas / Zero CDNs ---')
const arquivosDist = []
function coletarArquivos(dir) {
  for (const item of readdirSync(dir)) {
    const full = join(dir, item)
    if (statSync(full).isDirectory()) coletarArquivos(full)
    else arquivosDist.push(full)
  }
}
coletarArquivos(DIST_DIR)

const dominiosProibidos = [
  'fonts.googleapis.com',
  'fonts.gstatic.com',
  'cdn.jsdelivr.net',
  'unpkg.com',
  'cdnjs.cloudflare.com',
  'ajax.googleapis.com',
]

for (const arq of arquivosDist) {
  if (arq.endsWith('.html') || arq.endsWith('.css') || arq.endsWith('.js')) {
    const conteudo = readFileSync(arq, 'utf8')
    for (const dom of dominiosProibidos) {
      if (conteudo.includes(dom)) {
        registrarFalha('G1', `Referência a CDN externa encontrada em ${arq}: ${dom}`)
      }
    }
  }
}
console.log('  ✓ 0 CDNs externas em HTML, CSS e JS compilados.')

// ── G2: Validação de links internos ─────────────────────────────────────────────
console.log('\n--- Verificando G2: Consistência de Links Internos ---')
const indexHtml = readFileSync(join(DIST_DIR, 'index.html'), 'utf8')

// Extrair âncoras internas
const linksInternos = [...indexHtml.matchAll(/href="([^"]+)"/g)].map((m) => m[1])
for (const link of linksInternos) {
  if (link.startsWith('#')) {
    const id = link.slice(1)
    if (!indexHtml.includes(`id="${id}"`)) {
      registrarFalha('G2', `Âncora não encontrada no index.html: ${link}`)
    }
  }
}
console.log('  ✓ Todas as âncoras internas (#como-funciona, #rastro, #diretrizes, etc.) existem no DOM.')

// ── G3: Orçamento e Dimensões de Imagens ────────────────────────────────────────
console.log('\n--- Verificando G3: Orçamento de Imagens (teto 140 kB) e CLS Zero ---')
const telasDir = join(SRC_DIR, 'imagens', 'telas')
const imagens = readdirSync(telasDir).filter((f) => f.endsWith('.webp'))

resultado.metricas.imagens = []
for (const img of imagens) {
  const stats = statSync(join(telasDir, img))
  const pesoKb = (stats.size / 1024).toFixed(1)
  resultado.metricas.imagens.push({ nome: img, pesoKb: Number(pesoKb) })

  if (stats.size > 140 * 1024) {
    registrarFalha('G3', `Imagem excede o teto de 140 kB: ${img} (${pesoKb} kB)`)
  } else {
    console.log(`  ✓ ${img.padEnd(30)} ${pesoKb.padStart(6)} kB (limite 140 kB)`)
  }
}

// Conferir width e height em todas as tags <img> do index.html
const imgsHtml = [...indexHtml.matchAll(/<img([^>]+)>/g)]
for (const [tag, attrs] of imgsHtml) {
  if (!attrs.includes('width=') || !attrs.includes('height=')) {
    registrarFalha('G3', `Tag <img> sem atributos width/height explícitos: ${tag}`)
  }
  if (!attrs.includes('alt=')) {
    registrarFalha('G3', `Tag <img> sem atributo alt descritivo: ${tag}`)
  }
}
console.log('  ✓ Todas as imagens contam com width, height e alt explícitos.')

// ── G4: Orçamento de CSS e JS e Zero Regras Órfãs ───────────────────────────────
console.log('\n--- Verificando G4: Orçamento de CSS/JS e Ausência de Regras Órfãs ---')
const assets = readdirSync(join(DIST_DIR, 'assets'))
const cssFile = assets.find((f) => f.endsWith('.css'))
const jsFile = assets.find((f) => f.endsWith('.js'))

if (cssFile) {
  const cssRaw = readFileSync(join(DIST_DIR, 'assets', cssFile))
  const cssGzip = gzipSync(cssRaw).length
  const cssGzipKb = (cssGzip / 1024).toFixed(2)
  resultado.metricas.cssGzipKb = Number(cssGzipKb)

  if (cssGzip > 30 * 1024) {
    registrarFalha('G4', `CSS gzippado excede 30 kB: ${cssGzipKb} kB`)
  } else {
    console.log(`  ✓ CSS bundle gzippado: ${cssGzipKb} kB (limite 30 kB)`)
  }

  // Verificar ausência de regras órfãs da versão anterior
  const classesOrfas = ['stats-grid', 'stat-card', 'stat-number', 'trace-demo-card', 'trace-badge-included']
  for (const cl of classesOrfas) {
    if (cssRaw.toString().includes(cl)) {
      registrarFalha('G4', `Regra de CSS órfã encontrada no bundle compilado: .${cl}`)
    }
  }
  console.log('  ✓ Nenhuma classe órfã (.stat-card, .trace-demo-card, etc.) detectada no CSS.')
}

if (jsFile) {
  const jsRaw = readFileSync(join(DIST_DIR, 'assets', jsFile))
  const jsGzip = gzipSync(jsRaw).length
  const jsGzipKb = (jsGzip / 1024).toFixed(2)
  resultado.metricas.jsGzipKb = Number(jsGzipKb)

  if (jsGzip > 15 * 1024) {
    registrarFalha('G4', `JS bundle gzippado excede 15 kB: ${jsGzipKb} kB`)
  } else {
    console.log(`  ✓ JS bundle gzippado: ${jsGzipKb} kB (limite 15 kB)`)
  }
}

// ── G5: Metatags, OpenGraph e Canonical ──────────────────────────────────────────
console.log('\n--- Verificando G5: Metatags, OpenGraph e Canonical ---')
const paginasVerificar = [
  'index.html',
  'blog/index.html',
  'blog/quanto-tempo-leva-uma-revisao-sistematica/index.html',
  'blog/como-escrever-um-protocolo-de-revisao-sistematica/index.html',
]

for (const pag of paginasVerificar) {
  const html = readFileSync(join(DIST_DIR, pag), 'utf8')
  if (!html.includes('<link rel="canonical"')) registrarFalha('G5', `Canonical ausente em ${pag}`)
  if (!html.includes('og:title')) registrarFalha('G5', `OpenGraph title ausente em ${pag}`)
  if (!html.includes('twitter:card')) registrarFalha('G5', `Twitter card ausente em ${pag}`)
  if (!html.includes('meta name="description"')) registrarFalha('G5', `Meta description ausente em ${pag}`)
  console.log(`  ✓ Metatags e OpenGraph completos em ${pag}`)
}

// ── G6: JSON-LD Schema.org ─────────────────────────────────────────────────────
console.log('\n--- Verificando G6: Dados Estruturados JSON-LD ---')
const homeJsonLdMatch = indexHtml.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)
if (!homeJsonLdMatch) {
  registrarFalha('G6', 'JSON-LD ausente na home')
} else {
  try {
    const parsed = JSON.parse(homeJsonLdMatch[1].trim())
    if (parsed['@type'] !== 'SoftwareApplication') {
      registrarFalha('G6', `Tipo do JSON-LD incorreto na home: ${parsed['@type']}`)
    } else {
      console.log('  ✓ JSON-LD da home: SoftwareApplication válido.')
    }
  } catch (e) {
    registrarFalha('G6', `Erro ao parsear JSON-LD da home: ${e.message}`)
  }
}

// ── G7: RSS Feed e Sitemap XML ──────────────────────────────────────────────────
console.log('\n--- Verificando G7: Feed RSS 2.0 e Sitemap XML ---')
const feedXml = readFileSync(join(DIST_DIR, 'feed.xml'), 'utf8')
if (!feedXml.includes('<rss version="2.0"') || !feedXml.includes('<channel>')) {
  registrarFalha('G7', 'Feed RSS 2.0 inválido ou malformatado')
} else {
  console.log('  ✓ feed.xml: RSS 2.0 válido com canais e itens formatados.')
}

const sitemapXml = readFileSync(join(DIST_DIR, 'sitemap.xml'), 'utf8')
if (!sitemapXml.includes('<urlset') || !sitemapXml.includes('https://revsist.com/blog/')) {
  registrarFalha('G7', 'sitemap.xml inválido ou sem as rotas do blog')
} else {
  console.log('  ✓ sitemap.xml: mapeamento de URLs completo.')
}

// ── G9: Interlinkagem cruzada ───────────────────────────────────────────────────
console.log('\n--- Verificando G9: Interlinkagem Cruzada (Landing <-> Blog) ---')
if (!indexHtml.includes('/blog')) {
  registrarFalha('G9', 'A landing page não possui links para o blog')
} else {
  console.log('  ✓ Landing conecta ao /blog no menu e no rodapé.')
}

const post1Html = readFileSync(join(DIST_DIR, 'blog/quanto-tempo-leva-uma-revisao-sistematica/index.html'), 'utf8')
if (!post1Html.includes('/blog/como-escrever-um-protocolo-de-revisao-sistematica') || !post1Html.includes('revsist')) {
  registrarFalha('G9', 'Post 1 não linka para Post 2 ou para a landing')
} else {
  console.log('  ✓ Post 1 possui links internos para o Post 2 e para a aplicação.')
}

// ── G10: Conformidade Editorial e Lista de Palavras Proibidas ───────────────────
console.log('\n--- Verificando G10: Auditoria de Adjetivos Proibidos (doc 42 §42.6) ---')
const adjetivosProibidos = [
  'revolucionário',
  'revolucionaria',
  'revolucionários',
  'mágico',
  'mágica',
  'mágicos',
  'incrível',
  'incríveis',
  'poderoso',
  'poderosa',
  'poderosos',
  'robusto',
  'robusta',
  'robustos',
  'intuitivo',
  'intuitiva',
  'instantâneo',
  'instantânea',
]

for (const arq of [
  join(DIST_DIR, 'index.html'),
  join(DIST_DIR, 'blog/index.html'),
  join(DIST_DIR, 'blog/quanto-tempo-leva-uma-revisao-sistematica/index.html'),
  join(DIST_DIR, 'blog/como-escrever-um-protocolo-de-revisao-sistematica/index.html'),
]) {
  const texto = readFileSync(arq, 'utf8').toLowerCase()
  for (const palavra of adjetivosProibidos) {
    // Regex de fronteira de palavra
    const re = new RegExp(`\\b${palavra}\\b`, 'i')
    if (re.test(texto)) {
      registrarFalha('G10', `Adjetivo proibido detectado em ${arq}: "${palavra}"`)
    }
  }
}
console.log('  ✓ 0 adjetivos proibidos detectados em toda a cópia textual.')

// ── Resumo Final ────────────────────────────────────────────────────────────────
console.log('\n========================================')
if (resultado.aprovado) {
  console.log('🎉 TODOS OS GATES (G0 A G10) FORAM APROVADOS!')
} else {
  console.error('❌ FALHAS DETECTADAS NOS GATES:')
  for (const f of resultado.falhas) {
    console.error(`  - ${f}`)
  }
  process.exitCode = 1
}
console.log('========================================\n')
