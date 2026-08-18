#!/usr/bin/env node
/**
 * RSAC V2 — Auditoria de acessibilidade (doc 26 § 26.4, camada 3)
 * ====================================================================
 *
 * axe-core injetado via Playwright nas 8 telas do doc 24 § 24.4, em 2
 * paletas representativas (uma clara, uma escura — doc diz "paleta clara" e
 * "paleta escura", não todas as 13; isso é papel do contrast-check.mjs).
 *
 *   node scripts/a11y-audit.mjs           # relatório completo
 *   node scripts/a11y-audit.mjs --json    # saída para automação
 *
 * Critério de aceite (doc 26 § 26.4): zero violação `critical` ou `serious`.
 * Violações `moderate`/`minor` são só registradas — não derrubam o processo.
 *
 * Requer a fixture (`npm run test:seed`), o backend e o servidor de teste do
 * renderer (`vite.config.testserver.mts`) já no ar.
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  THEMES_REPRESENTATIVAS,
  abrirNavegador,
  acharProjetoFixture,
  checaBackend,
  checaFrontend,
  irPara,
  telas,
} from './shared/rsac-fixture.mjs'

const RAIZ = join(fileURLToPath(new URL('.', import.meta.url)), '..')
const AXE_SOURCE = readFileSync(join(RAIZ, 'node_modules/axe-core/axe.min.js'), 'utf-8')
const MODO_JSON = process.argv.includes('--json')
const BLOQUEANTES = new Set(['critical', 'serious'])

async function auditaPagina(page) {
  await page.addScriptTag({ content: AXE_SOURCE })
  // O axe percorre a árvore inteira do DOM; sob carga no sandbox isso passou
  // de 20 s numa amostra isolada — o timeout aqui é generoso de propósito.
  const violacoes = await Promise.race([
    page.evaluate(async () => {
      // eslint-disable-next-line no-undef
      const resultado = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] } })
      return resultado.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        description: v.description,
        nodes: v.nodes.map((n) => n.target.join(' ')).slice(0, 5),
      }))
    }),
    new Promise((_, rej) => setTimeout(() => rej(new Error('axe.run excedeu 30 s')), 30000)),
  ])
  return violacoes
}

async function main() {
  console.log('Auditando acessibilidade (axe-core, WCAG 2 A/AA)…')
  await checaBackend()
  await checaFrontend()
  const projeto = await acharProjetoFixture()

  const navegador = await abrirNavegador()
  // bypassCSP: a CSP do app bloqueia o <script> inline que o Playwright injeta.
  const page = await navegador.newPage({ viewport: { width: 1440, height: 900 }, bypassCSP: true })

  const achados = []
  for (const tela of telas(projeto.id)) {
    for (const tema of THEMES_REPRESENTATIVAS) {
      await irPara(page, tela.rota, tema)
      const violacoes = await auditaPagina(page)
      for (const v of violacoes) {
        achados.push({ tela: tela.id, tema, ...v })
      }
    }
  }
  await navegador.close()

  const bloqueantes = achados.filter((a) => BLOQUEANTES.has(a.impact))
  const informativas = achados.filter((a) => !BLOQUEANTES.has(a.impact))

  if (MODO_JSON) {
    console.log(JSON.stringify({ bloqueantes, informativas }, null, 2))
  } else {
    console.log(`\n${telas(projeto.id).length} telas × ${THEMES_REPRESENTATIVAS.length} paletas auditadas.\n`)
    if (bloqueantes.length === 0) {
      console.log('Nenhuma violação critical/serious. ✔')
    } else {
      console.log(`${bloqueantes.length} violação(ões) BLOQUEANTE(S) (critical/serious):\n`)
      for (const a of bloqueantes) {
        console.log(`  [${a.impact}] ${a.tela} (${a.tema}) — ${a.id}: ${a.description}`)
        for (const alvo of a.nodes) console.log(`      ${alvo}`)
      }
    }
    if (informativas.length) {
      console.log(`\n${informativas.length} violação(ões) informativa(s) (moderate/minor, não bloqueiam):`)
      for (const a of informativas) {
        console.log(`  [${a.impact}] ${a.tela} (${a.tema}) — ${a.id}: ${a.description}`)
      }
    }
  }

  process.exit(bloqueantes.length > 0 ? 1 : 0)
}

main().catch((err) => {
  console.error('\nFalha na auditoria de acessibilidade:', err.message)
  process.exit(1)
})
