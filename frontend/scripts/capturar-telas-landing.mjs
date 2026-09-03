#!/usr/bin/env node
/**
 * Revsist — Captura determinística de telas para a Landing Page (doc 51 §51.5 A2)
 * ==============================================================================
 *
 * Semeia a fixture e gera as 6 telas reais do app em WebP (1280w e 640w),
 * com viewport 1440×900 @2x, tema Platinum-Dusk / Light, sem dados pessoais.
 *
 * Saída em `landing/src/imagens/telas/`.
 */

import { existsSync, mkdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'
import {
  BACKEND_URL,
  FRONTEND_URL,
  abrirNavegador,
  acharProjetoFixture,
  checaBackend,
  checaFrontend,
  irPara,
} from './shared/rsac-fixture.mjs'

const DIR_TELAS = join(fileURLToPath(new URL('.', import.meta.url)), '..', '..', 'landing', 'src', 'imagens', 'telas')

if (!existsSync(DIR_TELAS)) {
  mkdirSync(DIR_TELAS, { recursive: true })
}

const TELAS_ESPEC = [
  {
    nome: '01-triagem',
    rota: (id) => `/projects/${id}/screening`,
    seletor: '.screening-workspace, .screening-page-layout, main, body',
    espera: 2000,
    descricao: 'Painel de triagem em duas colunas com metadados do estudo e checklist de elegibilidade',
  },
  {
    nome: '02-protocolo',
    rota: (id) => `/projects/${id}/protocol`,
    seletor: '.protocol-studio, .simplified-protocol, main, body',
    espera: 1500,
    descricao: 'Editor do protocolo de pesquisa com PICO, critérios e seleção de diretriz metodológica',
  },
  {
    nome: '03-coleta',
    rota: (id) => `/projects/${id}/harvest`,
    seletor: '.harvest-page, main, body',
    espera: 1500,
    descricao: 'Painel de coleta bibliográfica com busca federada e contagem de registros por base',
  },
  {
    nome: '04-rastro',
    rota: (id) => `/projects/${id}/screening`,
    seletor: '.study-evaluation-column, .paper-detail-card, .screening-workspace, main',
    espera: 2000,
    descricao: 'Detalhamento do rastro de auditoria da decisão com metadados de autoria e proveniência',
  },
  {
    nome: '05-extracao',
    rota: (id) => `/projects/${id}/extraction`,
    seletor: '.extraction-page, main, body',
    espera: 1500,
    descricao: 'Formulário de extração estruturada de variáveis metodológicas por artigo incluído',
  },
  {
    nome: '06-exportacao',
    rota: (id) => `/projects/${id}/export`,
    seletor: '.export-page, main, body',
    espera: 1500,
    descricao: 'Fluxograma PRISMA compilado do banco de dados e opções de exportação de dados',
  },
]

async function converterParaWebp(pngBuffer, nomeBase) {
  const metadata = await sharp(pngBuffer).metadata()
  const resultados = []

  // 1. Versão 1280w
  const path1280 = join(DIR_TELAS, `${nomeBase}-1280.webp`)
  const buf1280 = await sharp(pngBuffer)
    .resize({ width: 1280, withoutEnlargement: true })
    .webp({ quality: 82, effort: 6 })
    .toFile(path1280)

  // 2. Versão 640w
  const path640 = join(DIR_TELAS, `${nomeBase}-640.webp`)
  const buf640 = await sharp(pngBuffer)
    .resize({ width: 640, withoutEnlargement: true })
    .webp({ quality: 80, effort: 6 })
    .toFile(path640)

  const size1280 = statSync(path1280).size
  const size640 = statSync(path640).size

  return {
    nomeBase,
    path1280,
    path640,
    width1280: buf1280.width,
    height1280: buf1280.height,
    size1280Kb: (size1280 / 1024).toFixed(1),
    width640: buf640.width,
    height640: buf640.height,
    size640Kb: (size640 / 1024).toFixed(1),
  }
}

async function main() {
  console.log('=== Captura de Telas Determinística para a Landing (A2) ===')
  await checaBackend()
  await checaFrontend()

  const projeto = await acharProjetoFixture()
  console.log(`Projeto fixture carregado: ${projeto.id} (${projeto.title})`)

  console.log('Iniciando Chromium...')
  const browser = await abrirNavegador()
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: 'light',
  })
  const page = await context.newPage()

  const relatorio = []

  for (const tela of TELAS_ESPEC) {
    console.log(`\nCapturando: ${tela.nome} (${tela.descricao})...`)
    const rota = tela.rota(projeto.id)
    await irPara(page, rota, 'platinum-dusk')
    await page.waitForTimeout(tela.espera)

    // Esconder elementos dinâmicos ou de cursor se houver
    await page.evaluate(() => {
      document.body.style.cursor = 'default'
      const activeEl = document.activeElement
      if (activeEl && typeof activeEl.blur === 'function') {
        activeEl.blur()
      }
    })

    let clip = null
    const el = await page.$(tela.seletor)
    if (el) {
      const box = await el.boundingBox()
      if (box && box.width > 300 && box.height > 200) {
        // Enquadra na área útil relevante mantendo proporção ampla
        clip = {
          x: Math.max(0, box.x),
          y: Math.max(0, box.y),
          width: Math.min(1440, box.width),
          height: Math.min(900, Math.max(700, box.height)),
        }
      }
    }

    const pngBuffer = await page.screenshot({
      type: 'png',
      clip: clip || { x: 0, y: 0, width: 1440, height: 900 },
    })

    const res = await converterParaWebp(pngBuffer, tela.nome)
    relatorio.push(res)
    console.log(`  ✓ 1280w: ${res.size1280Kb} kB (${res.width1280}×${res.height1280}px)`)
    console.log(`  ✓ 640w:  ${res.size640Kb} kB (${res.width640}×${res.height640}px)`)
  }

  await browser.close()

  console.log('\n=== Resumo das Imagens Geradas ===')
  console.log('| Arquivo | Dimensão 1280 | Peso 1280 | Dimensão 640 | Peso 640 | Limite (140 kB) |')
  console.log('|---|---|---|---|---|---|')
  for (const r of relatorio) {
    const ok = parseFloat(r.size1280Kb) <= 140 ? '✔ OK' : '✘ EXCEDEU'
    console.log(`| ${r.nomeBase} | ${r.width1280}×${r.height1280} | ${r.size1280Kb} kB | ${r.width640}×${r.height640} | ${r.size640Kb} kB | ${ok} |`)
  }
}

main().catch((err) => {
  console.error('\nErro ao capturar telas:', err)
  process.exit(1)
})
