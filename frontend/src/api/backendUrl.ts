/**
 * RSAC V2 — Validação e confirmação do endereço do backend (doc 29 §29.12)
 *
 * O problema que este módulo resolve: o cliente aceitava `?api_url=` do
 * *search* e do fragmento, sem validar nada, e gravava em `localStorage`. O
 * próprio lançador **ensina** esse formato ao usuário, imprimindo
 * `https://<netlify>/#/?api_url=<túnel>` como o link oficial de acesso — de
 * modo que o pesquisador é treinado a clicar em links RSAC com `api_url`
 * embutido e não tem como distinguir o legítimo do hostil.
 *
 * Um link como
 * `https://rsac-do-usuario.netlify.app/#/?api_url=https://backend.attacker`
 * carregava a interface real, com o certificado real, e apontava **toda**
 * requisição seguinte para o servidor do atacante — incluindo o `PUT` com as
 * chaves que o usuário digitasse. E, por ficar em `localStorage`, o sequestro
 * sobrevivia ao fechamento da aba.
 */

/** Sufixos de host reconhecidos como destino plausível do RSAC. */
const SUFIXOS_CONHECIDOS = [
  'trycloudflare.com',
  'cfargotunnel.com',
  'ngrok.io',
  'ngrok-free.app',
  'localhost',
  '127.0.0.1',
]

export type ClassificacaoDeHost = 'local' | 'conhecido' | 'desconhecido'

export interface UrlDeBackend {
  /** URL normalizada, já com o sufixo `/api/v1`. */
  url: string
  /** Host, para nomear no diálogo de confirmação. */
  host: string
  origem: string
  classificacao: ClassificacaoDeHost
  /** Conexão sem TLS fora do loopback — dado de pesquisa trafegando em claro. */
  inseguro: boolean
}

export class UrlDeBackendInvalida extends Error {}

function ehLoopback(host: string): boolean {
  return host === 'localhost' || host === '127.0.0.1' || host === '[::1]' || host === '::1'
}

/**
 * Valida e normaliza um endereço de backend.
 *
 * Recusa o que não é endereço HTTP e o que trafegaria em claro fora da própria
 * máquina. Não decide se o destino é confiável — isso é do usuário, e é por
 * isso que `classificacao` sobe junto.
 */
export function analisarUrlDeBackend(entrada: string): UrlDeBackend {
  const bruto = (entrada || '').trim()
  if (!bruto) {
    throw new UrlDeBackendInvalida('Endereço vazio.')
  }

  let alvo: URL
  try {
    alvo = new URL(bruto)
  } catch {
    throw new UrlDeBackendInvalida(
      'Endereço inválido. Informe algo como https://seu-tunel.trycloudflare.com'
    )
  }

  if (alvo.protocol !== 'https:' && alvo.protocol !== 'http:') {
    throw new UrlDeBackendInvalida(
      `Protocolo não suportado (${alvo.protocol}). Use https:// ou http://localhost.`
    )
  }

  const host = alvo.hostname
  const local = ehLoopback(host)

  // `http://` fora do loopback significa dados de pesquisa e credenciais
  // trafegando em texto claro pela rede.
  if (alvo.protocol === 'http:' && !local) {
    throw new UrlDeBackendInvalida(
      `Conexão sem criptografia com ${host}. Use https:// — em http:// suas credenciais ` +
        'e seus dados de pesquisa trafegam em texto claro.'
    )
  }

  let classificacao: ClassificacaoDeHost = 'desconhecido'
  if (local) {
    classificacao = 'local'
  } else if (SUFIXOS_CONHECIDOS.some((s) => host === s || host.endsWith(`.${s}`))) {
    classificacao = 'conhecido'
  }

  const semBarra = `${alvo.origin}${alvo.pathname}`.replace(/\/+$/, '')
  const url = semBarra.endsWith('/api/v1') ? semBarra : `${semBarra}/api/v1`

  return {
    url,
    host,
    origem: alvo.origin,
    classificacao,
    inseguro: alvo.protocol === 'http:' && !local,
  }
}

/**
 * Texto do diálogo de confirmação.
 *
 * Nomear o host é o ponto: é a única informação que distingue o link legítimo
 * do hostil, e ela precisa aparecer antes de qualquer requisição sair.
 */
export function mensagemDeConfirmacao(destino: UrlDeBackend): string {
  const linhas = [
    `Conectar ao servidor RSAC em:`,
    ``,
    `    ${destino.host}`,
    ``,
    'Suas credenciais de acesso e seus dados de pesquisa serão enviados para este endereço.',
  ]

  if (destino.classificacao === 'desconhecido') {
    linhas.push(
      '',
      '⚠ Este endereço não é um túnel Cloudflare nem um servidor local. ' +
        'Só confirme se você mesmo o configurou.'
    )
  }

  linhas.push('', 'Deseja continuar?')
  return linhas.join('\n')
}

/**
 * Lê `api_url` da URL corrente e a remove do endereço exibido.
 *
 * Remover é parte da correção: deixar o parâmetro na barra faz o sequestro
 * sobreviver a um recarregamento e a um link compartilhado por engano.
 */
export function extrairApiUrlDaLocalizacao(): string | null {
  if (typeof window === 'undefined') return null

  try {
    const busca = new URLSearchParams(window.location.search)
    let valor = busca.get('api_url')

    if (!valor && window.location.hash.includes('?')) {
      const hashParams = new URLSearchParams(window.location.hash.split('?')[1])
      valor = hashParams.get('api_url')
    }
    if (!valor) return null

    const limpa = new URL(window.location.href)
    limpa.searchParams.delete('api_url')
    if (limpa.hash.includes('api_url')) {
      limpa.hash = limpa.hash.replace(/([?&])api_url=[^&]*/, '$1').replace(/[?&]$/, '')
    }
    window.history.replaceState({}, document.title, limpa.toString())

    return valor.trim() || null
  } catch {
    return null
  }
}
