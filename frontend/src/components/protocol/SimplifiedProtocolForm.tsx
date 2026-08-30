import React from 'react'
import { Plus, Trash2, Sparkles, Lock, Clock, Database, Layers } from 'lucide-react'
import type { Criterion, ExtractionQuestion, SearchFilters, SearchStrategy, SearchExecution } from '@/types/api'
import { Card, Button, Badge, FormGroup, Input, Textarea, Select } from '@/components/ui'
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
  // S6
  searchStrategy?: SearchStrategy | null
  onSearchStrategySaved?: (strat: SearchStrategy) => void
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
  infoSources,
  onInfoSourcesChange,
  criteria,
  onCriteriaChange,
  extractionQuestions,
  onExtractionQuestionsChange,
  searchExecutions = [],
  dedupNotes,
  onDedupNotesChange,
  readOnly = false,
}: SimplifiedProtocolFormProps): JSX.Element {
  const currentDesign = REVIEW_DESIGNS_CATALOG.find((d) => d.id === reviewDesign) || REVIEW_DESIGNS_CATALOG[3] // D4 default

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
      <Card className="protocol-field" surface="secundaria" relief="elevado" data-trilho-target="protocol-title">
        <div className="protocol-field__head">
          <div className="protocol-field__title">
            <span className="protocol-field__num">S1</span>
            <h4>Título provisório do estudo</h4>
          </div>
        </div>
        <p className="protocol-field__hint">
          Declare o objeto de investigação, o desenho metodológico e o recorte pretendido.
        </p>
        <Input
          type="text"
          value={title}
          disabled={readOnly}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="Ex.: Políticas públicas territoriais e inovação em arranjos produtivos locais — protocolo de revisão de escopo"
        />
      </Card>

      {/* ── S2 e S3: Pergunta e framework ─────────────────────── */}
      <Card className="protocol-field" surface="secundaria" relief="elevado" data-trilho-target="protocol-objective">
        <div className="protocol-field__head">
          <div className="protocol-field__title">
            <span className="protocol-field__num">S2</span>
            <h4>Pergunta principal e objetivo geral</h4>
          </div>
        </div>
        <p className="protocol-field__hint">
          Formule a pergunta central e a finalidade a priori da revisão.
        </p>
        <Textarea
          value={objective}
          disabled={readOnly}
          onChange={(e) => onObjectiveChange(e.target.value)}
          rows={3}
          placeholder="Ex.: Quais arranjos institucionais e mecanismos de governança territorial estão documentados na literatura sobre APLs no Brasil e na América Latina?"
        />

        <div className="protocol-field__subsection" data-trilho-target="protocol-framework">
          <div className="protocol-field__head">
            <div className="protocol-field__title">
              <span className="protocol-field__num">S3</span>
              <h4>Decomposição estruturada da pergunta</h4>
            </div>
            <div className="protocol-field__actions">
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
          </div>

          <div className="protocol-grid protocol-grid--3">
            {frameworkType === 'PCC' ? (
              <>
                <FormGroup label="População / Participantes (P)">
                  <Input
                    type="text"
                    value={frameworkComponents.population || ''}
                    disabled={readOnly}
                    onChange={(e) => onFrameworkComponentChange('population', e.target.value)}
                    placeholder="Ex.: APLs, cooperativas, governanças locais"
                  />
                </FormGroup>
                <FormGroup label="Conceito central (C)">
                  <Input
                    type="text"
                    value={frameworkComponents.intervention || frameworkComponents.concept || ''}
                    disabled={readOnly}
                    onChange={(e) => onFrameworkComponentChange('intervention', e.target.value)}
                    placeholder="Ex.: inovação socioeconômica, governança"
                  />
                </FormGroup>
                <FormGroup label="Contexto / Cenário (C)">
                  <Input
                    type="text"
                    value={frameworkComponents.comparison || frameworkComponents.context || ''}
                    disabled={readOnly}
                    onChange={(e) => onFrameworkComponentChange('comparison', e.target.value)}
                    placeholder="Ex.: Brasil, América Latina, regiões periféricas"
                  />
                </FormGroup>
              </>
            ) : (
              <>
                <FormGroup label="População (P)">
                  <Input
                    type="text"
                    value={frameworkComponents.population || ''}
                    disabled={readOnly}
                    onChange={(e) => onFrameworkComponentChange('population', e.target.value)}
                    placeholder="População-alvo…"
                  />
                </FormGroup>
                <FormGroup label="Intervenção / Exposição (I/E)">
                  <Input
                    type="text"
                    value={frameworkComponents.intervention || ''}
                    disabled={readOnly}
                    onChange={(e) => onFrameworkComponentChange('intervention', e.target.value)}
                    placeholder="Intervenção ou política…"
                  />
                </FormGroup>
                <FormGroup label="Comparador / Controle (C)">
                  <Input
                    type="text"
                    value={frameworkComponents.comparison || ''}
                    disabled={readOnly}
                    onChange={(e) => onFrameworkComponentChange('comparison', e.target.value)}
                    placeholder="Grupo de comparação…"
                  />
                </FormGroup>
                <FormGroup label="Desfecho / Resultado (O)">
                  <Input
                    type="text"
                    value={frameworkComponents.outcome || ''}
                    disabled={readOnly}
                    onChange={(e) => onFrameworkComponentChange('outcome', e.target.value)}
                    placeholder="Impacto ou resultado esperado…"
                  />
                </FormGroup>
              </>
            )}
          </div>
        </div>
      </Card>

      {/* ── S4: Desenho da revisão ────────────────────────────── */}
      <Card className="protocol-field" surface="secundaria" relief="elevado" data-trilho-target="protocol-design">
        <div className="protocol-field__head">
          <div className="protocol-field__title">
            <span className="protocol-field__num">S4</span>
            <h4>Desenho metodológico da revisão</h4>
          </div>
          <Badge variant="brand" size="sm">{currentDesign.badge}</Badge>
        </div>
        <p className="protocol-field__hint">
          O desenho define o pipeline, o framework sugerido, a diretriz de relato e a obrigatoriedade
          de apreciação crítica. {currentDesign.registryEligibility}.
        </p>

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
      </Card>

      {/* ── S5 e S8: Bases-alvo e recorte ─────────────────────── */}
      <Card className="protocol-field" surface="secundaria" relief="elevado" data-trilho-target="protocol-databases">
        <div className="protocol-field__head">
          <div className="protocol-field__title">
            <span className="protocol-field__num">S5</span>
            <h4>Bases-alvo e recorte da busca</h4>
          </div>
        </div>
        <p className="protocol-field__hint">
          A escolha das bases e os limites aplicados são itens 1, 2 e 6 do PRISMA-S — entram no
          Registro de Busca como a coluna “configurado”.
        </p>

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
      </Card>

      {/* ── S6 e S7: Estratégia canônica e adaptação por base ──── */}
      <Card className="protocol-field" surface="secundaria" relief="elevado">
        <div className="protocol-field__head">
          <div className="protocol-field__title">
            <span className="protocol-field__num">S6</span>
            <h4>Estratégia de busca canônica e adaptação por base</h4>
          </div>
        </div>
        <p className="protocol-field__hint">
          Blocos de conceito combinados uma única vez; cada base recebe a tradução do seu adaptador.
          A revisão PRESS confere a estratégia antes de executá-la.
        </p>
        <SearchStrategyStudio
          projectId={projectId}
          strategy={searchStrategy}
          searchFilters={searchFilters}
          onStrategySaved={onSearchStrategySaved}
          readOnly={readOnly}
        />
      </Card>

      {/* ── S9: Métodos complementares ────────────────────────── */}
      <Card className="protocol-field" surface="secundaria" relief="elevado">
        <div className="protocol-field__head">
          <div className="protocol-field__title">
            <span className="protocol-field__num">S9</span>
            <h4>Métodos complementares e literatura cinzenta</h4>
          </div>
        </div>
        <p className="protocol-field__hint">
          Busca em anais, portais governamentais, repositórios de preprints, citação regressiva e
          progressiva, contato com autores (PRISMA-S, itens 7 a 10).
        </p>
        <Textarea
          value={infoSources}
          disabled={readOnly}
          onChange={(e) => onInfoSourcesChange(e.target.value)}
          rows={2}
          placeholder="Ex.: consulta complementar aos anais dos encontros da ANPUR, repositórios do IPEA e busca reversa nas referências dos estudos incluídos…"
        />
      </Card>

      {/* ── S10: Critérios de elegibilidade ───────────────────── */}
      <Card className="protocol-field" surface="secundaria" relief="elevado" data-trilho-target="protocol-criteria">
        <div className="protocol-field__head">
          <div className="protocol-field__title">
            <span className="protocol-field__num">S10</span>
            <h4>Critérios de elegibilidade</h4>
          </div>
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
      </Card>

      {/* ── S11: Perguntas de extração (decisão D-C) ──────────── */}
      <Card className="protocol-field" surface="secundaria" relief="elevado" data-trilho-target="protocol-questions">
        <div className="protocol-field__head">
          <div className="protocol-field__title">
            <span className="protocol-field__num">S11</span>
            <h4>Perguntas de extração de dados</h4>
          </div>
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
      </Card>

      {/* ── S12, S13 e S14: Registro da Execução e Deduplicação (Doc 45 §8.2) ───────────────────────── */}
      <div className="protocol-field-trio">
        {/* S12: Data e hora de cada busca */}
        <Card className="protocol-field" surface="secundaria" relief="elevado" compact>
          <div className="protocol-field__title">
            <span className="protocol-field__num">S12</span>
            <h4>Data e hora de cada busca</h4>
            <span className="protocol-field__badge-lock">🔒 Automático</span>
          </div>
          <p className="protocol-field__hint">PRISMA-S i14 / PRISMA 2020 i7 — registrado na execução.</p>
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
        </Card>

        {/* S13: Nº de registros por base */}
        <Card className="protocol-field" surface="secundaria" relief="elevado" compact>
          <div className="protocol-field__title">
            <span className="protocol-field__num">S13</span>
            <h4>Nº de registros por base</h4>
            <span className="protocol-field__badge-lock">🔒 Automático</span>
          </div>
          <p className="protocol-field__hint">PRISMA 2020 i16a — registrado no retorno da busca.</p>
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
        </Card>

        {/* S14: Método de deduplicação */}
        <Card className="protocol-field" surface="secundaria" relief="elevado" compact>
          <div className="protocol-field__title">
            <span className="protocol-field__num">S14</span>
            <h4>Método de deduplicação</h4>
            <span className="protocol-field__badge-lock">🔒 Auto + Notas</span>
          </div>
          <p className="protocol-field__hint">PRISMA-S i15 — algoritmo padrão + notas do pesquisador.</p>
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
        </Card>
      </div>
    </div>
  )
}
