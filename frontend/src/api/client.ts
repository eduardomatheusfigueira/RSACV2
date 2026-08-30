/**
 * Revsist — HTTP & WebSocket Client
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
  ProtocolCatalog,
  ProtocolReadiness,
  SearchStrategy,
  SearchExecution,
  ProtocolVersion,
  ProtocolAmendment,
  ChecklistAudit,
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
  TeamResponse,
  ProjectMember,
  ProjectInvitation,
  ProjectInvitationCreate,
  AcceptInvitationResponse,
  ReopenScreeningPayload,
  ReopenScreeningResponse,
} from '@/types/api'

import { useLogStore } from '@/stores/useLogStore'
import { analisarUrlDeBackend } from '@/api/backendUrl'
import { construirQueryDeInsights } from '@/pages/insightsFormat'

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

/**
 * O erro veio de um cancelamento pedido pela interface?
 *
 * `AbortController` é o único jeito de soltar a tela de uma requisição longa
 * de assistência — o servidor termina o trabalho dele, mas quem esperava fica
 * livre. Quem chama usa isto para não anunciar como falha o que foi escolha.
 */
export function foiCancelado(err: unknown): boolean {
  return err instanceof DOMException
    ? err.name === 'AbortError'
    : (err as any)?.name === 'AbortError'
}

/** Onde o token de sessão é guardado entre recarregamentos da aba. */
const SESSION_STORAGE_KEY = 'rsac_session_token'

/**
 * Onde o endereço do backend é guardado.
 *
 * `sessionStorage`, não `localStorage`: era a persistência permanente que
 * fazia o sequestro de `api_url` sobreviver ao fechamento da aba (doc 29
 * §29.12).
 */
const BACKEND_URL_KEY = 'rsac_api_url'

/** Chamado quando o backend responde 401 — a aplicação volta para o login. */
type UnauthorizedHandler = () => void

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

class APIClient {
  private port: number = 8000

  /**
   * Token de sessão.
   *
   * Fica em `sessionStorage`, não em `localStorage`: sobrevive ao recarregar a
   * página, que é o que o uso normal exige, e morre ao fechar a aba — de modo
   * que um computador compartilhado não deixa a sessão pendurada. Quando a SPA
   * é servida pelo próprio backend, o cookie `HttpOnly` já resolve e este
   * token é apenas redundância; ele existe para o cliente hospedado em outra
   * origem (Netlify, Vite em desenvolvimento), que não recebe o cookie.
   */
  private sessionToken: string | null = (() => {
    if (typeof window === 'undefined') return null
    try {
      return sessionStorage.getItem(SESSION_STORAGE_KEY)
    } catch {
      return null
    }
  })()

