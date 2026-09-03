/**
 * Revsist — Seção de Indicadores Bibliométricos Nível 0 e 1 (docs 47, 48 §7, §8, doc 49 Fase 3, Fase 6).
 *
 * Exibe indicadores bibliométricos matematicamente rigorosos e auditáveis:
 * - Produção anual e taxa composta de crescimento (CAGR)
 * - Concentração de fontes / Lei de Bradford (1934)
 * - Produtividade de autores / Lei de Lotka (1926) com teste Kolmogorov-Smirnov
 * - Índice de colaboração de Subramanyam (1983) e média de autores
 * - Concentração (Gini e HHI)
 * - Impacto e Índice h do corpus (Hirsch, 2005)
 * - Distribuição de Acesso Aberto e Geografia por país
 * - Visualizador de Grafos e Redes Estruturais (Canvas 60fps)
 */

import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  AlertCircle,
  Award,
  BookOpen,
  CheckCircle,
  Download,
  Globe2,
  Layers,
  Lock,
  Network,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  Unlock,
  Users,
  XCircle,
} from 'lucide-react'

import { api } from '@/api/client'
import { Button, Card, EmptyState, ErrorBoundary, LoadingState, Select } from '@/components/ui'
import type {
  GrafoInfo,
  IndicadoresBibliometricos,
  InsightsFilters,
  TipoDeRede,
} from '@/types/api'
import { VisualizadorGrafoCanvas } from './VisualizadorGrafoCanvas'
import './SecaoBibliometria.css'

interface Props {
  projectId: string
  filtros: InsightsFilters
}

const CORES = {
  primary: 'var(--color-accent, #3b82f6)',
  series1: 'var(--color-chart-series-1, #0284c7)',
  series2: 'var(--color-chart-series-2, #0d9488)',
  series3: 'var(--color-chart-series-3, #d97706)',
  success: 'var(--color-success, #16a34a)',
  warning: 'var(--color-warning, #ea580c)',
  muted: 'var(--color-text-tertiary, #94a3b8)',
  border: 'var(--color-border-subtle, #e2e8f0)',
  bgElevated: 'var(--color-bg-elevated, #ffffff)',
}

const CORES_ZONAS = ['#0284c7', '#0d9488', '#e2e8f0']

