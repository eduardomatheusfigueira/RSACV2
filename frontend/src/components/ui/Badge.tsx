/**
 * RSAC V2 — Canonical Badge / Chip Component
 * Design System: Contemporary Neo-Retro System Aesthetic
 */

import React from 'react'
import './Badge.css'

export type BadgeVariant =
  | 'brand'
  | 'neutral'
  | 'included'
  | 'excluded'
  | 'pending'
  | 'info'
  | 'success'
  | 'warning'
  | 'error'

export type BadgeSize = 'xs' | 'sm' | 'md'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
  size?: BadgeSize
  dot?: boolean
  icon?: React.ReactNode
  interactive?: boolean
}

export function Badge({
  variant = 'neutral',
  size = 'sm',
  dot = false,
  icon,
  interactive = false,
  className = '',
  children,
  ...props
}: BadgeProps): JSX.Element {
  const classNames = [
    'rsac-badge',
    `rsac-badge--${variant}`,
    `rsac-badge--${size}`,
    interactive ? 'rsac-badge--interactive' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <span className={classNames} {...props}>
      {dot && <span className="rsac-badge__dot" />}
      {icon && <span className="rsac-badge__icon">{icon}</span>}
      <span className="rsac-badge__label">{children}</span>
    </span>
  )
}
