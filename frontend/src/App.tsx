/**
 * Revsist — Root Application Component
 * Configura roteamento, TanStack Query e inicializa conexão com backend.
 */

import { useEffect, useState } from 'react'
import { HashRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { DashboardPage } from '@/pages/DashboardPage'
import { ProjectsPage } from '@/pages/ProjectsPage'
import { ProtocolPage } from '@/pages/ProtocolPage'
import { ScreeningPage } from '@/pages/ScreeningPage'
import { HarvestPage } from '@/pages/HarvestPage'
import { ExtractionPage } from '@/pages/ExtractionPage'
import { InsightsPage } from '@/pages/InsightsPage'
import { ExportPage } from '@/pages/ExportPage'
import { SettingsPage } from '@/pages/SettingsPage'
import TeamPage from '@/pages/TeamPage'
import { LoginPage } from '@/pages/LoginPage'
import { ErrorBoundary, Toaster } from '@/components/ui'
import { api } from '@/api/client'
import {
  analisarUrlDeBackend,
  extrairApiUrlDaLocalizacao,
  mensagemDeConfirmacao,
} from '@/api/backendUrl'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useAuthStore } from '@/stores/useAuthStore'

// TanStack Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})

function ProjectRedirect(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  return <Navigate to={`/projects/${id}/protocol`} replace />
}

/**
 * Trata `?api_url=` com confirmação humana explícita (doc 29 §29.12).
 */
function aplicarApiUrlDaLocalizacao(): void {
  const bruto = extrairApiUrlDaLocalizacao()
  if (!bruto) return

  let destino
  try {
    destino = analisarUrlDeBackend(bruto)
  } catch (err: any) {
    window.alert(
      `O link usado aponta para um endereço de servidor inválido e foi ignorado.\n\n${err?.message ?? ''}`
    )
    return
  }

  if (typeof window !== 'undefined' && destino.origem === window.location.origin) {
    api.setBaseUrl(destino.url)
    return
  }

  if (window.confirm(mensagemDeConfirmacao(destino))) {
    api.setBaseUrl(destino.url)
  }
}

function BackendUnavailableView({ onRetry }: { onRetry: () => void }): JSX.Element {
  useEffect(() => {
    const id = window.setInterval(onRetry, 4000)
    return () => window.clearInterval(id)
  }, [onRetry])

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '1.25rem',
        background: 'linear-gradient(160deg, #101c2c 0%, #080e18 100%)',
        color: '#f8fafc',
        fontFamily: 'Inter, system-ui, sans-serif',
        padding: '2rem',
        textAlign: 'center',
        zIndex: 10000,
      }}
    >
      <div
        style={{
          maxWidth: '480px',
          width: '100%',
          background: '#132235',
          border: '1px solid #233b58',
          borderRadius: '12px',
          padding: '2.5rem 2rem',
          boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '1.25rem',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
          <h2 style={{ color: '#38bdf8', margin: 0, fontSize: '1.35rem', fontWeight: 600 }}>
            Conectando aos Serviços
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.6, margin: 0 }}>
            Aguardando resposta do servidor Revsist. A conexão será restabelecida automaticamente assim que o servidor estiver disponível.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginTop: '0.5rem' }}>
          <button
            onClick={() => onRetry()}
            style={{
              padding: '0.65rem 1.5rem',
              background: '#2563eb',
              border: 'none',
              borderRadius: '6px',
              color: '#ffffff',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'background 0.2s ease',
            }}
          >
            🔄 Tentar Novamente
          </button>
        </div>
      </div>
    </div>
  )
}

/**

 * Portão de autenticação.
 */
function AuthGate({ children }: { children: React.ReactNode }): JSX.Element {
  const { phase, bootstrap, markAnonymous } = useAuthStore()

  useEffect(() => {
    api.detectPort()
    aplicarApiUrlDaLocalizacao()
    api.setUnauthorizedHandler(markAnonymous)
    void bootstrap()
    return () => api.setUnauthorizedHandler(null)
  }, [])

  if (phase === 'checking') {
    return <></>
  }

  if (phase === 'unavailable') {
    return <BackendUnavailableView onRetry={() => void bootstrap()} />
  }

  if (phase === 'anonymous') {
    return <LoginPage />
  }

  return <>{children}</>
}

