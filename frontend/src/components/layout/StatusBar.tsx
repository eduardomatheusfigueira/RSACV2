/**
 * RSAC V2 — StatusBar Component
 * Barra de status inferior com indicadores de backend, modo de IA e versão.
 */

import { useSettingsStore } from '@/stores/useSettingsStore'
import { useLogStore } from '@/stores/useLogStore'
import { useAuthStore } from '@/stores/useAuthStore'
import { Sparkles, Edit3, Terminal, AlertCircle, LogOut, UserRound } from 'lucide-react'
import { RsacMark } from '@/components/brand/RsacMark'
import { BetaBadge } from '@/components/brand/BetaBadge'
import { api } from '@/api/client'
import { analisarUrlDeBackend, mensagemDeConfirmacao } from '@/api/backendUrl'
import './StatusBar.css'

export function StatusBar(): JSX.Element {
  const { backendStatus, backendVersion, aiEnabled } = useSettingsStore()
  const { entries, panelOpen, togglePanel } = useLogStore()
  const { user, logout } = useAuthStore()

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
    if (!input || !input.trim()) return

    // Mesma validação e mesma confirmação do link com `api_url`: trocar o
    // servidor pela barra de status é a mesma decisão, e mudar de destino sem
    // ver o host é o que a Fase 4 fecha (doc 29 §29.12).
    let destino
    try {
      destino = analisarUrlDeBackend(input)
    } catch (err: any) {
      window.alert(err?.message ?? 'Endereço de servidor inválido.')
      return
    }

    if (!window.confirm(mensagemDeConfirmacao(destino))) return

    api.setBaseUrl(destino.url)
    window.location.reload()
  }

  const handleLogout = async () => {
    if (!window.confirm('Encerrar a sessão? Você precisará entrar novamente.')) return
    await logout()
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
          {/* O host fica permanentemente visível: é o que permite perceber
              que a interface está falando com outro servidor (doc 29 §29.12). */}
          <span className="status-backend-host">{api.getBackendHost()}</span>
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
        {user && (
          <>
            {/* Quem está operando fica visível o tempo todo: num servidor
                compartilhado, a autoria das decisões de triagem depende de a
                pessoa saber com qual conta está trabalhando. */}
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
              <span>Sair</span>
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
