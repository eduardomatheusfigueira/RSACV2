/**
 * RSAC V2 — IPC Handlers (Main Process)
 * Handlers para mensagens IPC entre Main e Renderer.
 */

import { ipcMain, dialog, app, nativeTheme, Notification, BrowserWindow } from 'electron'

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
