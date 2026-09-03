/**
 * Revsist — TypeScript Types (espelhando schemas Pydantic do backend)
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

export type CollaborationMode = 'individual' | 'colaborativa' | 'cega_por_pares'

// ── Project ───────────────────────────────────────────────────────────

export interface Project {
  id: string
  title: string
  description: string
  methodology: Methodology
  collaboration_mode?: CollaborationMode
  reviewers_per_paper?: number
  conflict_resolution?: string
  created_at: string
  updated_at: string
  is_archived: boolean
  my_role?: 'coordenador' | 'revisor' | 'observador'
  member_count?: number
}

export interface ProjectCreate {
  title: string
  description?: string
  methodology: Methodology
  collaboration_mode?: CollaborationMode
  reviewers_per_paper?: number
  conflict_resolution?: string
}

export interface ProjectUpdate {
  title?: string
  description?: string
  methodology?: Methodology
  is_archived?: boolean
  collaboration_mode?: CollaborationMode
  reviewers_per_paper?: number
  conflict_resolution?: string
}

export interface ReopenScreeningPayload {
  collaboration_mode?: CollaborationMode
  motivo?: string
}

export interface ReopenScreeningResponse {
  status: string
  project_id: string
  collaboration_mode: string
  papers_reset: number
  message: string
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
  dimension?: 'populacao' | 'desenho' | 'periodo' | 'idioma' | 'tipo_doc' | 'contexto' | 'outro' | string
  applies_at?: 'titulo_resumo' | 'texto_completo' | 'ambos' | string
  order: number
}

export interface ExtractionQuestion {
  id?: string
  text: string
  answer_type?: 'texto' | 'numero' | 'categoria' | 'multipla' | 'booleano' | string
  options?: string[]
  required?: boolean
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

export interface SearchStrategyBlock {
  key: string
  label: string
  terms: string[]
}

export interface SearchStrategy {
  id: string
  protocol_id: string
  kind: 'canonica' | 'adaptacao' | string
  database: string
  blocks: SearchStrategyBlock[]
  combination: string
  target_fields: string[]
  limits: Record<string, any>
  rendered_query: string
  adaptation_note: string
  created_at: string
  updated_at: string
}

export interface SearchExecution {
  id: string
  protocol_id: string
  harvest_run_id?: string | null
  database: string
  query_sent: string
  filters: Record<string, any>
  executed_at: string
  records_returned: number
  records_after_dedup: number
  error?: string | null
}

export interface ProtocolVersion {
  id: string
  protocol_id: string
  label: string
  snapshot: Record<string, any>
  content_hash: string
  frozen_at: string
  frozen_by_user_id?: string | null
  frozen_by_username?: string | null
}

export interface ProtocolAmendment {
  id: string
  protocol_id: string
  from_version: string
  to_version: string
  diff: Record<string, any>
  reason: string
  project_phase: string
  created_at: string
  created_by_user_id?: string | null
  created_by_username?: string | null
}

export interface ChecklistAudit {
  id: string
  protocol_id: string
  guideline: string
  item_id: string
  state: 'atendido' | 'nao_aplica' | 'pendente' | string
  location: string
  justification: string
  updated_at: string
  updated_by_user_id?: string | null
}

export interface ProtocolGate {
  gate_name: string
  stage: string
  passed: boolean
  requirements: string[]
  missing: string[]
  is_blocking: boolean
  warning_message?: string | null
}

export interface ProtocolReadiness {
  overall_percentage: number
  mode: 'simplificado' | 'completo' | string
  review_design: string
  checklist_guideline: string
  total_checklist_items: number
  completed_checklist_items: number
  gates: ProtocolGate[]
  summary_badge: string
}

export interface ReviewDesignMeta {
  id: string
  name: string
  when_to_use: string
  default_framework: string
  default_reporting: string
  conduct_standards: string[]
  critical_appraisal_requirement: 'obrigatoria' | 'opcional' | 'nao_se_aplica' | string
  expected_synthesis: string
  registry_eligibility: string
  suggested_extraction_questions: string[]
}

export interface ReportingGuidelineMeta {
  id: string
  name: string
  description: string
  item_count: number
  reference: string
}

export interface ConductStandardMeta {
  id: string
  name: string
  organization: string
  description: string
  reference: string
}

export interface QuestionFrameworkMeta {
  id: string
  name: string
  components: Array<{ key: string; label: string }>
  recommended_for: string
}

export interface AppraisalInstrumentMeta {
  id: string
  name: string
  applicable_to: string
  domains: string[]
  reference: string
}

export interface ProtocolCatalog {
  designs: ReviewDesignMeta[]
  guidelines: ReportingGuidelineMeta[]
  standards: ConductStandardMeta[]
  frameworks: QuestionFrameworkMeta[]
  instruments: AppraisalInstrumentMeta[]
}

export interface Protocol {
  id: string
  project_id: string
  mode: 'simplificado' | 'completo' | string
  review_design: string
  reporting_guideline: string
  conduct_standards: string[]
  question_framework: Record<string, any>
  objective: string
  pico_framework: Record<string, string>
  search_descriptors: Record<string, string[]>
  search_filters?: SearchFilters
  manuscript_sections?: Record<string, string>
  appraisal?: Record<string, any>
  synthesis?: Record<string, any>
  bibliometrics?: Record<string, any>
  status: 'rascunho' | 'vigente' | 'emenda' | 'concluido' | string
  current_version?: string | null
  created_at: string
  updated_at: string
  criteria: Criterion[]
  extraction_questions: ExtractionQuestion[]
  search_strategies?: SearchStrategy[]
  latest_executions?: SearchExecution[]
  scope_stamp?: string | null
}

export interface ProtocolUpdate {
  mode?: 'simplificado' | 'completo' | string
  review_design?: string
  reporting_guideline?: string
  conduct_standards?: string[]
  question_framework?: Record<string, any>
  objective?: string
  pico_framework?: Record<string, string>
  search_descriptors?: Record<string, string[]>
  search_filters?: SearchFilters
  manuscript_sections?: Record<string, string>
  appraisal?: Record<string, any>
  synthesis?: Record<string, any>
  bibliometrics?: Record<string, any>
  criteria?: Criterion[]
  extraction_questions?: ExtractionQuestion[]
}

// ── Paper & Screening ──────────────────────────────────────────────────

export type ScreeningStatus =
  | 'aguardando'
  | 'parcial'
  | 'consenso'
  | 'conflito'
  | 'resolvido'
  | 'legado'

export interface PaperScreening {
  id: string
  paper_id: string
  reviewer_id: string
  reviewer_username?: string | null
  decision: Decision | string
  observations: string
  criteria_evaluations: Record<string, boolean>
  ai_confidence?: number | null
  ai_assisted: boolean
  decided_at?: string | null
  updated_at: string
}

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
  screening_status?: ScreeningStatus
  reviewers_completed_count?: number
  reviewers_required_count?: number
  my_screening?: PaperScreening | null
  screenings?: PaperScreening[] | null
  conflict_resolved_by_user_id?: string | null
  conflict_resolved_by_username?: string | null
  conflict_resolved_at?: string | null
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

export interface ConflictResolutionPayload {
  decision: Decision
  observations?: string
  criteria_evaluations?: Record<string, boolean>
}

export interface AgreementMetrics {
  total_papers: number
  evaluated_papers_count: number
  raw_agreement: number | null
  raw_agreement_percent: number
  cohen_kappa: number | null
  kappa_classification: string
  concordant_count: number
  discordant_count: number
  contingency_matrix: {
    both_included: number
    both_excluded: number
    r1_included_r2_excluded?: number
    r1_excluded_r2_included?: number
    divergent: number
  }
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
  run_by_user_id?: string | null
  run_by_username?: string | null
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
  email?: string | null
  full_name?: string
  phone?: string
  institution?: string
  academic_degree?: string
  is_studying?: boolean
  study_program?: string
  profession?: string
  research_area?: string
  auth_provider?: string
  created_at: string
  last_login_at?: string | null
}

export interface UserAdminUpdatePayload {
  role?: 'owner' | 'researcher'
  is_active?: boolean
  full_name?: string
  email?: string
  phone?: string
  institution?: string
  academic_degree?: string
  is_studying?: boolean
  study_program?: string
  profession?: string
  research_area?: string
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
  /** Há credencial de aplicativo Google configurada neste servidor. */
  google_login_enabled: boolean
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

