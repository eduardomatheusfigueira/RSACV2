#!/usr/bin/env node
/**
 * Revsist — Referência da comparação visual (doc 26 § 26.3, camada 2)
 * ====================================================================
 *
 * Grava a captura de 8 telas × 13 paletas (104 imagens, 1440×900) em
 * `test-visual/baseline/`. Rodar só na primeira vez, e depois só quando uma
 * mudança visual for intencional e aprovada — sempre regravando a referência
 * NO MESMO COMMIT da mudança, para o diff da referência ficar revisável
 * junto com o código (doc 26 § 26.9).
 *
 *   node scripts/visual-baseline.mjs
 *
 * ⚠️ Limitação conhecida: o doc 26 pede também 3 estados por tela onde
 * couber (vazio, carregado, erro). Esta primeira versão grava só o estado
 * "carregado" (a fixture semeada por seed-fixture.mjs) — os outros dois
 * ficam para uma iteração futura.
 *
 * Requer a fixture (`npm run test:seed`), o backend e o servidor de teste do
 * renderer (`vite.config.testserver.mts`) já no ar.
 */

import { mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { DIR_BASELINE, THEMES, abrirNavegador, acharProjetoFixture, checaBackend, checaFrontend, irPara, telas } from './shared/rsac-fixture.mjs'

async function main() {
  console.log(`Gravando referência visual: ${telas('x').length} telas × ${THEMES.length} paletas…`)
  await checaBackend()
  await checaFrontend()
  const projeto = await acharProjetoFixture()

  mkdirSync(DIR_BASELINE, { recursive: true })

  const navegador = await abrirNavegador()
  const page = await navegador.newPage({ viewport: { width: 1440, height: 900 } })

  let total = 0
  for (const tela of telas(projeto.id)) {
    await irPara(page, tela.rota)
    for (const tema of THEMES) {
      await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), tema)
      await page.waitForTimeout(250)
      await page.screenshot({ path: join(DIR_BASELINE, `${tela.id}__${tema}.png`) })
      total++
    }
    console.log(`  ${tela.id}: ${THEMES.length} paletas capturadas`)
  }
  await navegador.close()

  console.log(`\n${total} imagens gravadas em test-visual/baseline/`)
}

// Guarda de execução: este módulo é importado por visual-check.mjs só para
// reaproveitar DIR_BASELINE — sem isso, importar rodaria o baseline inteiro
// como efeito colateral toda vez que o check rodasse.
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error('\nFalha ao gravar a referência visual:', err.message)
    process.exit(1)
  })
}
