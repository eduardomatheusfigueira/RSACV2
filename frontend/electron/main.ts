/**
 * RSAC V2 — Electron Main Process
 * Gerencia lifecycle da aplicação, spawn do backend Python e criação da janela.
 */

import { app, BrowserWindow, shell } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { PythonManager } from './python-manager'
import { registerIpcHandlers } from './ipc-handlers'

const pythonManager = new PythonManager()
let mainWindow: BrowserWindow | null = null

function createWindow(backendPort: number): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    show: false,
    title: 'RSAC V2',
    backgroundColor: '#0f0f0f',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  // Passa a porta do backend para o renderer via query string
  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
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
  // Configurações de segurança do Electron
  electronApp.setAppUserModelId('com.rsac.v2')

  // Otimização de atalhos (DevTools: F12)
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // Registrar handlers IPC
  registerIpcHandlers()

  // Iniciar backend Python
  console.log('[Main] Iniciando backend Python...')
  let backendPort: number

  try {
    backendPort = await pythonManager.start()
    console.log(`[Main] Backend Python rodando na porta ${backendPort}`)
  } catch (error) {
    console.error('[Main] Falha ao iniciar backend Python:', error)
    // Em dev, usa porta padrão (backend pode estar rodando separadamente)
    backendPort = 8000
    console.log(`[Main] Usando porta padrão ${backendPort} (modo dev)`)
  }

  // Criar janela principal
  createWindow(backendPort)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow(backendPort)
    }
  })
})

app.on('window-all-closed', async () => {
  // Encerrar backend Python
  await pythonManager.stop()

  if (process.platform !== 'darwin') {
    app.quit()
  }
})
