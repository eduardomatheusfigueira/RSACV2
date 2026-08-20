/**
 * RSAC V2 — Root Application Component
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

function BackendUnavailableView({ onRetry }: { onRetry: () => void }): JSX.Element {
  const [customUrl, setCustomUrl] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  // Reconexão automática: o servidor pode simplesmente ainda não ter subido, e
  // sem isto quem deixasse a aba aberta esperando continuaria nesta tela mesmo
  // depois de ele voltar.
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
      // Confirmação nomeando o host antes de apontar o app para outro
      // servidor (doc 29 §29.12). Validar o formato não basta: o endereço
      // pode ser válido e hostil, e é para ele que a senha digitada em
      // seguida vai. `StatusBar` e o caminho do `?api_url=` já confirmam;
      // aqui a etapa faltava.
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

  if (phase === 'checking') {
    // A splash do index.html continua na tela até a aplicação montar; devolver
    // um fragmento vazio aqui a mantém visível enquanto se decide.
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
