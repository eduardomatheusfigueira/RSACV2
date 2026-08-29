/**
 * Token local do aplicativo de mesa (doc 29 §29.3.2).
 *
 * Existe por causa de uma falha relatada por quem instalou o programa: **toda**
 * instalação do Electron abria na tela de login. O processo principal carregava
 * o renderer passando apenas `?port`, sem nunca ler o token local que o backend
 * grava ao subir — o `scripts/launcher.py`, o outro caminho de execução, já
 * fazia isso desde que a autenticação foi introduzida.
 *
 * O defeito era de **ligação**, não de lógica: nenhum teste do backend podia
 * pegá-lo, porque o backend estava correto. Daí este teste viver aqui.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'

import { caminhosDoToken, lerTokenLocal, montarQueryDoRenderer } from './local-token'

describe('parâmetros de carga do renderer', () => {
  it('leva o token local quando ele existe', () => {
    const query = montarQueryDoRenderer(8000, 'token-de-teste')
    expect(query.local_token).toBe('token-de-teste')
    expect(query.port).toBe('8000')
  })

  it('não inventa token quando não há', () => {
    const query = montarQueryDoRenderer(8000, null)
    expect('local_token' in query).toBe(false)
    expect(query.port).toBe('8000')
  })

  it('não deixa token vazio virar credencial', () => {
    expect('local_token' in montarQueryDoRenderer(8000, '')).toBe(false)
  })

  it('sempre informa a porta, que é o que o cliente HTTP usa para achar o backend', () => {
    expect(montarQueryDoRenderer(8097, null).port).toBe('8097')
  })
})

describe('caminhos do token', () => {
  it('honra RSAC_DATA_DIR antes de qualquer padrão do sistema', () => {
    const caminhos = caminhosDoToken({ RSAC_DATA_DIR: '/dados' } as NodeJS.ProcessEnv, 'linux', '/casa')
    expect(caminhos[0]).toBe(join('/dados', 'runtime_token'))
  })

  /**
   * O nível repetido é o defeito que custou mais caro nesta série.
   * `platformdirs.user_data_dir("RSAC")`, sem `appauthor`, usa o `appname`
   * como autor e escreve em `%LOCALAPPDATA%\\RSAC\\RSAC`. A primeira versão
   * daqui procurava em `%LOCALAPPDATA%\\RSAC` — um nível acima — e portanto o
   * app instalado no Windows nunca achava o token que o backend acabara de
   * gravar, e abria na tela de login.
   *
   * Não apareceu em desenvolvimento porque Linux e macOS não têm esse nível
   * extra: só quem instalava no Windows via o defeito.
   */
  it('no Windows procura no nível duplicado que o platformdirs escreve', () => {
    const caminhos = caminhosDoToken({ LOCALAPPDATA: 'C:\\AppData' } as NodeJS.ProcessEnv, 'win32', 'C:\\Users\\eu')
    expect(caminhos).toContain(join('C:\\AppData', 'RSAC', 'RSAC', 'runtime_token'))
  })

  it('o nível duplicado vem antes do antigo, que fica só como reserva', () => {
    const caminhos = caminhosDoToken({ LOCALAPPDATA: 'C:\\AppData' } as NodeJS.ProcessEnv, 'win32', 'C:\\Users\\eu')
    const certo = caminhos.indexOf(join('C:\\AppData', 'RSAC', 'RSAC', 'runtime_token'))
    const antigo = caminhos.indexOf(join('C:\\AppData', 'RSAC', 'runtime_token'))
    expect(certo).toBeGreaterThanOrEqual(0)
    expect(antigo).toBeGreaterThan(certo)
  })

  it('no macOS procura em Application Support', () => {
    const caminhos = caminhosDoToken({} as NodeJS.ProcessEnv, 'darwin', '/Users/eu')
    expect(caminhos).toContain(join('/Users/eu', 'Library', 'Application Support', 'RSAC', 'runtime_token'))
  })

  it('no Linux respeita XDG_DATA_HOME', () => {
    const caminhos = caminhosDoToken({ XDG_DATA_HOME: '/xdg' } as NodeJS.ProcessEnv, 'linux', '/casa')
    expect(caminhos).toContain(join('/xdg', 'RSAC', 'runtime_token'))
  })

  /**
   * A chave de armazenamento continua `RSAC` mesmo depois de o produto passar a
   * se chamar Revsist: trocá-la faria o programa deixar de achar o acervo de
   * quem já o usa. Ver `brand/IDENTIDADE_VISUAL.md`.
   */
  it('mantém RSAC como chave de armazenamento, não Revsist', () => {
    const caminhos = caminhosDoToken({ LOCALAPPDATA: 'C:\\AppData' } as NodeJS.ProcessEnv, 'win32', 'C:\\Users\\eu')
    expect(caminhos.some((c) => c.includes('RSAC'))).toBe(true)
    expect(caminhos.some((c) => c.toLowerCase().includes('revsist'))).toBe(false)
  })
})

