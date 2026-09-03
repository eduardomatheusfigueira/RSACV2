import React, { useState, useEffect } from 'react'
import {
  DiagramaEstrategicoResponse,
  RajadasResponse,
  BootstrapRankingsResponse,
  SensibilidadeParametrosResponse,
  CoberturaCampoResponse,
} from '@/types/api'
import { api } from '@/api/client'
import {
  Compass,
  Zap,
  TrendingUp,
  Sliders,
  PieChart,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Info,
} from 'lucide-react'
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts'
import { Button, EmptyState, Select } from '@/components/ui'
import './PainelVanguardaSensibilidade.css'

interface PainelVanguardaSensibilidadeProps {
  projectId: string
  snapshotId?: string | null
}

type TabVanguarda = 'diagrama' | 'rajadas' | 'bootstrap' | 'sensibilidade' | 'cobertura'

export const PainelVanguardaSensibilidade: React.FC<PainelVanguardaSensibilidadeProps> = ({
  projectId,
  snapshotId,
}) => {
  const [tabAtiva, setTabAtiva] = useState<TabVanguarda>('diagrama')
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  // Dados
  const [diagrama, setDiagrama] = useState<DiagramaEstrategicoResponse | null>(null)
  const [rajadas, setRajadas] = useState<RajadasResponse | null>(null)
  const [tipoRanking, setTipoRanking] = useState<'periodicos' | 'autores' | 'instituicoes'>('periodicos')
  const [bootstrap, setBootstrap] = useState<BootstrapRankingsResponse | null>(null)
  const [sensibilidade, setSensibilidade] = useState<SensibilidadeParametrosResponse | null>(null)
  const [cobertura, setCobertura] = useState<CoberturaCampoResponse | null>(null)

  const carregarAba = async (tab: TabVanguarda) => {
    setCarregando(true)
    setErro(null)
    try {
      if (tab === 'diagrama') {
        const res = await api.obterDiagramaEstrategico(projectId, snapshotId)
        setDiagrama(res)
      } else if (tab === 'rajadas') {
        const res = await api.obterRajadasTermos(projectId, { snapshotId })
        setRajadas(res)
      } else if (tab === 'bootstrap') {
        const res = await api.obterBootstrapRankings(projectId, {
          tipoRanking,
          snapshotId,
        })
        setBootstrap(res)
      } else if (tab === 'sensibilidade') {
        const res = await api.obterSensibilidadeParametros(projectId, snapshotId)
        setSensibilidade(res)
      } else if (tab === 'cobertura') {
        const res = await api.obterCoberturaCampo(projectId, snapshotId)
        setCobertura(res)
      }
    } catch (err: any) {
      setErro(err.message || 'Erro ao carregar indicador de vanguarda.')
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregarAba(tabAtiva)
  }, [projectId, snapshotId, tabAtiva, tipoRanking])

  const scatterData = (diagrama?.items || []).map((item) => ({
    name: item.label,
    x: item.centralidade,
    y: item.densidade,
    z: item.tamanho,
    quadrante: item.quadrante,
    keywords: item.palavras_chave.join(', '),
  }))

  const coresQuadrante: Record<string, string> = {
    motor: '#10b981', // Verde
    basico: '#3b82f6', // Azul
    especializado: '#8b5cf6', // Roxo
    emergente_declinio: '#f59e0b', // Laranja
  }

  return (
    <div className="painel-vanguarda">
      {/* Cabeçalho */}
      <div className="painel-vanguarda__cabecalho">
        <div>
          <h3 className="painel-vanguarda__titulo">
            <Compass className="painel-vanguarda__titulo-icone" size={18} />
            Indicadores de Vanguarda e Sensibilidade
          </h3>
          <p className="painel-vanguarda__descricao">
            Análise estrutural SciMAT, rajadas temporais, incerteza bootstrap e diagnóstico de cobertura do campo (doc 48 §7.4, §10).
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => carregarAba(tabAtiva)}
          disabled={carregando}
          leftIcon={<RefreshCw size={14} className={carregando ? 'animate-spin' : ''} />}
        >
          Atualizar
        </Button>
      </div>

      {/* Navegação de Abas */}
      <div className="painel-vanguarda__subnav">
        <button
          type="button"
          onClick={() => setTabAtiva('diagrama')}
          className={`painel-vanguarda__subnav-btn ${tabAtiva === 'diagrama' ? 'painel-vanguarda__subnav-btn--active' : ''}`}
        >
          <TrendingUp size={14} />
          <span>Diagrama Estratégico (SciMAT)</span>
        </button>
        <button
          type="button"
          onClick={() => setTabAtiva('rajadas')}
          className={`painel-vanguarda__subnav-btn ${tabAtiva === 'rajadas' ? 'painel-vanguarda__subnav-btn--active' : ''}`}
        >
          <Zap size={14} />
          <span>Rajadas de Termos (Kleinberg)</span>
        </button>
        <button
          type="button"
          onClick={() => setTabAtiva('bootstrap')}
          className={`painel-vanguarda__subnav-btn ${tabAtiva === 'bootstrap' ? 'painel-vanguarda__subnav-btn--active' : ''}`}
        >
          <Info size={14} />
          <span>Incerteza Bootstrap (IC 95%)</span>
        </button>
        <button
          type="button"
          onClick={() => setTabAtiva('sensibilidade')}
          className={`painel-vanguarda__subnav-btn ${tabAtiva === 'sensibilidade' ? 'painel-vanguarda__subnav-btn--active' : ''}`}
        >
          <Sliders size={14} />
          <span>Sensibilidade Louvain (Rand Index)</span>
        </button>
        <button
          type="button"
          onClick={() => setTabAtiva('cobertura')}
          className={`painel-vanguarda__subnav-btn ${tabAtiva === 'cobertura' ? 'painel-vanguarda__subnav-btn--active' : ''}`}
        >
          <PieChart size={14} />
          <span>Cobertura do Campo (PRESS)</span>
        </button>
      </div>

      {erro && (
        <div className="painel-estatistica__alerta-erro">
          <AlertTriangle size={16} />
          <span>{erro}</span>
        </div>
      )}

      {/* ── 1. Aba Diagrama Estratégico ── */}
      {/* Sem termos agrupados não há diagrama: os eixos ficam em zero e o
          plano sai vazio, o que se lê como "o campo não tem estrutura" em vez
          de "faltam palavras-chave". O diagrama depende do enriquecimento e do
          tesauro (doc 48 §7.4a). */}
      {tabAtiva === 'diagrama' && diagrama && diagrama.items.length === 0 && (
        <EmptyState
          size="inline"
          title="Sem temas agrupados para posicionar"
          description="O diagrama estratégico parte da coocorrência de termos, que depende das palavras-chave obtidas no enriquecimento externo e do tesauro aprovado. Nenhum dos dois está disponível neste recorte."
        />
      )}

      {tabAtiva === 'diagrama' && diagrama && diagrama.items.length > 0 && (
        <div className="painel-vanguarda__conteudo">
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
            <span>
              Eixos divididos pela média: Centralidade = {diagrama.centralidade_media} | Densidade = {diagrama.densidade_media}
            </span>
            <span style={{ fontFamily: 'monospace' }}>Callon et al. (1991) / SciMAT</span>
          </div>

          {/* Gráfico Scatter 4 Quadrantes */}
          <div className="painel-vanguarda__scimat-grid">
            <div className="painel-vanguarda__grafico-container">
              <div style={{ width: '100%', height: 320 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" />
                    <XAxis
                      type="number"
                      dataKey="x"
                      name="Centralidade"
                      tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }}
                      label={{ value: 'Centralidade (Interação Externa) →', position: 'bottom', fontSize: 11, fill: 'var(--color-text-secondary)' }}
                    />
                    <YAxis
                      type="number"
                      dataKey="y"
                      name="Densidade"
                      tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }}
                      label={{ value: 'Densidade (Coesão Interna) ↑', angle: -90, position: 'left', fontSize: 11, fill: 'var(--color-text-secondary)' }}
                    />
                    <ZAxis type="number" dataKey="z" range={[80, 400]} name="Tamanho" />
                    <Tooltip
                      content={({ payload }) => {
                        if (!payload || !payload.length) return null
                        const d = payload[0].payload
                        return (
                          <div style={{ background: 'var(--color-bg-elevated)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', padding: 'var(--space-2)', fontSize: 'var(--text-xs)', color: 'var(--color-text-primary)' }}>
                            <div style={{ fontWeight: 700 }}>{d.name}</div>
                            <div style={{ color: 'var(--color-text-secondary)' }}>Quadrante: {d.quadrante}</div>
                            <div style={{ color: 'var(--color-text-secondary)' }}>Centralidade: {d.x} | Densidade: {d.y}</div>
                            <div className="painel-vanguarda__legenda-curta">Termos: {d.keywords}</div>
                          </div>
                        )
                      }}
                    />
                    <ReferenceLine x={diagrama.centralidade_media} stroke="var(--color-border)" strokeDasharray="4 4" />
                    <ReferenceLine y={diagrama.densidade_media} stroke="var(--color-border)" strokeDasharray="4 4" />
                    <Scatter name="Clusters" data={scatterData} fill="var(--color-accent)" />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Explicação dos Quadrantes */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <div className="painel-vanguarda__quadrante-badge painel-vanguarda__quadrante-badge--motor">
                <div>
                  <strong>Motores (Q1):</strong> Alta Centralidade & Alta Densidade. Temas estruturados e cruciais para o avanço da área.
                </div>
              </div>
              <div className="painel-vanguarda__quadrante-badge painel-vanguarda__quadrante-badge--basico">
                <div>
                  <strong>Básicos / Transversais (Q4):</strong> Alta Centralidade & Baixa Densidade. Temas genéricos compartilhados por múltiplos subcampos.
                </div>
              </div>
              <div className="painel-vanguarda__quadrante-badge painel-vanguarda__quadrante-badge--especializado">
                <div>
                  <strong>Especializados / Periféricos (Q2):</strong> Baixa Centralidade & Alta Densidade. Subtemas coesos e bem desenvolvidos, mas isolados.
                </div>
              </div>
              <div className="painel-vanguarda__quadrante-badge painel-vanguarda__quadrante-badge--emergente">
                <div>
                  <strong>Emergentes ou em Declínio (Q3):</strong> Baixa Centralidade & Baixa Densidade. Tópicos novos em gestação ou conceitos descontinuados.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 2. Aba Rajadas de Termos (Kleinberg) ── */}
      {/* "0 rajadas detectadas" sobre um corpus sem termos não é a ausência
          de surtos: é a ausência do insumo. */}
      {tabAtiva === 'rajadas' && rajadas && (rajadas.rajadas || []).length === 0 && (
        <EmptyState
          size="inline"
          title="Nenhuma rajada para detectar"
          description="A detecção de Kleinberg corre sobre a série temporal de termos. Sem palavras-chave no recorte — elas vêm do enriquecimento externo — não há série sobre a qual medir surtos."
        />
      )}

      {tabAtiva === 'rajadas' && rajadas && (rajadas.rajadas || []).length > 0 && (
        <div className="painel-vanguarda__conteudo">
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
            <span>Detecção de surtos exponenciais de frequência com modelo de estados ocultos (Kleinberg, 2003)</span>
            <span style={{ fontFamily: 'monospace' }}>{(rajadas.rajadas || []).length} rajadas detectadas</span>
          </div>

          <div className="painel-vanguarda__tabela-wrapper">
            <table className="painel-vanguarda__tabela">
              <thead>
                <tr>
                  <th>Termo / Conceito</th>
                  <th style={{ textAlign: 'right' }}>Força do Surto</th>
                  <th style={{ textAlign: 'center' }}>Período Ativo</th>
                  <th style={{ textAlign: 'right' }}>Pico</th>
                  <th style={{ textAlign: 'right' }}>Taxa de Crescimento</th>
                </tr>
              </thead>
              <tbody>
                {(rajadas.rajadas || []).map((b, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{b.termo}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent)' }}>
                      {(b.peso_rajada ?? 0).toFixed(2)}
                    </td>
                    <td style={{ textAlign: 'center', fontFamily: 'monospace' }}>
                      {b.ano_inicio} — {b.ano_fim}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                      {b.frequencia_pico} ocor./ano
                    </td>
                    <td style={{ textAlign: 'right', color: 'var(--color-success)', fontWeight: 600 }}>
                      +{(b.crescimento_pct ?? 0).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── 3. Aba Incerteza Bootstrap (IC 95%) ── */}
      {tabAtiva === 'bootstrap' && (
        <div className="painel-vanguarda__conteudo">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Ranking:</span>
            <Select
              sizeVariant="sm"
              value={tipoRanking}
              onChange={(e) => setTipoRanking(e.target.value as any)}
            >
              <option value="periodicos">Periódicos Mais Produtivos</option>
              <option value="autores">Autores Mais Produtivos</option>
              <option value="instituicoes">Instituições de Destaque</option>
            </Select>
          </div>

          {bootstrap?.aviso_empates && (
            <div className="painel-vanguarda__alerta-empate">
              <AlertTriangle size={16} />
              <span>{bootstrap.aviso_empates}</span>
            </div>
          )}

          {bootstrap && (
            <div className="painel-vanguarda__tabela-wrapper">
              <table className="painel-vanguarda__tabela">
                <thead>
                  <tr>
                    <th className="painel-vanguarda__coluna-estreita">Posição</th>
                    <th>Entidade</th>
                    <th style={{ textAlign: 'right' }}>Contagem Observada</th>
                    <th style={{ textAlign: 'center' }}>Intervalo de Confiança (IC 95%)</th>
                    <th>Diagnóstico de Incerteza</th>
                  </tr>
                </thead>
                <tbody>
                  {(bootstrap.items || []).map((item) => (
                    <tr key={item.posicao}>
                      <td style={{ textAlign: 'center', fontWeight: 700 }}>
                        {item.posicao}º
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        {item.rotulo}
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent)' }}>
                        {item.valor_estimado}
                      </td>
                      <td style={{ textAlign: 'center', fontFamily: 'monospace' }}>
                        <span className="painel-vanguarda__badge-ic">
                          [{item.ic_95[0]}, {item.ic_95[1]}]
                        </span>
                      </td>
                      <td>
                        {item.indistinguivel ? (
                          <span style={{ padding: 'var(--space-0-5) var(--space-2)', background: 'var(--color-warning-bg)', color: 'var(--color-warning-text)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)', fontWeight: 600 }}>
                            Empate técnico com posições: {item.empate_com?.join(', ')}º
                          </span>
                        ) : (
                          <span style={{ color: 'var(--color-success)', fontSize: 'var(--text-xs)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1)' }}>
                            <CheckCircle2 size={13} /> Posição estatisticamente distinta
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── 4. Aba Sensibilidade Louvain (Rand Index) ── */}
      {tabAtiva === 'sensibilidade' && sensibilidade && (
        <div className="painel-vanguarda__conteudo">
          <div style={{ padding: 'var(--space-2-5) var(--space-4)', background: 'var(--color-bg-primary)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-sm)', color: 'var(--color-text-primary)' }}>
            {sensibilidade.diagnostico}
          </div>

          <div className="painel-vanguarda__tabela-wrapper">
            <table className="painel-vanguarda__tabela">
              <thead>
                <tr>
                  <th>Resolução Louvain</th>
                  <th style={{ textAlign: 'right' }}>Nº de Clusters</th>
                  <th style={{ textAlign: 'right' }}>Índice de Rand Ajustado (ARI vs. 1.0)</th>
                  <th>Status da Partição</th>
                </tr>
              </thead>
              <tbody>
                {(sensibilidade.varredura || []).map((row) => (
                  <tr key={row.resolucao}>
                    <td style={{ fontFamily: 'monospace', fontWeight: 700 }}>
                      {row.resolucao.toFixed(1)}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 700 }}>{row.n_clusters}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                      {row.ari_vs_vigente !== null && row.ari_vs_vigente !== undefined
                        ? row.ari_vs_vigente.toFixed(4)
                        : '1.0000 (referência)'}
                    </td>
                    <td>
                      {row.is_vigente ? (
                        <span style={{ padding: 'var(--space-0-5) var(--space-2)', background: 'var(--color-accent)', color: 'var(--color-text-on-accent)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)', fontWeight: 600 }}>
                          Resolução Vigente (Padrão)
                        </span>
                      ) : (
                        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>Varredura de sensibilidade</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── 5. Aba Cobertura do Campo ── */}
      {tabAtiva === 'cobertura' && cobertura && (
        <div className="painel-vanguarda__conteudo">
          <div style={{ padding: 'var(--space-2-5) var(--space-4)', background: 'var(--color-info-bg)', border: 'var(--space-px) solid var(--color-info)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-sm)', color: 'var(--color-info-text)' }}>
            {cobertura.diagnostico_metodologico}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-3)' }}>
            {/* Tópicos Robustos */}
            <div style={{ border: 'var(--space-px) solid var(--color-success)', borderRadius: 'var(--radius-xl)', padding: 'var(--space-3)', background: 'var(--color-success-bg)' }}>
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-success-text)', display: 'flex', alignItems: 'center', gap: 'var(--space-1-5)', marginBottom: 'var(--space-2)' }}>
                <CheckCircle2 size={16} />
                Subtemas com Cobertura Robusta ({(cobertura.topicos_robustos || []).length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1-5)' }}>
                {(cobertura.topicos_robustos || []).map((t, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', padding: 'var(--space-1-5) var(--space-2)', background: 'var(--color-bg-elevated)', borderRadius: 'var(--radius-xl)', border: 'var(--space-px) solid var(--color-border-subtle)' }}>
                    <span style={{ fontWeight: 500, color: 'var(--color-text-primary)' }}>{t.topico}</span>
                    <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-success)' }}>{t.n_estudos_no_corpus} estudos</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Tópicos Ralos */}
            <div style={{ border: 'var(--space-px) solid var(--color-warning)', borderRadius: 'var(--radius-xl)', padding: 'var(--space-3)', background: 'var(--color-warning-bg)' }}>
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-warning-text)', display: 'flex', alignItems: 'center', gap: 'var(--space-1-5)', marginBottom: 'var(--space-2)' }}>
                <AlertTriangle size={16} />
                Subtemas Marginais / Ralos ({(cobertura.topicos_ralos || []).length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1-5)' }}>
                {(cobertura.topicos_ralos || []).map((t, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', padding: 'var(--space-1-5) var(--space-2)', background: 'var(--color-bg-elevated)', borderRadius: 'var(--radius-xl)', border: 'var(--space-px) solid var(--color-border-subtle)' }}>
                    <span style={{ fontWeight: 500, color: 'var(--color-text-primary)' }}>{t.topico}</span>
                    <span style={{ fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>{t.n_estudos_no_corpus} estudo</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
