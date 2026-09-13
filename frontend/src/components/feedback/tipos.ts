/**
 * Revsist — Vocabulário do feedback do beta, comum ao botão e ao painel.
 */

import { Bug, Heart, Lightbulb, MessageCircle, type LucideIcon } from 'lucide-react'
import type { BadgeVariant } from '@/components/ui'
import type { FeedbackStatus, FeedbackTipo } from '@/types/api'

export interface TipoDeFeedback {
  id: FeedbackTipo
  rotulo: string
  icone: LucideIcon
  badge: BadgeVariant
  /** O que a caixa de texto sugere escrever para este tipo. */
  convite: string
}

export const TIPOS_DE_FEEDBACK: TipoDeFeedback[] = [
  {
    id: 'problema',
    rotulo: 'Problema',
    icone: Bug,
    badge: 'error',
    convite:
      'O que aconteceu e o que você esperava que acontecesse? Se puder, conte o passo a passo até o problema.',
  },
  {
    id: 'sugestao',
    rotulo: 'Sugestão',
    icone: Lightbulb,
    badge: 'info',
    convite: 'O que faria o Revsist ajudar mais na sua revisão?',
  },
  {
    id: 'elogio',
    rotulo: 'Elogio',
    icone: Heart,
    badge: 'success',
    convite: 'O que funcionou bem para você? Saber disso também orienta o que manter.',
  },
  {
    id: 'outro',
    rotulo: 'Outro',
    icone: MessageCircle,
    badge: 'neutral',
    convite: 'Escreva o que quiser contar.',
  },
]

export const tipoDeFeedback = (id: FeedbackTipo): TipoDeFeedback =>
  TIPOS_DE_FEEDBACK.find((t) => t.id === id) ?? TIPOS_DE_FEEDBACK[TIPOS_DE_FEEDBACK.length - 1]

export const SITUACOES_DE_FEEDBACK: { id: FeedbackStatus; rotulo: string; badge: BadgeVariant }[] = [
  { id: 'novo', rotulo: 'Novo', badge: 'warning' },
  { id: 'em_andamento', rotulo: 'Em andamento', badge: 'info' },
  { id: 'resolvido', rotulo: 'Resolvido', badge: 'success' },
  { id: 'arquivado', rotulo: 'Arquivado', badge: 'neutral' },
]

export const MIN_CARACTERES = 5
export const MAX_CARACTERES = 5000
