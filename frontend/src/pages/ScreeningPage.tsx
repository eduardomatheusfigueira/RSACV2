/**
 * RSAC V2 — Screening Page (Triagem 1)
 *
 * Novo Layout Metodológico Otimizado para Leitura e Avaliação:
 * 1. Fila Horizontal de Estudos (no topo): com filtros de status, busca rápida e paginação.
 * 2. Área de Trabalho Lado a Lado (Two-Column Workspace):
 *    - Coluna da Esquerda: Metadados, Ações de Decisão, Análise por IA e Resumo Completo (Abstract).
 *    - Coluna da Direita: Avaliação de Critérios de Inclusão/Exclusão (Checklists interativos) e Observações do Revisor.
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
  ArrowRight,
  ChevronLeft,
  ChevronRight,
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
  FileCode,
  FileX,
  FileCheck,
  Upload,
  FileSearch,
  RotateCcw,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import { useLogStore } from '@/stores/useLogStore'
import type { DeduplicationReport, Paper, Decision, Protocol } from '@/types/api'
import { DeduplicationReportModal } from '@/components/common/DeduplicationReportModal'
import { PageHeader, Button, EmptyState, LoadingState } from '@/components/ui'
import './ScreeningPage.css'

export function ScreeningPage(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject, aiEnabled } = useSettingsStore()
  const { info, success, warn, error } = useLogStore()

  const [papers, setPapers] = useState<Paper[]>([])
  const [protocol, setProtocol] = useState<Protocol | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploadingPdf, setUploadingPdf] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [readingViewMode, setReadingViewMode] = useState<'abstract' | 'pdf_view' | 'pdf_text'>('abstract')
  const [pdfExtractedText, setPdfExtractedText] = useState<string | null>(null)
  const [loadingPdfText, setLoadingPdfText] = useState(false)
  const [acquiringPdf, setAcquiringPdf] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
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

  // Horizontal Queue Scroll Ref
  const queueScrollRef = useRef<HTMLDivElement | null>(null)

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
        // Se o filtro atual estiver ativo e a nova decisão for diferente, remove da lista filtrada e avança
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

        if (newPapers.length === 0 && page > 1) {
          setPage((prev) => Math.max(1, prev - 1))
        } else if (newPapers.length === 0) {
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


  const handleUploadFile = async (file: File) => {
    if (!id || !selectedPaper) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      error('Triagem', 'O arquivo selecionado não é um PDF válido (.pdf).')
      return
    }

    try {
      setUploadingPdf(true)
      const res: any = await api.uploadPaperPDF(id, selectedPaper.id, file)
      const updated = { ...selectedPaper, pdf_path: res.pdf_path, pdf_text_extracted: true }
      setSelectedPaper(updated)
      setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? updated : p)))
      setPdfExtractedText(null)
      success('Triagem', 'PDF anexado e vinculado com sucesso!')
      if (res.is_scanned) {
        warn('Triagem', 'O PDF anexado é digitalizado (imagem): não há texto selecionável.')
      }
    } catch (err: any) {
      error('Triagem', `Falha no upload do PDF: ${err.message}`)
    } finally {
      setUploadingPdf(false)
    }
  }

  /**
   * Busca o texto completo pelas mesmas vias usadas na Extração — o link
   * coletado normalmente é a página do registro, não o arquivo.
   */
  const handleAcquirePdf = async () => {
    if (!id || !selectedPaper) return
    try {
      setAcquiringPdf(true)
      const res = await api.acquirePaperPDF(id, selectedPaper.id)
      if (res.success) {
        const updated = { ...selectedPaper, pdf_path: res.pdf_path, pdf_text_extracted: true }
        setSelectedPaper(updated)
        setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? updated : p)))
        setPdfExtractedText(null)
        success('Triagem', `PDF obtido (${res.strategy})`, res.message)
      } else {
        warn(
          'Triagem',
          'Busca automática de PDF sem sucesso',
          `${res.attempts?.length || 0} caminho(s) tentado(s). ${res.message}`
        )
      }
    } catch (err: any) {
      error('Triagem', `Falha ao buscar PDF: ${err.message}`)
    } finally {
      setAcquiringPdf(false)
    }
  }

  const handleToggleReadingView = async (mode: 'abstract' | 'pdf_view' | 'pdf_text') => {
    setReadingViewMode(mode)
    if (mode === 'pdf_text' && selectedPaper?.pdf_path && !pdfExtractedText && id && selectedPaper) {
      try {
        setLoadingPdfText(true)
        const res = await api.getPaperPdfText(id, selectedPaper.id)
        setPdfExtractedText(res.text)
      } catch (err: any) {
        setPdfExtractedText('[Não foi possível extrair o texto deste PDF ou o arquivo é escaneado em imagem.]')
      } finally {
        setLoadingPdfText(false)
      }
    }
  }

  const handleSelectNextPaper = () => {
    if (!selectedPaper || papers.length === 0) return
    const currentIndex = papers.findIndex((p) => p.id === selectedPaper.id)
    if (currentIndex < papers.length - 1) {
      setSelectedPaper(papers[currentIndex + 1])
      setAiLastResult(null)
    } else if (page < totalPages) {
      setPage(page + 1)
    }
  }

  const handleSelectPrevPaper = () => {
    if (!selectedPaper || papers.length === 0) return
    const currentIndex = papers.findIndex((p) => p.id === selectedPaper.id)
    if (currentIndex > 0) {
      setSelectedPaper(papers[currentIndex - 1])
      setAiLastResult(null)
    } else if (page > 1) {
      setPage(page - 1)
    }
  }

  const scrollQueue = (direction: 'left' | 'right') => {
    if (!queueScrollRef.current) return
    const offset = direction === 'left' ? -350 : 350
    queueScrollRef.current.scrollBy({ left: offset, behavior: 'smooth' })
  }

  // Keyboard Shortcuts (Arrow keys for navigation, I for Include, E for Exclude, P for Pending)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (document.activeElement?.tagName || '').toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return

      if (e.key === 'ArrowRight') {
        e.preventDefault()
        handleSelectNextPaper()
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        handleSelectPrevPaper()
      } else if (e.key === 'i' || e.key === 'I') {
        if (selectedPaper) {
          e.preventDefault()
          handleDecision(selectedPaper.id, 'Incluído')
        }
      } else if (e.key === 'e' || e.key === 'E') {
        if (selectedPaper) {
          e.preventDefault()
          handleDecision(selectedPaper.id, 'Excluído')
        }
      } else if (e.key === 'p' || e.key === 'P') {
        if (selectedPaper) {
          e.preventDefault()
          handleDecision(selectedPaper.id, 'Pendente')
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedPaper, papers, page, totalPages])

  const handleSingleAIScreening = async () => {
    if (!id || !selectedPaper) return
    try {
      setIsAiScreeningSingle(true)
      setAiLastResult(null)
      info('Assistência', `Iniciando triagem assistida do estudo "${selectedPaper.title.slice(0, 50)}..."`)

      const res = await api.screenSinglePaperAI(id, selectedPaper.id)
      setAiLastResult(res)

      success('Assistência', `Parecer da Assistência: ${res.decision} (Confiança: ${(res.confidence * 100).toFixed(0)}%)`, `Justificativa: ${res.justification || (res as any).reasoning}\nCritérios atendidos: ${(res as any).criteria_met?.join(', ') || 'Nenhum'}`)

      const updatedPaper = await api.getPaper(id, selectedPaper.id)
      setSelectedPaper(updatedPaper)
      setPapers(papers.map((p) => (p.id === selectedPaper.id ? updatedPaper : p)))
      loadStats(id)
    } catch (err: any) {
      error('Assistência', `Falha na triagem com assistência: ${err.message}`)
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

  // ── Sincronização de Ações com o Ribbon Bar ─────────────────────────
  const registerRibbonActions = useRibbonStore((s) => s.registerActions)
  const unregisterRibbonActions = useRibbonStore((s) => s.unregisterActions)

  useEffect(() => {
    registerRibbonActions({
      decisionInclude: () => {
        if (selectedPaper) handleDecision(selectedPaper.id, 'Incluído')
      },
      decisionExclude: () => {
        if (selectedPaper) handleDecision(selectedPaper.id, 'Excluído')
      },
      decisionPending: () => {
        if (selectedPaper) handleDecision(selectedPaper.id, 'Pendente')
      },
      screenAiSingle: handleSingleAIScreening,
      screenAiBatch: handleStartBatchAI,
      /* Só captura `id` (estável na rota) e setters — a closure não envelhece,
         por isso fica fora das dependências. */
      openDedupModal: () => {
        void handleOpenDedupModal()
      },
      setDecisionFilter: (filter: string) => {
        setDecisionFilter(filter)
        setPage(1)
      },
      activeDecisionFilter: decisionFilter,
      canScreenSingle: !!selectedPaper,
    })
    return () => {
      unregisterRibbonActions([
        'decisionInclude',
        'decisionExclude',
        'decisionPending',
        'screenAiSingle',
        'screenAiBatch',
        'openDedupModal',
        'setDecisionFilter',
        'activeDecisionFilter',
        'canScreenSingle',
      ])
    }
  }, [
    registerRibbonActions,
    unregisterRibbonActions,
    selectedPaper,
    handleDecision,
    handleSingleAIScreening,
    handleStartBatchAI,
    decisionFilter,
  ])

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

  const handleOpenDedupModal = async () => {
    if (!id) return
    try {
      setIsDeduplicating(true)
      const report = await api.getDeduplicationReport(id)
      setDedupReport(report)
      setIsDedupModalOpen(true)
    } catch (err) {
      console.error('Erro ao carregar relatório de deduplicação:', err)
    } finally {
      setIsDeduplicating(false)
    }
  }

  const selectedIndex = papers.findIndex((p) => p.id === selectedPaper?.id)

  return (
    <div className="screening-page animate-fade-in">
      <PageHeader
        title="Triagem de Estudos (Triagem 1)"
        onBack={() => navigate('/projects')}
        subtitle={
          <span>
            Projeto: <strong>{activeProject?.title}</strong> — Avaliação rápida de título, resumo e critérios de
            inclusão/exclusão
          </span>
        }
        status={
          isDeduplicating && (
            <span className="save-indicator animate-fade-in" role="status" aria-live="polite">
              <Layers size={13} aria-hidden="true" /> Auditando duplicatas…
            </span>
          )
        }
        primaryAction={
          /* "Auditoria de Duplicatas" e "Triagem em Lote" saíram do cabeçalho:
             agora são despachadas pelo ribbon (`openDedupModal`,
             `screenAiBatch`), que é onde o resto dos comandos da etapa vive. */
          <Button variant="primary" size="md" onClick={() => setIsAddModalOpen(true)} leftIcon={<Plus size={14} />}>
            Adicionar Manual
          </Button>
        }
      />

      {/* ═══════════════════════════════════════════════════════════════════
          FILA HORIZONTAL DE TRABALHOS (ACIMA)
          Controles de busca, contadores de status, paginação e faixa de cards
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="screening-queue-container">
        {/* Top Control Bar of the Queue */}
        <div className="queue-controls-bar">
          <div className="queue-filter-buttons">
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
              <Clock size={14} />
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
              <CheckCircle2 size={14} />
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
              <XCircle size={14} />
              <span className="count-label">Excluídos</span>
              <span className="count-num">{stats.excluded}</span>
            </button>
          </div>

          <div className="queue-search-input-wrapper">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              placeholder="Filtrar por título, autor, resumo..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setPage(1)
              }}
            />
          </div>

          <div className="queue-pagination-inline">
            <button
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="btn-pagination-nav"
              title="Página Anterior"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="pagination-text">
              Pág <strong>{page}</strong> de {totalPages} ({totalCount} estudos)
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              className="btn-pagination-nav"
              title="Próxima Página"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>

        {/* Horizontal Strip with Chevron Scroll Buttons */}
        <div className="queue-strip-wrapper">
          <button
            type="button"
            className="btn-queue-scroll left"
            onClick={() => scrollQueue('left')}
            title="Rolar fila para a esquerda"
          >
            <ChevronLeft size={16} />
          </button>

          <div className="horizontal-papers-strip" ref={queueScrollRef}>
            {loading ? (
              <LoadingState size="inline" label="Carregando fila de estudos…" />
            ) : papers.length === 0 ? (
              <EmptyState
                size="inline"
                icon={<FileText size={18} aria-hidden="true" />}
                title="Nenhum estudo nesta fila"
                description="Nenhum registro corresponde ao filtro de decisão e à busca ativos."
              />
            ) : (
              papers.map((paper, idx) => {
                const isSelected = selectedPaper?.id === paper.id
                return (
                  <div
                    key={paper.id}
                    className={`queue-paper-card ${isSelected ? 'selected' : ''} dec-${paper.decision.toLowerCase()}`}
                    onClick={() => {
                      setSelectedPaper(paper)
                      setAiLastResult(null)
                    }}
                    title={paper.title}
                  >
                    <div className="queue-card-meta">
                      <span className={`badge-decision badge-${paper.decision.toLowerCase()}`}>
                        {paper.decision}
                      </span>
                      {paper.ai_confidence !== null && (
                        <span className="badge-ai-conf" title="Confiança da Assistência">
                          <Sparkles size={10} /> {Math.round(paper.ai_confidence * 100)}%
                        </span>
                      )}
                      {paper.year && <span className="queue-card-year">{paper.year}</span>}
                    </div>
                    <h4 className="queue-card-title">{paper.title}</h4>
                    {paper.authors && (
                      <p className="queue-card-authors">{paper.authors}</p>
                    )}
                  </div>
                )
              })
            )}
          </div>

          <button
            type="button"
            className="btn-queue-scroll right"
            onClick={() => scrollQueue('right')}
            title="Rolar fila para a direita"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          ÁREA DE TRABALHO PRINCIPAL LADO A LADO (TWO-COLUMN WORKSPACE)
          Coluna 1: Texto e Metadados do Estudo | Coluna 2: Critérios e Observações
      ═══════════════════════════════════════════════════════════════════ */}
      {selectedPaper ? (
        <div className="screening-workbench-grid animate-fade-in">
          {/* ── COLUNA DA ESQUERDA: TEXTO, METADADOS & AÇÕES ────────────── */}
          <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleUploadFile(file)
          if (fileInputRef.current) fileInputRef.current.value = ''
        }}
        accept=".pdf,application/pdf"
        style={{ display: 'none' }}
      />
          <div
            className={`study-reading-pane ${isDragOver ? 'drag-over-active' : ''}`}
            onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(true) }}
            onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(false) }}
            onDrop={(e) => {
              e.preventDefault(); e.stopPropagation(); setIsDragOver(false)
              const file = e.dataTransfer.files?.[0]
              if (file) handleUploadFile(file)
            }}
          >
            {/* Action Bar with Quick Decision & Navigation */}
            <div className="study-actions-toolbar">
              <div className="decision-buttons-group">
                <button
                  className={`btn-dec include ${selectedPaper.decision === 'Incluído' ? 'active' : ''}`}
                  onClick={() => handleDecision(selectedPaper.id, 'Incluído')}
                  title="Incluir estudo na revisão (Atalho: tecla 'I')"
                >
                  <CheckCircle2 size={16} />
                  <span>Incluir</span>
                  <span className="key-hint">I</span>
                </button>
                <button
                  className={`btn-dec exclude ${selectedPaper.decision === 'Excluído' ? 'active' : ''}`}
                  onClick={() => handleDecision(selectedPaper.id, 'Excluído')}
                  title="Excluir estudo da revisão (Atalho: tecla 'E')"
                >
                  <XCircle size={16} />
                  <span>Excluir</span>
                  <span className="key-hint">E</span>
                </button>
                <button
                  className={`btn-dec pending ${selectedPaper.decision === 'Pendente' ? 'active' : ''}`}
                  onClick={() => handleDecision(selectedPaper.id, 'Pendente')}
                  title="Manter como Pendente (Atalho: tecla 'P')"
                >
                  <Clock size={16} />
                  <span>Pendente</span>
                  <span className="key-hint">P</span>
                </button>
              </div>

              <div className="toolbar-secondary-actions">
                {aiEnabled && (
                  <button
                    className="btn-ai-triage"
                    onClick={handleSingleAIScreening}
                    disabled={isAiScreeningSingle}
                    title="Avaliar este artigo com Assistência"
                  >
                    {isAiScreeningSingle ? (
                      <>
                        <RefreshCw size={14} className="animate-spin" /> Analisando...
                      </>
                    ) : (
                      <>
                        <Sparkles size={14} /> Triar com Assistência
                      </>
                    )}
                  </button>
                )}

                <div className="study-nav-arrows">
                  <button
                    type="button"
                    className="btn-study-step"
                    onClick={handleSelectPrevPaper}
                    title="Estudo Anterior (Atalho: Seta Esquerda)"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span className="study-counter-label">
                    {selectedIndex >= 0 ? selectedIndex + 1 : 1} / {papers.length}
                  </span>
                  <button
                    type="button"
                    className="btn-study-step"
                    onClick={handleSelectNextPaper}
                    title="Próximo Estudo (Atalho: Seta Direita)"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>

            {/* Reading Content */}
            <div className="study-reading-content">
              <h2 className="study-title">{selectedPaper.title}</h2>

              <div className="study-meta-grid">
                {selectedPaper.authors && (
                  <div className="meta-pill">
                    <User size={13} className="icon-accent" />
                    <span>{selectedPaper.authors}</span>
                  </div>
                )}
                {selectedPaper.year && (
                  <div className="meta-pill">
                    <Calendar size={13} className="icon-accent" />
                    <span>Ano: <strong>{selectedPaper.year}</strong></span>
                  </div>
                )}
                {selectedPaper.institution && (
                  <div className="meta-pill">
                    <Building size={13} className="icon-accent" />
                    <span>{selectedPaper.institution}</span>
                  </div>
                )}
                {selectedPaper.doi && (
                  <div className="meta-pill">
                    <ExternalLink size={13} className="icon-accent" />
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
                      <Sparkles size={14} /> Parecer da Assistência ({aiLastResult.model_used})
                    </div>
                    <span className="ai-confidence">
                      Confiança: {Math.round(aiLastResult.confidence * 100)}%
                    </span>
                  </div>
                  <p className="ai-justification">{aiLastResult.justification}</p>
                </div>
              )}

              {/* Caixa de Leitura: Resumo | PDF original | Texto extraído */}
              <div className="study-abstract-container">
                <div className="abstract-header-row">
                  <FileText size={16} className="icon-accent" />
                  <h3>
                    {readingViewMode === 'abstract'
                      ? 'Resumo do Estudo (Abstract)'
                      : readingViewMode === 'pdf_view'
                        ? 'Documento Original (PDF)'
                        : 'Texto Integral Extraído do PDF'}
                  </h3>

                  <div className="screening-pdf-tools">
                    <div className="view-mode-toggle-group">
                      <button
                        type="button"
                        className={`btn-view-mode ${readingViewMode === 'abstract' ? 'active' : ''}`}
                        onClick={() => handleToggleReadingView('abstract')}
                      >
                        Resumo
                      </button>
                      <button
                        type="button"
                        className={`btn-view-mode ${readingViewMode === 'pdf_view' ? 'active' : ''}`}
                        onClick={() => handleToggleReadingView('pdf_view')}
                        disabled={!selectedPaper.pdf_path}
                      >
                        PDF
                      </button>
                      <button
                        type="button"
                        className={`btn-view-mode ${readingViewMode === 'pdf_text' ? 'active' : ''}`}
                        onClick={() => handleToggleReadingView('pdf_text')}
                        disabled={!selectedPaper.pdf_path}
                      >
                        Texto
                      </button>
                    </div>

                    <button
                      type="button"
                      className="btn-pdf-action primary"
                      onClick={handleAcquirePdf}
                      disabled={acquiringPdf}
                      title="Procura o texto completo por DOI, bases de acesso aberto e na página de origem"
                    >
                      {acquiringPdf ? (
                        <>
                          <RefreshCw size={12} className="animate-spin" /> Procurando...
                        </>
                      ) : (
                        <>
                          <FileSearch size={12} /> {selectedPaper.pdf_path ? 'Rebuscar' : 'Buscar PDF'}
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      className="btn-pdf-action"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploadingPdf}
                      title="Anexar arquivo PDF do computador"
                    >
                      {uploadingPdf ? (
                        <>
                          <RefreshCw size={12} className="animate-spin" /> Anexando...
                        </>
                      ) : (
                        <>
                          <Upload size={12} /> Anexar
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {readingViewMode === 'pdf_view' && selectedPaper.pdf_path && id ? (
                  <div className="pdf-embed-container">
                    <iframe
                      key={selectedPaper.id}
                      className="pdf-embed-frame"
                      title={`PDF — ${selectedPaper.title}`}
                      src={api.getPaperPdfUrl(id, selectedPaper.id)}
                    />
                  </div>
                ) : (
                  <div className="abstract-reading-card">
                    {readingViewMode === 'pdf_text' ? (
                      loadingPdfText ? (
                        <div className="empty-abstract-state">
                          <RefreshCw size={22} className="animate-spin icon-accent" />
                          <p>Extraindo o texto integral do PDF...</p>
                        </div>
                      ) : (
                        <p className="abstract-text">{pdfExtractedText}</p>
                      )
                    ) : selectedPaper.abstract ? (
                      <p className="abstract-text">{selectedPaper.abstract}</p>
                    ) : (
                      <div className="empty-abstract-state">
                        <AlertCircle size={24} />
                        <p>Resumo não disponível nos metadados coletados deste registro.</p>
                        <p className="empty-abstract-hint">
                          Busque ou anexe o PDF acima para ler o texto completo do estudo.
                        </p>
                        {selectedPaper.doi && (
                          <a
                            href={`https://doi.org/${selectedPaper.doi}`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn-secondary small"
                          >
                            <ExternalLink size={13} /> Consultar via DOI
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── COLUNA DA DIREITA: CRITÉRIOS DE ELEGIBILIDADE & OBSERVAÇÕES ── */}
          <div className="criteria-evaluation-pane">
            <div className="criteria-pane-header">
              <div className="criteria-pane-title">
                <CheckSquare size={18} className="icon-accent" />
                <h3>Critérios de Elegibilidade</h3>
              </div>

              {protocol && protocol.criteria && protocol.criteria.length > 0 && (
                <div className="criteria-actions-top">
                  {inclusionCriteria.length > 0 && (
                    <button
                      type="button"
                      className="btn-criteria-action"
                      onClick={handleCheckAllInclusion}
                      title="Marcar todos os critérios de inclusão como atendidos"
                    >
                      <CheckCheck size={13} /> Marcar Inclusões
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn-criteria-action text-muted"
                    onClick={handleClearCriteria}
                    title="Desmarcar todas as avaliações deste estudo"
                  >
                    <RotateCcw size={12} /> Limpar
                  </button>
                </div>
              )}
            </div>

            {/* Criteria Badges & Smart Recommendations */}
            {protocol && protocol.criteria && protocol.criteria.length > 0 ? (
              <div className="criteria-pane-body">
                <div className="criteria-summary-badges">
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
                        <XCircle size={13} /> Excluir Estudo
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
                        <CheckCircle2 size={13} /> Incluir Estudo
                      </button>
                    )}
                  </div>
                ) : null}

                {/* Inclusion Criteria Checklist */}
                <div className="criteria-group inc-group">
                  <div className="group-header">
                    <span className="group-label inc">Critérios de Inclusão</span>
                    <span className="group-score">{incMetCount} / {inclusionCriteria.length}</span>
                  </div>

                  {inclusionCriteria.length === 0 ? (
                    <p className="no-crit-hint">Nenhum critério de inclusão cadastrado no protocolo.</p>
                  ) : (
                    <div className="criteria-list">
                      {inclusionCriteria.map((c) => {
                        const isChecked = !!(c.id && selectedPaper.criteria_evaluations?.[c.id])
                        return (
                          <label
                            key={c.id || c.text}
                            className={`criterion-card inc-card ${isChecked ? 'checked' : ''}`}
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

                {/* Exclusion Criteria Checklist */}
                <div className="criteria-group exc-group">
                  <div className="group-header">
                    <span className="group-label exc">Critérios de Exclusão</span>
                    <span className="group-score">{excMetCount} / {exclusionCriteria.length}</span>
                  </div>

                  {exclusionCriteria.length === 0 ? (
                    <p className="no-crit-hint">Nenhum critério de exclusão cadastrado no protocolo.</p>
                  ) : (
                    <div className="criteria-list">
                      {exclusionCriteria.map((c) => {
                        const isChecked = !!(c.id && selectedPaper.criteria_evaluations?.[c.id])
                        return (
                          <label
                            key={c.id || c.text}
                            className={`criterion-card exc-card ${isChecked ? 'checked' : ''}`}
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

                {/* Reviewer Notes & Justifications */}
                <div className="reviewer-notes-box">
                  <div className="notes-header">
                    <FileText size={14} className="icon-accent" />
                    <h4>Observações & Justificativas do Revisor</h4>
                  </div>
                  <textarea
                    rows={4}
                    className="reviewer-textarea"
                    placeholder="Anote justificativas para inclusão/exclusão, dúvidas sobre o método ou observações contextuais deste estudo..."
                    value={selectedPaper.observations || ''}
                    onChange={(e) => handleObservationsChange(e.target.value)}
                  />
                </div>
              </div>
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
        </div>
      ) : (
        <div className="no-selection-workbench">
          <BookOpen size={48} strokeWidth={1} />
          <h3>Nenhum estudo selecionado</h3>
          <p>Selecione um artigo na fila horizontal acima para revisar os detalhes e marcar os critérios.</p>
        </div>
      )}

      {/* Batch AI Screening Modal */}
      {isBatchModalOpen && (
        <div className="modal-overlay animate-fade-in" onClick={() => !isBatchRunning && setIsBatchModalOpen(false)}>
          <div className="modal-content batch-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Triagem em Lote com Assistência</h2>
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
                  <span className="progress-label">Processando com Assistência...</span>
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