export interface ValidateInviteResponse {
  valid: boolean
  note: string
  expires_at?: string | null
}

export interface RegisterWithInvitePayload {
  invite_code: string
  username: string
  password: string
  full_name: string
  email: string
  phone?: string
  institution?: string
  academic_degree?: string
  is_studying?: boolean
  study_program?: string
  profession?: string
  research_area?: string
  terms_accepted: boolean
}

// ── AI ────────────────────────────────────────────────────────────────

/**
 * Estado das configurações de Assistência vindo do backend.
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
    /**
     * Quantos registros entraram na fila de triagem — o denominador.
     *
     * Sem ele, `records_screened` sozinho é lido como se a triagem estivesse
     * terminada.
     */
    records_to_screen?: number
    /**
     * Quantos já foram triados: os que têm decisão.
     *
     * Já significou "todos os registros do projeto", o que declarava triagem
     * que não aconteceu — 16.578 onde eram 454, e 65.955 onde eram 209
     * (medido em 01/09/2026).
     */
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

/** Processo e proveniência de Assistência (doc 32 §6.5, doc 33 Fase 3). */
export interface AiProvenance {
  throughput_by_user: NameCount[]
  decisions_by_origin: Record<string, number>
  ai_invalid_response_rate: number | null
  ai_confidence_distribution: NameCount[]
}

