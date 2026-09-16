/**
 * Revsist — Aba Sistema › Consumo de IA.
 *
 * Responde a duas perguntas do beta: quanto custa, em tokens, cada operação
 * em cada modelo (Q-04), e com que frequência a cota acaba ou a cadeia de
 * reserva responde no lugar do modelo pedido (Q-05).
 */

import { useEffect, useState } from 'react'
import { Cpu, RefreshCw } from 'lucide-react'
import { EmptyState, toast } from '@/components/ui'
import { api } from '@/api/client'
import type { ConsumoDeIA as Consumo, GrupoDeConsumo, PeriodoDoSistema } from '@/types/api'
import { OPERACOES_DE_IA, RESULTADOS_DE_IA, formatarCompacto, formatarNumero } from './formatos'

export function ConsumoDeIA({ periodo }: { periodo: PeriodoDoSistema }): JSX.Element {
  const [dados, setDados] = useState<Consumo | null>(null)
  const [carregando, setCarregando] = useState(false)

  const carregar = async () => {
    try {
      setCarregando(true)
      setDados(await api.getConsumoDeIA(periodo))
    } catch (err: any) {
      toast.error('Falha ao carregar o consumo de IA', { description: err.message })
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodo])

  const vazio = dados && !dados.suprimido && !dados.total_de_chamadas

  return (
    <div className="admin-panel sis-painel">
      <div className="admin-toolbar">
        <h4 className="admin-table-title">Consumo de IA</h4>
        <div className="admin-toolbar-actions">
          <button type="button" className="btn-text-action" onClick={carregar} disabled={carregando}>
            <RefreshCw size={12} className={carregando ? 'animate-spin' : ''} /> Atualizar
          </button>
        </div>
      </div>

      {!dados ? (
        <p className="sis-muted">{carregando ? 'Carregando…' : 'Sem dados.'}</p>
      ) : vazio ? (
        <EmptyState
          size="inline"
          icon={<Cpu size={22} strokeWidth={1.25} aria-hidden="true" />}
          title="Nenhuma chamada de IA registrada no período"
          description="As chamadas passam a ser contadas quando a coleta está ativa. Cada tentativa entra, inclusive as recusadas por cota."
        />
      ) : (
        <>
          <div className="sis-indicadores">
            <div className="sis-indicador">
              <span className="sis-muted">Chamadas no período</span>
              <strong className="sis-indicador__valor">
                {dados.suprimido ? '< 5 pessoas' : formatarNumero(dados.total_de_chamadas)}
              </strong>
            </div>
            <div className="sis-indicador">
              <span className="sis-muted">Respondidas pela cadeia de reserva</span>
              <strong className="sis-indicador__valor">
                {dados.porcentagem_reserva === null ? '—' : `${dados.porcentagem_reserva.toLocaleString('pt-BR')}%`}
              </strong>
            </div>
            <div className="sis-indicador">
              <span className="sis-muted">Contagens estimadas</span>
              <strong className="sis-indicador__valor">
                {dados.porcentagem_estimada === null ? '—' : `${dados.porcentagem_estimada.toLocaleString('pt-BR')}%`}
              </strong>
            </div>
          </div>

          <TabelaDeGrupos
            titulo="Por provedor e modelo que respondeu"
            grupos={dados.por_provedor_e_modelo}
            rotular={([provedor, modelo]) => `${provedor} · ${modelo || '—'}`}
          />
          <TabelaDeGrupos
            titulo="Por operação"
            grupos={dados.por_operacao}
            rotular={([op]) => OPERACOES_DE_IA[op] ?? op}
          />
          <TabelaDeGrupos
            titulo="Por resultado da chamada"
            grupos={dados.por_resultado}
            rotular={([r]) => RESULTADOS_DE_IA[r] ?? r}
          />
        </>
      )}
    </div>
  )
}

function TabelaDeGrupos({
  titulo,
  grupos,
  rotular,
}: {
  titulo: string
  grupos: GrupoDeConsumo[]
  rotular: (chaves: string[]) => string
}): JSX.Element | null {
  if (!grupos.length) return null
  const maximo = Math.max(1, ...grupos.map((g) => g.tokens ?? 0))

  return (
    <section className="sis-cartao">
      <h5 className="sis-subtitulo">{titulo}</h5>
      <table className="sis-tabela">
        <thead>
          <tr>
            <th scope="col">Grupo</th>
            <th scope="col" className="sis-num">
              Chamadas
            </th>
            <th scope="col" className="sis-num">
              Tokens
            </th>
            <th scope="col" className="sis-num">
              Latência média
            </th>
          </tr>
        </thead>
        <tbody>
          {grupos.map((g) => (
            <tr key={g.chaves.join('|')}>
              <td>
                <span>{rotular(g.chaves)}</span>
                {!g.suprimido && (
                  <span className="sis-barra-horizontal" aria-hidden="true">
                    <span style={{ width: `${Math.round(((g.tokens ?? 0) / maximo) * 100)}%` }} />
                  </span>
                )}
              </td>
              <td className="sis-num">{g.suprimido ? '< 5' : formatarNumero(g.chamadas)}</td>
              <td className="sis-num">{g.suprimido ? '< 5' : formatarCompacto(g.tokens)}</td>
              <td className="sis-num">
                {g.suprimido || g.latencia_media_ms === null ? '—' : `${formatarNumero(g.latencia_media_ms)} ms`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
