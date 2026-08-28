/**
 * Revsist — Auth Store (Zustand, sem persistência)
 *
 * Guarda a identidade da sessão corrente. Não usa o middleware `persist` de
 * propósito: quem persiste a sessão é o backend (cookie `HttpOnly`) e, no caso
 * de origem diferente, o `sessionStorage` gerido pelo cliente HTTP. Duplicar
 * isso aqui criaria uma segunda fonte da verdade que poderia dizer
 * "autenticado" depois de o servidor já ter revogado a sessão.
 */

import { create } from 'zustand'
import { api } from '@/api/client'
import type { AuthStatus, AuthUser } from '@/types/api'

/**
 * `checking` é um estado real, não um detalhe: antes de saber se há sessão a
 * aplicação não pode nem mostrar a tela de login (piscaria para quem já está
 * autenticado) nem o conteúdo (piscaria dado para quem não está).
 */
type AuthPhase = 'checking' | 'authenticated' | 'anonymous' | 'unavailable'

interface AuthState {
  phase: AuthPhase
  user: AuthUser | null
  status: AuthStatus | null
  error: string | null
  submitting: boolean

  bootstrap: () => Promise<void>
  login: (username: string, password: string) => Promise<boolean>
  loginWithLocalToken: (token: string) => Promise<boolean>
  logout: () => Promise<void>
  setError: (message: string | null) => void
  markAnonymous: () => void
}

/**
 * Token local passado pelo Electron ou pelo lançador local via query string.
 * É lido uma vez e removido da URL logo em seguida, para não ficar no
 * histórico do navegador nem em algum print de tela.
 */
function consumeLocalTokenFromUrl(): string | null {
  if (typeof window === 'undefined') return null
  try {
    const busca = new URLSearchParams(window.location.search)
    let token = busca.get('local_token')

    if (!token && window.location.hash.includes('?')) {
      const hashParams = new URLSearchParams(window.location.hash.split('?')[1])
      token = hashParams.get('local_token')
    }
    if (!token) return null

    const limpa = new URL(window.location.href)
    limpa.searchParams.delete('local_token')
    if (limpa.hash.includes('local_token')) {
      limpa.hash = limpa.hash.replace(/([?&])local_token=[^&]*/, '$1').replace(/[?&]$/, '')
    }
    window.history.replaceState({}, document.title, limpa.toString())

    return token
  } catch {
    return null
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  phase: 'checking',
  user: null,
  status: null,
  error: null,
  submitting: false,

  /**
   * Decide, na partida, entre entrar direto e pedir credenciais.
   *
   * Ordem: sessão já válida → token local do app de mesa → tela de login.
   */
  bootstrap: async () => {
    try {
      let status: import('@/types/api').AuthStatus
      try {
        status = await api.getAuthStatus()
      } catch (err) {
        // Recuar para o backend local: útil quando o túnel salvo expirou e o
        // servidor está na própria máquina.
        const eraRemoto =
          !api.getBaseUrl().includes('127.0.0.1') && !api.getBaseUrl().includes('localhost')
        if (eraRemoto && api.podeAlcancarLoopback()) {
          console.warn('[Auth] Falha ao conectar na URL remota configurada, tentando localhost:8000...')
          api.setBaseUrl('http://127.0.0.1:8000/api/v1')
          status = await api.getAuthStatus()
        } else {
          throw err
        }
      }
      set({ status })

      if (status.authenticated && status.user) {
        set({ phase: 'authenticated', user: status.user, error: null })
        return
      }

      const tokenDaUrl = consumeLocalTokenFromUrl()
      if (tokenDaUrl) {
        const entrou = await get().loginWithLocalToken(tokenDaUrl)
        if (entrou) return
      }

      set({ phase: 'anonymous', user: null })
    } catch {
      // Backend fora do ar é diferente de sessão ausente: mostrar a tela de
      // login aqui faria o usuário digitar a senha contra um servidor que não
      // responde, e concluir que a senha está errada.
      set({ phase: 'unavailable', user: null })
    }
  },

  login: async (username, password) => {
    set({ submitting: true, error: null })
    try {
      const res = await api.login(username, password)
      set({ phase: 'authenticated', user: res.user, error: null, submitting: false })
      return true
    } catch (err: any) {
      set({ error: err?.message || 'Não foi possível entrar.', submitting: false })
      return false
    }
  },

  loginWithLocalToken: async (token) => {
    try {
      const res = await api.loginWithLocalToken(token)
      set({ phase: 'authenticated', user: res.user, error: null })
      return true
    } catch {
      // Silencioso de propósito: no perfil servidor o token local não é aceito,
      // e a falha aqui apenas leva à tela de login normal.
      return false
    }
  },

  logout: async () => {
    try {
      await api.logout()
    } finally {
      set({ phase: 'anonymous', user: null, error: null })
    }
  },

  setError: (message) => set({ error: message }),

  markAnonymous: () => set({ phase: 'anonymous', user: null }),
}))