export interface ProjectInsights {
  /**
   * Sobre que corpus estes números foram calculados.
   *
   * `null` quando a consulta não citou instantâneo — e aí eles descrevem o
   * acervo de agora, que muda todo dia. É o que a tela precisa dizer, em vez
   * de deixar subentendido (doc 47 §B-05).
   */
  provenance: ProveniencaDeIndicador | null
  prisma: PrismaFlowData
  criteria_funnel: CriterionFunnelItem[]
  composition_by_decision: Record<string, number>
  composition_by_source: SourceComposition[]
  composition_by_year: YearCount[]
  composition_by_research_type: NameCount[]
  top_journals: NameCount[]
  top_authors: NameCount[]
  top_institutions: NameCount[]
  /**
   * Denominador de `top_institutions`.
   *
   * As bases de coleta não fornecem afiliação: o campo traz o nome do próprio
   * coletor em 99,7% dos registros do acervo medido (doc 47 §B-01). O ranking
   * cobre a fração pequena que sobra, e precisa dizer qual — sem isso, uma
   * lista construída sobre duzentos registros é lida como se descrevesse
   * oitenta e sete mil.
   */
  institutions_coverage: { with_affiliation: number; total: number }
  pdf_health: PdfHealth
  ai_provenance: AiProvenance
  filters_applied: InsightsFiltersApplied
}

export interface InsightsFilters {
  decision?: 'Incluído' | 'Excluído' | 'Pendente'
  source?: string
  year_from?: number
  year_to?: number
  /** Id do instantâneo: calcula sobre o corpus congelado (doc 48 §3). */
  instantaneo?: string
}

// ── Bibliometria: instantâneo do corpus (docs 47–49) ──────────────────

/**
 * O corpus congelado sobre o qual um indicador foi calculado.
 *
 * `corpus_hash` é a identidade do conjunto: dois instantâneos com o mesmo
 * hash descrevem exatamente os mesmos documentos, com o mesmo conteúdo.
 */
export interface Instantaneo {
  id: string
  project_id: string
  label: string
  scope: { decision?: string | null; source?: string | null; year_from?: number | null; year_to?: number | null }
  n_documents: number
  corpus_hash: string
  engine_version: string
  created_at: string | null
}

/**
 * O que mudou no acervo desde o congelamento (doc 48 §3.3).
 *
 * Os três estados são informação. O que não pode acontecer — e era o
 * comportamento anterior — é a tela mostrar um número diferente do de ontem
 * sem dizer que o corpus mudou.
 */
export interface ConferenciaDoInstantaneo {
  estado: 'identico' | 'conteudo_alterado' | 'conjunto_alterado'
  confiavel: boolean
  documentos_alterados: string[]
  documentos_adicionados: string[]
  documentos_removidos: string[]
}

/** O carimbo que acompanha todo número derivado (doc 48 §14.4). */
export interface ProveniencaDeIndicador {
  snapshot_id: string
  corpus_hash: string
  n_documents: number
  scope: Instantaneo['scope']
  engine_version: string
  frozen_at: string | null
}

