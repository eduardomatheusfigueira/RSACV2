/**
 * Revsist — Painel de Enriquecimento Bibliométrico (doc 48 §4, doc 49 Fase 2)
 *
 * Exibe a cobertura de metadados externos (OpenAlex/Crossref) para o projeto
 * e permite disparar rodadas assíncronas em segundo plano com acompanhamento.
 */

import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Database, Loader2, RefreshCw, Square } from 'lucide-react'

import { api } from '@/api/client'
import { Button, toast } from '@/components/ui'
import type { SituacaoEnriquecimento } from '@/types/api'
import './PainelEnriquecimento.css'

interface Props {
  projectId: string
  onAtualizarInsights?: () => void
}

export function PainelEnriquecimento({ projectId, onAtualizarInsights }: Props): JSX.Element {
  const [situacao, setSituacao] = useState<SituacaoEnriquecimento | null>(null)
  const [emExecucao, setEmExecucao] = useState(false)
  const [carregando, setCarregando] = useState(true)

  const carregarSituacao = useCallback(async () => {
    try {
      const s = await api.obterSituacaoEnriquecimento(projectId)
      setSituacao(s)
      if (s.last_enrichment?.status === 'em_andamento') {
        setEmExecucao(true)
      } else {
        setEmExecucao(false)
      }
    } catch {
      // Ignora erro silenciosamente para não quebrar a página
    } finally {
      setCarregando(false)
    }
  }, [projectId])

  useEffect(() => {
    void carregarSituacao()
  }, [carregarSituacao])

  // Polling quando em execução
  useEffect(() => {
    if (!emExecucao) return

    const interval = setInterval(async () => {
      try {
        const s = await api.obterSituacaoEnriquecimento(projectId)
        setSituacao(s)
        if (s.last_enrichment?.status !== 'em_andamento') {
          setEmExecucao(false)
          toast.success('Enriquecimento concluído!', {
            description: `${s.last_enrichment?.n_found ?? 0} estudos enriquecidos com metadados do OpenAlex.`,
          })
          onAtualizarInsights?.()
        }
      } catch {
        // ignora
      }
    }, 2500)

    return () => clearInterval(interval)
  }, [emExecucao, projectId, onAtualizarInsights])

  const handleIniciar = async () => {
    try {
      setEmExecucao(true)
      await api.iniciarEnriquecimento(projectId)
      toast.info('Enriquecimento iniciado em segundo plano', {
        description: 'Consultando afiliações e referências no OpenAlex...',
      })
      void carregarSituacao()
    } catch (e: unknown) {
      setEmExecucao(false)
      const msg = e instanceof Error ? e.message : 'Falha ao iniciar enriquecimento'
      toast.error('Erro ao enriquecer', { description: msg })
    }
  }

  const handleParar = async () => {
    try {
      await api.pararEnriquecimento(projectId)
      setEmExecucao(false)
      toast.info('Enriquecimento interrompido')
      void carregarSituacao()
    } catch {
      // ignora
    }
  }

  if (carregando && !situacao) {
    return <div className="painel-enriquecimento painel-enriquecimento--carregando" />
  }

  if (!situacao || situacao.papers_with_doi === 0) {
    return <></>
  }

  const { papers_with_doi, papers_enriched, papers_pending, coverage_pct } = situacao

  return (
    <div className="painel-enriquecimento" role="region" aria-label="Enriquecimento Bibliométrico">
      <div className="painel-enriquecimento__info">
        <div className="painel-enriquecimento__titulo">
          <Database className="painel-enriquecimento__icone" size={16} />
          <span>Enriquecimento OpenAlex / ROR</span>
        </div>
        <p className="painel-enriquecimento__descricao">
          {papers_enriched > 0 ? (
            <>
              <strong>{papers_enriched}</strong> de <strong>{papers_with_doi}</strong> estudos com DOI enriquecidos ({coverage_pct}%) com afiliações institucionais reais, referências e citações.
            </>
          ) : (
            <>
              Existem <strong>{papers_with_doi}</strong> estudos com DOI elegíveis para obter afiliações reais por ROR e referências abertas.
            </>
          )}
        </p>
      </div>

      <div className="painel-enriquecimento__acoes">
        {emExecucao ? (
          <div className="painel-enriquecimento__executando">
            <span className="painel-enriquecimento__status-label">
              <Loader2 className="painel-enriquecimento__spinner" size={14} />
              Consultando OpenAlex…
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleParar}
              className="painel-enriquecimento__btn-parar"
            >
              <Square size={12} className="mr-1" />
              Parar
            </Button>
          </div>
        ) : (
          <Button
            variant={papers_pending > 0 ? 'secondary' : 'outline'}
            size="sm"
            onClick={handleIniciar}
            disabled={papers_with_doi === 0}
          >
            {papers_pending > 0 ? (
              <>
                <RefreshCw size={14} className="mr-1.5" />
                {papers_enriched === 0 ? 'Enriquecer Acervo' : `Enriquecer Restantes (${papers_pending})`}
              </>
            ) : (
              <>
                <CheckCircle2 size={14} className="mr-1.5 is-ok" />
                100% Enriquecido (Reexecutar)
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  )
}
