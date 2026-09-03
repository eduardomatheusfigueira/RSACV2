/**
 * Revsist — Utilitários compartilhados da suíte de validação (doc 26)
 * ====================================================================
 *
 * Constantes e helpers usados por seed-fixture, a11y-audit, layout-budget,
 * visual-baseline e visual-check: URLs do backend/frontend, a lista das 13
 * paletas de `COLOR_THEMES` (SettingsPage.tsx) e as 8 telas do doc 24 § 24.4.
 *
 * Os scripts da camada 2/3 NÃO sobem o backend nem o servidor do renderer —
 * isso é responsabilidade de quem chama (CI ou o desenvolvedor). Rodar antes:
 *
 *   python3 backend/run.py &
 *   npx vite --config frontend/vite.config.testserver.mts &
 */

import { existsSync, readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

export const DIR_BASELINE = join(fileURLToPath(new URL('.', import.meta.url)), '..', '..', 'test-visual/baseline')
export const DIR_DIFF = join(fileURLToPath(new URL('.', import.meta.url)), '..', '..', 'test-visual/diff')

export const BACKEND_URL = process.env.RSAC_BACKEND_URL || 'http://127.0.0.1:8000'
export const FRONTEND_URL = process.env.RSAC_FRONTEND_URL || 'http://localhost:5199'

export function obterTokenLocal() {
  if (process.env.RSAC_LOCAL_TOKEN) return process.env.RSAC_LOCAL_TOKEN
  const caminhos = []
  if (process.env.RSAC_DATA_DIR) caminhos.push(join(process.env.RSAC_DATA_DIR, 'runtime_token'))
  if (process.platform === 'win32' && process.env.LOCALAPPDATA) {
    caminhos.push(join(process.env.LOCALAPPDATA, 'RSAC', 'RSAC', 'runtime_token'))
    caminhos.push(join(process.env.LOCALAPPDATA, 'RSAC', 'runtime_token'))
  } else if (process.platform === 'darwin') {
    caminhos.push(join(homedir(), 'Library', 'Application Support', 'RSAC', 'runtime_token'))
  } else {
    const xdg = process.env.XDG_DATA_HOME || join(homedir(), '.local', 'share')
    caminhos.push(join(xdg, 'RSAC', 'runtime_token'))
  }
  caminhos.push(join(homedir(), '.rsac', 'runtime_token'))
  for (const c of caminhos) {
    try {
      if (existsSync(c)) {
        const t = readFileSync(c, 'utf8').trim()
        if (t) return t
      }
    } catch {}
  }
  return null
}

function acharChromium() {
  if (process.env.RSAC_CHROMIUM_PATH) return process.env.RSAC_CHROMIUM_PATH
  const candidatos = [
    join(process.env.LOCALAPPDATA || '', 'ms-playwright', 'chromium-1161', 'chrome-win', 'chrome.exe'),
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  ]
  for (const c of candidatos) {
    try {
      if (existsSync(c)) return c
    } catch {}
  }
  return '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
}

export const CHROMIUM_PATH = acharChromium()

/** As 13 paletas de `frontend/src/pages/SettingsPage.tsx` (`COLOR_THEMES`). */
export const THEMES = [
  'dark',
  'light',
  'lava-steel',
  'pastel-dream',
  'stormy-tangerine',
  'platinum-dusk',
  'indigo-rose',
  'amethyst-deep',
  'parchment-linen',
  'periwinkle-ice',
  'fuchsia-blush',
  'powder-aqua',
  'synthwave-neon',
]

/** Uma clara e uma escura, para as camadas que só precisam de uma amostra (doc 26 § 26.4). */
export const THEMES_REPRESENTATIVAS = ['light', 'dark']

export const TITULO_FIXTURE = 'Revsist Fixture — Validação Visual (não editar)'

/** As 8 telas do doc 24 § 24.4, na ordem do ribbon. `rota` recebe o id do projeto fixture. */
export function telas(projectId) {
  return [
    { id: 'dashboard', rota: '/' },
    { id: 'projetos', rota: '/projects' },
    { id: 'protocolo', rota: `/projects/${projectId}/protocol` },
    { id: 'coleta', rota: `/projects/${projectId}/harvest` },
    { id: 'triagem', rota: `/projects/${projectId}/screening` },
    { id: 'extracao', rota: `/projects/${projectId}/extraction` },
    { id: 'exportar', rota: `/projects/${projectId}/export` },
    { id: 'config', rota: '/settings' },
  ]
}

async function chamar(caminho, opcoes = {}) {
  const token = obterTokenLocal()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'X-RSAC-Local-Token': token } : {}),
    ...(opcoes.headers || {}),
  }
  const res = await fetch(`${BACKEND_URL}/api/v1${caminho}`, {
    ...opcoes,
    headers,
  })
  if (!res.ok) {
    const corpo = await res.text().catch(() => '')
    throw new Error(`${opcoes.method || 'GET'} ${caminho} → ${res.status}: ${corpo.slice(0, 300)}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export { chamar }

/** Confirma que o backend responde antes de gastar tempo com o resto. */
export async function checaBackend() {
  try {
    await chamar('/projects?page_size=1')
  } catch (err) {
    throw new Error(
      `Backend inacessível em ${BACKEND_URL}. Suba-o antes: python3 backend/run.py\n  (${err.message})`
    )
  }
}

/** Confirma que o renderer responde antes de abrir o navegador. */
export async function checaFrontend() {
  try {
    const res = await fetch(FRONTEND_URL, { method: 'GET' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
  } catch (err) {
    throw new Error(
      `Frontend inacessível em ${FRONTEND_URL}. Suba-o antes:\n` +
        `  npx vite --config vite.config.testserver.mts\n  (${err.message})`
    )
  }
}

/** Acha o projeto fixture pelo título fixo. Lança erro pedindo `npm run test:seed` se não achar. */
export async function acharProjetoFixture() {
  const lista = await chamar('/projects?page_size=100')
  const items = lista.items || lista
  const projeto = (Array.isArray(items) ? items : []).find((p) => p.title === TITULO_FIXTURE)
  if (!projeto) {
    throw new Error(`Projeto fixture não encontrado. Rode primeiro: npm run test:seed`)
  }
  return projeto
}

/** Abre um Chromium consistente com o resto da suíte (mesmo binário do ambiente). */
export async function abrirNavegador() {
  return chromium.launch({ executablePath: CHROMIUM_PATH, args: ['--no-sandbox'] })
}

/**
 * Navega para uma rota do app já com a paleta aplicada e a UI assentada.
 *
 * `networkidle` nunca resolve aqui — o HMR do Vite e o polling de status do
 * backend mantêm a rede "ativa" para sempre — então esperamos só o DOM e
 * damos um tempo fixo de assentamento, como o resto da suíte já fazia.
 */
export async function irPara(page, rota, tema) {
  const token = obterTokenLocal()
  const tokenParam = token ? `&local_token=${encodeURIComponent(token)}` : ''
  const url = `${FRONTEND_URL}/?port=${new URL(BACKEND_URL).port}${tokenParam}#${rota}`
  // Timeout generoso: o ambiente de sandbox é lento sob carga (visto até 26 s
  // numa navegação isolada), não é sinal de travamento real.
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(1200)
  if (tema) {
    await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), tema)
    await page.waitForTimeout(250)
  }
}
