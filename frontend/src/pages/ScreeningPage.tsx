/**
 * Revsist — Screening Page (Triagem 1)
 *
 * Novo Layout Metodológico Otimizado para Leitura e Avaliação:
 * 1. Fila Horizontal de Estudos (no topo): com filtros de status, busca rápida e paginação.
 * 2. Área de Trabalho Lado a Lado (Two-Column Workspace):
 *    - Coluna da Esquerda: Metadados, Ações de Decisão, Análise por Assistência e Resumo Completo (Abstract).
 *    - Coluna da Direita: Avaliação de Critérios de Inclusão/Exclusão (Checklists interativos) e Observações do Revisor.
 */

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as Tabs from '@radix-ui/react-tabs'
import {
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Filter,
  ExternalLink,
  BookOpen,
  ArrowRight,
  ArrowUpDown,
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
  Globe,
  Maximize2,
  StopCircle,
  Edit3,
  Save,
  X,
  Users,
} from 'lucide-react'
import { api, foiCancelado } from '@/api/client'
import { useProjectChannel } from '@/hooks/useProjectChannel'
import { useAuthStore } from '@/stores/useAuthStore'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import { useLogStore } from '@/stores/useLogStore'
import type { DeduplicationReport, Paper, Decision, Protocol } from '@/types/api'
import { DeduplicationReportModal } from '@/components/common/DeduplicationReportModal'
import {
  BatchScreeningModal,
  type BatchScreeningItem,
  type CurrentScreeningStudy,
} from '@/components/common/BatchScreeningModal'
import {
  PageHeader,
  Button,
  Card,
  EmptyState,
  LoadingState,
  toast,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui'
import './ScreeningPage.css'

export function getDoiUrl(doi?: string | null): string {
  if (!doi) return ''
  const trimmed = doi.trim()
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed
  }
  return `https://doi.org/${trimmed}`
}

