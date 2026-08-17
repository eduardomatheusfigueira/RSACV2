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
import { Dialog, DialogContent, DialogTitle, DialogClose } from '@/components/ui'
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

  if (!report) return null

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

  /* A janela mantém o próprio layout, mas quem a monta agora é o Dialog do
     Radix: foco preso enquanto aberta, Escape fecha, foco volta ao botão que
     abriu. Nada disso existia na versão desenhada à mão. */
  return (
    <Dialog open={isOpen} onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        className="dedup-modal-window"
        showCloseButton={false}
        aria-describedby="dedup-modal-subtitle"
      >
        {/* Header */}
        <div className="dedup-modal-header">
          <div className="dedup-modal-title-area">
            <Layers size={22} className="icon-accent" aria-hidden="true" />
            <div>
              <DialogTitle asChild>
                <h2>Relatório de Deduplicação e Fusão de Fontes</h2>
              </DialogTitle>
              <p className="dedup-modal-subtitle" id="dedup-modal-subtitle">
                Consolidação dos 3 passes algorítmicos (DOI ➔ Título Normalizado ➔ Similaridade Fuzzy)
              </p>
            </div>
          </div>
          <DialogClose className="dedup-modal-close-btn" aria-label="Fechar" title="Fechar">
            <X size={20} aria-hidden="true" />
          </DialogClose>
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
      </DialogContent>
    </Dialog>
  )
}
