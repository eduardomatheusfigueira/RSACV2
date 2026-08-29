/**
 * Os dois defeitos que esta análise já teve, fixados como teste.
 *
 * Ambos foram encontrados olhando a tela, não lendo o código — e o segundo
 * corrompia justamente a frase mais importante do aviso.
 */

import { describe, expect, it } from 'vitest'

import { analisarAviso, fatiarEnfase } from './avisoMarkdown'

describe('parágrafos', () => {
  it('junta linhas seguidas num só parágrafo', () => {
    const blocos = analisarAviso('Primeira linha\nsegunda linha\nterceira.')
    expect(blocos).toEqual([
      { tipo: 'paragrafo', texto: 'Primeira linha segunda linha terceira.' },
    ])
  })

  it('a linha em branco é o que separa parágrafos', () => {
    const blocos = analisarAviso('Um.\n\nDois.')
    expect(blocos.map((b) => b.tipo)).toEqual(['paragrafo', 'paragrafo'])
  })

  /**
   * O defeito original: cada linha do arquivo virava um parágrafo, e o texto
   * saía com aparência de lista solta antes de o leitor chegar à primeira
   * frase inteira.
   */
  it('um texto de três linhas não vira três parágrafos', () => {
    expect(analisarAviso('a\nb\nc')).toHaveLength(1)
  })
})

describe('ênfase', () => {
  it('reconhece negrito no meio da frase', () => {
    expect(fatiarEnfase('isto é **importante** mesmo')).toEqual([
      { forte: false, texto: 'isto é ' },
      { forte: true, texto: 'importante' },
      { forte: false, texto: ' mesmo' },
    ])
  })

  /**
   * O segundo defeito, e o mais grave: no aviso, "**Não é um servidor
   * profissional em datacenter.**" está quebrado em duas linhas. Com a análise
   * antiga os asteriscos apareciam na tela, na frase que mais precisa ser
   * lida.
   */
  it('negrito que atravessa a quebra de linha é reconhecido', () => {
    const blocos = analisarAviso('Texto. **Não é\num servidor.** Fim.')
    expect(blocos).toHaveLength(1)
    const p = blocos[0] as { tipo: 'paragrafo'; texto: string }
    expect(fatiarEnfase(p.texto)).toEqual([
      { forte: false, texto: 'Texto. ' },
      { forte: true, texto: 'Não é um servidor.' },
      { forte: false, texto: ' Fim.' },
    ])
  })
})

describe('listas', () => {
  it('agrupa itens seguidos numa lista só', () => {
    const blocos = analisarAviso('- um\n- dois\n- três')
    expect(blocos).toEqual([{ tipo: 'lista', itens: ['um', 'dois', 'três'] }])
  })

  it('linha indentada continua o item anterior, não abre parágrafo', () => {
    const blocos = analisarAviso('- começo do item\n  continuação dele\n- outro')
    expect(blocos).toEqual([
      { tipo: 'lista', itens: ['começo do item continuação dele', 'outro'] },
    ])
  })

  it('negrito que atravessa a quebra dentro de um item é reconhecido', () => {
    const blocos = analisarAviso('- **Existe backup diário, mas\n  pode custar 24 horas.** Exporte.')
    const lista = blocos[0] as { tipo: 'lista'; itens: string[] }
    expect(fatiarEnfase(lista.itens[0])[0]).toEqual({
      forte: true,
      texto: 'Existe backup diário, mas pode custar 24 horas.',
    })
  })

  it('parágrafo depois da lista fecha a lista', () => {
    expect(analisarAviso('- item\n\nParágrafo.').map((b) => b.tipo)).toEqual(['lista', 'paragrafo'])
  })
})

describe('títulos', () => {
  it('reconhece seção', () => {
    expect(analisarAviso('## 3. Que dados')).toEqual([{ tipo: 'titulo', texto: '3. Que dados' }])
  })

  it('descarta o título de nível 1, que o cabeçalho do cartão já mostra', () => {
    expect(analisarAviso('# Aviso\n\n## Seção').map((b) => b.tipo)).toEqual(['titulo'])
  })
})

describe('o aviso real', () => {
  it('não deixa nenhum asterisco escapar para a tela', () => {
    // Reproduz as construções do texto de produção que quebraram antes.
    const trecho = [
      '# Aviso e Termos do Revsist BETA',
      '',
      '## 2. Onde os seus dados ficam',
      '',
      'Nesta fase o Revsist roda **no computador pessoal de [NOME]**, em',
      '[CIDADE], no Brasil. **Não é',
      'um servidor profissional em datacenter.** Na prática:',
      '',
      '- **Existe backup diário, mas uma falha pode custar até 24 horas de',
      '  trabalho.** Exporte com frequência.',
    ].join('\n')

    const renderizado = analisarAviso(trecho)
      .flatMap((b) =>
        b.tipo === 'lista' ? b.itens : [b.tipo === 'titulo' ? b.texto : b.texto]
      )
      .flatMap(fatiarEnfase)
      .map((p) => p.texto)
      .join(' ')

    expect(renderizado).not.toContain('**')
    expect(renderizado).toContain('Não é um servidor profissional em datacenter.')
  })
})
