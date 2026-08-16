/**
 * RSAC V2 — Screening Page (Triagem 1)
 * Triagem manual e assistida por IA (individual e em lote)
 * com leitor de resumos e avaliação de critérios em tempo real.
 */

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Filter,
  ExternalLink,
  BookOpen,
  ArrowLeft,
  FileText,
  AlertCircle,
  Calendar,
  Building,
  User,
  Plus,
  Sparkles,
  RefreshCw,
  Zap,
  Sliders,
  Check,
  Percent,
  Layers,
  CheckSquare,
  Square,
  CheckCheck,
  RotateCcw,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useLogStore } from '@/stores/useLogStore'
import type { DeduplicationReport, Paper, Decision, Protocol } from '@/types/api'
import { DeduplicationReportModal } from '@/components/common/DeduplicationReportModal'
import './ScreeningPage.css'

export function ScreeningPage(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject, aiEnabled } = useSettingsStore()
  const { info, success, warn, error } = useLogStore()

  const [papers, setPapers] = useState<Paper[]>([])

  const [protocol, setProtocol] = useState<Protocol | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)

  // Deduplication Report State
  const [dedupReport, setDedupReport] = useState<DeduplicationReport | null>(null)
  const [isDedupModalOpen, setIsDedupModalOpen] = useState(false)
  const [isDeduplicating, setIsDeduplicating] = useState(false)

  // Filters & Pagination
  const [decisionFilter, setDecisionFilter] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  // Stats
  const [stats, setStats] = useState({
    total: 0,
    included: 0,
    excluded: 0,
    pending: 0,
  })

  // AI Single Screening State
  const [isAiScreeningSingle, setIsAiScreeningSingle] = useState(false)
  const [aiLastResult, setAiLastResult] = useState<any>(null)

  // AI Batch Screening Modal & Live Progress State
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false)
  const [batchLimit, setBatchLimit] = useState(50)
  const [batchConcurrency, setBatchConcurrency] = useState(3)
  const [isBatchRunning, setIsBatchRunning] = useState(false)
  const [batchProgress, setBatchProgress] = useState<{
    processed: number
    total: number
    percentage: number
    included: number
    excluded: number
    pending: number
  } | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Quick add manual paper modal
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [manualTitle, setManualTitle] = useState('')
  const [manualAuthors, setManualAuthors] = useState('')
  const [manualYear, setManualYear] = useState('')
  const [manualAbstract, setManualAbstract] = useState('')

  useEffect(() => {
    if (id) {
      loadInitialData(id)
      initScreeningWebSocket(id)
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [id])

  useEffect(() => {
    if (id) {
      loadPapers(id)
    }
  }, [id, decisionFilter, searchTerm, page])

  const initScreeningWebSocket = (projectId: string) => {
    try {
      const wsUrl = api.getScreeningWebSocketUrl(projectId)
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'batch_screening_progress') {
            setIsBatchRunning(true)
            setBatchProgress({
              processed: msg.processed,
              total: msg.total,
              percentage: msg.percentage,
              included: msg.included_count,
              excluded: msg.excluded_count,
              pending: msg.pending_count,
            })
            info('Triagem', `Triagem em lote: ${msg.processed}/${msg.total} (${msg.percentage}%)`, `Incluídos: ${msg.included_count} | Excluídos: ${msg.excluded_count} | Pendentes: ${msg.pending_count}`)
          } else if (msg.type === 'batch_screening_completed') {
            setIsBatchRunning(false)
            success('Triagem', 'Triagem em lote finalizada com sucesso!')
            loadStats(projectId)
            loadPapers(projectId)
          }
        } catch (e) {
          // ignore non-json
        }
      }
    } catch (err: any) {
      error('WebSocket', 'Falha ao conectar WebSocket de triagem', err.message)
    }
  }

  const loadInitialData = async (projectId: string) => {
    try {
      if (!activeProject || activeProject.id !== projectId) {
        const proj = await api.getProject(projectId)
        setActiveProject(proj)
      }
      const proto = await api.getProtocol(projectId)
      setProtocol(proto)
      loadStats(projectId)
    } catch (err) {
      console.error('Erro ao carregar dados iniciais:', err)
    }
  }

  const loadStats = async (projectId: string) => {
    try {
      const s = await api.getProjectStats(projectId)
      setStats({
        total: s.total_papers,
        included: s.included_papers,
        excluded: s.excluded_papers,
        pending: s.pending_papers,
      })
    } catch (err) {
      console.error('Erro ao carregar stats:', err)
    }
  }

  const loadPapers = async (projectId: string) => {
    try {
      setLoading(true)
      const res = await api.listPapers(projectId, {
        page,
        page_size: 20,
        decision: decisionFilter || undefined,
        search: searchTerm || undefined,
      })
      setPapers(res.items)
      setTotalPages(res.total_pages)
      setTotalCount(res.total)

      if (res.items.length > 0) {
        setSelectedPaper((prev) => {
          if (!prev) return res.items[0]
          const existing = res.items.find((p) => p.id === prev.id)
          return existing || res.items[0]
        })
      } else {
        setSelectedPaper(null)
      }
    } catch (err) {
      console.error('Erro ao listar papers:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDecision = async (paperId: string, decision: Decision) => {
    if (!id) return
    try {
      const updated = await api.updatePaper(id, paperId, { decision })

      if (decisionFilter !== '' && decision !== decisionFilter) {
        // Se o filtro atual estiver ativo (ex: Pendente, Incluído, Excluído) e a nova decisão for diferente,
        // remove o artigo imediatamente da lista filtrada e avança para o próximo
        const currentIndex = papers.findIndex((p) => p.id === paperId)
        const newPapers = papers.filter((p) => p.id !== paperId)
        setPapers(newPapers)
        setTotalCount((prev) => Math.max(0, prev - 1))

        if (selectedPaper?.id === paperId) {
          if (newPapers.length > 0) {
            const nextIndex = Math.min(currentIndex >= 0 ? currentIndex : 0, newPapers.length - 1)
            setSelectedPaper(newPapers[nextIndex])
          } else {
            setSelectedPaper(null)
          }
          setAiLastResult(null)
        }

        // Se a página atual esvaziou e estávamos em uma página posterior, volta uma página
        if (newPapers.length === 0 && page > 1) {
          setPage((prev) => Math.max(1, prev - 1))
        } else if (newPapers.length === 0) {
          // Se esvaziou na página 1, recarrega para verificar se há mais itens pendentes no banco
          loadPapers(id)
        }
      } else {
        setPapers(papers.map((p) => (p.id === paperId ? updated : p)))
        if (selectedPaper?.id === paperId) {
          setSelectedPaper(updated)
        }
      }

      const logLvl = decision === 'Incluído' ? 'success' : decision === 'Excluído' ? 'warn' : 'info'
      useLogStore.getState().log(logLvl, 'Triagem', `Estudo marcado como "${decision}"`, `Título: ${updated.title}\nID: ${paperId}`)

      loadStats(id)
    } catch (err: any) {
      error('Triagem', `Erro ao registrar decisão ${decision}`, err.message)
    }
  }

  const handleSingleAIScreening = async () => {
    if (!id || !selectedPaper) return
    try {
      setIsAiScreeningSingle(true)
      setAiLastResult(null)
      info('IA', `Iniciando triagem por IA do estudo "${selectedPaper.title.slice(0, 50)}..."`)

      const res = await api.screenSinglePaperAI(id, selectedPaper.id)
      setAiLastResult(res)

      success('IA', `Parecer IA: ${res.decision} (Confiança: ${(res.confidence * 100).toFixed(0)}%)`, `Justificativa: ${res.justification || (res as any).reasoning}\nCritérios atendidos: ${(res as any).criteria_met?.join(', ') || 'Nenhum'}`)

      // Atualizar paper com os dados gerados
      const updatedPaper = await api.getPaper(id, selectedPaper.id)
      setSelectedPaper(updatedPaper)
      setPapers(papers.map((p) => (p.id === selectedPaper.id ? updatedPaper : p)))
      loadStats(id)
    } catch (err: any) {
      error('IA', `Falha na triagem com IA: ${err.message}`)
    } finally {
      setIsAiScreeningSingle(false)
    }
  }

  const handleStartBatchAI = async () => {
    if (!id) return
    try {
      setIsBatchRunning(true)
      setBatchProgress({
        processed: 0,
        total: batchLimit,
        percentage: 0,
        included: 0,
        excluded: 0,
        pending: 0,
      })
      await api.startBatchScreeningAI(id, {
        limit: batchLimit,
        concurrency: batchConcurrency,
      })
    } catch (err) {
      console.error('Erro ao iniciar batch screening:', err)
      setIsBatchRunning(false)
    }
  }

  const inclusionCriteria = useMemo(() => {
    return (protocol?.criteria || []).filter((c) => !c.is_exclusion)
  }, [protocol])

  const exclusionCriteria = useMemo(() => {
    return (protocol?.criteria || []).filter((c) => c.is_exclusion)
  }, [protocol])

  const incMetCount = useMemo(() => {
    if (!selectedPaper || !selectedPaper.criteria_evaluations) return 0
    return inclusionCriteria.filter((c) => c.id && selectedPaper.criteria_evaluations?.[c.id]).length
  }, [inclusionCriteria, selectedPaper])

  const excMetCount = useMemo(() => {
    if (!selectedPaper || !selectedPaper.criteria_evaluations) return 0
    return exclusionCriteria.filter((c) => c.id && selectedPaper.criteria_evaluations?.[c.id]).length
  }, [exclusionCriteria, selectedPaper])

  const handleToggleCriterion = async (criterionId: string) => {
    if (!id || !selectedPaper) return
    const currentVal = !!selectedPaper.criteria_evaluations?.[criterionId]
    const nextVal = !currentVal

    const updatedEvals = {
      ...(selectedPaper.criteria_evaluations || {}),
      [criterionId]: nextVal,
    }
    const updatedPaper = {
      ...selectedPaper,
      criteria_evaluations: updatedEvals,
    }

    // Optimistic UI update
    setSelectedPaper(updatedPaper)
    setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? updatedPaper : p)))

    try {
      const res = await api.updatePaper(id, selectedPaper.id, {
        criteria_evaluations: { [criterionId]: nextVal },
      })
      setSelectedPaper(res)
      setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? res : p)))
    } catch (err: any) {
      error('Triagem', 'Erro ao salvar avaliação do critério', err.message)
      setSelectedPaper(selectedPaper)
    }
  }

  const handleCheckAllInclusion = async () => {
    if (!id || !selectedPaper || !protocol) return
    if (inclusionCriteria.length === 0) return

    const updates: Record<string, boolean> = {}
    inclusionCriteria.forEach((c) => {
      if (c.id) updates[c.id] = true
    })

    const updatedEvals = {
      ...(selectedPaper.criteria_evaluations || {}),
      ...updates,
    }
    const updatedPaper = { ...selectedPaper, criteria_evaluations: updatedEvals }
    setSelectedPaper(updatedPaper)
    setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? updatedPaper : p)))

    try {
      const res = await api.updatePaper(id, selectedPaper.id, {
        criteria_evaluations: updates,
      })
      setSelectedPaper(res)
      setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? res : p)))
      success('Triagem', 'Todos os critérios de inclusão foram marcados como atendidos.')
    } catch (err: any) {
      error('Triagem', 'Erro ao marcar critérios de inclusão', err.message)
    }
  }

  const handleClearCriteria = async () => {
    if (!id || !selectedPaper || !protocol) return
    const updates: Record<string, boolean> = {}
    protocol.criteria.forEach((c) => {
      if (c.id) updates[c.id] = false
    })

    const updatedEvals = {
      ...(selectedPaper.criteria_evaluations || {}),
      ...updates,
    }
    const updatedPaper = { ...selectedPaper, criteria_evaluations: updatedEvals }
    setSelectedPaper(updatedPaper)
    setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? updatedPaper : p)))

    try {
      const res = await api.updatePaper(id, selectedPaper.id, {
        criteria_evaluations: updates,
      })
      setSelectedPaper(res)
      setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? res : p)))
      info('Triagem', 'Marcações de critérios limpas para este estudo.')
    } catch (err: any) {
      error('Triagem', 'Erro ao limpar critérios', err.message)
    }
  }


  const handleObservationsChange = async (obs: string) => {
    if (!id || !selectedPaper) return
    try {
      const updated = await api.updatePaper(id, selectedPaper.id, {
        observations: obs,
      })
      setSelectedPaper(updated)
      setPapers(papers.map((p) => (p.id === selectedPaper.id ? updated : p)))
    } catch (err) {
      console.error('Erro ao atualizar observações:', err)
    }
  }


  const handleAddManualPaper = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !manualTitle.trim()) return

    try {
      const newP = await api.createPaper(id, {
        title: manualTitle.trim(),
        authors: manualAuthors.trim(),
        year: manualYear.trim(),
        abstract: manualAbstract.trim(),
        sources: ['Manual'],
      })

      setPapers([newP, ...papers])
      setSelectedPaper(newP)
      setIsAddModalOpen(false)
      setManualTitle('')
      setManualAuthors('')
      setManualYear('')
      setManualAbstract('')
      loadStats(id)
    } catch (err) {
      console.error('Erro ao cadastrar paper manual:', err)
    }
  }

  const handleOpenDedupReport = async () => {
    if (!id) return
    try {
      setIsDeduplicating(true)
      // Tenta obter o relatório mais recente; se não existir, executa deduplicação
      try {
        const report = await api.getDeduplicationReport(id)
        setDedupReport(report)
        setIsDedupModalOpen(true)
      } catch {
        const res = await api.deduplicateProject(id)
        setDedupReport(res.data)
        setIsDedupModalOpen(true)
      }
    } catch (err: any) {
      error('Deduplicação', 'Falha ao carregar relatório de deduplicação', err.message)
    } finally {
      setIsDeduplicating(false)
    }
  }

  return (
    <div className="screening-page animate-fade-in">
      {/* Top Header */}
      <div className="page-header">
        <div>
          <button className="btn-back" onClick={() => navigate('/projects')}>
            <ArrowLeft size={16} /> Voltar para Projetos
          </button>
          <h1 className="page-title">Triagem de Estudos (Fase 1)</h1>
          <p className="page-subtitle">
            Avaliação de títulos e resumos com assistência de IA e guardrails de zero alucinação
          </p>
        </div>
        <div className="header-actions">
          <button
            className="btn-secondary btn-dedup"
            onClick={handleOpenDedupReport}
            disabled={isDeduplicating}
            title="Visualiza o relatório consolidado de deduplicação das fontes"
          >
            {isDeduplicating ? (
              <RefreshCw size={16} className="animate-spin" />
            ) : (
              <Layers size={16} className="icon-accent" />
            )}
            Relatório de Deduplicação
          </button>
          {aiEnabled && (
            <button className="btn-secondary" onClick={() => setIsBatchModalOpen(true)}>
              <Zap size={16} className="icon-accent" /> Triagem em Lote com IA
            </button>
          )}
          <button className="btn-primary" onClick={() => setIsAddModalOpen(true)}>
            <Plus size={18} /> Adicionar Manual
          </button>
        </div>
      </div>

      {/* Stats Counter Bar */}
      <div className="screening-counters">
        <button
          className={`counter-btn ${decisionFilter === '' ? 'active' : ''}`}
          onClick={() => {
            setDecisionFilter('')
            setPage(1)
          }}
        >
          <span className="count-label">Todos</span>
          <span className="count-num">{stats.total}</span>
        </button>

        <button
          className={`counter-btn pending ${decisionFilter === 'Pendente' ? 'active' : ''}`}
          onClick={() => {
            setDecisionFilter('Pendente')
            setPage(1)
          }}
        >
          <Clock size={16} />
          <span className="count-label">Pendentes</span>
          <span className="count-num">{stats.pending}</span>
        </button>

        <button
          className={`counter-btn included ${decisionFilter === 'Incluído' ? 'active' : ''}`}
          onClick={() => {
            setDecisionFilter('Incluído')
            setPage(1)
          }}
        >
          <CheckCircle2 size={16} />
          <span className="count-label">Incluídos</span>
          <span className="count-num">{stats.included}</span>
        </button>

        <button
          className={`counter-btn excluded ${decisionFilter === 'Excluído' ? 'active' : ''}`}
          onClick={() => {
            setDecisionFilter('Excluído')
            setPage(1)
          }}
        >
          <XCircle size={16} />
          <span className="count-label">Excluídos</span>
          <span className="count-num">{stats.excluded}</span>
        </button>
      </div>

      {/* Main Split Layout: List Left, Details Right */}
      <div className="screening-layout">
        {/* Left: Papers List */}
        <div className="screening-list-col">
          <div className="list-search-box">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Buscar em título, autor, resumo..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setPage(1)
              }}
            />
          </div>

          {loading ? (
            <div className="loading-state-small">
              <div className="loading-spinner animate-spin" />
              <span>Carregando estudos...</span>
            </div>
          ) : papers.length === 0 ? (
            <div className="empty-papers-box">
              <FileText size={32} />
              <p>Nenhum estudo encontrado para os filtros atuais.</p>
            </div>
          ) : (
            <div className="papers-scroll-list">
              {papers.map((paper) => {
                const isSelected = selectedPaper?.id === paper.id
                return (
                  <div
                    key={paper.id}
                    className={`paper-list-item ${isSelected ? 'selected' : ''} dec-${paper.decision.toLowerCase()}`}
                    onClick={() => {
                      setSelectedPaper(paper)
                      setAiLastResult(null)
                    }}
                  >
                    <div className="item-meta">
                      <span className={`badge-decision badge-${paper.decision.toLowerCase()}`}>
                        {paper.decision}
                      </span>
                      {paper.ai_confidence !== null && (
                        <span className="badge-ai-conf" title="Confiança da IA">
                          <Sparkles size={11} /> {Math.round(paper.ai_confidence * 100)}%
                        </span>
                      )}
                      {paper.criteria_evaluations && Object.values(paper.criteria_evaluations).some(Boolean) && (
                        <span className="badge-criteria-mini" title="Critérios avaliados para este estudo">
                          <CheckCircle2 size={11} /> Critérios
                        </span>
                      )}
                      {paper.year && <span className="item-year">{paper.year}</span>}
                    </div>

                    <h4 className="item-title">{paper.title}</h4>
                    {paper.authors && <p className="item-authors">{paper.authors}</p>}
                  </div>
                )
              })}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination-bar">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="btn-secondary small"
              >
                Anterior
              </button>
              <span>
                Pág {page} de {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="btn-secondary small"
              >
                Próxima
              </button>
            </div>
          )}
        </div>

        {/* Right: Paper Details & Decision Inspector */}
        <div className="screening-detail-col">
          {selectedPaper ? (
            <div className="paper-inspector animate-fade-in">
              {/* Decision Actions Header */}
              <div className="inspector-actions-bar">
                <div className="decision-buttons">
                  <button
                    className={`btn-dec include ${selectedPaper.decision === 'Incluído' ? 'active' : ''}`}
                    onClick={() => handleDecision(selectedPaper.id, 'Incluído')}
                  >
                    <CheckCircle2 size={16} /> Incluir
                  </button>
                  <button
                    className={`btn-dec exclude ${selectedPaper.decision === 'Excluído' ? 'active' : ''}`}
                    onClick={() => handleDecision(selectedPaper.id, 'Excluído')}
                  >
                    <XCircle size={16} /> Excluir
                  </button>
                  <button
                    className={`btn-dec pending ${selectedPaper.decision === 'Pendente' ? 'active' : ''}`}
                    onClick={() => handleDecision(selectedPaper.id, 'Pendente')}
                  >
                    <Clock size={16} /> Deixar Pendente
                  </button>
                </div>

                {aiEnabled && (
                  <button
                    className="btn-ai-triage"
                    onClick={handleSingleAIScreening}
                    disabled={isAiScreeningSingle}
                    title="Avaliar este artigo com Inteligência Artificial"
                  >
                    {isAiScreeningSingle ? (
                      <>
                        <RefreshCw size={15} className="animate-spin" /> Analisando...
                      </>
                    ) : (
                      <>
                        <Sparkles size={15} /> Triar com IA
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Title & Metadata */}
              <div className="inspector-content">
                <h2 className="inspector-title">{selectedPaper.title}</h2>

                <div className="inspector-metadata-grid">
                  {selectedPaper.authors && (
                    <div className="meta-item">
                      <User size={15} />
                      <span>{selectedPaper.authors}</span>
                    </div>
                  )}
                  {selectedPaper.year && (
                    <div className="meta-item">
                      <Calendar size={15} />
                      <span>Ano: {selectedPaper.year}</span>
                    </div>
                  )}
                  {selectedPaper.institution && (
                    <div className="meta-item">
                      <Building size={15} />
                      <span>{selectedPaper.institution}</span>
                    </div>
                  )}
                  {selectedPaper.doi && (
                    <div className="meta-item">
                      <ExternalLink size={15} />
                      <a
                        href={`https://doi.org/${selectedPaper.doi}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        DOI: {selectedPaper.doi}
                      </a>
                    </div>
                  )}
                </div>

                {/* AI Screening Live Callout */}
                {aiLastResult && (
                  <div className="ai-result-callout animate-fade-in">
                    <div className="ai-callout-header">
                      <div className="ai-tag">
                        <Sparkles size={14} /> Análise IA ({aiLastResult.model_used})
                      </div>
                      <span className="ai-confidence">
                        Confiança: {Math.round(aiLastResult.confidence * 100)}%
                      </span>
                    </div>
                    <p className="ai-justification">{aiLastResult.justification}</p>
                  </div>
                )}

                {/* Abstract Section */}
                <div className="inspector-section">
                  <h3>Resumo (Abstract)</h3>
                  <div className="abstract-box">
                    {selectedPaper.abstract ? (
                      <p>{selectedPaper.abstract}</p>
                    ) : (
                      <p className="no-abstract">
                        Resumo não disponível nos metadados coletados.
                      </p>
                    )}
                  </div>
                </div>

                {/* Criteria Evaluation Section with Interactive Checkboxes */}
                <div className="inspector-section criteria-evaluation-section">
                  <div className="criteria-section-header">
                    <div className="header-left">
                      <h3>Avaliação de Critérios de Elegibilidade</h3>
                      <p className="criteria-section-desc">
                        Marque os critérios atendidos pelo estudo para registrar a justificativa formal da decisão.
                      </p>
                    </div>

                    {protocol && protocol.criteria && protocol.criteria.length > 0 && (
                      <div className="criteria-section-actions">
                        {inclusionCriteria.length > 0 && (
                          <button
                            type="button"
                            className="btn-criteria-action"
                            onClick={handleCheckAllInclusion}
                            title="Marcar todos os critérios de inclusão como atendidos"
                          >
                            <CheckCheck size={14} /> Marcar Inclusões
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn-criteria-action text-muted"
                          onClick={handleClearCriteria}
                          title="Desmarcar todas as avaliações deste estudo"
                        >
                          <RotateCcw size={13} /> Limpar
                        </button>
                      </div>
                    )}
                  </div>

                  {protocol && protocol.criteria && protocol.criteria.length > 0 ? (
                    <>
                      {/* Summary Badges */}
                      <div className="criteria-stats-summary">
                        <div
                          className={`criteria-stat-badge inc-badge ${
                            incMetCount === inclusionCriteria.length && inclusionCriteria.length > 0
                              ? 'all-met'
                              : ''
                          }`}
                        >
                          <CheckCircle2 size={14} />
                          <span>
                            Inclusão: <strong>{incMetCount} / {inclusionCriteria.length}</strong> atendidos
                          </span>
                        </div>

                        <div
                          className={`criteria-stat-badge exc-badge ${
                            excMetCount > 0 ? 'has-exclusion' : 'none'
                          }`}
                        >
                          {excMetCount > 0 ? <AlertCircle size={14} /> : <ShieldCheck size={14} />}
                          <span>
                            Exclusão: <strong>{excMetCount}</strong>{' '}
                            {excMetCount === 1 ? 'identificado' : 'identificados'}
                          </span>
                        </div>
                      </div>

                      {/* Smart Recommendation Helper Banner */}
                      {excMetCount > 0 ? (
                        <div className="criteria-alert-banner alert-exclude animate-fade-in">
                          <div className="alert-text">
                            <strong>Atenção:</strong> {excMetCount} critério(s) de exclusão identificado(s). Registro de exclusão fundamentado.
                          </div>
                          {selectedPaper.decision !== 'Excluído' && (
                            <button
                              type="button"
                              className="btn-quick-decision btn-quick-exclude"
                              onClick={() => handleDecision(selectedPaper.id, 'Excluído')}
                            >
                              <XCircle size={14} /> Excluir Estudo
                            </button>
                          )}
                        </div>
                      ) : incMetCount === inclusionCriteria.length && inclusionCriteria.length > 0 ? (
                        <div className="criteria-alert-banner alert-include animate-fade-in">
                          <div className="alert-text">
                            <strong>Elegível:</strong> Todos os {inclusionCriteria.length} critérios de inclusão foram atendidos e nenhuma exclusão identificada.
                          </div>
                          {selectedPaper.decision !== 'Incluído' && (
                            <button
                              type="button"
                              className="btn-quick-decision btn-quick-include"
                              onClick={() => handleDecision(selectedPaper.id, 'Incluído')}
                            >
                              <CheckCircle2 size={14} /> Incluir Estudo
                            </button>
                          )}
                        </div>
                      ) : null}

                      {/* Criteria Split Grid: Inclusion & Exclusion */}
                      <div className="criteria-grid-layout">
                        {/* Inclusion Criteria Column */}
                        <div className="criteria-col inc-col">
                          <div className="col-header">
                            <span className="col-tag inc-tag">Critérios de Inclusão</span>
                            <span className="col-count">
                              {incMetCount}/{inclusionCriteria.length}
                            </span>
                          </div>

                          {inclusionCriteria.length === 0 ? (
                            <p className="no-criteria-hint">Nenhum critério de inclusão cadastrado.</p>
                          ) : (
                            <div className="criteria-checkbox-list">
                              {inclusionCriteria.map((c) => {
                                const isChecked = !!(
                                  c.id && selectedPaper.criteria_evaluations?.[c.id]
                                )
                                return (
                                  <label
                                    key={c.id || c.text}
                                    className={`criterion-card inc-card ${
                                      isChecked ? 'checked' : ''
                                    }`}
                                  >
                                    <input
                                      type="checkbox"
                                      className="sr-only"
                                      checked={isChecked}
                                      onChange={() => c.id && handleToggleCriterion(c.id)}
                                    />
                                    <div className="custom-checkbox inc-checkbox">
                                      {isChecked ? <CheckSquare size={16} /> : <Square size={16} />}
                                    </div>
                                    <span className="criterion-text">{c.text}</span>
                                  </label>
                                )
                              })}
                            </div>
                          )}
                        </div>

                        {/* Exclusion Criteria Column */}
                        <div className="criteria-col exc-col">
                          <div className="col-header">
                            <span className="col-tag exc-tag">Critérios de Exclusão</span>
                            <span className="col-count">
                              {excMetCount}/{exclusionCriteria.length}
                            </span>
                          </div>

                          {exclusionCriteria.length === 0 ? (
                            <p className="no-criteria-hint">Nenhum critério de exclusão cadastrado.</p>
                          ) : (
                            <div className="criteria-checkbox-list">
                              {exclusionCriteria.map((c) => {
                                const isChecked = !!(
                                  c.id && selectedPaper.criteria_evaluations?.[c.id]
                                )
                                return (
                                  <label
                                    key={c.id || c.text}
                                    className={`criterion-card exc-card ${
                                      isChecked ? 'checked' : ''
                                    }`}
                                  >
                                    <input
                                      type="checkbox"
                                      className="sr-only"
                                      checked={isChecked}
                                      onChange={() => c.id && handleToggleCriterion(c.id)}
                                    />
                                    <div className="custom-checkbox exc-checkbox">
                                      {isChecked ? <CheckSquare size={16} /> : <Square size={16} />}
                                    </div>
                                    <span className="criterion-text">{c.text}</span>
                                  </label>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="no-protocol-criteria-card">
                      <AlertCircle size={24} />
                      <div className="no-crit-info">
                        <strong>Nenhum critério de elegibilidade cadastrado no protocolo</strong>
                        <p>
                          Defina critérios de inclusão e exclusão no protocolo para registrá-los durante a triagem.
                        </p>
                      </div>
                      <button
                        type="button"
                        className="btn-secondary small"
                        onClick={() => navigate(`/projects/${id}/protocol`)}
                      >
                        Configurar Protocolo
                      </button>
                    </div>
                  )}
                </div>


                {/* Notes & Observations */}
                <div className="inspector-section">
                  <h3>Observações do Revisor</h3>
                  <textarea
                    rows={4}
                    className="inspector-textarea"
                    placeholder="Anote justificativas para inclusão/exclusão, dúvidas sobre o método ou observações..."
                    value={selectedPaper.observations || ''}
                    onChange={(e) => handleObservationsChange(e.target.value)}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="no-selection-box">
              <BookOpen size={48} strokeWidth={1} />
              <h3>Nenhum estudo selecionado</h3>
              <p>Selecione um artigo na lista à esquerda para revisar detalhes e tomar decisão.</p>
            </div>
          )}
        </div>
      </div>

      {/* Batch AI Screening Modal */}
      {isBatchModalOpen && (
        <div className="modal-overlay animate-fade-in" onClick={() => !isBatchRunning && setIsBatchModalOpen(false)}>
          <div className="modal-content batch-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Triagem em Lote com Inteligência Artificial</h2>
              <p>Execute a avaliação automática em massa de artigos com status Pendente</p>
            </div>

            {!isBatchRunning ? (
              <div className="batch-config-form">
                <div className="form-group">
                  <label>Quantidade Máxima de Artigos Pendentes ({batchLimit})</label>
                  <select
                    value={batchLimit}
                    onChange={(e) => setBatchLimit(Number(e.target.value))}
                  >
                    <option value={20}>20 artigos</option>
                    <option value={50}>50 artigos (Recomendado)</option>
                    <option value={100}>100 artigos</option>
                    <option value={200}>200 artigos</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Concorrência / Workers ({batchConcurrency})</label>
                  <select
                    value={batchConcurrency}
                    onChange={(e) => setBatchConcurrency(Number(e.target.value))}
                  >
                    <option value={1}>1 worker (Sequencial / Evita Rate Limit)</option>
                    <option value={3}>3 workers paralelos (Padrão)</option>
                    <option value={5}>5 workers paralelos (Rápido)</option>
                  </select>
                </div>

                <div className="modal-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setIsBatchModalOpen(false)}
                  >
                    Cancelar
                  </button>
                  <button type="button" className="btn-primary" onClick={handleStartBatchAI}>
                    <Zap size={16} /> Iniciar Triagem em Lote
                  </button>
                </div>
              </div>
            ) : (
              <div className="batch-progress-view animate-fade-in">
                <div className="progress-top-row">
                  <span className="progress-label">Processando com IA...</span>
                  <span className="progress-percentage">{batchProgress?.percentage || 0}%</span>
                </div>

                <div className="progress-bar-track">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${batchProgress?.percentage || 0}%` }}
                  />
                </div>

                <div className="batch-stats-counters">
                  <div className="batch-stat-box">
                    <span>Processados</span>
                    <strong>
                      {batchProgress?.processed || 0} / {batchProgress?.total || 0}
                    </strong>
                  </div>
                  <div className="batch-stat-box text-success">
                    <span>Incluídos</span>
                    <strong>{batchProgress?.included || 0}</strong>
                  </div>
                  <div className="batch-stat-box text-error">
                    <span>Excluídos</span>
                    <strong>{batchProgress?.excluded || 0}</strong>
                  </div>
                  <div className="batch-stat-box text-warning">
                    <span>Pendentes</span>
                    <strong>{batchProgress?.pending || 0}</strong>
                  </div>
                </div>

                <p className="batch-hint-text">
                  A triagem continuará em segundo plano mesmo se você fechar este modal.
                </p>
                <button
                  type="button"
                  className="btn-secondary"
                  style={{ alignSelf: 'center', marginTop: 'var(--space-4)' }}
                  onClick={() => setIsBatchModalOpen(false)}
                >
                  Minimizar e Continuar
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Manual Paper Modal */}
      {isAddModalOpen && (
        <div className="modal-overlay animate-fade-in" onClick={() => setIsAddModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Cadastrar Estudo Manualmente</h2>
              <p>Insira os metadados do artigo a ser triado</p>
            </div>
            <form onSubmit={handleAddManualPaper} className="modal-form">
              <div className="form-group">
                <label>Título do Estudo *</label>
                <input
                  type="text"
                  required
                  placeholder="Título completo do artigo científico..."
                  value={manualTitle}
                  onChange={(e) => setManualTitle(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>Autores</label>
                <input
                  type="text"
                  placeholder="Ex: Silva, J.; Santos, M.; Costa, A."
                  value={manualAuthors}
                  onChange={(e) => setManualAuthors(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Ano de Publicação</label>
                <input
                  type="text"
                  placeholder="Ex: 2024"
                  value={manualYear}
                  onChange={(e) => setManualYear(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Resumo (Abstract)</label>
                <textarea
                  rows={5}
                  placeholder="Cole aqui o resumo completo do artigo..."
                  value={manualAbstract}
                  onChange={(e) => setManualAbstract(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsAddModalOpen(false)}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Adicionar ao Projeto
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Deduplication Report Modal */}
      <DeduplicationReportModal
        report={dedupReport}
        isOpen={isDedupModalOpen}
        onClose={() => setIsDedupModalOpen(false)}
        projectId={id}
      />
    </div>
  )
}
