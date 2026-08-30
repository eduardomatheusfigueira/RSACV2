import React from 'react'
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, RefreshCw } from 'lucide-react'
import type { ProtocolReadiness } from '@/types/api'
import { Card, Button } from '@/components/ui'
import './ProtocolStudio.css'

interface ProtocolReadinessCardProps {
  readiness: ProtocolReadiness | null
  loading?: boolean
  onRefresh?: () => void
  onNavigateToStage?: (stage: string) => void
}

/**
 * Medidor de prontidão e portões por etapa (doc 45 §13.1).
 *
 * O portão AVISA e explica; só bloqueia quando a execução é tecnicamente
 * impossível. Por isso o cartão distingue três estados — aprovado, bloqueante e
 * aviso — em vez dos dois que um "válido/inválido" sugeriria: um portão não
 * atendido mas não bloqueante é uma lacuna a mostrar, não um erro a impedir.
 */
export function ProtocolReadinessCard({
  readiness,
  loading = false,
  onRefresh,
}: ProtocolReadinessCardProps): JSX.Element | null {
  if (!readiness) return null

  const estadoDoPortao = (passed: boolean, isBlocking: boolean): 'passed' | 'blocking' | 'warning' =>
    passed ? 'passed' : isBlocking ? 'blocking' : 'warning'

  const iconeDoPortao = (estado: 'passed' | 'blocking' | 'warning') => {
    if (estado === 'passed') return <CheckCircle2 size={15} className="protocol-gate__icon-passed" />
    if (estado === 'blocking') return <XCircle size={15} className="protocol-gate__icon-blocking" />
    return <AlertTriangle size={15} className="protocol-gate__icon-warning" />
  }

  const veredito = (estado: 'passed' | 'blocking' | 'warning'): string =>
    estado === 'passed' ? 'Aprovado' : estado === 'blocking' ? 'Bloqueante' : 'Aviso'

  const faixaDaBarra =
    readiness.overall_percentage >= 80 ? 'is-high' : readiness.overall_percentage >= 50 ? 'is-mid' : 'is-low'

  const prontoParaExecucao = readiness.summary_badge.includes('Pronto')

  return (
    <Card className="protocol-readiness" surface="secundaria" relief="elevado" accented>
      <div className="protocol-readiness__head">
        <div className="protocol-readiness__identity">
          <span className="protocol-readiness__icon" aria-hidden="true">
            <ShieldCheck size={20} />
          </span>
          <div className="protocol-readiness__titles">
            <div className="protocol-readiness__title-row">
              <h3 className="protocol-readiness__title">Medidor de Prontidão Metodológica</h3>
              <span
                className={`protocol-status__chip ${prontoParaExecucao ? 'is-vigente' : 'is-rascunho'}`}
              >
                {readiness.summary_badge}
              </span>
            </div>
            <p className="protocol-readiness__hint">
              Validação a priori dos {readiness.gates.length} portões de integridade e completude do protocolo
            </p>
          </div>
        </div>

        <div className="protocol-readiness__score">
          <span className="protocol-readiness__pct">
            <span className="protocol-readiness__pct-value">{readiness.overall_percentage}%</span>
            <span className="protocol-readiness__pct-label">completude</span>
          </span>
          {onRefresh && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={loading}
              title="Recalcular prontidão"
            >
              <RefreshCw size={13} className={loading ? 'protocol-readiness__spin' : undefined} />
              <span>Verificar</span>
            </Button>
          )}
        </div>
      </div>

      <div
        className="protocol-readiness__bar"
        role="progressbar"
        aria-valuenow={readiness.overall_percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Completude do protocolo"
      >
        <div
          className={`protocol-readiness__bar-fill ${faixaDaBarra}`}
          style={{ width: `${readiness.overall_percentage}%` }}
        />
      </div>

      <div className="protocol-gates">
        {readiness.gates.map((gate) => {
          const estado = estadoDoPortao(gate.passed, gate.is_blocking)
          return (
            <div key={gate.gate_name} className={`protocol-gate is-${estado}`}>
              <div className="protocol-gate__head">
                <span className="protocol-gate__name">
                  {iconeDoPortao(estado)}
                  {gate.gate_name}
                </span>
                <span className="protocol-gate__verdict">{veredito(estado)}</span>
              </div>

              {gate.passed ? (
                <p className="protocol-gate__body">Requisitos mínimos satisfeitos.</p>
              ) : (
                <ul className="protocol-gate__missing">
                  {gate.missing.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}
