/**
 * RSAC V2 — Protocol Page & Complete Manuscript Drafting Studio (PRISMA-ScR & PRISMA 2020)
 * Especializado em Ciências Sociais Aplicadas & Desenvolvimento Regional.
 * Redação integral de todos os 22 itens do artigo/protocolo:
 * Título, Resumo Estruturado, Justificativa, Objetivos (PCC/PICO), Registro, Critérios,
 * Fontes, Descritores em Pares (VuFind/BDTD), Seleção & Calibração, Data Charting,
 * Perguntas de Mapeamento, Avaliação Crítica, Síntese, Limitações, Conclusões e Financiamento.
 * Todos os campos contam com Guias Estruturados (?) e botão "Inserir Estrutura no Editor".
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
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { PROTOCOL_CATALOG, PROTOCOL_OPTIONS } from '@/data/protocolCatalog'
import type { Criterion, ExtractionQuestion, ProtocolSuggestions, Methodology } from '@/types/api'
import './ProtocolPage.css'

export function ProtocolPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject, aiEnabled } = useSettingsStore()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [copiedNotification, setCopiedNotification] = useState(false)

  // Active Tab for Manuscript Studio
  const [activeStudioTab, setActiveStudioTab] = useState<
    'overview' | 'intro' | 'search' | 'selection' | 'discussion' | 'checklist'
  >('overview')

  // Framework Mode (PICO vs PCC)
  const [frameworkType, setFrameworkType] = useState<'PICO' | 'PCC'>('PCC')

  // Core Protocol State
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

      const proto = await api.getProtocol(projectId)
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

      setCriteria(proto.criteria || [])
      setQuestions(proto.extraction_questions || [])

      if (proto.manuscript_sections) {
        setManuscript((prev) => ({
          ...prev,
          ...proto.manuscript_sections,
          manuscript_title: proto.manuscript_sections.manuscript_title || proj?.title || '',
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
    if (descriptors[lang].length >= 5) {
      alert('Limite máximo de 5 pares de descritores por idioma atingido.')
      return
    }
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
        question: '',
        field_type: 'text',
        options: [],
        required: true,
        order: questions.length,
      },
    ])
  }

  const updateQuestion = (index: number, text: string) => {
    const updated = [...questions]
    updated[index].question = text
    setQuestions(updated)
  }

  const removeQuestion = (index: number) => {
    setQuestions(questions.filter((_, i) => i !== index))
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
        .filter((q) => q.question.trim().length > 0)
        .map((q, idx) => ({ ...q, order: idx }))

      await api.updateProtocol(id, {
        objective,
        pico_framework: pico,
        search_descriptors: cleanDescriptors,
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
${questions.map((q, i) => `${i + 1}. ${q.question}`).join('\n') || 'Nenhuma pergunta cadastrada'}

### Avaliação Crítica da Evidência (Opcional)
${manuscript.critical_appraisal || 'Dispensada / Não realizada para esta revisão de escopo.'}

### Métodos de Síntese
${manuscript.synthesis_methods || 'Não preenchido.'}

---

## 5. Discussão, Limitações e Conclusões
### Síntese da Evidência
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
      (question, idx) => ({
        question,
        field_type: 'text',
        options: [],
        required: true,
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

      {/* Studio Navigation Tabs (All 6 tabs visible simultaneously without horizontal scroll) */}
      <div className="studio-tabs-bar">
        <button
          type="button"
          className={`studio-tab ${activeStudioTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveStudioTab('overview')}
          title="1. Título & Resumo Estruturado (Itens 1-2)"
        >
          <Edit3 size={13} className="tab-icon" />
          <span className="tab-label">1. Título & Resumo</span>
          <span className="tab-pill">1-2</span>
        </button>
        <button
          type="button"
          className={`studio-tab ${activeStudioTab === 'intro' ? 'active' : ''}`}
          onClick={() => setActiveStudioTab('intro')}
          title={`2. Justificativa & Objetivos (${frameworkType}) (Itens 3-4)`}
        >
          <BookOpen size={13} className="tab-icon" />
          <span className="tab-label">2. Justificativa ({frameworkType})</span>
          <span className="tab-pill">3-4</span>
        </button>
        <button
          type="button"
          className={`studio-tab ${activeStudioTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveStudioTab('search')}
          title="3. Fontes, Descritores & Elegibilidade (Itens 5-8)"
        >
          <Search size={13} className="tab-icon" />
          <span className="tab-label">3. Fontes & Elegibilidade</span>
          <span className="tab-pill">5-8</span>
        </button>
        <button
          type="button"
          className={`studio-tab ${activeStudioTab === 'selection' ? 'active' : ''}`}
          onClick={() => setActiveStudioTab('selection')}
          title="4. Seleção, Mapeamento & Síntese (Itens 9-14)"
        >
          <Filter size={13} className="tab-icon" />
          <span className="tab-label">4. Seleção & Síntese</span>
          <span className="tab-pill">9-14</span>
        </button>
        <button
          type="button"
          className={`studio-tab ${activeStudioTab === 'discussion' ? 'active' : ''}`}
          onClick={() => setActiveStudioTab('discussion')}
          title="5. Discussão, Limitações & Financiamento (Itens 24-27)"
        >
          <Bookmark size={13} className="tab-icon" />
          <span className="tab-label">5. Discussão & Limitações</span>
          <span className="tab-pill">24-27</span>
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

      {/* ── ABA 1: TÍTULO & RESUMO ESTRUTURADO ───────────────────────────── */}
      {activeStudioTab === 'overview' && (
        <div className="tab-pane animate-fade-in">
          {/* Item 1: Título */}
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

          {/* Item 2: Resumo Estruturado */}
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
        </div>
      )}

      {/* ── ABA 2: JUSTIFICATIVA & OBJETIVOS (PCC / PICO) ───────────────── */}
      {activeStudioTab === 'intro' && (
        <div className="tab-pane animate-fade-in">
          {/* Item 3: Justificativa */}
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

          {/* Item 4: Objetivos e PCC */}
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
                <label>
                  <strong>P</strong> — População / Atores Sociais
                </label>
                <textarea
                  rows={2}
                  placeholder="Ex: Produtores locais, cooperativas, pequenas e médias empresas, comunidades rurais ou gestores públicos..."
                  value={pico.population}
                  onChange={(e) => setPico({ ...pico, population: e.target.value })}
                />
              </div>
              <div className="pico-field">
                <label>
                  <strong>{frameworkType === 'PCC' ? 'C' : 'I'}</strong> —{' '}
                  {frameworkType === 'PCC' ? 'Conceito Central (Concept)' : 'Intervenção / Política (Intervention)'}
                </label>
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
                <label>
                  <strong>{frameworkType === 'PCC' ? 'C' : 'C'}</strong> —{' '}
                  {frameworkType === 'PCC' ? 'Contexto Territorial (Context)' : 'Comparador (Comparison)'}
                </label>
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
                <label>
                  <strong>{frameworkType === 'PCC' ? 'M' : 'O'}</strong> —{' '}
                  {frameworkType === 'PCC' ? 'Mapeamento de Escopo' : 'Desfecho Socioeconômico (Outcomes)'}
                </label>
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

      {/* ── ABA 3: FONTES, DESCRITORES & ELEGIBILIDADE ─────────────────── */}
      {activeStudioTab === 'search' && (
        <div className="tab-pane animate-fade-in">
          {/* Item 5: Protocolo e Registro */}
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

          {/* Item 7: Fontes de Informação */}
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

          {/* Item 8: Estratégia de Busca em Pares (VuFind/BDTD Compliance) */}
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

            <p className="section-help">
              Conforme PRISMA-ScR Item 8 e Diretrizes RSAC: Formulação em <strong>pares de termos com AND</strong> (máximo 2 termos por expressão e até 5 pares por idioma), garantindo perfeita compatibilidade com o motor VuFind da BDTD.
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
                    <span className="guide-tag">2. Limite de 5 Pares por Idioma</span>
                    <p>Até 5 pares em Português, 5 em Inglês e 5 em Espanhol para evitar sobrecarga ou falha no VuFind.</p>
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
                🇧🇷 Português ({descriptors.pt.filter(Boolean).length}/5)
              </button>
              <button
                type="button"
                className={`lang-tab ${activeLangTab === 'en' ? 'active' : ''}`}
                onClick={() => setActiveLangTab('en')}
              >
                🇺🇸 Inglês ({descriptors.en.filter(Boolean).length}/5)
              </button>
              <button
                type="button"
                className={`lang-tab ${activeLangTab === 'es' ? 'active' : ''}`}
                onClick={() => setActiveLangTab('es')}
              >
                🇪🇸 Espanhol ({descriptors.es.filter(Boolean).length}/5)
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

              {descriptors[activeLangTab].length < 5 && (
                <button
                  type="button"
                  className="btn-add-descriptor"
                  onClick={() => addDescriptor(activeLangTab)}
                >
                  <Plus size={14} /> Adicionar Par de Descritores ({descriptors[activeLangTab].length}/5)
                </button>
              )}
            </div>
          </div>

          {/* Item 6: Critérios de Elegibilidade */}
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
        </div>
      )}

      {/* ── ABA 4: SELEÇÃO, MAPEAMENTO & SÍNTESE ───────────────────────── */}
      {activeStudioTab === 'selection' && (
        <div className="tab-pane animate-fade-in">
          {/* Item 9: Processo de Seleção e Calibração */}
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

          {/* Item 10: Processo de Data Charting */}
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

          {/* Item 11: Perguntas de Mapeamento */}
          <div className="protocol-card">
            <div className="item-header-meta">
              <span className="item-tag essential">Item 11 — Essencial</span>
              <span className="item-section-tag">MÉTODOS / VARIÁVEIS</span>
            </div>
            <div className="card-section-title">
              <HelpCircle size={20} className="icon-accent" />
              <h2>Perguntas e Variáveis de Mapeamento (Data Items)</h2>
            </div>
            <p className="section-help">
              Conforme PRISMA-ScR Item 11: Liste as perguntas estruturadas de extração que responderão aos objetivos e mapearão as variáveis de cada estudo na Triagem 2.
            </p>

            <div className="criteria-list">
              {questions.map((q, idx) => (
                <div key={idx} className="criterion-card">
                  <span className="criterion-code inclusion">Q-{idx + 1}</span>
                  <input
                    type="text"
                    className="criterion-desc-input"
                    placeholder="Ex: Qual foi o modelo de governança territorial ou instrumento de política pública avaliado?"
                    value={q.question}
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

          {/* Item 12 (Opcional): Avaliação Crítica da Evidência */}
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

          {/* Item 14: Síntese e Mapeamento dos Resultados */}
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
        </div>
      )}

      {/* ── ABA 5: DISCUSSÃO, LIMITAÇÕES & FINANCIAMENTO ────────────────── */}
      {activeStudioTab === 'discussion' && (
        <div className="tab-pane animate-fade-in">
          {/* Item 24: Síntese dos Achados */}
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

          {/* Item 25: Limitações do Estudo */}
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

          {/* Item 26: Conclusões e Lacunas */}
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

          {/* Item 27: Financiamento e Conflitos */}
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

      {/* ── ABA 6: AUDITORIA E CHECKLIST DO PROTOCOLO ATIVO ─────────────────────── */}
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

            <div className="scr-items-grid">
              {currentProtocolDef.checklistItems.map((chk) => {
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
