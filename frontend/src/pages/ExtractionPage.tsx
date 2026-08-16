/**
 * RSAC V2 — Extraction Page (Triagem 2 / Extração de Dados)
 *
 * Layout Metodológico Otimizado e Ergonômico:
 * 1. Fila Horizontal de Estudos Incluídos (no topo): busca rápida, contagem e esteira de cards.
 * 2. Área de Trabalho Lado a Lado (Two-Column Workspace) com ROLAGEM INDEPENDENTE:
 *    - Coluna da Esquerda: Metadados e três modos de leitura — Resumo, PDF renderizado
 *      e Texto extraído — com busca, zoom tipográfico e diagnóstico de aquisição.
 *    - Coluna da Direita: Formulário de Extração (Q1..Qn) com evidência ancorada por página.
 *
 * A obtenção do PDF passa pelo resolvedor multi-estratégia do backend: o link
 * coletado é quase sempre uma landing page (DOI, PubMed, SciELO, repositório),
 * e não o arquivo. Quando nenhuma via funciona, a trilha de tentativas fica
 * visível para que o usuário saiba exatamente qual é o próximo passo manual.
 */

import { useState, useEffect, useRef, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  FileText,
  Sparkles,
  Save,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Download,
  FileCheck,
  FileX,
  FileSearch,
  Search,
  ExternalLink,
  BookOpen,
  Calendar,
  User,
  Building,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Layers,
  ListChecks,
  Upload,
  Trash2,
  Link,
  FileCode,
  Quote,
  X,
  ZoomIn,
  ZoomOut,
  Copy,
  Check,
  StopCircle,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useLogStore } from '@/stores/useLogStore'
import type {
  Paper,
  Protocol,
  PdfAttempt,
  PdfBatchState,
  PdfCandidate,
  PdfState,
  PdfTextResponse,
} from '@/types/api'
import './ExtractionPage.css'

type ReadingViewMode = 'abstract' | 'pdf_view' | 'pdf_text'

/** Rótulos das vias de busca, para explicar a procedência ao usuário. */
const STRATEGY_LABELS: Record<string, string> = {
  direct: 'Link direto',
  pattern: 'Padrão de repositório',
  unpaywall: 'Unpaywall',
  openalex: 'OpenAlex',
  semantic: 'Semantic Scholar',
  crossref: 'Crossref',
  europepmc: 'Europe PMC',
  landing: 'Página de origem',
  doi_landing: 'Página do DOI',
  upload: 'Arquivo anexado',
}

const ATTEMPT_STATUS_LABELS: Record<PdfAttempt['status'], string> = {
  ok: 'PDF obtido',
  nao_pdf: 'Devolveu HTML',
  http_erro: 'Erro HTTP',
  timeout: 'Sem resposta',
  erro: 'Falha de conexão',
  vazio: 'Resposta vazia',
  pequeno_demais: 'Arquivo inválido',
}

function strategyLabel(strategy: string): string {
  if (!strategy) return '—'
  const [base, suffix] = strategy.split('+')
  const label = STRATEGY_LABELS[base] || base
  return suffix ? `${label} (via página intermediária)` : label
}

const EMPTY_PDF_STATE: PdfState = {
  has_pdf: false,
  pdf_path: null,
  pdf_status: 'ausente',
  pdf_strategy: '',
  pdf_resolved_url: '',
  pdf_page_count: 0,
  pdf_size_bytes: 0,
  pdf_text_chars: 0,
  pdf_is_scanned: false,
  pdf_acquired_at: null,
  download_url: '',
  attempts: [],
  file_missing: false,
}