describe('leitura do token', () => {
  let raiz: string

  beforeEach(() => {
    raiz = mkdtempSync(join(tmpdir(), 'revsist-token-'))
  })

  afterEach(() => {
    rmSync(raiz, { recursive: true, force: true })
  })

  it('lê o token do primeiro caminho que existe', () => {
    const segundo = join(raiz, 'segundo')
    writeFileSync(segundo, 'token-do-segundo\n')
    expect(lerTokenLocal([join(raiz, 'inexistente'), segundo])).toBe('token-do-segundo')
  })

  it('devolve null quando nenhum caminho existe', () => {
    expect(lerTokenLocal([join(raiz, 'a'), join(raiz, 'b')])).toBeNull()
  })

  /**
   * Um arquivo vazio é o estado normal entre o backend criar o arquivo e
   * escrever nele. Tratá-lo como token faria o app tentar entrar com string
   * vazia e cair na tela de login — o defeito original, por outro caminho.
   */
  it('ignora arquivo vazio e segue para o próximo caminho', () => {
    const vazio = join(raiz, 'vazio')
    const bom = join(raiz, 'bom')
    writeFileSync(vazio, '   \n')
    writeFileSync(bom, 'token-bom')
    expect(lerTokenLocal([vazio, bom])).toBe('token-bom')
  })

  it('um caminho ilegível não derruba a partida', () => {
    const diretorio = join(raiz, 'sou-um-diretorio')
    mkdirSync(diretorio)
    const bom = join(raiz, 'bom')
    writeFileSync(bom, 'token-bom')
    expect(lerTokenLocal([diretorio, bom])).toBe('token-bom')
  })

  it('descarta espaços em volta do token', () => {
    const arquivo = join(raiz, 'com-espaco')
    writeFileSync(arquivo, '  token-limpo\n\n')
    expect(lerTokenLocal([arquivo])).toBe('token-limpo')
  })
})

/**
 * O defeito original não estava em nenhuma função: estava na **ausência da
 * chamada**. `main.ts` importa `electron`, que é CommonJS e não carrega sob o
 * Vitest, então não dá para exercitá-lo; o que dá é ler o arquivo e exigir que
 * a ligação esteja lá. É um teste grosseiro de propósito — ele existe para que
 * remover a chamada volte a ser visível, que foi justamente o que ninguém viu.
 */
describe('ligação no processo principal', () => {
  const fonte = readFileSync(join(__dirname, 'main.ts'), 'utf-8')

  it('lê o token local antes de carregar a interface', () => {
    expect(fonte).toMatch(/const token = lerTokenLocal\(/)
    expect(fonte).toMatch(/montarQueryDoRenderer\(\s*backendPort\s*,\s*token\s*\)/)
  })

  it('prefere o caminho que o backend anunciou à dedução local', () => {
    expect(fonte).toMatch(/pythonManager\.caminhoDoToken/)
    expect(fonte).toMatch(/lerTokenLocal\(\s*anunciado\s*\?/)
  })

  it('passa a query nos dois modos de carga, dev e produção', () => {
    expect(fonte).toMatch(/loadURL\(`\$\{process\.env\['ELECTRON_RENDERER_URL'\]\}\?\$\{parametros\}`\)/)
    expect(fonte).toMatch(/loadFile\(.*,\s*\{ query \}\)/)
  })
})
