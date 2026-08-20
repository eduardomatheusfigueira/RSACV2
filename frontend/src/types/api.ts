/**
 * RSAC V2 — TypeScript Types (espelhando schemas Pydantic do backend)
 */

// ── Enums ─────────────────────────────────────────────────────────────

export type Decision = 'Pendente' | 'Incluído' | 'Excluído'

export type Methodology =
  | 'PRISMA-ScR'
  | 'PRISMA-2020'
  | 'PRISMA-P'
  | 'Cochrane'
  | 'JBI (Scoping/Systematic)'
  | 'Campbell'
  | 'CEE/ROSES'
  | 'EBSE'
  | 'Umbrella Review'
  | 'Methodi Ordinatio'
  | 'Other'

export type HarvesterSource = 'BDTD' | 'SciELO' | 'OpenAlex' | 'PubMed' | 'Scopus'

export type AIProvider = 'gemini' | 'qwen' | 'local'

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export type CanonicalDocumentType =
  | 'Tese'
  | 'Dissertação'
  | 'Artigo de Periódico'
  | 'Livro'
  | 'Capítulo de Livro'
  | 'Preprint'
  | 'Trabalho em Anais/Conferência'
  | 'Relatório Técnico'
  | 'Outro'

// ── Project ───────────────────────────────────────────────────────────

export interface Project {
  id: string
  title: string
  description: string
  methodology: Methodology
  created_at: string
  updated_at: string
  is_archived: boolean
}

export interface ProjectCreate {
  title: string
  description?: string
  methodology: Methodology
}

export interface ProjectUpdate {
  title?: string
  description?: string
  methodology?: Methodology
  is_archived?: boolean
}

export interface ProjectListResponse {
  items: Project[]
  total: number
}

// ── Protocol & Criteria ───────────────────────────────────────────────

export interface Criterion {
  id?: string
  text: string
  is_exclusion: boolean
  order: number
}

export interface ExtractionQuestion {
  id?: string
  text: string
  order: number
}

export interface SearchFilters {
  year_start?: number | null
  year_end?: number | null
  languages?: string[]
  document_types?: string[]
  institutions?: string[]
  open_access_only?: boolean
  target_databases?: string[]
}

export interface Protocol {
  id: string
  project_id: string
  objective: string
  pico_framework: Record<string, string>
  search_descriptors: Record<string, string[]>
  search_filters?: SearchFilters
  manuscript_sections?: Record<string, string>
  created_at: string
  updated_at: string
  criteria: Criterion[]
  extraction_questions: ExtractionQuestion[]
}

export interface ProtocolUpdate {
  objective?: string
  pico_framework?: Record<string, string>
  search_descriptors?: Record<string, string[]>
  search_filters?: SearchFilters
  manuscript_sections?: Record<string, string>
  criteria?: Criterion[]
  extraction_questions?: ExtractionQuestion[]
}

// ── Paper ─────────────────────────────────────────────────────────────

export interface Paper {
  id: string
  project_id: string
  title: string
  title_normalized: string
  authors: string
  advisor?: string
  year: string
  source?: string
  sources?: string[]
  research_type: string
  institution: string
  journal?: string
  abstract: string
  download_url: string
  doi: string | null
  decision: Decision
  observations: string
  ai_confidence: number | null
  criteria_evaluations?: Record<string, boolean>
  pdf_path: string | null
  pdf_text_extracted: boolean
  pdf_status?: PdfStatus
  pdf_strategy?: string
  pdf_resolved_url?: string
  pdf_page_count?: number
  pdf_is_scanned?: boolean
  created_at: string
  updated_at: string
}


export interface PaperCreate {
  title: string
  authors?: string
  advisor?: string
  year?: string
  doi?: string
  abstract?: string
  research_type?: string
  institution?: string
  journal?: string
  download_url?: string
  decision?: Decision
  observations?: string
  sources?: string[]
}

export interface PaperUpdate {
  decision?: Decision
  observations?: string
  criteria_evaluations?: Record<string, boolean>
  extraction_answers?: Record<string, string>
  abstract?: string
  title?: string
  authors?: string
  year?: string
  doi?: string
  download_url?: string
}

