/**
 * Revsist — Batch Screening Modal & Live Progress
 * Modal interativo para configuração e acompanhamento em tempo real
 * da triagem em lote com Assistência.
 */

import { useEffect, useRef, useState } from 'react'
import {
  Sparkles,
  Zap,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  X,
  Sliders,
  ChevronRight,
  ShieldCheck,
  Check,
  Minimize2,
  ArrowRight,
  StopCircle,
  AlertTriangle,
} from 'lucide-react'
import { Dialog, DialogContent, DialogTitle, DialogClose } from '@/components/ui'
import './BatchScreeningModal.css'
import type { ItemDoLote, RitmoDoLote } from '@/types/api'
import { limitePadraoDoLote } from './limiteDoLote'

export interface BatchScreeningItem {
  id: string
  title: string
  decision: string
  confidence?: number
  justification?: string
}

export interface CurrentScreeningStudy {
  paper_id: string
  title: string
  authors?: string
  year?: string
  index?: number
  total?: number
}

interface BatchScreeningModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  pendingCount: number
  isRunning: boolean
  progress: {
    processed: number
    total: number
    percentage: number
    included: number
    excluded: number
    pending: number
    /** Paralelismo e pausa vigentes, ajustados pelo servidor. */
    ritmo?: RitmoDoLote | null
  } | null
  currentStudy: CurrentScreeningStudy | null
  /**
   * A relação do lote, na ordem de triagem.
   *
   * Substitui o antigo `activityFeed`, que listava só os últimos resultados. A
   * pergunta que a janela precisa responder é sobre o CONJUNTO — quais estudos
   * entraram, quais já foram, quais faltam —, e uma fila dos últimos eventos
   * nunca responde isso: quem abre a janela no meio, ou perde o canal por um
   * instante, fica sem o que passou.
   */
  itensDoLote: ItemDoLote[]
  /** O canal ao vivo está entregando? Falso = acompanhando por consulta. */
  canalAoVivo?: boolean
  onStartBatch: (limit: number, concurrency: number, pausa: number) => Promise<void>
  onCancelBatch: () => Promise<void>
}

/**
 * Os três ritmos oferecidos.
 *
 * `porMinuto` é uma estimativa para o pesquisador se situar, calculada para uma
 * resposta típica de ~8s do provedor. Não é promessa: o tempo de resposta varia
 * muito entre modelos e horários.
 */
/**
 * Os três ritmos oferecidos.
 *
 * `teto` é o MÁXIMO de estudos em paralelo, não um valor fixo: o lote começa
 * abaixo dele e se move sozinho — sobe enquanto o provedor aceita, recua assim
 * que ele recusa. Escolher um número fixo nunca funcionou aqui, porque o limite
 * real depende do plano, do modelo, de quantas chaves estão cadastradas e da
 * hora do dia. Alto demais derrubava o lote em recusas; baixo demais
 * desperdiçava minutos à toa.
 */
const RITMOS = {
  cauteloso: {
    rotulo: 'Cauteloso',
    teto: 2,
    pausa: 4,
    resumo: 'até 2 em paralelo',
    explicacao: 'Sobe pouco e espera bastante. É o que usar quando o provedor vem recusando por limite.',
  },
  equilibrado: {
    rotulo: 'Equilibrado',
    teto: 4,
    pausa: 1.5,
    resumo: 'até 4 em paralelo',
    explicacao: 'Começa com 2 e sobe até 4 se o provedor aceitar. Recua sozinho ao primeiro sinal de limite.',
  },
  rapido: {
    rotulo: 'Rápido',
    teto: 8,
    pausa: 0,
    resumo: 'até 8 em paralelo',
    explicacao: 'Aproveita várias chaves cadastradas ou plano pago. Recua igual, só parte de mais alto.',
  },
} as const

type ChaveDeRitmo = keyof typeof RITMOS

