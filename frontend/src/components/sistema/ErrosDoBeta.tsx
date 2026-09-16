/**
 * Revsist — Aba Sistema › Erros.
 *
 * Um cartão por defeito — impressão digital —, não por ocorrência, ordenado
 * por pessoas atingidas. A situação é do defeito: marcado como resolvido numa
 * versão, ele volta a "novo" sozinho se reaparecer numa versão posterior.
 */

import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Badge, EmptyState, Select, toast } from '@/components/ui'
import type { BadgeVariant } from '@/components/ui'
import { api } from '@/api/client'
import type { ErroAgrupado, PeriodoDoSistema, SituacaoDeErro } from '@/types/api'
import { dataHora, formatarNumero } from './formatos'

const SITUACOES: { id: SituacaoDeErro; rotulo: string; badge: BadgeVariant }[] = [
  { id: 'novo', rotulo: 'Novo', badge: 'warning' },
  { id: 'investigando', rotulo: 'Investigando', badge: 'info' },
  { id: 'resolvido', rotulo: 'Resolvido', badge: 'success' },
  { id: 'ignorado', rotulo: 'Ignorado', badge: 'neutral' },
]

export function ErrosDoBeta({ periodo }: { periodo: PeriodoDoSistema }): JSX.Element {
  const [itens, setItens] = useState<ErroAgrupado[]>([])
  const [carregando, setCarregando] = useState(false)
  const [ocupado, setOcupado] = useState<string | null>(null)
  const [notas, setNotas] = useState<Record<string, string>>({})

  const carregar = async () => {
    try {
      setCarregando(true)
      setItens((await api.getErrosDoBeta(periodo)).itens)
    } catch (err: any) {
      toast.error('Falha ao carregar os erros', { description: err.message })
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodo])

  const atualizar = async (erro: ErroAgrupado, mudanca: { situacao?: SituacaoDeErro; nota?: string }) => {
    try {
      setOcupado(erro.impressao)
      const res = await api.acompanharErro(erro.impressao, {
        situacao: mudanca.situacao ?? erro.situacao,
        nota: mudanca.nota,
      })
      setItens((atual) => atual.map((i) => (i.impressao === erro.impressao ? { ...i, ...res } : i)))
    } catch (err: any) {
      toast.error('Falha ao atualizar o defeito', { description: err.message })
    } finally {
      setOcupado(null)
    }
  }

  return (
    <div className="admin-panel sis-painel">
      <div className="admin-toolbar">
        <h4 className="admin-table-title">Erros agrupados por defeito</h4>
        <div className="admin-toolbar-actions">
          <button type="button" className="btn-text-action" onClick={carregar} disabled={carregando}>
            <RefreshCw size={12} className={carregando ? 'animate-spin' : ''} /> Atualizar
          </button>
        </div>
      </div>

      {itens.length === 0 ? (
        <EmptyState
          size="inline"
          icon={<AlertTriangle size={22} strokeWidth={1.25} aria-hidden="true" />}
          title="Nenhum erro registrado no período"
          description="As ocorrências chegam sanitizadas: sem e-mail, endereço, número longo nem trecho entre aspas."
        />
      ) : (
        <ul className="sis-lista">
          {itens.map((erro) => {
            const situacao = SITUACOES.find((s) => s.id === erro.situacao) ?? SITUACOES[0]
            const nota = notas[erro.impressao] ?? erro.nota
            return (
              <li key={erro.impressao} className={`sis-cartao sis-erro sis-erro--${erro.situacao}`}>
                <div className="sis-erro__cabeca">
                  <code className="sis-erro__tipo">{erro.tipo}</code>
                  <Badge variant={situacao.badge} size="xs">
                    {situacao.rotulo}
                    {erro.situacao === 'resolvido' && erro.resolvido_na_versao ? ` em ${erro.resolvido_na_versao}` : ''}
                  </Badge>
                  <Badge variant="neutral" size="xs">
                    {erro.origem === 'servidor' ? 'Servidor' : 'Navegador'}
                  </Badge>
                  <span className="sis-muted sis-erro__impressao" title={erro.impressao}>
                    #{erro.impressao.slice(0, 10)}
                  </span>
                </div>

                {erro.mensagem && <p className="sis-erro__mensagem">{erro.mensagem}</p>}

                <div className="sis-meta">
                  <span>
                    <strong>{erro.pessoas_suprimido ? '< 5' : formatarNumero(erro.pessoas)}</strong> pessoa(s)
                  </span>
                  <span>
                    <strong>{formatarNumero(erro.ocorrencias)}</strong> ocorrência(s)
                  </span>
                  {(erro.tela || erro.rota) && <code>{erro.tela || erro.rota}</code>}
                  {erro.versoes.length > 0 && <span>v{erro.versoes.join(', v')}</span>}
                  <span>
                    {dataHora(erro.primeira_vez)} → {dataHora(erro.ultima_vez)}
                  </span>
                </div>

                {erro.pilha && (
                  <details className="sis-erro__pilha">
                    <summary>Pilha sanitizada</summary>
                    <pre>{erro.pilha}</pre>
                  </details>
                )}

                <div className="sis-erro__acoes">
                  <label className="sis-campo-curto">
                    <span className="sis-muted">Situação</span>
                    <Select
                      sizeVariant="sm"
                      value={erro.situacao}
                      disabled={ocupado === erro.impressao}
                      onChange={(e) => atualizar(erro, { situacao: e.target.value as SituacaoDeErro })}
                    >
                      {SITUACOES.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.rotulo}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="sis-campo-longo">
                    <span className="sis-muted">Nota técnica (sem dados de quem foi atingido)</span>
                    <textarea
                      rows={2}
                      maxLength={2000}
                      value={nota}
                      disabled={ocupado === erro.impressao}
                      onChange={(e) => setNotas((n) => ({ ...n, [erro.impressao]: e.target.value }))}
                      onBlur={() => {
                        if (nota.trim() !== erro.nota.trim()) atualizar(erro, { nota })
                      }}
                    />
                  </label>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
