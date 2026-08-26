/**
 * RSAC V2 — IPC Handlers (Main Process)
 * Handlers para mensagens IPC entre Main e Renderer.
 */

import { ipcMain, dialog, app, nativeTheme, Notification, BrowserWindow } from 'electron'

/**
 * O que a interface precisa saber sobre o backend para falar com ele.
 *
 * `porta` nula significa que o backend não subiu — e a interface trata isso
 * como diagnóstico de conexão, não como espera indefinida.
 */
export interface InfoDoBackend {
  porta: number | null
  tokenLocal: string | null
  erro?: string
}

/**
 * Abre o canal pelo qual a interface pergunta onde está o backend.
 *
 * É `handle`, e não `send`, de propósito: o backend pode ficar pronto antes de
 * o renderer existir, e um evento disparado nesse intervalo se perderia. Aqui
 * a interface pergunta quando quiser e a resposta espera pela promessa —
 * quem chega tarde recebe o valor já resolvido, quem chega cedo aguarda.
 *
 * O token local sai por este canal, e só por ele: passá-lo na URL, como faz o
 * lançador do navegador, o deixaria no histórico e em qualquer captura de tela
 * da janela.
 */
export function registrarPonteDoBackend(obterInfo: () => Promise<InfoDoBackend>): void {
  ipcMain.handle('backend:info', () => obterInfo())
}

export function registerIpcHandlers(): void {
  // ── Informações do Sistema ──────────────────────────────────────────

  ipcMain.handle('app:version', () => {
    return app.getVersion()
  })

  ipcMain.handle('app:platform', () => {
    return process.platform
  })

  // ── Diálogos Nativos ────────────────────────────────────────────────

  ipcMain.handle('dialog:open', async (_event, options: Electron.OpenDialogOptions) => {
    return dialog.showOpenDialog(options)
  })

  ipcMain.handle('dialog:save', async (_event, options: Electron.SaveDialogOptions) => {
    return dialog.showSaveDialog(options)
  })

  // ── Sistema de Arquivos ─────────────────────────────────────────────

  ipcMain.handle('fs:selectPDFDirectory', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory'],
      title: 'Selecionar pasta de PDFs',
    })
    return result.canceled ? null : result.filePaths[0]
  })

  // ── Notificações ────────────────────────────────────────────────────

  ipcMain.handle('notification:show', (_event, { title, body }: { title: string; body: string }) => {
    if (Notification.isSupported()) {
      new Notification({ title, body }).show()
    }
  })

  // ── Tema do Sistema ─────────────────────────────────────────────────

  ipcMain.handle('theme:system', () => {
    return nativeTheme.shouldUseDarkColors ? 'dark' : 'light'
  })

  // Notificar renderer quando tema do sistema mudar
  nativeTheme.on('updated', () => {
    const windows = BrowserWindow.getAllWindows()
    const theme = nativeTheme.shouldUseDarkColors ? 'dark' : 'light'
    windows.forEach((win) => {
      win.webContents.send('theme:changed', theme)
    })
  })
}
