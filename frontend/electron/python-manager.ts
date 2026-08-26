/**
 * RSAC V2 — Python Backend Manager
 * Gerencia o spawn e lifecycle do processo Python (FastAPI + uvicorn).
 */

import { spawn, ChildProcess } from 'child_process'
import { app } from 'electron'
import { existsSync, readFileSync } from 'fs'
import { homedir } from 'os'
import { join } from 'path'
import net from 'net'

/**
 * Prefixo da linha que o backend imprime na saída padrão para dizer onde
 * gravou a pasta de dados e o arquivo de token (ver `_anunciar_pasta_de_dados`
 * em `backend/app/main.py`). É o que substitui a adivinhação de caminho que
 * cada lançador fazia do seu jeito.
 */
const PREFIXO_DE_HANDSHAKE = 'RSAC_RUNTIME'

export class PythonManager {
  private process: ChildProcess | null = null
  private port: number = 0
  /** Caminho do `runtime_token`, informado pelo próprio backend. */
  private tokenFile: string | null = null

  /**
   * Encontra uma porta TCP disponível no sistema.
   */
  private findFreePort(): Promise<number> {
    return new Promise((resolve, reject) => {
      const server = net.createServer()
      server.listen(0, '127.0.0.1', () => {
        const address = server.address() as net.AddressInfo
        const port = address.port
        server.close(() => resolve(port))
      })
      server.on('error', reject)
    })
  }

  /**
   * Lê a linha de handshake da saída do backend, se for uma.
   */
  private absorverHandshake(linha: string): void {
    const casamento = new RegExp(`^${PREFIXO_DE_HANDSHAKE}\\s+(\\w+)=(.+)$`).exec(linha)
    if (!casamento) return
    const [, chave, valor] = casamento
    if (chave === 'token_file') {
      this.tokenFile = valor.trim()
    }
  }

  /**
   * Inicia o backend Python (FastAPI + uvicorn).
   * Retorna a porta onde o backend está escutando.
   */
  async start(): Promise<number> {
    // Em dev, se o backend na porta 8000 já estiver rodando, reutiliza-o diretamente
    if (!app.isPackaged) {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/v1/health')
        if (response.ok) {
          console.log('[PythonManager] Backend Python ativo detectado na porta 8000. Reutilizando.')
          this.port = 8000
          return 8000
        }
      } catch {
        // Backend não está rodando na porta 8000, prossegue para spawn
      }
    }

    this.port = await this.findFreePort()

    let exePath: string
    let exeArgs: string[]

    const standaloneDirExe = join(process.resourcesPath, 'backend', 'rsac-backend', 'rsac-backend.exe')
    const standaloneSingleExe = join(process.resourcesPath, 'backend', 'rsac-backend.exe')

    if (app.isPackaged) {
      if (existsSync(standaloneDirExe)) {
        exePath = standaloneDirExe
        exeArgs = ['--port', String(this.port), '--host', '127.0.0.1']
      } else if (existsSync(standaloneSingleExe)) {
        exePath = standaloneSingleExe
        exeArgs = ['--port', String(this.port), '--host', '127.0.0.1']
      } else {
        exePath = join(process.resourcesPath, 'backend', 'python.exe')
        exeArgs = [
          join(process.resourcesPath, 'backend', 'run.py'),
          '--port', String(this.port),
          '--host', '127.0.0.1'
        ]
      }
    } else {
      exePath = 'python'
      exeArgs = [
        join(__dirname, '..', '..', '..', 'backend', 'run.py'),
        '--port', String(this.port),
        '--host', '127.0.0.1'
      ]
    }

    const backendCwd = app.isPackaged
      ? (existsSync(standaloneDirExe) ? join(process.resourcesPath, 'backend', 'rsac-backend') : join(process.resourcesPath, 'backend'))
      : join(__dirname, '..', '..', '..', 'backend')

    console.log(`[PythonManager] Spawning: ${exePath} ${exeArgs.join(' ')} (cwd: ${backendCwd})`)

