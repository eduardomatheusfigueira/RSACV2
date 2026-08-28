/**
 * Revsist — Accessible Radix Dialog / Modal Wrapper
 * Design System: Contemporary Neo-Retro System Aesthetic
 */

import React, { forwardRef } from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import './Dialog.css'

export const Dialog = RadixDialog.Root
export const DialogTrigger = RadixDialog.Trigger
export const DialogPortal = RadixDialog.Portal
export const DialogClose = RadixDialog.Close

export interface DialogContentProps
  extends React.ComponentPropsWithoutRef<typeof RadixDialog.Content> {
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  showCloseButton?: boolean
  /**
   * `window` reproduz a janela clássica do app — barra de título no acento,
   * corpo sem respiro próprio. É o que os cinco modais escritos à mão já
   * pareciam; a diferença é que agora vêm com foco preso, Escape e devolução
   * do foco de graça.
   */
  variant?: 'plain' | 'window'
}

export const DialogOverlay = forwardRef<
  React.ElementRef<typeof RadixDialog.Overlay>,
  React.ComponentPropsWithoutRef<typeof RadixDialog.Overlay>
>(({ className = '', ...props }, ref) => (
  <RadixDialog.Overlay
    ref={ref}
    className={`rsac-dialog-overlay ${className}`.trim()}
    {...props}
  />
))
DialogOverlay.displayName = 'DialogOverlay'

export const DialogContent = forwardRef<
  React.ElementRef<typeof RadixDialog.Content>,
  DialogContentProps
>(({ size = 'md', variant = 'plain', showCloseButton, className = '', children, ...props }, ref) => {
  /* Na variante janela quem fecha é o botão da barra de título — o X flutuante
     do Radix ficaria por cima dele. */
  const withClose = showCloseButton ?? variant !== 'window'
  return (
    <DialogPortal>
      <DialogOverlay />
      <RadixDialog.Content
        ref={ref}
        className={`rsac-dialog-content rsac-dialog-content--${size} rsac-dialog-content--${variant} ${className}`.trim()}
        {...props}
      >
        {children}
        {withClose && (
          <RadixDialog.Close className="rsac-dialog-close-btn" aria-label="Fechar modal">
            <X size={16} />
          </RadixDialog.Close>
        )}
      </RadixDialog.Content>
    </DialogPortal>
  )
})
DialogContent.displayName = 'DialogContent'

/**
 * Barra de título da janela clássica. Carrega o `DialogTitle` que o Radix exige
 * para nomear o diálogo, e o botão de fechar.
 */
export const DialogTitlebar = ({
  children,
  closeLabel = 'Fechar',
}: {
  children: React.ReactNode
  closeLabel?: string
}): JSX.Element => (
  <div className="rsac-dialog-titlebar">
    <RadixDialog.Title className="rsac-dialog-titlebar__title">{children}</RadixDialog.Title>
    <RadixDialog.Close className="rsac-dialog-titlebar__close" aria-label={closeLabel} title={closeLabel}>
      <X size={13} aria-hidden="true" />
    </RadixDialog.Close>
  </div>
)
DialogTitlebar.displayName = 'DialogTitlebar'

/** Corpo com o respiro da janela clássica. */
export const DialogBody = ({
  className = '',
  ...props
}: React.HTMLAttributes<HTMLDivElement>): JSX.Element => (
  <div className={`rsac-dialog-body ${className}`.trim()} {...props} />
)
DialogBody.displayName = 'DialogBody'

export const DialogHeader = ({
  className = '',
  ...props
}: React.HTMLAttributes<HTMLDivElement>): JSX.Element => (
  <div className={`rsac-dialog-header ${className}`.trim()} {...props} />
)
DialogHeader.displayName = 'DialogHeader'

export const DialogTitle = forwardRef<
  React.ElementRef<typeof RadixDialog.Title>,
  React.ComponentPropsWithoutRef<typeof RadixDialog.Title>
>(({ className = '', ...props }, ref) => (
  <RadixDialog.Title
    ref={ref}
    className={`rsac-dialog-title ${className}`.trim()}
    {...props}
  />
))
DialogTitle.displayName = 'DialogTitle'

export const DialogDescription = forwardRef<
  React.ElementRef<typeof RadixDialog.Description>,
  React.ComponentPropsWithoutRef<typeof RadixDialog.Description>
>(({ className = '', ...props }, ref) => (
  <RadixDialog.Description
    ref={ref}
    className={`rsac-dialog-description ${className}`.trim()}
    {...props}
  />
))
DialogDescription.displayName = 'DialogDescription'

export const DialogFooter = ({
  className = '',
  ...props
}: React.HTMLAttributes<HTMLDivElement>): JSX.Element => (
  <div className={`rsac-dialog-footer ${className}`.trim()} {...props} />
)
DialogFooter.displayName = 'DialogFooter'
