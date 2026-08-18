#!/usr/bin/env node
/**
 * RSAC V2 — Verificador de contraste WCAG nas 13 paletas (doc 26 § 26.4)
 * ====================================================================
 *
 * O axe-core (a11y-audit.mjs) só mede o que está renderizado numa amostra de
 * paletas. Este script lê os tokens de `src/styles/globals.css` diretamente e
 * calcula a razão de contraste de cada par do doc 24 § 24.5, nas 13 paletas —
 * inclusive combinações que nenhuma tela produz hoje.
 *
 * Sem navegador: cálculo puro sobre o CSS parseado, roda em milissegundos.
 *
 *   node scripts/contrast-check.mjs           # relatório completo
 *   node scripts/contrast-check.mjs --json    # saída para automação
 *
 * NOTA sobre `--rsac-accent`: o doc 26 lista o par "--rsac-accent ×
 * --black-forest", mas esse token não existe mais em globals.css — só
 * aparece como fallback morto (`var(--rsac-accent, var(--sunlit-clay))`).
 * `--color-accent` é o token que hoje faz esse papel (é o que colidiu com
 * `--black-forest` em platinum-dusk, o achado que o doc 26 § 26.4 cita como
 * exemplo), então o par abaixo usa `--color-accent`.
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { THEMES } from './shared/rsac-fixture.mjs'

const RAIZ = join(fileURLToPath(new URL('.', import.meta.url)), '..')
const CSS_PATH = join(RAIZ, 'src/styles/globals.css')
const MODO_JSON = process.argv.includes('--json')

/** Cada par exigido pelo doc 24 § 24.5, com o mínimo WCAG (doc 26 § 26.4). */
const PARES = [
  { primeiro: '--color-text-primary', fundos: ['--color-bg-primary', '--color-bg-secondary', '--color-bg-tertiary'], minimo: 4.5 },
  { primeiro: '--color-text-secondary', fundos: ['--color-bg-primary', '--color-bg-secondary', '--color-bg-tertiary'], minimo: 4.5 },
  { primeiro: '--color-text-sidebar', fundos: ['--color-bg-sidebar'], minimo: 4.5 },
  { primeiro: '--color-accent', fundos: ['--color-bg-primary', '--color-bg-secondary', '--color-bg-tertiary'], minimo: 3 },
  { primeiro: '--color-accent', fundos: ['--black-forest'], minimo: 3, nota: 'equivalente a --rsac-accent × --black-forest (doc 26)' },
  { primeiro: '--color-included-text', fundos: ['--color-included-bg'], minimo: 4.5, compositarSobre: '--color-bg-primary' },
  { primeiro: '--color-excluded-text', fundos: ['--color-excluded-bg'], minimo: 4.5, compositarSobre: '--color-bg-primary' },
  { primeiro: '--color-pending-text', fundos: ['--color-pending-bg'], minimo: 4.5, compositarSobre: '--color-bg-primary' },
  { primeiro: '--color-border', fundos: ['--color-bg-secondary'], minimo: 3 },
]

function extraiBloco(css, inicioSelector) {
  const chaveAbre = css.indexOf('{', inicioSelector)
  let profundidade = 1
  let i = chaveAbre + 1
  while (profundidade > 0 && i < css.length) {
    if (css[i] === '{') profundidade++
    else if (css[i] === '}') profundidade--
    i++
  }
  return css.slice(chaveAbre + 1, i - 1)
}

function parseiaTokens(bloco) {
  const tokens = new Map()
  const re = /--([\w-]+)\s*:\s*([^;]+);/g
  let m
  while ((m = re.exec(bloco))) {
    tokens.set(`--${m[1]}`, m[2].trim())
  }
  return tokens
}

/** :root = paleta 'light'; cada `[data-theme='X']` = override sobre a base. */
function carregaPaletas(css) {
  const raizIdx = css.indexOf(':root')
  const base = parseiaTokens(extraiBloco(css, raizIdx))

  const paletas = { light: new Map(base) }
  const reSeletor = /((?:\[data-theme='[\w-]+'\]\s*,?\s*)+)\{/g
  let m
  while ((m = reSeletor.exec(css))) {
    const ids = [...m[1].matchAll(/data-theme='([\w-]+)'/g)].map((x) => x[1])
    const idConhecido = ids.find((id) => THEMES.includes(id))
    if (!idConhecido) continue
    const bloco = extraiBloco(css, m.index)
    const overrides = parseiaTokens(bloco)
    paletas[idConhecido] = new Map([...base, ...overrides])
  }
  return paletas
}

function resolveVar(valor, tokens, profundidade = 0) {
  if (profundidade > 10) return null
  const m = /^var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)$/.exec(valor.trim())
  if (!m) return valor.trim()
  const [, nome, fallback] = m
  if (tokens.has(nome)) return resolveVar(tokens.get(nome), tokens, profundidade + 1)
  if (fallback) return resolveVar(fallback, tokens, profundidade + 1)
  return null
}

