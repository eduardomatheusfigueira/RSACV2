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

export interface Protocol {
  id: string
  project_id: string
  objective: string
  pico_framework: Record<string, string>
  search_descriptors: Record<string, string[]>
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
  year: string
  source?: string
  sources?: string[]
  research_type: string
  institution: string
  abstract: string
  download_url: string
  doi: string | null
  decision: Decision
  observations: string
  ai_confidence: number | null
  pdf_path: string | null
  pdf_text_extracted: boolean
  created_at: string
  updated_at: string
}

export interface PaperCreate {
  title: string
  authors?: string
  year?: string
  doi?: string
  abstract?: string
  research_type?: string
  institution?: string
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
  max_records_per_descriptor?: number
  custom_descriptors?: string[]
}

export interface HarvestRun {
  id: string
  project_id: string
  source_name: string
  descriptors_used: string[]
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
