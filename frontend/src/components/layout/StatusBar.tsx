/**
 * RSAC V2 — StatusBar Component
 * Barra de status inferior com indicadores de backend, modo de IA e versão.
 */

import { useSettingsStore } from '@/stores/useSettingsStore'
import { useLogStore } from '@/stores/useLogStore'
import { Sparkles, Edit3, Terminal, AlertCircle } from 'lucide-react'
import { RsacMark } from '@/components/brand/RsacMark'
import { BetaBadge } from '@/components/brand/BetaBadge'
import { api } from '@/api/client'
import './StatusBar.css'

export function StatusBar(): JSX.Element {
  const { backendStatus, backendVersion, aiEnabled } = useSettingsStore()
  const { entries, panelOpen, togglePanel } = useLogStore()

  const errorCount = entries.filter((e) => e.level === 'error').length

  const statusText =
    backendStatus === 'online' ? 'Backend Online' :
    backendStatus === 'connecting' ? 'Conectando...' : 'Backend Offline'

  const handleConfigureBackend = () => {
    const current = api.getBaseUrl().replace(/\/api\/v1\/?$/, '')
    const input = window.prompt(
      'Configurar URL do Backend (ex: https://seu-tunnel.trycloudflare.com ou http://127.0.0.1:8000):',
      current
    )
    if (input && input.trim()) {
      api.setBaseUrl(input.trim())
      window.location.reload()
    }
  }

  return (
    <footer className="status-bar">
      <div className="status-bar-left">
        <span className="status-brand" title="RSAC V2 — versão beta">
          <RsacMark size={12} tone="auto" label={null} />
          <span className="status-brand-name">RSAC V2</span>
          <BetaBadge tone="auto" size="xs" />
        </span>
        <span className="status-divider">|</span>
        <span
          className="status-indicator"
          onClick={handleConfigureBackend}
          style={{ cursor: 'pointer' }}
          title={`Backend: ${api.getBaseUrl()} (Clique para alterar URL)`}
        >
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
