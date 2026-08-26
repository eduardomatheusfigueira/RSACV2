/**
 * RSAC V2 — Estado do acesso local (Zustand, sem persistência)
 *
 * Guarda se esta janela consegue falar com o backend desta instalação. Era um
 * store de sessão — com login, logout, usuário corrente e papéis — e encolheu
 * junto com as contas: sem publicação por túnel, a credencial é o arquivo
 * `runtime_token`, que o processo principal do Electron lê e entrega por IPC.
 *
 * Sem persistência, de propósito: quem sabe o token é o Electron, e ele o
 * entrega de novo a cada partida. Guardar uma cópia aqui criaria uma segunda
 * fonte da verdade capaz de discordar do arquivo em disco.
 */

import { create } from 'zustand'
import { api } from '@/api/client'
import type { AuthStatus } from '@/types/api'

/**
 * `checking` é um estado real, não um detalhe: antes de saber se o backend
 * responde, a aplicação não pode mostrar nem o conteúdo (piscaria dado que
 * talvez não carregue) nem o diagnóstico de conexão (acusaria uma falha que
 * talvez não exista).
 */
type AuthPhase = 'checking' | 'ready' | 'unavailable'

interface AuthState {
  phase: AuthPhase
  status: AuthStatus | null

  definirTokenLocal: (token: string | null) => void
  bootstrap: () => Promise<void>
  marcarIndisponivel: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  phase: 'checking',
  status: null,

  /** Recebe o token local do processo principal e o entrega ao cliente HTTP. */
  definirTokenLocal: (token) => api.setLocalToken(token),

  /**
   * Confere, na partida, se o backend responde e aceita a credencial.
   *
   * Um token recusado e um backend fora do ar levam à mesma tela — e é o
   * certo: nos dois casos o que o usuário pode fazer é reiniciar o aplicativo
   * ou apontar para outro endereço. A distinção que importa está no texto, e
   * vem de `local_token_disponivel` no corpo da resposta.
   */
  bootstrap: async () => {
    try {
      const status = await api.getAuthStatus()
      set({ status, phase: status.authenticated ? 'ready' : 'unavailable' })
    } catch {
      set({ status: null, phase: 'unavailable' })
    }
  },

  marcarIndisponivel: () => set({ phase: 'unavailable' }),
}))
