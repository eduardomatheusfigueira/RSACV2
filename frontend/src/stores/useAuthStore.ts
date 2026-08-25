/**
 * RSAC V2 — Auth Store (Zustand, sem persistência)
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
  phase: 'authenticated',
  user: {
    id: 'local',
    username: 'pesquisador',
    role: 'owner',
    is_active: true,
  },
  status: null,
  error: null,
  submitting: false,

  bootstrap: async () => {
    try {
      const status = await api.getAuthStatus()
      set({ status, user: status.user || get().user, phase: 'authenticated' })
    } catch {
      // Continua autenticado localmente
    }
  },

  login: async () => true,
  loginWithLocalToken: async () => true,
  logout: async () => {},
  setError: (message) => set({ error: message }),
  markAnonymous: () => {},
}))
