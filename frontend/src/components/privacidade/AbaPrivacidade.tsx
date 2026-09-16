/**
 * Revsist — Configurações › Privacidade e dados de uso (doc 52 §6.7).
 *
 * É a contrapartida do que o Aviso promete na seção "Dados de uso durante o
 * beta": o interruptor que desliga o registro, a lista do que já foi
 * registrado — em linguagem comum, para ninguém ter de acreditar na descrição
 * — e o consumo de IA que saiu da própria chave de quem está olhando.
 *
 * Diferente da aba Sistema, aqui não há supressão nem agregado: são os dados
 * de uma pessoa só, mostrados a ela mesma.
 */

import { useEffect, useState } from 'react'
import { Cpu, Eye, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react'
import { Badge, Button, Card, EmptyState, toast } from '@/components/ui'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/useAuthStore'
import type { MeusRegistrosDeUso, SituacaoDeUso } from '@/types/api'
import './AbaPrivacidade.css'

const dataHora = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

const dataCurta = (iso: string) =>
  new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString('pt-BR')

const numero = (n: number) => n.toLocaleString('pt-BR')

const OPERACOES: Record<string, string> = {
  triagem: 'Triagem',
  sugestao_protocolo: 'Sugestão de protocolo',
  assistencia_campo: 'Assistência de campo',
  extracao: 'Extração',
  teste_conexao: 'Teste de conexão',
  bibliometria_tesauro: 'Tesauro',
}

export function AbaPrivacidade(): JSX.Element {
  const { refreshUser } = useAuthStore()
  const [situacao, setSituacao] = useState<SituacaoDeUso | null>(null)
  const [registros, setRegistros] = useState<MeusRegistrosDeUso | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [ocupado, setOcupado] = useState<string | null>(null)

  const carregar = async () => {
    try {
      setCarregando(true)
      setSituacao(await api.getSituacaoDeUso())
    } catch (err: any) {
      toast.error('Falha ao carregar a situação da coleta', { description: err.message })
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregar()
  }, [])

  const alternar = async () => {
    if (!situacao) return
    try {
      setOcupado('interruptor')
      const nova = await api.alterarColetaDeUso(!situacao.coleta_ativa)
      setSituacao(nova)
      void refreshUser()
      toast.success(
        nova.coleta_ativa
          ? 'Registro de uso religado'
          : 'Registro de uso desligado — nenhum recurso deixa de funcionar'
      )
    } catch (err: any) {
      toast.error('Não foi possível alterar', { description: err.message })
    } finally {
      setOcupado(null)
    }
  }

  const apagar = async () => {
    if (!window.confirm('Apagar tudo o que foi registrado sobre o seu uso? A ação não tem volta.')) {
      return
    }
    try {
      setOcupado('apagar')
      setSituacao(await api.apagarMeusDadosDeUso())
      setRegistros(null)
      toast.success('Seus registros de uso foram apagados')
    } catch (err: any) {
      toast.error('Não foi possível apagar', { description: err.message })
    } finally {
      setOcupado(null)
    }
  }

  const verRegistros = async () => {
    try {
      setOcupado('registros')
      setRegistros(await api.getMeusRegistrosDeUso())
    } catch (err: any) {
      toast.error('Falha ao carregar os registros', { description: err.message })
    } finally {
      setOcupado(null)
    }
  }

  return (
    <div className="settings-tab-content">
      <Card className="settings-card">
        <div className="admin-card-header">
          <span className="admin-card-icon" aria-hidden="true">
            <ShieldCheck size={20} />
          </span>
          <div>
            <h2>Privacidade e dados de uso</h2>
            <p className="admin-card-subtitle">
              O que o Revsist registra sobre o seu uso durante o beta, como desligar e como apagar.
              O detalhe está no <a href="/privacidade#uso-beta" target="_blank" rel="noopener noreferrer">Aviso de Privacidade</a>.
            </p>
          </div>
        </div>

        {!situacao ? (
          <p className="priv-muted">{carregando ? 'Carregando…' : 'Sem dados.'}</p>
        ) : (
          <div className="admin-panel priv-painel">
            {/* ── Interruptor ── */}
            <section className="priv-cartao">
              <div className="priv-linha">
                <div>
                  <h4 className="priv-titulo">Compartilhar dados de uso do beta</h4>
                  <p className="priv-muted">
                    Telas abertas, ações acionadas por nome fixo e tempo ativo. Nunca o conteúdo da sua
                    pesquisa, o que você digita ou a posição dos seus cliques.
                  </p>
                </div>
                <div className="priv-acoes">
                  <Badge variant={situacao.coleta_ativa ? 'success' : 'neutral'} size="sm">
                    {situacao.coleta_ativa ? 'Ligado' : 'Desligado'}
                  </Badge>
                  <Button
                    variant={situacao.coleta_ativa ? 'secondary' : 'primary'}
                    size="sm"
                    loading={ocupado === 'interruptor'}
                    disabled={ocupado !== null}
                    onClick={alternar}
                  >
                    {situacao.coleta_ativa ? 'Desligar' : 'Ligar'}
                  </Button>
                </div>
              </div>
              <p className="priv-muted">
                {situacao.coleta_em_vigor
                  ? 'A coleta está em vigor nesta instalação.'
                  : 'Nada está sendo registrado agora — a coleta não está ativa nesta instalação.'}{' '}
                O beta termina em {dataCurta(situacao.beta_fim)}, e com ele a coleta.
                {situacao.alterada_em ? ` Sua última escolha: ${dataHora(situacao.alterada_em)}.` : ''}
              </p>
              <p className="priv-muted">
                Erros e consumo de IA continuam registrados mesmo com o interruptor desligado: os
                primeiros para corrigir defeitos, o segundo para mostrar a você o que a sua chave
                gastou.
              </p>
            </section>

            {/* ── O que existe hoje ── */}
            <section className="priv-cartao">
              <div className="priv-linha">
                <h4 className="priv-titulo">O que existe registrado sobre você</h4>
                <div className="priv-acoes">
                  <Button
                    variant="secondary"
                    size="sm"
                    leftIcon={<Eye size={13} />}
                    loading={ocupado === 'registros'}
                    disabled={ocupado !== null}
                    onClick={verRegistros}
                  >
                    Ver o que foi registrado
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    leftIcon={<Trash2 size={13} />}
                    loading={ocupado === 'apagar'}
                    disabled={ocupado !== null}
                    onClick={apagar}
                  >
                    Apagar meus registros
                  </Button>
                </div>
              </div>
              <div className="priv-contagens">
                <span>
                  <strong>{numero(situacao.contagens.eventos)}</strong> registros de uso
                </span>
                <span>
                  <strong>{numero(situacao.contagens.erros)}</strong> erros
                </span>
                <span>
                  <strong>{numero(situacao.contagens.chamadas_ia)}</strong> chamadas de IA
                </span>
              </div>
              <p className="priv-muted">
                Ao eliminar sua conta, tudo isto é apagado junto. Você também pode baixar esses
                registros na exportação completa, em <em>Backup &amp; Portabilidade</em>.
              </p>
            </section>

            {/* ── Consumo de IA ── */}
            {registros && (
              <section className="priv-cartao">
                <h4 className="priv-titulo">
                  <Cpu size={14} aria-hidden="true" /> Seu consumo de IA
                </h4>
                {registros.consumo_de_ia.length === 0 ? (
                  <p className="priv-muted">Nenhuma chamada de IA registrada.</p>
                ) : (
                  <>
                    <p className="priv-muted">
                      Total: <strong>{numero(registros.tokens_total)}</strong> tokens, gastos com as suas
                      próprias chaves.
                    </p>
                    <table className="priv-tabela">
                      <thead>
                        <tr>
                          <th scope="col">Dia</th>
                          <th scope="col">Provedor e modelo</th>
                          <th scope="col">Operação</th>
                          <th scope="col" className="priv-num">
                            Chamadas
                          </th>
                          <th scope="col" className="priv-num">
                            Tokens
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {registros.consumo_de_ia.map((c, i) => (
                          <tr key={`${c.dia}-${c.modelo}-${c.operacao}-${i}`}>
                            <td>{dataCurta(c.dia)}</td>
                            <td>
                              {c.provedor}
                              {c.modelo ? ` · ${c.modelo}` : ''}
                            </td>
                            <td>{OPERACOES[c.operacao] ?? c.operacao}</td>
                            <td className="priv-num">{numero(c.chamadas)}</td>
                            <td className="priv-num">{numero(c.tokens)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </>
                )}
              </section>
            )}

            {/* ── Registros em linguagem comum ── */}
            {registros && (
              <section className="priv-cartao">
                <div className="priv-linha">
                  <h4 className="priv-titulo">Seus registros, um a um</h4>
                  <button
                    type="button"
                    className="btn-text-action"
                    onClick={verRegistros}
                    disabled={ocupado !== null}
                  >
                    <RefreshCw size={12} /> Atualizar
                  </button>
                </div>
                {registros.eventos.length === 0 && registros.erros.length === 0 ? (
                  <EmptyState
                    size="inline"
                    icon={<Eye size={22} strokeWidth={1.25} aria-hidden="true" />}
                    title="Nada registrado sobre o seu uso"
                    description="Ou a coleta não está ativa, ou você a desligou, ou ainda não houve o que registrar."
                  />
                ) : (
                  <ul className="priv-registros">
                    {[...registros.erros, ...registros.eventos].map((r, i) => (
                      <li key={`${r.ocorrido_em}-${i}`}>
                        <span className="priv-muted">{dataHora(r.ocorrido_em)}</span>
                        <span>{r.descricao}</span>
                        <span className="priv-muted">{r.detalhe}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
