/**
 * Revsist — Selo BETA
 *
 * O Revsist ainda está em desenvolvimento; o selo é parte permanente da
 * assinatura enquanto isso durar. Segue a linguagem de "etiqueta de
 * engenharia" do design system — mono, versalete, cantos cirúrgicos — e não
 * a pílula arredondada de app mobile.
 */

import './Brand.css'
import type { RsacTone } from './RsacMark'

interface BetaBadgeProps {
  /** `brand` = sólido sobre chrome escuro; `auto` = contorno sobre conteúdo. */
  tone?: Extract<RsacTone, 'auto' | 'brand'>
  size?: 'xs' | 'sm' | 'md'
  className?: string
  title?: string
}

export function BetaBadge({
  tone = 'auto',
  size = 'sm',
  className = '',
  title = 'Versão beta — funcionalidades em evolução',
}: BetaBadgeProps): JSX.Element {
  return (
    <span
      className={`rsac-beta rsac-beta--${tone} rsac-beta--${size} ${className}`.trim()}
      title={title}
    >
      Beta
    </span>
  )
}
