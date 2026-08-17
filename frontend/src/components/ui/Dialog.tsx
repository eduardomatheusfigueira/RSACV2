/**
 * RSAC V2 — Accessible Radix Dialog / Modal Wrapper
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
>(({ size = 'md', showCloseButton = true, className = '', children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <RadixDialog.Content
      ref={ref}
      className={`rsac-dialog-content rsac-dialog-content--${size} ${className}`.trim()}
      {...props}
    >
      {children}
      {showCloseButton && (
        <RadixDialog.Close className="rsac-dialog-close-btn" aria-label="Fechar modal">
          <X size={16} />
        </RadixDialog.Close>
      )}
    </RadixDialog.Content>
  </DialogPortal>
))
DialogContent.displayName = 'DialogContent'

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