export function BatchScreeningModal({
  isOpen,
  onClose,
  projectId: _projectId,
  pendingCount,
  isRunning,
  progress,
  currentStudy,
  itensDoLote,
  canalAoVivo = true,
  onStartBatch,
  onCancelBatch,
}: BatchScreeningModalProps): JSX.Element | null {
  /* O limite acompanha o contador de pendentes até o pesquisador escolher um.
     Sem isto, o valor era calculado uma única vez — na montagem da tela, com o
     contador ainda em 0 — e o lote saía com limite 1. */
  const [limitOption, setLimitOption] = useState<number>(() => limitePadraoDoLote(pendingCount))
  const limiteEscolhidoRef = useRef(false)

  useEffect(() => {
    if (limiteEscolhidoRef.current) return
    setLimitOption(limitePadraoDoLote(pendingCount))
  }, [pendingCount])

  /* Reabrir a janela depois de um lote volta a sugerir o padrão: o pesquisador
     que triou 10 e voltou para triar o resto não deveria reencontrar o 10. */
  useEffect(() => {
    if (!isOpen) {
      limiteEscolhidoRef.current = false
    }
  }, [isOpen])

  const escolherLimite = (valor: number) => {
    limiteEscolhidoRef.current = true
    setLimitOption(valor)
  }
  /**
   * Ritmo da triagem.
   *
   * Antes havia só "concorrência", em múltiplos de 1x a 5x. Dois problemas:
   * o número não diz nada a quem não conhece a API por dentro, e limitar
   * quantos correm ao mesmo tempo NÃO limita a que velocidade as requisições
   * saem — com chamadas rápidas, mesmo um por vez ultrapassa o limite por
   * minuto do provedor. Cada ritmo agora fixa os dois controles.
   */
  const [ritmo, setRitmo] = useState<ChaveDeRitmo>('equilibrado')
  const { pausa, teto: concurrency } = RITMOS[ritmo]
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)

  /* Nada mais correndo, mas houve um lote: terminou por completo ou parou no
     meio. Os dois casos precisam da mesma saída na janela — sem esta distinção,
     um lote interrompido ficava sem nenhum botão no rodapé. */
  const isConcluded = !isRunning && progress !== null
  const isFinished = isConcluded && progress.processed >= progress.total
  const isStopped = isConcluded && progress.processed < progress.total

  const handleStart = async () => {
    try {
      setIsStarting(true)
      await onStartBatch(limitOption, concurrency, pausa)
    } finally {
      setIsStarting(false)
    }
  }

  const handleStop = async () => {
    try {
      setIsStopping(true)
      await onCancelBatch()
    } finally {
      setIsStopping(false)
    }
  }

  /* Contados da própria relação: se a janela mostra a lista, a legenda tem de
     concordar com ela — e não com um contador que veio por outro caminho. */
  const concluidos = itensDoLote.filter((i) => i.status === 'concluido').length
  const emAnalise = itensDoLote.filter((i) => i.status === 'em_analise').length
  const naFila = itensDoLote.filter((i) => i.status === 'na_fila').length
  const naoTriados = itensDoLote.filter((i) => i.status === 'nao_triado').length

  const effectiveTotal = progress?.total || limitOption || pendingCount
  const effectiveProcessed = progress?.processed || 0
  const effectivePercentage = progress ? progress.percentage : 0

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="batch-screening-modal rsac-dialog-content"
        showCloseButton={false}
        aria-describedby="batch-screening-subtitle"
      >
        {/* Header */}
        <div className="batch-modal-header">
          <div className="batch-modal-title-group">
            <div className={`batch-icon-badge ${isRunning ? 'pulse-active' : ''}`}>
              <Sparkles size={20} className="icon-sparkle" aria-hidden="true" />
            </div>
            <div>
              <DialogTitle asChild>
                <h2>Triagem em Lote com Assistência</h2>
              </DialogTitle>
              <p className="batch-modal-subtitle" id="batch-screening-subtitle">
                {isRunning
                  ? `Processando ${effectiveProcessed} de ${effectiveTotal} estudos pendentes...`
                  : isFinished
                    ? 'Triagem em lote finalizada com sucesso!'
                    : isStopped
                      ? `Triagem interrompida em ${effectiveProcessed} de ${effectiveTotal} estudos.`
                      : `Analise estudos pendentes contra os critérios do protocolo ativo.`}
              </p>
            </div>
          </div>

          <div className="batch-modal-header-actions">
            {isRunning && (
              <button
                type="button"
                className="btn-header-minimize"
                onClick={onClose}
                title="Minimizar e continuar navegando enquanto a Assistência tria em segundo plano"
              >
                <Minimize2 size={16} />
                <span>Minimizar</span>
              </button>
            )}
            <DialogClose className="batch-modal-close-btn" aria-label="Fechar" title="Fechar">
              <X size={18} aria-hidden="true" />
            </DialogClose>
          </div>
        </div>

        {/* Modal Body */}
        <div className="batch-modal-body">
          {/* STATE 1: SETUP (Quando não está rodando nem terminou) */}
          {!isRunning && !progress && (
            <div className="batch-setup-view">
              <div className="batch-info-card">
                <div className="batch-info-stat">
                  <span className="stat-label">Estudos Pendentes</span>
                  <span className="stat-value">{pendingCount}</span>
                </div>
                <div className="batch-info-desc">
                  <ShieldCheck size={16} className="icon-accent" />
                  <span>
                    A assistência avaliará cada estudo individualmente aplicando os critérios de
                    inclusão e exclusão do protocolo, preenchendo as observações acadêmicas e atribuindo a decisão.
                  </span>
                </div>
              </div>

              <div className="batch-config-grid">
                {/* Quantidade a Triar */}
                <div className="batch-config-card">
                  <div className="config-card-header">
                    <Zap size={16} className="icon-accent" />
                    <strong>Quantidade de Estudos a Triar</strong>
                  </div>
                  <div className="preset-buttons-group">
                    {[10, 25, 50, 100].map((preset) => {
                      if (preset > pendingCount && pendingCount > 0 && preset !== 10) return null
                      return (
                        <button
                          key={preset}
                          type="button"
                          className={`btn-preset ${limitOption === preset ? 'active' : ''}`}
                          onClick={() => escolherLimite(preset)}
                        >
                          {preset} estudos
                        </button>
                      )
                    })}
                    {pendingCount > 0 && (
                      <button
                        type="button"
                        className={`btn-preset ${limitOption === pendingCount ? 'active' : ''}`}
                        onClick={() => escolherLimite(pendingCount)}
                      >
                        Todos ({pendingCount})
                      </button>
                    )}
                  </div>
                  <div className="custom-limit-input">
                    <label htmlFor="batch-limit-input">Ou informe uma quantidade exata:</label>
                    <input
                      id="batch-limit-input"
                      type="number"
                      min={1}
                      max={pendingCount || 1000}
                      value={limitOption}
                      onChange={(e) => escolherLimite(Math.max(1, parseInt(e.target.value) || 1))}
                    />
                  </div>
                </div>

                {/* Ritmo */}
                <div className="batch-config-card">
                  <div className="config-card-header">
                    <Sliders size={16} className="icon-accent" />
                    <strong>Ritmo da Triagem</strong>
                  </div>
                  <p className="config-card-desc">
                    O ritmo define o <strong>teto</strong>, não um valor fixo: a triagem
                    começa abaixo dele, sobe enquanto o provedor aceita e recua sozinha
                    assim que ele recusa por limite.
                  </p>
                  <div className="ritmo-selector">
                    {(Object.keys(RITMOS) as ChaveDeRitmo[]).map((chave) => (
                      <button
                        key={chave}
                        type="button"
                        className={`btn-ritmo ${ritmo === chave ? 'active' : ''}`}
                        onClick={() => setRitmo(chave)}
                      >
                        <span className="btn-ritmo__nome">{RITMOS[chave].rotulo}</span>
                        <span className="btn-ritmo__taxa">{RITMOS[chave].resumo}</span>
                      </button>
                    ))}
                  </div>
                  <span className="concurrency-hint">{RITMOS[ritmo].explicacao}</span>
                </div>
              </div>
            </div>
          )}

          {/* STATE 2: LIVE RUNNING OU FINISHED */}
          {(isRunning || progress !== null) && (
            <div className="batch-live-view">
              {/* O canal caiu: a triagem segue, mas a tela passa a depender da
                  consulta periódica. Dizer isso evita que uma atualização mais
                  lenta seja lida como lote travado. */}
              {!canalAoVivo && isRunning && (
                <div className="batch-canal-aviso">
                  <RefreshCw size={13} />
                  <span>
                    Canal ao vivo indisponível — acompanhando por consulta ao servidor.
                    A triagem segue normalmente; só a tela atualiza mais devagar.
                  </span>
                </div>
              )}

              {/* Placar de Resultados em Tempo Real */}
              <div className="batch-live-stats-bar">
                <div className="live-stat-chip processed">
                  <span className="stat-label">Processados</span>
                  <span className="stat-value">
                    {effectiveProcessed} / {effectiveTotal}
                  </span>
                </div>
                <div className="live-stat-chip included">
                  <span className="stat-label">
                    <CheckCircle2 size={13} /> Incluídos
                  </span>
                  <span className="stat-value">{progress?.included || 0}</span>
                </div>
                <div className="live-stat-chip excluded">
                  <span className="stat-label">
                    <XCircle size={13} /> Excluídos
                  </span>
                  <span className="stat-value">{progress?.excluded || 0}</span>
                </div>
                <div className="live-stat-chip remaining">
                  <span className="stat-label">
                    <Clock size={13} /> Restantes
                  </span>
                  <span className="stat-value">{progress?.pending || 0}</span>
                </div>
              </div>

              {/* Barra de Progresso Principal */}
              <div className="batch-progress-bar-container">
                <div className="progress-info-row">
                  <span className="progress-status-label">
                    {isRunning ? (
                      <>
                        <RefreshCw size={14} className="animate-spin text-accent" /> Triando lote em andamento...
                      </>
                    ) : isStopped ? (
                      <>
                        <StopCircle size={14} /> Interrompida
                      </>
                    ) : (
                      <>
                        <Check size={14} className="text-success" /> Concluído
                      </>
                    )}
                  </span>
                  <span className="progress-percentage-label">{effectivePercentage}%</span>
                </div>
                <div className="progress-track">
                  <div
                    className={`progress-fill ${isRunning ? 'animate-shimmer' : ''}`}
                    style={{ width: `${Math.min(100, Math.max(0, effectivePercentage))}%` }}
                  />
                </div>
              </div>

              {/* Estudo Atualmente em Análise (Destaque do Processo) */}
              {isRunning && (
                <div className="current-analyzing-card animate-fade-in">
                  <div className="analyzing-header">
                    <span className="analyzing-pulse-tag">
                      <Sparkles size={13} /> {currentStudy ? 'Analisando agora' : 'Preparando envio à Assistência...'}
                    </span>
                    {currentStudy?.year && <span className="analyzing-year">{currentStudy.year}</span>}
                  </div>
                  <h4 className="analyzing-title">
                    {currentStudy ? currentStudy.title : 'Enviando estudo para avaliação de critérios com IA...'}
                  </h4>
                  {currentStudy?.authors ? (
                    <p className="analyzing-authors">{currentStudy.authors}</p>
                  ) : (
                    <p className="analyzing-authors" style={{ fontStyle: 'italic', opacity: 0.8 }}>
                      Aguardando retorno do modelo de IA...
                    </p>
                  )}
                </div>
              )}

              {/* Feed de Estudos Concluídos no Lote */}
              {/* ── A relação do lote ───────────────────────────────
                  Cada estudo com a sua situação, na ordem em que serão
                  triados. É o painel que responde "onde está o lote": o que
                  já foi decidido, o que está sendo analisado agora e o que
                  ainda está na fila. */}
              <div className="batch-roster">
                <div className="batch-roster__head">
                  <h5>Estudos deste lote ({itensDoLote.length})</h5>
                  <div className="batch-roster__legend">
                    {isRunning && progress?.ritmo && (
                      <span
                        className="roster-chip is-ritmo"
                        title={`Teto de ${progress.ritmo.teto}. Ajustado automaticamente conforme o provedor responde.`}
                      >
                        {progress.ritmo.paralelismo} em paralelo
                        {progress.ritmo.pausa > 0 ? ` · ${progress.ritmo.pausa}s` : ''}
                      </span>
                    )}
                    <span className="roster-chip is-concluido">
                      {concluidos} triado{concluidos === 1 ? '' : 's'}
                    </span>
                    <span className="roster-chip is-em_analise">{emAnalise} em análise</span>
                    <span className="roster-chip is-na_fila">{naFila} na fila</span>
                    {naoTriados > 0 && (
                      <span className="roster-chip is-nao_triado">
                        {naoTriados} sem resposta do provedor
                      </span>
                    )}
                  </div>
                </div>

                <ol className="batch-roster__list">
                  {itensDoLote.length === 0 ? (
                    <li className="batch-roster__empty">
                      <RefreshCw size={16} className="animate-spin icon-accent" />
                      <span>Selecionando os estudos do lote...</span>
                    </li>
                  ) : (
                    itensDoLote.map((item, idx) => (
                      <li key={item.id || idx} className={`roster-item is-${item.status}`}>
                        <span className="roster-item__pos">{idx + 1}</span>

                        <span className="roster-item__estado">
                          {item.status === 'concluido' ? (
                            <span
                              className={`badge-decision badge-${(item.decision || '').toLowerCase()}`}
                            >
                              {item.decision === 'Incluído' ? (
                                <CheckCircle2 size={12} />
                              ) : item.decision === 'Excluído' ? (
                                <XCircle size={12} />
                              ) : (
                                <Clock size={12} />
                              )}
                              {item.decision || 'Sem decisão'}
                            </span>
                          ) : item.status === 'em_analise' ? (
                            <span className="roster-estado-tag em-analise">
                              <RefreshCw size={12} className="animate-spin" /> Analisando
                            </span>
                          ) : item.status === 'nao_triado' ? (
                            <span className="roster-estado-tag nao-triado">
                              <AlertTriangle size={12} /> Não triado
                            </span>
                          ) : (
                            <span className="roster-estado-tag na-fila">
                              <Clock size={12} /> Na fila
                            </span>
                          )}
                        </span>

                        <span className="roster-item__corpo">
                          <span className="roster-item__titulo">{item.title}</span>
                          {(item.authors || item.year) && (
                            <span className="roster-item__meta">
                              {[item.authors, item.year].filter(Boolean).join(' · ')}
                            </span>
                          )}
                          {(item.status === 'concluido' || item.status === 'nao_triado') &&
                            item.justification && (
                              <span className="roster-item__justificativa">
                                {item.justification}
                              </span>
                            )}
                        </span>

                        {item.status === 'concluido' && item.confidence != null && (
                          <span className="roster-item__conf" title="Confiança declarada pela assistência">
                            {Math.round(item.confidence * 100)}%
                          </span>
                        )}
                      </li>
                    ))
                  )}
                </ol>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="batch-modal-footer">
          <div className="batch-footer-left">
            {isRunning ? (
              <span className="batch-status-note">
                <RefreshCw size={13} className="animate-spin text-accent" /> As decisões estão sendo gravadas em tempo real no banco de dados.
              </span>
            ) : isFinished ? (
              <span className="batch-status-note text-success">
                <Check size={14} /> Fila atualizada. Todos os estudos do lote foram processados.
              </span>
            ) : isStopped ? (
              <span className="batch-status-note">
                As decisões tomadas até a parada foram gravadas. Os demais estudos seguem pendentes.
              </span>
            ) : (
              <span className="batch-status-note">
                Modo assistido: as decisões podem ser revistas ou alteradas a qualquer momento.
              </span>
            )}
          </div>

          <div className="batch-footer-right">
            {!isRunning && !progress && (
              <>
                <button type="button" className="btn-secondary" onClick={onClose}>
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleStart}
                  disabled={isStarting || pendingCount === 0}
                  /* Sem pendentes não há lote — mas um botão apagado sem
                     explicação é indistinguível de um botão quebrado, que foi
                     como este apareceu quando o contador não carregava. */
                  title={
                    pendingCount === 0
                      ? 'Nenhum estudo pendente de triagem neste projeto.'
                      : `Triar os próximos ${limitOption} estudos pendentes com assistência.`
                  }
                >
                  {isStarting ? (
                    <>
                      <RefreshCw size={15} className="animate-spin" /> Iniciando...
                    </>
                  ) : (
                    <>
                      <Sparkles size={15} /> Iniciar Triagem em Lote ({limitOption})
                    </>
                  )}
                </button>
              </>
            )}

            {isRunning && (
              <>
                {/* A triagem consome cota paga a cada estudo. Sem uma parada à
                    mão, um lote disparado por engano só terminava fechando o
                    programa — e mesmo isso deixava o servidor triando. */}
                <button
                  type="button"
                  className="btn-danger"
                  onClick={handleStop}
                  disabled={isStopping}
                  title="Interromper a triagem em lote agora"
                >
                  {isStopping ? (
                    <>
                      <RefreshCw size={15} className="animate-spin" /> Parando...
                    </>
                  ) : (
                    <>
                      <StopCircle size={15} /> Parar Triagem
                    </>
                  )}
                </button>
                <button type="button" className="btn-secondary" onClick={onClose}>
                  Acompanhar em Segundo Plano <ChevronRight size={15} />
                </button>
              </>
            )}

            {isConcluded && (
              <button type="button" className="btn-primary" onClick={onClose}>
                Concluir e Ver Fila <ArrowRight size={15} />
              </button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
