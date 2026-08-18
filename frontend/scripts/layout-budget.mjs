#!/usr/bin/env node
/**
 * RSAC V2 — Orçamento de proporção da moldura (doc 26 § 26.4, doc 24 § 24.4)
 * ====================================================================
 *
 * Com o app em execução, mede as regiões de "moldura" (tudo que não é área
 * de trabalho) contra a altura da janela:
 *
 *   moldura = titlebar do ribbon + abas do ribbon + toolstrip do ribbon
 *           + cabeçalho da página + barra de status
 *   falha se moldura / altura da janela > 0.25
 *
 * Baseline medida no doc 24 § 24.4: Protocolo 42%, Triagem 25%, Coleta 26%.
 * Alvo do doc 25: ≤ 25% em todas as 8 telas.
 *
 *   node scripts/layout-budget.mjs           # relatório completo
 *   node scripts/layout-budget.mjs --json    # saída para automação
 *
 * Requer a fixture (`npm run test:seed`), o backend e o servidor de teste do
 * renderer (`vite.config.testserver.mts`) já no ar.
 */

import { abrirNavegador, acharProjetoFixture, checaBackend, checaFrontend, irPara, telas } from './shared/rsac-fixture.mjs'

const MODO_JSON = process.argv.includes('--json')
const ORCAMENTO = 0.25
const ALTURA_JANELA = 900

const REGIOES_MOLDURA = [
  '.ribbon-titlebar',
  '.ribbon-tabs-bar',
  '.ribbon-toolstrip',
  '.rsac-page-header',
  '.status-bar',
]

async function medeMoldura(page) {
  return page.evaluate((seletores) => {
    let total = 0
    const detalhe = {}
    for (const sel of seletores) {
      const el = document.querySelector(sel)
      const altura = el ? el.getBoundingClientRect().height : 0
      detalhe[sel] = Math.round(altura)
      total += altura
    }
    return { total, detalhe }
  }, REGIOES_MOLDURA)
}

async function main() {
  console.log('Medindo orçamento de moldura (doc 24 § 24.4)…')
  await checaBackend()
  await checaFrontend()
  const projeto = await acharProjetoFixture()

  const navegador = await abrirNavegador()
  const page = await navegador.newPage({ viewport: { width: 1440, height: ALTURA_JANELA } })

  const resultados = []
  for (const tela of telas(projeto.id)) {
    await irPara(page, tela.rota)
    const { total, detalhe } = await medeMoldura(page)
    const proporcao = total / ALTURA_JANELA
    resultados.push({ tela: tela.id, molduraPx: Math.round(total), proporcao: Math.round(proporcao * 1000) / 1000, ok: proporcao <= ORCAMENTO, detalhe })
  }
  await navegador.close()

  const falhas = resultados.filter((r) => !r.ok)

  if (MODO_JSON) {
    console.log(JSON.stringify({ orcamento: ORCAMENTO, resultados }, null, 2))
  } else {
    console.log(`\nOrçamento: moldura ≤ ${ORCAMENTO * 100}% da altura da janela (${ALTURA_JANELA}px)\n`)
    for (const r of resultados) {
      const marca = r.ok ? '✔' : '✘'
      console.log(`  ${marca} ${r.tela.padEnd(12)} ${r.molduraPx}px  (${Math.round(r.proporcao * 1000) / 10}%)`)
    }
    if (falhas.length) {
      console.log(`\n${falhas.length} tela(s) acima do orçamento:`)
      for (const f of falhas) {
        console.log(`  ${f.tela}: ${JSON.stringify(f.detalhe)}`)
      }
    } else {
      console.log('\nTodas as telas dentro do orçamento. ✔')
    }
  }

  process.exit(falhas.length > 0 ? 1 : 0)
}

main().catch((err) => {
  console.error('\nFalha ao medir o orçamento de moldura:', err.message)
  process.exit(1)
})
