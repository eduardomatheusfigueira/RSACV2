/**
 * Revsist — Campo do Estúdio de Protocolo
 *
 * O Estúdio tinha 18 cartões de campo somando 1755 linhas — 58% do arquivo — e
 * os 18 repetiam a mesma anatomia: etiqueta do item na diretriz, título com
 * ações, ajuda derivada da diretriz ativa, guia estruturado opcional e um
 * corpo. Não era código diferente repetido; era o mesmo código com dados
 * diferentes, e mudar a anatomia custava 18 edições.
 *
 * O que varia de verdade é o CORPO — ora um `<textarea>`, ora uma lista de
 * critérios, ora uma grade de perguntas. Por isso o corpo é `children`, e não
 * mais uma prop de configuração: tentar descrevê-lo por props recriaria aqui
 * dentro a variedade que se queria tirar de lá.
 */

import React from 'react'
import { HelpCircle, Plus } from 'lucide-react'
import { Card } from '@/components/ui'
import type { GuiaEstruturado } from '@/data/guiasDoProtocolo'

export interface CampoDoProtocoloProps
  extends Omit<React.HTMLAttributes<HTMLElement>, 'title' | 'children'> {
  /** Ícone da seção, à esquerda do título. */
  icone: React.ReactNode
  titulo: string
  /** Etiqueta do item na diretriz ativa — vem de `getFieldItemTag`. */
  etiquetaItem: React.ReactNode
  /**
   * Item essencial da diretriz ou opcional. Muda a cor da etiqueta, e a
   * distinção é metodológica: sob a maioria das diretrizes a avaliação crítica
   * é dispensável numa revisão de escopo, e a etiqueta precisa dizer isso.
   */
  essencial?: boolean
  /** Seção do manuscrito: "MÉTODOS / VARIÁVEIS", "DISCUSSÃO", … */
  secao: string
  /** Ajuda derivada da diretriz ativa — vem de `getFieldGuideline`. */
  ajuda: string
  /** `<AIAssistButton>` já montado: o `onApply` de cada campo é específico. */
  assistencia?: React.ReactNode
  guia?: {
    conteudo: GuiaEstruturado
    /** Referência ao item na diretriz ativa — vem de `getFieldItemRef`. */
    referencia: string
    aberto: boolean
    alternar: () => void
    /**
     * Insere o modelo no editor. Fica com a página porque depende do valor
     * atual do campo — a confirmação só aparece quando há texto a substituir.
     */
    aoInserirModelo?: () => void
  }
  /** Cartão mais apertado — usado no trio de campos automáticos do núcleo. */
  compact?: boolean
  children: React.ReactNode
}

export function CampoDoProtocolo({
  icone,
  titulo,
  etiquetaItem,
  essencial = true,
  secao,
  ajuda,
  assistencia,
  guia,
  compact = false,
  children,
  className = '',
  ...resto
}: CampoDoProtocoloProps): JSX.Element {
  return (
    <Card
      surface="secundaria"
      compact={compact}
      className={`protocol-card ${className}`.trim()}
      {...resto}
    >
      <div className="item-header-meta">
        <span className={`item-tag ${essencial ? 'essential' : 'optional'}`}>{etiquetaItem}</span>
        <span className="item-section-tag">{secao}</span>
      </div>

      <div className="card-section-title-with-actions">
        <div className="card-section-title">
          {icone}
          <h2>{titulo}</h2>
        </div>
        {(assistencia || guia) && (
          <div className="card-header-actions">
            {assistencia}
            {guia && (
              <button
                type="button"
                className={`btn-help-toggle ${guia.aberto ? 'active' : ''}`}
                onClick={guia.alternar}
                title={guia.conteudo.tituloBotao}
                aria-expanded={guia.aberto}
              >
                <HelpCircle size={16} aria-hidden="true" />
                <span>{guia.conteudo.rotuloBotao}</span>
              </button>
            )}
          </div>
        )}
      </div>

      <p className="section-help">{ajuda}</p>

      {guia?.aberto && (
        <div className="structured-guide-box animate-fade-in">
          <div className="guide-header">
            <div className="guide-title">
              <HelpCircle size={18} className="icon-accent" aria-hidden="true" />
              <strong>
                {guia.conteudo.titulo} ({guia.referencia})
              </strong>
            </div>
            {guia.conteudo.modelo && guia.aoInserirModelo && (
              <button type="button" className="btn-insert-template" onClick={guia.aoInserirModelo}>
                <Plus size={14} aria-hidden="true" /> {guia.conteudo.modelo.rotulo}
              </button>
            )}
          </div>
          <div className="guide-grid">
            {guia.conteudo.itens.map((item) => (
              <div key={item.tag} className="guide-item">
                <span className="guide-tag">{item.tag}</span>
                <p>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {children}
    </Card>
  )
}
