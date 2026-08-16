/**
 * RSAC V2 — Dashboard Page
 * Tela inicial com métricas, boas-vindas e visão geral dos projetos.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FolderOpen,
  FileText,
  CheckCircle2,
  Clock,
  Plus,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import type { Project } from '@/types/api'
import './DashboardPage.css'

export function DashboardPage(): JSX.Element {
  const navigate = useNavigate()
  const { backendStatus, activeProject, setActiveProject } = useSettingsStore()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (backendStatus === 'online') {
      loadProjects()
    }
  }, [backendStatus])

  const loadProjects = async () => {
    try {
      const response = await api.listProjects(false)
      setProjects(response.items)
    } catch (error) {
      console.error('Erro ao carregar projetos:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenProject = (project: Project) => {
    setActiveProject(project)
    navigate(`/projects/${project.id}/protocol`)
  }

  return (
    <div className="dashboard animate-slide-up">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">
            <Sparkles size={28} className="dashboard-title-icon" />
            Revisão Sistemática Assistida por Computador
          </h1>
          <p className="dashboard-subtitle">
            Gerencie suas revisões sistemáticas com assistência de Inteligência Artificial
          </p>
        </div>
        <button
          className="dashboard-cta"
          onClick={() => navigate('/projects')}
        >
          <Plus size={18} />
          Novo Projeto
        </button>
      </div>

      {/* Stat Cards */}
      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}>
            <FolderOpen size={22} />
          </div>
          <div className="stat-content">
            <span className="stat-value">{projects.length}</span>
            <span className="stat-label">Projetos Ativos</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--color-info-bg)', color: 'var(--color-info)' }}>
            <FileText size={22} />
          </div>
          <div className="stat-content">
            <span className="stat-value">—</span>
            <span className="stat-label">Papers Coletados</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--color-success-bg)', color: 'var(--color-success)' }}>
            <CheckCircle2 size={22} />
          </div>
          <div className="stat-content">
            <span className="stat-value">—</span>
            <span className="stat-label">Papers Incluídos</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--color-warning-bg)', color: 'var(--color-warning)' }}>
            <Clock size={22} />
          </div>
          <div className="stat-content">
            <span className="stat-value">—</span>
            <span className="stat-label">Pendentes de Triagem</span>
          </div>
        </div>
      </div>

      {/* Projects List */}
      <div className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">Projetos Recentes</h2>
          <button className="section-link" onClick={() => navigate('/projects')}>
            Ver todos <ArrowRight size={14} />
          </button>
        </div>

        {loading ? (
          <div className="dashboard-loading">
            <div className="loading-spinner animate-spin" />
            <span>Carregando projetos...</span>
          </div>
        ) : projects.length === 0 ? (
          <div className="dashboard-empty">
            <FolderOpen size={48} strokeWidth={1} />
            <h3>Nenhum projeto ainda</h3>
            <p>Crie seu primeiro projeto de revisão sistemática para começar.</p>
            <button className="dashboard-cta" onClick={() => navigate('/projects')}>
              <Plus size={18} />
              Criar Primeiro Projeto
            </button>
          </div>
        ) : (
          <div className="project-grid">
            {projects.map((project) => {
              const isActive = activeProject?.id === project.id
              return (
                <div
                  key={project.id}
                  className={`project-card ${isActive ? 'active-card' : ''}`}
                  onClick={() => handleOpenProject(project)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handleOpenProject(project)
                    }
                  }}
                  title={`Abrir projeto: ${project.title}`}
                >
                  <div className="project-card-header">
                    <h3 className="project-card-title">{project.title}</h3>
                    <div className="project-card-meta">
                      <span className="project-card-methodology">{project.methodology}</span>
                      {isActive && (
                        <span className="badge-active">
                          <CheckCircle2 size={11} /> Ativo
                        </span>
                      )}
                    </div>
                  </div>
                  {project.description && (
                    <p className="project-card-description">{project.description}</p>
                  )}
                  <div className="project-card-footer">
                    <span className="project-card-date">
                      {new Date(project.created_at).toLocaleDateString('pt-BR')}
                    </span>
                    <span className="project-card-action">
                      Abrir Projeto <ArrowRight size={14} className="project-card-arrow" />
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
