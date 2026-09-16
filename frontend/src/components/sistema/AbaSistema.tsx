/**
 * Revsist — Aba Sistema: dados de uso e ciclo do beta (doc 52 §6.6).
 *
 * Só aparece para a conta dona, e todo dado que ela mostra chega do servidor
 * já agregado: não existe, em nenhuma subaba, uma linha por pessoa nem um
 * filtro por usuário. A aba 5 cuida de quem entra; esta, de como a plataforma
 * está sendo usada e de até quando.
 */

import { useState } from 'react'
import { Activity, AlertTriangle, BarChart3, Cpu, Database, Gauge, Server } from 'lucide-react'
import { Card, EmptyState, Select } from '@/components/ui'
import type { PeriodoDoSistema } from '@/types/api'
import { PERIODOS } from './formatos'
import { VisaoGeral } from './VisaoGeral'
import { ConsumoDeIA } from './ConsumoDeIA'
import { ErrosDoBeta } from './ErrosDoBeta'
import { DadosECiclo } from './DadosECiclo'
import './AbaSistema.css'

type Subaba = 'geral' | 'uso' | 'erros' | 'ia' | 'desempenho' | 'dados'

const SUBABAS: { id: Subaba; rotulo: string; icone: typeof Activity }[] = [
  { id: 'geral', rotulo: 'Visão geral', icone: Gauge },
  { id: 'uso', rotulo: 'Uso', icone: Activity },
  { id: 'erros', rotulo: 'Erros', icone: AlertTriangle },
  { id: 'ia', rotulo: 'Consumo de IA', icone: Cpu },
  { id: 'desempenho', rotulo: 'Desempenho', icone: BarChart3 },
  { id: 'dados', rotulo: 'Dados e ciclo do beta', icone: Database },
]

export function AbaSistema(): JSX.Element {
  const [subaba, setSubaba] = useState<Subaba>('geral')
  const [periodo, setPeriodo] = useState<PeriodoDoSistema>('30')
  const usaPeriodo = subaba === 'geral' || subaba === 'erros' || subaba === 'ia'

  return (
    <div className="settings-tab-content">
      <Card className="settings-card">
        <div className="admin-card-header">
          <span className="admin-card-icon" aria-hidden="true">
            <Server size={20} />
          </span>
          <div>
            <h2>Sistema: dados de uso e ciclo do beta</h2>
            <p className="admin-card-subtitle">
              Como a plataforma está sendo usada, o que está falhando e quanto a assistência consome. Tudo
              agregado: grupos com menos de cinco pessoas aparecem como "&lt; 5".
            </p>
          </div>
        </div>

        <div className="sis-barra">
          <div className="admin-tabs-nav sis-subabas" role="tablist" aria-label="Seções do Sistema">
            {SUBABAS.map(({ id, rotulo, icone: Icone }) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={subaba === id}
                className={`admin-tab-btn ${subaba === id ? 'active' : ''}`}
                onClick={() => setSubaba(id)}
              >
                <Icone size={14} aria-hidden="true" /> {rotulo}
              </button>
            ))}
          </div>

          {usaPeriodo && (
            <label className="sis-periodo">
              <span className="sis-muted">Período</span>
              <Select
                sizeVariant="sm"
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value as PeriodoDoSistema)}
                aria-label="Período"
              >
                {PERIODOS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.rotulo}
                  </option>
                ))}
              </Select>
            </label>
          )}
        </div>

        {subaba === 'geral' && <VisaoGeral periodo={periodo} onIrParaDados={() => setSubaba('dados')} />}
        {subaba === 'ia' && <ConsumoDeIA periodo={periodo} />}
        {subaba === 'erros' && <ErrosDoBeta periodo={periodo} />}
        {subaba === 'dados' && <DadosECiclo />}
        {subaba === 'uso' && (
          <EmptyState
            size="inline"
            icon={<Activity size={22} strokeWidth={1.25} aria-hidden="true" />}
            title="Os eventos de uso ainda não são enviados pela interface"
            description="Telas, ações e tempo ativo passam a chegar com a instrumentação da interface (doc 52, fase F4). O funil, a retenção e o mapa de frustração aparecem aqui quando houver dados."
          />
        )}
        {subaba === 'desempenho' && (
          <EmptyState
            size="inline"
            icon={<BarChart3 size={22} strokeWidth={1.25} aria-hidden="true" />}
            title="A medição de desempenho ainda não está ligada"
            description="Tempo de resposta por rota e tempo até a primeira tela útil entram na fase F6b do doc 52."
          />
        )}
      </Card>
    </div>
  )
}
