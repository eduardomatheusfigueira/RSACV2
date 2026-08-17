/**
 * RSAC V2 — Cabeçalho de Página Canônico
 *
 * Fonte única da altura do cabeçalho. Antes existia replicado nas 8 páginas,
 * cada uma com o próprio espaçamento — 84 px no Estúdio de Protocolo e 51 px
 * nas demais, sem que ninguém tivesse decidido isso.
 *
 * HIERARQUIA DE COMANDO (doc 24 § 24.9)
 * O cabeçalho abriga **no máximo uma ação primária**, mais o voltar. Os demais
 * comandos da etapa pertencem ao ribbon, que já os despacha pelo registro
 * tipado. Enquanto as duas superfícies repetiam os mesmos botões, o usuário não
 * tinha como saber qual era o caminho canônico — e os dois conjuntos nem
 * compartilhavam estado.
 */

import { ArrowLeft } from 'lucide-react'
import './PageHeader.css'

interface PageHeaderProps {
  title: string
  /** Linha de contexto: projeto, diretriz, contagem. */
  subtitle?: React.ReactNode
  /** Seletor ou etiqueta que qualifica o título (ex.: diretriz ativa). */
  meta?: React.ReactNode
  onBack?: () => void
  backLabel?: string
  /** A ÚNICA ação primária da tela. Demais comandos vão para o ribbon. */
  primaryAction?: React.ReactNode
  /** Indicador de estado transitório (ex.: "Salvo com sucesso"). */
  status?: React.ReactNode
}

export function PageHeader({
  title,
  subtitle,
  meta,
  onBack,
  backLabel = 'Voltar',
  primaryAction,
  status,
}: PageHeaderProps): JSX.Element {
  return (
    <header className="rsac-page-header">
      <div className="rsac-page-header__main">
        {onBack && (
          <button type="button" className="rsac-page-header__back" onClick={onBack}>
            <ArrowLeft size={13} aria-hidden="true" />
            <span>{backLabel}</span>
          </button>
        )}
        <h1 className="rsac-page-header__title">{title}</h1>
        {meta && <div className="rsac-page-header__meta">{meta}</div>}
      </div>

      {subtitle && <p className="rsac-page-header__subtitle">{subtitle}</p>}

      {(status || primaryAction) && (
        <div className="rsac-page-header__actions">
          {status}
          {primaryAction}
        </div>
      )}
    </header>
  )
}