function paraRGB(valor) {
  const hex = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.exec(valor)
  if (hex) {
    let h = hex[1]
    if (h.length === 3) h = [...h].map((c) => c + c).join('')
    const n = parseInt(h, 16)
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255, a: 1 }
  }
  const rgba = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/.exec(valor)
  if (rgba) {
    return { r: +rgba[1], g: +rgba[2], b: +rgba[3], a: rgba[4] !== undefined ? +rgba[4] : 1 }
  }
  return null
}

function compositar(fg, bg) {
  if (fg.a >= 1) return fg
  const a = fg.a
  return {
    r: a * fg.r + (1 - a) * bg.r,
    g: a * fg.g + (1 - a) * bg.g,
    b: a * fg.b + (1 - a) * bg.b,
    a: 1,
  }
}

function luminancia({ r, g, b }) {
  const canal = (c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)
}

function razaoDeContraste(rgb1, rgb2) {
  const l1 = luminancia(rgb1)
  const l2 = luminancia(rgb2)
  const [claro, escuro] = l1 >= l2 ? [l1, l2] : [l2, l1]
  return (claro + 0.05) / (escuro + 0.05)
}

/** Resolve um token até virar cor efetiva, compositando sobre `sobreToken` se vier com alfa. */
function corEfetiva(tokenNome, tokens, sobreToken) {
  const bruto = tokens.get(tokenNome)
  if (bruto === undefined) return null
  const resolvido = resolveVar(bruto, tokens)
  if (resolvido === null) return null
  const rgb = paraRGB(resolvido)
  if (!rgb) return null // color-mix() etc. — fora do escopo deste verificador
  if (rgb.a < 1 && sobreToken) {
    const fundoBruto = tokens.get(sobreToken)
    const fundoResolvido = fundoBruto && resolveVar(fundoBruto, tokens)
    const fundoRgb = fundoResolvido && paraRGB(fundoResolvido)
    if (fundoRgb) return compositar(rgb, fundoRgb)
  }
  return rgb
}

function main() {
  const css = readFileSync(CSS_PATH, 'utf-8')
  const paletas = carregaPaletas(css)

  const faltando = THEMES.filter((t) => !paletas[t])
  if (faltando.length) {
    console.error(`Paletas não encontradas em globals.css: ${faltando.join(', ')}`)
    process.exit(1)
  }

  const falhas = []
  const resultados = []

  for (const nomePaleta of THEMES) {
    const tokens = paletas[nomePaleta]
    for (const par of PARES) {
      const corTexto = corEfetiva(par.primeiro, tokens)
      for (const fundoToken of par.fundos) {
        const corFundo = corEfetiva(fundoToken, tokens, par.compositarSobre)
        if (!corTexto || !corFundo) {
          resultados.push({ paleta: nomePaleta, par: `${par.primeiro} × ${fundoToken}`, status: 'ignorado (cor não resolvível)' })
          continue
        }
        const razao = razaoDeContraste(corTexto, corFundo)
        const ok = razao >= par.minimo
        const item = {
          paleta: nomePaleta,
          par: `${par.primeiro} × ${fundoToken}`,
          razao: Math.round(razao * 100) / 100,
          minimo: par.minimo,
          ok,
          nota: par.nota,
        }
        resultados.push(item)
        if (!ok) falhas.push(item)
      }
    }
  }

  if (MODO_JSON) {
    console.log(JSON.stringify({ falhas, resultados }, null, 2))
  } else {
    console.log(`Contraste WCAG verificado em ${THEMES.length} paletas × ${PARES.length} pares.\n`)
    if (falhas.length === 0) {
      console.log('Todos os pares atingem o mínimo exigido. ✔')
    } else {
      console.log(`${falhas.length} par(es) abaixo do mínimo:\n`)
      for (const f of falhas) {
        console.log(`  [${f.paleta}] ${f.par}: ${f.razao}:1 (exige ${f.minimo}:1)${f.nota ? ` — ${f.nota}` : ''}`)
      }
    }
  }

  process.exit(falhas.length > 0 ? 1 : 0)
}

main()
