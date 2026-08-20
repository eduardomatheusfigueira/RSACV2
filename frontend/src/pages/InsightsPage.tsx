/**
 * RSAC V2 — Aba de Indicadores (B.I. e Bibliometria, doc 31/32/33)
 *
 * Sexto passo da esteira, entre Extração e Exportação. Mostra estatística
 * descritiva e de processo sobre o projeto — funil PRISMA e de critérios,
 * composição da amostra, rankings de periódico/autor/instituição e saúde de
 * aquisição de PDF. Não é bibliometria de citação (doc 31 §4): o dado para
 * isso não existe no RSAC hoje.
 *
 * Fase 0 do plano (doc 33): sem filtros na interface ainda — a página busca
 * os agregados padrão (decisão = Incluído) e os exibe. Filtros de
 * decisão/base/ano chegam na Fase 2.
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
import { Button, Card, EmptyState, LoadingState, PageHeader } from '@/components/ui'
import type { NameCount, ProjectInsights } from '@/types/api'
import { formatarPercentual } from './insightsFormat'
import './InsightsPage.css'

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
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    ;(async () => {
      try {
        setCarregando(true)
        setErro(null)
        if (!activeProject || activeProject.id !== id) {
          const proj = await api.getProject(id)
          setActiveProject(proj)
        }
        const resultado = await api.getInsights(id)
        setDados(resultado)
      } catch (e) {
        console.error('Erro ao carregar indicadores:', e)
        setErro('Não foi possível carregar os indicadores deste projeto.')
      } finally {
        setCarregando(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

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

      <div className="insights-grid">
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
        <Bloco titulo="Publicações incluídas por ano">
          <GraficoRanking
            itens={dados.composition_by_year.map((y) => ({ name: y.year, count: y.count }))}
            limite={dados.composition_by_year.length}
          />
        </Bloco>

        {/* ── Tipo de estudo ───────────────────────────────────────── */}
        <Bloco titulo="Tipo de estudo (incluídos)">
          <GraficoRanking itens={dados.composition_by_research_type} />
        </Bloco>

        {/* ── Rankings ──────────────────────────────────────────────── */}
        <Bloco titulo="Periódicos mais frequentes (incluídos)">
          <GraficoRanking itens={dados.top_journals} />
        </Bloco>

        <Bloco
          titulo="Autores mais frequentes (incluídos)"
          descricao="Contagem aproximada: nomes não são desambiguados entre si."
        >
          <GraficoRanking itens={dados.top_authors} />
        </Bloco>

        <Bloco titulo="Instituições mais frequentes (incluídos)">
          <GraficoRanking itens={dados.top_institutions} />
        </Bloco>

        {/* ── Saúde de PDF e extração ───────────────────────────────── */}
        <Bloco titulo="Saúde de aquisição de PDF (incluídos)">
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
      </div>
    </div>
  )
}
