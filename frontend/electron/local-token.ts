/**
 * Revsist — Token local do aplicativo de mesa (doc 29 §29.3.2).
 *
 * O backend grava um token ao subir; o app de mesa o apresenta e entra sem
 * senha, porque quem tem o arquivo já tem o sistema de arquivos do usuário e
 * exigir senha por cima disso seria atrito sem barreira.
 *
 * Este módulo existe separado do `main.ts` por uma razão prática: ele não
 * depende de nada do Electron, e por isso pode ser testado. O defeito que o
 * originou era de **ligação** — o processo principal carregava a interface
 * passando apenas `?port` e nunca lia o token, de modo que toda instalação
 * abria na tela de login. O `scripts/launcher.py`, o outro caminho de
 * execução, já fazia isso desde que a autenticação foi introduzida.
 */

import { existsSync, readFileSync } from 'fs'
import { homedir } from 'os'
import { join } from 'path'

/**
 * Caminhos onde o token pode estar, na ordem em que são tentados.
 *
 * Repetem os do lançador de propósito: é o mesmo arquivo, escrito por
 * `platformdirs.user_data_dir("RSAC")` no backend. O `RSAC` ali é a **chave do
 * armazenamento**, não o nome do produto — trocá-la faria o programa perder o
 * acervo de quem já o usa (ver `brand/IDENTIDADE_VISUAL.md`).
 */
export function caminhosDoToken(
  env: NodeJS.ProcessEnv = process.env,
  plataforma: string = process.platform,
  casa: string = homedir()
): string[] {
  const candidatos: string[] = []

  if (env.RSAC_DATA_DIR) candidatos.push(join(env.RSAC_DATA_DIR, 'runtime_token'))

  if (plataforma === 'win32' && env.LOCALAPPDATA) {
    candidatos.push(join(env.LOCALAPPDATA, 'RSAC', 'runtime_token'))
  } else if (plataforma === 'darwin') {
    candidatos.push(join(casa, 'Library', 'Application Support', 'RSAC', 'runtime_token'))
  } else {
    const xdg = env.XDG_DATA_HOME || join(casa, '.local', 'share')
    candidatos.push(join(xdg, 'RSAC', 'runtime_token'))
  }
  candidatos.push(join(casa, '.rsac', 'runtime_token'))

  return candidatos
}

/** Primeiro token legível entre os caminhos conhecidos, ou `null`. */
export function lerTokenLocal(caminhos: string[] = caminhosDoToken()): string | null {
  for (const caminho of caminhos) {
    try {
      if (!existsSync(caminho)) continue
      const token = readFileSync(caminho, 'utf-8').trim()
      if (token) return token
    } catch {
      // Um caminho ilegível não pode derrubar a partida: tenta o próximo.
    }
  }
  return null
}

/**
 * Parâmetros com que a interface é carregada.
 *
 * O token entra pela query; o `useAuthStore` o consome e o apaga da URL na
 * primeira leitura, para não sobrar no histórico nem numa captura de tela.
 */
export function montarQueryDoRenderer(
  porta: number,
  token: string | null
): Record<string, string> {
  const query: Record<string, string> = { port: String(porta) }
  if (token) query.local_token = token
  return query
}
