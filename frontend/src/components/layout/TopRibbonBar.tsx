/**
 * RSAC V2 — Professional Desktop Ribbon Bar
 *
 * Design philosophy:
 * Each tab shows ONLY the tools that matter for that exact stage of the systematic review.
 * The ribbon mirrors the actual workflow pipeline: Project → Protocol → Harvest → Screen → Extract → Export.
 * Tools are grouped by PURPOSE (what you're trying to do), not by type.
 * Large vertical buttons = primary actions (the thing you came to this tab to do).
 * Compact horizontal buttons = secondary navigation or contextual filters.
 * Info boxes = live metrics that inform your decisions.
 * Badges = status indicators for connected services.
 *
 * A "Next Step" smart indicator always shows what the logical next action is,
 * guiding the researcher through the entire review pipeline naturally.
 */

import { useState } from 'react'
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
  Sparkles,
  Layers,
  Database,
  ChevronUp,
  ChevronDown,
  Plus,
  Save,
  FolderDot,
  RefreshCw,
  Copy,
  Filter,
  FileSpreadsheet,
  Zap,
  HelpCircle,
  Clock,
  Check,
  X,
  ArrowRight,
  Play,
  Upload,
  BarChart3,
  ListChecks,
  BookMarked,
  Edit3,
  ShieldCheck,
  Globe,
  Key,
  Cpu,
  Server,
} from 'lucide-react'
import { useSettingsStore } from '@/stores/useSettingsStore'
import './TopRibbonBar.css'

interface RibbonTab {
  id: string
  label: string
  icon: React.ReactNode
  path: string
  requiresProject?: boolean
  stepNumber?: number
}

const RIBBON_TABS: RibbonTab[] = [
  { id: 'projects', label: 'Arquivo', icon: <FolderOpen size={14} />, path: '/projects' },
  { id: 'dashboard', label: 'Início', icon: <LayoutDashboard size={14} />, path: '/' },
  { id: 'protocol', label: 'Protocolo', icon: <BookOpen size={14} />, path: '/projects/:id/protocol', requiresProject: true, stepNumber: 1 },
  { id: 'harvest', label: 'Coleta', icon: <Download size={14} />, path: '/projects/:id/harvest', requiresProject: true, stepNumber: 2 },
  { id: 'screening', label: 'Triagem', icon: <CheckSquare size={14} />, path: '/projects/:id/screening', requiresProject: true, stepNumber: 3 },
  { id: 'extraction', label: 'Extração', icon: <FileText size={14} />, path: '/projects/:id/extraction', requiresProject: true, stepNumber: 4 },
  { id: 'export', label: 'Exportar', icon: <FileDown size={14} />, path: '/projects/:id/export', requiresProject: true, stepNumber: 5 },
  { id: 'settings', label: 'Ferramentas', icon: <Settings size={14} />, path: '/settings' },
]

