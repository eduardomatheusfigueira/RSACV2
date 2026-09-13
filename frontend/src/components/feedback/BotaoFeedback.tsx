/**
 * Revsist — Botão de feedback do beta.
 *
 * Fica no canto inferior direito de todas as telas do aplicativo, logo acima
 * da barra de status. Abre uma janela curta: o tipo (problema, sugestão,
 * elogio, outro), a mensagem e o envio. O que a tela e o navegador dizem sobre
 * o contexto vai junto sem ninguém precisar descrever — e a janela avisa isso
 * antes do envio, não depois.
 */

import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { CheckCircle2, MessageSquarePlus, Send } from 'lucide-react'
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitlebar,
  Textarea,
  toast,
} from '@/components/ui'
import { api } from '@/api/client'
import type { FeedbackTipo } from '@/types/api'
import { MAX_CARACTERES, MIN_CARACTERES, TIPOS_DE_FEEDBACK, tipoDeFeedback } from './tipos'
import './BotaoFeedback.css'

export function BotaoFeedback(): JSX.Element {
  const { pathname } = useLocation()
  const [aberto, setAberto] = useState(false)
  const [tipo, setTipo] = useState<FeedbackTipo>('problema')
  const [mensagem, setMensagem] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [enviado, setEnviado] = useState(false)
  const caixaRef = useRef<HTMLTextAreaElement>(null)

  // A tela registrada é a de onde a janela foi aberta, e não a que estiver
  // ativa na hora do envio: é nela que a pessoa viu o problema.
  const [pagina, setPagina] = useState(pathname)

  const abrir = () => {
    setPagina(pathname)
    setEnviado(false)
    setAberto(true)
  }

  useEffect(() => {
    if (aberto && !enviado) {
      // Depois da animação de entrada do Radix, que devolve o foco ao primeiro
      // elemento focável (o tipo) — a caixa de texto é onde se quer começar.
      const t = window.setTimeout(() => caixaRef.current?.focus(), 60)
      return () => window.clearTimeout(t)
    }
  }, [aberto, enviado])

  const texto = mensagem.trim()
  const curtoDemais = texto.length < MIN_CARACTERES
  const atual = tipoDeFeedback(tipo)

  const enviar = async () => {
    if (curtoDemais || enviando) return
    try {
      setEnviando(true)
      await api.sendFeedback({ tipo, mensagem: texto, pagina })
      setEnviado(true)
      setMensagem('')
    } catch (err: any) {
      toast.error('Não foi possível enviar o feedback', {
        description: err?.message || 'Tente de novo em instantes.',
      })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <button
        type="button"
        className="fb-botao"
        onClick={abrir}
        aria-haspopup="dialog"
        title="Enviar feedback, relatar um problema ou dar uma sugestão"
      >
        <MessageSquarePlus size={15} aria-hidden="true" />
        <span className="fb-botao__rotulo">Feedback</span>
        <span className="fb-botao__beta" aria-hidden="true">beta</span>
      </button>

      <DialogContent variant="window" size="md" className="fb-janela">
        <DialogTitlebar>Feedback do beta</DialogTitlebar>

        {enviado ? (
          <DialogBody className="fb-sucesso">
            <CheckCircle2 size={36} strokeWidth={1.5} className="fb-sucesso__icone" aria-hidden="true" />
            <p className="fb-sucesso__titulo">Recebido, obrigado!</p>
            <DialogDescription className="fb-sucesso__texto">
              Sua mensagem já chegou a quem desenvolve o Revsist. Se precisarmos de mais
              detalhes, respondemos no e-mail da sua conta.
            </DialogDescription>
            <div className="fb-sucesso__acoes">
              <Button variant="secondary" size="sm" onClick={() => setEnviado(false)}>
                Enviar outro
              </Button>
              <Button variant="primary" size="sm" onClick={() => setAberto(false)}>
                Fechar
              </Button>
            </div>
          </DialogBody>
        ) : (
          <DialogBody>
            <DialogDescription className="fb-intro">
              O Revsist está em beta. Achou um problema, teve uma ideia ou quer contar o que
              achou? Sua mensagem vai direto para quem desenvolve o aplicativo.
            </DialogDescription>

            <div className="fb-tipos" role="radiogroup" aria-label="Tipo de feedback">
              {TIPOS_DE_FEEDBACK.map((t) => {
                const Icone = t.icone
                const ativo = t.id === tipo
                return (
                  <button
                    key={t.id}
                    type="button"
                    role="radio"
                    aria-checked={ativo}
                    className={`fb-tipo fb-tipo--${t.id} ${ativo ? 'is-ativo' : ''}`}
                    onClick={() => setTipo(t.id)}
                  >
                    <Icone size={16} aria-hidden="true" />
                    {t.rotulo}
                  </button>
                )
              })}
            </div>

            <div className="fb-campo">
              <label htmlFor="fb-mensagem" className="fb-campo__rotulo">
                Sua mensagem
              </label>
              <Textarea
                id="fb-mensagem"
                ref={caixaRef}
                rows={6}
                maxLength={MAX_CARACTERES}
                placeholder={atual.convite}
                value={mensagem}
                onChange={(e) => setMensagem(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault()
                    enviar()
                  }
                }}
              />
              <div className="fb-campo__rodape">
                <span>Ctrl + Enter envia</span>
                <span className={mensagem.length > MAX_CARACTERES * 0.9 ? 'fb-contador--alto' : ''}>
                  {mensagem.length.toLocaleString('pt-BR')} / {MAX_CARACTERES.toLocaleString('pt-BR')}
                </span>
              </div>
            </div>

            <p className="fb-contexto">
              Junto com a mensagem vão a tela em que você está (<code>{pagina || '/'}</code>), a
              versão do aplicativo e o navegador. Seu nome e e-mail vêm da sua conta, para podermos
              responder.
            </p>

            <DialogFooter>
              <Button variant="ghost" size="sm" onClick={() => setAberto(false)}>
                Cancelar
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={enviar}
                loading={enviando}
                disabled={curtoDemais}
                leftIcon={<Send size={13} />}
                title={curtoDemais ? `Escreva pelo menos ${MIN_CARACTERES} caracteres` : undefined}
              >
                Enviar feedback
              </Button>
            </DialogFooter>
          </DialogBody>
        )}
      </DialogContent>
    </Dialog>
  )
}
