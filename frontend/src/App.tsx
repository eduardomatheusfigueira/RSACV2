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
import { InsightsPage } from '@/pages/InsightsPage'
import { ExportPage } from '@/pages/ExportPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { LoginPage } from '@/pages/LoginPage'
import { Toaster } from '@/components/ui'
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
 *
 * Antes, o parâmetro era aceito em silêncio e gravado para sempre: um link
 * como `https://rsac.netlify.app/#/?api_url=https://backend.attacker` carregava
 * a interface real, com o certificado real, e mandava toda requisição seguinte
 * — inclusive as chaves digitadas — para o servidor do atacante.
 *
 * O que fecha isso não é validar o endereço, e sim **nomear o host** para uma
 * pessoa antes que qualquer requisição saia: é a única informação capaz de
 * distinguir o link legítimo do hostil, e o usuário foi treinado pelo próprio
 * lançador a clicar em links do RSAC com `api_url` embutido.
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

  // Mesma origem da página: é o próprio backend que serviu a interface, não há
  // terceiro para confirmar.
  if (typeof window !== 'undefined' && destino.origem === window.location.origin) {
    api.setBaseUrl(destino.url)
    return
  }

  if (window.confirm(mensagemDeConfirmacao(destino))) {
    api.setBaseUrl(destino.url)
  }
}

/**
 * Portão de autenticação.
 *
 * Fica entre o health check e as rotas: enquanto a fase é `checking` não se
 * mostra nem login nem conteúdo, porque qualquer um dos dois piscaria para
 * metade dos usuários. `unavailable` é distinto de `anonymous` de propósito —
 * pedir a senha contra um backend fora do ar faria o usuário concluir que a
 * senha está errada.
 */
function AuthGate({ children }: { children: React.ReactNode }): JSX.Element {
  const { phase, bootstrap, markAnonymous } = useAuthStore()

  useEffect(() => {
    // A detecção de porta precisa vir antes da primeira chamada: os efeitos
    // dos filhos rodam antes dos do pai, então deixar isso só no AppContent
    // faria o bootstrap consultar o endereço errado no Electron.
    api.detectPort()
    aplicarApiUrlDaLocalizacao()
    api.setUnauthorizedHandler(markAnonymous)
    void bootstrap()
    return () => api.setUnauthorizedHandler(null)
  }, [])

  if (phase === 'checking' || phase === 'unavailable') {
    // A splash do index.html continua na tela até a aplicação montar; devolver
    // um fragmento vazio aqui a mantém visível enquanto se decide.
    return <></>
  }

  if (phase === 'anonymous') {
    return <LoginPage />
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
    <AuthGate>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:id" element={<ProjectRedirect />} />
          <Route path="/projects/:id/protocol" element={<ProtocolPage />} />
          <Route path="/projects/:id/harvest" element={<HarvestPage />} />
          <Route path="/projects/:id/screening" element={<ScreeningPage />} />
          <Route path="/projects/:id/extraction" element={<ExtractionPage />} />
          <Route path="/projects/:id/insights" element={<InsightsPage />} />
          <Route path="/projects/:id/export" element={<ExportPage />} />
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
        <AppContent />
        <Toaster />
      </HashRouter>
    </QueryClientProvider>
  )
}
