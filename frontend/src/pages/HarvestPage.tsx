/**
 * RSAC V2 — Harvest Page (Coleta Automatizada Multibase)
 * Execução concorrente de harvesters (BDTD, SciELO, OpenAlex, PubMed, Scopus)
 * com monitoramento em tempo real via WebSockets e deduplicação de 3 passes.
 */

import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Download,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Database,
  Search,
  ArrowLeft,
  RefreshCw,
  Layers,
  Sparkles,
  ExternalLink,
  Sliders,
  Radio,
  FileCheck,
  FileX,
  History,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useLogStore } from '@/stores/useLogStore'
import type { HarvestRun, HarvestSourceInfo, Protocol, Project } from '@/types/api'
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
  const [maxRecords, setMaxRecords] = useState<number>(100)
  const [harvestRuns, setHarvestRuns] = useState<HarvestRun[]>([])
  const [loading, setLoading] = useState(true)
  const [isHarvesting, setIsHarvesting] = useState(false)

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
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [id])

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
        } catch (e) {
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
      setLiveStatus(`[${msg.source}] Buscando: "${msg.descriptor}" (Página ${msg.page})`)
      setIsHarvesting(true)
      info('Coleta', `[${msg.source}] Consultando página ${msg.page} para "${msg.descriptor}"`)
    } else if (msg.type === 'paper_harvested') {
      setLiveFound(msg.total_found)
      setLiveNew(msg.total_new)
      setLiveDuplicate(msg.total_duplicate)

      const feedItem: LiveFeedItem = {
        id: Math.random().toString(36).substring(2, 9),
        source: msg.source,
        title: msg.title,
        isNew: msg.is_new,
        timestamp: new Date().toLocaleTimeString('pt-BR'),
      }

      setLiveFeed((prev) => [feedItem, ...prev.slice(0, 30)])

      if (msg.is_new) {
        success('Coleta', `[${msg.source}] Estudo novo inserido`, `Título: ${msg.title}\nID: ${msg.paper_id || 'N/A'}`)
      } else {
        warn('Coleta', `[${msg.source}] Duplicata detectada e unificada`, `Título: ${msg.title}`)
      }
    } else if (msg.type === 'harvest_source_completed') {
      setLiveStatus(`Fonte ${msg.source} concluída (${msg.records_new} novos, ${msg.records_duplicate} duplicados).`)
      info('Coleta', `Fonte [${msg.source}] finalizada`, `Novos inseridos: ${msg.records_new} | Duplicatas unificadas: ${msg.records_duplicate}`)
    } else if (msg.type === 'harvest_all_completed') {
      setIsHarvesting(false)
      setLiveStatus('Coleta multibase finalizada com sucesso!')
      success('Coleta', 'Busca federada e desduplicação concluídas com sucesso!', `Total recuperado: ${liveFound} | Novos: ${liveNew} | Duplicatas: ${liveDuplicate}`)
      if (id) {
        api.listHarvestRuns(id).then((res) => setHarvestRuns(res.items))
      }
    }
  }

  const toggleSource = (sourceId: string) => {
    if (selectedSources.includes(sourceId)) {
      setSelectedSources(selectedSources.filter((s) => s !== sourceId))
    } else {
      setSelectedSources([...selectedSources, sourceId])
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
      setLiveStatus('Disparando coletores...')

      await api.startHarvest(id, {
        sources: selectedSources,
        max_records_per_descriptor: maxRecords,
      })
    } catch (err) {
      console.error('Erro ao iniciar coleta:', err)
      setIsHarvesting(false)
      setLiveStatus('Erro ao iniciar coleta.')
    }
  }

  // Agrupar descritores configurados no protocolo
  const allDescriptors: string[] = []
  if (protocol?.search_descriptors) {
    for (const [, list] of Object.entries(protocol.search_descriptors)) {
      allDescriptors.push(...list)
    }
  }

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
            Projeto: <strong>{activeProject?.title}</strong> — Coleta automatizada com deduplicação de 3 passes
          </p>
        </div>
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

      {/* Main Grid: Config on Left, Live Progress & History on Right */}
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
              Selecione as bases que serão consultadas simultaneamente.
            </p>

            <div className="sources-list">
              {sources.map((src) => {
                const isSelected = selectedSources.includes(src.id)
                return (
                  <div
                    key={src.id}
                    className={`source-card-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => toggleSource(src.id)}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSource(src.id)}
                    />
                    <div className="source-info">
                      <span className="source-title">{src.name}</span>
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

          {/* Limit Config */}
          <div className="harvest-card">
            <div className="card-header-icon">
              <Sliders size={20} className="icon-accent" />
              <h2>3. Limite por Descritor</h2>
            </div>
            <div className="limit-selector">
              <label>Máximo de registros por descritor:</label>
              <select
                value={maxRecords}
                onChange={(e) => setMaxRecords(Number(e.target.value))}
                disabled={isHarvesting}
              >
                <option value={25}>25 artigos</option>
                <option value={50}>50 artigos</option>
                <option value={100}>100 artigos (Recomendado)</option>
                <option value={200}>200 artigos</option>
                <option value={300}>300 artigos</option>
              </select>
            </div>
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
              <h3>Stream de Artigos Recebidos:</h3>
              {liveFeed.length === 0 ? (
                <div className="empty-feed-placeholder">
                  <p>Inicie a coleta para visualizar os artigos sendo recuperados e deduplicados em tempo real.</p>
                </div>
              ) : (
                <div className="feed-items-scroll">
                  {liveFeed.map((item) => (
                    <div key={item.id} className={`feed-item ${item.isNew ? 'is-new' : 'is-dup'}`}>
                      <span className="feed-badge-source">{item.source}</span>
                      <span className="feed-title">{item.title}</span>
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
    </div>
  )
}
