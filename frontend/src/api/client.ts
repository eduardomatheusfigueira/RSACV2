/**
 * RSAC V2 — HTTP & WebSocket Client
 * Cliente configurado para comunicação com o backend Python.
 */

import type {
  HealthResponse,
  Project,
  ProjectCreate,
  ProjectListResponse,
  ProjectUpdate,
  ProjectStats,
  Protocol,
  ProtocolUpdate,
  Paper,
  PaperCreate,
  PaperUpdate,
  PaperListResponse,
  HarvestStartRequest,
  HarvestRunListResponse,
  HarvestSourceInfo,
  AISettings,
  AISettingsUpdate,
  AIScreeningSingleResult,
  ProtocolSuggestions,
} from '@/types/api'

import { useLogStore } from '@/stores/useLogStore'

export interface ExtractionResponse {
  paper_id: string
  has_pdf: boolean
  pdf_path: string | null
  answers: Array<{
    id: string
    question_id: string
    answer: string
    ai_generated: boolean
  }>
}

export interface PrismaFlowData {
  identification: {
    total_records_identified: number
    sources_breakdown: Record<string, number>
    duplicates_removed: number
  }
  screening: {
    records_screened: number
    records_excluded: number
    records_pending: number
  }
  included: {
    studies_included_in_synthesis: number
  }
}

class APIClient {
  private port: number = 8000
  private baseUrl: string = 'http://127.0.0.1:8000/api/v1'

  /**
   * Configura a URL base do backend (chamado após receber a porta do Electron).
   */
  setPort(port: number): void {
    this.port = port
    this.baseUrl = `http://127.0.0.1:${port}/api/v1`
  }

  getPort(): number {
    return this.port
  }

  /**
   * Detecta a porta do backend a partir da query string (passada pelo Electron).
   */
  detectPort(): void {
    const params = new URLSearchParams(window.location.search)
    const port = params.get('port')
    if (port) {
      this.setPort(parseInt(port, 10))
    }
  }

  getWebSocketUrl(projectId: string): string {
    return `ws://127.0.0.1:${this.port}/api/v1/projects/${projectId}/harvest/ws`
  }

  getScreeningWebSocketUrl(projectId: string): string {
    return `ws://127.0.0.1:${this.port}/api/v1/projects/${projectId}/screening/ai/ws`
  }

  getExcelExportUrl(projectId: string): string {
    return `${this.baseUrl}/projects/${projectId}/export/excel`
  }

