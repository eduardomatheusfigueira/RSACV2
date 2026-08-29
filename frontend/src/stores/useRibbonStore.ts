/**
 * Revsist — Ribbon Action & State Store (Zustand)
 * Desacopla o TopRibbonBar do DOM, substituindo clickDomByText, clickDom e clickDomByIndex
 * por registro declarativo e despacho direto de funções tipadas por página.
 */

import { create } from 'zustand'

export interface RibbonActionMap {
  // Arquivo / Projetos
  createProject?: () => void

  // Protocolo
  saveProtocol?: () => void
  copyManuscript?: () => void
  openAiSuggest?: () => void
  setStudioTab?: (tabIndex: number) => void
  activeStudioTabIndex?: number
  isProtocolSaving?: boolean

  // Coleta
  startHarvest?: () => void
  stopHarvest?: () => void
  isHarvesting?: boolean
  openImportRis?: () => void
  openDedupModal?: () => void

  // Triagem 1
  decisionInclude?: () => void
  decisionExclude?: () => void
  decisionPending?: () => void
  screenAiSingle?: () => void
  screenAiBatch?: () => void
  stopBatchScreening?: () => void
  isBatchScreening?: boolean
  batchScreeningProgressText?: string
  openDoiOrRepoLink?: () => void
  hasDoiOrRepo?: boolean
  setDecisionFilter?: (filter: string) => void
  activeDecisionFilter?: string
  canScreenSingle?: boolean

  // Extração / Triagem 2
  saveExtraction?: () => void
  extractAiGlobal?: () => void
  downloadPdf?: () => void
  openDoiLink?: () => void
  hasPdf?: boolean
  hasDoi?: boolean
  isExtractionSaving?: boolean

  // Exportação
  exportExcel?: () => void
  exportBibtex?: () => void

  // Ferramentas / Configurações
  testConnection?: () => void
  saveSettings?: () => void
  isTestingSettings?: boolean
  isSavingSettings?: boolean
}

interface RibbonState {
  actions: RibbonActionMap
  registerActions: (actions: Partial<RibbonActionMap>) => void
  unregisterActions: (keys: (keyof RibbonActionMap)[]) => void
  clearActions: () => void
}

export const useRibbonStore = create<RibbonState>((set) => ({
  actions: {},
  registerActions: (newActions) =>
    set((state) => ({
      actions: { ...state.actions, ...newActions },
    })),
  unregisterActions: (keys) =>
    set((state) => {
      const remaining = { ...state.actions }
      for (const k of keys) {
        delete remaining[k]
      }
      return { actions: remaining }
    }),
  clearActions: () => set({ actions: {} }),
}))
