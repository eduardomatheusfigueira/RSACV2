/**
 * RSAC V2 — Harvest Page (Coleta Automatizada Multibase)
 * Execução concorrente de harvesters (BDTD, SciELO, OpenAlex, PubMed, Scopus)
 * com monitoramento em tempo real via WebSockets, deduplicação de 3 passes e cancelamento.
 */

import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Play,
  ArrowLeft,
  RefreshCw,
  Sliders,
  Radio,
  FileCheck,
  FileX,
  History,
  AlertCircle,
  Database,
  Search,
  StopCircle,
  Key,
  Filter,
  Layers,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useLogStore } from '@/stores/useLogStore'
import type { DeduplicationReport, HarvestRun, HarvestSourceInfo, Protocol } from '@/types/api'
import { DeduplicationReportModal } from '@/components/common/DeduplicationReportModal'
import './HarvestPage.css'

interface LiveFeedItem {
  id: string
  source: string
  title: string
  isNew: boolean
  timestamp: string
}

export function HarvestPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject } = useSettingsStore()
  const { info, success, warn, error } = useLogStore()

  // State
  const [sources, setSources] = useState<HarvestSourceInfo[]>([])
  const [selectedSources, setSelectedSources] = useState<string[]>(['BDTD', 'SciELO', 'OpenAlex'])
  const [protocol, setProtocol] = useState<Protocol | null>(null)
  const [maxRecords, setMaxRecords] = useState<number>(0)
  const [fetchDetails, setFetchDetails] = useState<boolean>(true)
  const [harvestRuns, setHarvestRuns] = useState<HarvestRun[]>([])
  const [loading, setLoading] = useState(true)
  const [isHarvesting, setIsHarvesting] = useState(false)

  // Deduplication Report State
  const [isDeduplicating, setIsDeduplicating] = useState(false)
  const [dedupReport, setDedupReport] = useState<DeduplicationReport | null>(null)
  const [isDedupModalOpen, setIsDedupModalOpen] = useState(false)

  // Live WebSocket State
  const [liveStatus, setLiveStatus] = useState<string>('Pronto para iniciar coleta.')
  const [liveFound, setLiveFound] = useState<number>(0)
  const [liveNew, setLiveNew] = useState<number>(0)
  const [liveDuplicate, setLiveDuplicate] = useState<number>(0)
  const [liveFeed, setLiveFeed] = useState<LiveFeedItem[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (id) {
      loadData(id)
      initWebSocket(id)
      checkInitialStatus(id)
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [id])

  const checkInitialStatus = async (projectId: string) => {
    try {
      const statusRes = await api.getHarvestStatus(projectId)
      if (statusRes?.status === 'running') {
        setIsHarvesting(true)
        setLiveStatus('Coleta em andamento em segundo plano...')
      }
    } catch {
      // ignore
    }
  }

  const loadData = async (projectId: string) => {
    try {
      setLoading(true)
      if (!activeProject || activeProject.id !== projectId) {
        const proj = await api.getProject(projectId)
        setActiveProject(proj)
      }

      const [srcRes, protoRes, runsRes] = await Promise.all([
        api.getAvailableSources(projectId),
        api.getProtocol(projectId),
        api.listHarvestRuns(projectId),
      ])

      setSources(srcRes.sources)
      setProtocol(protoRes)
      setHarvestRuns(runsRes.items)

      // Selecionar apenas fontes habilitadas por padrão
      const enabledIds = srcRes.sources
        .filter((s) => s.enabled && ['BDTD', 'SciELO', 'OpenAlex'].includes(s.id))
        .map((s) => s.id)
      setSelectedSources(enabledIds.length > 0 ? enabledIds : ['BDTD', 'SciELO', 'OpenAlex'])
    } catch (err) {
      console.error('Erro ao carregar dados de coleta:', err)
    } finally {
      setLoading(false)
    }
  }

  const initWebSocket = (projectId: string) => {
    try {
      const wsUrl = api.getWebSocketUrl(projectId)
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        info('WebSocket', `Canal de streaming de coleta conectado ao projeto ${projectId}`)
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          handleWebSocketMessage(msg)
        } catch {
          // ignore non-json
        }
      }

      ws.onclose = () => {
        info('WebSocket', 'Canal de streaming de coleta desconectado.')
      }
    } catch (err: any) {
      error('WebSocket', 'Falha ao estabelecer conexão WebSocket de coleta', err.message)
    }
  }

  const handleWebSocketMessage = (msg: any) => {
    if (msg.type === 'harvest_progress') {
      const phaseLabel = msg.phase === 'scraping_details' ? 'Raspando orientadores' : 'Coletando'
      setLiveStatus(`[${msg.source}] ${phaseLabel}: "${msg.descriptor}" (Pág ${msg.page})`)
      setIsHarvesting(true)
      info('Coleta', `[${msg.source}] Consultando página ${msg.page} para "${msg.descriptor}"`)
    } else if (msg.type === 'paper_harvested') {
      setLiveFound(msg.total_found)
      setLiveNew(msg.total_new)
      setLiveDuplicate(msg.total_duplicate)

      if (msg.recent_items && Array.isArray(msg.recent_items)) {
        const newFeedItems = msg.recent_items.map((item: any) => ({
          id: item.paper_id || Math.random().toString(36).substring(2, 9),
          source: msg.source,
          title: item.title,
          isNew: item.is_new,
          timestamp: new Date().toLocaleTimeString('pt-BR'),
        }))
        setLiveFeed((prev) => [...newFeedItems, ...prev.slice(0, 480)])
      } else if (msg.title) {
        const feedItem: LiveFeedItem = {
          id: Math.random().toString(36).substring(2, 9),
          source: msg.source,
          title: msg.title,
          isNew: msg.is_new,
          timestamp: new Date().toLocaleTimeString('pt-BR'),
        }
        setLiveFeed((prev) => [feedItem, ...prev.slice(0, 499)])
      }

      if (msg.is_new) {
        success('Coleta', `[${msg.source}] Estudo novo inserido`)
      } else {
        warn('Coleta', `[${msg.source}] Duplicata unificada`)
      }
    } else if (msg.type === 'harvest_source_completed') {
      setLiveStatus(`Fonte ${msg.source} concluída (${msg.records_new} novos, ${msg.records_duplicate} duplicados).`)
      info('Coleta', `Fonte [${msg.source}] finalizada`, `Novos: ${msg.records_new} | Duplicatas: ${msg.records_duplicate}`)
    } else if (msg.type === 'harvest_source_failed') {
      setLiveStatus(`Erro na fonte ${msg.source}: ${msg.error}`)
      error('Coleta', `Fonte [${msg.source}] falhou: ${msg.error}`)
    } else if (msg.type === 'harvest_all_completed') {
      setIsHarvesting(false)
      setLiveStatus('Coleta multibase finalizada com sucesso!')
      success('Coleta', 'Busca federada concluída!', `Total: ${liveFound} | Novos: ${liveNew} | Duplicatas: ${liveDuplicate}`)
      if (id) {
        api.listHarvestRuns(id).then((res) => setHarvestRuns(res.items))
      }
    } else if (msg.type === 'harvest_cancelled') {
      setIsHarvesting(false)
      setLiveStatus('Coleta cancelada pelo usuário.')
      warn('Coleta', 'Execução de coleta cancelada.')
      if (id) {
        api.listHarvestRuns(id).then((res) => setHarvestRuns(res.items))
      }
    }
  }

  const toggleSource = (source: HarvestSourceInfo) => {
    if (!source.enabled) {
      navigate('/settings')
      return
    }

    if (selectedSources.includes(source.id)) {
      setSelectedSources(selectedSources.filter((s) => s !== source.id))
    } else {
      setSelectedSources([...selectedSources, source.id])
    }
  }

  const handleStartHarvest = async () => {
    if (!id || selectedSources.length === 0) return

    try {
      setIsHarvesting(true)
      setLiveFound(0)
      setLiveNew(0)
      setLiveDuplicate(0)
      setLiveFeed([])
      setLiveStatus('Disparando coletores concorrentes...')

      await api.startHarvest(id, {
        sources: selectedSources,
        max_records_per_descriptor: maxRecords > 0 ? maxRecords : null,
        fetch_details: fetchDetails,
      })
    } catch (err: any) {
      console.error('Erro ao iniciar coleta:', err)
      setIsHarvesting(false)
      setLiveStatus(`Erro: ${err.message || 'Falha ao iniciar'}`)
    }
  }

  const handleCancelHarvest = async () => {
    if (!id) return
    try {
      setLiveStatus('Cancelando coleta...')
      await api.cancelHarvest(id)
    } catch (err: any) {
      console.error('Erro ao cancelar coleta:', err)
    }
  }

  const handleDeduplicate = async () => {
    if (!id) return
    try {
      setIsDeduplicating(true)
      info('Deduplicação', 'Executando consolidação e deduplicação de 3 passes...')
      const res = await api.deduplicateProject(id)
      setDedupReport(res.data)
      setIsDedupModalOpen(true)
      success(
        'Deduplicação',
        `Deduplicação concluída com sucesso!`,
        `Únicos: ${res.data.total_unique} | Duplicatas Excluídas: ${res.data.total_duplicates} (${res.data.dup_rate}%)`
      )
    } catch (err: any) {
      error('Deduplicação', 'Falha ao executar deduplicação', err.message)
    } finally {
      setIsDeduplicating(false)
    }
  }

  // Agrupar descritores configurados no protocolo
  const allDescriptors: string[] = []
  if (protocol?.search_descriptors) {
    for (const [, list] of Object.entries(protocol.search_descriptors)) {
      allDescriptors.push(...list)
    }
  }

  const filters = protocol?.search_filters || {}

  return (
    <div className="harvest-page animate-fade-in">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <button className="btn-back" onClick={() => navigate('/projects')}>
            <ArrowLeft size={16} /> Voltar para Projetos
          </button>
          <h1 className="page-title">Coleta Multibase de Artigos</h1>
          <p className="page-subtitle">
            Projeto: <strong>{activeProject?.title}</strong> — Coleta concorrente com deduplicação de 3 passes
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {isHarvesting && (
            <button className="btn-secondary text-danger" onClick={handleCancelHarvest} style={{ borderColor: 'var(--color-danger, #ef4444)' }}>
              <StopCircle size={18} /> Cancelar Coleta
            </button>
          )}
          <button
            className="btn-secondary btn-dedup"
            onClick={handleDeduplicate}
            disabled={isDeduplicating || isHarvesting}
            title="Executa a desduplicação e gera o relatório consolidado"
          >
            {isDeduplicating ? (
              <>
                <RefreshCw size={18} className="animate-spin" /> Deduplicando...
              </>
            ) : (
              <>
                <Layers size={18} /> Deduplicar & Relatório
              </>
            )}
          </button>
          <button
            className="btn-primary"
            onClick={handleStartHarvest}
            disabled={isHarvesting || selectedSources.length === 0 || allDescriptors.length === 0}
          >
            {isHarvesting ? (
              <>
                <RefreshCw size={18} className="animate-spin" /> Coletando...
              </>
            ) : (
              <>
                <Play size={18} /> Iniciar Coleta Multibase
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="harvest-grid">
        {/* Left Column: Source Selection & Parameters */}
        <div className="harvest-config-col">
          {/* Sources Selector */}
          <div className="harvest-card">
            <div className="card-header-icon">
              <Database size={20} className="icon-accent" />
              <h2>1. Seleção de Bases de Dados</h2>
            </div>
            <p className="card-desc-text">
              Selecione as bases que serão consultadas em paralelo.
            </p>

            <div className="sources-list">
              {sources.map((src) => {
                const isSelected = selectedSources.includes(src.id)
                const isDisabled = !src.enabled

                return (
                  <div
                    key={src.id}
                    className={`source-card-item ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                    onClick={() => toggleSource(src)}
                    style={{ opacity: isDisabled ? 0.65 : 1 }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected && !isDisabled}
                      disabled={isDisabled}
                      onChange={() => toggleSource(src)}
                    />
                    <div className="source-info" style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span className="source-title">{src.name}</span>
                        {isDisabled && (
                          <span className="status-badge failed" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
                            <Key size={11} /> Requer Chave
                          </span>
                        )}
                      </div>
                      <span className="source-desc">{src.description}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Descriptors Overview */}
          <div className="harvest-card">
            <div className="card-header-icon">
              <Search size={20} className="icon-accent" />
              <h2>2. Descritores do Protocolo ({allDescriptors.length})</h2>
            </div>
            {allDescriptors.length === 0 ? (
              <div className="no-descriptors-warning">
                <AlertCircle size={18} />
                <span>
                  Nenhum descritor cadastrado. Configure os pares no{' '}
                  <a onClick={() => navigate(`/projects/${id}/protocol`)}>Protocolo</a>.
                </span>
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
          </div>

          {/* Active Search Filters Summary */}
          <div className="harvest-card">
            <div className="card-header-icon">
              <Filter size={20} className="icon-accent" />
              <h2>3. Recorte Vigente do Protocolo</h2>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              <p>
                <strong>Período:</strong>{' '}
                {filters.year_start || filters.year_end
                  ? `${filters.year_start || 'Início'} a ${filters.year_end || 'Atual'}`
                  : 'Todos os anos'}
              </p>
              <p>
                <strong>Idiomas:</strong>{' '}
                {filters.languages && filters.languages.length > 0
                  ? filters.languages.join(', ')
                  : 'Todos'}
              </p>
              <p>
                <strong>Tipos:</strong>{' '}
                {filters.document_types && filters.document_types.length > 0
                  ? filters.document_types.join(', ')
                  : 'Todos os tipos'}
              </p>
              <p style={{ marginTop: '6px', fontSize: '11px', color: 'var(--text-muted)' }}>
                * Filtros não suportados nativamente pela base são aplicados como pós-filtro local sem perda de registros.
              </p>
            </div>
          </div>

          {/* Limit and Details Config */}
          <div className="harvest-card">
            <div className="card-header-icon">
              <Sliders size={20} className="icon-accent" />
              <h2>4. Ritmo e Enriquecimento</h2>
            </div>
            <div className="limit-selector" style={{ marginBottom: '12px' }}>
              <label>Limite de registros por descritor:</label>
              <select
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

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={fetchDetails}
                onChange={(e) => setFetchDetails(e.target.checked)}
                disabled={isHarvesting}
              />
              <span>Enriquecer metadados (obter orientador, instituição de defesa e resumos completos)</span>
            </label>
          </div>
        </div>

        {/* Right Column: Live Monitor & Execution History */}
        <div className="harvest-monitor-col">
          {/* Live Progress Card */}
          <div className="harvest-card monitor-card">
            <div className="card-header-icon">
              <Radio size={20} className={isHarvesting ? 'icon-live-pulse' : 'icon-accent'} />
              <h2>Painel de Execução em Tempo Real</h2>
            </div>

            <div className="live-status-bar">
              <span className="live-status-text">{liveStatus}</span>
            </div>

            <div className="live-stats-row">
              <div className="live-stat-box found">
                <span className="stat-label">Total Recuperado</span>
                <span className="stat-num">{liveFound}</span>
              </div>
              <div className="live-stat-box new">
                <span className="stat-label">Novos Inseridos</span>
                <span className="stat-num">{liveNew}</span>
              </div>
              <div className="live-stat-box duplicate">
                <span className="stat-label">Duplicatas Unificadas</span>
                <span className="stat-num">{liveDuplicate}</span>
              </div>
            </div>

            {/* Live Feed Stream */}
            <div className="live-feed-container">
              <div className="live-feed-header-row">
                <h3>Stream de Artigos Recebidos:</h3>
                {liveFeed.length > 0 && (
                  <span className="live-feed-counter">{liveFeed.length} estudos no feed</span>
                )}
              </div>
              {liveFeed.length === 0 ? (
                <div className="empty-feed-placeholder">
                  <p>Inicie a coleta para visualizar os artigos sendo recuperados e deduplicados em tempo real.</p>
                </div>
              ) : (
                <div className="feed-items-scroll">
                  {liveFeed.map((item) => (
                    <div key={item.id} className={`feed-item ${item.isNew ? 'is-new' : 'is-dup'}`}>
                      <span className="feed-badge-source">{item.source}</span>
                      {item.timestamp && <span className="feed-time">{item.timestamp}</span>}
                      <span className="feed-title" title={item.title}>{item.title}</span>
                      <span className={`feed-tag ${item.isNew ? 'tag-new' : 'tag-dup'}`}>
                        {item.isNew ? <FileCheck size={13} /> : <FileX size={13} />}
                        {item.isNew ? 'Novo' : 'Duplicata'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Past Harvest Runs History */}
          <div className="harvest-card">
            <div className="card-header-icon">
              <History size={20} className="icon-accent" />
              <h2>Histórico de Execuções ({harvestRuns.length})</h2>
            </div>

            {harvestRuns.length === 0 ? (
              <p className="history-empty">Nenhuma execução de coleta registrada ainda.</p>
            ) : (
              <div className="runs-table-wrapper">
                <table className="runs-table">
                  <thead>
                    <tr>
                      <th>Base Fonte</th>
                      <th>Status</th>
                      <th>Recuperados</th>
                      <th>Novos</th>
                      <th>Duplicados</th>
                      <th>Data</th>
                    </tr>
                  </thead>
                  <tbody>
                    {harvestRuns.map((run) => (
                      <tr key={run.id}>
                        <td>
                          <strong>{run.source_name}</strong>
                        </td>
                        <td>
                          <span className={`status-badge ${run.status}`}>
                            {run.status === 'completed'
                              ? 'Concluído'
                              : run.status === 'running'
                              ? 'Em execução'
                              : run.status === 'cancelled'
                              ? 'Cancelado'
                              : 'Falha'}
                          </span>
                        </td>
                        <td>{run.records_found}</td>
                        <td>
                          <span className="text-success">{run.records_new}</span>
                        </td>
                        <td>
                          <span className="text-warning">{run.records_duplicate}</span>
                        </td>
                        <td>{new Date(run.started_at).toLocaleString('pt-BR')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

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
