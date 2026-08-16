/**
 * RSAC V2 — React Entry Point
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles/globals.css'

const rootElement = document.getElementById('root')!

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
)
