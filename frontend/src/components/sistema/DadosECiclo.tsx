/**
 * Revsist — Aba Sistema › Dados e ciclo do beta (doc 52 §6.6.3 e §6.6.4).
 *
 * A metade que age. Três cuidados orientam a tela:
 *
 *   * **Ativar** só fica disponível com o portão inteiro atendido — e o
 *     servidor confere de novo, porque a tela pode estar desatualizada;
 *   * **Encerrar** pede que se digite ENCERRAR, porque não tem volta;
 *   * **Prorrogar** não é um botão. A data de fim está no Aviso que cada
 *     pessoa aceitou; a tela explica o procedimento no lugar de oferecer um
 *     atalho que contornaria esse aceite.
 */

import { useEffect, useState } from 'react'
import { Download, Flag, History, Pause, Play, RefreshCw, Search, Trash2, UserSearch } from 'lucide-react'
import { Badge, Button, Input, toast } from '@/components/ui'
import { api } from '@/api/client'
import type { AcaoDoSistema, CicloDoBeta, ContagensDeUso, TabelaDeDadosDeUso } from '@/types/api'
import { ESTADOS, baixarJson, dataCurta, dataHora, formatarNumero } from './formatos'

const ROTULOS_DE_ACAO: Record<string, string> = {
  coleta_ativar: 'Coleta ativada',
  coleta_pausar: 'Coleta pausada',
  coleta_encerrar: 'Beta encerrado',
  retencao_aplicar: 'Retenção aplicada',
  erro_acompanhar: 'Defeito atualizado',
  titular_consultar: 'Pedido de titular: consulta',
  titular_exportar: 'Pedido de titular: exportação',
  titular_eliminar: 'Pedido de titular: eliminação',
}

