/**
 * RSAC V2 — Grupo do Ribbon
 *
 * O ribbon tem 29 grupos e os 29 repetiam a mesma casca: um contêiner, um
 * invólucro de ferramentas e o rótulo embaixo. São 559 das 1025 linhas do
 * arquivo, e a casca é justamente a parte que não pode variar — o rótulo
 * embaixo é o padrão que a barra herda do Office, e um grupo que o coloque em
 * outro lugar quebra a leitura da faixa inteira.
 *
 * Com a casca em um lugar só, o que sobra em cada aba do ribbon são as
 * ferramentas — que é o que de fato distingue uma etapa da revisão da outra.
 */

import type { ReactNode } from 'react'

export interface GrupoDoRibbonProps {
  /** Rótulo exibido embaixo do grupo, em versalete. */
  titulo: string
  /**
   * Ocupa a largura restante da faixa. Usado pelos grupos que carregam texto
   * corrido — "Próximo Passo", caixas de métrica — e não uma fila de botões.
   */
  expansivel?: boolean
  /** Deixa as ferramentas quebrarem em duas linhas. Usado pelos filtros. */
  quebraLinha?: boolean
  /**
   * Dois grupos trazem o próprio invólucro — a grade de bases conectadas e a
   * pilha de provedores, que são etiquetas de estado, não ferramentas. Para
   * esses, o invólucro padrão sobraria em volta do que já tem o seu.
   */
  semInvolucro?: boolean
  children: ReactNode
}

export function GrupoDoRibbon({
  titulo,
  expansivel = false,
  quebraLinha = false,
  semInvolucro = false,
  children,
}: GrupoDoRibbonProps): JSX.Element {
  return (
    <div className={`ribbon-group${expansivel ? ' ribbon-group-flex' : ''}`}>
      {semInvolucro ? (
        children
      ) : (
        <div className={`ribbon-group-tools${quebraLinha ? ' ribbon-group-tools-wrap' : ''}`}>
          {children}
        </div>
      )}
      <span className="ribbon-group-title">{titulo}</span>
    </div>
  )
}

/** Filete vertical entre grupos. */
export function DivisorDoRibbon(): JSX.Element {
  return <div className="ribbon-divider" />
}
