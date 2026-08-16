/**
 * RSAC V2 — AppShell Component
 * Layout principal profissional de alta produtividade (TopRibbonBar + Full Workspace + Right Dock LogPanel + StatusBar).
 */

import { Outlet } from 'react-router-dom'
import { TopRibbonBar } from './TopRibbonBar'
import { StatusBar } from './StatusBar'
import { LogPanel } from './LogPanel'
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
    </div>
  )
}