  private onUnauthorized: UnauthorizedHandler | null = null
  /**
   * Endereço do backend.
   *
   * A resolução **não** consulta mais `?api_url=` aqui: aceitar o parâmetro no
   * construtor era o que permitia sequestrar o cliente com um link (doc 28
   * V-08). Quem trata o parâmetro é `AuthGate`, que pede confirmação humana
   * nomeando o host antes de gravar qualquer coisa.
   *
   * A persistência é em `sessionStorage`, não em `localStorage`: um sequestro
   * que passe pela confirmação morre ao fechar a aba, em vez de ficar
   * pendurado para sempre.
   */
  private baseUrl: string = (() => {
    if (typeof window !== 'undefined') {
      try {
        const salva = sessionStorage.getItem(BACKEND_URL_KEY)
        if (salva && salva.trim()) return salva.trim()
      } catch {
        // Armazenamento bloqueado pelo navegador: cai na detecção automática.
      }
    }

    const envUrl = (import.meta as any).env?.VITE_API_URL
    if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
      const clean = envUrl.trim().replace(/\/+$/, '')
      return clean.endsWith('/api/v1') ? clean : `${clean}/api/v1`
    }

    // Servida pelo próprio backend (o caso do túnel): a origem da página é o
    // endereço da API, e não há o que confirmar — é o mesmo servidor.
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
  /**
   * Aponta o cliente para outro backend.
   *
   * Valida o endereço (protocolo e criptografia) antes de aceitar — a versão
   * anterior gravava qualquer string. Quem chama é responsável por já ter
   * obtido a confirmação humana; a validação aqui é a última barreira.
   */
  setBaseUrl(url: string): void {
    const destino = analisarUrlDeBackend(url)
    this.baseUrl = destino.url

    if (typeof window !== 'undefined') {
      try {
        sessionStorage.setItem(BACKEND_URL_KEY, destino.url)
        // Remove o resquício da versão que persistia para sempre.
        localStorage.removeItem(BACKEND_URL_KEY)
      } catch {
        // Armazenamento bloqueado: o endereço vale só para esta sessão.
      }
    }
  }

  /** Host do backend em uso, para exibição permanente na interface. */
  getBackendHost(): string {
    try {
      return new URL(this.baseUrl).host
    } catch {
      return this.baseUrl
    }
  }

  /**
   * Endereço que inicia a entrada com Google.
   *
   * É uma navegação de página inteira, e não uma requisição: o fluxo OAuth
   * termina num redirecionamento que precisa gravar o cookie de sessão no
   * navegador. Buscar isto por `fetch` traria o HTML do Google para dentro de
   * um XHR e não abriria sessão nenhuma.
   */
  googleLoginUrl(destino = '/app'): string {
    const base = this.baseUrl.replace(/\/$/, '')
    return `${base}/auth/google/start?redirect_after=${encodeURIComponent(destino)}`
  }

  /**
   * Configura a URL base a partir da porta (chamado pelo Electron ou ambiente local).
   */
  setPort(port: number): void {
    this.port = port
    const envUrl = (import.meta as any).env?.VITE_API_URL
    const salva =
      typeof window !== 'undefined' ? sessionStorage.getItem(BACKEND_URL_KEY) : null
    if (!envUrl && !salva) {
      this.baseUrl = `http://127.0.0.1:${port}/api/v1`
    }
  }

  getPort(): number {
    return this.port
  }

  /**
   * A página tem chance real de alcançar um backend em `127.0.0.1`?
   *
   * Só quando ela mesma foi carregada do loopback (dev, ou o backend servindo
   * a SPA) ou de `file://` (app de mesa). Numa origem remota — sobretudo em
   * https, como a build publicada — apontar para loopback é impossível por
   * conteúdo misto e CORS: o recuo não pode dar certo, e ainda troca a causa
   * real ("nenhum servidor configurado") por uma parede de erros que aponta
   * para o endereço errado, inclusive no diagnóstico mostrado ao usuário.
   */
  podeAlcancarLoopback(): boolean {
    if (typeof window === 'undefined') return true
    const { protocol, hostname } = window.location
    if (protocol === 'file:') return true
    return (
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '[::1]' ||
      hostname === '::1'
    )
  }

  getBaseUrl(): string {
    return this.baseUrl
  }

  /**
   * Detecta a porta do backend passada pelo Electron.
   *
   * Deixou de aceitar `api_url`: o endereço do backend só muda por
   * confirmação humana explícita, tratada no `AuthGate` (doc 29 §29.12).
   */
  detectPort(): void {
    if (typeof window === 'undefined') return

    const params = new URLSearchParams(window.location.search)
    let port = params.get('port')

    if (!port && window.location.hash.includes('?')) {
      const hashParams = new URLSearchParams(window.location.hash.split('?')[1])
      port = hashParams.get('port')
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

  /**
   * O navegador não deixa mandar cabeçalho ao abrir um WebSocket, e o cookie
   * não viaja entre origens diferentes — por isso o token vai na query. O
   * endereço de um WebSocket não entra em histórico nem em `Referer`, então
   * não é o mesmo risco de pôr credencial numa URL comum.
   */
  private withSessionToken(url: string): string {
    if (!this.sessionToken) return url
    const separador = url.includes('?') ? '&' : '?'
    return `${url}${separador}token=${encodeURIComponent(this.sessionToken)}`
  }

  getWebSocketUrl(projectId: string): string {
    return this.withSessionToken(`${this.getWsBaseUrl()}/projects/${projectId}/harvest/ws`)
  }

  getScreeningWebSocketUrl(projectId: string): string {
    return this.withSessionToken(`${this.getWsBaseUrl()}/projects/${projectId}/screening/ai/ws`)
  }

  getExcelExportUrl(projectId: string): string {
    return `${this.baseUrl}/projects/${projectId}/export/excel`
  }

  getBibtexExportUrl(projectId: string): string {
    return `${this.baseUrl}/projects/${projectId}/export/bibtex`
  }

  setSessionToken(token: string | null): void {
    this.sessionToken = token
    if (typeof window === 'undefined') return
    try {
      if (token) sessionStorage.setItem(SESSION_STORAGE_KEY, token)
      else sessionStorage.removeItem(SESSION_STORAGE_KEY)
    } catch {
      // Navegador com armazenamento bloqueado: o cookie ainda cobre o caso
      // de mesma origem, então não há por que interromper o fluxo.
    }
  }

  getSessionToken(): string | null {
    return this.sessionToken
  }

  /** Registra o que fazer quando o backend recusar a sessão. */
  setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
    this.onUnauthorized = handler
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
        // `include` faz o cookie de sessão viajar quando a SPA é servida pelo
        // próprio backend; o Bearer cobre o caso de origem diferente.
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(this.sessionToken ? { Authorization: `Bearer ${this.sessionToken}` } : {}),
          ...options.headers,
        },
      })

