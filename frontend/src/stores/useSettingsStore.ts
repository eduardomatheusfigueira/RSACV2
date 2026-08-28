/**
 * Revsist — Settings & Project Store (Zustand + localStorage Persistence)
 * Persiste preferências do usuário (tema, modo IA, projeto ativo) no localStorage,
 * para que sobrevivam a recarregamentos de página e reinícios do app.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Project } from '@/types/api'

export type ThemeId =
  | 'dark'
  | 'light'
  | 'lava-steel'
  | 'pastel-dream'
  | 'stormy-tangerine'
  | 'platinum-dusk'

interface SettingsState {
  theme: string
  backendStatus: 'connecting' | 'online' | 'offline'
  backendVersion: string
  activeProject: Project | null
  aiEnabled: boolean
  /**
   * Toolstrip do ribbon recolhido. Persiste porque a escolha é sobre COMO a
   * pessoa quer trabalhar, não sobre o que está fazendo agora: quem recolhe a
   * faixa quer a tela para o texto, e reabri-la a cada troca de rota desfaz a
   * decisão sem que ninguém tenha pedido. Recolhido, o Estúdio de Protocolo
   * sai de 29% de moldura para 20%.
   */
  ribbonCollapsed: boolean

  // Actions
  setTheme: (theme: string) => void
  toggleTheme: () => void
  setBackendStatus: (status: 'connecting' | 'online' | 'offline') => void
  setBackendVersion: (version: string) => void
  setActiveProject: (project: Project | null) => void
  setAiEnabled: (enabled: boolean) => void
  setRibbonCollapsed: (collapsed: boolean) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'platinum-dusk',
      backendStatus: 'connecting',
      backendVersion: '',
      activeProject: null,
      aiEnabled: true,
      ribbonCollapsed: false,

      setTheme: (theme) => {
        document.documentElement.setAttribute('data-theme', theme)
        set({ theme })
      },

      toggleTheme: () =>
        set((state) => {
          const isDark =
            state.theme === 'dark' ||
            state.theme === 'organic-dark' ||
            state.theme === 'lava-steel' ||
            state.theme === 'stormy-tangerine' ||
            state.theme === 'platinum-dusk'
          const newTheme = isDark ? 'light' : 'platinum-dusk'
          document.documentElement.setAttribute('data-theme', newTheme)
          return { theme: newTheme }
        }),

      setBackendStatus: (backendStatus) => set({ backendStatus }),
      setBackendVersion: (backendVersion) => set({ backendVersion }),
      setActiveProject: (activeProject) => set({ activeProject }),
      setAiEnabled: (aiEnabled) => set({ aiEnabled }),
      setRibbonCollapsed: (ribbonCollapsed) => set({ ribbonCollapsed }),
    }),
    {
      name: 'rsac-v2-settings',
      // Persistir apenas as preferências do usuário, não o estado de runtime (backend status/version)
      partialize: (state) => ({
        theme: state.theme,
        aiEnabled: state.aiEnabled,
        activeProject: state.activeProject,
        ribbonCollapsed: state.ribbonCollapsed,
      }),
      // Ao reidratar do localStorage, aplicar o tema salvo ao DOM imediatamente
      onRehydrateStorage: () => {
        return (state) => {
          const activeTheme = state?.theme || 'platinum-dusk'
          document.documentElement.setAttribute('data-theme', activeTheme)
        }
      },
    }
  )
)