export function getSourceUrl(paper?: Paper | null): string {
  if (!paper) return ''
  if (paper.download_url && (paper.download_url.startsWith('http://') || paper.download_url.startsWith('https://'))) {
    return paper.download_url
  }
  if (paper.doi) {
    return getDoiUrl(paper.doi)
  }
  if (paper.pdf_resolved_url && (paper.pdf_resolved_url.startsWith('http://') || paper.pdf_resolved_url.startsWith('https://'))) {
    return paper.pdf_resolved_url
  }
  return ''
}

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
  const [mobileTab, setMobileTab] = useState<'article' | 'criteria' | 'queue'>('article')

  // Abstract Inline Editing State
  const [isEditingAbstract, setIsEditingAbstract] = useState(false)
  const [editedAbstractText, setEditedAbstractText] = useState('')
  const [savingAbstract, setSavingAbstract] = useState(false)

  // Deduplication Report State
  const [dedupReport, setDedupReport] = useState<DeduplicationReport | null>(null)
  const [isDedupModalOpen, setIsDedupModalOpen] = useState(false)
  const [isDeduplicating, setIsDeduplicating] = useState(false)

  // Filters & Pagination
  const [decisionFilter, setDecisionFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sortBy, setSortBy] = useState<string>('year_desc')
  /** `null` = todos; `false` = só os sem resumo utilizável. */
  const [filtroDeResumo, setFiltroDeResumo] = useState<boolean | null>(null)
  const [conflictCount, setConflictCount] = useState(0)
  const [resolvingConflict, setResolvingConflict] = useState(false)
  const [conflictNotes, setConflictNotes] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  const isCoordinator = activeProject?.my_role === 'coordenador'
  const isBlindMode = activeProject?.collaboration_mode === 'cega_por_pares'

  // Stats
  const [stats, setStats] = useState({
    total: 0,
    included: 0,
    excluded: 0,
    pending: 0,
    /* Pendentes que a triagem assistida não alcança, por não terem resumo
       utilizável. Contados à parte de propósito: eles saem da fila da
       assistência, mas continuam no acervo e no fluxo PRISMA — e um número que
       some é um número que ninguém reconcilia depois. */
    pendingSemResumo: 0,
    pendingTriaveis: 0,
  })

  // Horizontal Queue Scroll Ref
  const queueScrollRef = useRef<HTMLDivElement | null>(null)

  // AI Single Screening State
  const [isAiScreeningSingle, setIsAiScreeningSingle] = useState(false)
  /* A triagem de um estudo é uma chamada só, mas pode demorar — e enquanto ela
     não volta o botão fica travado. O controlador devolve a tela a quem
     desistiu, em vez de exigir que se espere ou se feche o programa. */
  const triagemUnicaAbortRef = useRef<AbortController | null>(null)
  const [aiLastResult, setAiLastResult] = useState<any>(null)

  // AI Batch Screening Modal & Live Progress State
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false)
  const [isBatchRunning, setIsBatchRunning] = useState(false)
  const [batchProgress, setBatchProgress] = useState<{
    processed: number
    total: number
    percentage: number
    included: number
    excluded: number
    pending: number
    /** Paralelismo e pausa vigentes, ajustados pelo servidor. */
    ritmo?: import('@/types/api').RitmoDoLote | null
  } | null>(null)
  const [currentScreeningStudy, setCurrentScreeningStudy] = useState<CurrentScreeningStudy | null>(null)
  /* A relação do lote, na ordem de triagem. Substitui o feed de "recém-triados":
     o pesquisador precisa ver o CONJUNTO — o que já foi, o que está sendo e o
     que falta —, e não apenas os últimos que passaram. */
  const [itensDoLote, setItensDoLote] = useState<import('@/types/api').ItemDoLote[]>([])
  /** Último estudo concluído do lote — usado na barra flutuante. */
  const ultimoConcluidoDoLote = [...itensDoLote].reverse().find((i) => i.status === 'concluido')
  const wsRef = useRef<WebSocket | null>(null)
  const wsRetryRef = useRef<number | null>(null)
  /** Quantas reconexões seguidas falharam — alimenta o recuo progressivo. */
  const tentativasDeCanalRef = useRef<number>(0)
  /** Consulta periódica do lote — a rede de segurança do canal. */
  const pollLoteRef = useRef<number | null>(null)
  /** Instante da última mensagem de lote vinda do canal. */
  const ultimoEventoDoCanalRef = useRef<number>(0)
  /** O canal está entregando? Alimenta o aviso na janela do lote. */
  const [canalAoVivo, setCanalAoVivo] = useState(true)
  const wsEncerradoPelaTelaRef = useRef(false)

  // Quick add manual paper modal
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [manualTitle, setManualTitle] = useState('')
  const [manualAuthors, setManualAuthors] = useState('')
  const [manualYear, setManualYear] = useState('')
  const [manualAbstract, setManualAbstract] = useState('')

  // Sync abstract text when selectedPaper changes
  useEffect(() => {
    setIsEditingAbstract(false)
    setEditedAbstractText(selectedPaper?.abstract || '')
  }, [selectedPaper?.id])

  useEffect(() => {
    if (id) {
      loadInitialData(id)
      initScreeningWebSocket(id)
      restaurarEstadoDoLote(id)
    }

    return () => {
      wsEncerradoPelaTelaRef.current = true
      pararAcompanhamentoDoLote()
      if (wsRetryRef.current !== null) {
        window.clearTimeout(wsRetryRef.current)
        wsRetryRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [id])

  useEffect(() => {
    if (id) {
      loadPapers(id)
    }
  }, [id, decisionFilter, statusFilter, filtroDeResumo, searchTerm, page, sortBy])

  const handleBatchScreeningMessage = useCallback(
    (msg: any) => {
      if (!msg || typeof msg !== 'object') return
      const projectId = id || activeProject?.id || ''

      if (typeof msg.type === 'string' && msg.type.startsWith('batch_screening')) {
        ultimoEventoDoCanalRef.current = Date.now()
        setCanalAoVivo(true)
      }

      if (msg.type === 'batch_screening_started') {
        setIsBatchRunning(true)
        if (Array.isArray(msg.itens)) setItensDoLote(msg.itens)
        setBatchProgress({
          processed: 0,
          total: msg.total,
          percentage: 0,
          included: 0,
          excluded: 0,
          pending: msg.total,
        })
        info('Triagem', msg.message || `Iniciando triagem em lote de ${msg.total} estudos pendentes...`)
      } else if (msg.type === 'batch_screening_item_start') {
        setIsBatchRunning(true)
        setItensDoLote((rel) =>
          rel.map((i) => (i.id === msg.paper_id ? { ...i, status: 'em_analise' as const } : i))
        )
        setCurrentScreeningStudy({
          paper_id: msg.paper_id,
          title: msg.paper_title || 'Estudo em análise',
          authors: msg.paper_authors,
          year: msg.paper_year,
          total: msg.total,
        })
      } else if (msg.type === 'batch_screening_item_skipped') {
        // O estudo que o provedor recusou em todas as passadas. Ele não foi
        // triado e segue pendente — e é dito na relação, porque enquanto
        // desaparecia em silêncio o contador parava a um estudo do fim e o
        // item ficava eternamente "na fila".
        setItensDoLote((rel) =>
          rel.map((i) =>
            i.id === msg.paper_id
              ? {
                  ...i,
                  status: 'nao_triado' as const,
                  justification:
                    msg.message ||
                    'O provedor de IA recusou as tentativas desta rodada. O estudo segue pendente.',
                }
              : i
          )
        )
      } else if (msg.type === 'batch_screening_progress') {
        setIsBatchRunning(true)
        setBatchProgress({
          processed: msg.processed,
          total: msg.total,
          percentage: msg.percentage,
          included: msg.included_count,
          excluded: msg.excluded_count,
          pending: msg.pending_count,
          ritmo: msg.ritmo ?? null,
        })

        if (msg.current_paper_id) {
          setItensDoLote((rel) =>
            rel.map((i) =>
              i.id === msg.current_paper_id
                ? {
                    ...i,
                    status: 'concluido' as const,
                    decision: msg.decision,
                    confidence: msg.confidence,
                    justification: msg.justification,
                  }
                : i
            )
          )

          // Atualiza o estudo correspondente em memória imediatamente
          setPapers((prev) =>
            prev.map((p) =>
              p.id === msg.current_paper_id
                ? {
                    ...p,
                    decision: msg.decision,
                    ai_confidence: msg.confidence,
                    observations: msg.justification || p.observations,
                  }
                : p
            )
          )

          setSelectedPaper((prev) => {
            if (prev && prev.id === msg.current_paper_id) {
              return {
                ...prev,
                decision: msg.decision,
                ai_confidence: msg.confidence,
                observations: msg.justification || prev.observations,
              }
            }
            return prev
          })
        }

        info(
          'Triagem',
          `Triagem em lote: ${msg.processed}/${msg.total} (${msg.percentage}%)`,
          `Estudo: "${msg.current_paper_title}" ➔ Decisão: ${msg.decision}`
        )
      } else if (msg.type === 'batch_screening_completed') {
        pararAcompanhamentoDoLote()
        setIsBatchRunning(false)
        setCurrentScreeningStudy(null)
        setBatchProgress({
          processed: msg.total_processed,
          total: msg.total_processed + (msg.pending ?? 0),
          percentage: 100,
          included: msg.included,
          excluded: msg.excluded,
          pending: msg.pending ?? 0,
        })
        success(
          'Triagem',
          'Triagem em lote finalizada com sucesso!',
          `Total: ${msg.total_processed} | Incluídos: ${msg.included} | Excluídos: ${msg.excluded}`
        )
        toast.success('Triagem em lote concluída', {
          description: `${msg.total_processed} estudos processados (${msg.included} incluídos, ${msg.excluded} excluídos).`,
        })
        if (projectId) {
          loadStats(projectId)
          loadPapers(projectId)
        }
      } else if (msg.type === 'batch_screening_cancelled') {
        pararAcompanhamentoDoLote()
        setIsBatchRunning(false)
        setCurrentScreeningStudy(null)
        info(
          'Triagem',
          msg.message || 'Triagem em lote interrompida.',
          `Processados até parar: ${msg.processed ?? 0} de ${msg.total ?? 0}`
        )
        toast.info('Triagem em lote interrompida', {
          description: `${msg.processed ?? 0} de ${msg.total ?? 0} estudos foram triados antes da parada.`,
        })
        if (projectId) {
          loadStats(projectId)
          loadPapers(projectId)
        }
      } else if (
        msg.type === 'batch_screening_empty' ||
        msg.type === 'batch_screening_failed'
      ) {
        pararAcompanhamentoDoLote()
        setIsBatchRunning(false)
        setCurrentScreeningStudy(null)
        if (typeof msg.processed === 'number' && typeof msg.total === 'number') {
          setBatchProgress((prev) => ({
            processed: msg.processed,
            total: msg.total,
            percentage: msg.total ? Math.round((msg.processed / msg.total) * 1000) / 10 : 0,
            included: prev?.included ?? 0,
            excluded: prev?.excluded ?? 0,
            pending: msg.total - msg.processed,
          }))
        } else {
          setBatchProgress(null)
        }
        const mensagem = msg.message || 'A triagem em lote não pôde ser executada.'
        error('Triagem', mensagem)
        toast.error('Triagem em lote interrompida', {
          description: mensagem,
          duration: 12000,
        })
        if (projectId) {
          loadStats(projectId)
          loadPapers(projectId)
        }
      }
    },
    [id, activeProject?.id, info, success, error]
  )

  const initScreeningWebSocket = (projectId: string) => {
    try {
      wsEncerradoPelaTelaRef.current = false
      const wsUrl = api.getScreeningWebSocketUrl(projectId)
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      let pingTimer: number | null = null

      ws.onopen = () => {
        tentativasDeCanalRef.current = 0
        setCanalAoVivo(true)
        info('WebSocket', 'Canal ao vivo conectado.')
        pingTimer = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 20000)
      }

      ws.onmessage = (event) => {
        try {
          if (event.data === 'pong') return
          const msg = JSON.parse(event.data)
          handleBatchScreeningMessage(msg)
        } catch {
          // ignore non-json
        }
      }

      ws.onclose = (evento) => {
        if (pingTimer !== null) {
          window.clearInterval(pingTimer)
          pingTimer = null
        }
        if (wsEncerradoPelaTelaRef.current) return
        setCanalAoVivo(false)

        /* 1008 é recusa de credencial ou de origem: insistir só repete a
           recusa. Registrar o motivo é o que faltava — a falha era silenciosa,
           e "canal indisponível" não dizia se ele fora recusado ou se nem
           chegara a ser tentado. */
        if (evento.code === 1008) {
          error(
            'WebSocket',
            'Canal ao vivo recusado: credencial ou origem não autorizada.',
            `Código ${evento.code}. ${evento.reason || ''}`
          )
          return
        }
        info('WebSocket', `Canal ao vivo caiu (código ${evento.code}). Reconectando...`)

        tentativasDeCanalRef.current += 1
        const espera = Math.min(30000, 3000 * 2 ** (tentativasDeCanalRef.current - 1))
        wsRetryRef.current = window.setTimeout(() => {
          initScreeningWebSocket(projectId)
          restaurarEstadoDoLote(projectId)
        }, espera)
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
        pendingSemResumo: s.pending_sem_resumo ?? 0,
        pendingTriaveis: s.pending_triaveis ?? s.pending_papers,
      })
      if (activeProject?.collaboration_mode === 'cega_por_pares') {
        api.listScreeningConflicts(projectId).then(list => setConflictCount(list.length)).catch(() => {})
      }
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
        screening_status: statusFilter || undefined,
        com_resumo: filtroDeResumo ?? undefined,
        search: searchTerm || undefined,
        sort_by: sortBy,
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

  const handleResolveConflict = async (decision: Decision) => {
    if (!id || !selectedPaper) return
    try {
      setResolvingConflict(true)
      const updated = await api.resolveScreeningConflict(id, selectedPaper.id, {
        decision,
        observations: conflictNotes || undefined,
        criteria_evaluations: selectedPaper.criteria_evaluations,
      })
      setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? updated : p)))
      setSelectedPaper(updated)
      setConflictNotes('')
      toast.success('Conflito resolvido', {
        description: `Decisão arbitral registrada como "${decision}".`,
      })
      loadStats(id)
      if (isCoordinator && isBlindMode) {
        api.listScreeningConflicts(id).then(list => setConflictCount(list.length)).catch(() => {})
      }
    } catch (err: any) {
      toast.error('Falha ao resolver conflito', { description: err.message })
    } finally {
      setResolvingConflict(false)
    }
  }

  const usuarioAtual = useAuthStore((estado) => estado.user)

  const { activeUsers } = useProjectChannel({
    projectId: id,
    screen: 'triagem',
    onBatchScreeningMessage: handleBatchScreeningMessage,
    onPaperDecided: (evt) => {
      setPapers((prev) =>
        prev.map((p) =>
          p.id === evt.paper_id
            ? { ...p, decision: evt.decision as Decision, updated_at: evt.updated_at || p.updated_at }
            : p
        )
      )
      if (selectedPaper?.id === evt.paper_id) {
        setSelectedPaper((prev) =>
          prev
            ? {
                ...prev,
                decision: evt.decision as Decision,
                updated_at: evt.updated_at || prev.updated_at,
              }
            : prev
        )
        toast.info(`Decisão atualizada por @${evt.por}: ${evt.decision}`)
      }
      if (id) loadStats(id)
    },
  })

  /* "Triando agora com você" listava o próprio usuário junto dos colegas: a
     presença do servidor inclui quem pergunta. Aqui a lista é só de terceiros —
     e a barra some quando ninguém mais está na tela. */
  const colegasPresentes = activeUsers.filter(
    (u) => u.screen === 'triagem' && u.user_id !== usuarioAtual?.id
  )

  const handleDecision = async (paperId: string, decision: Decision, force = false) => {
    if (!id) return
    try {
      const targetPaper = papers.find((p) => p.id === paperId) || selectedPaper
      const ifMatch = (!force && targetPaper?.updated_at) ? new Date(targetPaper.updated_at).toISOString() : undefined

      const updated = await api.updatePaper(id, paperId, { decision }, ifMatch)

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
      if (err?.status === 409 || err?.message?.includes('409') || err?.detail?.includes('concorrência')) {
        toast.warning('Conflito de concorrência', {
          description: 'Outro pesquisador alterou este estudo. Os dados foram sincronizados.',
        })
        const latest = await api.getPaper(id, paperId)
        setPapers((prev) => prev.map((p) => (p.id === paperId ? latest : p)))
        if (selectedPaper?.id === paperId) setSelectedPaper(latest)
      } else {
        error('Triagem', `Erro ao registrar decisão ${decision}`, err.message)
      }
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

      triagemUnicaAbortRef.current?.abort()
      const controlador = new AbortController()
      triagemUnicaAbortRef.current = controlador

      const res = await api.screenSinglePaperAI(id, selectedPaper.id, controlador.signal)
      setAiLastResult(res)

      success('Assistência', `Parecer da Assistência: ${res.decision} (Confiança: ${(res.confidence * 100).toFixed(0)}%)`, `Justificativa: ${res.justification || (res as any).reasoning}\nCritérios atendidos: ${(res as any).criteria_met?.join(', ') || 'Nenhum'}`)

      const updatedPaper = await api.getPaper(id, selectedPaper.id)
      setSelectedPaper({ ...updatedPaper })
      setPapers((prev) => prev.map((p) => (p.id === selectedPaper.id ? { ...updatedPaper } : p)))
      loadStats(id)
    } catch (err: any) {
      if (foiCancelado(err)) {
        info('Assistência', 'Triagem assistida do estudo cancelada.')
        return
      }
      error('Assistência', `Falha na triagem com assistência: ${err.message}`)
    } finally {
      triagemUnicaAbortRef.current = null
      setIsAiScreeningSingle(false)
    }
  }

  /** Solta a tela da triagem assistida em curso neste estudo. */
  const handleCancelSingleAIScreening = () => {
    triagemUnicaAbortRef.current?.abort()
    triagemUnicaAbortRef.current = null
    setIsAiScreeningSingle(false)
  }

  const handleStartBatchAI = async (limit: number, concurrency: number, pausa: number) => {
    if (!id) return
    try {
      setIsBatchRunning(true)
      setItensDoLote([])
      setCurrentScreeningStudy(null)
      setBatchProgress({
        processed: 0,
        total: limit,
        percentage: 0,
        included: 0,
        excluded: 0,
        pending: limit,
      })
      info(
        'Triagem',
        `Disparando triagem em lote: até ${limit} estudos, ${concurrency} em paralelo` +
          `${pausa > 0 ? ` com ${pausa}s entre envios` : ' sem pausa'}...`
      )
      await api.startBatchScreeningAI(id, {
        limit,
        concurrency,
        pausa_entre_estudos: pausa,
      })
      iniciarAcompanhamentoDoLote(id)
    } catch (err: any) {
      error('Triagem', `Falha ao iniciar triagem em lote: ${err.message}`)
      setIsBatchRunning(false)
      // O lote nem chegou a existir: descartar o progresso otimista devolve a
      // janela ao formulário, em vez de deixá-la num "0 de 100 interrompido"
      // que nunca aconteceu.
      setBatchProgress(null)
      toast.error('Erro na triagem em lote', {
        description: err.message || 'Falha na comunicação com o backend.',
      })
    }
  }

  const handleCancelBatchAI = async () => {
    if (!id) return
    try {
      const res = await api.cancelBatchScreeningAI(id)
      if (res.status === 'not_running') {
        // O servidor já não tinha nada correndo: a tela é que estava
        // desatualizada. Alinhar aqui evita um botão de parar que não para nada.
        setIsBatchRunning(false)
        setCurrentScreeningStudy(null)
      }
    } catch (err: any) {
      error('Triagem', `Falha ao interromper a triagem em lote: ${err.message}`)
      toast.error('Não foi possível interromper', {
        description: err.message || 'Falha na comunicação com o backend.',
      })
    }
  }

  /**
   * Recompõe o estado do lote a partir do servidor.
   *
   * O progresso só chegava pelo WebSocket, então recarregar a página no meio
   * de uma triagem apagava a barra e o botão de parar — enquanto o servidor
   * seguia triando e consumindo cota, sem nada na tela para interrompê-lo.
   */
  /**
   * Consulta o servidor enquanto o lote corre.
   *
   * O progresso chegava exclusivamente pelo WebSocket, e isso tornava a barra
   * refém da saúde do canal: bastava o socket cair — reinício do servidor, rede
   * oscilando, a máquina suspendendo — para o modal ficar parado em 0% enquanto
   * o servidor triava normalmente. Não havia nada na tela que dissesse a
   * diferença entre "não começou" e "estou surdo".
   *
   * O canal continua sendo o caminho rápido, que traz também a justificativa de
   * cada decisão. Esta consulta é a rede de segurança: mais lenta, mas
   * independente dele.
   */
  const iniciarAcompanhamentoDoLote = (projectId: string) => {
    if (pollLoteRef.current !== null) return
    pollLoteRef.current = window.setInterval(async () => {
      try {
        const res = await api.getBatchScreeningStatus(projectId)

        if (!res.is_running) {
          /* O servidor devolve o DESFECHO do lote encerrado, e não `null`.
             Adotá-lo antes de parar é o que fecha o quadro: sem isto, a tela
             ficava com o penúltimo número lido — N-1 de N, com o último estudo
             preso em "analisando" —, exatamente o que parecia um lote travado
             no fim. */
          const fim = res.progress
          if (fim) {
            setBatchProgress({
              processed: fim.processed,
              total: fim.total,
              percentage: fim.percentage,
              included: fim.included,
              excluded: fim.excluded,
              pending: fim.pending,
              ritmo: fim.ritmo ?? null,
            })
            if (Array.isArray(fim.itens) && fim.itens.length > 0) {
              setItensDoLote(fim.itens)
            }
          }
          pararAcompanhamentoDoLote()
          setIsBatchRunning(false)
          setCurrentScreeningStudy(null)
          loadStats(projectId)
          loadPapers(projectId)
          return
        }

        const p = res.progress
        if (p) {
          if (p.current_paper_title) {
            setCurrentScreeningStudy({
              paper_id: p.current_paper_id || '',
              title: p.current_paper_title,
              authors: p.current_paper_authors || '',
              year: p.current_paper_year || '',
              total: p.total,
            })
          }
          /* A relação vem inteira do servidor: mais simples e mais correto do
             que costurar fragmentos, e é o que faz a janela mostrar o mesmo
             conjunto com ou sem canal ao vivo. */
          if (Array.isArray(p.itens) && p.itens.length > 0) {
            setItensDoLote(p.itens)

            // Reflete as decisões na fila horizontal de estudos.
            setPapers((prev) =>
              prev.map((paper) => {
                const item = p.itens?.find((i) => i.id === paper.id)
                if (item && item.status === 'concluido' && item.decision) {
                  return {
                    ...paper,
                    decision: item.decision as Decision,
                    ai_confidence: item.confidence ?? paper.ai_confidence,
                    observations: item.justification || paper.observations,
                  }
                }
                return paper
              })
            )
          }

          // Só avança: uma resposta atrasada não pode fazer a barra recuar
          // sobre o que o canal já entregou.
          setBatchProgress((anterior) =>
            anterior && anterior.processed >= p.processed
              ? anterior
              : {
                  processed: p.processed,
                  total: p.total,
                  percentage: p.percentage,
                  included: p.included,
                  excluded: p.excluded,
                  pending: p.pending,
                  ritmo: p.ritmo ?? null,
                }
          )
        }
      } catch {
        // Falha de rede momentânea: a próxima passada tenta de novo.
      }
      /* 8s, e não os 1,8s que estavam aqui.
         A 1,8s eram 33 consultas por minuto — mais do que o limitador do
         próprio aplicativo permite para a família de rotas de IA, de modo que a
         tela derrubava a si mesma com "muitas requisições em pouco tempo". E não
         havia ganho: o lote avança em segundos, não em milissegundos, e esta
         consulta só entra em ação quando o canal ao vivo cala. */
    }, 8000)
  }

  const pararAcompanhamentoDoLote = () => {
    if (pollLoteRef.current !== null) {
      window.clearInterval(pollLoteRef.current)
      pollLoteRef.current = null
    }
  }

  const restaurarEstadoDoLote = async (projectId: string) => {
    try {
      const res = await api.getBatchScreeningStatus(projectId)
      if (!res.is_running && res.progress) {
        // Lote recém-encerrado: a tela abre já mostrando o resultado, em vez
        // de fingir que nada aconteceu.
        setItensDoLote(res.progress.itens ?? [])
      }

      if (res.is_running) {
        setIsBatchRunning(true)
        iniciarAcompanhamentoDoLote(projectId)
        if (res.progress) {
          setBatchProgress({
            processed: res.progress.processed,
            total: res.progress.total,
            percentage: res.progress.percentage,
            included: res.progress.included,
            excluded: res.progress.excluded,
            pending: res.progress.pending,
          })
          if (res.progress.current_paper_title) {
            setCurrentScreeningStudy({
              paper_id: res.progress.current_paper_id || '',
              title: res.progress.current_paper_title,
              authors: res.progress.current_paper_authors || '',
              year: res.progress.current_paper_year || '',
              total: res.progress.total,
            })
          }
          if (Array.isArray(res.progress.itens) && res.progress.itens.length > 0) {
            setItensDoLote(res.progress.itens)
          }
        }
      }
    } catch {
      // Sem situação para restaurar a tela segue no estado inicial: é melhor
      // não mostrar lote nenhum do que inventar um que não existe.
    }
  }

  const handleSaveAbstract = async () => {
    if (!id || !selectedPaper) return
    try {
      setSavingAbstract(true)
      const trimmed = editedAbstractText.trim()
      const updated = await api.updatePaper(id, selectedPaper.id, {
        abstract: trimmed,
      })
      setSelectedPaper((prev) => (prev ? { ...prev, abstract: updated.abstract } : prev))
      setPapers((prev) =>
        prev.map((p) => (p.id === selectedPaper.id ? { ...p, abstract: updated.abstract } : p))
      )
      setIsEditingAbstract(false)
      success('Triagem', `Resumo do estudo "${selectedPaper.title.slice(0, 40)}..." atualizado com sucesso!`)
      toast.success('Resumo salvo', {
        description: 'O texto do resumo foi atualizado com sucesso e está pronto para análise.',
      })
    } catch (err: any) {
      error('Triagem', `Erro ao salvar resumo: ${err.message}`)
      toast.error('Erro ao salvar resumo', {
        description: err.message || 'Falha na comunicação com o servidor.',
      })
    } finally {
      setSavingAbstract(false)
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
      screenAiBatch: () => setIsBatchModalOpen(true),
      stopBatchScreening: () => {
        void handleCancelBatchAI()
      },
      isBatchScreening: isBatchRunning,
      batchScreeningProgressText: batchProgress
        ? `${batchProgress.processed}/${batchProgress.total}`
        : 'Triando...',
      openDoiOrRepoLink: () => {
        const url = getSourceUrl(selectedPaper)
        if (url) window.open(url, '_blank')
      },
      hasDoiOrRepo: !!getSourceUrl(selectedPaper),
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
        'stopBatchScreening',
        'isBatchScreening',
        'batchScreeningProgressText',
        'openDoiOrRepoLink',
        'hasDoiOrRepo',
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
    isBatchRunning,
    batchProgress,
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

      {/* Indicador de presença de pesquisadores na Triagem (Doc 43 §43.12, Fase 3) */}
      {colegasPresentes.length > 0 && (
        <div className="presence-bar">
          <Users size={14} className="icon-accent" aria-hidden="true" />
          <span>Triando agora com você:</span>
          <div className="presence-pills">
            {colegasPresentes.map((u) => (
                <span
                  key={u.user_id}
                  className="presence-pill"
                  title={`Conectado desde ${new Date(u.connected_at).toLocaleTimeString()}`}
                >
                  @{u.username}
                </span>
              ))}
          </div>
        </div>
      )}

      {/* ── NAVEGAÇÃO SEGMENTADA MOBILE (Exibida apenas em telas < 768px) ── */}
      <div className="screening-mobile-segmented-nav">
        <button
          type="button"
          className={`mobile-seg-btn ${mobileTab === 'article' ? 'active' : ''}`}
          onClick={() => setMobileTab('article')}
        >
          <FileText size={15} />
          <span>Artigo</span>
        </button>
        <button
          type="button"
          className={`mobile-seg-btn ${mobileTab === 'criteria' ? 'active' : ''}`}
          onClick={() => setMobileTab('criteria')}
        >
          <CheckSquare size={15} />
          <span>Critérios & IA</span>
        </button>
        <button
          type="button"
          className={`mobile-seg-btn ${mobileTab === 'queue' ? 'active' : ''}`}
          onClick={() => setMobileTab('queue')}
        >
          <Layers size={15} />
          <span>Fila ({stats.total})</span>
        </button>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          FILA HORIZONTAL DE TRABALHOS (ACIMA)
          Controles de busca, contadores de status, paginação e faixa de cards
      ═══════════════════════════════════════════════════════════════════ */}
      <div className={`screening-queue-container mobile-tab-view ${mobileTab === 'queue' ? 'mobile-show' : ''}`}>
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
                setStatusFilter('')
                setPage(1)
              }}
            >
              <XCircle size={14} />
              <span className="count-label">Excluídos</span>
              <span className="count-num">{stats.excluded}</span>
            </button>

            {stats.pendingSemResumo > 0 && (
              <button
                className={`counter-btn sem-resumo ${filtroDeResumo === false ? 'active' : ''}`}
                title={
                  'Pendentes sem resumo utilizável. Ficam fora da triagem assistida — não há ' +
                  'texto para julgar —, mas continuam no acervo: busque o resumo, decida pelo ' +
                  'título ou exclua com motivo declarado.'
                }
                onClick={() => {
                  const proximo = filtroDeResumo === false ? null : false
                  setFiltroDeResumo(proximo)
                  if (proximo === false) setDecisionFilter('Pendente')
                  setPage(1)
                }}
              >
                <FileX size={14} />
                <span className="count-label">Sem resumo</span>
                <span className="count-num">{stats.pendingSemResumo}</span>
              </button>
            )}

            {conflictCount > 0 && (
              <button
                className={`counter-btn conflict ${statusFilter === 'conflito' ? 'active' : ''}`}
                onClick={() => {
                  setStatusFilter(statusFilter === 'conflito' ? '' : 'conflito')
                  setDecisionFilter('')
                  setPage(1)
                }}
                title="Filtrar apenas estudos com divergência de triagem"
              >
                <AlertCircle size={14} />
                <span className="count-label">Conflitos</span>
                <span className="count-num">{conflictCount}</span>
              </button>
            )}

            {aiEnabled && (
              <button
                type="button"
                className={`btn-queue-batch ${isBatchRunning ? 'active' : ''}`}
                onClick={() => setIsBatchModalOpen(true)}
                title="Abrir painel de triagem em lote com Inteligência Artificial"
              >
                {isBatchRunning ? (
                  <RefreshCw size={13} className="animate-spin text-accent" />
                ) : (
                  <Zap size={13} />
                )}
                <span>
                  {isBatchRunning
                    ? `Triando (${batchProgress?.processed || 0}/${batchProgress?.total || stats.pending})`
                    : 'Triar Lote'}
                </span>
              </button>
            )}
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

          <div className="queue-sort-wrapper">
            <ArrowUpDown size={13} className="sort-icon" />
            <select
              className="queue-sort-select"
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value)
                setPage(1)
              }}
              title="Critério de ordenação dos estudos na fila"
              aria-label="Critério de ordenação dos estudos"
            >
              <option value="year_desc">📅 Publicação: Mais recentes primeiro</option>
              <option value="year_asc">📅 Publicação: Mais antigos primeiro</option>
              <option value="title_asc">🔤 Título: A → Z</option>
              <option value="title_desc">🔤 Título: Z → A</option>
              <option value="authors_asc">👤 Autor: A → Z</option>
              <option value="authors_desc">👤 Autor: Z → A</option>
              <option value="confidence_desc">⚡ Confiança da IA: Maior primeiro</option>
              <option value="confidence_asc">⚡ Confiança da IA: Menor primeiro</option>
              <option value="updated_desc">🕒 Modificação mais recente</option>
              <option value="created_desc">📥 Importação mais recente</option>
            </select>
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
                const isBeingScreened = currentScreeningStudy?.paper_id === paper.id
                return (
                  <button
                    type="button"
                    key={paper.id}
                    className={`queue-paper-card ${isSelected ? 'selected' : ''} ${isBeingScreened ? 'is-currently-screening' : ''} dec-${paper.decision.toLowerCase()}`}
                    onClick={() => {
                      setSelectedPaper(paper)
                      setAiLastResult(null)
                    }}
                    title={paper.title}
                    aria-current={isSelected}
                  >
                    <div className="queue-card-meta">
                      <span className={`badge-decision badge-${paper.decision.toLowerCase()}`}>
                        {paper.decision}
                      </span>
                      {paper.screening_status && paper.screening_status !== 'legado' && (
                        <span className={`badge-screening-status status-${paper.screening_status}`}>
                          {paper.screening_status === 'parcial' && paper.reviewers_required_count
                            ? `${paper.reviewers_completed_count || 0}/${paper.reviewers_required_count} pareceres`
                            : paper.screening_status}
                        </span>
                      )}
                      {paper.my_screening && paper.my_screening.decision !== 'Pendente' && (
                        <span className="badge-my-vote" title={`Seu parecer individual: ${paper.my_screening.decision}`}>
                          <Check size={10} /> Seu voto
                        </span>
                      )}
                      {isBeingScreened ? (
                        <span className="badge-screening-active" title="Análise da Assistência em andamento">
                          <RefreshCw size={10} className="animate-spin text-accent" /> Triando...
                        </span>
                      ) : (
                        paper.ai_confidence !== null && (
                          <span className="badge-ai-conf" title="Confiança da Assistência">
                            <Sparkles size={10} /> {Math.round(paper.ai_confidence * 100)}%
                          </span>
                        )
                      )}
                      {paper.year && <span className="queue-card-year">{paper.year}</span>}
                    </div>
                    <span className="queue-card-title">{paper.title}</span>
                    {paper.authors && (
                      <span className="queue-card-authors" title={paper.authors}>
                        {paper.authors}
                      </span>
                    )}
                  </button>
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
            className={`study-reading-pane mobile-tab-view ${mobileTab === 'article' ? 'mobile-show' : ''} ${isDragOver ? 'drag-over-active' : ''}`}
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
              <div className="decision-buttons-group" data-trilho-target="screening-decision-buttons">
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
                    onClick={
                      isAiScreeningSingle
                        ? handleCancelSingleAIScreening
                        : handleSingleAIScreening
                    }
                    title={
                      isAiScreeningSingle
                        ? 'Interromper a análise deste artigo'
                        : 'Avaliar este artigo com Assistência'
                    }
                  >
                    {isAiScreeningSingle ? (
                      <>
                        <RefreshCw size={14} className="animate-spin" /> Cancelar Análise
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
                    aria-label="Estudo Anterior (Atalho: Seta Esquerda)"
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
                    aria-label="Próximo Estudo (Atalho: Seta Direita)"
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
                      href={getDoiUrl(selectedPaper.doi)}
                      target="_blank"
                      rel="noreferrer"
                      title="Abrir publicação oficial via DOI"
                    >
                      DOI: {selectedPaper.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//i, '')}
                    </a>
                  </div>
                )}
                {selectedPaper.download_url && (
                  <div className="meta-pill">
                    <Globe size={13} className="icon-accent" />
                    <a
                      href={selectedPaper.download_url}
                      target="_blank"
                      rel="noreferrer"
                      title="Abrir no repositório institucional de origem (BDTD, SciELO, etc.)"
                    >
                      {selectedPaper.source ? `Repositório (${selectedPaper.source})` : 'Repositório / Fonte'}
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
              <Tabs.Root
                className="view-mode-tabs-root"
                value={readingViewMode}
                onValueChange={(v) => handleToggleReadingView(v as 'abstract' | 'pdf_view' | 'pdf_text')}
              >
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
                      <Tabs.List asChild>
                        <div className="view-mode-toggle-group">
                          <Tabs.Trigger
                            value="abstract"
                            className={`btn-view-mode ${readingViewMode === 'abstract' ? 'active' : ''}`}
                          >
                            Resumo
                          </Tabs.Trigger>
                          <Tabs.Trigger
                            value="pdf_view"
                            className={`btn-view-mode ${readingViewMode === 'pdf_view' ? 'active' : ''}`}
                            disabled={!selectedPaper.pdf_path}
                          >
                            PDF
                          </Tabs.Trigger>
                          <Tabs.Trigger
                            value="pdf_text"
                            className={`btn-view-mode ${readingViewMode === 'pdf_text' ? 'active' : ''}`}
                            disabled={!selectedPaper.pdf_path}
                          >
                            Texto
                          </Tabs.Trigger>
                        </div>
                      </Tabs.List>

                    {getSourceUrl(selectedPaper) && (
                      <a
                        href={getSourceUrl(selectedPaper)}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-pdf-action link"
                        title="Abrir trabalho na página do repositório ou editora oficial"
                      >
                        <Globe size={12} /> {selectedPaper.doi ? 'Abrir DOI' : 'Abrir Fonte'}
                      </a>
                    )}

                    {readingViewMode === 'abstract' && !isEditingAbstract && (
                      <button
                        type="button"
                        className="btn-pdf-action"
                        onClick={() => {
                          setEditedAbstractText(selectedPaper.abstract || '')
                          setIsEditingAbstract(true)
                        }}
                        title="Editar ou colar manualmente o resumo do artigo"
                      >
                        <Edit3 size={12} /> {selectedPaper.abstract ? 'Editar Resumo' : 'Colar Resumo'}
                      </button>
                    )}

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

                {/* Resumo do abstract: repetido também como fallback de "pdf_view"
                    sem pdf_path — mesmo comportamento de antes da migração
                    para Tabs, quando um único ternário cobria os três modos. */}
                {(() => {
                  const conteudoResumo = isEditingAbstract ? (
                    <div className="abstract-editor-card animate-fade-in">
                      <div className="editor-top-info">
                        <span className="editor-hint">
                          <Edit3 size={13} className="text-accent" /> Cole ou digite o resumo recuperado do repositório/artigo:
                        </span>
                        <div className="editor-char-counter">
                          <span>{editedAbstractText.length} caracteres</span>
                          <span>•</span>
                          <span>
                            {editedAbstractText.trim()
                              ? editedAbstractText.trim().split(/\s+/).length
                              : 0}{' '}
                            palavras
                          </span>
                        </div>
                      </div>

                      <textarea
                        className="abstract-edit-textarea"
                        rows={10}
                        placeholder="Cole aqui o texto completo do resumo (abstract) deste estudo..."
                        value={editedAbstractText}
                        onChange={(e) => setEditedAbstractText(e.target.value)}
                        autoFocus
                      />

                      <div className="abstract-editor-actions">
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setIsEditingAbstract(false)
                            setEditedAbstractText(selectedPaper.abstract || '')
                          }}
                          disabled={savingAbstract}
                          leftIcon={<X size={13} />}
                        >
                          Cancelar
                        </Button>
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          onClick={handleSaveAbstract}
                          disabled={savingAbstract}
                          leftIcon={
                            savingAbstract ? (
                              <RefreshCw size={13} className="animate-spin" />
                            ) : (
                              <Save size={13} />
                            )
                          }
                        >
                          {savingAbstract ? 'Salvando...' : 'Salvar Resumo'}
                        </Button>
                      </div>
                    </div>
                  ) : selectedPaper.abstract ? (
                    <div className="abstract-display-wrapper">
                      <p className="abstract-text">{selectedPaper.abstract}</p>
                      <div className="abstract-footer-row">
                        <button
                          type="button"
                          className="btn-abstract-edit-subtle"
                          onClick={() => {
                            setEditedAbstractText(selectedPaper.abstract || '')
                            setIsEditingAbstract(true)
                          }}
                          title="Editar ou complementar o texto do resumo"
                        >
                          <Edit3 size={12} /> Editar Resumo
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-abstract-state">
                      <AlertCircle size={24} />
                      <p>Resumo não disponível nos metadados coletados deste registro.</p>
                      <p className="empty-abstract-hint">
                        Acesse o repositório ou página do DOI para consultar e colar o resumo, ou anexe o PDF do estudo.
                      </p>
                      <div className="empty-abstract-actions">
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          onClick={() => {
                            setEditedAbstractText('')
                            setIsEditingAbstract(true)
                          }}
                          leftIcon={<Edit3 size={13} />}
                        >
                          Inserir Resumo Manualmente
                        </Button>
                        {getSourceUrl(selectedPaper) && (
                          <a
                            href={getSourceUrl(selectedPaper)}
                            target="_blank"
                            rel="noreferrer"
                            className="btn-secondary small"
                          >
                            <ExternalLink size={13} /> {selectedPaper.doi ? 'Consultar via DOI' : 'Abrir no Repositório'}
                          </a>
                        )}
                      </div>
                    </div>
                  )

                  return (
                    <>
                      <Tabs.Content value="abstract" className="tabs-content-passthrough">
                        <Card surface="primaria" relief="afundado" className="abstract-reading-card">
                          {conteudoResumo}
                        </Card>
                      </Tabs.Content>
                      <Tabs.Content value="pdf_view" className="tabs-content-passthrough">
                        {selectedPaper.pdf_path && id ? (
                          <div className="pdf-embed-container">
                            <iframe
                              key={selectedPaper.id}
                              className="pdf-embed-frame"
                              title={`PDF — ${selectedPaper.title}`}
                              src={api.getPaperPdfUrl(id, selectedPaper.id)}
                            />
                          </div>
                        ) : (
                          <Card surface="primaria" relief="afundado" className="abstract-reading-card">
                            {conteudoResumo}
                          </Card>
                        )}
                      </Tabs.Content>
                      <Tabs.Content value="pdf_text" className="tabs-content-passthrough">
                        <Card surface="primaria" relief="afundado" className="abstract-reading-card">
                          {loadingPdfText ? (
                            <div className="empty-abstract-state">
                              <RefreshCw size={22} className="animate-spin icon-accent" />
                              <p>Extraindo o texto integral do PDF...</p>
                            </div>
                          ) : (
                            <p className="abstract-text">{pdfExtractedText}</p>
                          )}
                        </Card>
                      </Tabs.Content>
                    </>
                  )
                })()}
              </div>
              </Tabs.Root>
            </div>
          </div>

          {/* ── COLUNA DA DIREITA: CRITÉRIOS DE ELEGIBILIDADE & OBSERVAÇÕES ── */}
          <div className={`criteria-evaluation-pane mobile-tab-view ${mobileTab === 'criteria' ? 'mobile-show' : ''}`}>
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

            {/* Painel de Resolução de Conflito de Triagem (Doc 43 §43.8.3).
                Fica FORA do bloco de critérios: estava aninhado nele, e uma
                revisão cega cujo protocolo ainda não tem critérios deixava a
                coordenação sem nenhuma tela para desempatar. */}
            {selectedPaper.screening_status === 'conflito' && (
              <div className="conflict-resolution-panel animate-fade-in">
                <div className="conflict-panel-header">
                  <AlertCircle size={18} className="text-warning" aria-hidden="true" />
                  <div>
                    <h4>Divergência entre Revisores (Conflito de Triagem)</h4>
                    <p>Os revisores independentes divergiram na avaliação deste estudo.</p>
                  </div>
                </div>

                {isCoordinator ? (
                  <div className="coordinator-resolution-container">
                    {selectedPaper.screenings && selectedPaper.screenings.length >= 2 && (
                      <div className="conflict-reviewers-grid">
                        {selectedPaper.screenings.map((s, idx) => (
                          <div key={s.id || idx} className={`reviewer-conflict-card dec-${(s.decision || '').toLowerCase()}`}>
                            <div className="reviewer-conflict-head">
                              <span className="reviewer-name">
                                <User size={13} /> @{s.reviewer_username || `Revisor ${idx + 1}`}
                              </span>
                              <span className={`badge-decision badge-${(s.decision || '').toLowerCase()}`}>
                                {s.decision}
                              </span>
                            </div>
                            {s.observations && (
                              <p className="reviewer-conflict-obs">"{s.observations}"</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="coordinator-resolve-actions">
                      <label className="resolution-label">Parecer Arbitral da Coordenação:</label>
                      <textarea
                        rows={3}
                        className="resolution-textarea"
                        placeholder="Anote a fundamentação do desempate metodológico..."
                        value={conflictNotes}
                        onChange={(e) => setConflictNotes(e.target.value)}
                      />
                      <div className="resolution-buttons">
                        <button
                          type="button"
                          className="btn-dec include"
                          disabled={resolvingConflict}
                          onClick={() => handleResolveConflict('Incluído')}
                        >
                          <CheckCircle2 size={16} /> Desempatar: Incluir
                        </button>
                        <button
                          type="button"
                          className="btn-dec exclude"
                          disabled={resolvingConflict}
                          onClick={() => handleResolveConflict('Excluído')}
                        >
                          <XCircle size={16} /> Desempatar: Excluir
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="reviewer-conflict-notice">
                    <p>Aguardando análise e desempate arbitral pela coordenação do projeto.</p>
                  </div>
                )}
              </div>
            )}
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

      {/* Modal de Triagem em Lote com Assistência & Progresso ao Vivo */}
      <BatchScreeningModal
        isOpen={isBatchModalOpen}
        onClose={() => setIsBatchModalOpen(false)}
        projectId={id || ''}
        pendingCount={stats.pending}
        isRunning={isBatchRunning}
        progress={batchProgress}
        currentStudy={currentScreeningStudy}
        itensDoLote={itensDoLote}
        canalAoVivo={canalAoVivo}
        onStartBatch={handleStartBatchAI}
        onCancelBatch={handleCancelBatchAI}
      />

      {/* Floating Mini-Dock quando a triagem está em execução e o modal foi minimizado */}
      {isBatchRunning && !isBatchModalOpen && (
        <div
          className="batch-floating-dock animate-fade-in"
          onClick={() => setIsBatchModalOpen(true)}
          role="button"
          tabIndex={0}
          title="Clique para abrir os detalhes da triagem em lote"
        >
          <div className="dock-icon">
            <RefreshCw size={16} className="animate-spin text-accent" />
          </div>
          <div className="dock-info">
            <div className="dock-info-header">
              <strong>Triagem em Lote com IA</strong>
              <span className="dock-progress-tag">
                {batchProgress
                  ? `${batchProgress.processed}/${batchProgress.total} (${batchProgress.percentage}%)`
                  : 'Iniciando...'}
              </span>
            </div>
            {currentScreeningStudy ? (
              <p className="dock-current-study" title={currentScreeningStudy.title}>
                <Sparkles size={11} className="text-accent" />
                <span>Triando: {currentScreeningStudy.title}</span>
              </p>
            ) : ultimoConcluidoDoLote ? (
              <p className="dock-last-result">
                <span>Último: {ultimoConcluidoDoLote.title}</span>
                <span className={`badge-decision badge-${(ultimoConcluidoDoLote.decision || '').toLowerCase()}`}>
                  {ultimoConcluidoDoLote.decision}
                </span>
              </p>
            ) : (
              <span style={{ fontSize: 'var(--font-size-2xs)', color: 'var(--color-text-secondary)' }}>
                Preparando lote...
              </span>
            )}
          </div>
          <button
            type="button"
            className="btn-dock-stop"
            title="Interromper a triagem em lote"
            aria-label="Interromper a triagem em lote"
            onClick={(e) => {
              e.stopPropagation()
              handleCancelBatchAI()
            }}
          >
            <StopCircle size={14} />
          </button>
          <button type="button" className="btn-dock-expand" title="Expandir painel de progresso">
            <Maximize2 size={14} />
          </button>
        </div>
      )}

      {/* Cadastro manual de estudo */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent size="md">
          <DialogHeader>
            <DialogTitle>Cadastrar Estudo Manualmente</DialogTitle>
            <DialogDescription>Insira os metadados do artigo a ser triado</DialogDescription>
          </DialogHeader>
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

              <DialogFooter>
                <Button variant="secondary" size="md" onClick={() => setIsAddModalOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" variant="primary" size="md">
                  Adicionar ao Projeto
                </Button>
              </DialogFooter>
            </form>
        </DialogContent>
      </Dialog>

      {/* Deduplication Report Modal */}
      <DeduplicationReportModal
        report={dedupReport}
        isOpen={isDedupModalOpen}
        onClose={() => setIsDedupModalOpen(false)}
        projectId={id}
      />

      {/* ── BARRA FIXA INFERIOR DE DECISÃO MOBILE (THUMB BAR) ── */}
      {selectedPaper && (
        <div className="screening-mobile-sticky-dock animate-fade-in">
          <button
            type="button"
            className={`mobile-dock-btn include ${selectedPaper.decision === 'Incluído' ? 'active' : ''}`}
            onClick={() => handleDecision(selectedPaper.id, 'Incluído')}
          >
            <CheckCircle2 size={18} />
            <span>Incluir</span>
          </button>
          <button
            type="button"
            className={`mobile-dock-btn pending ${selectedPaper.decision === 'Pendente' ? 'active' : ''}`}
            onClick={() => handleDecision(selectedPaper.id, 'Pendente')}
          >
            <Clock size={18} />
            <span>Pendente</span>
          </button>
          <button
            type="button"
            className={`mobile-dock-btn exclude ${selectedPaper.decision === 'Excluído' ? 'active' : ''}`}
            onClick={() => handleDecision(selectedPaper.id, 'Excluído')}
          >
            <XCircle size={18} />
            <span>Excluir</span>
          </button>
        </div>
      )}
    </div>
  )
}
