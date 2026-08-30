/**
 * Revsist — Hook de Canal de Colaboração e Presença em Tempo Real (Doc 43 §43.12, Fase 3)
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { api } from '@/api/client'

export interface ActiveUserPresence {
  user_id: string
  username: string
  screen: string
  connected_at: string
}

export interface ProjectChannelOptions {
  projectId: string | undefined
  screen?: string
  onPaperDecided?: (data: {
    paper_id: string
    decision: string
    por: string
    updated_at?: string
  }) => void
  onProtocolChanged?: (data: {
    secao: string
    por: string
    updated_at?: string
  }) => void
  onHarvestCompleted?: (data: {
    run_id: string
    source?: string
    por?: string
    novos?: number
    encontrados?: number
  }) => void
  onTeamChanged?: (data: { user_id: string; acao: string }) => void
  onPresenceUpdate?: (activeUsers: ActiveUserPresence[]) => void
}

export function useProjectChannel({
  projectId,
  screen = 'geral',
  onPaperDecided,
  onProtocolChanged,
  onHarvestCompleted,
  onTeamChanged,
  onPresenceUpdate,
}: ProjectChannelOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const [activeUsers, setActiveUsers] = useState<ActiveUserPresence[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<any>(null)

  const callbacksRef = useRef({
    onPaperDecided,
    onProtocolChanged,
    onHarvestCompleted,
    onTeamChanged,
    onPresenceUpdate,
  })

  useEffect(() => {
    callbacksRef.current = {
      onPaperDecided,
      onProtocolChanged,
      onHarvestCompleted,
      onTeamChanged,
      onPresenceUpdate,
    }
  }, [onPaperDecided, onProtocolChanged, onHarvestCompleted, onTeamChanged, onPresenceUpdate])

  useEffect(() => {
    if (!projectId) return

    let isSubscribed = true

    const connectWs = () => {
      const baseUrl = api.getBaseUrl()
      // Converte http:// ou https:// para ws:// ou wss://
      const wsProto = baseUrl.startsWith('https') ? 'wss' : 'ws'
      const hostPath = baseUrl.replace(/^https?:\/\//, '').replace(/\/$/, '')
      const token = api.getSessionToken()
      const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : ''
      const url = `${wsProto}://${hostPath}/projects/${projectId}/ws${tokenQuery}`

      try {
        const ws = new WebSocket(url)
        wsRef.current = ws

        ws.onopen = () => {
          if (!isSubscribed) return
          setIsConnected(true)
          ws.send(JSON.stringify({ type: 'presenca', tela: screen }))
        }

        ws.onmessage = (evt) => {
          if (!isSubscribed) return
          if (evt.data === 'pong') return
          try {
            const msg = JSON.parse(evt.data)
            if (msg.type === 'presenca') {
              if (Array.isArray(msg.active_users)) {
                setActiveUsers(msg.active_users)
                callbacksRef.current.onPresenceUpdate?.(msg.active_users)
              }
            } else if (msg.type === 'paper.decidido') {
              callbacksRef.current.onPaperDecided?.(msg)
            } else if (msg.type === 'protocolo.alterado') {
              callbacksRef.current.onProtocolChanged?.(msg)
            } else if (
              msg.type === 'coleta.concluida' ||
              msg.type === 'harvest_source_completed' ||
              msg.type === 'harvest_all_completed'
            ) {
              callbacksRef.current.onHarvestCompleted?.(msg)
            } else if (msg.type === 'equipe.alterada') {
              callbacksRef.current.onTeamChanged?.(msg)
            }
          } catch {
            // Mensagem não-JSON ignorada
          }
        }

        ws.onclose = () => {
          if (!isSubscribed) return
          setIsConnected(false)
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isSubscribed) connectWs()
          }, 3000)
        }

        ws.onerror = () => {
          ws.close()
        }
      } catch (err) {
        console.warn('[useProjectChannel] Falha ao abrir WebSocket:', err)
      }
    }

    connectWs()

    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 25000)

    return () => {
      isSubscribed = false
      clearInterval(pingInterval)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [projectId, screen])

  const sendPresence = useCallback((newScreen: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'presenca', tela: newScreen }))
    }
  }, [])

  return {
    isConnected,
    activeUsers,
    sendPresence,
  }
}
