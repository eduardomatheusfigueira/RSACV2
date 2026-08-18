/**
 * RSAC V2 — Servidor do renderer para a suíte de validação (doc 26)
 * ====================================================================
 *
 * Serve `src/` isoladamente (sem o shell do Electron) para os scripts de
 * a11y-audit, layout-budget, visual-baseline e visual-check, que dirigem o
 * Chromium via Playwright contra uma URL http comum.
 *
 * Uso:
 *   npx vite --config vite.config.testserver.mts
 *
 * Porta fixa (5199) para bater com o padrão de `RSAC_FRONTEND_URL` em
 * scripts/lib/rsac-fixture.mjs. Requer o backend rodando à parte
 * (`python3 backend/run.py`) — o app lê a porta dele via `?port=`.
 */
import { resolve } from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const RAIZ = resolve(__dirname)

export default defineConfig({
  root: RAIZ,
  plugins: [react()],
  resolve: { alias: { '@': resolve(RAIZ, 'src') } },
  server: { port: 5199, strictPort: true },
})