export interface UltimoEnriquecimento {
  id: string
  provider: string
  started_at: string | null
  completed_at: string | null
  n_consulted: number
  n_found: number
  status: string
}

export interface SituacaoEnriquecimento {
  project_id: string
  total_papers: number
  papers_with_doi: number
  papers_enriched: number
  papers_pending: number
  coverage_pct: number
  last_enrichment: UltimoEnriquecimento | null
}

// ── Indicadores Bibliométricos Nível 0 e 1 (docs 48 §7, 49 Fase 3) ───

export interface ProducaoAnoItem {
  year: number
  count: number
  growth_yoy_pct?: number | null
}

export interface ProducaoTemporalMetrics {
  series: ProducaoAnoItem[]
  cagr_pct: number | null
  year_start: number | null
  year_end: number | null
  total_period: number
}

export interface BradfordPeriodicoItem {
  name: string
  count: number
}

export interface BradfordZone {
  zone: number
  name: string
  journals: BradfordPeriodicoItem[]
  total_articles: number
  n_journals: number
  pct_articles?: number | null
}

export interface BradfordMetrics {
  total_journals: number
  total_articles: number
  zones: BradfordZone[]
  k_multiplier: number | null
  formula_ratio: string

  /**
   * `false` quando o recorte não tem periódicos suficientes para as três
   * zonas. Sem esta marca, um único periódico era apresentado como
   * "Zona 1: 100%" e razão "1 : 0 : 0", com aparência de resultado.
   */
  confiavel?: boolean
  /** Por que a partição não foi feita — texto pronto para a tela. */
  motivo?: string
}

export interface LotkaDistribuicaoItem {
  articles: number
  authors_observed: number
  authors_expected: number
  pct_observed: number
  pct_expected: number
}

export interface LotkaMetrics {
  n_authors: number
  alpha: number | null
  c_constant: number | null
  d_ks: number | null
  d_critical: number | null
  /** `null` quando a amostra não decide — ver `sample_ok`. */
  is_adherent: boolean | null
  p_verdict: string
  distribution: LotkaDistribuicaoItem[]

  /** A amostra atinge o piso para o teste de aderência (50 autores). */
  sample_ok?: boolean
}

export interface CoautoriaDistribuicaoItem {
  num_authors: number
  count: number
  pct: number
}

export interface ColaboracaoMetrics {
  total_articles: number
  single_author_articles: number
  multi_author_articles: number
  no_author_articles: number
  subramanyam_index: number | null
  avg_authors_per_paper: number
  max_authors: number
  distribution: CoautoriaDistribuicaoItem[]
}

export interface ConcentracaoMetrics {
  gini_authors: number | null
  gini_journals: number | null
  hhi_journals: number | null
}

export interface MultiSourceDistribuicaoItem {
  num_sources: number
  count: number
  pct: number
}

export interface SobreposicaoMetrics {
  sources: string[]
  exclusive_counts: Record<string, number>
  overlap_matrix: Record<string, Record<string, number>>
  multi_source_distribution: MultiSourceDistribuicaoItem[]
  total_papers: number
}

export interface CitationBandItem {
  label: string
  min: number
  max: number | null
  count: number
  pct: number
}

export interface CitacoesMetrics {
  total_citations: number
  mean_citations: number
  median_citations: number
  h_index: number
  max_citations: number
  citation_bands: CitationBandItem[]
  papers_with_citation_data: number
}

export interface OpenAccessStatusItem {
  status: string
  count: number
  pct: number
}

export interface AcessoAbertoMetrics {
  total_evaluated: number
  open_access_count: number
  open_access_pct: number
  by_status: OpenAccessStatusItem[]
}

export interface PaisItem {
  country: string
  count: number
}

export interface IndicadoresBibliometricos {
  project_id: string
  total_papers: number
  provenance: ProveniencaDeIndicador | null
  production_temporal: ProducaoTemporalMetrics
  bradford: BradfordMetrics
  lotka: LotkaMetrics
  collaboration: ColaboracaoMetrics
  concentration: ConcentracaoMetrics
  source_overlap: SobreposicaoMetrics
  citations: CitacoesMetrics
  open_access: AcessoAbertoMetrics
  countries: PaisItem[]
}

