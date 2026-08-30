/**
 * Revsist — StatusBar Component
 * Barra de status inferior com indicadores de backend, modo de Assistência e versão.
 */

import { useSettingsStore } from '@/stores/useSettingsStore'
import { useLogStore } from '@/stores/useLogStore'
import { useAuthStore } from '@/stores/useAuthStore'
import { Sparkles, Edit3, Terminal, AlertCircle, LogOut, UserRound } from 'lucide-react'
import { RsacMark } from '@/components/brand/RsacMark'
import { BetaBadge } from '@/components/brand/BetaBadge'
import { api } from '@/api/client'
import './StatusBar.css'

export function StatusBar(): JSX.Element {
  const { backendStatus, backendVersion, aiEnabled } = useSettingsStore()
  const { entries, panelOpen, togglePanel } = useLogStore()
  const { user, logout } = useAuthStore()

  const errorCount = entries.filter((e) => e.level === 'error').length

  const statusText =
    backendStatus === 'online' ? 'Serviços Online' :
    backendStatus === 'connecting' ? 'Conectando...' : 'Serviços Offline'

  const handleLogout = async () => {
    if (!window.confirm('Encerrar a sessão? Você precisará entrar novamente.')) return
    await logout()
  }

  return (
    <footer className="status-bar">
      <div className="status-bar-left">
        <span className="status-brand" title="Revsist — versão beta">
          <RsacMark size={12} tone="auto" label={null} />
          <span className="status-brand-name">Revsist</span>
          <BetaBadge tone="auto" size="xs" />
        </span>
        <span className="status-divider">|</span>
        {/* Os rótulos vão em `<span>` nomeado, e não soltos como nó de
            texto, porque é ele que a folha de estilo precisa poder recolher
            na tela pequena. Enquanto eram texto solto, a regra que tentava
            escondê-los no celular não pegava em nada — e a barra estourava
            para fora da largura. */}
        <span
          className="status-indicator"
          title={`Status da Aplicação: ${statusText}`}
        >
          <span className={`status-dot ${backendStatus || 'offline'}`} />
          <span className="status-label">{statusText}</span>
        </span>
        <span className="status-divider">|</span>
        <span
          className={`status-ai-mode ${aiEnabled ? 'active' : 'manual'}`}
          title={aiEnabled ? 'Modo Assistido' : 'Modo Manual'}
        >
          {aiEnabled ? <Sparkles size={12} /> : <Edit3 size={12} />}
          <span className="status-label">{aiEnabled ? 'Modo Assistido' : 'Modo Manual'}</span>
        </span>
      </div>
      <div className="status-bar-right">
        {user && (
          <>
            <span className="status-user" title={`Sessão de ${user.username} (${user.role})`}>
              <UserRound size={12} />
              <span className="status-user-name">{user.username}</span>
              {user.role === 'owner' && <span className="status-user-role">owner</span>}
            </span>
            <button
              type="button"
              className="status-logout-btn"
              onClick={handleLogout}
              title="Encerrar sessão"
            >
              <LogOut size={12} />
              <span className="status-label">Sair</span>
            </button>
            <span className="status-divider">|</span>
          </>
        )}
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
          <span className="status-label">Logs</span>
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
