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
  StopCircle,
  Upload,
  BarChart3,
  ListChecks,
  BookMarked,
  Edit3,
  ShieldCheck,
  Globe,
  Key,
  KeyRound,
  Cpu,
  Server,
  FolderArchive,
} from 'lucide-react'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import { PROTOCOL_CATALOG } from '@/data/protocolCatalog'
import type { Methodology } from '@/types/api'
import { RsacMark } from '@/components/brand/RsacMark'
import { BetaBadge } from '@/components/brand/BetaBadge'
import { GrupoDoRibbon } from './ribbon/GrupoDoRibbon'
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
  { id: 'export', label: 'Síntese & Exportar', icon: <FileDown size={14} />, path: '/projects/:id/export', requiresProject: true, stepNumber: 5 },
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
  const { actions } = useRibbonStore()

  /* Recolhimento vem do store persistido, não de `useState`: local, ele se
     perdia a cada troca de rota — recolher a faixa no Protocolo e voltar da
     Coleta com ela aberta de novo. */
  const ribbonCollapsed = useSettingsStore((s) => s.ribbonCollapsed)
  const setRibbonCollapsed = useSettingsStore((s) => s.setRibbonCollapsed)

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
      return pathname.includes(`/${tab.id}`)
    }
    return pathname.startsWith(tab.path)
  }

  const navToProjectPage = (section: string) => {
    if (activeProject) {
      navigate(`/projects/${activeProject.id}/${section}`)
    } else {
      navigate('/projects')
    }
  }

  const currentTab = RIBBON_TABS.find((tab) => isTabActive(tab)) || RIBBON_TABS[0]

  const activeProtocol =
    PROTOCOL_CATALOG[activeProject?.methodology as Methodology] ||
    PROTOCOL_CATALOG['PRISMA-ScR']
  const checklistCount = activeProtocol?.checklistItems?.length || 22

  return (
    <header className="ribbon-container">
      {/* ═══════════════════════════════════════════════════════════════════
          LAYER 1: APPLICATION TITLE BAR
          Brand + Active Project Context + Quick Global Controls
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="ribbon-titlebar">
        <button
          type="button"
          className="ribbon-brand rsac-on-brand"
          onClick={() => navigate('/')}
          title="RSAC — Revisão Sistemática Assistida por Computador (Versão 2, beta)"
          aria-label="Ir para o início"
        >
          <RsacMark size={19} tone="brand" label={null} />
          <span className="brand-name">RSAC<span className="brand-ver">v2</span></span>
          <BetaBadge tone="brand" size="xs" />
        </button>

        <div className="ribbon-active-project-bar">
          {activeProject ? (
            <button
              type="button"
              className="active-project-pill"
              onClick={() => navigate('/projects')}
              title="Trocar projeto ativo"
            >
              <FolderDot size={13} className="icon-project" aria-hidden="true" />
              <span className="project-label">PROJETO:</span>
              <strong className="project-title">{activeProject.title}</strong>
              <span className="project-methodology-tag">{activeProject.methodology}</span>
            </button>
          ) : (
            <button type="button" className="btn-select-project-alert" onClick={() => navigate('/projects')}>
              <FolderOpen size={13} />
              <span>Selecionar ou Criar Projeto</span>
            </button>
          )}
        </div>

        <div className="ribbon-quick-actions">
          {/* Master AI Mode Pill */}
          <button
            type="button"
            className={`ribbon-action-pill ${aiEnabled ? 'ai-active' : 'ai-manual'}`}
            onClick={() => setAiEnabled(!aiEnabled)}
            title={aiEnabled ? 'Assistência Ativa — clique para modo manual' : 'Modo 100% Manual — clique para ativar assistência'}
          >
            {aiEnabled ? <Sparkles size={12} className="icon-sparkle" /> : <Edit3 size={12} />}
            <span>{aiEnabled ? 'Assistência' : 'Manual'}</span>
          </button>

          {/* Collapse Ribbon */}
          <button
            type="button"
            className={`ribbon-icon-btn collapse-btn ${ribbonCollapsed ? 'active' : ''}`}
            onClick={() => setRibbonCollapsed(!ribbonCollapsed)}
            title={ribbonCollapsed ? 'Expandir barra de ferramentas' : 'Recolher barra de ferramentas'}
          >
            {ribbonCollapsed ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
          </button>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          LAYER 2: WORKFLOW NAVIGATION TABS
          The pipeline ribbon tabs (Project → Protocol → Harvest → Screen → Extract → Export)
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="ribbon-tabs-bar">
        <nav className="ribbon-tabs-nav" aria-label="Navegação da Revisão Sistemática">
          {RIBBON_TABS.map((tab) => {
            const active = isTabActive(tab)
            const disabled = tab.requiresProject && !activeProject

            return (
              <button
                key={tab.id}
                type="button"
                className={`ribbon-tab-btn ${active ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
                disabled={disabled}
                onClick={() => {
                  if (tab.requiresProject && !activeProject) {
                    navigate('/projects')
                    return
                  }
                  navigate(resolvePath(tab))
                }}
                title={
                  disabled
                    ? 'Selecione ou crie um projeto primeiro'
                    : tab.stepNumber
                    ? `Etapa ${tab.stepNumber}: ${tab.label}`
                    : tab.label
                }
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
              <GrupoDoRibbon titulo="Novo">
              <button
                type="button"
                className="tool-btn-large"
                onClick={() => {
                  if (actions.createProject) {
                    actions.createProject()
                  } else {
                    navigate('/projects')
                  }
                }}
              >
                <Plus size={20} className="icon-accent" />
                <span>Novo<br />Projeto</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Gerenciamento */}
              <GrupoDoRibbon titulo="Gerenciamento">
              <button type="button" className="tool-btn-vertical" onClick={() => window.location.reload()}>
                <RefreshCw size={15} />
                <span>Atualizar</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Portabilidade */}
              <GrupoDoRibbon titulo="Portabilidade">
              <button type="button" className="tool-btn-vertical" onClick={() => navigate('/settings')} title="Exportar ou importar perfil completo">
                <FolderArchive size={15} />
                <span>Perfil</span>
              </button>
              <button type="button" className="tool-btn-vertical" onClick={() => navigate('/settings')} title="Exportar ou importar chaves de API">
                <KeyRound size={15} />
                <span>Chaves</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Próximo Passo */}
              <GrupoDoRibbon titulo="Fluxo de Trabalho" expansivel>
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
              </GrupoDoRibbon>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: INÍCIO (Dashboard)
              Purpose: High-level overview, quick resume, pipeline status
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'dashboard' && (
            <>
              {/* Group: Ir Para (Etapas) */}
              <GrupoDoRibbon titulo="Ir para Etapa">
              <button
                type="button"
                className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                onClick={() => navToProjectPage('protocol')}
                disabled={!activeProject}
              >
                <BookOpen size={16} />
                <span>Protocolo</span>
              </button>
              <button
                type="button"
                className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                onClick={() => navToProjectPage('harvest')}
                disabled={!activeProject}
              >
                <Download size={16} />
                <span>Coleta</span>
              </button>
              <button
                type="button"
                className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                onClick={() => navToProjectPage('screening')}
                disabled={!activeProject}
              >
                <CheckSquare size={16} />
                <span>Triagem</span>
              </button>
              <button
                type="button"
                className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                onClick={() => navToProjectPage('extraction')}
                disabled={!activeProject}
              >
                <FileText size={16} />
                <span>Extração</span>
              </button>
              <button
                type="button"
                className={`tool-btn-vertical ${!activeProject ? 'disabled' : ''}`}
                onClick={() => navToProjectPage('export')}
                disabled={!activeProject}
              >
                <FileDown size={16} />
                <span>Exportar</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Projeto Atual */}
              <GrupoDoRibbon titulo="Contexto do Projeto" expansivel>
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
              </GrupoDoRibbon>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: 1. PROTOCOLO (Estúdio de Redação & Manuscrito)
              Purpose: Formulate research question, eligibility, descriptors.
              Primary actions: Save, Copy manuscript, AI suggestion.
              Secondary: Navigate between the sub-sections.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'protocol' && (
            <>
              {/* Group: Manuscrito */}
              <GrupoDoRibbon titulo="Manuscrito">
              <button
                type="button"
                className="tool-btn-large"
                onClick={() => actions.saveProtocol?.()}
                disabled={actions.isProtocolSaving}
              >
                <Save size={20} className="icon-accent" />
                <span>Salvar<br />Tudo</span>
              </button>
              <button
                type="button"
                className="tool-btn-large"
                onClick={() => actions.copyManuscript?.()}
              >
                <Copy size={20} />
                <span>Copiar<br />Artigo</span>
              </button>
              {aiEnabled && (
                <button
                  type="button"
                  className="tool-btn-large"
                  onClick={() => actions.openAiSuggest?.()}
                >
                  <Sparkles size={20} className="icon-sparkle" />
                  <span>Sugerir<br />com Assistência</span>
                </button>
              )}
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Seções */}
              <GrupoDoRibbon titulo="Seções do Protocolo" quebraLinha>
              <button
                type="button"
                className={`tool-btn-compact ${actions.activeStudioTabIndex === 0 ? 'active' : ''}`}
                onClick={() => actions.setStudioTab?.(0)}
              >
                <Edit3 size={12} /> Título & Resumo
              </button>
              <button
                type="button"
                className={`tool-btn-compact ${actions.activeStudioTabIndex === 1 ? 'active' : ''}`}
                onClick={() => actions.setStudioTab?.(1)}
              >
                <BookOpen size={12} /> Justificativa & PCC
              </button>
              <button
                type="button"
                className={`tool-btn-compact ${actions.activeStudioTabIndex === 2 ? 'active' : ''}`}
                onClick={() => actions.setStudioTab?.(2)}
              >
                <Search size={12} /> Fontes & Descritores
              </button>
              <button
                type="button"
                className={`tool-btn-compact ${actions.activeStudioTabIndex === 3 ? 'active' : ''}`}
                onClick={() => actions.setStudioTab?.(3)}
              >
                <Filter size={12} /> Seleção & Síntese
              </button>
              <button
                type="button"
                className={`tool-btn-compact ${actions.activeStudioTabIndex === 4 ? 'active' : ''}`}
                onClick={() => actions.setStudioTab?.(4)}
              >
                <BookMarked size={12} /> Discussão & Conclusões
              </button>
              <button
                type="button"
                className={`tool-btn-compact tool-btn-highlight ${actions.activeStudioTabIndex === 5 ? 'active' : ''}`}
                onClick={() => actions.setStudioTab?.(5)}
              >
                <ListChecks size={12} /> Checklist ({checklistCount} Itens)
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Regras & Próximo Passo */}
              <GrupoDoRibbon titulo="Diretriz & Próximo Passo" expansivel>
              <div className="ribbon-next-step">
                <HelpCircle size={14} className="icon-accent" />
                <div className="next-step-text">
                  <strong>Regra de Descritores:</strong>
                  <span>Máx. 2 termos por expressão (pares com AND) · Até 5 pares por idioma</span>
                </div>
                <button type="button" className="tool-btn-next" onClick={() => navToProjectPage('harvest')}>
                  Próximo: Coleta <ArrowRight size={12} />
                </button>
              </div>
              </GrupoDoRibbon>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: 2. COLETA (Busca Federada)
              Purpose: Execute searches across academic databases.
              Primary: Start Harvest, Deduplicate.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'harvest' && (
            <>
              {/* Group: Execução */}
              <GrupoDoRibbon titulo="Busca Federada">
              <button
                type="button"
                className="tool-btn-large"
                onClick={() => {
                  if (actions.isHarvesting) {
                    actions.stopHarvest?.()
                  } else {
                    actions.startHarvest?.()
                  }
                }}
              >
                {actions.isHarvesting ? (
                  <StopCircle size={20} className="icon-destructive" />
                ) : (
                  <Play size={20} className="icon-accent" />
                )}
                <span>
                  {actions.isHarvesting ? (
                    <>Parar<br />Coleta</>
                  ) : (
                    <>Iniciar<br />Coleta</>
                  )}
                </span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Limpeza & Deduplicação */}
              <GrupoDoRibbon titulo="Tratamento do Acervo">
              <button
                type="button"
                className="tool-btn-vertical"
                onClick={() => actions.openDedupModal?.()}
              >
                <Layers size={15} />
                <span>Deduplicação</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Bases Acadêmicas Conectadas */}
              <GrupoDoRibbon titulo="Bases Conectadas" semInvolucro>
            <div className="ribbon-db-grid">
              <span className="db-badge bdtd">BDTD</span>
              <span className="db-badge scielo">SciELO</span>
              <span className="db-badge scopus">Scopus</span>
              <span className="db-badge pubmed">PubMed</span>
              <span className="db-badge openalex">OpenAlex</span>
            </div>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Próximo Passo */}
              <GrupoDoRibbon titulo="Fluxo de Trabalho" expansivel>
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
              </GrupoDoRibbon>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: 3. TRIAGEM (Fase 1)
              Purpose: Decide Include/Exclude/Pending for each paper.
              Primary: The 3 decision buttons (the core of this tab).
              Secondary: Filters by status, AI batch.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'screening' && (
            <>
              {/* Group: Decisão */}
              <GrupoDoRibbon titulo="Decisão do Estudo">
              <button
                type="button"
                className="tool-btn-decision included"
                onClick={() => actions.decisionInclude?.()}
                disabled={!actions.canScreenSingle}
              >
                <Check size={18} />
                <span>Incluir</span>
              </button>
              <button
                type="button"
                className="tool-btn-decision excluded"
                onClick={() => actions.decisionExclude?.()}
                disabled={!actions.canScreenSingle}
              >
                <X size={18} />
                <span>Excluir</span>
              </button>
              <button
                type="button"
                className="tool-btn-decision pending"
                onClick={() => actions.decisionPending?.()}
                disabled={!actions.canScreenSingle}
              >
                <Clock size={18} />
                <span>Pendente</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Tratamento do Acervo
                  A auditoria de duplicatas era exclusiva do cabeçalho da
                  Triagem. Ao consolidar o cabeçalho em uma única ação primária,
                  o comando passa a viver aqui — mesmo registro tipado que a
                  Coleta usa. */}
              <GrupoDoRibbon titulo="Tratamento do Acervo">
              <button
                type="button"
                className="tool-btn-vertical"
                onClick={() => actions.openDedupModal?.()}
              >
                <Layers size={15} />
                <span>Auditar<br />Duplicatas</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Assistência */}
              {aiEnabled && (
                <>
                  <GrupoDoRibbon titulo="Assistência">
                      <button
                        type="button"
                        className="tool-btn-vertical"
                        onClick={() => actions.screenAiSingle?.()}
                        disabled={!actions.canScreenSingle}
                      >
                        <Sparkles size={15} className="icon-sparkle" />
                        <span>Triar Estudo</span>
                      </button>
                      <button
                        type="button"
                        className="tool-btn-vertical"
                        onClick={() => actions.screenAiBatch?.()}
                      >
                        <Zap size={15} />
                        <span>Triar Lote</span>
                      </button>
                  </GrupoDoRibbon>
                  <div className="ribbon-divider" />
                </>
              )}

              {/* Group: Filtros de Status */}
              <GrupoDoRibbon titulo="Filtrar por Decisão" quebraLinha>
              <button
                type="button"
                className={`tool-btn-compact ${actions.activeDecisionFilter === '' ? 'active' : ''}`}
                onClick={() => actions.setDecisionFilter?.('')}
              >
                Todos
              </button>
              <button
                type="button"
                className={`tool-btn-compact tool-btn-pending ${actions.activeDecisionFilter === 'Pendente' ? 'active' : ''}`}
                onClick={() => actions.setDecisionFilter?.('Pendente')}
              >
                <Clock size={11} /> Pendentes
              </button>
              <button
                type="button"
                className={`tool-btn-compact tool-btn-included ${actions.activeDecisionFilter === 'Incluído' ? 'active' : ''}`}
                onClick={() => actions.setDecisionFilter?.('Incluído')}
              >
                <Check size={11} /> Incluídos
              </button>
              <button
                type="button"
                className={`tool-btn-compact tool-btn-excluded ${actions.activeDecisionFilter === 'Excluído' ? 'active' : ''}`}
                onClick={() => actions.setDecisionFilter?.('Excluído')}
              >
                <X size={11} /> Excluídos
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Próximo Passo */}
              <GrupoDoRibbon titulo="Avanço Metodológico" expansivel>
              <div className="ribbon-next-step">
                <ShieldCheck size={14} className="icon-accent" />
                <div className="next-step-text">
                  <strong>Após triar todos os estudos:</strong>
                  <span>Os estudos com decisão "Incluído" avançam para a Extração de Dados (Fase 2)</span>
                </div>
                <button type="button" className="tool-btn-next" onClick={() => navToProjectPage('extraction')}>
                  Próximo: Extração <ArrowRight size={12} />
                </button>
              </div>
              </GrupoDoRibbon>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: 4. EXTRAÇÃO (Fase 2 / Data Charting)
              Purpose: Fill the extraction questionnaire for included papers.
              Primary: Save answers, AI extraction.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'extraction' && (
            <>
              {/* Group: Data Charting */}
              <GrupoDoRibbon titulo="Data Charting">
              <button
                type="button"
                className="tool-btn-large"
                onClick={() => actions.saveExtraction?.()}
                disabled={actions.isExtractionSaving}
              >
                <Save size={20} className="icon-accent" />
                <span>Salvar<br />Respostas</span>
              </button>
              {aiEnabled && (
                <button
                  type="button"
                  className="tool-btn-large"
                  onClick={() => actions.extractAiGlobal?.()}
                >
                  <Sparkles size={20} className="icon-sparkle" />
                  <span>Extrair<br />com Assistência</span>
                </button>
              )}
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Navegação de Artigos */}
              <GrupoDoRibbon titulo="Texto Completo">
              <button
                type="button"
                className="tool-btn-vertical"
                onClick={() => actions.downloadPdf?.()}
              >
                <Download size={15} />
                <span>Baixar PDF</span>
              </button>
              <button
                type="button"
                className="tool-btn-vertical"
                onClick={() => actions.openDoiLink?.()}
                disabled={!actions.hasDoi}
              >
                <Globe size={15} />
                <span>Abrir DOI</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Próximo Passo */}
              <GrupoDoRibbon titulo="Mapeamento & Fluxo" expansivel>
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
              </GrupoDoRibbon>
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
              <GrupoDoRibbon titulo="Exportar Dados">
              <button
                type="button"
                className="tool-btn-large"
                onClick={() => actions.exportExcel?.()}
              >
                <FileSpreadsheet size={20} className="icon-accent" />
                <span>Planilha<br />Excel</span>
              </button>
              <button
                type="button"
                className="tool-btn-large"
                onClick={() => actions.exportBibtex?.()}
              >
                <BookMarked size={20} />
                <span>BibTeX<br />Citações</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Manuscrito */}
              <GrupoDoRibbon titulo="Manuscrito">
              <button type="button" className="tool-btn-vertical" onClick={() => navToProjectPage('protocol')}>
                <Copy size={15} />
                <span>Copiar Artigo</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Visualizações */}
              <GrupoDoRibbon titulo="Visualização">
              <div className="ribbon-info-box">
                <span className="info-label">Diagrama Ativo:</span>
                <span className="info-value">Fluxo de Seleção · {activeProtocol.shortLabel}</span>
              </div>
              <div className="ribbon-info-box">
                <span className="info-label">Formato:</span>
                <span className="info-value">Excel (.xlsx) + BibTeX (.bib)</span>
              </div>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Revisão Concluída */}
              <GrupoDoRibbon titulo="Finalização" expansivel>
              <div className="ribbon-next-step ribbon-step-final">
                <CheckSquare size={14} className="icon-accent" />
                <div className="next-step-text">
                  <strong>Etapa Final:</strong>
                  <span>Verifique o checklist {activeProtocol.shortLabel} ({checklistCount} itens) no Protocolo antes de submeter</span>
                </div>
                <button type="button" className="tool-btn-next" onClick={() => navToProjectPage('protocol')}>
                  Voltar ao Protocolo <ArrowRight size={12} />
                </button>
              </div>
              </GrupoDoRibbon>
            </>
          )}

          {/* ──────────────────────────────────────────────────────────────
              TAB: FERRAMENTAS (Configurações & IA)
              Purpose: Configure AI providers, test connections, set preferences.
          ────────────────────────────────────────────────────────────── */}
          {currentTab.id === 'settings' && (
            <>
              {/* Group: Modo de Operação */}
              <GrupoDoRibbon titulo="Modo de Operação">
              <button
                type="button"
                className={`tool-btn-large ${aiEnabled ? 'tool-active' : ''}`}
                onClick={() => setAiEnabled(true)}
              >
                <Sparkles size={20} className={aiEnabled ? 'icon-sparkle' : ''} />
                <span>Modo<br />Assistido</span>
              </button>
              <button
                type="button"
                className={`tool-btn-large ${!aiEnabled ? 'tool-active' : ''}`}
                onClick={() => setAiEnabled(false)}
              >
                <Edit3 size={20} />
                <span>Modo<br />Manual</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Provedores de Assistência */}
              <GrupoDoRibbon titulo="Provedores Disponíveis" semInvolucro>
            <div className="ribbon-provider-stack">
              <span className="db-badge google"><Cpu size={10} /> Google Gemini</span>
              <span className="db-badge qwen"><Server size={10} /> Alibaba Qwen</span>
              <span className="db-badge local"><Database size={10} /> Ollama Local</span>
            </div>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Ações de Teste */}
              <GrupoDoRibbon titulo="Conexão">
              <button
                type="button"
                className="tool-btn-vertical"
                onClick={() => actions.testConnection?.()}
                disabled={actions.isTestingSettings}
              >
                <Zap size={15} />
                <span>Testar Conexão</span>
              </button>
              <button
                type="button"
                className="tool-btn-vertical"
                onClick={() => actions.saveSettings?.()}
                disabled={actions.isSavingSettings}
              >
                <Save size={15} />
                <span>Salvar Config</span>
              </button>
              </GrupoDoRibbon>

              <div className="ribbon-divider" />

              {/* Group: Sistema */}
              <GrupoDoRibbon titulo="Estado do Sistema" expansivel>
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
              </GrupoDoRibbon>
            </>
          )}

        </div>
      )}
    </header>
  )
}
