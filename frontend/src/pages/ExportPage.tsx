/**
 * RSAC V2 — Export Page (Central de Exportação & Relatórios PRISMA)
 *
 * Layout Metodológico e Ergonômico Padronizado:
 * 1. Barra Superior de Métricas PRISMA: Identificados, Duplicatas, Triados e Incluídos.
 * 2. Painel Bipartido Lado a Lado (Workbench Split Grid):
 *    - Coluna da Esquerda: Pacotes acadêmicos de exportação (.xlsx, .bib, .md, auditoria).
 *    - Coluna da Direita: Diagrama de Fluxo PRISMA 2020 interativo em tempo real.
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Download,
  FileSpreadsheet,
  BookMarked,
  Layers,
  ArrowDown,
  ArrowRight,
  CheckCircle2,
  FileText,
  Database,
  Filter,
  ShieldCheck,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import { PageHeader, Button, LoadingState } from '@/components/ui'
import type { PrismaFlowData } from '@/types/api'
import './ExportPage.css'

export function ExportPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject } = useSettingsStore()
  const registerRibbonActions = useRibbonStore((s) => s.registerActions)
  const unregisterRibbonActions = useRibbonStore((s) => s.unregisterActions)

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

      const data = await api.getPrismaFlow(projectId)
      setPrismaData(data)
    } catch (err) {
      console.error('Erro ao carregar dados do PRISMA:', err)
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

  useEffect(() => {
    registerRibbonActions({
      exportExcel: handleDownloadExcel,
      exportBibtex: handleDownloadBibtex,
    })
    return () => {
      unregisterRibbonActions(['exportExcel', 'exportBibtex'])
    }
  }, [registerRibbonActions, unregisterRibbonActions, id])

  return (
    <div className="export-page animate-fade-in">
      <PageHeader
        title="Central de Exportação & Fluxograma PRISMA"
        onBack={() => navigate('/projects')}
        subtitle={
          <span>
            Projeto: <strong>{activeProject?.title}</strong> — Relatórios acadêmicos, planilhas consolidadas e
            manuscrito
          </span>
        }
        primaryAction={
          /* Navegação lateral, não comando de exportação: os downloads em si
             vivem no ribbon (`exportExcel`, `exportBibtex`) e nos cartões
             abaixo. */
          <Button
            variant="secondary"
            size="md"
            onClick={() => navigate(`/projects/${id}/protocol`)}
            leftIcon={<FileText size={14} />}
          >
            Ver Protocolo
          </Button>
        }
      />

      {/* ═══════════════════════════════════════════════════════════════════
          BARRA SUPERIOR DE MÉTRICAS PRISMA
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="export-queue-container">
        <div className="export-top-controls-bar">
          <div className="export-metrics-group">
            <span className="queue-status-chip">
              <Database size={13} className="icon-accent" />
              Identificados: <strong>{prismaData?.identification.total_records_identified ?? 0}</strong>
            </span>
            <span className="queue-status-chip">
              <Layers size={13} className="icon-accent" />
              Duplicatas Removidas: <strong>{prismaData?.identification.duplicates_removed ?? 0}</strong>
            </span>
            <span className="queue-status-chip">
              <Filter size={13} className="icon-accent" />
              Triados (Fase 1): <strong>{prismaData?.screening.records_screened ?? 0}</strong>
            </span>
            <span className="queue-status-chip inc">
              <CheckCircle2 size={13} />
              Incluídos na Síntese: <strong>{prismaData?.included.studies_included_in_synthesis ?? 0}</strong>
            </span>
          </div>

          <div className="export-top-actions">
            <button
              type="button"
              className="btn-secondary small"
              onClick={() => navigate(`/projects/${id}/extraction`)}
            >
              <FileText size={13} /> Ver Extração <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          GRID BIPARTIDO LADO A LADO (WORKBENCH GRID)
          Coluna 1: Pacotes de Exportação | Coluna 2: Fluxograma PRISMA 2020
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="export-workbench-grid">
        {/* ── COLUNA DA ESQUERDA: PACOTES ACADÊMICOS ─────────────────── */}
        <div className="export-packages-pane">
          <div className="pane-header-title">
            <Download size={16} className="icon-accent" />
            <h3>Pacotes & Relatórios Acadêmicos</h3>
          </div>

          <div className="pane-scroll-body">
            {/* Card Excel */}
            <div className="export-package-card" onClick={handleDownloadExcel}>
              <div className="package-card-icon excel">
                <FileSpreadsheet size={24} />
              </div>
              <div className="package-card-content">
                <h4>Planilha Excel Completa (.xlsx)</h4>
                <p>
                  Exporta 4 abas estruturadas: Artigos Incluídos, Matriz de Respostas Q1..Qn, Artigos Excluídos e Métricas PRISMA.
                </p>
                <div className="package-card-footer">
                  <span className="btn-package-action">
                    <Download size={13} /> Baixar Planilha (.xlsx)
                  </span>
                </div>
              </div>
            </div>

            {/* Card BibTeX */}
            <div className="export-package-card" onClick={handleDownloadBibtex}>
              <div className="package-card-icon bibtex">
                <BookMarked size={24} />
              </div>
              <div className="package-card-content">
                <h4>Citações BibTeX (.bib)</h4>
                <p>
                  Arquivo padronizado para importação direta no Zotero, Mendeley ou compilação de bibliografia em LaTeX / Overleaf.
                </p>
                <div className="package-card-footer">
                  <span className="btn-package-action">
                    <Download size={13} /> Baixar Referências (.bib)
                  </span>
                </div>
              </div>
            </div>

            {/* Card Manuscrito */}
            <div
              className="export-package-card"
              onClick={() => navigate(`/projects/${id}/protocol`)}
            >
              <div className="package-card-icon doc">
                <FileText size={24} />
              </div>
              <div className="package-card-content">
                <h4>Manuscrito & Protocolo em Markdown (.md)</h4>
                <p>
                  Texto completo estruturado com as seções A Priori e A Posteriori (Introdução, Métodos, Síntese e Discussão).
                </p>
                <div className="package-card-footer">
                  <span className="btn-package-action">
                    <FileText size={13} /> Abrir no Estúdio de Redação
                  </span>
                </div>
              </div>
            </div>

            {/* Banner de Auditoria e Reprodutibilidade */}
            <div className="export-audit-card">
              <div className="audit-content">
                <ShieldCheck size={20} className="icon-accent" />
                <div>
                  <strong>Reprodutibilidade & Rastreabilidade Metodológica</strong>
                  <p>
                    Todos os registros exportados mantêm ancoragem com os descritores, bases de origem, datas de coleta e decisões de triagem.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── COLUNA DA DIREITA: FLUXOGRAMA PRISMA 2020 ───────────────── */}
        <div className="export-prisma-pane">
          <div className="pane-header-title">
            <Layers size={16} className="icon-accent" />
            <h3>Diagrama de Fluxo da Seleção de Estudos</h3>
          </div>

          <div className="pane-scroll-body">
            {loading || !prismaData ? (
              <LoadingState label="Calculando métricas do PRISMA…" />
            ) : (
              <div className="prisma-flow-chart-compact">
                {/* 1. Identificação */}
                <div className="prisma-compact-stage">
                  <div className="stage-compact-tag">1. Identificação</div>
                  <div className="prisma-box-compact highlight">
                    <h5>Registros identificados nas bases de dados</h5>
                    <div className="prisma-count-big">
                      {prismaData.identification.total_records_identified} registros
                    </div>
                    <div className="prisma-subsources-list">
                      {Object.entries(prismaData.identification.sources_breakdown || {}).map(([s, count]) => (
                        <span key={s} className="subsource-pill">
                          {s}: {String(count)}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flow-down-arrow">
                    <ArrowDown size={16} />
                  </div>

                  <div className="prisma-box-compact secondary">
                    <h5>Registros duplicados removidos antes da triagem</h5>
                    <div className="prisma-count-danger">
                      {prismaData.identification.duplicates_removed} duplicatas
                    </div>
                  </div>
                </div>

                <div className="flow-down-arrow stage">
                  <ArrowDown size={18} />
                </div>

                {/* 2. Triagem */}
                <div className="prisma-compact-stage">
                  <div className="stage-compact-tag">2. Triagem de Elegibilidade</div>
                  <div className="prisma-compact-row">
                    <div className="prisma-box-compact highlight">
                      <h5>Registros únicos triados</h5>
                      <div className="prisma-count-big">
                        {prismaData.screening.records_screened} artigos
                      </div>
                    </div>

                    <div className="prisma-box-compact excluded">
                      <h5>Registros excluídos</h5>
                      <div className="prisma-count-danger">
                        {prismaData.screening.records_excluded} excluídos
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flow-down-arrow stage">
                  <ArrowDown size={18} />
                </div>

                {/* 3. Inclusão na Síntese */}
                <div className="prisma-compact-stage">
                  <div className="stage-compact-tag">3. Inclusão na Síntese (Extração)</div>
                  <div className="prisma-box-compact included">
                    <h5>Estudos incluídos na síntese qualitativa e quantitativa</h5>
                    <div className="prisma-count-success">
                      {prismaData.included.studies_included_in_synthesis} estudos incluídos
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
