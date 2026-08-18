#!/usr/bin/env node
/**
 * RSAC V2 — Comparação visual pixel a pixel (doc 26 § 26.3, camada 2)
 * ====================================================================
 *
 * Recaptura as mesmas 8 telas × 13 paletas de visual-baseline.mjs e compara
 * cada imagem contra `test-visual/baseline/` com pixelmatch, tolerância de
 * 0,1% de pixels diferentes (limiar de antialiasing).
 *
 *   node scripts/visual-check.mjs           # relatório completo
 *   node scripts/visual-check.mjs --json    # saída para automação
 *
 * Diferença acima da tolerância grava a imagem de diff em
 * `test-visual/diff/` e falha o processo. Mudança visual intencional se
 * aprova regravando a referência (`npm run visual:baseline`) no mesmo
 * commit da mudança — nunca em commit separado.
 *
 * Requer a fixture (`npm run test:seed`), o backend, o servidor de teste do
 * renderer e uma referência já gravada (`npm run visual:baseline`).
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { PNG } from 'pngjs'
import pixelmatch from 'pixelmatch'
import {
  DIR_BASELINE,
  DIR_DIFF,
  THEMES,
  abrirNavegador,
  acharProjetoFixture,
  checaBackend,
  checaFrontend,
  irPara,
  telas,
} from './shared/rsac-fixture.mjs'

const TOLERANCIA = 0.001 // 0,1% dos pixels — doc 26 § 26.3
const MODO_JSON = process.argv.includes('--json')

function comparaPNG(bufAtual, bufBaseline) {
  const atual = PNG.sync.read(bufAtual)
  const baseline = PNG.sync.read(bufBaseline)
  if (atual.width !== baseline.width || atual.height !== baseline.height) {
    return { diferentes: true, motivo: `dimensões mudaram (${baseline.width}×${baseline.height} → ${atual.width}×${atual.height})` }
  }
  const { width, height } = atual
  const diff = new PNG({ width, height })
  const nDiff = pixelmatch(atual.data, baseline.data, diff.data, width, height, { threshold: 0.1 })
  const proporcao = nDiff / (width * height)
  return { diferentes: proporcao > TOLERANCIA, proporcao, nDiff, diffPNG: diff }
}

async function main() {
  if (!existsSync(DIR_BASELINE)) {
    console.error(`Referência não encontrada em ${DIR_BASELINE}. Rode primeiro: npm run visual:baseline`)
    process.exit(1)
  }

  console.log(`Comparando ${telas('x').length} telas × ${THEMES.length} paletas contra a referência…`)
  await checaBackend()
  await checaFrontend()
  const projeto = await acharProjetoFixture()

  mkdirSync(DIR_DIFF, { recursive: true })

  const navegador = await abrirNavegador()
  const page = await navegador.newPage({ viewport: { width: 1440, height: 900 } })

  const resultados = []
  for (const tela of telas(projeto.id)) {
    await irPara(page, tela.rota)
    for (const tema of THEMES) {
      await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), tema)
      await page.waitForTimeout(250)
      const nomeArquivo = `${tela.id}__${tema}.png`
      const caminhoBaseline = join(DIR_BASELINE, nomeArquivo)

      if (!existsSync(caminhoBaseline)) {
        resultados.push({ tela: tela.id, tema, status: 'sem-referencia' })
        continue
      }

      const atual = await page.screenshot()
      const baseline = readFileSync(caminhoBaseline)
      const cmp = comparaPNG(atual, baseline)

      if (cmp.diferentes) {
        if (cmp.diffPNG) {
          writeFileSync(join(DIR_DIFF, nomeArquivo), PNG.sync.write(cmp.diffPNG))
        }
        resultados.push({ tela: tela.id, tema, status: 'diferente', proporcao: cmp.proporcao, motivo: cmp.motivo })
      } else {
        resultados.push({ tela: tela.id, tema, status: 'ok' })
      }
    }
  }
  await navegador.close()

  const diferentes = resultados.filter((r) => r.status === 'diferente')
  const semReferencia = resultados.filter((r) => r.status === 'sem-referencia')

  if (MODO_JSON) {
    console.log(JSON.stringify({ diferentes, semReferencia, total: resultados.length }, null, 2))
  } else {
    console.log(`\n${resultados.length} imagens comparadas (tolerância ${TOLERANCIA * 100}%).\n`)
    if (diferentes.length === 0 && semReferencia.length === 0) {
      console.log('Nenhuma diferença além da tolerância. ✔')
    }
    if (diferentes.length) {
      console.log(`${diferentes.length} imagem(ns) com diferença — diff salvo em test-visual/diff/:`)
      for (const d of diferentes) {
        console.log(`  ${d.tela}__${d.tema}: ${d.motivo || `${(d.proporcao * 100).toFixed(2)}% dos pixels`}`)
      }
    }
    if (semReferencia.length) {
      console.log(`\n${semReferencia.length} imagem(ns) sem referência (rode npm run visual:baseline):`)
      for (const s of semReferencia) console.log(`  ${s.tela}__${s.tema}`)
    }
  }

  process.exit(diferentes.length > 0 || semReferencia.length > 0 ? 1 : 0)
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error('\nFalha na comparação visual:', err.message)
    process.exit(1)
  })
}
