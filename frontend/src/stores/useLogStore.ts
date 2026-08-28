/**
 * Revsist — Log Store (Zustand)
 * Gerencia o registro centralizado de eventos do sistema.
 * Toda chamada de API, WebSocket, e ação relevante é registrada aqui.
 *
 * O painel de logs fica FECHADO por padrão. Enquanto ele era o único destino
 * dos erros, uma falha ao registrar decisão de triagem ou ao salvar o protocolo
 * não produzia sinal nenhum na tela — a ação simplesmente não acontecia. Nível
 * `error` agora também levanta um aviso do sonner, que é anunciado por leitor
 * de tela e não depende do painel estar aberto.
 */

import { create } from 'zustand'
import { toast } from '@/components/ui/Toaster'

export type LogLevel = 'info' | 'success' | 'warn' | 'error' | 'debug'
export type LogSource = 'API' | 'WebSocket' | 'Assistência' | 'IA' | 'Sistema' | 'Coleta' | 'Triagem' | 'Extração' | 'Exportação' | 'Protocolo' | 'Deduplicação'

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

const MAX_ENTRIES = 500

function novaEntrada(
  level: LogLevel,
  source: LogSource,
  message: string,
  detail?: string,
  duration?: number
): LogEntry {
  return {
    id: `log-${++idCounter}-${Date.now()}`,
    timestamp: new Date(),
    level,
    source,
    message,
    detail,
    duration,
  }
}

/**
 * Fontes de diagnóstico. Uma falha de rede produz DUAS entradas aqui ("erro de
 * rede" e "falhou (500)"), ambas em linguagem de protocolo — "DELETE
 * /projects/<uuid> falhou (500)" não é recado para quem está triando artigos.
 * Elas ficam no painel; quem fala com a pessoa é a camada de domínio.
 */
const FONTES_DE_DIAGNOSTICO: ReadonlySet<LogSource> = new Set<LogSource>(['API', 'WebSocket'])

/**
 * Só `error` vira aviso na tela. `info` é emitido a cada tique do progresso da
 * triagem em lote — transformá-lo em aviso encheria o canto da janela de
 * cartões idênticos. O `id` estável faz o sonner substituir o aviso anterior em
 * vez de empilhar quando a mesma falha se repete.
 */
function avisa(level: LogLevel, source: LogSource, message: string, detail?: string): void {
  if (level !== 'error' || FONTES_DE_DIAGNOSTICO.has(source)) return
  toast.error(message, {
    description: detail,
    id: `log-${source}-${message}`,
  })
}

export const useLogStore = create<LogState>((set) => {
  const registra = (
    level: LogLevel,
    source: LogSource,
    message: string,
    detail?: string,
    duration?: number
  ) => {
    avisa(level, source, message, detail)
    set((state) => ({
      entries: [novaEntrada(level, source, message, detail, duration), ...state.entries].slice(
        0,
        MAX_ENTRIES
      ),
    }))
  }

  return {
    entries: [],
    panelOpen: false,
    filter: 'all',

    log: registra,
    info: (source, message, detail) => registra('info', source, message, detail),
    success: (source, message, detail, duration) =>
      registra('success', source, message, detail, duration),
    warn: (source, message, detail) => registra('warn', source, message, detail),
    error: (source, message, detail) => registra('error', source, message, detail),
    debug: (source, message, detail) => registra('debug', source, message, detail),

    togglePanel: () => set((state) => ({ panelOpen: !state.panelOpen })),
    setPanelOpen: (panelOpen) => set({ panelOpen }),
    setFilter: (filter) => set({ filter }),
    clearLogs: () => set({ entries: [] }),
  }
})
