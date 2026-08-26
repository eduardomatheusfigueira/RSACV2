/**
 * RSAC V2 — Electron Main Process
 * Gerencia lifecycle da aplicação, spawn do backend Python e criação da janela.
 */

import { app, BrowserWindow, shell } from 'electron'
import { existsSync, appendFileSync, mkdirSync } from 'fs'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { PythonManager } from './python-manager'
import { registerIpcHandlers, registrarPonteDoBackend, type InfoDoBackend } from './ipc-handlers'

function logToFile(msg: string) {
  try {
    const logDir = join(process.env.LOCALAPPDATA || 'C:\\Temp', 'RSAC')
    mkdirSync(logDir, { recursive: true })
    appendFileSync(join(logDir, 'electron_boot.log'), `[${new Date().toISOString()}] ${msg}\n`)
  } catch {}
}

process.on('uncaughtException', (err) => {
  logToFile(`Uncaught Exception: ${err?.stack || err}`)
})
process.on('unhandledRejection', (reason) => {
  logToFile(`Unhandled Rejection: ${reason}`)
})

const pythonManager = new PythonManager()
let mainWindow: BrowserWindow | null = null

const APP_ID = 'br.ufsc.rsac'
const BRAND_BACKGROUND = '#171f0d'

function resolveAppIcon(): string | undefined {
  const candidates = is.dev
    ? [join(__dirname, '../../resources/icon.png'), join(__dirname, '../../build/icon.png')]
    : [join(process.resourcesPath, 'icon.png')]
  return candidates.find(existsSync)
}

function createWindow(): void {
  logToFile('Creating main window')
  const icon = resolveAppIcon()

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    show: true,
    title: 'RSAC V2',
    backgroundColor: BRAND_BACKGROUND,
    ...(icon ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      plugins: true
    }
  })

  // Abrir links externos no browser padrão
  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // Em dev, carrega do dev server; em prod, do arquivo HTML
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

/**
 * Sobe o backend e resolve o que a interface precisa saber sobre ele.
 *
 * Devolve sempre — inclusive quando falha. A janela já está aberta quando isto
 * roda, e uma promessa rejeitada aqui viraria uma tela parada sem explicação;
 * o `erro` preenchido é o que permite à interface mostrar o diagnóstico de
 * conexão em vez de girar para sempre.
 */
async function iniciarBackend(): Promise<InfoDoBackend> {
  try {
    const porta = await pythonManager.start()
    logToFile(`Python backend started on port ${porta}`)
    return { porta, tokenLocal: pythonManager.lerTokenLocal() }
  } catch (error) {
    logToFile(`Python backend start failed: ${error}`)
    return { porta: null, tokenLocal: null, erro: String(error) }
  }
}

app.whenReady().then(() => {
  logToFile('App whenReady triggered')
  electronApp.setAppUserModelId(APP_ID)

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  registerIpcHandlers()

  // A partida do backend corre **em paralelo** com a janela, não antes dela.
  //
  // Antes, `whenReady` esperava o health check do Python para só então chamar
  // `createWindow`: até 30 s entre o duplo-clique e qualquer pixel na tela, com
  // a splash de marca do `index.html` — feita justamente para cobrir essa
  // espera — só aparecendo depois que a espera havia terminado. Quem instalava
  // o app via o ícone saltar na barra de tarefas e nada acontecer.
  //
  // Agora a janela aparece no primeiro instante, mostra a splash, e pergunta
  // pela porta quando precisa dela (`backend:info`).
  const backendPronto = iniciarBackend()
  registrarPonteDoBackend(() => backendPronto)

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', async () => {
  logToFile('Window all closed, stopping backend...')
  await pythonManager.stop()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
