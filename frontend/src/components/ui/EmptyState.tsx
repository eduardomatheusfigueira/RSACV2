/**
 * RSAC V2 — Estado Vazio e Estado de Carregamento
 *
 * Substitui as 11 classes distintas de estado vazio que existiam
 * (`empty-state`, `queue-empty-state`, `terminal-empty`, `log-empty`,
 * `dashboard-empty`, `empty-abstract-state`…), cada uma com o próprio
 * espaçamento e a própria voz.
 *
 * Um estado vazio bom diz três coisas: o que deveria estar aqui, por que não
 * está, e o que fazer a respeito. `<EmptyState>` obriga as duas primeiras e
 * oferece a terceira.
 */

import { Loader2 } from 'lucide-react'
import './EmptyState.css'

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  /** Por que está vazio e o que muda isso. */
  description?: React.ReactNode
  action?: React.ReactNode
  /** `inline` cabe dentro de um painel; `block` ocupa a área de trabalho. */
  size?: 'inline' | 'block'
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  size = 'block',
}: EmptyStateProps): JSX.Element {
  return (
    <div className={`rsac-empty rsac-empty--${size}`}>
      {icon && <div className="rsac-empty__icon">{icon}</div>}
      <p className="rsac-empty__title">{title}</p>
      {description && <p className="rsac-empty__description">{description}</p>}
      {action && <div className="rsac-empty__action">{action}</div>}
    </div>
  )
}

interface LoadingStateProps {
  label?: string
  size?: 'inline' | 'block'
}

/**
 * Carregamento com rótulo. O `aria-live="polite"` é o motivo de existir: sem
 * ele, quem usa leitor de tela não recebe aviso nenhum de que a aplicação está
 * ocupada — a tela simplesmente fica em silêncio.
 */
export function LoadingState({
  label = 'Carregando…',
  size = 'block',
}: LoadingStateProps): JSX.Element {
  return (
    <div className={`rsac-empty rsac-empty--${size}`} role="status" aria-live="polite">
      <Loader2 size={size === 'block' ? 28 : 18} className="rsac-empty__spinner" aria-hidden="true" />
      <p className="rsac-empty__title">{label}</p>
    </div>
  )
}
