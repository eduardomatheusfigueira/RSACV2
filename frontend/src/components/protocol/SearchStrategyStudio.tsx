import React, { useState, useEffect } from 'react'
import {
  Search,
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Sparkles,
  Copy,
  Check,
  Layers,
} from 'lucide-react'
import type { SearchFilters, SearchStrategy, SearchStrategyBlock } from '@/types/api'
import { Button, Input, Dialog, DialogContent, DialogTitlebar, DialogBody, DialogFooter } from '@/components/ui'
import { api } from '@/api/client'
import { AIAssistButton } from '@/components/common/AIAssistButton'
import type { FerramentasDeApoio } from './apoioDoProtocolo'
import './ProtocolStudio.css'

/** Bases com adaptador declarado no backend (doc 45 §10.2). */
const BASES_TESTAVEIS = ['BDTD', 'SciELO', 'OpenAlex', 'Scopus', 'PubMed'] as const

interface SearchStrategyStudioProps {
  projectId: string
  strategy?: SearchStrategy | null
  /**
   * Recorte vigente do protocolo. O teste por base precisa dele: renderizar a
   * consulta com anos fixos mostraria uma string que NÃO é a que será executada,
   * e é justamente a correspondência entre configurado e executado que o
   * Registro de Busca (doc 45 §10.5) existe para provar.
   */
  searchFilters?: SearchFilters
  onStrategySaved?: (strat: SearchStrategy) => void
  /** Guia e assistência por campo (doc 45 §16.4). Ver `apoioDoProtocolo.ts`. */
  apoio?: FerramentasDeApoio
  readOnly?: boolean
}

