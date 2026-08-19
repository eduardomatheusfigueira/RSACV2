/**
 * RSAC V2 — Harvest Page (Coleta Multibase de Artigos)
 *
 * Recursos Integrados e Padronizados:
 * 1. Barra Superior de Métricas: Bases ativas, descritores, contadores (novos vs. duplicados).
 * 2. Painel Esquerdo: Configuração de bases (BDTD, SciELO, Scopus, PubMed, OpenAlex), descritores e histórico de execuções.
 * 3. Painel Direito: Stream em Tempo Real de Trabalhos Coletados (com indicação se é Novo ou Duplicata),
 *    tabela de progresso concorrente por base, alternador para Terminal de Logs e avanço para Triagem 1.
 */

import { useState, useEffect, useRef, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as Tabs from '@radix-ui/react-tabs'
import {
  Play,
  StopCircle,
  Database,
  Search,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Layers,
  Key,
  RefreshCw,
  BookOpen,
  Terminal,
  FileCheck,
  FileX,
  History,
  Radio,
  Filter,
  Check,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import { useLogStore } from '@/stores/useLogStore'
import { DeduplicationReportModal } from '@/components/common/DeduplicationReportModal'
import { PageHeader, Button, Card, toast } from '@/components/ui'
import type {
  HarvestSourceInfo,
  HarvestRun,
  Protocol,
  DeduplicationReport,
  Paper,
} from '@/types/api'
import './HarvestPage.css'

interface LiveFeedItem {
  id: string
  title: string
  source: string
  isNew: boolean
  authors?: string | null
  year?: string | number | null
}

export function HarvestPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject } = useSettingsStore()
  const { entries } = useLogStore()

  const [protocol, setProtocol] = useState<Protocol | null>(null)
  const [sources, setSources] = useState<HarvestSourceInfo[]>([])
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [maxRecords, setMaxRecords] = useState<number>(0) // 0 = Ilimitado
  const [isHarvesting, setIsHarvesting] = useState(false)
  const [isDeduplicating, setIsDeduplicating] = useState(false)
  const [progress, setProgress] = useState<Record<string, { status: string; total_found: number }>>({})
  const [totalFound, setTotalFound] = useState(0)
  const [totalNew, setTotalNew] = useState(0)
  const [totalDuplicate, setTotalDuplicate] = useState(0)

  // Live feed stream and collected papers
  const [liveFeed, setLiveFeed] = useState<LiveFeedItem[]>([])
  const [collectedPapers, setCollectedPapers] = useState<Paper[]>([])
  const [harvestRuns, setHarvestRuns] = useState<HarvestRun[]>([])
  const [feedTab, setFeedTab] = useState<'stream' | 'terminal'>('stream')
  const [feedFilter, setFeedFilter] = useState<'all' | 'new' | 'dup'>('all')
  const [mobileTab, setMobileTab] = useState<'sources' | 'monitor'>('sources')

  const [dedupReport, setDedupReport] = useState<DeduplicationReport | null>(null)
  const [isDedupModalOpen, setIsDedupModalOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  const logConsoleRef = useRef<HTMLDivElement | null>(null)
  const feedScrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (id) {
      loadInitialData(id)
    }
  }, [id])

  // WebSocket for real-time paper harvest events
  useEffect(() => {
    if (!id) return
    const wsUrl = api.getWebSocketUrl(id)
    let ws: WebSocket | null = null

    try {
      ws = new WebSocket(wsUrl)

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'paper_harvested') {
            if (msg.recent_items && Array.isArray(msg.recent_items)) {
              setLiveFeed((prev) => {
                const newItems: LiveFeedItem[] = msg.recent_items.map((it: any) => ({
                  id: it.paper_id || String(Math.random()),
                  title: it.title || 'Sem título',
                  source: msg.source || 'Base',
                  isNew: Boolean(it.is_new),
                }))
                // Keep top 120 most recent
                return [...newItems, ...prev].slice(0, 120)
              })
            }
            if (msg.total_found !== undefined) setTotalFound(msg.total_found)
            if (msg.total_new !== undefined) setTotalNew(msg.total_new)
            if (msg.total_duplicate !== undefined) setTotalDuplicate(msg.total_duplicate)
          } else if (msg.type === 'harvest_source_completed') {
            // Refresh runs
            api.listHarvestRuns(id).then((res) => setHarvestRuns(res.items)).catch(() => {})
          }
        } catch (err) {
          console.error('Erro ao processar mensagem do WebSocket:', err)
        }
      }
    } catch (e) {
      console.warn('WebSocket indisponível, utilizando modo polling.', e)
    }

    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [id])

  useEffect(() => {
    if (logConsoleRef.current && feedTab === 'terminal') {
      logConsoleRef.current.scrollTop = logConsoleRef.current.scrollHeight
    }
  }, [entries, feedTab])

  const loadInitialData = async (projectId: string) => {
    try {
      setLoading(true)
      if (!activeProject || activeProject.id !== projectId) {
        const proj = await api.getProject(projectId)
        setActiveProject(proj)
      }

      const [protoRes, sourcesRes, statsRes, runsRes, papersRes] = await Promise.all([
        api.getProtocol(projectId),
        api.getAvailableSources(projectId),
        api.getProjectStats(projectId),
        api.listHarvestRuns(projectId),
        api.listPapers(projectId, { page_size: 60 }),
      ])

      setProtocol(protoRes)
      const srcList = sourcesRes.sources || []
      setSources(srcList)
      setSelectedSources(srcList.filter((s: HarvestSourceInfo) => s.enabled).map((s: HarvestSourceInfo) => s.id))
      setTotalFound(statsRes.total_papers || 0)
      setTotalNew(statsRes.total_papers || 0)
      setHarvestRuns(runsRes.items || [])
      setCollectedPapers(papersRes.items || [])

      // Initialize live feed from already collected papers
      if (papersRes.items && papersRes.items.length > 0) {
        const initialFeed: LiveFeedItem[] = papersRes.items.map((p) => ({
          id: p.id,
          title: p.title,
          source: (p.sources && p.sources.length > 0) ? p.sources.join(', ') : 'Coleta',
          isNew: Boolean(p.sources && p.sources.length === 1),
          authors: p.authors,
          year: p.year,
        }))
        setLiveFeed(initialFeed)
      }
    } catch (err) {
      console.error('Erro ao carregar dados da coleta:', err)
    } finally {
      setLoading(false)
    }
  }

  const toggleSource = (source: HarvestSourceInfo) => {
    if (!source.enabled) return
    setSelectedSources((prev) =>
      prev.includes(source.id)
        ? prev.filter((id) => id !== source.id)
        : [...prev, source.id]
    )
  }

  const handleStartHarvest = async () => {
    if (!id || selectedSources.length === 0) return

    try {
      setIsHarvesting(true)
      const initialProgress: Record<string, { status: string; total_found: number }> = {}
      selectedSources.forEach((srcId) => {
        initialProgress[srcId] = {
          status: 'running',
          total_found: 0,
        }
      })
      setProgress(initialProgress)

      await api.startHarvest(id, {
        sources: selectedSources,
        max_records_per_descriptor: maxRecords > 0 ? maxRecords : null,
      })

      // Polling de status da coleta
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await api.getHarvestStatus(id)
          setProgress(statusRes.progress || {})

          if (statusRes.is_complete) {
            clearInterval(pollInterval)
            setIsHarvesting(false)
            setTotalFound(statusRes.total_found || 0)
            setTotalNew(statusRes.total_new || statusRes.total_found || 0)
            setTotalDuplicate(statusRes.total_duplicate || 0)

            // Reload runs and papers
            const [runsRes, papersRes] = await Promise.all([
              api.listHarvestRuns(id),
              api.listPapers(id, { page_size: 60 }),
            ])
            setHarvestRuns(runsRes.items || [])
            setCollectedPapers(papersRes.items || [])

            /* Uma coleta multibase leva minutos; a pessoa sai da tela. O aviso
               é anunciado por leitor de tela e alcança quem já mudou de aba. */
            toast.success('Coleta multibase concluída', {
              description: `${statusRes.total_new || statusRes.total_found || 0} trabalhos novos · ${statusRes.total_duplicate || 0} duplicatas unificadas.`,
            })
          }
        } catch (err) {
          console.error('Erro no polling de status:', err)
          clearInterval(pollInterval)
          setIsHarvesting(false)
          toast.error('A coleta foi interrompida', {
            description: 'Falha ao consultar o andamento. O que já foi recuperado está no acervo.',
          })
        }
      }, 1500)
    } catch (err: any) {
      console.error('Erro ao iniciar coleta:', err)
      setIsHarvesting(false)
      toast.error('Não foi possível iniciar a coleta', {
        description: err?.message || 'Falha na comunicação com o backend.',
      })
    }
  }

  const handleCancelHarvest = async () => {
    if (!id) return
    try {
      await api.cancelHarvest(id)
      setIsHarvesting(false)
    } catch (err) {
      console.error('Erro ao cancelar coleta:', err)
    }
  }

  const handleDeduplicate = async () => {
    if (!id) return
    try {
      setIsDeduplicating(true)
      const res = await api.deduplicateProject(id)
      setDedupReport(res.data)
      setIsDedupModalOpen(true)
    } catch (err) {
      console.error('Erro ao executar deduplicação:', err)
    } finally {
      setIsDeduplicating(false)
    }
  }

  // ── Sincronização de Ações com o Ribbon Bar ─────────────────────────
  const registerRibbonActions = useRibbonStore((s) => s.registerActions)
  const unregisterRibbonActions = useRibbonStore((s) => s.unregisterActions)

  useEffect(() => {
    registerRibbonActions({
      startHarvest: handleStartHarvest,
      stopHarvest: handleCancelHarvest,
      isHarvesting,
      openDedupModal: () => {
        if (dedupReport) {
          setIsDedupModalOpen(true)
        } else {
          handleDeduplicate()
        }
      },
    })
    return () => {
      unregisterRibbonActions(['startHarvest', 'stopHarvest', 'isHarvesting', 'openDedupModal'])
    }
  }, [registerRibbonActions, unregisterRibbonActions, handleStartHarvest, handleCancelHarvest, isHarvesting, dedupReport, handleDeduplicate])

  const allDescriptors: string[] = []
  if (protocol?.search_descriptors) {
    for (const [, list] of Object.entries(protocol.search_descriptors)) {
      allDescriptors.push(...list)
    }
  }

  const filters = protocol?.search_filters || {}

  const harvestEntries = entries.filter(
    (e) => e.source === 'Coleta' || e.source === 'Deduplicação' || e.source === 'Sistema'
  )

  const filteredFeed = useMemo(() => {
    if (feedFilter === 'new') return liveFeed.filter((item) => item.isNew)
    if (feedFilter === 'dup') return liveFeed.filter((item) => !item.isNew)
    return liveFeed
  }, [liveFeed, feedFilter])

  return (
    <div className="harvest-page animate-fade-in">
      <PageHeader
        title="Coleta Multibase de Artigos"
        onBack={() => navigate('/projects')}
        subtitle={
          <span>
            Projeto: <strong>{activeProject?.title}</strong> — Coleta concorrente com deduplicação algorítmica de 3 passes
          </span>
        }
        primaryAction={
          /* Ação primária ÚNICA. "Cancelar Coleta" e "Deduplicar & Relatório"
             saíram daqui: o ribbon já os despacha por `stopHarvest` e
             `openDedupModal`, e manter os dois conjuntos dava dois caminhos
             para o mesmo comando. */
          isHarvesting ? (
            <Button
              variant="destructive"
              size="md"
              onClick={handleCancelHarvest}
              leftIcon={<StopCircle size={14} />}
            >
              Cancelar Coleta
            </Button>
          ) : (
            <Button
              variant="primary"
              size="md"
              onClick={handleStartHarvest}
              disabled={selectedSources.length === 0 || allDescriptors.length === 0}
              leftIcon={<Play size={14} />}
            >
              Iniciar Coleta Multibase
            </Button>
          )
        }
        status={
          isDeduplicating && (
            <span className="save-indicator animate-fade-in" role="status" aria-live="polite">
              <RefreshCw size={13} className="animate-spin" aria-hidden="true" /> Deduplicando…
            </span>
          )
        }
      />

      {/* ── NAVEGAÇÃO SEGMENTADA MOBILE (Exibida apenas em telas < 900px) ── */}
      <div className="harvest-mobile-segmented-nav">
        <button
          type="button"
          className={`mobile-seg-btn ${mobileTab === 'sources' ? 'active' : ''}`}
          onClick={() => setMobileTab('sources')}
        >
          <Database size={15} />
          <span>Bases & Parâmetros ({selectedSources.length})</span>
        </button>
        <button
          type="button"
          className={`mobile-seg-btn ${mobileTab === 'monitor' ? 'active' : ''}`}
          onClick={() => setMobileTab('monitor')}
        >
          <Radio size={15} />
          <span>Monitor & Logs ({totalFound})</span>
        </button>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          BARRA SUPERIOR DE STATUS E MÉTRICAS DA COLETA (ACIMA)
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="harvest-queue-container">
        <div className="harvest-top-controls-bar">
          <div className="harvest-metrics-group">
            <span className="queue-status-chip">
              <Database size={13} className="icon-accent" />
              Bases Selecionadas: <strong>{selectedSources.length} / {sources.length}</strong>
            </span>
            <span className="queue-status-chip">
              <Search size={13} className="icon-accent" />
              Descritores Ativos: <strong>{allDescriptors.length} pares</strong>
            </span>
            <span className="queue-status-chip inc">
              <CheckCircle2 size={13} />
              Total Recuperado: <strong>{totalFound}</strong> artigos
            </span>
            {totalDuplicate > 0 && (
              <span className="queue-status-chip warning">
                <Layers size={13} />
                Duplicatas Unificadas: <strong>{totalDuplicate}</strong>
              </span>
            )}
          </div>

          <div className="harvest-top-actions">
            <button
              type="button"
              className="btn-secondary small"
              onClick={() => navigate(`/projects/${id}/screening`)}
              title="Avançar diretamente para a tela de triagem de estudos"
            >
              <BookOpen size={13} /> Ir para Triagem 1 <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          GRID BIPARTIDO LADO A LADO (WORKBENCH TWO-COLUMN GRID)
          Coluna 1: Parâmetros, Bases & Histórico | Coluna 2: Lista de Artigos & Monitor
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="harvest-workbench-grid">
        {/* ── COLUNA DA ESQUERDA: PARÂMETROS, BASES & HISTÓRICO ───────── */}
        <div className={`harvest-config-pane mobile-tab-view ${mobileTab === 'sources' ? 'mobile-show' : ''}`}>
          <div className="pane-header-title">
            <Database size={16} className="icon-accent" />
            <h3>Parâmetros da Coleta Multibase</h3>
          </div>

          <div className="pane-scroll-body">
            {/* Seção 1: Seleção de Bases */}
            <Card surface="primaria" className="harvest-config-card">
              <div className="card-mini-title">
                <h4>1. Bases de Dados Acadêmicas</h4>
                <span className="meta-hint">{selectedSources.length} ativas</span>
              </div>
              <div className="sources-list-grid">
                {sources.map((src) => {
                  const isSelected = selectedSources.includes(src.id)
                  const isDisabled = !src.enabled

                  return (
                    /* O cartão é o rótulo da própria caixa de seleção: com
                       <label>, o clique em qualquer ponto e a navegação por
                       teclado saem de graça do controle nativo. O onClick no
                       contêiner, além de invisível ao teclado, disparava duas
                       vezes junto com o onChange. */
                    <label
                      key={src.id}
                      className={`source-card-item ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected && !isDisabled}
                        disabled={isDisabled}
                        onChange={() => toggleSource(src)}
                      />
                      <div className="source-info">
                        <div className="source-title-row">
                          <span className="source-title">{src.name}</span>
                          {isDisabled && (
                            <span className="badge-key-warning">
                              <Key size={10} /> Requer Chave
                            </span>
                          )}
                        </div>
                        <span className="source-desc">{src.description}</span>
                      </div>
                    </label>
                  )
                })}
              </div>
            </Card>

            {/* Seção 2: Descritores Ativos do Protocolo */}
            <Card surface="primaria" className="harvest-config-card">
              <div className="card-mini-title">
                <h4>2. Descritores em Pares ({allDescriptors.length})</h4>
                <button
                  type="button"
                  className="link-action"
                  onClick={() => navigate(`/projects/${id}/protocol`)}
                >
                  Editar no Protocolo
                </button>
              </div>
              {allDescriptors.length === 0 ? (
                <div className="no-descriptors-warning">
                  <AlertCircle size={15} />
                  <span>Nenhum descritor em pares cadastrado no protocolo.</span>
                </div>
              ) : (
                <div className="descriptors-chips-list">
                  {allDescriptors.map((desc, idx) => (
                    <span key={idx} className="desc-chip">
                      <code>{desc}</code>
                    </span>
                  ))}
                </div>
              )}
            </Card>

            {/* Seção 3: Recorte Temporal & Limites */}
            <Card surface="primaria" className="harvest-config-card">
              <div className="card-mini-title">
                <h4>3. Recorte Vigente & Limites</h4>
              </div>
              <div className="config-fields-group">
                <div className="config-info-row">
                  <span>Período:</span>
                  <strong>
                    {filters.year_start || filters.year_end
                      ? `${filters.year_start || 'Início'} a ${filters.year_end || 'Atual'}`
                      : 'Todos os anos'}
                  </strong>
                </div>
                <div className="config-info-row">
                  <span>Idiomas:</span>
                  <strong>
                    {filters.languages && filters.languages.length > 0
                      ? filters.languages.join(', ')
                      : 'Todos'}
                  </strong>
                </div>
                <div className="form-group-limit">
                  <label htmlFor="max-records-select">Limite de Registros por Consulta:</label>
                  <select
                    id="max-records-select"
                    className="select-control"
                    value={maxRecords}
                    onChange={(e) => setMaxRecords(Number(e.target.value))}
                    disabled={isHarvesting}
                  >
                    <option value={0}>♾️ Ilimitado (Recuperar todos os registros disponíveis)</option>
                    <option value={50}>50 artigos por descritor</option>
                    <option value={100}>100 artigos por descritor</option>
                    <option value={200}>200 artigos por descritor</option>
                    <option value={500}>500 artigos por descritor</option>
                    <option value={1000}>1.000 artigos por descritor</option>
                  </select>
                </div>
              </div>
            </Card>

            {/* Seção 4: Histórico de Execuções */}
            <Card surface="primaria" className="harvest-config-card">
              <div className="card-mini-title">
                <h4>
                  <History size={14} className="icon-accent" /> Histórico de Execuções ({harvestRuns.length})
                </h4>
              </div>
              {harvestRuns.length === 0 ? (
                <p className="empty-subtext">Nenhuma execução anterior registrada.</p>
              ) : (
                <div className="runs-mini-list">
                  {harvestRuns.map((run) => (
                    <div key={run.id} className="run-mini-item">
                      <div className="run-header">
                        <strong>{run.source_name}</strong>
                        <span className={`run-status ${run.status}`}>
                          {run.status === 'completed' ? 'Concluído' : run.status === 'running' ? 'Em execução' : 'Falha'}
                        </span>
                      </div>
                      <div className="run-counts">
                        <span>Recuperados: {run.records_found}</span>
                        <span className="text-success">Novos: +{run.records_new}</span>
                        {run.records_duplicate > 0 && (
                          <span className="text-warning">Duplicatas: {run.records_duplicate}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>

        {/* ── COLUNA DA DIREITA: LISTA DE TRABALHOS COLETADOS & MONITOR ─ */}
        <div className={`harvest-monitor-pane mobile-tab-view ${mobileTab === 'monitor' ? 'mobile-show' : ''}`}>
        <Tabs.Root
          className="monitor-tabs-root"
          value={feedTab}
          onValueChange={(v) => setFeedTab(v as 'stream' | 'terminal')}
        >
          <div className="pane-header-title">
            <Tabs.List asChild>
              <div className="monitor-title-tabs">
                <Tabs.Trigger value="stream" className={`monitor-tab-btn ${feedTab === 'stream' ? 'active' : ''}`}>
                  <Radio size={14} className={isHarvesting ? 'icon-live-pulse' : 'icon-accent'} />
                  Trabalhos Coletados ({filteredFeed.length})
                </Tabs.Trigger>
                <Tabs.Trigger value="terminal" className={`monitor-tab-btn ${feedTab === 'terminal' ? 'active' : ''}`}>
                  <Terminal size={14} />
                  Terminal de Logs ({harvestEntries.length})
                </Tabs.Trigger>
              </div>
            </Tabs.List>

            <span className={`live-status-pill ${isHarvesting ? 'running' : 'idle'}`}>
              {isHarvesting ? 'Coleta em Execução' : 'Pronto para Coleta'}
            </span>
          </div>

          <div className="pane-scroll-body">
            {/* Progresso Concorrente por Base */}
            <Card surface="primaria" className="sources-progress-card">
              <div className="sources-progress-header">
                <h4>Progresso Concorrente por Base:</h4>
                <div className="feed-filters-inline">
                  <button
                    type="button"
                    className={`btn-feed-filter ${feedFilter === 'all' ? 'active' : ''}`}
                    onClick={() => setFeedFilter('all')}
                  >
                    Todos
                  </button>
                  <button
                    type="button"
                    className={`btn-feed-filter ${feedFilter === 'new' ? 'active' : ''}`}
                    onClick={() => setFeedFilter('new')}
                  >
                    Apenas Novos
                  </button>
                  <button
                    type="button"
                    className={`btn-feed-filter ${feedFilter === 'dup' ? 'active' : ''}`}
                    onClick={() => setFeedFilter('dup')}
                  >
                    Duplicatas
                  </button>
                </div>
              </div>

              {/* Resumo anunciado. As linhas abaixo se atualizam a cada 1,5 s —
                  colocar `aria-live` nelas faria o leitor de tela ler a grade
                  inteira dez vezes por minuto. Este resumo só muda quando uma
                  base TRANSICIONA de estado, que é o evento que interessa: são
                  poucas mudanças por coleta, e cada uma é notícia. */}
              <p className="sources-progress-resumo" role="status" aria-live="polite">
                {(() => {
                  const feitas = selectedSources.filter((s) => progress[s]?.status === 'completed').length
                  const rodando = selectedSources.filter((s) => progress[s]?.status === 'running').length
                  const comErro = selectedSources.filter((s) => progress[s]?.status === 'error').length
                  const partes = [`${feitas} de ${selectedSources.length} bases concluídas`]
                  if (rodando) partes.push(`${rodando} em execução`)
                  if (comErro) partes.push(`${comErro} com erro`)
                  return partes.join(' · ')
                })()}
              </p>

              <div className="sources-progress-grid">
                {selectedSources.map((srcId) => {
                  const p = progress[srcId]
                  const srcObj = sources.find((s) => s.id === srcId)
                  const isRunning = p?.status === 'running'
                  const isDone = p?.status === 'completed'
                  const isError = p?.status === 'error'

                  return (
                    <div key={srcId} className="source-progress-row">
                      <div className="source-progress-info">
                        <strong>{srcObj?.name || srcId}</strong>
                        <span className={`status-tag ${p?.status || 'idle'}`}>
                          {isRunning ? 'Em execução' : isDone ? 'Concluído' : isError ? 'Erro' : 'Aguardando'}
                        </span>
                      </div>
                      <div className="source-progress-count">
                        <span>{p?.total_found ?? 0} registros</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>

            {/* Visualização de Trabalhos Coletados (Feed Stream) */}
            <Tabs.Content value="stream" className="harvest-stream-container">
                <div className="stream-header-info">
                  <span>Feed de Artigos Recuperados:</span>
                  <span className="stream-counter-badge">{filteredFeed.length} exibidos</span>
                </div>

                <div className="stream-items-scroll" ref={feedScrollRef}>
                  {filteredFeed.length === 0 ? (
                    <div className="stream-empty-box">
                      <BookOpen size={24} />
                      <p>
                        {totalFound === 0
                          ? 'Inicie a coleta multibase para visualizar os artigos sendo recuperados e deduplicados em tempo real.'
                          : 'Nenhum artigo corresponde ao filtro selecionado.'}
                      </p>
                    </div>
                  ) : (
                    filteredFeed.map((item, index) => (
                      <div key={`${item.id}-${index}`} className={`feed-item-card ${item.isNew ? 'is-new' : 'is-dup'}`}>
                        <div className="feed-item-top">
                          <span className="feed-badge-source">{item.source}</span>
                          {item.year && <span className="feed-item-year">{item.year}</span>}
                          <span className={`feed-tag-pill ${item.isNew ? 'tag-new' : 'tag-dup'}`}>
                            {item.isNew ? <FileCheck size={12} /> : <FileX size={12} />}
                            {item.isNew ? 'Novo Inserido' : 'Duplicata Unificada'}
                          </span>
                        </div>
                        <h4 className="feed-item-title">{item.title}</h4>
                        {item.authors && <p className="feed-item-authors">{item.authors}</p>}
                      </div>
                    ))
                  )}
                </div>
            </Tabs.Content>
            <Tabs.Content value="terminal" className="tabs-content-passthrough">
              {/* Terminal Console de Logs */}
              <Card surface="primaria" relief="afundado" className="harvest-terminal-card">
                <div className="terminal-header">
                  <span>Logs de Execução da Coleta & Deduplicação</span>
                  <span className="log-count-tag">{harvestEntries.length} eventos</span>
                </div>
                <div className="terminal-body" ref={logConsoleRef}>
                  {harvestEntries.length === 0 ? (
                    <div className="terminal-empty">
                      <span>Nenhum evento registrado nesta sessão. Clique em "Iniciar Coleta Multibase".</span>
                    </div>
                  ) : (
                    harvestEntries.map((e) => (
                      <div key={e.id} className={`terminal-line ${e.level}`}>
                        <span className="terminal-time">
                          [{e.timestamp instanceof Date ? e.timestamp.toLocaleTimeString() : String(e.timestamp)}]
                        </span>
                        <span className="terminal-cat">[{e.source}]</span>
                        <span className="terminal-msg">{e.message}</span>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </Tabs.Content>

            {/* Banner de Avanço para a Triagem 1 */}
            <Card surface="primaria" className="harvest-next-phase-card">
              <div className="next-phase-content">
                <BookOpen size={20} className="icon-accent" />
                <div>
                  <strong>Pronto para a Triagem de Elegibilidade?</strong>
                  <p>
                    Após a coleta e deduplicação, acesse a <strong>Triagem 1</strong> para avaliar títulos e resumos conforme os critérios do protocolo.
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="btn-primary small"
                onClick={() => navigate(`/projects/${id}/screening`)}
              >
                Avançar para Triagem 1 <ArrowRight size={14} />
              </button>
            </Card>
          </div>
        </Tabs.Root>
        </div>
      </div>

      {/* Deduplication Report Modal */}
      {id && (
        <DeduplicationReportModal
          report={dedupReport}
          isOpen={isDedupModalOpen}
          onClose={() => setIsDedupModalOpen(false)}
          projectId={id}
        />
      )}
    </div>
  )
}
