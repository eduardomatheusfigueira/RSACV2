/**
 * Revsist — Protocol Page & Complete Manuscript Drafting Studio (PRISMA-ScR & PRISMA 2020)
 * Especializado em Ciências Sociais Aplicadas & Desenvolvimento Regional.
 *
 * Estrutura Metodológica com Separação Temporal Rigorosa:
 * 1. FASE A PRIORI (Protocolo de Pesquisa & Planejamento Prévio à Coleta):
 *    - Identificação & Registro (Itens 1, 5, 3)
 *    - Questão de Pesquisa & Objetivos PCC/PICO (Item 4)
 *    - Fontes de Informação, Descritores em Pares & Critérios de Elegibilidade (Itens 6, 7, 8)
 *    - Processo de Seleção, Extração, Questionário de Mapeamento, Avaliação Crítica e Métodos de Síntese (Itens 9-13, 17)
 *
 * 2. FASE A POSTERIORI (Síntese dos Achados, Discussão & Manuscrito Final Pós-Extração):
 *    - Síntese das Evidências Extraídas, Limitações Encontradas & Conclusões/Lacunas (Itens 14, 15, 16)
 *    - Resumo Estruturado Final do Artigo Concluído & Título Definitivo (Itens 2, 1)
 *    - Auditoria de Conformidade com o Checklist Oficial
 */

import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as Tabs from '@radix-ui/react-tabs'
import {
  BookOpen,
  Layers,
  Search,
  Filter,
  HelpCircle,
  Sparkles,
  Cpu,
  Save,
  Plus,
  Trash2,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  FileText,
  CheckSquare,
  Copy,
  Edit3,
  Bookmark,
  ShieldCheck,
  BarChart3,
  Database,
  Clock,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  BookMarked,
  ListChecks,
  Check,
  Calendar,
  Globe,
  Sliders,
  Lock,
  Unlock,
  Building2,
  Info,
  StopCircle,
  Users,
  RotateCcw,
} from 'lucide-react'
import { api, foiCancelado } from '@/api/client'
import { useProjectChannel } from '@/hooks/useProjectChannel'
import { useAuthStore } from '@/stores/useAuthStore'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import { ANCORAGEM_NORMATIVA, PROTOCOL_CATALOG, PROTOCOL_OPTIONS, REVIEW_DESIGNS_CATALOG } from '@/data/protocolCatalog'
import { GUIAS } from '@/data/guiasDoProtocolo'
import { CampoDoProtocolo } from '@/components/protocol/CampoDoProtocolo'
import type { CampoDoProtocoloProps } from '@/components/protocol/CampoDoProtocolo'
import type { ProtocolSectionKey } from '@/data/protocolCatalog'
import { ProtocolReadinessCard } from '@/components/protocol/ProtocolReadinessCard'
import { SimplifiedProtocolForm } from '@/components/protocol/SimplifiedProtocolForm'
import { ProtocolVersionDialog } from '@/components/protocol/ProtocolVersionDialog'
import type { ProtocolReadiness, SearchStrategy, SearchExecution } from '@/types/api'

export const AVAILABLE_LANGUAGES = [
  { code: 'pt', label: 'Português', flag: '🇧🇷' },
  { code: 'en', label: 'Inglês', flag: '🇺🇸' },
  { code: 'es', label: 'Espanhol', flag: '🇪🇸' },
  { code: 'fr', label: 'Francês', flag: '🇫🇷' },
  { code: 'de', label: 'Alemão', flag: '🇩🇪' },
  { code: 'it', label: 'Italiano', flag: '🇮🇹' },
]

export const AVAILABLE_DOC_TYPES = [
  { id: 'Artigo de Periódico', label: 'Artigo de Periódico', icon: '📄' },
  { id: 'Tese', label: 'Tese de Doutorado', icon: '🎓' },
  { id: 'Dissertação', label: 'Dissertação de Mestrado', icon: '📜' },
  { id: 'Preprint', label: 'Preprint', icon: '⚡' },
  { id: 'Livro', label: 'Livro', icon: '📚' },
  { id: 'Capítulo de Livro', label: 'Capítulo de Livro', icon: '📑' },
  { id: 'Trabalho em Anais/Conferência', label: 'Trabalho em Anais', icon: '🏛️' },
  { id: 'Relatório Técnico', label: 'Relatório Técnico', icon: '📊' },
]

export const AVAILABLE_DATABASES = [
  { id: 'BDTD', name: 'BDTD (IBICT)', desc: 'Teses e dissertações brasileiras com orientador e instituição', badge: 'Nacional / Aberto' },
  { id: 'SciELO', name: 'SciELO', desc: 'Periódicos científicos de Acesso Aberto (América Latina e Caribe)', badge: 'Regional / 100% OA' },
  { id: 'OpenAlex', name: 'OpenAlex', desc: 'Grafo científico global aberto com +250M de trabalhos', badge: 'Global / Aberto' },
  { id: 'PubMed', name: 'PubMed (NCBI)', desc: 'Literatura biomédica e ciências da saúde pública', badge: 'Biomédica / NCBI' },
  { id: 'Scopus', name: 'Scopus (Elsevier)', desc: 'Base multidisciplinar internacional indexada com peer review', badge: 'Multidisciplinar / API' },
]

export const FILTER_BEHAVIOR_MATRIX = [
  {
    db: 'BDTD (IBICT)',
    years: { mode: 'Nativo', note: 'publishDate:[ini TO fim]' },
    languages: { mode: 'Pós-filtro local', note: 'Filtrado após download (limitação de WAF máx 2 filtros na API)' },
    types: { mode: 'Nativo', note: 'format:"masterThesis" / "doctoralThesis"' },
    institutions: { mode: 'Nativo / Pós-filtro', note: 'institution:... e refinamento local' },
    oa: { mode: 'Nativo (100%)', note: '100% Repositórios Públicos Abertos' },
  },
  {
    db: 'SciELO',
    years: { mode: 'Pós-filtro local', note: 'Filtrado após raspagem das páginas' },
    languages: { mode: 'Pós-filtro local', note: 'Filtrado após raspagem das páginas' },
    types: { mode: 'Nativo', note: 'Artigos de Periódicos' },
    institutions: { mode: 'Pós-filtro local', note: 'Filtrado por afiliação autoral' },
    oa: { mode: 'Nativo (100%)', note: '100% Acesso Aberto (Gold OA)' },
  },
  {
    db: 'OpenAlex',
    years: { mode: 'Nativo', note: 'publication_year:ini-fim' },
    languages: { mode: 'Nativo', note: 'language:pt|en|es' },
    types: { mode: 'Nativo', note: 'type:article|dissertation|book...' },
    institutions: { mode: 'Nativo', note: 'institutions.ror' },
    oa: { mode: 'Nativo', note: 'is_oa:true' },
  },
  {
    db: 'PubMed (NCBI)',
    years: { mode: 'Nativo', note: 'Filtro de data [dp]' },
    languages: { mode: 'Nativo', note: 'Filtro de idioma [la]' },
    types: { mode: 'Nativo', note: 'Tipo de publicação [pt]' },
    institutions: { mode: 'Nativo', note: 'Afiliação institucional [ad]' },
    oa: { mode: 'Nativo', note: 'free full text[filter]' },
  },
  {
    db: 'Scopus (Elsevier)',
    years: { mode: 'Nativo', note: 'PUBYEAR' },
    languages: { mode: 'Nativo', note: 'LANGUAGE' },
    types: { mode: 'Nativo', note: 'DOCTYPE' },
    institutions: { mode: 'Nativo', note: 'AF-ID / AFFIL' },
    oa: { mode: 'Nativo', note: 'OPENACCESS(1)' },
  },
]
import { AIAssistButton } from '@/components/common/AIAssistButton'
import {
  PageHeader,
  Button,
  Card,
  LoadingState,
  Dialog,
  DialogContent,
  DialogTitlebar,
  DialogBody,
  DialogFooter,
} from '@/components/ui'
import type {
  Criterion,
  ExtractionQuestion,
  ProtocolSuggestions,
  Methodology,
  ExtractionSummaryResponse,
} from '@/types/api'
import './ProtocolPage.css'
import '@/components/protocol/ProtocolStudio.css'

export type StudioTab =
  | 'ident_intro'
  | 'objectives'
  | 'search_eligibility'
  | 'methods_extraction'
  | 'synthesis_discussion'
  | 'final_summary'
  | 'checklist'

