import { describe, expect, it } from 'vitest'
import { LIMITE_PADRAO_DO_LOTE, limitePadraoDoLote } from './limiteDoLote'

describe('limitePadraoDoLote', () => {
  it('devolve o padrão enquanto o contador de pendentes não chegou', () => {
    // Este é o caso que quebrava a triagem em lote: a janela é montada junto
    // com a tela, quando `stats.pending` ainda é 0. A fórmula antiga
    // (`Math.min(50, Math.max(1, 0))`) devolvia 1 e congelava aí.
    expect(limitePadraoDoLote(0)).toBe(LIMITE_PADRAO_DO_LOTE)
    expect(limitePadraoDoLote(null)).toBe(LIMITE_PADRAO_DO_LOTE)
    expect(limitePadraoDoLote(undefined)).toBe(LIMITE_PADRAO_DO_LOTE)
    expect(limitePadraoDoLote(NaN)).toBe(LIMITE_PADRAO_DO_LOTE)
  })

  it('nunca promete mais estudos do que existem pendentes', () => {
    expect(limitePadraoDoLote(7)).toBe(7)
    expect(limitePadraoDoLote(1)).toBe(1)
  })

  it('não passa do teto padrão quando há acervo grande', () => {
    expect(limitePadraoDoLote(500)).toBe(LIMITE_PADRAO_DO_LOTE)
  })

  it('nunca devolve fração nem número negativo', () => {
    expect(limitePadraoDoLote(3.7)).toBe(3)
    expect(limitePadraoDoLote(-5)).toBe(LIMITE_PADRAO_DO_LOTE)
  })
})
