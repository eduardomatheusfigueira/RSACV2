/**
 * RSAC V2 — Root Application Component
 * Configura roteamento, TanStack Query e inicializa conexão com backend.
 */

import { useEffect } from 'react'
import { HashRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { DashboardPage } from '@/pages/DashboardPage'
import { ProjectsPage } from '@/pages/ProjectsPage'
import { ProtocolPage } from '@/pages/ProtocolPage'
import { ScreeningPage } from '@/pages/ScreeningPage'
import { HarvestPage } from '@/pages/HarvestPage'
import { ExtractionPage } from '@/pages/ExtractionPage'
import { ExportPage } from '@/pages/ExportPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { Toaster } from '@/components/ui'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'

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
        console.log(`[App] Backend conectado na porta ${api.getPort()} — v${health.version}`)
      } catch (error) {
        if (api.getPort() !== 8000) {
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
        console.warn('[App] Backend não disponível, tentando novamente em 2s...')
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
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectRedirect />} />
        <Route path="/projects/:id/protocol" element={<ProtocolPage />} />
        <Route path="/projects/:id/harvest" element={<HarvestPage />} />
        <Route path="/projects/:id/screening" element={<ScreeningPage />} />
        <Route path="/projects/:id/extraction" element={<ExtractionPage />} />
        <Route path="/projects/:id/export" element={<ExportPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export function App(): JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <AppContent />
        <Toaster />
      </HashRouter>
    </QueryClientProvider>
  )
}