      const duration = Math.round(performance.now() - startTime)

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }))
        let errorMsg = error.detail || `HTTP ${response.status}`
        if (Array.isArray(errorMsg)) {
          errorMsg = errorMsg
            .map((e: any) => {
              const campo = e.loc ? e.loc.slice(1).join('.') : ''
              const msg = e.msg || JSON.stringify(e)
              return campo ? `${campo}: ${msg}` : msg
            })
            .join(' | ')
        } else if (typeof errorMsg === 'object' && errorMsg !== null) {
          errorMsg = errorMsg.msg || errorMsg.message || JSON.stringify(errorMsg)
        }
        logStore.error(source, `${method} ${path} falhou (${response.status})`, `Erro: ${errorMsg}\nTempo: ${duration}ms`)

        // Sessão expirada ou revogada: descarta o token e devolve o usuário ao
        // login em vez de deixar a interface tentando de novo em silêncio.
        if (response.status === 401 && !path.startsWith('/auth/')) {
          this.setSessionToken(null)
          this.onUnauthorized?.()
        }
        throw new ApiError(response.status, String(errorMsg))
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
      if (err instanceof ApiError) {
        throw err
      }

      // Pedido interrompido pelo pesquisador. Não é falha: registrar como erro
      // encheria o log de vermelho por uma ação deliberada — e o recuo para a
      // porta 8000 logo abaixo tentaria "consertar" o que ninguém quebrou.
      if (foiCancelado(err)) {
        logStore.info(source, `${method} ${path} cancelado`)
        throw err
      }

      // Erro de rede: recuar para a porta padrão 8000 só faz sentido onde o
      // backend poderia estar na máquina de quem abriu a página. O comentário
      // aqui dizia "apenas em dev local", mas o código não impunha isso.
      const envUrl = (import.meta as any).env?.VITE_API_URL
      if (
        !envUrl &&
        this.podeAlcancarLoopback() &&
        this.port !== 8000 &&
        err.message?.includes('fetch')
      ) {
        this.setPort(8000)
        return this.request<T>(path, options)
      }
      const duration = Math.round(performance.now() - startTime)
      logStore.error(source, `${method} ${path} erro de rede`, `Detalhe: ${err.message}\nTempo: ${duration}ms`)
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

  async reopenScreening(
    projectId: string,
    data: ReopenScreeningPayload = {}
  ): Promise<ReopenScreeningResponse> {
    return this.request<ReopenScreeningResponse>(`/projects/${projectId}/screening/reabrir`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getProjectStats(id: string): Promise<ProjectStats> {
    return this.request<ProjectStats>(`/projects/${id}/stats`)
  }

  // ── Protocols (4 Eixos, Estratégia, Versões e Auditoria) ──────────

  async getProtocolCatalog(): Promise<ProtocolCatalog> {
    return this.request<ProtocolCatalog>('/protocol-catalog')
  }

  async getProtocol(projectId: string): Promise<Protocol> {
    return this.request<Protocol>(`/projects/${projectId}/protocol`)
  }

  async updateProtocol(projectId: string, data: ProtocolUpdate, ifMatch?: string): Promise<Protocol> {
    const headers: Record<string, string> = {}
    if (ifMatch) {
      headers['If-Match'] = ifMatch
    }
    return this.request<Protocol>(`/projects/${projectId}/protocol`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(data),
    })
  }

  async switchProtocolMode(projectId: string, mode: 'simplificado' | 'completo'): Promise<Protocol> {
    return this.request<Protocol>(`/projects/${projectId}/protocol/mode`, {
      method: 'POST',
      body: JSON.stringify({ mode }),
    })
  }

  async switchReviewDesign(projectId: string, review_design: string): Promise<any> {
    return this.request<any>(`/projects/${projectId}/protocol/design`, {
      method: 'POST',
      body: JSON.stringify({ review_design }),
    })
  }

  async getProtocolReadiness(projectId: string): Promise<ProtocolReadiness> {
    return this.request<ProtocolReadiness>(`/projects/${projectId}/protocol/readiness`)
  }

  async getSearchStrategies(projectId: string): Promise<SearchStrategy[]> {
    return this.request<SearchStrategy[]>(`/projects/${projectId}/protocol/search-strategy`)
  }

  async saveSearchStrategy(projectId: string, data: any): Promise<SearchStrategy> {
    return this.request<SearchStrategy>(`/projects/${projectId}/protocol/search-strategy`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async renderSearchStrategy(
    projectId: string,
    data: { database: string; blocks: any[]; combination?: string; limits?: any }
  ): Promise<any> {
    return this.request<any>(`/projects/${projectId}/protocol/search-strategy/render`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async analyzePressReview(
    projectId: string,
    data: { blocks: any[]; combination?: string }
  ): Promise<any> {
    return this.request<any>(`/projects/${projectId}/protocol/search-strategy/press`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async freezeProtocolVersion(projectId: string, label: string): Promise<ProtocolVersion> {
    return this.request<ProtocolVersion>(`/projects/${projectId}/protocol/freeze`, {
      method: 'POST',
      body: JSON.stringify({ label }),
    })
  }

  async listProtocolVersions(projectId: string): Promise<ProtocolVersion[]> {
    return this.request<ProtocolVersion[]>(`/projects/${projectId}/protocol/versions`)
  }

  async createProtocolAmendment(
    projectId: string,
    data: { from_version: string; to_version: string; reason: string; project_phase: string; diff?: any }
  ): Promise<ProtocolAmendment> {
    return this.request<ProtocolAmendment>(`/projects/${projectId}/protocol/amendments`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async listProtocolAmendments(projectId: string): Promise<ProtocolAmendment[]> {
    return this.request<ProtocolAmendment[]>(`/projects/${projectId}/protocol/amendments`)
  }

  async getChecklistAudits(projectId: string, guideline?: string): Promise<ChecklistAudit[]> {
    const qs = guideline ? `?guideline=${encodeURIComponent(guideline)}` : ''
    return this.request<ChecklistAudit[]>(`/projects/${projectId}/protocol/checklist-audit${qs}`)
  }

  async updateChecklistAuditItem(
    projectId: string,
    data: { guideline: string; item_id: string; state: string; location?: string; justification?: string }
  ): Promise<ChecklistAudit> {
    return this.request<ChecklistAudit>(`/projects/${projectId}/protocol/checklist-audit`, {
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
      screening_status?: string
      search?: string
      source?: string
    }
  ): Promise<PaperListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    if (params?.decision) searchParams.set('decision', params.decision)
    if (params?.screening_status) searchParams.set('screening_status', params.screening_status)
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

  async updatePaper(projectId: string, paperId: string, data: PaperUpdate, ifMatch?: string): Promise<Paper> {
    const headers: Record<string, string> = {}
    if (ifMatch) {
      headers['If-Match'] = ifMatch
    }
    return this.request<Paper>(`/projects/${projectId}/papers/${paperId}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(data),
    })
  }

  // ── Screening, Conflicts & Agreement (Doc 43) ──────────────────────

  async listScreeningConflicts(projectId: string): Promise<Paper[]> {
    return this.request<Paper[]>(`/projects/${projectId}/screening/conflitos`)
  }

  async resolveScreeningConflict(
    projectId: string,
    paperId: string,
    data: import('@/types/api').ConflictResolutionPayload
  ): Promise<Paper> {
    return this.request<Paper>(`/projects/${projectId}/screening/conflitos/${paperId}/resolver`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getAgreementMetrics(projectId: string): Promise<import('@/types/api').AgreementMetrics> {
    return this.request<import('@/types/api').AgreementMetrics>(`/projects/${projectId}/screening/concordancia`)
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

  // ── Autenticação ──────────────────────────────────────────────────

  async getAuthStatus(): Promise<import('@/types/api').AuthStatus> {
    return this.request<import('@/types/api').AuthStatus>('/auth/status')
  }

  async login(username: string, password: string): Promise<import('@/types/api').LoginResponse> {
    const res = await this.request<import('@/types/api').LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    this.setSessionToken(res.access_token)
    return res
  }

  /**
   * Troca o token local do app de mesa por uma sessão.
   *
   * É o que mantém o uso desktop sem tela de login: o Electron lê o arquivo
   * `runtime_token` e passa o conteúdo adiante.
   */
  async loginWithLocalToken(token: string): Promise<import('@/types/api').LoginResponse> {
    const res = await this.request<import('@/types/api').LoginResponse>('/auth/local', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
    this.setSessionToken(res.access_token)
    return res
  }

  async validateInvite(inviteCode: string): Promise<import('@/types/api').ValidateInviteResponse> {
    return this.request<import('@/types/api').ValidateInviteResponse>('/auth/invite/validate', {
      method: 'POST',
      body: JSON.stringify({ invite_code: inviteCode }),
    })
  }

  async registerWithInvite(
    payload: import('@/types/api').RegisterWithInvitePayload
  ): Promise<import('@/types/api').LoginResponse> {
    const res = await this.request<import('@/types/api').LoginResponse>('/auth/register-with-invite', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    this.setSessionToken(res.access_token)
    return res
  }

  async logout(): Promise<void> {
    try {
      await this.request<{ status: string }>('/auth/logout', { method: 'POST' })
    } finally {
      // O token local morre mesmo se a chamada falhar: manter a sessão do lado
      // do cliente depois de um pedido de saída seria o pior dos dois mundos.
      this.setSessionToken(null)
    }
  }

  async getCurrentUser(): Promise<import('@/types/api').AuthUser> {
    return this.request<import('@/types/api').AuthUser>('/auth/me')
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>('/auth/password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    })
  }



  async getAISettings(): Promise<AISettings> {
    return this.request<AISettings>('/ai/settings')
  }

  async updateAISettings(data: AISettingsUpdate): Promise<AISettings> {
    return this.request<AISettings>('/ai/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  /**
   * Remove todas as chaves de um provedor.
   *
   * Contrapartida da gravação write-only: salvar o formulário com o campo
   * vazio não apaga nada, então apagar precisa de um pedido explícito.
   */
  async deleteProviderKeys(provider: 'gemini' | 'qwen' | 'local'): Promise<AISettings> {
    return this.request<AISettings>(`/ai/settings/keys/${provider}`, {
      method: 'DELETE',
    })
  }

  async testAIConnection(): Promise<any> {
    return this.request<any>('/ai/test', {
      method: 'POST',
    })
  }

  async suggestProtocol(
    data: { title: string; methodology: string; description?: string },
    signal?: AbortSignal
  ): Promise<ProtocolSuggestions> {
    return this.request<ProtocolSuggestions>('/ai/suggest-protocol', {
      method: 'POST',
      body: JSON.stringify(data),
      signal,
    })
  }

  async assistField(
    data: import('@/types/api').FieldAssistRequest,
    signal?: AbortSignal
  ): Promise<import('@/types/api').FieldAssistResponse> {
    return this.request<import('@/types/api').FieldAssistResponse>('/ai/assist-field', {
      method: 'POST',
      body: JSON.stringify(data),
      signal,
    })
  }

  async screenSinglePaperAI(
    projectId: string,
    paperId: string,
    signal?: AbortSignal
  ): Promise<AIScreeningSingleResult> {
    return this.request<AIScreeningSingleResult>(`/projects/${projectId}/screening/ai/single/${paperId}`, {
      method: 'POST',
      signal,
    })
  }

  async startBatchScreeningAI(projectId: string, data: { limit?: number; concurrency?: number }): Promise<any> {
    return this.request<any>(`/projects/${projectId}/screening/ai/batch`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  /** Interrompe a triagem em lote em andamento no projeto. */
  async cancelBatchScreeningAI(projectId: string): Promise<{ status: string; message: string }> {
    return this.request(`/projects/${projectId}/screening/ai/batch/cancel`, {
      method: 'POST',
    })
  }

  /**
   * Situação da triagem em lote no servidor.
   *
   * É o que permite à tela se recompor: o progresso do lote só chegava pelo
   * WebSocket, então recarregar a página no meio da triagem apagava a barra e
   * o botão de parar, embora o servidor seguisse triando.
   */
  async getBatchScreeningStatus(projectId: string): Promise<{
    is_running: boolean
    progress: {
      processed: number
      total: number
      percentage: number
      included: number
      excluded: number
      pending: number
      current_paper_title?: string
    } | null
  }> {
    return this.request(`/projects/${projectId}/screening/ai/batch/status`)
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

  async extractAnswersWithAI(
    projectId: string,
    paperId: string,
    questionId?: string,
    signal?: AbortSignal
  ): Promise<any> {
    const query = questionId ? `?question_id=${encodeURIComponent(questionId)}` : ''
    return this.request<any>(`/projects/${projectId}/papers/${paperId}/extraction/ai${query}`, {
      method: 'POST',
      signal,
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

  // ── Indicadores (B.I. e Bibliometria) ──────────────────────────────

  async getInsights(
    projectId: string,
    filters?: import('@/types/api').InsightsFilters
  ): Promise<import('@/types/api').ProjectInsights> {
    const qs = construirQueryDeInsights(filters)
    return this.request<import('@/types/api').ProjectInsights>(`/projects/${projectId}/insights${qs}`)
  }

  // ── Profile & Keys Portability ────────────────────────────────────

  /**
   * Exporta as credenciais em um arquivo cifrado com a senha informada.
   *
   * Era um GET que devolvia as chaves em texto claro — acionável por simples
   * navegação. Virou POST com senha, e o que volta é um envelope inútil sem
   * ela.
   */
  async exportKeys(exportPassword: string): Promise<import('@/types/api').EncryptedEnvelope> {
    return this.request<import('@/types/api').EncryptedEnvelope>('/profile/keys/export', {
      method: 'POST',
      body: JSON.stringify({ export_password: exportPassword }),
    })
  }

  /** Importa backup cifrado (com senha) ou arquivo legado em texto claro. */
  async importKeys(
    payload: Record<string, any> | null,
    options?: { rawContent?: string; exportPassword?: string }
  ): Promise<import('@/types/api').KeysImportResponse> {
    return this.request<import('@/types/api').KeysImportResponse>('/profile/keys/import', {
      method: 'POST',
      body: JSON.stringify({
        payload,
        raw_content: options?.rawContent,
        export_password: options?.exportPassword,
      }),
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

  // ── Gestão de Convites (Owner / Gerente) ──────────────────────────

  async listInvites(): Promise<{ invites: any[]; items?: any[]; total: number }> {
    return this.request<{ invites: any[]; items?: any[]; total: number }>('/invites')
  }

  async createInvite(data?: { custom_code?: string; expires_in_days?: number | null; note?: string }): Promise<any> {
    return this.request<any>('/invites', {
      method: 'POST',
      body: JSON.stringify(data || {}),
    })
  }

  async revokeInvite(inviteId: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/invites/${inviteId}`, {
      method: 'DELETE',
    })
  }

  // ── Gestão de Contas de Usuários (Owner / Gerente) ──────────────────

  async listUsers(): Promise<import('@/types/api').UserListResponse> {
    return this.request<import('@/types/api').UserListResponse>('/auth/users')
  }

  async createUser(data: {
    username: string
    role?: string
    password?: string
    full_name?: string
    email?: string
    institution?: string
  }): Promise<import('@/types/api').UserCreatedResponse> {
    return this.request<import('@/types/api').UserCreatedResponse>('/auth/users', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateUserAdmin(
    userId: string,
    data: import('@/types/api').UserAdminUpdatePayload
  ): Promise<import('@/types/api').AuthUser> {
    return this.request<import('@/types/api').AuthUser>(`/auth/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deactivateUser(userId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/auth/users/${userId}`, {
      method: 'DELETE',
    })
  }

  async resetUserPasswordAdmin(
    userId: string,
    newPassword?: string
  ): Promise<{ status: string; message: string; temporary_password?: string }> {
    return this.request<{ status: string; message: string; temporary_password?: string }>(
      `/auth/users/${userId}/reset-password`,
      {
        method: 'POST',
        body: JSON.stringify({ new_password: newPassword || undefined }),
      }
    )
  }

  // ── Pesquisa em Equipe e Convites de Projeto (doc 43, Fase 1) ──────

  async getTeam(projectId: string): Promise<TeamResponse> {
    return this.request<TeamResponse>(`/projects/${projectId}/team`)
  }

  async getTeamMembers(projectId: string): Promise<ProjectMember[]> {
    return this.request<ProjectMember[]>(`/projects/${projectId}/team/members`)
  }

  async removeTeamMember(projectId: string, userId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/projects/${projectId}/team/members/${userId}`, {
      method: 'DELETE',
    })
  }

  async getTeamInvitations(projectId: string): Promise<ProjectInvitation[]> {
    return this.request<ProjectInvitation[]>(`/projects/${projectId}/team/invitations`)
  }

  async createTeamInvitation(projectId: string, data: ProjectInvitationCreate): Promise<ProjectInvitation> {
    return this.request<ProjectInvitation>(`/projects/${projectId}/team/invitations`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async revokeTeamInvitation(projectId: string, inviteId: string): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>(`/projects/${projectId}/team/invitations/${inviteId}`, {
      method: 'DELETE',
    })
  }

  async acceptTeamInvitation(code: string): Promise<AcceptInvitationResponse> {
    return this.request<AcceptInvitationResponse>(`/projects/invitations/${code}/accept`, {
      method: 'POST',
    })
  }
}

export const api = new APIClient()
