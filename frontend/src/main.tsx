/**
 * Revsist — React Entry Point
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles/globals.css'
/* A camada móvel entra DEPOIS do grafo de componentes (avaliado ao importar
   `App`), para que suas regras vençam os `@media` locais de cada folha sem
   precisar de `!important` espalhado. Não reordenar. */
import './styles/mobile.css'

const rootElement = document.getElementById('root')!

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
)

/**
 * Remove a splash de inicialização declarada no index.html.
 *
 * A Content-Security-Policy do app proíbe script inline, então a camada não
 * consegue se remover sozinha — quem a dispensa é este ponto de entrada, no
 * primeiro frame após a montagem, com uma esmaecida curta para não haver
 * corte seco entre a marca e a interface.
 */
const splash = document.getElementById('boot-splash')
if (splash) {
  requestAnimationFrame(() => {
    splash.classList.add('is-leaving')
    splash.addEventListener('transitionend', () => splash.remove(), { once: true })
    // Rede de segurança caso a transição não dispare (ex.: prefers-reduced-motion).
    window.setTimeout(() => splash.remove(), 600)
  })
}
