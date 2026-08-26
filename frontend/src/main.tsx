/**
 * RSAC V2 — React Entry Point
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { dispensarBootSplash } from './bootSplash'
import './styles/globals.css'

const rootElement = document.getElementById('root')!

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
)

/**
 * A splash é dispensada pela própria aplicação, quando há tela para mostrar
 * (ver `bootSplash.ts` e o `AuthGate` em `App.tsx`). O que fica aqui é apenas
 * a rede de segurança: se nada tiver decidido em 60 s, a marca sai de cena
 * para não esconder um erro de renderização atrás de uma animação bonita.
 */
window.setTimeout(dispensarBootSplash, 60_000)
