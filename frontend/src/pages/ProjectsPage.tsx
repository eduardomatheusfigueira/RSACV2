/**
 * RSAC V2 — Projects Page
 * Listagem, criação e seleção de projetos de revisão sistemática.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus,
  FolderOpen,
  Calendar,
  CheckCircle2,
  Trash2,
  BookOpen,
  Search,
  Sparkles,
  ArrowRight,
  Filter,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { PROTOCOL_CATALOG, PROTOCOL_OPTIONS } from '@/data/protocolCatalog'
import type { Project, Methodology } from '@/types/api'
import './ProjectsPage.css'

export function ProjectsPage(): JSX.Element {
  const navigate = useNavigate()
  const { activeProject, setActiveProject } = useSettingsStore()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [searchFilter, setSearchFilter] = useState('')

  // Form State
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [methodology, setMethodology] = useState<Methodology>('PRISMA-ScR')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      setLoading(true)
      const data = await api.listProjects()
      setProjects(data.items)
    } catch (err) {
      console.error('Erro ao listar projetos:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    try {
      setSubmitting(true)
      const newProj = await api.createProject({
        title: title.trim(),
        description: description.trim(),
        methodology,
      })
      setProjects([newProj, ...projects])
      setActiveProject(newProj)
      setIsModalOpen(false)
      setTitle('')
      setDescription('')
      navigate(`/projects/${newProj.id}/protocol`)
    } catch (err) {
      console.error('Erro ao criar projeto:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm('Tem certeza que deseja excluir este projeto? Todos os dados vinculados serão apagados.')) {
      return
    }
    try {
      await api.deleteProject(id)
      setProjects(projects.filter((p) => p.id !== id))
      if (activeProject?.id === id) {
        setActiveProject(null)
      }
    } catch (err) {
      console.error('Erro ao excluir projeto:', err)
    }
  }

  const handleSelectProject = (project: Project) => {
    setActiveProject(project)
    navigate(`/projects/${project.id}/protocol`)
  }

  const filteredProjects = projects.filter(
    (p) =>
      p.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      p.description.toLowerCase().includes(searchFilter.toLowerCase()) ||
      p.methodology.toLowerCase().includes(searchFilter.toLowerCase())
  )

  return (
    <div className="projects-page animate-fade-in">
      {/* Top Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Projetos de Revisão</h1>
          <p className="page-subtitle">
            Crie, selecione ou gerencie seus protocolos e revisões sistemáticas
          </p>
        </div>
        <button className="btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={18} />
          Novo Projeto
        </button>
      </div>

      {/* Filter Bar */}
      <div className="projects-filter-bar">
        <div className="search-input-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Filtrar por título, metodologia ou descrição..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
          />
        </div>
      </div>

      {/* Grid of Projects */}
      {loading ? (
        <div className="loading-state">
          <div className="loading-spinner animate-spin" />
          <span>Carregando projetos...</span>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="empty-state">
          <FolderOpen size={48} strokeWidth={1.2} />
          <h3>Nenhum projeto encontrado</h3>
          <p>Comece criando seu primeiro projeto de revisão sistemática.</p>
          <button className="btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={18} />
            Criar Novo Projeto
          </button>
        </div>
      ) : (
        <div className="projects-grid">
          {filteredProjects.map((project) => {
            const isActive = activeProject?.id === project.id
            return (
              <div
                key={project.id}
                className={`project-card-full ${isActive ? 'active-card' : ''}`}
                onClick={() => handleSelectProject(project)}
              >
                <div className="card-header">
                  <div className="card-meta">
                    <span className="badge-methodology">{project.methodology}</span>
                    {isActive && (
                      <span className="badge-active">
                        <CheckCircle2 size={12} /> Ativo
                      </span>
                    )}
                  </div>
                  <button
                    className="btn-icon danger"
                    title="Excluir Projeto"
                    onClick={(e) => handleDeleteProject(project.id, e)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <h3 className="card-title">{project.title}</h3>
                <p className="card-desc">
                  {project.description || 'Sem descrição cadastrada.'}
                </p>

                <div className="card-footer">
                  <span className="card-date">
                    <Calendar size={13} />
                    {new Date(project.created_at).toLocaleDateString('pt-BR')}
                  </span>
                  <span className="card-action">
                    Acessar Etapas <ArrowRight size={14} />
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Create Modal */}
      {isModalOpen && (
        <div className="modal-overlay animate-fade-in" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Novo Projeto de Revisão</h2>
              <p>Defina o título, descrição e metodologia inicial</p>
            </div>
            <form onSubmit={handleCreateProject} className="modal-form">
              <div className="form-group">
                <label>Título do Projeto *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Arranjos Produtivos Locais e Governança Territorial no Desenvolvimento Regional: Uma Revisão de Escopo..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>Diretriz / Protocolo Metodológico</label>
                <select
                  value={methodology}
                  onChange={(e) => setMethodology(e.target.value as Methodology)}
                >
                  {PROTOCOL_OPTIONS.map((m) => {
                    const proto = PROTOCOL_CATALOG[m]
                    return (
                      <option key={m} value={m}>
                        {proto?.name || m}
                      </option>
                    )
                  })}
                </select>

                {/* Protocol Info Preview Card */}
                {PROTOCOL_CATALOG[methodology] && (
                  <div className="protocol-preview-box">
                    <div className="protocol-preview-header">
                      <span className="protocol-preview-badge">
                        {PROTOCOL_CATALOG[methodology].badge}
                      </span>
                      <span className="protocol-preview-framework">
                        Framework: <strong>{PROTOCOL_CATALOG[methodology].defaultFramework}</strong>
                      </span>
                    </div>
                    <p className="protocol-preview-desc">
                      {PROTOCOL_CATALOG[methodology].description}
                    </p>
                    <div className="protocol-preview-focus">
                      <strong>Foco:</strong> {PROTOCOL_CATALOG[methodology].domainFocus}
                    </div>
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>Descrição / Justificativa</label>
                <textarea
                  rows={4}
                  placeholder="Descreva o escopo geral, objetivos e contexto da revisão..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                  disabled={submitting}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? 'Criando...' : 'Criar e Configurar Protocolo'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
