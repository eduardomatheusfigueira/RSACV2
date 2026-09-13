/**
 * Revsist — Fila de feedback do beta, no painel de administração.
 *
 * Cartões, e não tabela: um feedback é texto corrido — às vezes um passo a
 * passo inteiro —, e numa célula de tabela ele vira reticências. Cada cartão
 * mostra quem escreveu, de que tela, a mensagem inteira e a situação, que o
 * dono muda num clique.
 */

import { useEffect, useState } from 'react'
import { Archive, CheckCircle2, Clock, Inbox, Mail, MonitorSmartphone, RefreshCw, Trash2, Undo2 } from 'lucide-react'
import { Badge, Button, EmptyState, toast } from '@/components/ui'
import { api } from '@/api/client'
import type { FeedbackItem, FeedbackStatus } from '@/types/api'
import { SITUACOES_DE_FEEDBACK, tipoDeFeedback } from './tipos'
import './PainelFeedback.css'

type Filtro = FeedbackStatus | 'todos'

const FILTROS: { id: Filtro; rotulo: string }[] = [
  { id: 'novo', rotulo: 'Novos' },
  { id: 'em_andamento', rotulo: 'Em andamento' },
  { id: 'resolvido', rotulo: 'Resolvidos' },
  { id: 'arquivado', rotulo: 'Arquivados' },
  { id: 'todos', rotulo: 'Todos' },
]

const dataHora = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

