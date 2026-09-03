/**
 * Revsist — Modal de Bifurcação Metodológica do Modo Trilho
 * Apresenta alternativas determinísticas A vs B para tomada de decisão (Doc 46).
 */

import React from 'react'
import { GitBranch, Check, X, ArrowRight, BookOpen } from 'lucide-react'
import { useTrilhoStore } from '@/stores/useTrilhoStore'
import { Badge, Button } from '@/components/ui'
import type { TrilhoBranchOption } from '@/data/trilhoGraph'
import './Trilho.css'

interface TrilhoDecisionModalProps {
  onApplyActionPayload?: (payload: TrilhoBranchOption['actionPayload']) => Promise<void> | void
}

export function TrilhoDecisionModal({ onApplyActionPayload }: TrilhoDecisionModalProps): JSX.Element | null {
  const { isDecisionModalOpen, closeDecisionModal, getCurrentNode, chooseBranch } = useTrilhoStore()
  const currentNode = getCurrentNode()

  if (!isDecisionModalOpen || !currentNode?.branchingQuestion) {
    return null
  }

  const { questionText, helpContext, options } = currentNode.branchingQuestion

  const handleSelectOption = async (option: TrilhoBranchOption) => {
    if (option.actionPayload && onApplyActionPayload) {
      await onApplyActionPayload(option.actionPayload)
    }
    chooseBranch(option)
  }

  return (
    <div className="trilho-decision-overlay" role="dialog" aria-modal="true" aria-labelledby="trilho-decision-title">
      <div className="trilho-decision-modal">
        {/* Cabeçalho */}
        <div className="trilho-decision-header">
          <h3 id="trilho-decision-title">
            <GitBranch size={18} className="icon-accent" aria-hidden="true" />
            <span>Decisão Metodológica — {currentNode.title}</span>
          </h3>
          <button
            type="button"
            className="trilho-btn-icon"
            onClick={closeDecisionModal}
            aria-label="Fechar janela de decisão"
            title="Fechar"
          >
            <X size={16} />
          </button>
        </div>

        {/* Corpo com Pergunta e Grade de Opções */}
        <div className="trilho-decision-body">
          <div>
            <p className="trilho-decision-prompt">
              <strong>{questionText}</strong>
            </p>
            {helpContext && (
              <p className="trilho-decision-help">{helpContext}</p>
            )}
          </div>

          <div className="trilho-options-grid">
            {options.map((opt) => (
              <button
                key={opt.id}
                type="button"
                className="trilho-option-card"
                onClick={() => handleSelectOption(opt)}
              >
                <div className="trilho-option-header">
                  <h4 className="trilho-option-title">{opt.label}</h4>
                  {opt.badge && (
                    <Badge variant="brand" size="xs">
                      {opt.badge}
                    </Badge>
                  )}
                </div>

                <p className="trilho-option-desc">{opt.description}</p>

                {opt.example && (
                  <div className="trilho-option-example">
                    <span className="trilho-option-label">Exemplo: </span>
                    {opt.example}
                  </div>
                )}

                <div className="trilho-option-consequences">
                  <span className="trilho-option-label">Consequência: </span>
                  {opt.consequences}
                </div>

                <div className="trilho-option-cta">
                  <span>Escolher este caminho</span>
                  <ArrowRight size={13} />
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Rodapé */}
        <div className="trilho-tutor-footer">
          <div className="trilho-decision-source">
            <BookOpen size={13} />
            <span>Fundamentado em: {currentNode.guidelineReference}</span>
          </div>

          <Button variant="secondary" size="sm" onClick={closeDecisionModal}>
            Decidir depois
          </Button>
        </div>
      </div>
    </div>
  )
}
