/**
 * Revsist — Accessible Radix Tooltip Wrapper
 * Design System: Contemporary Neo-Retro System Aesthetic
 */

import React from 'react'
import * as RadixTooltip from '@radix-ui/react-tooltip'
import './Tooltip.css'

export interface TooltipProps {
  content: React.ReactNode
  children: React.ReactNode
  side?: 'top' | 'right' | 'bottom' | 'left'
  align?: 'start' | 'center' | 'end'
  delayDuration?: number
  className?: string
  asChild?: boolean
}

export function Tooltip({
  content,
  children,
  side = 'top',
  align = 'center',
  delayDuration = 300,
  className = '',
  asChild = true,
}: TooltipProps): JSX.Element {
  if (!content) {
    return <>{children}</>
  }

  return (
    <RadixTooltip.Provider delayDuration={delayDuration}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild={asChild}>
          {children}
        </RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            side={side}
            align={align}
            sideOffset={4}
            className={`rsac-tooltip-content ${className}`.trim()}
          >
            {content}
            <RadixTooltip.Arrow className="rsac-tooltip-arrow" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  )
}

export const TooltipProvider = RadixTooltip.Provider
export const TooltipRoot = RadixTooltip.Root
export const TooltipTrigger = RadixTooltip.Trigger
export const TooltipContent = RadixTooltip.Content
export const TooltipPortal = RadixTooltip.Portal