export function PainelFeedback({
  onContagem,
}: {
  /** Avisa quantos feedbacks novos há, para o selo da aba. */
  onContagem?: (novos: number) => void
}): JSX.Element {
  const [itens, setItens] = useState<FeedbackItem[]>([])
  const [carregando, setCarregando] = useState(false)
  const [filtro, setFiltro] = useState<Filtro>('novo')
  const [ocupado, setOcupado] = useState<string | null>(null)
  const [notas, setNotas] = useState<Record<string, string>>({})

  const carregar = async () => {
    try {
      setCarregando(true)
      const res = await api.listFeedback()
      setItens(res.items || [])
      onContagem?.(res.novos || 0)
    } catch (err: any) {
      toast.error('Falha ao carregar o feedback', { description: err.message })
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const substituir = (atualizado: FeedbackItem) => {
    const proximos = itens.map((i) => (i.id === atualizado.id ? atualizado : i))
    setItens(proximos)
    onContagem?.(proximos.filter((i) => i.status === 'novo').length)
  }

  const mudarSituacao = async (item: FeedbackItem, status: FeedbackStatus) => {
    try {
      setOcupado(item.id)
      substituir(await api.updateFeedback(item.id, { status }))
    } catch (err: any) {
      toast.error('Falha ao atualizar o feedback', { description: err.message })
    } finally {
      setOcupado(null)
    }
  }

  const salvarNota = async (item: FeedbackItem) => {
    const texto = (notas[item.id] ?? item.admin_notes).trim()
    if (texto === item.admin_notes.trim()) return
    try {
      setOcupado(item.id)
      substituir(await api.updateFeedback(item.id, { admin_notes: texto }))
      setNotas((n) => {
        const resto = { ...n }
        delete resto[item.id]
        return resto
      })
      toast.success('Anotação salva')
    } catch (err: any) {
      toast.error('Falha ao salvar a anotação', { description: err.message })
    } finally {
      setOcupado(null)
    }
  }

  const excluir = async (item: FeedbackItem) => {
    if (!window.confirm(`Excluir definitivamente este feedback de ${item.autor_nome || item.autor_usuario}?`)) {
      return
    }
    try {
      setOcupado(item.id)
      await api.deleteFeedback(item.id)
      const proximos = itens.filter((i) => i.id !== item.id)
      setItens(proximos)
      onContagem?.(proximos.filter((i) => i.status === 'novo').length)
      toast.success('Feedback excluído')
    } catch (err: any) {
      toast.error('Falha ao excluir o feedback', { description: err.message })
    } finally {
      setOcupado(null)
    }
  }

  const contagem = (f: Filtro) => (f === 'todos' ? itens.length : itens.filter((i) => i.status === f).length)
  const visiveis = filtro === 'todos' ? itens : itens.filter((i) => i.status === filtro)

  return (
    <div className="admin-panel pf">
      <div className="admin-toolbar">
        <h4 className="admin-table-title">Feedback enviado pelo botão do beta</h4>
        <div className="admin-toolbar-actions">
          <button type="button" className="btn-text-action" onClick={carregar} disabled={carregando}>
            <RefreshCw size={12} className={carregando ? 'animate-spin' : ''} /> Atualizar
          </button>
        </div>
      </div>

      <div className="pf-filtros" role="tablist" aria-label="Filtrar por situação">
        {FILTROS.map((f) => (
          <button
            key={f.id}
            type="button"
            role="tab"
            aria-selected={filtro === f.id}
            className={`pf-filtro ${filtro === f.id ? 'is-ativo' : ''}`}
            onClick={() => setFiltro(f.id)}
          >
            {f.rotulo} <span className="pf-filtro__n">{contagem(f.id)}</span>
          </button>
        ))}
      </div>

      {visiveis.length === 0 ? (
        <EmptyState
          size="inline"
          icon={<Inbox size={22} strokeWidth={1.25} aria-hidden="true" />}
          title={filtro === 'novo' ? 'Nenhum feedback novo' : 'Nada nesta situação'}
          description="Quem usa o aplicativo envia feedback pelo botão do canto inferior direito. Cada envio chega aqui e no seu e-mail."
        />
      ) : (
        <ul className="pf-lista">
          {visiveis.map((item) => {
            const tipo = tipoDeFeedback(item.tipo)
            const Icone = tipo.icone
            const situacao = SITUACOES_DE_FEEDBACK.find((s) => s.id === item.status)
            const nota = notas[item.id] ?? item.admin_notes
            const travado = ocupado === item.id
            const autor = item.autor_nome || item.autor_usuario || 'Conta removida'
            const assunto = encodeURIComponent(`Re: seu feedback no Revsist (${tipo.rotulo.toLowerCase()})`)

            return (
              <li key={item.id} className={`pf-cartao pf-cartao--${item.tipo} ${item.status === 'novo' ? 'is-novo' : ''}`}>
                <div className="pf-cabeca">
                  <Badge variant={tipo.badge} size="xs" icon={<Icone size={11} />}>
                    {tipo.rotulo}
                  </Badge>
                  {situacao && (
                    <Badge variant={situacao.badge} size="xs">
                      {situacao.rotulo}
                    </Badge>
                  )}
                  <span className="pf-data">{dataHora(item.created_at)}</span>
                </div>

                <div className="pf-autor">
                  <strong>{autor}</strong>
                  {item.autor_usuario && <span className="pf-muted">@{item.autor_usuario}</span>}
                  {item.autor_email && (
                    <a href={`mailto:${item.autor_email}?subject=${assunto}`} className="pf-muted">
                      {item.autor_email}
                    </a>
                  )}
                </div>

                <p className="pf-mensagem">{item.mensagem}</p>

                <div className="pf-meta">
                  <span title="Tela de onde o feedback foi enviado">
                    <code>{item.pagina || '/'}</code>
                  </span>
                  {item.versao && <span>v{item.versao}</span>}
                  {item.navegador && (
                    <span className="pf-navegador" title={item.navegador}>
                      <MonitorSmartphone size={11} aria-hidden="true" /> {item.navegador}
                    </span>
                  )}
                </div>

                <div className="pf-nota">
                  <label htmlFor={`pf-nota-${item.id}`} className="pf-muted">
                    Anotação interna
                  </label>
                  <textarea
                    id={`pf-nota-${item.id}`}
                    rows={2}
                    maxLength={2000}
                    placeholder="Só você vê. Ex.: reproduzido, corrigir na próxima versão."
                    value={nota}
                    onChange={(e) => setNotas((n) => ({ ...n, [item.id]: e.target.value }))}
                    onBlur={() => salvarNota(item)}
                    disabled={travado}
                  />
                </div>

                <div className="pf-acoes">
                  {item.autor_email && (
                    <Button
                      variant="secondary"
                      size="xs"
                      leftIcon={<Mail size={12} />}
                      onClick={() => window.open(`mailto:${item.autor_email}?subject=${assunto}`, '_self')}
                    >
                      Responder
                    </Button>
                  )}
                  {item.status !== 'em_andamento' && item.status !== 'resolvido' && (
                    <Button
                      variant="secondary"
                      size="xs"
                      leftIcon={<Clock size={12} />}
                      disabled={travado}
                      onClick={() => mudarSituacao(item, 'em_andamento')}
                    >
                      Em andamento
                    </Button>
                  )}
                  {item.status !== 'resolvido' && (
                    <Button
                      variant="primary"
                      size="xs"
                      leftIcon={<CheckCircle2 size={12} />}
                      disabled={travado}
                      onClick={() => mudarSituacao(item, 'resolvido')}
                    >
                      Resolvido
                    </Button>
                  )}
                  {item.status === 'novo' || item.status === 'em_andamento' ? (
                    <Button
                      variant="ghost"
                      size="xs"
                      leftIcon={<Archive size={12} />}
                      disabled={travado}
                      onClick={() => mudarSituacao(item, 'arquivado')}
                    >
                      Arquivar
                    </Button>
                  ) : (
                    <Button
                      variant="ghost"
                      size="xs"
                      leftIcon={<Undo2 size={12} />}
                      disabled={travado}
                      onClick={() => mudarSituacao(item, 'novo')}
                    >
                      Reabrir
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="xs"
                    leftIcon={<Trash2 size={12} />}
                    disabled={travado}
                    onClick={() => excluir(item)}
                    title="Excluir o feedback definitivamente"
                  >
                    Excluir
                  </Button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
