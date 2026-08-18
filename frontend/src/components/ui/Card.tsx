/**
 * RSAC V2 — Canonical Card Component
 * Design System: Contemporary Neo-Retro System Aesthetic
 */

import React, { forwardRef } from 'react'
import './Card.css'

/**
 * Superfície e relevo são escolhas INDEPENDENTES — foi assim que as 28 classes
 * de cartão das páginas se combinaram na prática. Uma lista fechada de
 * variantes obrigaria a nomear as seis combinações e ainda assim deixaria de
 * fora a próxima.
 */
export type CardSurface = 'primaria' | 'secundaria'
export type CardRelief = 'elevado' | 'afundado' | 'plano'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  surface?: CardSurface
  relief?: CardRelief
  /** Filete de acento na borda esquerda: marca o cartão em foco ou ativo. */
  accented?: boolean
  compact?: boolean
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      surface = 'secundaria',
      relief = 'elevado',
      accented = false,
      compact = false,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const classNames = [
      'rsac-card',
      `rsac-card--${surface}`,
      `rsac-card--${relief}`,
      accented ? 'rsac-card--acentuado' : '',
      compact ? 'rsac-card--compact' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ')

    return (
      <div ref={ref} className={classNames} {...props}>
        {children}
      </div>
    )
  }
)
Card.displayName = 'Card'

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  actions?: React.ReactNode
}

export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className = '', actions, children, ...props }, ref) => {
    return (
      <div ref={ref} className={`rsac-card__header ${className}`.trim()} {...props}>
        <div className="rsac-card__header-content">{children}</div>
        {actions && <div className="rsac-card__header-actions">{actions}</div>}
      </div>
    )
  }
)
CardHeader.displayName = 'CardHeader'

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  icon?: React.ReactNode
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
}

export const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ as: Component = 'h3', icon, className = '', children, ...props }, ref) => {
    return (
      <Component ref={ref} className={`rsac-card__title ${className}`.trim()} {...props}>
        {icon && <span className="rsac-card__title-icon">{icon}</span>}
        <span>{children}</span>
      </Component>
    )
  }
)
CardTitle.displayName = 'CardTitle'

export const CardDescription = forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <p ref={ref} className={`rsac-card__description ${className}`.trim()} {...props}>
        {children}
      </p>
    )
  }
)
CardDescription.displayName = 'CardDescription'

export const CardContent = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <div ref={ref} className={`rsac-card__content ${className}`.trim()} {...props}>
        {children}
      </div>
    )
  }
)
CardContent.displayName = 'CardContent'

export const CardFooter = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <div ref={ref} className={`rsac-card__footer ${className}`.trim()} {...props}>
        {children}
      </div>
    )
  }
)
CardFooter.displayName = 'CardFooter'
