/**
 * RSAC V2 — Extraction Page (Triagem 2 / Extração de Dados)
 * Extração de dados estruturados a partir do texto completo (PDF) e resumo
 * dos estudos incluídos, com preenchimento manual e assistência de IA.
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  FileText,
  Sparkles,
  Save,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  Download,
  Upload,
  FileCheck,
  FileX,
  Search,
  ExternalLink,
  BookOpen,
  Calendar,
  User,
  RefreshCw,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import type { ExtractionResponse, Paper, Protocol } from '@/types/api'
import './ExtractionPage.css'

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
  const [hasPdf, setHasPdf] = useState(false)
  const [pdfPath, setPdfPath] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [extractingAI, setExtractingAI] = useState(false)
  const [downloadingPdf, setDownloadingPdf] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    if (id) {
      loadInitialData(id)
    }
  }, [id])

  useEffect(() => {
    if (id && selectedPaper) {
      loadPaperExtraction(id, selectedPaper.id)
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
        api.listPapers(projectId, { decision: 'Incluído', page_size: 100 }),
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
      extRes.answers.forEach((a) => {
        ansMap[a.question_id] = a.answer
      })
      setAnswers(ansMap)
    } catch (err) {
      console.error('Erro ao carregar respostas de extração:', err)
    }
  }

  const handleAnswerChange = (questionId: string, value: string) => {
    setAnswers({ ...answers, [questionId]: value })
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
      res.answers?.forEach((a: any) => {
        nextAns[a.question_id] = a.answer
      })
      setAnswers(nextAns)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err: any) {
      console.error('Erro ao extrair com IA:', err)
      setErrorMessage(err.message || 'Falha ao processar extração com IA.')
    } finally {
      setExtractingAI(false)
    }
  }

  const handleDownloadPDF = async () => {
    if (!id || !selectedPaper) return
    try {
      setDownloadingPdf(true)
      setErrorMessage('')
      const res = await api.downloadPaperPDF(id, selectedPaper.id)
      setHasPdf(true)
      setPdfPath(res.pdf_path)
    } catch (err: any) {
      console.error('Erro ao baixar PDF:', err)
      setErrorMessage(err.message || 'Não foi possível baixar o PDF automaticamente da URL.')
    } finally {
      setDownloadingPdf(false)
    }
  }

  const questions = protocol?.extraction_questions || []

  return (
    <div className="extraction-page animate-fade-in">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <button className="btn-back" onClick={() => navigate('/projects')}>
            <ArrowLeft size={16} /> Voltar para Projetos
          </button>
          <h1 className="page-title">Extração de Dados (Triagem 2)</h1>
          <p className="page-subtitle">
            Projeto: <strong>{activeProject?.title}</strong> — Extração estruturada a partir do texto completo dos estudos incluídos
          </p>
        </div>
        <div className="header-actions">
          {saveSuccess && (
            <span className="save-indicator success">
              <CheckCircle2 size={16} /> Respostas Salvas!
            </span>
          )}
          {aiEnabled && (
            <button
              type="button"
              className="btn-secondary"
              onClick={handleExtractWithAI}
              disabled={extractingAI || !selectedPaper || questions.length === 0}
              title="Extrai automaticamente as respostas do PDF/Resumo usando IA"
            >
              {extractingAI ? (
                <>
                  <RefreshCw size={16} className="animate-spin" /> Extraindo com IA...
                </>
              ) : (
                <>
                  <Sparkles size={16} className="icon-accent" /> Extrair com IA
                </>
              )}
            </button>
          )}
          <button className="btn-primary" onClick={handleSaveAnswers} disabled={saving || !selectedPaper}>
            <Save size={18} />
            {saving ? 'Salvando...' : 'Salvar Respostas'}
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="extraction-error-banner animate-fade-in">
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Split Layout: Left Included Papers List & PDF, Right Questionnaire */}
      <div className="extraction-layout">
        {/* Left Column: Included Papers List */}
        <div className="extraction-list-col">
          <div className="list-col-header">
            <h3>Estudos Incluídos ({papers.length})</h3>
          </div>

          {loading ? (
            <div className="loading-state-small">
              <div className="loading-spinner animate-spin" />
              <span>Carregando estudos incluídos...</span>
            </div>
          ) : papers.length === 0 ? (
            <div className="empty-papers-box">
              <BookOpen size={32} />
              <p>Nenhum estudo com status "Incluído" ainda.</p>
              <button className="btn-secondary small" onClick={() => navigate(`/projects/${id}/screening`)}>
                Ir para Triagem 1
              </button>
            </div>
          ) : (
            <div className="papers-scroll-list">
              {papers.map((paper) => {
                const isSelected = selectedPaper?.id === paper.id
                return (
                  <div
                    key={paper.id}
                    className={`paper-list-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedPaper(paper)}
                  >
                    <div className="item-meta">
                      <span className="badge-inc">Incluído</span>
                      {paper.year && <span className="item-year">{paper.year}</span>}
                    </div>
                    <h4 className="item-title">{paper.title}</h4>
                    {paper.authors && <p className="item-authors">{paper.authors}</p>}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Column: Questionnaire & Document Context */}
        <div className="extraction-detail-col">
          {selectedPaper ? (
            <div className="extraction-content animate-fade-in">
              {/* Paper Top Info Bar */}
              <div className="paper-info-bar">
                <div className="info-main">
                  <h2>{selectedPaper.title}</h2>
                  <div className="info-meta">
                    {selectedPaper.authors && (
                      <span className="meta-tag">
                        <User size={13} /> {selectedPaper.authors}
                      </span>
                    )}
                    {selectedPaper.year && (
                      <span className="meta-tag">
                        <Calendar size={13} /> {selectedPaper.year}
                      </span>
                    )}
                    {selectedPaper.doi && (
                      <a
                        href={`https://doi.org/${selectedPaper.doi}`}
                        target="_blank"
                        rel="noreferrer"
                        className="meta-tag link"
                      >
                        <ExternalLink size={13} /> DOI: {selectedPaper.doi}
                      </a>
                    )}
                  </div>
                </div>

                {/* PDF Status Badge & Actions */}
                <div className="pdf-actions-box">
                  {hasPdf ? (
                    <div className="badge-pdf success">
                      <FileCheck size={16} /> PDF Local Disponível
                    </div>
                  ) : (
                    <div className="pdf-missing-actions">
                      <div className="badge-pdf missing">
                        <FileX size={16} /> PDF Não Baixado
                      </div>
                      {selectedPaper.download_url && (
                        <button
                          type="button"
                          className="btn-secondary small"
                          onClick={handleDownloadPDF}
                          disabled={downloadingPdf}
                        >
                          {downloadingPdf ? (
                            <>
                              <RefreshCw size={13} className="animate-spin" /> Baixando...
                            </>
                          ) : (
                            <>
                              <Download size={13} /> Baixar PDF
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Questions Questionnaire Form */}
              <div className="questionnaire-container">
                <div className="questionnaire-header">
                  <FileText size={18} className="icon-accent" />
                  <h3>Formulário de Extração de Dados do Protocolo ({questions.length} perguntas)</h3>
                </div>

                {questions.length === 0 ? (
                  <div className="no-questions-box">
                    <AlertCircle size={24} />
                    <p>
                      Nenhuma pergunta de extração cadastrada no protocolo.{' '}
                      <a onClick={() => navigate(`/projects/${id}/protocol`)}>
                        Configurar Perguntas no Protocolo
                      </a>.
                    </p>
                  </div>
                ) : (
                  <div className="questions-form-list">
                    {questions.map((q, idx) => (
                      <div key={q.id || idx} className="question-field-card">
                        <div className="question-field-header">
                          <span className="q-badge">Q{idx + 1}</span>
                          <span className="q-title">{q.text}</span>
                        </div>
                        <textarea
                          rows={3}
                          className="q-textarea"
                          placeholder="Digite ou gere com IA a resposta extraída deste artigo..."
                          value={answers[q.id || ''] || ''}
                          onChange={(e) => handleAnswerChange(q.id || '', e.target.value)}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="no-selection-box">
              <BookOpen size={48} strokeWidth={1} />
              <h3>Nenhum estudo selecionado</h3>
              <p>Selecione um artigo incluído na lista para preencher o formulário de extração.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
