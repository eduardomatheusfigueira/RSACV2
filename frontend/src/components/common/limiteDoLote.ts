/**
 * Revsist — Limite padrão da triagem em lote
 *
 * A janela do lote calculava este valor uma única vez, no inicializador do
 * `useState`. Como ela é montada junto com a tela de Triagem — e não quando
 * abre —, esse cálculo acontecia com o contador de pendentes ainda em 0, e o
 * limite nascia **1** e nunca mais mudava: o pesquisador abria a janela, via
 * "Iniciar Triagem em Lote (1)" e disparava um lote de um único estudo, que
 * terminava antes de a barra de progresso dizer qualquer coisa.
 *
 * Separado em módulo porque a regra é do domínio, não da marcação, e porque
 * assim ela tem teste.
 */

/** Teto de estudos sugerido por padrão quando a janela do lote abre. */
export const LIMITE_PADRAO_DO_LOTE = 50

/**
 * Limite inicial coerente com o acervo.
 *
 * - Sem pendentes conhecidos ainda (contador em 0, ou ausente): devolve o
 *   padrão. Um limite maior que o acervo não faz mal — o servidor tria o que
 *   houver —, ao passo que um limite menor silenciosamente deixa estudos para
 *   trás, que é o erro caro dos dois.
 * - Com pendentes: o menor entre o padrão e o que existe, para que o rótulo do
 *   botão nunca prometa mais do que há.
 */
export function limitePadraoDoLote(pendentes: number | null | undefined): number {
  if (!Number.isFinite(pendentes as number) || (pendentes as number) <= 0) {
    return LIMITE_PADRAO_DO_LOTE
  }
  return Math.min(LIMITE_PADRAO_DO_LOTE, Math.floor(pendentes as number))
}
