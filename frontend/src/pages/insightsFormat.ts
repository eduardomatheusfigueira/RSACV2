/**
 * Revsist — Formatação pura da Aba de Indicadores (doc 32)
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

/**
 * Forma estrutural dos filtros da aba — não importa `InsightsFilters` de
 * `@/types/api` para manter este módulo livre de import (ver cabeçalho).
 * Estruturalmente idêntico, então qualquer `InsightsFilters` real serve aqui.
 */
interface FiltrosDeConsulta {
  decision?: string
  source?: string
  year_from?: number
  year_to?: number
}

/**
 * Monta a query string de `GET /projects/{id}/insights` a partir dos
 * filtros da interface (doc 32 §3.2, doc 33 Fase 2). Sem filtro nenhum,
 * devolve string vazia — o endpoint já assume decisão = Incluído por padrão.
 */
export function construirQueryDeInsights(filtros?: FiltrosDeConsulta): string {
  const params = new URLSearchParams()
  if (filtros?.decision) params.set('decision', filtros.decision)
  if (filtros?.source) params.set('source', filtros.source)
  if (filtros?.year_from) params.set('year_from', String(filtros.year_from))
  if (filtros?.year_to) params.set('year_to', String(filtros.year_to))

  const qs = params.toString()
  return qs ? `?${qs}` : ''
}