// ── Camada de Texto e Tesauro (Fase 4, doc 48 §5, §12) ──────────────────

export interface SecaoItem {
  name: string
  canonical_type: string
  start_page: number
  end_page: number
  char_offset: number
  char_length: number
}

export interface BibTextoInfo {
  paper_id: string
  pipeline_version: string
  pdf_sha256?: string | null
  n_pages: number
  n_words: number
  sections: SecaoItem[]
  extracted_at?: string | null
}

export interface TesauroInfo {
  id: string
  project_id: string
  name: string
  description: string
  created_by?: string | null
  created_at?: string | null
}

export interface TesauroEntryInfo {
  id: string
  thesaurus_id: string
  preferred_term: string
  variants: string[]
  scope: string
  proposed_by: string
  approved_by?: string | null
  approved_at?: string | null
  created_at?: string | null
}

export interface TesauroEntryCreatePayload {
  preferred_term: string
  variants?: string[]
  scope?: string
}

// ── Instrumentos de Medida e Evidências (Fase 5, doc 48 §6, §12) ─────────

export interface TermoInclusao {
  forma: string
  tipo?: string
  idioma?: string
}

export interface TermoExclusao {
  forma: string
  motivo: string
}

export interface LexicoPayload {
  conceito: string
  definicao?: string
  modo: 'lema' | 'literal' | 'regex'
  incluir: TermoInclusao[]
  excluir: TermoExclusao[]
  janela_de_coocorrencia?: number
}

export interface SugerirLexicoResponse {
  concept: string
  definition: string
  lexicon: LexicoPayload
  proposed_by: string
  model_used?: string | null
  prompt_hash?: string | null
}

export interface InstrumentoInfo {
  id: string
  project_id: string
  concept: string
  definition: string
  lexicon: LexicoPayload
  version: string
  status: 'rascunho' | 'aprovado' | 'arquivado'
  proposed_by: string
  model_used?: string | null
  prompt_hash?: string | null
  approved_by?: string | null
  approved_at?: string | null
  estimated_precision?: number | null
  precision_ci?: [number, number] | null
  created_at?: string | null
}

export interface InstrumentoCreatePayload {
  concept: string
  definition?: string
  lexicon: LexicoPayload
  proposed_by?: string
  model_used?: string | null
  prompt_hash?: string | null
}

export interface MedidaResultado {
  frequencia_bruta: number
  frequencia_relativa_por_mil: number
  frequencia_documental: number
  frequencia_documental_pct: number
  distribuicao_por_secao: Record<string, number>
  n_documents: number
  n_documents_with_text: number
  n_documents_without_text: number
  total_words_analyzed: number
  is_preview: boolean
  measurement_id?: string | null
}

export interface MedidaInfo {
  id: string
  snapshot_id?: string | null
  instrument_id: string
  instrument_version: string
  result: MedidaResultado
  n_documents: number
  n_documents_with_text: number
  executed_at?: string | null
}

export interface OcorrenciaInfo {
  id?: number | null
  paper_id: string
  section: string
  page: number
  char_start: number
  char_end: number
  matched_form: string
  context_snippet: string
}

// ── Grafos e Análise Estrutural (Fase 6, doc 48 §8, §12) ─────────────────

/**
 * Os quatro tipos de rede, no vocabulário que a API entende.
 *
 * Nomeado e exportado de propósito: enquanto a tela mantinha apelidos próprios
 * ('termos', 'acoplamento'), dois dos quatro respondiam HTTP 400 "Tipo de rede
 * desconhecido" e metade do seletor estava quebrada sem nada acusar.
 */
export type TipoDeRede =
  | 'coautoria'
  | 'coocorrencia_termos'
  | 'acoplamento_bibliografico'
  | 'cocitacao'

export interface GerarGrafoPayload {
  network_type: TipoDeRede
  snapshot_id?: string | null
  normalizacao?: 'association_strength' | 'jaccard' | 'cosine'
  corte_minimo?: number
  max_nos?: number
  resolucao_louvain?: number
  semente?: number
  iteracoes_fr?: number
}

export interface NoGrafo {
  id: string
  label: string
  size: number
  degree: number
  cluster: number
  color: string
  x: number
  y: number
}

export interface ArestaGrafo {
  source: string
  target: string
  weight: number
  count: number
}

