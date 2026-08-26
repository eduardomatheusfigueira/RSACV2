/**
 * RSAC V2 — Root Application Component
 * Configura roteamento, TanStack Query e inicializa conexão com backend.
 */

import { lazy, Suspense, useEffect, useState } from 'react'
import { HashRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { LoginPage } from '@/pages/LoginPage'
import { Toaster } from '@/components/ui'
import { api } from '@/api/client'
import {
  analisarUrlDeBackend,
  extrairApiUrlDaLocalizacao,
  mensagemDeConfirmacao,
} from '@/api/backendUrl'
import { atualizarStatusDoSplash, dispensarBootSplash } from '@/bootSplash'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useAuthStore } from '@/stores/useAuthStore'

/*
 * As telas de trabalho entram por importação dinâmica.
 *
 * Estáticas, as nove somavam um pacote único de ~1,1 MB que o navegador
 * precisava baixar, analisar e executar inteiro antes de desenhar a primeira
 * tela — incluindo a biblioteca de gráficos, que só a aba de Indicadores usa,
 * e as três páginas maiores do produto, que quem abre o app no Painel não vê.
 * Agora cada aba chega quando é aberta, e a primeira pintura carrega o que
 * cabe nela.
 *
 * `LoginPage` fica estática de propósito: é uma das duas primeiras telas
 * possíveis, e adiar seu código só acrescentaria um piscar à entrada.
 */
