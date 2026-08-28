/**
 * Revsist — Assinatura horizontal (marca + logotipo + versão + selo)
 *
 * Usada onde a marca precisa se apresentar por extenso: cabeçalho do app,
 * splash de inicialização e cartão "Sobre" das Configurações. Em espaços
 * apertados use apenas o <RsacMark />.
 */

import './Brand.css'
import { RsacMark, type RsacTone } from './RsacMark'
import { BetaBadge } from './BetaBadge'

interface RsacLockupProps {
  size?: 'sm' | 'md' | 'lg'
  tone?: RsacTone
  /** Linha de apoio abaixo do logotipo. `null` remove a linha. */
  version?: string | null
  showBeta?: boolean
  className?: string
}

const MARK_PX: Record<NonNullable<RsacLockupProps['size']>, number> = {
  sm: 22,
  md: 34,
  lg: 56,
}

export function RsacLockup({
  size = 'md',
  tone = 'auto',
  version = 'v2',
  showBeta = true,
  className = '',
}: RsacLockupProps): JSX.Element {
  return (
    <div className={`rsac-lockup rsac-lockup--${size} ${className}`.trim()}>
      <RsacMark size={MARK_PX[size]} tone={tone} label={null} />
      <div className="rsac-lockup-text">
        <div className="rsac-lockup-title-row">
          <span className="rsac-lockup-word">REVSIST</span>
          {showBeta && (
            <BetaBadge
              tone={tone === 'brand' ? 'brand' : 'auto'}
              size={size === 'lg' ? 'md' : size === 'md' ? 'sm' : 'xs'}
            />
          )}
        </div>
        {version && <span className="rsac-lockup-version">{version}</span>}
      </div>
    </div>
  )
}
