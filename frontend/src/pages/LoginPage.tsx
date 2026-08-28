/**
 * RSAC V2 — Tela de Acesso
 *
 * A porta que o modo servidor não tinha. Aparece apenas quando o backend
 * reporta que não há sessão válida — no app de mesa o token local resolve
 * antes, e esta tela nunca chega a ser vista.
 */

import { useEffect, useRef, useState } from 'react'
import { AlertCircle, ChevronDown, KeyRound, LogIn, ShieldCheck, User } from 'lucide-react'
import { Button, FormGroup, Input } from '@/components/ui'
import { RsacLockup } from '@/components/brand/RsacLockup'
import { useAuthStore } from '@/stores/useAuthStore'
import { api } from '@/api/client'
import { analisarUrlDeBackend, mensagemDeConfirmacao } from '@/api/backendUrl'
import './LoginPage.css'

/**
 * O "G" do Google, em SVG inline.
 *
 * As diretrizes de marca do Google exigem o logotipo em quatro cores sobre
 * fundo branco ou o monocromático sobre escuro. Inline por decisão de
 * privacidade: buscá-lo de `google.com` entregaria o IP de quem abre a tela de
 * login ao Google antes mesmo de a pessoa decidir entrar com Google.
 */
function GoogleG(): JSX.Element {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  )
}

export function LoginPage(): JSX.Element {
  const { login, error, submitting, status, setError } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const usuarioRef = useRef<HTMLInputElement>(null)
  const comGoogle = status?.google_login_enabled === true
  // Com o Google disponível, a senha fica recolhida: é a via de exceção
  // (acesso de emergência do administrador), não a porta principal.
  const [mostrarSenha, setMostrarSenha] = useState(!comGoogle)

  useEffect(() => {
    if (mostrarSenha) usuarioRef.current?.focus()
  }, [mostrarSenha])

  useEffect(() => {
    setMostrarSenha(!comGoogle)
  }, [comGoogle])

  // O callback do OAuth devolve o navegador com o motivo na query quando algo
  // dá errado. Traduzir aqui — e não no backend — mantém a mensagem no idioma
  // da interface e evita que o servidor devolva texto para a tela.
  useEffect(() => {
    const motivo = new URLSearchParams(window.location.search).get('erro')
    if (!motivo) return
    const mensagens: Record<string, string> = {
      cancelado: 'Entrada cancelada no Google.',
      estado_invalido: 'O pedido de entrada expirou. Tente novamente.',
      recusado:
        'O Google não confirmou este e-mail. Verifique o endereço na sua conta Google e tente de novo.',
      indisponivel: 'A entrada com Google não está disponível neste servidor.',
      nao_admitido: 'Esta conta Google não está autorizada neste servidor.',
      conta_inativa: 'Esta conta está desativada. Procure quem administra o servidor.',
    }
    setError(mensagens[motivo] ?? 'Não foi possível concluir a entrada.')
    window.history.replaceState({}, '', window.location.pathname)
  }, [setError])

  const semContas = status?.has_accounts === false

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) {
      setError('Informe usuário e senha.')
      return
    }
    await login(username.trim(), password)
    setPassword('')
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <RsacLockup size="lg" />
        </div>

        <h1 className="login-title">Acesso ao ambiente de revisão</h1>
        <p className="login-subtitle">
          Este servidor exige identificação. Suas credenciais protegem os projetos, os dados
          coletados e as chaves de API configuradas.
        </p>

        {semContas ? (
          /*
           * Instalação sem conta nenhuma. Provisionar pela interface seria
           * abrir um "criar o primeiro administrador" na internet — que é
           * exatamente o buraco que esta fase fecha. O caminho é o terminal.
           */
          <div className="login-alert login-alert--info" role="status">
            <ShieldCheck size={18} />
            <div>
              <strong>Nenhuma conta provisionada</strong>
              <p>
                Crie a primeira conta no computador que hospeda o servidor:
                <code>python -m app.cli create-user seu_usuario --role owner</code>
                A senha é exibida uma única vez no terminal.
              </p>
            </div>
          </div>
        ) : (
          <>
            {error && !mostrarSenha && (
              <div className="login-alert login-alert--error" role="alert">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            {comGoogle && (
              <div className="login-oauth">
                <a className="login-google" href={api.googleLoginUrl()}>
                  <GoogleG />
                  <span>Entrar com Google</span>
                </a>
                {!mostrarSenha && (
                  <button
                    type="button"
                    className="login-outras-vias"
                    onClick={() => setMostrarSenha(true)}
                  >
                    <ChevronDown size={14} />
                    Outras formas de entrar
                  </button>
                )}
              </div>
            )}

            {mostrarSenha && (
          <form className="login-form" onSubmit={handleSubmit}>
            <FormGroup label="Usuário" htmlFor="login-usuario">
              <Input
                id="login-usuario"
                ref={usuarioRef}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                placeholder="seu_usuario"
                leftIcon={<User size={15} />}
                disabled={submitting}
              />
            </FormGroup>

            <FormGroup label="Senha" htmlFor="login-senha">
              <Input
                id="login-senha"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                placeholder="••••••••••••"
                leftIcon={<KeyRound size={15} />}
                disabled={submitting}
              />
            </FormGroup>

            {error && (
              <div className="login-alert login-alert--error" role="alert">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={submitting}
              leftIcon={<LogIn size={16} />}
              className="login-submit"
            >
              {submitting ? 'Entrando…' : 'Entrar'}
            </Button>
          </form>
            )}
          </>
        )}

        <div className="login-server-info" style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.08)', fontSize: '0.8rem', color: '#94a3b8', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
          <span>Servidor: <strong style={{ color: '#cbd8e4' }}>{api.getBackendHost()}</strong></span>
          <button
            type="button"
            onClick={() => {
              const current = api.getBaseUrl().replace(/\/api\/v1\/?$/, '')
              const input = window.prompt(
                'Configurar URL do Backend / Túnel (ex: https://seu-tunnel.trycloudflare.com ou http://127.0.0.1:8000):',
                current
              )
              if (!input || !input.trim()) return
              try {
                const destino = analisarUrlDeBackend(input)
                // Confirmação nomeando o host (doc 29 §29.12). É desta tela
                // que sai a senha do usuário: trocar o destino sem ver para
                // onde ela vai é justamente o que a Fase 4 fechou.
                if (!window.confirm(mensagemDeConfirmacao(destino))) return
                api.setBaseUrl(destino.url)
                window.location.reload()
              } catch (err: any) {
                window.alert(err?.message ?? 'Endereço inválido.')
              }
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#38bdf8',
              textDecoration: 'underline',
              cursor: 'pointer',
              fontSize: '0.8rem',
              padding: 0
            }}
          >
            Alterar URL do Servidor
          </button>
        </div>

        {status?.deployment_profile === 'server' && (
          <p className="login-footnote">
            Servidor publicado — não compartilhe o endereço nem suas credenciais.
          </p>
        )}
      </div>
    </div>
  )
}