const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage }))
)
const ProjectsPage = lazy(() =>
  import('@/pages/ProjectsPage').then((m) => ({ default: m.ProjectsPage }))
)
const ProtocolPage = lazy(() =>
  import('@/pages/ProtocolPage').then((m) => ({ default: m.ProtocolPage }))
)
const ScreeningPage = lazy(() =>
  import('@/pages/ScreeningPage').then((m) => ({ default: m.ScreeningPage }))
)
const HarvestPage = lazy(() =>
  import('@/pages/HarvestPage').then((m) => ({ default: m.HarvestPage }))
)
const ExtractionPage = lazy(() =>
  import('@/pages/ExtractionPage').then((m) => ({ default: m.ExtractionPage }))
)
const InsightsPage = lazy(() =>
  import('@/pages/InsightsPage').then((m) => ({ default: m.InsightsPage }))
)
const ExportPage = lazy(() =>
  import('@/pages/ExportPage').then((m) => ({ default: m.ExportPage }))
)
const SettingsPage = lazy(() =>
  import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage }))
)

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
  const [customUrl, setCustomUrl] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const id = window.setInterval(onRetry, 5000)
    return () => window.clearInterval(id)
  }, [onRetry])

  const handleConnect = (targetUrl: string) => {
    setErrorMsg('')
    const trimmed = targetUrl.trim()
    if (!trimmed) {
      setErrorMsg('Informe uma URL de servidor ou túnel.')
      return
    }
    try {
      const destino = analisarUrlDeBackend(trimmed)
      if (!window.confirm(mensagemDeConfirmacao(destino))) return
      api.setBaseUrl(destino.url)
      onRetry()
    } catch (err: any) {
      setErrorMsg(err?.message || 'URL inválida.')
    }
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1.25rem',
      background: 'linear-gradient(160deg, #1a3350 0%, #0d1b2a 100%)',
      color: '#f8fafc',
      fontFamily: 'Inter, system-ui, sans-serif',
      padding: '2rem',
      textAlign: 'center',
      zIndex: 10000
    }}>
      <div style={{
        maxWidth: '540px',
        width: '100%',
        background: '#132438',
        border: '1px solid #234164',
        borderRadius: '12px',
        padding: '2rem',
        boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <h2 style={{ color: '#38bdf8', margin: 0, fontSize: '1.4rem' }}>Conectar ao Servidor Backend</h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.5, margin: 0 }}>
            Não foi possível conectar ao endereço atual (<code>{api.getBackendHost()}</code>). Cole o endereço do seu servidor local ou túnel Cloudflare abaixo:
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', textAlign: 'left' }}>
          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#cbd8e4' }}>
            URL do Backend / Túnel Cloudflare:
          </label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              placeholder="Ex: https://seu-tunel.trycloudflare.com ou http://localhost:8000"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleConnect(customUrl)}
              style={{
                flex: 1,
                padding: '0.7rem 1rem',
                background: '#0d1b2a',
                border: '1px solid #335377',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '0.9rem',
                outline: 'none'
              }}
            />
            <button
              onClick={() => handleConnect(customUrl)}
              style={{
                padding: '0.7rem 1.25rem',
                background: '#2563eb',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              Conectar
            </button>
          </div>
          {errorMsg && (
            <span style={{ color: '#f87171', fontSize: '0.8rem' }}>{errorMsg}</span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ flex: 1, height: '1px', background: '#234164' }} />
          <span style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase' }}>ou escolha um atalho</span>
          <div style={{ flex: 1, height: '1px', background: '#234164' }} />
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => handleConnect('http://127.0.0.1:8000')}
            style={{
              padding: '0.6rem 1rem',
              background: '#1e3a5f',
              border: '1px solid #3b6294',
              borderRadius: '6px',
              color: '#e2e8f0',
              fontSize: '0.85rem',
              cursor: 'pointer'
            }}
          >
            💻 Usar Localhost (127.0.0.1:8000)
          </button>
          <button
            onClick={() => onRetry()}
            style={{
              padding: '0.6rem 1rem',
              background: '#334155',
              border: '1px solid #475569',
              borderRadius: '6px',
              color: '#e2e8f0',
              fontSize: '0.85rem',
              cursor: 'pointer'
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
 * Descobre onde está o backend antes da primeira chamada da API.
 *
 * No app de mesa quem sabe a porta é o processo principal — ela é sorteada a
 * cada execução —, e ele só responde quando o Python passa no health check.
 * Aguardar essa resposta é o que substitui a antiga tentativa às cegas na
 * porta 8000, que só se corrigia depois de falhar e entrar em repetição.
 *
 * Na web e em desenvolvimento a ponte não existe, e vale o que sempre valeu:
 * a porta vem da query string, ou a origem da própria página é o backend.
 */
async function resolverBackendLocal(): Promise<void> {
  api.detectPort()

  const ponte = window.rsacAPI?.getBackendInfo
  if (typeof ponte !== 'function') return

  atualizarStatusDoSplash('Iniciando o servidor local')
  try {
    const info = await window.rsacAPI.getBackendInfo()
    if (info?.porta) api.setPort(info.porta)
    if (info?.tokenLocal) useAuthStore.getState().definirTokenLocal(info.tokenLocal)
  } catch (err) {
    console.warn('[App] Não foi possível obter a porta do backend local:', err)
  }
}

/**
 * Portão de autenticação.
 */
function AuthGate({ children }: { children: React.ReactNode }): JSX.Element {
  const { phase, bootstrap, markAnonymous } = useAuthStore()

  useEffect(() => {
    api.setUnauthorizedHandler(markAnonymous)
    void (async () => {
      await resolverBackendLocal()
      aplicarApiUrlDaLocalizacao()
      atualizarStatusDoSplash('Preparando o ambiente de revisão')
      await bootstrap()
    })()
    return () => api.setUnauthorizedHandler(null)
  }, [])

  // A splash de marca cobre a espera; sai quando há tela de verdade a mostrar.
  useEffect(() => {
    if (phase !== 'checking') dispensarBootSplash()
  }, [phase])

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

function AppContent(): JSX.Element {
  const { setBackendStatus, setBackendVersion, theme, setTheme } = useSettingsStore()

  useEffect(() => {
    // Aplicar o tema persistido (do localStorage) ao DOM sem forçar override
    document.documentElement.setAttribute('data-theme', theme)

    let cancelado = false
    let proximaTentativa: number | undefined

    /*
     * Health check para o indicador da barra de estado.
     *
     * A porta já foi resolvida pelo `AuthGate` (ver `resolverBackendLocal`),
     * então a repetição aqui é só para a queda do backend em uso — não é mais
     * o mecanismo que descobre onde ele está. O recuo cego para a 8000 saiu
     * junto: com a porta sorteada a cada execução, ele acertava por acaso e,
     * quando errava, apontava o diagnóstico para o endereço errado.
     */
    const verificarSaude = async () => {
      if (cancelado) return
      try {
        const health = await api.health()
        setBackendStatus('online')
        setBackendVersion(health.version)
        console.log(`[App] Backend conectado: ${api.getBaseUrl()} — v${health.version}`)
      } catch {
        setBackendStatus('connecting')
        proximaTentativa = window.setTimeout(verificarSaude, 2000)
      }
    }

    void verificarSaude()

    // Detectar mudanças de tema do sistema (via Electron IPC)
    if (window.rsacAPI?.onThemeChanged) {
      window.rsacAPI.onThemeChanged((theme) => {
        setTheme(theme)
      })
    }

    return () => {
      cancelado = true
      if (proximaTentativa) window.clearTimeout(proximaTentativa)
    }
  }, [])

  return (
    <AuthGate>
      {/*
        O `fallback` é vazio de propósito: o AppShell (faixa superior, painel de
        log, barra de estado) permanece montado enquanto o pedaço da aba chega,
        e uma tela de carregamento sobre ele piscaria a cada troca de aba num
        carregamento que, vindo do disco, dura poucos quadros.
      */}
      <Suspense fallback={<></>}>
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
      </Suspense>
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
