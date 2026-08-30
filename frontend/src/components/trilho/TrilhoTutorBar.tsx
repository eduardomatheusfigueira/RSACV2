/**
 * Revsist — Barra do Tutor Metodológico (Modo Trilho)
 * Acompanhamento contínuo e contextual passo a passo (Doc 46).
 */

import React from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Compass,
  ChevronLeft,
  ChevronRight,
  Minimize2,
  Maximize2,
  X,
  GitBranch,
  Target,
  BookOpen,
  CheckCircle2,
} from 'lucide-react'
import { useTrilhoStore } from '@/stores/useTrilhoStore'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { Button } from '@/components/ui'
import './Trilho.css'

export function TrilhoTutorBar(): JSX.Element | null {
  const navigate = useNavigate()
  const { id: urlProjectId } = useParams<{ id: string }>()
  const { activeProject } = useSettingsStore()
  const projectId = urlProjectId || activeProject?.id

  const {
    isActive,
    isMinimized,
    toggleMinimized,
    stopTrilho,
    goToNext,
    goToPrevious,
    openDecisionModal,
    getCurrentNode,
    getCurrentPhaseInfo,
    getProgressPercentage,
  } = useTrilhoStore()

  const currentNode = getCurrentNode()
  const phaseInfo = getCurrentPhaseInfo()
  const progressPct = getProgressPercentage()

  if (!isActive) return null

  const handleActionClick = () => {
    if (currentNode.branchingQuestion) {
      openDecisionModal()
      return
    }

    if (currentNode.actionButton?.targetUrl && projectId) {
      const targetUrl = currentNode.actionButton.targetUrl.replace(':id', projectId)
      navigate(targetUrl)
      return
    }

    if (currentNode.targetElementSelector) {
      const el = document.querySelector<HTMLElement>(currentNode.targetElementSelector)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        el.focus?.()
      }
    }
  }

  // Visualização Compacta / Minimizada
  if (isMinimized) {
    return (
      <div className="trilho-tutor-container">
        <div className="trilho-tutor-card is-minimized animate-fade-in">
          <div className="trilho-progress-track">
            <div className="trilho-progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <div className="trilho-tutor-header">
            <div className="trilho-tutor-meta">
              <div className="trilho-tutor-icon" title="Modo Trilho: Tutor Ativo">
                <Compass size={14} />
              </div>
              <span className="trilho-phase-badge">{phaseInfo.shortName}</span>
              <h4 className="trilho-tutor-title">{currentNode.title}</h4>
            </div>

            <div className="trilho-tutor-controls">
              <button
                type="button"
                className="trilho-btn-icon"
                onClick={toggleMinimized}
                title="Expandir orientações do tutor"
                aria-label="Expandir tutor"
              >
                <Maximize2 size={14} />
              </button>
              <button
                type="button"
                className="trilho-btn-icon"
                onClick={stopTrilho}
                title="Pausar Modo Trilho"
                aria-label="Pausar tutor"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Visualização Completa / Expandida
  return (
    <div className="trilho-tutor-container">
      <div className="trilho-tutor-card animate-fade-in">
        {/* Barra de Progresso Superior */}
        <div className="trilho-progress-track">
          <div
            className="trilho-progress-fill"
            style={{ width: `${progressPct}%` }}
            role="progressbar"
            aria-valuenow={progressPct}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>

        {/* Cabeçalho */}
        <div className="trilho-tutor-header">
          <div className="trilho-tutor-meta">
            <div className="trilho-tutor-icon">
              <Compass size={15} />
            </div>
            <span className="trilho-phase-badge">
              Etapa {phaseInfo.phase} de {phaseInfo.totalPhases - 1} · {phaseInfo.name}
            </span>
            <h4 className="trilho-tutor-title">{currentNode.title}</h4>
          </div>

          <div className="trilho-tutor-controls">
            <button
              type="button"
              className="trilho-btn-icon"
              onClick={toggleMinimized}
              title="Minimizar barra do tutor"
              aria-label="Minimizar tutor"
            >
              <Minimize2 size={14} />
            </button>
            <button
              type="button"
              className="trilho-btn-icon"
              onClick={stopTrilho}
              title="Pausar Modo Trilho"
              aria-label="Pausar tutor"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Corpo com Instrução e Racional */}
        <div className="trilho-tutor-body">
          <div className="trilho-instruction-section">
            <span className="text-3xs uppercase font-bold tracking-wider text-muted-foreground" style={{ fontSize: 'var(--text-3xs)', fontWeight: 'var(--weight-bold)', letterSpacing: '0.05em', color: 'var(--color-text-tertiary)' }}>
              O que fazer agora
            </span>
            <p className="trilho-instruction-text">{currentNode.instruction}</p>
          </div>

          <div className="trilho-rationale-box">
            <span className="trilho-rationale-label">Por que fazer assim?</span>
            <p className="trilho-rationale-text">{currentNode.rationale}</p>
            <div className="trilho-guideline-tag">
              <BookOpen size={10} style={{ display: 'inline', marginRight: '4px' }} />
              <span>{currentNode.guidelineReference}</span>
            </div>
          </div>
        </div>

        {/* Rodapé com Navegação e Ação Contextual */}
        <div className="trilho-tutor-footer">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="xs"
              onClick={goToPrevious}
              disabled={!currentNode.previousNodeId}
              leftIcon={<ChevronLeft size={13} />}
            >
              Anterior
            </Button>

            {currentNode.branchingQuestion ? (
              <Button
                variant="primary"
                size="xs"
                onClick={openDecisionModal}
                leftIcon={<GitBranch size={13} />}
              >
                Abrir Decisão Metodológica
              </Button>
            ) : currentNode.actionButton ? (
              <Button
                variant="primary"
                size="xs"
                onClick={handleActionClick}
                leftIcon={<Target size={13} />}
              >
                {currentNode.actionButton.label}
              </Button>
            ) : null}
          </div>

          <div className="trilho-footer-actions">
            <Button
              variant="secondary"
              size="xs"
              onClick={goToNext}
              disabled={!currentNode.nextNodeId && !currentNode.branchingQuestion}
              rightIcon={<ChevronRight size={13} />}
            >
              {currentNode.branchingQuestion ? 'Decidir' : 'Avançar'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