export function SearchStrategyStudio({
  projectId,
  strategy,
  searchFilters,
  onStrategySaved,
  apoio,
  readOnly = false,
}: SearchStrategyStudioProps): JSX.Element {
  const [blocks, setBlocks] = useState<SearchStrategyBlock[]>(() => {
    if (strategy?.blocks && strategy.blocks.length > 0) {
      return strategy.blocks
    }
    /* Blocos vazios, e não termos de exemplo: o protocolo é do pesquisador, e
       um campo pré-preenchido com a pesquisa de outra pessoa entra no documento
       exportado como se tivesse sido escrito por ele. */
    return [
      { key: 'A', label: 'População / Fenômeno', terms: [''] },
      { key: 'B', label: 'Conceito / Intervenção', terms: [''] },
    ]
  })

  const [combination, setCombination] = useState(strategy?.combination || 'A AND B')
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [copied, setCopied] = useState(false)

  // Modais de Teste e PRESS
  const [testModalOpen, setTestModalOpen] = useState(false)
  const [testDb, setTestDb] = useState('BDTD')
  const [renderedResult, setRenderedResult] = useState<{
    database: string
    rendered_query: string
    adaptation_note: string
    is_decomposed?: boolean
    rendered_pairs?: string[]
  } | null>(null)
  const [renderLoading, setRenderLoading] = useState(false)

  const [pressModalOpen, setPressModalOpen] = useState(false)
  const [pressResult, setPressResult] = useState<{
    score_percentage: number
    domains: Array<{ domain: string; passed: boolean; message: string }>
  } | null>(null)
  const [pressLoading, setPressLoading] = useState(false)

  // Live Canonical Query Preview
  const generateLiveCanonicalQuery = () => {
    if (!blocks || blocks.length === 0) return ''
    const parts = blocks.map((b) => {
      const validTerms = b.terms
        .filter((t) => t.trim().length > 0)
        .map((t) => (t.includes(' ') && !t.startsWith('"') ? `"${t.trim()}"` : t.trim()))
      if (validTerms.length === 0) return ''
      return `(${validTerms.join(' OR ')})`
    }).filter(Boolean)

    return parts.join(' AND ')
  }

  const handleAddBlock = () => {
    const nextKey = String.fromCharCode(65 + blocks.length)
    const newBlocks = [...blocks, { key: nextKey, label: `Bloco ${nextKey}`, terms: [''] }]
    setBlocks(newBlocks)
    setCombination(newBlocks.map((b) => b.key).join(' AND '))
  }

  const handleRemoveBlock = (idx: number) => {
    const newBlocks = blocks.filter((_, i) => i !== idx)
    setBlocks(newBlocks)
    setCombination(newBlocks.map((b) => b.key).join(' AND '))
  }

  const handleBlockLabelChange = (idx: number, label: string) => {
    const newBlocks = [...blocks]
    newBlocks[idx].label = label
    setBlocks(newBlocks)
  }

  const handleAddTerm = (blockIdx: number) => {
    const newBlocks = [...blocks]
    newBlocks[blockIdx].terms.push('')
    setBlocks(newBlocks)
  }

  const handleTermChange = (blockIdx: number, termIdx: number, val: string) => {
    const newBlocks = [...blocks]
    newBlocks[blockIdx].terms[termIdx] = val
    setBlocks(newBlocks)
  }

  const handleRemoveTerm = (blockIdx: number, termIdx: number) => {
    const newBlocks = [...blocks]
    newBlocks[blockIdx].terms = newBlocks[blockIdx].terms.filter((_, i) => i !== termIdx)
    setBlocks(newBlocks)
  }

  const handleSaveStrategy = async () => {
    if (readOnly) return
    setSaving(true)
    try {
      const saved = await api.saveSearchStrategy(projectId, {
        kind: 'canonica',
        database: '',
        blocks,
        combination,
        target_fields: ['title', 'abstract', 'keywords'],
        limits: {},
        adaptation_note: 'Estratégia canônica principal elaborada no Estúdio.',
      })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
      if (onStrategySaved) onStrategySaved(saved)
    } catch (err) {
      console.error('Erro ao salvar estratégia canônica:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleTestDatabaseSyntax = async (targetDb: string) => {
    setTestDb(targetDb)
    setTestModalOpen(true)
    setRenderLoading(true)
    try {
      const res = await api.renderSearchStrategy(projectId, {
        database: targetDb,
        blocks,
        combination,
        limits: {
          year_start: searchFilters?.year_start ?? null,
          year_end: searchFilters?.year_end ?? null,
          languages: searchFilters?.languages ?? [],
          document_types: searchFilters?.document_types ?? [],
        },
      })
      setRenderedResult(res)
    } catch (err) {
      console.error('Erro ao renderizar busca por base:', err)
    } finally {
      setRenderLoading(false)
    }
  }

  const handleRunPressAudit = async () => {
    setPressModalOpen(true)
    setPressLoading(true)
    try {
      const res = await api.analyzePressReview(projectId, {
        blocks,
        combination,
      })
      setPressResult(res)
    } catch (err) {
      console.error('Erro na auditoria PRESS:', err)
    } finally {
      setPressLoading(false)
    }
  }

  /**
   * Substitui os termos de um bloco pelo que a assistência devolveu, um termo
   * por linha. Substitui em vez de acrescentar porque o pesquisador vê a lista
   * proposta antes de aplicar, e porque `AIAssistButton` já oferece desfazer.
   */
  const aplicarTermosSugeridos = (blockIdx: number, texto: string) => {
    const termos = texto
      .split('\n')
      .map((t) => t.replace(/^[-*\d.)\s]+/, '').trim())
      .filter(Boolean)
    if (termos.length === 0) return
    const novos = [...blocks]
    novos[blockIdx] = { ...novos[blockIdx], terms: termos }
    setBlocks(novos)
  }

  const consultaCanonica = generateLiveCanonicalQuery()

  const handleCopyQuery = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="search-strategy">
      <div className="search-strategy__head">
        <div>
          <h4>
            <Search size={15} />
            Estratégia canônica e blocos conceituais
          </h4>
          <p>
            Um bloco por conceito, sinônimos unidos por OR, blocos unidos por AND. Cada base recebe a
            tradução do seu adaptador (PRISMA-S, itens 3 e 4).
          </p>
        </div>

        <div className="search-strategy__actions">
          <Button variant="outline" size="sm" onClick={handleRunPressAudit} data-trilho-target="search-press-btn">
            <Sparkles size={13} />
            <span>Revisão PRESS</span>
          </Button>

          <Button variant="outline" size="sm" onClick={() => handleTestDatabaseSyntax(testDb)}>
            <FileCode size={13} />
            <span>Testar por base</span>
          </Button>

          {!readOnly && (
            <Button size="sm" onClick={handleSaveStrategy} disabled={saving}>
              {saveSuccess ? <CheckCircle2 size={13} /> : <Check size={13} />}
              <span>{saveSuccess ? 'Salva' : 'Salvar estratégia'}</span>
            </Button>
          )}
        </div>
      </div>

      <div className="search-strategy__blocks" data-trilho-target="search-blocks-container">
        {blocks.map((block, bIdx) => (
          <div key={block.key} className="strategy-block">
            <div className="strategy-block__head">
              <div className="strategy-block__identity">
                <span className="strategy-block__key">{block.key}</span>
                <Input
                  type="text"
                  value={block.label}
                  disabled={readOnly}
                  sizeVariant="sm"
                  onChange={(e) => handleBlockLabelChange(bIdx, e.target.value)}
                  placeholder="Nome do bloco…"
                  aria-label={`Rótulo do bloco ${block.key}`}
                />
              </div>

              {!readOnly && blocks.length > 1 && (
                <button
                  type="button"
                  onClick={() => handleRemoveBlock(bIdx)}
                  className="protocol-row__remove"
                  title="Remover bloco"
                  aria-label={`Remover bloco ${block.key}`}
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>

            <div className="strategy-block__terms">
              <div className="strategy-block__terms-head">
                <span className="strategy-block__terms-label">Termos e sinônimos (OR)</span>
                {!readOnly && (
                  <AIAssistButton
                    fieldId={`search_block_${block.key}`}
                    fieldLabel={`Sinônimos do bloco ${block.key} — ${block.label}`}
                    currentValue={block.terms.filter(Boolean).join('\n')}
                    fieldGuidelines={`Liste termos de busca para o conceito "${block.label}", um por linha, sem numeração e sem operadores. Inclua sinônimos, variantes de grafia, plurais, siglas por extenso e as traduções em inglês e espanhol que a literatura da área efetivamente usa.`}
                    projectTitle={apoio?.projeto?.titulo}
                    methodology={apoio?.projeto?.metodologia}
                    projectContext={apoio?.contexto?.('search_strategy')}
                    onApply={(texto) => aplicarTermosSugeridos(bIdx, texto)}
                    compact
                  />
                )}
              </div>

              {block.terms.map((term, tIdx) => (
                <div key={tIdx} className="strategy-term">
                  <Input
                    type="text"
                    value={term}
                    disabled={readOnly}
                    sizeVariant="sm"
                    onChange={(e) => handleTermChange(bIdx, tIdx, e.target.value)}
                    placeholder="Ex.: inovação regional"
                    aria-label={`Termo ${tIdx + 1} do bloco ${block.key}`}
                  />
                  {!readOnly && block.terms.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveTerm(bIdx, tIdx)}
                      className="protocol-row__remove"
                      title="Remover termo"
                      aria-label={`Remover termo ${tIdx + 1} do bloco ${block.key}`}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              ))}

              {!readOnly && (
                <button
                  type="button"
                  onClick={() => handleAddTerm(bIdx)}
                  className="strategy-block__add-term"
                >
                  <Plus size={12} />
                  <span>Adicionar sinônimo (OR)</span>
                </button>
              )}
            </div>
          </div>
        ))}

        {!readOnly && blocks.length < 6 && (
          <button type="button" onClick={handleAddBlock} className="strategy-block--add">
            <Plus size={18} />
            <span>Adicionar bloco conceitual (AND)</span>
          </button>
        )}
      </div>

      <div className="strategy-preview" data-trilho-target="search-preview">
        <div className="strategy-preview__head">
          <span className="strategy-preview__label">
            <Layers size={13} />
            Consulta canônica compilada
          </span>
          <Button
            variant="ghost"
            size="xs"
            onClick={() => handleCopyQuery(generateLiveCanonicalQuery())}
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
            <span>{copied ? 'Copiada' : 'Copiar'}</span>
          </Button>
        </div>
        <div className={`strategy-query ${consultaCanonica ? '' : 'strategy-query--vazia'}`}>
          {consultaCanonica || 'Preencha ao menos um bloco para gerar a consulta.'}
        </div>
      </div>

      {/* Adaptação por base (doc 45 §10.2) */}
      <Dialog open={testModalOpen} onOpenChange={setTestModalOpen}>
        <DialogContent>
          <DialogTitlebar>
            <FileCode size={15} />
            <span>Adaptação da busca por base</span>
          </DialogTitlebar>
          <DialogBody>
            <div className="strategy-dialog-body">
              <div className="strategy-db-picker">
                {BASES_TESTAVEIS.map((db) => (
                  <button
                    key={db}
                    type="button"
                    onClick={() => handleTestDatabaseSyntax(db)}
                    aria-pressed={testDb === db}
                    className={`protocol-toggle ${testDb === db ? 'is-selected' : ''}`}
                  >
                    {db}
                  </button>
                ))}
              </div>

              {renderLoading ? (
                <p className="strategy-loading">Renderizando a adaptação para {testDb}…</p>
              ) : renderedResult ? (
                <>
                  <div className="strategy-note">
                    <strong>Nota de adaptação</strong>
                    <p>{renderedResult.adaptation_note}</p>
                  </div>

                  {renderedResult.is_decomposed && renderedResult.rendered_pairs ? (
                    <div>
                      <span className="strategy-section-label">
                        Decomposta em {renderedResult.rendered_pairs.length} consultas-par, unidas e
                        deduplicadas — limitação da interface da base, declarada no Registro de Busca.
                      </span>
                      <div className="strategy-pairs">
                        {renderedResult.rendered_pairs.map((par, idx) => (
                          <div key={idx} className="strategy-pair">
                            <span>{par}</span>
                            <span className="strategy-pair__index">par {idx + 1}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div>
                      <span className="strategy-section-label">
                        Consulta como será enviada a {renderedResult.database}
                      </span>
                      <div className="strategy-query">{renderedResult.rendered_query}</div>
                    </div>
                  )}
                </>
              ) : null}
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setTestModalOpen(false)}>
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revisão PRESS (doc 45 §10.3) */}
      <Dialog open={pressModalOpen} onOpenChange={setPressModalOpen}>
        <DialogContent>
          <DialogTitlebar>
            <Sparkles size={15} />
            <span>Revisão PRESS da estratégia</span>
          </DialogTitlebar>
          <DialogBody>
            <div className="strategy-dialog-body">
              {pressLoading ? (
                <p className="strategy-loading">Analisando os seis domínios do PRESS…</p>
              ) : pressResult ? (
                <>
                  <div className="press-score">
                    <div>
                      <h4>Conformidade da estratégia de busca</h4>
                      <p>
                        Heurística sobre os domínios do PRESS (McGowan et al., 2016). É uma sugestão
                        de revisão, não um parecer.
                      </p>
                    </div>
                    <span className="press-score__value">{pressResult.score_percentage}%</span>
                  </div>

                  <div className="press-domains">
                    {pressResult.domains.map((d, idx) => (
                      <div key={idx} className={`press-domain ${d.passed ? 'is-passed' : 'is-failed'}`}>
                        {d.passed ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}
                        <div>
                          <span className="press-domain__name">{d.domain}</span>
                          <p className="press-domain__message">{d.message}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : null}
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setPressModalOpen(false)}>
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