function ProjectRouteGuard({ children }: { children: React.ReactNode }): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const { setActiveProject } = useSettingsStore()
  const [checking, setChecking] = useState(true)
  const [authorized, setAuthorized] = useState(false)

  useEffect(() => {
    let cancel = false
    const checkAccess = async () => {
      if (!id) {
        setActiveProject(null)
        setAuthorized(false)
        setChecking(false)
        return
      }

      try {
        const proj = await api.getProject(id)
        if (cancel) return
        setActiveProject(proj)
        setAuthorized(true)
      } catch (err) {
        if (cancel) return
        console.warn(`[ProjectGuard] Projeto ${id} inacessível ou inexistente:`, err)
        setActiveProject(null)
        setAuthorized(false)
      } finally {
        if (!cancel) setChecking(false)
      }
    }

    void checkAccess()
    return () => {
      cancel = true
    }
  }, [id])

  if (checking) {
    return <div className="animate-fade-in" style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>Carregando projeto…</div>
  }

  if (!authorized) {
    return <Navigate to="/projects" replace />
  }

  return <>{children}</>
}

function AppContent(): JSX.Element {
  const { setBackendStatus, setBackendVersion, theme, setTheme } = useSettingsStore()

  useEffect(() => {
    // Detectar porta do backend passada via query string pelo Electron
    api.detectPort()

    // Aplicar o tema persistido (do localStorage) ao DOM sem forçar override
    document.documentElement.setAttribute('data-theme', theme)

    // Health check — verificar conexão com backend
    const checkHealth = async () => {
      try {
        const health = await api.health()
        setBackendStatus('online')
        setBackendVersion(health.version)
        console.log(`[App] Backend conectado: ${api.getBaseUrl()} — v${health.version}`)
      } catch (error) {
        const envUrl = (import.meta as any).env?.VITE_API_URL
        if (!envUrl && api.getPort() !== 8000) {
          console.warn(`[App] Backend não respondeu na porta ${api.getPort()}, tentando porta padrão 8000...`)
          api.setPort(8000)
          try {
            const health = await api.health()
            setBackendStatus('online')
            setBackendVersion(health.version)
            console.log(`[App] Backend conectado na porta 8000 — v${health.version}`)
            return
          } catch {
            // Continua
          }
        }
        setBackendStatus('connecting')
        // Retry após 2 segundos
        setTimeout(checkHealth, 2000)
      }
    }

    checkHealth()

    // Detectar mudanças de tema do sistema (via Electron IPC)
    if (window.rsacAPI?.onThemeChanged) {
      window.rsacAPI.onThemeChanged((theme) => {
        setTheme(theme)
      })
    }
  }, [])

  return (
    <AuthGate>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:id" element={<ProjectRedirect />} />
          <Route
            path="/projects/:id/protocol"
            element={
              <ProjectRouteGuard>
                <ProtocolPage />
              </ProjectRouteGuard>
            }
          />
          <Route
            path="/projects/:id/harvest"
            element={
              <ProjectRouteGuard>
                <HarvestPage />
              </ProjectRouteGuard>
            }
          />
          <Route
            path="/projects/:id/screening"
            element={
              <ProjectRouteGuard>
                <ScreeningPage />
              </ProjectRouteGuard>
            }
          />
          <Route
            path="/projects/:id/extraction"
            element={
              <ProjectRouteGuard>
                <ExtractionPage />
              </ProjectRouteGuard>
            }
          />
          <Route
            path="/projects/:id/insights"
            element={
              <ProjectRouteGuard>
                <InsightsPage />
              </ProjectRouteGuard>
            }
          />
          <Route
            path="/projects/:id/export"
            element={
              <ProjectRouteGuard>
                <ExportPage />
              </ProjectRouteGuard>
            }
          />
          <Route
            path="/projects/:id/team"
            element={
              <ProjectRouteGuard>
                <TeamPage />
              </ProjectRouteGuard>
            }
          />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AuthGate>
  )
}

export function App(): JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <ErrorBoundary fallbackTitle="Erro na aplicação">
          <AppContent />
        </ErrorBoundary>
        <Toaster />
      </HashRouter>
    </QueryClientProvider>
  )
}
