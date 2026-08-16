/**
 * RSAC V2 — Sidebar Component
 * Navegação lateral principal da aplicação.
 */

import { useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  FolderOpen,
  Settings,
  FileText,
  Search,
  CheckSquare,
  FileDown,
  Download,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  FolderDot,
} from 'lucide-react'
import { useSettingsStore } from '@/stores/useSettingsStore'
import './Sidebar.css'

interface NavItem {
  id: string
  label: string
  icon: React.ReactNode
  path: string
  requiresProject?: boolean
}

const mainNav: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} />, path: '/' },
  { id: 'projects', label: 'Projetos', icon: <FolderOpen size={20} />, path: '/projects' },
]

const projectNav: NavItem[] = [
  { id: 'protocol', label: 'Protocolo', icon: <BookOpen size={20} />, path: '/projects/:id/protocol', requiresProject: true },
  { id: 'harvest', label: 'Coleta', icon: <Download size={20} />, path: '/projects/:id/harvest', requiresProject: true },
  { id: 'screening', label: 'Triagem', icon: <CheckSquare size={20} />, path: '/projects/:id/screening', requiresProject: true },
  { id: 'extraction', label: 'Extração', icon: <FileText size={20} />, path: '/projects/:id/extraction', requiresProject: true },
  { id: 'export', label: 'Exportar', icon: <FileDown size={20} />, path: '/projects/:id/export', requiresProject: true },
]

const bottomNav: NavItem[] = [
  { id: 'settings', label: 'Configurações', icon: <Settings size={20} />, path: '/settings' },
]

export function Sidebar(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  const { sidebarCollapsed, toggleSidebar, activeProject } = useSettingsStore()

  const resolvePath = (item: NavItem): string => {
    if (item.requiresProject && activeProject) {
      return item.path.replace(':id', activeProject.id)
    }
    return item.path
  }

  const isActive = (item: NavItem): boolean => {
    const targetPath = resolvePath(item)
    if (targetPath === '/') return location.pathname === '/'
    return location.pathname === targetPath || location.pathname.startsWith(targetPath + '/')
  }

  const handleNavClick = (item: NavItem) => {
    if (item.requiresProject && !activeProject) {
      navigate('/projects')
      return
    }
    navigate(resolvePath(item))
  }

  const renderNavItem = (item: NavItem) => {
    const disabled = item.requiresProject && !activeProject
    return (
      <button
        key={item.id}
        className={`sidebar-item ${isActive(item) ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
        onClick={() => handleNavClick(item)}
        title={
          sidebarCollapsed
            ? item.label + (disabled ? ' (Selecione um projeto)' : '')
            : undefined
        }
      >
        <span className="sidebar-item-icon">{item.icon}</span>
        {!sidebarCollapsed && (
          <span className="sidebar-item-label">{item.label}</span>
        )}
      </button>
    )
  }

  return (
    <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
      {/* Logo */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Search size={24} strokeWidth={2.5} />
          {!sidebarCollapsed && (
            <span className="sidebar-title">
              RSAC<span className="sidebar-version">v2</span>
            </span>
          )}
        </div>
      </div>

      {/* Active Project Banner */}
      {!sidebarCollapsed && activeProject && (
        <div className="sidebar-active-project" title={activeProject.title}>
          <div className="active-project-tag">
            <FolderDot size={14} />
            <span>Projeto Ativo</span>
          </div>
          <p className="active-project-name">{activeProject.title}</p>
        </div>
      )}

      {/* Navegação Principal */}
      <nav className="sidebar-nav">
        <div className="sidebar-section">
          {mainNav.map(renderNavItem)}
        </div>

        <div className="sidebar-divider" />

        <div className="sidebar-section">
          {!sidebarCollapsed && (
            <span className="sidebar-section-title">
              {activeProject ? 'Etapas da Revisão' : 'Etapas (Nenhum Projeto)'}
            </span>
          )}
          {projectNav.map(renderNavItem)}
        </div>
      </nav>

      {/* Bottom */}
      <div className="sidebar-bottom">
        <div className="sidebar-divider" />
        {bottomNav.map(renderNavItem)}
        <button className="sidebar-item sidebar-toggle" onClick={toggleSidebar}>
          {sidebarCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
          {!sidebarCollapsed && <span className="sidebar-item-label">Recolher</span>}
        </button>
      </div>
    </aside>
  )
}
