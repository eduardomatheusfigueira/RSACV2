/**
 * Revsist — Análise do subconjunto de Markdown do aviso do BETA.
 *
 * Separado da tela porque é onde os defeitos moram, e função pura se testa.
 * Os dois primeiros erros desta análise foram encontrados olhando a tela
 * renderizada, não lendo o código:
 *
 * 1. Cada linha do arquivo virava um parágrafo. O texto saía com espaçamento
 *    de lista, e o leitor via um documento estranho antes de ler uma frase.
 * 2. Como consequência, um `**negrito**` que atravessasse a quebra de linha
 *    aparecia com os asteriscos à mostra — inclusive na frase mais importante
 *    do aviso, a que diz que não é um servidor profissional.
 *
 * Uma biblioteca de Markdown resolveria os dois, e traria junto uma superfície
 * de HTML arbitrário numa tela cuja função é ser confiável. O subconjunto aqui
 * é pequeno de propósito: títulos de seção, parágrafos, listas e ênfase forte.
 */

export type Bloco =
  | { tipo: 'titulo'; texto: string }
  | { tipo: 'paragrafo'; texto: string }
  | { tipo: 'lista'; itens: string[] }

export function analisarAviso(markdown: string): Bloco[] {
  const blocos: Bloco[] = []
  let itens: string[] = []
  let linhasDoParagrafo: string[] = []

  const fecharLista = () => {
    if (!itens.length) return
    blocos.push({ tipo: 'lista', itens })
    itens = []
  }

  const fecharParagrafo = () => {
    if (!linhasDoParagrafo.length) return
    blocos.push({ tipo: 'paragrafo', texto: linhasDoParagrafo.join(' ') })
    linhasDoParagrafo = []
  }

  for (const linha of markdown.split('\n')) {
    const t = linha.trim()

    // Linha em branco encerra o que estiver aberto — é ela que separa
    // parágrafos no Markdown, e não a quebra de linha.
    if (!t) {
      fecharParagrafo()
      fecharLista()
      continue
    }

    if (t.startsWith('- ')) {
      fecharParagrafo()
      itens.push(t.slice(2))
      continue
    }

    // Linha indentada logo abaixo de um item continua **aquele item**.
    if (itens.length && /^\s/.test(linha)) {
      itens[itens.length - 1] += ' ' + t
      continue
    }

    fecharLista()

    if (t.startsWith('## ')) {
      fecharParagrafo()
      blocos.push({ tipo: 'titulo', texto: t.slice(3) })
    } else if (t.startsWith('# ')) {
      // O `# ` do topo repete o título do cabeçalho do cartão; mostrá-lo de
      // novo só gastaria a primeira tela de quem precisa ler.
      fecharParagrafo()
    } else {
      linhasDoParagrafo.push(t)
    }
  }

  fecharParagrafo()
  fecharLista()
  return blocos
}

/** Fatia o texto em trechos normais e em negrito, na ordem. */
export function fatiarEnfase(texto: string): { forte: boolean; texto: string }[] {
  return texto
    .split(/\*\*(.+?)\*\*/g)
    .map((parte, i) => ({ forte: i % 2 === 1, texto: parte }))
    .filter((p) => p.texto !== '')
}
