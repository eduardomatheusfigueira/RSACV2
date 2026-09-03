/**
 * Revsist — Ferramentas de apoio do Estúdio de Protocolo
 *
 * Guia e assistência não são enfeite neste produto: são o que faz um
 * pesquisador conseguir preencher um protocolo sem ter o manual da diretriz
 * aberto ao lado. O modo Completo já entregava as duas coisas em todos os seus
 * cartões, porque `ProtocolPage` tem à mão o que elas precisam — a diretriz
 * ativa, o estado do painel de ajuda, o contexto do projeto para a IA.
 *
 * Os componentes do Núcleo de Busca (doc 45 §8) vivem fora da página, e por
 * isso nasceram sem nenhum dos dois. Este contrato é o que os liga de volta:
 * um único objeto, passado como prop, em vez de sete props avulsas ou de um
 * contexto global que acoplaria os componentes à página.
 *
 * Tudo é opcional de propósito. Um componente do Estúdio precisa renderizar
 * mesmo sem apoio — numa pré-visualização, num teste, num modo somente-leitura
 * —, e o que ele perde nesse caso é o botão de guia, não o campo.
 */

import type { CampoDoProtocoloProps } from './CampoDoProtocolo'

export interface FerramentasDeApoio {
  /**
   * Monta o guia de um campo a partir de `guiasDoProtocolo.ts`, já ligado ao
   * painel de ajuda da página. `alvo` diz onde o modelo de texto é inserido:
   * sem ele, o guia abre sem o botão de modelo — que é o certo para campos em
   * que "inserir texto" não significa nada (o seletor de desenho, a grade de
   * bases).
   */
  montarGuia?: (
    chaveDoGuia: string,
    chaveDeAjuda: string,
    alvo?: { valorAtual: string; aplicar: (texto: string) => void }
  ) => CampoDoProtocoloProps['guia']

  /** Ajuda derivada da diretriz ATIVA, com texto de reserva quando ela não trata do campo. */
  ajuda?: (chaveDoCampo: string, reserva: string) => string

  /** Contexto do protocolo para a assistência, excluindo o campo que está sendo gerado. */
  contexto?: (excluirCampo?: string) => Record<string, string>

  projeto?: {
    titulo?: string
    metodologia?: string
  }
}
