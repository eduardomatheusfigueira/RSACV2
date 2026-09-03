/**
 * Revsist — Barra de instantâneo (doc 48 §14.2, doc 49 Fase 1)
 *
 * Diz sobre que corpus os números da tela foram calculados.
 *
 * Sem ela, o pesquisador não tem como saber sobre o que está olhando: o
 * acervo muda todo dia por coleta, deduplicação e triagem, e o mesmo
 * indicador devolvia outro número sem nada explicar (doc 47 §B-05).
 *
 * O semáforo da conferência é o coração do componente. Ele não impede nada —
 * apenas diz a verdade sobre a distância entre o corpus congelado e o acervo
 * de agora, que é a informação que decide se o número ainda pode ser citado.
 */

import { useCallback, useEffect, useState } from 'react'
import { Camera, CircleCheck, CircleAlert, TriangleAlert } from 'lucide-react'

import { api } from '@/api/client'
import { Button, Select, toast } from '@/components/ui'
import type { ConferenciaDoInstantaneo, Instantaneo } from '@/types/api'
import './BarraDeInstantaneo.css'

interface Props {
  projectId: string
  /** Instantâneo aberto; `null` significa "acervo de agora". */
  selecionado: string | null
  onSelecionar: (id: string | null) => void
  /**
   * Os filtros visíveis na aba. Congelar corpus congela **o que está na
   * tela** — se o botão ignorasse o recorte aberto, a pessoa pediria um
   * instantâneo dos incluídos e receberia um do acervo inteiro.
   */
  escopo: Instantaneo['scope']
}

/** Texto e tom de cada desfecho da conferência (doc 48 §3.3). */
const CONFERENCIA: Record<
  ConferenciaDoInstantaneo['estado'],
  { tom: 'ok' | 'atencao' | 'grave'; rotulo: string; explicacao: (c: ConferenciaDoInstantaneo) => string }
> = {
  identico: {
    tom: 'ok',
    rotulo: 'Confere',
    explicacao: () => 'O acervo não mudou desde o congelamento.',
  },
  conteudo_alterado: {
    tom: 'atencao',
    rotulo: 'Conteúdo alterado',
    explicacao: (c) =>
      `${c.documentos_alterados.length} ${
        c.documentos_alterados.length === 1 ? 'estudo teve metadado editado' : 'estudos tiveram metadado editado'
      } depois do congelamento. Os mesmos estudos, com conteúdo diferente.`,
  },
  conjunto_alterado: {
    tom: 'grave',
    rotulo: 'Conjunto alterado',
    explicacao: (c) => {
      const partes: string[] = []
      if (c.documentos_adicionados.length) partes.push(`${c.documentos_adicionados.length} entraram`)
      if (c.documentos_removidos.length) partes.push(`${c.documentos_removidos.length} saíram`)
      return `O corpus não é mais o mesmo: ${partes.join(' e ')}. Os números deste instantâneo descrevem o acervo de então.`
    },
  },
}

function formatarData(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? '—'
    : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

function rotuloDe(i: Instantaneo): string {
  const nome = i.label?.trim() || 'Sem rótulo'
  return `${nome} — ${i.n_documents} ${i.n_documents === 1 ? 'estudo' : 'estudos'} · ${formatarData(i.created_at)}`
}

export function BarraDeInstantaneo({
  projectId,
  selecionado,
  onSelecionar,
  escopo,
}: Props): JSX.Element {
  const [lista, setLista] = useState<Instantaneo[]>([])
  const [conferencia, setConferencia] = useState<ConferenciaDoInstantaneo | null>(null)
  const [congelando, setCongelando] = useState(false)

  const carregarLista = useCallback(async () => {
    try {
      setLista(await api.listarInstantaneos(projectId))
    } catch {
      // A barra é acessório de leitura: falhar aqui não pode derrubar a aba
      // inteira de indicadores, que funciona sem instantâneo nenhum.
      setLista([])
    }
  }, [projectId])

  useEffect(() => {
    void carregarLista()
  }, [carregarLista])

  useEffect(() => {
    let cancelado = false
    if (!selecionado) {
      setConferencia(null)
      return
    }
    void (async () => {
      try {
        const c = await api.conferirInstantaneo(projectId, selecionado)
        if (!cancelado) setConferencia(c)
      } catch {
        if (!cancelado) setConferencia(null)
      }
    })()
    return () => {
      cancelado = true
    }
  }, [projectId, selecionado])

  const congelar = async () => {
    setCongelando(true)
    try {
      const criado = await api.criarInstantaneo(projectId, {
        rotulo: `Congelado em ${new Date().toLocaleDateString('pt-BR')}`,
        escopo,
      })
      await carregarLista()
      onSelecionar(criado.id)
      toast.success(
        `Corpus congelado: ${criado.n_documents} ${criado.n_documents === 1 ? 'estudo' : 'estudos'}.`
      )
    } catch {
      toast.error('Não foi possível congelar o corpus agora.')
    } finally {
      setCongelando(false)
    }
  }

  const aberto = lista.find((i) => i.id === selecionado) ?? null
  const estado = conferencia ? CONFERENCIA[conferencia.estado] : null

  return (
    <div className="barra-instantaneo" role="region" aria-label="Corpus dos indicadores">
      <div className="barra-instantaneo__escolha">
        <label htmlFor="instantaneo-aberto" className="barra-instantaneo__rotulo">
          Corpus
        </label>
        <Select
          id="instantaneo-aberto"
          value={selecionado ?? ''}
          onChange={(e) => onSelecionar(e.target.value || null)}
        >
          <option value="">Acervo de agora (muda a cada coleta e triagem)</option>
          {lista.map((i) => (
            <option key={i.id} value={i.id}>
              {rotuloDe(i)}
            </option>
          ))}
        </Select>
      </div>

      <div className="barra-instantaneo__estado">
        {aberto && estado ? (
          <span className={`barra-instantaneo__selo is-${estado.tom}`}>
            {estado.tom === 'ok' ? (
              <CircleCheck size={14} aria-hidden="true" />
            ) : estado.tom === 'atencao' ? (
              <CircleAlert size={14} aria-hidden="true" />
            ) : (
              <TriangleAlert size={14} aria-hidden="true" />
            )}
            <span>
              <strong>{estado.rotulo}</strong> — {estado.explicacao(conferencia!)}
            </span>
          </span>
        ) : (
          <span className="barra-instantaneo__aviso">
            Estes números descrevem o acervo de agora. Congele o corpus para poder reproduzi-los
            depois.
          </span>
        )}
      </div>

      {aberto && (
        <p className="barra-instantaneo__proveniencia">
          {aberto.corpus_hash.slice(0, 12)} · motor {aberto.engine_version} · congelado em{' '}
          {formatarData(aberto.created_at)}
        </p>
      )}

      <Button
        variant="secondary"
        size="sm"
        onClick={congelar}
        disabled={congelando}
        leftIcon={<Camera size={14} />}
      >
        {congelando ? 'Congelando…' : 'Congelar corpus'}
      </Button>
    </div>
  )
}
