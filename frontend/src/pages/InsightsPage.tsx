/**
 * Revsist — Central de Indicadores & Bibliometria (docs 31, 32, 47, 48, 49)
 *
 * Workbench metodológico em 5 visões especializadas:
 * 1. 📊 Panorama da Revisão (Processo, Funil PRISMA, Critérios, Bases, PDFs e Concordância Kappa)
 * 2. 📈 Bibliometria Clássica & Redes (Bradford, Lotka, Subramanyam, CAGR, HHI, Hirsch e Grafos Canvas)
 * 3. 🔍 Laboratório Analítico (Estatística Sob Demanda com tradutor em linguagem natural)
 * 4. ✨ Vanguarda & Sensibilidade (SciMAT, Kleinberg Bursts, Incerteza Bootstrap IC 95%, Louvain ARI)
 * 5. 📋 Pré-Registro & Exportação (Protocolo D11, Checklist BIBLIO 20 itens e Pacote ZIP)
 */

import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Archive,
  Award,
  BarChart3,
  BookOpen,
  CheckCircle2,
  Database,
  FileCheck2,
  FileDown,
  FileText,
  Layers,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  XCircle,
} from 'lucide-react'
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
import {
  Button,
  Card,
  EmptyState,
  ErrorBoundary,
  FormGroup,
  Input,
  LoadingState,
  PageHeader,
  Select,
} from '@/components/ui'
import type { AgreementMetrics, InsightsFilters, NameCount, ProjectInsights } from '@/types/api'
import { BarraDeInstantaneo } from '@/components/bibliometria/BarraDeInstantaneo'
import { PainelEnriquecimento } from '@/components/bibliometria/PainelEnriquecimento'
import { SecaoBibliometria } from '@/components/bibliometria/SecaoBibliometria'
import { PainelEstatisticaSobDemanda } from '@/components/bibliometria/PainelEstatisticaSobDemanda'
import { PainelVanguardaSensibilidade } from '@/components/bibliometria/PainelVanguardaSensibilidade'
import { PainelPreRegistroExportacao } from '@/components/bibliometria/PainelPreRegistroExportacao'
import { formatarContagem, formatarPercentual } from './insightsFormat'
import './InsightsPage.css'

const DECISOES: NonNullable<InsightsFilters['decision']>[] = ['Incluído', 'Excluído', 'Pendente']

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

const RÓTULOS_PDF_STATUS: Record<string, string> = {
  ausente: 'Ainda não buscado',
  obtido: 'Obtido automaticamente',
  manual: 'Anexado manualmente',
  falhou: 'Falhou',
  indisponivel: 'Indisponível em acesso aberto',
}

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

type TabKey = 'processo' | 'classicos' | 'estatistica' | 'vanguarda' | 'preregistro'

/**
 * As cinco visões, em dado e não em JSX repetido.
 *
 * Antes eram cinco blocos de marcação quase idênticos dentro de um `<nav>`,
 * sem `role="tablist"`, sem `aria-selected` e sem navegação por seta — quando
 * o próprio aplicativo já tem o padrão correto em `ProtocolVersionDialog`.
 * Para quem usa leitor de tela, aquilo era uma fileira de botões sem estado.
 */
const ABAS: { chave: TabKey; rotulo: string; Icone: typeof BarChart3 }[] = [
  { chave: 'processo', rotulo: 'Panorama da Revisão (PRISMA)', Icone: BarChart3 },
  { chave: 'classicos', rotulo: 'Bibliometria Clássica & Redes', Icone: TrendingUp },
  { chave: 'estatistica', rotulo: 'Laboratório de Consultas', Icone: Search },
  { chave: 'vanguarda', rotulo: 'Vanguarda & Sensibilidade', Icone: Sparkles },
  { chave: 'preregistro', rotulo: 'Pré-Registro & Relatório BIBLIO', Icone: Archive },
]

