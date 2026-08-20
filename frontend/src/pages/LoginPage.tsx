/**
 * RSAC V2 — Tela de Acesso
 *
 * A porta que o modo servidor não tinha. Aparece apenas quando o backend
 * reporta que não há sessão válida — no app de mesa o token local resolve
 * antes, e esta tela nunca chega a ser vista.
 */

import { useEffect, useRef, useState } from 'react'
import { AlertCircle, KeyRound, LogIn, ShieldCheck, User } from 'lucide-react'
import { Button, FormGroup, Input } from '@/components/ui'
import { RsacLockup } from '@/components/brand/RsacLockup'
import { useAuthStore } from '@/stores/useAuthStore'
import { api } from '@/api/client'
import { analisarUrlDeBackend, mensagemDeConfirmacao } from '@/api/backendUrl'
import './LoginPage.css'

export function LoginPage(): JSX.Element {
  const { login, error, submitting, status, setError } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const usuarioRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    usuarioRef.current?.focus()
  }, [])

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
