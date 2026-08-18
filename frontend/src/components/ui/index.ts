/**
 * RSAC V2 — Canonical UI Component Library
 * Design System: Contemporary Neo-Retro System Aesthetic
 */

// Button
export { Button } from './Button'
export type { ButtonProps, ButtonVariant, ButtonSize } from './Button'

// Badge
export { Badge } from './Badge'
export type { BadgeProps, BadgeVariant, BadgeSize } from './Badge'

// Card
export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from './Card'
export type {
  CardProps,
  CardSurface,
  CardRelief,
  CardHeaderProps,
  CardTitleProps,
} from './Card'

// Tooltip
export {
  Tooltip,
  TooltipProvider,
  TooltipRoot,
  TooltipTrigger,
  TooltipContent,
  TooltipPortal,
} from './Tooltip'
export type { TooltipProps } from './Tooltip'

// Dialog
export {
  Dialog,
  DialogTrigger,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogHeader,
  DialogTitlebar,
  DialogBody,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from './Dialog'
export type { DialogContentProps } from './Dialog'

// Page Header
export { PageHeader } from './PageHeader'

// Avisos transitórios
export { Toaster, toast } from './Toaster'

// Empty & Loading States
export { EmptyState, LoadingState } from './EmptyState'

// Form Controls
export {
  FormGroup,
  Input,
  Textarea,
  Select,
} from './FormControls'
export type {
  FormGroupProps,
  InputProps,
  TextareaProps,
  SelectProps,
} from './FormControls'
