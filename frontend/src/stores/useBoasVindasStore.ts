/**
 * Revsist — Estado das boas-vindas.
 *
 * Guarda uma coisa só: se esta pessoa, neste navegador, já viu a apresentação.
 * O que substituiu o Modo Trilho não é outro tutor que acompanha o trabalho —
 * é o que todo aplicativo faz na primeira vez: conta o que existe, mostra por
 * onde começar e sai do caminho.
 *
 * A visita fica por conta, e não global: num computador compartilhado de
 * laboratório, o segundo pesquisador a entrar merece a mesma apresentação que
 * o primeiro recebeu, e não a tela de quem já conhece o produto.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface BoasVindasState {
  /** Está aberta agora? Não é persistido — a janela abre por decisão, não por memória. */
  aberta: boolean
  /** Contas que já viram, por `username`. */
  jaViram: string[]

  abrir: () => void
  fechar: () => void
  /** Abre se esta conta ainda não viu; devolve se abriu. */
  abrirSePrimeiraVez: (username: string) => boolean
  marcarComoVista: (username: string) => void
}

export const useBoasVindasStore = create<BoasVindasState>()(
  persist(
    (set, get) => ({
      aberta: false,
      jaViram: [],

      abrir: () => set({ aberta: true }),
      fechar: () => set({ aberta: false }),

      abrirSePrimeiraVez: (username) => {
        if (!username || get().jaViram.includes(username)) return false
        set({ aberta: true })
        return true
      },

      marcarComoVista: (username) => {
        if (!username) return
        set((s) =>
          s.jaViram.includes(username) ? s : { ...s, jaViram: [...s.jaViram, username] }
        )
      },
    }),
    {
      name: 'rsac_boas_vindas',
      // `aberta` fica de fora: persistida, uma aba fechada no meio da
      // apresentação faria a janela reaparecer sozinha no próximo acesso,
      // como se o aplicativo tivesse insistido.
      partialize: (s) => ({ jaViram: s.jaViram }),
    }
  )
)
