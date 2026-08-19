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
  ExtractionResponse,
} from '@/types/api'

import { useLogStore } from '@/stores/useLogStore'

// A forma da resposta de extração vive em `types/api.ts` (junto do estado do
// PDF que ela carrega); aqui apenas reexportamos para quem importa do cliente.
export type { ExtractionResponse }

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
  private baseUrl: string = (() => {
    // 1. Verificar query param direto no carregamento inicial (?api_url= ou #/?api_url=)
    if (typeof window !== 'undefined') {
      try {
        const searchParams = new URLSearchParams(window.location.search)
        const urlFromSearch = searchParams.get('api_url')
        if (urlFromSearch && urlFromSearch.trim()) {
          const clean = urlFromSearch.trim().replace(/\/+$/, '')
          const finalUrl = clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`
          localStorage.setItem('rsac_api_url', finalUrl)
          return finalUrl
        }
        if (window.location.hash.includes('?')) {
          const hashQuery = window.location.hash.split('?')[1]
          const hashParams = new URLSearchParams(hashQuery)
          const urlFromHash = hashParams.get('api_url')
          if (urlFromHash && urlFromHash.trim()) {
            const clean = urlFromHash.trim().replace(/\/+$/, '')
            const finalUrl = clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`
            localStorage.setItem('rsac_api_url', finalUrl)
            return finalUrl
          }
        }
        // 2. Verificar URL previamente salva no localStorage
        const saved = localStorage.getItem('rsac_api_url')
        if (saved && saved.trim()) {
          const clean = saved.trim().replace(/\/+$/, '')
          return clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`
        }
      } catch {
        // Ignora erros de acesso a window/localStorage
      }
    }
    // 3. Verificar variável de ambiente do Vite
    const envUrl = (import.meta as any).env?.VITE_API_URL
    if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
      const clean = envUrl.trim().replace(/\/+$/, '')
      return clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`
    }
    // 4. Detecção automática se estiver no navegador Web (servido pelo backend ou Cloudflare)
    if (typeof window !== 'undefined' && window.location.protocol.startsWith('http')) {
      if (!window.location.host.includes(':5173')) {
        return `${window.location.origin}/api/v1`
      }
    }
    return 'http://127.0.0.1:8000/api/v1'
  })()

  /**
   * Configura a URL base do backend manualmente e persiste no navegador.
   */
  setBaseUrl(url: string): void {
    const clean = url.trim().replace(/\/+$/, '')
    this.baseUrl = clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('rsac_api_url', this.baseUrl)
      } catch {
        // Ignora erros
      }
    }
  }

  /**
   * Configura a URL base a partir da porta (chamado pelo Electron ou ambiente local).
   */
  setPort(port: number): void {
    this.port = port
    const envUrl = (import.meta as any).env?.VITE_API_URL
    const saved = typeof window !== 'undefined' ? localStorage.getItem('rsac_api_url') : null
    if (!envUrl && !saved) {
      this.baseUrl = `http://127.0.0.1:${port}/api/v1`
    }
  }

  getPort(): number {
    return this.port
  }

  getBaseUrl(): string {
    return this.baseUrl
  }

  /**
   * Detecta a porta ou URL do backend a partir da query string (suporta search e hash).
   */
  detectPort(): void {
    if (typeof window === 'undefined') return

    // 1. Procurar em window.location.search (?api_url=... ou ?port=...)
    const params = new URLSearchParams(window.location.search)
    let apiUrl = params.get('api_url')
    let port = params.get('port')

    // 2. Se não achou, procurar em window.location.hash (#/.../?api_url=...)
    if (!apiUrl && !port && window.location.hash.includes('?')) {
      const hashQuery = window.location.hash.split('?')[1]
      const hashParams = new URLSearchParams(hashQuery)
      apiUrl = hashParams.get('api_url')
      port = hashParams.get('port')
    }

    if (apiUrl) {
      this.setBaseUrl(apiUrl)
      return
    }
    if (port) {
      this.setPort(parseInt(port, 10))
    }
  }

  private getWsBaseUrl(): string {
    const isSecure = this.baseUrl.startsWith('https://')
    const protocol = isSecure ? 'wss://' : 'ws://'
    const hostAndPath = this.baseUrl.replace(/^https?:\/\//, '')
    return `${protocol}${hostAndPath}`
  }

  getWebSocketUrl(projectId: string): string {
    return `${this.getWsBaseUrl()}/projects/${projectId}/harvest/ws`
  }

  getScreeningWebSocketUrl(projectId: string): string {
    return `${this.getWsBaseUrl()}/projects/${projectId}/screening/ai/ws`
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
    let source: 'API' | 'Assistência' | 'IA' | 'Coleta' | 'Triagem' | 'Extração' | 'Exportação' | 'Protocolo' = 'API'
    if (path.includes('/ai/') || path.includes('/ai-settings') || path.includes('/suggest')) source = 'Assistência'
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
      // Se deu erro de rede (Failed to fetch) e a porta configurada não for 8000, tenta fallback para 8000 (apenas em dev local)
      const envUrl = (import.meta as any).env?.VITE_API_URL
      if (!envUrl && this.port !== 8000 && err.message?.includes('fetch')) {
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

  async cancelHarvest(projectId: string): Promise<any> {
    return this.request<any>(`/projects/${projectId}/harvest/cancel`, {
      method: 'POST',
    })
  }

  async getHarvestStatus(projectId: string): Promise<any> {
    return this.request<any>(`/projects/${projectId}/harvest/status`)
  }

  async listHarvestRuns(projectId: string): Promise<HarvestRunListResponse> {
    return this.request<HarvestRunListResponse>(`/projects/${projectId}/harvest/runs`)
  }

  // ── Deduplication & Reports ───────────────────────────────────────

  async deduplicateProject(projectId: string): Promise<{ status: string; data: import('@/types/api').DeduplicationReport }> {
    return this.request<{ status: string; data: import('@/types/api').DeduplicationReport }>(
      `/projects/${projectId}/deduplicate`,
      { method: 'POST' }
    )
  }

  async getDeduplicationReport(projectId: string): Promise<import('@/types/api').DeduplicationReport> {
    return this.request<import('@/types/api').DeduplicationReport>(`/projects/${projectId}/deduplicate/report`)
  }

  getDeduplicationDownloadUrl(projectId: string): string {
    return `${this.baseUrl}/projects/${projectId}/deduplicate/download`
  }

  // ── Source Credentials ────────────────────────────────────────────

  async getSourceCredentials(): Promise<import('@/types/api').SourceCredential[]> {
    return this.request<import('@/types/api').SourceCredential[]>('/settings/sources')
  }

  async updateSourceCredential(
    sourceName: string,
    data: import('@/types/api').SourceCredentialUpdate
  ): Promise<import('@/types/api').SourceCredential> {
    return this.request<import('@/types/api').SourceCredential>(`/settings/sources/${sourceName}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteSourceCredential(sourceName: string): Promise<any> {
    return this.request<any>(`/settings/sources/${sourceName}`, {
      method: 'DELETE',
    })
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

  async extractAnswersWithAI(projectId: string, paperId: string, questionId?: string): Promise<any> {
    const query = questionId ? `?question_id=${encodeURIComponent(questionId)}` : ''
    return this.request<any>(`/projects/${projectId}/papers/${paperId}/extraction/ai${query}`, {
      method: 'POST',
    })
  }

  /**
   * Busca o PDF por todas as vias disponíveis (DOI, Unpaywall, OpenAlex,
   * Crossref, Europe PMC, padrões de repositório, raspagem da landing page).
   * Não lança quando não encontra: a falha vem no corpo, com a trilha do que
   * foi tentado, para que a interface possa orientar o próximo passo.
   */
  async acquirePaperPDF(
    projectId: string,
    paperId: string
  ): Promise<import('@/types/api').PdfAcquisitionResult> {
    return this.request<import('@/types/api').PdfAcquisitionResult>(
      `/projects/${projectId}/papers/${paperId}/extraction/pdf/acquire`,
      { method: 'POST' }
    )
  }

  async downloadPaperPDF(
    projectId: string,
    paperId: string
  ): Promise<import('@/types/api').PdfAcquisitionResult> {
    return this.acquirePaperPDF(projectId, paperId)
  }

  async getPaperPdfStatus(
    projectId: string,
    paperId: string
  ): Promise<import('@/types/api').PdfState & { paper_id: string }> {
    return this.request(`/projects/${projectId}/papers/${paperId}/extraction/pdf/status`)
  }

  async getPaperPdfCandidates(
    projectId: string,
    paperId: string
  ): Promise<{ paper_id: string; total: number; candidates: import('@/types/api').PdfCandidate[] }> {
    return this.request(`/projects/${projectId}/papers/${paperId}/extraction/pdf/candidates`)
  }

  async startPdfBatch(
    projectId: string,
    onlyMissing = true,
    decision = 'Incluído'
  ): Promise<import('@/types/api').PdfBatchState> {
    const params = new URLSearchParams({
      only_missing: String(onlyMissing),
      decision,
    })
    return this.request(`/projects/${projectId}/extraction/pdf/batch?${params}`, { method: 'POST' })
  }

  async getPdfBatchStatus(projectId: string): Promise<import('@/types/api').PdfBatchState> {
    return this.request(`/projects/${projectId}/extraction/pdf/batch`)
  }

  async cancelPdfBatch(projectId: string): Promise<{ status: string }> {
    return this.request(`/projects/${projectId}/extraction/pdf/batch`, { method: 'DELETE' })
  }

  async uploadPaperPDF(projectId: string, paperId: string, file: File): Promise<{ status: string; pdf_path: string }> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${this.baseUrl}/projects/${projectId}/papers/${paperId}/extraction/pdf/upload`, {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Erro ao enviar o arquivo PDF.' }))
      throw new Error(err.detail || 'Falha no upload do PDF.')
    }
    return res.json()
  }

  /** URL do arquivo servido pelo backend — usada pelo visualizador embutido. */
  getPaperPdfUrl(projectId: string, paperId: string, forceDownload = false): string {
    const suffix = forceDownload ? '?download=true' : ''
    return `${this.baseUrl}/projects/${projectId}/papers/${paperId}/extraction/pdf${suffix}`
  }

  async getPaperPdfText(
    projectId: string,
    paperId: string,
    refresh = false
  ): Promise<import('@/types/api').PdfTextResponse> {
    const suffix = refresh ? '?refresh=true' : ''
    return this.request<import('@/types/api').PdfTextResponse>(
      `/projects/${projectId}/papers/${paperId}/extraction/pdf/text${suffix}`
    )
  }

  async deletePaperPDF(projectId: string, paperId: string): Promise<{ status: string }> {
    return this.request<{ status: string }>(`/projects/${projectId}/papers/${paperId}/extraction/pdf`, {
      method: 'DELETE',
    })
  }

  async updatePaperDownloadUrl(projectId: string, paperId: string, downloadUrl: string): Promise<any> {
    return this.request<any>(`/projects/${projectId}/papers/${paperId}/extraction/download-url`, {
      method: 'PATCH',
      body: JSON.stringify({ download_url: downloadUrl }),
    })
  }

  async getExtractionSummary(projectId: string): Promise<import('@/types/api').ExtractionSummaryResponse> {
    return this.request<import('@/types/api').ExtractionSummaryResponse>(`/projects/${projectId}/extraction/summary`)
  }

  // ── Export ────────────────────────────────────────────────────────

  async getPrismaFlow(projectId: string): Promise<PrismaFlowData> {
    return this.request<PrismaFlowData>(`/projects/${projectId}/export/prisma`)
  }

  // ── Profile & Keys Portability ────────────────────────────────────

  async exportKeys(): Promise<import('@/types/api').KeysBackupData> {
    return this.request<import('@/types/api').KeysBackupData>('/profile/keys/export')
  }

  async importKeys(payload: { raw_content?: string } | Record<string, any>): Promise<import('@/types/api').KeysImportResponse> {
    return this.request<import('@/types/api').KeysImportResponse>('/profile/keys/import', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async exportProfile(sessionPrefs?: import('@/types/api').ProfileSessionPreferences): Promise<import('@/types/api').ProfileBackupData> {
    return this.request<import('@/types/api').ProfileBackupData>('/profile/export', {
      method: 'POST',
      body: JSON.stringify({ session_preferences: sessionPrefs }),
    })
  }

  async importProfile(profileData: any): Promise<import('@/types/api').ProfileImportResponse> {
    return this.request<import('@/types/api').ProfileImportResponse>('/profile/import', {
      method: 'POST',
      body: JSON.stringify(profileData),
    })
  }
}

export const api = new APIClient()
