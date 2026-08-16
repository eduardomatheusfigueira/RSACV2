/**
 * RSAC V2 — Export Page (Exportação de Dados & Fluxograma PRISMA 2020)
 * Visualização interativa do fluxo metodológico PRISMA 2020
 * e exportação de planilhas Excel (.xlsx) e citações BibTeX (.bib).
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  FileDown,
  Download,
  FileSpreadsheet,
  BookMarked,
  ArrowLeft,
  ArrowDown,
  Layers,
  CheckCircle2,
  XCircle,
  Database,
  Search,
  ExternalLink,
  Sparkles,
} from 'lucide-react'
import { api, type PrismaFlowData } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import './ExportPage.css'

export function ExportPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject } = useSettingsStore()

  const [prismaData, setPrismaData] = useState<PrismaFlowData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (id) {
      loadData(id)
    }
  }, [id])

  const loadData = async (projectId: string) => {
    try {
      setLoading(true)
      if (!activeProject || activeProject.id !== projectId) {
        const proj = await api.getProject(projectId)
        setActiveProject(proj)
      }

      const pData = await api.getPrismaFlow(projectId)
      setPrismaData(pData)
    } catch (err) {
      console.error('Erro ao carregar dados PRISMA:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadExcel = () => {
    if (!id) return
    window.open(api.getExcelExportUrl(id), '_blank')
  }

  const handleDownloadBibtex = () => {
    if (!id) return
    window.open(api.getBibtexExportUrl(id), '_blank')
  }

  return (
    <div className="export-page animate-fade-in">
      {/* Top Header */}
      <div className="page-header">
        <div>
          <button className="btn-back" onClick={() => navigate('/projects')}>
            <ArrowLeft size={16} /> Voltar para Projetos
          </button>
          <h1 className="page-title">Exportação & Fluxograma PRISMA 2020</h1>
          <p className="page-subtitle">
            Projeto: <strong>{activeProject?.title}</strong> — Relatórios acadêmicos e síntese do fluxo metodológico
          </p>
        </div>
      </div>

      {/* Export Action Cards */}
      <div className="export-actions-grid">
        <div className="export-card" onClick={handleDownloadExcel}>
          <div className="export-card-icon excel">
            <FileSpreadsheet size={28} />
          </div>
          <div className="export-card-content">
            <h3>Planilha Excel (.xlsx)</h3>
            <p>
              Exporta 4 abas estruturadas: Artigos Incluídos, Matriz de Extração de Dados, Artigos Excluídos e Métricas PRISMA.
            </p>
            <span className="export-btn-link">
              <Download size={15} /> Baixar Relatório Completo (.xlsx)
            </span>
          </div>
        </div>

        <div className="export-card" onClick={handleDownloadBibtex}>
          <div className="export-card-icon bibtex">
            <BookMarked size={28} />
          </div>
          <div className="export-card-content">
            <h3>Citações BibTeX (.bib)</h3>
            <p>
              Arquivo padronizado para importação direta no Zotero, Mendeley ou compilação de bibliografia em LaTeX / Overleaf.
            </p>
            <span className="export-btn-link">
              <Download size={15} /> Baixar Referências (.bib)
            </span>
          </div>
        </div>
      </div>

      {/* PRISMA 2020 Interactive Flow Diagram */}
      <div className="prisma-section">
        <div className="section-title-row">
          <Layers size={20} className="icon-accent" />
          <h2>Diagrama de Fluxo PRISMA 2020</h2>
        </div>
        <p className="section-desc">
          Representação visual padronizada do fluxo de inclusão e exclusão de artigos da revisão sistemática.
        </p>

        {loading || !prismaData ? (
          <div className="loading-state">
            <div className="loading-spinner animate-spin" />
            <span>Calculando métricas PRISMA...</span>
          </div>
        ) : (
          <div className="prisma-flow-chart">
            {/* Phase 1: Identification */}
            <div className="prisma-stage">
              <div className="stage-tag">1. Identificação</div>
              <div className="prisma-box highlight">
                <h4>Registros identificados nas buscas de bases de dados</h4>
                <div className="prisma-number">
                  {prismaData.identification.total_records_identified} registros
                </div>
                <div className="prisma-subsources">
                  {Object.entries(prismaData.identification.sources_breakdown).map(([s, count]) => (
                    <span key={s} className="subsource-badge">
                      {s}: {count}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flow-arrow">
                <ArrowDown size={20} />
              </div>

              <div className="prisma-box secondary">
                <h4>Registros duplicados removidos antes da triagem</h4>
                <div className="prisma-number duplicate">
                  {prismaData.identification.duplicates_removed} duplicatas
                </div>
              </div>
            </div>

            <div className="flow-arrow stage-divider">
              <ArrowDown size={24} />
            </div>

            {/* Phase 2: Screening */}
            <div className="prisma-stage">
              <div className="stage-tag">2. Triagem 1 (Título e Resumo)</div>
              <div className="prisma-row-split">
                <div className="prisma-box highlight">
                  <h4>Registros únicos triados</h4>
                  <div className="prisma-number">
                    {prismaData.screening.records_screened} artigos
                  </div>
                </div>

                <div className="prisma-box excluded">
                  <h4>Registros excluídos na Triagem 1</h4>
                  <div className="prisma-number text-error">
                    {prismaData.screening.records_excluded} excluídos
                  </div>
                </div>
              </div>
            </div>

            <div className="flow-arrow stage-divider">
              <ArrowDown size={24} />
            </div>

            {/* Phase 3: Included */}
            <div className="prisma-stage">
              <div className="stage-tag">3. Incluídos na Síntese</div>
              <div className="prisma-box success">
                <h4>Estudos elegíveis incluídos na revisão sistemática</h4>
                <div className="prisma-number text-success">
                  {prismaData.included.studies_included_in_synthesis} estudos incluídos
                </div>
                <p className="prisma-hint">
                  Dados estruturados extraídos na Triagem 2 e prontos para síntese qualitativa e quantitativa.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
