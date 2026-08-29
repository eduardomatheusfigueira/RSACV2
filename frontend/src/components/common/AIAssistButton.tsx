/**
 * Revsist — AIAssistButton
 * Botão contemporâneo e inteligente de assistência de IA por campo de texto.
 * Permite preencher, corrigir, revisar estilo acadêmico e adequar às diretrizes metodológicas.
 */

import React, { useState, useRef, useEffect } from 'react'
import { Sparkles, ChevronDown, Check, RotateCcw, Loader2, Wand2, SpellCheck, Maximize2, Minimize2, MessageSquare } from 'lucide-react'
import { api, foiCancelado } from '@/api/client'
import { toast } from '@/components/ui'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useLogStore } from '@/stores/useLogStore'
import './AIAssistButton.css'

export interface AIAssistButtonProps {
  fieldId: string
  fieldLabel: string
  currentValue?: string
  fieldGuidelines?: string
  projectTitle?: string
  methodology?: string
  projectContext?: Record<string, string>
  onApply: (newText: string) => void
  size?: 'sm' | 'md'
  compact?: boolean
  className?: string
}

type AIAction = 'generate' | 'improve' | 'grammar' | 'expand' | 'shorten'

export function AIAssistButton({
  fieldId,
  fieldLabel,
  currentValue = '',
  fieldGuidelines = '',
  projectTitle = '',
  methodology = 'PRISMA-ScR',
  projectContext,
  onApply,
  size = 'sm',
  compact = false,
  className = '',
}: AIAssistButtonProps): JSX.Element | null {
  const { aiEnabled } = useSettingsStore()
  const logStore = useLogStore()

  const [loading, setLoading] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [customPromptOpen, setCustomPromptOpen] = useState(false)
  const [customPromptText, setCustomPromptText] = useState('')
  const [lastOriginalValue, setLastOriginalValue] = useState<string | null>(null)
  const [showUndo, setShowUndo] = useState(false)
  const [justApplied, setJustApplied] = useState(false)

  const dropdownRef = useRef<HTMLDivElement>(null)
  /* A chamada de assistência pode levar dezenas de segundos, e o campo fica
     travado enquanto ela corre. O controlador é o que devolve a tela a quem
     desistiu — o servidor termina o trabalho dele, mas ninguém mais espera. */
  const abortRef = useRef<AbortController | null>(null)

  // Sair da tela também cancela: uma resposta que chega para um componente
  // desmontado só serviria para tentar escrever num campo que não existe mais.
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  // Fechar dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false)
        setCustomPromptOpen(false)
      }
    }
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [dropdownOpen])

  // Se a IA estiver desligada nas configurações, o botão não é renderizado (após todos os hooks)
  if (!aiEnabled) {
    return null
  }

  const hasText = Boolean(currentValue && currentValue.trim().length > 0)

  const handleExecuteAI = async (action: AIAction, customInstruction = '') => {
    setDropdownOpen(false)
    setCustomPromptOpen(false)
    setLoading(true)

    const actionNames: Record<AIAction, string> = {
      generate: 'Preenchimento',
      improve: 'Aprimoramento',
      grammar: 'Revisão Gramatical',
      expand: 'Expansão',
      shorten: 'Síntese',
    }

    logStore.info('Assistência', `Solicitando ${actionNames[action]} para: "${fieldLabel}"`, `Ação: ${action}`)

    abortRef.current?.abort()
    const controlador = new AbortController()
    abortRef.current = controlador

    try {
      // Salva valor anterior para permitir desfazer
      setLastOriginalValue(currentValue)

      const response = await api.assistField({
        field_id: fieldId,
        field_label: fieldLabel,
        current_value: currentValue,
        field_guidelines: fieldGuidelines,
        project_title: projectTitle,
        methodology: methodology,
        project_context: projectContext,
        action,
        custom_instruction: customInstruction,
      }, controlador.signal)

      if (response.suggested_text) {
        onApply(response.suggested_text)
        setJustApplied(true)
        setShowUndo(true)

        logStore.success(
          'Assistência',
          `"${fieldLabel}" atualizado com sucesso (${response.model_used || 'Assistência'})`,
          response.explanation ? `Justificativa: ${response.explanation}` : undefined
        )

        // Limpa o estado de "just applied" após 3 segundos
        setTimeout(() => setJustApplied(false), 3000)

        // Limpa o botão de desfazer após 15 segundos
        setTimeout(() => setShowUndo(false), 15000)
      }
    } catch (err: any) {
      if (foiCancelado(err)) {
        logStore.info('Assistência', `Assistência de "${fieldLabel}" cancelada.`)
        return
      }
      console.error(`[AIAssistButton] Erro ao processar campo ${fieldId}:`, err)
      logStore.error('Assistência', `Falha ao processar "${fieldLabel}"`, err.message || 'Erro desconhecido')
      /* `alert()` trava a janela inteira e não é anunciado por leitor de tela
         como erro; o aviso do sonner é anunciado e não interrompe o trabalho. */
      toast.error('Falha no assistente', {
        description: err.message || 'Erro de comunicação com o servidor.',
      })
    } finally {
      if (abortRef.current === controlador) {
        abortRef.current = null
      }
      setLoading(false)
    }
  }

  const handleCancelarAssistencia = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
  }

  const handleUndo = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (lastOriginalValue !== null) {
      onApply(lastOriginalValue)
      setShowUndo(false)
      setLastOriginalValue(null)
      logStore.info('Assistência', `Alteração de assistência desfeita em "${fieldLabel}"`)
    }
  }

  return (
    <div className={`ai-assist-wrapper ${size} ${className}`} ref={dropdownRef}>
      {/* Botão Principal com Gatilho Rápido */}
      <div className="ai-assist-btn-group">
        <button
          type="button"
          className={`btn-ai-assist ${loading ? 'loading' : ''} ${justApplied ? 'applied' : ''}`}
          onClick={() =>
            loading
              ? handleCancelarAssistencia()
              : handleExecuteAI(hasText ? 'improve' : 'generate')
          }
          title={
            loading
              ? `Cancelar a assistência em "${fieldLabel}"`
              : hasText
                ? `Aperfeiçoar "${fieldLabel}" com Assistência`
                : `Preencher "${fieldLabel}" com Assistência`
          }
        >
          {/* O ícone segue girando para dizer que há trabalho em curso; o
              rótulo diz o que o clique faz agora, que é interromper. */}
          {loading ? (
            <Loader2 size={13} className="ai-spin-icon" />
          ) : justApplied ? (
            <Check size={13} className="ai-check-icon" />
          ) : (
            <Sparkles size={13} className="ai-sparkle-icon" />
          )}
          {!compact && (
            <span className="ai-btn-text">
              {loading ? 'Cancelar' : justApplied ? 'Aplicado!' : hasText ? 'Aperfeiçoar com Assistência' : 'Preencher com Assistência'}
            </span>
          )}
        </button>

        {/* Menu Dropdown de Ações Especializadas */}
        <button
          type="button"
          className={`btn-ai-dropdown-toggle ${dropdownOpen ? 'active' : ''}`}
          onClick={(e) => {
            e.stopPropagation()
            setDropdownOpen(!dropdownOpen)
          }}
          disabled={loading}
          title="Mais opções de assistência"
        >
          <ChevronDown size={11} />
        </button>
      </div>

      {/* Botão de Desfazer Rápido */}
      {showUndo && lastOriginalValue !== null && (
        <button
          type="button"
          className="btn-ai-undo animate-fade-in"
          onClick={handleUndo}
          title="Desfazer e restaurar texto anterior"
        >
          <RotateCcw size={11} />
          <span>Desfazer</span>
        </button>
      )}

      {/* Painel Dropdown */}
      {dropdownOpen && (
        <div className="ai-assist-dropdown-menu animate-fade-in">
          <div className="ai-dropdown-header">
            <Sparkles size={12} className="icon-accent" />
            <span>Assistente Especializado</span>
          </div>

          <div className="ai-dropdown-options">
            <button
              type="button"
              className="ai-dropdown-item"
              onClick={() => handleExecuteAI('generate')}
            >
              <Wand2 size={13} className="item-icon" />
              <div className="item-content">
                <span className="item-title">Preencher do Zero</span>
                <span className="item-desc">Gera proposta completa seguindo as diretrizes</span>
              </div>
            </button>

            {hasText && (
              <>
                <button
                  type="button"
                  className="ai-dropdown-item"
                  onClick={() => handleExecuteAI('improve')}
                >
                  <Sparkles size={13} className="item-icon" />
                  <div className="item-content">
                    <span className="item-title">Aperfeiçoar & Adequar</span>
                    <span className="item-desc">Melhora clareza e conformidade metodológica</span>
                  </div>
                </button>

                <button
                  type="button"
                  className="ai-dropdown-item"
                  onClick={() => handleExecuteAI('grammar')}
                >
                  <SpellCheck size={13} className="item-icon" />
                  <div className="item-content">
                    <span className="item-title">Corrigir Gramática & Estilo</span>
                    <span className="item-desc">Revisão formal sem alterar o conteúdo técnico</span>
                  </div>
                </button>

                <button
                  type="button"
                  className="ai-dropdown-item"
                  onClick={() => handleExecuteAI('expand')}
                >
                  <Maximize2 size={13} className="item-icon" />
                  <div className="item-content">
                    <span className="item-title">Expandir Fundamentação</span>
                    <span className="item-desc">Aprofunda o detalhamento e embasamento</span>
                  </div>
                </button>

                <button
                  type="button"
                  className="ai-dropdown-item"
                  onClick={() => handleExecuteAI('shorten')}
                >
                  <Minimize2 size={13} className="item-icon" />
                  <div className="item-content">
                    <span className="item-title">Tornar Mais Conciso</span>
                    <span className="item-desc">Sintetiza mantendo os pontos essenciais</span>
                  </div>
                </button>
              </>
            )}

            {/* Prompt Personalizado */}
            {!customPromptOpen ? (
              <button
                type="button"
                className="ai-dropdown-item custom-prompt-trigger"
                onClick={() => setCustomPromptOpen(true)}
              >
                <MessageSquare size={13} className="item-icon" />
                <div className="item-content">
                  <span className="item-title">Instrução Personalizada...</span>
                  <span className="item-desc">Forneça uma diretriz específica para a assistência</span>
                </div>
              </button>
            ) : (
              <div className="ai-custom-prompt-box">
                <input
                  type="text"
                  placeholder="Ex: Foque nos APLs do semiárido..."
                  value={customPromptText}
                  onChange={(e) => setCustomPromptText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleExecuteAI(hasText ? 'improve' : 'generate', customPromptText)
                    }
                  }}
                  autoFocus
                />
                <div className="custom-prompt-actions">
                  <button
                    type="button"
                    className="btn-custom-cancel"
                    onClick={() => setCustomPromptOpen(false)}
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    className="btn-custom-submit"
                    onClick={() => handleExecuteAI(hasText ? 'improve' : 'generate', customPromptText)}
                  >
                    Executar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
