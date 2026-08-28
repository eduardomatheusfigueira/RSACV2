/**
 * Revsist — Log Panel (Painel Lateral de Logs)
 * Painel colapsável na lateral direita que exibe todos os eventos do sistema
 * com filtros por nível, detalhes expandíveis e timestamp preciso.
 */

import { useState } from 'react'
import {
  X,
  Trash2,
  Info,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Bug,
  ChevronDown,
  ChevronRight,
  Filter,
} from 'lucide-react'
import { useLogStore, type LogEntry, type LogLevel } from '@/stores/useLogStore'
import './LogPanel.css'

const LEVEL_CONFIG: Record<LogLevel, { icon: React.ReactNode; label: string; className: string }> = {
  info:    { icon: <Info size={12} />,           label: 'Info',    className: 'level-info' },
  success: { icon: <CheckCircle2 size={12} />,   label: 'OK',      className: 'level-success' },
  warn:    { icon: <AlertTriangle size={12} />,  label: 'Aviso',   className: 'level-warn' },
  error:   { icon: <XCircle size={12} />,        label: 'Erro',    className: 'level-error' },
  debug:   { icon: <Bug size={12} />,            label: 'Debug',   className: 'level-debug' },
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDuration(ms?: number): string {
  if (ms === undefined) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function LogEntryRow({ entry }: { entry: LogEntry }): JSX.Element {
  const [expanded, setExpanded] = useState(false)
  const config = LEVEL_CONFIG[entry.level]

  return (
    <div className={`log-entry ${config.className} ${expanded ? 'expanded' : ''}`}>
      {/* A linha inteira é o controle que expande o detalhe: precisa ser um
          <button> para o teclado e para o leitor de tela chegarem nela. */}
      <button
        type="button"
        className="log-entry-main"
        onClick={() => entry.detail && setExpanded(!expanded)}
        disabled={!entry.detail}
        aria-expanded={entry.detail ? expanded : undefined}
      >
        <span className="log-level-badge">
          {config.icon}
        </span>
        <span className="log-time">{formatTime(entry.timestamp)}</span>
        <span className="log-source-tag">{entry.source}</span>
        <span className="log-message">{entry.message}</span>
        {entry.duration !== undefined && (
          <span className="log-duration">{formatDuration(entry.duration)}</span>
        )}
        {entry.detail && (
          <span className="log-expand-indicator">
            {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          </span>
        )}
      </button>
      {expanded && entry.detail && (
        <div className="log-entry-detail">
          <pre>{entry.detail}</pre>
        </div>
      )}
    </div>
  )
}

export function LogPanel(): JSX.Element {
  const { entries, panelOpen, filter, setPanelOpen, setFilter, clearLogs } = useLogStore()

  if (!panelOpen) return <></>

  const filteredEntries = filter === 'all'
    ? entries
    : entries.filter((e) => e.level === filter)

  const counts = {
    all: entries.length,
    info: entries.filter((e) => e.level === 'info').length,
    success: entries.filter((e) => e.level === 'success').length,
    warn: entries.filter((e) => e.level === 'warn').length,
    error: entries.filter((e) => e.level === 'error').length,
    debug: entries.filter((e) => e.level === 'debug').length,
  }

  return (
    <aside className="log-panel">
      {/* Header */}
      <div className="log-panel-header">
        <div className="log-panel-title-row">
          <span className="log-panel-title">Log do Sistema</span>
          <span className="log-panel-count">{entries.length} eventos</span>
        </div>
        <div className="log-panel-actions">
          <button type="button" className="log-action-btn" onClick={clearLogs} title="Limpar Logs"
            aria-label="Limpar Logs"
          >
            <Trash2 size={12} />
          </button>
          <button type="button" className="log-action-btn" onClick={() => setPanelOpen(false)} title="Fechar Painel">
            <X size={12} />
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="log-filter-bar">
        <Filter size={10} className="filter-icon" />
        <button
          type="button"
          className={`log-filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          Todos <span className="filter-count">{counts.all}</span>
        </button>
        <button
          type="button"
          className={`log-filter-btn filter-error ${filter === 'error' ? 'active' : ''}`}
          onClick={() => setFilter('error')}
        >
          Erros <span className="filter-count">{counts.error}</span>
        </button>
        <button
          type="button"
          className={`log-filter-btn filter-warn ${filter === 'warn' ? 'active' : ''}`}
          onClick={() => setFilter('warn')}
        >
          Avisos <span className="filter-count">{counts.warn}</span>
        </button>
        <button
          type="button"
          className={`log-filter-btn filter-success ${filter === 'success' ? 'active' : ''}`}
          onClick={() => setFilter('success')}
        >
          OK <span className="filter-count">{counts.success}</span>
        </button>
        <button
          type="button"
          className={`log-filter-btn filter-debug ${filter === 'debug' ? 'active' : ''}`}
          onClick={() => setFilter('debug')}
        >
          Debug <span className="filter-count">{counts.debug}</span>
        </button>
      </div>

      {/* Log Entries */}
      <div className="log-entries-scroll">
        {filteredEntries.length === 0 ? (
          <div className="log-empty">
            <span>Nenhum evento registrado{filter !== 'all' ? ` para "${filter}"` : ''}.</span>
          </div>
        ) : (
          filteredEntries.map((entry) => (
            <LogEntryRow key={entry.id} entry={entry} />
          ))
        )}
      </div>
    </aside>
  )
}