export function InsightsPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { activeProject, setActiveProject } = useSettingsStore()

  const [tabAtiva, setTabAtiva] = useState<TabKey>('processo')
  const [dados, setDados] = useState<ProjectInsights | null>(null)
  const [agreement, setAgreement] = useState<AgreementMetrics | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [atualizando, setAtualizando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [filtros, setFiltros] = useState<InsightsFilters>({ decision: 'Incluído' })
  const [instantaneo, setInstantaneo] = useState<string | null>(null)

  /** Setas andam entre as abas; Home e End vão aos extremos. */
  const aoNavegarPorTeclado = (evento: React.KeyboardEvent<HTMLButtonElement>) => {
    const passo =
      evento.key === 'ArrowRight' ? 1 : evento.key === 'ArrowLeft' ? -1 : 0
    let destino: TabKey | null = null

    if (passo !== 0) {
      const atual = ABAS.findIndex((a) => a.chave === tabAtiva)
      destino = ABAS[(atual + passo + ABAS.length) % ABAS.length].chave
    } else if (evento.key === 'Home') {
      destino = ABAS[0].chave
    } else if (evento.key === 'End') {
      destino = ABAS[ABAS.length - 1].chave
    }

    if (!destino) return
    evento.preventDefault()
    setTabAtiva(destino)
    // O foco acompanha a seleção — sem isso, a seta muda o painel e deixa o
    // foco para trás, e a próxima seta parte do lugar errado.
    document.getElementById(`insights-aba-${destino}`)?.focus()
  }

  const carregar = async () => {
    if (!id) return
    try {
      if (dados === null) setCarregando(true)
      else setAtualizando(true)
      setErro(null)
      if (!activeProject || activeProject.id !== id) {
        const proj = await api.getProject(id)
        setActiveProject(proj)
      }
      const [resultado, metrics] = await Promise.all([
        api.getInsights(id, { ...filtros, instantaneo: instantaneo ?? undefined }),
        api.getAgreementMetrics(id).catch(() => null),
      ])
      setDados(resultado)
      if (metrics) setAgreement(metrics)
    } catch (e) {
      console.error('Erro ao carregar indicadores:', e)
      setErro('Não foi possível carregar os indicadores deste projeto.')
    } finally {
      setCarregando(false)
      setAtualizando(false)
    }
  }

  useEffect(() => {
    void carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, filtros.decision, filtros.source, filtros.year_from, filtros.year_to, instantaneo])

  if (carregando) {
    return (
      <div className="insights-page animate-fade-in">
        <LoadingState label="Calculando indicadores e carregando ambiente bibliométrico…" />
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
  const basesDisponiveis = dados.composition_by_source.map((s) => s.source_name)

  const totalIdentificados = dados.prisma.identification.total_records_identified
  const totalTriados = dados.prisma.screening.records_screened
  const totalAtriar = dados.prisma.screening.records_to_screen ?? totalTriados
  const totalIncluidos = dados.prisma.included.studies_included_in_synthesis
  const totalExcluidos = dados.composition_by_decision?.['Excluído'] ?? 0

  // Quatro degraus, e não três. O degrau da deduplicação é onde a maior queda
  // acontece — 43.861 para 16.578 num dos acervos reais —, e omiti-lo fazia o
  // salto parecer efeito da triagem.
  const funilPrisma: NameCount[] = [
    { name: 'Identificados', count: totalIdentificados },
    { name: 'Únicos (após deduplicação)', count: totalAtriar },
    { name: 'Triados', count: totalTriados },
    { name: 'Incluídos', count: totalIncluidos },
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
        title="Indicadores & Bibliometria"
        onBack={() => navigate(`/projects/${id}/extraction`)}
        subtitle={
          <span>
            Projeto: <strong>{activeProject?.title}</strong> — Ambiente de análise descritiva, leis bibliométricas e replicação
          </span>
        }
        primaryAction={
          <Button
            variant="secondary"
            size="md"
            onClick={() => navigate(`/projects/${id}/export`)}
            leftIcon={<FileDown size={14} />}
          >
            Ir para Exportação PRISMA
          </Button>
        }
      />

      {/* ── 1. BARRA DE ESCOPO UNIFICADA & ENRIQUECIMENTO (Topo) ─────────── */}
      {id && (
        <ErrorBoundary fallbackTitle="Erro nos controles de instantâneo e enriquecimento">
          <div className="insights-escopo-container">
            <BarraDeInstantaneo
              projectId={id}
              selecionado={instantaneo}
              onSelecionar={setInstantaneo}
              escopo={{
                decision: filtros.decision ?? null,
                source: filtros.source ?? null,
                year_from: filtros.year_from ?? null,
                year_to: filtros.year_to ?? null,
              }}
            />
            <PainelEnriquecimento projectId={id} onAtualizarInsights={carregar} />
          </div>
        </ErrorBoundary>
      )}

      {/* ── 2. NAVEGAÇÃO DE WORKBENCH EM 5 ABAS PRINCIPAIS ────────────────── */}
      <div
        className="insights-tabs-nav"
        role="tablist"
        aria-label="Visões de Indicadores e Bibliometria"
      >
        {ABAS.map(({ chave, rotulo, Icone }) => (
          <button
            key={chave}
            type="button"
            role="tab"
            id={`insights-aba-${chave}`}
            aria-selected={tabAtiva === chave}
            aria-controls={`insights-painel-${chave}`}
            // Roving tabindex: o Tab entra na barra uma vez e as setas andam
            // entre as abas, que é o comportamento esperado de um tablist.
            tabIndex={tabAtiva === chave ? 0 : -1}
            onKeyDown={aoNavegarPorTeclado}
            onClick={() => setTabAtiva(chave)}
            className={`insights-tab-btn ${tabAtiva === chave ? 'insights-tab-btn--active' : ''}`}
          >
            <Icone size={15} />
            <span>{rotulo}</span>
          </button>
        ))}
      </div>

      {/* ── ABA 1: PANORAMA DA REVISÃO (Processo & PRISMA) ───────────────── */}
      {tabAtiva === 'processo' && (
        <div
          className="insights-painel"
          role="tabpanel"
          id="insights-painel-processo"
          aria-labelledby="insights-aba-processo"
        >
          {/* KPIs de topo */}
          <div className="insights-kpis-bar">
            <div className="insights-kpi-card">
              <div className="insights-kpi-card__icon">
                <Database size={18} />
              </div>
              <div className="insights-kpi-card__info">
                <span className="insights-kpi-card__val">{formatarContagem(totalIdentificados)}</span>
                <span className="insights-kpi-card__lbl">Identificados</span>
              </div>
            </div>

            <div className="insights-kpi-card">
              <div className="insights-kpi-card__icon" style={{ color: 'var(--color-chart-series-1)' }}>
                <Layers size={18} />
              </div>
              <div className="insights-kpi-card__info">
                <span className="insights-kpi-card__val">{formatarContagem(totalTriados)}</span>
                <span className="insights-kpi-card__lbl">
                  Triados <em>de {formatarContagem(totalAtriar)}</em>
                </span>
              </div>
            </div>

            <div className="insights-kpi-card">
              <div className="insights-kpi-card__icon" style={{ color: 'var(--color-success)' }}>
                <CheckCircle2 size={18} />
              </div>
              <div className="insights-kpi-card__info">
                <span className="insights-kpi-card__val" style={{ color: 'var(--color-success)' }}>
                  {formatarContagem(totalIncluidos)}
                </span>
                <span className="insights-kpi-card__lbl">Incluídos</span>
              </div>
            </div>

            <div className="insights-kpi-card">
              <div className="insights-kpi-card__icon" style={{ color: 'var(--color-error)' }}>
                <XCircle size={18} />
              </div>
              <div className="insights-kpi-card__info">
                <span className="insights-kpi-card__val" style={{ color: 'var(--color-error)' }}>
                  {formatarContagem(totalExcluidos)}
                </span>
                <span className="insights-kpi-card__lbl">Excluídos</span>
              </div>
            </div>
          </div>

          {/* Filtros interativos */}
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

            <Bloco
              titulo={`Instituições mais frequentes ${sufixoDecisao}`}
              descricao={
                dados.institutions_coverage.with_affiliation > 0
                  ? `Sobre ${dados.institutions_coverage.with_affiliation} de ${dados.institutions_coverage.total} estudos — as bases de coleta raramente informam a afiliação dos autores.`
                  : undefined
              }
            >
              {dados.institutions_coverage.with_affiliation === 0 ? (
                <EmptyState
                  size="inline"
                  title="Afiliações institucionais não enriquecidas ainda."
                  description="As bases de coleta não informam a instituição dos autores. Clique em 'Enriquecer com OpenAlex' no topo para obter afiliações reais resolvidas por ROR."
                />
              ) : (
                <GraficoRanking itens={dados.top_institutions} />
              )}
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

            {/* ── Processo e proveniência de Assistência ─────────────────────────── */}
            <Bloco
              titulo="Throughput de triagem por pessoa"
              descricao="Decisões manuais e assistidas registradas — sempre sobre o projeto inteiro."
            >
              <GraficoRanking itens={dados.ai_provenance.throughput_by_user} />
            </Bloco>
          </div>
        </div>
      )}

      {/* ── ABA 2: BIBLIOMETRIA CLÁSSICA & REDES ESTRUTURAIS ──────────────── */}
      {tabAtiva === 'classicos' && id && (
        <div
          className="insights-painel"
          role="tabpanel"
          id="insights-painel-classicos"
          aria-labelledby="insights-aba-classicos"
        >
        <ErrorBoundary fallbackTitle="Erro nos Indicadores Bibliométricos Clássicos">
          <SecaoBibliometria
            projectId={id}
            filtros={{
              ...filtros,
              instantaneo: instantaneo ?? undefined,
            }}
          />
        </ErrorBoundary>
        </div>
      )}

      {/* ── ABA 3: LABORATÓRIO ANALÍTICO (Estatística Sob Demanda) ───────── */}
      {tabAtiva === 'estatistica' && id && (
        <div
          className="insights-painel"
          role="tabpanel"
          id="insights-painel-estatistica"
          aria-labelledby="insights-aba-estatistica"
        >
        <ErrorBoundary fallbackTitle="Erro no Laboratório de Consultas">
          <PainelEstatisticaSobDemanda
            projectId={id}
            snapshotId={instantaneo}
          />
        </ErrorBoundary>
        </div>
      )}

      {/* ── ABA 4: VANGUARDA & SENSIBILIDADE ─────────────────────────────── */}
      {tabAtiva === 'vanguarda' && id && (
        <div
          className="insights-painel"
          role="tabpanel"
          id="insights-painel-vanguarda"
          aria-labelledby="insights-aba-vanguarda"
        >
        <ErrorBoundary fallbackTitle="Erro no Painel de Vanguarda e Sensibilidade">
          <PainelVanguardaSensibilidade
            projectId={id}
            snapshotId={instantaneo}
          />
        </ErrorBoundary>
        </div>
      )}

      {/* ── ABA 5: PRÉ-REGISTRO & RELATÓRIO BIBLIO ───────────────────────── */}
      {tabAtiva === 'preregistro' && id && (
        <div
          className="insights-painel"
          role="tabpanel"
          id="insights-painel-preregistro"
          aria-labelledby="insights-aba-preregistro"
        >
        <ErrorBoundary fallbackTitle="Erro no Painel de Pré-Registro e Conformidade">
          <PainelPreRegistroExportacao
            projectId={id}
            snapshotId={instantaneo}
          />
        </ErrorBoundary>
        </div>
      )}
    </div>
  )
}