export interface ClusterGrafo {
  count: number
  nodes: string[]
  color: string
}

export interface GrafoInfo {
  id: string
  project_id: string
  snapshot_id?: string | null
  network_type: string
  parameters: Record<string, any>
  nodes: NoGrafo[]
  edges: ArestaGrafo[]
  coordinates: Record<string, { x: number; y: number }>
  clusters: Record<string, ClusterGrafo>
  seed: number
  calculated_at?: string | null
}

// ── Estatística Sob Demanda (Fase 7, doc 48 §9, §12) ─────────────────────

export interface FiltroEspecificacao {
  campo: string
  op: string
  valor: any
}

export interface EspecificacaoEstatistica {
  medida: 'contagem' | 'distintos' | 'soma' | 'media' | 'mediana' | 'quantil' | 'taxa' | 'desvio_padrao'
  campo?: string | null
  por: string[]
  onde?: FiltroEspecificacao[]
  ordenar_por?: 'grupo' | 'valor' | 'valor_desc'
  limite?: number
  quantil_p?: number
  snapshot_id?: string | null
}

export interface InterpretarPerguntaResponse {
  supported: boolean
  question: string
  specification?: EspecificacaoEstatistica | null
  explanation: string
  supported_vocabulary?: Record<string, any> | null
}

export interface LinhaResultadoEstatistica {
  grupo: Record<string, any>
  valor: number | null
  n_docs: number
}

export interface ExecutarEspecificacaoResponse {
  specification: EspecificacaoEstatistica
  results: LinhaResultadoEstatistica[]
  total_documents_analyzed: number
  provenance: Record<string, any>
}

export interface AnaliseSalvaInfo {
  id: string
  project_id: string
  question: string
  specification: EspecificacaoEstatistica
  created_by?: string | null
  created_at?: string | null
}

// ── Indicadores de Vanguarda e Sensibilidade (Fase 8, doc 48 §7.4, §10, §12) ──

export interface ItemDiagramaEstrategico {
  cluster_id: number
  label: string
  centralidade: number
  densidade: number
  quadrante: 'motor' | 'basico' | 'especializado' | 'emergente_declinio'
  tamanho: number
  palavras_chave: string[]
}

export interface DiagramaEstrategicoResponse {
  items: ItemDiagramaEstrategico[]
  centralidade_media: number
  densidade_media: number
  provenance: Record<string, any>
}

export interface RajadaTermo {
  termo: string
  peso_rajada: number
  ano_inicio: string
  ano_fim: string
  frequencia_pico: number
  crescimento_pct: number
}

export interface RajadasResponse {
  rajadas: RajadaTermo[]
  parametros: Record<string, any>
  provenance: Record<string, any>
}

export interface ItemRankingBootstrap {
  posicao: number
  rotulo: string
  valor_estimado: number
  ic_95: [number, number]
  empate_com: number[]
  indistinguivel: boolean
}

export interface BootstrapRankingsResponse {
  tipo_ranking: string
  items: ItemRankingBootstrap[]
  n_bootstrap: number
  seed: number
  tem_empates_tecnicos: boolean
  aviso_empates?: string | null
  provenance: Record<string, any>
}

export interface SensibilidadeResolucaoItem {
  resolucao: number
  n_clusters: number
  ari_vs_vigente?: number | null
  is_vigente: boolean
}

export interface SensibilidadeParametrosResponse {
  parametro: string
  valor_vigente: number
  varredura: SensibilidadeResolucaoItem[]
  diagnostico: string
  provenance: Record<string, any>
}

export interface SubtemaCobertura {
  topico: string
  campo: string
  n_estudos_no_corpus: number
  score_medio: number
  status_cobertura: 'robusto' | 'moderado' | 'ralo'
}

export interface CoberturaCampoResponse {
  total_topicos_identificados: number
  topicos_robustos: SubtemaCobertura[]
  topicos_ralos: SubtemaCobertura[]
  taxa_cobertura_ampla_pct: number
  diagnostico_metodologico: string
  provenance: Record<string, any>
}

// ── Pré-Registro e Relatório BIBLIO (Fase 9, doc 48 §11, §12) ─────────────

export interface EmendaProtocolo {
  id: string
  from_version: string
  to_version: string
  section: string
  reason: string
  created_at: string | null
}

