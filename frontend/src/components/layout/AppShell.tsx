/**
 * Revsist — AppShell Component
 * Layout principal profissional de alta produtividade (TopRibbonBar + Full Workspace + Right Dock LogPanel + StatusBar).
 */

import { Outlet } from 'react-router-dom'
import { TopRibbonBar } from './TopRibbonBar'
import { StatusBar } from './StatusBar'
import { LogPanel } from './LogPanel'
import { BoasVindas } from '@/components/boasvindas'
import { BotaoFeedback } from '@/components/feedback/BotaoFeedback'
import './AppShell.css'

export function AppShell(): JSX.Element {
  return (
    <div className="app-shell">
      <TopRibbonBar />
      <div className="app-main">
        <div className="app-workspace-body">
          <main className="app-content">
            <Outlet />
          </main>
          <LogPanel />
        </div>
        <StatusBar />
      </div>

      {/* Boas-vindas da primeira vez. Mora aqui, e nao numa pagina, porque
          precisa aparecer sobre qualquer tela em que a pessoa entre — o
          primeiro acesso nem sempre cai no painel inicial. */}
      <BoasVindas />

      {/* Feedback do beta: em toda tela, no canto inferior direito. */}
      <BotaoFeedback />
    </div>
  )
}