export function DadosECiclo(): JSX.Element {
  const [ciclo, setCiclo] = useState<CicloDoBeta | null>(null)
  const [tabelas, setTabelas] = useState<TabelaDeDadosDeUso[]>([])
  const [ultimaRetencao, setUltimaRetencao] = useState<string | null>(null)
  const [diario, setDiario] = useState<AcaoDoSistema[]>([])
  const [carregando, setCarregando] = useState(false)
  const [ocupado, setOcupado] = useState<string | null>(null)

  const [motivo, setMotivo] = useState('')
  const [confirmacao, setConfirmacao] = useState('')

  const [email, setEmail] = useState('')
  const [contagens, setContagens] = useState<ContagensDeUso | null>(null)
  const [confirmacaoTitular, setConfirmacaoTitular] = useState('')

  const carregar = async () => {
    try {
      setCarregando(true)
      const [c, d, a] = await Promise.all([api.getCicloDoBeta(), api.getDadosDeUso(), api.getDiarioDoSistema(30)])
      setCiclo(c)
      setTabelas(d.tabelas)
      setUltimaRetencao(d.ultima_retencao_em)
      setDiario(a.itens)
    } catch (err: any) {
      toast.error('Falha ao carregar os dados do Sistema', { description: err.message })
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregar()
  }, [])

  const executar = async (chave: string, acao: () => Promise<unknown>, sucesso: string) => {
    try {
      setOcupado(chave)
      await acao()
      toast.success(sucesso)
      await carregar()
      return true
    } catch (err: any) {
      toast.error('A ação não foi concluída', { description: err.message })
      return false
    } finally {
      setOcupado(null)
    }
  }

  const mudarColeta = async (acao: 'ativar' | 'pausar' | 'encerrar') => {
    const rotulo = { ativar: 'Coleta ativada', pausar: 'Coleta pausada', encerrar: 'Beta encerrado' }[acao]
    const ok = await executar(acao, () => api.mudarColeta(acao, { motivo, confirmacao }), rotulo)
    if (ok) {
      setMotivo('')
      setConfirmacao('')
    }
  }

  const consultar = async () => {
    if (!email.trim()) return
    try {
      setOcupado('consultar')
      const res = await api.consultarTitular(email.trim())
      setContagens(res.contagens)
      carregar()
    } catch (err: any) {
      setContagens(null)
      toast.error('Consulta não concluída', { description: err.message })
    } finally {
      setOcupado(null)
    }
  }

  const exportar = () =>
    executar(
      'exportar',
      async () => baixarJson('revsist-dados-de-uso-do-titular.json', await api.exportarTitular(email.trim())),
      'Pacote gerado — envie ao titular pelo canal do pedido'
    )

  const eliminar = async () => {
    const ok = await executar(
      'eliminar',
      async () => {
        await api.eliminarTitular(email.trim(), confirmacaoTitular)
        setContagens({ eventos: 0, erros: 0, chamadas_ia: 0 })
      },
      'Dados de uso da conta apagados'
    )
    if (ok) setConfirmacaoTitular('')
  }

  if (!ciclo) {
    return <p className="sis-muted">{carregando ? 'Carregando…' : 'Sem dados.'}</p>
  }

  const estado = ciclo.estado.estado
  const pode = (destino: string) => ciclo.estado.transicoes.includes(destino as never)
  const pendencias = ciclo.portao.filter((i) => i.bloqueante && !i.ok)

  return (
    <div className="admin-panel sis-painel">
      <div className="admin-toolbar">
        <h4 className="admin-table-title">Dados e ciclo do beta</h4>
        <div className="admin-toolbar-actions">
          <button type="button" className="btn-text-action" onClick={carregar} disabled={carregando}>
            <RefreshCw size={12} className={carregando ? 'animate-spin' : ''} /> Atualizar
          </button>
        </div>
      </div>

      {/* ── Controle da coleta ── */}
      <section className="sis-cartao" aria-labelledby="sis-controle-titulo">
        <div className="sis-ciclo__topo">
          <h5 className="sis-subtitulo" id="sis-controle-titulo">
            Controle da coleta
          </h5>
          <Badge variant={ESTADOS[estado].badge} size="sm">
            {ESTADOS[estado].rotulo}
          </Badge>
        </div>
        <p className="sis-muted">{ESTADOS[estado].explicacao}</p>

        {estado === 'encerrada' ? (
          <p className="sis-muted">
            Encerrado em {dataHora(ciclo.estado.alterado_em)}
            {ciclo.estado.motivo ? ` — ${ciclo.estado.motivo}` : ''}.
          </p>
        ) : (
          <>
            <div className="sis-formulario">
              <label className="sis-campo-longo">
                <span className="sis-muted">Motivo (obrigatório para pausar ou encerrar)</span>
                <Input
                  sizeVariant="sm"
                  value={motivo}
                  maxLength={300}
                  placeholder="Incidente na instrumentação da triagem"
                  onChange={(e) => setMotivo(e.target.value)}
                />
              </label>
            </div>
            <div className="sis-acoes">
              {pode('ativa') && (
                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={<Play size={13} />}
                  loading={ocupado === 'ativar'}
                  disabled={!ciclo.pode_ativar || ocupado !== null}
                  title={pendencias.length ? `Falta: ${pendencias.map((p) => p.rotulo).join('; ')}` : undefined}
                  onClick={() => mudarColeta('ativar')}
                >
                  Ativar coleta
                </Button>
              )}
              {pode('pausada') && (
                <Button
                  variant="secondary"
                  size="sm"
                  leftIcon={<Pause size={13} />}
                  loading={ocupado === 'pausar'}
                  disabled={!motivo.trim() || ocupado !== null}
                  onClick={() => mudarColeta('pausar')}
                >
                  Pausar coleta
                </Button>
              )}
            </div>
            {pode('ativa') && pendencias.length > 0 && (
              <p className="sis-muted">Para ativar, falta: {pendencias.map((p) => p.rotulo.toLowerCase()).join('; ')}.</p>
            )}

            <div className="sis-perigo">
              <div>
                <strong>Encerrar o beta agora</strong>
                <p className="sis-muted">
                  Irreversível. A coleta para, e os eventos brutos são descartados em 30 dias. Um novo ciclo exige
                  nova data e nova versão do Aviso e dos Termos.
                </p>
              </div>
              <div className="sis-acoes">
                <Input
                  sizeVariant="sm"
                  value={confirmacao}
                  placeholder="Digite ENCERRAR"
                  aria-label="Confirmação para encerrar o beta"
                  onChange={(e) => setConfirmacao(e.target.value)}
                />
                <Button
                  variant="destructive"
                  size="sm"
                  leftIcon={<Flag size={13} />}
                  loading={ocupado === 'encerrar'}
                  disabled={confirmacao !== 'ENCERRAR' || !motivo.trim() || ocupado !== null}
                  onClick={() => mudarColeta('encerrar')}
                >
                  Encerrar o beta
                </Button>
              </div>
            </div>
          </>
        )}
      </section>

      {/* ── Ciclo de um ano ── */}
      <section className="sis-cartao" aria-labelledby="sis-prazo-titulo">
        <h5 className="sis-subtitulo" id="sis-prazo-titulo">
          O ciclo de um ano
        </h5>
        <table className="sis-tabela">
          <tbody>
            <tr>
              <th scope="row">Início do beta</th>
              <td>{dataCurta(ciclo.inicio)}</td>
            </tr>
            <tr>
              <th scope="row">Aviso de decisão (60 dias antes)</th>
              <td>{dataCurta(ciclo.aviso_de_decisao_em)}</td>
            </tr>
            <tr>
              <th scope="row">Fim do beta</th>
              <td>
                <strong>{dataCurta(ciclo.fim)}</strong> · {ciclo.dias_restantes} dias restantes
              </td>
            </tr>
            <tr>
              <th scope="row">Descarte final dos eventos brutos</th>
              <td>{dataCurta(ciclo.descarte_final_em)}</td>
            </tr>
          </tbody>
        </table>
        <p className="sis-muted">
          <strong>Por que prorrogar não é um botão:</strong> a data de fim está escrita no Aviso de Privacidade que
          cada pessoa aceitou. Para prorrogar, altere <code>RSAC_BETA_DURACAO_DIAS</code>, publique o Aviso e os Termos
          com a nova data, suba <code>terms_version</code> e faça o deploy. A coleta de cada pessoa só continua depois
          que ela aceitar a nova versão.
        </p>
      </section>

      {/* ── Inventário e retenção ── */}
      <section className="sis-cartao" aria-labelledby="sis-inventario-titulo">
        <div className="sis-ciclo__topo">
          <h5 className="sis-subtitulo" id="sis-inventario-titulo">
            Inventário e retenção
          </h5>
          <Button
            variant="secondary"
            size="xs"
            leftIcon={<Trash2 size={12} />}
            loading={ocupado === 'retencao'}
            disabled={ocupado !== null}
            onClick={() => executar('retencao', () => api.aplicarRetencaoAgora(), 'Retenção aplicada')}
          >
            Aplicar retenção agora
          </Button>
        </div>
        <table className="sis-tabela">
          <thead>
            <tr>
              <th scope="col">Dado</th>
              <th scope="col" className="sis-num">
                Registros
              </th>
              <th scope="col">Mais antigo</th>
              <th scope="col">Prazo</th>
              <th scope="col">Próximo descarte</th>
            </tr>
          </thead>
          <tbody>
            {tabelas.map((t) => (
              <tr key={t.chave}>
                <td>{t.rotulo}</td>
                <td className="sis-num">{formatarNumero(t.linhas)}</td>
                <td>{dataCurta(t.mais_antigo)}</td>
                <td>{t.prazo}</td>
                <td>{dataCurta(t.proximo_descarte)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="sis-muted">Última retenção neste processo: {dataHora(ultimaRetencao)}</p>
      </section>

      {/* ── Pedido de titular ── */}
      <section className="sis-cartao" aria-labelledby="sis-titular-titulo">
        <h5 className="sis-subtitulo" id="sis-titular-titulo">
          <UserSearch size={14} aria-hidden="true" /> Pedido de titular recebido por e-mail
        </h5>
        <p className="sis-muted">
          Use só para atender quem escreveu ao canal do controlador. A consulta mostra contagens; exportar e apagar
          ficam registrados no ROPA e no diário, sem o e-mail informado.
        </p>
        <div className="sis-formulario">
          <label className="sis-campo-longo">
            <span className="sis-muted">E-mail informado no pedido</span>
            <Input
              sizeVariant="sm"
              type="email"
              value={email}
              placeholder="pessoa@universidade.br"
              onChange={(e) => {
                setEmail(e.target.value)
                setContagens(null)
              }}
              onKeyDown={(e) => e.key === 'Enter' && consultar()}
            />
          </label>
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Search size={13} />}
            loading={ocupado === 'consultar'}
            disabled={!email.trim() || ocupado !== null}
            onClick={consultar}
          >
            Consultar contagens
          </Button>
        </div>

        {contagens && (
          <div className="sis-titular">
            <p>
              <strong>{formatarNumero(contagens.eventos)}</strong> eventos ·{' '}
              <strong>{formatarNumero(contagens.erros)}</strong> erros ·{' '}
              <strong>{formatarNumero(contagens.chamadas_ia)}</strong> chamadas de IA
            </p>
            <div className="sis-acoes">
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<Download size={13} />}
                loading={ocupado === 'exportar'}
                disabled={ocupado !== null}
                onClick={exportar}
              >
                Exportar para o titular
              </Button>
              <Input
                sizeVariant="sm"
                value={confirmacaoTitular}
                placeholder="Digite APAGAR"
                aria-label="Confirmação para apagar os dados de uso da conta"
                onChange={(e) => setConfirmacaoTitular(e.target.value)}
              />
              <Button
                variant="destructive"
                size="sm"
                leftIcon={<Trash2 size={13} />}
                loading={ocupado === 'eliminar'}
                disabled={confirmacaoTitular !== 'APAGAR' || ocupado !== null}
                onClick={eliminar}
              >
                Apagar dados de uso
              </Button>
            </div>
          </div>
        )}
      </section>

      {/* ── Diário ── */}
      <section className="sis-cartao" aria-labelledby="sis-diario-titulo">
        <h5 className="sis-subtitulo" id="sis-diario-titulo">
          <History size={14} aria-hidden="true" /> Diário de ações
        </h5>
        {diario.length === 0 ? (
          <p className="sis-muted">Nenhuma ação registrada ainda.</p>
        ) : (
          <ul className="sis-diario">
            {diario.map((a, i) => (
              <li key={`${a.executada_em}-${i}`}>
                <span className="sis-muted">{dataHora(a.executada_em)}</span>
                <strong>{ROTULOS_DE_ACAO[a.acao] ?? a.acao}</strong>
                <span>{a.resultado}</span>
                <span className="sis-muted">@{a.executada_por}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
