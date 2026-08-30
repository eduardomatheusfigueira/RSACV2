/**
 * Revsist — Extraction Page (Triagem 2 / Extração de Dados)
 *
 * Layout Metodológico Otimizado e Ergonômico:
 * 1. Fila Horizontal de Estudos Incluídos (no topo): busca rápida, contagem e esteira de cards.
 * 2. Área de Trabalho Lado a Lado (Two-Column Workspace) com ROLAGEM INDEPENDENTE:
 *    - Coluna da Esquerda: Metadados, Leitor Avançado de Texto Completo / Resumo com busca e zoom.
 *    - Coluna da Direita: Formulário de Extração com Assistência Global e INDIVIDUAL por pergunta,
 *      evidências comprovatórias e barra de progresso.
 */

import { useState, useEffect, useRef, useMemo, Fragment } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as Tabs from '@radix-ui/react-tabs'
import {
  FileText,
  Sparkles,
  Save,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Download,
  FileCheck,
  FileX,
  Search,
  ExternalLink,
  BookOpen,
  Calendar,
  User,
  Building,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Layers,
  Upload,
  Trash2,
  Link,
  FileCode,
  ZoomIn,
  ZoomOut,
  Copy,
  Check,
  Quote,
  CheckCheck,
  StopCircle,
} from 'lucide-react'
import { api, foiCancelado } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import {
  PageHeader,
  Button,
  Card,
  EmptyState,
  LoadingState,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui'
import type { Paper, Protocol } from '@/types/api'
import './ExtractionPage.css'

interface EvidenceItem {
  evidence: string
  page_ref: string
  source_kind: string
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
  const [evidences, setEvidences] = useState<Record<string, EvidenceItem>>({})
  const [hasPdf, setHasPdf] = useState(false)
  const [pdfPath, setPdfPath] = useState<string | null>(null)
  const [pdfExtractedText, setPdfExtractedText] = useState<string | null>(null)
  const [readingViewMode, setReadingViewMode] = useState<'abstract' | 'pdf_text'>('abstract')
  const [loadingPdfText, setLoadingPdfText] = useState(false)

  // Advanced Full-Text Reader Tools
  const [fontSizeLevel, setFontSizeLevel] = useState<number>(13) // 11 to 18
  const [textSearchTerm, setTextSearchTerm] = useState('')
  const [copiedText, setCopiedText] = useState(false)

  // Actions & AI Loading State
  const [saving, setSaving] = useState(false)
  const [extractingAI, setExtractingAI] = useState(false)
  const [extractingSingleId, setExtractingSingleId] = useState<string | null>(null)
  /* A extração assistida percorre todas as perguntas do protocolo num único
     pedido e pode levar minutos. Sem um controlador, a única saída de quem
     desistisse era fechar a tela — e mesmo assim a espera continuava. */
  const extracaoAbortRef = useRef<AbortController | null>(null)
  const [downloadingPdf, setDownloadingPdf] = useState(false)
  const [uploadingPdf, setUploadingPdf] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [isUrlModalOpen, setIsUrlModalOpen] = useState(false)
  const [customDownloadUrl, setCustomDownloadUrl] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  // Search & Navigation in Included Papers
  const [searchTerm, setSearchTerm] = useState('')
  const [mobileTab, setMobileTab] = useState<'document' | 'questions' | 'queue'>('document')
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
      setPdfExtractedText(null)
      setTextSearchTerm('')
      setCustomDownloadUrl(selectedPaper.download_url || '')
    }
  }, [id, selectedPaper?.id])

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
      setHasPdf(extRes.has_pdf)
      setPdfPath(extRes.pdf_path)

      const ansMap: Record<string, string> = {}
      const evMap: Record<string, EvidenceItem> = {}

      extRes.answers.forEach((a) => {
        ansMap[a.question_id] = a.answer
        if (a.evidence || a.page_ref || a.source_kind) {
          evMap[a.question_id] = {
            evidence: a.evidence || '',
            page_ref: a.page_ref || '',
            source_kind: a.source_kind || '',
          }
        }
      })
      setAnswers(ansMap)
      setEvidences(evMap)
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

  // ── Extração com Assistência Global (todas as perguntas) ──────────
  const handleExtractWithAI = async () => {
    if (!id || !selectedPaper) return
    try {
      setExtractingAI(true)
      setErrorMessage('')
      extracaoAbortRef.current?.abort()
      const controlador = new AbortController()
      extracaoAbortRef.current = controlador
      const res = await api.extractAnswersWithAI(id, selectedPaper.id, undefined, controlador.signal)
      const nextAns = { ...answers }
      const nextEv = { ...evidences }

      res.answers?.forEach((a: any) => {
        nextAns[a.question_id] = a.answer
        if (a.evidence || a.page_ref || a.source_kind) {
          nextEv[a.question_id] = {
            evidence: a.evidence || '',
            page_ref: a.page_ref || '',
            source_kind: a.source_kind || '',
          }
        }
      })
      setAnswers(nextAns)
      setEvidences(nextEv)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err: any) {
      if (foiCancelado(err)) return
      console.error('Erro ao extrair com assistência:', err)
      setErrorMessage(err.message || 'Falha ao processar extração assistida.')
    } finally {
      extracaoAbortRef.current = null
      setExtractingAI(false)
    }
  }

  /** Solta a tela da extração em curso. O servidor conclui o que começou. */
  const handleCancelExtraction = () => {
    extracaoAbortRef.current?.abort()
    extracaoAbortRef.current = null
    setExtractingAI(false)
    setExtractingSingleId(null)
  }

  // ── Extração com Assistência INDIVIDUAL (apenas uma pergunta) ────
  const handleExtractSingleQuestion = async (questionId: string) => {
    if (!id || !selectedPaper || !questionId) return
    try {
      setExtractingSingleId(questionId)
      setErrorMessage('')
      extracaoAbortRef.current?.abort()
      const controlador = new AbortController()
      extracaoAbortRef.current = controlador
      const res = await api.extractAnswersWithAI(id, selectedPaper.id, questionId, controlador.signal)
      const nextAns = { ...answers }
      const nextEv = { ...evidences }

      res.answers?.forEach((a: any) => {
        if (a.question_id === questionId) {
          nextAns[a.question_id] = a.answer
          if (a.evidence || a.page_ref || a.source_kind) {
            nextEv[a.question_id] = {
              evidence: a.evidence || '',
              page_ref: a.page_ref || '',
              source_kind: a.source_kind || '',
            }
          }
        }
      })
      setAnswers(nextAns)
      setEvidences(nextEv)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err: any) {
      if (foiCancelado(err)) return
      console.error(`Erro ao extrair pergunta ${questionId}:`, err)
      setErrorMessage(err.message || 'Falha ao processar extração da pergunta.')
    } finally {
      extracaoAbortRef.current = null
      setExtractingSingleId(null)
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
      const res = await api.uploadPaperPDF(id, selectedPaper.id, file)
      setHasPdf(true)
      setPdfPath(res.pdf_path)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err: any) {
      console.error('Erro no upload do PDF:', err)
      setErrorMessage(err.message || 'Falha no upload do arquivo PDF.')
    } finally {
      setUploadingPdf(false)
    }
  }

  const handleDownloadPDF = async () => {
    if (!id || !selectedPaper) return
    try {
      setDownloadingPdf(true)
      setErrorMessage('')
      const res = await api.downloadPaperPDF(id, selectedPaper.id)
      if (res.success && res.pdf_path) {
        setHasPdf(true)
        setPdfPath(res.pdf_path)
      } else {
        setErrorMessage(res.message || 'Não foi possível baixar o PDF automaticamente.')
      }
    } catch (err: any) {
      console.error('Erro ao baixar PDF:', err)
      setErrorMessage(err.message || 'Não foi possível baixar o PDF automaticamente da URL.')
    } finally {
      setDownloadingPdf(false)
    }
  }

  const handleSaveCustomDownloadUrl = async () => {
    if (!id || !selectedPaper || !customDownloadUrl.trim()) return
    try {
      setDownloadingPdf(true)
      setErrorMessage('')
      await api.updatePaperDownloadUrl(id, selectedPaper.id, customDownloadUrl.trim())
      selectedPaper.download_url = customDownloadUrl.trim()
      setIsUrlModalOpen(false)
      const res = await api.downloadPaperPDF(id, selectedPaper.id)
      if (res.success && res.pdf_path) {
        setHasPdf(true)
        setPdfPath(res.pdf_path)
      } else {
        setErrorMessage(res.message || 'Link salvo, mas não foi possível obter o PDF diretamente.')
      }
    } catch (err: any) {
      console.error('Erro ao baixar por novo link:', err)
      setErrorMessage(err.message || 'Link salvo, mas não foi possível obter o PDF diretamente.')
    } finally {
      setDownloadingPdf(false)
    }
  }

  const handleToggleReadingView = async (mode: 'abstract' | 'pdf_text') => {
    setReadingViewMode(mode)
    if (mode === 'pdf_text' && hasPdf && !pdfExtractedText && id && selectedPaper) {
      try {
        setLoadingPdfText(true)
        const res = await api.getPaperPdfText(id, selectedPaper.id)
        setPdfExtractedText(res.text)
      } catch (err: any) {
        setPdfExtractedText('[Não foi possível extrair o texto deste PDF ou o arquivo é composto por páginas escaneadas como imagem.]')
      } finally {
        setLoadingPdfText(false)
      }
    }
  }

  // ── Sincronização de Ações com o Ribbon Bar ─────────────────────────
  const registerRibbonActions = useRibbonStore((s) => s.registerActions)
  const unregisterRibbonActions = useRibbonStore((s) => s.unregisterActions)

  useEffect(() => {
    registerRibbonActions({
      saveExtraction: handleSaveAnswers,
      extractAiGlobal: handleExtractWithAI,
      downloadPdf: handleDownloadPDF,
      openDoiLink: () => {
        if (selectedPaper?.doi) {
          window.open(`https://doi.org/${selectedPaper.doi}`, '_blank')
        }
      },
      hasPdf,
      hasDoi: !!selectedPaper?.doi,
      isExtractionSaving: saving,
    })
    return () => {
      unregisterRibbonActions([
        'saveExtraction',
        'extractAiGlobal',
        'downloadPdf',
        'openDoiLink',
        'hasPdf',
        'hasDoi',
        'isExtractionSaving',
      ])
    }
  }, [
    registerRibbonActions,
    unregisterRibbonActions,
    handleSaveAnswers,
    handleExtractWithAI,
    handleDownloadPDF,
    selectedPaper,
    hasPdf,
    saving,
  ])

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
      setHasPdf(false)
      setPdfPath(null)
      setPdfExtractedText(null)
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

      <PageHeader
        title="Extração de Dados (Triagem 2)"
        onBack={() => navigate('/projects')}
        subtitle={
          <span>
            Projeto: <strong>{activeProject?.title}</strong> — Extração estruturada a partir do texto completo dos
            estudos incluídos
          </span>
        }
        status={
          <>
            {saveSuccess && (
              <span className="save-indicator success animate-fade-in" role="status" aria-live="polite">
                <CheckCircle2 size={14} aria-hidden="true" /> Respostas Salvas!
              </span>
            )}
            {extractingAI && (
              <span className="save-indicator animate-fade-in" role="status" aria-live="polite">
                <RefreshCw size={13} className="animate-spin" aria-hidden="true" /> Extraindo todas as respostas…
                <button
                  type="button"
                  className="btn-inline-stop"
                  onClick={handleCancelExtraction}
                  title="Interromper a extração assistida"
                >
                  <StopCircle size={13} aria-hidden="true" /> Parar
                </button>
              </span>
            )}
          </>
        }
        primaryAction={
          /* "Extrair Todas com Assistência" saiu do cabeçalho — o ribbon já a
             despacha por `extractAiGlobal`. Aqui fica só o salvar. */
          <Button
            variant="primary"
            size="md"
            onClick={handleSaveAnswers}
            loading={saving}
            disabled={!selectedPaper}
            leftIcon={<Save size={14} />}
          >
            {saving ? 'Salvando…' : 'Salvar Respostas'}
          </Button>
        }
      />

      {errorMessage && (
        <div className="extraction-error-banner animate-fade-in">
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
          <button className="btn-close-error" onClick={() => setErrorMessage('')}>✕</button>
        </div>
      )}

      {/* ── NAVEGAÇÃO SEGMENTADA MOBILE (Exibida apenas em telas < 768px) ── */}
      <div className="extraction-mobile-segmented-nav">
        <button
          type="button"
          className={`mobile-seg-btn ${mobileTab === 'document' ? 'active' : ''}`}
          onClick={() => setMobileTab('document')}
        >
          <BookOpen size={15} />
          <span>Documento / PDF</span>
        </button>
        <button
          type="button"
          className={`mobile-seg-btn ${mobileTab === 'questions' ? 'active' : ''}`}
          onClick={() => setMobileTab('questions')}
        >
          <FileText size={15} />
          <span>Extração ({answeredQuestionsCount}/{questions.length})</span>
        </button>
        <button
          type="button"
          className={`mobile-seg-btn ${mobileTab === 'queue' ? 'active' : ''}`}
          onClick={() => setMobileTab('queue')}
        >
          <Layers size={15} />
          <span>Artigos ({papers.length})</span>
        </button>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          FILA HORIZONTAL DE ESTUDOS INCLUÍDOS (ACIMA)
      ═══════════════════════════════════════════════════════════════════ */}
      <div className={`extraction-queue-container mobile-tab-view ${mobileTab === 'queue' ? 'mobile-show' : ''}`}>
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
              <LoadingState size="inline" label="Carregando estudos incluídos…" />
            ) : filteredPapers.length === 0 ? (
              <EmptyState
                size="inline"
                icon={<BookOpen size={18} aria-hidden="true" />}
                title={papers.length === 0 ? 'Nenhum estudo incluído ainda' : 'Nenhum estudo corresponde à busca'}
                description={
                  papers.length === 0
                    ? 'A extração trabalha sobre o que a Triagem 1 incluiu. Conclua a triagem para povoar esta fila.'
                    : 'Ajuste ou limpe o termo de busca para ver os estudos incluídos.'
                }
                action={
                  papers.length === 0 ? (
                    <Button variant="secondary" size="sm" onClick={() => navigate(`/projects/${id}/screening`)}>
                      Ir para Triagem 1
                    </Button>
                  ) : (
                    <Button variant="secondary" size="sm" onClick={() => setSearchTerm('')}>
                      Limpar busca
                    </Button>
                  )
                }
              />
            ) : (
              filteredPapers.map((paper) => {
                const isSelected = selectedPaper?.id === paper.id
                return (
                  <button
                    type="button"
                    key={paper.id}
                    className={`queue-paper-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedPaper(paper)}
                    title={paper.title}
                    aria-current={isSelected}
                  >
                    <div className="queue-card-meta">
                      <span className="badge-decision badge-incluído">Incluído</span>
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
          ÁREA DE TRABALHO PRINCIPAL LADO A LADO COM SCROLL INDEPENDENTE
      ═══════════════════════════════════════════════════════════════════ */}
      {selectedPaper ? (
        <div className="extraction-workbench-grid animate-fade-in">
          {/* ── COLUNA DA ESQUERDA: LEITURA DO ARTIGO (ABSTRACT & METADATA) ── */}
          <Tabs.Root
            className="view-mode-tabs-root"
            value={readingViewMode}
            onValueChange={(v) => handleToggleReadingView(v as 'abstract' | 'pdf_text')}
          >
          <div
            className={`paper-reading-pane mobile-tab-view ${mobileTab === 'document' ? 'mobile-show' : ''} ${isDragOver ? 'drag-over-active' : ''}`}
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
                  <div className="badge-pdf ready">
                    <FileCheck size={14} /> PDF Vinculado
                  </div>
                ) : (
                  <div className="badge-pdf missing">
                    <FileX size={14} /> Sem PDF
                  </div>
                )}

                {/* Alternador de Visão: Resumo <-> Texto Integral */}
                {hasPdf && (
                  <Tabs.List asChild>
                    <div className="view-mode-toggle-group">
                      <Tabs.Trigger
                        value="abstract"
                        className={`btn-view-mode ${readingViewMode === 'abstract' ? 'active' : ''}`}
                      >
                        <BookOpen size={11} /> Resumo
                      </Tabs.Trigger>
                      <Tabs.Trigger
                        value="pdf_text"
                        className={`btn-view-mode ${readingViewMode === 'pdf_text' ? 'active' : ''}`}
                      >
                        <FileCode size={11} /> Texto do PDF
                      </Tabs.Trigger>
                    </div>
                  </Tabs.List>
                )}

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
                      <Upload size={12} /> {hasPdf ? 'Substituir' : 'Anexar PDF'}
                    </>
                  )}
                </button>

                {selectedPaper.download_url && !hasPdf && (
                  <button
                    type="button"
                    className="btn-pdf-action"
                    onClick={handleDownloadPDF}
                    disabled={downloadingPdf}
                    title="Baixar PDF automaticamente da fonte"
                  >
                    {downloadingPdf ? (
                      <>
                        <RefreshCw size={12} className="animate-spin" /> Baixando...
                      </>
                    ) : (
                      <>
                        <Download size={12} /> Baixar
                      </>
                    )}
                  </button>
                )}

                <button
                  type="button"
                  className="btn-pdf-action"
                  onClick={() => setIsUrlModalOpen(true)}
                  title="Colar ou editar link direto do PDF"
                >
                  <Link size={12} /> Link
                </button>

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
                      aria-label="Desvincular PDF deste artigo"
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
                  aria-label="Estudo Anterior (Atalho: Seta Esquerda)"
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
                  aria-label="Próximo Estudo (Atalho: Seta Direita)"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>

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
                        : 'Texto Integral do Documento (PDF)'}
                    </h3>
                    <span className="word-count-badge">
                      {wordCount} palavras
                    </span>
                  </div>

                  {/* Search inside text & Typography Zoom */}
                  <div className="academic-reader-tools">
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

                {/* Article Typography Reader Card */}
                <div
                  className="abstract-reading-card academic-reader-body"
                  style={{ fontSize: `${fontSizeLevel}px` }}
                >
                  <Tabs.Content value="abstract">
                    {selectedPaper.abstract ? (
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
                    )}
                  </Tabs.Content>
                  <Tabs.Content value="pdf_text">
                    {/* Visualizador de Texto do PDF Formatado */}
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
                          <AlertCircle size={24} />
                          <p>O texto do PDF não pôde ser extraído ou está vazio.</p>
                        </div>
                      )}
                    </div>
                  </Tabs.Content>
                </div>
              </div>
            </div>
          </div>
          </Tabs.Root>

          {/* ── COLUNA DA DIREITA: FORMULÁRIO DE EXTRAÇÃO COM ASSISTÊNCIA INDIVIDUAL ── */}
          <div className={`extraction-form-pane mobile-tab-view ${mobileTab === 'questions' ? 'mobile-show' : ''}`}>
            <div className="form-pane-header">
              <div className="form-pane-title-group">
                <FileText size={18} className="icon-accent" />
                <div className="form-pane-title-details">
                  <div className="form-pane-title-row">
                    <h3 className="form-pane-title">Matriz de Extração de Dados</h3>
                    <span className={`analysis-base-pill ${hasPdf ? 'pdf' : 'abstract'}`}>
                      {hasPdf ? (
                        <>
                          <FileCheck size={11} /> Base: PDF Integral + Metadados
                        </>
                      ) : (
                        <>
                          <FileText size={11} /> Base: Resumo + Metadados
                        </>
                      )}
                    </span>
                  </div>
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
                  const isFilled = currentAnswer.trim().length > 0
                  const isExtractingThis = q.id ? extractingSingleId === q.id : false
                  const evidenceData = q.id ? evidences[q.id] : undefined

                  return (
                    <Card surface="primaria"
                      key={q.id || idx}
                      className={`question-field-card ${isFilled ? 'filled' : 'pending'}`}
                    >
                      <div className="question-field-header">
                        <div className="question-field-header-left">
                          <div className="question-code-badge">
                            Q{idx + 1}
                          </div>
                          <label className="question-text-label" htmlFor={`q-${q.id || idx}`}>
                            {q.text}
                          </label>
                        </div>

                        <div className="question-field-header-actions">
                          {isFilled && (
                            <span className="badge-answered">
                              <CheckCircle2 size={12} /> Respondida
                            </span>
                          )}

                          {aiEnabled && q.id && (
                            <button
                              type="button"
                              className="btn-extract-single-q"
                              onClick={() =>
                                isExtractingThis
                                  ? handleCancelExtraction()
                                  : handleExtractSingleQuestion(q.id!)
                              }
                              disabled={extractingAI && !isExtractingThis}
                              title={
                                isExtractingThis
                                  ? 'Interromper a extração desta pergunta'
                                  : 'Extrair ou atualizar apenas esta pergunta com Assistência'
                              }
                            >
                              {isExtractingThis ? (
                                <>
                                  <RefreshCw size={11} className="animate-spin" /> Cancelar
                                </>
                              ) : (
                                <>
                                  <Sparkles size={11} /> Extrair Questão
                                </>
                              )}
                            </button>
                          )}
                        </div>
                      </div>

                      <textarea
                        id={`q-${q.id || idx}`}
                        className="question-textarea"
                        rows={3}
                        placeholder="Insira os achados, evidências e dados extraídos deste artigo..."
                        value={currentAnswer}
                        onChange={(e) => q.id && handleAnswerChange(q.id, e.target.value)}
                      />

                      {/* Evidence Callout if generated by AI */}
                      {evidenceData && evidenceData.evidence && (
                        <div className="question-evidence-callout animate-fade-in">
                          <div className="evidence-header">
                            <span className="evidence-badge">
                              <Quote size={11} /> Evidência do Estudo {evidenceData.page_ref ? `(Pág. ${evidenceData.page_ref})` : ''}
                            </span>
                            <span className="evidence-source-tag">
                              {evidenceData.source_kind === 'pdf' ? '📄 Texto do PDF' : '📝 Resumo/Metadados'}
                            </span>
                          </div>
                          <p className="evidence-quote">"{evidenceData.evidence}"</p>
                        </div>
                      )}
                    </Card>
                  )
                })
              )}

              {/* Synthesis Bridge Banner */}
              <Card surface="primaria" className="synthesis-bridge-card">
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
              </Card>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <Card surface="secundaria" className="extraction-empty-state-card animate-fade-in">
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
        </Card>
      )}

      {/* Link direto de PDF */}
      <Dialog open={isUrlModalOpen} onOpenChange={setIsUrlModalOpen}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>
              <Link size={15} className="icon-accent" aria-hidden="true" /> Link Direto do PDF
            </DialogTitle>
            <DialogDescription>
              Cole a URL direta do arquivo PDF (ex: repositório institucional, SciELO, ResearchGate) para download
              automático:
            </DialogDescription>
          </DialogHeader>
          <input
            type="url"
            className="input-text-full"
            placeholder="https://exemplo.org/artigo.pdf"
            value={customDownloadUrl}
            onChange={(e) => setCustomDownloadUrl(e.target.value)}
            autoFocus
          />
          <DialogFooter>
            <Button variant="secondary" size="md" onClick={() => setIsUrlModalOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={handleSaveCustomDownloadUrl}
              loading={downloadingPdf}
              disabled={!customDownloadUrl.trim()}
              leftIcon={<Download size={14} />}
            >
              {downloadingPdf ? 'Baixando…' : 'Salvar & Baixar PDF'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── BARRA FIXA INFERIOR DE AÇÕES MOBILE ── */}
      {selectedPaper && (
        <div className="extraction-mobile-sticky-dock animate-fade-in">
          <Button
            variant="secondary"
            size="md"
            className="mobile-extract-btn"
            onClick={extractingAI ? handleCancelExtraction : handleExtractWithAI}
            disabled={questions.length === 0}
            leftIcon={extractingAI ? <StopCircle size={16} /> : <Sparkles size={16} />}
          >
            {extractingAI ? 'Parar Extração' : 'Preencher com Assistência'}
          </Button>
          <Button
            variant="primary"
            size="md"
            className="mobile-save-btn"
            onClick={handleSaveAnswers}
            loading={saving}
            leftIcon={<Save size={16} />}
          >
            {saving ? 'Salvando…' : 'Salvar Respostas'}
          </Button>
        </div>
      )}
    </div>
  )
}