export interface PlanoBibliometrico {
  indicadores_previstos: string[]
  unidade_analise: string
  janela_temporal: string
  justificativa_janela: string
  cortes_declarados: Record<string, any>
  tesauro_obrigatorio: boolean
  status_protocolo: string
  versao_protocolo: string
  emendas: EmendaProtocolo[]
}

export interface AtualizarPlanoBibliometricoRequest {
  indicadores_previstos: string[]
  unidade_analise: string
  janela_temporal: string
  justificativa_janela: string
  cortes_declarados: Record<string, any>
  tesauro_obrigatorio: boolean
}

export interface ItemConformidadeBiblio {
  numero: number
  secao: string
  item: string
  descricao: string
  responsabilidade: 'sistema' | 'autor'
  status: 'conforme' | 'pendente' | 'nao_aplicavel'
  evidencia: string
}

export interface RelatorioConformidadeBiblioResponse {
  total_itens: number
  itens_conformes: number
  itens_do_sistema: number
  itens_do_autor: number
  secoes: string[]
  itens: ItemConformidadeBiblio[]
  resumo_executivo: string
  provenance: Record<string, any>
}








// ── Stats ─────────────────────────────────────────────────────────────

export interface ProjectStats {
  total_papers: number
  included_papers: number
  excluded_papers: number
  pending_papers: number
  /** Pendentes que a triagem assistida alcança (têm resumo utilizável). */
  pending_triaveis?: number
  /** Pendentes sem resumo utilizável: fora da fila da assistência, dentro do acervo. */
  pending_sem_resumo?: number
  total_harvest_runs: number
  sources: Record<string, number>
}

// ── Health ─────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  version: string
  database: string
}

// ── Equipe e Convites de Projeto (doc 43 §43.3, Fase 1) ─────────────────

export type ProjectRoleType = 'coordenador' | 'revisor' | 'observador'

export interface ProjectMember {
  id: string
  project_id: string
  user_id: string
  username: string
  display_name?: string
  email?: string
  project_role: ProjectRoleType
  is_active: boolean
  joined_at: string
  left_at?: string
}

export interface ProjectInvitationCreate {
  email?: string
  project_role: ProjectRoleType
  note?: string
}

export interface ProjectInvitation {
  id: string
  project_id: string
  code: string
  email?: string
  project_role: ProjectRoleType
  created_by_user_id: string
  created_by_username?: string
  created_at: string
  expires_at: string
  accepted_at?: string
  accepted_by_user_id?: string
  accepted_by_username?: string
  revoked_at?: string
  is_valid: boolean
  note: string
}

export interface TeamResponse {
  project_id: string
  members: ProjectMember[]
  invitations: ProjectInvitation[]
  my_role: ProjectRoleType
  my_user_id: string
}

export interface AcceptInvitationResponse {
  status: string
  project_id: string
  project_title: string
  project_role: ProjectRoleType
  message: string
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

/**
 * Um estudo dentro de um lote de triagem, com a sua situação.
 *
 * Substitui o antigo "feed de recém-triados": a janela precisa responder quais
 * estudos entraram no lote, quais faltam e o que deu em cada um — e isso é uma
 * relação com estado, não uma fila de eventos que passaram.
 */
export interface ItemDoLote {
  id: string
  title: string
  authors?: string
  year?: string
  /**
   * `nao_triado` é o estudo que o provedor recusou em todas as passadas da
   * rodada. Ele segue pendente no acervo e entra no próximo lote — mas precisa
   * aparecer como tal: enquanto era descartado em silêncio, a relação mostrava
   * um item eternamente "na fila" e o contador parava a um estudo do fim.
   */
  status: 'na_fila' | 'em_analise' | 'concluido' | 'nao_triado'
  decision?: string | null
  confidence?: number | null
  justification?: string | null
}

/**
 * Onde o lote se acomodou.
 *
 * `paralelismo` é o valor vigente, ajustado sozinho pelo servidor entre 1 e
 * `teto`; `pausa` é o intervalo atual entre disparos. A tela mostra isso para
 * que o pesquisador veja o sistema reagindo — e entenda por que a velocidade
 * muda ao longo de um mesmo lote.
 */
export interface RitmoDoLote {
  paralelismo: number
  teto: number
  pausa: number
}
