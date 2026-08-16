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
  open_access_only?: boolean
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

// ── AI ────────────────────────────────────────────────────────────────

export interface AISettings {
  ai_enabled: boolean
  provider: 'gemini' | 'qwen' | 'local'
  model: string
  has_api_keys: boolean
  api_keys?: string[]
  endpoint: string | null
  temperature: number
  max_tokens: number
}

export interface AISettingsUpdate {
  ai_enabled: boolean
  provider: string
  model: string
  api_keys: string[]
  endpoint?: string | null
  temperature: number
  max_tokens: number
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