    this.process = spawn(exePath, exeArgs, {
      cwd: backendCwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env }
    })

    // Log stdout/stderr do Python
    this.process.stdout?.on('data', (data) => {
      const texto = data.toString()
      texto.split(/\r?\n/).forEach((linha: string) => {
        const limpa = linha.trim()
        if (!limpa) return
        this.absorverHandshake(limpa)
        console.log(`[Python] ${limpa}`)
      })
    })

    this.process.stderr?.on('data', (data) => {
      console.log(`[Python:err] ${data.toString().trim()}`)
    })

    this.process.on('exit', (code) => {
      console.log(`[PythonManager] Processo Python encerrado com código ${code}`)
      this.process = null
    })

    // Aguardar health check
    await this.waitForReady()
    return this.port
  }

  /**
   * Caminhos onde o `runtime_token` pode estar quando o handshake não chegou.
   *
   * Espelham o que o `platformdirs.user_data_dir("RSAC")` produz em cada
   * sistema. É recuo, não caminho principal: quem sabe onde o arquivo está é
   * o processo que o escreveu.
   */
  private caminhosProvaveisDoToken(): string[] {
    const doAmbiente = process.env.RSAC_DATA_DIR
    const caminhos: string[] = []
    if (doAmbiente) caminhos.push(join(doAmbiente, 'runtime_token'))

    if (process.platform === 'win32') {
      const localAppData = process.env.LOCALAPPDATA
      if (localAppData) {
        caminhos.push(join(localAppData, 'RSAC', 'RSAC', 'runtime_token'))
        caminhos.push(join(localAppData, 'RSAC', 'runtime_token'))
      }
    } else if (process.platform === 'darwin') {
      caminhos.push(join(homedir(), 'Library', 'Application Support', 'RSAC', 'runtime_token'))
    } else {
      const xdg = process.env.XDG_DATA_HOME || join(homedir(), '.local', 'share')
      caminhos.push(join(xdg, 'RSAC', 'runtime_token'))
    }
    return caminhos
  }

  /**
   * Lê o token local que autentica o app de mesa sem tela de login.
   *
   * Sem isto o app instalado chegava ao backend e caía na tela de acesso, que
   * no perfil desktop manda criar conta pelo terminal — um beco sem saída para
   * quem só instalou o programa.
   */
  lerTokenLocal(): string | null {
    const candidatos = [
      ...(this.tokenFile ? [this.tokenFile] : []),
      ...this.caminhosProvaveisDoToken()
    ]
    for (const caminho of candidatos) {
      try {
        if (!existsSync(caminho)) continue
        const conteudo = readFileSync(caminho, 'utf-8').trim()
        if (conteudo) return conteudo
      } catch {
        // Arquivo ilegível: tenta o próximo candidato.
      }
    }
    return null
  }

  /**
   * Aguarda o backend responder ao health check.
   */
  private async waitForReady(timeoutMs = 30000): Promise<void> {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
      try {
        const response = await fetch(`http://127.0.0.1:${this.port}/api/v1/health`)
        if (response.ok) {
          console.log('[PythonManager] Backend respondendo — health check OK')
          return
        }
      } catch {
        // Backend ainda não está pronto, retry
      }
      await new Promise((r) => setTimeout(r, 250))
    }
    throw new Error(`Backend Python não respondeu em ${timeoutMs}ms`)
  }

  /**
   * Encerra o processo Python gracefully.
   */
  async stop(): Promise<void> {
    if (this.process) {
      console.log('[PythonManager] Encerrando backend Python...')
      this.process.kill('SIGTERM')

      // Aguardar 5s para encerramento graceful, depois forçar
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          if (this.process) {
            this.process.kill('SIGKILL')
          }
          resolve()
        }, 5000)

        this.process?.on('exit', () => {
          clearTimeout(timeout)
          resolve()
        })
      })

      this.process = null
      console.log('[PythonManager] Backend Python encerrado.')
    }
  }

  get apiPort(): number {
    return this.port
  }

  get isRunning(): boolean {
    return this.process !== null && !this.process.killed
  }
}
