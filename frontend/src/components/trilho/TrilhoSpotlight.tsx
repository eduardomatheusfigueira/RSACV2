/**
 * Revsist — Spotlight do Modo Trilho
 * Destaca visualmente na interface o campo ou botão correspondente à etapa ativa (Doc 46).
 */

import { useEffect } from 'react'
import { useTrilhoStore } from '@/stores/useTrilhoStore'

export function TrilhoSpotlight(): JSX.Element | null {
  const { isActive, getCurrentNode } = useTrilhoStore()
  const currentNode = getCurrentNode()

  useEffect(() => {
    if (!isActive || !currentNode?.targetElementSelector) return

    let previousEl: HTMLElement | null = null

    // Função de localização e destaque do elemento alvo
    const applySpotlight = () => {
      const el = document.querySelector<HTMLElement>(currentNode.targetElementSelector!)
      if (el) {
        el.classList.add('trilho-spotlight-active')
        previousEl = el

        // Rolagem suave até o elemento se não estiver visível na janela
        const rect = el.getBoundingClientRect()
        const isVisible =
          rect.top >= 0 &&
          rect.left >= 0 &&
          rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
          rect.right <= (window.innerWidth || document.documentElement.clientWidth)

        if (!isVisible) {
          el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }
      }
    }

    // Executa imediatamente e agenda retry caso elemento seja renderizado de forma assíncrona
    applySpotlight()
    const timer = setTimeout(applySpotlight, 200)

    return () => {
      clearTimeout(timer)
      if (previousEl) {
        previousEl.classList.remove('trilho-spotlight-active')
      }
      // Limpeza geral caso o seletor tenha mudado
      if (currentNode?.targetElementSelector) {
        document.querySelectorAll(currentNode.targetElementSelector).forEach((el) => {
          el.classList.remove('trilho-spotlight-active')
        })
      }
    }
  }, [isActive, currentNode?.id, currentNode?.targetElementSelector])

  return null
}
