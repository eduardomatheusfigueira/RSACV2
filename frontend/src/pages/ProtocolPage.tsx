/**
 * RSAC V2 — Protocol Page & Complete Manuscript Drafting Studio (PRISMA-ScR & PRISMA 2020)
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

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  BookOpen,
  Layers,
  Search,
  Filter,
  HelpCircle,
  Sparkles,
  Save,
  Plus,
  Trash2,
  ArrowLeft,
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
  ArrowRight,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { PROTOCOL_CATALOG, PROTOCOL_OPTIONS } from '@/data/protocolCatalog'
import { AIAssistButton } from '@/components/common/AIAssistButton'
import type {
  Criterion,
  ExtractionQuestion,
  ProtocolSuggestions,
  Methodology,
  ExtractionSummaryResponse,
} from '@/types/api'
import './ProtocolPage.css'

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
    open_access_only: false,
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
  const [checkedScRItems, setCheckedScRItems] = useState<Record<number, boolean>>({})

  // Section Help Drawers/Popups Toggle State
  const [helpOpen, setHelpOpen] = useState<Record<string, boolean>>({})

  // AI Suggestion Modal
  const [isAiModalOpen, setIsAiModalOpen] = useState(false)
  const [aiSuggestions, setAiSuggestions] = useState<ProtocolSuggestions | null>(null)
  const [aiLoading, setAiLoading] = useState(false)

  // Language Tabs for Descriptors
  const [activeLangTab, setActiveLangTab] = useState<'pt' | 'en' | 'es'>('pt')

  const currentProtocolDef = PROTOCOL_CATALOG[activeProject?.methodology as Methodology] || PROTOCOL_CATALOG['PRISMA-ScR']

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

      // Carregar protocolo e resumo de extração em paralelo
      const [proto, extSummary] = await Promise.all([
        api.getProtocol(projectId),
        api.getExtractionSummary(projectId).catch(() => null),
      ])

      if (extSummary) {
        setExtractionSummary(extSummary)
      }

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
          open_access_only: proto.search_filters.open_access_only ?? false,
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

  const toggleScRItem = (itemId: number) => {
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

  // ── Salvar Protocolo & Seções do Manuscrito ────────────────────────

  const handleSave = async () => {
    if (!id) return
    try {
      setSaving(true)
      setErrorMessage('')

      const cleanDescriptors = {
        pt: descriptors.pt.map((d) => d.trim()).filter(Boolean),
        en: descriptors.en.map((d) => d.trim()).filter(Boolean),
        es: descriptors.es.map((d) => d.trim()).filter(Boolean),
      }

      const cleanCriteria = criteria
        .filter((c) => c.text.trim().length > 0)
        .map((c, idx) => ({ ...c, order: idx }))

      const cleanQuestions = questions
        .filter((q) => (q.text || (q as any).question || '').trim().length > 0)
        .map((q, idx) => ({ ...q, text: (q.text || (q as any).question || '').trim(), order: idx }))

      await api.updateProtocol(id, {
        objective,
        pico_framework: pico,
        search_descriptors: cleanDescriptors,
        search_filters: searchFilters,
        manuscript_sections: manuscript,
        criteria: cleanCriteria,
        extraction_questions: cleanQuestions,
      })

      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err: any) {
      console.error('Erro ao salvar protocolo:', err)
      setErrorMessage(err.message || 'Falha ao salvar o protocolo.')
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

  // ── Sugestão com IA ────────────────────────────────────────────────

  const handleSuggestWithAI = async () => {
    if (!activeProject) return
    try {
      setAiLoading(true)
      setIsAiModalOpen(true)
      setErrorMessage('')

      const suggestions = await api.suggestProtocol({
        title: manuscript.manuscript_title || activeProject.title,
        methodology: activeProject.methodology,
        description: activeProject.description || manuscript.rationale || objective,
      })

      setAiSuggestions(suggestions)
    } catch (err: any) {
      console.error('Erro ao sugerir protocolo via IA:', err)
      setErrorMessage(err.message || 'Falha na comunicação com o provedor de IA.')
      setIsAiModalOpen(false)
    } finally {
      setAiLoading(false)
    }
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

  const aPrioriChecklistItems = currentProtocolDef.checklistItems.filter(
    (item) => item.phase === 'a_priori' || !item.phase
  )
  const aPosterioriChecklistItems = currentProtocolDef.checklistItems.filter(
    (item) => item.phase === 'a_posteriori'
  )

  return (
    <div className="protocol-page animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <button className="btn-back" onClick={() => navigate('/projects')}>
            <ArrowLeft size={16} /> Voltar para Projetos
          </button>
          <h1 className="page-title">Estúdio de Redação do Protocolo & Artigo</h1>
          <div className="page-subtitle-with-select">
            <span>Projeto: <strong>{activeProject?.title}</strong></span>
            <span className="subtitle-divider">·</span>
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
              <span className="badge-methodology-header">
                {currentProtocolDef.badge}
              </span>
            </div>
          </div>
        </div>
        <div className="header-actions">
          {saveSuccess && (
            <span className="save-indicator success animate-fade-in">
              <CheckCircle2 size={16} /> Salvo com Sucesso!
            </span>
          )}
          {copiedNotification && (
            <span className="save-indicator success animate-fade-in">
              <CheckCircle2 size={16} /> Artigo Copiado (Markdown)!
            </span>
          )}
          <button
            type="button"
            className="btn-secondary"
            onClick={handleCopyFullManuscript}
            title="Copia todo o texto estruturado do artigo/protocolo em formato Markdown para colar no Word/Docs"
          >
            <Copy size={16} className="icon-accent" />
            Copiar Manuscrito
          </button>
          {aiEnabled && (
            <button
              type="button"
              className="btn-secondary"
              onClick={handleSuggestWithAI}
              disabled={saving}
              title="Gera proposta com IA"
            >
              <Sparkles size={16} className="icon-accent" />
              Sugerir com IA
            </button>
          )}
          <button className="btn-primary" onClick={handleSave} disabled={saving}>
            <Save size={18} />
            {saving ? 'Salvando...' : 'Salvar Tudo'}
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="protocol-error-banner animate-fade-in">
          <AlertTriangle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Studio Navigation Tabs with Clear Temporal Phase Grouping */}
      <div className="studio-tabs-container">
        <div className="studio-tabs-bar-grouped">
          {/* GRUPO A PRIORI: PROTOCOLO DE PESQUISA */}
          <div className="tabs-group a-priori-group">
            <div className="tabs-group-header">
              <span className="group-tag a-priori">Fase A Priori (Protocolo / Planejamento)</span>
            </div>
            <div className="tabs-group-buttons">
              <button
                type="button"
                className={`studio-tab ${activeStudioTab === 'ident_intro' ? 'active' : ''}`}
                onClick={() => setActiveStudioTab('ident_intro')}
                title="1. Identificação, Registro & Justificativa (Itens 1, 5, 3)"
              >
                <Edit3 size={13} className="tab-icon" />
                <span className="tab-label">1. Identificação & Justificativa</span>
                <span className="tab-pill">1, 5, 3</span>
              </button>
              <button
                type="button"
                className={`studio-tab ${activeStudioTab === 'objectives' ? 'active' : ''}`}
                onClick={() => setActiveStudioTab('objectives')}
                title={`2. Questão & Objetivos (${frameworkType}) (Item 4)`}
              >
                <BookOpen size={13} className="tab-icon" />
                <span className="tab-label">2. Questão & Objetivos ({frameworkType})</span>
                <span className="tab-pill">4</span>
              </button>
              <button
                type="button"
                className={`studio-tab ${activeStudioTab === 'search_eligibility' ? 'active' : ''}`}
                onClick={() => setActiveStudioTab('search_eligibility')}
                title="3. Fontes, Descritores & Elegibilidade (Itens 6, 7, 8)"
              >
                <Search size={13} className="tab-icon" />
                <span className="tab-label">3. Fontes & Elegibilidade</span>
                <span className="tab-pill">6-8</span>
              </button>
              <button
                type="button"
                className={`studio-tab ${activeStudioTab === 'methods_extraction' ? 'active' : ''}`}
                onClick={() => setActiveStudioTab('methods_extraction')}
                title="4. Seleção, Data Charting & Métodos de Síntese (Itens 9-13, 17)"
              >
                <Filter size={13} className="tab-icon" />
                <span className="tab-label">4. Métodos & Extração</span>
                <span className="tab-pill">9-13, 17</span>
              </button>
            </div>
          </div>

          {/* GRUPO A POSTERIORI: SÍNTESE & REDAÇÃO FINAL */}
          <div className="tabs-group a-posteriori-group">
            <div className="tabs-group-header">
              <span className="group-tag a-posteriori">Fase A Posteriori (Pós-Extração / Síntese)</span>
            </div>
            <div className="tabs-group-buttons">
              <button
                type="button"
                className={`studio-tab ${activeStudioTab === 'synthesis_discussion' ? 'active' : ''}`}
                onClick={() => setActiveStudioTab('synthesis_discussion')}
                title="5. Síntese dos Achados, Limitações & Conclusões (Itens 14-16)"
              >
                <Bookmark size={13} className="tab-icon" />
                <span className="tab-label">5. Síntese dos Achados & Discussão</span>
                <span className="tab-pill">14-16</span>
              </button>
              <button
                type="button"
                className={`studio-tab ${activeStudioTab === 'final_summary' ? 'active' : ''}`}
                onClick={() => setActiveStudioTab('final_summary')}
                title="6. Resumo Estruturado Final do Artigo Concluído (Item 2)"
              >
                <FileText size={13} className="tab-icon" />
                <span className="tab-label">6. Resumo Estruturado Final</span>
                <span className="tab-pill">2</span>
              </button>
              <button
                type="button"
                className={`studio-tab checklist-tab ${activeStudioTab === 'checklist' ? 'active' : ''}`}
                onClick={() => setActiveStudioTab('checklist')}
                title={`Auditoria de Conformidade ${currentProtocolDef.shortLabel}`}
              >
                <CheckSquare size={13} className="tab-icon" />
                <span className="tab-label">Auditoria {currentProtocolDef.shortLabel}</span>
                <span className="tab-pill-count">{currentProtocolDef.checklistItems.length}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── ABA 1: IDENTIFICAÇÃO & JUSTIFICATIVA (A PRIORI) ──────────────── */}
      {activeStudioTab === 'ident_intro' && (
        <div className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-priori-banner">
            <span className="phase-badge a-priori">Fase A Priori — Planejamento do Estudo</span>
            <p>
              Defina o título preliminar do protocolo, registre seu planejamento e estabeleça a justificativa teórica <strong>antes</strong> de iniciar a busca nas bases de dados.
            </p>
          </div>
          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 1 — Essencial</span>
              <span className="item-section-tag">TÍTULO</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <Edit3 size={20} className="icon-accent" />
                <h2>Título Oficial da Revisão de Escopo (Scoping Review)</h2>
              </div>
              <div className="card-header-actions">
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
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.title ? 'active' : ''}`}
                  onClick={() => toggleHelp('title')}
                  title="Ver guia de elaboração do título"
                >
                  <HelpCircle size={16} />
                  <span>Guia do Título (?)</span>
                </button>
              </div>
            </div>
            <p className="section-help">
              Conforme PRISMA-ScR Item 1: Identifique claramente o trabalho como uma <strong>Scoping Review</strong> e reflita os elementos centrais de elegibilidade (População/Atores, Conceito Central e Contexto Territorial).
            </p>

            {helpOpen.title && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura Recomendada para o Título (PRISMA-ScR Item 1)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Políticas Públicas de [Instrumento / Política] e [Conceito Central] no [Contexto Regional / Território] para [Atores Sociais / Setor Produtivo]: Uma Revisão de Escopo`
                      if (manuscript.manuscript_title && !window.confirm('Substituir título atual pelo modelo?')) return
                      updateManuscriptField('manuscript_title', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Identificação do Método</span>
                    <p>O subtítulo DEVE conter explicitamente "Uma Revisão de Escopo" ou "Scoping Review".</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Elementos PCC</span>
                    <p>Mencione o Conceito Central (ex: Arranjos Produtivos Locais), o Contexto Territorial e os Atores Sociais.</p>
                  </div>
                </div>
              </div>
            )}

            <input
              type="text"
              className="protocol-input-large"
              placeholder="Ex: Governança Territorial e Arranjos Produtivos Locais no Desenvolvimento Regional do Semiárido: Uma Revisão de Escopo"
              value={manuscript.manuscript_title}
              onChange={(e) => updateManuscriptField('manuscript_title', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 5 — Essencial</span>
              <span className="item-section-tag">MÉTODOS / REGISTRO</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <ShieldCheck size={20} className="icon-accent" />
                <h2>Registro do Protocolo a Priori (Protocol & Registration)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="protocol_registration"
                  fieldLabel="Registro do Protocolo (OSF / Repositório)"
                  currentValue={manuscript.protocol_registration}
                  fieldGuidelines="Conforme PRISMA-ScR Item 5: Informe a plataforma de registro público (ex: OSF, Figshare, Zenodo), DOI permanente e data de depósito a priori."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('protocol_registration')}
                  onApply={(text) => updateManuscriptField('protocol_registration', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.registration ? 'active' : ''}`}
                  onClick={() => toggleHelp('registration')}
                  title="Ver guia de registro do protocolo"
                >
                  <HelpCircle size={16} />
                  <span>Guia de Registro (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 5: Informe a plataforma de registro público (ex: Open Science Framework - OSF, Figshare, Zenodo), identificador/DOI e data de submissão do protocolo.
            </p>

            {helpOpen.registration && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura de Registro do Protocolo (PRISMA-ScR Item 5)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `O protocolo desta scoping review foi desenvolvido a priori em conformidade com as diretrizes PRISMA-P e PRISMA-ScR, registrado na plataforma Open Science Framework (OSF) sob o DOI: https://doi.org/10.17605/OSF.IO/XXXXX em DD/MM/AAAA.`
                      if (manuscript.protocol_registration && !window.confirm('Substituir dados de registro pelo modelo?')) return
                      updateManuscriptField('protocol_registration', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Modelo no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Plataforma Pública</span>
                    <p>OSF (Open Science Framework), Figshare, Zenodo ou periódicos de protocolo acadêmico.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. DOI / URL Permanente</span>
                    <p>Link direto e identificador persistente para verificação e transparência científica.</p>
                  </div>
                </div>
              </div>
            )}

            <input
              type="text"
              className="protocol-input-large"
              placeholder="Ex: Registrado no Open Science Framework (OSF) sob o identificador https://doi.org/10.17605/OSF.IO/XXXXX em 15/08/2026."
              value={manuscript.protocol_registration}
              onChange={(e) => updateManuscriptField('protocol_registration', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 3 — Essencial</span>
              <span className="item-section-tag">INTRODUÇÃO</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <BookOpen size={20} className="icon-accent" />
                <h2>Justificativa e Estado da Arte (Rationale)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="rationale"
                  fieldLabel="Justificativa e Racional da Revisão"
                  currentValue={manuscript.rationale}
                  fieldGuidelines="Conforme PRISMA-ScR Item 3: Descreva o contexto do conhecimento existente na área e fundamente por que o escopo necessita de uma Scoping Review em vez de uma revisão sistemática tradicional nas Ciências Sociais Aplicadas e Desenvolvimento Regional."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('rationale')}
                  onApply={(text) => updateManuscriptField('rationale', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.rationale ? 'active' : ''}`}
                  onClick={() => toggleHelp('rationale')}
                  title="Ver tópicos recomendados para a justificativa"
                >
                  <HelpCircle size={16} />
                  <span>Guia da Justificativa (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 3: Descreva o contexto do conhecimento existente na área e fundamente <strong>por que o escopo necessita de uma Scoping Review</strong> em vez de uma revisão sistemática tradicional com meta-análise.
            </p>

            {helpOpen.rationale && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura Recomendada para a Justificativa (PRISMA-ScR Item 3)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Contexto e Estado da Arte:
[Apresente o panorama atual da literatura em Ciências Sociais Aplicadas / Desenvolvimento Regional e as dinâmicas recentes]

Problema de Pesquisa e Lacuna Identificada:
[Explique qual desafio persiste nas políticas públicas ou na governança e quais aspectos ainda carecem de síntese estruturada]

Justificativa da Abordagem de Scoping Review:
[Fundamente por que uma Scoping Review é o método indicado face à heterogeneidade dos estudos territoriais e organizacionais]

Relevância e Contribuição Esperada:
[Destaque a relevância acadêmica, institucional e social dos achados para apoiar tomadas de decisão e planejamento regional]`

                      if (manuscript.rationale && !window.confirm('Substituir justificativa pelo modelo estruturado?')) return
                      updateManuscriptField('rationale', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Estado da Arte</span>
                    <p>Panorama do que já se conhece na literatura sobre o território ou setor produtivo.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Lacuna Crítica</span>
                    <p>Por que os estudos anteriores não responderam plenamente às demandas regionais.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Por que Scoping Review</span>
                    <p>Necessidade de mapear a amplitude conceitual e heterogeneidade empírica.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">4. Relevância Prática</span>
                    <p>Apoio à formulação de políticas públicas e governança territorial.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={7}
              className="protocol-textarea"
              placeholder="Descreva o contexto do desenvolvimento regional, a relevância socioeconômica e institucional, a heterogeneidade das experiências territoriais existentes e por que o mapeamento amplo de evidências é a abordagem mais apropriada..."
              value={manuscript.rationale}
              onChange={(e) => updateManuscriptField('rationale', e.target.value)}
            />
          </div>
        </div>
      )}

      {/* ── ABA 2: QUESTÃO & OBJETIVOS (A PRIORI) ───────────────────────── */}
      {activeStudioTab === 'objectives' && (
        <div className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-priori-banner">
            <span className="phase-badge a-priori">Fase A Priori — Planejamento do Estudo</span>
            <p>
              Estruture o objetivo geral e desmembre os conceitos orientadores no framework teórico ({frameworkType}) para guiar a busca sem ambiguidades.
            </p>
          </div>
          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 4 — Essencial</span>
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
                  PCC (PRISMA-ScR / Escopo)
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
                  ? 'Conforme PRISMA-ScR Item 4 e JBI: Estruture os objetivos centrais em População/Atores (P), Conceito Central (C) e Contexto Territorial (C).'
                  : 'Estruture os objetivos em População/Atores (P), Intervenção/Política (I), Comparador (C) e Desfecho (O).'}
              </p>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="objective"
                  fieldLabel="Objetivo Geral da Revisão"
                  currentValue={objective}
                  fieldGuidelines={`Conforme PRISMA-ScR Item 4: Formule o objetivo geral da scoping review delimitando a questão norteadora com base nos elementos ${frameworkType} em Ciências Sociais Aplicadas / Desenvolvimento Regional.`}
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
                    <strong>Formulação de Objetivos PCC (PRISMA-ScR Item 4)</strong>
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
          </div>
        </div>
      )}

      {/* ── ABA 3: FONTES & ELEGIBILIDADE (A PRIORI) ────────────────────── */}
      {activeStudioTab === 'search_eligibility' && (
        <div className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-priori-banner">
            <span className="phase-badge a-priori">Fase A Priori — Planejamento do Estudo</span>
            <p>
              Estabeleça os critérios de inclusão/exclusão e as strings de busca em pares ("termo_1" AND "termo_2") compatíveis com a BDTD (VuFind) antes da coleta.
            </p>
          </div>
          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 6 — Essencial</span>
              <span className="item-section-tag">MÉTODOS / ELEGIBILIDADE</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <Filter size={20} className="icon-accent" />
                <h2>Critérios de Elegibilidade (Eligibility Criteria)</h2>
              </div>
              <div className="card-header-actions">
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
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.criteria ? 'active' : ''}`}
                  onClick={() => toggleHelp('criteria')}
                  title="Ver guia de formulação dos critérios"
                >
                  <HelpCircle size={16} />
                  <span>Guia dos Critérios (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 6: Defina as regras de inclusão e exclusão com base na população/atores, conceitos avaliados, recortes territoriais, idiomas e períodos considerados.
            </p>

            {helpOpen.criteria && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Diretrizes de Critérios de Elegibilidade (PRISMA-ScR Item 6)</strong>
                  </div>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">Critérios de Inclusão (INC)</span>
                    <p>Estudos empíricos ou teóricos que analisem políticas públicas, arranjos produtivos ou governança regional no contexto delimitado.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">Critérios de Exclusão (EXC)</span>
                    <p>Artigos de opinião sem dados, resumos simples de anais, trabalhos fora do escopo geográfico/temático ou duplicados.</p>
                  </div>
                </div>
              </div>
            )}

            <div className="criteria-list">
              {criteria.map((crit, idx) => (
                <div key={idx} className="criterion-card">
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
                </div>
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
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 7 — Essencial</span>
              <span className="item-section-tag">MÉTODOS / FONTES</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <Search size={20} className="icon-accent" />
                <h2>Fontes de Informação & Período de Cobertura (Information Sources)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="info_sources"
                  fieldLabel="Fontes de Informação e Bases"
                  currentValue={manuscript.info_sources}
                  fieldGuidelines="Conforme PRISMA-ScR Item 7: Descreva todas as bases de dados bibliográficas (BDTD, SciELO, Scopus, OpenAlex), literatura cinzenta, recorte temporal e a data da busca mais recente."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('info_sources')}
                  onApply={(text) => updateManuscriptField('info_sources', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.sources ? 'active' : ''}`}
                  onClick={() => toggleHelp('sources')}
                  title="Ver guia de reporte das fontes de informação"
                >
                  <HelpCircle size={16} />
                  <span>Guia das Fontes (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 7: Liste todas as bases consultadas (BDTD, SciELO, Scopus, OpenAlex), literatura cinzenta, busca manual e a <strong>data exata da busca mais recente</strong>.
            </p>

            {helpOpen.sources && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura de Fontes de Informação (PRISMA-ScR Item 7)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Bases Bibliográficas Consultadas:
Foram realizadas buscas sistemáticas nas bases de dados BDTD (Teses e Dissertações), SciELO, Scopus e OpenAlex.

Período Cronológico de Cobertura:
Publicações compreendidas entre 2015 e agosto de 2026.

Literatura Cinzenta e Busca Manual:
Consulta ao repositório de teses da BDTD, relatórios técnicos institucionais e varredura das listas de referências dos estudos incluídos.

Data de Execução da Busca Mais Recente:
A estratégia de busca eletrônica definitiva foi executada em DD/MM/AAAA.`

                      if (manuscript.info_sources && !window.confirm('Substituir fontes pelo modelo estruturado?')) return
                      updateManuscriptField('info_sources', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Bases Eletrônicas</span>
                    <p>Nome de todas as bases pesquisadas (BDTD, SciELO, Scopus, OpenAlex, etc.).</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Período de Cobertura</span>
                    <p>Janela temporal de publicação dos trabalhos considerados.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Literatura Cinzenta</span>
                    <p>Teses, dissertações, relatórios técnicos governamentais ou de institutos de pesquisa.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">4. Data da Busca Mais Recente</span>
                    <p>Data exata da última rodada de busca para aferir a atualidade da revisão.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: Foram consultadas as bases bibliográficas BDTD (Teses e Dissertações), SciELO, Scopus e OpenAlex, cobrindo o período de 2015 a agosto de 2026. A busca eletrônica mais recente foi executada em 15/08/2026."
              value={manuscript.info_sources}
              onChange={(e) => updateManuscriptField('info_sources', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 8 — Essencial</span>
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
              Conforme PRISMA-ScR Item 8 e Diretrizes RSAC: Formulação em <strong>pares de termos com AND</strong> (máximo 2 termos por expressão e sugestão de ~5 pares por idioma), garantindo perfeita compatibilidade com o motor VuFind da BDTD.
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
          </div>
        </div>
      )}

      {/* ── ABA 4: MÉTODOS & EXTRAÇÃO (A PRIORI) ────────────────────────── */}
      {activeStudioTab === 'methods_extraction' && (
        <div className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-priori-banner">
            <span className="phase-badge a-priori">Fase A Priori — Planejamento do Estudo</span>
            <p>
              Planeje os procedimentos de triagem, o questionário com as variáveis que serão extraídas de cada estudo incluído e os métodos previstos de síntese.
            </p>
          </div>
          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 9 — Essencial</span>
              <span className="item-section-tag">MÉTODOS / TRIAGEM</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <Filter size={20} className="icon-accent" />
                <h2>Processo de Seleção de Estudos & Calibração (Selection Process)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="selection_process"
                  fieldLabel="Processo de Seleção de Estudos"
                  currentValue={manuscript.selection_process}
                  fieldGuidelines="Conforme PRISMA-ScR Item 9: Especifique os métodos de triagem em duas etapas (títulos/resumos e texto integral), duplo-cego independente, teste piloto prévio e resolução de conflitos."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('selection_process')}
                  onApply={(text) => updateManuscriptField('selection_process', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.selection ? 'active' : ''}`}
                  onClick={() => toggleHelp('selection')}
                  title="Ver guia do processo de seleção"
                >
                  <HelpCircle size={16} />
                  <span>Guia da Seleção (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 9: Descreva como foi realizada a triagem em duas etapas (1: Títulos e Resumos; 2: Texto Completo), o número de revisores independentes, exercícios prévios de calibração piloto e como foram resolvidas as divergências (consenso ou terceiro revisor).
            </p>

            {helpOpen.selection && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura do Processo de Seleção (PRISMA-ScR Item 9)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Etapas da Triagem:
A seleção dos estudos foi conduzida no software RSAC V2 em duas fases: (1) avaliação inicial de títulos e resumos para exclusão de estudos fora do escopo temático/territorial; e (2) análise integral dos artigos pré-selecionados.

Exercício Piloto de Calibração:
Antes do início da triagem definitiva, realizou-se um teste piloto com uma amostra de 50 artigos entre os revisores para calibração e refinamento dos critérios de inclusão e exclusão.

Revisores e Resolução de Divergências:
A seleção foi realizada de forma independente por dois pesquisadores. Discrepâncias na decisão foram resolvidas por consenso; havendo persistência, um terceiro revisor sênior foi acionado para decisão final.`

                      if (manuscript.selection_process && !window.confirm('Substituir seleção pelo modelo estruturado?')) return
                      updateManuscriptField('selection_process', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Triagem em Duas Fases</span>
                    <p>Fase 1 (Títulos/Resumos) e Fase 2 (Texto Completo).</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Teste Piloto</span>
                    <p>Amostra prévia de calibração entre os revisores.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Duplo-Cego / Independente</span>
                    <p>Número de pesquisadores e mecanismo de resolução de conflitos.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={5}
              className="protocol-textarea"
              placeholder="Ex: A triagem foi conduzida em duas etapas independentes através do sistema RSAC V2. Previamente, realizou-se exercício de calibração com amostra piloto de 50 artigos para alinhamento de critérios. Divergências na decisão foram resolvidas por consenso entre os revisores..."
              value={manuscript.selection_process}
              onChange={(e) => updateManuscriptField('selection_process', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 10 — Essencial</span>
              <span className="item-section-tag">MÉTODOS / EXTRAÇÃO</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <HelpCircle size={20} className="icon-accent" />
                <h2>Processo de Extração de Dados (Data Charting Process)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="data_charting_process"
                  fieldLabel="Processo de Extração de Dados"
                  currentValue={manuscript.data_charting_process}
                  fieldGuidelines="Conforme PRISMA-ScR Item 10: Descreva o formulário de extração de dados calibrado, o procedimento de extração em duplicata independente e a resolução de discordâncias."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('data_charting_process')}
                  onApply={(text) => updateManuscriptField('data_charting_process', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.charting ? 'active' : ''}`}
                  onClick={() => toggleHelp('charting')}
                  title="Ver guia do processo de extração"
                >
                  <HelpCircle size={16} />
                  <span>Guia do Charting (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 10: Descreva os procedimentos de preenchimento do formulário de mapeamento (*data charting form*), se foi calibrado previamente e como os dados foram checados e confirmados.
            </p>

            {helpOpen.charting && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura do Processo de Data Charting (PRISMA-ScR Item 10)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Formulário de Extração Padronizado:
A extração de dados foi realizada por meio de formulário padronizado no RSAC V2, pré-testado em 10 estudos pelos pesquisadores.

Procedimento de Preenchimento:
Dois revisores extraíram independentemente as informações metodológicas, atores envolvidos, instrumentos de política pública e resultados socioeconômicos observados.

Consolidação e Contato com Autores:
Os dados foram cruzados e eventuais omissões foram esclarecidas por contato direto com os autores correspondentes.`

                      if (manuscript.data_charting_process && !window.confirm('Substituir processo de charting pelo modelo?')) return
                      updateManuscriptField('data_charting_process', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Formulário Calibrado</span>
                    <p>Instrumento estruturado pré-testado para extração uniforme.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Extração em Duplicata</span>
                    <p>Conduzida de forma independente por pares de revisores.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: A extração de dados foi realizada por meio de formulário padronizado e calibrado no RSAC V2, cobrindo metadados bibliográficos, setor econômico analisado, modelo de governança, impactos no desenvolvimento local e limitações reportadas..."
              value={manuscript.data_charting_process}
              onChange={(e) => updateManuscriptField('data_charting_process', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 11 — Essencial</span>
              <span className="item-section-tag">MÉTODOS / VARIÁVEIS</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <HelpCircle size={20} className="icon-accent" />
                <h2>Perguntas e Variáveis de Mapeamento (Data Items)</h2>
              </div>
              <div className="card-header-actions">
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
              </div>
            </div>
            <p className="section-help">
              Conforme PRISMA-ScR Item 11: Liste as perguntas estruturadas de extração que responderão aos objetivos e mapearão as variáveis de cada estudo na Triagem 2.
            </p>

            <div className="criteria-list">
              {questions.map((q, idx) => (
                <div key={q.id || idx} className="criterion-card">
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
                </div>
              ))}
            </div>

            <div style={{ marginTop: 'var(--space-3)' }}>
              <button type="button" className="btn-secondary small" onClick={addQuestion}>
                <Plus size={14} /> Adicionar Pergunta de Mapeamento
              </button>
            </div>
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag optional">Item 12 — Opcional</span>
              <span className="item-section-tag">MÉTODOS / AVALIAÇÃO CRÍTICA</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <ShieldCheck size={20} className="icon-accent" />
                <h2>Avaliação Crítica da Qualidade Metodológica (Critical Appraisal)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="critical_appraisal"
                  fieldLabel="Avaliação Crítica e Risco de Viés"
                  currentValue={manuscript.critical_appraisal}
                  fieldGuidelines="Conforme PRISMA-ScR Item 12: Em revisões de escopo, a avaliação de risco de viés é opcional. Descreva o instrumento ou justifique a dispensa metodológica formal."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('critical_appraisal')}
                  onApply={(text) => updateManuscriptField('critical_appraisal', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.appraisal ? 'active' : ''}`}
                  onClick={() => toggleHelp('appraisal')}
                  title="Ver orientação sobre avaliação crítica em scoping reviews"
                >
                  <HelpCircle size={16} />
                  <span>Guia da Avaliação Crítica (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 12: Em revisões de escopo, a avaliação formal de risco de viés é <strong>opcional</strong>. Caso realizada, descreva o instrumento utilizado ou justifique sua dispensa.
            </p>

            {helpOpen.appraisal && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Orientações sobre Avaliação Crítica (PRISMA-ScR Item 12)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Em conformidade com as diretrizes do Joanna Briggs Institute (JBI) e da extensão PRISMA-ScR (Tricco et al., 2018), a avaliação formal de risco de viés e qualidade metodológica individual não foi realizada, tendo em vista que o objetivo central desta scoping review é mapear abrangentemente a literatura existente sobre o desenvolvimento regional e políticas públicas, independentemente do desenho metodológico das pesquisas primárias.`
                      if (manuscript.critical_appraisal && !window.confirm('Substituir justificativa de dispensa pelo modelo?')) return
                      updateManuscriptField('critical_appraisal', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Justificativa Padrão
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">Dispensa Padrão em Scoping Review</span>
                    <p>Revisões de escopo buscam amplitude temática e mapeamento abrangente.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">Se for Avaliar</span>
                    <p>Especifique os critérios de consistência metodológica adotados.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: Em conformidade com o framework de Arksey & O'Malley e com o PRISMA-ScR, a avaliação formal de risco de viés não foi realizada por se tratar de um mapeamento abrangente da extensão das evidências."
              value={manuscript.critical_appraisal}
              onChange={(e) => updateManuscriptField('critical_appraisal', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 14 — Essencial</span>
              <span className="item-section-tag">MÉTODOS / SÍNTESE</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <Layers size={20} className="icon-accent" />
                <h2>Métodos de Síntese e Mapeamento de Evidências (Synthesis of Results)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="synthesis_methods"
                  fieldLabel="Métodos de Síntese e Mapeamento"
                  currentValue={manuscript.synthesis_methods}
                  fieldGuidelines="Conforme PRISMA-ScR Item 14: Descreva os métodos de agrupamento temático, mapas de evidências tabulares, gráficos de tendências e matriz de identificação de lacunas."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('synthesis_methods')}
                  onApply={(text) => updateManuscriptField('synthesis_methods', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.synthesis ? 'active' : ''}`}
                  onClick={() => toggleHelp('synthesis')}
                  title="Ver guia de métodos de síntese"
                >
                  <HelpCircle size={16} />
                  <span>Guia da Síntese (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 14: Descreva como os dados serão estruturados (tabelas descritivas, gráficos de tendências temporais, mapas territoriais ou matrizes de lacunas de evidência).
            </p>

            {helpOpen.synthesis && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura de Métodos de Síntese (PRISMA-ScR Item 14)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Síntese Narrativa e Temática:
Os dados extraídos serão agrupados por eixos temáticos (ex: tipologia de governança, setor produtivo, instrumentos de fomento) alinhados ao framework PCC.

Apresentação Tabular e Mapeamento:
Elaboração de tabelas descritivas detalhando autoria, ano, território/região de estudo, metodologia empregada e principais achados socioeconômicos.

Diagramas e Representações Visuais:
Geração de gráficos de distribuição cronológica e geográfica das pesquisas, acompanhados pelo fluxograma PRISMA 2020 de seleção.

Matriz de Identificação de Lacunas (Gap Analysis):
Construção de matriz estruturada para apontar territórios e temas com carência de evidências empíricas.`

                      if (manuscript.synthesis_methods && !window.confirm('Substituir métodos de síntese pelo modelo?')) return
                      updateManuscriptField('synthesis_methods', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Síntese Narrativa</span>
                    <p>Descrição qualitativa dos padrões conceituais e institucionais identificados.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Mapas Tabulares</span>
                    <p>Tabelas consolidadas com características e recortes territoriais dos estudos.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Matriz de Lacunas</span>
                    <p>Mapeamento visual de lacunas na literatura acadêmica.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: Os resultados serão apresentados em formato de mapa de evidências narrativo e tabular, acompanhado de diagramas de distribuição temporal e territorial por arranjo produtivo..."
              value={manuscript.synthesis_methods}
              onChange={(e) => updateManuscriptField('synthesis_methods', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 27 — Essencial</span>
              <span className="item-section-tag">FINANCIAMENTO</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <ShieldCheck size={20} className="icon-accent" />
                <h2>Financiamento & Declaração de Conflitos de Interesse (Funding)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="funding"
                  fieldLabel="Financiamento e Declaração de Conflitos"
                  currentValue={manuscript.funding}
                  fieldGuidelines="Conforme PRISMA-ScR Item 27: Declare as agências de fomento, bolsas (CAPES, CNPq, FAPESP) e confirme a inexistência de conflitos de interesse."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('funding')}
                  onApply={(text) => updateManuscriptField('funding', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.funding ? 'active' : ''}`}
                  onClick={() => toggleHelp('funding')}
                  title="Ver guia de financiamento e conflitos"
                >
                  <HelpCircle size={16} />
                  <span>Guia do Financiamento (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 27: Declare as fontes de financiamento ou bolsas (ex: CAPES, CNPq, FAPESP, FAPEMIG) e confirme a inexistência de conflitos de interesse.
            </p>

            {helpOpen.funding && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura de Financiamento e Conflitos (PRISMA-ScR Item 27)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Fontes de Financiamento:
O presente trabalho foi realizado com apoio da Coordenação de Aperfeiçoamento de Pessoal de Nível Superior - Brasil (CAPES) - Código de Financiamento 001, e do Conselho Nacional de Desenvolvimento Científico e Tecnológico (CNPq).

Papel dos Financiadores:
As entidades financiadoras não exerceram qualquer influência na formulação do protocolo, na busca, análise ou interpretação dos dados, na redação deste manuscrito ou na decisão de publicação.

Declaração de Conflitos de Interesse:
Os autores declaram expressamente a inexistência de quaisquer conflitos de interesse financeiros, profissionais ou institucionais.`

                      if (manuscript.funding && !window.confirm('Substituir financiamento pelo modelo estruturado?')) return
                      updateManuscriptField('funding', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Agências de Fomento</span>
                    <p>Nome das agências financiadoras e números de processo / bolsas acadêmicas.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Papel dos Financiadores</span>
                    <p>Declaração de total independência dos autores na condução da pesquisa.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Conflitos de Interesse</span>
                    <p>Declaração formal de inexistência de conflitos.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: Este trabalho foi realizado com apoio da Coordenação de Aperfeiçoamento de Pessoal de Nível Superior - Brasil (CAPES) - Código de Financiamento 001. Os autores declaram não haver conflitos de interesse."
              value={manuscript.funding}
              onChange={(e) => updateManuscriptField('funding', e.target.value)}
            />
          </div>
        </div>
      )}

      {/* ── ABA 5: SÍNTESE DOS ACHADOS & DISCUSSÃO (A POSTERIORI) ─────────── */}
      {activeStudioTab === 'synthesis_discussion' && (
        <div className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-posteriori-banner">
            <span className="phase-badge a-posteriori">Fase A Posteriori — Pós-Extração / Síntese dos Resultados</span>
            <p>
              Esta seção <strong>deve ser redigida após a execução da coleta, triagem e extração</strong> dos dados dos estudos incluídos, com base nas evidências empíricas reais consolidadas.
            </p>
          </div>

          {/* Painel de Evidências Reais & Rastreabilidade */}
          <div className="evidence-traceability-card">
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
          </div>
          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 24 — Essencial</span>
              <span className="item-section-tag">DISCUSSÃO / RESULTADOS</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <Bookmark size={20} className="icon-accent" />
                <h2>Síntese Geral das Evidências (Summary of Evidence)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="summary_evidence"
                  fieldLabel="Síntese Geral das Evidências"
                  currentValue={manuscript.summary_evidence}
                  fieldGuidelines="Conforme PRISMA-ScR Item 24: Resuma os principais conceitos, tendências territoriais e relevância prática dos achados para políticas públicas e pesquisadores."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('summary_evidence')}
                  onApply={(text) => updateManuscriptField('summary_evidence', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.summaryEvidence ? 'active' : ''}`}
                  onClick={() => toggleHelp('summaryEvidence')}
                  title="Ver guia de síntese das evidências"
                >
                  <HelpCircle size={16} />
                  <span>Guia dos Achados (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 24: Resuma os principais conceitos identificados, os temas dominantes e a relevância prática dos achados para formuladores de políticas públicas e pesquisadores.
            </p>

            {helpOpen.summaryEvidence && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura da Síntese de Evidências (PRISMA-ScR Item 24)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Panorama das Evidências Mapeadas:
A síntese dos estudos incluídos evidenciou a evolução das pesquisas sobre [Conceito Central / Desenvolvimento Regional], concentrada principalmente em...

Temas Dominantes e Padrões Identificados:
Observou-se predominância de abordagens voltadas para..., com relativa escassez de análises longitudinais sobre sustentabilidade institucional dos arranjos territoriais.

Relevância Prática e Institucional:
Os resultados oferecem um panorama estruturado para gestores públicos, formuladores de políticas e pesquisadores sobre as potencialidades e desafios do desenvolvimento regional.`

                      if (manuscript.summary_evidence && !window.confirm('Substituir síntese de evidências pelo modelo?')) return
                      updateManuscriptField('summary_evidence', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Panorama Geral</span>
                    <p>Volume e amplitude das evidências encontradas na literatura.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Temas Dominantes</span>
                    <p>Principais tendências teóricas ou territoriais mapeadas.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Relevância Prática</span>
                    <p>Utilidade para planejamento governamental e desenvolvimento local.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={5}
              className="protocol-textarea"
              placeholder="Ex: A presente revisão de escopo identificou um crescimento expressivo na produção acadêmica sobre governança em arranjos produtivos..."
              value={manuscript.summary_evidence}
              onChange={(e) => updateManuscriptField('summary_evidence', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 25 — Essencial</span>
              <span className="item-section-tag">DISCUSSÃO / LIMITAÇÕES</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <AlertTriangle size={20} className="icon-accent" />
                <h2>Limitações da Revisão de Escopo (Limitations)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="limitations"
                  fieldLabel="Limitações da Revisão"
                  currentValue={manuscript.limitations}
                  fieldGuidelines="Conforme PRISMA-ScR Item 25: Aponte as limitações inerentes ao processo da revisão (filtros linguísticos, bases consultadas, relatórios institucionais não capturados)."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('limitations')}
                  onApply={(text) => updateManuscriptField('limitations', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.limitations ? 'active' : ''}`}
                  onClick={() => toggleHelp('limitations')}
                  title="Ver guia de limitações"
                >
                  <HelpCircle size={16} />
                  <span>Guia das Limitações (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 25: Aponte as limitações inerentes ao processo da revisão (ex: restrições de idioma, bases indexadas, ausência de busca manual de literatura cinzenta não publicada).
            </p>

            {helpOpen.limitations && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura de Limitações da Revisão (PRISMA-ScR Item 25)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Limitações do Processo de Busca:
A busca foi restrita a publicações em português, inglês e espanhol, o que pode ter desconsiderado estudos relevantes em outras línguas.

Literatura Cinzenta e Documentos Institucionais:
Embora teses e dissertações tenham sido consultadas na BDTD, relatórios técnicos municipais e documentos institucionais não indexados podem não ter sido integralmente capturados.

Heterogeneidade dos Estudos Primários:
A diversidade metodológica e conceitual na caracterização dos territórios limitou a comparabilidade direta entre determinadas realidades regionais.`

                      if (manuscript.limitations && !window.confirm('Substituir limitações pelo modelo estruturado?')) return
                      updateManuscriptField('limitations', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Limitações de Busca</span>
                    <p>Filtros de idioma, bases consultadas e período considerado.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Literatura Cinzenta</span>
                    <p>Potencial não captura de relatórios governamentais não indexados.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Desvios do Protocolo</span>
                    <p>Justifique qualquer ajuste metodológico feito durante a revisão.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={4}
              className="protocol-textarea"
              placeholder="Ex: Como limitação deste estudo, destaca-se a inclusão restrita a artigos publicados em português, inglês e espanhol, além da potencial não captura de relatórios técnicos governamentais não indexados."
              value={manuscript.limitations}
              onChange={(e) => updateManuscriptField('limitations', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 26 — Essencial</span>
              <span className="item-section-tag">CONCLUSÕES</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <CheckCircle2 size={20} className="icon-accent" />
                <h2>Conclusões e Lacunas de Conhecimento (Conclusions)</h2>
              </div>
              <div className="card-header-actions">
                <AIAssistButton
                  fieldId="conclusions"
                  fieldLabel="Conclusões e Lacunas de Conhecimento"
                  currentValue={manuscript.conclusions}
                  fieldGuidelines="Conforme PRISMA-ScR Item 26: Forneça interpretação geral dos resultados, aponte lacunas científicas evidentes e sugira direções concretas para estudos e políticas públicas futuras."
                  projectTitle={activeProject?.title}
                  methodology={activeProject?.methodology}
                  projectContext={getFullProtocolContext('conclusions')}
                  onApply={(text) => updateManuscriptField('conclusions', text)}
                />
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.conclusions ? 'active' : ''}`}
                  onClick={() => toggleHelp('conclusions')}
                  title="Ver guia de conclusões e lacunas"
                >
                  <HelpCircle size={16} />
                  <span>Guia das Conclusões (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 26: Forneça interpretação geral dos resultados, aponte lacunas científicas evidentes e sugira direções concretas para estudos e políticas públicas futuras.
            </p>

            {helpOpen.conclusions && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura de Conclusões e Lacunas (PRISMA-ScR Item 26)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Conclusão Geral:
Esta scoping review sintetizou com rigor a produção científica sobre [Conceito Central / Desenvolvimento Regional], demonstrando que...

Principais Lacunas Identificadas:
Constatou-se escassez de pesquisas que avaliem a sustentabilidade financeira de longo prazo dos arranjos locais e a integração com políticas de inovação aberta.

Recomendações para Estudos Futuros:
Sugere-se que investigações futuras priorizem estudos longitudinais de governança territorial e análises comparadas entre diferentes recortes regionais.`

                      if (manuscript.conclusions && !window.confirm('Substituir conclusões pelo modelo estruturado?')) return
                      updateManuscriptField('conclusions', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Síntese Conclusiva</span>
                    <p>Resposta direta aos objetivos e questão norteadora.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Lacunas Mapeadas</span>
                    <p>O que ainda falta na literatura para avanço do conhecimento na área.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Próximos Passos</span>
                    <p>Recomendações objetivas para futuras pesquisas e políticas públicas.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={5}
              className="protocol-textarea"
              placeholder="Ex: Conclui-se que, embora haja vasta produção acadêmica sobre desenvolvimento territorial, verifica-se escassez de estudos com avaliação de impacto socioeconômico de longo prazo..."
              value={manuscript.conclusions}
              onChange={(e) => updateManuscriptField('conclusions', e.target.value)}
            />
          </div>
        </div>
      )}

      {/* ── ABA 6: RESUMO ESTRUTURADO FINAL (A POSTERIORI) ───────────────── */}
      {activeStudioTab === 'final_summary' && (
        <div className="tab-pane animate-fade-in">
          <div className="phase-indicator-banner a-posteriori-banner">
            <span className="phase-badge a-posteriori">Fase A Posteriori — Resumo Executivo Definitivo</span>
            <p>
              O Resumo Estruturado Final deve ser fechado <strong>após a conclusão de todo o trabalho</strong>, sintetizando os quantitativos exatos do funil PRISMA, as evidências descobertas e a conclusão central da pesquisa.
            </p>
          </div>
          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 2 — Essencial</span>
              <span className="item-section-tag">RESUMO</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <FileText size={20} className="icon-accent" />
                <h2>Resumo Estruturado do Artigo / Protocolo (Structured Summary)</h2>
              </div>
              <div className="card-header-actions">
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
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.summary ? 'active' : ''}`}
                  onClick={() => toggleHelp('summary')}
                  title="Ver tópicos sugeridos e guia estruturado do resumo"
                >
                  <HelpCircle size={16} />
                  <span>Guia do Resumo (?)</span>
                </button>
              </div>
            </div>

            <p className="section-help">
              Conforme PRISMA-ScR Item 2: Estruture o resumo com os tópicos recomendados (Contexto, Objetivos, Elegibilidade, Fontes, Métodos de Charting, Resultados e Conclusões).
            </p>

            {helpOpen.summary && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura Recomendada para o Resumo (PRISMA-ScR Item 2)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Contexto / Introdução:
[Descreva o panorama socioeconômico, as dinâmicas territoriais e a relevância do desenvolvimento regional no tema abordado]

Objetivo:
[Defina a questão central e o objetivo do mapeamento conceitual com base no framework PCC]

Critérios de Elegibilidade:
[Atores sociais, políticas públicas/conceitos avaliados, contextos territoriais e tipos de estudo aceitos]

Fontes de Informação:
[Bases consultadas: BDTD, SciELO, Scopus, OpenAlex, literatura cinzenta institucional e data da busca]

Métodos de Charting (Extração):
[Extração em duplicata independente com formulário padronizado no RSAC V2]

Resultados Esperados:
[Mapeamento das abordagens metodológicas, instrumentos de política pública e principais lacunas identificadas]

Conclusões:
[Síntese das implicações para a formulação de políticas públicas e direções para pesquisas futuras]`

                      if (manuscript.structured_summary && !window.confirm('Substituir resumo pelo modelo estruturado?')) return
                      updateManuscriptField('structured_summary', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>

                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Contexto / Background</span>
                    <p>Panorama do problema socioeconômico, institucional ou territorial abordado.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Objetivos / Objectives</span>
                    <p>Questão norteadora e finalidade de mapear a extensão da literatura.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">3. Critérios de Elegibilidade</span>
                    <p>Atores, conceitos centrais, cenários territoriais e limites temporais/idiomáticos.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">4. Fontes de Informação</span>
                    <p>Bases consultadas (BDTD, SciELO, etc.) e data da execução da busca.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">5. Métodos de Charting</span>
                    <p>Extração dos dados em duplicata com instrumento padronizado.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">6. Resultados Esperados</span>
                    <p>Mapeamento das características e lacunas teóricas/empíricas identificadas.</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">7. Conclusões</span>
                    <p>Contribuições para o desenvolvimento regional e políticas públicas.</p>
                  </div>
                </div>
              </div>
            )}

            <textarea
              rows={9}
              className="protocol-textarea"
              placeholder="Digite ou cole aqui o resumo estruturado do seu artigo / protocolo..."
              value={manuscript.structured_summary}
              onChange={(e) => updateManuscriptField('structured_summary', e.target.value)}
            />
          </div>

          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 1 — Essencial</span>
              <span className="item-section-tag">TÍTULO</span>
            </div>
            <div className="card-section-title-with-actions">
              <div className="card-section-title">
                <Edit3 size={20} className="icon-accent" />
                <h2>Título Oficial da Revisão de Escopo (Scoping Review)</h2>
              </div>
              <div className="card-header-actions">
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
                <button
                  type="button"
                  className={`btn-help-toggle ${helpOpen.title ? 'active' : ''}`}
                  onClick={() => toggleHelp('title')}
                  title="Ver guia de elaboração do título"
                >
                  <HelpCircle size={16} />
                  <span>Guia do Título (?)</span>
                </button>
              </div>
            </div>
            <p className="section-help">
              Conforme PRISMA-ScR Item 1: Identifique claramente o trabalho como uma <strong>Scoping Review</strong> e reflita os elementos centrais de elegibilidade (População/Atores, Conceito Central e Contexto Territorial).
            </p>

            {helpOpen.title && (
              <div className="structured-guide-box animate-fade-in">
                <div className="guide-header">
                  <div className="guide-title">
                    <HelpCircle size={18} className="icon-accent" />
                    <strong>Estrutura Recomendada para o Título (PRISMA-ScR Item 1)</strong>
                  </div>
                  <button
                    type="button"
                    className="btn-insert-template"
                    onClick={() => {
                      const template = `Políticas Públicas de [Instrumento / Política] e [Conceito Central] no [Contexto Regional / Território] para [Atores Sociais / Setor Produtivo]: Uma Revisão de Escopo`
                      if (manuscript.manuscript_title && !window.confirm('Substituir título atual pelo modelo?')) return
                      updateManuscriptField('manuscript_title', template)
                    }}
                  >
                    <Plus size={14} /> Inserir Estrutura no Editor
                  </button>
                </div>
                <div className="guide-grid">
                  <div className="guide-item">
                    <span className="guide-tag">1. Identificação do Método</span>
                    <p>O subtítulo DEVE conter explicitamente "Uma Revisão de Escopo" ou "Scoping Review".</p>
                  </div>
                  <div className="guide-item">
                    <span className="guide-tag">2. Elementos PCC</span>
                    <p>Mencione o Conceito Central (ex: Arranjos Produtivos Locais), o Contexto Territorial e os Atores Sociais.</p>
                  </div>
                </div>
              </div>
            )}

            <input
              type="text"
              className="protocol-input-large"
              placeholder="Ex: Governança Territorial e Arranjos Produtivos Locais no Desenvolvimento Regional do Semiárido: Uma Revisão de Escopo"
              value={manuscript.manuscript_title}
              onChange={(e) => updateManuscriptField('manuscript_title', e.target.value)}
            />
          </div>
        </div>
      )}

      {/* ── ABA 7: AUDITORIA E CHECKLIST DO PROTOCOLO ATIVO ───────────────── */}
      {activeStudioTab === 'checklist' && (
        <div className="tab-pane animate-fade-in">
          <div className="protocol-card scr-checklist-card">
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
                    <div
                      key={chk.id}
                      className={`scr-checklist-row ${isChecked ? 'checked' : ''} ${chk.essential ? 'essential' : 'optional'}`}
                      onClick={() => toggleScRItem(chk.id)}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleScRItem(chk.id)}
                        onClick={(e) => e.stopPropagation()}
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
                        <p className="scr-item-desc">{chk.desc}</p>
                      </div>
                    </div>
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
                      <div
                        key={chk.id}
                        className={`scr-checklist-row ${isChecked ? 'checked' : ''} ${chk.essential ? 'essential' : 'optional'}`}
                        onClick={() => toggleScRItem(chk.id)}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleScRItem(chk.id)}
                          onClick={(e) => e.stopPropagation()}
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
                          <p className="scr-item-desc">{chk.desc}</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* AI Suggestion Modal */}
      {isAiModalOpen && (
        <div className="modal-overlay animate-fade-in" onClick={() => setIsAiModalOpen(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-titlebar">
              <span>Proposta de Protocolo Gerada por IA ({activeProject?.methodology})</span>
              <button className="modal-titlebar-btn" onClick={() => setIsAiModalOpen(false)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              {aiLoading ? (
                <div className="empty-state" style={{ padding: 'var(--space-8)' }}>
                  <Sparkles size={32} className="animate-spin icon-accent" />
                  <p style={{ marginTop: 'var(--space-2)' }}>
                    Elaborando proposta de PICO/PCC, descritores em pares e critérios em Ciências Sociais Aplicadas...
                  </p>
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

                  <div className="modal-actions">
                    <button type="button" className="btn-secondary" onClick={() => setIsAiModalOpen(false)}>
                      Cancelar
                    </button>
                    <button type="button" className="btn-primary" onClick={handleApplyAISuggestions}>
                      <Sparkles size={16} /> Aplicar Proposta ao Protocolo
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
