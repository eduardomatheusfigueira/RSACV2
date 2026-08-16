/**
 * RSAC V2 — StatusBar Component
 * Barra de status inferior com indicadores de backend, modo de IA e versão.
 */

import { useSettingsStore } from '@/stores/useSettingsStore'
import { useLogStore } from '@/stores/useLogStore'
import { Sparkles, Edit3, Terminal, AlertCircle } from 'lucide-react'
import './StatusBar.css'

export function StatusBar(): JSX.Element {
  const { backendStatus, backendVersion, aiEnabled } = useSettingsStore()
  const { entries, panelOpen, togglePanel } = useLogStore()

  const errorCount = entries.filter((e) => e.level === 'error').length

  const statusText =
    backendStatus === 'online' ? 'Backend Online' :
    backendStatus === 'connecting' ? 'Conectando...' : 'Backend Offline'

  return (
    <footer className="status-bar">
      <div className="status-bar-left">
        <span className="status-indicator">
          <span className={`status-dot ${backendStatus || 'offline'}`} />
          {statusText}
        </span>
        <span className="status-divider">|</span>
        <span className={`status-ai-mode ${aiEnabled ? 'active' : 'manual'}`}>
          {aiEnabled ? (
            <>
              <Sparkles size={12} /> Modo Assistido
            </>
          ) : (
            <>
              <Edit3 size={12} /> Modo Manual
            </>
          )}
        </span>
      </div>
      <div className="status-bar-right">
        {backendVersion && (
          <span className="status-version">v{backendVersion}</span>
        )}
        <button
          type="button"
          className={`status-log-btn ${panelOpen ? 'active' : ''} ${errorCount > 0 ? 'has-errors' : ''}`}
          onClick={togglePanel}
          title={panelOpen ? 'Fechar painel de logs' : 'Abrir painel de logs de processos'}
        >
          <Terminal size={12} />
          <span>Logs</span>
          {errorCount > 0 ? (
            <span className="log-badge error">
              <AlertCircle size={9} /> {errorCount}
            </span>
          ) : entries.length > 0 ? (
            <span className="log-badge count">{entries.length}</span>
          ) : null}
        </button>
      </div>
    </footer>
  )
}
