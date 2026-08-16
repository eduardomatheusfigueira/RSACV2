/**
 * RSAC V2 — Log Store (Zustand)
 * Gerencia o registro centralizado de eventos do sistema.
 * Toda chamada de API, WebSocket, e ação relevante é registrada aqui.
 */

import { create } from 'zustand'

export type LogLevel = 'info' | 'success' | 'warn' | 'error' | 'debug'
export type LogSource = 'API' | 'WebSocket' | 'IA' | 'Sistema' | 'Coleta' | 'Triagem' | 'Extração' | 'Exportação' | 'Protocolo'

export interface LogEntry {
  id: string
  timestamp: Date
  level: LogLevel
  source: LogSource
  message: string
  detail?: string
  duration?: number // ms
}

interface LogState {
  entries: LogEntry[]
  panelOpen: boolean
  filter: LogLevel | 'all'

  // Actions
  log: (level: LogLevel, source: LogSource, message: string, detail?: string, duration?: number) => void
  info: (source: LogSource, message: string, detail?: string) => void
  success: (source: LogSource, message: string, detail?: string, duration?: number) => void
  warn: (source: LogSource, message: string, detail?: string) => void
  error: (source: LogSource, message: string, detail?: string) => void
  debug: (source: LogSource, message: string, detail?: string) => void
  togglePanel: () => void
  setPanelOpen: (open: boolean) => void
  setFilter: (filter: LogLevel | 'all') => void
  clearLogs: () => void
}

let idCounter = 0

export const useLogStore = create<LogState>((set) => ({
  entries: [],
  panelOpen: false,
  filter: 'all',

  log: (level, source, message, detail, duration) =>
    set((state) => ({
      entries: [
        {
          id: `log-${++idCounter}-${Date.now()}`,
          timestamp: new Date(),
          level,
          source,
          message,
          detail,
          duration,
        },
        ...state.entries,
      ].slice(0, 500), // manter últimas 500 entradas
    })),

  info: (source, message, detail) =>
    set((state) => ({
      entries: [
        { id: `log-${++idCounter}-${Date.now()}`, timestamp: new Date(), level: 'info', source, message, detail },
        ...state.entries,
      ].slice(0, 500),
    })),

  success: (source, message, detail, duration) =>
    set((state) => ({
      entries: [
        { id: `log-${++idCounter}-${Date.now()}`, timestamp: new Date(), level: 'success', source, message, detail, duration },
        ...state.entries,
      ].slice(0, 500),
    })),

  warn: (source, message, detail) =>
    set((state) => ({
      entries: [
        { id: `log-${++idCounter}-${Date.now()}`, timestamp: new Date(), level: 'warn', source, message, detail },
        ...state.entries,
      ].slice(0, 500),
    })),

  error: (source, message, detail) =>
    set((state) => ({
      entries: [
        { id: `log-${++idCounter}-${Date.now()}`, timestamp: new Date(), level: 'error', source, message, detail },
        ...state.entries,
      ].slice(0, 500),
    })),

  debug: (source, message, detail) =>
    set((state) => ({
      entries: [
        { id: `log-${++idCounter}-${Date.now()}`, timestamp: new Date(), level: 'debug', source, message, detail },
        ...state.entries,
      ].slice(0, 500),
    })),

  togglePanel: () => set((state) => ({ panelOpen: !state.panelOpen })),
  setPanelOpen: (panelOpen) => set({ panelOpen }),
  setFilter: (filter) => set({ filter }),
  clearLogs: () => set({ entries: [] }),
}))
