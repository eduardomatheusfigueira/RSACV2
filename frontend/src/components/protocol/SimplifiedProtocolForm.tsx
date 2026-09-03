import React, { useState } from 'react'
import {
  BookOpen,
  Building2,
  CheckSquare,
  Clock,
  Copy,
  Database,
  FileText,
  Filter,
  Globe,
  HelpCircle,
  Layers,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from 'lucide-react'
import type { Criterion, ExtractionQuestion, SearchFilters, SearchStrategy, SearchExecution } from '@/types/api'
import { Card, Button, FormGroup, Input, Textarea, Select } from '@/components/ui'
import { AIAssistButton } from '@/components/common/AIAssistButton'
import { CampoDoProtocolo } from './CampoDoProtocolo'
import type { FerramentasDeApoio } from './apoioDoProtocolo'
import { ANCORAGEM_NORMATIVA, REVIEW_DESIGNS_CATALOG } from '@/data/protocolCatalog'
import { AVAILABLE_DATABASES, AVAILABLE_DOC_TYPES, AVAILABLE_LANGUAGES } from '@/pages/ProtocolPage'
import { SearchStrategyStudio } from './SearchStrategyStudio'
import './ProtocolStudio.css'

interface SimplifiedProtocolFormProps {
  projectId: string
  // S1
  title: string
  onTitleChange: (val: string) => void
  // S2
  objective: string
  onObjectiveChange: (val: string) => void
  // S3
  frameworkType: 'PCC' | 'PICO' | string
  onFrameworkTypeChange: (val: any) => void
  frameworkComponents: Record<string, string>
  onFrameworkComponentChange: (key: string, val: string) => void
  // S4
  reviewDesign: string
  onReviewDesignChange: (designId: string) => void
  // S5 & S7
  searchFilters: SearchFilters
  onSearchFiltersChange: (filters: SearchFilters) => void
  // S6 & S7 (Estratégia Canônica e Descritores)
  searchStrategy?: SearchStrategy | null
  onSearchStrategySaved?: (strat: SearchStrategy) => void
  descriptors?: Record<string, string[]>
  onDescriptorsChange?: (descriptors: Record<string, string[]>) => void
  // S8
  infoSources: string
  onInfoSourcesChange: (val: string) => void
  // S9 & S10
  criteria: Criterion[]
  onCriteriaChange: (criteria: Criterion[]) => void
  // S11 (Decisão D-C)
  extractionQuestions: ExtractionQuestion[]
  onExtractionQuestionsChange: (questions: ExtractionQuestion[]) => void
  // S12 & S13 (Doc 45 §8.2: 🔒 Automático / Execuções de Busca)
  searchExecutions?: SearchExecution[]
  // S14 (Doc 45 §8.2: 🔒 Automático + Notas de Deduplicação)
  dedupNotes: string
  onDedupNotesChange: (val: string) => void
  /** Guia e assistência por campo (doc 45 §16.4). Ver `apoioDoProtocolo.ts`. */
  apoio?: FerramentasDeApoio
  readOnly?: boolean
}

export function SimplifiedProtocolForm({
  projectId,
  title,
  onTitleChange,
  objective,
  onObjectiveChange,
  frameworkType,
  onFrameworkTypeChange,
  frameworkComponents,
  onFrameworkComponentChange,
  reviewDesign,
  onReviewDesignChange,
  searchFilters,
  onSearchFiltersChange,
  searchStrategy,
  onSearchStrategySaved,
  descriptors,
  onDescriptorsChange,
  infoSources,
  onInfoSourcesChange,
  criteria,
  onCriteriaChange,
  extractionQuestions,
  onExtractionQuestionsChange,
  searchExecutions = [],
  dedupNotes,
  onDedupNotesChange,
  apoio,
  readOnly = false,
}: SimplifiedProtocolFormProps): JSX.Element {
  const currentDesign = REVIEW_DESIGNS_CATALOG.find((d) => d.id === reviewDesign) || REVIEW_DESIGNS_CATALOG[3] // D4 default

  /* Ajuda de reserva: `apoio.ajuda` prefere o item da diretriz ATIVA, e estes
     textos entram quando ela não trata do campo — comum no Núcleo de Busca,
     cujos campos vêm do PRISMA-S e não da diretriz principal. */
  const AJUDA = {
    titulo: 'Declare o objeto investigado, o desenho da revisão e o recorte territorial e temporal pretendido.',
    objetivo: 'Uma pergunta central respondível e o objetivo geral no infinitivo. Se a pergunta não puder ser respondida pelos estudos que a busca trará, ela ainda está ampla demais.',
    framework: 'Cada componente vira um bloco de conceito da estratégia de busca — é esta ligação que impede a busca de nascer desalinhada da pergunta.',
    desenho: 'O desenho define o framework sugerido, a diretriz de relato, se a apreciação crítica é obrigatória e a elegibilidade a registro.',
    recorte: 'A escolha das bases pede razão declarada, e todo limite exclui: ano, idioma e tipo documental cortam resultados e precisam de justificativa metodológica.',
    estrategia: 'Um bloco por conceito, sinônimos unidos por OR, blocos unidos por AND. Cada base recebe a tradução do seu adaptador.',
    complementares: 'Busca manual em anais e portais, repositórios de teses, citação regressiva e progressiva e contato com autores.',
    criterios: 'Cada critério declara em que momento se aplica — título e resumo, texto completo, ou ambos. É o que torna o motivo de exclusão auditável no fluxograma.',
    deduplicacao: 'Método, chave usada e se houve conferência humana. Os números daqui são os do topo do fluxograma.',
    execucaoData: 'Momento exato em que cada base foi consultada. Preenchido pela execução, porque é fato da coleta e não decisão do pesquisador.',
    execucaoVolume: 'Quantos registros cada base devolveu, antes e depois da deduplicação. É a coluna “executado” do Registro de Busca.',
  }

  /* Os componentes exibidos dependem do framework. A tabela substitui os dois
     blocos de JSX quase idênticos que havia aqui, e é o que torna barato
     acrescentar SPIDER e CIMO de verdade em vez de só listá-los no seletor. */
  const COMPONENTES_POR_FRAMEWORK: Record<
    string,
    Array<{ chave: string; rotulo: string; fieldId: string; exemplo: string }>
  > = {
    PCC: [
      { chave: 'population', rotulo: 'População / Participantes (P)', fieldId: 'pico_population', exemplo: 'Ex.: APLs, cooperativas, governanças locais' },
      { chave: 'intervention', rotulo: 'Conceito central (C)', fieldId: 'pico_intervention', exemplo: 'Ex.: inovação socioeconômica, governança' },
      { chave: 'comparison', rotulo: 'Contexto / Cenário (C)', fieldId: 'pico_comparison', exemplo: 'Ex.: Brasil, América Latina, regiões periféricas' },
    ],
    PICO: [
      { chave: 'population', rotulo: 'População (P)', fieldId: 'pico_population', exemplo: 'População-alvo…' },
      { chave: 'intervention', rotulo: 'Intervenção (I)', fieldId: 'pico_intervention', exemplo: 'Intervenção ou política…' },
      { chave: 'comparison', rotulo: 'Comparador (C)', fieldId: 'pico_comparison', exemplo: 'Grupo de comparação…' },
      { chave: 'outcome', rotulo: 'Desfecho (O)', fieldId: 'pico_outcome', exemplo: 'Impacto ou resultado esperado…' },
    ],
    PECO: [
      { chave: 'population', rotulo: 'População (P)', fieldId: 'pico_population', exemplo: 'População-alvo…' },
      { chave: 'intervention', rotulo: 'Exposição (E)', fieldId: 'pico_intervention', exemplo: 'Exposição observada…' },
      { chave: 'comparison', rotulo: 'Comparador (C)', fieldId: 'pico_comparison', exemplo: 'Grupo não exposto…' },
      { chave: 'outcome', rotulo: 'Desfecho (O)', fieldId: 'pico_outcome', exemplo: 'Resultado observado…' },
    ],
    SPIDER: [
      { chave: 'population', rotulo: 'Amostra (S)', fieldId: 'pico_population', exemplo: 'Quem foi estudado…' },
      { chave: 'intervention', rotulo: 'Fenômeno de interesse (PI)', fieldId: 'pico_intervention', exemplo: 'Experiência ou percepção investigada…' },
      { chave: 'comparison', rotulo: 'Desenho e avaliação (D/E)', fieldId: 'pico_comparison', exemplo: 'Entrevista, grupo focal, etnografia…' },
      { chave: 'outcome', rotulo: 'Tipo de pesquisa (R)', fieldId: 'pico_outcome', exemplo: 'Qualitativa, mista…' },
    ],
    CIMO: [
      { chave: 'population', rotulo: 'Contexto (C)', fieldId: 'pico_population', exemplo: 'Onde e sob que condições…' },
      { chave: 'intervention', rotulo: 'Intervenção (I)', fieldId: 'pico_intervention', exemplo: 'Programa, política ou prática…' },
      { chave: 'comparison', rotulo: 'Mecanismo (M)', fieldId: 'pico_comparison', exemplo: 'Por que funcionaria…' },
      { chave: 'outcome', rotulo: 'Desfecho (O)', fieldId: 'pico_outcome', exemplo: 'Resultado esperado…' },
    ],
  }

  const componentesDoFramework =
    COMPONENTES_POR_FRAMEWORK[frameworkType] || COMPONENTES_POR_FRAMEWORK.PCC

  /** Assistência de um campo de texto simples do núcleo. */
  const assistir = (
    fieldId: string,
    fieldLabel: string,
    valor: string,
    orientacao: string,
    aplicar: (t: string) => void
  ) => (
    <AIAssistButton
      fieldId={fieldId}
      fieldLabel={fieldLabel}
      currentValue={valor}
      fieldGuidelines={orientacao}
      projectTitle={apoio?.projeto?.titulo}
      methodology={apoio?.projeto?.metodologia}
      projectContext={apoio?.contexto?.(fieldId)}
      onApply={aplicar}
    />
  )

  /* A assistência devolve texto; a lista é reconstruída a partir dele. O
     prefixo INC/EXC é o mesmo contrato do modo Completo, para que a mesma
     resposta do provedor sirva aos dois modos. */
  const aplicarCriteriosDeTexto = (texto: string) => {
    const linhas = texto.split('\n').map((l) => l.trim()).filter(Boolean)
    if (linhas.length === 0) return
    onCriteriaChange(
      linhas.map((linha, idx) => ({
        text: linha.replace(/^(INC:|EXC:)\s*/i, '').trim() || linha,
        is_exclusion: linha.toUpperCase().startsWith('EXC:'),
        dimension: 'outro' as const,
        applies_at: 'ambos' as const,
        order: idx,
      }))
    )
  }

  const aplicarPerguntasDeTexto = (texto: string) => {
    const linhas = texto.split('\n').map((l) => l.trim()).filter(Boolean)
    if (linhas.length === 0) return
    onExtractionQuestionsChange(
      linhas.map((linha, idx) => ({
        text: linha.replace(/^Q-?\d+[:.]\s*/i, '').trim() || linha,
        answer_type: 'texto' as const,
        options: [],
        required: false,
        order: idx,
      }))
    )
  }

  const [activeLangTab, setActiveLangTab] = useState<'pt' | 'en' | 'es'>('pt')

  const handleSyncFromStrategy = () => {
    if (!searchStrategy?.blocks || searchStrategy.blocks.length === 0) return
    const termsA = (searchStrategy.blocks[0]?.terms || []).filter((t: string) => t && t.trim())
    const termsB = (searchStrategy.blocks[1]?.terms || []).filter((t: string) => t && t.trim())
    const pairs: string[] = []
    if (termsA.length > 0 && termsB.length > 0) {
      for (const a of termsA) {
        for (const b of termsB) {
          const qa = a.includes(' ') && !a.startsWith('"') ? `"${a.trim()}"` : a.trim()
          const qb = b.includes(' ') && !b.startsWith('"') ? `"${b.trim()}"` : b.trim()
          pairs.push(`${qa} AND ${qb}`)
          if (pairs.length >= 5) break
        }
        if (pairs.length >= 5) break
      }
    } else if (termsA.length > 0) {
      pairs.push(...termsA.slice(0, 5).map((t: string) => (t.includes(' ') && !t.startsWith('"') ? `"${t.trim()}"` : t.trim())))
    }

    if (pairs.length > 0 && onDescriptorsChange) {
      onDescriptorsChange({
        ...(descriptors || {}),
        [activeLangTab]: pairs,
      })
    }
  }

  // Handlers para Critérios
  const handleAddCriterion = (isExclusion: boolean) => {
    if (readOnly) return
    const newCrit: Criterion = {
      text: '',
      is_exclusion: isExclusion,
      dimension: 'populacao',
      applies_at: 'ambos',
      order: criteria.length,
    }
    onCriteriaChange([...criteria, newCrit])
  }

  const handleUpdateCriterion = (idx: number, updates: Partial<Criterion>) => {
    if (readOnly) return
    const updated = [...criteria]
    updated[idx] = { ...updated[idx], ...updates }
    onCriteriaChange(updated)
  }

  const handleRemoveCriterion = (idx: number) => {
    if (readOnly) return
    onCriteriaChange(criteria.filter((_, i) => i !== idx))
  }

  // Handlers para Perguntas de Extração (Decisão D-C)
  const handleAddQuestion = () => {
    if (readOnly) return
    const newQ: ExtractionQuestion = {
      text: '',
      answer_type: 'texto',
      options: [],
      required: false,
      order: extractionQuestions.length,
    }
    onExtractionQuestionsChange([...extractionQuestions, newQ])
  }

  const handleUpdateQuestion = (idx: number, updates: Partial<ExtractionQuestion>) => {
    if (readOnly) return
    const updated = [...extractionQuestions]
    updated[idx] = { ...updated[idx], ...updates }
    onExtractionQuestionsChange(updated)
  }

  const handleRemoveQuestion = (idx: number) => {
    if (readOnly) return
    onExtractionQuestionsChange(extractionQuestions.filter((_, i) => i !== idx))
  }

  const handleApplySuggestedQuestions = () => {
    if (readOnly || !currentDesign?.suggestedExtractionQuestions) return
    const newQuestions: ExtractionQuestion[] = currentDesign.suggestedExtractionQuestions.map((qText, idx) => ({
      text: qText,
      answer_type: 'texto',
      options: [],
      required: true,
      order: idx,
    }))
    onExtractionQuestionsChange(newQuestions)
  }

  return (
    <div className="simplified-protocol">
      {/* ── S1: Título provisório ─────────────────────────────── */}
      <CampoDoProtocolo
        data-trilho-target="protocol-title"
        icone={<FileText size={20} className="icon-accent" aria-hidden="true" />}
        titulo="Título Provisório do Estudo"
        etiquetaItem="S1"
        secao="NÚCLEO / IDENTIFICAÇÃO"
        ajuda={apoio?.ajuda?.('manuscript_title', AJUDA.titulo) ?? AJUDA.titulo}
        assistencia={assistir(
          'manuscript_title',
          'Título Provisório do Protocolo',
          title,
          'Redija um título que declare o objeto investigado, o desenho da revisão e o recorte territorial e temporal pretendido.',
          onTitleChange
        )}
        guia={apoio?.montarGuia?.('manuscript_title', 's1', { valorAtual: title, aplicar: onTitleChange })}
      >
        <Input
          type="text"
          value={title}
          disabled={readOnly}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="Ex.: Políticas públicas territoriais e inovação em arranjos produtivos locais — protocolo de revisão de escopo"
        />
      </CampoDoProtocolo>

      {/* ── S2 e S3: Pergunta e framework ─────────────────────── */}
      <CampoDoProtocolo
        data-trilho-target="protocol-objective"
        icone={<BookOpen size={20} className="icon-accent" aria-hidden="true" />}
        titulo="Pergunta Principal e Objetivo Geral"
        etiquetaItem="S2"
        secao="NÚCLEO / PERGUNTA"
        ajuda={apoio?.ajuda?.('objective', AJUDA.objetivo) ?? AJUDA.objetivo}
        assistencia={assistir(
          'objective',
          'Pergunta e Objetivo da Revisão',
          objective,
          'Formule uma pergunta central respondível e o objetivo geral no infinitivo, com recorte territorial e temporal explícito.',
          onObjectiveChange
        )}
        guia={apoio?.montarGuia?.('objective', 's2', { valorAtual: objective, aplicar: onObjectiveChange })}
      >
        <Textarea
          value={objective}
          disabled={readOnly}
          onChange={(e) => onObjectiveChange(e.target.value)}
          rows={3}
          placeholder="Ex.: Quais arranjos institucionais e mecanismos de governança territorial estão documentados na literatura sobre APLs no Brasil e na América Latina?"
        />

      </CampoDoProtocolo>

      {/* ── S3: Decomposição estruturada da pergunta ──────────── */}
      <CampoDoProtocolo
        data-trilho-target="protocol-framework"
        icone={<Layers size={20} className="icon-accent" aria-hidden="true" />}
        titulo={`Decomposição Estruturada da Pergunta (${frameworkType})`}
        etiquetaItem="S3"
        secao="NÚCLEO / FRAMEWORK"
        ajuda={AJUDA.framework}
        guia={apoio?.montarGuia?.('question_framework', 's3')}
      >
        <div className="protocol-field__actions protocol-field__actions--fim">
          <span className="protocol-inline-label">Framework</span>
          <Select
            value={frameworkType}
            disabled={readOnly}
            sizeVariant="sm"
            onChange={(e) => onFrameworkTypeChange(e.target.value)}
            aria-label="Framework de estruturação da pergunta"
          >
            <option value="PCC">PCC — escopo e mapeamento</option>
            <option value="PICO">PICO — efetividade e intervenção</option>
            <option value="PECO">PECO — exposição e observacional</option>
            <option value="SPIDER">SPIDER — qualitativa e mista</option>
            <option value="CIMO">CIMO — gestão e políticas</option>
          </Select>
        </div>

        <div className="protocol-grid protocol-grid--3">
          {componentesDoFramework.map((c) => (
            <FormGroup
              key={c.chave}
              label={
                <span className="protocol-component-label">
                  <span>{c.rotulo}</span>
                  {assistir(
                    c.fieldId,
                    c.rotulo,
                    frameworkComponents[c.chave] || '',
                    `Descreva de forma sucinta o componente "${c.rotulo}" da pergunta, em termos que possam virar termos de busca.`,
                    (t) => onFrameworkComponentChange(c.chave, t)
                  )}
                </span>
              }
            >
              <Input
                type="text"
                value={frameworkComponents[c.chave] || ''}
                disabled={readOnly}
                onChange={(e) => onFrameworkComponentChange(c.chave, e.target.value)}
                placeholder={c.exemplo}
              />
            </FormGroup>
          ))}
        </div>
      </CampoDoProtocolo>

      {/* ── S4: Desenho da revisão ────────────────────────────── */}
      <CampoDoProtocolo
        data-trilho-target="protocol-design"
        icone={<CheckSquare size={20} className="icon-accent" aria-hidden="true" />}
        titulo="Desenho Metodológico da Revisão"
        etiquetaItem={`S4 · ${currentDesign.badge}`}
        secao="NÚCLEO / DESENHO"
        ajuda={`${AJUDA.desenho} ${currentDesign.registryEligibility}.`}
        guia={apoio?.montarGuia?.('review_design', 's4')}
      >

        <div className="protocol-design-grid">
          {REVIEW_DESIGNS_CATALOG.map((d) => (
            <button
              key={d.id}
              type="button"
              disabled={readOnly}
              aria-pressed={reviewDesign === d.id}
              onClick={() => onReviewDesignChange(d.id)}
              className={`protocol-design-option ${reviewDesign === d.id ? 'is-selected' : ''}`}
            >
              <span className="protocol-design-option__name">
                {d.id} · {d.name}
              </span>
              <p className="protocol-design-option__when">{d.whenToUse}</p>
            </button>
          ))}
        </div>
      </CampoDoProtocolo>

      {/* ── S5 e S8: Bases-alvo e recorte ─────────────────────── */}
      <CampoDoProtocolo
        data-trilho-target="protocol-databases"
        icone={<Database size={20} className="icon-accent" aria-hidden="true" />}
        titulo="Bases-alvo e Recorte da Busca"
        etiquetaItem="S5 · S8"
        secao="NÚCLEO / FONTES"
        ajuda={AJUDA.recorte}
        guia={apoio?.montarGuia?.('search_filters', 's5')}
      >

        <div className="protocol-grid protocol-grid--2">
          <div>
            <span className="protocol-inline-label">Bases selecionadas para coleta</span>
            <div className="protocol-source-list">
              {AVAILABLE_DATABASES.map((db) => {
                const marcada = searchFilters.target_databases?.includes(db.id) || false
                return (
                  <label key={db.id} className={`protocol-source ${marcada ? 'is-selected' : ''}`}>
                    <span className="protocol-source__label">
                      <input
                        type="checkbox"
                        checked={marcada}
                        disabled={readOnly}
                        onChange={(e) => {
                          const atuais = searchFilters.target_databases || []
                          const proximas = e.target.checked
                            ? [...atuais, db.id]
                            : atuais.filter((x) => x !== db.id)
                          onSearchFiltersChange({ ...searchFilters, target_databases: proximas })
                        }}
                      />
                      <span>{db.name}</span>
                    </span>
                    <span className="protocol-source__badge">{db.badge}</span>
                  </label>
                )
              })}
            </div>
          </div>

          <div className="protocol-field__body">
            <div className="protocol-grid protocol-grid--2">
              <FormGroup label="Ano inicial">
                <Input
                  type="number"
                  value={searchFilters.year_start || ''}
                  disabled={readOnly}
                  onChange={(e) =>
                    onSearchFiltersChange({
                      ...searchFilters,
                      year_start: e.target.value ? parseInt(e.target.value, 10) : null,
                    })
                  }
                  placeholder="Ex.: 2015"
                />
              </FormGroup>
              <FormGroup label="Ano final">
                <Input
                  type="number"
                  value={searchFilters.year_end || ''}
                  disabled={readOnly}
                  onChange={(e) =>
                    onSearchFiltersChange({
                      ...searchFilters,
                      year_end: e.target.value ? parseInt(e.target.value, 10) : null,
                    })
                  }
                  placeholder="Ex.: 2026"
                />
              </FormGroup>
            </div>

            <div>
              <span className="protocol-inline-label">Idiomas</span>
              <div className="protocol-toggle-row">
                {AVAILABLE_LANGUAGES.map((l) => {
                  const marcado = searchFilters.languages?.includes(l.code) || false
                  return (
                    <button
                      key={l.code}
                      type="button"
                      disabled={readOnly}
                      aria-pressed={marcado}
                      onClick={() => {
                        const atuais = searchFilters.languages || []
                        const proximos = marcado
                          ? atuais.filter((x) => x !== l.code)
                          : [...atuais, l.code]
                        onSearchFiltersChange({ ...searchFilters, languages: proximos })
                      }}
                      className={`protocol-toggle ${marcado ? 'is-selected' : ''}`}
                    >
                      <span aria-hidden="true">{l.flag}</span>
                      <span>{l.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <span className="protocol-inline-label">Tipos documentais</span>
              <div className="protocol-toggle-row">
                {AVAILABLE_DOC_TYPES.map((t) => {
                  const marcado = searchFilters.document_types?.includes(t.id) || false
                  return (
                    <button
                      key={t.id}
                      type="button"
                      disabled={readOnly}
                      aria-pressed={marcado}
                      onClick={() => {
                        const atuais = searchFilters.document_types || []
                        const proximos = marcado
                          ? atuais.filter((x) => x !== t.id)
                          : [...atuais, t.id]
                        onSearchFiltersChange({ ...searchFilters, document_types: proximos })
                      }}
                      className={`protocol-toggle ${marcado ? 'is-selected' : ''}`}
                    >
                      {t.label}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </CampoDoProtocolo>

      {/* ── S6 e S7: Estratégia canônica e adaptação por base ──── */}
      <CampoDoProtocolo
        data-trilho-target="protocol-strategy"
        icone={<Search size={20} className="icon-accent" aria-hidden="true" />}
        titulo="Estratégia de Busca Canônica e Adaptação por Base"
        etiquetaItem="S6 · S7"
        secao="NÚCLEO / ESTRATÉGIA"
        ajuda={AJUDA.estrategia}
        guia={apoio?.montarGuia?.('search_strategy', 's6')}
      >
        <SearchStrategyStudio
          projectId={projectId}
          strategy={searchStrategy}
          searchFilters={searchFilters}
          onStrategySaved={onSearchStrategySaved}
          readOnly={readOnly}
        />

        {/* ── Pares de Descritores para a Coleta Multibase ──── */}
        {descriptors && onDescriptorsChange && (
          <div className="protocol-descriptors-sync-box" style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-border)' }}>
            <div className="protocol-field__head">
              <div>
                <span className="protocol-inline-label" style={{ fontWeight: 'bold', fontSize: 'var(--font-size-sm)' }}>
                  Pares de Descritores para Coleta Multibase (BDTD / SciELO / Scopus / OpenAlex / PubMed)
                </span>
                <p className="protocol-field-hint" style={{ margin: 'var(--space-1) 0 var(--space-2)' }}>
                  Formulação em <strong>pares de termos com AND</strong> (máximo 2 termos por linha, ex.: <code>"termo 1" AND "termo 2"</code>), enviados aos coletores das bases.
                </p>
              </div>
              {!readOnly && searchStrategy?.blocks && (
                <Button
                  size="xs"
                  variant="outline"
                  type="button"
                  onClick={handleSyncFromStrategy}
                  title="Gerar pares automaticamente a partir dos blocos conceituais acima"
                >
                  <Sparkles size={13} className="icon-accent" />
                  <span>Sincronizar dos Blocos</span>
                </Button>
              )}
            </div>

            {/* Language Tabs */}
            <div className="lang-tabs" style={{ marginBottom: 'var(--space-2)' }}>
              <button
                type="button"
                className={`lang-tab ${activeLangTab === 'pt' ? 'active' : ''}`}
                onClick={() => setActiveLangTab('pt')}
              >
                🇧🇷 Português ({(descriptors.pt || []).filter(Boolean).length})
              </button>
              <button
                type="button"
                className={`lang-tab ${activeLangTab === 'en' ? 'active' : ''}`}
                onClick={() => setActiveLangTab('en')}
              >
                🇺🇸 Inglês ({(descriptors.en || []).filter(Boolean).length})
              </button>
              <button
                type="button"
                className={`lang-tab ${activeLangTab === 'es' ? 'active' : ''}`}
                onClick={() => setActiveLangTab('es')}
              >
                🇪🇸 Espanhol ({(descriptors.es || []).filter(Boolean).length})
              </button>
            </div>

            <div className="descriptors-list">
              {(descriptors[activeLangTab] || ['']).map((desc, idx) => (
                <div key={idx} className="descriptor-row">
                  <span className="descriptor-index">#{idx + 1}</span>
                  <input
                    type="text"
                    className="descriptor-input"
                    placeholder='Ex: "desenvolvimento regional" AND "arranjos produtivos"'
                    value={desc}
                    disabled={readOnly}
                    onChange={(e) => {
                      const currentList = [...(descriptors[activeLangTab] || [''])]
                      currentList[idx] = e.target.value
                      onDescriptorsChange({
                        ...descriptors,
                        [activeLangTab]: currentList,
                      })
                    }}
                  />
                  {!readOnly && (
                    <button
                      type="button"
                      className="btn-icon danger"
                      title="Remover par de descritores"
                      onClick={() => {
                        const currentList = (descriptors[activeLangTab] || ['']).filter((_, i) => i !== idx)
                        onDescriptorsChange({
                          ...descriptors,
                          [activeLangTab]: currentList.length > 0 ? currentList : [''],
                        })
                      }}
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              ))}

              {!readOnly && (
                <button
                  type="button"
                  className="btn-add-descriptor"
                  onClick={() => {
                    const currentList = [...(descriptors[activeLangTab] || [''])]
                    currentList.push('')
                    onDescriptorsChange({
                      ...descriptors,
                      [activeLangTab]: currentList,
                    })
                  }}
                >
                  <Plus size={14} /> Adicionar Par de Descritores ({(descriptors[activeLangTab] || []).length})
                </button>
              )}
            </div>
          </div>
        )}
      </CampoDoProtocolo>

      {/* ── S9: Métodos complementares ────────────────────────── */}
      <CampoDoProtocolo
        data-trilho-target="protocol-sources"
        icone={<Globe size={20} className="icon-accent" aria-hidden="true" />}
        titulo="Métodos Complementares e Literatura Cinzenta"
        etiquetaItem="S9"
        secao="NÚCLEO / FONTES"
        ajuda={apoio?.ajuda?.('info_sources', AJUDA.complementares) ?? AJUDA.complementares}
        assistencia={assistir(
          'info_sources',
          'Métodos Complementares e Literatura Cinzenta',
          infoSources,
          'Descreva busca manual em anais e portais, repositórios de teses, citação regressiva e progressiva e contato com autores.',
          onInfoSourcesChange
        )}
        guia={apoio?.montarGuia?.('info_sources', 's9', { valorAtual: infoSources, aplicar: onInfoSourcesChange })}
      >
        <Textarea
          value={infoSources}
          disabled={readOnly}
          onChange={(e) => onInfoSourcesChange(e.target.value)}
          rows={2}
          placeholder="Ex.: consulta complementar aos anais dos encontros da ANPUR, repositórios do IPEA e busca reversa nas referências dos estudos incluídos…"
        />
      </CampoDoProtocolo>

      {/* ── S10: Critérios de elegibilidade ───────────────────── */}
      <CampoDoProtocolo
        data-trilho-target="protocol-criteria"
        icone={<Filter size={20} className="icon-accent" aria-hidden="true" />}
        titulo="Critérios de Elegibilidade"
        etiquetaItem="S10"
        secao="NÚCLEO / ELEGIBILIDADE"
        ajuda={apoio?.ajuda?.('criteria', AJUDA.criterios) ?? AJUDA.criterios}
        assistencia={
          <AIAssistButton
            fieldId="criteria"
            fieldLabel="Critérios de Elegibilidade"
            currentValue={criteria.map((c) => (c.is_exclusion ? 'EXC: ' : 'INC: ') + c.text).join('\n')}
            fieldGuidelines="Gere critérios de inclusão (prefixados com 'INC: ') e de exclusão (prefixados com 'EXC: '), um por linha, coerentes com a pergunta e o recorte declarados."
            projectTitle={apoio?.projeto?.titulo}
            methodology={apoio?.projeto?.metodologia}
            projectContext={apoio?.contexto?.('criteria')}
            onApply={aplicarCriteriosDeTexto}
          />
        }
        guia={apoio?.montarGuia?.('criteria', 's10')}
      >
        <div className="protocol-field__head">
          {!readOnly && (
            <div className="protocol-field__actions">
              <Button size="xs" variant="outline" onClick={() => handleAddCriterion(false)}>
                <Plus size={12} />
                <span>Inclusão</span>
              </Button>
              <Button size="xs" variant="outline" onClick={() => handleAddCriterion(true)}>
                <Plus size={12} />
                <span>Exclusão</span>
              </Button>
            </div>
          )}
        </div>
        <p className="protocol-field__hint">
          Cada critério declara em que momento se aplica — título e resumo, texto completo, ou ambos.
          É o que torna o motivo de exclusão auditável no fluxograma PRISMA.
        </p>

        {criteria.length === 0 ? (
          <p className="protocol-empty-note">
            Nenhum critério declarado. O portão da Triagem exige ao menos um critério de inclusão.
          </p>
        ) : (
          <div className="protocol-row-list">
            {criteria.map((c, idx) => (
              <div
                key={c.id || idx}
                className={`protocol-row ${c.is_exclusion ? 'protocol-row--exclusao' : 'protocol-row--inclusao'}`}
              >
                <span className="protocol-row__tag">{c.is_exclusion ? 'Exclusão' : 'Inclusão'}</span>

                <div className="protocol-row__field">
                  <Input
                    type="text"
                    value={c.text}
                    disabled={readOnly}
                    sizeVariant="sm"
                    onChange={(e) => handleUpdateCriterion(idx, { text: e.target.value })}
                    placeholder="Descrição clara do critério de elegibilidade…"
                    aria-label={`Texto do critério ${idx + 1}`}
                  />
                </div>

                <div className="protocol-row__controls">
                  <Select
                    value={c.dimension || 'outro'}
                    disabled={readOnly}
                    sizeVariant="sm"
                    onChange={(e) => handleUpdateCriterion(idx, { dimension: e.target.value as any })}
                    aria-label={`Dimensão do critério ${idx + 1}`}
                  >
                    <option value="populacao">População</option>
                    <option value="desenho">Desenho</option>
                    <option value="periodo">Período</option>
                    <option value="idioma">Idioma</option>
                    <option value="tipo_doc">Tipo documental</option>
                    <option value="contexto">Contexto</option>
                    <option value="outro">Outro</option>
                  </Select>

                  <Select
                    value={c.applies_at || 'ambos'}
                    disabled={readOnly}
                    sizeVariant="sm"
                    onChange={(e) => handleUpdateCriterion(idx, { applies_at: e.target.value as any })}
                    aria-label={`Momento de aplicação do critério ${idx + 1}`}
                  >
                    <option value="titulo_resumo">Título e resumo</option>
                    <option value="texto_completo">Texto completo</option>
                    <option value="ambos">Ambos</option>
                  </Select>

                  {!readOnly && (
                    <button
                      type="button"
                      onClick={() => handleRemoveCriterion(idx)}
                      className="protocol-row__remove"
                      aria-label={`Remover critério ${idx + 1}`}
                      title="Remover critério"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CampoDoProtocolo>

      {/* ── S11: Perguntas de extração (decisão D-C) ──────────── */}
      <CampoDoProtocolo
        data-trilho-target="protocol-questions"
        icone={<HelpCircle size={20} className="icon-accent" aria-hidden="true" />}
        titulo="Perguntas de Extração de Dados"
        etiquetaItem="S11"
        secao="NÚCLEO / VARIÁVEIS"
        ajuda={ANCORAGEM_NORMATIVA.perguntasDeExtracaoNoNucleo}
        assistencia={
          <AIAssistButton
            fieldId="questions"
            fieldLabel="Perguntas de Extração de Dados"
            currentValue={extractionQuestions.map((q) => q.text).join('\n')}
            fieldGuidelines="Gere perguntas de extração, uma por linha, cada uma cobrindo uma única variável, coerentes com a pergunta da revisão e com o desenho escolhido."
            projectTitle={apoio?.projeto?.titulo}
            methodology={apoio?.projeto?.metodologia}
            projectContext={apoio?.contexto?.('questions')}
            onApply={aplicarPerguntasDeTexto}
          />
        }
        guia={apoio?.montarGuia?.('extraction_questions', 's11')}
      >
        <div className="protocol-field__head">
          {!readOnly && (
            <div className="protocol-field__actions">
              <Button
                size="xs"
                variant="outline"
                onClick={handleApplySuggestedQuestions}
                title="Carregar o conjunto sugerido para o desenho ativo"
              >
                <Sparkles size={12} />
                <span>Sugeridas pelo desenho</span>
              </Button>
              <Button size="xs" variant="secondary" onClick={handleAddQuestion}>
                <Plus size={12} />
                <span>Pergunta</span>
              </Button>
            </div>
          )}
        </div>
        <p className="protocol-field__hint">
          {ANCORAGEM_NORMATIVA.perguntasDeExtracaoNoNucleo}
        </p>

        {extractionQuestions.length === 0 ? (
          <p className="protocol-empty-note">
            Nenhuma pergunta declarada. Use “Sugeridas pelo desenho” para partir do conjunto de{' '}
            {currentDesign.id} e ajustar.
          </p>
        ) : (
          <div className="protocol-row-list">
            {extractionQuestions.map((q, idx) => (
              <div key={q.id || idx} className="protocol-row">
                <span className="protocol-row__index">Q{idx + 1}</span>

                <div className="protocol-row__field">
                  <Input
                    type="text"
                    value={q.text}
                    disabled={readOnly}
                    sizeVariant="sm"
                    onChange={(e) => handleUpdateQuestion(idx, { text: e.target.value })}
                    placeholder="Ex.: qual o referencial teórico e a metodologia empírica utilizada?"
                    aria-label={`Texto da pergunta ${idx + 1}`}
                  />
                </div>

                <div className="protocol-row__controls">
                  <Select
                    value={q.answer_type || 'texto'}
                    disabled={readOnly}
                    sizeVariant="sm"
                    onChange={(e) => handleUpdateQuestion(idx, { answer_type: e.target.value as any })}
                    aria-label={`Tipo de resposta da pergunta ${idx + 1}`}
                  >
                    <option value="texto">Texto livre</option>
                    <option value="numero">Número</option>
                    <option value="categoria">Escolha única</option>
                    <option value="multipla">Múltipla escolha</option>
                    <option value="booleano">Sim / Não</option>
                  </Select>

                  <label className="protocol-row__check">
                    <input
                      type="checkbox"
                      checked={q.required || false}
                      disabled={readOnly}
                      onChange={(e) => handleUpdateQuestion(idx, { required: e.target.checked })}
                    />
                    <span>Obrigatória</span>
                  </label>

                  {!readOnly && (
                    <button
                      type="button"
                      onClick={() => handleRemoveQuestion(idx)}
                      className="protocol-row__remove"
                      aria-label={`Remover pergunta ${idx + 1}`}
                      title="Remover pergunta"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CampoDoProtocolo>

      {/* ── S12, S13 e S14: Registro da Execução e Deduplicação (Doc 45 §8.2) ───────────────────────── */}
      <div className="protocol-field-trio">
        {/* S12: Data e hora de cada busca */}
        <CampoDoProtocolo
          compact
          icone={<Clock size={18} className="icon-accent" aria-hidden="true" />}
          titulo="Data e Hora de Cada Busca"
          etiquetaItem="S12 · 🔒 automático"
          secao="NÚCLEO / EXECUÇÃO"
          ajuda={AJUDA.execucaoData}
          guia={apoio?.montarGuia?.('registro_execucao', 's12')}
        >
          {searchExecutions && searchExecutions.length > 0 ? (
            <div className="protocol-execution-list">
              {searchExecutions.map((exec, i) => (
                <div key={exec.id || i} className="protocol-execution-item">
                  <span className="protocol-execution-db">{exec.database}:</span>
                  <span className="protocol-execution-val">
                    {exec.executed_at ? new Date(exec.executed_at).toLocaleString() : 'Pendente'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="protocol-auto-lock-box">
              <span className="protocol-auto-lock-text">
                🔒 Preenchido automaticamente pelo sistema no momento em que a coleta for disparada em cada base cadastrada.
              </span>
            </div>
          )}
        </CampoDoProtocolo>

        {/* S13: Nº de registros por base */}
        <CampoDoProtocolo
          compact
          icone={<Layers size={18} className="icon-accent" aria-hidden="true" />}
          titulo="Nº de Registros por Base"
          etiquetaItem="S13 · 🔒 automático"
          secao="NÚCLEO / EXECUÇÃO"
          ajuda={AJUDA.execucaoVolume}
          guia={apoio?.montarGuia?.('registro_execucao', 's13')}
        >
          {searchExecutions && searchExecutions.length > 0 ? (
            <div className="protocol-execution-list">
              {searchExecutions.map((exec, i) => (
                <div key={exec.id || i} className="protocol-execution-item">
                  <span className="protocol-execution-db">{exec.database}:</span>
                  <span className="protocol-execution-val">
                    <strong>{exec.records_returned}</strong> brutos ({exec.records_after_dedup} pós-dedup)
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="protocol-auto-lock-box">
              <span className="protocol-auto-lock-text">
                🔒 Preenchido automaticamente pelo sistema com os totais de registros brutos retornados por cada base após a coleta.
              </span>
            </div>
          )}
        </CampoDoProtocolo>

        {/* S14: Método de deduplicação */}
        <CampoDoProtocolo
          compact
          icone={<Copy size={18} className="icon-accent" aria-hidden="true" />}
          titulo="Método de Deduplicação"
          etiquetaItem="S14 · 🔒 auto + notas"
          secao="NÚCLEO / TRATAMENTO"
          ajuda={AJUDA.deduplicacao}
          assistencia={assistir(
            'deduplication',
            'Notas de Deduplicação',
            dedupNotes,
            'Descreva a deduplicação manual complementar, softwares usados e a conferência humana dos pares sinalizados.',
            onDedupNotesChange
          )}
          guia={apoio?.montarGuia?.('deduplication', 's14', { valorAtual: dedupNotes, aplicar: onDedupNotesChange })}
        >
          <div className="protocol-dedup-badge-info">
            Algoritmo Revsist: correspondência exata por DOI e título normalizado, mais similaridade de Levenshtein (limiar 90%) em títulos e autores.
          </div>
          <Textarea
            value={dedupNotes}
            disabled={readOnly}
            onChange={(e) => onDedupNotesChange(e.target.value)}
            rows={2}
            placeholder="Notas metodológicas adicionais sobre deduplicação manual ou softwares complementares…"
          />
        </CampoDoProtocolo>
      </div>
    </div>
  )
}
