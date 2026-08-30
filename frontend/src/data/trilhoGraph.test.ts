import { describe, it, expect } from 'vitest'
import { TRILHO_GRAPH, TRILHO_PHASES } from './trilhoGraph'

describe('Modo Trilho — Validação Estrutural do Grafo (Doc 46)', () => {
  it('deve possuir todas as 8 fases (0 a 7) configuradas', () => {
    expect(TRILHO_PHASES).toHaveLength(8)
    TRILHO_PHASES.forEach((p, idx) => {
      expect(p.phase).toBe(idx)
      expect(p.name).toBeTruthy()
      expect(p.shortName).toBeTruthy()
    })
  })

  it('deve possuir o nó de entrada intro_welcome', () => {
    const startNode = TRILHO_GRAPH['intro_welcome']
    expect(startNode).toBeDefined()
    expect(startNode.phase).toBe(0)
    expect(startNode.nextNodeId).toBe('decision_review_goal')
  })

  it('todos os nós do grafo devem ter campos essenciais preenchidos', () => {
    const nodeIds = Object.keys(TRILHO_GRAPH)
    expect(nodeIds.length).toBeGreaterThanOrEqual(10)

    for (const id of nodeIds) {
      const node = TRILHO_GRAPH[id]
      expect(node.id).toBe(id)
      expect(node.phase).toBeGreaterThanOrEqual(0)
      expect(node.phase).toBeLessThanOrEqual(7)
      expect(node.title).toBeTruthy()
      expect(node.instruction).toBeTruthy()
      expect(node.rationale).toBeTruthy()
      expect(node.guidelineReference).toBeTruthy()
    }
  })

  it('todas as transições de nextNodeId e previousNodeId devem apontar para nós existentes', () => {
    for (const [id, node] of Object.entries(TRILHO_GRAPH)) {
      if (node.nextNodeId) {
        expect(
          TRILHO_GRAPH[node.nextNodeId],
          `Nó ${id} possui nextNodeId inválido: ${node.nextNodeId}`
        ).toBeDefined()
      }

      if (node.previousNodeId) {
        expect(
          TRILHO_GRAPH[node.previousNodeId],
          `Nó ${id} possui previousNodeId inválido: ${node.previousNodeId}`
        ).toBeDefined()
      }
    }
  })

  it('todas as bifurcações (branchingQuestions) devem ser válidas e determinísticas', () => {
    for (const [id, node] of Object.entries(TRILHO_GRAPH)) {
      if (node.branchingQuestion) {
        const { questionText, options } = node.branchingQuestion
        expect(questionText).toBeTruthy()
        expect(options.length).toBeGreaterThanOrEqual(2)

        for (const opt of options) {
          expect(opt.id).toBeTruthy()
          expect(opt.label).toBeTruthy()
          expect(opt.description).toBeTruthy()
          expect(opt.example).toBeTruthy()
          expect(opt.consequences).toBeTruthy()
          expect(
            TRILHO_GRAPH[opt.nextNodeId],
            `Bifurcação em ${id} (opção ${opt.id}) aponta para nextNodeId inexistente: ${opt.nextNodeId}`
          ).toBeDefined()
        }
      }
    }
  })
})