export function SecaoBibliometria({ projectId, filtros }: Props): JSX.Element {
  const [subVisao, setSubVisao] = useState<'leis' | 'redes'>('leis')
  const [dados, setDados] = useState<IndicadoresBibliometricos | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  // Estados de Redes e Grafos
  // Os nomes são os que a API entende. Enquanto a tela usava apelidos
  // ('termos', 'acoplamento'), dois dos quatro tipos respondiam HTTP 400
  // "Tipo de rede desconhecido" — metade do seletor estava quebrada.
  const [tipoRede, setTipoRede] =
    useState<TipoDeRede>('coautoria')
  const [grafoAtivo, setGrafoAtivo] = useState<GrafoInfo | null>(null)
  const [carregandoGrafo, setCarregandoGrafo] = useState(false)
  const [erroGrafo, setErroGrafo] = useState<string | null>(null)

  useEffect(() => {
    let ativo = true

    async function carregar() {
      try {
        setCarregando(true)
        setErro(null)
        const res = await api.obterIndicadoresBibliometricos(projectId, {
          instantaneo: filtros.instantaneo,
          decision: filtros.decision,
          source: filtros.source,
          year_from: filtros.year_from,
          year_to: filtros.year_to,
        })
        if (ativo) {
          setDados(res)
        }
      } catch (e: unknown) {
        if (ativo) {
          const msg = e instanceof Error ? e.message : 'Falha ao carregar indicadores bibliométricos.'
          setErro(msg)
        }
      } finally {
        if (ativo) {
          setCarregando(false)
        }
      }
    }

    void carregar()

    return () => {
      ativo = false
    }
  }, [projectId, filtros.instantaneo, filtros.decision, filtros.source, filtros.year_from, filtros.year_to])

  // Carregar / Gerar Grafo quando alternado para a aba de Redes
  const carregarOuGerarGrafo = async (tipo = tipoRede) => {
    try {
      setCarregandoGrafo(true)
      setErroGrafo(null)
      const res = await api.gerarGrafo(projectId, {
        network_type: tipo,
        snapshot_id: filtros.instantaneo,
        normalizacao: 'association_strength',
        corte_minimo: 2,
        max_nos: 50,
        resolucao_louvain: 1.0,
      })
      setGrafoAtivo(res)
    } catch (e: any) {
      setErroGrafo(e.message || 'Não foi possível construir o grafo para este recorte.')
    } finally {
      setCarregandoGrafo(false)
    }
  }

  useEffect(() => {
    if (subVisao === 'redes' && !grafoAtivo && !carregandoGrafo) {
      void carregarOuGerarGrafo(tipoRede)
    }
  }, [subVisao, tipoRede, projectId, filtros.instantaneo])

  if (carregando) {
    return (
      <div className="secao-biblio secao-biblio--loading">
        <LoadingState label="Calculando indicadores bibliométricos determinísticos..." />
      </div>
    )
  }

  if (erro || !dados) {
    return (
      <div className="secao-biblio">
        <EmptyState
          size="inline"
          title="Não foi possível calcular os indicadores"
          description={erro || 'Nenhum dado disponível para o recorte selecionado.'}
        />
      </div>
    )
  }

  const {
    production_temporal,
    bradford,
    lotka,
    collaboration,
    concentration,
    citations,
    open_access,
    countries,
    provenance,
  } = dados

  return (
    <section className="secao-biblio" aria-label="Ambiente de Bibliometria e Indicadores">
      {/* ── Carimbo de integridade numérica e proveniência ── */}
      <div className="secao-biblio__carimbo">
        <div className="secao-biblio__carimbo-badge">
          <ShieldCheck size={15} className="text-success" />
          <span>Cálculo Determinístico (Doc 48 §2)</span>
        </div>
        <p className="secao-biblio__carimbo-texto">
          {provenance ? (
            <>
              Instantâneo congelado <code>{provenance.corpus_hash.slice(0, 12)}…</code> · {provenance.n_documents} documentos analisados.
            </>
          ) : (
            <>
              Medido sobre o acervo do momento · <strong>{dados.total_papers}</strong> estudos no recorte.
            </>
          )}
        </p>

        {/* Sub-toggle entre Leis e Redes */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 'var(--space-1-5)' }}>
          <button
            type="button"
            onClick={() => setSubVisao('leis')}
            className={`secao-biblio__tab-btn ${subVisao === 'leis' ? 'secao-biblio__tab-btn--active' : ''}`}
            style={{ padding: 'var(--space-1) var(--space-2-5)', fontSize: 'var(--text-xs)' }}
          >
            <TrendingUp size={13} />
            <span>Leis & Concentração</span>
          </button>
          <button
            type="button"
            onClick={() => setSubVisao('redes')}
            className={`secao-biblio__tab-btn ${subVisao === 'redes' ? 'secao-biblio__tab-btn--active' : ''}`}
            style={{ padding: 'var(--space-1) var(--space-2-5)', fontSize: 'var(--text-xs)' }}
          >
            <Network size={13} />
            <span>Redes Estruturais (Canvas)</span>
          </button>
        </div>
      </div>

      {/* ── Sub-Visão 1: Leis Bibliométricas ──────────────────────────────── */}
      {subVisao === 'leis' && (
        <div className="secao-biblio__grid">
          {/* ── 1. Produção Temporal e CAGR ── */}
          <Card surface="secundaria" relief="plano" className="secao-biblio__card">
            <div className="secao-biblio__card-header">
              <div className="secao-biblio__card-titulo">
                <TrendingUp size={18} className="text-primary" />
                <h3>Produção Temporal e CAGR</h3>
              </div>
              {production_temporal.cagr_pct !== null && (
                <span className="secao-biblio__badge-destaque">
                  CAGR: <strong>{production_temporal.cagr_pct > 0 ? `+${production_temporal.cagr_pct}%` : `${production_temporal.cagr_pct}%`}</strong> /ano
                </span>
              )}
            </div>
            <p className="secao-biblio__card-desc">
              Taxa composta de crescimento anual (Price, 1963) entre {production_temporal.year_start ?? '—'} e {production_temporal.year_end ?? '—'}.
            </p>

            {production_temporal.series.length === 0 ? (
              <EmptyState size="inline" title="Sem dados de ano de publicação" />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={production_temporal.series} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CORES.border} />
                  <XAxis dataKey="year" stroke={CORES.muted} fontSize={11} />
                  <YAxis stroke={CORES.muted} fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: CORES.bgElevated, border: `1px solid ${CORES.border}`, fontSize: 12 }}
                    formatter={(val) => [`${Number(val ?? 0)} artigos`, 'Produção']}
                    labelFormatter={(label) => `Ano: ${label}`}
                  />
                  <Area type="monotone" dataKey="count" stroke={CORES.series1} fill={CORES.series1} fillOpacity={0.15} strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </Card>

          {/* ── 2. Lei de Bradford (1934) ── */}
          <Card surface="secundaria" relief="plano" className="secao-biblio__card">
            <div className="secao-biblio__card-header">
              <div className="secao-biblio__card-titulo">
                <BookOpen size={18} className="text-primary" />
                <h3>Concentração de Fontes (Bradford, 1934)</h3>
              </div>
              {bradford.k_multiplier !== null && (
                <span className="secao-biblio__badge-destaque">
                  k = <strong>{bradford.k_multiplier}</strong>
                </span>
              )}
            </div>
            <p className="secao-biblio__card-desc">
              Partição dos periódicos em 3 zonas com ~1/3 dos artigos. Razão observada: <strong>{bradford.formula_ratio || '—'}</strong>.
            </p>

            {bradford.total_articles === 0 ? (
              <EmptyState size="inline" title="Nenhum periódico identificado nos estudos" />
            ) : bradford.confiavel === false || bradford.zones.length === 0 ? (
              // Um periódico não faz três zonas. Antes, a tela exibia
              // "Zona 1: 1 periódico, 100%" e razão "1 : 0 : 0" como resultado.
              <EmptyState
                size="inline"
                title="Periódicos insuficientes para a partição de Bradford"
                description={
                  bradford.motivo ??
                  'A lei de Bradford parte os periódicos em três zonas; o recorte não tem periódicos suficientes para isso.'
                }
              />
            ) : (
              <div className="secao-biblio__bradford-container">
                <div className="secao-biblio__bradford-zonas">
                  {bradford.zones.map((z, idx) => (
                    <div key={z.zone} className="secao-biblio__bradford-zona" style={{ borderColor: CORES_ZONAS[idx] }}>
                      <div className="secao-biblio__bradford-zona-head">
                        <span className="secao-biblio__bradford-zona-num" style={{ background: CORES_ZONAS[idx] }}>
                          Z{z.zone}
                        </span>
                        <strong>{z.name}</strong>
                      </div>
                      <div className="secao-biblio__bradford-zona-stats">
                        <span><strong>{z.n_journals}</strong> periódicos</span>
                        <span><strong>{z.total_articles}</strong> artigos ({z.pct_articles}%)</span>
                      </div>
                    </div>
                  ))}
                </div>

                {bradford.zones[0]?.journals.length > 0 && (
                  <div className="secao-biblio__bradford-nucleo">
                    <h4>Principais Periódicos do Núcleo (Zona 1):</h4>
                    <ul className="secao-biblio__lista-nucleo">
                      {bradford.zones[0].journals.slice(0, 5).map((j) => (
                        <li key={j.name}>
                          <span className="secao-biblio__journal-name">{j.name}</span>
                          <span className="secao-biblio__journal-count">{j.count}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </Card>

          {/* ── 3. Lei de Lotka (1926) & Kolmogorov-Smirnov ── */}
          <Card surface="secundaria" relief="plano" className="secao-biblio__card">
            <div className="secao-biblio__card-header">
              <div className="secao-biblio__card-titulo">
                <Users size={18} className="text-primary" />
                <h3>Produtividade de Autores (Lotka, 1926)</h3>
              </div>
              {lotka.alpha !== null && (
                <span className="secao-biblio__badge-destaque">
                  α = <strong>{lotka.alpha}</strong>
                </span>
              )}
            </div>
            <p className="secao-biblio__card-desc">
              Ajuste da lei de potência com teste de aderência Kolmogorov-Smirnov (Clauset et al., 2009).
            </p>

            <div className="secao-biblio__lotka-status">
              {/* Três estados, e não dois: aceita, rejeitada, e "a amostra não
                  decide". Enquanto eram dois, 17 autores produziam um selo
                  verde de "aderência aceita" que o teste não sustentava. */}
              <div
                className={`secao-biblio__lotka-badge ${
                  lotka.is_adherent === null || lotka.is_adherent === undefined
                    ? 'is-indeterminado'
                    : lotka.is_adherent
                      ? 'is-ok'
                      : 'is-rejected'
                }`}
              >
                {lotka.is_adherent === null || lotka.is_adherent === undefined ? (
                  <AlertCircle size={14} />
                ) : lotka.is_adherent ? (
                  <CheckCircle size={14} />
                ) : (
                  <XCircle size={14} />
                )}
                <span>{lotka.p_verdict}</span>
              </div>
              {lotka.c_constant !== null && (
                <span className="secao-biblio__lotka-subtext">
                  C = {lotka.c_constant} · {lotka.n_authors} autores únicos avaliados.
                </span>
              )}
            </div>

            {lotka.distribution.length === 0 ? (
              <EmptyState size="inline" title="Sem autores suficientes para ajuste de Lotka" />
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={lotka.distribution.slice(0, 8)} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CORES.border} />
                  <XAxis dataKey="articles" stroke={CORES.muted} fontSize={11} label={{ value: 'Artigos por autor', position: 'insideBottom', offset: -2, fontSize: 10 }} />
                  <YAxis stroke={CORES.muted} fontSize={11} />
                  <Tooltip
                    contentStyle={{ background: CORES.bgElevated, border: `1px solid ${CORES.border}`, fontSize: 12 }}
                    formatter={(val, name) => [
                      Number(val ?? 0),
                      name === 'authors_observed' ? 'Observados' : 'Esperados',
                    ]}
                    labelFormatter={(lbl) => `${lbl} artigo(s)`}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="authors_observed" name="Observado" fill={CORES.series1} maxBarSize={16} />
                  <Bar dataKey="authors_expected" name="Esperado (Lotka)" fill={CORES.series3} maxBarSize={16} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>

          {/* ── 4. Colaboração (Subramanyam, 1983) & Concentração ── */}
          <Card surface="secundaria" relief="plano" className="secao-biblio__card">
            <div className="secao-biblio__card-header">
              <div className="secao-biblio__card-titulo">
                <Users size={18} className="text-primary" />
                <h3>Colaboração e Concentração</h3>
              </div>
              {collaboration.subramanyam_index !== null && (
                <span className="secao-biblio__badge-destaque">
                  Subramanyam: <strong>{collaboration.subramanyam_index}</strong>
                </span>
              )}
            </div>
            <p className="secao-biblio__card-desc">
              Grau de coautoria (Subramanyam, 1983) e índices de desigualdade estrutural (Gini e HHI).
            </p>

            <div className="secao-biblio__metricas-grid">
              <div className="secao-biblio__metrica-box">
                <span className="secao-biblio__metrica-rotulo">Média de Autores</span>
                <span className="secao-biblio__metrica-valor">{collaboration.avg_authors_per_paper}</span>
                <span className="secao-biblio__metrica-sub">por artigo</span>
              </div>
              <div className="secao-biblio__metrica-box">
                <span className="secao-biblio__metrica-rotulo">Em Coautoria</span>
                <span className="secao-biblio__metrica-valor">{collaboration.multi_author_articles}</span>
                <span className="secao-biblio__metrica-sub">de {collaboration.total_articles} estudos</span>
              </div>
              <div className="secao-biblio__metrica-box">
                <span className="secao-biblio__metrica-rotulo">Gini de Autores</span>
                <span className="secao-biblio__metrica-valor">{concentration.gini_authors ?? '—'}</span>
                <span className="secao-biblio__metrica-sub">0 = igual, 1 = conc.</span>
              </div>
              <div className="secao-biblio__metrica-box">
                <span className="secao-biblio__metrica-rotulo">HHI Periódicos</span>
                <span className="secao-biblio__metrica-valor">{concentration.hhi_journals ?? '—'}</span>
                {/* A escala precisa aparecer: um HHI de 5.000 ao lado de um
                    Gini de 0,4 não se compara sem ela. */}
                <span className="secao-biblio__metrica-sub">
                  {concentration.hhi_journals === null
                    ? 'periódicos insuficientes'
                    : 'Herfindahl · 0 a 10.000'}
                </span>
              </div>
            </div>

            {collaboration.distribution.length > 0 && (
              <div className="secao-biblio__coautoria-chart">
                <ResponsiveContainer width="100%" height={130}>
                  <BarChart data={collaboration.distribution.slice(0, 7)} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CORES.border} />
                    <XAxis dataKey="num_authors" stroke={CORES.muted} fontSize={10} />
                    <YAxis stroke={CORES.muted} fontSize={10} />
                    <Tooltip contentStyle={{ background: CORES.bgElevated, border: `1px solid ${CORES.border}`, fontSize: 11 }} />
                    <Bar dataKey="count" name="Artigos" fill={CORES.series2} maxBarSize={14} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>

          {/* ── 5. Impacto e Citações (Hirsch, 2005) ── */}
          <Card surface="secundaria" relief="plano" className="secao-biblio__card">
            <div className="secao-biblio__card-header">
              <div className="secao-biblio__card-titulo">
                <Award size={18} className="text-primary" />
                <h3>Impacto e Citações (Nível 1)</h3>
              </div>
              {citations.papers_with_citation_data > 0 && (
                <span className="secao-biblio__badge-hindex">
                  Índice h: <strong>{citations.h_index}</strong>
                </span>
              )}
            </div>
            <p className="secao-biblio__card-desc">
              Métricas de citação recebidas obtidas via OpenAlex / Crossref.
            </p>

            {/* Zero citações medidas e corpus não enriquecido são coisas
                diferentes, e a tela dizia a mesma coisa para as duas:
                "Índice h: 0", "Total de citações: 0". A primeira é resultado;
                a segunda é ausência de dado, e tem conserto. */}
            {citations.papers_with_citation_data === 0 ? (
              <EmptyState
                size="inline"
                title="O corpus ainda não foi enriquecido"
                description="Contagem de citações, índice h e acesso aberto dependem dos metadados do OpenAlex. Use “Enriquecer Acervo”, no topo da aba, para obtê-los."
              />
            ) : (
              <div className="secao-biblio__metricas-grid">
                <div className="secao-biblio__metrica-box">
                  <span className="secao-biblio__metrica-rotulo">Total de Citações</span>
                  <span className="secao-biblio__metrica-valor">{citations.total_citations}</span>
                  <span className="secao-biblio__metrica-sub">
                    em {citations.papers_with_citation_data} estudos
                  </span>
                </div>
                <div className="secao-biblio__metrica-box">
                  <span className="secao-biblio__metrica-rotulo">Média por Artigo</span>
                  <span className="secao-biblio__metrica-valor">{citations.mean_citations}</span>
                  <span className="secao-biblio__metrica-sub">
                    mediana: {citations.median_citations}
                  </span>
                </div>
              </div>
            )}

            {citations.citation_bands.length > 0 && (
              <div className="secao-biblio__faixas-citacao">
                <ResponsiveContainer width="100%" height={150}>
                  <BarChart data={citations.citation_bands} layout="vertical" margin={{ top: 5, right: 15, left: 30, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={CORES.border} />
                    <XAxis type="number" stroke={CORES.muted} fontSize={10} allowDecimals={false} />
                    <YAxis type="category" dataKey="label" stroke={CORES.muted} fontSize={10} width={80} tickLine={false} />
                    <Tooltip contentStyle={{ background: CORES.bgElevated, border: `1px solid ${CORES.border}`, fontSize: 11 }} />
                    <Bar dataKey="count" name="Artigos" fill={CORES.series1} maxBarSize={12} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>

          {/* ── 6. Acesso Aberto & Geografia ── */}
          <Card surface="secundaria" relief="plano" className="secao-biblio__card">
            <div className="secao-biblio__card-header">
              <div className="secao-biblio__card-titulo">
                <Globe2 size={18} className="text-primary" />
                <h3>Acesso Aberto e Países</h3>
              </div>
              {open_access.by_status.length > 0 && (
                <span className="secao-biblio__badge-destaque">
                  {open_access.open_access_pct}% Open Access
                </span>
              )}
            </div>
            <p className="secao-biblio__card-desc">
              Distribuição de modalidades de acesso e geografia dos autores identificados.
            </p>

            {/* Sem enriquecimento não há modalidade de acesso nem país: "0%
                Open Access" afirmaria que nenhum dos estudos é aberto. */}
            {open_access.by_status.length === 0 && countries.length === 0 ? (
              <EmptyState
                size="inline"
                title="Sem dados de acesso aberto e afiliação"
                description="Modalidade de acesso e país dos autores vêm do enriquecimento externo, ainda não executado neste projeto."
              />
            ) : (
            <div className="secao-biblio__oa-container">
              <div className="secao-biblio__oa-status-list">
                {open_access.by_status.map((st) => (
                  <div key={st.status} className="secao-biblio__oa-item">
                    <div className="secao-biblio__oa-item-info">
                      {st.status === 'closed' ? <Lock size={12} className="text-muted" /> : <Unlock size={12} className="text-success" />}
                      <span className="secao-biblio__oa-status-nome">{st.status}</span>
                    </div>
                    <span className="secao-biblio__oa-item-val">
                      <strong>{st.count}</strong> ({st.pct}%)
                    </span>
                  </div>
                ))}
              </div>

              {countries.length > 0 && (
                <div className="secao-biblio__paises-box">
                  <h4>Países mais frequentes:</h4>
                  <div className="secao-biblio__paises-chips">
                    {countries.slice(0, 8).map((c) => (
                      <span key={c.country} className="secao-biblio__pais-chip">
                        <strong>{c.country}</strong> ({c.count})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            )}
          </Card>
        </div>
      )}

      {/* ── Sub-Visão 2: Redes Estruturais e Grafos (Canvas 60fps) ────────── */}
      {subVisao === 'redes' && (
        <Card surface="secundaria" relief="plano" className="p-4" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-2-5)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                Tipo de Rede Estrutural:
              </span>
              <Select
                sizeVariant="sm"
                value={tipoRede}
                onChange={(e) => {
                  const val = e.target.value as TipoDeRede
                  setTipoRede(val)
                  void carregarOuGerarGrafo(val)
                }}
              >
                <option value="coautoria">👥 Rede de Coautoria</option>
                <option value="coocorrencia_termos">🔤 Rede de Coocorrência de Termos</option>
                <option value="acoplamento_bibliografico">🔗 Acoplamento Bibliográfico</option>
                <option value="cocitacao">📚 Rede de Cocitação</option>
              </Select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => carregarOuGerarGrafo()}
                disabled={carregandoGrafo}
                leftIcon={<RefreshCw size={13} className={carregandoGrafo ? 'animate-spin' : ''} />}
              >
                {carregandoGrafo ? 'Processando layout...' : 'Recalcular Rede'}
              </Button>
              {grafoAtivo && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(api.exportarGrafoUrl(projectId, grafoAtivo.id), '_blank')}
                  leftIcon={<Download size={13} />}
                >
                  Exportar GraphML
                </Button>
              )}
            </div>
          </div>

          {erroGrafo && (
            <div style={{ padding: 'var(--space-2) var(--space-3)', background: 'var(--color-warning-bg)', border: 'var(--space-px) solid var(--color-warning)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)', color: 'var(--color-warning-text)' }}>
              {erroGrafo}
            </div>
          )}

          {carregandoGrafo ? (
            <LoadingState label="Calculando topologia, clusters Louvain e layout Fruchterman-Reingold..." />
          ) : grafoAtivo ? (
            <VisualizadorGrafoCanvas
              grafo={grafoAtivo}
              onExportGraphML={() => window.open(api.exportarGrafoUrl(projectId, grafoAtivo.id), '_blank')}
            />
          ) : (
            <EmptyState
              size="inline"
              title="Rede ainda não gerada"
              description="Selecione o tipo de rede acima e clique em 'Recalcular Rede'."
            />
          )}
        </Card>
      )}
    </section>
  )
}
