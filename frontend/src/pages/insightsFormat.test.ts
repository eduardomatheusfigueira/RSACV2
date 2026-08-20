/**
 * RSAC V2 — Testes da Aba de Indicadores (doc 33 Fase 1)
 *
 * O projeto não tem infraestrutura de teste de renderização de componente
 * (nenhuma das 8 páginas existentes tem — só `backendUrl.test.ts`, sobre
 * função pura). Reproduzir esse padrão aqui, em vez de introduzir
 * `@testing-library/react` sem precedente, é a escolha consistente: testa a
 * lógica pura extraível e verifica a renderização de verdade manualmente,
 * como pede o próprio fluxo de trabalho para mudanças de interface.
 *
 * A verificação manual (servidor real, projeto com dado variado, screenshot)
 * confirmou: os nove blocos renderizam, os estados vazios aparecem quando o
 * agregado correspondente vem zerado (ex.: "Periódicos" sem nenhum artigo com
 * `journal` preenchido), as cores de decisão batem com os tokens
 * `--color-included/-excluded/-pending`, e não há erro de console além de uma
 * falha de rede pré-existente e alheia (Google Fonts, sem acesso à internet
 * no sandbox — reproduz idêntica na ExportPage já existente).
 */

import { describe, expect, it } from 'vitest'
import { formatarPercentual } from './insightsFormat'

describe('formatarPercentual', () => {
  it('devolve travessão para valor nulo (agregado sem dado suficiente)', () => {
    expect(formatarPercentual(null)).toBe('—')
  })

  it('formata frações como percentual inteiro', () => {
    expect(formatarPercentual(0)).toBe('0%')
    expect(formatarPercentual(1)).toBe('100%')
    expect(formatarPercentual(0.5)).toBe('50%')
  })

  it('arredonda para o inteiro mais próximo', () => {
    expect(formatarPercentual(0.334)).toBe('33%')
    expect(formatarPercentual(0.336)).toBe('34%')
  })
})
