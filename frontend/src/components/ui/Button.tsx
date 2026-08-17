/**
 * RSAC V2 — Canonical Button Component
 * Design System: Contemporary Neo-Retro System Aesthetic
 */

import React, { forwardRef } from 'react'
import { Loader2 } from 'lucide-react'
import './Button.css'

export type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'outline'
  | 'ghost'
  | 'destructive'
  | 'decision-included'
  | 'decision-excluded'
  | 'decision-pending'

export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  fullWidth?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'secondary',
      size = 'md',
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      className = '',
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const classNames = [
      'rsac-btn',
      `rsac-btn--${variant}`,
      `rsac-btn--${size}`,
      fullWidth ? 'rsac-btn--full' : '',
      loading ? 'rsac-btn--loading' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ')

    return (
      <button
        ref={ref}
        type={props.type || 'button'}
        className={classNames}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <Loader2 size={size === 'xs' ? 12 : size === 'sm' ? 13 : 15} className="rsac-btn__spinner" />
        ) : (
          leftIcon && <span className="rsac-btn__icon rsac-btn__icon--left">{leftIcon}</span>
        )}
        <span className="rsac-btn__content">{children}</span>
        {!loading && rightIcon && (
          <span className="rsac-btn__icon rsac-btn__icon--right">{rightIcon}</span>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'
