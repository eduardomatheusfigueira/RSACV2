/**
 * Revsist — Electron Main Process
 * Gerencia lifecycle da aplicação, spawn do backend Python e criação da janela.
 */

import { app, BrowserWindow, shell } from 'electron'
import { existsSync, appendFileSync, mkdirSync } from 'fs'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { PythonManager } from './python-manager'
import { registerIpcHandlers } from './ipc-handlers'

function logToFile(msg: string) {
  try {
    const logDir = join(process.env.LOCALAPPDATA || 'C:\\Temp', 'Revsist')
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

function createWindow(backendPort: number): void {
  logToFile(`Creating main window with backend port: ${backendPort}`)
  const icon = resolveAppIcon()

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    show: true,
    title: 'Revsist',
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
    mainWindow.loadURL(`${process.env['ELECTRON_RENDERER_URL']}?port=${backendPort}`)
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'), {
      query: { port: String(backendPort) }
    })
  }
}

app.whenReady().then(async () => {
  logToFile('App whenReady triggered')
  electronApp.setAppUserModelId(APP_ID)

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  registerIpcHandlers()

  let backendPort = 8000
  try {
    backendPort = await pythonManager.start()
    logToFile(`Python backend started on port ${backendPort}`)
  } catch (error) {
    logToFile(`Python backend start failed: ${error}. Falling back to default port.`)
  }

  createWindow(backendPort)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow(backendPort)
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
