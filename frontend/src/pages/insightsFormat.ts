/**
 * RSAC V2 — Formatação pura da Aba de Indicadores (doc 32)
 *
 * Módulo sem import algum — mesmo padrão de `api/backendUrl.ts`, o único
 * outro arquivo com teste no projeto. `InsightsPage.tsx` puxa `recharts`,
 * componentes de UI e o cliente HTTP; nada disso precisa estar de pé só para
 * testar uma formatação de número.
 */

export function formatarPercentual(valor: number | null): string {
  if (valor === null) return '—'
  return `${Math.round(valor * 100)}%`
}