export interface PaperListResponse {
  items: Paper[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ── Harvest ───────────────────────────────────────────────────────────

export interface HarvestStartRequest {
  sources: string[]
  max_records_per_descriptor?: number | null
  custom_descriptors?: string[]
  year_start?: number | null
  year_end?: number | null
  languages?: string[]
  document_types?: string[]
  institutions?: string[]
  open_access_only?: boolean
  fetch_details?: boolean
}

export interface HarvestRun {
  id: string
  project_id: string
  source_name: string
  descriptors_used: string[]
  query_parameters?: Record<string, unknown>
  started_at: string
  completed_at: string | null
  records_found: number
  records_new: number
  records_duplicate: number
  status: string
  error_message: string | null
}

export interface HarvestRunListResponse {
  items: HarvestRun[]
  total: number
}

export interface HarvestSourceInfo {
  id: string
  name: string
  description: string
  enabled: boolean
  requires_api_key?: boolean
  has_api_key?: boolean
  supports_year_range?: boolean
  supports_language?: boolean
  supports_document_type?: boolean
  supports_institution?: boolean
  supports_open_access?: boolean
  supports_boolean_query?: boolean
  max_native_filters?: number | null
  default_page_size?: number
}

// ── Source Credentials ────────────────────────────────────────────────

export interface SourceCredential {
  source_name: string
  has_api_key: boolean
  key_preview: string
  has_inst_token: boolean
  inst_token_preview: string
  custom_endpoint?: string | null
  updated_at?: string | null
}

export interface SourceCredentialUpdate {
  api_key?: string
  inst_token?: string
  custom_endpoint?: string | null
}

// ── PDF: aquisição, procedência e leitura ─────────────────────────────

export type PdfStatus = 'ausente' | 'obtido' | 'manual' | 'falhou' | 'indisponivel'

/** Uma tentativa registrada pelo resolvedor multi-estratégia. */
export interface PdfAttempt {
  strategy: string
  url: string
  status: 'ok' | 'nao_pdf' | 'http_erro' | 'timeout' | 'erro' | 'vazio' | 'pequeno_demais'
  detail: string
  http_status: number | null
}

/** Estado do PDF de um trabalho, comum a todas as respostas de PDF. */
export interface PdfState {
  has_pdf: boolean
  pdf_path: string | null
  pdf_status: PdfStatus
  pdf_strategy: string
  pdf_resolved_url: string
  pdf_page_count: number
  pdf_size_bytes: number
  pdf_text_chars: number
  pdf_is_scanned: boolean
  pdf_acquired_at: string | null
  download_url: string
  attempts: PdfAttempt[]
  file_missing: boolean
}

export interface PdfAcquisitionResult extends PdfState {
  status: 'downloaded' | 'failed'
  success: boolean
  strategy: string
  label: string
  message: string
  page_count: number
  is_scanned: boolean
  text_chars: number
}

export interface PdfCandidate {
  url: string
  strategy: string
  label: string
}

export interface PdfTextResponse {
  paper_id: string
  text: string
  pages: Array<{ number: number; text: string }>
  page_count: number
  char_count: number
  is_scanned: boolean
  engine: string
  error: string
  sections: Array<{ key: string; title: string; start_page: number; char_count: number }>
}

export interface PdfBatchState {
  project_id: string
  status: 'idle' | 'running' | 'done' | 'cancelled' | 'error' | 'empty'
  total: number
  processed: number
  succeeded: number
  failed: number
  current_title: string
  progress_percent: number
  started_at?: string
  finished_at?: string | null
  error_message?: string
  message?: string
  results: Array<{
    paper_id: string
    title: string
    success: boolean
    strategy: string
    message: string
    attempts: number
  }>
}

export interface ExtractionResponse extends PdfState {
  paper_id: string
  answers: Array<{
    id: string
    question_id: string
    answer: string
    ai_generated: boolean
    evidence: string
    page_ref: string
    source_kind: string
  }>
}


// ── Deduplication Report ──────────────────────────────────────────────

export interface DeduplicationReport {
  id: string
  project_id: string
  total_raw: number
  total_unique: number
  total_duplicates: number
  dup_rate: number
  sources_breakdown: Record<string, number>
  duplicates_list: Array<{
    titulo: string
    autores: string
    ano: string
    fontes: string[]
    primary_id: string
    duplicate_id: string
  }>
  report_text: string
  created_at: string
}

// ── Autenticação ──────────────────────────────────────────────────────

export interface AuthUser {
  id: string
  username: string
  role: 'owner' | 'researcher'
  is_active: boolean
  created_at: string
  last_login_at?: string | null
}

export interface LoginResponse {
  user: AuthUser
  access_token: string
  token_type: string
  expires_in_hours: number
}

/** Única resposta que o backend dá antes do login. */
export interface AuthStatus {
  authentication_enabled: boolean
  deployment_profile: 'desktop' | 'server' | 'ci'
  has_accounts: boolean
  /** O perfil desktop aceita o token local em vez de usuário e senha. */
  local_token_accepted: boolean
  authenticated: boolean
  user?: AuthUser | null
}

export interface UserListResponse {
  items: AuthUser[]
  total: number
}

export interface UserCreatedResponse {
  user: AuthUser
  /** Devolvida apenas na criação, e nunca mais. */
  generated_password?: string | null
}

// ── AI ────────────────────────────────────────────────────────────────

/**
 * Estado das configurações de IA vindo do backend.
 *
 * As chaves NÃO trafegam mais em texto claro: o que chega são máscaras
 * (`••••••••abcd`) e contagens. Para trocar uma chave envia-se a nova por
 * inteiro; para apagar, `deleteProviderKeys`.
 */
export interface AISettings {
  ai_enabled: boolean
  provider: 'gemini' | 'qwen' | 'local'
  model: string
  has_api_keys: boolean
  key_previews: string[]
  gemini_key_previews: string[]
  qwen_key_previews: string[]
  local_key_previews: string[]
  gemini_keys_count: number
  qwen_keys_count: number
  local_keys_count: number
  endpoint: string | null
  temperature: number
  max_tokens: number
}

export interface AISettingsUpdate {
  ai_enabled: boolean
  provider: string
  model: string
  // Omitir o campo mantém as chaves gravadas; enviar uma lista as substitui.
  // Lista vazia é ignorada pelo backend — apagar exige deleteProviderKeys.
  api_keys?: string[]
  gemini_api_keys?: string[]
  qwen_api_keys?: string[]
  local_api_keys?: string[]
  endpoint?: string | null
  temperature: number
  max_tokens: number
}

// ── Profile & Keys Backup ─────────────────────────────────────────────

export interface SourceCredentialBackupItem {
  api_key?: string
  inst_token?: string
  custom_endpoint?: string | null
}

/** Backup legado, em claro — ainda aceito na importação. */
export interface KeysBackupData {
  schema_version: string
  exported_at: string
  gemini_api_keys: string[]
  qwen_api_keys: string[]
  local_api_keys: string[]
  sources: Record<string, SourceCredentialBackupItem>
}

/** Envelope cifrado devolvido pela exportação de credenciais. */
export interface EncryptedEnvelope {
  schema_version: string
  encrypted: boolean
  kdf: string
  iterations: number
  salt: string
  ciphertext: string
  exported_at: string
}

export interface KeysImportResponse {
  status: string
  message: string
  gemini_keys_count: number
  qwen_keys_count: number
  local_keys_count: number
  sources_configured: string[]
}

export interface ProfileSessionPreferences {
  theme: string
  active_project_id?: string | null
  sidebar_collapsed?: boolean
  ai_enabled?: boolean
}

export interface ProfileBackupData {
  schema_version: string
  app_version: string
  exported_at: string
  session_preferences: ProfileSessionPreferences
  ai_settings: Record<string, any>
  source_credentials: Array<{
    source_name: string
    api_key: string
    inst_token: string
    custom_endpoint?: string | null
  }>
  projects: any[]
}

export interface ProfileImportResponse {
  status: string
  message: string
  projects_imported: number
  papers_imported: number
  extractions_imported: number
  restored_session: ProfileSessionPreferences
}

export interface AIScreeningSingleResult {
  status: string
  paper_id: string
  decision: Decision
  confidence: number
  justification: string
  inclusion_criteria: Record<string, boolean>
  exclusion_criteria: Record<string, boolean>
  model_used: string
  provider: string
}

export interface ProtocolSuggestions {
  objective: string
  pico_population: string
  pico_intervention: string
  pico_comparison: string
  pico_outcome: string
  descriptors_pt: string[]
  descriptors_en: string[]
  descriptors_es: string[]
  inclusion_criteria: string[]
  exclusion_criteria: string[]
  extraction_questions: string[]
}

export interface FieldAssistRequest {
  field_id: string
  field_label: string
  current_value?: string
  field_guidelines?: string
  project_title?: string
  methodology?: string
  project_context?: Record<string, string>
  action?: 'generate' | 'improve' | 'grammar' | 'expand' | 'shorten'
  custom_instruction?: string
}

export interface FieldAssistResponse {
  field_id: string
  suggested_text: string
  explanation?: string
  model_used: string
  provider: string
}

// ── Extraction Summary & Evidence Matrix ──────────────────────────────

export interface ExtractionAnswerSummaryItem {
  paper_id: string
  paper_title: string
  authors: string
  year: string
  answer: string
  ai_generated: boolean
}

export interface ExtractionQuestionSummary {
  question_id: string
  question_text: string
  order: number
  total_answered: number
  answers: ExtractionAnswerSummaryItem[]
}

export interface ExtractionSummaryResponse {
  project_id: string
  total_screened: number
  total_included: number
  total_excluded: number
  total_pending: number
  total_extracted: number
  extraction_progress_percent: number
  questions_matrix: ExtractionQuestionSummary[]
}

export interface PrismaFlowData {
  identification: {
    total_records_identified: number
    duplicates_removed: number
    sources_breakdown: Record<string, number>
  }
  screening: {
    records_screened: number
    records_excluded: number
    records_pending?: number
  }
  included: {
    studies_included_in_synthesis: number
  }
}

// ── Indicadores (B.I. e Bibliometria, doc 32) ──────────────────────────

export interface CriterionFunnelItem {
  criterion_id: string
  text: string
  is_exclusion: boolean
  evaluated_count: number
  met_count: number
  not_met_count: number
}

export interface SourceComposition {
  source_name: string
  found_count: number
  included_count: number
}

export interface YearCount {
  year: string
  count: number
}

/** Item de ranking (periódico, autor, instituição ou tipo de estudo). */
export interface NameCount {
  name: string
  count: number
}

export interface PdfHealth {
  by_status: Record<string, number>
  scanned_ratio: number | null
  extraction_completeness: number | null
}

export interface InsightsFiltersApplied {
  decision: string
  source: string | null
  year_from: number | null
  year_to: number | null
}

/** Processo e proveniência de IA (doc 32 §6.5, doc 33 Fase 3). */
export interface AiProvenance {
  throughput_by_user: NameCount[]
  decisions_by_origin: Record<string, number>
  ai_invalid_response_rate: number | null
  ai_confidence_distribution: NameCount[]
}

export interface ProjectInsights {
  prisma: PrismaFlowData
  criteria_funnel: CriterionFunnelItem[]
  composition_by_decision: Record<string, number>
  composition_by_source: SourceComposition[]
  composition_by_year: YearCount[]
  composition_by_research_type: NameCount[]
  top_journals: NameCount[]
  top_authors: NameCount[]
  top_institutions: NameCount[]
  pdf_health: PdfHealth
  ai_provenance: AiProvenance
  filters_applied: InsightsFiltersApplied
}

export interface InsightsFilters {
  decision?: 'Incluído' | 'Excluído' | 'Pendente'
  source?: string
  year_from?: number
  year_to?: number
}

// ── Stats ─────────────────────────────────────────────────────────────

export interface ProjectStats {
  total_papers: number
  included_papers: number
  excluded_papers: number
  pending_papers: number
  total_harvest_runs: number
  sources: Record<string, number>
}

// ── Health ─────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  version: string
  database: string
}

// ── Electron API ──────────────────────────────────────────────────────

export interface RsacAPI {
  getAppVersion: () => Promise<string>
  getPlatform: () => Promise<string>
  showOpenDialog: (options: unknown) => Promise<unknown>
  showSaveDialog: (options: unknown) => Promise<unknown>
  selectPDFDirectory: () => Promise<string | null>
  showNotification: (title: string, body: string) => Promise<void>
  getSystemTheme: () => Promise<'dark' | 'light'>
  onThemeChanged: (callback: (theme: 'dark' | 'light') => void) => void
}

declare global {
  interface Window {
    rsacAPI: RsacAPI
  }
}
