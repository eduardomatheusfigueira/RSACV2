/**
 * Revsist — Aba de Indicadores (B.I. e Bibliometria, doc 31/32/33)
 *
 * Sexto passo da esteira, entre Extração e Exportação. Mostra estatística
 * descritiva e de processo sobre o projeto — funil PRISMA e de critérios,
 * composição da amostra, rankings de periódico/autor/instituição e saúde de
 * aquisição de PDF. Não é bibliometria de citação (doc 31 §4): o dado para
 * isso não existe no Revsist hoje.
 *
 * Fase 2 do plano (doc 33): filtros de decisão/base/ano na interface,
 * afetando só os agregados de conteúdo — o funil PRISMA, o funil de
 * critérios e a composição por base continuam sobre o projeto inteiro
 * (doc 32 §3.2), porque o backend já os calcula assim independente do que a
 * consulta pedir.
 */

import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BarChart3, FileDown, FileText } from 'lucide-react'
import {
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
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { Button, Card, EmptyState, FormGroup, Input, LoadingState, PageHeader, Select } from '@/components/ui'
import type { AgreementMetrics, InsightsFilters, NameCount, ProjectInsights } from '@/types/api'
import { formatarPercentual } from './insightsFormat'
import './InsightsPage.css'

const DECISOES: NonNullable<InsightsFilters['decision']>[] = ['Incluído', 'Excluído', 'Pendente']

/** Rótulo plural para os títulos de bloco — "incluídos", não "Incluído-s". */
const PLURAL_DECISAO: Record<string, string> = {
  Incluído: 'incluídos',
  Excluído: 'excluídos',
  Pendente: 'pendentes',
}

const CORES = {
  serie1: 'var(--color-chart-series-1)',
  serie2: 'var(--color-chart-series-2)',
  accent: 'var(--color-accent)',
  accentMuted: 'var(--color-accent-muted)',
  included: 'var(--color-included)',
  excluded: 'var(--color-excluded)',
  pending: 'var(--color-pending)',
}

/** Rótulos legíveis para cada valor de `pdf_status` (doc 32 §6.4). */
const RÓTULOS_PDF_STATUS: Record<string, string> = {
  ausente: 'Ainda não buscado',
  obtido: 'Obtido automaticamente',
  manual: 'Anexado manualmente',
  falhou: 'Falhou',
  indisponivel: 'Indisponível em acesso aberto',
}

/**
 * Tabela alternativa acessível: mesmo dado do gráfico, para quem navega por
 * teclado/leitor de tela sem depender só da leitura visual do SVG
 * (doc 32 §5.3). Visualmente oculta, sempre presente no DOM.
 */
function TabelaAcessivel({
  legendaColunas,
  linhas,
}: {
  legendaColunas: [string, string]
  linhas: { rotulo: string; valor: number | string }[]
}): JSX.Element {
  return (
    <table className="insights-tabela-acessivel">
      <caption className="rsac-visually-hidden">Dados subjacentes ao gráfico acima</caption>
      <thead>
        <tr>
          <th>{legendaColunas[0]}</th>
          <th>{legendaColunas[1]}</th>
        </tr>
      </thead>
      <tbody>
        {linhas.map((linha) => (
          <tr key={linha.rotulo}>
            <td>{linha.rotulo}</td>
            <td>{linha.valor}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

interface BlocoProps {
  titulo: string
  descricao?: string
  children: React.ReactNode
}

function Bloco({ titulo, descricao, children }: BlocoProps): JSX.Element {
  return (
    <Card surface="secundaria" relief="elevado" className="insights-bloco">
      <div className="insights-bloco__cabecalho">
        <h3>{titulo}</h3>
        {descricao && <p>{descricao}</p>}
      </div>
      {children}
    </Card>
  )
}

/** Ranking horizontal de uma única série (contagem por nome). */
function GraficoRanking({ itens, limite = 10 }: { itens: NameCount[]; limite?: number }): JSX.Element {
  if (itens.length === 0) {
    return <EmptyState size="inline" title="Sem dado suficiente para este ranking ainda." />
  }
  const exibidos = itens.slice(0, limite)
  const altura = Math.max(exibidos.length * 32, 80)

  return (
    <>
      <ResponsiveContainer width="100%" height={altura}>
        <BarChart data={exibidos} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--color-border-subtle)" />
          <XAxis type="number" allowDecimals={false} stroke="var(--color-text-tertiary)" fontSize={11} />
          <YAxis
            type="category"
            dataKey="name"
            width={160}
            stroke="var(--color-text-tertiary)"
            fontSize={11}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--color-bg-elevated)',
              border: '1px solid var(--color-border)',
              fontSize: 12,
            }}
          />
          <Bar dataKey="count" fill={CORES.accent} radius={[0, 4, 4, 0]} maxBarSize={18} />
        </BarChart>
      </ResponsiveContainer>
      <TabelaAcessivel
        legendaColunas={['Nome', 'Ocorrências']}
        linhas={exibidos.map((i) => ({ rotulo: i.name, valor: i.count }))}
      />
    </>
  )
}

export function InsightsPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject } = useSettingsStore()

  const [dados, setDados] = useState<ProjectInsights | null>(null)
  const [agreement, setAgreement] = useState<AgreementMetrics | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [atualizando, setAtualizando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [filtros, setFiltros] = useState<InsightsFilters>({ decision: 'Incluído' })

  useEffect(() => {
    if (!id) return
    let cancelado = false
    ;(async () => {
      try {
        if (dados === null) setCarregando(true)
        else setAtualizando(true)
        setErro(null)
        if (!activeProject || activeProject.id !== id) {
          const proj = await api.getProject(id)
          if (!cancelado) setActiveProject(proj)
        }
        const [resultado, metrics] = await Promise.all([
          api.getInsights(id, filtros),
          api.getAgreementMetrics(id).catch(() => null),
        ])
        if (!cancelado) {
          setDados(resultado)
          if (metrics) setAgreement(metrics)
        }
      } catch (e) {
        console.error('Erro ao carregar indicadores:', e)
        if (!cancelado) setErro('Não foi possível carregar os indicadores deste projeto.')
      } finally {
        if (!cancelado) {
          setCarregando(false)
          setAtualizando(false)
        }
      }
    })()
    return () => {
      cancelado = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, filtros.decision, filtros.source, filtros.year_from, filtros.year_to])

  if (carregando) {
    return (
      <div className="insights-page animate-fade-in">
        <LoadingState label="Calculando indicadores…" />
      </div>
    )
  }

  if (erro || !dados) {
    return (
      <div className="insights-page animate-fade-in">
        <EmptyState
          title="Indicadores indisponíveis"
          description={erro ?? 'Tente novamente em instantes.'}
        />
      </div>
    )
  }

  const decisaoSelecionada = filtros.decision ?? 'Incluído'
  const sufixoDecisao = `(${PLURAL_DECISAO[decisaoSelecionada]})`
  // As bases vêm da composição por base, que é agregado de processo — inclui
  // toda base já registrada no projeto, independente do filtro corrente.
  const basesDisponiveis = dados.composition_by_source.map((s) => s.source_name)

  const funilPrisma: NameCount[] = [
    { name: 'Identificados', count: dados.prisma.identification.total_records_identified },
    { name: 'Triados', count: dados.prisma.screening.records_screened },
    { name: 'Incluídos', count: dados.prisma.included.studies_included_in_synthesis },
  ]

  const decisoes = Object.entries(dados.composition_by_decision)
  const coresPorDecisao: Record<string, string> = {
    Incluído: CORES.included,
    Excluído: CORES.excluded,
    Pendente: CORES.pending,
  }

  const funilCriterios = dados.criteria_funnel

  return (
    <div className="insights-page animate-fade-in">
      <PageHeader
        title="Indicadores"
        onBack={() => navigate(`/projects/${id}/extraction`)}
        subtitle={
          <span>
            Projeto: <strong>{activeProject?.title}</strong> — estatística descritiva e de processo da revisão
          </span>
        }
        primaryAction={
          <Button
            variant="secondary"
            size="md"
            onClick={() => navigate(`/projects/${id}/export`)}
            leftIcon={<FileDown size={14} />}
          >
            Ir para Exportação
          </Button>
        }
      />

      <Card surface="secundaria" relief="plano" className="insights-filtros">
        <FormGroup label="Decisão" htmlFor="insights-filtro-decisao">
          <Select
            id="insights-filtro-decisao"
            sizeVariant="sm"
            value={decisaoSelecionada}
            onChange={(e) =>
              setFiltros((f) => ({ ...f, decision: e.target.value as InsightsFilters['decision'] }))
            }
          >
            {DECISOES.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </Select>
        </FormGroup>

        <FormGroup label="Base" htmlFor="insights-filtro-base">
          <Select
            id="insights-filtro-base"
            sizeVariant="sm"
            value={filtros.source ?? ''}
            onChange={(e) => setFiltros((f) => ({ ...f, source: e.target.value || undefined }))}
          >
            <option value="">Todas as bases</option>
            {basesDisponiveis.map((base) => (
              <option key={base} value={base}>
                {base}
              </option>
            ))}
          </Select>
        </FormGroup>

        <FormGroup label="Ano — de" htmlFor="insights-filtro-ano-de">
          <Input
            id="insights-filtro-ano-de"
            sizeVariant="sm"
            type="number"
            inputMode="numeric"
            placeholder="Ex.: 2015"
            value={filtros.year_from ?? ''}
            onChange={(e) =>
              setFiltros((f) => ({ ...f, year_from: e.target.value ? Number(e.target.value) : undefined }))
            }
          />
        </FormGroup>

        <FormGroup label="Ano — até" htmlFor="insights-filtro-ano-ate">
          <Input
            id="insights-filtro-ano-ate"
            sizeVariant="sm"
            type="number"
            inputMode="numeric"
            placeholder="Ex.: 2024"
            value={filtros.year_to ?? ''}
            onChange={(e) =>
              setFiltros((f) => ({ ...f, year_to: e.target.value ? Number(e.target.value) : undefined }))
            }
          />
        </FormGroup>

        {atualizando && <span className="insights-filtros__status">Atualizando…</span>}
      </Card>

      <p className="insights-filtros__nota">
        O filtro restringe rankings, distribuição temporal, tipo de estudo e saúde de PDF. O funil PRISMA, o
        funil de critérios e o volume por base continuam sobre o projeto inteiro.
      </p>

      <div className="insights-grid" data-trilho-target="prisma-flowchart">
        {/* ── Funil PRISMA ──────────────────────────────────────────── */}
        <Bloco
          titulo="Funil de identificação e triagem"
          descricao="Sempre sobre o projeto inteiro — não é afetado por nenhum filtro."
        >
          <GraficoRanking itens={funilPrisma} limite={funilPrisma.length} />
        </Bloco>

        {/* ── Funil de critérios ────────────────────────────────────── */}
        <Bloco
          titulo="Critérios de inclusão e exclusão"
          descricao="Quantos artigos avaliados atendem cada critério — explica por que a amostra tem o tamanho que tem."
        >
          {funilCriterios.length === 0 ? (
            <EmptyState
              size="inline"
              title="Nenhum critério avaliado ainda"
              description="A triagem ainda não registrou avaliação de critérios para este projeto."
            />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={Math.max(funilCriterios.length * 44, 100)}>
                <BarChart
                  data={funilCriterios.map((c) => ({
                    text: c.text.length > 28 ? `${c.text.slice(0, 28)}…` : c.text,
                    fullText: c.text,
                    Atende: c.met_count,
                    'Não atende': c.not_met_count,
                  }))}
                  layout="vertical"
                  margin={{ left: 8, right: 16 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--color-border-subtle)" />
                  <XAxis type="number" allowDecimals={false} stroke="var(--color-text-tertiary)" fontSize={11} />
                  <YAxis
                    type="category"
                    dataKey="text"
                    width={180}
                    stroke="var(--color-text-tertiary)"
                    fontSize={11}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--color-bg-elevated)',
                      border: '1px solid var(--color-border)',
                      fontSize: 12,
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Atende" fill={CORES.serie1} maxBarSize={14} />
                  <Bar dataKey="Não atende" fill={CORES.serie2} maxBarSize={14} />
                </BarChart>
              </ResponsiveContainer>
              <TabelaAcessivel
                legendaColunas={['Critério', 'Atende / Não atende']}
                linhas={funilCriterios.map((c) => ({
                  rotulo: `${c.text} (${c.is_exclusion ? 'exclusão' : 'inclusão'})`,
                  valor: `${c.met_count} / ${c.not_met_count}`,
                }))}
              />
            </>
          )}
        </Bloco>

        {/* ── Composição por decisão ───────────────────────────────── */}
        <Bloco titulo="Composição da amostra">
          {decisoes.length === 0 ? (
            <EmptyState size="inline" title="Nenhuma decisão registrada ainda." />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={Math.max(decisoes.length * 32, 80)}>
                <BarChart
                  data={decisoes.map(([nome, total]) => ({ name: nome, count: total }))}
                  layout="vertical"
                  margin={{ left: 8, right: 16 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--color-border-subtle)" />
                  <XAxis type="number" allowDecimals={false} stroke="var(--color-text-tertiary)" fontSize={11} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    stroke="var(--color-text-tertiary)"
                    fontSize={11}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--color-bg-elevated)',
                      border: '1px solid var(--color-border)',
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={22}>
                    {decisoes.map(([nome]) => (
                      <Cell key={nome} fill={coresPorDecisao[nome] ?? CORES.accent} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <TabelaAcessivel
                legendaColunas={['Decisão', 'Artigos']}
                linhas={decisoes.map(([nome, total]) => ({ rotulo: nome, valor: total }))}
              />
            </>
          )}
        </Bloco>

        {/* ── Composição por base ──────────────────────────────────── */}
        <Bloco
          titulo="Volume por base de coleta"
          descricao="Encontrados (tom claro) vs. incluídos na síntese (tom sólido) — sempre sobre o projeto inteiro."
        >
          {dados.composition_by_source.length === 0 ? (
            <EmptyState size="inline" title="Nenhuma fonte registrada ainda." />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={Math.max(dados.composition_by_source.length * 40, 100)}>
                <BarChart
                  data={dados.composition_by_source.map((s) => ({
                    name: s.source_name,
                    Encontrados: s.found_count,
                    Incluídos: s.included_count,
                  }))}
                  layout="vertical"
                  margin={{ left: 8, right: 16 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--color-border-subtle)" />
                  <XAxis type="number" allowDecimals={false} stroke="var(--color-text-tertiary)" fontSize={11} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    stroke="var(--color-text-tertiary)"
                    fontSize={11}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--color-bg-elevated)',
                      border: '1px solid var(--color-border)',
                      fontSize: 12,
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Encontrados" fill={CORES.accentMuted} maxBarSize={14} />
                  <Bar dataKey="Incluídos" fill={CORES.accent} maxBarSize={14} />
                </BarChart>
              </ResponsiveContainer>
              <TabelaAcessivel
                legendaColunas={['Base', 'Encontrados / Incluídos']}
                linhas={dados.composition_by_source.map((s) => ({
                  rotulo: s.source_name,
                  valor: `${s.found_count} / ${s.included_count}`,
                }))}
              />
            </>
          )}
        </Bloco>

        {/* ── Distribuição temporal ────────────────────────────────── */}
        <Bloco titulo={`Publicações por ano ${sufixoDecisao}`}>
          <GraficoRanking
            itens={dados.composition_by_year.map((y) => ({ name: y.year, count: y.count }))}
            limite={dados.composition_by_year.length}
          />
        </Bloco>

        {/* ── Tipo de estudo ───────────────────────────────────────── */}
        <Bloco titulo={`Tipo de estudo ${sufixoDecisao}`}>
          <GraficoRanking itens={dados.composition_by_research_type} />
        </Bloco>

        {/* ── Rankings ──────────────────────────────────────────────── */}
        <Bloco titulo={`Periódicos mais frequentes ${sufixoDecisao}`}>
          <GraficoRanking itens={dados.top_journals} />
        </Bloco>

        <Bloco
          titulo={`Autores mais frequentes ${sufixoDecisao}`}
          descricao="Contagem aproximada: nomes não são desambiguados entre si."
        >
          <GraficoRanking itens={dados.top_authors} />
        </Bloco>

        <Bloco titulo={`Instituições mais frequentes ${sufixoDecisao}`}>
          <GraficoRanking itens={dados.top_institutions} />
        </Bloco>

        {/* ── Saúde de PDF e extração ───────────────────────────────── */}
        <Bloco titulo={`Saúde de aquisição de PDF ${sufixoDecisao}`}>
          {Object.keys(dados.pdf_health.by_status).length === 0 ? (
            <EmptyState size="inline" title="Nenhum PDF processado ainda." />
          ) : (
            <>
              <GraficoRanking
                itens={Object.entries(dados.pdf_health.by_status).map(([status, total]) => ({
                  name: RÓTULOS_PDF_STATUS[status] ?? status,
                  count: total,
                }))}
                limite={10}
              />
              <dl className="insights-metricas-secundarias">
                <div>
                  <dt>PDFs escaneados</dt>
                  <dd>{formatarPercentual(dados.pdf_health.scanned_ratio)}</dd>
                </div>
                <div>
                  <dt>Completude da extração</dt>
                  <dd>{formatarPercentual(dados.pdf_health.extraction_completeness)}</dd>
                </div>
              </dl>
            </>
          )}
        </Bloco>

        {/* ── Processo e proveniência de Assistência ─────────────────────────── */}
        <Bloco
          titulo="Throughput de triagem por pessoa"
          descricao="Decisões manuais e assistidas registradas — sempre sobre o projeto inteiro."
        >
          <GraficoRanking itens={dados.ai_provenance.throughput_by_user} />
        </Bloco>

        <Bloco
          titulo="Proveniência da decisão"
          descricao="Quanto veio de Assistência, e com que confiabilidade — sempre sobre o projeto inteiro."
        >
          {Object.keys(dados.ai_provenance.decisions_by_origin).length === 0 ? (
            <EmptyState size="inline" title="Nenhuma decisão auditada ainda." />
          ) : (
            <>
              <GraficoRanking
                itens={Object.entries(dados.ai_provenance.decisions_by_origin).map(([origem, total]) => ({
                  name: origem,
                  count: total,
                }))}
                limite={2}
              />
              <dl className="insights-metricas-secundarias">
                <div>
                  <dt>Resposta de Assistência fora do vocabulário</dt>
                  <dd>{formatarPercentual(dados.ai_provenance.ai_invalid_response_rate)}</dd>
                </div>
              </dl>
              {dados.ai_provenance.ai_confidence_distribution.length > 0 && (
                <>
                  <p className="insights-bloco__subtitulo">Distribuição de confiança das decisões assistidas</p>
                  <GraficoRanking
                    itens={dados.ai_provenance.ai_confidence_distribution}
                    limite={10}
                  />
                </>
              )}
            </>
          )}
        </Bloco>

        {/* ── Concordância Interobservador e Kappa de Cohen (Doc 43 §43.9) ── */}
        <Bloco
          titulo="Concordância Interobservador (Kappa de Cohen)"
          descricao="Estatística de confiabilidade e concordância metodológica entre pares independentes (Doc 43 §43.9)."
        >
          {!agreement || agreement.evaluated_papers_count === 0 ? (
            <EmptyState
              size="inline"
              title="Sem estudos com triagem independente suficiente"
              description="O cálculo de concordância requer ao menos 1 estudo avaliado por 2 revisores distintos."
            />
          ) : (
            <div className="insights-concordancia-container">
              <div className="insights-concordancia-cards">
                <div className="insights-kappa-card">
                  <span className="insights-stat-label">Kappa de Cohen (κ)</span>
                  <span className="insights-kappa-value">
                    {agreement.cohen_kappa !== null ? agreement.cohen_kappa.toFixed(3) : '—'}
                  </span>
                  <span className={`insights-kappa-badge kappa-${agreement.kappa_classification.toLowerCase().split(' ')[0]}`}>
                    {agreement.kappa_classification}
                  </span>
                </div>
                <div className="insights-kappa-card">
                  <span className="insights-stat-label">Concordância Bruta (Po)</span>
                  <span className="insights-po-value">{agreement.raw_agreement_percent}%</span>
                  <span className="insights-po-detail">
                    {agreement.concordant_count} de {agreement.evaluated_papers_count} estudos em acordo
                  </span>
                </div>
              </div>

              <div className="insights-contingency-table-wrapper">
                <p className="insights-bloco__subtitulo">Matriz de Contingência Cruzada (2x2)</p>
                <table className="insights-contingency-table">
                  <thead>
                    <tr>
                      <th>Julgamento</th>
                      <th>Estudos</th>
                      <th>Percentual</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><span className="dot-included">●</span> Ambos Incluíram</td>
                      <td><strong>{agreement.contingency_matrix.both_included}</strong></td>
                      <td>{((agreement.contingency_matrix.both_included / agreement.evaluated_papers_count) * 100).toFixed(1)}%</td>
                    </tr>
                    <tr>
                      <td><span className="dot-excluded">●</span> Ambos Excluíram</td>
                      <td><strong>{agreement.contingency_matrix.both_excluded}</strong></td>
                      <td>{((agreement.contingency_matrix.both_excluded / agreement.evaluated_papers_count) * 100).toFixed(1)}%</td>
                    </tr>
                    <tr>
                      <td><span className="dot-divergent">●</span> Divergentes (Conflito)</td>
                      <td><strong>{agreement.contingency_matrix.divergent}</strong></td>
                      <td>{((agreement.contingency_matrix.divergent / agreement.evaluated_papers_count) * 100).toFixed(1)}%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Bloco>
      </div>
    </div>
  )
}
