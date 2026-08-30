/**
 * Revsist — Store Zustand do Modo Trilho (Tutor Metodológico)
 * Gerenciamento de estado determinístico da jornada metodológica (Doc 46).
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { TRILHO_GRAPH, TRILHO_PHASES, type TrilhoNode, type TrilhoBranchOption } from '@/data/trilhoGraph'

interface TrilhoState {
  isActive: boolean
  isMinimized: boolean
  currentNodeId: string
  completedNodes: string[]
  decisionHistory: Record<string, string> // nodeId -> optionId
  isDecisionModalOpen: boolean

  // Ações
  startTrilho: (startNodeId?: string) => void
  stopTrilho: () => void
  toggleTrilho: () => void
  goToNode: (nodeId: string) => void
  goToNext: () => void
  goToPrevious: () => void
  openDecisionModal: () => void
  closeDecisionModal: () => void
  chooseBranch: (option: TrilhoBranchOption) => void
  toggleMinimized: () => void
  resetTrilho: () => void

  // Getters computados
  getCurrentNode: () => TrilhoNode
  getCurrentPhaseInfo: () => { phase: number; name: string; shortName: string; totalPhases: number }
  getProgressPercentage: () => number
}

const DEFAULT_START_NODE = 'intro_welcome'

export const useTrilhoStore = create<TrilhoState>()(
  persist(
    (set, get) => ({
      isActive: false,
      isMinimized: false,
      currentNodeId: DEFAULT_START_NODE,
      completedNodes: [],
      decisionHistory: {},
      isDecisionModalOpen: false,

      startTrilho: (startNodeId) => {
        const targetNode = startNodeId && TRILHO_GRAPH[startNodeId] ? startNodeId : get().currentNodeId || DEFAULT_START_NODE
        set({
          isActive: true,
          isMinimized: false,
          currentNodeId: targetNode,
        })
      },

      stopTrilho: () => {
        set({
          isActive: false,
          isDecisionModalOpen: false,
        })
      },

      toggleTrilho: () => {
        const current = get().isActive
        set({
          isActive: !current,
          isDecisionModalOpen: false,
        })
      },

      goToNode: (nodeId) => {
        if (!TRILHO_GRAPH[nodeId]) return
        const completed = Array.from(new Set([...get().completedNodes, get().currentNodeId]))
        const node = TRILHO_GRAPH[nodeId]

        set({
          currentNodeId: nodeId,
          completedNodes: completed,
          isDecisionModalOpen: !!node.branchingQuestion,
        })
      },

      goToNext: () => {
        const current = get().getCurrentNode()
        if (current.branchingQuestion) {
          // Se for nó de bifurcação, abre o modal de tomada de decisão
          set({ isDecisionModalOpen: true })
          return
        }

        if (current.nextNodeId && TRILHO_GRAPH[current.nextNodeId]) {
          get().goToNode(current.nextNodeId)
        }
      },

      goToPrevious: () => {
        const current = get().getCurrentNode()
        if (current.previousNodeId && TRILHO_GRAPH[current.previousNodeId]) {
          set({
            currentNodeId: current.previousNodeId,
            isDecisionModalOpen: !!TRILHO_GRAPH[current.previousNodeId].branchingQuestion,
          })
        }
      },

      openDecisionModal: () => {
        set({ isDecisionModalOpen: true })
      },

      closeDecisionModal: () => {
        set({ isDecisionModalOpen: false })
      },

      chooseBranch: (option: TrilhoBranchOption) => {
        const currentNodeId = get().currentNodeId
        const history = { ...get().decisionHistory, [currentNodeId]: option.id }
        const completed = Array.from(new Set([...get().completedNodes, currentNodeId]))

        set({
          decisionHistory: history,
          completedNodes: completed,
          currentNodeId: option.nextNodeId,
          isDecisionModalOpen: false,
        })
      },

      toggleMinimized: () => {
        set((state) => ({ isMinimized: !state.isMinimized }))
      },

      resetTrilho: () => {
        set({
          currentNodeId: DEFAULT_START_NODE,
          completedNodes: [],
          decisionHistory: {},
          isDecisionModalOpen: false,
        })
      },

      getCurrentNode: () => {
        const id = get().currentNodeId
        return TRILHO_GRAPH[id] || TRILHO_GRAPH[DEFAULT_START_NODE]
      },

      getCurrentPhaseInfo: () => {
        const node = get().getCurrentNode()
        const phaseInfo = TRILHO_PHASES.find((p) => p.phase === node.phase) || TRILHO_PHASES[0]
        return {
          ...phaseInfo,
          totalPhases: TRILHO_PHASES.length,
        }
      },

      getProgressPercentage: () => {
        const node = get().getCurrentNode()
        const phase = node.phase
        const maxPhase = TRILHO_PHASES.length - 1
        return Math.min(100, Math.round((phase / maxPhase) * 100))
      },
    }),
    {
      name: 'revsist_trilho_state_v1',
      partialize: (state) => ({
        isActive: state.isActive,
        currentNodeId: state.currentNodeId,
        completedNodes: state.completedNodes,
        decisionHistory: state.decisionHistory,
        isMinimized: state.isMinimized,
      }),
    }
  )
)
