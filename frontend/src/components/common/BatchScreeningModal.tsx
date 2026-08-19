/**
 * RSAC V2 — Batch Screening Modal & Live Progress
 * Modal interativo para configuração e acompanhamento em tempo real
 * da triagem em lote com Inteligência Artificial.
 */

import { useState } from 'react'
import {
  Sparkles,
  Zap,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  X,
  Sliders,
  ChevronRight,
  ShieldCheck,
  Check,
  Minimize2,
  ArrowRight,
} from 'lucide-react'
import { Dialog, DialogContent, DialogTitle, DialogClose } from '@/components/ui'
import './BatchScreeningModal.css'

export interface BatchScreeningItem {
  id: string
  title: string
  decision: string
  confidence?: number
  justification?: string
}

export interface CurrentScreeningStudy {
  paper_id: string
  title: string
  authors?: string
  year?: string
  index?: number
  total?: number
}

interface BatchScreeningModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  pendingCount: number
  isRunning: boolean
  progress: {
    processed: number
    total: number
    percentage: number
    included: number
    excluded: number
    pending: number
  } | null
  currentStudy: CurrentScreeningStudy | null
  activityFeed: BatchScreeningItem[]
  onStartBatch: (limit: number, concurrency: number) => Promise<void>
}

export function BatchScreeningModal({
  isOpen,
  onClose,
  projectId: _projectId,
  pendingCount,
  isRunning,
  progress,
  currentStudy,
  activityFeed,
  onStartBatch,
}: BatchScreeningModalProps): JSX.Element | null {
  const [limitOption, setLimitOption] = useState<number>(Math.min(50, Math.max(1, pendingCount)))
  const [concurrency, setConcurrency] = useState<number>(3)
  const [isStarting, setIsStarting] = useState(false)

  const isFinished = !isRunning && progress !== null && progress.processed > 0 && progress.processed >= progress.total

  const handleStart = async () => {
    try {
      setIsStarting(true)
      await onStartBatch(limitOption, concurrency)
    } finally {
      setIsStarting(false)
    }
  }

  const effectiveTotal = progress?.total || limitOption || pendingCount
  const effectiveProcessed = progress?.processed || 0
  const effectivePercentage = progress ? progress.percentage : 0

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="batch-screening-modal rsac-dialog-content"
        showCloseButton={false}
        aria-describedby="batch-screening-subtitle"
      >
        {/* Header */}
        <div className="batch-modal-header">
          <div className="batch-modal-title-group">
            <div className={`batch-icon-badge ${isRunning ? 'pulse-active' : ''}`}>
              <Sparkles size={20} className="icon-sparkle" aria-hidden="true" />
            </div>
            <div>
              <DialogTitle asChild>
                <h2>Triagem em Lote com Assistência IA</h2>
              </DialogTitle>
              <p className="batch-modal-subtitle" id="batch-screening-subtitle">
                {isRunning
                  ? `Processando ${effectiveProcessed} de ${effectiveTotal} estudos pendentes...`
                  : isFinished
                    ? 'Triagem em lote finalizada com sucesso!'
                    : `Analise estudos pendentes contra os critérios do protocolo ativo.`}
              </p>
            </div>
          </div>

          <div className="batch-modal-header-actions">
            {isRunning && (
              <button
                type="button"
                className="btn-header-minimize"
                onClick={onClose}
                title="Minimizar e continuar navegando enquanto a IA tria em segundo plano"
              >
                <Minimize2 size={16} />
                <span>Minimizar</span>
              </button>
            )}
            <DialogClose className="batch-modal-close-btn" aria-label="Fechar" title="Fechar">
              <X size={18} aria-hidden="true" />
            </DialogClose>
          </div>
        </div>

        {/* Modal Body */}
        <div className="batch-modal-body">
          {/* STATE 1: SETUP (Quando não está rodando nem terminou) */}
          {!isRunning && !progress && (
            <div className="batch-setup-view">
              <div className="batch-info-card">
                <div className="batch-info-stat">
                  <span className="stat-label">Estudos Pendentes</span>
                  <span className="stat-value">{pendingCount}</span>
                </div>
                <div className="batch-info-desc">
                  <ShieldCheck size={16} className="icon-accent" />
                  <span>
                    A inteligência artificial avaliará cada estudo individualmente aplicando os critérios de
                    inclusão e exclusão do protocolo, preenchendo as observações acadêmicas e atribuindo a decisão.
                  </span>
                </div>
              </div>

              <div className="batch-config-grid">
                {/* Quantidade a Triar */}
                <div className="batch-config-card">
                  <div className="config-card-header">
                    <Zap size={16} className="icon-accent" />
                    <strong>Quantidade de Estudos a Triar</strong>
                  </div>
                  <div className="preset-buttons-group">
                    {[10, 25, 50, 100].map((preset) => {
                      if (preset > pendingCount && pendingCount > 0 && preset !== 10) return null
                      return (
                        <button
                          key={preset}
                          type="button"
                          className={`btn-preset ${limitOption === preset ? 'active' : ''}`}
                          onClick={() => setLimitOption(preset)}
                        >
                          {preset} estudos
                        </button>
                      )
                    })}
                    {pendingCount > 0 && (
                      <button
                        type="button"
                        className={`btn-preset ${limitOption === pendingCount ? 'active' : ''}`}
                        onClick={() => setLimitOption(pendingCount)}
                      >
                        Todos ({pendingCount})
                      </button>
                    )}
                  </div>
                  <div className="custom-limit-input">
                    <label htmlFor="batch-limit-input">Ou informe uma quantidade exata:</label>
                    <input
                      id="batch-limit-input"
                      type="number"
                      min={1}
                      max={pendingCount || 1000}
                      value={limitOption}
                      onChange={(e) => setLimitOption(Math.max(1, parseInt(e.target.value) || 1))}
                    />
                  </div>
                </div>

                {/* Concorrência */}
                <div className="batch-config-card">
                  <div className="config-card-header">
                    <Sliders size={16} className="icon-accent" />
                    <strong>Concorrência / Velocidade</strong>
                  </div>
                  <p className="config-card-desc">Número de requisições simultâneas ao modelo de linguagem:</p>
                  <div className="concurrency-selector">
                    {[1, 2, 3, 4, 5].map((level) => (
                      <button
                        key={level}
                        type="button"
                        className={`btn-concurrency ${concurrency === level ? 'active' : ''}`}
                        onClick={() => setConcurrency(level)}
                      >
                        {level}x
                      </button>
                    ))}
                  </div>
                  <span className="concurrency-hint">
                    {concurrency <= 2 ? 'Recomendado para limites de taxa restritos.' : concurrency === 3 ? 'Equilíbrio ideal entre velocidade e estabilidade.' : 'Velocidade máxima (requer limites de API compatíveis).'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* STATE 2: LIVE RUNNING OU FINISHED */}
          {(isRunning || (progress && progress.processed > 0)) && (
            <div className="batch-live-view">
              {/* Placar de Resultados em Tempo Real */}
              <div className="batch-live-stats-bar">
                <div className="live-stat-chip processed">
                  <span className="stat-label">Processados</span>
                  <span className="stat-value">
                    {effectiveProcessed} / {effectiveTotal}
                  </span>
                </div>
                <div className="live-stat-chip included">
                  <span className="stat-label">
                    <CheckCircle2 size={13} /> Incluídos
                  </span>
                  <span className="stat-value">{progress?.included || 0}</span>
                </div>
                <div className="live-stat-chip excluded">
                  <span className="stat-label">
                    <XCircle size={13} /> Excluídos
                  </span>
                  <span className="stat-value">{progress?.excluded || 0}</span>
                </div>
                <div className="live-stat-chip remaining">
                  <span className="stat-label">
                    <Clock size={13} /> Restantes
                  </span>
                  <span className="stat-value">{progress?.pending || 0}</span>
                </div>
              </div>

              {/* Barra de Progresso Principal */}
              <div className="batch-progress-bar-container">
                <div className="progress-info-row">
                  <span className="progress-status-label">
                    {isRunning ? (
                      <>
                        <RefreshCw size={14} className="animate-spin text-accent" /> Triando lote em andamento...
                      </>
                    ) : (
                      <>
                        <Check size={14} className="text-success" /> Concluído
                      </>
                    )}
                  </span>
                  <span className="progress-percentage-label">{effectivePercentage}%</span>
                </div>
                <div className="progress-track">
                  <div
                    className={`progress-fill ${isRunning ? 'animate-shimmer' : ''}`}
                    style={{ width: `${Math.min(100, Math.max(0, effectivePercentage))}%` }}
                  />
                </div>
              </div>

              {/* Estudo Atualmente em Análise (Destaque do Processo) */}
              {isRunning && currentStudy && (
                <div className="current-analyzing-card animate-fade-in">
                  <div className="analyzing-header">
                    <span className="analyzing-pulse-tag">
                      <Sparkles size={13} /> Analisando agora
                    </span>
                    {currentStudy.year && <span className="analyzing-year">{currentStudy.year}</span>}
                  </div>
                  <h4 className="analyzing-title">{currentStudy.title}</h4>
                  {currentStudy.authors && (
                    <p className="analyzing-authors">{currentStudy.authors}</p>
                  )}
                </div>
              )}

              {/* Feed de Estudos Concluídos no Lote */}
              <div className="batch-feed-container">
                <div className="feed-header">
                  <h5>Estudos Recém-Triados neste Lote ({activityFeed.length})</h5>
                </div>
                <div className="feed-list">
                  {activityFeed.length === 0 ? (
                    <div className="feed-empty-state">
                      <RefreshCw size={18} className="animate-spin icon-accent" />
                      <span>Aguardando a resposta dos primeiros estudos...</span>
                    </div>
                  ) : (
                    activityFeed.map((item, idx) => (
                      <div key={item.id || idx} className="feed-item-card animate-fade-in">
                        <div className="feed-item-header">
                          <span className={`badge-decision badge-${item.decision.toLowerCase()}`}>
                            {item.decision === 'Incluído' ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                            {item.decision}
                          </span>
                          {item.confidence !== undefined && (
                            <span className="feed-item-conf">
                              Confiança: {Math.round(item.confidence * 100)}%
                            </span>
                          )}
                        </div>
                        <p className="feed-item-title">{item.title}</p>
                        {item.justification && (
                          <p className="feed-item-justification">{item.justification}</p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="batch-modal-footer">
          <div className="batch-footer-left">
            {isRunning ? (
              <span className="batch-status-note">
                <RefreshCw size={13} className="animate-spin text-accent" /> As decisões estão sendo gravadas em tempo real no banco de dados.
              </span>
            ) : isFinished ? (
              <span className="batch-status-note text-success">
                <Check size={14} /> Fila atualizada. Todos os estudos do lote foram processados.
              </span>
            ) : (
              <span className="batch-status-note">
                Modo assistido: as decisões podem ser revistas ou alteradas a qualquer momento.
              </span>
            )}
          </div>

          <div className="batch-footer-right">
            {!isRunning && !progress && (
              <>
                <button type="button" className="btn-secondary" onClick={onClose}>
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleStart}
                  disabled={isStarting || pendingCount === 0}
                >
                  {isStarting ? (
                    <>
                      <RefreshCw size={15} className="animate-spin" /> Iniciando...
                    </>
                  ) : (
                    <>
                      <Sparkles size={15} /> Iniciar Triagem em Lote ({limitOption})
                    </>
                  )}
                </button>
              </>
            )}

            {isRunning && (
              <button type="button" className="btn-secondary" onClick={onClose}>
                Acompanhar em Segundo Plano <ChevronRight size={15} />
              </button>
            )}

            {isFinished && (
              <button type="button" className="btn-primary" onClick={onClose}>
                Concluir e Ver Fila <ArrowRight size={15} />
              </button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
