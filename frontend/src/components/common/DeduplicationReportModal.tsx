/**
 * RSAC V2 — Deduplication Report Modal
 * Exibe o Relatório de Deduplicação e Fusão de Fontes (3_relatorio_deduplicacao.txt)
 * em estrita paridade com o pop-up e recursos do RSAC V1.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileDown,
  Copy,
  Check,
  X,
  Layers,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import type { DeduplicationReport } from '@/types/api'
import './DeduplicationReportModal.css'

interface DeduplicationReportModalProps {
  report: DeduplicationReport | null
  isOpen: boolean
  onClose: () => void
  projectId?: string
}

export function DeduplicationReportModal({
  report,
  isOpen,
  onClose,
  projectId,
}: DeduplicationReportModalProps): JSX.Element | null {
  const navigate = useNavigate()
  const [copied, setCopied] = useState(false)

  if (!isOpen || !report) return null

  const handleCopyText = async () => {
    try {
      await navigator.clipboard.writeText(report.report_text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback
    }
  }

  const handleDownloadTxt = () => {
    const blob = new Blob([report.report_text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '3_relatorio_deduplicacao.txt'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleGoToScreening = () => {
    onClose()
    if (projectId) {
      navigate(`/projects/${projectId}/screening`)
    }
  }

  return (
    <div className="dedup-modal-backdrop" onClick={onClose}>
      <div className="dedup-modal-window" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="dedup-modal-header">
          <div className="dedup-modal-title-area">
            <Layers size={22} className="icon-accent" />
            <div>
              <h2>Relatório de Deduplicação e Fusão de Fontes</h2>
              <p className="dedup-modal-subtitle">
                Consolidação dos 3 passes algorítmicos (DOI ➔ Título Normalizado ➔ Similaridade Fuzzy)
              </p>
            </div>
          </div>
          <button className="dedup-modal-close-btn" onClick={onClose} title="Fechar">
            <X size={20} />
          </button>
        </div>

        {/* Top Summary Bar */}
        <div className="dedup-stats-bar">
          <div className="dedup-stat-chip raw">
            <span className="stat-label">Total Lidos</span>
            <span className="stat-val">{report.total_raw}</span>
          </div>
          <div className="dedup-stat-chip unique">
            <span className="stat-label">Trabalhos Únicos</span>
            <span className="stat-val">{report.total_unique}</span>
          </div>
          <div className="dedup-stat-chip duplicate">
            <span className="stat-label">Duplicatas Excluídas</span>
            <span className="stat-val">{report.total_duplicates}</span>
          </div>
          <div className="dedup-stat-chip rate">
            <span className="stat-label">Taxa de Duplicação</span>
            <span className="stat-val">{report.dup_rate}%</span>
          </div>
        </div>

        {/* Body Text Area */}
        <div className="dedup-modal-body">
          <textarea
            className="dedup-report-textarea"
            value={report.report_text}
            readOnly
            spellCheck={false}
          />
        </div>

        {/* Footer Actions */}
        <div className="dedup-modal-footer">
          <div className="dedup-footer-left">
            <button className="btn-secondary" onClick={handleDownloadTxt}>
              <FileDown size={16} /> Salvar Relatório (.txt)
            </button>
            <button className="btn-secondary" onClick={handleCopyText}>
              {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
              {copied ? 'Copiado!' : 'Copiar Texto'}
            </button>
          </div>

          <div className="dedup-footer-right">
            <button className="btn-secondary" onClick={onClose}>
              Fechar
            </button>
            {projectId && (
              <button className="btn-primary" onClick={handleGoToScreening}>
                Iniciar Triagem <ArrowRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
