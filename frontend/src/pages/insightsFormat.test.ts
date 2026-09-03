/**
 * Revsist — Testes da Aba de Indicadores (doc 33 Fases 1 e 2)
 *
 * O projeto não tem infraestrutura de teste de renderização de componente
 * (nenhuma das 8 páginas existentes tem — só `backendUrl.test.ts`, sobre
 * função pura). Reproduzir esse padrão aqui, em vez de introduzir
 * `@testing-library/react` sem precedente, é a escolha consistente: testa a
 * lógica pura extraível — formatação e montagem da query de filtros — e
 * verifica a renderização de verdade manualmente, como pede o próprio fluxo
 * de trabalho para mudanças de interface.
 *
 * A verificação manual (servidor real, projeto com dado variado, screenshot)
 * confirmou: os blocos renderizam, os estados vazios aparecem quando o
 * agregado correspondente vem zerado (ex.: "Periódicos" sem nenhum artigo com
 * `journal` preenchido), as cores de decisão batem com os tokens
 * `--color-included/-excluded/-pending`, e não há erro de console além de uma
 * falha de rede pré-existente e alheia (Google Fonts, sem acesso à internet
 * no sandbox — reproduz idêntica na ExportPage já existente).
 */

import { describe, expect, it } from 'vitest'
import { construirQueryDeInsights, formatarPercentual, formatarContagem } from './insightsFormat'

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

describe('construirQueryDeInsights', () => {
  it('devolve string vazia sem filtro nenhum', () => {
    expect(construirQueryDeInsights()).toBe('')
    expect(construirQueryDeInsights({})).toBe('')
  })

  it('inclui só os parâmetros presentes', () => {
    expect(construirQueryDeInsights({ decision: 'Excluído' })).toBe('?decision=Exclu%C3%ADdo')
    expect(construirQueryDeInsights({ source: 'SciELO' })).toBe('?source=SciELO')
  })

  it('combina múltiplos filtros na mesma query', () => {
    const qs = construirQueryDeInsights({
      decision: 'Incluído',
      source: 'BDTD',
      year_from: 2015,
      year_to: 2024,
    })
    const params = new URLSearchParams(qs.replace(/^\?/, ''))
    expect(params.get('decision')).toBe('Incluído')
    expect(params.get('source')).toBe('BDTD')
    expect(params.get('year_from')).toBe('2015')
    expect(params.get('year_to')).toBe('2024')
  })

  it('muda a query quando o filtro muda — a garantia que a Fase 2 pede', () => {
    const semFiltro = construirQueryDeInsights({ decision: 'Incluído' })
    const comOutraDecisao = construirQueryDeInsights({ decision: 'Pendente' })
    expect(semFiltro).not.toBe(comOutraDecisao)
  })
})

describe('construirQueryDeInsights — instantâneo', () => {
  it('leva o instantâneo para a query quando há um escolhido', () => {
    expect(construirQueryDeInsights({ instantaneo: 'snp_a91f' })).toContain('instantaneo=snp_a91f')
  })

  it('omite o parâmetro quando os indicadores descrevem o acervo de agora', () => {
    expect(construirQueryDeInsights({ decision: 'Incluído' })).not.toContain('instantaneo')
  })
})

describe('formatarContagem', () => {
  it('separa milhar na convenção pt-BR', () => {
    expect(formatarContagem(43861)).toBe('43.861')
    expect(formatarContagem(1000000)).toBe('1.000.000')
  })

  it('não enfeita número pequeno', () => {
    expect(formatarContagem(454)).toBe('454')
    expect(formatarContagem(0)).toBe('0')
  })

  it('ausência de dado não vira zero', () => {
    expect(formatarContagem(null)).toBe('—')
    expect(formatarContagem(undefined)).toBe('—')
    expect(formatarContagem(NaN)).toBe('—')
  })
})
