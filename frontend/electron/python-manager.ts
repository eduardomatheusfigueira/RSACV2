/**
 * RSAC V2 — Python Backend Manager
 * Gerencia o spawn e lifecycle do processo Python (FastAPI + uvicorn).
 */

import { spawn, ChildProcess } from 'child_process'
import { app } from 'electron'
import { join } from 'path'
import net from 'net'

export class PythonManager {
  private process: ChildProcess | null = null
  private port: number = 0

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

    // Em produção, Python está embarcado; em dev, usa o do sistema
    const pythonPath = app.isPackaged
      ? join(process.resourcesPath, 'backend', 'python.exe')
      : 'python'

    const scriptPath = app.isPackaged
      ? join(process.resourcesPath, 'backend', 'run.py')
      : join(__dirname, '..', '..', '..', 'backend', 'run.py')

    console.log(`[PythonManager] Spawning: ${pythonPath} ${scriptPath} --port ${this.port}`)

    this.process = spawn(pythonPath, [
      scriptPath,
      '--port', String(this.port),
      '--host', '127.0.0.1'
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env }
    })

    // Log stdout/stderr do Python
    this.process.stdout?.on('data', (data) => {
      console.log(`[Python] ${data.toString().trim()}`)
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
      await new Promise((r) => setTimeout(r, 500))
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