export function ProtocolPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject, aiEnabled } = useSettingsStore()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [copiedNotification, setCopiedNotification] = useState(false)

  // Colaboração em tempo real e controle de concorrência (Doc 43 §43.12, Fase 3)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null)
  const [showConflictModal, setShowConflictModal] = useState(false)
  const [remoteUpdateNotice, setRemoteUpdateNotice] = useState<string | null>(null)

  const usuarioAtual = useAuthStore((estado) => estado.user)

  const { activeUsers } = useProjectChannel({
    projectId: id,
    screen: 'protocolo',
    onProtocolChanged: (evt) => {
      setRemoteUpdateNotice(`Protocolo atualizado por @${evt.por} há instantes.`)
      setTimeout(() => setRemoteUpdateNotice(null), 7000)
    },
  })

  /* "Editando agora com você" listava o próprio usuário junto dos colegas: a
     presença do servidor inclui quem pergunta. Aqui a lista é só de terceiros —
     e a barra some quando ninguém mais está na tela. */
  const colegasPresentes = activeUsers.filter(
    (u) => u.screen === 'protocolo' && u.user_id !== usuarioAtual?.id
  )

  // 4 Eixos Metodológicos & Modo (Doc 45)
  const [protocolMode, setProtocolMode] = useState<'simplificado' | 'completo'>('simplificado')
  const [reviewDesign, setReviewDesign] = useState<string>('D4')
  const [protocolStatus, setProtocolStatus] = useState<string>('rascunho')
  const [currentVersion, setCurrentVersion] = useState<string | null>(null)
  const [scopeStamp, setScopeStamp] = useState<string | null>(null)
  const [readiness, setReadiness] = useState<ProtocolReadiness | null>(null)
  const [readinessLoading, setReadinessLoading] = useState(false)
  const [searchStrategies, setSearchStrategies] = useState<SearchStrategy[]>([])
  const [searchExecutions, setSearchExecutions] = useState<SearchExecution[]>([])
  const [isVersionDialogOpen, setIsVersionDialogOpen] = useState(false)

  // Active Tab for Manuscript Studio (Chronological Stages)
  const [activeStudioTab, setActiveStudioTab] = useState<StudioTab>('ident_intro')

  // Framework Mode (PICO vs PCC)
  const [frameworkType, setFrameworkType] = useState<'PICO' | 'PCC'>('PCC')

  // Core Protocol State (A Priori)
  const [objective, setObjective] = useState('')
  const [pico, setPico] = useState<Record<string, string>>({
    population: '',
    intervention: '',
    comparison: '',
    outcome: '',
  })
  const [descriptors, setDescriptors] = useState<Record<string, string[]>>({
    pt: [''],
    en: [''],
    es: [''],
  })
  const [searchFilters, setSearchFilters] = useState<import('@/types/api').SearchFilters>({
    year_start: null,
    year_end: null,
    languages: ['pt', 'en', 'es'],
    document_types: ['Tese', 'Dissertação', 'Artigo de Periódico'],
    institutions: [],
    open_access_only: false,
    target_databases: ['BDTD', 'SciELO', 'OpenAlex', 'Scopus'],
  })
  const [criteria, setCriteria] = useState<Criterion[]>([])
  const [questions, setQuestions] = useState<ExtractionQuestion[]>([])

  // Comprehensive Manuscript Sections (PRISMA-ScR 22 Items)
  const [manuscript, setManuscript] = useState<Record<string, string>>({
    manuscript_title: '',
    structured_summary: '',
    rationale: '',
    protocol_registration: '',
    info_sources: '',
    search_strategy_notes: '',
    selection_process: '',
    data_charting_process: '',
    critical_appraisal: '',
    synthesis_methods: '',
    summary_evidence: '',
    limitations: '',
    conclusions: '',
    funding: '',
  })

  // Live Extraction Summary (Rastreabilidade das Evidências Reais)
  const [extractionSummary, setExtractionSummary] = useState<ExtractionSummaryResponse | null>(null)
  const [showEvidenceMatrix, setShowEvidenceMatrix] = useState(false)

  // Checklist Checkbox State
  // Chaveado pelo código oficial do item da diretriz ativa — que nem sempre é
  // um inteiro: o PRISMA 2020 numera subitens como "10a"/"13b" e o EBSE usa
  // "1.1". Estado apenas de sessão; a auditoria não é persistida no backend.
  const [checkedScRItems, setCheckedScRItems] = useState<Record<string, boolean>>({})

  // Section Help Drawers/Popups Toggle State
  const [helpOpen, setHelpOpen] = useState<Record<string, boolean>>({})

  // AI Suggestion Modal
  const [isAiModalOpen, setIsAiModalOpen] = useState(false)
  const [aiSuggestions, setAiSuggestions] = useState<ProtocolSuggestions | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  /* A proposta de protocolo é uma única chamada longa ao provedor. O
     controlador é o que permite desistir dela sem fechar o programa — e o que
     faz "fechar a janela" significar de fato parar de esperar. */
  const sugestaoAbortRef = useRef<AbortController | null>(null)

  // Language Tabs for Descriptors
  const [activeLangTab, setActiveLangTab] = useState<'pt' | 'en' | 'es'>('pt')

  const currentProtocolDef = PROTOCOL_CATALOG[activeProject?.methodology as Methodology] || PROTOCOL_CATALOG['PRISMA-ScR']

  const getFieldGuideline = (fieldKey: string, fallbackDesc: string): string => {
    const item = currentProtocolDef.checklistItems?.find((i) => i.fieldKey === fieldKey)
    if (item) {
      return `Conforme ${currentProtocolDef.shortLabel} Item ${item.id}: ${item.desc}`
    }
    return `Conforme ${currentProtocolDef.shortLabel}: ${fallbackDesc}`
  }

  /**
   * Referência do campo na diretriz ativa, pronta para exibição.
   *
   * Quando a diretriz não tem item para o campo — o PRISMA-P não trata de
   * conclusões, o Methodi Ordinatio não trata de redação —, devolve só a sigla,
   * sem número. Citar o número de OUTRA diretriz seria pior do que não citar
   * nenhum, num aplicativo cujo valor é o rigor metodológico.
   */
  const getFieldItemRef = (fieldKey: string): string => {
    const item = currentProtocolDef.checklistItems?.find((i) => i.fieldKey === fieldKey)
    return item
      ? `${currentProtocolDef.shortLabel} Item ${item.id}`
      : currentProtocolDef.shortLabel
  }

  /**
   * Liga o guia declarado em `guiasDoProtocolo.ts` ao estado desta página: o
   * que está aberto, a referência à diretriz ativa e a inserção do modelo.
   *
   * A inserção fica aqui, e não no componente, porque depende do valor ATUAL do
   * campo — a confirmação só faz sentido quando há texto a substituir. Passar
   * `manuscript` inteiro para o componente o acoplaria ao formato do
   * manuscrito por nada.
   */
  /**
   * `alvo` generaliza o que antes era fixo no manuscrito. Os campos do Núcleo
   * de Busca — objetivo, critérios, estratégia, perguntas de extração — não
   * moram em `manuscript`, e sem isso metade do Estúdio ficaria sem botão de
   * guia. Quando `alvo` não é passado, o guia abre sem o botão de modelo: há
   * campo (o seletor de desenho, a grade de bases) em que "inserir texto" não
   * quer dizer nada.
   */
  const montarGuia = (
    chaveDoGuia: string,
    chaveDeAjuda: string,
    alvo?: { valorAtual: string; aplicar: (texto: string) => void }
  ): CampoDoProtocoloProps['guia'] => {
    const conteudo = GUIAS[chaveDoGuia]
    if (!conteudo) return undefined

    const doManuscrito = chaveDoGuia in manuscript
    const alvoEfetivo =
      alvo ??
      (doManuscrito
        ? {
            valorAtual: manuscript[chaveDoGuia] || '',
            aplicar: (texto: string) => updateManuscriptField(chaveDoGuia, texto),
          }
        : undefined)

    return {
      conteudo,
      referencia: getFieldItemRef(chaveDoGuia),
      aberto: Boolean(helpOpen[chaveDeAjuda]),
      alternar: () => toggleHelp(chaveDeAjuda),
      aoInserirModelo:
        conteudo.modelo && alvoEfetivo
          ? () => {
              const { texto, confirmacao } = conteudo.modelo!
              const resolvido =
                typeof texto === 'function'
                  ? texto({
                      diretriz: currentProtocolDef.name,
                      referencia: currentProtocolDef.reference,
                      framework: currentProtocolDef.defaultFramework,
                    })
                  : texto
              if (alvoEfetivo.valorAtual && !window.confirm(confirmacao)) return
              alvoEfetivo.aplicar(resolvido)
            }
          : undefined,
    }
  }

  const getFieldItemTag = (fieldKey: string, _fallbackNum: number, essential = true): string => {
    const item = currentProtocolDef.checklistItems?.find((i) => i.fieldKey === fieldKey)
    const grau = (item ? item.essential : essential) ? 'Essencial' : 'Opcional'
    return item ? `Item ${item.id} — ${grau}` : grau
  }

  useEffect(() => {
    if (id) {
      loadProtocolAndProject(id)
    }
  }, [id])

  const handleChangeMethodology = async (newMethodology: Methodology) => {
    if (!id) return
    try {
      setSaving(true)
      const updated = await api.updateProject(id, { methodology: newMethodology })
      setActiveProject(updated)
      const protoDef = PROTOCOL_CATALOG[newMethodology] || PROTOCOL_CATALOG['PRISMA-ScR']
      if (protoDef.defaultFramework === 'PCC') {
        setFrameworkType('PCC')
      } else {
        setFrameworkType('PICO')
      }
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2500)
    } catch (err: any) {
      console.error('Erro ao trocar metodologia:', err)
      setErrorMessage(err.message || 'Falha ao atualizar metodologia do projeto.')
    } finally {
      setSaving(false)
    }
  }

  const loadProtocolAndProject = async (projectId: string) => {
    try {
      setLoading(true)
      setErrorMessage('')
      let proj = activeProject
      if (!proj || proj.id !== projectId) {
        proj = await api.getProject(projectId)
        setActiveProject(proj)
      }

      const protoDef = PROTOCOL_CATALOG[proj?.methodology as Methodology] || PROTOCOL_CATALOG['PRISMA-ScR']
      if (protoDef.defaultFramework === 'PCC') {
        setFrameworkType('PCC')
      } else {
        setFrameworkType('PICO')
      }

      // Carregar protocolo, resumo de extração e prontidão em paralelo
      const [proto, extSummary, readinessData] = await Promise.all([
        api.getProtocol(projectId),
        api.getExtractionSummary(projectId).catch(() => null),
        api.getProtocolReadiness(projectId).catch(() => null),
      ])

      if (extSummary) {
        setExtractionSummary(extSummary)
      }

      if (readinessData) {
        setReadiness(readinessData)
      }

      setProtocolMode((proto.mode as any) || 'simplificado')
      setReviewDesign(proto.review_design || 'D4')
      setProtocolStatus(proto.status || 'rascunho')
      setCurrentVersion(proto.current_version || null)
      setScopeStamp(proto.scope_stamp || null)
      setSearchStrategies(proto.search_strategies || [])
      setSearchExecutions(proto.latest_executions || [])

      setLastUpdatedAt(proto.updated_at ? new Date(proto.updated_at).toISOString() : null)
      setObjective(proto.objective || '')
      setPico({
        population: proto.pico_framework?.population || '',
        intervention: proto.pico_framework?.intervention || '',
        comparison: proto.pico_framework?.comparison || '',
        outcome: proto.pico_framework?.outcome || '',
      })

      setDescriptors({
        pt: proto.search_descriptors?.pt?.length ? proto.search_descriptors.pt : [''],
        en: proto.search_descriptors?.en?.length ? proto.search_descriptors.en : [''],
        es: proto.search_descriptors?.es?.length ? proto.search_descriptors.es : [''],
      })

      if (proto.search_filters) {
        setSearchFilters({
          year_start: proto.search_filters.year_start ?? null,
          year_end: proto.search_filters.year_end ?? null,
          languages: proto.search_filters.languages ?? ['pt', 'en', 'es'],
          document_types: proto.search_filters.document_types ?? ['Tese', 'Dissertação', 'Artigo de Periódico'],
          institutions: proto.search_filters.institutions ?? [],
          open_access_only: proto.search_filters.open_access_only ?? false,
          target_databases: proto.search_filters.target_databases ?? ['BDTD', 'SciELO', 'OpenAlex', 'Scopus'],
        })
      }

      setCriteria(proto.criteria || [])
      setQuestions((proto.extraction_questions || []).map((q) => ({ ...q, text: q.text || (q as any).question || '' })))

      if (proto.manuscript_sections) {
        setManuscript((prev) => ({
          ...prev,
          ...proto.manuscript_sections,
          manuscript_title: proto.manuscript_sections?.manuscript_title || proj?.title || '',
        }))
      } else {
        setManuscript((prev) => ({
          ...prev,
          manuscript_title: proj?.title || '',
        }))
      }
    } catch (err: any) {
      console.error('Erro ao carregar protocolo:', err)
      setErrorMessage(err.message || 'Falha ao carregar protocolo.')
    } finally {
      setLoading(false)
    }
  }

  const handleSwitchMode = async (newMode: 'simplificado' | 'completo') => {
    if (!id) return
    try {
      setSaving(true)
      const updated = await api.switchProtocolMode(id, newMode)
      setProtocolMode(updated.mode as any)
      setScopeStamp(updated.scope_stamp || null)
      const newReadiness = await api.getProtocolReadiness(id).catch(() => null)
      if (newReadiness) setReadiness(newReadiness)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2000)
    } catch (err: any) {
      console.error('Erro ao alternar modo do protocolo:', err)
      setErrorMessage(err.message || 'Falha ao alternar modo.')
    } finally {
      setSaving(false)
    }
  }

  const handleSwitchReviewDesign = async (newDesignId: string) => {
    if (!id) return
    try {
      setSaving(true)
      const res = await api.switchReviewDesign(id, newDesignId)
      setReviewDesign(newDesignId)
      if (res.suggested_framework) {
        setFrameworkType(res.suggested_framework as any)
      }
      const newReadiness = await api.getProtocolReadiness(id).catch(() => null)
      if (newReadiness) setReadiness(newReadiness)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2000)
    } catch (err: any) {
      console.error('Erro ao alternar desenho metodológico:', err)
      setErrorMessage(err.message || 'Falha ao alternar desenho.')
    } finally {
      setSaving(false)
    }
  }

  const handleRefreshReadiness = async () => {
    if (!id) return
    setReadinessLoading(true)
    try {
      const res = await api.getProtocolReadiness(id)
      setReadiness(res)
    } catch (err) {
      console.error('Erro ao recalcular prontidão:', err)
    } finally {
      setReadinessLoading(false)
    }
  }

  const updateManuscriptField = (key: string, value: string) => {
    setManuscript((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const getFullProtocolContext = (excludeFieldId?: string): Record<string, string> => {
    const ctx: Record<string, string> = {}
    if (activeProject?.title) ctx['project_title'] = activeProject.title
    if (activeProject?.description) ctx['project_description'] = activeProject.description
    if (activeProject?.methodology) ctx['methodology'] = activeProject.methodology
    if (objective && excludeFieldId !== 'objective') ctx['objective'] = objective
    if (pico.population && excludeFieldId !== 'pico_population') ctx['pico_population'] = pico.population
    if (pico.intervention && excludeFieldId !== 'pico_intervention') ctx['pico_intervention'] = pico.intervention
    if (pico.comparison && excludeFieldId !== 'pico_comparison') ctx['pico_comparison'] = pico.comparison
    if (pico.outcome && excludeFieldId !== 'pico_outcome') ctx['pico_outcome'] = pico.outcome

    const descPt = descriptors.pt.filter(Boolean).join('; ')
    const descEn = descriptors.en.filter(Boolean).join('; ')
    const descEs = descriptors.es.filter(Boolean).join('; ')
    if (descPt && excludeFieldId !== 'descriptors_pt') ctx['descriptors_pt'] = descPt
    if (descEn && excludeFieldId !== 'descriptors_en') ctx['descriptors_en'] = descEn
    if (descEs && excludeFieldId !== 'descriptors_es') ctx['descriptors_es'] = descEs

    const incCrit = criteria.filter((c) => !c.is_exclusion && c.text.trim()).map((c) => c.text.trim()).join('; ')
    const excCrit = criteria.filter((c) => c.is_exclusion && c.text.trim()).map((c) => c.text.trim()).join('; ')
    if (incCrit && excludeFieldId !== 'inclusion_criteria') ctx['inclusion_criteria'] = incCrit
    if (excCrit && excludeFieldId !== 'exclusion_criteria') ctx['exclusion_criteria'] = excCrit

    const qList = questions
      .map((q) => (q.text || (q as any).question || '').trim())
      .filter(Boolean)
      .join('; ')
    if (qList && excludeFieldId !== 'questions') ctx['extraction_questions'] = qList

    // Injeção de contexto factual das extrações para as seções a posteriori
    if (extractionSummary) {
      ctx['total_screened_papers'] = String(extractionSummary.total_screened)
      ctx['total_included_papers'] = String(extractionSummary.total_included)
      ctx['total_extracted_papers'] = String(extractionSummary.total_extracted)
      ctx['extraction_progress'] = `${extractionSummary.extraction_progress_percent}%`
      if (extractionSummary.questions_matrix?.length) {
        const qSummary = extractionSummary.questions_matrix
          .map(
            (qm, i) =>
              `Q${i + 1} (${qm.question_text}): ${qm.total_answered} respostas extraídas`
          )
          .join('; ')
        ctx['extracted_evidence_overview'] = qSummary
      }
    }

    // Injeção dos filtros estruturados de busca
    if (searchFilters.year_start || searchFilters.year_end) {
      ctx['search_years'] = `${searchFilters.year_start || 'Início'} a ${searchFilters.year_end || 'Atual'}`
    }
    if (searchFilters.languages?.length) {
      ctx['search_languages'] = searchFilters.languages.join(', ')
    }
    if (searchFilters.document_types?.length) {
      ctx['search_document_types'] = searchFilters.document_types.join(', ')
    }
    if (searchFilters.open_access_only) {
      ctx['search_open_access'] = 'Apenas Acesso Aberto (Open Access)'
    }
    if (searchFilters.institutions?.length) {
      ctx['search_institutions'] = searchFilters.institutions.join(', ')
    }
    if (searchFilters.target_databases?.length) {
      ctx['search_target_databases'] = searchFilters.target_databases.join(', ')
    }

    Object.entries(manuscript).forEach(([k, v]) => {
      if (v && v.trim() && k !== excludeFieldId) {
        ctx[k] = v.trim()
      }
    })

    return ctx
  }

  const toggleHelp = (key: string) => {
    setHelpOpen((prev) => ({
      ...prev,
      [key]: !prev[key],
    }))
  }

  const toggleScRItem = (itemId: string) => {
    setCheckedScRItems((prev) => ({
      ...prev,
      [itemId]: !prev[itemId],
    }))
  }

  // ── Handlers de Critérios ──────────────────────────────────────────

  const addCriterion = (isExclusion: boolean) => {
    setCriteria([
      ...criteria,
      {
        text: '',
        is_exclusion: isExclusion,
        order: criteria.length,
      },
    ])
  }

  const updateCriterion = (index: number, text: string) => {
    const updated = [...criteria]
    updated[index].text = text
    setCriteria(updated)
  }

  const removeCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index))
  }

  // ── Handlers de Descritores em Pares (VuFind/BDTD Compliance) ──────

  const addDescriptor = (lang: 'pt' | 'en' | 'es') => {
    setDescriptors({
      ...descriptors,
      [lang]: [...descriptors[lang], ''],
    })
  }

  const updateDescriptor = (lang: 'pt' | 'en' | 'es', index: number, value: string) => {
    const list = [...descriptors[lang]]
    list[index] = value
    setDescriptors({
      ...descriptors,
      [lang]: list,
    })
  }

  const removeDescriptor = (lang: 'pt' | 'en' | 'es', index: number) => {
    const list = descriptors[lang].filter((_, i) => i !== index)
    setDescriptors({
      ...descriptors,
      [lang]: list.length ? list : [''],
    })
  }

  // ── Handlers de Filtros Estruturados de Busca (PRISMA Scope) ──────

  const updateSearchFilter = <K extends keyof import('@/types/api').SearchFilters>(
    key: K,
    value: import('@/types/api').SearchFilters[K]
  ) => {
    setSearchFilters((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const toggleFilterLanguage = (langCode: string) => {
    const current = searchFilters.languages || []
    const next = current.includes(langCode)
      ? current.filter((l) => l !== langCode)
      : [...current, langCode]
    updateSearchFilter('languages', next)
  }

  const toggleFilterDocType = (docType: string) => {
    const current = searchFilters.document_types || []
    const next = current.includes(docType)
      ? current.filter((t) => t !== docType)
      : [...current, docType]
    updateSearchFilter('document_types', next)
  }

  const toggleTargetDatabase = (dbName: string) => {
    const current = searchFilters.target_databases || ['BDTD', 'SciELO', 'OpenAlex', 'Scopus']
    const next = current.includes(dbName)
      ? current.filter((d) => d !== dbName)
      : [...current, dbName]
    updateSearchFilter('target_databases', next)
  }

  const applyYearPreset = (yearsBack: number | null) => {
    if (yearsBack === null) {
      setSearchFilters((prev) => ({
        ...prev,
        year_start: null,
        year_end: null,
      }))
    } else {
      const currentYear = new Date().getFullYear()
      setSearchFilters((prev) => ({
        ...prev,
        year_start: currentYear - yearsBack + 1,
        year_end: currentYear,
      }))
    }
  }

  // ── Handlers de Perguntas de Extração / Mapeamento ─────────────────

  const addQuestion = () => {
    setQuestions([
      ...questions,
      {
        text: '',
        order: questions.length,
      },
    ])
  }

  const updateQuestion = (index: number, text: string) => {
    const updated = [...questions]
    updated[index] = {
      ...updated[index],
      text: text,
    }
    setQuestions(updated)
  }

  const removeQuestion = (index: number) => {
    setQuestions(questions.filter((_, i) => i !== index))
  }

  // ── Handlers de Compilação de Evidências Reais (A Posteriori) ──────

  const handleCompileEvidenceIntoEditor = () => {
    if (!extractionSummary || !extractionSummary.questions_matrix?.length) return
    let compiled = `### Matriz de Evidências Extraídas (${extractionSummary.total_extracted} estudos com respostas extraídas)\n\n`
    extractionSummary.questions_matrix.forEach((qm, idx) => {
      compiled += `#### Variável / Pergunta ${idx + 1}: ${qm.question_text}\n`
      if (qm.answers.length === 0) {
        compiled += `- *Nenhuma resposta extraída cadastrada para esta variável até o momento.*\n\n`
      } else {
        qm.answers.forEach((ans) => {
          compiled += `- **${ans.paper_title}** (${ans.authors || 'Sem autores'}, ${ans.year || 's/d'}):\n  "${ans.answer}"\n`
        })
        compiled += `\n`
      }
    })

    if (manuscript.summary_evidence && !window.confirm('Inserir o compilado factual das respostas extraídas no campo de Síntese?')) return
    const current = manuscript.summary_evidence ? `${compiled}\n\n### Síntese Narrativa dos Achados:\n${manuscript.summary_evidence}` : compiled
    updateManuscriptField('summary_evidence', current)
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 2500)
  }

  const handleSave = async (forceOverwrite = false) => {
    if (!id) return
    try {
      setSaving(true)
      setErrorMessage('')

      let cleanDescriptors = {
        pt: descriptors.pt.map((d) => d.trim()).filter(Boolean),
        en: descriptors.en.map((d) => d.trim()).filter(Boolean),
        es: descriptors.es.map((d) => d.trim()).filter(Boolean),
      }

      // Se cleanDescriptors estiver vazio, derivar dos blocos da estratégia canônica
      const totalPairs = cleanDescriptors.pt.length + cleanDescriptors.en.length + cleanDescriptors.es.length
      if (totalPairs === 0) {
        const canonical = searchStrategies.find((s) => s.kind === 'canonica')
        if (canonical?.blocks && canonical.blocks.length >= 1) {
          const termsA = (canonical.blocks[0]?.terms || []).filter((t: string) => t && t.trim())
          const termsB = (canonical.blocks[1]?.terms || []).filter((t: string) => t && t.trim())
          const derived: string[] = []
          if (termsA.length > 0 && termsB.length > 0) {
            for (const a of termsA) {
              for (const b of termsB) {
                const qa = a.includes(' ') && !a.startsWith('"') ? `"${a.trim()}"` : a.trim()
                const qb = b.includes(' ') && !b.startsWith('"') ? `"${b.trim()}"` : b.trim()
                derived.push(`${qa} AND ${qb}`)
                if (derived.length >= 5) break
              }
              if (derived.length >= 5) break
            }
          } else if (termsA.length > 0) {
            derived.push(...termsA.slice(0, 5).map((t: string) => (t.includes(' ') && !t.startsWith('"') ? `"${t.trim()}"` : t.trim())))
          }
          if (derived.length > 0) {
            cleanDescriptors = {
              pt: derived,
              en: [],
              es: [],
            }
          }
        }
      }

      const cleanCriteria = criteria
        .filter((c) => c.text.trim().length > 0)
        .map((c, idx) => ({ ...c, order: idx }))

      const cleanQuestions = questions
        .filter((q) => (q.text || (q as any).question || '').trim().length > 0)
        .map((q, idx) => ({ ...q, text: (q.text || (q as any).question || '').trim(), order: idx }))

      const ifMatchHeader = forceOverwrite ? undefined : (lastUpdatedAt || undefined)

      const updated = await api.updateProtocol(
        id,
        {
          mode: protocolMode,
          review_design: reviewDesign,
          objective,
          pico_framework: pico,
          search_descriptors: cleanDescriptors,
          search_filters: searchFilters,
          manuscript_sections: manuscript,
          criteria: cleanCriteria,
          extraction_questions: cleanQuestions,
        },
        ifMatchHeader
      )

      setLastUpdatedAt(updated.updated_at ? new Date(updated.updated_at).toISOString() : null)
      const newReadiness = await api.getProtocolReadiness(id).catch(() => null)
      if (newReadiness) setReadiness(newReadiness)
      setSaveSuccess(true)
      setShowConflictModal(false)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err: any) {
      if (
        err?.status === 409 ||
        err?.message?.includes('409') ||
        err?.detail?.includes('concorrência') ||
        err?.detail?.includes('alterado por outro')
      ) {
        setShowConflictModal(true)
      } else {
        console.error('Erro ao salvar protocolo:', err)
        setErrorMessage(err.message || err.detail || 'Falha ao salvar o protocolo.')
      }
    } finally {
      setSaving(false)
    }
  }

  // ── Exportar Manuscrito Completo em Markdown ───────────────────────

  const handleCopyFullManuscript = () => {
    const markdown = `# ${manuscript.manuscript_title || activeProject?.title || 'Protocolo de Revisão de Escopo'}
**Metodologia:** ${activeProject?.methodology || 'PRISMA-ScR (Tricco et al., 2018)'}
**Área Temática:** Ciências Sociais Aplicadas / Desenvolvimento Regional
**Registro do Protocolo:** ${manuscript.protocol_registration || 'Não registrado'}

---

## 1. Resumo Estruturado (Structured Summary)
${manuscript.structured_summary || 'Não preenchido.'}

---

## 2. Introdução e Justificativa (Rationale)
${manuscript.rationale || 'Não preenchido.'}

### Questão e Objetivos da Revisão (${frameworkType})
**Objetivo Geral:** ${objective || 'Não preenchido.'}
- **População / Atores Sociais (P):** ${pico.population || '-'}
- **${frameworkType === 'PCC' ? 'Conceito Central / Política (C)' : 'Intervenção (I)'}:** ${pico.intervention || '-'}
- **${frameworkType === 'PCC' ? 'Contexto Territorial / Regional (C)' : 'Comparador (C)'}:** ${pico.comparison || '-'}
- **${frameworkType === 'PCC' ? 'Mapeamento de Resultados (M)' : 'Desfecho (O)'}:** ${pico.outcome || '-'}

---

## 3. Métodos de Busca e Elegibilidade
### Fontes de Informação
${manuscript.info_sources || 'Não preenchido.'}

### Estratégia de Busca em Pares (VuFind/BDTD Compliance)
- **Português:** ${descriptors.pt.filter(Boolean).join(' ; ') || 'Nenhum'}
- **Inglês:** ${descriptors.en.filter(Boolean).join(' ; ') || 'Nenhum'}
- **Espanhol:** ${descriptors.es.filter(Boolean).join(' ; ') || 'Nenhum'}

### Recorte Temporal e Filtros Estruturados
- **Período de Cobertura:** ${searchFilters.year_start || searchFilters.year_end ? `${searchFilters.year_start || 'Início'} a ${searchFilters.year_end || 'Atual'}` : 'Sem restrição temporal (Todos os anos)'}
- **Idiomas Elegíveis:** ${searchFilters.languages?.length ? searchFilters.languages.join(', ') : 'Todos os idiomas'}
- **Tipos de Documento Aceitos:** ${searchFilters.document_types?.length ? searchFilters.document_types.join(', ') : 'Todos os tipos'}
- **Instituições / Afiliações:** ${searchFilters.institutions?.length ? searchFilters.institutions.join(', ') : 'Sem restrição (Todas as instituições)'}
- **Acesso Aberto:** ${searchFilters.open_access_only ? 'Restrito estritamente a Acesso Aberto (Open Access)' : 'Sem restrição de modelo de acesso'}
- **Bases de Dados Alvo:** ${searchFilters.target_databases?.length ? searchFilters.target_databases.join(', ') : 'BDTD, SciELO, OpenAlex, Scopus'}

### Critérios de Inclusão
${criteria.filter((c) => !c.is_exclusion).map((c, i) => `${i + 1}. ${c.text}`).join('\n') || 'Nenhum'}

### Critérios de Exclusão
${criteria.filter((c) => c.is_exclusion).map((c, i) => `${i + 1}. ${c.text}`).join('\n') || 'Nenhum'}

---

## 4. Seleção, Extração e Mapeamento de Dados
### Processo de Seleção e Calibração
${manuscript.selection_process || 'Não preenchido.'}

### Processo de Data Charting
${manuscript.data_charting_process || 'Não preenchido.'}

### Variáveis e Questionário de Mapeamento
${questions.map((q, i) => `${i + 1}. ${q.text || (q as any).question || ''}`).join('\n') || 'Nenhuma pergunta cadastrada'}

### Avaliação Crítica da Evidência (Opcional)
${manuscript.critical_appraisal || 'Dispensada / Não realizada para esta revisão de escopo.'}

### Métodos de Síntese
${manuscript.synthesis_methods || 'Não preenchido.'}

---

## 5. Síntese dos Achados, Limitações e Conclusões (Fase A Posteriori)
### Síntese da Evidência (Resultados)
${manuscript.summary_evidence || 'Não preenchido.'}

### Limitações do Estudo
${manuscript.limitations || 'Não preenchido.'}

### Conclusões e Lacunas de Conhecimento
${manuscript.conclusions || 'Não preenchido.'}

### Financiamento e Declaração de Interesses
${manuscript.funding || 'Nenhum financiamento a declarar.'}
`

    navigator.clipboard.writeText(markdown)
    setCopiedNotification(true)
    setTimeout(() => setCopiedNotification(false), 3000)
  }

  // ── Sugestão com Assistência ────────────────────────────────────────────────

  const handleSuggestWithAI = async () => {
    if (!activeProject) return
    try {
      setAiLoading(true)
      setIsAiModalOpen(true)
      setErrorMessage('')

      sugestaoAbortRef.current?.abort()
      const controlador = new AbortController()
      sugestaoAbortRef.current = controlador

      const suggestions = await api.suggestProtocol(
        {
          title: manuscript.manuscript_title || activeProject.title,
          methodology: activeProject.methodology,
          description: activeProject.description || manuscript.rationale || objective,
        },
        controlador.signal
      )

      setAiSuggestions(suggestions)
    } catch (err: any) {
      if (foiCancelado(err)) return
      console.error('Erro ao sugerir protocolo via assistência:', err)
      setErrorMessage(err.message || 'Falha na comunicação com o serviço de assistência.')
      setIsAiModalOpen(false)
    } finally {
      sugestaoAbortRef.current = null
      setAiLoading(false)
    }
  }

  /** Desiste da proposta em elaboração e devolve a tela ao protocolo. */
  const handleCancelSuggestion = () => {
    sugestaoAbortRef.current?.abort()
    sugestaoAbortRef.current = null
    setAiLoading(false)
    setIsAiModalOpen(false)
  }

  const handleApplyAISuggestions = () => {
    if (!aiSuggestions) return

    setObjective(aiSuggestions.objective || objective)
    setPico({
      population: aiSuggestions.pico_population || pico.population,
      intervention: aiSuggestions.pico_intervention || pico.intervention,
      comparison: aiSuggestions.pico_comparison || pico.comparison,
      outcome: aiSuggestions.pico_outcome || pico.outcome,
    })

    setDescriptors({
      pt: aiSuggestions.descriptors_pt?.length ? aiSuggestions.descriptors_pt : descriptors.pt,
      en: aiSuggestions.descriptors_en?.length ? aiSuggestions.descriptors_en : descriptors.en,
      es: aiSuggestions.descriptors_es?.length ? aiSuggestions.descriptors_es : descriptors.es,
    })

    const newCriteria: Criterion[] = [
      ...(aiSuggestions.inclusion_criteria || []).map((text, idx) => ({
        text,
        is_exclusion: false,
        order: idx,
      })),
      ...(aiSuggestions.exclusion_criteria || []).map((text, idx) => ({
        text,
        is_exclusion: true,
        order: (aiSuggestions.inclusion_criteria?.length || 0) + idx,
      })),
    ]
    if (newCriteria.length) setCriteria(newCriteria)

    const newQuestions: ExtractionQuestion[] = (aiSuggestions.extraction_questions || []).map(
      (questionText, idx) => ({
        text: questionText,
        order: idx,
      })
    )
    if (newQuestions.length) setQuestions(newQuestions)

    setIsAiModalOpen(false)
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  // ── Sincronização de Ações com o Ribbon Bar ─────────────────────────
  const registerRibbonActions = useRibbonStore((s) => s.registerActions)
  const unregisterRibbonActions = useRibbonStore((s) => s.unregisterActions)

  const studioTabsList: StudioTab[] = [
    'ident_intro',
    'objectives',
    'search_eligibility',
    'methods_extraction',
    'synthesis_discussion',
    'checklist',
  ]

  useEffect(() => {
    registerRibbonActions({
      saveProtocol: handleSave,
      copyManuscript: handleCopyFullManuscript,
      openAiSuggest: handleSuggestWithAI,
      setStudioTab: (tabIndex: number) => {
        if (studioTabsList[tabIndex]) {
          setActiveStudioTab(studioTabsList[tabIndex])
        }
      },
      activeStudioTabIndex: studioTabsList.indexOf(activeStudioTab),
      isProtocolSaving: saving,
    })
    return () => {
      unregisterRibbonActions([
        'saveProtocol',
        'copyManuscript',
        'openAiSuggest',
        'setStudioTab',
        'activeStudioTabIndex',
        'isProtocolSaving',
      ])
    }
  }, [
    registerRibbonActions,
    unregisterRibbonActions,
    handleSave,
    handleCopyFullManuscript,
    handleSuggestWithAI,
    activeStudioTab,
    saving,
  ])

  if (loading) {
    return (
      <div className="protocol-page">
        <div className="empty-state">
          <Layers size={36} className="animate-spin icon-accent" />
          <p>Carregando estúdio de redação do protocolo...</p>
        </div>
      </div>
    )
  }

  // Quais itens da diretriz ATIVA cada seção do estúdio cobre. As seções têm
  // formato PRISMA, então nem toda diretriz mapeia — as que não mapeiam ficam
  // sem etiqueta, em vez de exibir a numeração de outra diretriz.
  const sectionItems = currentProtocolDef.sectionItems ?? {}
  const sectionItemsTitle = (key: ProtocolSectionKey, label: string): string => {
    const items = sectionItems[key]
    return items ? `${label} (Itens ${items} · ${currentProtocolDef.shortLabel})` : label
  }

  const aPrioriChecklistItems = currentProtocolDef.checklistItems.filter(
    (item) => item.phase === 'a_priori' || !item.phase
  )
  const aPosterioriChecklistItems = currentProtocolDef.checklistItems.filter(
    (item) => item.phase === 'a_posteriori'
  )

  return (
    <div className="protocol-page animate-fade-in">
      {/* Header */}
      <PageHeader
        title="Estúdio de Redação do Protocolo & Artigo"
        onBack={() => navigate('/projects')}
        meta={
          <div className="protocol-selector-inline">
            <label htmlFor="methodology-select">Diretriz:</label>
            <select
              id="methodology-select"
              className="protocol-select-control"
              value={activeProject?.methodology || 'PRISMA-ScR'}
              onChange={(e) => handleChangeMethodology(e.target.value as Methodology)}
              disabled={saving}
              title="Trocar protocolo metodológico deste projeto"
            >
              {PROTOCOL_OPTIONS.map((m) => (
                <option key={m} value={m}>
                  {PROTOCOL_CATALOG[m]?.name || m}
                </option>
              ))}
            </select>
            <span className="badge-methodology-header">{currentProtocolDef.badge}</span>
          </div>
        }
        subtitle={<span>Projeto: <strong>{activeProject?.title}</strong></span>}
        status={
          /* Confirmações são anunciadas: sem aria-live, quem usa leitor de tela
             salva o protocolo e não recebe retorno nenhum. */
          (saveSuccess || copiedNotification) && (
            <span className="save-indicator success animate-fade-in" role="status" aria-live="polite">
              <CheckCircle2 size={14} aria-hidden="true" />
              {saveSuccess ? 'Salvo com Sucesso!' : 'Artigo Copiado (Markdown)!'}
            </span>
          )
        }
        primaryAction={
          /* Ação primária ÚNICA. "Copiar Manuscrito" e "Sugerir com Assistência"
             saíram daqui: já vivem no ribbon, despachados pelo registro de
             comandos, e repetir os três criava dois caminhos sem estado comum.

             `onClick={handleSave}` entregava o MouseEvent como `forceOverwrite`:
             todo salvamento pelo cabeçalho ia sem `If-Match` e sobrescrevia o
             colega em silêncio — o oposto do que a Fase 3 existe para impedir. */
          <Button variant="primary" size="md" loading={saving} onClick={() => handleSave()} leftIcon={<Save size={14} />}>
            {saving ? 'Salvando…' : 'Salvar Tudo'}
          </Button>
        }
      />

      {/* Aviso de atualização remota por colega (Doc 43 §43.12, Fase 3) */}
      {remoteUpdateNotice && (
        <div className="protocol-remote-notice animate-fade-in">
          <Info size={16} className="icon-accent" aria-hidden="true" />
          <span>{remoteUpdateNotice}</span>
          <button
            type="button"
            className="btn-link-sm"
            onClick={() => id && loadProtocolAndProject(id)}
          >
            Recarregar dados
          </button>
        </div>
      )}

      {/* Indicador de presença de pesquisadores no protocolo */}
      {colegasPresentes.length > 0 && (
        <div className="presence-bar">
          <Users size={14} className="icon-accent" aria-hidden="true" />
          <span>Editando agora com você:</span>
          <div className="presence-pills">
            {colegasPresentes.map((u) => (
                <span
                  key={u.user_id}
                  className="presence-pill"
                  title={`Conectado desde ${new Date(u.connected_at).toLocaleTimeString()}`}
                >
                  @{u.username}
                </span>
              ))}
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="protocol-error-banner animate-fade-in">
          <AlertTriangle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Barra Superior de 4 Eixos & Governança Metodológica (doc 45 §4, §8.5, §12.1) */}
      <div className="protocol-governance-bar">
        <div className="protocol-governance-group">
          <span className="protocol-governance-label">Modo de trabalho</span>
          <div className="protocol-mode-switch" role="group" aria-label="Modo de preenchimento do protocolo">
            <button
              type="button"
              onClick={() => handleSwitchMode('simplificado')}
              aria-pressed={protocolMode === 'simplificado'}
              className={`protocol-mode-option ${protocolMode === 'simplificado' ? 'is-active' : ''}`}
            >
              Simplificado (14 campos)
            </button>
            <button
              type="button"
              onClick={() => handleSwitchMode('completo')}
              aria-pressed={protocolMode === 'completo'}
              className={`protocol-mode-option ${protocolMode === 'completo' ? 'is-active' : ''}`}
            >
              Completo (gabarito da diretriz)
            </button>
          </div>
        </div>

        <div className="protocol-governance-state">
          <span className="protocol-status">
            <span className="protocol-governance-label">Status</span>
            <span className={`protocol-status__chip ${currentVersion ? 'is-vigente' : 'is-rascunho'}`}>
              {currentVersion ? `Vigente (${currentVersion})` : 'Rascunho a priori'}
            </span>
          </span>

          <Button variant="outline" size="sm" onClick={() => setIsVersionDialogOpen(true)}>
            <Lock size={13} />
            <span>Versões &amp; Emendas</span>
          </Button>
        </div>
      </div>

      {/* Carimbo Normativo de Escopo no Modo Simplificado (doc 45 §8.4) */}
      {protocolMode === 'simplificado' && scopeStamp && (
        <div className="protocol-scope-stamp">
          <Info size={18} className="protocol-scope-stamp__icon" />
          <div className="protocol-scope-stamp__body">
            <div className="protocol-scope-stamp__head">
              <span className="protocol-scope-stamp__title">Carimbo de escopo metodológico</span>
              <button
                type="button"
                onClick={() => handleSwitchMode('completo')}
                className="protocol-scope-stamp__action"
              >
                Migrar para o modo Completo →
              </button>
            </div>
            <p className="protocol-scope-stamp__text">{scopeStamp}</p>
          </div>
        </div>
      )}

      {/* Medidor de Prontidão e Avaliação de Portões */}
      <ProtocolReadinessCard
        readiness={readiness}
        loading={readinessLoading}
        onRefresh={handleRefreshReadiness}
      />

      {/* Corpo: Modo Simplificado vs Modo Completo */}
      {protocolMode === 'simplificado' ? (
        <SimplifiedProtocolForm
          projectId={id || ''}
          title={manuscript.manuscript_title || activeProject?.title || ''}
          onTitleChange={(val) => updateManuscriptField('manuscript_title', val)}
          objective={objective}
          onObjectiveChange={setObjective}
          frameworkType={frameworkType}
          onFrameworkTypeChange={setFrameworkType}
          frameworkComponents={pico}
          onFrameworkComponentChange={(k, v) => setPico((prev) => ({ ...prev, [k]: v }))}
          reviewDesign={reviewDesign}
          onReviewDesignChange={handleSwitchReviewDesign}
          searchFilters={searchFilters}
          onSearchFiltersChange={setSearchFilters}
          searchStrategy={searchStrategies.find((s) => s.kind === 'canonica') || null}
          onSearchStrategySaved={(strat) => {
            const next = searchStrategies.filter((s) => s.id !== strat.id)
            setSearchStrategies([...next, strat])
            // Sincronizar pares de descritores caso descriptors.pt esteja vazio
            if (strat.blocks && strat.blocks.length >= 1) {
              const termsA = (strat.blocks[0]?.terms || []).filter((t: string) => t && t.trim())
              const termsB = (strat.blocks[1]?.terms || []).filter((t: string) => t && t.trim())
              const derived: string[] = []
              if (termsA.length > 0 && termsB.length > 0) {
                for (const a of termsA) {
                  for (const b of termsB) {
                    const qa = a.includes(' ') && !a.startsWith('"') ? `"${a.trim()}"` : a.trim()
                    const qb = b.includes(' ') && !b.startsWith('"') ? `"${b.trim()}"` : b.trim()
                    derived.push(`${qa} AND ${qb}`)
                    if (derived.length >= 5) break
                  }
                  if (derived.length >= 5) break
                }
              } else if (termsA.length > 0) {
                derived.push(...termsA.slice(0, 5).map((t: string) => (t.includes(' ') && !t.startsWith('"') ? `"${t.trim()}"` : t.trim())))
              }
              if (derived.length > 0) {
                setDescriptors((prev) => ({
                  ...prev,
                  pt: prev.pt.filter(Boolean).length > 0 ? prev.pt : derived,
                }))
              }
            }
            handleRefreshReadiness()
          }}
          descriptors={descriptors}
          onDescriptorsChange={setDescriptors}
          infoSources={manuscript.info_sources || ''}
          onInfoSourcesChange={(val) => updateManuscriptField('info_sources', val)}
          criteria={criteria}
          onCriteriaChange={setCriteria}
          extractionQuestions={questions}
          onExtractionQuestionsChange={setQuestions}
          searchExecutions={searchExecutions}
          dedupNotes={manuscript.search_strategy_notes || ''}
          onDedupNotesChange={(val) => updateManuscriptField('search_strategy_notes', val)}
          apoio={{
            montarGuia,
            ajuda: getFieldGuideline,
            contexto: getFullProtocolContext,
            projeto: {
              titulo: activeProject?.title,
              metodologia: activeProject?.methodology,
            },
          }}
        />
      ) : (
        /* Modo Completo: Studio Navigation Tabs with Clear Temporal Phase Grouping */
        <Tabs.Root
          className="studio-tabs-root"
          value={activeStudioTab}
          onValueChange={(v) => setActiveStudioTab(v as StudioTab)}
        >
          <div className="studio-tabs-container">
            <Tabs.List asChild>
              <div className="studio-tabs-bar-grouped" aria-label="Seções do protocolo">
              {/* GRUPO A PRIORI: PROTOCOLO DE PESQUISA */}
              <div className="tabs-group a-priori-group">
                <div className="tabs-group-header">
                  <span className="group-tag a-priori">A Priori</span>
                </div>
                <div className="tabs-group-buttons">
                  <Tabs.Trigger
                    value="ident_intro"
                    className={`studio-tab ${activeStudioTab === 'ident_intro' ? 'active' : ''}`}
                    title={sectionItemsTitle('ident_intro', '1. Identificação, Registro & Justificativa')}
                  >
                    <Edit3 size={13} className="tab-icon" />
                    <span className="tab-label">1. Identificação</span>
                    {sectionItems.ident_intro && <span className="tab-pill">{sectionItems.ident_intro}</span>}
                  </Tabs.Trigger>
                  <Tabs.Trigger
                    value="objectives"
                    className={`studio-tab ${activeStudioTab === 'objectives' ? 'active' : ''}`}
                    title={sectionItemsTitle('objectives', `2. Questão & Objetivos (${frameworkType})`)}
                  >
                    <BookOpen size={13} className="tab-icon" />
                    <span className="tab-label">2. Questão & Objetivos ({frameworkType})</span>
                    {sectionItems.objectives && <span className="tab-pill">{sectionItems.objectives}</span>}
                  </Tabs.Trigger>
                  <Tabs.Trigger
                    value="search_eligibility"
                    className={`studio-tab ${activeStudioTab === 'search_eligibility' ? 'active' : ''}`}
                    title={sectionItemsTitle('search_eligibility', '3. Fontes, Descritores & Elegibilidade')}
                  >
                    <Search size={13} className="tab-icon" />
                    <span className="tab-label">3. Fontes & Elegibilidade</span>
                    {sectionItems.search_eligibility && <span className="tab-pill">{sectionItems.search_eligibility}</span>}
                  </Tabs.Trigger>
                  <Tabs.Trigger
                    value="methods_extraction"
                    className={`studio-tab ${activeStudioTab === 'methods_extraction' ? 'active' : ''}`}
                    title={sectionItemsTitle('methods_extraction', '4. Seleção, Data Charting & Métodos de Síntese')}
                  >
                    <Filter size={13} className="tab-icon" />
                    <span className="tab-label">4. Métodos & Extração</span>
                    {sectionItems.methods_extraction && <span className="tab-pill">{sectionItems.methods_extraction}</span>}
                  </Tabs.Trigger>
                </div>
              </div>

              {/* GRUPO A POSTERIORI: SÍNTESE & REDAÇÃO FINAL */}
              <div className="tabs-group a-posteriori-group">
                <div className="tabs-group-header">
                  <span className="group-tag a-posteriori">A Posteriori</span>
                </div>
                <div className="tabs-group-buttons">
                  <Tabs.Trigger
                    value="synthesis_discussion"
                    className={`studio-tab ${activeStudioTab === 'synthesis_discussion' ? 'active' : ''}`}
                    title={sectionItemsTitle('synthesis_discussion', '5. Síntese dos Achados, Limitações & Conclusões')}
                  >
                    <Bookmark size={13} className="tab-icon" />
                    <span className="tab-label">5. Síntese & Discussão</span>
                    {sectionItems.synthesis_discussion && <span className="tab-pill">{sectionItems.synthesis_discussion}</span>}
                  </Tabs.Trigger>
                  <Tabs.Trigger
                    value="final_summary"
                    className={`studio-tab ${activeStudioTab === 'final_summary' ? 'active' : ''}`}
                    title={sectionItemsTitle('final_summary', '6. Resumo Estruturado Final do Artigo Concluído')}
                  >
                    <FileText size={13} className="tab-icon" />
                    <span className="tab-label">6. Resumo Final</span>
                    {sectionItems.final_summary && <span className="tab-pill">{sectionItems.final_summary}</span>}
                  </Tabs.Trigger>
                  <Tabs.Trigger
                    value="checklist"
                    className={`studio-tab checklist-tab ${activeStudioTab === 'checklist' ? 'active' : ''}`}
                    title={`Auditoria de Conformidade ${currentProtocolDef.shortLabel}`}
                  >
                    <CheckSquare size={13} className="tab-icon" />
                    <span className="tab-label">Auditoria {currentProtocolDef.shortLabel}</span>
                    <span className="tab-pill-count">{currentProtocolDef.checklistItems.length}</span>
                  </Tabs.Trigger>
                </div>
              </div>
            </div>
          </Tabs.List>
        </div>

      {/* ── ABA 1: IDENTIFICAÇÃO & JUSTIFICATIVA (A PRIORI) ──────────────── */}
      <Tabs.Content value="ident_intro" className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-priori-banner">
            <span className="phase-badge a-priori">Fase A Priori — Planejamento do Estudo</span>
            <p>
              Defina o título preliminar do protocolo, registre seu planejamento e estabeleça a justificativa teórica <strong>antes</strong> de iniciar a busca nas bases de dados.
            </p>
          </div>
                    <CampoDoProtocolo
            icone={<Edit3 size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Título Oficial da Revisão de Escopo (Scoping Review)"
            etiquetaItem={getFieldItemTag('manuscript_title', 1)}
            secao="TÍTULO"
            ajuda={getFieldGuideline('manuscript_title', 'Identifique claramente o trabalho e reflita os elementos centrais de elegibilidade (População/Atores, Conceito Central e Contexto Territorial).')}
            assistencia={
              <AIAssistButton
                fieldId="manuscript_title"
                fieldLabel="Título Oficial da Revisão"
                currentValue={manuscript.manuscript_title}
                fieldGuidelines="Identifique claramente o trabalho como uma Scoping Review / Revisão Sistemática e reflita os elementos centrais de elegibilidade (População/Atores, Conceito Central e Contexto Territorial no Desenvolvimento Regional)."
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('manuscript_title')}
                onApply={(text) => updateManuscriptField('manuscript_title', text)}
              />
            }
            guia={montarGuia('manuscript_title', 'title')}
          >
            <input
              type="text"
              className="protocol-input-large"
              placeholder="Ex: Governança Territorial e Arranjos Produtivos Locais no Desenvolvimento Regional do Semiárido: Uma Revisão de Escopo"
              value={manuscript.manuscript_title}
              onChange={(e) => updateManuscriptField('manuscript_title', e.target.value)}
            />
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<ShieldCheck size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Registro do Protocolo a Priori (Protocol & Registration)"
            etiquetaItem={getFieldItemTag('protocol_registration', 5)}
            secao="MÉTODOS / REGISTRO"
            ajuda={getFieldGuideline('protocol_registration', 'Informe a plataforma de registro público (ex: Open Science Framework - OSF, Figshare, Zenodo), identificador/DOI e data de submissão do protocolo.')}
            assistencia={
              <AIAssistButton
                fieldId="protocol_registration"
                fieldLabel="Registro do Protocolo (OSF / Repositório)"
                currentValue={manuscript.protocol_registration}
                fieldGuidelines={getFieldGuideline('protocol_registration', 'Informe a plataforma de registro público (ex: OSF, Figshare, Zenodo), DOI permanente e data de depósito a priori.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('protocol_registration')}
                onApply={(text) => updateManuscriptField('protocol_registration', text)}
              />
            }
            guia={montarGuia('protocol_registration', 'registration')}
          >
            <input
              type="text"
              className="protocol-input-large"
              placeholder="Ex: Registrado no Open Science Framework (OSF) sob o identificador https://doi.org/10.17605/OSF.IO/XXXXX em 15/08/2026."
              value={manuscript.protocol_registration}
              onChange={(e) => updateManuscriptField('protocol_registration', e.target.value)}
            />
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<BookOpen size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Justificativa e Estado da Arte (Rationale)"
            etiquetaItem={getFieldItemTag('rationale', 3)}
            secao="INTRODUÇÃO"
            ajuda={getFieldGuideline('rationale', 'Descreva o contexto do conhecimento existente na área e fundamente a necessidade da revisão nas Ciências Sociais Aplicadas e Desenvolvimento Regional.')}
            assistencia={
              <AIAssistButton
                fieldId="rationale"
                fieldLabel="Justificativa e Racional da Revisão"
                currentValue={manuscript.rationale}
                fieldGuidelines={getFieldGuideline('rationale', 'Descreva o contexto do conhecimento existente na área e fundamente a necessidade da revisão nas Ciências Sociais Aplicadas e Desenvolvimento Regional.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('rationale')}
                onApply={(text) => updateManuscriptField('rationale', text)}
              />
            }
            guia={montarGuia('rationale', 'rationale')}
          >
            <textarea
              rows={7}
              className="protocol-textarea"
              placeholder="Descreva o contexto do desenvolvimento regional, a relevância socioeconômica e institucional, a heterogeneidade das experiências territoriais existentes e por que o mapeamento amplo de evidências é a abordagem mais apropriada..."
              value={manuscript.rationale}
              onChange={(e) => updateManuscriptField('rationale', e.target.value)}
            />
          </CampoDoProtocolo>

        </Tabs.Content>

      {/* ── ABA 2: QUESTÃO & OBJETIVOS (A PRIORI) ───────────────────────── */}
      <Tabs.Content value="objectives" className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-priori-banner">
            <span className="phase-badge a-priori">Fase A Priori — Planejamento do Estudo</span>
            <p>
              Estruture o objetivo geral e desmembre os conceitos orientadores no framework teórico ({frameworkType}) para guiar a busca sem ambiguidades.
            </p>
          </div>
          <Card surface="secundaria" className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">{getFieldItemTag('objective', 4)}</span>
              <span className="item-section-tag">INTRODUÇÃO / OBJETIVOS</span>
            </div>
            <div className="card-header-with-toggle">
              <div className="card-section-title">
                <Layers size={20} className="icon-accent" />
                <h2>Objetivos e Framework da Questão ({frameworkType})</h2>
              </div>
              <div className="framework-toggle-buttons">
                <button
                  type="button"
                  className={`btn-framework-opt ${frameworkType === 'PCC' ? 'active' : ''}`}
                  onClick={() => setFrameworkType('PCC')}
                >
                  PCC ({currentProtocolDef.shortLabel} / Escopo)
                </button>
                <button
                  type="button"
                  className={`btn-framework-opt ${frameworkType === 'PICO' ? 'active' : ''}`}
                  onClick={() => setFrameworkType('PICO')}
                >
                  PICO (Sistemática)
                </button>
              </div>
            </div>

            <div className="card-section-title-with-actions" style={{ marginTop: 'var(--space-2)' }}>
              <p className="section-help" style={{ margin: 0 }}>
                {frameworkType === 'PCC'
                  ? getFieldGuideline('objective', `Estruture os objetivos centrais em População/Atores (P), Conceito Central (C) e Contexto Territorial (C).`)
                  : getFieldGuideline('objective', `Estruture os objetivos em População/Atores (P), Intervenção/Política (I), Comparador (C) e Desfecho (O).`)}
              </p>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="objective"
                  fieldLabel="Objetivo Geral da Revisão"
                  currentValue={objective}
                  fieldGuidelines={getFieldGuideline('objective', `Formule o objetivo geral da revisão delimitando a questão norteadora com base nos elementos ${frameworkType} em Ciências Sociais Aplicadas / Desenvolvimento Regional.`)}
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('objective')}
                  onApply={(text) => setObjective(text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.objective ? 'active' : ''}`}
                  onClick={() => toggleHelp('objective')}
                  title="Ver guia de formulação de objetivos e PCC"
                >
                  <HelpCircle size={16} />
                  <span>Guia dos Objetivos (?)</span>
                </button>
              </div>
            </div>

            {helpOpen.objective && (
              <div className="structured-guide-box animate-fade-in" style={{ marginTop: 'var(--space-3)' }}>
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Formulação de Objetivos {frameworkType} ({getFieldItemRef('objective')})</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Mapear e sintetizar a extensão, variedade e características das evidências científicas disponíveis sobre [Conceito Central / Políticas] aplicadas a [População / Atores Sociais / Setor Produtivo] no âmbito de [Contexto Territorial / Regional], identificando lacunas no conhecimento e implicações para a governança local.`
                      if (objective && !window.confirm('Substituir objetivo geral pelo modelo?')) return
                      setObjective(template)
                    }}
                  >
                    <Plus size={14} /> Inserir Modelo no Objetivo
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">P — População / Atores</span>
                    <p>Atores sociais, produtores, organizações, cooperativas, comunidades ou instituições.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">C — Conceito Central</span>
                    <p>Arranjos produtivos, políticas públicas, governança territorial, inovação regional ou sustentabilidade.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">C — Contexto Territorial</span>
                    <p>Municípios, bacias hidrográficas, regiões metropolitanas, semiárido ou recortes espaciais.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">M — Mapeamento</span>
                    <p>Dimensões de impacto socioeconômico e lacunas de literatura caracterizadas.</p>
                  </div>
                </div>
              </div>
            )}

            <div className="form-group" style={{ margin: 'var(--space-4) 0' }}>
              <label>Objetivo Geral da Revisão:</label>
              <textarea
                rows={3}
                className="protocol-textarea"
                placeholder="Ex: Mapear e sintetizar a extensão, variedade e características das evidências científicas sobre..."
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
              />
            </div>

            <div className="pico-grid">
              <div className="pico-field">
                <div className="pico-label-row">
                  <label>
                    <strong>P</strong> — População / Atores Sociais
                  </label>
                  <AIAssistButton
                    fieldId="pico_population"
                    fieldLabel="População e Atores Sociais (P)"
                    currentValue={pico.population}
                    fieldGuidelines="Delimite os atores sociais, grupos produtivos, cooperativas, comunidades ou organizações em foco no contexto regional."
                    projectTitle={activeProject?.title}
                    methodology={activeProject?.methodology}
                    projectContext={getFullProtocolContext('pico_population')}
                    compact
                    onApply={(text) => setPico({ ...pico, population: text })}
                  />
                </div>
                <textarea
                  rows={2}
                  placeholder="Ex: Produtores locais, cooperativas, pequenas e médias empresas, comunidades rurais ou gestores públicos..."
                  value={pico.population}
                  onChange={(e) => setPico({ ...pico, population: e.target.value })}
                />
              </div>

              <div className="pico-field">
                <div className="pico-label-row">
                  <label>
                    <strong>{frameworkType === 'PCC' ? 'C' : 'I'}</strong> —{' '}
                    {frameworkType === 'PCC' ? 'Conceito Central (Concept)' : 'Intervenção / Política (Intervention)'}
                  </label>
                  <AIAssistButton
                    fieldId="pico_intervention"
                    fieldLabel="Conceito Central / Política Pública (C)"
                    currentValue={pico.intervention}
                    fieldGuidelines="Defina o conceito central, política pública territorial, APL, governança ou instrumento socioeconômico investigado."
                    projectTitle={activeProject?.title}
                    methodology={activeProject?.methodology}
                    projectContext={getFullProtocolContext('pico_intervention')}
                    compact
                    onApply={(text) => setPico({ ...pico, intervention: text })}
                  />
                </div>
                <textarea
                  rows={2}
                  placeholder={
                    frameworkType === 'PCC'
                      ? 'Ex: Arranjos Produtivos Locais (APLs), Governança Territorial, Sistemas Regionais de Inovação...'
                      : 'Ex: Políticas públicas de fomento, programas de extensão tecnológica ou incentivos fiscais...'
                  }
                  value={pico.intervention}
                  onChange={(e) => setPico({ ...pico, intervention: e.target.value })}
                />
              </div>

              <div className="pico-field">
                <div className="pico-label-row">
                  <label>
                    <strong>{frameworkType === 'PCC' ? 'C' : 'C'}</strong> —{' '}
                    {frameworkType === 'PCC' ? 'Contexto Territorial (Context)' : 'Comparador (Comparison)'}
                  </label>
                  <AIAssistButton
                    fieldId="pico_comparison"
                    fieldLabel="Contexto Territorial / Espacial (C)"
                    currentValue={pico.comparison}
                    fieldGuidelines="Delimite o recorte espacial, territorial, regional ou institucional (ex: semiárido, arranjos locais, bacias, municípios)."
                    projectTitle={activeProject?.title}
                    methodology={activeProject?.methodology}
                    projectContext={getFullProtocolContext('pico_comparison')}
                    compact
                    onApply={(text) => setPico({ ...pico, comparison: text })}
                  />
                </div>
                <textarea
                  rows={2}
                  placeholder={
                    frameworkType === 'PCC'
                      ? 'Ex: Municípios do semiárido, regiões metropolitanas, áreas rurais ou contexto latino-americano...'
                      : 'Ex: Cenários de ausência de política de fomento ou arranjos produtivos convencionais...'
                  }
                  value={pico.comparison}
                  onChange={(e) => setPico({ ...pico, comparison: e.target.value })}
                />
              </div>

              <div className="pico-field">
                <div className="pico-label-row">
                  <label>
                    <strong>{frameworkType === 'PCC' ? 'M' : 'O'}</strong> —{' '}
                    {frameworkType === 'PCC' ? 'Mapeamento de Escopo' : 'Desfecho Socioeconômico (Outcomes)'}
                  </label>
                  <AIAssistButton
                    fieldId="pico_outcome"
                    fieldLabel="Mapeamento de Escopo / Desfecho (M/O)"
                    currentValue={pico.outcome}
                    fieldGuidelines="Defina os eixos de mapeamento, tipologia de evidências, impactos socioeconômicos e lacunas de conhecimento."
                    projectTitle={activeProject?.title}
                    methodology={activeProject?.methodology}
                    projectContext={getFullProtocolContext('pico_outcome')}
                    compact
                    onApply={(text) => setPico({ ...pico, outcome: text })}
                  />
                </div>
                <textarea
                  rows={2}
                  placeholder={
                    frameworkType === 'PCC'
                      ? 'Ex: Mapear impactos no desenvolvimento socioeconômico, geração de emprego/renda e lacunas teóricas...'
                      : 'Ex: Crescimento do PIB local, taxa de inovação, retenção de capital e sustentabilidade...'
                  }
                  value={pico.outcome}
                  onChange={(e) => setPico({ ...pico, outcome: e.target.value })}
                />
              </div>
            </div>
          </Card>
        </Tabs.Content>

      {/* ── ABA 3: FONTES & ELEGIBILIDADE (A PRIORI) ────────────────────── */}
      <Tabs.Content value="search_eligibility" className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-priori-banner">
            <span className="phase-badge a-priori">Fase A Priori — Planejamento do Estudo</span>
            <p>
              Estabeleça os critérios de inclusão/exclusão e as strings de busca em pares ("termo_1" AND "termo_2") compatíveis com a BDTD (VuFind) antes da coleta.
            </p>
          </div>
                    <CampoDoProtocolo
            icone={<Filter size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Critérios de Elegibilidade (Eligibility Criteria)"
            etiquetaItem={getFieldItemTag('criteria', 6)}
            secao="MÉTODOS / ELEGIBILIDADE"
            ajuda={getFieldGuideline('criteria', 'Defina as regras de inclusão e exclusão com base na população/atores, conceitos avaliados, recortes territoriais, idiomas e períodos considerados.')}
            assistencia={
              <AIAssistButton
                fieldId="criteria"
                fieldLabel="Critérios de Elegibilidade (Inclusão e Exclusão)"
                currentValue={criteria.map((c) => (c.is_exclusion ? 'EXC: ' : 'INC: ') + c.text).join('\n')}
                fieldGuidelines="Gere critérios de inclusão (prefixados com 'INC: ') e de exclusão (prefixados com 'EXC: '), um por linha, alinhados com o escopo temático em Ciências Sociais Aplicadas / Desenvolvimento Regional."
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('criteria')}
                onApply={(text) => {
                  const lines = text
                    .split('\n')
                    .map((l) => l.trim())
                    .filter(Boolean)
                  const parsedCriteria = lines.map((l, idx) => {
                    const isExc = l.toUpperCase().startsWith('EXC:')
                    const cleanText = l.replace(/^(INC:|EXC:)\s*/i, '').trim()
                    return {
                      text: cleanText || l,
                      is_exclusion: isExc,
                      order: idx,
                    }
                  })
                  if (parsedCriteria.length > 0) {
                    setCriteria(parsedCriteria)
                  }
                }}
              />
            }
            guia={montarGuia('criteria', 'criteria')}
          >
            <div className="criteria-list">
              {criteria.map((crit, idx) => (
                <Card surface="primaria" relief="afundado" key={idx} className="criterion-card">
                  <span className={`criterion-code ${crit.is_exclusion ? 'exclusion' : 'inclusion'}`}>
                    {crit.is_exclusion ? `EXC-${idx + 1}` : `INC-${idx + 1}`}
                  </span>
                  <input
                    type="text"
                    className="criterion-desc-input"
                    placeholder={
                      crit.is_exclusion
                        ? 'Ex: EXC: Estudos sem fundamentação empírica/documental, ensaios puramente opinativos ou sem foco no desenvolvimento territorial.'
                        : 'Ex: INC: Estudos empíricos que avaliem arranjos produtivos locais, governança ou políticas públicas territoriais.'
                    }
                    value={crit.text}
                    onChange={(e) => updateCriterion(idx, e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn-icon danger"
                    onClick={() => removeCriterion(idx)}
                    title="Remover critério"
                  >
                    <Trash2 size={16} />
                  </button>
                </Card>
              ))}
            </div>

            <div className="add-criterion-form">
              <button type="button" className="btn-secondary small" onClick={() => addCriterion(false)}>
                <Plus size={14} /> Adicionar Critério de Inclusão (INC)
              </button>
              <button type="button" className="btn-secondary small" onClick={() => addCriterion(true)}>
                <Plus size={14} /> Adicionar Critério de Exclusão (EXC)
              </button>
            </div>
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<Search size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Fontes de Informação & Período de Cobertura (Information Sources)"
            etiquetaItem={getFieldItemTag('info_sources', 7)}
            secao="MÉTODOS / FONTES"
            ajuda={getFieldGuideline('info_sources', 'Liste todas as bases consultadas (BDTD, SciELO, Scopus, OpenAlex), literatura cinzenta, busca manual e a data exata da busca mais recente.')}
            assistencia={
              <AIAssistButton
                fieldId="info_sources"
                fieldLabel="Fontes de Informação e Bases"
                currentValue={manuscript.info_sources}
                fieldGuidelines={getFieldGuideline('info_sources', 'Descreva todas as bases de dados bibliográficas (BDTD, SciELO, Scopus, OpenAlex), literatura cinzenta, recorte temporal e a data da busca mais recente.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('info_sources')}
                onApply={(text) => updateManuscriptField('info_sources', text)}
              />
            }
            guia={montarGuia('info_sources', 'sources')}
          >
            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: Foram consultadas as bases bibliográficas BDTD (Teses e Dissertações), SciELO, Scopus e OpenAlex, cobrindo o período de 2015 a agosto de 2026. A busca eletrônica mais recente foi executada em 15/08/2026."
              value={manuscript.info_sources}
              onChange={(e) => updateManuscriptField('info_sources', e.target.value)}
            />
          </CampoDoProtocolo>


          <Card surface="secundaria" className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">{getFieldItemTag('search_descriptors', 8)}</span>
              <span className="item-section-tag">MÉTODOS / DESCRITORES</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <Search size={20} className="icon-accent" />
                <h2>Estratégia de Busca Eletrônica em Pares (Search Strategy)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId={`descriptors_${activeLangTab}`}
                  fieldLabel={`Descritores de Busca em Pares (${activeLangTab.toUpperCase()})`}
                  currentValue={descriptors[activeLangTab].join('\n')}
                  fieldGuidelines={`Gere pares de descritores (recomendado ~5 pares) no formato "termo 1" AND "termo 2", separados por quebra de linha. Mantenha o formato de pares (máximo 2 termos por linha) para compatibilidade com o VuFind da BDTD. Idioma: ${activeLangTab === 'pt' ? 'Português' : activeLangTab === 'en' ? 'Inglês' : 'Espanhol'}.`}
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext(`descriptors_${activeLangTab}`)}
                  onApply={(text) => {
                    const lines = text
                      .split('\n')
                      .map((l) => l.trim())
                      .filter(Boolean)
                    if (lines.length > 0) {
                      setDescriptors((prev) => ({
                        ...prev,
                        [activeLangTab]: lines,
                      }))
                    }
                  }}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.descriptors ? 'active' : ''}`}
                  onClick={() => toggleHelp('descriptors')}
                  title="Ver regras de descritores VuFind / BDTD"
                >
                  <HelpCircle size={16} />
                  <span>Guia dos Descritores (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme {getFieldItemRef('search_descriptors')} e Diretrizes Revsist: Formulação em <strong>pares de termos com AND</strong> (máximo 2 termos por expressão e sugestão de ~5 pares por idioma), garantindo perfeita compatibilidade com o motor VuFind da BDTD.
            </p>

            {helpOpen.descriptors && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Regras de Descritores em Pares (Compatibilidade VuFind / BDTD)</strong>
                  </div>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Estrutura em Pares</span>
                    <p>No máximo 2 termos combinados com AND por expressão (ex: <code>"desenvolvimento regional" AND "arranjos produtivos"</code>).</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Sugestão de ~5 Pares por Idioma</span>
                    <p>Recomenda-se cerca de 5 pares em Português, 5 em Inglês e 5 em Espanhol para equilibrar especificidade e abrangência sem sobrecarga de consultas.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Aspas em Termos Compostos</span>
                    <p>Utilize aspas para garantir busca exata de expressões compostas.</p>
                  </div>
                </div>
              </div>
            )}

            {/* Language Tabs */}
            <div className="lang-tabs">
              <button
                type="button"
                className={`lang-tab ${activeLangTab === 'pt' ? 'active' : ''}`}
                onClick={() => setActiveLangTab('pt')}
              >
                🇧🇷 Português ({descriptors.pt.filter(Boolean).length})
              </button>
              <button
                type="button"
                className={`lang-tab ${activeLangTab === 'en' ? 'active' : ''}`}
                onClick={() => setActiveLangTab('en')}
              >
                🇺🇸 Inglês ({descriptors.en.filter(Boolean).length})
              </button>
              <button
                type="button"
                className={`lang-tab ${activeLangTab === 'es' ? 'active' : ''}`}
                onClick={() => setActiveLangTab('es')}
              >
                🇪🇸 Espanhol ({descriptors.es.filter(Boolean).length})
              </button>
            </div>

            <div className="descriptors-list">
              {descriptors[activeLangTab].map((desc, idx) => (
                <div key={idx} className="descriptor-row">
                  <span className="descriptor-index">#{idx + 1}</span>
                  <input
                    type="text"
                    className="descriptor-input"
                    placeholder='Ex: "desenvolvimento regional" AND "arranjos produtivos"'
                    value={desc}
                    onChange={(e) => updateDescriptor(activeLangTab, idx, e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn-icon danger"
                    title="Remover par de descritores"
                    onClick={() => removeDescriptor(activeLangTab, idx)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}

              <button
                type="button"
                className="btn-add-descriptor"
                onClick={() => addDescriptor(activeLangTab)}
              >
                <Plus size={14} /> Adicionar Par de Descritores ({descriptors[activeLangTab].length})
              </button>
            </div>
          </Card>

          {/* Seção 4: Recorte & Filtros Estruturados da Busca */}
          <Card surface="secundaria" className="protocol-card search-filters-card">
            <div className="item-header-meta">
              <span className="item-tag essential">{getFieldItemTag('search_filters', 7)}</span>
              <span className="item-section-tag">MÉTODOS / RECORTE & FILTROS ESTRUTURADOS</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <Sliders size={20} className="icon-accent" />
                <h2>Recorte Temporal, Idiomas, Tipos de Documento & Bases Alvo</h2>
              </div>
              <div className="card-header-actions">
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.searchFilters ? 'active' : ''}`}
                  onClick={() => toggleHelp('searchFilters')}
                  title="Ver orientações metodológicas para filtros de busca"
                >
                  <HelpCircle size={16} />
                  <span>Guia dos Filtros (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">{ANCORAGEM_NORMATIVA.limitesDeBusca}</p>

            {helpOpen.searchFilters && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Orientações Metodológicas para Filtros Estruturados</strong>
                  </div>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Recorte Temporal</span>
                    <p>Delimite o ano inicial e final com base na evolução histórica do tema ou marcos regulatórios/conceituais em Ciências Sociais Aplicadas.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Restrições Linguísticas</span>
                    <p>Documente os idiomas elegíveis (ex: Português, Inglês e Espanhol) para evitar viés de publicação não justificado.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Tipos de Produção</span>
                    <p>Especifique se a revisão inclui literatura cinzenta (Teses e Dissertações na BDTD) e artigos revisados por pares.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">4. Bases Alvo</span>
                    <p>Selecione as bases que serão consultadas na etapa de Coleta para manter o alinhamento rigoroso entre protocolo e execução.</p>
                  </div>
                </div>
              </div>
            )}

            <div className="search-filters-form-grid">
              {/* 1. Recorte Temporal */}
              <div className="filter-section-block">
                <div className="filter-block-header">
                  <Calendar size={16} className="icon-accent" />
                  <h4>1. Recorte Temporal (Anos de Publicação)</h4>
                </div>
                <div className="temporal-controls-container">
                  <div className="temporal-inputs-row">
                    <div className="temporal-input-group">
                      <label htmlFor="filter-year-start">Ano Inicial (De):</label>
                      <input
                        id="filter-year-start"
                        type="number"
                        min="1900"
                        max="2100"
                        placeholder="Ex: 2015"
                        value={searchFilters.year_start ?? ''}
                        onChange={(e) =>
                          updateSearchFilter('year_start', e.target.value ? Number(e.target.value) : null)
                        }
                      />
                    </div>
                    <span className="temporal-separator">até</span>
                    <div className="temporal-input-group">
                      <label htmlFor="filter-year-end">Ano Final (Até):</label>
                      <input
                        id="filter-year-end"
                        type="number"
                        min="1900"
                        max="2100"
                        placeholder="Ex: 2026"
                        value={searchFilters.year_end ?? ''}
                        onChange={(e) =>
                          updateSearchFilter('year_end', e.target.value ? Number(e.target.value) : null)
                        }
                      />
                    </div>
                  </div>
                  <div className="temporal-presets-row">
                    <span className="presets-label">Atalhos:</span>
                    <button
                      type="button"
                      className="btn-preset-chip"
                      onClick={() => applyYearPreset(5)}
                    >
                      Últimos 5 Anos
                    </button>
                    <button
                      type="button"
                      className="btn-preset-chip"
                      onClick={() => applyYearPreset(10)}
                    >
                      Últimos 10 Anos
                    </button>
                    <button
                      type="button"
                      className="btn-preset-chip"
                      onClick={() => applyYearPreset(null)}
                    >
                      Sem Limite Temporal
                    </button>
                  </div>
                </div>
              </div>

              {/* 2. Restrição de Acesso Aberto */}
              <div className="filter-section-block">
                <div className="filter-block-header">
                  <Lock size={16} className="icon-accent" />
                  <h4>2. Modelo de Acesso</h4>
                </div>
                <label className={`oa-toggle-card ${searchFilters.open_access_only ? 'active' : ''}`}>
                  <input
                    type="checkbox"
                    checked={Boolean(searchFilters.open_access_only)}
                    onChange={(e) => updateSearchFilter('open_access_only', e.target.checked)}
                  />
                  <div className="oa-toggle-info">
                    <div className="oa-toggle-title">
                      {searchFilters.open_access_only ? <Unlock size={14} className="text-success" /> : <Lock size={14} />}
                      <strong>Restringir apenas a publicações de Acesso Aberto (Open Access)</strong>
                    </div>
                    <p>Quando ativado, filtra somente trabalhos disponíveis publicamente e sem paywall nas bases compatíveis.</p>
                  </div>
                </label>
              </div>

              {/* 3. Idiomas Elegíveis */}
              <div className="filter-section-block">
                <div className="filter-block-header">
                  <Globe size={16} className="icon-accent" />
                  <h4>3. Idiomas Elegíveis ({searchFilters.languages?.length || 0} selecionados)</h4>
                </div>
                <div className="filter-chips-grid">
                  {AVAILABLE_LANGUAGES.map((lang) => {
                    const isSelected = searchFilters.languages?.includes(lang.code)
                    return (
                      <button
                        key={lang.code}
                        type="button"
                        className={`filter-chip-btn ${isSelected ? 'active' : ''}`}
                        onClick={() => toggleFilterLanguage(lang.code)}
                      >
                        <span className="chip-flag">{lang.flag}</span>
                        <span className="chip-label">{lang.label}</span>
                        {isSelected ? <Check size={13} className="chip-check" /> : null}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* 4. Tipos de Documento Aceitos */}
              <div className="filter-section-block">
                <div className="filter-block-header">
                  <FileText size={16} className="icon-accent" />
                  <h4>4. Tipos de Documento Aceitos ({searchFilters.document_types?.length || 0} selecionados)</h4>
                </div>
                <div className="filter-chips-grid doc-types-grid">
                  {AVAILABLE_DOC_TYPES.map((dt) => {
                    const isSelected = searchFilters.document_types?.includes(dt.id)
                    return (
                      <button
                        key={dt.id}
                        type="button"
                        className={`filter-chip-btn ${isSelected ? 'active' : ''}`}
                        onClick={() => toggleFilterDocType(dt.id)}
                      >
                        <span className="chip-icon">{dt.icon}</span>
                        <span className="chip-label">{dt.label}</span>
                        {isSelected ? <Check size={13} className="chip-check" /> : null}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* 5. Instituições / Afiliações Alvo (Opcional) */}
              <div className="filter-section-block full-width">
                <div className="filter-block-header">
                  <Building2 size={16} className="icon-accent" />
                  <h4>5. Instituições / Afiliações de Origem (Opcional)</h4>
                </div>
                <div className="institutions-input-container">
                  <input
                    type="text"
                    className="form-control institution-text-input"
                    placeholder="Ex: USP, UFMS, UFRJ, UNICAMP, IPEA (deixe em branco para incluir todas as instituições)"
                    value={(searchFilters.institutions || []).join(', ')}
                    onChange={(e) => {
                      const list = e.target.value
                        .split(',')
                        .map((s) => s.trim())
                        .filter(Boolean)
                      updateSearchFilter('institutions', list)
                    }}
                  />
                  <span className="meta-hint">
                    {searchFilters.institutions?.length
                      ? `Filtrando por ${searchFilters.institutions.length} instituição(ões): ${searchFilters.institutions.join(', ')}`
                      : 'Nenhuma restrição institucional (todas as instituições aceitas).'}
                  </span>
                </div>
              </div>

              {/* 6. Bases de Dados Alvo do Protocolo */}
              <div className="filter-section-block full-width">
                <div className="filter-block-header">
                  <Database size={16} className="icon-accent" />
                  <h4>6. Bases de Dados Acadêmicas Alvo do Protocolo ({searchFilters.target_databases?.length || 0} selecionadas)</h4>
                </div>
                <div className="target-dbs-grid">
                  {AVAILABLE_DATABASES.map((db) => {
                    const isSelected = (searchFilters.target_databases || ['BDTD', 'SciELO', 'OpenAlex', 'Scopus']).includes(db.id)
                    return (
                      <div
                        key={db.id}
                        className={`target-db-card ${isSelected ? 'selected' : ''}`}
                        onClick={() => toggleTargetDatabase(db.id)}
                      >
                        <div className="target-db-header">
                          <label className="target-db-checkbox-label" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleTargetDatabase(db.id)}
                            />
                            <span className="target-db-name">{db.name}</span>
                          </label>
                          <span className="target-db-badge">{db.badge}</span>
                        </div>
                        <p className="target-db-desc">{db.desc}</p>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* 7. Matriz de Transparência & Comportamento dos Filtros por Base */}
              <div className="filter-section-block full-width filter-matrix-block">
                <div className="filter-block-header">
                  <Info size={16} className="icon-accent" />
                  <h4>7. Transparência Metodológica: Comportamento dos Filtros por Base</h4>
                </div>
                <p className="matrix-description">
                  Cada base de dados acadêmica possui regras de API e limitações de servidor distintas.
                  A tabela abaixo detalha quando cada filtro é aplicado diretamente na consulta remota (<strong>Filtro Nativo</strong>)
                  ou após o download dos registros brutos em memória local (<strong>Pós-Filtro Local</strong>):
                </p>

                <div className="filter-matrix-table-wrapper">
                  <table className="filter-matrix-table">
                    <thead>
                      <tr>
                        <th>Base de Dados</th>
                        <th>Período</th>
                        <th>Idioma</th>
                        <th>Tipos de Documento</th>
                        <th>Instituições</th>
                        <th>Acesso Aberto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {FILTER_BEHAVIOR_MATRIX.map((row) => (
                        <tr key={row.db}>
                          <td className="matrix-db-cell">
                            <strong>{row.db}</strong>
                          </td>
                          <td>
                            <span className={`matrix-mode-badge ${row.years.mode.includes('Nativo') ? 'native' : 'post'}`}>
                              {row.years.mode}
                            </span>
                            <span className="matrix-note">{row.years.note}</span>
                          </td>
                          <td>
                            <span className={`matrix-mode-badge ${row.languages.mode.includes('Nativo') ? 'native' : 'post'}`}>
                              {row.languages.mode}
                            </span>
                            <span className="matrix-note">{row.languages.note}</span>
                          </td>
                          <td>
                            <span className={`matrix-mode-badge ${row.types.mode.includes('Nativo') ? 'native' : 'post'}`}>
                              {row.types.mode}
                            </span>
                            <span className="matrix-note">{row.types.note}</span>
                          </td>
                          <td>
                            <span className={`matrix-mode-badge ${row.institutions.mode.includes('Nativo') ? 'native' : 'post'}`}>
                              {row.institutions.mode}
                            </span>
                            <span className="matrix-note">{row.institutions.note}</span>
                          </td>
                          <td>
                            <span className={`matrix-mode-badge ${row.oa.mode.includes('Nativo') ? 'native' : 'post'}`}>
                              {row.oa.mode}
                            </span>
                            <span className="matrix-note">{row.oa.note}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="matrix-info-alert">
                  <Info size={16} className="text-info" />
                  <div className="matrix-info-alert-content">
                    <strong>Por que o Pós-Filtro Local é necessário?</strong>
                    <p>
                      Em servidores como o da <strong>BDTD (VuFind)</strong>, o envio de múltiplos filtros combinados aciona o Firewall de Aplicação Web (WAF) retornando erro <code>429 (Too Many Requests)</code>.
                      Ao aplicar o filtro de idioma localmente em memória após a recuperação, o Revsist garante 100% de conformidade com o protocolo sem risco de sobrecarga ou bloqueio.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </Tabs.Content>

      {/* ── ABA 4: MÉTODOS & EXTRAÇÃO (A PRIORI) ────────────────────────── */}
      <Tabs.Content value="methods_extraction" className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-priori-banner">
            <span className="phase-badge a-priori">Fase A Priori — Planejamento do Estudo</span>
            <p>
              Planeje os procedimentos de triagem, o questionário com as variáveis que serão extraídas de cada estudo incluído e os métodos previstos de síntese.
            </p>
          </div>
                    <CampoDoProtocolo
            icone={<Filter size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Processo de Seleção de Estudos & Calibração (Selection Process)"
            etiquetaItem={getFieldItemTag('selection_process', 9)}
            secao="MÉTODOS / TRIAGEM"
            ajuda={getFieldGuideline('selection_process', 'Descreva como foi realizada a triagem em duas etapas (1: Títulos e Resumos; 2: Texto Completo), o número de revisores independentes e resolução de divergências.')}
            assistencia={
              <AIAssistButton
                fieldId="selection_process"
                fieldLabel="Processo de Seleção de Estudos"
                currentValue={manuscript.selection_process}
                fieldGuidelines={getFieldGuideline('selection_process', 'Especifique os métodos de triagem em duas etapas (títulos/resumos e texto integral), duplo-cego independente, teste piloto prévio e resolução de conflitos.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('selection_process')}
                onApply={(text) => updateManuscriptField('selection_process', text)}
              />
            }
            guia={montarGuia('selection_process', 'selection')}
          >
            <textarea
              rows={5}
              className="protocol-textarea"
              placeholder="Ex: A triagem foi conduzida em duas etapas independentes através do sistema Revsist. Previamente, realizou-se exercício de calibração com amostra piloto de 50 artigos para alinhamento de critérios. Divergências na decisão foram resolvidas por consenso entre os revisores..."
              value={manuscript.selection_process}
              onChange={(e) => updateManuscriptField('selection_process', e.target.value)}
            />
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<HelpCircle size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Processo de Extração de Dados (Data Charting Process)"
            etiquetaItem={getFieldItemTag('data_charting_process', 10)}
            secao="MÉTODOS / EXTRAÇÃO"
            ajuda={getFieldGuideline('data_charting_process', 'Descreva os procedimentos de preenchimento do formulário de mapeamento (data charting form), se foi calibrado previamente e como os dados foram checados e confirmados.')}
            assistencia={
              <AIAssistButton
                fieldId="data_charting_process"
                fieldLabel="Processo de Extração de Dados"
                currentValue={manuscript.data_charting_process}
                fieldGuidelines={getFieldGuideline('data_charting_process', 'Descreva o formulário de extração de dados calibrado, o procedimento de extração em duplicata independente e a resolução de discordâncias.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('data_charting_process')}
                onApply={(text) => updateManuscriptField('data_charting_process', text)}
              />
            }
            guia={montarGuia('data_charting_process', 'charting')}
          >
            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: A extração de dados foi realizada por meio de formulário padronizado e calibrado no Revsist, cobrindo metadados bibliográficos, setor econômico analisado, modelo de governança, impactos no desenvolvimento local e limitações reportadas..."
              value={manuscript.data_charting_process}
              onChange={(e) => updateManuscriptField('data_charting_process', e.target.value)}
            />
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<HelpCircle size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Perguntas e Variáveis de Mapeamento (Data Items)"
            etiquetaItem={getFieldItemTag('extraction_questions', 11)}
            secao="MÉTODOS / VARIÁVEIS"
            ajuda={getFieldGuideline('extraction_questions', 'Liste as perguntas estruturadas de extração que responderão aos objetivos e mapearão as variáveis de cada estudo na Triagem 2.')}
            assistencia={
              <AIAssistButton
                fieldId="questions"
                fieldLabel="Perguntas de Mapeamento e Extração"
                currentValue={questions.map((q) => q.text || (q as any).question || '').join('\n')}
                fieldGuidelines="Gere perguntas estruturadas de extração (uma por linha) para mapear atores, conceitos, variáveis metodológicas e impactos socioeconômicos dos estudos incluídos nas Ciências Sociais Aplicadas e Desenvolvimento Regional."
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('questions')}
                onApply={(text) => {
                  const lines = text
                    .split('\n')
                    .map((l) => l.trim())
                    .filter(Boolean)
                  const parsedQuestions = lines.map((l, idx) => ({
                    text: l.replace(/^Q-?\d+[:.]\s*/i, '').trim(),
                    order: idx,
                  }))
                  if (parsedQuestions.length > 0) {
                    setQuestions(parsedQuestions)
                  }
                }}
              />
            }
            guia={montarGuia('extraction_questions', 'dataItems')}
          >


            <div className="criteria-list">
              {questions.map((q, idx) => (
                <Card surface="primaria" relief="afundado" key={q.id || idx} className="criterion-card">
                  <span className="criterion-code inclusion">Q-{idx + 1}</span>
                  <input
                    type="text"
                    className="criterion-desc-input"
                    placeholder="Ex: Qual foi o modelo de governança territorial ou instrumento de política pública avaliado?"
                    value={q.text || (q as any).question || ''}
                    onChange={(e) => updateQuestion(idx, e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn-icon danger"
                    onClick={() => removeQuestion(idx)}
                    title="Remover pergunta"
                  >
                    <Trash2 size={16} />
                  </button>
                </Card>
              ))}
            </div>

            <div style={{ marginTop: 'var(--space-3)' }}>
              <button type="button" className="btn-secondary small" onClick={addQuestion}>
                <Plus size={14} /> Adicionar Pergunta de Mapeamento
              </button>
            </div>
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<ShieldCheck size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Avaliação Crítica da Qualidade Metodológica (Critical Appraisal)"
            etiquetaItem={getFieldItemTag('critical_appraisal', 12, false)}
            essencial={false}
            secao="MÉTODOS / AVALIAÇÃO CRÍTICA"
            ajuda={getFieldGuideline('critical_appraisal', 'Caso realizada avaliação formal de risco de viés, descreva o instrumento utilizado ou justifique sua dispensa.')}
            assistencia={
              <AIAssistButton
                fieldId="critical_appraisal"
                fieldLabel="Avaliação Crítica e Risco de Viés"
                currentValue={manuscript.critical_appraisal}
                fieldGuidelines={getFieldGuideline('critical_appraisal', 'Em revisões de escopo, a avaliação de risco de viés é opcional. Descreva o instrumento ou justifique a dispensa metodológica formal.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('critical_appraisal')}
                onApply={(text) => updateManuscriptField('critical_appraisal', text)}
              />
            }
            guia={montarGuia('critical_appraisal', 'appraisal')}
          >
            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder={`Ex: Em conformidade com ${currentProtocolDef.name}, a avaliação formal de risco de viés não foi realizada por se tratar de um mapeamento abrangente da extensão das evidências.`}
              value={manuscript.critical_appraisal}
              onChange={(e) => updateManuscriptField('critical_appraisal', e.target.value)}
            />
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<Layers size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Métodos de Síntese e Mapeamento de Evidências (Synthesis of Results)"
            etiquetaItem={getFieldItemTag('synthesis_methods', 13)}
            secao="MÉTODOS / SÍNTESE"
            ajuda={getFieldGuideline('synthesis_methods', 'Descreva como os dados serão estruturados (tabelas descritivas, gráficos de tendências temporais, mapas territoriais ou matrizes de lacunas de evidência).')}
            assistencia={
              <AIAssistButton
                fieldId="synthesis_methods"
                fieldLabel="Métodos de Síntese e Mapeamento"
                currentValue={manuscript.synthesis_methods}
                fieldGuidelines={getFieldGuideline('synthesis_methods', 'Descreva os métodos de agrupamento temático, mapas de evidências tabulares, gráficos de tendências e matriz de identificação de lacunas.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('synthesis_methods')}
                onApply={(text) => updateManuscriptField('synthesis_methods', text)}
              />
            }
            guia={montarGuia('synthesis_methods', 'synthesis')}
          >
            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: Os resultados serão apresentados em formato de mapa de evidências narrativo e tabular, acompanhado de diagramas de distribuição temporal e territorial por arranjo produtivo..."
              value={manuscript.synthesis_methods}
              onChange={(e) => updateManuscriptField('synthesis_methods', e.target.value)}
            />
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<ShieldCheck size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Financiamento & Declaração de Conflitos de Interesse (Funding)"
            etiquetaItem={getFieldItemTag('funding', 17)}
            secao="FINANCIAMENTO"
            ajuda={getFieldGuideline('funding', 'Declare as fontes de financiamento ou bolsas e confirme a inexistência de conflitos de interesse.')}
            assistencia={
              <AIAssistButton
                fieldId="funding"
                fieldLabel="Financiamento e Declaração de Conflitos"
                currentValue={manuscript.funding}
                fieldGuidelines={getFieldGuideline('funding', 'Declare as agências de fomento, bolsas (CAPES, CNPq, FAPESP) e confirme a inexistência de conflitos de interesse.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('funding')}
                onApply={(text) => updateManuscriptField('funding', text)}
              />
            }
            guia={montarGuia('funding', 'funding')}
          >
            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: Este trabalho foi realizado com apoio da Coordenação de Aperfeiçoamento de Pessoal de Nível Superior - Brasil (CAPES) - Código de Financiamento 001. Os autores declaram não haver conflitos de interesse."
              value={manuscript.funding}
              onChange={(e) => updateManuscriptField('funding', e.target.value)}
            />
          </CampoDoProtocolo>

        </Tabs.Content>

      {/* ── ABA 5: SÍNTESE DOS ACHADOS & DISCUSSÃO (A POSTERIORI) ─────────── */}
      <Tabs.Content value="synthesis_discussion" className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-posteriori-banner">
            <span className="phase-badge a-posteriori">Fase A Posteriori — Pós-Extração / Síntese dos Resultados</span>
            <p>
              Esta seção <strong>deve ser redigida após a execução da coleta, triagem e extração</strong> dos dados dos estudos incluídos, com base nas evidências empíricas reais consolidadas.
            </p>
          </div>

          {/* Painel de Evidências Reais & Rastreabilidade */}
          <Card surface="secundaria" className="evidence-traceability-card">
            <div className="traceability-header">
              <div className="traceability-title">
                <BarChart3 size={18} className="icon-accent" />
                <strong>Rastreabilidade de Evidências do Estudo</strong>
              </div>
              {extractionSummary && extractionSummary.total_extracted > 0 && (
                <button
                  type="button"
                  className="btn-toggle-matrix"
                  onClick={() => setShowEvidenceMatrix(!showEvidenceMatrix)}
                >
                  {showEvidenceMatrix ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  {showEvidenceMatrix ? 'Ocultar Matriz de Respostas' : 'Ver Matriz de Respostas Extraídas'}
                </button>
              )}
            </div>

            <div className="traceability-stats-grid">
              <div className="trace-stat-item">
                <span className="trace-stat-label">Total Triados (Triagem 1)</span>
                <span className="trace-stat-val">{extractionSummary?.total_screened ?? 0}</span>
              </div>
              <div className="trace-stat-item highlight-inc">
                <span className="trace-stat-label">Estudos Incluídos</span>
                <span className="trace-stat-val">{extractionSummary?.total_included ?? 0}</span>
              </div>
              <div className="trace-stat-item highlight-ext">
                <span className="trace-stat-label">Com Extração Realizada</span>
                <span className="trace-stat-val">
                  {extractionSummary?.total_extracted ?? 0}
                  <span className="trace-stat-sub">
                    {' '}({extractionSummary?.extraction_progress_percent ?? 0}%)
                  </span>
                </span>
              </div>
              <div className="trace-stat-item">
                <span className="trace-stat-label">Pendentes de Avaliação</span>
                <span className="trace-stat-val">{extractionSummary?.total_pending ?? 0}</span>
              </div>
            </div>

            {/* Alerta Metodológico caso não haja extrações */}
            {(!extractionSummary || extractionSummary.total_extracted === 0) ? (
              <div className="methodological-flow-alert animate-fade-in">
                <AlertTriangle size={20} className="alert-icon" />
                <div className="flow-alert-body">
                  <strong>Aviso Metodológico de Fluxo:</strong>
                  <p>
                    Você ainda não possui estudos com dados extraídos cadastrados na etapa de Extração (Triagem 2). Redigir a Síntese dos Achados, Limitações e Conclusões antes de extrair os dados reais dos estudos pode gerar conclusões prematuras que precisarão ser reescritas.
                  </p>
                  <div className="flow-alert-actions">
                    <button
                      type="button"
                      className="btn-flow-nav"
                      onClick={() => navigate(`/projects/${id}/harvest`)}
                    >
                      <Database size={13} /> Ir para Coleta
                    </button>
                    <button
                      type="button"
                      className="btn-flow-nav"
                      onClick={() => navigate(`/projects/${id}/screening`)}
                    >
                      <CheckSquare size={13} /> Ir para Triagem
                    </button>
                    <button
                      type="button"
                      className="btn-flow-nav primary"
                      onClick={() => navigate(`/projects/${id}/extraction`)}
                    >
                      <FileText size={13} /> Ir para Extração dos Incluídos <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="methodological-flow-success animate-fade-in">
                <CheckCircle2 size={20} className="success-icon" />
                <div className="flow-success-body">
                  <strong>Evidências Extraídas Disponíveis:</strong>
                  <p>
                    {extractionSummary.total_extracted} estudos possuem respostas extraídas consolidadas para subsidiar a redação dos achados empíricos.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-compile-evidence"
                  onClick={handleCompileEvidenceIntoEditor}
                  title="Insere o compilado estruturado das respostas extraídas de todos os artigos no editor de síntese"
                >
                  <Sparkles size={14} /> Compilar Evidências no Editor
                </button>
              </div>
            )}

            {/* Matriz sanfonada de evidências */}
            {showEvidenceMatrix && extractionSummary && extractionSummary.questions_matrix?.length > 0 && (
              <div className="evidence-matrix-drawer animate-fade-in">
                <h4>Respostas Extraídas por Variável / Pergunta:</h4>
                <div className="matrix-questions-list">
                  {extractionSummary.questions_matrix.map((qm, qIdx) => (
                    <div key={qm.question_id} className="matrix-question-item">
                      <div className="matrix-q-header">
                        <strong>Q{qIdx + 1}: {qm.question_text}</strong>
                        <span className="badge-answered">{qm.total_answered} respostas</span>
                      </div>
                      <div className="matrix-answers-sublist">
                        {qm.answers.length === 0 ? (
                          <p className="no-answers-note">Nenhuma resposta cadastrada para este item.</p>
                        ) : (
                          qm.answers.map((ans) => (
                            <div key={ans.paper_id} className="matrix-answer-row">
                              <div className="ans-paper-meta">
                                <span className="ans-paper-title">{ans.paper_title}</span>
                                <span className="ans-paper-year">({ans.authors || 's/a'}, {ans.year || 's/d'})</span>
                              </div>
                              <p className="ans-text">"{ans.answer}"</p>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
          <CampoDoProtocolo
            icone={<Bookmark size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Síntese Geral das Evidências (Summary of Evidence)"
            etiquetaItem={getFieldItemTag('summary_evidence', 14)}
            secao="DISCUSSÃO / RESULTADOS"
            ajuda={getFieldGuideline(
              'summary_evidence',
              'Resuma os principais conceitos identificados, os temas dominantes e a relevância prática dos achados para formuladores de políticas públicas e pesquisadores.'
            )}
            assistencia={
              <AIAssistButton
                fieldId="summary_evidence"
                fieldLabel="Síntese Geral das Evidências"
                currentValue={manuscript.summary_evidence}
                fieldGuidelines={getFieldGuideline('summary_evidence', 'Resuma os principais conceitos, tendências territoriais e relevância prática dos achados para políticas públicas e pesquisadores.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('summary_evidence')}
                onApply={(text) => updateManuscriptField('summary_evidence', text)}
              />
            }
            guia={montarGuia('summary_evidence', 'summaryEvidence')}
          >
            <textarea
              rows={5}
              className="protocol-textarea"
              placeholder="Ex: A presente revisão de escopo identificou um crescimento expressivo na produção acadêmica sobre governança em arranjos produtivos..."
              value={manuscript.summary_evidence}
              onChange={(e) => updateManuscriptField('summary_evidence', e.target.value)}
            />
          </CampoDoProtocolo>

                    <CampoDoProtocolo
            icone={<AlertTriangle size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Limitações da Revisão (Limitations)"
            etiquetaItem={getFieldItemTag('limitations', 15)}
            secao="DISCUSSÃO / LIMITAÇÕES"
            ajuda={getFieldGuideline('limitations', 'Aponte as limitações inerentes ao processo da revisão (ex: restrições de idioma, bases indexadas, ausência de busca manual de literatura cinzenta não publicada).')}
            assistencia={
              <AIAssistButton
                fieldId="limitations"
                fieldLabel="Limitações da Revisão"
                currentValue={manuscript.limitations}
                fieldGuidelines={getFieldGuideline('limitations', 'Aponte as limitações inerentes ao processo da revisão (filtros linguísticos, bases consultadas, relatórios institucionais não capturados).')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('limitations')}
                onApply={(text) => updateManuscriptField('limitations', text)}
              />
            }
            guia={montarGuia('limitations', 'limitations')}
          >
            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: Como limitação deste estudo, destaca-se a inclusão restrita a artigos publicados em português, inglês e espanhol, além da potencial não captura de relatórios técnicos governamentais não indexados."
              value={manuscript.limitations}
              onChange={(e) => updateManuscriptField('limitations', e.target.value)}
            />
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<CheckCircle2 size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Conclusões e Lacunas de Conhecimento (Conclusions)"
            etiquetaItem={getFieldItemTag('conclusions', 16)}
            secao="CONCLUSÕES"
            ajuda={getFieldGuideline('conclusions', 'Forneça interpretação geral dos resultados, aponte lacunas científicas evidentes e sugira direções concretas para estudos e políticas públicas futuras.')}
            assistencia={
              <AIAssistButton
                fieldId="conclusions"
                fieldLabel="Conclusões e Lacunas de Conhecimento"
                currentValue={manuscript.conclusions}
                fieldGuidelines={getFieldGuideline('conclusions', 'Forneça interpretação geral dos resultados, aponte lacunas científicas evidentes e sugira direções concretas para estudos e políticas públicas futuras.')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('conclusions')}
                onApply={(text) => updateManuscriptField('conclusions', text)}
              />
            }
            guia={montarGuia('conclusions', 'conclusions')}
          >
            <textarea
              rows={5}
              className="protocol-textarea"
              placeholder="Ex: Conclui-se que, embora haja vasta produção acadêmica sobre desenvolvimento territorial, verifica-se escassez de estudos com avaliação de impacto socioeconômico de longo prazo..."
              value={manuscript.conclusions}
              onChange={(e) => updateManuscriptField('conclusions', e.target.value)}
            />
          </CampoDoProtocolo>

        </Tabs.Content>

      {/* ── ABA 6: RESUMO ESTRUTURADO FINAL (A POSTERIORI) ───────────────── */}
      <Tabs.Content value="final_summary" className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-posteriori-banner">
            <span className="phase-badge a-posteriori">Fase A Posteriori — Resumo Executivo Definitivo</span>
            <p>
              O Resumo Estruturado Final deve ser fechado <strong>após a conclusão de todo o trabalho</strong>, sintetizando os quantitativos exatos do funil PRISMA, as evidências descobertas e a conclusão central da pesquisa.
            </p>
          </div>
                    <CampoDoProtocolo
            icone={<FileText size={20} className="icon-accent" aria-hidden="true" />}
            titulo="Resumo Estruturado do Artigo / Protocolo (Structured Summary)"
            etiquetaItem={getFieldItemTag('structured_summary', 2)}
            secao="RESUMO"
            ajuda={getFieldGuideline('structured_summary', 'Estruture o resumo com os tópicos recomendados (Contexto, Objetivos, Elegibilidade, Fontes, Métodos de Charting, Resultados e Conclusões).')}
            assistencia={
              <AIAssistButton
                fieldId="structured_summary"
                fieldLabel="Resumo Estruturado da Revisão"
                currentValue={manuscript.structured_summary}
                fieldGuidelines="Estruture o resumo com os tópicos recomendados: Contexto, Objetivos, Elegibilidade, Fontes, Métodos de Charting, Resultados e Conclusões nas Ciências Sociais Aplicadas e Desenvolvimento Regional."
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('structured_summary')}
                onApply={(text) => updateManuscriptField('structured_summary', text)}
              />
            }
            guia={montarGuia('structured_summary', 'summary')}
          >
            <textarea
              rows={9}
              className="protocol-textarea"
              placeholder="Digite ou cole aqui o resumo estruturado do seu artigo / protocolo..."
              value={manuscript.structured_summary}
              onChange={(e) => updateManuscriptField('structured_summary', e.target.value)}
            />
          </CampoDoProtocolo>


                    <CampoDoProtocolo
            icone={<Edit3 size={20} className="icon-accent" aria-hidden="true" />}
            titulo={`Título Oficial da Revisão (${currentProtocolDef.shortLabel})`}
            etiquetaItem={getFieldItemTag('manuscript_title', 1)}
            secao="TÍTULO"
            ajuda={getFieldGuideline('manuscript_title', 'Identifique claramente o trabalho e reflita os elementos centrais de elegibilidade (População/Atores, Conceito Central e Contexto Territorial).')}
            assistencia={
              <AIAssistButton
                fieldId="manuscript_title"
                fieldLabel="Título Oficial da Revisão"
                currentValue={manuscript.manuscript_title}
                fieldGuidelines={getFieldGuideline('manuscript_title', 'Identifique claramente o trabalho e reflita os elementos centrais de elegibilidade (População/Atores, Conceito Central e Contexto Territorial no Desenvolvimento Regional).')}
                projectTitle={activeProject?.title}
                methodology={activeProject?.methodology}
                projectContext={getFullProtocolContext('manuscript_title')}
                onApply={(text) => updateManuscriptField('manuscript_title', text)}
              />
            }
            guia={montarGuia('manuscript_title', 'title')}
          >
            <input
              type="text"
              className="protocol-input-large"
              placeholder="Ex: Governança Territorial e Arranjos Produtivos Locais no Desenvolvimento Regional do Semiárido: Uma Revisão de Escopo"
              value={manuscript.manuscript_title}
              onChange={(e) => updateManuscriptField('manuscript_title', e.target.value)}
            />
          </CampoDoProtocolo>

        </Tabs.Content>

      {/* ── ABA 7: AUDITORIA E CHECKLIST DO PROTOCOLO ATIVO ───────────────── */}
      <Tabs.Content value="checklist" className="tab-pane animate-fade-in">
          <Card surface="secundaria" className="protocol-card scr-checklist-card">
            <div className="card-section-title">
              <CheckSquare size={20} className="icon-accent" />
              <h2>{currentProtocolDef.checklistTitle}</h2>
            </div>
            <p className="section-help">
              {currentProtocolDef.description} Referência: <em>{currentProtocolDef.reference}</em>. Utilize esta matriz para auditar e verificar o cumprimento de cada item metodológico no seu artigo.
            </p>

            {/* Grupo 1: Itens do Protocolo A Priori */}
            <div className="checklist-phase-group">
              <div className="checklist-group-header">
                <span className="group-tag a-priori">1. Itens do Protocolo de Pesquisa (A Priori)</span>
                <span className="group-count">
                  {aPrioriChecklistItems.filter((chk) => checkedScRItems[chk.id]).length} / {aPrioriChecklistItems.length} atendidos
                </span>
              </div>
              <div className="scr-items-grid">
                {aPrioriChecklistItems.map((chk) => {
                  const isChecked = checkedScRItems[chk.id] || false
                  return (
                    <label
                      key={chk.id}
                      className={`scr-checklist-row ${isChecked ? 'checked' : ''} ${chk.essential ? 'essential' : 'optional'}`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleScRItem(chk.id)}
                      />
                      <div className="scr-item-info">
                        <div className="scr-item-header">
                          <span className="scr-item-num">Item {chk.id}</span>
                          <span className="scr-item-section">{chk.section}</span>
                          <strong className="scr-item-title">{chk.item}</strong>
                          <span className={`scr-item-badge ${chk.essential ? 'ess' : 'opt'}`}>
                            {chk.essential ? 'Essencial' : 'Opcional'}
                          </span>
                        </div>
                        <span className="scr-item-desc">{chk.desc}</span>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>

            {/* Grupo 2: Itens do Manuscrito Final A Posteriori */}
            {aPosterioriChecklistItems.length > 0 && (
              <div className="checklist-phase-group" style={{ marginTop: 'var(--space-6)' }}>
                <div className="checklist-group-header">
                  <span className="group-tag a-posteriori">2. Itens do Manuscrito Final Pós-Extração (A Posteriori)</span>
                  <span className="group-count">
                    {aPosterioriChecklistItems.filter((chk) => checkedScRItems[chk.id]).length} / {aPosterioriChecklistItems.length} atendidos
                  </span>
                </div>
                <div className="scr-items-grid">
                  {aPosterioriChecklistItems.map((chk) => {
                    const isChecked = checkedScRItems[chk.id] || false
                    return (
                      <label
                        key={chk.id}
                        className={`scr-checklist-row ${isChecked ? 'checked' : ''} ${chk.essential ? 'essential' : 'optional'}`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleScRItem(chk.id)}
                        />
                        <div className="scr-item-info">
                          <div className="scr-item-header">
                            <span className="scr-item-num">Item {chk.id}</span>
                            <span className="scr-item-section">{chk.section}</span>
                            <strong className="scr-item-title">{chk.item}</strong>
                            <span className={`scr-item-badge ${chk.essential ? 'ess' : 'opt'}`}>
                              {chk.essential ? 'Essencial' : 'Opcional'}
                            </span>
                          </div>
                          <span className="scr-item-desc">{chk.desc}</span>
                        </div>
                      </label>
                    )
                  })}
                </div>
              </div>
            )}
          </Card>
        </Tabs.Content>
      </Tabs.Root>
      )}

      {/* Proposta de protocolo por assistência */}
      <Dialog
        open={isAiModalOpen}
        onOpenChange={(aberto) => {
          // Fechar a janela no meio da elaboração é um pedido de parar: manter
          // a requisição viva deixaria a proposta chegar para uma tela que
          // ninguém está mais olhando.
          if (!aberto && aiLoading) {
            handleCancelSuggestion()
            return
          }
          setIsAiModalOpen(aberto)
        }}
      >
        <DialogContent variant="window" size="md" aria-describedby={undefined}>
          <DialogTitlebar>
            Proposta de Protocolo Gerada por Assistência ({activeProject?.methodology})
          </DialogTitlebar>
          <DialogBody>
              {aiLoading ? (
                <div className="ai-suggestion-loading">
                  <LoadingState label="Elaborando proposta de PICO/PCC, descritores em pares e critérios em Ciências Sociais Aplicadas…" />
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={handleCancelSuggestion}
                    title="Interromper a elaboração da proposta"
                  >
                    <StopCircle size={15} /> Parar Elaboração
                  </button>
                </div>
              ) : aiSuggestions ? (
                <div className="ai-suggestions-preview">
                  <div className="form-group">
                    <label>Objetivo Proposto:</label>
                    <p className="ai-preview-text">{aiSuggestions.objective}</p>
                  </div>

                  <div className="form-group">
                    <label>População / Atores Sociais:</label>
                    <p className="ai-preview-text">{aiSuggestions.pico_population}</p>
                  </div>

                  <div className="form-group">
                    <label>Descritores em Pares (Português):</label>
                    <div className="ai-chips">
                      {aiSuggestions.descriptors_pt?.map((d, i) => (
                        <span key={i} className="ai-chip">
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Descritores em Pares (Inglês):</label>
                    <div className="ai-chips">
                      {aiSuggestions.descriptors_en?.map((d, i) => (
                        <span key={i} className="ai-chip">
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>

                  <DialogFooter>
                    <Button variant="secondary" size="md" onClick={() => setIsAiModalOpen(false)}>
                      Cancelar
                    </Button>
                    <Button
                      variant="primary"
                      size="md"
                      onClick={handleApplyAISuggestions}
                      leftIcon={<Sparkles size={14} />}
                    >
                      Aplicar Proposta ao Protocolo
                    </Button>
                  </DialogFooter>
                </div>
              ) : null}
          </DialogBody>
        </DialogContent>
      </Dialog>

      {/* Modal de Conflito de Concorrência (Doc 43 §43.12.2, Fase 3) */}
      <Dialog open={showConflictModal} onOpenChange={setShowConflictModal}>
        <DialogContent variant="window" size="md" aria-describedby={undefined}>
          <DialogTitlebar>
            Conflito de Concorrência Detectado
          </DialogTitlebar>
          <DialogBody>
            <div className="protocol-conflict-modal-body">
              <div className="conflict-notice-box">
                <AlertTriangle size={24} className="text-warning" />
                <div>
                  <strong>Alterações concorrentes encontradas</strong>
                  <p>
                    Outro pesquisador salvou uma nova versão deste protocolo no servidor enquanto você o editava.
                    Escolha como deseja proceder para evitar perda de dados da equipe:
                  </p>
                </div>
              </div>

              <div className="conflict-options-list">
                <div className="conflict-option-card">
                  <h4>Opção 1: Recarregar dados do servidor (Recomendado)</h4>
                  <p>Descarta o rascunho local e carrega a versão mais recente gravada pelo colega.</p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      if (id) loadProtocolAndProject(id)
                      setShowConflictModal(false)
                    }}
                    leftIcon={<RotateCcw size={14} />}
                  >
                    Recarregar Versão do Servidor
                  </Button>
                </div>

                <div className="conflict-option-card danger">
                  <h4>Opção 2: Sobrescrever versão do servidor</h4>
                  <p>Força o salvamento do seu rascunho atual, sobrepondo o estado do servidor.</p>
                  <Button
                    variant="destructive"
                    size="sm"
                    loading={saving}
                    onClick={() => handleSave(true)}
                    leftIcon={<Save size={14} />}
                  >
                    Sobrescrever Versão Atual
                  </Button>
                </div>
              </div>
            </div>
          </DialogBody>
        </DialogContent>
      </Dialog>

      {/* Diálogo de Versionamento, Congelamento e Emendas (Doc 45 §12) */}
      <ProtocolVersionDialog
        projectId={id || ''}
        open={isVersionDialogOpen}
        onOpenChange={setIsVersionDialogOpen}
        apoio={{
          montarGuia,
          ajuda: getFieldGuideline,
          contexto: getFullProtocolContext,
          projeto: { titulo: activeProject?.title, metodologia: activeProject?.methodology },
        }}
        currentVersion={currentVersion}
        protocolStatus={protocolStatus}
        onVersionChanged={() => {
          if (id) loadProtocolAndProject(id)
        }}
      />
    </div>
  )
}