export function TopRibbonBar(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  const {
    activeProject,
    aiEnabled,
    setAiEnabled,
    backendStatus,
    backendVersion,
  } = useSettingsStore()

  const [ribbonCollapsed, setRibbonCollapsed] = useState(false)

  const resolvePath = (tab: RibbonTab): string => {
    if (tab.requiresProject && activeProject) {
      return tab.path.replace(':id', activeProject.id)
    }
    return tab.path
  }

  const isTabActive = (tab: RibbonTab): boolean => {
    const pathname = location.pathname
    if (tab.id === 'dashboard') {
      return pathname === '/'
    }
    if (tab.id === 'projects') {
      return pathname === '/projects' || pathname === '/projects/'
    }
    if (tab.id === 'settings') {
      return pathname === '/settings' || pathname.startsWith('/settings/')
    }
    if (tab.requiresProject) {
      if (tab.id === 'protocol') return pathname.includes('/protocol')
      if (tab.id === 'harvest') return pathname.includes('/harvest')
      if (tab.id === 'screening') return pathname.includes('/screening')
      if (tab.id === 'extraction') return pathname.includes('/extraction')
      if (tab.id === 'export') return pathname.includes('/export')
    }
    return false
  }

  const handleTabClick = (tab: RibbonTab) => {
    if (tab.requiresProject && !activeProject) {
      navigate('/projects')
      return
    }
    navigate(resolvePath(tab))
  }

  const navToProjectPage = (page: string) => {
    if (!activeProject) return
    navigate(`/projects/${activeProject.id}/${page}`)
  }

  const currentTab = RIBBON_TABS.find((tab) => isTabActive(tab)) || RIBBON_TABS[0]

  // Helper: trigger a click on a DOM element by selector
  const clickDom = (selector: string) => {
    const el = document.querySelector(selector) as HTMLElement
    if (el) el.click()
  }

  const clickDomByText = (selector: string, text: string) => {
    const els = Array.from(document.querySelectorAll(selector)) as HTMLElement[]
    const el = els.find((e) => e.textContent?.includes(text))
    if (el) el.click()
  }

  const clickDomByIndex = (selector: string, index: number) => {
    const els = Array.from(document.querySelectorAll(selector)) as HTMLElement[]
    if (els[index]) els[index].click()
  }

  return (
    <header className="ribbon-container">
      {/* ═══════════════════════════════════════════════════════════════════
          LAYER 1: APPLICATION TITLE BAR
          Brand + Active Project Context + Quick Global Controls
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="ribbon-titlebar">
        <div className="ribbon-brand" onClick={() => navigate('/')}>
          <div className="brand-badge"><Search size={13} strokeWidth={2.5} /></div>
          <span className="brand-name">RSAC<span className="brand-ver">v2</span></span>
        </div>

        <div className="ribbon-active-project-bar">
          {activeProject ? (
            <div className="active-project-pill" onClick={() => navigate('/projects')} title="Trocar projeto ativo">
              <FolderDot size={13} className="icon-project" />
              <span className="project-label">Projeto:</span>
              <strong className="project-title">{activeProject.title}</strong>
              <span className="project-methodology-tag">{activeProject.methodology}</span>
            </div>
          ) : (
            <button className="btn-select-project-alert" onClick={() => navigate('/projects')}>
              <FolderOpen size={13} />
              <span>Selecionar ou Criar Projeto</span>
            </button>
          )}
        </div>

        <div className="ribbon-quick-actions">
          <button
            type="button"
            className={`ribbon-action-pill ${aiEnabled ? 'ai-active' : 'ai-manual'}`}
            onClick={() => setAiEnabled(!aiEnabled)}
            title={aiEnabled ? 'IA Ativa — Clique para Modo Manual' : 'Modo Manual — Clique para ativar IA'}
          >
            {aiEnabled ? <Sparkles size={12} /> : <Edit3 size={12} />}
            <span>{aiEnabled ? 'IA' : 'Manual'}</span>
          </button>

          <button type="button" className={`ribbon-icon-btn collapse-btn ${ribbonCollapsed ? 'active' : ''}`}
            onClick={() => setRibbonCollapsed(!ribbonCollapsed)}
            title={ribbonCollapsed ? 'Expandir Ribbon' : 'Recolher Ribbon'}>
            {ribbonCollapsed ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
          </button>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          LAYER 2: TAB BAR
          The 8 navigation tabs — each one is a phase of the review process
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="ribbon-tabs-bar">
        <nav className="ribbon-tabs-nav">
          {RIBBON_TABS.map((tab) => {
            const active = isTabActive(tab)
            const disabled = tab.requiresProject && !activeProject
            return (
              <button
                key={tab.id}
                type="button"
                className={`ribbon-tab-btn ${active ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
                onClick={() => handleTabClick(tab)}
              >
                {tab.stepNumber && <span className="tab-step-num">{tab.stepNumber}</span>}
                <span className="ribbon-tab-icon">{tab.icon}</span>
                <span className="ribbon-tab-label">{tab.label}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          LAYER 3: CONTEXTUAL TOOLSTRIP
          100% dynamic — renders ONLY the tools for the active tab.
          Every group, every button, every metric is purposeful.
      ═══════════════════════════════════════════════════════════════════ */}
      {!ribbonCollapsed && (
        <div className="ribbon-toolstrip animate-fade-in">

          {/* ──────────────────────────────────────────────────────────────
              TAB: ARQUIVO (Projetos)
              Purpose: Create, open, organize review projects
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'projects' && (
            <>
              {/* Group: Novo */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-large" onClick={() => clickDom('.btn-create-project, .dashboard-cta')}>
                    <Plus size={20} className="icon-accent" />
                    <span>Novo<br />Projeto</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Novo</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Gerenciamento */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-vertical" onClick={() => window.location.reload()}>
                    <RefreshCw size={15} />
                    <span>Atualizar</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Gerenciamento</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Próximo Passo */}
              <div className="ribbon-group ribbon-group-flex">
                <div className="ribbon-group-tools">
                  <div className="ribbon-next-step">
                    <ArrowRight size={14} className="icon-accent" />
                    <div className="next-step-text">
                      <strong>Próximo Passo:</strong>
                      <span>{activeProject ? 'Abrir o Protocolo e definir PCC, descritores e critérios' : 'Criar ou selecionar um projeto de revisão'}</span>
                    </div>
                    {activeProject && (
                      <button type="button" className="tool-btn-next" onClick={() => navToProjectPage('protocol')}>
                        Ir para Protocolo <ArrowRight size={12} />
                      </button>
                    )}
                  </div>
                </div>
                <span className="ribbon-group-title">Fluxo de Trabalho</span>
              </div>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: INÍCIO (Dashboard)
              Purpose: Overview of the project, quick navigation to stages
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'dashboard' && (
            <>
              {/* Group: Ir Para (Etapas) */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                    onClick={() => navToProjectPage('protocol')} disabled={!activeProject}>
                    <BookOpen size={16} /><span>Protocolo</span>
                  </button>
                  <button type="button" className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                    onClick={() => navToProjectPage('harvest')} disabled={!activeProject}>
                    <Download size={16} /><span>Coleta</span>
                  </button>
                  <button type="button" className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                    onClick={() => navToProjectPage('screening')} disabled={!activeProject}>
                    <CheckSquare size={16} /><span>Triagem</span>
                  </button>
                  <button type="button" className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                    onClick={() => navToProjectPage('extraction')} disabled={!activeProject}>
                    <FileText size={16} /><span>Extração</span>
                  </button>
                  <button type="button" className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                    onClick={() => navToProjectPage('export')} disabled={!activeProject}>
                    <FileDown size={16} /><span>Exportar</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Ir para Etapa</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Projeto Atual */}
              <div className="ribbon-group ribbon-group-flex">
                <div className="ribbon-group-tools">
                  <div className="ribbon-info-box">
                    <span className="info-label">Projeto:</span>
                    <span className="info-value">{activeProject?.title || '—'}</span>
                  </div>
                  <div className="ribbon-info-box">
                    <span className="info-label">Diretriz:</span>
                    <span className="info-value">{activeProject?.methodology || 'PRISMA-ScR'}</span>
                  </div>
                  <div className="ribbon-info-box">
                    <span className="info-label">Domínio:</span>
                    <span className="info-value">Ciências Sociais Aplicadas</span>
                  </div>
                </div>
                <span className="ribbon-group-title">Contexto do Projeto</span>
              </div>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: 1. PROTOCOLO
              Purpose: Write the entire manuscript/protocol.
              Primary actions: Save, Copy manuscript, AI suggestion.
              Secondary: Navigate between the 6 sub-sections.
              Context: Descriptor rules reminder.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'protocol' && (
            <>
              {/* Group: Manuscrito */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-large" onClick={() => clickDomByText('button', 'Salvar Tudo')}>
                    <Save size={20} className="icon-accent" />
                    <span>Salvar<br />Tudo</span>
                  </button>
                  <button type="button" className="tool-btn-large" onClick={() => clickDomByText('button', 'Copiar Manuscrito')}>
                    <Copy size={20} />
                    <span>Copiar<br />Artigo</span>
                  </button>
                  {aiEnabled && (
                    <button type="button" className="tool-btn-large" onClick={() => clickDomByText('button', 'Sugerir com IA')}>
                      <Sparkles size={20} className="icon-sparkle" />
                      <span>Sugerir<br />com IA</span>
                    </button>
                  )}
                </div>
                <span className="ribbon-group-title">Manuscrito</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Seções (PRISMA-ScR sub-tabs) */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools ribbon-group-tools-wrap">
                  <button type="button" className="tool-btn-compact" onClick={() => clickDomByIndex('.studio-tab', 0)}>
                    <Edit3 size={12} /> Título & Resumo
                  </button>
                  <button type="button" className="tool-btn-compact" onClick={() => clickDomByIndex('.studio-tab', 1)}>
                    <BookOpen size={12} /> Justificativa & PCC
                  </button>
                  <button type="button" className="tool-btn-compact" onClick={() => clickDomByIndex('.studio-tab', 2)}>
                    <Search size={12} /> Fontes & Descritores
                  </button>
                  <button type="button" className="tool-btn-compact" onClick={() => clickDomByIndex('.studio-tab', 3)}>
                    <Filter size={12} /> Seleção & Síntese
                  </button>
                  <button type="button" className="tool-btn-compact" onClick={() => clickDomByIndex('.studio-tab', 4)}>
                    <BookMarked size={12} /> Discussão & Conclusões
                  </button>
                  <button type="button" className="tool-btn-compact tool-btn-highlight" onClick={() => clickDomByIndex('.studio-tab', 5)}>
                    <ListChecks size={12} /> Checklist (22 Itens)
                  </button>
                </div>
                <span className="ribbon-group-title">Seções do Protocolo</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Regras & Próximo Passo */}
              <div className="ribbon-group ribbon-group-flex">
                <div className="ribbon-group-tools">
                  <div className="ribbon-next-step">
                    <HelpCircle size={14} className="icon-accent" />
                    <div className="next-step-text">
                      <strong>Descritores VuFind:</strong>
                      <span>Máx. 2 termos com AND por par · Sugestão: ~5 pares por idioma</span>
                    </div>
                    <button type="button" className="tool-btn-next" onClick={() => navToProjectPage('harvest')}>
                      Próximo: Coleta <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
                <span className="ribbon-group-title">Regras & Fluxo</span>
              </div>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: 2. COLETA
              Purpose: Execute federated search, import files, deduplicate.
              Primary: Start harvest (the one action you came here for).
              Context: Which bases are connected, descriptor preview.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'harvest' && (
            <>
              {/* Group: Execução */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-large" onClick={() => clickDom('.btn-primary')}>
                    <Play size={20} className="icon-accent" />
                    <span>Iniciar<br />Coleta</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Busca Federada</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Importar & Desduplicar */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-vertical" onClick={() => clickDom('.btn-import-ris')}>
                    <Upload size={15} />
                    <span>Importar RIS</span>
                  </button>
                  <button type="button" className="tool-btn-vertical" onClick={() => clickDom('.btn-dedup')}>
                    <Layers size={15} />
                    <span>Desduplicar</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Importação & Limpeza</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Bases Acadêmicas Conectadas */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <span className="db-badge bdtd">BDTD</span>
                  <span className="db-badge scielo">SciELO</span>
                  <span className="db-badge scopus">Scopus</span>
                  <span className="db-badge pubmed">PubMed</span>
                  <span className="db-badge openalex">OpenAlex</span>
                </div>
                <span className="ribbon-group-title">Bases Conectadas</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Próximo Passo */}
              <div className="ribbon-group ribbon-group-flex">
                <div className="ribbon-group-tools">
                  <div className="ribbon-next-step">
                    <ArrowRight size={14} className="icon-accent" />
                    <div className="next-step-text">
                      <strong>Após a coleta:</strong>
                      <span>Verifique o acervo recuperado e prossiga para a triagem de títulos e resumos</span>
                    </div>
                    <button type="button" className="tool-btn-next" onClick={() => navToProjectPage('screening')}>
                      Próximo: Triagem <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
                <span className="ribbon-group-title">Fluxo de Trabalho</span>
              </div>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: 3. TRIAGEM (Fase 1)
              Purpose: Decide Include/Exclude/Pending for each paper.
              Primary: The 3 decision buttons (the core of this tab).
              Secondary: Filters by status, AI batch, add manual paper.
              Context: Zero hallucination rule.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'screening' && (
            <>
              {/* Group: Decisão (the 3 actions that are THE point of this tab) */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-decision included" onClick={() => clickDomByText('button', 'Incluir')}>
                    <Check size={18} />
                    <span>Incluir</span>
                  </button>
                  <button type="button" className="tool-btn-decision excluded" onClick={() => clickDomByText('button', 'Excluir')}>
                    <X size={18} />
                    <span>Excluir</span>
                  </button>
                  <button type="button" className="tool-btn-decision pending" onClick={() => clickDomByText('button', 'Pendente')}>
                    <Clock size={18} />
                    <span>Pendente</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Decisão do Estudo</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Assistente IA */}
              {aiEnabled && (
                <>
                  <div className="ribbon-group">
                    <div className="ribbon-group-tools">
                      <button type="button" className="tool-btn-vertical" onClick={() => clickDomByText('button', 'Triar')}>
                        <Sparkles size={15} className="icon-sparkle" />
                        <span>Triar com IA</span>
                      </button>
                      <button type="button" className="tool-btn-vertical" onClick={() => clickDom('.btn-secondary')}>
                        <Zap size={15} />
                        <span>Lote com IA</span>
                      </button>
                    </div>
                    <span className="ribbon-group-title">Assistente de IA</span>
                  </div>
                  <div className="ribbon-divider" />
                </>
              )}

              {/* Group: Filtros de Status */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools ribbon-group-tools-wrap">
                  <button type="button" className="tool-btn-compact" onClick={() => clickDomByIndex('.counter-btn', 0)}>
                    Todos
                  </button>
                  <button type="button" className="tool-btn-compact tool-btn-pending" onClick={() => clickDomByIndex('.counter-btn', 1)}>
                    <Clock size={11} /> Pendentes
                  </button>
                  <button type="button" className="tool-btn-compact tool-btn-included" onClick={() => clickDomByIndex('.counter-btn', 2)}>
                    <Check size={11} /> Incluídos
                  </button>
                  <button type="button" className="tool-btn-compact tool-btn-excluded" onClick={() => clickDomByIndex('.counter-btn', 3)}>
                    <X size={11} /> Excluídos
                  </button>
                </div>
                <span className="ribbon-group-title">Filtrar por Decisão</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Acervo */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-vertical" onClick={() => clickDom('.btn-primary')}>
                    <Plus size={15} />
                    <span>Adicionar Artigo</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Acervo Manual</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Próximo Passo */}
              <div className="ribbon-group ribbon-group-flex">
                <div className="ribbon-group-tools">
                  <div className="ribbon-next-step">
                    <ShieldCheck size={14} className="icon-accent" />
                    <div className="next-step-text">
                      <strong>Regra de Ouro:</strong>
                      <span>Na dúvida, marque como Pendente para leitura integral do texto completo</span>
                    </div>
                    <button type="button" className="tool-btn-next" onClick={() => navToProjectPage('extraction')}>
                      Próximo: Extração <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
                <span className="ribbon-group-title">Diretrizes & Fluxo</span>
              </div>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: 4. EXTRAÇÃO (Fase 2 / Data Charting)
              Purpose: Fill the extraction questionnaire for included papers.
              Primary: Save answers, AI extraction.
              Context: How many papers extracted vs remaining.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'extraction' && (
            <>
              {/* Group: Data Charting */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-large" onClick={() => clickDomByText('button', 'Salvar')}>
                    <Save size={20} className="icon-accent" />
                    <span>Salvar<br />Respostas</span>
                  </button>
                  {aiEnabled && (
                    <button type="button" className="tool-btn-large" onClick={() => clickDomByText('button', 'Extrair com IA')}>
                      <Sparkles size={20} className="icon-sparkle" />
                      <span>Extrair<br />com IA</span>
                    </button>
                  )}
                </div>
                <span className="ribbon-group-title">Data Charting</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Navegação de Artigos */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-vertical" onClick={() => clickDomByText('button', 'Baixar PDF')}>
                    <Download size={15} />
                    <span>Baixar PDF</span>
                  </button>
                  <button type="button" className="tool-btn-vertical" onClick={() => clickDomByText('button', 'DOI')}>
                    <Globe size={15} />
                    <span>Abrir DOI</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Texto Completo</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Próximo Passo */}
              <div className="ribbon-group ribbon-group-flex">
                <div className="ribbon-group-tools">
                  <div className="ribbon-next-step">
                    <ArrowRight size={14} className="icon-accent" />
                    <div className="next-step-text">
                      <strong>Questionário:</strong>
                      <span>Responda as perguntas de mapeamento (Q-1 a Q-N) para cada estudo incluído</span>
                    </div>
                    <button type="button" className="tool-btn-next" onClick={() => navToProjectPage('export')}>
                      Próximo: Exportar <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
                <span className="ribbon-group-title">Mapeamento & Fluxo</span>
              </div>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: 5. EXPORTAR (Síntese & Relatórios)
              Purpose: Generate outputs — the deliverables of the review.
              Primary: Download Excel, manuscript, diagrams.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'export' && (
            <>
              {/* Group: Relatórios de Dados */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-large" onClick={() => clickDom('.export-card:first-child')}>
                    <FileSpreadsheet size={20} className="icon-accent" />
                    <span>Planilha<br />Excel</span>
                  </button>
                  <button type="button" className="tool-btn-large" onClick={() => clickDom('.export-card:last-child')}>
                    <BookMarked size={20} />
                    <span>BibTeX<br />Citações</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Exportar Dados</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Manuscrito */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-vertical" onClick={() => navToProjectPage('protocol')}>
                    <Copy size={15} />
                    <span>Copiar Artigo</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Manuscrito</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Visualizações */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <div className="ribbon-info-box">
                    <span className="info-label">Diagrama Ativo:</span>
                    <span className="info-value">Fluxograma PRISMA 2020</span>
                  </div>
                  <div className="ribbon-info-box">
                    <span className="info-label">Formato:</span>
                    <span className="info-value">Excel (.xlsx) + BibTeX (.bib)</span>
                  </div>
                </div>
                <span className="ribbon-group-title">Visualização</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Revisão Concluída */}
              <div className="ribbon-group ribbon-group-flex">
                <div className="ribbon-group-tools">
                  <div className="ribbon-next-step ribbon-step-final">
                    <CheckSquare size={14} className="icon-accent" />
                    <div className="next-step-text">
                      <strong>Etapa Final:</strong>
                      <span>Verifique o checklist PRISMA-ScR (22 itens) no Protocolo antes de submeter</span>
                    </div>
                    <button type="button" className="tool-btn-next" onClick={() => navToProjectPage('protocol')}>
                      Voltar ao Protocolo <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
                <span className="ribbon-group-title">Finalização</span>
              </div>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: FERRAMENTAS (Configurações & IA)
              Purpose: Configure AI providers, test connections, set preferences.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'settings' && (
            <>
              {/* Group: Modo de Operação */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className={`tool-btn-large ${aiEnabled ? 'tool-active' : ''}`}
                    onClick={() => setAiEnabled(true)}>
                    <Sparkles size={20} className={aiEnabled ? 'icon-sparkle' : ''} />
                    <span>Modo<br />IA</span>
                  </button>
                  <button type="button" className={`tool-btn-large ${!aiEnabled ? 'tool-active' : ''}`}
                    onClick={() => setAiEnabled(false)}>
                    <Edit3 size={20} />
                    <span>Modo<br />Manual</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Modo de Operação</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Provedores de IA */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <div className="ribbon-provider-stack">
                    <span className="db-badge google"><Cpu size={10} /> Google Gemini</span>
                    <span className="db-badge qwen"><Server size={10} /> Alibaba Qwen</span>
                    <span className="db-badge local"><Database size={10} /> Ollama Local</span>
                  </div>
                </div>
                <span className="ribbon-group-title">Provedores Disponíveis</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Ações de Teste */}
              <div className="ribbon-group">
                <div className="ribbon-group-tools">
                  <button type="button" className="tool-btn-vertical" onClick={() => clickDomByText('button', 'Testar')}>
                    <Zap size={15} />
                    <span>Testar IA</span>
                  </button>
                  <button type="button" className="tool-btn-vertical" onClick={() => clickDomByText('button', 'Salvar')}>
                    <Save size={15} />
                    <span>Salvar Config</span>
                  </button>
                </div>
                <span className="ribbon-group-title">Conexão</span>
              </div>

              <div className="ribbon-divider" />

              {/* Group: Sistema */}
              <div className="ribbon-group ribbon-group-flex">
                <div className="ribbon-group-tools">
                  <div className="ribbon-info-box">
                    <span className="info-label">Backend:</span>
                    <span className="info-value">
                      <span className={`status-dot-inline ${backendStatus === 'online' ? 'online' : 'offline'}`} />
                      {backendVersion || 'v2.0'} ({backendStatus === 'online' ? 'conectado' : 'desconectado'})
                    </span>
                  </div>
                  <div className="ribbon-info-box">
                    <span className="info-label">Modelos Aprovados:</span>
                    <span className="info-value">gemini-3.6-flash · qwen3.8-max · Qwen-3.5-27B</span>
                  </div>
                </div>
                <span className="ribbon-group-title">Estado do Sistema</span>
              </div>
            </>
          )}
        </div>
      )}
    </header>
  )
}
