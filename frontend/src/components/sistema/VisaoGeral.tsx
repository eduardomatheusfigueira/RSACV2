/**
 * Revsist — Aba Sistema › Visão geral.
 *
 * Três perguntas, nesta ordem: em que ponto do beta estamos, a coleta pode
 * funcionar (portão), e o que os números do período dizem.
 */

import { useEffect, useState } from 'react'
import { CalendarClock, CheckCircle2, CircleAlert, RefreshCw, XCircle } from 'lucide-react'
import { Badge, Button, toast } from '@/components/ui'
import { api } from '@/api/client'
import type { CicloDoBeta, PeriodoDoSistema, ResumoDoSistema } from '@/types/api'
import { ESTADOS, dataCurta, dataHora, formatarAgregado, formatarCompacto } from './formatos'

export function VisaoGeral({
  periodo,
  onIrParaDados,
}: {
  periodo: PeriodoDoSistema
  onIrParaDados: () => void
}): JSX.Element {
  const [ciclo, setCiclo] = useState<CicloDoBeta | null>(null)
  const [resumo, setResumo] = useState<ResumoDoSistema | null>(null)
  const [carregando, setCarregando] = useState(false)

  const carregar = async () => {
    try {
      setCarregando(true)
      const [c, r] = await Promise.all([api.getCicloDoBeta(), api.getResumoDoSistema(periodo)])
      setCiclo(c)
      setResumo(r)
    } catch (err: any) {
      toast.error('Falha ao carregar o Sistema', { description: err.message })
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodo])

  if (!ciclo) {
    return <p className="sis-muted">{carregando ? 'Carregando…' : 'Sem dados.'}</p>
  }

  const estado = ESTADOS[ciclo.estado.estado]
  const hojeIso = new Date().toISOString().slice(0, 10)
  const avisoDeDecisao = ciclo.estado.estado !== 'encerrada' && hojeIso >= ciclo.aviso_de_decisao_em
  const pendencias = ciclo.portao.filter((i) => i.bloqueante && !i.ok)

  return (
    <div className="admin-panel sis-painel">
      <div className="admin-toolbar">
        <h4 className="admin-table-title">Visão geral</h4>
        <div className="admin-toolbar-actions">
          <button type="button" className="btn-text-action" onClick={carregar} disabled={carregando}>
            <RefreshCw size={12} className={carregando ? 'animate-spin' : ''} /> Atualizar
          </button>
        </div>
      </div>

      <section className="sis-cartao sis-ciclo" aria-labelledby="sis-ciclo-titulo">
        <div className="sis-ciclo__topo">
          <div>
            <p className="sis-muted" id="sis-ciclo-titulo">
              <CalendarClock size={12} aria-hidden="true" /> Ciclo do beta
            </p>
            <p className="sis-destaque">
              {ciclo.dias_restantes} {ciclo.dias_restantes === 1 ? 'dia restante' : 'dias restantes'}
            </p>
            <p className="sis-muted">
              {dataCurta(ciclo.inicio)} → {dataCurta(ciclo.fim)} · registros brutos descartados até{' '}
              {dataCurta(ciclo.descarte_final_em)}
            </p>
          </div>
          <Badge variant={estado.badge} size="sm">
            {estado.rotulo}
          </Badge>
        </div>

        <div
          className="sis-progresso"
          role="progressbar"
          aria-label="Progresso do beta"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(ciclo.progresso * 100)}
        >
          <div className="sis-progresso__barra" style={{ width: `${Math.round(ciclo.progresso * 1000) / 10}%` }} />
        </div>

        <p className="sis-muted">{estado.explicacao}</p>
        {ciclo.estado.motivo && (
          <p className="sis-muted">
            Última mudança: {dataHora(ciclo.estado.alterado_em)}
            {ciclo.estado.alterado_por ? ` por @${ciclo.estado.alterado_por}` : ''} — {ciclo.estado.motivo}
          </p>
        )}
        {avisoDeDecisao && (
          <p className="sis-alerta" role="status">
            <CircleAlert size={14} aria-hidden="true" /> Faltam menos de 60 dias. Decida se o beta será encerrado
            na data ou prorrogado — prorrogar exige nova versão do Aviso e dos Termos.
          </p>
        )}
      </section>

      <section className="sis-cartao" aria-labelledby="sis-portao-titulo">
        <h5 className="sis-subtitulo" id="sis-portao-titulo">
          Portão de ativação
        </h5>
        <ul className="sis-portao">
          {ciclo.portao.map((item) => (
            <li key={item.chave} className="sis-portao__item">
              {item.ok ? (
                <CheckCircle2 size={14} className="sis-ok" aria-label="atendido" />
              ) : item.bloqueante ? (
                <XCircle size={14} className="sis-falta" aria-label="pendente" />
              ) : (
                <CircleAlert size={14} className="sis-aviso" aria-label="informativo" />
              )}
              <span className="sis-portao__rotulo">{item.rotulo}</span>
              <span className="sis-muted">{item.detalhe}</span>
            </li>
          ))}
        </ul>
        {ciclo.estado.estado !== 'ativa' && ciclo.estado.estado !== 'encerrada' && (
          <div className="sis-rodape">
            <span className="sis-muted">
              {pendencias.length
                ? `Falta: ${pendencias.map((p) => p.rotulo.toLowerCase()).join('; ')}.`
                : 'Portão completo: a coleta pode ser ativada.'}
            </span>
            <Button variant="secondary" size="xs" onClick={onIrParaDados}>
              Ir para o controle da coleta
            </Button>
          </div>
        )}
      </section>

      {resumo && (
        <div className="sis-indicadores">
          <Indicador rotulo="Participantes ativos" valor={formatarAgregado(resumo.participantes_ativos)} />
          <Indicador
            rotulo="Tempo ativo mediano por sessão"
            valor={formatarAgregado(resumo.tempo_ativo_mediano_min, (n) => `${n.toLocaleString('pt-BR')} min`)}
          />
          <Indicador rotulo="Erros novos" valor={resumo.erros_novos.toLocaleString('pt-BR')} />
          <Indicador rotulo="Pessoas atingidas por erro" valor={formatarAgregado(resumo.pessoas_atingidas_por_erro)} />
          <Indicador rotulo="Tokens de IA" valor={formatarAgregado(resumo.tokens, formatarCompacto)} />
          <Indicador
            rotulo="Contas com coleta de uso desligada"
            valor={`${formatarAgregado(ciclo.participacao.coleta_desligada)} de ${ciclo.participacao.contas_ativas}`}
          />
        </div>
      )}
    </div>
  )
}

function Indicador({ rotulo, valor }: { rotulo: string; valor: string }): JSX.Element {
  return (
    <div className="sis-indicador">
      <span className="sis-muted">{rotulo}</span>
      <strong className="sis-indicador__valor">{valor}</strong>
    </div>
  )
}