  getBibtexExportUrl(projectId: string): string {
    return `${this.baseUrl}/projects/${projectId}/export/bibtex`
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`
    const method = options.method || 'GET'
    const startTime = performance.now()
    const logStore = useLogStore.getState()

    // Determine source domain
    let source: 'API' | 'IA' | 'Coleta' | 'Triagem' | 'Extração' | 'Exportação' | 'Protocolo' = 'API'
    if (path.includes('/ai/') || path.includes('/ai-settings') || path.includes('/suggest')) source = 'IA'
    else if (path.includes('/harvest')) source = 'Coleta'
    else if (path.includes('/screening') || path.includes('/papers')) source = 'Triagem'
    else if (path.includes('/extractions')) source = 'Extração'
    else if (path.includes('/export')) source = 'Exportação'
    else if (path.includes('/protocol')) source = 'Protocolo'

    logStore.debug(source, `${method} ${path}`, options.body ? `Payload:\n${typeof options.body === 'string' ? options.body : JSON.stringify(options.body, null, 2)}` : undefined)

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      })

      const duration = Math.round(performance.now() - startTime)

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }))
        const errorMsg = error.detail || `HTTP ${response.status}`
        logStore.error(source, `${method} ${path} falhou (${response.status})`, `Erro: ${errorMsg}\nTempo: ${duration}ms`)
        throw new Error(errorMsg)
      }

      // 204 No Content
      if (response.status === 204) {
        logStore.success(source, `${method} ${path} [204 OK]`, undefined, duration)
        return undefined as T
      }

      const data = await response.json()
      logStore.success(source, `${method} ${path} [${response.status} OK]`, `Resposta:\n${JSON.stringify(data, null, 2).slice(0, 1000)}`, duration)
      return data
    } catch (err: any) {
      // Se deu erro de rede (Failed to fetch) e a porta configurada não for 8000, tenta fallback para 8000
      if (this.port !== 8000 && err.message?.includes('fetch')) {
        this.setPort(8000)
        return this.request<T>(path, options)
      }
      const duration = Math.round(performance.now() - startTime)
      if (!err.message?.includes('falhou')) {
        logStore.error(source, `${method} ${path} erro de rede`, `Detalhe: ${err.message}\nTempo: ${duration}ms`)
      }
      throw err
    }
  }

  // ── Health ────────────────────────────────────────────────────────

  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health')
  }

  // ── Projects ──────────────────────────────────────────────────────

  async listProjects(archived?: boolean): Promise<ProjectListResponse> {
    const params = archived !== undefined ? `?archived=${archived}` : ''
    return this.request<ProjectListResponse>(`/projects${params}`)
  }

  async createProject(data: ProjectCreate): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/projects/${id}`)
  }

  async updateProject(id: string, data: ProjectUpdate): Promise<Project> {
    return this.request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteProject(id: string): Promise<void> {
    return this.request<void>(`/projects/${id}`, { method: 'DELETE' })
  }

  async getProjectStats(id: string): Promise<ProjectStats> {
    return this.request<ProjectStats>(`/projects/${id}/stats`)
  }

  // ── Protocols ─────────────────────────────────────────────────────

  async getProtocol(projectId: string): Promise<Protocol> {
    return this.request<Protocol>(`/projects/${projectId}/protocol`)
  }

  async updateProtocol(projectId: string, data: ProtocolUpdate): Promise<Protocol> {
    return this.request<Protocol>(`/projects/${projectId}/protocol`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  // ── Papers ────────────────────────────────────────────────────────

  async listPapers(
    projectId: string,
    params?: {
      page?: number
      page_size?: number
      decision?: string
      search?: string
      source?: string
    }
  ): Promise<PaperListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    if (params?.decision) searchParams.set('decision', params.decision)
    if (params?.search) searchParams.set('search', params.search)
    if (params?.source) searchParams.set('source', params.source)

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return this.request<PaperListResponse>(`/projects/${projectId}/papers${qs}`)
  }

  async createPaper(projectId: string, data: PaperCreate): Promise<Paper> {
    return this.request<Paper>(`/projects/${projectId}/papers`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getPaper(projectId: string, paperId: string): Promise<Paper> {
    return this.request<Paper>(`/projects/${projectId}/papers/${paperId}`)
  }

  async updatePaper(projectId: string, paperId: string, data: PaperUpdate): Promise<Paper> {
    return this.request<Paper>(`/projects/${projectId}/papers/${paperId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  // ── Harvest ───────────────────────────────────────────────────────

  async getAvailableSources(projectId: string): Promise<{ sources: HarvestSourceInfo[] }> {
    return this.request<{ sources: HarvestSourceInfo[] }>(`/projects/${projectId}/harvest/sources`)
  }

  async startHarvest(projectId: string, data: HarvestStartRequest): Promise<any> {
    return this.request<any>(`/projects/${projectId}/harvest`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async listHarvestRuns(projectId: string): Promise<HarvestRunListResponse> {
    return this.request<HarvestRunListResponse>(`/projects/${projectId}/harvest/runs`)
  }

  // ── AI ────────────────────────────────────────────────────────────

  async getAISettings(): Promise<AISettings> {
    return this.request<AISettings>('/ai/settings')
  }

  async updateAISettings(data: AISettingsUpdate): Promise<AISettings> {
    return this.request<AISettings>('/ai/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async testAIConnection(): Promise<any> {
    return this.request<any>('/ai/test', {
      method: 'POST',
    })
  }

  async suggestProtocol(data: { title: string; methodology: string; description?: string }): Promise<ProtocolSuggestions> {
    return this.request<ProtocolSuggestions>('/ai/suggest-protocol', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async assistField(data: import('@/types/api').FieldAssistRequest): Promise<import('@/types/api').FieldAssistResponse> {
    return this.request<import('@/types/api').FieldAssistResponse>('/ai/assist-field', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async screenSinglePaperAI(projectId: string, paperId: string): Promise<AIScreeningSingleResult> {
    return this.request<AIScreeningSingleResult>(`/projects/${projectId}/screening/ai/single/${paperId}`, {
      method: 'POST',
    })
  }

  async startBatchScreeningAI(projectId: string, data: { limit?: number; concurrency?: number }): Promise<any> {
    return this.request<any>(`/projects/${projectId}/screening/ai/batch`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // ── Extraction (Triagem 2) ────────────────────────────────────────

  async getExtractionAnswers(projectId: string, paperId: string): Promise<ExtractionResponse> {
    return this.request<ExtractionResponse>(`/projects/${projectId}/papers/${paperId}/extraction`)
  }

  async updateExtractionAnswers(projectId: string, paperId: string, answers: Record<string, string>): Promise<any> {
    return this.request<any>(`/projects/${projectId}/papers/${paperId}/extraction`, {
      method: 'PUT',
      body: JSON.stringify(answers),
    })
  }

  async extractAnswersWithAI(projectId: string, paperId: string): Promise<any> {
    return this.request<any>(`/projects/${projectId}/papers/${paperId}/extraction/ai`, {
      method: 'POST',
    })
  }

  async downloadPaperPDF(projectId: string, paperId: string): Promise<any> {
    return this.request<any>(`/projects/${projectId}/papers/${paperId}/extraction/pdf/download`, {
      method: 'POST',
    })
  }

  // ── Export ────────────────────────────────────────────────────────

  async getPrismaFlow(projectId: string): Promise<PrismaFlowData> {
    return this.request<PrismaFlowData>(`/projects/${projectId}/export/prisma`)
  }
}

export const api = new APIClient()
