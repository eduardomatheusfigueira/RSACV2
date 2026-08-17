/**
 * RSAC V2 — Canonical Form Controls (Input, Textarea, Select, FormGroup)
 * Design System: Contemporary Neo-Retro System Aesthetic
 */

import React, { forwardRef } from 'react'
import './FormControls.css'

export interface FormGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: React.ReactNode
  error?: string
  helperText?: string
  required?: boolean
  htmlFor?: string
}

export const FormGroup = ({
  label,
  error,
  helperText,
  required = false,
  htmlFor,
  className = '',
  children,
  ...props
}: FormGroupProps): JSX.Element => {
  return (
    <div className={`rsac-form-group ${error ? 'has-error' : ''} ${className}`.trim()} {...props}>
      {label && (
        <label htmlFor={htmlFor} className="rsac-form-label">
          {label}
          {required && <span className="rsac-form-required">*</span>}
        </label>
      )}
      {children}
      {error ? (
        <span className="rsac-form-error">{error}</span>
      ) : helperText ? (
        <span className="rsac-form-helper">{helperText}</span>
      ) : null}
    </div>
  )
}
FormGroup.displayName = 'FormGroup'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  sizeVariant?: 'sm' | 'md' | 'lg'
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  error?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      sizeVariant = 'md',
      leftIcon,
      rightIcon,
      error = false,
      className = '',
      ...props
    },
    ref
  ) => {
    const classNames = [
      'rsac-input',
      `rsac-input--${sizeVariant}`,
      leftIcon ? 'rsac-input--has-left-icon' : '',
      rightIcon ? 'rsac-input--has-right-icon' : '',
      error ? 'rsac-input--error' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ')

    if (leftIcon || rightIcon) {
      return (
        <div className="rsac-input-wrapper">
          {leftIcon && <span className="rsac-input-icon rsac-input-icon--left">{leftIcon}</span>}
          <input ref={ref} className={classNames} {...props} />
          {rightIcon && <span className="rsac-input-icon rsac-input-icon--right">{rightIcon}</span>}
        </div>
      )
    }

    return <input ref={ref} className={classNames} {...props} />
  }
)
Input.displayName = 'Input'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ error = false, className = '', ...props }, ref) => {
    const classNames = [
      'rsac-textarea',
      error ? 'rsac-textarea--error' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ')

    return <textarea ref={ref} className={classNames} {...props} />
  }
)
Textarea.displayName = 'Textarea'

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  sizeVariant?: 'sm' | 'md' | 'lg'
  error?: boolean
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ sizeVariant = 'md', error = false, className = '', children, ...props }, ref) => {
    const classNames = [
      'rsac-select',
      `rsac-select--${sizeVariant}`,
      error ? 'rsac-select--error' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ')

    return (
      <div className="rsac-select-wrapper">
        <select ref={ref} className={classNames} {...props}>
          {children}
        </select>
        <span className="rsac-select-arrow" />
      </div>
    )
  }
)
Select.displayName = 'Select'
