import React, { useState, useEffect } from 'react'
import {
  EspecificacaoEstatistica,
  InterpretarPerguntaResponse,
  ExecutarEspecificacaoResponse,
  AnaliseSalvaInfo,
} from '@/types/api'
import { api } from '@/api/client'
import {
  Sparkles,
  Play,
  BookmarkPlus,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Code2,
  Table as TableIcon,
  BarChart2,
  RefreshCw,
} from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import { Button } from '@/components/ui'
import './PainelEstatisticaSobDemanda.css'

interface PainelEstatisticaSobDemandaProps {
  projectId: string
  snapshotId?: string | null
}

const EXEMPLOS_PERGUNTAS = [
  'qual a mediana de citações por ano, só dos incluídos?',
  'quantos artigos por periódico?',
  'qual a média de citações por instituição?',
  'produção temporal de artigos por ano',
  'composição de estudos por decisão',
]

export const PainelEstatisticaSobDemanda: React.FC<PainelEstatisticaSobDemandaProps> = ({
  projectId,
  snapshotId,
}) => {
  const [pergunta, setPergunta] = useState('')
  const [interpretando, setInterpretando] = useState(false)
  const [executando, setExecutando] = useState(false)
  const [respostaInterp, setRespostaInterp] = useState<InterpretarPerguntaResponse | null>(null)
  const [specEditavel, setSpecEditavel] = useState('')
  const [resultado, setResultado] = useState<ExecutarEspecificacaoResponse | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [analisesSalvas, setAnalisesSalvas] = useState<AnaliseSalvaInfo[]>([])
  const [salvando, setSalvando] = useState(false)

  const carregarAnalisesSalvas = async () => {
    try {
      const res = await api.listarAnalisesEstatisticas(projectId)
      setAnalisesSalvas(res)
    } catch {
      // silencioso
    }
  }

  useEffect(() => {
    carregarAnalisesSalvas()
  }, [projectId])

  const handleInterpretar = async (texto: string) => {
    if (!texto.trim()) return
    setInterpretando(true)
    setErro(null)
    try {
      const res = await api.interpretarPerguntaEstatistica(projectId, texto)
      setRespostaInterp(res)
      if (res.specification) {
        setSpecEditavel(JSON.stringify(res.specification, null, 2))
        // Executa automaticamente a primeira vez para fluidez
        handleExecutar(res.specification)
      } else {
        setSpecEditavel('')
        setResultado(null)
      }
    } catch (err: any) {
      setErro(err.message || 'Erro ao interpretar a pergunta.')
    } finally {
      setInterpretando(false)
    }
  }

  const handleExecutar = async (specObj?: EspecificacaoEstatistica) => {
    let specParaRodar = specObj
    if (!specParaRodar) {
      try {
        specParaRodar = JSON.parse(specEditavel)
      } catch {
        setErro('O JSON da especificação é inválido. Corrija a sintaxe antes de executar.')
        return
      }
    }

    setExecutando(true)
    setErro(null)
    try {
      const res = await api.executarEspecificacaoEstatistica(projectId, {
        specification: specParaRodar!,
        snapshot_id: snapshotId,
      })
      setResultado(res)
    } catch (err: any) {
      setErro(err.message || 'Erro ao executar a consulta estatística.')
    } finally {
      setExecutando(false)
    }
  }

  const handleSalvar = async () => {
    if (!specEditavel) return
    setSalvando(true)
    try {
      const specObj = JSON.parse(specEditavel)
      await api.salvarAnaliseEstatistica(projectId, {
        question: pergunta || 'Consulta estatística personalizada',
        specification: specObj,
      })
      await carregarAnalisesSalvas()
    } catch (err: any) {
      setErro(err.message || 'Erro ao salvar a análise.')
    } finally {
      setSalvando(false)
    }
  }

  const handleExcluirSalva = async (id: string) => {
    try {
      await api.excluirAnaliseEstatistica(projectId, id)
      setAnalisesSalvas((prev) => prev.filter((a) => a.id !== id))
    } catch {
      // erro
    }
  }

  const carregarSalva = (analise: AnaliseSalvaInfo) => {
    setPergunta(analise.question)
    setSpecEditavel(JSON.stringify(analise.specification, null, 2))
    handleExecutar(analise.specification)
  }

  const chartData = (resultado?.results || []).map((r) => {
    const labelGrupo = Object.values(r.grupo).join(' • ') || 'Total'
    return {
      nome: labelGrupo,
      valor: r.valor ?? 0,
      documentos: r.n_docs,
    }
  })

  return (
    <div className="painel-estatistica">
      {/* Cabeçalho */}
      <div className="painel-estatistica__cabecalho">
        <h3 className="painel-estatistica__titulo">
          <Sparkles className="painel-estatistica__titulo-icone" size={18} />
          Estatística Sob Demanda
        </h3>
        <p className="painel-estatistica__descricao">
          Pergunte em linguagem natural. A IA traduz em uma especificação JSON formal com vocabulário
          fechado e o servidor executa consultas determinísticas parametrizadas (doc 48 §9).
        </p>
      </div>

      {/* Caixa de Entrada de Pergunta */}
      <div className="painel-estatistica__busca">
        <div className="painel-estatistica__input-group">
          <input
            type="text"
            placeholder="Ex: qual a mediana de citações por ano, só dos incluídos?"
            value={pergunta}
            onChange={(e) => setPergunta(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleInterpretar(pergunta)}
            className="painel-estatistica__input"
          />
          <Button
            variant="primary"
            size="sm"
            onClick={() => handleInterpretar(pergunta)}
            disabled={interpretando || !pergunta.trim()}
            leftIcon={
              interpretando ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Sparkles size={14} />
              )
            }
          >
            Interpretar
          </Button>
        </div>

        {/* Sugestões de Perguntas */}
        <div className="painel-estatistica__exemplos">
          <span className="painel-estatistica__exemplos-label">Exemplos:</span>
          {EXEMPLOS_PERGUNTAS.map((ex, i) => (
            <button
              key={i}
              type="button"
              onClick={() => {
                setPergunta(ex)
                handleInterpretar(ex)
              }}
              className="painel-estatistica__exemplo-chip"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {erro && (
        <div className="painel-estatistica__alerta-erro">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      {/* Recusa explicada caso a pergunta não caiba */}
      {respostaInterp && !respostaInterp.supported && (
        <div className="painel-estatistica__alerta-recusa">
          <div className="painel-estatistica__alerta-recusa-head">
            <AlertCircle size={16} />
            <span>Pergunta fora do vocabulário fechado</span>
          </div>
          <p>{respostaInterp.explanation}</p>
          {respostaInterp.supported_vocabulary && (
            <div className="painel-estatistica__vocabulario">
              <div>
                <strong>Medidas suportadas:</strong>{' '}
                {respostaInterp.supported_vocabulary.medidas?.join(', ')}
              </div>
              <div>
                <strong>Agrupadores suportados:</strong>{' '}
                {respostaInterp.supported_vocabulary.agrupadores?.join(', ')}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Especificação Formal (Doc 48 §9.1, §9.3) */}
      {specEditavel && (
        <div className="painel-estatistica__spec">
          <div className="painel-estatistica__spec-header">
            <div className="painel-estatistica__spec-titulo">
              <Code2 size={16} className="text-accent" />
              <span>Especificação Formal Fechada (JSON Editável)</span>
            </div>
            <div className="painel-estatistica__spec-acoes">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleSalvar}
                disabled={salvando}
                leftIcon={<BookmarkPlus size={14} />}
              >
                {salvando ? 'Salvando...' : 'Salvar'}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleExecutar()}
                disabled={executando}
                leftIcon={
                  executando ? (
                    <RefreshCw size={14} className="animate-spin" />
                  ) : (
                    <Play size={14} />
                  )
                }
              >
                Reexecutar
              </Button>
            </div>
          </div>

          <textarea
            value={specEditavel}
            onChange={(e) => setSpecEditavel(e.target.value)}
            rows={6}
            className="painel-estatistica__textarea"
          />
        </div>
      )}

      {/* Resultados: Tabela e Gráfico */}
      {resultado && (
        <div className="painel-estatistica__resultado">
          <div className="painel-estatistica__resultado-header">
            <h4 className="painel-estatistica__resultado-titulo">
              <CheckCircle2 size={16} className="text-success" />
              Resultado: {resultado.results.length} grupos encontrados ({resultado.total_documents_analyzed} documentos analisados)
            </h4>
          </div>

          {/* Gráfico Recharts */}
          {chartData.length > 0 && (
            <div className="painel-estatistica__grafico-box">
              <div className="painel-estatistica__grafico-titulo">
                <BarChart2 size={14} />
                <span>Visualização Gráfica ({resultado.specification.medida})</span>
              </div>
              <div style={{ width: '100%', height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border-subtle)" />
                    <XAxis
                      dataKey="nome"
                      tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }}
                      angle={-20}
                      textAnchor="end"
                    />
                    <YAxis tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--color-bg-elevated)',
                        border: '1px solid var(--color-border)',
                        borderRadius: '6px',
                        fontSize: '12px',
                        color: 'var(--color-text-primary)',
                      }}
                    />
                    <Bar dataKey="valor" fill="var(--color-accent)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Tabela de Resultados */}
          <div className="painel-estatistica__tabela-wrapper">
            <table className="painel-estatistica__tabela">
              <thead>
                <tr>
                  {resultado.specification.por.map((col, idx) => (
                    <th key={idx} style={{ textTransform: 'capitalize' }}>
                      {col}
                    </th>
                  ))}
                  <th style={{ textAlign: 'right' }}>
                    Valor ({resultado.specification.medida})
                  </th>
                  <th style={{ textAlign: 'right' }}>Nº Documentos</th>
                </tr>
              </thead>
              <tbody>
                {resultado.results.map((linha, idx) => (
                  <tr key={idx}>
                    {resultado.specification.por.map((col, cIdx) => (
                      <td key={cIdx}>
                        {linha.grupo[col] || '—'}
                      </td>
                    ))}
                    <td className="painel-estatistica__tabela-valor">
                      {linha.valor !== null ? linha.valor : '—'}
                    </td>
                    <td className="painel-estatistica__tabela-docs">
                      {linha.n_docs}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Consultas Salvas e Reexecutáveis (Doc 48 §9.3) */}
      {analisesSalvas.length > 0 && (
        <div className="painel-estatistica__salvas">
          <div className="painel-estatistica__salvas-titulo">
            <BookmarkPlus size={14} className="text-accent" />
            <span>Análises Salvas no Projeto ({analisesSalvas.length})</span>
          </div>
          <div className="painel-estatistica__salvas-grid">
            {analisesSalvas.map((salva) => (
              <div key={salva.id} className="painel-estatistica__salva-card">
                <span
                  onClick={() => carregarSalva(salva)}
                  className="painel-estatistica__salva-texto"
                  title={salva.question}
                >
                  {salva.question}
                </span>
                <div className="painel-estatistica__salva-acoes">
                  <button
                    type="button"
                    onClick={() => carregarSalva(salva)}
                    className="painel-estatistica__btn-icon"
                    title="Carregar e reexecutar"
                  >
                    <Play size={13} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExcluirSalva(salva.id)}
                    className="painel-estatistica__btn-icon painel-estatistica__btn-icon--del"
                    title="Excluir"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
