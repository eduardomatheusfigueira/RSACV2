/**
 * RSAC V2 — Preload Script (Context Bridge)
 * Expõe APIs seguras do Node.js para o Renderer Process via contextBridge.
 */

import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

// API customizada exposta ao renderer
const rsacAPI = {
  // ── Informações do Sistema ──────────────────────────────────────────
  getAppVersion: (): Promise<string> =>
    ipcRenderer.invoke('app:version'),

  getPlatform: (): Promise<string> =>
    ipcRenderer.invoke('app:platform'),

  // ── Diálogos Nativos ────────────────────────────────────────────────
  showOpenDialog: (options: Electron.OpenDialogOptions): Promise<Electron.OpenDialogReturnValue> =>
    ipcRenderer.invoke('dialog:open', options),

  showSaveDialog: (options: Electron.SaveDialogOptions): Promise<Electron.SaveDialogReturnValue> =>
    ipcRenderer.invoke('dialog:save', options),

  // ── Sistema de Arquivos ─────────────────────────────────────────────
  selectPDFDirectory: (): Promise<string | null> =>
    ipcRenderer.invoke('fs:selectPDFDirectory'),

  // ── Notificações ────────────────────────────────────────────────────
  showNotification: (title: string, body: string): Promise<void> =>
    ipcRenderer.invoke('notification:show', { title, body }),

  // ── Tema do Sistema ─────────────────────────────────────────────────
  getSystemTheme: (): Promise<'dark' | 'light'> =>
    ipcRenderer.invoke('theme:system'),

  onThemeChanged: (callback: (theme: 'dark' | 'light') => void): void => {
    ipcRenderer.on('theme:changed', (_event, theme) => callback(theme))
  }
}

// Expor APIs ao renderer
if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('rsacAPI', rsacAPI)
  } catch (error) {
    console.error('Erro ao expor APIs via contextBridge:', error)
  }
} else {
  // @ts-ignore - fallback para testes
  window.electron = electronAPI
  // @ts-ignore
  window.rsacAPI = rsacAPI
}
