/**
 * RSAC V2 — Electron Main Process
 * Gerencia lifecycle da aplicação, spawn do backend Python e criação da janela.
 */

import { app, BrowserWindow, shell } from 'electron'
import { existsSync, readFileSync } from 'fs'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { PythonManager } from './python-manager'
import { registerIpcHandlers } from './ipc-handlers'

const pythonManager = new PythonManager()
let mainWindow: BrowserWindow | null = null

/**
 * Identificador do modelo de usuário do Windows. Precisa ser idêntico ao
 * `appId` do electron-builder: é ele que faz a barra de tarefas, o menu
 * Iniciar e as notificações associarem a janela ao ícone instalado do app.
 */
const APP_ID = 'br.ufsc.rsac'

/** Cor de fundo da janela — mesma base da splash e dos ícones gerados. */
const BRAND_BACKGROUND = '#171f0d'

/**
 * Ícone da janela (barra de tarefas no Linux, janela em desenvolvimento).
 * No Windows empacotado quem manda é o ícone embutido no .exe pelo
 * electron-builder; aqui garantimos o mesmo símbolo nos demais casos.
 */
function resolveAppIcon(): string | undefined {
  const candidates = is.dev
    ? [join(__dirname, '../../resources/icon.png'), join(__dirname, '../../build/icon.png')]
    : [join(process.resourcesPath, 'icon.png')]
  return candidates.find(existsSync)
}

/**
 * Lê o token local gravado pelo backend em `<user_data>/runtime_token`.
 *
 * O caminho espelha o `platformdirs.user_data_dir("RSAC")` do Python — é o
 * mesmo diretório que o backend usa para o banco. Falhar aqui não é fatal: o
 * renderer cai na tela de login, que continua funcionando.
 */
function readLocalToken(): string | null {
  const candidatos =
    process.platform === 'win32'
      ? [join(process.env.LOCALAPPDATA || app.getPath('appData'), 'RSAC', 'runtime_token')]
      : process.platform === 'darwin'
        ? [join(app.getPath('home'), 'Library', 'Application Support', 'RSAC', 'runtime_token')]
        : [
            join(process.env.XDG_DATA_HOME || join(app.getPath('home'), '.local', 'share'), 'RSAC', 'runtime_token')
          ]

  for (const caminho of candidatos) {
    try {
      const conteudo = readFileSync(caminho, 'utf-8').trim()
      if (conteudo) return conteudo
    } catch {
      // Arquivo ainda não existe (primeiro start) ou é ilegível.
    }
  }
  return null
}

function createWindow(backendPort: number): void {
  const icon = resolveAppIcon()

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    show: false,
    title: 'RSAC V2',
    backgroundColor: BRAND_BACKGROUND,
    ...(icon ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      // Habilita o visualizador de PDF embutido do Chromium — é o que permite
      // ler o documento original dentro da aba de Extração, sem depender de
      // aplicativo externo nem de biblioteca de terceiros no renderer.
      plugins: true
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

  // O backend passou a exigir sessão (doc 30, Fase 1). No app de mesa a prova
  // de identidade é o token local: um arquivo que só o dono da máquina lê,
  // gravado pelo próprio backend na pasta de dados do usuário. Repassá-lo ao
  // renderer é o que mantém o desktop sem tela de login — e quem não tem
  // acesso ao sistema de arquivos do usuário não consegue produzi-lo.
  const localToken = readLocalToken()
  const query: Record<string, string> = { port: String(backendPort) }
  if (localToken) query.local_token = localToken

  const queryString = new URLSearchParams(query).toString()

  // Em dev, carrega do dev server; em prod, do arquivo HTML
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(`${process.env['ELECTRON_RENDERER_URL']}?${queryString}`)
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'), { query })
  }
}

app.whenReady().then(async () => {
  // Configurações de segurança do Electron
  electronApp.setAppUserModelId(APP_ID)

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
