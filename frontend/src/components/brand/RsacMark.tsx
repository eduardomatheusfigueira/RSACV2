/**
 * Revsist — Monograma "R-Lupa"
 *
 * O símbolo da marca: um "R" monolinear em que o laço da letra é a LENTE de
 * uma lupa e a perna diagonal é o CABO. A geometria abaixo é a mesma declarada
 * em `brand/generate_brand_assets.py`, que gera o ícone do executável, do
 * instalador e o favicon — qualquer alteração precisa acontecer nos dois lados.
 *
 *   Grade 80 × 100 · traço 14 · haste x=7 (y 7→93) · lente (32,32) r=25
 *   Cabo: o raio da lente prolongado até (73,93) — junção radial, sem emenda.
 *
 * O viewBox é folgado para 100 × 100 (com −10 de recuo) para que o componente
 * ocupe uma caixa quadrada e alinhe com os ícones lucide ao lado.
 *
 * CORES: haste e lente herdam `currentColor`, então o monograma acompanha
 * automaticamente a cor do texto de qualquer um dos 13 temas. O cabo usa a
 * variável `--rsac-accent`, resolvida por tom (ver Brand.css).
 */

import './Brand.css'

/**
 * `auto`  — acento do tema corrente (superfícies de conteúdo).
 * `brand` — Sunlit Clay do tema (chrome escuro: ribbon, sidebar, splash).
 * `mono`  — traço único, sem acento (favicons, impressão, alto contraste).
 */
export type RsacTone = 'auto' | 'brand' | 'mono'

interface RsacMarkProps {
  size?: number
  tone?: RsacTone
  className?: string
  /** Rótulo acessível. `null` marca o símbolo como decorativo. */
  label?: string | null
}

export function RsacMark({
  size = 24,
  tone = 'auto',
  className = '',
  label = 'Revsist',
}: RsacMarkProps): JSX.Element {
  return (
    <svg
      className={`rsac-mark rsac-mark--${tone} ${className}`.trim()}
      viewBox="-10 0 100 100"
      width={size}
      height={size}
      fill="none"
      strokeWidth={14}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? 'img' : 'presentation'}
      aria-label={label ?? undefined}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      {label && <title>{label}</title>}
      <g stroke="currentColor">
        <path d="M 7 7 V 93" />
        <circle cx="32" cy="32" r="25" />
      </g>
      <path className="rsac-mark-leg" d="M 45.946 52.749 L 73 93" />
    </svg>
  )
}
