/**
 * Revsist — Formatação comum da aba Sistema.
 *
 * O ponto delicado é `agregado`: o servidor suprime todo número que resulta
 * de menos de cinco pessoas (doc 52 §6.6.2), e a tela precisa dizer isso —
 * "< 5" —, e não mostrar um zero que seria mentira nem um traço que pareceria
 * falta de dado.
 */

import type { Agregado, EstadoDaColeta, PeriodoDoSistema } from '@/types/api'
import type { BadgeVariant } from '@/components/ui'

const numero = new Intl.NumberFormat('pt-BR')
const compacto = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })

export const formatarNumero = (n: number | null | undefined): string =>
  n === null || n === undefined ? '—' : numero.format(Math.round(n))

export const formatarCompacto = (n: number | null | undefined): string =>
  n === null || n === undefined ? '—' : compacto.format(n)

export function formatarAgregado(a: Agregado, formato: (n: number) => string = formatarNumero): string {
  if (a.suprimido) return '< 5'
  return a.valor === null ? '—' : formato(a.valor)
}

export const dataCurta = (iso: string | null | undefined): string =>
  iso ? new Date(iso.length === 10 ? `${iso}T12:00:00` : iso).toLocaleDateString('pt-BR') : '—'

export const dataHora = (iso: string | null | undefined): string =>
  iso
    ? new Date(iso).toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—'

export const PERIODOS: { id: PeriodoDoSistema; rotulo: string }[] = [
  { id: '7', rotulo: '7 dias' },
  { id: '30', rotulo: '30 dias' },
  { id: '90', rotulo: '90 dias' },
  { id: 'beta', rotulo: 'Beta inteiro' },
]

export const ESTADOS: Record<EstadoDaColeta, { rotulo: string; badge: BadgeVariant; explicacao: string }> = {
  aguardando: {
    rotulo: 'Aguardando ativação',
    badge: 'warning',
    explicacao: 'Nada é registrado até o portão estar completo e alguém ativar a coleta.',
  },
  ativa: {
    rotulo: 'Coleta ativa',
    badge: 'success',
    explicacao: 'Eventos, erros e consumo de IA são registrados para quem aceitou a versão vigente dos termos.',
  },
  pausada: {
    rotulo: 'Coleta pausada',
    badge: 'info',
    explicacao: 'Nada novo é registrado. O que já existe continua sujeito aos prazos de retenção.',
  },
  encerrada: {
    rotulo: 'Beta encerrado',
    badge: 'neutral',
    explicacao: 'A coleta terminou e não pode ser reaberta. Os registros brutos são descartados no prazo.',
  },
}

export const OPERACOES_DE_IA: Record<string, string> = {
  triagem: 'Triagem',
  sugestao_protocolo: 'Sugestão de protocolo',
  assistencia_campo: 'Assistência de campo',
  extracao: 'Extração',
  teste_conexao: 'Teste de conexão',
  bibliometria_tesauro: 'Tesauro (bibliometria)',
}

export const RESULTADOS_DE_IA: Record<string, string> = {
  ok: 'Respondida',
  limite_minuto: 'Limite por minuto',
  limite_diario: 'Cota diária esgotada',
  modelo_indisponivel: 'Modelo indisponível',
  falha: 'Falha',
  resposta_invalida: 'Resposta inválida',
}

/** Baixa um objeto como arquivo JSON, a partir de um clique de quem pediu. */
export function baixarJson(nome: string, conteudo: unknown): void {
  const blob = new Blob([JSON.stringify(conteudo, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = nome
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