export function ExtractionPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject, aiEnabled } = useSettingsStore()

  const [papers, setPapers] = useState<Paper[]>([])
  const [protocol, setProtocol] = useState<Protocol | null>(null)
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
  const [loading, setLoading] = useState(true)

  // Extraction State for Selected Paper
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [evidences, setEvidences] = useState<Record<string, { text: string; page: string }>>({})
  const [pdfState, setPdfState] = useState<PdfState>(EMPTY_PDF_STATE)
  const [pdfDoc, setPdfDoc] = useState<PdfTextResponse | null>(null)
  const [readingViewMode, setReadingViewMode] = useState<ReadingViewMode>('abstract')
  const [loadingPdfText, setLoadingPdfText] = useState(false)

  // Advanced Full-Text Reader Tools
  const [fontSizeLevel, setFontSizeLevel] = useState<number>(13) // 11 to 17
  const [textSearchTerm, setTextSearchTerm] = useState('')
  const [copiedText, setCopiedText] = useState(false)

  // Aquisição de PDF (individual, diagnóstico e lote)
  const [acquiring, setAcquiring] = useState(false)
  const [acquireMessage, setAcquireMessage] = useState('')
  const [showDiagnostics, setShowDiagnostics] = useState(false)
  const [candidates, setCandidates] = useState<PdfCandidate[] | null>(null)
  const [loadingCandidates, setLoadingCandidates] = useState(false)
  const [batchState, setBatchState] = useState<PdfBatchState | null>(null)

  const [saving, setSaving] = useState(false)
  const [extractingAI, setExtractingAI] = useState(false)
  const [uploadingPdf, setUploadingPdf] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [isUrlModalOpen, setIsUrlModalOpen] = useState(false)
  const [customDownloadUrl, setCustomDownloadUrl] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const hasPdf = pdfState.has_pdf
  const pdfExtractedText = pdfDoc?.text ?? null

  // Search & Navigation in Included Papers
  const [searchTerm, setSearchTerm] = useState('')
  const queueScrollRef = useRef<HTMLDivElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (id) {
      loadInitialData(id)
    }
  }, [id])

  useEffect(() => {
    if (id && selectedPaper) {
      loadPaperExtraction(id, selectedPaper.id)
      setReadingViewMode('abstract')
      setPdfDoc(null)
      setTextSearchTerm('')
      setCandidates(null)
      setShowDiagnostics(false)
      setAcquireMessage('')
      setCustomDownloadUrl(selectedPaper.download_url || '')
    }
  }, [id, selectedPaper?.id])

  // Enquanto o lote roda, acompanha o progresso e recarrega a fila ao terminar.
  useEffect(() => {
    if (!id || !batchState || batchState.status !== 'running') return

    const timer = window.setInterval(async () => {
      try {
        const state = await api.getPdfBatchStatus(id)
        setBatchState(state)
        if (state.status !== 'running') {
          window.clearInterval(timer)
          useLogStore
            .getState()
            .log(
              state.succeeded > 0 ? 'success' : 'warn',
              'Extração',
              `Busca de PDFs concluída: ${state.succeeded} obtidos, ${state.failed} sem arquivo`,
            )
          const papersRes = await api.listPapers(id, { decision: 'Incluído', page_size: 200 })
          setPapers(papersRes.items)
          if (selectedPaper) loadPaperExtraction(id, selectedPaper.id)
        }
      } catch (err) {
        window.clearInterval(timer)
      }
    }, 1500)

    return () => window.clearInterval(timer)
  }, [id, batchState?.status])

  const loadInitialData = async (projectId: string) => {
    try {
      setLoading(true)
      if (!activeProject || activeProject.id !== projectId) {
        const proj = await api.getProject(projectId)
        setActiveProject(proj)
      }

      const [protoRes, papersRes] = await Promise.all([
        api.getProtocol(projectId),
        api.listPapers(projectId, { decision: 'Incluído', page_size: 200 }),
      ])

      setProtocol(protoRes)
      setPapers(papersRes.items)
      if (papersRes.items.length > 0) {
        setSelectedPaper(papersRes.items[0])
      }
    } catch (err) {
      console.error('Erro ao carregar dados de extração:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadPaperExtraction = async (projectId: string, paperId: string) => {
    try {
      setErrorMessage('')
      const extRes = await api.getExtractionAnswers(projectId, paperId)
      const { answers: answerList, paper_id: _pid, ...state } = extRes
      setPdfState({ ...EMPTY_PDF_STATE, ...state })

      const ansMap: Record<string, string> = {}
      const evidenceMap: Record<string, { text: string; page: string }> = {}
      answerList.forEach((a) => {
        ansMap[a.question_id] = a.answer
        if (a.evidence) {
          evidenceMap[a.question_id] = { text: a.evidence, page: a.page_ref }
        }
      })
      setAnswers(ansMap)
      setEvidences(evidenceMap)
    } catch (err) {
      console.error('Erro ao carregar respostas de extração:', err)
    }
  }

  const handleAnswerChange = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  const handleSaveAnswers = async () => {
    if (!id || !selectedPaper) return
    try {
      setSaving(true)
      setErrorMessage('')
      await api.updateExtractionAnswers(id, selectedPaper.id, answers)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err: any) {
      console.error('Erro ao salvar extração:', err)
      setErrorMessage(err.message || 'Falha ao salvar respostas.')
    } finally {
      setSaving(false)
    }
  }

  const handleExtractWithAI = async () => {
    if (!id || !selectedPaper) return
    try {
      setExtractingAI(true)
      setErrorMessage('')
      const res = await api.extractAnswersWithAI(id, selectedPaper.id)
      const nextAns = { ...answers }
      const nextEvidence = { ...evidences }
      res.answers?.forEach((a: any) => {
        nextAns[a.question_id] = a.answer
        if (a.evidence) {
          nextEvidence[a.question_id] = { text: a.evidence, page: a.page_ref || '' }
        }
      })
      setAnswers(nextAns)
      setEvidences(nextEvidence)

      const usedAbstract = res.answers?.some((a: any) => a.source_kind === 'resumo')
      if (usedAbstract && !hasPdf) {
        setAcquireMessage(
          'A extração assistida usou apenas o resumo — anexe ou busque o PDF para respostas ancoradas no texto completo.'
        )
      }
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err: any) {
      console.error('Erro ao extrair com assistência:', err)
      setErrorMessage(err.message || 'Falha ao processar extração assistida.')
    } finally {
      setExtractingAI(false)
    }
  }

  // ── Métodos de PDF ───────────────────────────────────────────────
  const handleUploadFile = async (file: File) => {
    if (!id || !selectedPaper) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('O arquivo selecionado não é um PDF válido (.pdf).')
      return
    }

    try {
      setUploadingPdf(true)
      setErrorMessage('')
      const res: any = await api.uploadPaperPDF(id, selectedPaper.id, file)
      setPdfDoc(null)
      setAcquireMessage(res.message || 'PDF anexado.')
      await refreshPdfState()
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
      if (res.is_scanned) {
        setErrorMessage(
          'O PDF anexado não possui texto selecionável (documento digitalizado). ' +
            'A leitura de texto e a extração assistida ficarão limitadas ao resumo.'
        )
      }
    } catch (err: any) {
      console.error('Erro no upload do PDF:', err)
      setErrorMessage(err.message || 'Falha no upload do arquivo PDF.')
    } finally {
      setUploadingPdf(false)
    }
  }

  const refreshPdfState = async () => {
    if (!id || !selectedPaper) return
    const state = await api.getPaperPdfStatus(id, selectedPaper.id)
    const { paper_id: _pid, ...rest } = state
    setPdfState({ ...EMPTY_PDF_STATE, ...rest })
  }

  /**
   * Dispara a busca multi-estratégia. A falha não é exceção: vem no corpo com a
   * trilha completa, que abrimos automaticamente para orientar o próximo passo.
   */
  const handleAcquirePDF = async () => {
    if (!id || !selectedPaper) return
    try {
      setAcquiring(true)
      setErrorMessage('')
      setAcquireMessage('')
      setCandidates(null)

      const res = await api.acquirePaperPDF(id, selectedPaper.id)
      const { paper_id: _pid, ...rest } = res as any
      setPdfState({ ...EMPTY_PDF_STATE, ...rest })
      setAcquireMessage(res.message || '')
      setPdfDoc(null)

      if (res.success) {
        setShowDiagnostics(false)
        setPapers((prev) =>
          prev.map((p) =>
            p.id === selectedPaper.id
              ? { ...p, pdf_path: res.pdf_path, pdf_status: 'obtido', pdf_text_extracted: true }
              : p
          )
        )
        useLogStore
          .getState()
          .log('success', 'Extração', `PDF obtido via ${strategyLabel(res.strategy)}`, res.message)
        if (res.is_scanned) {
          setErrorMessage(
            'PDF obtido, mas sem texto selecionável (documento digitalizado). ' +
              'A extração assistida usará o resumo.'
          )
        }
      } else {
        setShowDiagnostics(true)
        useLogStore
          .getState()
          .log(
            'warn',
            'Extração',
            'Busca automática de PDF sem sucesso',
            `${res.attempts?.length || 0} caminho(s) tentado(s).`
          )
      }
    } catch (err: any) {
      console.error('Erro ao buscar PDF:', err)
      setErrorMessage(err.message || 'Falha ao executar a busca automática do PDF.')
    } finally {
      setAcquiring(false)
    }
  }

  const handleLoadCandidates = async () => {
    if (!id || !selectedPaper) return
    try {
      setLoadingCandidates(true)
      const res = await api.getPaperPdfCandidates(id, selectedPaper.id)
      setCandidates(res.candidates)
    } catch (err: any) {
      setErrorMessage(err.message || 'Não foi possível levantar links candidatos.')
    } finally {
      setLoadingCandidates(false)
    }
  }

  const handleSaveCustomDownloadUrl = async () => {
    if (!id || !selectedPaper || !customDownloadUrl.trim()) return
    try {
      setAcquiring(true)
      setErrorMessage('')
      await api.updatePaperDownloadUrl(id, selectedPaper.id, customDownloadUrl.trim())
      selectedPaper.download_url = customDownloadUrl.trim()
      setIsUrlModalOpen(false)
      setAcquiring(false)
      await handleAcquirePDF()
    } catch (err: any) {
      console.error('Erro ao baixar por novo link:', err)
      setErrorMessage(err.message || 'Link salvo, mas não foi possível obter o PDF diretamente.')
      setAcquiring(false)
    }
  }

  // ── Lote: buscar PDFs de todos os estudos incluídos ───────────────
  const handleStartBatch = async () => {
    if (!id) return
    try {
      setErrorMessage('')
      const state = await api.startPdfBatch(id, true, 'Incluído')
      setBatchState(state)
      if (state.status === 'empty') {
        setAcquireMessage(state.message || 'Todos os estudos incluídos já possuem PDF.')
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Não foi possível iniciar a busca em lote.')
    }
  }

  const handleCancelBatch = async () => {
    if (!id) return
    await api.cancelPdfBatch(id)
    const state = await api.getPdfBatchStatus(id)
    setBatchState(state)
  }

  const handleToggleReadingView = async (mode: ReadingViewMode) => {
    setReadingViewMode(mode)
    if (mode === 'pdf_text' && hasPdf && !pdfDoc && id && selectedPaper) {
      try {
        setLoadingPdfText(true)
        const res = await api.getPaperPdfText(id, selectedPaper.id)
        setPdfDoc(res)
      } catch (err: any) {
        setPdfDoc(null)
        setErrorMessage(
          err.message ||
            'Não foi possível extrair o texto deste PDF — o arquivo pode ser composto por páginas digitalizadas como imagem.'
        )
      } finally {
        setLoadingPdfText(false)
      }
    }
  }

  const handleOpenPdfExternally = () => {
    if (!id || !selectedPaper || !hasPdf) return
    window.open(api.getPaperPdfUrl(id, selectedPaper.id), '_blank')
  }

  const handleDeletePDF = async () => {
    if (!id || !selectedPaper || !hasPdf) return
    if (!window.confirm('Deseja realmente desvincular o PDF deste trabalho?')) return
    try {
      setErrorMessage('')
      await api.deletePaperPDF(id, selectedPaper.id)
      setPdfState(EMPTY_PDF_STATE)
      setPdfDoc(null)
      setAcquireMessage('')
      setReadingViewMode('abstract')
    } catch (err: any) {
      setErrorMessage(err.message || 'Falha ao desvincular PDF.')
    }
  }

  const handleCopyFullText = () => {
    const textToCopy = readingViewMode === 'abstract' ? selectedPaper?.abstract : pdfExtractedText
    if (!textToCopy) return
    navigator.clipboard.writeText(textToCopy)
    setCopiedText(true)
    setTimeout(() => setCopiedText(false), 2000)
  }

  const questions = protocol?.extraction_questions || []

  const filteredPapers = useMemo(() => {
    if (!searchTerm.trim()) return papers
    const term = searchTerm.toLowerCase()
    return papers.filter(
      (p) =>
        p.title.toLowerCase().includes(term) ||
        (p.authors && p.authors.toLowerCase().includes(term)) ||
        (p.doi && p.doi.toLowerCase().includes(term))
    )
  }, [papers, searchTerm])

  const selectedIndex = filteredPapers.findIndex((p) => p.id === selectedPaper?.id)

  const handleSelectNextPaper = () => {
    if (!selectedPaper || filteredPapers.length === 0) return
    const currentIndex = filteredPapers.findIndex((p) => p.id === selectedPaper.id)
    if (currentIndex < filteredPapers.length - 1) {
      setSelectedPaper(filteredPapers[currentIndex + 1])
    }
  }

  const handleSelectPrevPaper = () => {
    if (!selectedPaper || filteredPapers.length === 0) return
    const currentIndex = filteredPapers.findIndex((p) => p.id === selectedPaper.id)
    if (currentIndex > 0) {
      setSelectedPaper(filteredPapers[currentIndex - 1])
    }
  }

  const scrollQueue = (direction: 'left' | 'right') => {
    if (!queueScrollRef.current) return
    const offset = direction === 'left' ? -350 : 350
    queueScrollRef.current.scrollBy({ left: offset, behavior: 'smooth' })
  }

  // Keyboard navigation between included papers
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
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedPaper, filteredPapers])

  // Count answered questions for the selected paper
  const answeredQuestionsCount = useMemo(() => {
    if (questions.length === 0) return 0
    return questions.filter((q) => q.id && answers[q.id] && answers[q.id].trim().length > 0).length
  }, [questions, answers])

  const completionPercentage = questions.length > 0
    ? Math.round((answeredQuestionsCount / questions.length) * 100)
    : 0

  // Formatação Estruturada de Parágrafos com Highlight de Busca
  const structuredParagraphs = useMemo(() => {
    if (readingViewMode === 'abstract') {
      if (!selectedPaper?.abstract) return []
      return selectedPaper.abstract.split(/\n\n+/).filter((p) => p.trim().length > 0)
    } else {
      if (!pdfExtractedText) return []
      return pdfExtractedText.split(/\n\n+/).filter((p) => p.trim().length > 0)
    }
  }, [readingViewMode, selectedPaper?.abstract, pdfExtractedText])

  const wordCount = useMemo(() => {
    const text = readingViewMode === 'abstract' ? selectedPaper?.abstract : pdfExtractedText
    if (!text) return 0
    return text.trim().split(/\s+/).length
  }, [readingViewMode, selectedPaper?.abstract, pdfExtractedText])

  const renderHighlightedText = (text: string) => {
    if (!textSearchTerm.trim()) return text

    const parts = text.split(new RegExp(`(${textSearchTerm.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&')})`, 'gi'))
    return parts.map((part, i) =>
      part.toLowerCase() === textSearchTerm.toLowerCase() ? (
        <mark key={i} className="text-highlight">
          {part}
        </mark>
      ) : (
        part
      )
    )
  }

  return (
    <div className="extraction-page animate-fade-in">
      {/* Hidden File Input for Local PDF Selection */}
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

      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-left">
          <div className="page-header-title-row">
            <button className="btn-back" onClick={() => navigate('/projects')}>
              <ArrowLeft size={13} /> Voltar
            </button>
            <h1 className="page-title">Extração de Dados (Triagem 2)</h1>
          </div>
          <p className="page-subtitle">
            Projeto: <strong>{activeProject?.title}</strong> — Extração estruturada a partir do texto completo dos estudos incluídos
          </p>
        </div>
        <div className="header-actions">
          {saveSuccess && (
            <span className="save-indicator success animate-fade-in">
              <CheckCircle2 size={14} /> Respostas Salvas!
            </span>
          )}
          <button
            type="button"
            className="btn-secondary"
            onClick={handleStartBatch}
            disabled={batchState?.status === 'running' || papers.length === 0}
            title="Procura o texto completo de todos os estudos incluídos que ainda não têm PDF"
          >
            {batchState?.status === 'running' ? (
              <>
                <RefreshCw size={14} className="animate-spin" /> Buscando PDFs...
              </>
            ) : (
              <>
                <Download size={14} /> Buscar PDFs de todos
              </>
            )}
          </button>
          {aiEnabled && (
            <button
              type="button"
              className="btn-secondary"
              onClick={handleExtractWithAI}
              disabled={extractingAI || !selectedPaper || questions.length === 0}
              title="Extrai automaticamente as respostas do PDF/Resumo usando Assistência"
            >
              {extractingAI ? (
                <>
                  <RefreshCw size={14} className="animate-spin" /> Extraindo...
                </>
              ) : (
                <>
                  <Sparkles size={14} /> Extrair com Assistência
                </>
              )}
            </button>
          )}
          <button className="btn-primary" onClick={handleSaveAnswers} disabled={saving || !selectedPaper}>
            <Save size={14} />
            {saving ? 'Salvando...' : 'Salvar Respostas'}
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="extraction-error-banner animate-fade-in">
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
          <button className="btn-close-error" onClick={() => setErrorMessage('')}>✕</button>
        </div>
      )}

      {/* Progresso da busca de PDFs em lote */}
      {batchState && batchState.status !== 'idle' && batchState.status !== 'empty' && (
        <div className="pdf-batch-banner animate-fade-in">
          <div className="batch-banner-info">
            <Download size={15} className="icon-accent" />
            <div>
              <strong>
                {batchState.status === 'running'
                  ? 'Buscando PDFs dos estudos incluídos'
                  : batchState.status === 'cancelled'
                    ? 'Busca de PDFs cancelada'
                    : 'Busca de PDFs concluída'}
              </strong>
              <span className="batch-banner-counts">
                {batchState.processed} de {batchState.total} processados — {batchState.succeeded}{' '}
                obtidos, {batchState.failed} sem arquivo
                {batchState.current_title && batchState.status === 'running' && (
                  <em> — {batchState.current_title}</em>
                )}
              </span>
            </div>
          </div>
          <div className="batch-banner-actions">
            <div className="progress-bar-container batch">
              <div
                className="progress-bar-fill"
                style={{ width: `${batchState.progress_percent}%` }}
              />
            </div>
            {batchState.status === 'running' ? (
              <button type="button" className="btn-secondary small" onClick={handleCancelBatch}>
                <StopCircle size={13} /> Parar
              </button>
            ) : (
              <button
                type="button"
                className="btn-close-error"
                onClick={() => setBatchState(null)}
              >
                ✕
              </button>
            )}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          FILA HORIZONTAL DE ESTUDOS INCLUÍDOS (ACIMA)
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="extraction-queue-container">
        {/* Top Controls of the Queue */}
        <div className="queue-controls-bar">
          <div className="queue-filter-info">
            <span className="queue-status-chip inc">
              <Layers size={13} /> Estudos Incluídos: <strong>{papers.length}</strong>
            </span>
            {selectedPaper && questions.length > 0 && (
              <span className={`queue-completion-chip ${completionPercentage === 100 ? 'done' : ''}`}>
                <CheckCircle2 size={13} />
                Artigo Selecionado: <strong>{answeredQuestionsCount} / {questions.length}</strong> perguntas ({completionPercentage}%)
              </span>
            )}
          </div>

          <div className="queue-search-input-wrapper">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              placeholder="Buscar em estudos incluídos (título, autor, DOI)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="queue-counter-inline">
            <span>
              Estudo <strong>{selectedIndex >= 0 ? selectedIndex + 1 : 0}</strong> de {filteredPapers.length}
            </span>
          </div>
        </div>

        {/* Horizontal Strip */}
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
              <div className="queue-loading-state">
                <div className="loading-spinner animate-spin" />
                <span>Carregando estudos incluídos...</span>
              </div>
            ) : filteredPapers.length === 0 ? (
              <div className="queue-empty-state">
                <BookOpen size={18} />
                <span>
                  {papers.length === 0
                    ? 'Nenhum estudo incluído para extração. Conclua a Triagem 1 primeiro.'
                    : 'Nenhum estudo incluído corresponde à busca.'}
                </span>
                {papers.length === 0 && (
                  <button
                    type="button"
                    className="btn-secondary small"
                    onClick={() => navigate(`/projects/${id}/screening`)}
                  >
                    Ir para Triagem 1
                  </button>
                )}
              </div>
            ) : (
              filteredPapers.map((paper) => {
                const isSelected = selectedPaper?.id === paper.id
                return (
                  <div
                    key={paper.id}
                    className={`queue-paper-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedPaper(paper)}
                    title={paper.title}
                  >
                    <div className="queue-card-meta">
                      <span className="badge-decision badge-incluído">Incluído</span>
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
          ÁREA DE TRABALHO PRINCIPAL LADO A LADO COM SCROLL INDEPENDENTE
      ═══════════════════════════════════════════════════════════════════ */}
      {selectedPaper ? (
        <div className="extraction-workbench-grid animate-fade-in">
          {/* ── COLUNA DA ESQUERDA: LEITURA DO ARTIGO (ABSTRACT & METADATA) ── */}
          <div
            className={`paper-reading-pane ${isDragOver ? 'drag-over-active' : ''}`}
            onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(true) }}
            onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(false) }}
            onDrop={(e) => {
              e.preventDefault(); e.stopPropagation(); setIsDragOver(false)
              const file = e.dataTransfer.files?.[0]
              if (file) handleUploadFile(file)
            }}
          >
            {/* Reading Actions Bar (Sticky) */}
            <div className="reading-actions-toolbar">
              <div className="pdf-status-group">
                {hasPdf ? (
                  <div
                    className={`badge-pdf ${pdfState.pdf_is_scanned ? 'warning' : 'ready'}`}
                    title={
                      pdfState.pdf_resolved_url
                        ? `Origem: ${pdfState.pdf_resolved_url}`
                        : 'Arquivo anexado manualmente'
                    }
                  >
                    <FileCheck size={14} />
                    {pdfState.pdf_is_scanned ? 'PDF sem texto' : 'PDF vinculado'}
                    {pdfState.pdf_page_count > 0 && (
                      <span className="badge-pdf-meta">{pdfState.pdf_page_count}p</span>
                    )}
                  </div>
                ) : (
                  <div className="badge-pdf missing">
                    <FileX size={14} /> Sem PDF
                  </div>
                )}

                {/* Alternador de Visão: Resumo | PDF renderizado | Texto extraído */}
                <div className="view-mode-toggle-group">
                  <button
                    type="button"
                    className={`btn-view-mode ${readingViewMode === 'abstract' ? 'active' : ''}`}
                    onClick={() => handleToggleReadingView('abstract')}
                  >
                    <BookOpen size={11} /> Resumo
                  </button>
                  <button
                    type="button"
                    className={`btn-view-mode ${readingViewMode === 'pdf_view' ? 'active' : ''}`}
                    onClick={() => handleToggleReadingView('pdf_view')}
                    disabled={!hasPdf}
                    title={hasPdf ? 'Ver o PDF original' : 'Nenhum PDF vinculado'}
                  >
                    <FileText size={11} /> PDF
                  </button>
                  <button
                    type="button"
                    className={`btn-view-mode ${readingViewMode === 'pdf_text' ? 'active' : ''}`}
                    onClick={() => handleToggleReadingView('pdf_text')}
                    disabled={!hasPdf}
                    title={hasPdf ? 'Ver o texto extraído do PDF' : 'Nenhum PDF vinculado'}
                  >
                    <FileCode size={11} /> Texto
                  </button>
                </div>

                {/* Busca automática multi-estratégia */}
                <button
                  type="button"
                  className="btn-pdf-action primary"
                  onClick={handleAcquirePDF}
                  disabled={acquiring}
                  title="Procura o texto completo por DOI, Unpaywall, OpenAlex, Crossref, Europe PMC, padrões de repositório e na página de origem"
                >
                  {acquiring ? (
                    <>
                      <RefreshCw size={12} className="animate-spin" /> Procurando...
                    </>
                  ) : (
                    <>
                      <FileSearch size={12} /> {hasPdf ? 'Buscar novamente' : 'Buscar PDF'}
                    </>
                  )}
                </button>

                {/* Botão de Anexar / Substituir PDF Local */}
                <button
                  type="button"
                  className="btn-pdf-action"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingPdf}
                  title="Selecionar arquivo PDF do computador ou arrastar sobre a tela"
                >
                  {uploadingPdf ? (
                    <>
                      <RefreshCw size={12} className="animate-spin" /> Anexando...
                    </>
                  ) : (
                    <>
                      <Upload size={12} /> {hasPdf ? 'Substituir' : 'Anexar'}
                    </>
                  )}
                </button>

                <button
                  type="button"
                  className="btn-pdf-action"
                  onClick={() => setIsUrlModalOpen(true)}
                  title="Colar ou editar link direto do PDF"
                >
                  <Link size={12} /> Link
                </button>

                {(pdfState.attempts.length > 0 || candidates) && (
                  <button
                    type="button"
                    className={`btn-pdf-action ${showDiagnostics ? 'highlight' : ''}`}
                    onClick={() => setShowDiagnostics((prev) => !prev)}
                    title="Ver o que a busca automática tentou"
                  >
                    <ListChecks size={12} /> Diagnóstico
                  </button>
                )}

                {hasPdf && (
                  <>
                    <button
                      type="button"
                      className="btn-pdf-action highlight"
                      onClick={handleOpenPdfExternally}
                      title="Abrir PDF no visualizador padrão do sistema"
                    >
                      <ExternalLink size={12} /> Abrir
                    </button>
                    <button
                      type="button"
                      className="btn-pdf-action danger"
                      onClick={handleDeletePDF}
                      title="Desvincular PDF deste artigo"
                    >
                      <Trash2 size={12} />
                    </button>
                  </>
                )}

                {selectedPaper.doi && (
                  <a
                    href={`https://doi.org/${selectedPaper.doi}`}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-pdf-action link"
                    title="Abrir página oficial do DOI"
                  >
                    <ExternalLink size={12} /> DOI
                  </a>
                )}
              </div>

              <div className="reading-nav-arrows">
                <button
                  type="button"
                  className="btn-study-step"
                  onClick={handleSelectPrevPaper}
                  title="Estudo Anterior (Atalho: Seta Esquerda)"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="study-counter-label">
                  {selectedIndex >= 0 ? selectedIndex + 1 : 1} / {filteredPapers.length}
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

            {/* Mensagem de resultado da última aquisição */}
            {acquireMessage && (
              <div className="pdf-acquire-note animate-fade-in">
                <FileSearch size={14} className="icon-accent" />
                <span>{acquireMessage}</span>
                <button
                  type="button"
                  className="btn-close-error"
                  onClick={() => setAcquireMessage('')}
                >
                  ✕
                </button>
              </div>
            )}

            {/* Painel de Diagnóstico da Busca de PDF */}
            {showDiagnostics && (
              <div className="pdf-diagnostics-panel animate-fade-in">
                <div className="diagnostics-header">
                  <div className="diagnostics-title-group">
                    <ListChecks size={15} className="icon-accent" />
                    <h4>Trilha da busca automática</h4>
                    <span className="diagnostics-count">
                      {pdfState.attempts.length} tentativa(s)
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn-close-error"
                    onClick={() => setShowDiagnostics(false)}
                  >
                    <ChevronDown size={14} />
                  </button>
                </div>

                {pdfState.attempts.length === 0 ? (
                  <p className="diagnostics-empty">
                    Nenhuma busca automática executada para este trabalho ainda.
                  </p>
                ) : (
                  <ul className="diagnostics-list">
                    {pdfState.attempts.map((attempt, idx) => (
                      <li key={idx} className={`diagnostics-item status-${attempt.status}`}>
                        <span className="diag-strategy">{strategyLabel(attempt.strategy)}</span>
                        <span className={`diag-status ${attempt.status}`}>
                          {ATTEMPT_STATUS_LABELS[attempt.status] || attempt.status}
                        </span>
                        <span className="diag-detail">{attempt.detail}</span>
                        {attempt.url && (
                          <a
                            className="diag-url"
                            href={attempt.url}
                            target="_blank"
                            rel="noreferrer"
                            title={attempt.url}
                          >
                            abrir link <ExternalLink size={10} />
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                )}

                <div className="diagnostics-actions">
                  <button
                    type="button"
                    className="btn-secondary small"
                    onClick={handleLoadCandidates}
                    disabled={loadingCandidates}
                  >
                    {loadingCandidates ? (
                      <>
                        <RefreshCw size={12} className="animate-spin" /> Levantando links...
                      </>
                    ) : (
                      <>
                        <Search size={12} /> Listar links candidatos
                      </>
                    )}
                  </button>
                  {selectedPaper.doi && (
                    <a
                      className="btn-secondary small"
                      href={`https://doi.org/${selectedPaper.doi}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <ExternalLink size={12} /> Abrir DOI
                    </a>
                  )}
                  <a
                    className="btn-secondary small"
                    href={`https://scholar.google.com/scholar?q=${encodeURIComponent(
                      selectedPaper.title
                    )}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Search size={12} /> Procurar no Google Acadêmico
                  </a>
                  <button
                    type="button"
                    className="btn-secondary small"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload size={12} /> Anexar arquivo baixado
                  </button>
                </div>

                {candidates && (
                  <div className="candidates-block">
                    <h5>
                      Links candidatos encontrados ({candidates.length})
                      <span className="candidates-hint">
                        — abra no navegador e, se for o arquivo certo, use "Link" ou anexe
                      </span>
                    </h5>
                    {candidates.length === 0 ? (
                      <p className="diagnostics-empty">
                        Nenhum link candidato: o registro não tem DOI nem página de origem
                        utilizável.
                      </p>
                    ) : (
                      <ul className="candidates-list">
                        {candidates.map((candidate, idx) => (
                          <li key={idx}>
                            <span className="cand-strategy">
                              {strategyLabel(candidate.strategy)}
                            </span>
                            <a href={candidate.url} target="_blank" rel="noreferrer">
                              {candidate.url}
                            </a>
                            <button
                              type="button"
                              className="btn-cand-use"
                              title="Usar este link como origem e tentar baixar"
                              onClick={() => {
                                setCustomDownloadUrl(candidate.url)
                                setIsUrlModalOpen(true)
                              }}
                            >
                              usar
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Reading Content (Scrollable Container) */}
            <div className="paper-reading-content">
              <h2 className="reading-title">{selectedPaper.title}</h2>

              <div className="reading-meta-grid">
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
                    <span>DOI: {selectedPaper.doi}</span>
                  </div>
                )}
              </div>

              {/* Advanced Reading Box */}
              <div className="reading-abstract-container">
                {/* Secondary Academic Tools Header */}
                <div className="abstract-header-row">
                  <div className="abstract-header-title-group">
                    <FileText size={16} className="icon-accent" />
                    <h3>
                      {readingViewMode === 'abstract'
                        ? 'Resumo do Estudo (Abstract)'
                        : readingViewMode === 'pdf_view'
                          ? 'Documento Original (PDF)'
                          : 'Texto Integral Extraído do PDF'}
                    </h3>
                    {readingViewMode === 'pdf_view' ? (
                      <span className="word-count-badge">
                        {pdfState.pdf_page_count || '—'} páginas
                      </span>
                    ) : (
                      <span className="word-count-badge">{wordCount} palavras</span>
                    )}
                    {readingViewMode !== 'abstract' && pdfState.pdf_strategy && (
                      <span
                        className="provenance-badge"
                        title={pdfState.pdf_resolved_url || 'Arquivo anexado manualmente'}
                      >
                        origem: {strategyLabel(pdfState.pdf_strategy)}
                      </span>
                    )}
                  </div>

                  {/* Search inside text & Typography Zoom */}
                  <div
                    className="academic-reader-tools"
                    style={{ display: readingViewMode === 'pdf_view' ? 'none' : undefined }}
                  >
                    <div className="reader-search-input-box">
                      <Search size={12} className="icon-subtle" />
                      <input
                        type="text"
                        placeholder="Buscar termo no texto..."
                        value={textSearchTerm}
                        onChange={(e) => setTextSearchTerm(e.target.value)}
                      />
                      {textSearchTerm && (
                        <button
                          type="button"
                          className="btn-clear-search"
                          onClick={() => setTextSearchTerm('')}
                        >
                          ✕
                        </button>
                      )}
                    </div>

                    <div className="font-size-stepper">
                      <button
                        type="button"
                        onClick={() => setFontSizeLevel((prev) => Math.max(11, prev - 1))}
                        disabled={fontSizeLevel <= 11}
                        title="Diminuir tamanho da fonte"
                      >
                        <ZoomOut size={12} />
                      </button>
                      <span className="font-level-indicator">{fontSizeLevel}px</span>
                      <button
                        type="button"
                        onClick={() => setFontSizeLevel((prev) => Math.min(18, prev + 1))}
                        disabled={fontSizeLevel >= 18}
                        title="Aumentar tamanho da fonte"
                      >
                        <ZoomIn size={12} />
                      </button>
                    </div>

                    <button
                      type="button"
                      className="btn-reader-tool"
                      onClick={handleCopyFullText}
                      title="Copiar texto para área de transferência"
                    >
                      {copiedText ? <Check size={12} /> : <Copy size={12} />}
                    </button>
                  </div>
                </div>

                {/* Visualizador do PDF original (renderizado pelo Chromium) */}
                {readingViewMode === 'pdf_view' ? (
                  <div className="pdf-embed-container">
                    {hasPdf && id && selectedPaper ? (
                      <>
                        {pdfState.pdf_is_scanned && (
                          <div className="pdf-scanned-warning">
                            <AlertTriangle size={14} />
                            <span>
                              Documento digitalizado: é possível ler as páginas aqui, mas não há
                              texto selecionável para busca nem para a extração assistida.
                            </span>
                          </div>
                        )}
                        <iframe
                          key={`${selectedPaper.id}-${pdfState.pdf_acquired_at || 'local'}`}
                          className="pdf-embed-frame"
                          title={`PDF — ${selectedPaper.title}`}
                          src={api.getPaperPdfUrl(id, selectedPaper.id)}
                        />
                      </>
                    ) : (
                      <div className="empty-abstract-state">
                        <FileX size={24} />
                        <p>Nenhum PDF vinculado a este trabalho.</p>
                      </div>
                    )}
                  </div>
                ) : (

                /* Article Typography Reader Card */
                <div
                  className="abstract-reading-card academic-reader-body"
                  style={{ fontSize: `${fontSizeLevel}px` }}
                >
                  {readingViewMode === 'abstract' ? (
                    selectedPaper.abstract ? (
                      <div className="academic-paragraphs-container">
                        {structuredParagraphs.map((p, idx) => (
                          <p key={idx} className="academic-paragraph">
                            {renderHighlightedText(p)}
                          </p>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-abstract-state">
                        <AlertCircle size={24} />
                        <p>Resumo textual não encontrado nos metadados coletados deste registro.</p>
                        <div className="empty-abstract-actions">
                          <button
                            type="button"
                            className="btn-primary small"
                            onClick={() => fileInputRef.current?.click()}
                          >
                            <Upload size={13} /> Anexar PDF Local
                          </button>
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
                      </div>
                    )
                  ) : (
                    /* Visualizador de Texto do PDF Formatado */
                    <div className="pdf-text-viewer">
                      {loadingPdfText ? (
                        <div className="pdf-loading-state">
                          <RefreshCw size={22} className="animate-spin icon-accent" />
                          <span>Extraindo e formatando texto integral do PDF...</span>
                        </div>
                      ) : structuredParagraphs.length > 0 ? (
                        <div className="academic-paragraphs-container">
                          {structuredParagraphs.map((p, idx) => {
                            const isHeading =
                              p.length < 80 &&
                              (p.toUpperCase() === p ||
                                /^(abstract|introdução|introduction|metodologia|methodology|métodos|methods|resultados|results|discussão|discussion|conclusão|conclusion|referências|references|materiais)/i.test(p))

                            return (
                              <p
                                key={idx}
                                className={`academic-paragraph ${isHeading ? 'section-heading-highlight' : ''}`}
                              >
                                {renderHighlightedText(p)}
                              </p>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="empty-abstract-state">
                          <AlertTriangle size={24} />
                          <p>
                            {pdfState.pdf_is_scanned
                              ? 'Este PDF é composto por páginas digitalizadas (imagem), sem camada de texto. Use a aba "PDF" para ler o documento; para extração assistida, anexe uma versão com texto pesquisável (OCR).'
                              : 'O texto deste PDF não pôde ser extraído ou está vazio.'}
                          </p>
                          <div className="empty-abstract-actions">
                            <button
                              type="button"
                              className="btn-secondary small"
                              onClick={() => handleToggleReadingView('pdf_view')}
                            >
                              <FileText size={13} /> Ver documento original
                            </button>
                            <button
                              type="button"
                              className="btn-secondary small"
                              onClick={async () => {
                                if (!id || !selectedPaper) return
                                setLoadingPdfText(true)
                                try {
                                  setPdfDoc(await api.getPaperPdfText(id, selectedPaper.id, true))
                                } finally {
                                  setLoadingPdfText(false)
                                }
                              }}
                            >
                              <RefreshCw size={13} /> Reextrair texto
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                )}
              </div>
            </div>
          </div>

          {/* ── COLUNA DA DIREITA: FORMULÁRIO DE EXTRAÇÃO (Q1..Qn) COM SCROLL ── */}
          <div className="extraction-form-pane">
            <div className="form-pane-header">
              <div className="form-pane-title-group">
                <FileText size={18} className="icon-accent" />
                <div>
                  <h3 className="form-pane-title">Matriz de Extração de Dados</h3>
                  <span className="form-pane-counter">
                    {answeredQuestionsCount} de {questions.length} perguntas respondidas ({completionPercentage}%)
                  </span>
                </div>
              </div>
              <div className="progress-bar-container">
                <div className="progress-bar-fill" style={{ width: `${completionPercentage}%` }} />
              </div>
            </div>

            {/* Questions Form Body (Scrollable Container) */}
            <div className="extraction-questions-scroll">
              {questions.length === 0 ? (
                <div className="empty-questions-card">
                  <AlertCircle size={28} className="icon-accent" />
                  <h4>Nenhuma pergunta de extração cadastrada</h4>
                  <p>
                    Cadastre as perguntas de pesquisa na aba <strong>5. Formulário de Extração</strong> do Estúdio de Protocolo.
                  </p>
                  <button
                    type="button"
                    className="btn-secondary small"
                    onClick={() => navigate(`/projects/${id}/protocol`)}
                  >
                    Ir para o Protocolo
                  </button>
                </div>
              ) : (
                questions.map((q, idx) => {
                  const currentAnswer = (q.id && answers[q.id]) || ''
                  const evidence = q.id ? evidences[q.id] : undefined
                  const isFilled = currentAnswer.trim().length > 0

                  return (
                    <div
                      key={q.id || idx}
                      className={`question-field-card ${isFilled ? 'filled' : 'pending'}`}
                    >
                      <div className="question-field-header">
                        <div className="question-code-badge">
                          Q{idx + 1}
                        </div>
                        <label className="question-text-label" htmlFor={`q-${q.id || idx}`}>
                          {q.text}
                        </label>
                        {isFilled && (
                          <span className="badge-answered">
                            <CheckCircle2 size={13} /> Respondida
                          </span>
                        )}
                      </div>

                      <textarea
                        id={`q-${q.id || idx}`}
                        className="question-textarea"
                        rows={3}
                        placeholder="Insira os achados, evidências e dados extraídos deste artigo..."
                        value={currentAnswer}
                        onChange={(e) => q.id && handleAnswerChange(q.id, e.target.value)}
                      />

                      {/* Evidência ancorada: trecho literal e página de onde veio */}
                      {evidence?.text && (
                        <div className="answer-evidence-block">
                          <div className="evidence-header">
                            <Quote size={11} />
                            <span>Evidência no texto</span>
                            {evidence.page && (
                              <button
                                type="button"
                                className="evidence-page-chip"
                                title="Abrir o documento original nesta página"
                                onClick={() => {
                                  if (!id || !selectedPaper || !hasPdf) return
                                  window.open(
                                    `${api.getPaperPdfUrl(id, selectedPaper.id)}#page=${evidence.page}`,
                                    '_blank'
                                  )
                                }}
                              >
                                p. {evidence.page}
                              </button>
                            )}
                          </div>
                          <blockquote>{evidence.text}</blockquote>
                        </div>
                      )}
                    </div>
                  )
                })
              )}

              {/* Synthesis Bridge Banner */}
              <div className="synthesis-bridge-card">
                <div className="bridge-content">
                  <Sparkles size={20} className="icon-accent" />
                  <div>
                    <strong>Fase Posterior: Síntese dos Achados</strong>
                    <p>
                      Após extrair os dados de todos os estudos incluídos, os dados consolidados alimentarão a redação da <strong>Síntese e Resultados</strong> no Estúdio de Protocolo.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-secondary small"
                  onClick={() => navigate(`/projects/${id}/protocol`)}
                >
                  Ver Protocolo & Síntese <ArrowRight size={13} />
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="extraction-empty-state-card animate-fade-in">
          <BookOpen size={48} className="icon-accent" />
          <h3>Nenhum Estudo Incluído Selecionado</h3>
          <p>
            {papers.length === 0
              ? 'Nenhum artigo foi classificado como "Incluído" na Triagem 1 até o momento.'
              : 'Selecione um artigo na esteira superior para preencher a matriz de extração.'}
          </p>
          {papers.length === 0 && (
            <button
              type="button"
              className="btn-primary"
              onClick={() => navigate(`/projects/${id}/screening`)}
            >
              Ir para Triagem 1 (Elegibilidade) <ArrowRight size={14} />
            </button>
          )}
        </div>
      )}

      {/* Modal / Diálogo Rápido de Link Direto de PDF */}
      {isUrlModalOpen && (
        <div className="modal-overlay animate-fade-in" onClick={() => setIsUrlModalOpen(false)}>
          <div className="modal-content-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <Link size={16} className="icon-accent" />
                <h3>Link Direto do PDF</h3>
              </div>
              <button className="btn-close-modal" onClick={() => setIsUrlModalOpen(false)}>
                <X size={16} />
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-desc">
                Cole a URL direta do arquivo PDF (ex: repositório institucional, SciELO, ResearchGate) para download automático:
              </p>
              <input
                type="url"
                className="input-text-full"
                placeholder="https://exemplo.org/artigo.pdf"
                value={customDownloadUrl}
                onChange={(e) => setCustomDownloadUrl(e.target.value)}
                autoFocus
              />
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setIsUrlModalOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={handleSaveCustomDownloadUrl}
                disabled={!customDownloadUrl.trim() || acquiring}
              >
                {acquiring ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" /> Procurando...
                  </>
                ) : (
                  <>
                    <Download size={14} /> Salvar link e buscar PDF
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
